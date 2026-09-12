# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from scripts.hphi_mesh_reference import rectangular_holes
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_native import solve_hphi,save_hphi_run
from superfish_ng.jobs import JobManager
from superfish_ng.gui_hphi import hphi_response


class HphiGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.manager=JobManager(self.root/'workspace');self.addCleanup(self.manager.close);self.lock=threading.Lock()
        self.project=HphiProject(HphiMeshCase(MeridionalMesh(**rectangular_holes(1)),modes=2))
    def request(self,action,**data):return hphi_response(self.manager,action,data,self.lock,self.root/'plot-cache')
    def import_job(self):
        native=self.root/'native';save_hphi_run(self.project.case,solve_hphi(self.project.case),native)
        return self.request('hphi-import',path=str(native))[0]['id']

    def test_strict_project_worker_result_and_both_native_types(self):
        for project in (self.project,HphiProject(CoaxialCase(.025,.05,.18,nr=3,nz=6,modes=2))):
            self.assertEqual(self.request('hphi-normalize',document=project.dumps())[0],project.to_dict())
            for data in ({},{'document':project.to_dict(),'extra':0},{'document':{'case':{}}}):
                with self.assertRaises(ValueError):self.request('hphi-normalize',**data)
            identifier=self.request('hphi-start',document=project.to_dict())[0]['id']
            self.assertEqual(self.manager.processes[identifier].wait(timeout=30),0)
            result,media=self.request('hphi-result',id=identifier)
            self.assertEqual(result['project'],project.to_dict());self.assertEqual(result['state']['numerical_validation'],'not_checked')
            self.assertEqual(len(result['files']),5);self.assertIsNone(result['result']['modes'][0]['r_over_q_accelerator_ohm'])
            self.assertIn('application/json',media)

    def test_native_download_and_probe_source_binding(self):
        identifier=self.import_job();native=self.manager.directory(identifier)/'solution';before={p.name:p.read_bytes() for p in native.iterdir()}
        for file,data in before.items():self.assertEqual(self.request('hphi-download',id=identifier,file=file)[0],data)
        points=[[.03,.09],[.04,.09]];csv,media=self.request('hphi-probe',id=identifier,points_rz_m=points,mode=2)
        metadata,_=self.request('hphi-probe-metadata',id=identifier,points_rz_m=points,mode=2)
        self.assertEqual(metadata['data_sha256'],hashlib.sha256(csv).hexdigest());self.assertEqual(metadata['mode'],2)
        self.assertEqual(metadata['points_rz_m'],points);self.assertIn('text/csv',media)
        self.assertEqual(metadata['native_sha256'],{k:hashlib.sha256(v).hexdigest() for k,v in before.items()})
        for points in ([[.06,.09]],[[0,.09]],[[True,.09]]):
            with self.assertRaises(ValueError):self.request('hphi-probe',id=identifier,points_rz_m=points)
        with self.assertRaises(ValueError):self.request('hphi-download',id=identifier,file='../project.json')
        self.assertEqual(before,{p.name:p.read_bytes() for p in native.iterdir()})

    def test_plot_cache_modes_units_and_tampering(self):
        try: import matplotlib
        except ImportError:self.skipTest('optional matplotlib unavailable')
        identifier=self.import_job();one,media=self.request('hphi-plot',id=identifier,mode=1,mesh=True,length_unit='m')
        self.assertTrue(one.startswith(b'\x89PNG'));self.assertEqual(media,'image/png')
        self.assertEqual(one,self.request('hphi-plot',id=identifier,mode=1,mesh=True,length_unit='m')[0])
        two,_=self.request('hphi-plot',id=identifier,mode=2,mesh=False,length_unit='mm');self.assertNotEqual(one,two)
        for params in ({'mode':True},{'mode':3},{'mesh':1},{'length_unit':'cm'}):
            with self.assertRaises(ValueError):self.request('hphi-plot',id=identifier,**params)
        for path in self.manager.directory(identifier).glob('hphi-*.png'):path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'integrity'):self.request('hphi-plot',id=identifier,mode=1,mesh=True,length_unit='m')

    def test_real_http_assets_authentication_and_strict_actions(self):
        from superfish_ng.gui import create_server
        try:server=create_server(self.root/'http')
        except PermissionError:self.skipTest('local HTTP binding is denied in this sandbox; verify in the permitted local HTTP run')
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base,token=server.launch_url.split('/#');origin=base
        try:
            for path,content in (('/hphi.html',b'Project JSON'),('/hphi.js',b'hphi-normalize')):
                with urllib.request.urlopen(base+path) as response:self.assertIn(content,response.read())
            def call(data,auth=True):
                headers={'Content-Type':'application/json','Origin':origin}
                if auth:headers['X-NG-Token']=token
                request=urllib.request.Request(base+'/api',data=json.dumps(data).encode(),headers=headers)
                return urllib.request.urlopen(request)
            payload=dict(action='hphi-normalize',document=self.project.to_dict())
            with call(payload) as response:self.assertEqual(json.load(response),self.project.to_dict())
            with self.assertRaises(urllib.error.HTTPError) as error:call(payload,False)
            self.assertEqual(error.exception.code,403);error.exception.close()
            with self.assertRaises(urllib.error.HTTPError) as error:call(dict(payload,extra=1))
            self.assertEqual(error.exception.code,400);error.exception.close()
        finally:
            server.shutdown();thread.join();server.server_close();server.manager.close()

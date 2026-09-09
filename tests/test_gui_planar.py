# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from superfish_ng.gui_planar import planar_response
from superfish_ng.jobs import JobManager
from superfish_ng.planar import PlanarCase, solve_planar
from superfish_ng.planar_saved import save_planar_run
from superfish_ng.planar_project import PlanarProject


class PlanarGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.manager=JobManager(self.root/'workspace');self.lock=threading.Lock()
        self.project=PlanarProject(PlanarCase(.31,.2,'tm',nx=6,ny=5,modes=2))
    def tearDown(self):
        self.manager.close();self.temp.cleanup()
    def request(self,action,**data):
        return planar_response(self.manager,action,data,self.lock,self.root/'plot-cache')
    def import_job(self):
        native=self.root/'native';save_planar_run(self.project.case,solve_planar(self.project.case),native)
        return self.request('planar-import',path=str(native))[0]['id']

    def test_strict_project_input_and_worker_result(self):
        self.assertEqual(self.request('planar-normalize',document=self.project.dumps())[0],self.project.to_dict())
        for data in ({'document':self.project.to_dict(),'extra':0},{}, {'document':{'case':{}}}):
            with self.assertRaises(ValueError):self.request('planar-normalize',**data)
        identifier=self.request('planar-start',document=self.project.to_dict())[0]['id']
        process=self.manager.processes[identifier];self.assertEqual(process.wait(timeout=30),0)
        response,media=self.request('planar-result',id=identifier)
        self.assertEqual(response['project'],self.project.to_dict())
        self.assertEqual(response['state']['numerical_validation'],'not_checked')
        self.assertEqual(response['result']['physics'],'cartesian_cutoff_rf')
        self.assertEqual(len(response['files']),5)
        self.assertIn('application/json',media)

    def test_native_download_and_si_probe_bind_to_source(self):
        identifier=self.import_job();native=self.manager.directory(identifier)/'solution'
        before={p.name:p.read_bytes() for p in native.iterdir()}
        for file,data in before.items():self.assertEqual(self.request('planar-download',id=identifier,file=file)[0],data)
        points=[[.03,.02],[.2,.1]]
        csv,media=self.request('planar-probe',id=identifier,points_xy_m=points,mode=2)
        metadata,_=self.request('planar-probe-metadata',id=identifier,points_xy_m=points,mode=2)
        self.assertEqual(hashlib.sha256(csv).hexdigest(),metadata['data_sha256'])
        self.assertEqual(metadata['points_xy_m'],points);self.assertEqual(metadata['mode'],2)
        self.assertEqual(metadata['native_sha256'],{k:hashlib.sha256(v).hexdigest() for k,v in before.items()})
        self.assertIn('text/csv',media)
        with self.assertRaises(ValueError):self.request('planar-probe',id=identifier,points_xy_m=[[.9,.1]])
        with self.assertRaises(ValueError):self.request('planar-download',id=identifier,file='../project.json')
        self.assertEqual(before,{p.name:p.read_bytes() for p in native.iterdir()})

    def test_plot_cache_integrity_and_selection(self):
        try:import matplotlib
        except ImportError:self.skipTest('optional matplotlib unavailable')
        identifier=self.import_job()
        one,media=self.request('planar-plot',id=identifier,mode=1,mesh=True,length_unit='m')
        self.assertTrue(one.startswith(b'\x89PNG'));self.assertEqual(media,'image/png')
        self.assertEqual(one,self.request('planar-plot',id=identifier,mode=1,mesh=True,length_unit='m')[0])
        two,_=self.request('planar-plot',id=identifier,mode=2,mesh=False,length_unit='mm')
        self.assertNotEqual(one,two)
        for path in self.manager.directory(identifier).glob('planar-*.png'):path.write_bytes(b'corrupt cache')
        with self.assertRaisesRegex(ValueError,'integrity'):self.request('planar-plot',id=identifier,mode=1,mesh=True,length_unit='m')
        for params in ({'mode':True},{'mode':3},{'mesh':1},{'length_unit':'cm'}):
            with self.assertRaises(ValueError):self.request('planar-plot',id=identifier,**params)

    def test_independent_study_and_verified_point_import(self):
        from superfish_ng.planar_study import PlanarStudy
        study=PlanarStudy(self.project,'uniform_scale',[1,2])
        self.assertEqual(self.request('planar-normalize-study',document=study.to_dict())[0],study.to_dict())
        identifier=self.request('planar-start-study',document=study.to_dict())[0]['id']
        self.assertEqual(self.manager.processes[identifier].wait(timeout=30),0)
        result,_=self.request('planar-study-result',id=identifier)
        self.assertEqual(result['result']['mode_tracking'],'not_performed')
        self.assertEqual(result['study'],study.to_dict())
        for index in (True,-1,2):
            with self.assertRaises(ValueError):self.request('planar-study-point',id=identifier,index=index)
        imported=self.request('planar-study-point',id=identifier,index=1)[0]['id']
        opened,_=self.request('planar-result',id=imported)
        self.assertEqual(opened['project'],study.projects()[1].to_dict())
        source=self.manager.directory(identifier)/'point-0001/solution'
        target=self.manager.directory(imported)/'solution'
        self.assertEqual({p.name:p.read_bytes() for p in source.iterdir()},{p.name:p.read_bytes() for p in target.iterdir()})

    def test_convergence_worker_diagnostics_and_level_import(self):
        from superfish_ng.planar_convergence import PlanarConvergence
        request=PlanarConvergence(PlanarProject(PlanarCase(.31,.2,nx=2,ny=2,modes=2)))
        self.assertEqual(self.request('planar-normalize-convergence',document=request.to_dict())[0],request.to_dict())
        identifier=self.request('planar-start-convergence',document=request.to_dict())[0]['id']
        self.assertEqual(self.manager.processes[identifier].wait(timeout=60),0)
        data,media=self.request('planar-convergence-result',id=identifier)
        self.assertEqual(data['request'],request.to_dict())
        self.assertEqual(len(data['result']['comparisons']),2)
        self.assertIn('application/json',media)
        with self.assertRaises(ValueError):self.request('planar-convergence-point',id=identifier,index=True)
        imported=self.request('planar-convergence-point',id=identifier,index=2)[0]['id']
        result=self.request('planar-result',id=imported)[0]
        self.assertEqual(result['project'],request.projects()[2].to_dict())

# SPDX-License-Identifier: Apache-2.0
from contextlib import ExitStack
from dataclasses import replace
import hashlib,json,tempfile,threading,unittest
from pathlib import Path
import numpy as np
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.axis_hphi import AxisHphiCase,AxisAccelerationPath
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_study import HphiStudy
from superfish_ng.hphi_native import hphi_result,read_hphi_run,solve_hphi
from superfish_ng.hphi_jobs import execute_hphi_project
from superfish_ng.hphi_display import display_hphi_fields
from superfish_ng.jobs import JobManager,read_job
from superfish_ng.gui_hphi import hphi_response
import test_axis_connected_mesh as geometry_tests


def example(order=2,acceleration=True):
    case=AxisHphiCase(AxisConnectedMesh(**geometry_tests.AxisConnectedMeshTests().data(1)),element_order=order,modes=2,
        acceleration=AxisAccelerationPath(.01,.16,.8,.02) if acceleration else None)
    return HphiProject(case,'mm')


class AxisHphiWorkspaceTests(unittest.TestCase):
    def test_explicit_path_scales_and_null_is_preserved(self):
        for order in (1,2):
            project=example(order);study=HphiStudy(project,'uniform_scale',[1,2]);first,second=study.projects()
            self.assertEqual(HphiProject.from_dict(project.to_dict()),project)
            self.assertEqual(second.case.acceleration,AxisAccelerationPath(.02,.32,.8,.04))
            np.testing.assert_array_equal(second.case.mesh.points_rz_m,2*first.case.mesh.points_rz_m)
            values=[hphi_result(solve_hphi(p.case))['modes'][0] for p in (first,second)]
            for key,factor in dict(frequency_hz=.5,stored_energy_j=1.,wall_loss_w=2**-1.5,q0=2**.5,
                r_over_q_accelerator_ohm=1.,r_over_q_circuit_ohm=1.).items():
                self.assertAlmostEqual(values[1][key]/values[0][key],factor,delta=1e-9,msg=key)
            a,b=(complex(v['vacc_v']['real'],v['vacc_v']['imag']) for v in values)
            self.assertLess(abs(abs(b/a)-2**-.5),1e-9)
            null=HphiStudy(example(order,False),'uniform_scale',[1,2])
            self.assertTrue(all(p.case.acceleration is None for p in null.projects()))
            with self.assertRaises(ValueError):HphiStudy(project,'/case/geometry/length_m',[.1,.2])

    def test_real_worker_import_cancel_and_restart_preserve_native(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as cleanup:
            root=Path(temp);manager=JobManager(root/'jobs');cleanup.callback(manager.close)
            cancelled=manager.start_hphi(example());self.assertEqual(manager.cancel(cancelled)['status'],'cancelled')
            identifier=manager.start_hphi(example());self.assertEqual(manager.processes[identifier].wait(timeout=30),0)
            self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
            source=manager.directory(identifier)/'solution';before={p.name:p.read_bytes() for p in source.iterdir()}
            for imported in (manager.import_hphi_result(source),manager.import_hphi_result(manager.directory(identifier))):
                self.assertEqual(before,{p.name:p.read_bytes() for p in (manager.directory(imported)/'solution').iterdir()})
                self.assertEqual(manager.status(imported,verify=True)['case_format'],'superfish_ng_axis_hphi_case')
            manager.close();manager=JobManager(root/'jobs');cleanup.callback(manager.close)
            self.assertEqual(manager.status(cancelled)['status'],'cancelled')
            self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
            solution=read_hphi_run(source);display=display_hphi_fields(solution)
            np.testing.assert_array_equal(display['fields']['Hphi_real_A_per_m'],solution.fields_in_cells(display['parent_cells'],display['barycentric'])['Hphi_real_A_per_m'])

    def test_kind_and_rehashed_acceleration_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for change in ('kind','acceleration'):
                directory=root/change;execute_hphi_project(example(),directory)
                if change=='kind':
                    for name in ('job.json','manifest.json'):
                        p=directory/name;raw=json.loads(p.read_text());raw['kind']='solve';p.write_text(json.dumps(raw))
                else:
                    p=directory/'project.json';raw=json.loads(p.read_text());raw['case']['acceleration']['beta']=.9;p.write_text(json.dumps(raw))
                    p=directory/'manifest.json';raw=json.loads(p.read_text());raw['files']={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in raw['files']};p.write_text(json.dumps(raw))
                with self.assertRaises(ValueError):read_job(directory)

    def test_gui_study_point_and_axis_probe_metadata(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as cleanup:
            root=Path(temp);manager=JobManager(root/'jobs');cleanup.callback(manager.close);lock=threading.Lock()
            def request(action,**data):return hphi_response(manager,action,data,lock,root/'cache')[0]
            study=HphiStudy(example(),'uniform_scale',[1,2]);document=study.to_dict()
            self.assertEqual(request('hphi-normalize-study',document=document),document)
            identifier=request('hphi-start-study',document=document)['id'];self.assertEqual(manager.processes[identifier].wait(timeout=30),0)
            result=request('hphi-study-result',id=identifier);self.assertEqual(result['result']['mode_tracking'],'not_performed')
            point=request('hphi-study-point',id=identifier,index=1)['id'];reply=request('hphi-result',id=point)
            self.assertEqual(reply['project'],study.projects()[1].to_dict())
            self.assertIsNotNone(reply['result']['modes'][0]['vacc_v'])
            points=[[0.,0.],[0.,.2]];data=request('hphi-probe',id=point,points_rz_m=points,mode=1)
            metadata=request('hphi-probe-metadata',id=point,points_rz_m=points,mode=1)
            self.assertIn(b'Hphi_real_A_per_m',data);self.assertEqual(metadata['data_sha256'],hashlib.sha256(data).hexdigest())
            self.assertEqual(metadata['points_rz_m'],points);self.assertEqual(metadata['case']['acceleration']['phase_origin_m'],.04)


if __name__=='__main__':unittest.main()

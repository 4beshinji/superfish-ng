# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.jobs import JobManager, read_job, _digest
from superfish_ng.planar import PlanarCase
from superfish_ng.planar_project import PlanarProject
from superfish_ng.planar_study import PlanarStudy
from superfish_ng.planar_study_jobs import execute_planar_study, read_planar_study, execute_prepared_planar_study, _prepare


class PlanarStudyTests(unittest.TestCase):
    def study(self):
        return PlanarStudy(PlanarProject(PlanarCase(.31,.2,'te',nx=6,ny=5,modes=2)),'uniform_scale',[1,2])
    def rehash(self,folder):
        path=folder/'manifest.json';m=json.loads(path.read_text());m['files']={k:_digest(folder/k) for k in m['files']};path.write_text(json.dumps(m))

    def test_strict_document_all_points_and_polygon_transform(self):
        study=self.study();self.assertEqual(PlanarStudy.from_dict(study.to_dict()),study)
        for key,value in [('study_version',True),('kind','mesh_convergence'),('extra',0),('parameter','/case/mesh/nx'),('values',[1,False]),('values',[1,float('nan')]),('values',[1,1e308])]:
            raw=study.to_dict();raw[key]=value
            with self.assertRaises(ValueError):PlanarStudy.from_dict(raw)
        project=PlanarProject.load('examples/planar/project_triangle_tm.json');original=project.to_dict()
        scaled=PlanarStudy(project,'uniform_scale',[1,3]).projects()[1]
        np.testing.assert_array_equal(scaled.case.mesh.points_xy_m,project.case.mesh.points_xy_m*3)
        np.testing.assert_array_equal(scaled.case.mesh.triangles,project.case.mesh.triangles)
        self.assertEqual(project.to_dict(),original)
        with self.assertRaises(ValueError):PlanarStudy(project,'/case/geometry/width_m',[.2,.3])
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'study.json';study.save(path);self.assertEqual(PlanarStudy.load(path),study)
            with self.assertRaises(FileExistsError):study.save(path)

    def test_saved_sweep_frequency_rf_and_untracked_ranks(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'run';result=execute_planar_study(self.study(),folder)
            self.assertEqual(read_planar_study(folder),result);self.assertEqual(read_job(folder)['kind'],'planar_study')
            self.assertEqual(result['mode_tracking'],'not_performed');self.assertEqual(result['numerical_validation'],'not_checked')
            for a,b in zip(result['points'][0]['modes'],result['points'][1]['modes']):
                self.assertAlmostEqual(b['frequency_hz']*2/a['frequency_hz'],1.,places=10)
                self.assertAlmostEqual(b['q0']/a['q0'],np.sqrt(2),places=9)
                self.assertIsNone(b['r_over_q_accelerator_ohm']);self.assertIsNone(b['r_over_q_circuit_ohm'])
            with self.assertRaises(FileExistsError):execute_planar_study(self.study(),folder)

    def test_rehashed_summary_and_point_project_changes_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'run';execute_planar_study(self.study(),folder)
            result_path=folder/'study-results.json';original=result_path.read_bytes()
            for change in ('rf','index','tracking','extra'):
                data=json.loads(original)
                if change=='rf':data['points'][0]['modes'][0]['q0']*=1.1
                elif change=='index':data['points'][1]['index']=True
                elif change=='tracking':data['mode_tracking']='tracked'
                else:data['unrecognized']=1
                result_path.write_text(json.dumps(data));self.rehash(folder)
                with self.assertRaises(ValueError):read_job(folder)
            result_path.write_bytes(original)
            point=folder/'point-0001';path=point/'project.json';data=json.loads(path.read_text());data['display_length_unit']='m';path.write_text(json.dumps(data));self.rehash(point);self.rehash(folder)
            with self.assertRaisesRegex(ValueError,'Project'):read_planar_study(folder)

    def test_kind_downgrade_missing_files_and_extra_point_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'run';execute_planar_study(self.study(),folder)
            saved={name:(folder/name).read_bytes() for name in ('manifest.json','job.json')}
            for kind in (None,'study','solve','planar_solve'):
                for name,raw in saved.items():
                    data=json.loads(raw)
                    if kind is None:data.pop('kind')
                    else:data['kind']=kind
                    (folder/name).write_text(json.dumps(data))
                with self.assertRaises(ValueError):read_job(folder)
            for name,raw in saved.items():(folder/name).write_bytes(raw)
            (folder/'point-extra').mkdir()
            with self.assertRaises(ValueError):read_planar_study(folder)
            (folder/'point-extra').rmdir();(folder/'point-0001/solution/manifest.json').unlink()
            with self.assertRaises(ValueError):read_job(folder)

    def test_queued_change_and_completed_reentry_preserve_results(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'run';study=self.study();_prepare(study,folder)
            data=study.to_dict();data['values']=[1.,3.];(folder/'study.json').write_text(json.dumps(data))
            with patch('superfish_ng.planar_study_jobs.execute_planar_project',side_effect=AssertionError('must not solve')):
                with self.assertRaisesRegex(ValueError,'changed'):execute_prepared_planar_study(folder)
            self.assertEqual(read_job(folder)['status'],'failed')
            completed=Path(temp)/'complete';execute_planar_study(study,completed);before={str(p.relative_to(completed)):p.read_bytes() for p in completed.rglob('*') if p.is_file()}
            with self.assertRaises(ValueError):execute_prepared_planar_study(completed)
            self.assertEqual(before,{str(p.relative_to(completed)):p.read_bytes() for p in completed.rglob('*') if p.is_file()})

    def test_completion_input_change_and_point_save_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'run';original=read_planar_study
            def change_after_read(path):
                result=original(path);data=json.loads((path/'study.json').read_text());data['project']['display_length_unit']='m';(path/'study.json').write_text(json.dumps(data));return result
            with patch('superfish_ng.planar_study_jobs.read_planar_study',side_effect=change_after_read):
                with self.assertRaisesRegex(ValueError,'changed'):execute_planar_study(self.study(),folder)
            self.assertEqual(read_job(folder)['status'],'failed')
            with patch('superfish_ng.planar_study_jobs.execute_planar_project',side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):execute_planar_study(self.study(),Path(temp)/'disk')
            self.assertEqual(read_job(Path(temp)/'disk')['status'],'failed')

    def test_worker_cancel_restart_and_import_point(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manager=JobManager(root/'workspace')
            try:
                large=PlanarStudy(PlanarProject(PlanarCase(.31,.2,nx=300,ny=300)),'uniform_scale',[1,2]);cancelled=manager.start_planar_study(large)
                self.assertEqual(manager.cancel(cancelled)['status'],'cancelled');self.assertIsNotNone(manager.processes[cancelled].poll())
                identifier=manager.start_planar_study(self.study());self.assertEqual(manager.processes[identifier].wait(timeout=30),0)
                self.assertEqual(manager.status(identifier,verify=True)['computed_points'],2)
                source=manager.directory(identifier)/'point-0001';before={p.name:p.read_bytes() for p in (source/'solution').iterdir()}
                imported=manager.import_planar_result(source);self.assertEqual(before,{p.name:p.read_bytes() for p in (manager.directory(imported)/'solution').iterdir()})
                manager.close();manager=JobManager(root/'workspace');self.assertEqual(manager.status(identifier,verify=True)['status'],'complete');self.assertEqual(manager.status(imported,verify=True)['status'],'complete')
            finally:manager.close()
            with self.assertRaises(ValueError):manager.start_planar_study(self.study())

    def test_cli_execution_and_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'study.json';self.study().save(path)
            for command in (['execute-planar-study',str(path),'--out',str(root/'run')],['replay-planar-study',str(root/'run')]):
                result=subprocess.run([sys.executable,'-m','superfish_ng',*command],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout)['mode_tracking'],'not_performed')

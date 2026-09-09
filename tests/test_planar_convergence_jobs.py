# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng.planar import PlanarCase
from superfish_ng.planar_project import PlanarProject
from superfish_ng.planar_convergence import PlanarConvergence
from superfish_ng.planar_convergence_jobs import (
    execute_planar_convergence, read_planar_convergence,
    execute_prepared_planar_convergence, _prepare, _snapshot,
)
from superfish_ng.jobs import JobManager, read_job


class PlanarConvergenceJobTests(unittest.TestCase):
    def request(self):
        return PlanarConvergence(PlanarProject(PlanarCase(.31,.2,nx=2,ny=2,modes=2)))

    def rehash(self, directory):
        path=directory/'manifest.json';data=json.loads(path.read_text())
        data['files']={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in data['files']}
        path.write_text(json.dumps(data))

    def test_saved_diagnostic_and_rehashed_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'run';request=self.request()
            result=execute_planar_convergence(request,directory)
            self.assertEqual(read_planar_convergence(directory),result)
            self.assertEqual(read_job(directory)['numerical_validation'],result['status'])
            path=directory/'convergence-results.json';original=path.read_bytes()
            for key in ('status','phase','threshold','rank'):
                bad=json.loads(original)
                if key=='status':bad['status']='CERTIFIED'
                elif key=='phase':bad['comparisons'][0]['modes'][0]['coarse_phase_multiplier']*=-1
                elif key=='threshold':bad['decisions'][0]['checks']['frequency_relative']['threshold']=.9
                else:bad['decisions'][0]['mode_rank']=True
                path.write_text(json.dumps(bad));self.rehash(directory)
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'summary differs'):
                    read_job(directory)
            path.write_bytes(original);self.rehash(directory)
            before=_snapshot(directory,request)
            with self.assertRaises(ValueError):execute_prepared_planar_convergence(directory)
            self.assertEqual(before,_snapshot(directory,request))
            point=directory/'point-0001';path=point/'project.json';bad=json.loads(path.read_text())
            bad['display_length_unit']='m';path.write_text(json.dumps(bad));self.rehash(point);self.rehash(directory)
            with self.assertRaisesRegex(ValueError,'Project'):read_planar_convergence(directory)

    def test_kind_downgrade_and_extra_level_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'run';execute_planar_convergence(self.request(),directory)
            saved={name:(directory/name).read_bytes() for name in ('job.json','manifest.json')}
            for kind in (None,'planar_study','study','planar_solve'):
                for name,raw in saved.items():
                    data=json.loads(raw)
                    if kind is None:data.pop('kind')
                    else:data['kind']=kind
                    (directory/name).write_text(json.dumps(data))
                with self.assertRaises(ValueError):read_job(directory)
            for name,raw in saved.items():(directory/name).write_bytes(raw)
            (directory/'point-extra').mkdir()
            with self.assertRaises(ValueError):read_planar_convergence(directory)

    def test_changed_queued_input_and_completion_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'run';request=self.request();_prepare(request,directory)
            path=directory/'convergence.json';path.write_text(path.read_text()+' ')
            with patch('superfish_ng.planar_convergence_jobs.execute_planar_project',side_effect=AssertionError('must not solve')):
                with self.assertRaisesRegex(ValueError,'changed'):execute_prepared_planar_convergence(directory)
            self.assertEqual(read_job(directory)['status'],'failed')
            original=read_planar_convergence
            def changed(path):
                result=original(path);request_path=path/'convergence.json'
                request_path.write_text(request_path.read_text()+' ');return result
            with patch('superfish_ng.planar_convergence_jobs.read_planar_convergence',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed'):execute_planar_convergence(request,Path(tmp)/'completion')
            self.assertEqual(read_job(Path(tmp)/'completion')['status'],'failed')

    def test_actual_worker_cancel_restart_and_level_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager=JobManager(Path(tmp)/'workspace')
            try:
                cancelled=manager.start_planar_convergence(self.request())
                self.assertEqual(manager.cancel(cancelled)['status'],'cancelled')
                self.assertIsNotNone(manager.processes[cancelled].poll())
                identifier=manager.start_planar_convergence(self.request())
                self.assertEqual(manager.processes[identifier].wait(timeout=60),0)
                before=_snapshot(manager.directory(identifier),self.request())
                imported=manager.import_planar_result(manager.directory(identifier)/'point-0002')
                self.assertEqual(before,_snapshot(manager.directory(identifier),self.request()))
                manager.close();manager=JobManager(Path(tmp)/'workspace')
                self.assertEqual(manager.status(identifier,verify=True)['computed_points'],3)
                self.assertEqual(manager.status(imported,verify=True)['status'],'complete')
            finally:manager.close()
            with self.assertRaises(ValueError):manager.start_planar_convergence(self.request())

    def test_cli_execute_and_full_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=root/'request.json';self.request().save(request)
            results=[]
            for command in (['execute-planar-convergence',str(request),'--out',str(root/'run')],
                            ['replay-planar-convergence',str(root/'run')]):
                result=subprocess.run([sys.executable,'-m','superfish_ng',*command],capture_output=True,text=True,timeout=60)
                self.assertEqual(result.returncode,0,result.stderr);results.append(json.loads(result.stdout))
            self.assertEqual(*results)

# SPDX-License-Identifier: Apache-2.0
import json
import shutil
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import numpy as np
from superfish_ng import solve
from superfish_ng.completion import digest
from superfish_ng.io import save_run
from superfish_ng.jobs import JobManager, execute_project, read_job
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.project import Project
from superfish_ng.te_saved import read_te_run
from superfish_ng.te import te_quantities
from test_te import cavity
from test_te_curved import sphere


def await_job(manager, identifier):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        state=manager.status(identifier)
        if state['status'] not in ('queued','running'):
            return state
        time.sleep(.03)
    raise AssertionError('TE worker did not finish within 30 seconds')


class TEJobTests(unittest.TestCase):
    def test_project_and_native_job_preserve_p1_p2_and_curved_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i,c in enumerate((cavity(order=1,n=8,modes=1),cavity(n=8,modes=1),sphere())):
                project=Project.from_dict(dict(project_version=1,case=c.to_dict()))
                folder=Path(tmp)/str(i);state=execute_project(project,folder)
                self.assertEqual(state['status'],'complete')
                self.assertEqual(state['numerical_validation'],'not_checked')
                actual=read_te_run(folder/'solution');expected=solve(c)
                np.testing.assert_array_equal(actual.coefficients_v_per_m2,expected.coefficients_v_per_m2)
                self.assertEqual(te_quantities(actual),te_quantities(expected))
                self.assertIsNone(te_quantities(actual)['r_over_q_accelerator_ohm'])

    def test_manifest_cannot_hide_missing_te_geometry_or_a_different_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'run';c=sphere();execute_project(Project(c),folder)
            manifest=json.loads((folder/'manifest.json').read_text());original=json.dumps(manifest)
            del manifest['files']['solution/geometry.npz']
            (folder/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'TE job manifest'):read_job(folder)
            manifest=json.loads(original)
            project=Project(replace(c,normalization_j=2.));(folder/'project.json').write_text(json.dumps(project.to_dict()))
            manifest['files']['project.json']=digest(folder/'project.json')
            (folder/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'case differs'):read_job(folder)

    def test_forged_native_coefficients_fail_even_with_all_updated_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'run';execute_project(Project(cavity(n=8,modes=1)),folder)
            solution=folder/'solution';path=solution/'fields.npz'
            with np.load(path) as data:arrays={key:data[key] for key in data.files}
            arrays['coefficients_v_per_m2']*=1.01;np.savez_compressed(path,**arrays)
            marker=json.loads((solution/'te_complete.json').read_text());marker['files']['fields.npz']=digest(path)
            (solution/'te_complete.json').write_text(json.dumps(marker))
            manifest=json.loads((folder/'manifest.json').read_text())
            for name in ('fields.npz','te_complete.json'):manifest['files']['solution/'+name]=digest(solution/name)
            (folder/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'normalization'):read_job(folder)

    def test_direct_import_preserves_external_source_mesh_and_can_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);c=cavity(n=8,modes=1)
            mesh=mesh_to_dict(make_mesh(replace(c,nr=6,nz=9)))
            original=solve(c,mesh_data=mesh)
            self.assertGreater(abs(original.frequencies_hz[0]/solve(c).frequencies_hz[0]-1),1e-5)
            save_run(c,original,root/'native')
            manager=JobManager(root/'jobs')
            try:
                identifier=manager.import_result(root/'native')
                imported=manager.directory(identifier)
                state=manager.status(identifier)
                self.assertEqual(state['origin'],'imported')
                self.assertEqual(state['source_completion'],'verified TE native completion')
                project=Project.load(imported/'project.json')
                self.assertEqual(project.to_dict()['project_version'],2)
                self.assertEqual(project.mesh_data,mesh)
                execute_project(project,root/'rerun')
                actual=read_te_run(root/'rerun/solution')
                np.testing.assert_array_equal(actual.coefficients_v_per_m2,original.coefficients_v_per_m2)
                second=manager.import_result(imported)
                self.assertEqual(Project.load(manager.directory(second)/'project.json'),project)
                self.assertEqual(manager.status(second)['source_completion'],'verified manifest')
                forged=Project(c,mesh_data=mesh_to_dict(make_mesh(c)))
                (imported/'project.json').write_text(json.dumps(forged.to_dict()))
                manifest=json.loads((imported/'manifest.json').read_text())
                manifest['files']['project.json']=digest(imported/'project.json')
                (imported/'manifest.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError,'source mesh differs'):read_job(imported)
            finally:manager.close()

    def test_worker_cancel_restart_and_managed_curved_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manager=JobManager(root)
            try:
                cancelled=manager.start(Project(cavity(n=300,modes=1)));manager.cancel(cancelled)
                self.assertEqual(manager.status(cancelled)['status'],'cancelled')
                identifier=manager.start(Project(sphere()))
                self.assertEqual(await_job(manager,identifier)['status'],'complete')
            finally:manager.close()
            restarted=JobManager(root)
            try:
                self.assertEqual(restarted.status(identifier)['status'],'complete')
                imported=restarted.import_result(restarted.directory(identifier))
                self.assertEqual(restarted.status(imported)['origin'],'imported')
                a=read_te_run(restarted.directory(identifier)/'solution')
                b=read_te_run(restarted.directory(imported)/'solution')
                np.testing.assert_array_equal(a.coefficients_v_per_m2,b.coefficients_v_per_m2)
            finally:restarted.close()

    def test_import_change_never_publishes_a_complete_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);c=cavity(n=8,modes=1);save_run(c,solve(c),root/'native')
            manager=JobManager(root/'jobs');copy=shutil.copyfile
            def changing(source,target,*args,**kwargs):
                result=copy(source,target,*args,**kwargs)
                if Path(target).name=='fields.npz':
                    with (root/'native/fields.npz').open('ab') as stream:stream.write(b'changed')
                return result
            try:
                with patch('superfish_ng.te_jobs.shutil.copyfile',side_effect=changing):
                    with self.assertRaisesRegex(ValueError,'changed'):manager.import_result(root/'native')
                states=manager.list();self.assertEqual(len(states),1)
                self.assertEqual(states[0]['status'],'failed')
                self.assertFalse((manager.directory(states[0]['id'])/'solution/te_complete.json').exists())
            finally:manager.close()

    def test_job_verification_rechecks_files_and_outer_manifest_after_native_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kind in ('native_file','manifest'):
                folder=Path(tmp)/kind;execute_project(Project(cavity(n=8,modes=1)),folder)
                def changing(directory):
                    result=read_te_run(directory)
                    if kind=='native_file':
                        with (Path(directory)/'modes.csv').open('a') as stream:stream.write('changed during verification\n')
                    else:
                        path=folder/'manifest.json';data=json.loads(path.read_text())
                        data['changed_after_initial_read']=True;path.write_text(json.dumps(data))
                    return result
                with patch('superfish_ng.te_jobs.read_te_run',side_effect=changing):
                    with self.assertRaisesRegex(ValueError,'changed during verification'):read_job(folder)

    def test_unconnected_project_workflows_are_rejected(self):
        from superfish_ng.studies import Study
        from superfish_ng.tuning import _request
        from superfish_ng.rf_optimization import validate_optimization_request
        with self.assertRaisesRegex(ValueError,'TE reflected'):Project(cavity(),reflect_full=True)
        with self.assertRaisesRegex(ValueError,'mesh convergence requires'):Study(Project(cavity()),'mesh_convergence','nr',[8,16])
        root=Path(__file__).resolve().parents[1]
        for filename,validator in (('examples/optimization/curved_rf.json',validate_optimization_request),('examples/tuning/curved_affine_scale.json',_request)):
            request=json.loads((root/filename).read_text());request['project']['case']['model']['polarization']='te'
            with self.assertRaisesRegex(ValueError,'TE .*fixed' if validator is _request else 'TE .*integration is pending'):validator(request)

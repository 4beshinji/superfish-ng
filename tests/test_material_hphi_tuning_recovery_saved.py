# SPDX-License-Identifier: Apache-2.0
"""Owned material tuning recovery: actual CLI search, worker refinement and replay."""
from contextlib import ExitStack,redirect_stdout
from copy import deepcopy
import io,json,os,tempfile,unittest
from pathlib import Path
import numpy as np
from scripts.validate_coaxial import radial_roots
from superfish_ng.cli import main
from superfish_ng.jobs import JobManager
from superfish_ng.hphi_project import HphiProject
from superfish_ng.material_hphi_saved import read_material_hphi_run,material_hphi_result
from superfish_ng.material_hphi_tuning_saved import read_material_hphi_tune,replay_material_hphi_tune
from superfish_ng.material_hphi_tuning_jobs import verify_material_hphi_tune_job
from test_material_hphi_tuning_recovery import request
from test_material_hphi_tuning import request as base_request
from superfish_ng.constants import C0


def root_for(cleanup,name):
    artifact=os.environ.get('SUPERFISH_MATERIAL_TUNE_RECOVERY_TEST_OUT')
    if artifact:
        root=Path(artifact).resolve()/name;root.mkdir(parents=True,exist_ok=False)
        return root
    return Path(cleanup.enter_context(tempfile.TemporaryDirectory()))


def verify_job(manager,identifier):
    directory=manager.directory(identifier)
    state=manager.status(identifier,verify=False);state.pop('id')
    manifest=json.loads((directory/'manifest.json').read_text())
    return verify_material_hphi_tune_job(directory,state,manifest)


class MaterialHphiTuneRecoverySavedTests(unittest.TestCase):
    def test_cli_search_worker_refinement_owned_recovery_after_restart(self):
        with ExitStack() as cleanup,redirect_stdout(io.StringIO()):
            root=root_for(cleanup,'recovery');q=request()
            length=np.pi/radial_roots(.0625,.125,1)[0]
            path=root/'request.json';path.write_text(json.dumps(q,indent=2)+'\n')
            self.assertEqual(main(['tune-material-hphi',str(path),'--out',str(root/'first'),'--max-new-trials','3']),0)
            first=read_material_hphi_tune(root/'first/checkpoint-003.json')
            self.assertEqual(first['status'],'PAUSED')
            self.assertEqual(first['trials'][2]['identity_recovery']['status'],'PASS')
            manager=JobManager(root/'workspace');cleanup.callback(manager.close)
            identifier=manager.start_material_hphi_tune(q,checkpoint=first)
            self.assertEqual(manager.processes[identifier].wait(timeout=1800),0)
            manager.close();(root/'first').rename(root/'moved-original')
            manager=JobManager(root/'workspace');cleanup.callback(manager.close)
            final=verify_job(manager,identifier)
            self.assertEqual(final['status'],'TUNED');self.assertEqual(final['request'],q)
            self.assertEqual(final['trials'][:3],first['trials'])
            self.assertEqual(final['trial_sources_sha256'][:3],first['trial_sources_sha256'])
            self.assertEqual([t['identity_recovery']['anchor_trial_index'] for t in final['trials'][2:]],[1,2])
            for index,new in enumerate(final['trial_runs'][:3]):
                old=root/'moved-original'/f'trial-{index+1:03d}'
                for item in old.rglob('*'):
                    if item.is_file():self.assertEqual(item.read_bytes(),(Path(new)/item.relative_to(old)).read_bytes())
            for trial,run in zip(final['trials'],final['trial_runs']):
                solution=read_material_hphi_run(Path(run)/'solution');r,z=solution.space.dof_points.T
                exact=np.cos(np.pi*z/(length*trial['value']))
                self.assertAlmostEqual(trial['frequency_hz']/(C0/(12*length*trial['value'])),1.,delta=1e-3)
                actual=solution.coefficients[:,trial['current_mode_ids'].index('TEM')];mass=solution.mass
                self.assertGreater(abs(actual@(mass@exact))/np.sqrt((actual@(mass@actual))*(exact@(mass@exact))),.999)
                native=material_hphi_result(solution)
                self.assertEqual(native,json.loads((Path(run)/'solution/results.json').read_text()))
                for mode in native['modes']:
                    self.assertIsNone(mode['r_over_q_accelerator_ohm']);self.assertIsNone(mode['r_over_q_circuit_ohm'])
                    self.assertTrue(mode['accelerating_quantities_reason'])
            before={str(p):p.read_bytes() for run in final['trial_runs'] for p in Path(run).rglob('*') if p.is_file()}
            changed=deepcopy(final);changed['trials'][3]['identity_recovery']['anchor_trial_index']=0
            with self.assertRaisesRegex(ValueError,'checkpoint differs'):replay_material_hphi_tune(changed)
            changed=deepcopy(final);changed['request']['identity_recovery']['anchor_selection']='fixed_trial'
            changed['request']['identity_recovery']['anchor_trial_index']=0
            with self.assertRaises(ValueError):replay_material_hphi_tune(changed)
            self.assertEqual(before,{p:Path(p).read_bytes() for p in before})
            (root/'accepted.json').write_text(json.dumps(dict(status='PASS',job=identifier,request=q,
                decision=final['decision'],native_files_unchanged=len(before)),indent=2)+'\n')

    def test_worker_preserves_material_axis_rf_and_import(self):
        from dataclasses import replace
        from superfish_ng.axis_hphi import AxisAccelerationPath
        from test_material_hphi_workspace import example
        with ExitStack() as cleanup:
            root=root_for(cleanup,'axis');project=example();q=base_request()
            q.update(project=project.to_dict(),initial_ids=['first'],mode_id='first')
            manager=JobManager(root/'workspace');cleanup.callback(manager.close)
            identifier=manager.start_material_hphi_tune(q,max_new_trials=1)
            self.assertEqual(manager.processes[identifier].wait(timeout=900),0)
            result=verify_job(manager,identifier)
            self.assertEqual(len(result['trial_runs']),1)
            run=Path(result['trial_runs'][0]);owned=HphiProject.load(run/'project.json')
            self.assertEqual(owned.to_dict(),project.to_dict())
            self.assertEqual(len(owned.case.partition.mesh.holes_rz_m),1)
            solution=read_material_hphi_run(run/'solution');native=material_hphi_result(solution)
            self.assertEqual(native,json.loads((run/'solution/results.json').read_text()))
            for mode in native['modes']:
                self.assertGreater(mode['r_over_q_accelerator_ohm'],0.)
                self.assertAlmostEqual(mode['r_over_q_accelerator_ohm']/mode['r_over_q_circuit_ohm'],2.)
                self.assertIsNone(mode['accelerating_quantities_reason'])
            imported=manager.import_hphi_result(run/'solution',project=owned)
            imported_run=manager.directory(imported)
            self.assertEqual(HphiProject.load(imported_run/'project.json').to_dict(),project.to_dict())
            for item in (run/'solution').iterdir():
                self.assertEqual(item.read_bytes(),(imported_run/'solution'/item.name).read_bytes())
            with self.assertRaisesRegex(ValueError,'vacuum'):
                replace(project.case,acceleration=AxisAccelerationPath(.01,.1,.8,.02))
            bad=deepcopy(q);bad['project']['case']['partition']['materials'][0]['loss_tangent']=.01
            path=root/'unsupported.json';path.write_text(json.dumps(bad))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(['tune-material-hphi',str(path),'--out',str(root/'rejected')]),2)
            self.assertFalse((root/'rejected').exists())
            (root/'accepted.json').write_text(json.dumps(dict(status='PASS',job=identifier,
                tuning_status=result['status'],scope='one owned vacuum-axis/material-hole trial and native reimport; no successful hole tuning claim',
                request=q),indent=2)+'\n')

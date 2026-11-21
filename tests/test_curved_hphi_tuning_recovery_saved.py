# SPDX-License-Identifier: Apache-2.0
"""Owned curved tuning recovery: actual CLI search, worker refinement and replay."""
from contextlib import ExitStack,redirect_stdout
from copy import deepcopy
import io,json,os,tempfile,unittest
from pathlib import Path
import numpy as np
from scripts.validate_coaxial import radial_roots
from superfish_ng.cli import main
from superfish_ng.jobs import JobManager
from superfish_ng.hphi_project import HphiProject
from superfish_ng.curved_hphi import solve_curved_hphi
from superfish_ng.curved_hphi_shape_tuning import CurvedHphiShapeLaw
from superfish_ng.curved_hphi_saved import read_curved_hphi_run,save_curved_hphi_run,curved_hphi_result
from superfish_ng.curved_hphi_tuning_saved import read_curved_hphi_tune,replay_curved_hphi_tune
from superfish_ng.curved_hphi_tuning_jobs import verify_curved_hphi_tune_job
from test_curved_hphi_tuning_recovery import request
from test_curved_hphi_tuning import request as hole_request


def root_for(cleanup,name):
    artifact=os.environ.get('SUPERFISH_CURVED_TUNE_RECOVERY_TEST_OUT')
    if artifact:
        root=Path(artifact).resolve()/name;root.mkdir(parents=True,exist_ok=False)
        return root
    return Path(cleanup.enter_context(tempfile.TemporaryDirectory()))


def verify_job(manager,identifier):
    directory=manager.directory(identifier)
    state=manager.status(identifier,verify=False);state.pop('id')
    manifest=json.loads((directory/'manifest.json').read_text())
    return verify_curved_hphi_tune_job(directory,state,manifest)


class CurvedHphiTuneRecoverySavedTests(unittest.TestCase):
    def test_cli_search_worker_refinement_owned_recovery_after_restart(self):
        with ExitStack() as cleanup,redirect_stdout(io.StringIO()):
            root=root_for(cleanup,'recovery');q=request(shear=1/64)
            q['bounds']=[.8,1.12];q['controls']['relative_cluster_gap']=.06
            project=HphiProject.from_dict(q['project']);law=CurvedHphiShapeLaw.from_dict(q['shape_law'])
            middle=q['bounds'][0]/2+q['bounds'][1]/2
            target=solve_curved_hphi(law.apply(project,middle).project.case)
            length=np.pi/radial_roots(.0625,.125,1)[0];r,z=target.space.dof_points.T
            exact=np.cos(np.pi*(z-middle*r*r/64)/(length*middle));mass=target.mass
            overlaps=[abs(v@(mass@exact))/np.sqrt((v@(mass@v))*(exact@(mass@exact))) for v in target.coefficients.T]
            self.assertGreater(max(overlaps),.999)
            q['target_hz']=float(target.frequencies_hz[int(np.argmax(overlaps))])
            save_curved_hphi_run(target.case,target,root/'independent-target')
            path=root/'request.json';path.write_text(json.dumps(q,indent=2)+'\n')
            self.assertEqual(main(['tune-curved-hphi',str(path),'--out',str(root/'first'),'--max-new-trials','3']),0)
            first=read_curved_hphi_tune(root/'first/checkpoint-003.json')
            self.assertEqual(first['status'],'PAUSED')
            self.assertEqual(first['trials'][2]['identity_recovery']['status'],'PASS')
            manager=JobManager(root/'workspace');cleanup.callback(manager.close)
            identifier=manager.start_curved_hphi_tune(q,checkpoint=first)
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
                solution=read_curved_hphi_run(Path(run)/'solution');r,z=solution.space.dof_points.T
                exact=np.cos(np.pi*(z-trial['value']*r*r/64)/(length*trial['value']))
                actual=solution.coefficients[:,trial['current_mode_ids'].index('TEM')];mass=solution.mass
                self.assertGreater(abs(actual@(mass@exact))/np.sqrt((actual@(mass@actual))*(exact@(mass@exact))),.999)
                self.assertEqual(curved_hphi_result(solution),json.loads((Path(run)/'solution/results.json').read_text()))
            before={str(p):p.read_bytes() for run in final['trial_runs'] for p in Path(run).rglob('*') if p.is_file()}
            changed=deepcopy(final);changed['trials'][3]['identity_recovery']['anchor_trial_index']=0
            with self.assertRaisesRegex(ValueError,'checkpoint differs'):replay_curved_hphi_tune(changed)
            changed=deepcopy(final);changed['request']['identity_recovery']['anchor_selection']='fixed_trial'
            changed['request']['identity_recovery']['anchor_trial_index']=0
            with self.assertRaises(ValueError):replay_curved_hphi_tune(changed)
            self.assertEqual(before,{p:Path(p).read_bytes() for p in before})
            (root/'accepted.json').write_text(json.dumps(dict(status='PASS',job=identifier,request=q,
                decision=final['decision'],native_files_unchanged=len(before)),indent=2)+'\n')

    def test_worker_owns_complete_curved_hole_project_and_rf(self):
        with ExitStack() as cleanup:
            root=root_for(cleanup,'hole');q=hole_request()
            manager=JobManager(root/'workspace');cleanup.callback(manager.close)
            identifier=manager.start_curved_hphi_tune(q,max_new_trials=1)
            self.assertEqual(manager.processes[identifier].wait(timeout=900),0)
            result=verify_job(manager,identifier)
            self.assertEqual(result['status'],'PAUSED')
            run=Path(result['trial_runs'][0]);project=HphiProject.load(run/'project.json')
            self.assertEqual(project.to_dict(),q['project'])
            self.assertEqual(len(project.case.geometry.base_mesh.holes_rz_m),1)
            solution=read_curved_hphi_run(run/'solution')
            self.assertEqual(curved_hphi_result(solution),json.loads((run/'solution/results.json').read_text()))
            (root/'accepted.json').write_text(json.dumps(dict(status='PASS',job=identifier,
                scope='one owned curved hole trial; successful hole tuning is covered separately',request=q),indent=2)+'\n')

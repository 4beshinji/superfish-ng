# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
from scipy.special import jn_zeros
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study
from superfish_ng.jobs import execute_project,JobManager
from superfish_ng.completion import digest
from superfish_ng.adaptive_study import execute_adaptive_study,read_adaptive_study,replay_adaptive_study


class AdaptiveStudyIdentityRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        zeros=jn_zeros(0,2);crossing=float(np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2))
        case=Case(((0.,.1),(.04,.1)),nr=8,nz=8,modes=3,element_order=2)
        study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/0',[.04,.055,crossing,.075,.08,.085])
        self.controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,
            relative_cluster_gap=.001,minimum_relative_singular_value=1e-8)
        retained=dict(self.controls,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)
        steps=[dict(retained) for _ in range(5)];steps[0]['minimum_overlap']=.9999999988
        # This later, explicitly declared near-frequency grouping is distinct
        # from the earlier analytical degeneracy.
        steps[3]['relative_cluster_gap']=.2
        self.request=dict(schema_version=2,study=study.to_dict(),initial_ids=['TM010','TM020','TM011'],step_controls=steps,
            adaptive=dict(max_depth=4,max_attempts=16,minimum_parameter_step=1e-6),
            identity_recoveries=[dict(target_index=3,anchor_target_index=1,controls=deepcopy(self.controls)),
                                 dict(target_index=5,anchor_target_index=3,controls=deepcopy(self.controls))])

    def test_inserted_point_does_not_shift_the_declared_anchor(self):
        first=execute_adaptive_study(self.request,self.root/'first',max_new_attempts=1)
        self.assertEqual(first['schema_version'],3);self.assertEqual(first['attempts'][0]['decision'],'BISECT')
        original={str(p):digest(p) for p in (self.root/'first').rglob('*') if p.is_file()}
        with patch('superfish_ng.adaptive_study.execute_project',wraps=execute_project) as solve:
            anchor=execute_adaptive_study(self.request,self.root/'anchor',max_new_attempts=2,checkpoint=first)
        self.assertEqual(solve.call_count,1);self.assertEqual(anchor['accepted_point_indices'],[0,2,1])
        recovered=execute_adaptive_study(self.request,self.root/'recovered',max_new_attempts=2,checkpoint=anchor)
        event=recovered['attempts'][-1]['identity_recovery']
        self.assertEqual(event['anchor_target_index'],1);self.assertEqual(event['anchor_point_index'],1)
        self.assertEqual(event['anchor_snapshot_index'],2)
        self.assertEqual(event['event']['comparison']['request']['previous_run'],str(Path(recovered['points'][1]['run'])/'solution'))
        self.assertEqual(recovered['history']['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual(recovered['reached_target_indices'],[0,1,2,3]);self.assertTrue(recovered['can_resume'])
        final=execute_adaptive_study(self.request,self.root/'final',checkpoint=recovered)
        self.assertEqual(final['status'],'COMPLETE');self.assertEqual(len(final['points']),7)
        self.assertEqual(final['attempts'][-1]['identity_recovery']['anchor_target_index'],3)
        self.assertEqual(final['attempts'][-1]['identity_recovery']['anchor_snapshot_index'],4)
        self.assertEqual(len(final['history']['identity_recoveries']),2)
        with patch('superfish_ng.jobs.solve',side_effect=AssertionError('replay must not solve')):
            self.assertEqual(replay_adaptive_study(final),final)
        for path,value in original.items():self.assertEqual(digest(path),value)

    def test_failed_recovery_keeps_accepted_history_and_does_not_bisect_or_advance(self):
        self.request['identity_recoveries'][0]['target_index']=2
        result=execute_adaptive_study(self.request,self.root/'failed')
        self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(result['stop_reason'],'identity_recovery_unverified')
        self.assertEqual(len(result['points']),4);self.assertEqual(result['accepted_point_indices'],[0,2,1])
        last=result['attempts'][-1]
        self.assertEqual(last['correspondence']['status'],'PASS');self.assertEqual(last['decision'],'STOP')
        self.assertEqual(last['identity_recovery']['status'],'UNVERIFIED')
        self.assertEqual(result['history']['current_mode_ids'],['TM010','TM020','TM011'])
        self.assertEqual(result['unreached_target_indices'],[2,3,4,5]);self.assertFalse(result['can_resume'])
        self.assertEqual(read_adaptive_study(self.root/'failed/adaptive-study-results.json'),result)
        self.assertFalse((self.root/'failed/point-005').exists())
        with self.assertRaisesRegex(ValueError,'PAUSED'):execute_adaptive_study(self.request,self.root/'invalid',checkpoint=result)
        self.assertFalse((self.root/'invalid').exists())

    def test_every_recovery_plan_is_checked_before_output(self):
        mutations=[lambda r:r.update(identity_recoveries=[]),lambda r:r['identity_recoveries'][1].update(target_index=True),
            lambda r:r['identity_recoveries'][1].update(target_index=3),lambda r:r['identity_recoveries'][1].update(anchor_target_index=5),
            lambda r:r['identity_recoveries'][1].update(anchor_snapshot_index=1),
            lambda r:r['identity_recoveries'][1]['controls'].update(cluster_transition_policy='retain_subspace',minimum_cluster_link=.2),
            lambda r:r.update(schema_version=1)]
        for mutate in mutations:
            request=deepcopy(self.request);mutate(request)
            with self.assertRaises(ValueError):execute_adaptive_study(request,self.root/'invalid',max_new_attempts=1)
            self.assertFalse((self.root/'invalid').exists())

    def test_binding_event_and_resume_plan_tampering_are_rejected(self):
        saved=execute_adaptive_study(self.request,self.root/'saved',max_new_attempts=5)
        for kind in ['binding','event','accepted','version']:
            changed=deepcopy(saved)
            if kind=='binding':changed['attempts'][-1]['identity_recovery']['anchor_snapshot_index']=1
            elif kind=='event':changed['attempts'][-1]['identity_recovery']['event']['assessment']['current_mode_ids'][1]='forged'
            elif kind=='accepted':changed['accepted_point_indices'][1:3]=[1,2]
            else:changed['schema_version']=2
            with self.assertRaises(ValueError):replay_adaptive_study(changed)
        request=deepcopy(self.request);request['identity_recoveries'][1]['controls']['minimum_overlap']=.97
        with self.assertRaisesRegex(ValueError,'request differs'):execute_adaptive_study(request,self.root/'invalid',checkpoint=saved)
        self.assertFalse((self.root/'invalid').exists())

    def test_decreasing_targets_recover_the_same_analytical_branches(self):
        request=deepcopy(self.request);request['study']['values']=[.075,self.request['study']['values'][2],.055,.04]
        request['initial_ids']=['TM010','TM011','TM020'];request['step_controls']=[dict(self.request['step_controls'][1]) for _ in range(3)]
        request['identity_recoveries']=[dict(target_index=2,anchor_target_index=0,controls=self.controls)]
        result=execute_adaptive_study(request,self.root/'reverse')
        self.assertEqual(result['status'],'COMPLETE');self.assertEqual(result['history']['current_mode_ids'],['TM010','TM020','TM011'])
        self.assertEqual(result['reached_target_indices'],[0,1,2,3])

    def test_later_solve_failure_preserves_recovery_checkpoint(self):
        saved=execute_adaptive_study(self.request,self.root/'first',max_new_attempts=5)
        with patch('superfish_ng.adaptive_study.execute_project',side_effect=RuntimeError('injected later solve failure')):
            with self.assertRaisesRegex(RuntimeError,'injected'):execute_adaptive_study(self.request,self.root/'failed',checkpoint=saved)
        self.assertEqual(read_adaptive_study(self.root/'first/checkpoint-005.json'),saved)
        self.assertFalse((self.root/'failed/adaptive-study-results.json').exists())

    def test_worker_restart_and_gui_transport_preserve_recovery(self):
        from superfish_ng.gui_tracked_study import tracked_study_response
        manager=JobManager(self.root/'jobs');self.addCleanup(manager.close)
        def wait(identifier):
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                state=manager.status(identifier)
                if state['status'] not in ('queued','running'):
                    self.assertEqual(state['status'],'complete',state)
                    return tracked_study_response(manager,'adaptive-study-result',dict(id=identifier))
                time.sleep(.025)
            self.fail('adaptive recovery worker did not finish')
        identifier=tracked_study_response(manager,'start-adaptive-study',dict(request=json.dumps(self.request),max_new_attempts=5))['id']
        first=wait(identifier);self.assertTrue(first['document']['history']['individual_ids_complete'])
        manager.close();manager=JobManager(self.root/'jobs');self.addCleanup(manager.close)
        identifier=tracked_study_response(manager,'resume-adaptive-study',dict(document=first['serialized']))['id']
        final=wait(identifier)
        self.assertEqual(final['document']['status'],'COMPLETE');self.assertEqual(len(final['document']['history']['identity_recoveries']),2)

    def test_cli_pause_at_recovery_resume_and_replay(self):
        from superfish_ng.cli import main
        request=self.root/'request.json';request.write_text(json.dumps(self.request))
        self.assertEqual(main(['execute-adaptive-study',str(request),'--out',str(self.root/'cli'),'--max-new-attempts','5']),0)
        checkpoint=self.root/'cli/checkpoint-005.json'
        self.assertEqual(main(['resume-adaptive-study',str(checkpoint),'--out',str(self.root/'continued')]),0)
        self.assertEqual(main(['replay-adaptive-study',str(self.root/'continued/adaptive-study-results.json')]),0)

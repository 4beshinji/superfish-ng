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
from superfish_ng.completion import digest
from superfish_ng.jobs import execute_project,JobManager
from superfish_ng.tracked_study import execute_tracked_study,read_tracked_study,replay_tracked_study


class TrackedStudyIdentityRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        zeros=jn_zeros(0,2);crossing=float(np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2))
        case=Case(((0.,.1),(.055,.1)),nr=8,nz=8,modes=3,element_order=2)
        study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/0',[.055,crossing,.075,.056,crossing,.08])
        self.controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,
            minimum_assignment_margin=.05,relative_cluster_gap=.001,minimum_relative_singular_value=1e-8)
        self.request=dict(schema_version=2,study=study.to_dict(),initial_ids=['TM010','TM020','TM011'],
            step_controls=[dict(self.controls,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2) for _ in range(5)],
            identity_recoveries=[dict(point_index=2,anchor_snapshot_index=0,controls=deepcopy(self.controls)),
                                 dict(point_index=5,anchor_snapshot_index=2,controls=deepcopy(self.controls))])

    def test_resume_recovers_analytic_mode_identity_without_recomputing_prior_points(self):
        first=execute_tracked_study(self.request,self.root/'first',max_new_points=2)
        self.assertEqual(first['history']['current_mode_ids'],['TM010',None,None])
        hashes={str(p):digest(p) for p in (self.root/'first').rglob('*') if p.is_file()}
        with patch('superfish_ng.tracked_study.execute_project',wraps=execute_project) as solve:
            recovered=execute_tracked_study(self.request,self.root/'recovered',max_new_points=1,checkpoint=first)
        self.assertEqual(solve.call_count,1);self.assertEqual(recovered['status'],'PAUSED')
        self.assertEqual(recovered['schema_version'],2)
        self.assertEqual(recovered['history']['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual(recovered['point_results'][2]['identity_recovery_status'],'PASS')
        last=execute_tracked_study(self.request,self.root/'last',checkpoint=recovered)
        self.assertEqual(last['status'],'COMPLETE')
        self.assertEqual(last['point_results'][3]['current_mode_ids'],['TM010','TM020','TM011'])
        self.assertEqual([e['after_step_index'] for e in last['history']['identity_recoveries']],[1,4])
        with patch('superfish_ng.jobs.solve',side_effect=AssertionError('replay must not solve')):
            self.assertEqual(replay_tracked_study(last),last)
        for path,value in hashes.items():self.assertEqual(digest(path),value)

    def test_unverified_recovery_stops_before_computing_another_point(self):
        self.request['identity_recoveries'][0]['point_index']=1
        with patch('superfish_ng.tracked_study.execute_project',wraps=execute_project) as solve:
            result=execute_tracked_study(self.request,self.root/'stop')
        self.assertEqual(solve.call_count,2);self.assertEqual(result['status'],'UNVERIFIED')
        self.assertEqual(result['history']['steps'][0]['status'],'PASS')
        self.assertEqual(result['point_results'][1]['identity_recovery_status'],'UNVERIFIED')
        self.assertEqual(result['point_results'][2]['status'],'NOT_COMPUTED')
        self.assertFalse((self.root/'stop/point-003').exists())
        self.assertEqual(read_tracked_study(self.root/'stop/checkpoint-002.json'),result)
        with self.assertRaisesRegex(ValueError,'PAUSED'):execute_tracked_study(self.request,self.root/'invalid',checkpoint=result)
        self.assertFalse((self.root/'invalid').exists())

    def test_all_recovery_controls_preflight_before_any_output(self):
        mutations=[lambda r:r.update(identity_recoveries=[]),lambda r:r['identity_recoveries'][1].update(point_index=True),
            lambda r:r['identity_recoveries'][1].update(anchor_snapshot_index=5),lambda r:r['identity_recoveries'][1].update(extra=True),
            lambda r:r['identity_recoveries'][1]['controls'].update(cluster_transition_policy='retain_subspace',minimum_cluster_link=.2),
            lambda r:r['identity_recoveries'][1]['controls'].update(unsupported=True)]
        for mutate in mutations:
            request=deepcopy(self.request);mutate(request)
            with self.assertRaises(ValueError):execute_tracked_study(request,self.root/'invalid',max_new_points=1)
            self.assertFalse((self.root/'invalid').exists())

    def test_modified_recovery_or_resume_request_cannot_replace_a_checkpoint(self):
        saved=execute_tracked_study(self.request,self.root/'first',max_new_points=3)
        for kind in ['event','row','request']:
            changed=deepcopy(saved)
            if kind=='event':changed['history']['identity_recoveries'][0]['assessment']['current_mode_ids'][1]='forged'
            elif kind=='row':changed['point_results'][2]['identity_recovery_status']='UNVERIFIED'
            else:changed['request']['identity_recoveries'][0]['anchor_snapshot_index']=1
            with self.assertRaises(ValueError):replay_tracked_study(changed)
        request=deepcopy(self.request);request['identity_recoveries'][1]['controls']['minimum_overlap']=.97
        with self.assertRaisesRegex(ValueError,'request differs'):execute_tracked_study(request,self.root/'invalid',checkpoint=saved)
        self.assertFalse((self.root/'invalid').exists())

    def test_solve_failure_after_recovery_keeps_the_last_replayable_checkpoint(self):
        saved=execute_tracked_study(self.request,self.root/'first',max_new_points=3)
        with patch('superfish_ng.tracked_study.execute_project',side_effect=RuntimeError('injected later solve failure')):
            with self.assertRaisesRegex(RuntimeError,'injected'):execute_tracked_study(self.request,self.root/'failed',checkpoint=saved)
        self.assertEqual(read_tracked_study(self.root/'first/checkpoint-003.json'),saved)
        self.assertFalse((self.root/'failed/checkpoint-004.json').exists())

    def test_gui_raw_json_preflight_and_worker_resume_after_manager_restart(self):
        from superfish_ng.gui_tracked_study import tracked_study_response
        manager=JobManager(self.root/'jobs');self.addCleanup(manager.close)
        with self.assertRaisesRegex(ValueError,'duplicate JSON key'):
            tracked_study_response(manager,'start-tracked-study',dict(request='{"schema_version":2,"schema_version":2}'))
        self.assertEqual(manager.list(),[])
        def wait(identifier):
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                state=manager.status(identifier)
                if state['status'] not in ('queued','running'):
                    self.assertEqual(state['status'],'complete',state)
                    return tracked_study_response(manager,'tracked-study-result',dict(id=identifier))
                time.sleep(.025)
            self.fail('worker did not finish')
        identifier=tracked_study_response(manager,'start-tracked-study',dict(request=json.dumps(self.request),max_new_points=3))['id']
        first=wait(identifier);self.assertTrue(first['document']['history']['individual_ids_complete'])
        manager.close();manager=JobManager(self.root/'jobs');self.addCleanup(manager.close)
        identifier=tracked_study_response(manager,'resume-tracked-study',dict(document=first['serialized']))['id']
        final=wait(identifier)
        self.assertEqual(final['document']['status'],'COMPLETE')
        self.assertEqual(len(final['document']['history']['identity_recoveries']),2)

    def test_cli_pause_at_recovery_and_resume_preserve_the_plan(self):
        from superfish_ng.cli import main
        request=self.root/'request.json';request.write_text(json.dumps(self.request))
        self.assertEqual(main(['execute-tracked-study',str(request),'--out',str(self.root/'cli'),'--max-new-points','3']),0)
        checkpoint=self.root/'cli/checkpoint-003.json'
        self.assertEqual(main(['resume-tracked-study',str(checkpoint),'--out',str(self.root/'continued')]),0)
        last=self.root/'continued/checkpoint-006.json'
        self.assertEqual(main(['replay-tracked-study',str(last)]),0)
        self.assertEqual(read_tracked_study(last)['request'],self.request)

# SPDX-License-Identifier: Apache-2.0
"""A root evaluation needs resolved IDs even after verified subspace matching."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from superfish_ng.tuning import execute_tune,replay_tune,read_tune
from superfish_ng.jobs import execute_project
from test_tuning import request as base_request


def recovery_request():
    base=base_request();controls=deepcopy(base['controls'])
    base['controls'].update(relative_cluster_gap=.2,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)
    return dict(schema_version=6,tune_request=base,identity_recovery=dict(anchor_selection='fixed_trial',anchor_trial_index=0,controls=controls))


class TuningIdentityRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)

    def test_recovered_ids_drive_root_updates_and_refinement_after_restart(self):
        request=recovery_request();first=execute_tune(request,self.root/'first',max_new_trials=2)
        self.assertEqual(first['schema_version'],2);self.assertEqual(first['status'],'PAUSED')
        second=first['trials'][1];self.assertFalse(second['tracking']['tracking']['individual_ids_complete'])
        self.assertEqual(second['identity_recovery']['status'],'PASS');self.assertEqual(second['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual(second['identity_recovery']['comparison']['request']['previous_run'],str(Path(first['trial_runs'][0])/'solution'))
        with patch('superfish_ng.tuning.execute_project',wraps=execute_project) as solver:
            final=execute_tune(request,self.root/'next',checkpoint=read_tune(self.root/'first/checkpoint-002.json'))
        self.assertEqual(solver.call_count,2);self.assertEqual(final['status'],'TUNED')
        self.assertEqual([t['value'] for t in final['trials']],[.06,.1,.08,.08])
        self.assertEqual(final['trials'][-1]['parent_index'],2)
        self.assertEqual(final['trials'][-1]['identity_recovery']['anchor_trial_index'],0)
        self.assertEqual(final['trial_sources_sha256'][:2],first['trial_sources_sha256'])
        with patch('superfish_ng.jobs.solve',side_effect=AssertionError('replay must not solve')):
            self.assertEqual(replay_tune(final),final)
        self.assertEqual(read_tune(self.root/'first/checkpoint-002.json'),first)

    def test_failed_recovery_never_becomes_a_frequency_evaluation(self):
        request=recovery_request();request['identity_recovery']['controls']['relative_cluster_gap']=.2
        result=execute_tune(request,self.root/'stopped')
        self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(len(result['trials']),2)
        last=result['trials'][-1]
        self.assertEqual(last['tracking']['status'],'PASS');self.assertEqual(last['identity_recovery']['status'],'UNVERIFIED')
        self.assertIsNone(last['frequency_hz']);self.assertIsNone(last['target_error_hz'])
        self.assertFalse(result['can_resume']);self.assertFalse((self.root/'stopped/trial-003').exists())
        self.assertEqual(read_tune(self.root/'stopped/checkpoint-002.json'),result)
        with self.assertRaisesRegex(ValueError,'PAUSED'):execute_tune(request,self.root/'invalid',checkpoint=result)

    def test_latest_recovered_anchor_is_not_the_selected_refinement_parent(self):
        from superfish_ng.analytic import tm0np_frequency
        request=recovery_request();base=request['tune_request'];base['target_hz']=tm0np_frequency(.1,.06,1,1)
        request['identity_recovery']=dict(anchor_selection='latest_resolved_trial',controls=request['identity_recovery']['controls'])
        result=execute_tune(request,self.root/'latest')
        self.assertEqual(result['status'],'TUNED');self.assertEqual(len(result['trials']),3)
        last=result['trials'][-1];self.assertEqual(last['parent_index'],0)
        self.assertEqual(last['identity_recovery']['anchor_trial_index'],1)
        self.assertEqual(last['current_mode_ids'],['TM010','TM020','TM011'])
        self.assertEqual(last['identity_recovery']['comparison']['request']['previous_ids'],['TM010','TM011','TM020'])
        self.assertEqual(read_tune(self.root/'latest/checkpoint-003.json'),result)

    def test_recovery_neither_replaces_failed_correspondence_nor_relabels_resolved_ids(self):
        for name,controls,expected in [('resolved',base_request()['controls'],'TUNED'),
                ('unverified',dict(base_request()['controls'],minimum_overlap=1.),'UNVERIFIED')]:
            request=recovery_request();request['tune_request']['controls']=controls
            with patch('superfish_ng.tuning.recover_trial',side_effect=AssertionError('recovery must not run')):
                result=execute_tune(request,self.root/name)
            self.assertEqual(result['status'],expected)
            self.assertTrue(all(t['identity_recovery'] is None for t in result['trials']))

    def test_strict_wrapper_policy_and_unavailable_anchor(self):
        from superfish_ng.tuning import _request
        mutations=[lambda r:r.update(schema_version=True),lambda r:r.update(extra=1),
            lambda r:r['identity_recovery'].update(anchor_trial_index=True),
            lambda r:r['identity_recovery'].update(anchor_trial_index=16),
            lambda r:r['identity_recovery'].update(anchor_selection='automatic'),
            lambda r:r['identity_recovery'].update(anchor_selection='latest_resolved_trial'),
            lambda r:r['identity_recovery']['controls'].update(cluster_transition_policy='retain_subspace',minimum_cluster_link=.2),
            lambda r:r.update(tune_request=recovery_request())]
        for mutate in mutations:
            r=recovery_request();mutate(r)
            with self.assertRaises(ValueError):_request(r)
        request=recovery_request();request['identity_recovery']['anchor_trial_index']=1
        first=execute_tune(request,self.root/'first',max_new_trials=1)
        with self.assertRaisesRegex(ValueError,'earlier trial'):execute_tune(request,self.root/'failed',checkpoint=first)
        self.assertEqual(read_tune(self.root/'first/checkpoint-001.json'),first)
        self.assertTrue((self.root/'failed/failure-002.json').exists())

    def test_recovery_binding_assessment_version_and_resume_changes_are_rejected(self):
        request=recovery_request();first=execute_tune(request,self.root/'first',max_new_trials=2)
        for target in ['anchor','assessment','comparison','version']:
            changed=deepcopy(first)
            if target=='anchor':changed['trials'][1]['identity_recovery']['anchor_trial_index']=1
            elif target=='assessment':changed['trials'][1]['identity_recovery']['assessment']['group_checks'][0]['consistent']=False
            elif target=='comparison':changed['trials'][1]['identity_recovery']['comparison']['request']['controls']['minimum_overlap']=.9
            else:changed['schema_version']=1
            with self.assertRaises(ValueError):replay_tune(changed)
        request['identity_recovery']['controls']['minimum_overlap']=.9
        with self.assertRaisesRegex(ValueError,'request differs'):execute_tune(request,self.root/'invalid',checkpoint=first)
        self.assertFalse((self.root/'invalid').exists())

    def test_later_failure_preserves_recovered_checkpoint(self):
        request=recovery_request();first=execute_tune(request,self.root/'first',max_new_trials=2)
        with patch('superfish_ng.tuning.execute_project',side_effect=RuntimeError('injected later failure')):
            with self.assertRaisesRegex(RuntimeError,'injected'):execute_tune(request,self.root/'failed',checkpoint=first)
        self.assertEqual(read_tune(self.root/'first/checkpoint-002.json'),first)
        self.assertTrue((self.root/'failed/failure-003.json').exists())
        self.assertFalse((self.root/'failed/checkpoint-003.json').exists())

    def test_cli_and_recreated_worker_gui_transport_use_saved_policy(self):
        from superfish_ng.cli import main
        from superfish_ng.jobs import JobManager
        from superfish_ng.gui_tuning import tuning_response
        request=recovery_request();path=self.root/'request.json';path.write_text(json.dumps(request))
        self.assertEqual(main(['tune',str(path),'--out',str(self.root/'cli'),'--max-new-trials','2']),0)
        first=read_tune(self.root/'cli/checkpoint-002.json')
        manager=JobManager(self.root/'jobs');manager.close();manager=JobManager(self.root/'jobs');self.addCleanup(manager.close)
        identifier=tuning_response(manager,'resume-tune',dict(document=json.dumps(first),max_new_trials=1))['id']
        def finish(identifier):
            while True:
                status=manager.status(identifier)
                if status['status'] not in ('queued','running'):
                    self.assertEqual(status['status'],'complete',status);manager.status(identifier,verify=True)
                    return tuning_response(manager,'tune-result',dict(id=identifier))
                time.sleep(.025)
        middle=finish(identifier);manager.close();manager=JobManager(self.root/'jobs');self.addCleanup(manager.close)
        identifier=tuning_response(manager,'resume-tune',dict(document=middle['serialized']))['id'];last=finish(identifier)
        self.assertEqual(last['document']['status'],'TUNED')
        self.assertEqual(last['document']['request'],request)
        self.assertEqual(main(['replay-tune',str(manager.directory(identifier)/'tune-results.json')]),0)

    def test_harmonic_recovery_uses_actual_earlier_trial_mesh_and_fixed_history(self):
        from test_curved_harmonic_tuning import harmonic_request
        from test_curved_harmonic_deformation import space
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        from superfish_ng import solve
        from superfish_ng.tuning import _project
        base=harmonic_request();base['project']['case']['solver']['modes']=3;base['initial_ids']=['A','B','C']
        controls=deepcopy(base['controls']);base['controls'].update(relative_cluster_gap=.99,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)
        initial=_project(base,0.,'search');base['target_hz']=float(solve(initial.case,mesh_data=initial.mesh_data).frequencies_hz[0])
        request=dict(schema_version=6,tune_request=base,identity_recovery=dict(anchor_selection='latest_resolved_trial',controls=controls))
        result=execute_tune(request,self.root/'harmonic');self.assertEqual(result['status'],'TUNED')
        last=result['trials'][-1];self.assertEqual(last['parent_index'],0);self.assertEqual(last['identity_recovery']['anchor_trial_index'],1)
        ordinary=last['tracking']['request']['controls']['comparison_meshes'];recovery=last['identity_recovery']['comparison']['request']['controls']['comparison_meshes']
        self.assertEqual(ordinary[0],ordinary[1]);self.assertNotEqual(recovery[0],ordinary[0]);self.assertEqual(recovery[1],ordinary[1])
        self.assertEqual(recovery[0]['source_mesh'],_project(base,1.,'search').mesh_data)
        self.assertEqual(recovery[0]['curved_refinement_steps'],base['project']['case']['mesh']['curved_refinement_steps'])
        before=boundary_moments(space(initial));after=boundary_moments(space(_project(base,0.,'refinement')))
        for key in ['signed_area_m2','signed_volume_m3']:self.assertAlmostEqual(before[key],after[key],places=14)
        self.assertEqual(replay_tune(result),result)

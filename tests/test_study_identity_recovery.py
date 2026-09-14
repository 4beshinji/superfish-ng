# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scipy.special import jn_zeros
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study,execute_study
from superfish_ng.completion import digest
from superfish_ng.study_mode_tracking import build_study_mode_tracking,save_study_mode_tracking,read_study_mode_tracking,replay_study_mode_tracking


class StudyIdentityRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name)
        zeros=jn_zeros(0,2);length=float(np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2))
        case=Case(((0.,.1),(.055,.1)),nr=8,nz=8,modes=3,element_order=2)
        study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/0',[.055,length,.075,.056,length,.08])
        execute_study(study,cls.root/'study')
        cls.controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,
            minimum_assignment_margin=.05,relative_cluster_gap=.001,minimum_relative_singular_value=1e-8)

    def request(self):
        return dict(schema_version=2,study_run='study',initial_ids=['TM010','TM020','TM011'],
            step_controls=[dict(self.controls,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2) for _ in range(5)],
            identity_recoveries=[dict(point_index=2,anchor_snapshot_index=0,controls=deepcopy(self.controls)),
                                 dict(point_index=5,anchor_snapshot_index=2,controls=deepcopy(self.controls))])

    def test_analytic_crossing_recovers_ids_at_declared_points_and_propagates(self):
        before={str(p):digest(p) for p in (self.root/'study').rglob('*') if p.is_file()}
        with patch('superfish_ng.jobs.solve',side_effect=AssertionError('saved Study must not solve again')):
            result=build_study_mode_tracking(self.request(),base_directory=self.root)
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['history']['schema_version'],3)
        self.assertEqual(result['visited_point_indices'],list(range(6)))
        rows=result['point_results']
        self.assertEqual(rows[1]['current_mode_ids'],['TM010',None,None])
        self.assertEqual(rows[2]['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual(rows[3]['current_mode_ids'],['TM010','TM020','TM011'])
        self.assertEqual(rows[4]['current_mode_ids'],['TM010',None,None])
        self.assertEqual(rows[5]['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual([x['after_step_index'] for x in result['history']['identity_recoveries']],[1,4])
        self.assertIsNone(result['history']['steps'][1]['tracking']['current_mode_ids'][1])
        self.assertEqual(rows[2]['identity_recovery_status'],'PASS')
        for path,value in before.items():self.assertEqual(digest(path),value)

    def test_degenerate_recovery_stops_without_skipping_and_retains_pair(self):
        request=self.request();request['identity_recoveries'][0]['point_index']=1
        result=build_study_mode_tracking(request,base_directory=self.root)
        self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(result['visited_point_indices'],[0,1])
        self.assertEqual(result['unvisited_point_indices'],[2,3,4,5])
        self.assertEqual(result['point_results'][1]['status'],'UNVERIFIED')
        self.assertEqual(result['point_results'][1]['current_mode_ids'],['TM010',None,None])
        self.assertEqual(result['point_results'][5]['status'],'NOT_VISITED')
        self.assertEqual(result['history']['steps'][0]['status'],'PASS')
        self.assertEqual(replay_study_mode_tracking(result),result)

    def test_recovery_plan_is_strict_even_beyond_an_earlier_stop(self):
        changes=[lambda r:r.update(schema_version=True),lambda r:r.update(identity_recoveries=[]),
            lambda r:r['identity_recoveries'][1].update(point_index=True),lambda r:r['identity_recoveries'][1].update(point_index=6),
            lambda r:r['identity_recoveries'][1].update(point_index=2),lambda r:r['identity_recoveries'][1].update(anchor_snapshot_index=5),
            lambda r:r['identity_recoveries'][1].update(extra=True),lambda r:r['identity_recoveries'][1]['controls'].update(sample_order=True),
            lambda r:r['identity_recoveries'][1]['controls'].update(cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)]
        for change in changes:
            request=self.request();request['step_controls'][0]['minimum_overlap']=1.;change(request)
            with self.subTest(change=change):
                with self.assertRaises(ValueError):build_study_mode_tracking(request,base_directory=self.root)

    def test_saved_replay_rejects_modified_event_plan_and_point_summary(self):
        path=self.root/'scheduled-recovery.json';result=save_study_mode_tracking(self.request(),path,base_directory=self.root)
        self.assertEqual(read_study_mode_tracking(path),result)
        with self.assertRaises(FileExistsError):save_study_mode_tracking(self.request(),path,base_directory=self.root)
        for kind in ['summary','event','plan']:
            bad=deepcopy(result)
            if kind=='summary':bad['point_results'][2]['current_mode_ids'][1]='forged'
            elif kind=='event':bad['history']['identity_recoveries'][0]['assessment']['status']='UNVERIFIED'
            else:bad['request']['identity_recoveries'][0]['anchor_snapshot_index']=1
            with self.assertRaises(ValueError):replay_study_mode_tracking(bad)

    def test_anchor_controls_are_derived_from_actual_nonadjacent_values(self):
        from superfish_ng.study_shape_tracking import pair_controls
        from superfish_ng.studies import Study
        study=Study.from_dict(json.loads((self.root/'study/study.json').read_text()))
        with patch('superfish_ng.study_identity_recovery.pair_controls',wraps=pair_controls) as derived:
            build_study_mode_tracking(self.request(),base_directory=self.root)
        pairs=[call.args[2:4] for call in derived.call_args_list]
        self.assertIn((study.values[0],study.values[2]),pairs)
        self.assertIn((study.values[2],study.values[5]),pairs)

    def test_existing_study_history_can_add_recovery_through_gui(self):
        from superfish_ng.gui_mode_tracking import tracking_response
        request=self.request();request.pop('identity_recoveries');request['schema_version']=1
        original=build_study_mode_tracking(request,base_directory=self.root);copy=deepcopy(original)
        recovery=dict(anchor_snapshot_index=0,controls=self.controls)
        response=tracking_response(None,'recover-study-mode-identities',dict(document=json.dumps(original),request_document=json.dumps(recovery)))
        self.assertEqual(original,copy);result=response['document']
        self.assertEqual(result['schema_version'],2);self.assertTrue(result['history']['individual_ids_complete'])
        self.assertEqual(result['request']['identity_recoveries'][0]['point_index'],5)
        self.assertEqual(replay_study_mode_tracking(result),result)
        with self.assertRaises(ValueError):tracking_response(None,'recover-study-mode-identities',dict(document=json.dumps(original),request_document='{"anchor_snapshot_index":0,"anchor_snapshot_index":0,"controls":{}}'))

    def test_cli_uses_recovery_plan_and_refuses_duplicate_json_keys(self):
        from superfish_ng.cli import main
        path=self.root/'recovery-request.json';path.write_text(json.dumps(self.request()));out=self.root/'cli-recovery.json'
        self.assertEqual(main(['track-study-modes',str(path),'--out',str(out)]),0)
        self.assertEqual(main(['replay-study-mode-tracking',str(out)]),0)
        path.write_text('{"schema_version":2,"schema_version":2}')
        self.assertEqual(main(['track-study-modes',str(path),'--out',str(self.root/'invalid.json')]),2)
        self.assertFalse((self.root/'invalid.json').exists())

    def test_recovery_does_not_certify_an_unresolved_surface_refinement_step(self):
        from superfish_ng.gui_surface_convergence import surface_convergence_response
        from superfish_ng.surface_convergence import _target_match
        result=build_study_mode_tracking(self.request(),base_directory=self.root)
        self.assertTrue(result['history']['individual_ids_complete'])
        with self.assertRaisesRegex(ValueError,'fixed quadratic geometry'):
            surface_convergence_response('assess-surface-convergence',dict(document=json.dumps(result),mode_id='TM011'))
        with self.assertRaisesRegex(ValueError,'individual correspondence at every refinement step'):
            _target_match(result['history']['steps'][0],'TM011')

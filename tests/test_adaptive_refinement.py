# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.analytic import pillbox_spectrum
from superfish_ng.adaptive_refinement import execute_adaptive_refinement,replay_adaptive_refinement,read_adaptive_refinement


def request(order=2):
    case=Case(((0.,.1),(.2,.1)),nr=4,nz=5,modes=2,element_order=order)
    return dict(schema_version=1,case=case.to_dict(),initial_mesh=None,initial_ids=['fundamental','second'],mode_id='fundamental',
        controls=dict(mapping='same_domain',sample_order=3,minimum_overlap=.95,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8),bulk_fraction=.5,max_levels=4,
        max_triangles=5000,minimum_angle_deg=5.,relative_tolerances=dict(frequency_hz=.01,r_over_q_accelerator_ohm=.1,geometry_factor_ohm=.1))


class AdaptiveRefinementTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)

    def test_native_tracking_two_changes_and_analytic_ritz_improvement(self):
        for order in (1,2):
            req=request(order);result=execute_adaptive_refinement(req,self.root/f'p{order}')
            self.assertEqual(result['status'],'TARGETS_MET');self.assertEqual(len(result['levels']),3)
            exact=pillbox_spectrum(.1,.2,1)[0][0]
            errors=[row['quantities']['frequency_hz']/exact-1 for row in result['levels']]
            self.assertTrue(all(0<b<a for a,b in zip(errors,errors[1:])))
            self.assertTrue(all(row['current_mode_ids'][row['mode_index']]=='fundamental' for row in result['levels']))
            self.assertIsNone(result['physical_error_bound']);self.assertEqual(result['surface_status'],'UNASSESSED')
            with patch('superfish_ng.adaptive_refinement.solve',side_effect=AssertionError('no solve on replay')):
                self.assertEqual(replay_adaptive_refinement(result),result)

    def test_resume_replays_mesh_selection_sources_and_failure(self):
        req=request();first=execute_adaptive_refinement(req,self.root/'first',max_new_levels=1)
        self.assertEqual(first['status'],'PAUSED')
        with patch('superfish_ng.adaptive_refinement.solve',side_effect=RuntimeError('injected')):
            with self.assertRaisesRegex(RuntimeError,'injected'):execute_adaptive_refinement(req,self.root/'failed',checkpoint=first)
        self.assertTrue((self.root/'failed/failure-002.json').exists())
        with patch('superfish_ng.adaptive_refinement.solve',wraps=solve) as calls:
            result=execute_adaptive_refinement(req,self.root/'resume',checkpoint=first)
            self.assertEqual(calls.call_count,2)
        self.assertEqual(result['status'],'TARGETS_MET');self.assertEqual(result['sources'][:1],first['sources'])
        self.assertEqual(read_adaptive_refinement(self.root/'first/checkpoint-001.json'),first)
        bad=deepcopy(result);bad['levels'][1]['marked_cells']=[0]
        with self.assertRaises(ValueError):replay_adaptive_refinement(bad)
        source=Path(first['level_runs'][0])/'case.json';source.write_text(source.read_text()+' ')
        with self.assertRaises(ValueError):replay_adaptive_refinement(first)

    def test_limits_and_unresolved_tracking_are_terminal(self):
        large=request();large['case']['mesh'].update(nr=6,nz=8);large['controls']['sample_order']=32
        self.assertEqual(execute_adaptive_refinement(large,self.root/'tracking-budget')['status'],'TRACKING_BUDGET')
        for name,modify,expected in (
            ('level',dict(max_levels=3,relative_tolerances=dict.fromkeys(request()['relative_tolerances'],1e-14)),'LEVEL_LIMIT'),
            ('mesh',dict(max_triangles=40),'REFINEMENT_LIMIT'),
            ('identity',dict(controls=dict(request()['controls'],relative_cluster_gap=.9)),'UNVERIFIED')):
            req=dict(request(),**modify);result=execute_adaptive_refinement(req,self.root/name)
            self.assertEqual(result['status'],expected);self.assertFalse(result['can_resume'])
            with self.assertRaises(ValueError):execute_adaptive_refinement(req,self.root/'invalid',checkpoint=result)

    def test_symmetry_conditions_and_strict_request(self):
        for tag in ('electric_symmetry','magnetic_symmetry'):
            req=request();case=Case.from_dict(req['case']);from dataclasses import replace
            req['case']=replace(case,z_min=tag).to_dict()
            result=execute_adaptive_refinement(req,self.root/tag,max_new_levels=2)
            self.assertEqual(result['levels'][-1]['status'],'PASS')
        for modify in (dict(extra=1),dict(max_levels=True),dict(bulk_fraction=0),dict(initial_ids=['x','x']),dict(mode_id='missing'),
                       dict(relative_tolerances={'frequency_hz':.01}),dict(minimum_angle_deg=60)):
            with self.assertRaises(ValueError):execute_adaptive_refinement(dict(request(),**modify),self.root/'bad')
            self.assertFalse((self.root/'bad').exists())

    def test_cli_pause_resume_and_terminal_exit(self):
        import json
        from superfish_ng.cli import main
        path=self.root/'request.json';path.write_text(json.dumps(request()))
        self.assertEqual(main(['adaptive-refine',str(path),'--out',str(self.root/'cli'),'--max-new-levels','1']),0)
        checkpoint=self.root/'cli/checkpoint-001.json'
        self.assertEqual(main(['resume-adaptive-refinement',str(checkpoint),'--out',str(self.root/'cli-resume')]),0)
        self.assertEqual(main(['replay-adaptive-refinement',str(self.root/'cli-resume/checkpoint-003.json')]),0)
        limited=dict(request(),max_triangles=40);path.write_text(json.dumps(limited))
        self.assertEqual(main(['adaptive-refine',str(path),'--out',str(self.root/'limited')]),1)
        self.assertEqual(main(['replay-adaptive-refinement',str(self.root/'limited/checkpoint-001.json')]),1)

    def test_rf_failure_and_first_interval_cannot_be_hidden(self):
        from superfish_ng.adaptive_refinement import _next
        req=request();req['max_levels']=3;req['relative_tolerances']=dict.fromkeys(req['relative_tolerances'],.005)
        case=Case.from_dict(req['case'])
        for values in ((1.,1.02,1.02),(1.,1.,1.02),(0.,0.,0.),(1e-300,1e300,1e300)):
            levels=[dict(status='PASS',quantities=dict(frequency_hz=1.,geometry_factor_ohm=1.,r_over_q_accelerator_ohm=v)) for v in values]
            decision,_=_next(case,req,levels,None)
            self.assertIn(decision['status'],('LEVEL_LIMIT','QUANTITY_UNVERIFIED'))

    def test_saved_reconstruction_rechecks_field_and_rf_invariants(self):
        from superfish_ng.io import save_run
        from superfish_ng.affine_saved import read_verified_affine_solution
        from superfish_ng.saved import read_solution
        from superfish_ng.residual_indicator import residual_indicator
        for order in (1,2):
            case=Case.from_dict(request(order)['case']);solution=solve(case);directory=self.root/f'saved-{order}'
            save_run(case,solution,directory);loaded=read_verified_affine_solution(directory)
            np.testing.assert_allclose(residual_indicator(case,loaded)['cell_relative_squared'],residual_indicator(case,solution)['cell_relative_squared'],rtol=1e-10,atol=1e-15)
            for kind in ('normalization','frequency','rf'):
                changed=read_solution(directory)
                if kind=='normalization':changed.u*=2
                elif kind=='frequency':changed.frequencies_hz*=1.01
                else:changed.results['modes'][0]['r_over_q_accelerator_ohm']*=1.01
                with patch('superfish_ng.affine_saved.read_solution',return_value=changed):
                    with self.assertRaises(ValueError):read_verified_affine_solution(directory)

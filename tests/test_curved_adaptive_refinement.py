# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from superfish_ng import Case,solve
from superfish_ng.conics import LineSegment,EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.adaptive_refinement import execute_adaptive_refinement,replay_adaptive_refinement
from superfish_ng.curved_adaptive_refinement import next_plan,validate_request

PEAKS=('epk_over_eacc','bpk_over_eacc_mt_per_mv_per_m')


def request(scale=1.,modes=1):
    radius=.08*scale
    case=Case((),name='synthetic_sphere_adaptive',curved_contour=CurvedContour(
        (LineSegment((0,0),(2*radius,0)),EllipseArc((radius,0),(radius,radius),0,math.pi)),('axis','pec'),1e-14*scale),
        curve_chord_tolerance_m=.0016*scale,contour_mesh=ContourMeshControls(.128*scale,min_angle_deg=5.),
        element_order=2,geometry_order=2,quadrature_order=12,modes=modes,normalization_j=scale**2)
    return dict(schema_version=4,case=case.to_dict(),initial_mesh=None,initial_ids=['fundamental']+(['second'] if modes==2 else []),
        mode_id='fundamental',controls=dict(mapping='nested_curved',minimum_overlap=.95,minimum_assignment_margin=.05,
        relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8),bulk_fraction=.5,max_levels=5,max_triangles=10000,
        minimum_corner_angle_deg=5.,relative_tolerances=dict(frequency_hz=.01,r_over_q_accelerator_ohm=.1,geometry_factor_ohm=.1),
        confirmation='uniform_two_steps',surface_relative_tolerances=dict.fromkeys(PEAKS,.05),quadrature_check_order=24,
        quadrature_relative_tolerance=1e-6)


class CurvedAdaptiveRefinementTests(unittest.TestCase):
    def test_five_quantities_uniform_steps_and_quadrature_are_required(self):
        r=request();case=Case.from_dict(r['case'])
        levels=[dict(status='PASS',refinement_kind='uniform_confirmation',quantities=dict.fromkeys(r['relative_tolerances'],1.),
            quadrature_check=dict(passed=True),surface=dict(intervals=dict.fromkeys(PEAKS,[1.,1.]))) for _ in range(5)]
        self.assertEqual(next_plan(case,r,levels,None)[0]['status'],'TARGETS_MET')
        for key in PEAKS:
            bad=deepcopy(levels);bad[-2]['surface']['intervals'][key]=[.9,1.1]
            decision,_=next_plan(case,r,bad,None)
            self.assertEqual(decision['status'],'LEVEL_LIMIT')
            self.assertTrue(all(item['passed'] for row in decision['changes'] for item in row.values()))
        bad=deepcopy(levels);bad[-1]['quadrature_check']['passed']=False
        self.assertEqual(next_plan(case,r,bad,None)[0]['status'],'QUADRATURE_UNVERIFIED')
        bad=deepcopy(levels);bad[-2]['refinement_kind']='residual'
        self.assertEqual(next_plan(case,r,bad,None)[0]['status'],'LEVEL_LIMIT')
        bad=deepcopy(levels);bad[-1]['surface']['intervals'][PEAKS[0]]=None
        self.assertEqual(next_plan(case,r,bad,None)[0]['status'],'QUANTITY_UNVERIFIED')

    def test_strict_geometry_integration_controls_and_initial_budget(self):
        r=request()
        bads=[dict(r,confirmation='none'),
              dict(r,quadrature_check_order=12),dict(r,quadrature_check_order=True),dict(r,quadrature_relative_tolerance=0),
              dict(r,controls=dict(r['controls'],mapping='nested_affine')),dict(r,minimum_corner_angle_deg=60),
              dict(r,surface_relative_tolerances={}),dict(r,minimum_angle_deg=5)]
        for bad in bads:
            with self.assertRaises(ValueError):validate_request(bad)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'bad'
            with self.assertRaisesRegex(ValueError,'max_triangles'):
                execute_adaptive_refinement(dict(r,max_triangles=10),path)
            self.assertFalse(path.exists())

    def test_native_resume_cli_and_tamper_rejection(self):
        r=request(modes=2)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            first=execute_adaptive_refinement(r,root/'first',max_new_levels=4)
            self.assertEqual(first['status'],'PAUSED');self.assertEqual(len(first['levels']),4)
            with patch('superfish_ng.curved_adaptive_refinement.solve',wraps=solve) as calls:
                final=execute_adaptive_refinement(r,root/'last',checkpoint=first)
                self.assertEqual(calls.call_count,1)
            self.assertEqual(final['status'],'TARGETS_MET');self.assertEqual(final['surface_status'],'TARGETS_MET')
            self.assertEqual(final['sources'][:4],first['sources'])
            self.assertTrue(all(row['mode_index']==0 and row['current_mode_ids']==['fundamental','second'] for row in final['levels']))
            self.assertTrue(all(row['quadrature_check']['passed'] for row in final['levels']))
            self.assertEqual([row['refinement_kind'] for row in final['levels'][-2:]],['uniform_confirmation']*2)
            self.assertIsNone(final['physical_error_bound'])
            from superfish_ng.cli import main
            with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('must not solve')):
                self.assertEqual(main(['replay-adaptive-refinement',str(root/'last/checkpoint-005.json')]),0)
            bad=deepcopy(final);bad['levels'][0]['surface']['intervals'][PEAKS[0]][0]*=.5
            with self.assertRaises(ValueError):replay_adaptive_refinement(bad)
            source=Path(final['level_runs'][0])/'case.json';source.write_text(source.read_text()+' ')
            with self.assertRaises(ValueError):replay_adaptive_refinement(final)

    def test_managed_one_level_resume_preserves_native_history(self):
        from superfish_ng.jobs import JobManager
        from superfish_ng.adaptive_refinement import read_adaptive_refinement
        with tempfile.TemporaryDirectory() as temp:
            manager=JobManager(Path(temp))
            try:
                def wait(identifier):
                    deadline=time.monotonic()+180
                    while time.monotonic()<deadline:
                        state=manager.status(identifier)
                        if state['status'] in ('complete','failed','cancelled'):return manager.status(identifier,verify=True)
                        time.sleep(.1)
                    self.fail('curved adaptive worker did not finish')
                first_id=manager.start_adaptive_refinement(request(),max_new_levels=1)
                self.assertEqual(wait(first_id)['status'],'complete')
                first=read_adaptive_refinement(manager.directory(first_id)/'adaptive-refinement-results.json')
                second_id=manager.start_adaptive_refinement(first['request'],checkpoint=first,max_new_levels=1)
                self.assertEqual(wait(second_id)['status'],'complete')
                second=read_adaptive_refinement(manager.directory(second_id)/'adaptive-refinement-results.json')
                self.assertEqual(len(second['levels']),2);self.assertEqual(second['status'],'PAUSED')
                self.assertEqual(second['sources'][:1],first['sources'])
                case=Case.load(Path(second['level_runs'][-1])/'case.json')
                self.assertEqual(len(case.curved_refinement_steps),1)
            finally:manager.close()

    def test_high_order_reuse_matches_fully_validated_indicator(self):
        from superfish_ng.curved_adaptive_refinement import _quadrature
        from superfish_ng.curved_residual_indicator import curved_residual_indicator
        r=request();case=Case.from_dict(r['case']);solution=solve(case)
        low=curved_residual_indicator(case,solution,quadrature_order=case.quadrature_order)
        high=curved_residual_indicator(case,solution,quadrature_order=r['quadrature_check_order'])
        report=_quadrature(solution,r,0,low)
        import numpy as np
        denominator=math.fsum(high['cell_relative_squared'])
        for key in ('volume_relative_squared','interior_relative_squared','boundary_relative_squared'):
            expected=float(np.sum(abs(np.array(low[key])-high[key])))/denominator
            self.assertEqual(report['relative_differences'][key],expected)
        self.assertTrue(report['passed'])

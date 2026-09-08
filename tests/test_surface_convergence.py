# SPDX-License-Identifier: Apache-2.0
"""Peak convergence must retain interval uncertainty and physical corner limits."""
import copy
from dataclasses import replace
import math
from pathlib import Path
import tempfile
import unittest
from fractions import Fraction
from superfish_ng import Case,solve
from superfish_ng.conics import LineSegment,EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history
from superfish_ng.surface_convergence import (assess_surface_convergence,save_surface_convergence,
    read_surface_convergence,_interval_change,_evaluate_rows,_geometry_assessment,_ratio_interval,LIMITS)

CONTROLS=dict(mapping='curved_same_domain',sample_order=3,minimum_overlap=.98,
    minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

class SurfaceConvergenceTests(unittest.TestCase):
    def test_ratio_interval_rounding_contains_exact_binary_input_ratio(self):
        for a,b,c in ((.1,.2,.3),(1e-200,2e-200,1e-100),(1.,2.,3.)):
            lo,hi=_ratio_interval(a,b,c)
            self.assertLessEqual(Fraction(lo),Fraction(a)/Fraction(c))
            self.assertGreaterEqual(Fraction(hi),Fraction(b)/Fraction(c))
        self.assertIsNone(_ratio_interval(1e300,1e301,1e-300))

    def test_equal_upper_estimates_do_not_hide_peak_uncertainty(self):
        self.assertAlmostEqual(_interval_change([9.,10.],[9.,10.]),1/9)
        self.assertAlmostEqual(_interval_change([2.,2.],[3.,3.]),.5)
        self.assertIsNone(_interval_change([0.,1.],[1.,1.]))
        rows=[dict(intervals={k:[1.,1.] for k in LIMITS}) for _ in range(3)]
        self.assertEqual(_evaluate_rows(rows)['status'],'TARGETS_MET')
        rows[1]['intervals']['epk_over_eacc']=[.9,1.]
        report=_evaluate_rows(rows)
        self.assertEqual(report['status'],'NOT_CONVERGED')
        self.assertTrue(report['comparisons'][-1]['gates']['frequency_hz'])
        self.assertFalse(report['comparisons'][-1]['gates']['epk_over_eacc'])

    def test_both_final_changes_and_each_quantity_are_required(self):
        rows=[dict(intervals={k:[1.,1.] for k in LIMITS}) for _ in range(3)]
        for key in LIMITS:
            changed=copy.deepcopy(rows);changed[0]['intervals'][key]=[.8,.8]
            self.assertEqual(_evaluate_rows(changed)['status'],'NOT_CONVERGED')
        rows[-1]['intervals']['epk_over_eacc']=None
        self.assertEqual(_evaluate_rows(rows)['status'],'UNVERIFIED')

    def test_axis_pole_and_reentrant_corner_policy(self):
        sphere=CurvedContour((LineSegment((0,0),(.2,0)),EllipseArc((.1,0),(.1,.1),0,math.pi)),('axis','pec'),1e-14)
        self.assertEqual(_geometry_assessment(sphere)['status'],'SMOOTH_WITHIN_TOLERANCE')
        p=[(0,0),(.2,0),(.1,.1)]
        cone=CurvedContour(tuple(LineSegment(p[i],p[(i+1)%3]) for i in range(3)),('axis','pec','pec'),0.)
        self.assertEqual(_geometry_assessment(cone)['status'],'UNVERIFIED_GEOMETRY')
        p=[(0,0),(.2,0),(.2,.1),(.1,.1),(.1,.05),(0,.05)]
        step=CurvedContour(tuple(LineSegment(p[i],p[(i+1)%6]) for i in range(6)),('axis',*['pec']*5),0.)
        self.assertEqual(_geometry_assessment(step)['status'],'SINGULAR_GEOMETRY')

    def test_native_history_saved_replay_and_tamper_rejection(self):
        raw=Case.load('examples/curved_ellipse.json').to_dict()
        raw['mesh']['geometry_order']=2;raw['mesh']['contour_mesh'].update(max_edge_m=.08,min_angle_deg=5.)
        raw['geometry']['chord_tolerance_m']=.008;case=Case.from_dict(raw)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for level in range(3):
                c=replace(case,curved_refinement_levels=level);save_run(c,solve(c),root/str(level))
            pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(root/'0'),current_run=str(root/'1'),previous_ids=['fundamental'],controls=CONTROLS))
            initial=start_mode_history(pair)
            with self.assertRaisesRegex(ValueError,'three'):assess_surface_convergence(initial,'fundamental')
            history=extend_mode_history(initial,dict(current_run=str(root/'2'),controls=CONTROLS))
            report=save_surface_convergence(history,'fundamental',root/'assessment.json')
            self.assertEqual(read_surface_convergence(root/'assessment.json'),report)
            self.assertEqual([r['refinement_level'] for r in report['rows']],[0,1,2])
            self.assertTrue(all(r['mode_index']==1 for r in report['rows']))
            self.assertFalse(report['geometry_approximation_assessed'])
            self.assertIsNone(report['physical_error_bound'])
            with self.assertRaises(FileExistsError):save_surface_convergence(history,'fundamental',root/'assessment.json')
            with self.assertRaisesRegex(ValueError,'mode_id'):assess_surface_convergence(history,'missing')
            changed=copy.deepcopy(report);changed['limits']['frequency_hz']=1.
            import json
            (root/'tampered.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'differs'):read_surface_convergence(root/'tampered.json')
            reverse=extend_mode_history(initial,dict(current_run=str(root/'0'),controls=CONTROLS))
            with self.assertRaisesRegex(ValueError,'increasing'):assess_surface_convergence(reverse,'fundamental')

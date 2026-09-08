# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import json,math
from pathlib import Path
import unittest
from superfish_ng.conics import LineSegment,EllipseArc,HyperbolaArc
from superfish_ng.meridional_radius import certify_minimum_meridional_radius
from superfish_ng.curved_contour import CurvedContour

ROOT=Path(__file__).resolve().parents[1]
class MeridionalRadiusTests(unittest.TestCase):
    def check(self,curve,radius,**kwargs):return certify_minimum_meridional_radius(curve,minimum_radius_m=radius,**kwargs)

    def test_exact_circle_line_and_no_threshold_snapping(self):
        circle=EllipseArc((0,0),(1,1),0.,math.pi)
        self.assertEqual(self.check(circle,1.)['status'],'PASS')
        failed=self.check(circle,math.nextafter(1.,math.inf))
        self.assertEqual(failed['status'],'FAIL');self.assertIsNotNone(failed['witness'])
        self.assertEqual(self.check(LineSegment((0,0),(3,4)),1e100)['status'],'PASS')

    def test_ellipse_hyperbola_extrema_finite_arc_and_scaling(self):
        for curve in (EllipseArc((0,0),(2,1),0.,math.pi),HyperbolaArc((0,0),(2,1),-.4,.4)):
            self.assertEqual(self.check(curve,.5)['status'],'PASS')
            self.assertEqual(self.check(curve,.6)['status'],'FAIL')
            large=replace(curve,semiaxes_m=(4,2))
            self.assertEqual(self.check(large,1.)['status'],'PASS')
        arc=EllipseArc((0,0),(2,1),1.4,.2)
        self.assertEqual(self.check(arc,3.)['status'],'PASS')
        self.assertEqual(self.check(replace(arc,start_rad=1.6,sweep_rad=-.2),3.)['status'],'PASS')

    def test_uncertain_and_exhausted_bounds_are_not_passes(self):
        arc=EllipseArc((0,0),(2,1),1.4,.2)
        self.assertEqual(self.check(arc,3.8,max_boxes=1)['status'],'UNVERIFIED')
        self.assertEqual(self.check(arc,3.8)['status'],'PASS')
        self.assertEqual(self.check(arc,3.,max_series_terms=1)['status'],'UNVERIFIED')
        for kwargs in ({'max_boxes':True},{'fraction_width':0}):
            with self.assertRaises(ValueError):self.check(arc,1.,**kwargs)
        with self.assertRaises(ValueError):self.check(arc,True)

    def test_contour_rejects_pec_corner_and_preserves_optional_contract(self):
        curves=(LineSegment((0,0),(2,0)),EllipseArc((1,0),(1,1),0.,math.pi))
        old=CurvedContour(curves,('axis','pec'),1e-12)
        self.assertNotIn('minimum_meridional_radius_m',old.to_dict())
        constrained=replace(old,minimum_meridional_radius_m=1.)
        self.assertEqual(CurvedContour.from_dict(constrained.to_dict()),constrained)
        self.assertEqual(constrained.radius_constraint_report()['status'],'PASS')
        vertices=((0,0),(2,0),(2,1),(0,1))
        lines=tuple(LineSegment(a,b) for a,b in zip(vertices,vertices[1:]+vertices[:1]))
        with self.assertRaisesRegex(ValueError,'PEC join'):
            CurvedContour(lines,('axis','pec','pec','pec'),0.,minimum_meridional_radius_m=.1)
        for value in (0,-1,True,float('inf'),None):
            data=old.to_dict();data['minimum_meridional_radius_m']=value
            with self.assertRaises(ValueError):CurvedContour.from_dict(data)

    def test_construction_case_gui_and_fem_preserve_constraint(self):
        from superfish_ng.config import Case
        from superfish_ng.tangent_construction import construct_tangent_case,replay_construction
        from superfish_ng.gui import tangent_document
        from superfish_ng.solver import solve
        from superfish_ng.rf import quantities
        request=json.loads((ROOT/'examples/construction/line_conic_fillet_request.json').read_text())
        plain=Case.from_dict(construct_tangent_case(request,candidate_index=0)['case'])
        request['case_template']['geometry']['minimum_meridional_radius_m']=.019
        result=construct_tangent_case(request,candidate_index=0);case=Case.from_dict(result['case'])
        self.assertEqual(case.curved_contour.minimum_meridional_radius_m,.019)
        self.assertEqual(replay_construction(result),result)
        gui=tangent_document(request,candidate_index=0)
        self.assertEqual(gui['preview']['project']['case']['geometry']['minimum_meridional_radius_m'],.019)
        solution=solve(case)
        self.assertEqual(quantities(plain,solve(plain)),quantities(case,solution))
        import tempfile
        from superfish_ng.io import save_run
        from superfish_ng.saved import read_solution
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'run';save_run(case,solution,directory)
            restored=read_solution(directory)
            self.assertEqual(restored.case.curved_contour.minimum_meridional_radius_m,.019)
            self.assertEqual(quantities(restored.case,restored),quantities(case,solution))
        request['case_template']['geometry']['minimum_meridional_radius_m']=.021
        with self.assertRaisesRegex(ValueError,'meridional'):construct_tangent_case(request,candidate_index=0)

    def test_reflection_rechecks_and_preserves_radius_contract(self):
        curves=(LineSegment((0,0),(1,0)),EllipseArc((0,0),(1,1),0.,math.pi/2),LineSegment((0,1),(0,0)))
        for tag in ('electric_symmetry','magnetic_symmetry'):
            half=CurvedContour(curves,('axis','pec',tag),1e-12,minimum_meridional_radius_m=1.)
            full=half.reflected()
            self.assertEqual(full.minimum_meridional_radius_m,1.)
            self.assertEqual(full.radius_constraint_report()['status'],'PASS')

if __name__=='__main__':unittest.main()

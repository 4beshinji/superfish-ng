# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from fractions import Fraction as F
import math
import unittest
from superfish_ng.conics import LineSegment, EllipseArc, HyperbolaArc
from superfish_ng.line_arc_tangent import line_arc_tangent_candidates, connect_line_arc


class LineArcTangentTests(unittest.TestCase):
    def controls(self, **extra):
        return dict(line_first=True, allow_extension=False, position_tolerance_m=1e-9,
                    angle_tolerance_rad=1e-8, **extra)

    def test_circle_exact_contact_and_fraction(self):
        arc=EllipseArc((0,0),(1,1),0.,math.pi)
        line=LineSegment((2,1),(-2,1))
        result=connect_line_arc(line,arc,**self.controls())
        c=result['selected_candidate']
        self.assertEqual(c['exact_contact_zr_m'],(F(0),F(1)))
        self.assertEqual(c['line_parameter'],F(1,2))
        self.assertEqual(result['curves'][0].start_zr_m,line.start_zr_m)
        self.assertEqual(result['curves'][0].end_zr_m,(0.,1.))
        self.assertEqual(c['connection_direction'],'FORWARD')

    def test_extension_is_explicit_and_does_not_reverse_line(self):
        arc=EllipseArc((0,0),(1,1),0.,math.pi)
        line=LineSegment((2,1),(1,1))
        with self.assertRaises(ValueError):connect_line_arc(line,arc,**self.controls())
        controls=self.controls();controls['allow_extension']=True
        result=connect_line_arc(line,arc,**controls)
        self.assertEqual(result['selected_candidate']['line_parameter'],2)
        self.assertTrue(result['selected_candidate']['line_extended'])
        with self.assertRaises(ValueError):
            connect_line_arc(LineSegment((-2,1),(-1,1)),arc,**controls)

    def test_nontangent_lines_are_not_snapped_and_asymptote_distinguished(self):
        arc=EllipseArc((0,0),(1,1),0.,math.pi)
        for height in (1.+1e-10,.5):
            report=line_arc_tangent_candidates(LineSegment((2,height),(-2,height)),arc,**self.controls())
            self.assertEqual(report['status'],'PASS');self.assertFalse(report['candidates'])
            self.assertEqual(report['contact_status'],'NOT_TANGENT')
        h=HyperbolaArc((0,0),(1,1),-1.,1.)
        report=line_arc_tangent_candidates(LineSegment((1,1),(2,2)),h,**self.controls())
        self.assertEqual(report['contact_status'],'AT_INFINITY')
        self.assertFalse(report['candidates'])

    def test_hyperbola_branch_empty_parts_and_both_orderings(self):
        h=HyperbolaArc((0,0),(1,1),-1.,1.)
        line=LineSegment((1,-2),(1,2))
        first=connect_line_arc(line,h,**self.controls())
        self.assertEqual(first['selected_candidate']['exact_contact_zr_m'],(F(1),F(0)))
        controls=self.controls();controls['line_first']=False
        second=connect_line_arc(line,h,**controls)
        self.assertEqual(second['curves'][1].end_zr_m,(1.,2.))
        with self.assertRaises(ValueError):connect_line_arc(line,replace(h,branch=-1),**controls)
        with self.assertRaises(ValueError):connect_line_arc(line,replace(h,end_parameter=0.),**self.controls())
        with self.assertRaises(ValueError):connect_line_arc(LineSegment((1,0),(1,2)),h,**self.controls())

    def test_reversed_direction_budgets_and_strict_controls(self):
        a=EllipseArc((0,0),(1,1),0.,math.pi);line=LineSegment((-2,1),(2,1))
        report=line_arc_tangent_candidates(line,a,**self.controls())
        self.assertEqual(report['candidates'][0]['connection_direction'],'OPPOSED')
        controls=self.controls(max_series_terms=1)
        report=line_arc_tangent_candidates(line,a,**controls)
        self.assertEqual(report['status'],'UNVERIFIED')
        for key in ('line_first','allow_extension'):
            c=self.controls();c[key]=1
            with self.assertRaises(ValueError):line_arc_tangent_candidates(line,a,**c)

    def test_v3_case_save_replay_and_gui_share_certified_line_contract(self):
        import json
        import tempfile
        from pathlib import Path
        from superfish_ng.tangent_construction import construct_tangent_case,save_construction,read_construction
        from superfish_ng.gui import tangent_document
        from superfish_ng.config import Case
        request=line_arc_request()
        result=construct_tangent_case(request,candidate_index=0)
        self.assertEqual(result['schema_version'],3)
        self.assertEqual(result['enumeration']['arc_filter_status'],'CERTIFIED_FIXED_LINE_CONTACT')
        case=Case.from_dict(result['case'])
        self.assertEqual(len(case.curved_contour.curves),4)
        self.assertAlmostEqual(case.curved_contour.area_m2,.4*.1+math.pi*.1**2/2,places=12)
        self.assertAlmostEqual(case.curved_contour.volume_m3,math.pi*.1**2*.4+4*math.pi*.1**3/3,places=12)
        gui=tangent_document(request,candidate_index=0)
        self.assertEqual(gui['construction'],result)
        self.assertEqual(tangent_document(gui['serialized'],replay=True)['construction'],result)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'result.json'
            save_construction(request,path,candidate_index=0)
            self.assertEqual(read_construction(path),result)
        request['controls']['normal_width']=2.**-44
        with self.assertRaises(ValueError):construct_tangent_case(request)

    def test_v3_fem_scaling(self):
        from copy import deepcopy
        from superfish_ng.tangent_construction import construct_tangent_case
        from superfish_ng.config import Case
        from superfish_ng.solver import solve
        from superfish_ng.rf import quantities
        request=line_arc_request()
        first=Case.from_dict(construct_tangent_case(request,candidate_index=0)['case'])
        large=deepcopy(request);g=large['case_template']['geometry']
        for curve in g['curves']:
            for key in ('start_zr_m','end_zr_m','center_zr_m','semiaxes_m'):
                if key in curve:curve[key]=[2*x for x in curve[key]]
        for key in ('join_tolerance_m','minimum_gap_m','chord_tolerance_m'):g[key]*=2
        large['case_template']['mesh']['contour_mesh']['max_edge_m']*=2
        large['controls']['position_tolerance_m']*=2
        second=Case.from_dict(construct_tangent_case(large,candidate_index=0)['case'])
        a,b=quantities(first,solve(first)),quantities(second,solve(second))
        self.assertAlmostEqual(b['frequency_hz']/a['frequency_hz'],.5,places=10)
        for key in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs'):
            self.assertAlmostEqual(b[key]/a[key],1.,places=9)


def line_arc_request():
    import json
    from pathlib import Path
    from superfish_ng.conics import curve_to_dict
    source=Path(__file__).resolve().parents[1]/'examples/construction/capsule_certified_request.json'
    request=json.loads(source.read_text())
    request['schema_version']=3;request['pair_start']=2
    case=request['case_template'];case['name']='synthetic fixed-line tangent capsule'
    case['geometry']['curves']=[curve_to_dict(c) for c in (
        LineSegment((0,0),(.6,0)),EllipseArc((.5,0),(.1,.1),0.,math.pi/2),
        LineSegment((.5,.1),(0.,.1)),EllipseArc((.1,0),(.1,.1),0.,math.pi))]
    case['geometry']['edge_tags']=['axis','pec','pec','pec']
    for key in ('normal_width','max_boxes','residual_tolerance','max_contact_width_m'):
        request['controls'].pop(key)
    request['controls']['allow_extension']=False
    return request

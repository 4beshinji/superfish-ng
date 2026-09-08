# SPDX-License-Identifier: Apache-2.0
import math
import unittest
import numpy as np
from superfish_ng.conics import LineSegment
from superfish_ng.line_fillet import line_fillet_candidates, connect_line_fillet


class LineFilletTests(unittest.TestCase):
    def controls(self, radius=.25, **extra):
        return dict(radius_m=radius, allow_extension=False, position_tolerance_m=1e-10,
                    angle_tolerance_rad=1e-8, **extra)

    def corner(self):
        return LineSegment((0,0),(1,0)),LineSegment((1,0),(1,1))

    def test_known_right_angle_contacts_center_curvature_and_area(self):
        result=connect_line_fillet(*self.corner(),candidate_index=0,**self.controls())
        first,arc,last=result['curves']
        np.testing.assert_allclose(first.end_zr_m,(.75,0),atol=1e-14)
        np.testing.assert_allclose(last.start_zr_m,(1,.25),atol=1e-14)
        np.testing.assert_allclose(arc.center_zr_m,(.75,.25),atol=1e-14)
        self.assertAlmostEqual(arc.sweep_rad,math.pi/2)
        np.testing.assert_allclose(arc.evaluate(np.linspace(0,1,17))['curvature_per_m'],4)
        removed=sum(c.signed_line_area_m2 for c in self.corner())-sum(c.signed_line_area_m2 for c in result['curves'])
        self.assertAlmostEqual(removed,.25**2*(1-math.pi/4),places=14)

    def test_rotation_reflection_scaling_and_reversed_path(self):
        first,second=self.corner()
        base=connect_line_fillet(first,second,candidate_index=0,**self.controls())['curves']
        for angle,scale,mirror in ((.7,3,1),(-1.2,.01,-1)):
            c,s=math.cos(angle),math.sin(angle);matrix=np.array([[c,-s],[s,c]])@np.diag([1,mirror])
            def transform(p):return tuple(map(float,scale*(matrix@p)+np.array([2.,3.])))
            pair=[LineSegment(transform(c.start_zr_m),transform(c.end_zr_m)) for c in (first,second)]
            controls=self.controls(.25*scale)
            built=connect_line_fillet(*pair,candidate_index=0,**controls)['curves']
            for old,new in zip(base,built):
                np.testing.assert_allclose(new.evaluate(.37)['points_zr_m'],transform(old.evaluate(.37)['points_zr_m']),atol=1e-12)
        reverse=[LineSegment(c.end_zr_m,c.start_zr_m) for c in (second,first)]
        built=connect_line_fillet(*reverse,candidate_index=0,**self.controls())['curves']
        self.assertLess(built[1].sweep_rad,0)
        for old,new in zip(base,reversed(built)):
            np.testing.assert_allclose(new.evaluate(.63)['points_zr_m'],old.evaluate(.37)['points_zr_m'],atol=1e-14)

    def test_finite_extent_extension_and_no_empty_retained_line(self):
        for radius in (1.,2.):
            with self.assertRaises(ValueError):connect_line_fillet(*self.corner(),candidate_index=0,**self.controls(radius))
        pair=(LineSegment((0,0),(.5,0)),LineSegment((1,.5),(1,1)))
        with self.assertRaises(ValueError):connect_line_fillet(*pair,candidate_index=0,**self.controls())
        controls=self.controls();controls['allow_extension']=True
        result=connect_line_fillet(*pair,candidate_index=0,**controls)
        self.assertEqual(result['selected_candidate']['line_extended'],[True,True])
        controls['radius_m']=2.
        with self.assertRaises(ValueError):connect_line_fillet(*self.corner(),candidate_index=0,**controls)

    def test_parallel_reversal_and_strict_inputs(self):
        first=self.corner()[0]
        for second in (LineSegment((1,0),(2,0)),LineSegment((1,0),(0,0)),LineSegment((1,1),(2,1))):
            result=line_fillet_candidates(first,second,**self.controls())
            self.assertEqual(result['status'],'PASS');self.assertEqual(result['contact_status'],'PARALLEL_SUPPORTS')
            self.assertFalse(result['candidates'])
        for key,value in (('radius_m',0),('radius_m',True),('radius_m',math.inf),('allow_extension',1)):
            controls=self.controls();controls[key]=value
            with self.assertRaises(ValueError):line_fillet_candidates(*self.corner(),**controls)
        for index in (None,True,-1,1):
            with self.assertRaises(ValueError):connect_line_fillet(*self.corner(),candidate_index=index,**self.controls())


    def test_shallow_and_obtuse_turns_and_numerical_failure(self):
        for angle in (1e-5,.3,2.8,-2.8):
            u=(math.cos(angle),math.sin(angle))
            second=LineSegment((1,0),(1+10*u[0],10*u[1]))
            result=connect_line_fillet(LineSegment((-10,0),(1,0)),second,candidate_index=0,**self.controls(.01))
            arc=result['curves'][1]
            self.assertAlmostEqual(arc.sweep_rad,angle,places=12)
            for join in result['joins']:self.assertLess(join['tangent_angle_rad'],1e-8)
        controls=self.controls();controls['position_tolerance_m']=1e-30
        report=line_fillet_candidates(self.corner()[0],LineSegment((1,0),(2,.7)),**controls)
        self.assertEqual(report['status'],'UNVERIFIED')
        self.assertTrue(report['unresolved'])

    def test_version4_case_replay_gui_strictness_and_analytic_area(self):
        import json
        from copy import deepcopy
        from superfish_ng.tangent_construction import construct_tangent_case,replay_construction
        from superfish_ng.gui import tangent_document
        from superfish_ng.config import Case
        request=fillet_request();result=construct_tangent_case(request,candidate_index=0)
        case=Case.from_dict(result['case'])
        self.assertEqual(len(case.curved_contour.curves),5)
        self.assertAlmostEqual(case.curved_contour.area_m2,.2*.1-.02**2*(1-math.pi/4),places=14)
        self.assertEqual(replay_construction(result),result)
        gui=tangent_document(request,candidate_index=0)
        self.assertEqual(gui['construction'],result)
        self.assertEqual(replay_construction(json.loads(gui['serialized'])),result)
        altered=deepcopy(result);altered['enumeration']['radius_m']=.01
        with self.assertRaises(ValueError):replay_construction(altered)
        request['controls']['fraction_width']=1e-10
        with self.assertRaises(ValueError):construct_tangent_case(request)

    def test_fillet_case_curved_fem_scaling(self):
        from copy import deepcopy
        from superfish_ng.tangent_construction import construct_tangent_case
        from superfish_ng.config import Case
        from superfish_ng.solver import solve
        from superfish_ng.rf import quantities
        request=fillet_request();large=deepcopy(request)
        for curve in large['case_template']['geometry']['curves']:
            for key in ('start_zr_m','end_zr_m'):curve[key]=[2*x for x in curve[key]]
        g=large['case_template']['geometry']
        for key in ('join_tolerance_m','minimum_gap_m','chord_tolerance_m'):g[key]*=2
        large['case_template']['mesh']['contour_mesh']['max_edge_m']*=2
        for key in ('radius_m','position_tolerance_m'):large['controls'][key]*=2
        values=[]
        for r in (request,large):
            case=Case.from_dict(construct_tangent_case(r,candidate_index=0)['case'])
            self.assertEqual(case.geometry_order,2)
            values.append(quantities(case,solve(case)))
        a,b=values
        self.assertAlmostEqual(b['frequency_hz']/a['frequency_hz'],.5,places=10)
        for key in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs'):
            self.assertAlmostEqual(b[key]/a[key],1.,places=9)


def fillet_request():
    import json
    from pathlib import Path
    from superfish_ng.conics import curve_to_dict
    request=json.loads((Path(__file__).resolve().parents[1]/'examples/construction/capsule_line_arc_request.json').read_text())
    request['schema_version']=4;request['pair_start']=1
    case=request['case_template'];case['name']='synthetic radius-specified corner fillet'
    vertices=((0,0),(.2,0),(.2,.1),(0,.1),(0,0))
    case['geometry']['curves']=[curve_to_dict(LineSegment(a,b)) for a,b in zip(vertices,vertices[1:])]
    case['geometry']['chord_tolerance_m']=.0005
    case['mesh']['geometry_order']=2
    request['controls']=dict(radius_m=.02,allow_extension=False,position_tolerance_m=1e-12,angle_tolerance_rad=1e-8)
    return request


if __name__=='__main__':unittest.main()

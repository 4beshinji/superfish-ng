# SPDX-License-Identifier: Apache-2.0
from fractions import Fraction as F
import math
import unittest
import numpy as np
from superfish_ng.conics import EllipseArc,HyperbolaArc
from superfish_ng.conic_fillet import conic_fillet_candidates,connect_conic_fillet


class ConicFilletTests(unittest.TestCase):
    def controls(self,**extra):
        return dict(radius_m=1.,turn_direction=1,max_sweep_rad=math.pi,position_tolerance_m=1e-9,
                    angle_tolerance_rad=1e-8,fraction_width=F(1,2**40),max_boxes=2000,**extra)

    def circles(self):
        return EllipseArc((0,0),(2,2),-2.7,5.4),EllipseArc((1,0),(2,2),-2.7,5.4)

    def test_circle_contacts_radius_and_minor_major_selection(self):
        report=conic_fillet_candidates(*self.circles(),**self.controls())
        self.assertEqual(report['status'],'PASS');self.assertEqual(len(report['candidates']),2)
        self.assertEqual([c['connection_direction'] for c in report['candidates']],['SWEEP_LIMIT','FORWARD'])
        result=connect_conic_fillet(*self.circles(),candidate_index=1,**self.controls())
        a,fillet,b=result['curves']
        np.testing.assert_allclose(fillet.center_zr_m,(.5,math.sqrt(3)/2),atol=1e-9)
        np.testing.assert_allclose(a.evaluate(1.)['points_zr_m'],(1.,math.sqrt(3)),atol=1e-9)
        np.testing.assert_allclose(b.evaluate(0.)['points_zr_m'],(0.,math.sqrt(3)),atol=1e-9)
        self.assertAlmostEqual(fillet.sweep_rad,math.pi/3,places=8)
        np.testing.assert_allclose(fillet.evaluate([0.,.5,1.])['curvature_per_m'],1.,atol=1e-14)
        with self.assertRaises(ValueError):connect_conic_fillet(*self.circles(),candidate_index=0,**self.controls())
        controls=self.controls();controls['max_sweep_rad']=2*math.pi
        result=connect_conic_fillet(*self.circles(),candidate_index=0,**controls)
        self.assertAlmostEqual(result['curves'][1].sweep_rad,5*math.pi/3,places=8)

    def test_ellipse_hyperbola_known_quarter_circle(self):
        a=EllipseArc((0,0),(2,1),-.2,.5)
        b=HyperbolaArc((1.75,-1.75),(2,1),-.2,.3,1,math.pi/2)
        controls=self.controls();controls['radius_m']=.25
        result=connect_conic_fillet(a,b,candidate_index=0,**controls)
        np.testing.assert_allclose(result['curves'][1].center_zr_m,(1.75,0),atol=1e-9)
        self.assertAlmostEqual(result['curves'][1].sweep_rad,math.pi/2,places=8)
        selected=result['selected_candidate']
        self.assertTrue(all(x<=1e-9 for x in selected['trim_contact_error_bounds_m']))
        self.assertTrue(all(x<=1e-9 for x in selected['fillet_contact_error_bounds_m']))
        self.assertTrue(all(j['tangent_angle_rad']<=1e-8 for j in result['joins']))

    def test_direction_radius_and_interval_failure_are_explicit(self):
        for key,value in [('radius_m',0),('turn_direction',True),('turn_direction',0),('max_sweep_rad',7.)]:
            controls=self.controls();controls[key]=value
            with self.assertRaises(ValueError):conic_fillet_candidates(*self.circles(),**controls)
        controls=self.controls();controls['max_boxes']=1
        report=conic_fillet_candidates(*self.circles(),**controls)
        self.assertEqual(report['status'],'UNVERIFIED')
        with self.assertRaises(ValueError):connect_conic_fillet(*self.circles(),candidate_index=0,**controls)
        controls=self.controls();controls['position_tolerance_m']=1e-30
        report=conic_fillet_candidates(*self.circles(),**controls)
        self.assertFalse(any(c['connection_direction']=='FORWARD' for c in report['candidates']))
        for index in (None,True,-1,99):
            with self.assertRaises(ValueError):connect_conic_fillet(*self.circles(),candidate_index=index,**self.controls())


    def test_reversing_both_arcs_and_turn_preserves_fillet(self):
        from dataclasses import replace
        a,b=self.circles()
        original=connect_conic_fillet(a,b,candidate_index=1,**self.controls())['curves']
        def reverse(c):return replace(c,start_rad=c.start_rad+c.sweep_rad,sweep_rad=-c.sweep_rad)
        controls=self.controls();controls['turn_direction']=-1
        report=conic_fillet_candidates(reverse(b),reverse(a),**controls)
        self.assertEqual(report['status'],'PASS')
        indices=[i for i,c in enumerate(report['candidates']) if c['connection_direction']=='FORWARD']
        self.assertEqual(len(indices),1)
        result=connect_conic_fillet(reverse(b),reverse(a),candidate_index=indices[0],**controls)['curves']
        for first,second in zip(original,reversed(result)):
            np.testing.assert_allclose(first.evaluate(.3)['points_zr_m'],second.evaluate(.7)['points_zr_m'],atol=1e-9)

    def test_version5_case_replay_gui_and_independent_area_volume(self):
        from copy import deepcopy
        from superfish_ng.tangent_construction import construct_tangent_case,replay_construction
        from superfish_ng.gui import tangent_document
        from superfish_ng.config import Case
        request=conic_fillet_request();doc=construct_tangent_case(request,candidate_index=0)
        case=Case.from_dict(doc['case'])
        self.assertEqual(len(case.curved_contour.curves),4)
        a,R,B=.1,.02,.1;H=math.sqrt((a+R)**2-B**2);t=R*B/(a+R);z=.2-t;x=z-.1
        def integral(radius,end):return (end*math.sqrt(radius**2-end**2)+radius**2*math.asin(end/radius))/2
        area=2*(integral(a,x)+math.pi*a*a/4+H*t-integral(R,t))
        volume=2*math.pi*(a*a*z-(x**3+a**3)/3+(H*H+R*R)*t-t**3/3-2*H*integral(R,t))
        self.assertAlmostEqual(case.curved_contour.area_m2,area,places=11)
        self.assertAlmostEqual(case.curved_contour.volume_m3,volume,places=11)
        self.assertEqual(replay_construction(doc),doc)
        gui=tangent_document(request,candidate_index=0)
        self.assertEqual(gui['construction'],doc)
        changed=deepcopy(doc);changed['case']['name']='changed'
        with self.assertRaises(ValueError):replay_construction(changed)
        request['controls']['allow_extension']=True
        with self.assertRaises(ValueError):construct_tangent_case(request)

    def test_version5_curved_fem_scaling(self):
        from copy import deepcopy
        from superfish_ng.tangent_construction import construct_tangent_case
        from superfish_ng.config import Case
        from superfish_ng.solver import solve
        from superfish_ng.rf import quantities
        request=conic_fillet_request();large=deepcopy(request)
        for curve in large['case_template']['geometry']['curves']:
            for key in ('start_zr_m','end_zr_m','center_zr_m','semiaxes_m'):
                if key in curve:curve[key]=[2*x for x in curve[key]]
        g=large['case_template']['geometry']
        for key in ('join_tolerance_m','minimum_gap_m','chord_tolerance_m'):g[key]*=2
        large['case_template']['mesh']['contour_mesh']['max_edge_m']*=2
        for key in ('radius_m','position_tolerance_m'):large['controls'][key]*=2
        rows=[]
        for r in (request,large):
            case=Case.from_dict(construct_tangent_case(r,candidate_index=0)['case'])
            self.assertEqual(case.geometry_order,2)
            rows.append(quantities(case,solve(case)))
        a,b=rows
        self.assertAlmostEqual(b['frequency_hz']/a['frequency_hz'],.5,places=10)
        for key in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs'):
            self.assertAlmostEqual(b[key]/a[key],1.,places=9)


def conic_fillet_request():
    import json
    from pathlib import Path
    from superfish_ng.conics import LineSegment,curve_to_dict
    request=json.loads((Path(__file__).resolve().parents[1]/'examples/construction/corner_fillet_request.json').read_text())
    request['schema_version']=5;request['pair_start']=1
    case=request['case_template'];case['name']='synthetic two-lobe conic fillet'
    case['geometry']['curves']=[curve_to_dict(c) for c in (LineSegment((0,0),(.4,0)),
        EllipseArc((.3,0),(.1,.1),0.,math.pi),EllipseArc((.1,0),(.1,.1),0.,math.pi))]
    case['geometry']['edge_tags']=['axis','pec','pec']
    case['geometry']['join_tolerance_m']=1e-12
    request['controls']=dict(radius_m=.02,turn_direction=-1,max_sweep_rad=math.pi,
        position_tolerance_m=1e-12,angle_tolerance_rad=1e-8,fraction_width=2.**-44,max_boxes=2000,
        precision_bits=96,endpoint_width=2.**-100,max_series_terms=96)
    return request


if __name__=='__main__':unittest.main()

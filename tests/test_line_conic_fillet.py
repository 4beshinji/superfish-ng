# SPDX-License-Identifier: Apache-2.0
from fractions import Fraction as F
import math
import unittest
import numpy as np
from superfish_ng.conics import LineSegment,EllipseArc,HyperbolaArc
from superfish_ng.normal_offsets import normal_offset_bounds
from superfish_ng.conic_fillet import connect_conic_fillet,conic_fillet_candidates

class LineConicFilletTests(unittest.TestCase):
    def controls(self,extension=False):
        return dict(radius_m=.5,turn_direction=1,max_sweep_rad=math.pi,position_tolerance_m=1e-9,
                    angle_tolerance_rad=1e-8,allow_extension=extension)

    def test_exact_line_normal_box_and_derivative(self):
        result=normal_offset_bounds(LineSegment((0,0),(3,4)),distance_m=.5)
        self.assertEqual(result['center_box_zr_m'],((F(-2,5),F(13,5)),(F(3,10),F(43,10))))
        self.assertEqual(result['derivative_box_zr_m'],((F(3),F(3)),(F(4),F(4))))
        self.assertEqual(result['speed_factor_interval'],(F(1),F(1)))

    def test_known_line_circle_contact_and_radius(self):
        line=LineSegment((1.5,-2),(1.5,2));arc=EllipseArc((0,0),(2,2),0.,math.pi)
        result=connect_conic_fillet(line,arc,candidate_index=0,**self.controls())
        a,fillet,b=result['curves']
        np.testing.assert_allclose(fillet.center_zr_m,(1.,math.sqrt(5)/2),atol=1e-9)
        np.testing.assert_allclose(a.end_zr_m,(1.5,math.sqrt(5)/2),atol=1e-9)
        np.testing.assert_allclose(b.evaluate(0.)['points_zr_m'],(4/3,2*math.sqrt(5)/3),atol=1e-9)
        self.assertEqual(a.start_zr_m,line.start_zr_m)
        self.assertEqual(fillet.semiaxes_m,(.5,.5))

    def test_extension_and_reverse_order_are_explicit(self):
        from dataclasses import replace
        line=LineSegment((1.5,-2),(1.5,.5));arc=EllipseArc((0,0),(2,2),0.,math.pi)
        with self.assertRaises(ValueError):connect_conic_fillet(line,arc,candidate_index=0,**self.controls())
        result=connect_conic_fillet(line,arc,candidate_index=0,**self.controls(True))
        self.assertTrue(result['selected_candidate']['line_extended'])
        reverse_arc=replace(arc,start_rad=arc.start_rad+arc.sweep_rad,sweep_rad=-arc.sweep_rad)
        reverse_line=LineSegment(line.end_zr_m,line.start_zr_m)
        controls=self.controls(True);controls['turn_direction']=-1
        reverse=connect_conic_fillet(reverse_arc,reverse_line,candidate_index=0,**controls)
        for a,b in zip(result['curves'],reversed(reverse['curves'])):
            np.testing.assert_allclose(a.evaluate(.3)['points_zr_m'],b.evaluate(.7)['points_zr_m'],atol=1e-9)
        controls['allow_extension']=1
        with self.assertRaises(ValueError):conic_fillet_candidates(line,arc,**controls)


    def test_hyperbola_contact_and_reversed_extension_rejection(self):
        line=LineSegment((2,-.7),(2,1))
        arc=HyperbolaArc((1.75,-1.75),(2,1),-.2,.3,rotation_rad=math.pi/2)
        controls=self.controls();controls['radius_m']=.25
        result=connect_conic_fillet(line,arc,candidate_index=0,**controls)
        a,fillet,b=result['curves']
        np.testing.assert_allclose(fillet.center_zr_m,(1.75,0),atol=1e-9)
        np.testing.assert_allclose(a.end_zr_m,(2,0),atol=1e-9)
        np.testing.assert_allclose(b.evaluate(0.)['points_zr_m'],(1.75,.25),atol=1e-9)
        self.assertAlmostEqual(abs(fillet.sweep_rad),math.pi/2,places=8)
        controls['allow_extension']=True
        report=conic_fillet_candidates(LineSegment((2,.5),(2,1)),arc,**controls)
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(len(report['candidates']),1)
        self.assertIn('empty or reversed',report['candidates'][0]['construction_reason'])
        with self.assertRaisesRegex(ValueError,'empty or reversed'):
            connect_conic_fillet(LineSegment((2,.5),(2,1)),arc,candidate_index=0,**controls)

    def test_version6_case_area_volume_replay_and_gui(self):
        from copy import deepcopy
        import json
        from superfish_ng.config import Case
        from superfish_ng.tangent_construction import construct_tangent_case,replay_construction
        from superfish_ng.gui import tangent_document
        request=line_conic_request();result=construct_tangent_case(request,candidate_index=0)
        case=Case.from_dict(result['case'])
        A,R,c,L=.1,.02,.1,.15;C=L-R;H=math.sqrt((A-R)**2-(C-c)**2)
        z=c+A*(C-c)/(A-R);u=z-C;x=z-c
        def integral(r,t):return (t*math.sqrt(max(0.,r*r-t*t))+r*r*math.asin(t/r))/2
        area=integral(A,x)+math.pi*A*A/4+H*(L-z)+integral(R,R)-integral(R,u)
        volume=math.pi*(A*A*z-(x**3+A**3)/3+(H*H+R*R)*(L-z)-(R**3-u**3)/3+2*H*(integral(R,R)-integral(R,u)))
        self.assertAlmostEqual(case.curved_contour.area_m2,area,places=11)
        self.assertAlmostEqual(case.curved_contour.volume_m3,volume,places=11)
        self.assertEqual(replay_construction(result),result)
        gui=tangent_document(request,candidate_index=0)
        self.assertEqual(replay_construction(json.loads(gui['serialized'])),result)
        changed=deepcopy(result);changed['case']['name']='altered'
        with self.assertRaises(ValueError):replay_construction(changed)
        request['controls']['line_interval']=[-1,2]
        with self.assertRaises(ValueError):construct_tangent_case(request)

    def test_version6_curved_fem_scaling(self):
        from copy import deepcopy
        from superfish_ng.config import Case
        from superfish_ng.tangent_construction import construct_tangent_case
        from superfish_ng.solver import solve
        from superfish_ng.rf import quantities
        request=line_conic_request();large=deepcopy(request)
        for curve in large['case_template']['geometry']['curves']:
            for key in ('start_zr_m','end_zr_m','center_zr_m','semiaxes_m'):
                if key in curve:curve[key]=[2*x for x in curve[key]]
        g=large['case_template']['geometry']
        for key in ('join_tolerance_m','minimum_gap_m','chord_tolerance_m'):g[key]*=2
        large['case_template']['mesh']['contour_mesh']['max_edge_m']*=2
        for key in ('radius_m','position_tolerance_m'):large['controls'][key]*=2
        rows=[]
        for r in (request,large):
            c=Case.from_dict(construct_tangent_case(r,candidate_index=0)['case']);self.assertEqual(c.geometry_order,2)
            rows.append(quantities(c,solve(c)))
        a,b=rows
        self.assertAlmostEqual(b['frequency_hz']/a['frequency_hz'],.5,places=10)
        for key in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs'):
            self.assertAlmostEqual(b[key]/a[key],1.,places=9)


def line_conic_request():
    import json
    from pathlib import Path
    from superfish_ng.conics import curve_to_dict
    request=json.loads((Path(__file__).resolve().parents[1]/'examples/construction/two_lobe_fillet_request.json').read_text())
    request['schema_version']=6;request['case_template']['name']='synthetic line-conic fillet'
    request['case_template']['geometry']['curves']=[curve_to_dict(c) for c in (
        LineSegment((0,0),(.15,0)),LineSegment((.15,0),(.15,.1)),EllipseArc((.1,0),(.1,.1),0.,math.pi))]
    request['controls']['allow_extension']=False;request['controls']['turn_direction']=1
    return request

if __name__=='__main__':unittest.main()

# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import json
import math
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.conics import EllipseArc, HyperbolaArc
from superfish_ng.circle_conic_fillet import intersect_algebraic_circle_conic_offsets, circle_conic_fillet_candidates, connect_circle_conic_fillet

ROOT = Path(__file__).resolve().parents[1]


def controls(radius=.625, **overrides):
    result = dict(radius_m=radius, turn_direction=1, max_sweep_rad=math.pi,
                  position_tolerance_m=1e-10, angle_tolerance_rad=1e-8)
    result.update(overrides); return result


def request():
    return json.loads((ROOT/'examples/construction/circle_conic_fillet_request.json').read_text())


class CircleConicFilletTests(unittest.TestCase):
    def pair(self):
        return EllipseArc((.875, .375), (1.25, 1.25), -1., 1.), EllipseArc((0, 0), (2, 1), 0., 1.)

    def test_known_endpoint_and_all_source_pair_order(self):
        first, second = self.pair(); report = circle_conic_fillet_candidates(first, second, **controls())
        self.assertEqual(report['status'], 'PASS'); self.assertEqual(len(report['candidates']), 2)
        self.assertLess(report['candidates'][0]['root']['parameter_box'][0][1], report['candidates'][1]['root']['parameter_box'][0][0])
        built = connect_circle_conic_fillet(first, second, candidate_index=1, **controls())
        selected = built['selected_candidate']
        self.assertEqual(built['curves'][2], second)
        self.assertEqual(selected['root']['parameter_box'][1], (F(0), F(0)))
        np.testing.assert_allclose(built['curves'][1].center_zr_m, (1.375, 0), atol=1e-14)
        np.testing.assert_allclose(selected['contacts_zr_m'], ((1.875, -.375), (2, 0)), atol=1e-10)
        self.assertAlmostEqual(selected['requested_fillet_sweep_rad'], math.atan2(3, 4), places=10)
        self.assertEqual(built['curves'][1].semiaxes_m, (.625, .625))

    def test_whole_first_and_second_primitives_reverse_and_empty_piece(self):
        circle = EllipseArc((1.375, .625), (1.25, 1.25), -1., 1., -math.pi/2)
        arc = EllipseArc((0, 0), (2, 1), 0., 1.)
        report = circle_conic_fillet_candidates(circle, arc, **controls())
        index = next(i for i,r in enumerate(report['candidates']) if r['root']['parameter_box']==((F(1),F(1)),(F(0),F(0))))
        built = connect_circle_conic_fillet(circle, arc, candidate_index=index, **controls())
        self.assertEqual(built['curves'][0], circle); self.assertEqual(built['curves'][2], arc)
        a = replace(arc, start_rad=1., sweep_rad=-1.); c = replace(circle, start_rad=0., sweep_rad=-1.)
        reverse = circle_conic_fillet_candidates(a, c, **controls(turn_direction=-1))
        j = next(i for i,r in enumerate(reverse['candidates']) if r['root']['parameter_box']==((F(1),F(1)),(F(0),F(0))))
        reversed_built = connect_circle_conic_fillet(a, c, candidate_index=j, **controls(turn_direction=-1))
        for left,right in zip(built['curves'], reversed(reversed_built['curves'])):
            np.testing.assert_allclose(left.evaluate(.3)['points_zr_m'], right.evaluate(.7)['points_zr_m'], atol=1e-9)
        empty = circle_conic_fillet_candidates(replace(circle, start_rad=0.), arc, **controls())
        row = next(r for r in empty['candidates'] if r['root']['parameter_box'][0]==(F(0),F(0)))
        self.assertEqual(row['connection_direction'], 'UNVERIFIED'); self.assertIn('empty',row['construction_reason'])

    def test_same_center_ties_retain_source_pairs_and_exact_zero_length(self):
        circle = EllipseArc((1,0),(3,3),-.1,6.2); arc = EllipseArc((0,0),(2,1),-.1,3.4)
        report = circle_conic_fillet_candidates(circle,arc,**controls(2.,max_sweep_rad=6.2))
        self.assertEqual(report['status'],'PASS'); self.assertEqual(len(report['candidates']),2)
        first,second = report['candidates']
        self.assertEqual(first['root']['center_group'],second['root']['center_group'])
        self.assertEqual(first['root']['parameter_box'][0],second['root']['parameter_box'][0])
        self.assertLess(first['root']['parameter_box'][1][1],second['root']['parameter_box'][1][0])
        self.assertEqual(first['connection_direction'],'FORWARD'); self.assertFalse(first['root']['source_contacts_coincide'])
        self.assertEqual(second['connection_direction'],'ZERO_LENGTH'); self.assertEqual(second['contact_distance_m'],0.)
        with self.assertRaisesRegex(ValueError,'coincide'):connect_circle_conic_fillet(circle,arc,candidate_index=1,**controls(2.,max_sweep_rad=6.2))

    def test_cusp_and_both_hyperbola_branches_construct_at_known_centers(self):
        circle = EllipseArc((1.5,-1.5),(2,2),-3.,6.); arc = EllipseArc((0,0),(2,1),-.1,3.4)
        cusp = connect_circle_conic_fillet(circle,arc,candidate_index=0,**controls(.5,max_sweep_rad=6.2))
        self.assertEqual(cusp['selected_candidate']['root']['source_contact_kind'],'CUSP')
        np.testing.assert_allclose(cusp['curves'][1].center_zr_m,(1.5,0),atol=1e-12)
        for branch in (-1,1):
            a = HyperbolaArc((0,0),(2,1),0.,1.,branch=branch)
            c = EllipseArc((1.25,-.75),(1,1),0.,1.) if branch==1 else EllipseArc((-3.25,.75),(1.5,1.5),-1.,1.)
            report = circle_conic_fillet_candidates(c,a,**controls(.25,turn_direction=-branch))
            self.assertEqual(report['status'],'PASS')
            index = next(i for i,r in enumerate(report['candidates']) if r['root']['parameter_box'][1]==(F(0),F(0)))
            built = connect_circle_conic_fillet(c,a,candidate_index=index,**controls(.25,turn_direction=-branch))
            self.assertEqual(built['curves'][2],a)
            np.testing.assert_allclose(built['curves'][1].center_zr_m,(2.25*branch,0),atol=1e-12)

    def test_collapsed_circle_continuum_disjoint_and_finite_restriction(self):
        circle = EllipseArc((1,0),(1,1),-.3,1.); arc = EllipseArc((0,0),(2,1),0.,1.)
        report = circle_conic_fillet_candidates(circle,arc,**controls(1.))
        self.assertEqual(report['status'],'UNVERIFIED'); self.assertEqual(report['candidates'],[])
        self.assertTrue(report['certificate']['algebraic_intersections']['infinite'])
        self.assertTrue(any(r.get('stage')=='collapsed_circle' for r in report['unresolved']))
        with self.assertRaisesRegex(ValueError,'UNVERIFIED'):connect_circle_conic_fillet(circle,arc,candidate_index=0,**controls(1.))
        disjoint = circle_conic_fillet_candidates(replace(circle,center_zr_m=(10,0)),arc,**controls(1.))
        self.assertEqual(disjoint['status'],'PASS'); self.assertEqual(disjoint['candidates'],[])
        result = intersect_algebraic_circle_conic_offsets(*self.pair(),first_distance_m=.625,second_distance_m=.625,second_interval=(.1,1))
        self.assertEqual(result['status'],'PASS'); self.assertEqual(len(result['roots']),1)

    def test_negative_circle_radius_preserves_exact_coincident_source_contacts(self):
        # The circle and ellipse share source contacts (0,+/-1). Their distance
        # 2 offsets meet at (0,-/+1), although the circular radial map reverses.
        # There are also four crossings: with s=sqrt(1+3*sin(theta)^2),
        # incidence factors as (s-2)*(s*s+2*s-4)=0, so s=sqrt(5)-1 is admitted.
        circle=EllipseArc((0,0),(1,1),-3.,6.);arc=EllipseArc((0,0),(2,1),-3.,6.)
        for reverse in (False,True):
            c=replace(circle,start_rad=3.,sweep_rad=-6.) if reverse else circle
            a=replace(arc,start_rad=3.,sweep_rad=-6.) if reverse else arc
            for exchange in (False,True):
                report=circle_conic_fillet_candidates(*( (a,c) if exchange else (c,a)),**controls(2.,turn_direction=-1 if reverse else 1))
                self.assertEqual(report['status'],'PASS');self.assertEqual(len(report['candidates']),6)
                zeros=[row for row in report['candidates'] if row['connection_direction']=='ZERO_LENGTH']
                self.assertEqual(len(zeros),2)
                self.assertTrue(all(row['root']['source_contacts_coincide'] for row in zeros))
                self.assertTrue(all(row['root']['source_contacts_coincide'] is False for row in report['candidates'] if row not in zeros))
                centers={row['root']['center_box_zr_m'] for row in zeros}
                self.assertEqual(centers,{((F(0),F(0)),(F(-1),F(-1))),((F(0),F(0)),(F(1),F(1)))})

    def test_precision_order_budgets_and_output_errors_remain_separate(self):
        for extra in ({'max_root_boxes':1},{'max_refinements':1},{'max_fraction_steps':1},{'fraction_width':.75}):
            report=circle_conic_fillet_candidates(*self.pair(),**controls(**extra))
            self.assertEqual(report['status'],'UNVERIFIED')
            with self.assertRaisesRegex(ValueError,'UNVERIFIED'):connect_circle_conic_fillet(*self.pair(),candidate_index=0,**controls(**extra))
        strict=circle_conic_fillet_candidates(*self.pair(),**controls(position_tolerance_m=1e-30))
        self.assertEqual(strict['status'],'PASS')
        self.assertFalse(any(r['connection_direction']=='FORWARD' for r in strict['candidates']))
        limited=circle_conic_fillet_candidates(*self.pair(),**controls(max_sweep_rad=.1))
        self.assertTrue(all(r['connection_direction']=='SWEEP_LIMIT' for r in limited['candidates']))

    def test_old_complete_documents_and_strict_version_eight(self):
        from superfish_ng.tangent_construction import construct_tangent_case,replay_construction
        for name in ('fillet_construction_v5_v6.json','fillet_construction_v7.json'):
            raw=(ROOT/'tests/fixtures'/name).read_bytes();data=json.loads(raw)
            for doc in data if isinstance(data,list) else [data]:self.assertEqual(replay_construction(doc),doc)
            self.assertEqual((ROOT/'tests/fixtures'/name).read_bytes(),raw)
        for key,value in (('allow_extension',False),('max_boxes',100),('precision_bits',96),('max_refinements',True)):
            changed=request();changed['controls'][key]=value
            with self.assertRaises(ValueError):construct_tangent_case(changed)
        changed=request();changed['case_template']['geometry']['curves'][3]['semiaxes_m'][1]*=2
        with self.assertRaisesRegex(ValueError,'one circle'):construct_tangent_case(changed)
        for index in (None,True,-1,99):
            with self.assertRaises(ValueError):connect_circle_conic_fillet(*self.pair(),candidate_index=index,**controls())

    def test_closed_case_independent_area_volume_save_cli_gui_and_rejection(self):
        from superfish_ng.tangent_construction import construct_tangent_case,replay_construction
        from superfish_ng.construction_diagnostics import diagnose_construction,replay_construction_diagnosis
        from superfish_ng.config import Case
        from superfish_ng.gui import tangent_document
        from superfish_ng.cli import main
        r=request();doc=construct_tangent_case(r,candidate_index=0);case=Case.from_dict(doc['case']);u=1/32;alpha=math.atan2(3,4)
        self.assertEqual(doc['status'],'CASE_VALIDATED');self.assertEqual(len(doc['case']['geometry']['curves']),7)
        self.assertEqual(doc['case']['geometry']['curves'][5],r['case_template']['geometry']['curves'][4])
        self.assertAlmostEqual(case.curved_contour.area_m2,(751/256+121*math.pi/64-75*alpha/128)*u*u,delta=1e-12)
        self.assertAlmostEqual(case.curved_contour.volume_m3,math.pi*(46723/6144+1043*math.pi/256-225*alpha/128)*u**3,delta=1e-12)
        self.assertEqual(replay_construction(doc),doc)
        diagnosis=diagnose_construction(doc);self.assertEqual(diagnosis['schema_version'],10);self.assertEqual(replay_construction_diagnosis(diagnosis),diagnosis)
        self.assertEqual(tangent_document(diagnosis,replay=True)['construction'],doc)
        for key in ('case','enumeration','candidate_index'):
            changed=deepcopy(doc);changed[key]=None
            with self.assertRaises(ValueError):replay_construction(changed)
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'request.json';out=Path(tmp)/'constructed.json';export=Path(tmp)/'case.json'
            source.write_text(json.dumps(r)+'\n')
            self.assertEqual(main(['construct-tangent',str(source),'--out',str(out),'--candidate-index','0']),0)
            self.assertEqual(main(['export-constructed-case',str(out),'--out',str(export)]),0)
            self.assertEqual(json.loads(out.read_text()),doc);self.assertEqual(json.loads(export.read_text()),doc['case'])
        bad=deepcopy(r);bad['case_template']['rf']['beta']=0
        self.assertEqual(construct_tangent_case(bad)['status'],'CANDIDATES')
        with self.assertRaisesRegex(ValueError,'beta'):construct_tangent_case(bad,candidate_index=0)


if __name__=='__main__':unittest.main()

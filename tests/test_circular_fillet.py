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

from superfish_ng.circular_fillet import circular_fillet_candidates, connect_circular_fillet, intersect_algebraic_circular_offsets
from superfish_ng.conics import EllipseArc

ROOT = Path(__file__).resolve().parents[1]


def controls(radius=.625, **changes):
    result = dict(radius_m=radius, turn_direction=1, max_sweep_rad=math.pi,
                  position_tolerance_m=1e-10, angle_tolerance_rad=1e-8)
    result.update(changes); return result


def request():
    return json.loads((ROOT/'examples/construction/circular_fillet_request.json').read_text())


class CircularFilletTests(unittest.TestCase):
    def pair(self):
        return EllipseArc((.875,.375),(1.25,1.25),-1.,1.), EllipseArc((0,0),(2,2),0.,1.)

    def test_known_finite_endpoint_and_two_support_crossings(self):
        first, second = self.pair()
        result = connect_circular_fillet(first, second, candidate_index=0, **controls())
        self.assertEqual(len(result['enumeration']['candidates']),1)
        self.assertEqual(result['curves'][2],second)
        self.assertEqual(result['selected_candidate']['root']['parameter_box'][1],(F(0),F(0)))
        np.testing.assert_allclose(result['curves'][1].center_zr_m,(1.375,0),atol=1e-14)
        np.testing.assert_allclose(result['selected_candidate']['contacts_zr_m'],((1.875,-.375),(2,0)),atol=1e-10)
        self.assertAlmostEqual(result['selected_candidate']['requested_fillet_sweep_rad'],math.atan2(3,4),places=10)
        circles=[replace(c,start_rad=-3.,sweep_rad=6.) for c in (first,second)]
        report=circular_fillet_candidates(*circles,**controls(max_sweep_rad=6.2))
        self.assertEqual(report['status'],'PASS');self.assertEqual(len(report['candidates']),2)
        self.assertLess(report['candidates'][0]['root']['parameter_box'][0][1],report['candidates'][1]['root']['parameter_box'][0][0])

    def test_whole_primitives_reverse_and_empty_retained_range(self):
        a=EllipseArc((1.375,.625),(1.25,1.25),-1.,1.,-math.pi/2);b=EllipseArc((0,0),(2,2),0.,1.)
        built=connect_circular_fillet(a,b,candidate_index=0,**controls())
        self.assertEqual(built['curves'][0],a);self.assertEqual(built['curves'][2],b)
        rev=connect_circular_fillet(replace(b,start_rad=1.,sweep_rad=-1.),replace(a,start_rad=0.,sweep_rad=-1.),
                                  candidate_index=0,**controls(turn_direction=-1))
        for left,right in zip(built['curves'],reversed(rev['curves'])):
            np.testing.assert_allclose(left.evaluate(.3)['points_zr_m'],right.evaluate(.7)['points_zr_m'],atol=1e-9)
        empty=circular_fillet_candidates(replace(a,start_rad=0.),b,**controls())
        self.assertEqual(empty['status'],'PASS')
        row=next(r for r in empty['candidates'] if r['root']['parameter_box'][0]==(F(0),F(0)))
        self.assertEqual(row['connection_direction'],'UNVERIFIED');self.assertIn('empty',row['construction_reason'])

    def test_external_internal_and_negative_radius_tangencies(self):
        cases=[(2.,2.,2.,0.,math.pi,False,(1.,0.)),
               (3.,2.,1.,0.,0.,True,(2.,0.)),
               (.5,.5,1.,math.pi,0.,False,(.5,0.)),
               (.5,1.5,1.,math.pi,math.pi,True,(.5,0.))]
        for ra,rb,separation,aa,ab,zero,center in cases:
            a=EllipseArc((0,0),(ra,ra),-1.,2.,aa);b=EllipseArc((separation,0),(rb,rb),-1.,2.,ab)
            result=circular_fillet_candidates(a,b,**controls(1.,max_sweep_rad=3.2))
            self.assertEqual(result['status'],'PASS');self.assertEqual(len(result['candidates']),1)
            row=result['candidates'][0]
            self.assertEqual(row['root']['source_contact_kind'],'REGULAR_TANGENCY')
            self.assertEqual(row['root']['source_contacts_coincide'],zero)
            self.assertEqual(row['connection_direction'],'ZERO_LENGTH' if zero else 'FORWARD')
            for bounds,value in zip(row['root']['center_box_zr_m'],center):self.assertEqual(bounds,(F(value),F(value)))

    def test_same_support_isolated_endpoints_and_continuum(self):
        a=EllipseArc((0,0),(3,3),-1.,1.);b=EllipseArc((0,0),(1,1),0.,1.,math.pi)
        result=connect_circular_fillet(a,b,candidate_index=0,**controls(2.,max_sweep_rad=3.2))
        self.assertEqual(result['curves'][0],a);self.assertEqual(result['curves'][2],b)
        self.assertEqual(result['selected_candidate']['root']['source_contact_kind'],'SHARED_SUPPORT_ENDPOINT')
        self.assertEqual(result['selected_candidate']['root']['parameter_box'],((F(1),F(1)),(F(0),F(0))))
        self.assertEqual(result['curves'][1].center_zr_m,(1.,0.))
        zero=circular_fillet_candidates(a,replace(a,start_rad=0.),**controls(2.))
        self.assertEqual(zero['status'],'PASS');self.assertEqual(zero['candidates'][0]['connection_direction'],'ZERO_LENGTH')
        for c,d in ((replace(a,start_rad=-.5),replace(b,start_rad=-.5)),
                    (replace(a,rotation_rad=.3,start_rad=-.5),replace(a,rotation_rad=-.3,start_rad=-.5))):
            infinite=circular_fillet_candidates(c,d,**controls(2.))
            self.assertEqual(infinite['status'],'UNVERIFIED');self.assertEqual(infinite['candidates'],[])
            with self.assertRaisesRegex(ValueError,'UNVERIFIED'):connect_circular_fillet(c,d,candidate_index=0,**controls(2.))
        disjoint=circular_fillet_candidates(a,replace(b,start_rad=.5),**controls(2.))
        self.assertEqual(disjoint['status'],'PASS');self.assertEqual(disjoint['candidates'],[])
        # Different binary rotation norms define different concentric circles.
        unequal=circular_fillet_candidates(replace(a,rotation_rad=.3),replace(a,rotation_rad=.7),**controls(2.))
        self.assertEqual(unequal['status'],'PASS');self.assertEqual(unequal['candidates'],[])
        rotated=replace(a,rotation_rad=.3,start_rad=-.75)
        endpoint=circular_fillet_candidates(rotated,replace(rotated,start_rad=.25),**controls(2.))
        self.assertEqual(endpoint['status'],'PASS');self.assertEqual(endpoint['candidates'][0]['connection_direction'],'ZERO_LENGTH')
        self.assertEqual(endpoint['candidates'][0]['root']['parameter_box'],((F(1),F(1)),(F(0),F(0))))

    def test_collapsed_circles_incidence_exclusion_and_concentric_disjoint(self):
        a=EllipseArc((1,0),(1,1),-.5,1.);b=EllipseArc((0,0),(2,2),-.5,1.)
        for c,d in ((a,b),(a,a)):
            r=circular_fillet_candidates(c,d,**controls(1.))
            self.assertEqual(r['status'],'UNVERIFIED');self.assertEqual(r['candidates'],[])
            self.assertTrue(r['certificate']['algebraic_intersections']['infinite'])
        for c,d in ((a,replace(b,start_rad=1.)),(a,replace(a,center_zr_m=(3,0))),
                    (replace(a,center_zr_m=(0,0)),replace(b,semiaxes_m=(3,3)))):
            r=circular_fillet_candidates(c,d,**controls(1.))
            self.assertEqual(r['status'],'PASS');self.assertEqual(r['candidates'],[])

    def test_near_tangent_counts_and_restricted_domains(self):
        a=EllipseArc((0,0),(2,2),-1.,2.);b=EllipseArc((2,0),(2,2),-1.,2.,math.pi)
        for delta,count in ((-2**-30,2),(0.,1),(2**-30,0)):
            r=intersect_algebraic_circular_offsets(a,replace(b,center_zr_m=(2+delta,0)),first_distance_m=1.,second_distance_m=1.)
            self.assertEqual(r['status'],'PASS');self.assertEqual(len(r['roots']),count)
        r=intersect_algebraic_circular_offsets(*self.pair(),first_distance_m=.625,second_distance_m=.625,second_interval=(.1,1))
        self.assertEqual(r['status'],'PASS');self.assertEqual(r['roots'],[])

    def test_budgets_precision_and_strict_input(self):
        for change in ({'max_fraction_steps':1},{'max_series_terms':1}):
            r=circular_fillet_candidates(*self.pair(),**controls(**change));self.assertEqual(r['status'],'UNVERIFIED')
            with self.assertRaisesRegex(ValueError,'UNVERIFIED'):connect_circular_fillet(*self.pair(),candidate_index=0,**controls(**change))
        strict=circular_fillet_candidates(*self.pair(),**controls(position_tolerance_m=1e-30))
        self.assertEqual(strict['status'],'PASS');self.assertFalse(any(r['connection_direction']=='FORWARD' for r in strict['candidates']))
        self.assertEqual(circular_fillet_candidates(*self.pair(),**controls(max_sweep_rad=.1))['candidates'][0]['connection_direction'],'SWEEP_LIMIT')
        from superfish_ng.tangent_construction import construct_tangent_case
        for key,value in (('allow_extension',False),('max_boxes',100),('max_root_boxes',100),('precision_bits',96),('max_radical_refinements',True)):
            r=request();r['controls'][key]=value
            with self.assertRaises(ValueError):construct_tangent_case(r)
        r=request();r['case_template']['geometry']['curves'][4]['semiaxes_m'][1]*=.75
        with self.assertRaisesRegex(ValueError,'two circular'):construct_tangent_case(r)
        for index in (None,True,-1,99):
            with self.assertRaises(ValueError):connect_circular_fillet(*self.pair(),candidate_index=index,**controls())

    def test_saved_versions_five_through_eight_remain_exact(self):
        from superfish_ng.tangent_construction import replay_construction
        for name in ('fillet_construction_v5_v6.json','fillet_construction_v7.json','fillet_construction_v8.json'):
            raw=(ROOT/'tests/fixtures'/name).read_bytes();data=json.loads(raw)
            for doc in data if isinstance(data,list) else [data]:self.assertEqual(replay_construction(doc),doc)
            self.assertEqual((ROOT/'tests/fixtures'/name).read_bytes(),raw)

    def test_closed_case_analytic_integrals_cli_gui_and_replay(self):
        from superfish_ng.tangent_construction import construct_tangent_case,replay_construction
        from superfish_ng.construction_diagnostics import diagnose_construction,replay_construction_diagnosis
        from superfish_ng.config import Case
        from superfish_ng.gui import tangent_document
        from superfish_ng.cli import main
        r=request();doc=construct_tangent_case(r,candidate_index=0);case=Case.from_dict(doc['case']);u=1/32;alpha=math.atan2(3,4)
        self.assertEqual(doc['status'],'CASE_VALIDATED');self.assertEqual(len(doc['case']['geometry']['curves']),7)
        self.assertEqual(doc['case']['geometry']['curves'][5],r['case_template']['geometry']['curves'][4])
        self.assertAlmostEqual(case.curved_contour.area_m2,(751/256+153*math.pi/64-75*alpha/128)*u*u,delta=1e-12)
        self.assertAlmostEqual(case.curved_contour.volume_m3,math.pi*(75395/6144+1299*math.pi/256-225*alpha/128)*u**3,delta=1e-12)
        self.assertEqual(replay_construction(doc),doc)
        diagnosis=diagnose_construction(doc);self.assertEqual(diagnosis['schema_version'],10)
        self.assertEqual(replay_construction_diagnosis(diagnosis),diagnosis)
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


if __name__ == '__main__': unittest.main()

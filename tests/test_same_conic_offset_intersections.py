# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D,localcontext
from fractions import Fraction as F
import itertools,json,math
from pathlib import Path
import tempfile
import unittest
from superfish_ng.conics import EllipseArc,HyperbolaArc,curve_from_dict
from superfish_ng.offset_degeneracies import classify_offset_degeneracies
from superfish_ng.same_conic_offset_intersections import _sqrt_interval

FIXTURES=Path(__file__).parent/'fixtures'


class SameConicOffsetIntersectionTests(unittest.TestCase):
    def diagnose(self,a,b,d,e=None,**kwargs):
        return classify_offset_degeneracies(a,b,first_distance_m=d,second_distance_m=d if e is None else e,**kwargs)

    def previous(self):return json.loads((FIXTURES/'offset_diagnosis_v3_same_conics.json').read_text())

    def pair(self,old):
        request=old['construction']['request'];index=request['pair_start']
        curves=tuple(map(curve_from_dict,request['case_template']['geometry']['curves'][index:index+2]))
        controls=request['controls'];distance=controls['radius_m']*controls['turn_direction']
        return curves,distance

    def test_seven_independent_initial_invariants_are_complete(self):
        for old,count in zip(self.previous(),(1,2,1,0,1,2,0)):
            curves,distance=self.pair(old);result=self.diagnose(*curves,distance)
            self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['finite_center_count'],count)
            self.assertFalse(result['infinite_parameter_pairs'])
            self.assertEqual(result['classification'],'FINITE_CENTERS' if count else 'DISJOINT')

    def test_exchange_reverse_binary_rotations_scale_and_hyperbola_branches(self):
        for old,count in zip(self.previous(),(1,2,1,0,1,2,0)):
            original,distance=self.pair(old)
            for scale,angle,reverse,exchange in itertools.product((2.**-100,1.,2.**100),(0.,.3),(False,True),(False,True)):
                curves=[replace(curve,center_zr_m=(3*scale,4*scale),semiaxes_m=tuple(x*scale for x in curve.semiaxes_m),rotation_rad=angle) for curve in original]
                distances=[distance*scale]*2
                if reverse:
                    b=curves[1]
                    curves[1]=(replace(b,start_rad=b.start_rad+b.sweep_rad,sweep_rad=-b.sweep_rad) if isinstance(b,EllipseArc)
                               else replace(b,start_parameter=b.end_parameter,end_parameter=b.start_parameter))
                    distances[1]=-distances[1]
                if exchange:curves.reverse();distances.reverse()
                result=self.diagnose(*curves,*distances)
                self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['finite_center_count'],count)
            if isinstance(original[0],HyperbolaArc):
                result=self.diagnose(*(replace(curve,branch=-1) for curve in original),-distance)
                self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['finite_center_count'],count)

    def test_both_ellipse_axis_orders_and_one_ulp_cusp_limits(self):
        a=EllipseArc((0,0),(1,2),1.,.5)
        result=self.diagnose(a,replace(a,start_rad=-1.5),2.5)
        self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['finite_center_count'],1)
        a=replace(a,start_rad=.5)
        result=self.diagnose(a,replace(a,start_rad=2.),.75)
        self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['finite_center_count'],1)
        a=EllipseArc((0,0),(2,1),0.,.25);b=replace(a,start_rad=-.25)
        for distance,count in ((math.nextafter(.5,0.),1),(.5,1),(math.nextafter(.5,math.inf),2)):
            result=self.diagnose(a,b,distance)
            self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['finite_center_count'],count)
        a=HyperbolaArc((0,0),(2,1),0.,.25);b=replace(a,start_parameter=-.25,end_parameter=0.)
        for distance,count in ((math.nextafter(-.5,0.),1),(-.5,1),(math.nextafter(-.5,-math.inf),2)):
            result=self.diagnose(a,b,distance)
            self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['finite_center_count'],count)

    def test_shared_endpoint_deduplication_zero_offsets_periods_and_partial_domains(self):
        a=EllipseArc((0,0),(2,1),0.,4.);b=replace(a,start_rad=-1.,sweep_rad=1.)
        result=self.diagnose(a,b,2.)
        self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['finite_center_count'],1)
        self.assertEqual(result['classification'],'SHARED_PARAMETER_ENDPOINT')
        present=[row for row in result['evidence']['self_contacts'] if row['parameter_pair_in_domain']]
        self.assertEqual(len(present),1);self.assertEqual(present[0]['duplicates_shared_endpoint'],[True])
        a=replace(a,start_rad=3.,sweep_rad=.5);b=replace(a,start_rad=-3.1,sweep_rad=.3)
        result=self.diagnose(a,b,0.)
        self.assertTrue(result['finite_domain_complete']);self.assertTrue(result['infinite_parameter_pairs'])
        self.assertIsNone(result['finite_center_count'])
        result=self.diagnose(a,b,0.,first_interval=(0.,.1))
        self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['classification'],'DISJOINT')
        a=HyperbolaArc((0,0),(2,1),0.,1.);b=replace(a,start_parameter=1.,end_parameter=2.)
        result=self.diagnose(a,b,0.)
        self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['finite_center_count'],1)

    def test_root_enclosures_have_independent_decimal_bounds_without_float_floor(self):
        with localcontext() as context:
            context.prec=160
            for value in (F(0),F(1,2),F(1),F(2),F(1,2**200),F(2**200),F(.3)):
                low,high=_sqrt_interval(value,F(1,2**120))
                self.assertLessEqual(low*low,value);self.assertGreaterEqual(high*high,value)
                self.assertLessEqual(high-low,F(1,2**120))
                expected=(D(value.numerator)/D(value.denominator)).sqrt()
                self.assertLessEqual(D(low.numerator)/D(low.denominator),expected)
                self.assertGreaterEqual(D(high.numerator)/D(high.denominator),expected)

    def test_budget_keeps_known_witnesses_and_unmatched_supports_remain_unknown(self):
        for a in (EllipseArc((0,0),(2,1),0.,1.),HyperbolaArc((0,0),(2,1),0.,1.)):
            b=replace(a,start_rad=-1.) if isinstance(a,EllipseArc) else replace(a,start_parameter=-1.,end_parameter=0.)
            distance=.75 if isinstance(a,EllipseArc) else -.75
            result=self.diagnose(a,b,distance,max_series_terms=1)
            self.assertFalse(result['finite_domain_complete']);self.assertEqual(result['classification'],'SHARED_PARAMETER_ENDPOINT')
            for changed in (replace(b,center_zr_m=(math.nextafter(0.,1.),0)),replace(b,semiaxes_m=(3,1)),replace(b,rotation_rad=.1)):
                self.assertFalse(self.diagnose(a,changed,distance)['finite_domain_complete'])
            for extra in ({'first_interval':(-.1,1.)},{'max_series_terms':True},{'endpoint_width':0}):
                with self.assertRaises(ValueError):self.diagnose(a,b,distance,**extra)
        a=HyperbolaArc((0,0),(2,1),.25,.75)
        self.assertFalse(self.diagnose(a,replace(a,branch=-1),-.75)['finite_domain_complete'])

    def test_saved_versions_one_two_three_and_current_keep_rules_and_bytes(self):
        from superfish_ng.construction_diagnostics import diagnose_construction,replay_construction_diagnosis
        from superfish_ng.gui import tangent_document
        from superfish_ng.cli import main
        with tempfile.TemporaryDirectory() as temporary:
            for index,(old,count) in enumerate(zip(self.previous(),(1,2,1,0,1,2,0))):
                self.assertEqual(old['schema_version'],3);self.assertFalse(old['diagnosis']['finite_domain_complete'])
                self.assertEqual(replay_construction_diagnosis(old),old)
                self.assertEqual(tangent_document(old,replay=True)['offset_diagnosis'],old)
                new=diagnose_construction(old['construction'])
                self.assertEqual(new['schema_version'],7);self.assertTrue(new['diagnosis']['finite_domain_complete'])
                self.assertEqual(new['diagnosis']['finite_center_count'],count)
                self.assertEqual(new['construction'],old['construction']);self.assertEqual(replay_construction_diagnosis(new),new)
                changed=deepcopy(new);changed['schema_version']=3
                with self.assertRaises(ValueError):replay_construction_diagnosis(changed)
                source=Path(temporary)/f'{index}-old.json';out=Path(temporary)/f'{index}-replayed.json'
                source.write_text(json.dumps(old,indent=2)+'\n')
                expected_code=1 if old['diagnosis']['status']=='UNVERIFIED' else 0
                self.assertEqual(main(['diagnose-construction',str(source),'--out',str(out)]),expected_code)
                self.assertEqual(source.read_bytes(),out.read_bytes())
                source=Path(temporary)/f'{index}-construction.json';out=Path(temporary)/f'{index}-new.json'
                source.write_text(json.dumps(old['construction']))
                self.assertEqual(main(['diagnose-construction',str(source),'--out',str(out)]),0)
                self.assertEqual(json.loads(out.read_text()),new)
        for name in ('offset_diagnosis_v1.json','offset_diagnosis_v2_general.json'):
            for row in json.loads((FIXTURES/name).read_text()):self.assertEqual(replay_construction_diagnosis(row),row)


if __name__=='__main__':unittest.main()

# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import itertools,json,math
from pathlib import Path
import tempfile
import unittest

from test_coincident_circle_arcs import decimal_pi
from superfish_ng.conics import EllipseArc,rotation_cos_sin
from superfish_ng.general_coincident_circle_arcs import _equal_support_radii,_relative_phase
from superfish_ng.offset_degeneracies import classify_offset_degeneracies


def decimal_value(value):
    fraction=F(value)
    return D(fraction.numerator)/D(fraction.denominator)


def decimal_sine_cosine(angle):
    sine=angle;cosine=D(1);sine_term=angle;cosine_term=D(1)
    for index in range(1,180):
        sine_term*=-angle*angle/D((2*index)*(2*index+1))
        cosine_term*=-angle*angle/D((2*index-1)*(2*index))
        sine+=sine_term;cosine+=cosine_term
        if max(abs(sine_term),abs(cosine_term))<D('1e-130'):return sine,cosine
    raise AssertionError('independent trigonometric reference did not converge')


def decimal_phase(x,y):
    """Independent Newton zero of y*cos(theta)-x*sin(theta), no atan series."""
    with localcontext() as context:
        context.prec=120
        scale=max(abs(x),abs(y));x=decimal_value(F(x)/scale);y=decimal_value(F(y)/scale)
        angle=D(math.atan2(float(y),float(x)))
        for _ in range(8):
            sine,cosine=decimal_sine_cosine(angle)
            angle+=(y*cosine-x*sine)/(y*sine+x*cosine)
        sine,cosine=decimal_sine_cosine(angle)
        if abs(y*cosine-x*sine)>D('1e-110'):raise AssertionError('independent phase residual failed')
        return +angle


class GeneralCoincidentCircleArcTests(unittest.TestCase):
    def diagnose(self,a,b,d=1.,e=1.,**kwargs):
        return classify_offset_degeneracies(a,b,first_distance_m=d,second_distance_m=e,**kwargs)

    def test_algebraic_support_identity_rejects_extraneous_squared_solutions(self):
        sources=(F(1,2),F(1),F(2),F(3));distances=tuple(map(F,(-4,-1,0,.5,1,2,4)))
        rejected_squared=0
        for a,b,d,e in itertools.product(sources,sources,distances,distances):
            first,second=a-d,b-e
            result=_equal_support_radii(a*a,b*b,d,e)
            if first==0 or second==0:self.assertIsNone(result);continue
            expected=abs(first)==abs(second)
            self.assertEqual(result is not None,expected)
            sign=(1 if first>0 else -1)*(1 if second>0 else -1)
            c=d-sign*e;remainder=a*a+b*b-c*c
            if remainder*remainder==4*a*a*b*b and not expected:rejected_squared+=1
        self.assertGreater(rejected_squared,0)
        for a,d,e in itertools.product((F(2),F(3),F(5),F(7)),distances,distances):
            self.assertEqual(_equal_support_radii(a,a,d,e) is not None,d==e)

    def test_relative_phase_enclosures_match_independent_trigonometric_newton(self):
        with localcontext() as context:
            context.prec=120;pi=decimal_pi()
            for x,y in itertools.product((F(-10),F(-1),F(-1,10),F(1,10),F(1),F(10)),repeat=2):
                coefficient,bounds=_relative_phase(x,y,F(1,2**100),96)
                angle=decimal_phase(x,y)
                self.assertLess(decimal_value(coefficient)*pi+decimal_value(bounds[0]),angle)
                self.assertLess(angle,decimal_value(coefficient)*pi+decimal_value(bounds[1]))
            for x,y,expected in ((1,0,F(0)),(-1,0,F(1)),(0,1,F(1,2)),(0,-1,F(-1,2))):
                self.assertEqual(_relative_phase(F(x),F(y),F(1,2**100),96),(expected,(F(0),F(0))))

    def test_nonrational_rotation_norm_and_general_relative_angle_are_complete(self):
        for angle in (.1,.3,.7,1.2):
            a=EllipseArc((0,0),(2,2),0.,1.,angle)
            for name,b,expected in [('same',replace(a,start_rad=.5),'INFINITE_PARAMETER_PAIRS'),
                    ('reflected',replace(a,rotation_rad=-angle),'INFINITE_PARAMETER_PAIRS' if angle<.5 else 'DISJOINT')]:
                result=self.diagnose(a,b)
                self.assertTrue(result['finite_domain_complete'],name);self.assertEqual(result['classification'],expected)
                self.assertIn('source_radius_squares',result['evidence'])

    def test_exchange_reverse_orientation_scale_and_negative_radius(self):
        for scale,distance,reverse in itertools.product((2.**-100,1.,2.**100),(1.,4.),(False,True)):
            a=EllipseArc((3*scale,4*scale),(2*scale,2*scale),-1.,2.,.3)
            b=replace(a,rotation_rad=-.3)
            d=e=distance*scale
            if reverse:b=replace(b,start_rad=1.,sweep_rad=-2.);e=-e
            for first,second,left,right in ((a,b,d,e),(b,a,e,d)):
                result=self.diagnose(first,second,left,right)
                self.assertTrue(result['finite_domain_complete']);self.assertTrue(result['infinite_parameter_pairs'])
                self.assertEqual(result['evidence']['signed_radius_signs'],(1,1) if distance==1. else (-1,-1))

    def test_exact_endpoints_one_ulp_and_wrapped_partial_domains(self):
        a=EllipseArc((0,0),(2,2),0.,1.,.3)
        for start,expected in ((math.nextafter(1.,0.),'INFINITE_PARAMETER_PAIRS'),(1.,'SHARED_PARAMETER_ENDPOINT'),
                               (math.nextafter(1.,math.inf),'DISJOINT')):
            result=self.diagnose(a,replace(a,start_rad=start))
            self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['classification'],expected)
        a=replace(a,start_rad=-2.,sweep_rad=4.,rotation_rad=1.2);b=replace(a,rotation_rad=-1.2)
        result=self.diagnose(a,b)
        self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['evidence']['positive_components'],2)
        result=self.diagnose(a,b,first_interval=(0.,.1),second_interval=(.8,1.))
        self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['classification'],'DISJOINT')

    def test_budget_preserves_known_witness_and_unequal_supports_are_classified(self):
        a=EllipseArc((0,0),(2,2),0.,1.,.3)
        for start,kind in ((.5,'INFINITE_PARAMETER_PAIRS'),(1.,'SHARED_PARAMETER_ENDPOINT')):
            result=self.diagnose(a,replace(a,start_rad=start),max_series_terms=1)
            self.assertFalse(result['finite_domain_complete']);self.assertEqual(result['classification'],kind)
        result=self.diagnose(a,replace(a,rotation_rad=-.3),max_series_terms=1)
        self.assertFalse(result['finite_domain_complete']);self.assertEqual(result['classification'],'COINCIDENT_SUPPORTING_CIRCLES')
        for b in (replace(a,center_zr_m=(math.nextafter(0.,1.),0)),replace(a,semiaxes_m=(3,3)),replace(a,rotation_rad=.1)):
            result=self.diagnose(a,b)
            self.assertTrue(result['finite_domain_complete']);self.assertEqual(result['classification'],'DISJOINT')

    def test_version_two_and_one_saved_documents_keep_original_rules_and_bytes(self):
        from copy import deepcopy
        from superfish_ng.construction_diagnostics import diagnose_construction,replay_construction_diagnosis
        from superfish_ng.gui import tangent_document
        from superfish_ng.cli import main
        previous=json.loads((Path(__file__).parent/'fixtures/offset_diagnosis_v2_general.json').read_text())
        self.assertEqual(len(previous),8)
        with tempfile.TemporaryDirectory() as temporary:
            for index,old in enumerate(previous):
                self.assertEqual(old['schema_version'],2);self.assertFalse(old['diagnosis']['finite_domain_complete'])
                self.assertEqual(replay_construction_diagnosis(old),old)
                self.assertEqual(tangent_document(old,replay=True)['offset_diagnosis'],old)
                new=diagnose_construction(old['construction'])
                self.assertEqual(new['schema_version'],8);self.assertTrue(new['diagnosis']['finite_domain_complete'])
                self.assertEqual(new['construction'],old['construction']);self.assertEqual(replay_construction_diagnosis(new),new)
                changed=deepcopy(new);changed['schema_version']=2
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
        old_one=json.loads((Path(__file__).parent/'fixtures/offset_diagnosis_v1.json').read_text())
        for row in old_one:self.assertEqual(replay_construction_diagnosis(row),row)


if __name__=='__main__':unittest.main()

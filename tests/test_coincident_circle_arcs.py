# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import math
import json
from pathlib import Path
import tempfile
import unittest

from superfish_ng.coincident_circle_arcs import pi_bounds
from superfish_ng.conics import EllipseArc
from superfish_ng.offset_degeneracies import classify_offset_degeneracies


def decimal_pi():
    """Independent arithmetic-geometric-mean reference, used only in verification."""
    with localcontext() as context:
        context.prec = 120
        a, b, t, p = D(1), D(1)/D(2).sqrt(), D(1)/4, D(1)
        for _ in range(9):
            following = (a+b)/2
            b = (a*b).sqrt(); t -= p*(a-following)**2
            a = following; p *= 2
        return +(a+b)**2/(4*t)


class CoincidentCircleArcTests(unittest.TestCase):
    def diagnose(self, a, b, first=1., second=1., **kwargs):
        return classify_offset_degeneracies(a,b,first_distance_m=first,second_distance_m=second,**kwargs)

    def test_pi_enclosure_matches_independent_agm_and_exact_tangent_identity(self):
        reference = F(decimal_pi())
        for width in (F(1,2**40),F(1,2**100),F(1,2**180)):
            low,high=pi_bounds(width,96)
            self.assertLess(low,reference);self.assertLess(reference,high)
            self.assertLessEqual(high-low,width)
        twice=2*F(1,5)/(1-F(1,5)**2)
        four=2*twice/(1-twice**2)
        self.assertEqual((four-F(1,239))/(1+four*F(1,239)),1)
        with self.assertRaisesRegex(ValueError,'budget'):pi_bounds(F(1,2**100),1)
        for width,budget in ((True,96),(0,96),(F(1,100),True)):
            with self.assertRaises(ValueError):pi_bounds(width,budget)

    def test_overlap_endpoint_and_one_ulp_gap_or_overlap_are_distinct(self):
        a=EllipseArc((0,0),(2,2),0.,1.)
        for start,classification,centers in ((.5,'INFINITE_PARAMETER_PAIRS',None),(1.,'SHARED_PARAMETER_ENDPOINT',1),
                (math.nextafter(1.,0.),'INFINITE_PARAMETER_PAIRS',None),
                (math.nextafter(1.,math.inf),'DISJOINT',0),(1.5,'DISJOINT',0)):
            r=self.diagnose(a,replace(a,start_rad=start))
            self.assertEqual(r['classification'],classification);self.assertTrue(r['finite_domain_complete'])
            self.assertEqual(r['finite_center_count'],centers)
        r=self.diagnose(a,replace(a,start_rad=.5),first_interval=(0.,.25))
        self.assertEqual(r['classification'],'DISJOINT')

    def test_periodic_two_components_and_wrapped_single_overlap(self):
        a=EllipseArc((0,0),(2,2),-2.,4.)
        b=replace(a,rotation_rad=math.pi)
        r=self.diagnose(a,b)
        self.assertTrue(r['finite_domain_complete']);self.assertEqual(r['evidence']['positive_components'],2)
        self.assertEqual(r['classification'],'INFINITE_PARAMETER_PAIRS')
        a=replace(a,start_rad=3.,sweep_rad=.5)
        b=replace(a,start_rad=-3.1,sweep_rad=.3)
        r=self.diagnose(a,b)
        self.assertTrue(r['finite_domain_complete']);self.assertEqual(r['evidence']['positive_components'],1)
        self.assertTrue(r['infinite_parameter_pairs'])

    def test_exchange_orientation_scale_and_signed_offset_radius(self):
        a=EllipseArc((0,0),(2,2),-.25,.5)
        b=replace(a,start_rad=0.)
        for rotation in (0.,math.pi/2,-math.pi/2,math.pi):
            first,second=replace(a,rotation_rad=rotation),replace(b,rotation_rad=rotation)
            for x,y in ((first,second),(second,first)):
                self.assertTrue(self.diagnose(x,y)['finite_domain_complete'])
                self.assertEqual(self.diagnose(x,y)['classification'],'INFINITE_PARAMETER_PAIRS')
            reverse=replace(second,start_rad=.5,sweep_rad=-.5)
            self.assertEqual(self.diagnose(first,reverse,1.,-1.)['classification'],'INFINITE_PARAMETER_PAIRS')
        for scale in (2.**-80,1.,2.**80):
            first=replace(a,center_zr_m=(3*scale,4*scale),semiaxes_m=(2*scale,2*scale))
            second=replace(first,start_rad=0.,rotation_rad=math.pi)
            r=self.diagnose(first,second,scale,3*scale)
            self.assertTrue(r['finite_domain_complete']);self.assertTrue(r['infinite_parameter_pairs'])

    def test_binary_pi_endpoint_does_not_become_exact_period(self):
        a=EllipseArc((0,0),(2,2),0.,math.pi)
        b=EllipseArc((0,0),(2,2),0.,.5,math.pi)
        r=self.diagnose(a,b)
        self.assertEqual(r['classification'],'DISJOINT');self.assertTrue(r['finite_domain_complete'])
        a=replace(a,sweep_rad=math.nextafter(math.pi,math.inf))
        r=self.diagnose(a,b)
        self.assertEqual(r['classification'],'INFINITE_PARAMETER_PAIRS');self.assertTrue(r['finite_domain_complete'])

    def test_unequal_rotation_norm_budget_and_collapsed_center_are_distinguished(self):
        a=EllipseArc((0,0),(2,2),0.,.5)
        r=self.diagnose(a,replace(a,rotation_rad=.1))
        self.assertEqual(r['classification'],'DISJOINT');self.assertTrue(r['finite_domain_complete'])
        r=self.diagnose(a,replace(a,rotation_rad=math.pi),max_series_terms=1)
        self.assertFalse(r['finite_domain_complete'])
        r=self.diagnose(a,a,2.,2.)
        self.assertTrue(r['finite_domain_complete']);self.assertEqual(r['finite_center_count'],1)
        self.assertTrue(r['infinite_parameter_pairs'])

    def test_previous_version_one_saved_diagnoses_replay_without_silent_upgrade(self):
        from superfish_ng.construction_diagnostics import diagnose_construction,replay_construction_diagnosis
        from superfish_ng.gui import tangent_document
        from superfish_ng.cli import main
        path=Path(__file__).parent/'fixtures/offset_diagnosis_v1.json'
        previous=json.loads(path.read_text())
        self.assertEqual(len(previous),3)
        with tempfile.TemporaryDirectory() as temporary:
            for index,old in enumerate(previous):
                self.assertEqual(old['schema_version'],1)
                self.assertFalse(old['diagnosis']['finite_domain_complete'])
                self.assertEqual(replay_construction_diagnosis(old),old)
                restored=tangent_document(old,replay=True)
                self.assertEqual(restored['offset_diagnosis'],old)
                self.assertEqual(json.loads(restored['diagnosis_serialized']),old)
                new=diagnose_construction(old['construction'])
                self.assertEqual(new['schema_version'],7)
                self.assertTrue(new['diagnosis']['finite_domain_complete'])
                self.assertEqual(new['construction'],old['construction'])
                self.assertEqual(replay_construction_diagnosis(new),new)
                source=Path(temporary)/f'{index}-old.json';out=Path(temporary)/f'{index}-replayed.json'
                source.write_text(json.dumps(old,indent=2)+'\n')
                self.assertEqual(main(['diagnose-construction',str(source),'--out',str(out)]),0)
                self.assertEqual(source.read_bytes(),out.read_bytes())


if __name__=='__main__':unittest.main()

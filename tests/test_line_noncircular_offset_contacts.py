# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import itertools,json,math
from pathlib import Path
import tempfile
import unittest
from superfish_ng.conics import EllipseArc,HyperbolaArc,LineSegment,rotation_cos_sin
from superfish_ng.offset_degeneracies import _classify_offset_degeneracies_v7 as classify_offset_degeneracies


class LineNoncircularOffsetContactTests(unittest.TestCase):
    def diagnose(self,a,b,d,e=None,**controls):
        return classify_offset_degeneracies(a,b,first_distance_m=d,second_distance_m=d if e is None else e,**controls)

    def assert_count(self,result,count):
        self.assertTrue(result['finite_domain_complete'],result['reason'])
        self.assertEqual(result['finite_center_count'],count)

    def test_regular_ellipse_hyperbola_contacts_and_exact_finite_endpoints(self):
        line=LineSegment((2,0),(2,1))
        for curve in (EllipseArc((0,0),(2,1),0.,.5),HyperbolaArc((0,0),(2,1),0.,.5)):
            result=self.diagnose(curve,line,.25)
            self.assert_count(result,1);self.assertEqual(result['classification'],'SINGLE_TANGENCY')
            contact=next(r for r in result['evidence']['source_tangent_contacts'] if r['incidence_sign']==0)
            self.assertEqual(contact['center_box_zr_m'],((F(7,4),F(7,4)),(F(0),F(0))))
            self.assertEqual([r['status'] for r in contact['membership']],['START','START'])
            self.assert_count(self.diagnose(curve,line,.25,first_interval=(.1,1)),0)
            self.assert_count(self.diagnose(curve,line,.25,second_interval=(.1,1)),0)
            short=LineSegment((2,1),(2,2))
            self.assert_count(self.diagnose(curve,short,.25,second_interval=(-1,1)),1)

    def test_nonprincipal_rational_contacts_with_irrational_tangent_length(self):
        pairs=((EllipseArc((0,0),(5,2.5),0.,1.5),LineSegment((3,2),(-1,3.5)),(F(3,5),F(4,5))),
               (HyperbolaArc((0,0),(3,1.5),0.,1.5),LineSegment((5,2),(9,4.5)),(F(5,3),F(4,3))))
        for curve,line,local in pairs:
            result=self.diagnose(curve,line,.5)
            self.assert_count(result,1)
            contact=next(r for r in result['evidence']['source_tangent_contacts'] if r['incidence_sign']==0)
            self.assertEqual(contact['source_local_coefficients'],tuple((x,) for x in local))
            self.assertEqual([r['status'] for r in contact['membership']],['INTERIOR','START'])
            self.assertEqual(contact['offset_speed_factor_sign'],1)

    def test_global_extrema_and_one_ulp_separation_do_not_snap(self):
        line=LineSegment((2,-1),(2,1))
        for curve,distance,outside in ((EllipseArc((0,0),(2,1),-.5,1.),.25,math.inf),
                                       (EllipseArc((0,0),(2,1),-.5,1.),5.,-math.inf),
                                       (HyperbolaArc((0,0),(2,1),-.5,.5),.25,-math.inf)):
            result=self.diagnose(curve,line,distance);self.assert_count(result,1)
            x=math.nextafter(2.,outside)
            self.assert_count(self.diagnose(curve,LineSegment((x,-1),(x,1)),distance),0)
            x=math.nextafter(2.,-outside)
            result=self.diagnose(curve,LineSegment((x,-1),(x,1)),distance)
            self.assertFalse(result['finite_domain_complete'])
            self.assertEqual(result['evidence']['supporting_parameter_intersection_count'],2)

    def test_nonregular_cusps_and_two_source_contacts_at_one_center_are_witnesses(self):
        line=LineSegment((2,-2),(2,2))
        for curve,distance,kind in ((EllipseArc((0,0),(2,1),0.,.5),1.,'REGULAR_TANGENCY'),
                                    (EllipseArc((0,0),(2,1),0.,.5),.5,'CUSP_AT_SOURCE_TANGENCY'),
                                    (HyperbolaArc((0,0),(2,1),0.,.5),-.5,'CUSP_AT_SOURCE_TANGENCY')):
            result=self.diagnose(curve,line,distance)
            self.assertEqual(result['classification'],'TANGENCY_WITNESSES')
            self.assertFalse(result['finite_domain_complete']);self.assertIsNone(result['finite_center_count'])
            self.assertEqual(result['evidence']['tangency_witness_center_count'],1)
            contact=next(r for r in result['evidence']['source_tangent_contacts'] if r['incidence_sign']==0)
            self.assertEqual(contact['contact_kind'],kind)
        curve=EllipseArc((0,0),(2,1),-.1,3.4)
        result=self.diagnose(curve,line,2.)
        self.assertEqual(result['evidence']['same_center_contact_groups'],[[0,1]])
        self.assertEqual(result['evidence']['tangency_witness_center_count'],1)
        self.assertFalse(result['finite_domain_complete'])  # The top source point also offsets to (0,-1).

    def test_general_binary_rotations_scales_exchange_reverse_and_both_branches(self):
        for angle,scale,hyperbola,branch,exchange,reverse in itertools.product((0.,.3),(2.**-160,1.,2.**160),(False,True),(-1,1),(False,True),(False,True)):
            c,s=rotation_cos_sin(angle)
            curve=(HyperbolaArc((-2*branch*c*scale,-2*branch*s*scale),(2*scale,scale),0.,.5,branch=branch,rotation_rad=angle)
                   if hyperbola else EllipseArc((-2*c*scale,-2*s*scale),(2*scale,scale),0.,.5,angle))
            line=LineSegment((0,0),(-s*scale,c*scale))
            distance=.25*scale*(branch if hyperbola else 1)
            curves=[curve,line];distances=[distance,distance]
            if reverse:
                curves[0]=(replace(curve,start_parameter=.5,end_parameter=0.) if hyperbola
                           else replace(curve,start_rad=.5,sweep_rad=-.5))
                distances[0]*=-1
            if exchange:curves.reverse();distances.reverse()
            self.assert_count(self.diagnose(*curves,*distances),1)

    def test_budget_unknown_asymptote_and_unsupported_pairs_remain_explicit(self):
        curve=EllipseArc((0,0),(5,2.5),0.,1.5);line=LineSegment((3,2),(-1,3.5))
        result=self.diagnose(curve,line,.5,max_series_terms=1)
        self.assertFalse(result['finite_domain_complete']);self.assertEqual(result['classification'],'UNVERIFIED')
        self.assertEqual(result['evidence']['supporting_parameter_intersection_count'],1)
        hyperbola=HyperbolaArc((0,0),(2,1),-.5,.5)
        result=self.diagnose(hyperbola,LineSegment((0,0),(2,1)),.25)
        self.assertEqual(result['evidence']['support_square'],0);self.assertFalse(result['finite_domain_complete'])
        for controls in ({'max_series_terms':True},{'endpoint_width':0},{'first_interval':(-1,1)}):
            with self.assertRaises(ValueError):self.diagnose(curve,line,.5,**controls)

    def test_saved_six_and_current_preserve_rules_construction_and_cli_bytes(self):
        from superfish_ng.construction_diagnostics import diagnose_construction,replay_construction_diagnosis
        from superfish_ng.gui import tangent_document
        from superfish_ng.cli import main
        path=Path(__file__).parent/'fixtures/offset_diagnosis_v6_line_noncircular.json';raw=path.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            for index,old in enumerate(json.loads(raw)):
                self.assertEqual(old['schema_version'],6);self.assertEqual(replay_construction_diagnosis(old),old)
                new=diagnose_construction(old['construction']);self.assertEqual(new['schema_version'],13)
                self.assertEqual(new['construction'],old['construction'])
                self.assertEqual(new['diagnosis']['classification'],'FINITE_CENTERS' if index==1 else 'SINGLE_TANGENCY')
                for document in (old,new):
                    self.assertEqual(tangent_document(document,replay=True)['offset_diagnosis'],document)
                    source=Path(temporary)/f'{index}-{document["schema_version"]}.json';out=source.with_suffix('.replayed.json')
                    source.write_text(json.dumps(document,indent=2)+'\n')
                    self.assertEqual(main(['diagnose-construction',str(source),'--out',str(out)]),1 if document['diagnosis']['status']=='UNVERIFIED' else 0)
                    self.assertEqual(source.read_bytes(),out.read_bytes())
                changed=deepcopy(new);changed['schema_version']=6
                with self.assertRaises(ValueError):replay_construction_diagnosis(changed)
        self.assertEqual(path.read_bytes(),raw)


if __name__=='__main__':unittest.main()

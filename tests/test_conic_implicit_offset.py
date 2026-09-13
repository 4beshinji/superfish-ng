# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import json
import math
from pathlib import Path
import tempfile
import unittest

from superfish_ng.conics import EllipseArc, HyperbolaArc, curve_to_dict
from superfish_ng.conic_implicit_offset import classify_conic_implicit_offset
from superfish_ng.offset_degeneracies import classify_offset_degeneracies, diagnose_offsets_document

ROOT = Path(__file__).resolve().parents[1]


def request():
    return json.loads((ROOT/'examples/construction/conic_implicit_offset_request.json').read_text())


def classify(a,b,d=0.,**changes):
    settings=dict(endpoint_width=F(1,2**100),max_series_terms=96);settings.update(changes)
    return classify_conic_implicit_offset((a,b),(d,0.),((0,1),(0,1)),**settings)


class ConicImplicitOffsetTests(unittest.TestCase):
    def test_four_ellipse_intersections_satisfy_both_independent_equations(self):
        a=EllipseArc((0,0),(2,1),-3.,6.);b=EllipseArc((0,0),(1,2),-3.,6.)
        r=classify(a,b);self.assertTrue(r['complete']);self.assertEqual(r['centers'],4)
        points=[]
        for row in r['evidence']['intersections']:
            z,y=[float(sum(box)/2) for box in row['center_box_zr_m']];points.append((z,y))
            self.assertAlmostEqual(z*z,4/5,places=14);self.assertAlmostEqual(y*y,4/5,places=14)
            self.assertEqual(row['contact_kind'],'TRANSVERSE');self.assertEqual(row['original_incidence_sign'],0)
        self.assertEqual({(z>0,y>0) for z,y in points},{(False,False),(False,True),(True,False),(True,True)})
        self.assertEqual(classify_offset_degeneracies(a,b,first_distance_m=0.,second_distance_m=0.)['finite_center_count'],4)

    def test_ellipse_hyperbola_and_hyperbola_hyperbola_branches(self):
        for branch in (-1,1):
            ellipse=EllipseArc((0,0),(2,1),-3.,6.);hyper=HyperbolaArc((0,0),(1,1),-2.,2.,branch=branch)
            for a,b in ((ellipse,hyper),(hyper,ellipse)):
                r=classify(a,b);self.assertTrue(r['complete']);self.assertEqual(r['centers'],2)
                for row in r['evidence']['intersections']:
                    z,y=[float(sum(box)/2) for box in row['center_box_zr_m']]
                    self.assertEqual(z>0,branch>0);self.assertAlmostEqual(z*z,8/5,places=13);self.assertAlmostEqual(y*y,3/5,places=13)
            other=HyperbolaArc((0,0),(2,3),-2.5,2.5,branch=branch)
            r=classify(hyper,other);self.assertTrue(r['complete']);self.assertEqual(r['centers'],2)
            for row in r['evidence']['intersections']:
                z,y=[float(sum(box)/2) for box in row['center_box_zr_m']]
                self.assertAlmostEqual(z*z,32/5,places=13);self.assertAlmostEqual(y*y,27/5,places=13)
            self.assertEqual(classify(hyper,replace(other,branch=-branch))['centers'],0)

    def test_original_square_root_rejects_extraneous_candidates(self):
        a=EllipseArc((0,0),(2,1),0.,1.);b=EllipseArc((0,0),(1.75,.5),0.,1.)
        r=classify(a,b,.25);self.assertTrue(r['complete']);self.assertEqual(r['centers'],1)
        row=r['evidence']['intersections'][0]
        self.assertEqual(row['center_box_zr_m'],((F(7,4),F(7,4)),(F(0),F(0))))
        self.assertEqual(row['contact_kind'],'REGULAR_TANGENCY')
        self.assertEqual([m['status'] for m in row['membership']],['START','START'])
        # A larger target touches the opposite (outward) normal at (9/4,0),
        # while the requested inward offset remains strictly inside it.
        opposite=classify(a,EllipseArc((0,0),(2.25,1.5),0.,1.),.25)
        self.assertTrue(opposite['complete']);self.assertEqual(opposite['centers'],0)
        self.assertTrue(any('extraneous' in row['reason'] for row in opposite['evidence']['excluded']))
        reverse=classify(replace(a,start_rad=1.,sweep_rad=-1.),replace(b,start_rad=1.,sweep_rad=-1.),-.25)
        self.assertTrue(reverse['complete']);self.assertEqual(reverse['centers'],1)
        self.assertEqual([m['status'] for m in reverse['evidence']['intersections'][0]['membership']],['END','END'])

    def test_cusp_and_shared_center_keep_distinct_source_pairs(self):
        a=EllipseArc((0,0),(2,1),-.5,1.);b=EllipseArc((0,0),(1.5,.75),-.5,1.)
        cusp=classify(a,b,.5);self.assertTrue(cusp['complete']);self.assertEqual(cusp['centers'],1)
        self.assertEqual(cusp['evidence']['intersections'][0]['contact_kind'],'CUSP')
        self.assertEqual(cusp['evidence']['intersections'][0]['offset_speed_factor_sign'],0)
        shared=classify(replace(a,start_rad=-.1,sweep_rad=3.4),EllipseArc((1,0),(1,.5),-.5,1.,math.pi),2.)
        self.assertTrue(shared['complete']);self.assertEqual(shared['centers'],1)
        self.assertEqual(len(shared['evidence']['intersections']),2);self.assertEqual(shared['evidence']['same_center_groups'],[[0,1]])
        self.assertTrue(all(row['center_box_zr_m']==((F(0),F(0)),(F(0),F(0))) for row in shared['evidence']['intersections']))

    def test_domains_budgets_unsupported_scope_and_shared_support(self):
        a=EllipseArc((0,0),(2,1),-3.,6.);b=EllipseArc((0,0),(1,2),-3.,6.)
        for settings in ({'max_root_boxes':1},{'max_refinements':1},{'max_series_terms':1}):
            r=classify(a,b,**settings);self.assertFalse(r['complete']);self.assertIsNone(r['centers']);self.assertTrue(r['evidence']['unresolved'])
        for value in (True,0,-1):
            with self.assertRaises(ValueError):classify(a,b,max_root_boxes=value)
        self.assertIsNone(classify_conic_implicit_offset((a,b),(.25,.25),((0,1),(0,1)),endpoint_width=F(1,2**100),max_series_terms=96))
        identity=classify(a,replace(b,rotation_rad=math.pi/2));self.assertFalse(identity['complete']);self.assertIsNone(identity['centers'])
        self.assertTrue(all('identically zero' in row['reason'] for row in identity['evidence']['unresolved']))
        restricted=classify_offset_degeneracies(a,b,first_distance_m=0.,second_distance_m=0.,first_interval=(.5,1),second_interval=(.5,1))
        self.assertTrue(restricted['finite_domain_complete']);self.assertEqual(restricted['finite_center_count'],2)

    def test_scale_binary_rotations_reverse_and_exchange(self):
        for unit in (2.**-40,1.,2.**40):
            a=EllipseArc((0,0),(2*unit,unit),-3.,6.,.3);b=EllipseArc((0,0),(unit,2*unit),-3.,6.,.3)
            for reverse in (False,True):
                pair=[replace(c,start_rad=3.,sweep_rad=-6.) for c in (a,b)] if reverse else [a,b]
                for exchange in (False,True):
                    r=classify(*(pair[::-1] if exchange else pair));self.assertTrue(r['complete']);self.assertEqual(r['centers'],4)
                    # Apply the exact stored binary inverse rotation before checking the conics.
                    c,s=math.cos(.3),math.sin(.3);norm=c*c+s*s
                    for row in r['evidence']['intersections']:
                        z,y=[float(sum(box)/2)/unit for box in row['center_box_zr_m']]
                        x,v=(c*z+s*y)/norm,(-s*z+c*y)/norm
                        self.assertAlmostEqual(x*x,4/5,places=13);self.assertAlmostEqual(v*v,4/5,places=13)

    def test_cli_strict_requests_and_preserved_saved_version_nine(self):
        from superfish_ng.cli import main
        from superfish_ng.construction_diagnostics import diagnose_construction,replay_construction_diagnosis
        from superfish_ng.gui import tangent_document
        req=request();report=diagnose_offsets_document(req)
        self.assertEqual(report['schema_version'],12);self.assertEqual(report['diagnosis']['finite_center_count'],4)
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'request.json';out=Path(tmp)/'diagnosis.json';source.write_text(json.dumps(req)+'\n')
            self.assertEqual(main(['diagnose-offsets',str(source),'--out',str(out)]),0)
            self.assertEqual(json.loads(out.read_text()),report)
            self.assertEqual(main(['diagnose-offsets',str(source),'--out',str(out)]),2)
        for key,value in (('distance',1.),('max_root_boxes',10),('first_interval',[0,2])):
            bad=deepcopy(req);bad['controls'][key]=value
            with self.assertRaises(ValueError):diagnose_offsets_document(bad)
        raw=(ROOT/'tests/fixtures/offset_diagnosis_v9.json').read_bytes();old=json.loads(raw)
        self.assertEqual(old['schema_version'],9);self.assertEqual(replay_construction_diagnosis(old),old)
        self.assertEqual(tangent_document(old,replay=True)['offset_diagnosis'],old)
        new=diagnose_construction(old['construction']);self.assertEqual(new['schema_version'],12)
        self.assertEqual(new['construction'],old['construction']);self.assertEqual(new['diagnosis'],old['diagnosis'])
        self.assertEqual(replay_construction_diagnosis(new),new)
        bad=deepcopy(old);bad['diagnosis']['finite_center_count']=100
        with self.assertRaisesRegex(ValueError,'replay differs'):replay_construction_diagnosis(bad)
        self.assertEqual((ROOT/'tests/fixtures/offset_diagnosis_v9.json').read_bytes(),raw)


if __name__=='__main__':unittest.main()

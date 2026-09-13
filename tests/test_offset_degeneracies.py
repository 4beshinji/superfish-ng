# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from fractions import Fraction as F
import math
import unittest
from superfish_ng.conics import EllipseArc,HyperbolaArc,LineSegment
from superfish_ng.offset_degeneracies import classify_offset_degeneracies


class OffsetDegeneracyTests(unittest.TestCase):
    def diagnose(self,a,b,d=1.,e=1.,**extra):
        return classify_offset_degeneracies(a,b,first_distance_m=d,second_distance_m=e,**extra)

    def circles(self):
        return EllipseArc((0,0),(2,2),-.5,1.),EllipseArc((2,0),(2,2),-.5,1.,math.pi)

    def test_external_internal_tangency_and_no_tolerance_snapping(self):
        a,b=self.circles();r=self.diagnose(a,b)
        self.assertEqual(r['classification'],'SINGLE_TANGENCY');self.assertTrue(r['finite_domain_complete'])
        self.assertEqual(r['evidence']['center_zr_m'],(F(1),F(0)))
        self.assertEqual(r['finite_center_count'],1);self.assertFalse(r['infinite_parameter_pairs'])
        large=replace(a,semiaxes_m=(3,3));small=replace(a,center_zr_m=(1,0))
        r=self.diagnose(large,small);self.assertEqual(r['classification'],'SINGLE_TANGENCY')
        self.assertEqual(r['evidence']['center_zr_m'],(F(2),F(0)))
        self.assertEqual(self.diagnose(a,replace(b,center_zr_m=(math.nextafter(2.,math.inf),0)))['classification'],'DISJOINT')
        inside=self.diagnose(a,replace(b,center_zr_m=(math.nextafter(2.,0.),0)))
        self.assertEqual(inside['status'],'CERTIFIED');self.assertEqual(inside['finite_center_count'],2)

    def test_finite_arc_endpoint_exterior_and_budget(self):
        a,b=self.circles();a=replace(a,start_rad=0.,sweep_rad=.5)
        r=self.diagnose(a,b);self.assertEqual(r['evidence']['membership'][0]['status'],'START')
        self.assertEqual(r['classification'],'SINGLE_TANGENCY')
        a=replace(a,start_rad=.1);self.assertEqual(self.diagnose(a,b)['classification'],'DISJOINT')
        a,b=self.circles();r=self.diagnose(a,b,max_series_terms=1)
        self.assertEqual(r['status'],'UNVERIFIED');self.assertFalse(r['finite_domain_complete'])

    def test_collapsed_offsets_distinguish_centers_from_parameter_pairs(self):
        a,b=self.circles();b=replace(b,center_zr_m=(0,0))
        r=self.diagnose(a,b,2.,2.);self.assertEqual(r['classification'],'INFINITE_PARAMETER_PAIRS')
        self.assertEqual(r['finite_center_count'],1);self.assertTrue(r['finite_domain_complete'])
        self.assertEqual(self.diagnose(a,replace(b,center_zr_m=(1,0)),2.,2.)['classification'],'DISJOINT')
        b=replace(b,center_zr_m=(1,0));r=self.diagnose(a,b,2.,1.)
        self.assertTrue(r['infinite_parameter_pairs']);self.assertEqual(r['finite_center_count'],1)
        self.assertEqual(self.diagnose(a,replace(b,start_rad=.2,sweep_rad=.2),2.,1.)['classification'],'DISJOINT')

    def test_shared_ellipse_hyperbola_parameters_and_direction(self):
        for a in (EllipseArc((0,0),(2,1),0.,1.),HyperbolaArc((0,0),(2,1),0.,1.)):
            if isinstance(a,EllipseArc):
                b=replace(a,start_rad=.5,sweep_rad=1.);reverse=replace(b,start_rad=1.5,sweep_rad=-1.);end=replace(a,start_rad=1.)
            else:
                b=replace(a,start_parameter=.5,end_parameter=1.5);reverse=replace(b,start_parameter=1.5,end_parameter=.5);end=replace(a,start_parameter=1.,end_parameter=2.)
            for second,d in ((b,.25),(reverse,-.25)):
                r=self.diagnose(a,second,.25,d)
                self.assertEqual(r['classification'],'INFINITE_PARAMETER_PAIRS')
                self.assertEqual(r['evidence']['shared_parameter_interval'],(F(1,2),F(1)))
                self.assertTrue(r['finite_domain_complete'])
            r=self.diagnose(a,end,.25,.25);self.assertEqual(r['classification'],'SHARED_PARAMETER_ENDPOINT')
            self.assertEqual(r['evidence']['fraction_intervals'],[(F(1),F(1)),(F(0),F(0))])
            self.assertEqual(self.diagnose(a,reverse,.25,.25)['status'],'UNVERIFIED')

    def test_line_circle_tangent_and_finite_line_domain(self):
        circle=EllipseArc((0,0),(2,2),-.5,1.);line=LineSegment((1,-1),(1,1))
        r=self.diagnose(line,circle,0.,1.);self.assertEqual(r['classification'],'SINGLE_TANGENCY')
        self.assertEqual(r['evidence']['membership'][0]['fraction'],F(1,2))
        self.assertEqual(self.diagnose(line,circle,0.,1.,first_interval=(0.,.25))['classification'],'DISJOINT')
        short=LineSegment((1,-1),(1,-.5))
        self.assertEqual(self.diagnose(short,circle,0.,1.,first_interval=(0.,3.))['classification'],'SINGLE_TANGENCY')
        collapsed=replace(circle,center_zr_m=(1,0))
        r=self.diagnose(line,collapsed,0.,2.);self.assertTrue(r['infinite_parameter_pairs']);self.assertEqual(r['finite_center_count'],1)

    def test_parallel_line_overlap_endpoint_and_separation(self):
        a=LineSegment((0,0),(3,4));b=LineSegment((3,4),(6,8))
        self.assertEqual(self.diagnose(a,b,.5,.5)['classification'],'SHARED_PARAMETER_ENDPOINT')
        r=self.diagnose(a,b,.5,.5,first_interval=(0.,2.));self.assertTrue(r['infinite_parameter_pairs'])
        self.assertTrue(r['finite_domain_complete'])
        self.assertEqual(self.diagnose(a,b,.5,.25)['classification'],'DISJOINT')
        self.assertEqual(self.diagnose(a,b,.5,.5,first_interval=(0.,.5))['classification'],'DISJOINT')

    def test_exchange_scale_rotation_unknown_and_strict_inputs(self):
        a,b=self.circles();r=self.diagnose(b,a);self.assertEqual(r['classification'],'SINGLE_TANGENCY')
        a=replace(a,semiaxes_m=(4,4));b=replace(b,center_zr_m=(4,0),semiaxes_m=(4,4))
        r=self.diagnose(a,b,2.,2.);self.assertEqual(r['evidence']['center_zr_m'],(F(2),F(0)))
        a=replace(a,rotation_rad=.1);self.assertEqual(self.diagnose(a,b)['classification'],'DISJOINT')
        for extra in ({'first_interval':(-.1,1.)},{'max_series_terms':True},{'endpoint_width':0}):
            with self.assertRaises(ValueError):self.diagnose(a,b,**extra)
        with self.assertRaises(ValueError):self.diagnose(a,b,True)

    def test_coincident_support_with_opposite_short_arcs_is_disjoint(self):
        a=EllipseArc((0,0),(2,2),-.1,.2)
        b=replace(a,rotation_rad=math.pi)
        r=self.diagnose(a,b)
        self.assertEqual(r['classification'],'DISJOINT')
        self.assertTrue(r['finite_domain_complete']);self.assertEqual(r['finite_center_count'],0)
        self.assertFalse(r['infinite_parameter_pairs'])

    def test_cli_diagnosis_roundtrip_strict_input_unknown_and_exclusive_output(self):
        import json
        from pathlib import Path
        import tempfile
        from superfish_ng.cli import main
        from superfish_ng.conics import curve_to_dict
        from superfish_ng.offset_degeneracies import diagnose_offsets_document
        a,b=self.circles()
        request=dict(schema_version=1,curves=[curve_to_dict(c) for c in (a,b)],
                     controls=dict(first_distance_m=1.,second_distance_m=1.))
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'request.json';out=Path(tmp)/'diagnosis.json'
            source.write_text(json.dumps(request))
            self.assertEqual(main(['diagnose-offsets',str(source),'--out',str(out)]),0)
            saved=json.loads(out.read_text());self.assertEqual(diagnose_offsets_document(saved['request']),saved)
            original=out.read_bytes()
            self.assertNotEqual(main(['diagnose-offsets',str(source),'--out',str(out)]),0)
            self.assertEqual(out.read_bytes(),original)
            request['curves'][1]=curve_to_dict(replace(b,center_zr_m=(1,0),semiaxes_m=(2,1)))
            supported=diagnose_offsets_document(request)
            self.assertEqual(supported['diagnosis']['classification'],'DISJOINT')
            self.assertTrue(supported['diagnosis']['finite_domain_complete'])
            request['curves'][0]=curve_to_dict(replace(a,semiaxes_m=(3,1)))
            # An identically zero projection with opposite signed distances
            # remains explicitly unresolved after general finite-root recovery.
            request['curves'][1]=request['curves'][0].copy()
            request['controls']['second_distance_m']=-1.
            source.write_text(json.dumps(request));unknown=Path(tmp)/'unknown.json'
            self.assertEqual(main(['diagnose-offsets',str(source),'--out',str(unknown)]),1)
            self.assertEqual(json.loads(unknown.read_text())['diagnosis']['status'],'UNVERIFIED')
        request['controls']['allow_extension']=True
        with self.assertRaises(ValueError):diagnose_offsets_document(request)

if __name__=='__main__':unittest.main()

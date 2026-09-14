# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest
from superfish_ng.conics import EllipseArc,LineSegment,curve_to_dict
from superfish_ng.tangent_construction import construct_tangent_case
from superfish_ng.construction_diagnostics import diagnose_construction,replay_construction_diagnosis
from superfish_ng.gui import tangent_document

ROOT=Path(__file__).resolve().parents[1]
def tangent_request():
    r=json.loads((ROOT/'examples/construction/two_lobe_fillet_request.json').read_text())
    pair=(EllipseArc((0,0),(2,2),0.,.5),EllipseArc((2,0),(2,2),-.5,1.,math.pi))
    r['case_template']['geometry']['curves'][1:3]=[curve_to_dict(c) for c in pair]
    r['controls'].update(radius_m=1.,turn_direction=1,max_boxes=8)
    return r

class ConstructionDiagnosisTests(unittest.TestCase):
    def test_tangent_certificate_does_not_validate_a_case(self):
        request=tangent_request();construction=construct_tangent_case(request)
        self.assertEqual(construction['status'],'UNVERIFIED')
        report=diagnose_construction(construction)
        self.assertEqual(report['diagnosis']['classification'],'SINGLE_TANGENCY')
        self.assertTrue(report['diagnosis']['finite_domain_complete'])
        self.assertEqual(report['construction'],construction)
        gui=tangent_document(request)
        self.assertIsNone(gui['preview']);self.assertIsNone(gui['construction']['case'])
        self.assertEqual(gui['offset_diagnosis'],report)
        self.assertEqual(json.loads(gui['serialized']),construction)
        self.assertEqual(tangent_document(gui['diagnosis_serialized'],replay=True),gui)

    def test_extended_line_uses_the_actual_search_domain(self):
        r=tangent_request();r['schema_version']=6;r['controls']['allow_extension']=True
        r['case_template']['geometry']['curves'][1:3]=[curve_to_dict(c) for c in
            (LineSegment((2,-1),(2,-.5)),EllipseArc((0,0),(2,2),-.5,1.))]
        construction=construct_tangent_case(r);report=diagnose_construction(construction)
        self.assertEqual(report['parameter_domain_box'],construction['enumeration']['certificate']['domain_box'])
        self.assertEqual(report['diagnosis']['classification'],'SINGLE_TANGENCY')
        self.assertEqual(report['diagnosis']['evidence']['membership'][0]['fraction'],{'rational_numerator':'2','rational_denominator':'1'})
        self.assertIsNone(report['construction']['case'])

    def test_unknown_special_case_does_not_invalidate_a_built_case(self):
        from superfish_ng.construction_diagnostics import _from_replayed_construction
        request=json.loads((ROOT/'examples/construction/line_conic_fillet_request.json').read_text())
        gui=tangent_document(request,candidate_index=0)
        self.assertEqual(gui['offset_diagnosis']['diagnosis']['status'],'CERTIFIED')
        self.assertEqual(gui['construction']['status'],'CASE_VALIDATED');self.assertIsNotNone(gui['preview'])
        self.assertEqual(replay_construction_diagnosis(gui['offset_diagnosis']),gui['offset_diagnosis'])
        prior=_from_replayed_construction(gui['construction'],schema_version=4)
        self.assertEqual(prior['diagnosis']['status'],'UNVERIFIED')
        restored=tangent_document(prior,replay=True)
        self.assertEqual(restored['construction'],gui['construction']);self.assertIsNotNone(restored['preview'])
        self.assertEqual(restored['offset_diagnosis'],prior)
        legacy=json.loads((ROOT/'examples/construction/corner_fillet_request.json').read_text())
        old=tangent_document(legacy,candidate_index=0)
        self.assertIsNone(old['offset_diagnosis']);self.assertIsNone(old['diagnosis_serialized'])
        with self.assertRaisesRegex(ValueError,'offset diagnosis requires a saved version .* fillet construction'):diagnose_construction(old['construction'])

    def test_diagnosis_domain_and_construction_tampering_rejected(self):
        original=diagnose_construction(construct_tangent_case(tangent_request()))
        variants=[]
        changed=deepcopy(original);changed['diagnosis']['finite_center_count']=0;variants.append(changed)
        changed=deepcopy(original);changed['parameter_domain_box'][0][0]['rational_numerator']='1';variants.append(changed)
        changed=deepcopy(original);changed['construction']['status']='CASE_VALIDATED';variants.append(changed)
        changed=deepcopy(original);changed['schema_version']=999;variants.append(changed)
        for changed in variants:
            with self.assertRaises(ValueError):replay_construction_diagnosis(changed)
            with self.assertRaises(ValueError):tangent_document(changed,replay=True)

    def test_cli_saved_construction_and_diagnosis_replay(self):
        from superfish_ng.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'construction.json';out=Path(tmp)/'diagnosis.json';again=Path(tmp)/'again.json'
            source.write_text(json.dumps(construct_tangent_case(tangent_request())))
            self.assertEqual(main(['diagnose-construction',str(source),'--out',str(out)]),0)
            self.assertEqual(main(['diagnose-construction',str(out),'--out',str(again)]),0)
            self.assertEqual(out.read_bytes(),again.read_bytes())
            original=out.read_bytes()
            self.assertNotEqual(main(['diagnose-construction',str(source),'--out',str(out)]),0)
            self.assertEqual(out.read_bytes(),original)

if __name__=='__main__':unittest.main()

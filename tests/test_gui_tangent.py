# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import unittest
from superfish_ng.gui import tangent_document
from superfish_ng.tangent_construction import construct_tangent_case


class GuiTangentTests(unittest.TestCase):
    def request(self):
        return json.loads((Path(__file__).resolve().parents[1]/'examples/construction/capsule_request.json').read_text())

    def test_preview_selection_and_replay_share_cli_case(self):
        request = self.request()
        preview = tangent_document(json.dumps(request))
        self.assertIsNone(preview['preview'])
        self.assertEqual(preview['construction']['status'], 'CANDIDATES')
        built = tangent_document(request, candidate_index=0)
        self.assertEqual(built['construction'], construct_tangent_case(request, candidate_index=0))
        self.assertTrue(built['preview']['outline_closed'])
        self.assertEqual(built['preview']['project']['case'], built['construction']['case'])
        self.assertEqual(tangent_document(json.dumps(built['construction']), replay=True), built)
        # The response passes through browser JSON parsing; the download string
        # must retain Python's exact numeric representation for strict replay.
        transported = json.loads(json.dumps(built))
        self.assertEqual(tangent_document(transported['serialized'], replay=True), built)

    def test_duplicate_keys_unverified_and_modified_saved_case(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            tangent_document('{"schema_version":1,"schema_version":1}')
        built = tangent_document(self.request(), candidate_index=0)
        built['construction']['case']['rf']['normalization_j'] = 2.
        with self.assertRaisesRegex(ValueError, 'replay'):
            tangent_document(built['construction'], replay=True)
        request = self.request()
        request['case_template']['geometry']['curves'][2] = request['case_template']['geometry']['curves'][1]
        response = tangent_document(request)
        self.assertEqual(response['construction']['status'], 'UNVERIFIED')
        self.assertIsNone(response['preview'])

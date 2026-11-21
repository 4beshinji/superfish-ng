# SPDX-License-Identifier: Apache-2.0
"""Keep raw selection declarations strict through the real local HTTP transport."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from superfish_ng.curved_selection_transfer import transfer_curved_cell_selection
from superfish_ng.gui import create_server
from superfish_ng.project import load_document, parse_json


class CurvedSelectionChartsGuiTests(unittest.TestCase):
    def setUp(self):
        self.scope = ExitStack()
        self.addCleanup(self.scope.close)
        root = Path(self.scope.enter_context(tempfile.TemporaryDirectory()))
        self.guards = [self.scope.enter_context(patch(name, side_effect=AssertionError('geometry must not solve')))
                       for name in ('superfish_ng.solver.solve', 'superfish_ng.solver._solve',
                                    'superfish_ng.curved_solution.solve_curved', 'superfish_ng.te.solve_te')]
        self.server = create_server(root/'workspace')
        for closer in (self.server.manager.close, self.server.magnetic_access.close,
                       self.server.static_access.close, self.server.static_study_access.close,
                       self.server.server_close):
            self.scope.callback(closer)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.scope.callback(self.stop)
        self.base, self.token = self.server.launch_url.split('/#')
        examples = Path(__file__).resolve().parents[1]/'examples/curved_selection_charts'
        self.previous, self.current = [(examples/name).read_text() for name in ('old-project.json', 'new-project.json')]
        self.request = (examples/'intersects.json').read_text()

    def stop(self):
        self.server.shutdown()
        self.thread.join(timeout=10)
        self.assertFalse(self.thread.is_alive())
        for guard in self.guards:
            guard.assert_not_called()

    def call(self, data, authenticated=True):
        headers = {'Content-Type': 'application/json', 'Origin': self.base}
        if authenticated:
            headers['X-NG-Token'] = self.token
        with urlopen(Request(self.base+'/api', json.dumps(data).encode(), headers), timeout=30) as response:
            return json.load(response)

    def transfer(self, request=None, **extra):
        return dict(action='transfer-curved-selection', previous_document=self.previous,
                    current_document=self.current, request_document=request or self.request, **extra)

    def rejected(self, data, message, status=400, authenticated=True):
        with self.assertRaises(HTTPError) as caught:
            self.call(data, authenticated)
        with caught.exception as response:
            self.assertEqual(response.code, status)
            self.assertIn(message, json.load(response)['error'])

    def test_both_policies_complete_replay_and_original_v1_transport(self):
        previous, current = map(load_document, (self.previous, self.current))
        request = parse_json(self.request)
        for policy in ('intersects', 'contained'):
            with self.subTest(policy=policy):
                raw = dict(request, coverage_policy=policy)
                expected = transfer_curved_cell_selection(previous, current, raw)
                actual = self.call(self.transfer(json.dumps(raw)))
                self.assertEqual(actual, expected)
                self.assertEqual(self.call(dict(action='replay-curved-selection-transfer', document=json.dumps(actual))), expected)
        old = dict(schema_version=1, selected_cells=[0], boundary_pairing='same_curve_fractions',
                   coverage_policy='intersects', max_pair_tests=100000)
        data = self.transfer(json.dumps(old))
        data['current_document'] = self.previous
        expected = transfer_curved_cell_selection(previous, previous, old)
        self.assertEqual(self.call(data), expected)
        self.assertEqual(self.call(dict(action='replay-curved-selection-transfer', document=json.dumps(expected))), expected)
        self.assertEqual(self.call(dict(action='jobs')), [])

    def test_raw_duplicate_nonfinite_id_budget_tampering_and_transport_refusals(self):
        request = parse_json(self.request)
        self.rejected(self.transfer(self.request.replace('"schema_version": 2', '"schema_version": 2, "schema_version": 2')), 'duplicate JSON key')
        nonfinite = deepcopy(request)
        nonfinite['reference_vertices'][0][0][0] = float('nan')
        self.rejected(self.transfer(json.dumps(nonfinite)), 'finite')
        for invalid in ([False], [0.0]):
            self.rejected(self.transfer(json.dumps(dict(request, selected_cells=invalid))), 'integers')
        for key in ('max_pair_tests', 'max_triangles'):
            self.rejected(self.transfer(json.dumps(dict(request, **{key: 1}))), key)
        self.rejected(self.transfer(extra=True), 'unknown')
        self.rejected(self.transfer(), 'local session', status=403, authenticated=False)
        self.rejected(dict(self.transfer(), previous_document='{"project_version":2,"project_version":2}'), 'duplicate JSON key')
        expected = self.call(self.transfer())
        changed = deepcopy(expected)
        changed['reference_partition']['triangles'][0]['current_cell'] = True
        self.rejected(dict(action='replay-curved-selection-transfer', document=json.dumps(changed)), 'full reconstruction')
        self.assertEqual(self.call(dict(action='replay-curved-selection-transfer', document=json.dumps(expected))), expected)
        self.assertEqual(self.call(dict(action='jobs')), [])


if __name__ == '__main__':
    unittest.main()

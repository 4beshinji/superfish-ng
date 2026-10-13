# SPDX-License-Identifier: Apache-2.0
"""Strict local HTTP transport for complete boundary generation documents."""
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

from superfish_ng.gui import create_server
from superfish_ng.curved_remesh_generation import build_curved_remesh_generation
from superfish_ng.project import load_document, parse_json


class CurvedBoundaryRemeshGuiTests(unittest.TestCase):
    def setUp(self):
        self.scope = ExitStack(); self.addCleanup(self.scope.close)
        root = Path(self.scope.enter_context(tempfile.TemporaryDirectory()))
        self.guards = [self.scope.enter_context(patch(name, side_effect=AssertionError('generation must not solve')))
                       for name in ('superfish_ng.solver.solve', 'superfish_ng.solver._solve',
                                    'superfish_ng.curved_solution.solve_curved', 'superfish_ng.te.solve_te')]
        self.server = create_server(root/'workspace')
        for closer in (self.server.manager.close, self.server.magnetic_access.close,
                       self.server.static_access.close, self.server.static_study_access.close, self.server.server_close):
            self.scope.callback(closer)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.scope.callback(self.stop)
        self.base, self.token = self.server.launch_url.split('/#')
        examples = Path(__file__).resolve().parents[1]/'examples'
        self.project = (examples/'curved_boundary_remesh/nonaffine-project.json').read_text()
        self.settings = (examples/'curved_boundary_remesh/nonaffine-settings.json').read_text()
        self.old_settings = (examples/'curved_remesh_generation/settings.json').read_text()

    def stop(self):
        self.server.shutdown(); self.thread.join(timeout=10)
        self.assertFalse(self.thread.is_alive())
        for guard in self.guards:guard.assert_not_called()

    def call(self, data, authenticated=True):
        headers = {'Content-Type': 'application/json', 'Origin': self.base}
        if authenticated:headers['X-NG-Token'] = self.token
        with urlopen(Request(self.base+'/api', json.dumps(data).encode(), headers), timeout=60) as response:
            return json.load(response)

    def request(self, settings=None, **extra):
        return dict(action='generate-curved-remesh-plan', document=self.project,
                    settings_document=settings or self.settings, **extra)

    def rejected(self, data, message, status=400, authenticated=True):
        with self.assertRaises(HTTPError) as caught:self.call(data, authenticated)
        with caught.exception as response:
            self.assertEqual(response.code, status)
            self.assertIn(message, json.load(response)['error'])

    def test_complete_documents_and_legacy_bare_plan_for_both_settings_versions(self):
        for settings in (self.old_settings, self.settings):
            expected = build_curved_remesh_generation(load_document(self.project), parse_json(settings))
            self.assertEqual(self.call(self.request(settings)), expected['plan'])
            actual = self.call(self.request(settings, format='document'))
            self.assertEqual(actual, expected)
            self.assertEqual(self.call(dict(action='replay-curved-remesh-generation', document=json.dumps(actual))), expected)
        self.assertEqual(self.call(dict(action='jobs')), [])

    def test_raw_duplicate_tampered_budget_format_and_unauthenticated_refusals(self):
        self.rejected(self.request(self.settings.replace('"schema_version": 2', '"schema_version": 2,"schema_version": 2'), format='document'), 'duplicate JSON key')
        settings = parse_json(self.settings)
        self.rejected(self.request(json.dumps(dict(settings, max_boundary_edges=9)), format='document'), 'max_boundary_edges')
        self.rejected(self.request(json.dumps(dict(settings, max_chord_edge_m=float('nan')))), 'finite')
        for value in (True, None, 'partial'):
            self.rejected(self.request(format=value), 'format')
        self.rejected(self.request(unknown=1), 'unknown')
        self.rejected(self.request(), 'local session', 403, False)
        original = self.call(self.request(format='document'))
        changed = deepcopy(original); changed['validation']['prefix_triangle_counts'][-1] = 1
        self.rejected(dict(action='replay-curved-remesh-generation', document=json.dumps(changed)), 'full reconstruction')
        raw = json.dumps(original).replace('"seed_triangle_count": 8', '"seed_triangle_count": 8,"seed_triangle_count": 8')
        self.rejected(dict(action='replay-curved-remesh-generation', document=raw), 'duplicate JSON key')
        self.assertEqual(self.call(dict(action='replay-curved-remesh-generation', document=json.dumps(original))), original)
        self.assertEqual(self.call(dict(action='jobs')), [])

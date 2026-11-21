# SPDX-License-Identifier: Apache-2.0
"""Strict metadata for declared-chart selected regions, independent of FEM."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from superfish_ng.project import parse_json

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples/curved_selection_charts'


def request():
    return parse_json((EXAMPLES / 'intersects.json').read_text())


class CurvedSelectionChartsInputTests(unittest.TestCase):
    def validate(self, value):
        from superfish_ng.curved_selection_transfer import _validate_chart_request
        return _validate_chart_request(value)

    def test_examples_distinguish_metadata_from_geometric_validation(self):
        for name in ('intersects.json', 'contained.json', 'invalid-reference-boundary.json'):
            value = parse_json((EXAMPLES / name).read_text())
            before = deepcopy(value)
            with self.subTest(example=name):
                self.assertIsNone(self.validate(value))
                self.assertEqual(value, before)
        value = parse_json((EXAMPLES / 'invalid-boolean-id.json').read_text())
        with self.assertRaisesRegex(ValueError, 'selected_cells'):
            self.validate(value)

    def test_closed_schema_and_version_do_not_accept_legacy_chart_mixtures(self):
        original = request()
        for field in original:
            value = deepcopy(original)
            del value[field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                self.validate(value)
        for version in (1, 3, True, 2.0, '2', None):
            with self.subTest(version=version), self.assertRaises(ValueError):
                self.validate(dict(original, schema_version=version))
        for bad in (None, [], True, dict(original, unknown=0),
                    dict(original, boundary_pairing='same_curve_fractions'),
                    dict(original, boundary_pairing=[]),
                    dict(original, coverage_policy='nearest'),
                    dict(original, coverage_policy={})):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                self.validate(bad)

    def test_selected_ids_are_nonempty_unique_nonnegative_integers(self):
        original = request()
        for cells in ([], (), [True], [False], [0.0], [-1], [0, 0], ['0'], None, 0):
            value = dict(original, selected_cells=cells)
            before = deepcopy(value)
            with self.subTest(cells=cells), self.assertRaisesRegex(ValueError, 'selected_cells'):
                self.validate(value)
            self.assertEqual(value, before)
        # Mesh-dependent range validation belongs to the geometry stage.
        self.validate(dict(original, selected_cells=[0, 100000]))

    def test_both_resource_budgets_are_strict_positive_integers(self):
        original = request()
        for name in ('max_pair_tests', 'max_triangles'):
            for value in (True, False, 0, -1, 1.0, '1', None, []):
                with self.subTest(field=name, value=value), self.assertRaisesRegex(ValueError, name):
                    self.validate(dict(original, **{name: value}))
            self.validate(dict(original, **{name: 1}))

    def test_two_vertex_charts_require_lists_of_finite_real_pairs(self):
        original = request()
        charts = original['reference_vertices']
        bad_charts = [None, [], [charts[0]], [*charts, charts[0]], tuple(charts),
                      [tuple(charts[0]), charts[1]], [[], charts[1]],
                      [[[0, 0]], charts[1]]]
        for vertex in ([0], [0, 0, 0], (0, 0), [True, 0], [0, False],
                       ['0', 0], [None, 0], [float('nan'), 0], [0, float('inf')],
                       [float('-inf'), 0]):
            changed = deepcopy(charts)
            changed[0][0] = vertex
            bad_charts.append(changed)
        for value in bad_charts:
            with self.subTest(charts=value), self.assertRaisesRegex(ValueError, 'reference_vertices'):
                self.validate(dict(original, reference_vertices=value))
        # Large integers are finite mathematical coordinates; geometry may
        # reject their maps, but metadata must not overflow by casting them.
        changed = deepcopy(charts)
        changed[0][0] = [10**400, 0]
        self.validate(dict(original, reference_vertices=changed))

    def test_raw_nested_duplicate_keys_and_nonfinite_values_cannot_disappear(self):
        text = (EXAMPLES / 'intersects.json').read_text()
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key: schema_version'):
            parse_json(text.replace('"schema_version": 2', '"schema_version": 2, "schema_version": 2'))
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key: coordinate'):
            parse_json('{"reference_vertices": [{"coordinate": 0, "coordinate": 1}]}')
        changed = request()
        changed['reference_vertices'][0][0][0] = float('nan')
        parsed = parse_json(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, 'reference_vertices'):
            self.validate(parsed)

    def test_legacy_request_validator_retains_its_original_contract(self):
        from superfish_ng.curved_selection_transfer import _validate_request
        legacy = dict(schema_version=1, selected_cells=[0],
                      boundary_pairing='same_curve_fractions',
                      coverage_policy='intersects', max_pair_tests=100000)
        before = deepcopy(legacy)
        self.assertIsNone(_validate_request(legacy))
        self.assertEqual(legacy, before)
        with self.assertRaises(ValueError):
            self.validate(legacy)
        with self.assertRaises(ValueError):
            _validate_request(dict(legacy, reference_vertices=request()['reference_vertices']))


if __name__ == '__main__':
    unittest.main()

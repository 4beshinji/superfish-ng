# SPDX-License-Identifier: Apache-2.0
"""Strict generation metadata, separate from native geometry and size feasibility."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from superfish_ng.project import Project, parse_json

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples/curved_boundary_remesh'


def settings():
    return parse_json((EXAMPLES / 'nonaffine-settings.json').read_text())


class CurvedBoundaryRemeshInputTests(unittest.TestCase):
    def validate(self, value):
        from superfish_ng.curved_remesh_generation import validate_generation_settings
        return validate_generation_settings(value)

    def test_examples_validate_metadata_without_claiming_mesh_feasibility(self):
        for name in ('rectangle-settings', 'nonaffine-settings',
                     'reject-root-coarsening', 'reject-size-budget'):
            value = parse_json((EXAMPLES / f'{name}.json').read_text())
            before = deepcopy(value)
            with self.subTest(example=name):
                result = self.validate(value)
                self.assertEqual(result, before)
                self.assertEqual(value, before)
                self.assertIsNot(result, value)

    def test_closed_schema_policy_and_strict_version(self):
        original = settings()
        for field in original:
            value = deepcopy(original)
            del value[field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                self.validate(value)
        for version in (0, 3, True, 2.0, '2', None):
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, 'schema_version'):
                self.validate(dict(original, schema_version=version))
        for policy in ('reproject_analytic', 'fixed', True, None, [], {}):
            with self.subTest(policy=policy), self.assertRaisesRegex(ValueError, 'boundary_policy'):
                self.validate(dict(original, boundary_policy=policy))
        for value in (None, [], True, dict(original, unknown=1),
                      dict(original, source_mesh={}), dict(original, max_chord_edge_mm=1)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.validate(value)

    def test_finite_positive_sizes_and_bounded_angle(self):
        original = settings()
        for name in ('max_chord_edge_m', 'max_chord_triangle_area_m2', 'minimum_corner_angle_deg'):
            for value in (True, False, 0, -1, '1', None, [],
                          float('nan'), float('inf'), float('-inf'), 10**400):
                with self.subTest(field=name, value=value), self.assertRaisesRegex(ValueError, name):
                    self.validate(dict(original, **{name: value}))
            self.validate(dict(original, **{name: 1}))
        for value in (60, 61):
            with self.subTest(angle=value), self.assertRaisesRegex(ValueError, 'minimum_corner_angle_deg'):
                self.validate(dict(original, minimum_corner_angle_deg=value))

    def test_budgets_and_uniform_history_are_integers_with_distinct_minima(self):
        original = settings()
        for name in ('max_triangles', 'max_boundary_edges', 'max_seed_rounds', 'max_rounds',
                     'curved_refinement_levels'):
            for value in (True, False, -1, 1.0, '1', None, []):
                with self.subTest(field=name, value=value), self.assertRaisesRegex(ValueError, name):
                    self.validate(dict(original, **{name: value}))
            self.validate(dict(original, **{name: 1}))
            # Metadata does not allocate mesh resources or invent a global cap.
            self.validate(dict(original, **{name: 10**400}))
            if name == 'curved_refinement_levels':
                self.validate(dict(original, **{name: 0}))
            else:
                with self.subTest(field=name), self.assertRaisesRegex(ValueError, name):
                    self.validate(dict(original, **{name: 0}))

    def test_exactly_one_history_and_invalid_marked_choices(self):
        original = settings()
        with self.assertRaisesRegex(ValueError, 'either'):
            self.validate(dict(original, curved_refinement_steps=[dict(kind='uniform')]))
        del original['curved_refinement_levels']
        invalid = [[], (), None, [dict(kind='unknown')], [dict(kind='uniform', marked_cells=[0])]]
        for cells in ([], [True], [0.0], [-1], [0, 0], ('0',), None):
            invalid.append([dict(kind='marked', marked_cells=cells, minimum_corner_angle_deg=1)])
        for angle in (True, 0, 60, float('nan'), float('inf'), 10**400):
            invalid.append([dict(kind='marked', marked_cells=[0], minimum_corner_angle_deg=angle)])
        invalid.append([dict(kind='marked', marked_cells=[0], minimum_corner_angle_deg=1,
                             split_pattern={})])
        for history in invalid:
            with self.subTest(history=history), self.assertRaises(ValueError):
                self.validate(dict(original, curved_refinement_steps=history))

    def test_valid_mixed_frozen_history_is_copied_without_reinterpreting_ids(self):
        original = settings()
        del original['curved_refinement_levels']
        project = Project.load(EXAMPLES / 'nonaffine-project.json')
        original['curved_refinement_steps'] = project.to_dict()['case']['mesh']['curved_refinement_steps']
        before = deepcopy(original)
        result = self.validate(original)
        self.assertEqual(result, before)
        result['curved_refinement_steps'][0]['marked_cells'][0] = 12345
        result['curved_refinement_steps'][0]['split_pattern']['marked_cells'][0] = 12345
        self.assertEqual(original, before)
        # Whether the pattern belongs to the regenerated seed is checked by
        # geometry generation, never inferred from the numeric cell index.

    def test_raw_duplicate_and_nonfinite_input_is_rejected_before_generation(self):
        raw = json.dumps(settings())
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key: schema_version'):
            parse_json(raw.replace('"schema_version": 2', '"schema_version": 2, "schema_version": 2'))
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key: kind'):
            parse_json('{"curved_refinement_steps":[{"kind":"uniform","kind":"uniform"}]}')
        for value in (float('nan'), float('inf'), float('-inf')):
            parsed = parse_json(json.dumps(dict(settings(), max_chord_edge_m=value)))
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'max_chord_edge_m'):
                self.validate(parsed)

    def test_legacy_settings_keep_their_original_schema(self):
        from superfish_ng.curved_remesh_generation import _settings
        legacy = dict(settings(), schema_version=1)
        for name in ('boundary_policy', 'max_boundary_edges', 'max_seed_rounds'):
            del legacy[name]
        before = deepcopy(legacy)
        self.assertEqual(self.validate(legacy), before)
        self.assertEqual(_settings(legacy), dict(schema_version=1, source_mesh={},
                         minimum_corner_angle_deg=1., curved_refinement_levels=0))
        self.assertEqual(legacy, before)
        for name in ('boundary_policy', 'max_boundary_edges', 'max_seed_rounds'):
            with self.subTest(field=name), self.assertRaises(ValueError):
                self.validate(dict(legacy, **{name: settings()[name]}))

    def test_public_generation_still_refuses_unimplemented_v2_without_mesh_or_solve(self):
        from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
        project = Project.load(EXAMPLES / 'nonaffine-project.json')
        with patch('superfish_ng.curved_remesh_generation._boundary_case') as mesher, \
             patch('superfish_ng.solver.solve') as solve:
            with self.assertRaises(ValueError):
                generate_curved_remesh_plan(project, settings())
            mesher.assert_not_called()
            solve.assert_not_called()

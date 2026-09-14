# SPDX-License-Identifier: Apache-2.0
"""RF search must refine after a fixed local history, preserving its geometry."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

from superfish_ng import rf_optimization as engine
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.frozen_curved_refinement import freeze_curved_refinement
from superfish_ng.project import Project
from superfish_ng.surface_convergence import _refinement_sequence
from test_frozen_curved_refinement import native_space
from test_rf_optimization import request


def history_request():
    result = request()
    project = Project.from_dict(result['project'])
    project = replace(project, case=replace(project.case,
        curved_refinement_steps=(Step('marked', (0,), 1.),)))
    result['schema_version'] = 2
    result['project'] = freeze_curved_refinement(project).to_dict()
    return result


class RFOptimizationHistoryTests(unittest.TestCase):
    def test_fixed_history_is_explicit_and_version_one_remains_strict(self):
        data = history_request()
        before = deepcopy(data)
        engine.validate_optimization_request(data)
        self.assertEqual(data, before)
        old = dict(data, schema_version=1)
        with self.assertRaisesRegex(ValueError, 'history'):
            engine.validate_optimization_request(old)
        unfrozen = deepcopy(data)
        del unfrozen['project']['case']['mesh']['curved_refinement_steps'][0]['split_pattern']
        with self.assertRaisesRegex(ValueError, 'freeze-curved-refinement'):
            engine.validate_optimization_request(unfrozen)
        missing_mesh = deepcopy(data)
        del missing_mesh['project']['mesh_data']
        missing_mesh['project']['project_version'] = 1
        with self.assertRaisesRegex(ValueError, 'source mesh'):
            engine.validate_optimization_request(missing_mesh)
        for version in (True, 3):
            with self.subTest(version=version), self.assertRaises(ValueError):
                engine.validate_optimization_request(dict(data, schema_version=version))

    def test_surface_sequence_counts_uniform_suffix_and_rejects_changed_history(self):
        source = Project.from_dict(history_request()['project']).case
        prefix = source.curved_refinement_steps
        cases = [replace(source, curved_refinement_steps=prefix + (Step('uniform'),) * n)
                 for n in (1, 2, 3)]
        levels, sequence = _refinement_sequence(cases)
        self.assertEqual(levels, [1, 2, 3])
        self.assertEqual(sequence['fixed_prefix'], [step.to_dict() for step in prefix])
        self.assertEqual(sequence['kind'], 'uniform_suffix')
        variants = [
            replace(cases[-1], curved_refinement_steps=(Step('uniform'),) + prefix),
            replace(cases[-1], curved_refinement_steps=prefix + (Step('marked', (1,), 1.),)),
            replace(cases[-1], normalization_j=2.),
            cases[0],
        ]
        for changed in variants:
            with self.subTest(case=changed), self.assertRaises(ValueError):
                _refinement_sequence([cases[0], cases[1], changed])
        ordinary = Project.from_dict(request()['project']).case
        self.assertEqual(_refinement_sequence([replace(ordinary, curved_refinement_levels=n)
                                              for n in (1, 2, 3)]), ([1, 2, 3], None))

    def test_gui_preparation_preserves_explicit_request_and_source_mesh(self):
        from superfish_ng.gui_rf_optimization import rf_optimization_response
        data = history_request()
        result = rf_optimization_response(None, 'prepare-rf-optimization',
                                          dict(request=json.dumps(data)))
        self.assertEqual(result['request'], data)
        self.assertEqual(json.loads(result['serialized']), data)

    def test_changed_split_topology_records_failure_without_fem_or_objective(self):
        data = history_request()
        pattern = data['project']['case']['mesh']['curved_refinement_steps'][0]['split_pattern']
        pattern['parent_topology_sha256'] = '0' * 64
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'failed'
            with self.assertRaisesRegex(ValueError, 'topology'):
                engine.execute_rf_optimization(data, out)
            failure = json.loads((out / 'failure-001.json').read_text())
            self.assertEqual(failure['fem_calls_attempted'], 0)
            self.assertFalse(list(out.glob('checkpoint-*.json')))
            self.assertNotIn('objective', failure)
    def test_trial_refinement_follows_prefix_and_commutes_with_affine_map(self):
        data = history_request()
        source = Project.from_dict(data['project'])
        prefix = source.case.curved_refinement_steps
        before = deepcopy(data)
        initial = engine._projects(data, dict(values=[1., 1.], phase='search'))
        changed = engine._projects(data, dict(values=[1.2, .8], phase='search'))
        final = engine._projects(data, dict(values=[1.2, .8], phase='final'))
        for phase, projects, counts in [('search', changed, (0, 1, 2)),
                                        ('final', final, (1, 2, 3))]:
            for project, count in zip(projects, counts):
                with self.subTest(phase=phase, count=count):
                    self.assertEqual(project.case.curved_refinement_levels, 0)
                    self.assertEqual(project.case.curved_refinement_steps,
                                     prefix + (Step('uniform'),) * count)
        for old, new in zip(initial, changed):
            a, b = native_space(old), native_space(new)
            np.testing.assert_array_equal(a.geometry.cell_nodes, b.geometry.cell_nodes)
            np.testing.assert_array_equal(a.geometry.boundary_nodes, b.geometry.boundary_nodes)
            np.testing.assert_allclose(a.geometry.points_rz_m * [1.2, .8],
                                       b.geometry.points_rz_m, rtol=0, atol=2e-15)
        for a, b in zip(changed[1:], final[:2]):
            self.assertEqual(a.to_dict(), b.to_dict())
        self.assertEqual(data, before)


if __name__ == '__main__':
    unittest.main()

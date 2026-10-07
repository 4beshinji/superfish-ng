# SPDX-License-Identifier: Apache-2.0
"""Fixed original inputs, fresh-execution order and fail-before-FEM binding."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from superfish_ng import Case
from superfish_ng.adaptive_efficiency_plan import INPUTS, build_adaptive_efficiency_plan
from superfish_ng.adaptive_refinement import _request

ROOT = Path(__file__).resolve().parents[1]


class AdaptiveEfficiencyPlanTests(unittest.TestCase):
    def copy_inputs(self, root):
        for _, relative, _ in INPUTS:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)

    def test_original_case_physics_mesh_and_historical_controls_survive(self):
        with patch('superfish_ng.solver.solve', side_effect=AssertionError('no FEM in plan')):
            plan = build_adaptive_efficiency_plan()
        self.assertEqual(plan['new_fem_solves'], 0)
        self.assertEqual(plan['physical_acceptance_status'], 'NOT_RUN')
        for record, old_name in zip(plan['cases'][:2], ('pillbox_confirmed', 'curved_sphere_confirmed')):
            original = json.loads((ROOT / f'examples/adaptive_refinement/{old_name}.json').read_text())
            request = record['request']
            self.assertEqual(request['case'], original['case'])
            self.assertEqual(request['initial_mesh'], original['initial_mesh'])
            self.assertEqual(request['initial_ids'], original['initial_ids'])
            self.assertEqual(request['controls'], original['controls'])
            self.assertEqual(_request(request), Case.from_dict(original['case']))
            self.assertEqual(request['max_levels'], 8)
            self.assertEqual(request['max_triangles'], 250000)
        self.assertEqual(plan['cases'][0]['request']['schema_version'], 3)
        self.assertEqual(plan['cases'][1]['request']['schema_version'], 4)
        self.assertEqual(plan['comparison_limits']['r_over_q_circuit_ohm'], .005)
        self.assertEqual(plan['comparison_limits']['electric_relative_l2'], .005)

    def test_rounded_complete_case_and_source_match_original_n03_bytes(self):
        plan = build_adaptive_efficiency_plan()
        request = plan['cases'][2]['request']
        for key, relative, expected in (('case', INPUTS[2][1], INPUTS[2][2]),
                                        ('initial_mesh', INPUTS[3][1], INPUTS[3][2])):
            value = (ROOT / relative).read_bytes()
            self.assertEqual(hashlib.sha256(value).hexdigest(), expected)
            self.assertEqual(request[key], json.loads(value))
        self.assertEqual(request['initial_ids'], ['target', 'guard-2', 'guard-3'])
        self.assertEqual(request['controls']['minimum_overlap'], .98)
        case = _request(request)
        self.assertEqual(case.curved_refinement_levels, 0)
        self.assertEqual(case.curved_refinement_steps, ())
        self.assertEqual(case.quadrature_order, 12)
        self.assertIsNone(plan['cases'][2]['physical_error_bound'])

    def test_alternating_independent_repetitions_and_mutation_isolation(self):
        plan = build_adaptive_efficiency_plan()
        rows = plan['executions']
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({r['id'] for r in rows}), 12)
        for offset, case in zip((0, 4, 8), plan['cases']):
            group = rows[offset:offset+4]
            self.assertEqual([(r['repetition'], r['method']) for r in group],
                             [(1, 'uniform'), (1, 'adaptive'), (2, 'adaptive'), (2, 'uniform')])
            self.assertTrue(all(r['request'] == case['request'] for r in group))
            self.assertTrue(all(r['wall_limit_seconds'] == 3600 and
                                r['memory_limit_bytes'] == 32*1024**3 and
                                r['status'] == 'NOT_RUN' for r in group))
        before = deepcopy(plan)
        rows[0]['request']['case']['rf']['normalization_j'] = 2
        self.assertEqual(plan['cases'], before['cases'])
        self.assertEqual(rows[1:], before['executions'][1:])
        self.assertEqual(build_adaptive_efficiency_plan(), before)

    def test_changed_fixed_inputs_are_rejected_before_validation_or_fem(self):
        for _, relative, _ in INPUTS:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.copy_inputs(root)
                with (root / relative).open('ab') as stream:
                    stream.write(b' ')
                with patch('superfish_ng.adaptive_efficiency_plan.validate_adaptive_request') as validate:
                    with self.assertRaisesRegex(ValueError, 'sha256 differs.*restore'):
                        build_adaptive_efficiency_plan(base_directory=root)
                    validate.assert_not_called()

    def test_missing_or_symlink_initial_mesh_is_rejected_before_validation(self):
        for link in (False, True):
            with self.subTest(link=link), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.copy_inputs(root)
                path = root / INPUTS[3][1]
                path.unlink()
                if link:
                    path.symlink_to(ROOT / INPUTS[3][1])
                with patch('superfish_ng.adaptive_efficiency_plan.validate_adaptive_request') as validate:
                    with self.assertRaisesRegex(ValueError, 'regular file without symlinks'):
                        build_adaptive_efficiency_plan(base_directory=root)
                    validate.assert_not_called()


if __name__ == '__main__':
    unittest.main()

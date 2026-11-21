# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
from test_planar_curved import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from planar_curved_mesh_reference import restriction_chain, compare_meshes
from extend_planar_curved_mixed_refinement import mixed_specification


class PlanarCurvedMixedRefinementTests(unittest.TestCase):
    def fixture(self, root):
        source, failure = root/'original', root/'failure'
        source.mkdir(); failure.mkdir()
        names = ('validate_planar_curved_shapes.py', 'planar_curved_mesh_reference.py',
            'planar_curved_shape_reference.py', 'planar_curved_vector_reference.py',
            'validate_planar_curved_independent.py', 'validate_planar_curved_convergence.py',
            'validate_planar_curved_fem.py', 'validate_planar_curved_rf.py')
        paths = [Path(__file__).resolve().parents[1]/'scripts'/name for name in names]
        (source/'validator-hashes.json').write_text(json.dumps({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}))
        for name in ('implementation-before.json', 'implementation-after.json'):
            (source/name).write_text(json.dumps(_implementation_hashes()))
        rows = [dict(label=f'A-L{level}', patterns=['uniform']*level, passed=False) for level in range(1, 5)]
        # Only metadata preflight is tested here; these are not physical solutions.
        for row in rows:
            trial = source/row['label']; trial.mkdir()
            for name in ('case.json', 'fem-fields.npz', 'patterns.json', 'regenerated-parent-charts.npz'):
                (trial/name).write_text('metadata fixture')
        report = dict(passed=False, shape='corner', polarization='tm', scale=1,
            scope='one synthetic noncircle, fixed original P2 domain; finite A/B and last-two f/E/H/full RF',
            records=rows, accepted_A=None, accepted_B=None, new_FEM_solves=4)
        (source/'progress.json').write_text(json.dumps(rows))
        (source/'report.json').write_text(json.dumps(report))
        (failure/'previous-report.json').write_text(json.dumps(report))
        (failure/'progress.json').write_text('[]')
        (failure/'failed-evidence.json').write_text(json.dumps(dict(error='ValueError: planar geometry UNVERIFIED: max_geometry_boxes=100000000 exhausted')))
        return source, failure, report

    def test_metadata_requires_exact_prefix_and_measured_geometry_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            source, failure, report = self.fixture(Path(directory))
            accepted, original, snapshot, failed_snapshot = mixed_specification(source, failure)
            self.assertEqual(accepted, report)
            self.assertEqual(len(original.cell_nodes), 96)
            self.assertEqual(len(snapshot), 21)
            self.assertEqual(len(failed_snapshot), 3)
            (failure/'failed-evidence.json').write_text(json.dumps(dict(error='FEM did not converge')))
            with self.assertRaisesRegex(ValueError, 'strict geometry budget'):
                mixed_specification(source, failure)

    def test_completed_trial_or_wrong_physics_cannot_be_repeated_as_budget_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            source, failure, report = self.fixture(Path(directory))
            (failure/'progress.json').write_text('[{}]')
            with self.assertRaisesRegex(ValueError, 'no completed'):
                mixed_specification(source, failure)
            (failure/'progress.json').write_text('[]')
            report['polarization'] = 'te'
            (source/'report.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'corner TM'):
                mixed_specification(source, failure)

    def test_mixed_orders_preserve_original_linear_E_H_and_RF_on_different_meshes(self):
        original = patch(shift=(-.03, .01))
        a = restriction_chain(original, ('uniform', 'bisection'))
        b = restriction_chain(original, ('bisection', 'uniform'))
        self.assertNotEqual(a.domain, b.domain)
        solutions = []
        for charts in (a, b):
            solution = solve_planar_curved(PlanarCurvedCase(charts.domain, modes=2, max_geometry_boxes=100000000))
            # Known polynomial fields test the comparison, not global eigenmodes.
            solutions.append(replace(solution, coefficients=charts.domain.points_xy_m-np.array([-.03, .01]),
                frequencies_hz=np.repeat(1e10, 2)))
        for polarization in ('te', 'tm'):
            pair = [replace(s, case=replace(s.case, polarization=polarization)) for s in solutions]
            row = compare_meshes(*pair, a, b, [2])['groups'][0]
            self.assertLess(row['electric_relative_L2_difference'], 1e-12)
            self.assertLess(row['magnetic_relative_L2_difference'], 1e-12)
            self.assertLess(max(row['RF_relative_differences'].values()), 1e-11)
        self.assertEqual(a.domain.area_m2, b.domain.area_m2)
        self.assertEqual(a.domain.max_geometry_boxes, 100000000)
        self.assertEqual(b.domain.max_geometry_boxes, 100000000)


if __name__ == '__main__':
    unittest.main()

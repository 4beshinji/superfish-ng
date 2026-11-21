# SPDX-License-Identifier: Apache-2.0
"""Reuse evidence remains read-only and cannot bypass native physical checks."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
from superfish_ng.jobs import _implementation_hashes
from test_planar_curved import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from planar_curved_mesh_reference import restriction_chain
from validate_planar_curved_independent import save_solution
from extend_planar_curved_shapes import artifact_hashes, previous_specification, restore_state


class PlanarCurvedShapeExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = patch(shift=(-.03, .01))
        cls.charts = restriction_chain(cls.original, ('uniform',))
        cls.solution = solve_planar_curved(PlanarCurvedCase(cls.charts.domain, modes=2, max_geometry_boxes=100000000))

    def preflight_fixture(self, root):
        names = ('validate_planar_curved_shapes.py', 'planar_curved_mesh_reference.py',
            'planar_curved_shape_reference.py', 'planar_curved_vector_reference.py',
            'validate_planar_curved_independent.py', 'validate_planar_curved_convergence.py',
            'validate_planar_curved_fem.py', 'validate_planar_curved_rf.py')
        paths = [Path(__file__).resolve().parents[1]/'scripts'/name for name in names]
        (root/'validator-hashes.json').write_text(json.dumps({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}))
        for name in ('implementation-before.json', 'implementation-after.json'):
            (root/name).write_text(json.dumps(_implementation_hashes()))
        save_solution(root/'A-L1', self.solution, self.charts)
        row = dict(label='A-L1', patterns=['uniform'], passed=False)
        report = dict(passed=False, shape='corner', polarization='te', scale=1,
            scope='one synthetic noncircle, fixed original P2 domain; finite A/B and last-two f/E/H/full RF',
            records=[row], accepted_A=None, accepted_B=None, new_FEM_solves=1)
        (root/'report.json').write_text(json.dumps(report))
        (root/'progress.json').write_text(json.dumps([row]))
        return report

    def test_physically_restored_original_arrays_RF_and_complete_charts_are_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save_solution(root/'A-L1', self.solution, self.charts)
            before = artifact_hashes(root)
            restored, charts, _ = restore_state(root, dict(label='A-L1', patterns=['uniform']), self.original)
            np.testing.assert_array_equal(restored.coefficients, self.solution.coefficients)
            np.testing.assert_array_equal(restored.frequencies_hz, self.solution.frequencies_hz)
            self.assertEqual(charts.domain, self.charts.domain)
            from superfish_ng.planar_curved_solver import planar_curved_quantities
            self.assertEqual(planar_curved_quantities(restored), planar_curved_quantities(self.solution))
            self.assertEqual(before, artifact_hashes(root))

    def test_rehashed_frequency_and_changed_saved_charts_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save_solution(root/'A-L1', self.solution, self.charts)
            row = dict(label='A-L1', patterns=['uniform'])
            np.savez_compressed(root/'A-L1/fem-fields.npz', coefficients=self.solution.coefficients,
                frequencies_hz=self.solution.frequencies_hz*1.01)
            artifact_hashes(root)  # Fresh byte hashes cannot make a false eigenpair physical.
            with self.assertRaises(ValueError):
                restore_state(root, row, self.original)
            np.savez_compressed(root/'A-L1/fem-fields.npz', coefficients=self.solution.coefficients,
                frequencies_hz=self.solution.frequencies_hz)
            changed = self.charts.vertices.copy()
            changed[0, 0, 0] += .01
            np.savez_compressed(root/'A-L1/regenerated-parent-charts.npz', parent_cells=self.charts.parents,
                parent_reference_vertices=changed, coordinate_error_bounds_m=self.charts.coordinate_bounds_m)
            with self.assertRaisesRegex(ValueError, 'chart'):
                restore_state(root, row, self.original)

    def test_terminal_preflight_rejects_success_incomplete_code_and_nonlocal_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = self.preflight_fixture(root)
            before = artifact_hashes(root)
            previous_specification(root)  # Metadata preflight only; this patch is not the declared L.
            self.assertEqual(before, artifact_hashes(root))
            with self.assertRaises(ValueError):
                restore_state(root, report['records'][0], previous_specification(root)[1])
            changed = copy.deepcopy(report)
            changed['passed'] = True
            (root/'report.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'terminal failed'):
                previous_specification(root)
            changed = copy.deepcopy(report)
            changed['records'][0]['label'] = '../outside'
            (root/'report.json').write_text(json.dumps(changed))
            (root/'progress.json').write_text(json.dumps(changed['records']))
            with self.assertRaisesRegex(ValueError, 'local'):
                previous_specification(root)
            (root/'report.json').write_text(json.dumps(report))
            (root/'progress.json').write_text(json.dumps(report['records']))
            (root/'validator-hashes.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'complete validator'):
                previous_specification(root)

    def test_previous_artifact_snapshot_rejects_links_and_detects_new_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'native').write_text('original')
            before = artifact_hashes(root)
            (root/'new').write_text('unexpected')
            self.assertNotEqual(before, artifact_hashes(root))
            (root/'link').symlink_to(root/'native')
            with self.assertRaisesRegex(ValueError, 'symbolic'):
                artifact_hashes(root)


if __name__ == '__main__':
    unittest.main()

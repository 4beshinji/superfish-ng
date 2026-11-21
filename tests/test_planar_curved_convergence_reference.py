# SPDX-License-Identifier: Apache-2.0
"""Validator tests of independently known transfer and vector differences.

Manufactured fields here test integration/alignment, not FEM eigenpair accuracy.
The dedicated driver separately restores actual eigenpairs physically.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
from superfish_ng.planar_curved_solver import solve_planar_curved
from test_planar_curved import curved_ellipse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_planar_curved_convergence import compare_pair, verify_source
from superfish_ng.jobs import _implementation_hashes


class PlanarCurvedConvergenceReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = curved_ellipse(12)
        cls.coarse = solve_planar_curved(PlanarCurvedCase(original, modes=2))
        cls.restriction = refine_planar_curved_domain(original, max_geometry_boxes=1000000)
        cls.fine = solve_planar_curved(PlanarCurvedCase(cls.restriction.domain, modes=2,
            max_geometry_boxes=1000000))

    def transferred(self, scalar_scale=1., frequency_scale=1.):
        return replace(self.fine,
            coefficients=self.restriction.prolongation@self.coarse.coefficients*scalar_scale,
            frequencies_hz=self.coarse.frequencies_hz*frequency_scale)

    def test_original_restriction_preserves_both_vector_fields_and_all_RF(self):
        result = compare_pair(self.coarse, self.transferred(), [1, 1])
        self.assertEqual(json.loads(json.dumps(result)), result)
        for row in result['groups']:
            self.assertTrue(row['passed'])
            self.assertLess(row['electric_relative_L2_difference'], 1e-12)
            self.assertLess(row['magnetic_relative_L2_difference'], 1e-12)
            self.assertLess(max(row['RF_relative_differences'].values()), 1e-10)
        self.assertEqual(result['comparison_quadrature_order'], 10)

    def test_single_scalar_group_rotation_applies_to_E_and_H(self):
        # Two independent linear scalars at one declared frequency give an
        # exactly known two-dimensional field space. Neither scalar is offered
        # as a Helmholtz eigenfunction. Polar(H R)=R for positive H.
        xy = self.coarse.case.domain.points_xy_m-np.mean(self.coarse.case.domain.points_xy_m, axis=0)
        frequency = np.repeat(self.coarse.frequencies_hz[0], 2)
        coarse = replace(self.coarse, coefficients=xy, frequencies_hz=frequency)
        angle = .71
        rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        fine = replace(self.fine, coefficients=self.restriction.prolongation@xy@rotation,
            frequencies_hz=frequency)
        result = compare_pair(coarse, fine, [2])['groups'][0]
        np.testing.assert_allclose(result['common_scalar_rotation'], rotation, rtol=0, atol=1e-13)
        self.assertLess(result['electric_relative_L2_difference'], 1e-12)
        self.assertLess(result['magnetic_relative_L2_difference'], 1e-12)
        # RF is computed from each unmodified original rank, never from the
        # rotated vector comparisons; this test does not declare individual IDs.
        self.assertEqual(result['numerical_ranks_zero_based'], [0, 1])

    def test_frequency_error_changes_only_derived_E_and_amplitude_is_not_fitted(self):
        result = compare_pair(self.coarse, self.transferred(frequency_scale=1.03), [1, 1])
        for row in result['groups']:
            self.assertFalse(row['gates']['electric'])
            self.assertTrue(row['gates']['magnetic'])
            self.assertFalse(row['gates']['frequency'])
            self.assertAlmostEqual(row['electric_relative_L2_difference'], .03, places=11)
        result = compare_pair(self.coarse, self.transferred(scalar_scale=1.03), [1, 1])
        for row in result['groups']:
            for name in ('electric_relative_L2_difference', 'magnetic_relative_L2_difference'):
                self.assertAlmostEqual(row[name], 1-1/1.03, places=11)
            self.assertFalse(row['passed'])

    def test_rejects_changed_domain_metadata_and_incomplete_groups(self):
        for group in ([1], [0, 2], [True, 1], []):
            with self.subTest(group=group), self.assertRaisesRegex(ValueError, 'partition'):
                compare_pair(self.coarse, self.transferred(), group)
        with self.assertRaisesRegex(ValueError, 'regenerated'):
            compare_pair(self.coarse, self.coarse, [1, 1])
        with self.assertRaisesRegex(ValueError, 'conductivity'):
            compare_pair(self.coarse, replace(self.transferred(), case=replace(self.fine.case,
                conductivity_s_per_m=1e7)), [1, 1])
        for order in (True, 3, 33):
            with self.assertRaisesRegex(ValueError, 'order'):
                compare_pair(self.coarse, self.transferred(), [1, 1], quadrature_order=order)

    def test_reused_artifacts_require_complete_hashes_and_exact_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = root/'previous'
            previous.mkdir()
            hashes = _implementation_hashes()
            for name in ('implementation-before.json', 'implementation-after.json'):
                (previous/name).write_text(json.dumps(hashes))
            (previous/'case.json').write_text('preserved original bytes')
            audit = root/'audit.json'
            audit.write_text(json.dumps(dict(raw_artifact_hashes={
                str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in previous.iterdir()})))
            self.assertEqual(verify_source(previous, audit)[0], hashes)
            (previous/'case.json').write_text('changed bytes')
            with self.assertRaisesRegex(ValueError, 'artifact hashes'):
                verify_source(previous, audit)
            (previous/'implementation-after.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'implementation'):
                verify_source(previous, audit)


if __name__ == '__main__':
    unittest.main()

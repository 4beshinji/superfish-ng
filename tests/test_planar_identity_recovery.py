# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.constants import C0
from superfish_ng.planar import PlanarCase, solve_planar
from superfish_ng.planar_tracking import PlanarTrackingRequest, track_planar_modes
from superfish_ng.planar_identity_recovery import PlanarIdentityRecoveryRequest, recover_planar_modes


class PlanarIdentityRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solutions = [solve_planar(PlanarCase(w, .2, nx=6, ny=6, modes=3)) for w in (.18, .2, .22, .23)]
        cls.anchor, cls.square, cls.current, cls.next = cls.solutions
        cls.groups = [dict(indices=[1, 2], ids=['x', 'y'])]
        cls.inherited = PlanarTrackingRequest(2, 2, None, cls.groups)
        cls.comparison = PlanarTrackingRequest(2, 2, ['y', 'x'])
        for solution in cls.solutions:
            expected = sorted([C0/(2*solution.case.width_m), C0/.4])
            np.testing.assert_allclose(solution.frequencies_hz[:2], expected, rtol=1e-4)

    def recover(self, *, current=None, inherited=None, comparison=None):
        return recover_planar_modes(self.anchor, self.square, current or self.current,
            inherited or self.inherited, PlanarIdentityRecoveryRequest(0, comparison or self.comparison),
            current_snapshot_index=2)

    def test_analytic_field_identity_rank_exchange_and_following_inheritance(self):
        # Independent rectangular TE E shapes: x mode has only Ey~sin(pi*x/w),
        # y mode only Ex~sin(pi*y/h). Check actual original fields, not labels.
        for solution, names in ((self.anchor, ('y', 'x')), (self.current, ('x', 'y'))):
            cells = np.arange(len(solution.space.triangles))
            bary = np.tile([.2, .3, .5], (len(cells), 1))
            vertices = solution.space.points_xy_m[solution.space.triangles]
            points = np.einsum('nj,njk->nk', bary, vertices)
            for mode, name in enumerate(names):
                field = solution.fields_in_cells(cells, bary, mode)
                key = 'Ey_quadrature_V_per_m' if name == 'x' else 'Ex_quadrature_V_per_m'
                coordinate = points[:, 0] if name == 'x' else points[:, 1]
                length = solution.case.width_m if name == 'x' else solution.case.height_m
                expected = np.sin(np.pi*coordinate/length)
                observed = field[key]
                correlation = abs(observed@expected)/np.linalg.norm(observed)/np.linalg.norm(expected)
                self.assertGreater(correlation, .999)
        before = [(s.coefficients.copy(), s.frequencies_hz.copy()) for s in self.solutions]
        report = self.recover()
        self.assertEqual(report['inherited']['current_mode_ids'], [None, None])
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['assessment']['current_mode_ids'], ['x', 'y'])
        self.assertAlmostEqual(report['recovered_frequencies_hz']['x']/ (C0/.44), 1., delta=1e-4)
        next_result = track_planar_modes(self.current, self.next, PlanarTrackingRequest(2, 2, ['x', 'y']))
        self.assertEqual(next_result['current_mode_ids'], ['x', 'y'])
        self.assertTrue(next_result['individual_ids_complete'])
        for solution, (coefficients, frequencies) in zip(self.solutions, before):
            np.testing.assert_array_equal(solution.coefficients, coefficients)
            np.testing.assert_array_equal(solution.frequencies_hz, frequencies)

    def test_true_degeneracy_and_wrong_anchor_ids_keep_frequency_null(self):
        for options in ({'current': self.square}, {'comparison': replace(self.comparison, previous_mode_ids=['outside', 'x'])}):
            report = self.recover(**options)
            self.assertEqual(report['status'], 'UNVERIFIED')
            self.assertIsNone(report['recovered_frequencies_hz'])
            self.assertEqual(report['assessment']['current_mode_ids'], [None, None])
            self.assertEqual(report['assessment']['current_identity_groups'], self.groups)

    def test_inherited_guard_blocks_anchor_and_anchor_guard_blocks_ids(self):
        inherited = replace(self.inherited, controls=replace(self.inherited.controls, relative_cluster_gap=.9))
        with patch('superfish_ng.planar_identity_recovery.track_planar_modes', wraps=track_planar_modes) as compare:
            report = self.recover(inherited=inherited)
            self.assertEqual(compare.call_count, 1)
        self.assertEqual(report['status'], 'UNVERIFIED')
        self.assertIsNone(report['comparison']); self.assertIsNone(report['recovered_frequencies_hz'])
        comparison = replace(self.comparison, controls=replace(self.comparison.controls, relative_cluster_gap=.9))
        report = self.recover(comparison=comparison)
        self.assertEqual(report['status'], 'UNVERIFIED')
        self.assertIsNone(report['recovered_frequencies_hz'])

    def test_complete_request_indices_band_and_id_sets_are_strict(self):
        request = PlanarIdentityRecoveryRequest(0, self.comparison)
        self.assertEqual(PlanarIdentityRecoveryRequest.from_dict(request.to_dict()), request)
        for change in ({'recovery_version': True}, {'anchor_snapshot_index': True}, {'extra': 1}):
            with self.assertRaises(ValueError): PlanarIdentityRecoveryRequest.from_dict({**request.to_dict(), **change})
        with self.assertRaisesRegex(ValueError, 'resolved'):
            PlanarIdentityRecoveryRequest(0, self.inherited)
        with self.assertRaisesRegex(ValueError, 'integer >= 1'):
            recover_planar_modes(self.anchor, self.square, self.current, self.inherited, request, current_snapshot_index=0)
        with self.assertRaisesRegex(ValueError, 'precede'):
            recover_planar_modes(self.anchor, self.square, self.current, self.inherited,
                                 PlanarIdentityRecoveryRequest(1, self.comparison), current_snapshot_index=1)
        with self.assertRaisesRegex(ValueError, 'same current band'):
            self.recover(comparison=replace(self.comparison, current_mode_count=1))


if __name__ == '__main__': unittest.main()

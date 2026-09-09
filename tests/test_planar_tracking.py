# SPDX-License-Identifier: Apache-2.0
import copy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.planar import PlanarCase, solve_planar
from superfish_ng.planar_tracking import PlanarTrackingRequest, track_planar_modes
from superfish_ng.mode_tracking import track_sampled_mode_subspaces


class PlanarTrackingTests(unittest.TestCase):
    def test_strict_request_and_identity_partitions(self):
        request = PlanarTrackingRequest()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'request.json'; request.save(path)
            self.assertEqual(PlanarTrackingRequest.load(path).to_dict(), request.to_dict())
            with self.assertRaises(FileExistsError): request.save(path)
        for key, value in [('tracking_version', True), ('previous_mode_count', True),
                           ('current_mode_count', 0), ('mapping', 'same_domain'),
                           ('previous_mode_ids', ['x', 'x']), ('extra', 0)]:
            data = request.to_dict(); data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                PlanarTrackingRequest.from_dict(data)
        groups = [dict(indices=[1, 2], ids=['a', 'b'])]
        grouped = PlanarTrackingRequest(previous_mode_ids=None, previous_identity_groups=groups)
        groups[0]['ids'][0] = 'changed'
        self.assertEqual(grouped.previous_identity_groups[0]['ids'], ['a', 'b'])
        with self.assertRaises(ValueError):
            PlanarTrackingRequest(previous_identity_groups=groups)

    def test_real_electric_field_tracks_rank_crossing_on_different_meshes(self):
        a = solve_planar(PlanarCase(.18, .2, nx=6, ny=7, modes=3))
        b = solve_planar(PlanarCase(.22, .2, nx=8, ny=6, modes=3))
        result = track_planar_modes(a, b, PlanarTrackingRequest(previous_mode_ids=['cos-y', 'cos-x']))
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['current_mode_ids'], ['cos-x', 'cos-y'])
        self.assertTrue(result['individual_ids_complete'])
        self.assertLess(result['physical_mapping']['maximum_normalized_gram_discrepancy'], 1e-10)
        self.assertTrue(all(abs(m['previous_phase_multiplier']) == 1 for m in result['matches']))
        flipped = copy.deepcopy(b); flipped.coefficients *= -1
        other = track_planar_modes(a, flipped, PlanarTrackingRequest(previous_mode_ids=['cos-y', 'cos-x']))
        self.assertEqual(result['current_mode_ids'], other['current_mode_ids'])
        self.assertEqual([m['previous_phase_multiplier'] for m in result['matches']],
                         [-m['previous_phase_multiplier'] for m in other['matches']])

    def test_square_merge_retains_subspace_and_split_does_not_invent_ids(self):
        a = solve_planar(PlanarCase(.18, .2, nx=6, ny=6, modes=3))
        square = solve_planar(replace(a.case, width_m=.2))
        merged = track_planar_modes(a, square, PlanarTrackingRequest())
        self.assertEqual(merged['status'], 'PASS')
        self.assertFalse(merged['individual_ids_complete'])
        self.assertEqual(merged['current_mode_ids'], [None, None])
        self.assertEqual(merged['matches'][0]['kind'], 'SUBSPACE')
        groups = [dict(indices=m['current_indices'], ids=m['previous_ids']) for m in merged['matches']]
        b = solve_planar(replace(a.case, width_m=.22))
        split = track_planar_modes(square, b, PlanarTrackingRequest(previous_mode_ids=None, previous_identity_groups=groups))
        self.assertEqual(split['status'], 'PASS')
        self.assertFalse(split['individual_ids_complete'])
        self.assertEqual(split['matches'][0]['previous_ids'], ['mode-1', 'mode-2'])

    def test_coarse_square_splitting_guard_overlap_and_missing_guard(self):
        a = solve_planar(PlanarCase(.2, .2, 'tm', nx=4, ny=4, element_order=1, modes=4))
        request = PlanarTrackingRequest(3, 3, ['a', 'b', 'c'])
        result = track_planar_modes(a, a, request)
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertTrue(any(result['guard_overlap']))
        self.assertEqual(result['current_mode_ids'], [None]*3)
        with self.assertRaisesRegex(ValueError, 'guard mode'):
            track_planar_modes(a, a, PlanarTrackingRequest(4, 4, ['a', 'b', 'c', 'd']))

    def test_explicit_current_groups_preserve_generic_validation(self):
        args = (np.eye(2), np.eye(2), np.ones(2), [1., 2.], [1., 2.], None)
        controls = dict(comparison_description='test Euclidean basis', minimum_overlap=.9,
                        minimum_assignment_margin=.1, relative_cluster_gap=.001,
                        previous_identity_groups=[dict(indices=[1, 2], ids=['a', 'b'])])
        result = track_sampled_mode_subspaces(*args, current_frequency_groups=[[1, 2]], **controls)
        self.assertEqual(result['matches'][0]['kind'], 'SUBSPACE')
        for groups in ([[True, 2]], [[2, 1]], [[1]], [[1], []], 'all'):
            with self.assertRaises(ValueError):
                track_sampled_mode_subspaces(*args, current_frequency_groups=groups, **controls)

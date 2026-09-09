# SPDX-License-Identifier: Apache-2.0
import copy
from dataclasses import replace
import tempfile
from pathlib import Path
import unittest
import numpy as np
from superfish_ng.planar import PlanarCase, solve_planar
from superfish_ng.planar_project import PlanarProject
from superfish_ng.planar_convergence import PlanarConvergence, PlanarConvergenceThresholds
from superfish_ng.planar_convergence_compare import compare_planar_convergence
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_refinement import planar_prolongation


class PlanarConvergenceTests(unittest.TestCase):
    def request(self, **case_options):
        options = dict(nx=4, ny=3, modes=3)
        options.update(case_options)
        return PlanarConvergence(PlanarProject(PlanarCase(.31, .2, **options)))

    def test_strict_request_roundtrip_budget_and_full_geometry(self):
        request = self.request()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'convergence.json'
            request.save(path)
            self.assertEqual(PlanarConvergence.load(path).to_dict(), request.to_dict())
            with self.assertRaises(FileExistsError):
                request.save(path)
        for key, value in [('levels', 2), ('levels', True), ('levels', 10**100),
                           ('mode_ranks', [True]), ('mode_ranks', [1, 1]),
                           ('mode_ranks', []), ('mode_ranks', [4]), ('max_triangles', 383),
                           ('convergence_version', True), ('unknown', 0)]:
            data = request.to_dict()
            data[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                PlanarConvergence.from_dict(data)
        for value in (True, float('nan'), 0., 1.):
            with self.assertRaises(ValueError):
                PlanarConvergenceThresholds(minimum_overlap=value)
        projects = request.projects()
        self.assertEqual(projects[0].to_dict(), request.project.to_dict())
        for i, project in enumerate(projects[1:], 1):
            self.assertEqual(len(project.case.mesh.triangles), 24*4**i)
            self.assertEqual(project.case.to_dict()['rf'], projects[0].case.to_dict()['rf'])
            self.assertEqual(project.case.to_dict()['model'], projects[0].case.to_dict()['model'])

    def test_field_integrals_match_independent_matrix_identity(self):
        for polarization in ('te', 'tm'):
            for order in (1, 2):
                request = self.request(polarization=polarization, element_order=order)
                solutions = [solve_planar(p.case) for p in request.projects()]
                result = compare_planar_convergence(request, solutions)
                for a, b, pair in zip(solutions[:-1], solutions[1:], result['comparisons']):
                    boundary = b.case.mesh.polygon_xy_m
                    coarse = PlanarMesh.create(boundary, a.space.points_xy_m, a.space.triangles)
                    transfer = planar_prolongation(coarse, b.case.mesh, order, polarization)
                    row = pair['modes'][0]
                    x = row['coarse_phase_multiplier']*(transfer @ a.coefficients[:, 0])
                    y = b.coefficients[:, 0]
                    scalar = float(np.sqrt((x-y) @ (b.mass @ (x-y)) / (y @ (b.mass @ y))))
                    # Actual omega factors enter the transverse field; no fitted
                    # normalization or independently chosen E/H sign is used.
                    u = x/a.frequencies_hz[0]
                    v = y/b.frequencies_hz[0]
                    transverse = float(np.sqrt((u-v) @ (b.stiffness @ (u-v)) / (v @ (b.stiffness @ v))))
                    electric, magnetic = (scalar, transverse) if polarization == 'tm' else (transverse, scalar)
                    self.assertAlmostEqual(row['electric_field_relative'], electric, places=10)
                    self.assertAlmostEqual(row['magnetic_field_relative'], magnetic, places=10)
                    self.assertIsNone(row['r_over_q_accelerator_ohm'])
                    self.assertIsNone(row['r_over_q_circuit_ohm'])
                changed = copy.deepcopy(solutions)
                changed[1].coefficients *= -1
                other = compare_planar_convergence(request, changed)
                self.assertEqual(result['decisions'], other['decisions'])

    def test_degeneracy_missing_spectrum_and_mismatched_levels(self):
        request = PlanarConvergence(PlanarProject(PlanarCase(.2, .2, nx=4, ny=4, modes=3)), mode_ranks=(1, 3))
        solutions = [solve_planar(p.case) for p in request.projects()]
        result = compare_planar_convergence(request, solutions)
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertTrue(all(not d['correspondence_verified'] for d in result['decisions']))
        self.assertIn('near-degenerate', result['comparisons'][-1]['modes'][0]['reasons'][0])
        self.assertIn('upper spectral neighbor', result['comparisons'][-1]['modes'][1]['reasons'][0])
        with self.assertRaises(ValueError):
            compare_planar_convergence(request, solutions[:-1])
        wrong = copy.deepcopy(solutions)
        wrong[1].case = replace(wrong[1].case, normalization_j_per_m=2.)
        with self.assertRaisesRegex(ValueError, 'declared level case'):
            compare_planar_convergence(request, wrong)
        wrong = copy.deepcopy(solutions)
        wrong[1].space.points_xy_m *= 2
        with self.assertRaisesRegex(ValueError, 'mesh differs'):
            compare_planar_convergence(request, wrong)

    def test_discrete_splitting_cannot_resolve_physical_square_doublet(self):
        # The analytic square TM12/TM21 pair has exactly equal eigenvalues.
        # P1 diagonal triangles split it by more than the fixed gap threshold.
        request = PlanarConvergence(PlanarProject(PlanarCase(
            .2, .2, polarization='tm', nx=4, ny=4, element_order=1, modes=4)), mode_ranks=(2,))
        solutions = [solve_planar(p.case) for p in request.projects()]
        result = compare_planar_convergence(request, solutions)
        self.assertFalse(result['decisions'][0]['correspondence_verified'])
        self.assertEqual(result['status'], 'UNVERIFIED')
        last = result['comparisons'][-1]['modes'][0]
        self.assertGreater(last['minimum_spectral_gap_relative'], request.thresholds.spectral_gap_relative)
        self.assertLess(last['minimum_spectral_gap_relative'], last['required_spectral_gap_relative'])


if __name__ == '__main__':
    unittest.main()

# SPDX-License-Identifier: Apache-2.0
"""Independent original FEM energy Grams and Cartesian area transport."""
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng.constants import EPS0, MU0, TAU
from superfish_ng.planar_curved import PlanarCurvedCase, PlanarCurvedDomain
from superfish_ng.planar_curved_solver import solve_planar_curved, planar_curved_quantities
from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonDomain
from test_planar_curved import curved_ellipse


class PlanarCurvedFieldOverlapTests(unittest.TestCase):
    def test_original_energy_grams_separate_electric_and_magnetic(self):
        from superfish_ng.planar_curved_field_overlap import planar_curved_field_grams
        for polarization in ('te', 'tm'):
            case = PlanarCurvedCase(curved_ellipse(12), polarization, modes=2, quadrature_order=16)
            solution = solve_planar_curved(case)
            before = (solution.coefficients.tobytes(), solution.frequencies_hz.tobytes(),
                      [planar_curved_quantities(solution, i) for i in range(case.modes)])
            result = planar_curved_field_grams(solution, solution,
                PlanarCurvedComparisonDomain(case.domain, case.domain))
            c = solution.coefficients
            scalar = c.T@(solution.mass@c)
            omega = TAU*solution.frequencies_hz
            gradient = c.T@(solution.stiffness@c)/omega[:,None]/omega[None,:]
            expected = (gradient/EPS0**2, scalar) if polarization == 'te' else (scalar, gradient/MU0**2)
            for family, source in zip((result.electric, result.magnetic), expected):
                norm = np.sqrt(np.diag(source))
                for matrix in family:
                    self.assertLess(np.max(abs(matrix-source)/norm[:,None]/norm[None,:]), 1e-10)
                    with self.assertRaises(ValueError):matrix.setflags(write=True)
            energy = (EPS0*np.diag(result.electric[0])+MU0*np.diag(result.magnetic[0]))/4
            np.testing.assert_allclose(energy, case.normalization_j_per_m, rtol=1e-10)
            self.assertEqual(before, (solution.coefficients.tobytes(), solution.frequencies_hz.tobytes(),
                             [planar_curved_quantities(solution, i) for i in range(case.modes)]))
            self.assertEqual(result.diagnostic['mode_tracking'], 'not_performed')

    def test_scale_normalization_and_original_phase_sign(self):
        from superfish_ng.planar_curved_field_overlap import planar_curved_field_grams
        from superfish_ng.planar_curved_solver import restore_planar_curved_solution
        for polarization in ('te', 'tm'):
            base = curved_ellipse(12)
            a = solve_planar_curved(PlanarCurvedCase(base, polarization, modes=2, quadrature_order=16))
            scaled = PlanarCurvedDomain(2*base.points_xy_m, base.cell_nodes, base.boundary_nodes)
            b = solve_planar_curved(replace(a.case, domain=scaled, normalization_j_per_m=3.7))
            # Keep the original +/- phasor, with no abs() applied to Grams.
            signs = np.sign(np.sum(a.coefficients*b.coefficients, axis=0))
            b = restore_planar_curved_solution(b.case, -b.coefficients*signs, b.frequencies_hz)
            grams = planar_curved_field_grams(a, b,
                PlanarCurvedComparisonDomain(base, scaled, 'declared_quadratic'))
            np.testing.assert_allclose(b.frequencies_hz*2, a.frequencies_hz, rtol=1e-11)
            for family in (grams.electric, grams.magnetic):
                aa, ab, bb = family
                np.testing.assert_allclose(np.diag(bb)/np.diag(aa), 3.7, rtol=1e-10)
                normalized = ab/np.sqrt(np.diag(aa))[:,None]/np.sqrt(np.diag(bb))[None,:]
                np.testing.assert_allclose(normalized, -np.eye(2), rtol=0, atol=1e-10)

    def test_non_nested_constant_phasors_and_declared_area_density(self):
        from types import SimpleNamespace
        from superfish_ng.planar_curved_comparison import build_planar_curved_comparison
        from superfish_ng.planar_curved_field_overlap import _integrate_fields
        from test_planar_curved_comparison import analytic_patch
        base_a, _ = analytic_patch()
        base_b, _ = analytic_patch(stretch=(2., 3.), displacement=(0., 0.))
        a, ca = analytic_patch((.25, .25))
        b, cb = analytic_patch((.5, .25), stretch=(2., 3.), displacement=(0., 0.))
        domain = PlanarCurvedComparisonDomain(base_a, base_b, 'declared_quadratic')
        comparison = build_planar_curved_comparison(a, b, domain, previous_cells=ca, current_cells=cb)
        # Manufacture all real and quadrature phases only at the PRIVATE seam.
        # Production API rejects these test objects before their sampler runs.
        matrices = [np.arange(1., 25.).reshape(12, 2), np.arange(-8., 16.).reshape(12, 2)]
        names = [f'{field}{axis}_{phase}_{unit}' for field, unit in (('E', 'V_per_m'), ('H', 'A_per_m'))
                 for axis in 'xyz' for phase in ('real', 'quadrature')]
        def sample(matrix):
            return lambda cells, refs: {name:np.tile(values, (len(cells), 1)) for name,values in zip(names,matrix)}
        objects = [SimpleNamespace(case=SimpleNamespace(modes=2), all_fields_at_reference=sample(matrix)) for matrix in matrices]
        electric, magnetic = _integrate_fields(*objects, comparison, 6, 100000)
        area = (1/8)**2*(.5-(1/4)/6)
        for offset, family in zip((0, 6), (electric, magnetic)):
            left, right = [m[offset:offset+6] for m in matrices]
            expected = (area*left.T@left, area*np.sqrt(6)*left.T@right, 6*area*right.T@right)
            for value, target in zip(family, expected):
                np.testing.assert_allclose(value, target, rtol=3e-14, atol=1e-14)
        from superfish_ng.planar_curved_field_overlap import planar_curved_field_grams
        with self.assertRaises(ValueError):planar_curved_field_grams(*objects, domain)

    def test_independent_cell_numbering_and_original_mapped_fields(self):
        from superfish_ng.planar_curved_field_overlap import planar_curved_field_grams
        base = curved_ellipse(12)
        a = solve_planar_curved(PlanarCurvedCase(base, 'tm', modes=2, quadrature_order=16))
        reordered = PlanarCurvedDomain(base.points_xy_m, base.cell_nodes[::-1][:,[1,2,0,4,5,3]], base.boundary_nodes)
        b = solve_planar_curved(replace(a.case, domain=reordered))
        charts = [dict(base_cell=11-i, reference_vertices=[[[1,1],[0,1]],[[0,1],[1,1]],[[0,1],[0,1]]]) for i in range(12)]
        grams = planar_curved_field_grams(a, b, PlanarCurvedComparisonDomain(base, base), current_cells=charts)
        signs = np.sign(np.sum(a.coefficients*b.coefficients, axis=0))
        for aa, ab, bb in (grams.electric, grams.magnetic):
            normalized = ab/np.sqrt(np.diag(aa))[:,None]/np.sqrt(np.diag(bb))[None,:]
            np.testing.assert_allclose(normalized, np.diag(signs), rtol=0, atol=1e-10)

    def test_actual_fixed_quadratic_boundary_refinement_reproduces_sources(self):
        from fractions import Fraction as F
        from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
        from superfish_ng.planar_curved_field_overlap import planar_curved_field_grams
        base = curved_ellipse(8)
        fine = refine_planar_curved_domain(base)
        charts = [dict(base_cell=int(owner), reference_vertices=[[[F(float(v)).numerator, F(float(v)).denominator]
                  for v in point] for point in vertices])
                  for owner, vertices in zip(fine.parent_cells, fine.parent_reference_vertices)]
        for polarization in ('te', 'tm'):
            a = solve_planar_curved(PlanarCurvedCase(base, polarization, modes=2, quadrature_order=16))
            b = solve_planar_curved(replace(a.case, domain=fine.domain))
            grams = planar_curved_field_grams(a, b, PlanarCurvedComparisonDomain(base, base,
                restriction_policy='binary64_roundoff'), current_cells=charts)
            self.assertFalse(grams.diagnostic['geometry']['exact_native_restrictions'])
            self.assertLess(grams.diagnostic['maximum_source_gram_difference'], 1e-10)
            for aa, ab, bb in (grams.electric, grams.magnetic):
                norm = ab/np.sqrt(np.diag(aa))[:,None]/np.sqrt(np.diag(bb))[None,:]
                self.assertLessEqual(np.max(abs(norm)), 1+1e-10)
                self.assertGreater(abs(norm[0,0]), .8)

    def test_budget_is_cumulative_across_both_sides_and_orders(self):
        from superfish_ng.planar_curved_field_overlap import planar_curved_field_grams
        from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonBudgetExceeded
        solution = solve_planar_curved(PlanarCurvedCase(curved_ellipse(8), modes=2, quadrature_order=16))
        domain = PlanarCurvedComparisonDomain(solution.case.domain, solution.case.domain)
        # One order on both sides fits 8*2*24^2 points; both orders do not.
        with self.assertRaises(PlanarCurvedComparisonBudgetExceeded) as caught:
            planar_curved_field_grams(solution, solution, domain, max_sample_points=8*2*24**2)
        self.assertEqual(caught.exception.status, 'UNVERIFIED')
        for options in ({'max_pair_tests':7}, {'max_triangles':7}, {'max_gram_modes':1}):
            with self.assertRaises(PlanarCurvedComparisonBudgetExceeded):
                planar_curved_field_grams(solution, solution, domain, **options)
        for options in ({'quadrature_order':True}, {'quadrature_order':29}, {'quadrature_order':3},
                         {'max_sample_points':True}, {'max_gram_modes':0}):
            with self.assertRaises(ValueError):planar_curved_field_grams(solution, solution, domain, **options)

    def test_small_algebraic_residual_cannot_accept_unresolved_energy_integral(self):
        from superfish_ng.planar_curved_field_overlap import planar_curved_field_grams
        case = PlanarCurvedCase(curved_ellipse(8), 'te', modes=1, quadrature_order=4)
        solution = solve_planar_curved(case)
        self.assertLess(solution.residuals[0], 1e-12)
        with self.assertRaisesRegex(ValueError, 'original FEM E/H energy Grams'):
            planar_curved_field_grams(solution, solution, PlanarCurvedComparisonDomain(case.domain, case.domain))
        accurate = solve_planar_curved(replace(case, quadrature_order=16))
        with self.assertRaisesRegex(ValueError, 'field quadrature'):
            planar_curved_field_grams(accurate, accurate,
                PlanarCurvedComparisonDomain(case.domain, case.domain), quadrature_order=4)

    def test_rejects_forged_spectrum_arrays_geometry_and_matrices(self):
        from superfish_ng.planar_curved_field_overlap import planar_curved_field_grams
        from superfish_ng.planar_curved_solver import restore_planar_curved_solution
        solution = solve_planar_curved(PlanarCurvedCase(curved_ellipse(8), modes=2, quadrature_order=16))
        domain = PlanarCurvedComparisonDomain(solution.case.domain, solution.case.domain)
        for bad in (replace(solution, coefficients=solution.coefficients*2),
                    replace(solution, frequencies_hz=solution.frequencies_hz*1.001),
                    replace(solution, coefficients=solution.coefficients.astype('float32')),
                    replace(solution, stiffness=solution.stiffness*1.001),
                    replace(solution, mass=solution.mass*1.001),
                    replace(solution, free_dofs=solution.free_dofs[::-1]),
                    replace(solution, residuals=solution.residuals+1),
                    replace(solution, orthogonality_error=1.)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                planar_curved_field_grams(solution, bad, domain)
        shifted = restore_planar_curved_solution(replace(solution.case, modes=1), solution.coefficients[:,:1], solution.frequencies_hz[:1])
        # Valid reconstruction from a strided column must survive immutable
        # replay even if the derived BLAS orthogonality changes a last bit.
        from superfish_ng.planar_curved_field_overlap import verified_planar_curved_solution
        replay = verified_planar_curved_solution(shifted)
        self.assertEqual(replay.coefficients.tobytes(), shifted.coefficients.tobytes())
        # Reject a valid higher band passed as the lowest single mode.
        bad = replace(shifted, coefficients=solution.coefficients[:,1:2], frequencies_hz=solution.frequencies_hz[1:2])
        with self.assertRaisesRegex(ValueError, 'lowest positive'):
            planar_curved_field_grams(shifted, bad, domain)
        tm = solve_planar_curved(replace(solution.case, polarization='tm'))
        with self.assertRaisesRegex(ValueError, 'TE and TM'):
            planar_curved_field_grams(solution, tm, domain)


if __name__ == '__main__':unittest.main()

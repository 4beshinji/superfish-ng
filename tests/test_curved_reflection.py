# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import math
import unittest
import numpy as np
from superfish_ng import Case
from superfish_ng.conics import LineSegment, EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.mesh import make_mesh
from superfish_ng.curved_space import case_curved_space
from superfish_ng.curved_reflection import reflect_curved_space
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.curved_solution import solve_curved


def half_case(side, tag, level=0):
    axis = LineSegment((0., 0.), (.1, 0.))
    if side == 'z_min':
        curves = (axis, EllipseArc((0., 0.), (.1, .08), 0., math.pi/2), LineSegment((0., .08), (0., 0.)))
        tags = ('axis', 'pec', tag)
    else:
        curves = (axis, LineSegment((.1, 0.), (.1, .08)), EllipseArc((.1, 0.), (.1, .08), math.pi/2, math.pi/2))
        tags = ('axis', tag, 'pec')
    return Case((), curved_contour=CurvedContour(curves, tags, 1e-14),
                curve_chord_tolerance_m=.002, contour_mesh=ContourMeshControls(.04),
                element_order=2, geometry_order=2, quadrature_order=12,
                curved_refinement_levels=level, modes=1)


class CurvedReflectionTests(unittest.TestCase):
    def test_fixed_maps_gradients_energy_and_curve_ancestry(self):
        for side in ('z_min', 'z_max'):
            for tag in ('electric_symmetry', 'magnetic_symmetry'):
                with self.subTest(side=side, tag=tag):
                    case = half_case(side, tag, level=1)
                    parent = case_curved_space(case, make_mesh(case))
                    reflection = reflect_curved_space(case, parent)
                    full = reflection.space
                    g, f = parent.geometry, full.geometry
                    self.assertEqual(len(f.cell_nodes), 2*len(g.cell_nodes))
                    self.assertEqual(set(full.boundary_tags), {'axis', 'pec'})
                    self.assertEqual(len(full.constrained_dofs), 0)
                    self.assertEqual(full.edge_check['status'], 'PASS')
                    u = np.random.default_rng(193).normal(size=len(g.points_rz_m))
                    u[parent.constrained_dofs] = 0
                    v = reflection.apply(u)
                    q = np.array([[.2, .3], [.1, .1]])
                    for i, mapping in enumerate(g.local_maps):
                        a = mapping.evaluate(q)
                        b = f.local_maps[i+len(g.cell_nodes)].evaluate(q[:, ::-1])
                        expected = a['points_rz_m'].copy()
                        expected[:, 1] = (case.length if side == 'z_min' else 2*case.length)-expected[:, 1]
                        np.testing.assert_allclose(b['points_rz_m'], expected, atol=1e-16)
                        av = u[g.cell_nodes[i]]
                        bv = v[f.cell_nodes[i+len(g.cell_nodes)]]
                        np.testing.assert_allclose(b['basis_values']@bv, reflection.parity*(a['basis_values']@av), atol=1e-13)
                        ag = np.einsum('qia,i->qa', a['basis_gradients'], av)
                        bg = np.einsum('qia,i->qa', b['basis_gradients'], bv)
                        np.testing.assert_allclose(bg, reflection.parity*ag*[1, -1], atol=1e-9, rtol=1e-10)
                    for a, b in zip(assemble_curved(parent, quadrature_order=12), assemble_curved(full, quadrature_order=12)):
                        self.assertLess(abs(float(v@(b@v))/(2*float(u@(a@u)))-1), 1e-10)
                        free = np.setdiff1d(np.arange(len(u)), parent.constrained_dofs)
                        transfer = reflection.coefficient_map[:, free]
                        expected = 2*a[free][:, free]
                        difference = transfer.T@b@transfer-expected
                        self.assertLess(np.linalg.norm(difference.data)/np.linalg.norm(expected.data), 1e-10)
                    # Refined boundary nodes are not reprojected: compare their analytic ancestry instead.
                    kept = parent.boundary_tags != tag
                    count = np.count_nonzero(kept)
                    for index in range(count):
                        owner = int(g.boundary_curve_indices[kept][index])
                        t = float(g.boundary_parameters[kept][index, 0])
                        p = case.curved_contour.curves[owner].evaluate(t)['points_zr_m'].copy()
                        p[0] = (case.length if side == 'z_min' else 2*case.length)-p[0]
                        full_owner = int(f.boundary_curve_indices[count+index])
                        full_t = float(f.boundary_parameters[count+index, 1])
                        actual = reflection.reflected_contour.curves[full_owner].evaluate(full_t)['points_zr_m']
                        np.testing.assert_allclose(actual, p, atol=1e-15)

    def test_eigenmode_full_equations_without_resolve(self):
        for tag in ('electric_symmetry', 'magnetic_symmetry'):
            case = half_case('z_min', tag)
            solution = solve_curved(case)
            reflection = reflect_curved_space(case, solution.space)
            u = reflection.apply(solution.u)
            k, m = assemble_curved(reflection.space, quadrature_order=12)
            ku, mu = k@u, m@u
            residual = np.linalg.norm(ku-mu*solution.eigenvalues)/(np.linalg.norm(ku)+solution.eigenvalues[0]*np.linalg.norm(mu))
            self.assertLess(residual, 1e-7)

    def test_invalid_seam_rejected(self):
        case = half_case('z_min', 'electric_symmetry')
        space = case_curved_space(case, make_mesh(case))
        wrong = replace(space, boundary_tags=np.where(space.boundary_tags == 'electric_symmetry', 'pec', space.boundary_tags))
        with self.assertRaisesRegex(ValueError, 'seam'):
            reflect_curved_space(case, wrong)
        with self.assertRaisesRegex(ValueError, 'CurvedSpace'):
            reflect_curved_space(case, None)

    def test_odd_coefficients_and_displaced_seam_rejected(self):
        case = half_case('z_max', 'magnetic_symmetry', 1)
        space = case_curved_space(case, make_mesh(case))
        reflection = reflect_curved_space(case, space)
        with self.assertRaisesRegex(ValueError, 'zero u'):
            reflection.apply(np.ones(len(space.geometry.points_rz_m)))
        with self.assertRaisesRegex(ValueError, 'matching node'):
            reflection.apply(np.zeros(1))
        points = space.geometry.points_rz_m.copy()
        points[reflection.seam_dofs[0], 1] -= 1e-8
        wrong = replace(space, geometry=replace(space.geometry, points_rz_m=points))
        with self.assertRaisesRegex(ValueError, 'seam'):
            reflect_curved_space(case, wrong)

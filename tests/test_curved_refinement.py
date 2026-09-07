# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import unittest
import numpy as np
from superfish_ng import Case
from superfish_ng.mesh import make_mesh
from superfish_ng.curved_space import curved_space
from superfish_ng.curved_refinement import refine_curved_space
from superfish_ng.curved_fem import assemble_curved


class CurvedRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = Case.load(Path(__file__).resolve().parents[1]/'examples/curved_ellipse.json')
        cls.parent = curved_space(cls.case, make_mesh(cls.case))
        cls.refinement = refine_curved_space(cls.parent)

    def test_maps_fields_and_gradients_are_restrictions(self):
        parent = self.parent.geometry
        result = self.refinement
        child = result.space.geometry
        self.assertEqual(len(child.cell_nodes), 4*len(parent.cell_nodes))
        self.assertEqual(result.space.edge_check['status'], 'PASS')
        u = np.random.default_rng(20260908).normal(size=len(parent.points_rz_m))
        fine_u = result.prolongation@u
        q = np.array([[.2, .3], [.1, .1], [0., 0.]])
        for i, mapping in enumerate(child.local_maps):
            vertices = result.parent_reference_vertices[i]
            parent_q = vertices[0]+q@(vertices[1:]-vertices[0])
            parent_index = result.parent_cells[i]
            a = parent.local_maps[parent_index].evaluate(parent_q)
            b = mapping.evaluate(q)
            np.testing.assert_allclose(a['points_rz_m'], b['points_rz_m'], atol=1e-16, rtol=1e-13)
            coarse = u[parent.cell_nodes[parent_index]]
            fine = fine_u[child.cell_nodes[i]]
            np.testing.assert_allclose(a['basis_values']@coarse, b['basis_values']@fine, atol=1e-13)
            np.testing.assert_allclose(np.einsum('qia,i->qa', a['basis_gradients'], coarse),
                                       np.einsum('qia,i->qa', b['basis_gradients'], fine),
                                       atol=1e-9, rtol=1e-10)
        self.assertTrue(np.all(child.points_rz_m[result.space.axis_dofs, 0] == 0))
        self.assertFalse(child.points_rz_m.flags.writeable)

    def test_galerkin_energy_identity_on_fixed_geometry(self):
        prolongation = self.refinement.prolongation
        coarse = assemble_curved(self.parent, quadrature_order=12)
        fine = assemble_curved(self.refinement.space, quadrature_order=12)
        for a, b in zip(coarse, fine):
            restriction = prolongation.T@b@prolongation
            relative = np.linalg.norm((restriction-a).data)/np.linalg.norm(a.data)
            self.assertLess(relative, 1e-10)

    def test_boundary_is_parent_quadratic_not_reprojected_analytic_curve(self):
        parent = self.parent.geometry
        child = self.refinement.space.geometry
        # The first child midpoint is the parent edge at t=1/4.
        shape = np.array([.375, -.125, .75])
        expected = np.einsum('i,eia->ea', shape, parent.points_rz_m[parent.boundary_nodes])
        np.testing.assert_allclose(child.points_rz_m[child.boundary_nodes[::2, 2]], expected, atol=1e-16)
        np.testing.assert_array_equal(child.boundary_curve_indices, np.repeat(parent.boundary_curve_indices, 2))
        np.testing.assert_array_equal(child.boundary_parameters[::2, 0], parent.boundary_parameters[:, 0])
        np.testing.assert_array_equal(child.boundary_parameters[1::2, 1], parent.boundary_parameters[:, 1])
        analytic = np.array([self.case.curved_contour.curves[int(owner)].evaluate(float((3*lo+hi)/4))['points_zr_m'][::-1]
                             for owner, (lo, hi) in zip(parent.boundary_curve_indices, parent.boundary_parameters)])
        self.assertGreater(np.max(np.linalg.norm(expected-analytic, axis=1)), 1e-12)
        with self.assertRaisesRegex(ValueError, 'CurvedSpace'):
            refine_curved_space(None)

    def test_repeated_refinement_preserves_axis_and_symmetry_constraints(self):
        from superfish_ng.conics import LineSegment
        from superfish_ng.curved_contour import CurvedContour
        from superfish_ng.mesh_controls import ContourMeshControls
        vertices = ((0., 0.), (.1, 0.), (.1, .08), (0., .08))
        case = Case((), curved_contour=CurvedContour(tuple(LineSegment(vertices[i], vertices[(i+1)%4])
                    for i in range(4)), ('axis', 'pec', 'pec', 'magnetic_symmetry'), 0.),
                    curve_chord_tolerance_m=.001, contour_mesh=ContourMeshControls(.05),
                    element_order=2, modes=1)
        parent = curved_space(case, make_mesh(case))
        coefficients = np.ones(len(parent.geometry.points_rz_m))
        coefficients[parent.constrained_dofs] = 0
        for _ in range(2):
            refined = refine_curved_space(parent)
            coefficients = refined.prolongation@coefficients
            parent = refined.space
            self.assertTrue(np.all(coefficients[parent.constrained_dofs] == 0))
            self.assertTrue(np.all(parent.geometry.points_rz_m[parent.axis_dofs, 0] == 0))

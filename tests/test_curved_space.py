# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from superfish_ng import Case
from superfish_ng.conics import LineSegment
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.mesh import make_mesh
from superfish_ng.high_order import quadratic_space,assemble_p2
from superfish_ng.curved_space import curved_space,check_curved_edges
from superfish_ng.curved_fem import assemble_curved


class CurvedSpaceTests(unittest.TestCase):
    def case(self,tag='pec'):
        vertices = ((0.,0.),(.1,0.),(.1,.08),(0.,.08))
        curves = tuple(LineSegment(vertices[i],vertices[(i+1)%4]) for i in range(4))
        return Case((),curved_contour=CurvedContour(curves,('axis','pec','pec',tag),0.),
                    curve_chord_tolerance_m=.001,contour_mesh=ContourMeshControls(.05),element_order=2,modes=1)

    def test_global_affine_reduction_and_symmetry_constraints(self):
        case = self.case('magnetic_symmetry')
        mesh = make_mesh(case)
        space = curved_space(case,mesh)
        straight = quadratic_space(mesh)
        np.testing.assert_array_equal(space.geometry.points_rz_m,straight.dof_points)
        np.testing.assert_array_equal(space.geometry.cell_nodes,straight.cell_dofs)
        np.testing.assert_array_equal(space.axis_dofs,straight.axis_dofs)
        np.testing.assert_array_equal(space.constrained_dofs,
                                     np.unique(straight.boundary_dofs[mesh.boundary_tags=='magnetic_symmetry']))
        for mapped,affine in zip(assemble_curved(space),assemble_p2(straight)):
            np.testing.assert_allclose(mapped.toarray(),affine.toarray(),rtol=1e-11,atol=1e-15)
        self.assertEqual(space.edge_check['euler_characteristic'],1)

    def test_corrupted_sharing_boundary_and_orientation_are_rejected(self):
        case = self.case()
        space = curved_space(case,make_mesh(case))
        g = space.geometry
        bad = g.cell_nodes.copy()
        bad[0,3] = bad[1,4]
        with self.assertRaises(ValueError):
            check_curved_edges(g.points_rz_m,bad,g.boundary_nodes)
        with self.assertRaisesRegex(ValueError,'boundary'):
            check_curved_edges(g.points_rz_m,g.cell_nodes,g.boundary_nodes[:-1])
        bad = g.cell_nodes.copy()
        bad[0] = bad[0,[0,2,1,5,4,3]]
        with self.assertRaisesRegex(ValueError,'orientations'):
            check_curved_edges(g.points_rz_m,bad,g.boundary_nodes)

    def test_internal_curve_crossing_is_rejected(self):
        case = self.case()
        space = curved_space(case,make_mesh(case))
        g = space.geometry
        boundary_midpoints = set(g.boundary_nodes[:,2])
        interior = next(int(n) for n in g.cell_nodes[:,3:].ravel() if n not in boundary_midpoints)
        points = g.points_rz_m.copy()
        points[interior] = [1.,1.]  # Curves cross other edges, source topology unchanged.
        with self.assertRaises(ValueError):
            check_curved_edges(points,g.cell_nodes,g.boundary_nodes)

# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_fem import planar_curved_matrices
from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
from test_planar_curved import patch, curved_ellipse


class PlanarCurvedRefinementTests(unittest.TestCase):
    def test_exact_parent_coverage_and_bounded_original_map_restrictions(self):
        for pattern in ('uniform','bisection'):
            original=curved_ellipse(12)
            result=refine_planar_curved_domain(original,pattern=pattern,max_geometry_boxes=1000000)
            self.assertEqual(len(result.domain.boundary_nodes),len(original.boundary_nodes)*2)
            self.assertLess(abs(result.domain.area_m2/original.area_m2-1),1e-12)
            self.assertLess(result.maximum_relative_coordinate_bound,512*np.finfo(float).eps)
            vertices=result.parent_reference_vertices
            jac=np.stack((vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]),axis=2)
            determinants=np.linalg.det(jac)
            self.assertTrue(np.all(determinants>0))
            for parent in range(len(original.cell_nodes)):
                self.assertEqual(float(np.sum(determinants[result.parent_cells==parent])),1.)
            ref=np.array([[.2,.3],[.1,.6]])
            for cell,parent in enumerate(result.parent_cells):
                vertices=result.parent_reference_vertices[cell]
                parent_ref=vertices[0]+ref@(vertices[1:]-vertices[0])
                expected=original.elements[parent].evaluate(parent_ref)['points_xy_m']
                actual=result.domain.elements[cell].evaluate(ref)['points_xy_m']
                padding=64*np.finfo(float).eps*np.max(abs(original.points_xy_m))
                self.assertTrue(np.all(abs(actual-expected)<=result.coordinate_error_bounds_m[cell]+padding))
            # Source boundary points remain the original quadratic restrictions,
            # not new points reprojected to the generating true ellipse.
            for name in ('points_xy_m','cell_nodes','boundary_nodes'):
                with self.assertRaises(ValueError):getattr(result.domain,name).setflags(write=True)

    def test_coarse_scalar_mass_stiffness_and_linear_fields_preserved(self):
        for pattern in ('uniform','bisection'):
            original=curved_ellipse(12)
            coarse=PlanarCurvedCase(original,modes=1,quadrature_order=12)
            _,k,m,_=planar_curved_matrices(coarse)
            refined=refine_planar_curved_domain(original,pattern=pattern,max_geometry_boxes=1000000)
            case=PlanarCurvedCase(refined.domain,modes=1,quadrature_order=12,max_geometry_boxes=1000000)
            _,kk,mm,_=planar_curved_matrices(case)
            p=refined.prolongation
            for a,b,tol in [(p.T@mm@p,m,1e-12),(p.T@kk@p,k,1e-10)]:
                self.assertLess(np.linalg.norm((a-b).toarray())/np.linalg.norm(b.toarray()),tol)
            np.testing.assert_array_equal(p@np.ones(len(original.points_xy_m)),np.ones(len(refined.domain.points_xy_m)))
            np.testing.assert_allclose(p@original.points_xy_m,refined.domain.points_xy_m,rtol=0,atol=1e-16)
            # The two closed refinement patterns have different internal FEM
            # triangulations; comparison must use the original reference maps.
            self.assertGreater(len(refined.domain.cell_nodes),len(original.cell_nodes))

    def test_refinement_never_accepts_unknown_pattern_or_exhausted_budget(self):
        original=patch()
        with self.assertRaises(ValueError):refine_planar_curved_domain(original,pattern='circle_projection')
        for budget in (True,0,100000001):
            with self.assertRaises(ValueError):refine_planar_curved_domain(original,max_geometry_boxes=budget)
        with self.assertRaisesRegex(ValueError,'budget|exhausted'):
            refine_planar_curved_domain(original,max_geometry_boxes=1)
        first=refine_planar_curved_domain(original,max_geometry_boxes=1000000)
        second=refine_planar_curved_domain(first.domain,max_geometry_boxes=1000000)
        self.assertEqual(len(second.domain.cell_nodes),16)
        self.assertLess(abs(second.domain.area_m2/original.area_m2-1),1e-12)


if __name__=='__main__':unittest.main()

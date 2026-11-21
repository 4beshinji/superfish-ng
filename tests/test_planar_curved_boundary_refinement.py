# SPDX-License-Identifier: Apache-2.0
"""Physical invariants for boundary-only conforming original-map restrictions."""
from fractions import Fraction
import unittest
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_fem import planar_curved_matrices
from superfish_ng.planar_curved_geometry import _map_coefficients
from superfish_ng.planar_curved_refinement import refine_planar_curved_domain, _evaluate
from test_planar_curved import curved_ellipse


class BoundaryRefinementTests(unittest.TestCase):
    def test_boundary_splits_and_interior_remains_unmodified_with_exact_coverage(self):
        base=curved_ellipse(12)
        coarse=refine_planar_curved_domain(base,max_geometry_boxes=1000000).domain
        fine=refine_planar_curved_domain(coarse,pattern='boundary',max_geometry_boxes=1000000)
        boundary_edges={tuple(sorted(map(int,edge[:2]))) for edge in coarse.boundary_nodes}
        touched=set()
        for parent,cell in enumerate(coarse.cell_nodes):
            if any(tuple(sorted((int(cell[i]),int(cell[j])))) in boundary_edges for i,j in ((0,1),(1,2),(2,0))):touched.add(parent)
        self.assertTrue(touched)
        self.assertLess(len(fine.domain.cell_nodes),4*len(coarse.cell_nodes))
        self.assertEqual(len(fine.domain.boundary_nodes),2*len(coarse.boundary_nodes))
        counts=np.bincount(fine.parent_cells,minlength=len(coarse.cell_nodes))
        for parent in touched:self.assertEqual(counts[parent],4)
        unchanged=np.flatnonzero(counts==1)
        self.assertGreater(len(unchanged),0)
        for parent in unchanged:
            child=np.flatnonzero(fine.parent_cells==parent)[0]
            np.testing.assert_array_equal(fine.domain.cell_nodes[child],coarse.cell_nodes[parent])
        for parent in range(len(coarse.cell_nodes)):
            covered=Fraction(0)
            coeff=_map_coefficients(coarse.points_xy_m[coarse.cell_nodes[parent]])
            for child in np.flatnonzero(fine.parent_cells==parent):
                tri=[[Fraction(float(v)) for v in p] for p in fine.parent_reference_vertices[child]]
                covered+=(tri[1][0]-tri[0][0])*(tri[2][1]-tri[0][1])-(tri[1][1]-tri[0][1])*(tri[2][0]-tri[0][0])
                refs=tri+[[ (tri[i][a]+tri[j][a])/2 for a in range(2)] for i,j in ((0,1),(1,2),(2,0))]
                for index,ref in enumerate(refs):
                    actual=fine.domain.points_xy_m[fine.domain.cell_nodes[child,index]]
                    expected=_evaluate(coeff,ref)
                    self.assertLessEqual(max(abs(Fraction(float(actual[a]))-expected[a]) for a in range(2)),max(fine.coordinate_error_bounds_m[child]))
            self.assertEqual(covered,Fraction(1))
        self.assertLess(fine.maximum_relative_coordinate_bound,512*np.finfo(float).eps)
        self.assertLess(abs(fine.domain.area_m2/coarse.area_m2-1),1e-12)
        self.assertLess(abs(fine.domain.boundary_length_m()/coarse.boundary_length_m()-1),1e-12)

    def test_coarse_energy_forms_and_linear_field_are_preserved(self):
        coarse=refine_planar_curved_domain(curved_ellipse(12),max_geometry_boxes=1000000).domain
        fine=refine_planar_curved_domain(coarse,pattern='boundary',max_geometry_boxes=1000000)
        _,k,m,_=planar_curved_matrices(PlanarCurvedCase(coarse,modes=1,quadrature_order=16))
        _,kk,mm,_=planar_curved_matrices(PlanarCurvedCase(fine.domain,modes=1,quadrature_order=16,max_geometry_boxes=1000000))
        p=fine.prolongation
        for result,reference,tol in ((p.T@kk@p,k,1e-10),(p.T@mm@p,m,1e-12)):
            self.assertLess(np.linalg.norm((result-reference).toarray())/np.linalg.norm(reference.toarray()),tol)
        np.testing.assert_array_equal(p@np.ones(len(coarse.points_xy_m)),np.ones(len(fine.domain.points_xy_m)))
        np.testing.assert_allclose(p@coarse.points_xy_m,fine.domain.points_xy_m,rtol=0,atol=1e-16)

    def test_boundary_pattern_still_enforces_shared_geometry_budget(self):
        with self.assertRaisesRegex(ValueError,'exhausted'):
            refine_planar_curved_domain(curved_ellipse(12),pattern='boundary',max_geometry_boxes=1)
        with self.assertRaisesRegex(ValueError,'uniform/bisection/boundary'):
            refine_planar_curved_domain(curved_ellipse(12),pattern='boundary_projection')


if __name__=='__main__':unittest.main()

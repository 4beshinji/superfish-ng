# SPDX-License-Identifier: Apache-2.0
"""Closed reference membership must distinguish exact contact from rounded sums."""
from fractions import Fraction
from pathlib import Path
import sys
import unittest
import numpy as np
from superfish_ng import planar_curved_geometry as geometry
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved, planar_curved_quantities
from test_planar_curved import patch, curved_ellipse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from planar_curved_vector_reference import original_vectors,vectorized_validation_view
from validate_planar_curved_independent import independent_integrals


class ExactReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solution=solve_planar_curved(PlanarCurvedCase(patch(shift=(-.03,.01)),modes=2))

    def test_exact_outside_points_cannot_enter_through_rounded_unit_sum(self):
        for refs in ([[.5,np.nextafter(.5,1)]],[[1.,np.nextafter(0.,1)]],[[np.nextafter(0.,1),1.]]):
            self.assertEqual(sum(refs[0]),1.)
            with self.assertRaisesRegex(ValueError,'closed.*triangle'):
                self.solution.case.domain.elements[0].evaluate(refs)
            for call in (lambda:self.solution.fields_at_reference([0],refs),lambda:self.solution.all_fields_at_reference([0],refs),lambda:original_vectors(self.solution,0,refs),lambda:vectorized_validation_view(self.solution).all_fields_at_reference([0],refs)):
                with self.assertRaisesRegex(ValueError,'closed.*triangle'):call()
        for refs in ([[.5,.5]],[[1.,0.]],[[0.,1.]],[[.5,np.nextafter(.5,0)]]):
            self.solution.all_fields_at_reference([0],refs)

    def test_representable_wall_parameters_keep_exact_contact_on_all_three_edges(self):
        t,_=np.polynomial.legendre.leggauss(32)
        t=(t+1)/2
        canonical=geometry._canonical_boundary_parameters(t)
        self.assertLessEqual(np.max(abs(canonical-t)),np.finfo(float).eps/2)
        for value in canonical:
            self.assertEqual(Fraction(float(value))+Fraction(float(1-value)),1)
        domain=self.solution.case.domain
        for edge,local in enumerate(domain.boundary_local_edges):
            refs=(np.column_stack((canonical,0*canonical)) if local==0 else np.column_stack((1-canonical,canonical)) if local==1 else np.column_stack((0*canonical,1-canonical)))
            self.assertTrue(np.all(geometry._closed_reference_mask(refs)))
            mapped=domain.elements[domain.boundary_cells[edge]].evaluate(refs)
            actual=domain.boundary_evaluate(edge,canonical)['points_xy_m']
            np.testing.assert_allclose(mapped['points_xy_m'],actual,rtol=0,atol=2e-17)
        for mode in range(2):
            rf=planar_curved_quantities(self.solution,mode)
            self.assertAlmostEqual(rf['stored_energy_j_per_m'],1.,places=12)
        self.assertTrue(independent_integrals(self.solution)['passed'])
        self.assertTrue(independent_integrals(vectorized_validation_view(self.solution))['passed'])

    def test_exact_classifier_matches_rational_oracle_at_corners_and_one_ulp_neighbors(self):
        values=[0.,np.nextafter(0.,1),np.nextafter(.5,0),.5,np.nextafter(.5,1),np.nextafter(1.,0),1.,np.nextafter(1.,2)]
        refs=np.array([(x,y) for x in values for y in values])
        expected=np.array([Fraction(float(x))>=0 and Fraction(float(y))>=0 and Fraction(float(x))+Fraction(float(y))<=1 for x,y in refs])
        np.testing.assert_array_equal(geometry._closed_reference_mask(refs),expected)

    def test_actual_TM_essential_PEC_scalar_is_exactly_zero_on_canonical_wall(self):
        solution=solve_planar_curved(PlanarCurvedCase(curved_ellipse(12),'tm',modes=1))
        t,_=np.polynomial.legendre.leggauss(32)
        t=geometry._canonical_boundary_parameters((t+1)/2)
        for owner,local in zip(solution.case.domain.boundary_cells,solution.case.domain.boundary_local_edges):
            refs=(np.column_stack((t,0*t)) if local==0 else np.column_stack((1-t,t)) if local==1 else np.column_stack((0*t,1-t)))
            fields=solution.fields_at_reference(np.full(len(t),owner),refs)
            np.testing.assert_array_equal(fields['Ez_real_V_per_m'],np.zeros(len(t)))
        self.assertTrue(independent_integrals(solution)['passed'])


if __name__=='__main__':unittest.main()

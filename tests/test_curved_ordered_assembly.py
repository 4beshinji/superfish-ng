# SPDX-License-Identifier: Apache-2.0
"""Scalar arithmetic compatibility and independent mapped-field moments."""
import unittest
import numpy as np
from superfish_ng.curved_fem import mapped_element_matrices
from superfish_ng.fem import triangle_quadrature
from superfish_ng.high_order import basis_p2
from superfish_ng.quadratic_geometry import QuadraticTriangle

NODES = np.array(((0.,0.),(1.,0.),(0.,1.),(.5,0.),(.5,.5),(0.,.5)))


def scalar_evaluate(geometry, points):
    """Project's pre-batching P2 evaluation, kept as an arithmetic oracle."""
    values, gradients = [], []
    for x,y in points:
        n,d = basis_p2(np.array((1-x-y,x,y)),np.array(((-1.,-1.),(1.,0.),(0.,1.))))
        values.append(n); gradients.append(d)
    values,gradients = np.asarray(values),np.asarray(gradients)
    jacobian = np.einsum('ia,qib->qab',geometry.points_rz_m-geometry.points_rz_m[0],gradients)
    return dict(points_rz_m=values@geometry.points_rz_m,jacobian=jacobian,
                determinant_m2=np.linalg.det(jacobian),basis_values=values,
                basis_gradients=np.einsum('qia,qab->qib',gradients,np.linalg.inv(jacobian)))


def scalar_matrices(geometry, order):
    rule = list(triangle_quadrature(order=order))
    mapped = scalar_evaluate(geometry,[b[1:] for b,w in rule])
    stiffness,mass = np.zeros((6,6)),np.zeros((6,6))
    for i,(_,weight) in enumerate(rule):
        n = mapped['basis_values'][i]
        derivative = mapped['basis_gradients'][i]
        radius = mapped['points_rz_m'][i,0]
        measure = weight*mapped['determinant_m2'][i]
        curl_z = 2*n+radius*derivative[:,0]
        curl_r = radius*derivative[:,1]
        stiffness += measure*radius*(np.outer(curl_z,curl_z)+np.outer(curl_r,curl_r))
        mass += measure*radius**3*np.outer(n,n)
    return stiffness,mass


class CurvedOrderedAssemblyTests(unittest.TestCase):
    def geometries(self):
        x,y = NODES.T
        for scale in (.125,1.,2.):
            for shift in (0.,.3):
                yield QuadraticTriangle(scale*np.column_stack((x+shift,y*(1+.4*x))))

    def test_evaluation_matches_scalar_bytes_at_interior_and_boundary(self):
        points = np.random.default_rng(941).random((100,2))
        points[:,1] *= 1-points[:,0]
        points = np.vstack((NODES,points))
        for geometry in self.geometries():
            actual,expected = geometry.evaluate(points),scalar_evaluate(geometry,points)
            for key in expected:
                with self.subTest(key=key,geometry=geometry.points_rz_m.tolist()):
                    self.assertEqual(actual[key].tobytes(),expected[key].tobytes())

    def test_ordered_matrices_match_scalar_bytes_and_release_prefix_storage(self):
        for geometry in self.geometries():
            for order in (2,3,4,5,8,12,24,32):
                actual = mapped_element_matrices(geometry,quadrature_order=order)
                for a,b in zip(actual,scalar_matrices(geometry,order)):
                    with self.subTest(order=order,geometry=geometry.points_rz_m.tolist()):
                        self.assertEqual(a.tobytes(),b.tobytes())
                        self.assertTrue(a.flags.owndata)
                        self.assertEqual(a.nbytes,6*6*8)

    def test_exact_curved_moments_and_maxwell_matrix_scaling(self):
        # r=x, z=y(1+a*x): det J=1+a*x on the unit triangle.
        x,y = NODES.T
        a = .4
        nodes = np.column_stack((x,y*(1+a*x)))
        one = np.ones(6)
        for order in (5,12,24,32):
            k,m = mapped_element_matrices(QuadraticTriangle(nodes),quadrature_order=order)
            self.assertAlmostEqual(one@k@one,4*(1/6+a/12),places=12)
            self.assertAlmostEqual(one@m@one,1/20+a/30,places=12)
            self.assertAlmostEqual(x@k@x,9*(1/20+a/30),places=12)
            ks,ms = mapped_element_matrices(QuadraticTriangle(2*nodes),quadrature_order=order)
            np.testing.assert_allclose(ks,8*k,rtol=2e-14,atol=1e-14)
            np.testing.assert_allclose(ms,32*m,rtol=2e-14,atol=1e-14)

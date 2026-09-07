# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from superfish_ng.quadratic_geometry import QuadraticTriangle
from superfish_ng.curved_fem import mapped_element_matrices
from superfish_ng.high_order import basis_p2
from superfish_ng.fem import triangle_quadrature

NODES = np.array(((0.,0.),(1.,0.),(0.,1.),(.5,0.),(.5,.5),(0.,.5)))


class CurvedElementTests(unittest.TestCase):
    def test_affine_reduction_to_straight_integrals(self):
        points = NODES*np.array((2.,3.))+np.array((.2,.1))
        geometry = QuadraticTriangle(points)
        actual = mapped_element_matrices(geometry)
        k,m = np.zeros((6,6)),np.zeros((6,6))
        gradient = np.array(((-.5,-1/3),(.5,0),(0,1/3)))
        for barycentric,weight in triangle_quadrature(order=5):
            n,d = basis_p2(barycentric,gradient)
            r = .2+2*barycentric[1]
            cz,cr = 2*n+r*d[:,0],r*d[:,1]
            k += weight*6*r*(np.outer(cz,cz)+np.outer(cr,cr))
            m += weight*6*r**3*np.outer(n,n)
        for a,b in zip(actual,(k,m)):
            np.testing.assert_allclose(a,b,rtol=1e-12,atol=1e-13)

    def test_curved_constant_and_linear_physical_fields(self):
        x,y = NODES.T
        a = .4
        geometry = QuadraticTriangle(np.column_stack((x,y*(1+a*x))))
        k,m = mapped_element_matrices(geometry,quadrature_order=12)
        one = np.ones(6)
        moment_r = 1/6+a/12
        moment_r3 = 1/20+a/30
        self.assertAlmostEqual(one@k@one,4*moment_r,places=12)
        self.assertAlmostEqual(one@m@one,moment_r3,places=12)
        self.assertAlmostEqual(x@k@x,9*moment_r3,places=12)
        self.assertGreater(np.linalg.eigvalsh(k)[0],0)
        self.assertGreater(np.linalg.eigvalsh(m)[0],0)
        coarse = mapped_element_matrices(geometry,quadrature_order=4)
        middle = mapped_element_matrices(geometry,quadrature_order=8)
        self.assertLess(np.linalg.norm(middle[0]-k),np.linalg.norm(coarse[0]-k))
        np.testing.assert_allclose(middle[0],k,rtol=1e-10,atol=1e-12)

    def test_negative_radius_and_invalid_quadrature_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'radius'):
            mapped_element_matrices(QuadraticTriangle(NODES-np.array((.1,0))))
        for value in (True,0,1,2.5):
            with self.assertRaisesRegex(ValueError,'quadrature_order'):
                mapped_element_matrices(QuadraticTriangle(NODES),quadrature_order=value)

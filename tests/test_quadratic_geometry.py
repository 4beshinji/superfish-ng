# SPDX-License-Identifier: Apache-2.0
import math
import unittest
import numpy as np
from superfish_ng.quadratic_geometry import QuadraticTriangle,quadratic_minimum
from superfish_ng.fem import triangle_quadrature

NODES = np.array(((0.,0.),(1.,0.),(0.,1.),(.5,0.),(.5,.5),(0.,.5)))


class QuadraticGeometryTests(unittest.TestCase):
    def test_affine_limit_and_physical_linear_gradients(self):
        matrix = np.array(((2.,.3),(.2,1.5)))
        points = NODES@matrix.T+np.array((3.,4.))
        geometry = QuadraticTriangle(points)
        result = geometry.evaluate(NODES)
        np.testing.assert_allclose(result['points_rz_m'],points,atol=1e-14)
        np.testing.assert_allclose(result['determinant_m2'],np.linalg.det(matrix))
        self.assertAlmostEqual(geometry.minimum_determinant_m2,np.linalg.det(matrix))
        np.testing.assert_allclose(result['basis_values'].sum(axis=1),1)
        np.testing.assert_allclose(result['basis_gradients'].sum(axis=1),0,atol=1e-14)
        gradients = np.einsum('ia,qib->qab',points,result['basis_gradients'])
        np.testing.assert_allclose(gradients,np.broadcast_to(np.eye(2),gradients.shape),atol=1e-14)
        with self.assertRaises(ValueError):
            geometry.points_rz_m[0,0]=2.

    def test_curved_area_and_revolution_volume(self):
        x,y = NODES.T
        a = .4
        points = np.column_stack((x,y*(1+a*x)))
        geometry = QuadraticTriangle(points)
        self.assertAlmostEqual(geometry.minimum_determinant_m2,1)
        area,volume = 0.,0.
        for barycentric,weight in triangle_quadrature(order=5):
            result = geometry.evaluate([barycentric[1:]])
            jacobian = result['determinant_m2'][0]
            radius = result['points_rz_m'][0,0]
            area += weight*jacobian
            volume += 2*math.pi*weight*jacobian*radius
        self.assertAlmostEqual(area,.5+a/6)
        self.assertAlmostEqual(volume,2*math.pi*(1/6+a/12))
        scaled = QuadraticTriangle(points*3)
        self.assertAlmostEqual(scaled.minimum_determinant_m2,9)

    def test_fold_between_positive_nodal_jacobians_is_rejected(self):
        x,y = NODES.T
        points = np.column_stack(((x-.25)**2-y,(x-.25)*y-.01*x))
        # Exact determinant 2(x-.25)^2+y-.01 is positive at all six nodes,
        # but negative at (.25,0). Nodal positivity is insufficient.
        self.assertTrue(np.all(2*(x-.25)**2+y-.01>0))
        with self.assertRaisesRegex(ValueError,'Jacobian'):
            QuadraticTriangle(points)
        minimum,location = quadratic_minimum((.115,-1.,1.,2.,0.,0.))
        self.assertAlmostEqual(minimum,-.01)
        np.testing.assert_allclose(location,(.25,0.))

    def test_interior_minimum_and_invalid_maps(self):
        minimum,location = quadratic_minimum((.23,-.4,-.6,1.,0.,1.))
        self.assertAlmostEqual(minimum,.1)
        np.testing.assert_allclose(location,(.2,.3))
        for points in (NODES[:,::-1],np.zeros((6,2)),np.full((6,2),np.nan),
                       [[True,False]]*6,NODES[:3]):
            with self.assertRaises(ValueError):
                QuadraticTriangle(points)
        for points in ([[.6,.6]],[[-.01,0]],[[0,float('nan')]],[],[['0','0']]):
            with self.assertRaises(ValueError):
                QuadraticTriangle(NODES).evaluate(points)

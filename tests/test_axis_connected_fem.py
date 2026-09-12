# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.linalg import eigh
from scipy.special import jn_zeros
import test_axis_connected_mesh as geometry_tests
from superfish_ng.axis_connected_fem import axis_connected_matrices
from superfish_ng.constants import C0,TAU


class AxisConnectedFormTests(unittest.TestCase):
    def test_polynomial_moments_and_no_circulation_nullspace(self):
        fixture=geometry_tests.AxisConnectedMeshTests()
        from superfish_ng.axis_connected_mesh import AxisConnectedMesh
        for holes in (0,1,2):
            mesh=AxisConnectedMesh(**fixture.data(holes));rectangles=[(*mesh.outer_rz_m[0],*mesh.outer_rz_m[2],1.)]
            rectangles += [(h[0,0],h[0,1],h[2,0],h[2,1],-1.) for h in mesh.holes_rz_m]
            def moment(rpower,zpower):
                return sum(sign*(b**(rpower+1)-a**(rpower+1))/(rpower+1)*(d**(zpower+1)-c**(zpower+1))/(zpower+1) for a,c,b,d,sign in rectangles)
            for order in (1,2):
                space,k,m=axis_connected_matrices(mesh,order);r,z=space.dof_points.T
                for value,exact_k,exact_m in ((np.ones_like(r),4*moment(1,0),moment(3,0)),(r,9*moment(3,0),moment(5,0)),(z,4*moment(1,2)+moment(3,0),moment(3,2))):
                    self.assertLess(abs(float(value@(k@value))/exact_k-1),1e-12)
                    self.assertLess(abs(float(value@(m@value))/exact_m-1),1e-12)
                values,vectors=eigh(k.toarray(),m.toarray());self.assertGreater(values[0],0.)
                self.assertGreater(np.linalg.norm(vectors[space.axis_dofs,0]),0.)
                self.assertEqual(len(space.axis_dofs),7 if order==1 else 13)
                if not holes:
                    exact=(jn_zeros(0,1)[0]/max(r))**2
                    self.assertGreaterEqual(values[0],exact*(1-1e-12))
                    self.assertLess(values[0]/exact-1,.01)
    def test_unsupported_element_order_rejected(self):
        from superfish_ng.axis_connected_mesh import AxisConnectedMesh
        mesh=AxisConnectedMesh(**geometry_tests.AxisConnectedMeshTests().data())
        for order in (True,0,3,1.):
            with self.assertRaises(ValueError):axis_connected_matrices(mesh,order)

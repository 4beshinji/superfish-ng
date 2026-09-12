# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.linalg import eigh
from scripts.curved_meridional_reference import fixture,form_invariants
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi_fem import curved_hphi_matrices
from superfish_ng.axis_connected_fem import axis_connected_matrices
from superfish_ng.hphi_mesh import HphiMeshCase,hphi_mesh_matrices


class CurvedHphiFemTests(unittest.TestCase):
    def geometry(self,axis=False,holes=1,shear=1.,scale=1.):
        data,_=fixture(axis,holes,scale=scale,shear=shear)
        return CurvedMeridionalGeometry(**data)

    def test_affine_limit_matches_both_existing_forms(self):
        for axis in (False,True):
            for holes in (0,1,2):
                g=self.geometry(axis,holes,shear=0.)
                for order in (1,2):
                    space,k,m,report=curved_hphi_matrices(g,order)
                    original=axis_connected_matrices(g.base_mesh,order) if axis else hphi_mesh_matrices(HphiMeshCase(g.base_mesh,element_order=order,modes=1,quadrature_order=12))
                    np.testing.assert_array_equal(space.cell_dofs,original[0].cell_dofs)
                    for a,b in zip((k,m),original[1:3]):
                        self.assertLess(np.linalg.norm((a-b).data)/np.linalg.norm(b.data),1e-12)
                    if axis:np.testing.assert_array_equal(space.axis_dofs,original[0].axis_dofs)
                    self.assertEqual(report['common_azimuthal_factor_included'],False)

    def test_constant_fields_coordinate_energies_and_static_kernel(self):
        for axis in (False,True):
            for holes in (0,1,2):
                g=self.geometry(axis,holes)
                for order in (1,2):
                    space,k,m,report=curved_hphi_matrices(g,order)
                    expected=form_invariants(axis,holes,1,1.,1.,0.);radial=expected['radial_integrals'];one=np.ones(len(space.dof_points))
                    eigen=eigh(k.toarray(),m.toarray(),eigvals_only=True)
                    self.assertTrue(np.linalg.eigvalsh(m.toarray()).min()>0)
                    for matrix in (k,m):self.assertLess(np.linalg.norm((matrix-matrix.T).data)/np.linalg.norm(matrix.data),1e-14)
                    if axis:
                        self.assertGreater(eigen[0],1.)
                        self.assertAlmostEqual((one@k@one)/(4*radial[1]),1.,places=11)
                        self.assertAlmostEqual((one@m@one)/radial[3],1.,places=11)
                        self.assertGreater(len(space.axis_dofs),0)
                    else:
                        self.assertLess(np.linalg.norm(k@one)/(np.linalg.norm(k.data)*np.linalg.norm(one)),1e-14)
                        self.assertLess(abs(eigen[0])/eigen[-1],1e-14);self.assertGreater(eigen[1],1.)
                        r,z=space.dof_points.T
                        self.assertAlmostEqual((one@m@one)/radial[-1],1.,places=10)
                        self.assertAlmostEqual((r@k@r)/radial[-1],1.,places=10)
                        self.assertAlmostEqual((r@m@r)/radial[1],1.,places=10)
                        if order==2:
                            self.assertAlmostEqual((z@k@z)/radial[-1],1.,places=10)
                            self.assertLess(abs(r@k@z)/radial[-1],1e-12)
                            self.assertAlmostEqual((z@m@z)/expected['z_mass'],1.,places=10)

    def test_similarity_of_each_scalar_form(self):
        for axis in (False,True):
            for order in (1,2):
                a=curved_hphi_matrices(self.geometry(axis,2,scale=1.),order)
                b=curved_hphi_matrices(self.geometry(axis,2,scale=4.),order)
                for first,second,power in zip(a[1:3],b[1:3],(3,5) if axis else (-1,1)):
                    self.assertLess(np.linalg.norm((second-first*4**power).data)/np.linalg.norm(second.data),1e-12)

    def test_strict_forms_and_unresolved_quadrature(self):
        g=self.geometry()
        for order in (True,0,3,1.):
            with self.assertRaises(ValueError):curved_hphi_matrices(g,order)
        for order in (True,1,33,8.):
            with self.assertRaises(ValueError):curved_hphi_matrices(g,quadrature_order=order)
        with self.assertRaisesRegex(ValueError,'unresolved'):curved_hphi_matrices(g,quadrature_order=2)
        with self.assertRaises(ValueError):curved_hphi_matrices(g.base_mesh)

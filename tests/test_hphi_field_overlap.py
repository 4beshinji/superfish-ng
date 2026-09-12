# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng.constants import EPS0,MU0
from superfish_ng.axis_hphi import AxisHphiCase,solve_axis_hphi
from superfish_ng.coaxial import CoaxialCase,solve_coaxial
from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.hphi_field_overlap import hphi_field_grams
from test_meridional_overlap import fixture


def solution(axis,order=2,n=1,holes=1,opposite=False,energy=1.):
    mesh=fixture(n,holes,axis,opposite)
    return solve_axis_hphi(AxisHphiCase(mesh,element_order=order,modes=3,normalization_j=energy)) if axis else solve_hphi_mesh(HphiMeshCase(mesh,element_order=order,modes=3,normalization_j=energy,quadrature_order=12))


class HphiFieldOverlapTests(unittest.TestCase):
    def test_self_energy_and_signed_normalization(self):
        for axis in (False,True):
            for order in (1,2):
                a=solution(axis,order);b=solution(axis,order,energy=4.);b.coefficients[:,1]*=-1
                grams=hphi_field_grams(a,b)
                for family,constant in (('electric',EPS0),('magnetic',MU0)):
                    aa,ab,bb=getattr(grams,family)
                    np.testing.assert_allclose(constant/4*aa,np.eye(3)/2,atol=1e-10,rtol=1e-9)
                    np.testing.assert_allclose(constant/4*bb,np.eye(3)*2,atol=1e-10,rtol=1e-9)
                    np.testing.assert_allclose(ab,aa*np.array([2,-2,2]),atol=np.max(abs(aa))*1e-10,rtol=1e-9)
                    self.assertFalse(ab.flags.writeable)
                self.assertEqual(grams.diagnostic['mode_tracking'],'not_performed')

    def test_independent_mesh_mixed_order_and_exchange(self):
        for axis in (False,True):
            a,b=solution(axis,1),solution(axis,2,n=2,opposite=True)
            forward,reverse=hphi_field_grams(a,b),hphi_field_grams(b,a)
            for family in ('electric','magnetic'):
                aa,ab,bb=getattr(forward,family);reverse_cross=getattr(reverse,family)[1]
                np.testing.assert_allclose(ab,reverse_cross.T,atol=np.sqrt(np.diag(aa).max()*np.diag(bb).max())*1e-10)
                self.assertLessEqual(np.max(abs(ab/np.sqrt(np.diag(aa)[:,None]*np.diag(bb)[None,:]))),1+1e-10)

    def test_closed_coaxial_and_explicit_mesh_same_field(self):
        for order in (1,2):
            a=solve_coaxial(CoaxialCase(.03125,.125,.09375,nr=3,nz=3,element_order=order,modes=3,quadrature_order=12))
            mesh=MeridionalMesh([[.03125,0],[.125,0],[.125,.09375],[.03125,.09375]],[],a.space.mesh.points,a.space.mesh.triangles)
            b=solve_hphi_mesh(HphiMeshCase(mesh,element_order=order,modes=3,quadrature_order=12));grams=hphi_field_grams(a,b)
            for family in ('electric','magnetic'):
                aa,ab,bb=getattr(grams,family);normalized=ab/np.sqrt(np.diag(aa)[:,None]*np.diag(bb)[None,:])
                np.testing.assert_allclose(abs(normalized),np.eye(3),atol=1e-9)

    def test_invalid_solution_geometry_and_budget_rejected(self):
        a=solution(True)
        bad=deepcopy(a);bad.coefficients[0,0]*=2
        with self.assertRaisesRegex(ValueError,'energy|residual'):hphi_field_grams(a,bad)
        bad=deepcopy(a);bad.space.cell_dofs[0,0]=bad.space.cell_dofs[0,1]
        with self.assertRaisesRegex(ValueError,'mesh|space'):hphi_field_grams(a,bad)
        with self.assertRaisesRegex(ValueError,'same.*vacuum'):hphi_field_grams(a,solution(True,holes=0))
        with self.assertRaises(ValueError):hphi_field_grams(a,object())
        for kwargs in ({'max_gram_modes':2},{'max_gram_modes':True},{'max_candidate_tests':1}):
            with self.assertRaises(ValueError):hphi_field_grams(a,a,**kwargs)


if __name__=='__main__':unittest.main()

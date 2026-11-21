# SPDX-License-Identifier: Apache-2.0
"""Curved scalar mass transfer against independent moments and nested algebra."""
import unittest
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi_fem import curved_hphi_matrices
from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain
from superfish_ng.curved_hphi_refinement import refine_curved_hphi_geometry


def geometry(axis=False,scale=.7,shear=1.):
    data,_=fixture(axis,2,scale=scale,shear=shear)
    return CurvedMeridionalGeometry(**data)


class CurvedHphiMassProjectionTests(unittest.TestCase):
    def test_independent_constant_moments_and_exact_refinement_transfer(self):
        for axis in (False,True):
            a=geometry(axis);refined=refine_curved_hphi_geometry(a);b=refined.geometry
            space,_,mass,_=curved_hphi_matrices(a)
            original,_=fixture(axis,2,scale=.7,shear=0.);base=original['base_mesh'];expected=0.
            for sign,loop in [(1,base.outer_rz_m),*((-1,h) for h in base.holes_rz_m)]:
                x,z0=loop.min(axis=0);y,z1=loop.max(axis=0)
                expected+=sign*(z1-z0)*((y**4-x**4)/4 if axis else np.log(y/x))
            ones=np.ones(mass.shape[0]);self.assertAlmostEqual((ones@mass@ones)/expected,1.,places=11)
            from superfish_ng.curved_hphi_mass_projection import project_curved_hphi_coefficients
            domain=CurvedHphiComparisonDomain(a,a,'same_vacuum',restriction_policy='binary64_roundoff')
            c=np.column_stack((ones,space.dof_points[:,0],space.dof_points[:,1],np.zeros(len(ones))))
            result=project_curved_hphi_coefficients(a,b,c,domain,current_cells=refined.native_cells)
            np.testing.assert_allclose(result.coefficients,refined.prolongation@c,rtol=1e-9,atol=1e-11)
            self.assertLess(max(result.diagnostic['relative_mass_error']),1e-9)
            self.assertEqual(result.diagnostic['relative_mass_error'][-1],0.)
            self.assertNotIn('frequency_hz',result.diagnostic)

    def test_coarsening_loss_agrees_with_independent_nested_mass_algebra(self):
        from superfish_ng.curved_hphi_mass_projection import project_curved_hphi_coefficients
        for axis in (False,True):
            coarse=geometry(axis);refined=refine_curved_hphi_geometry(coarse);fine=refined.geometry
            space,_,mf,_=curved_hphi_matrices(fine);p=refined.prolongation
            c=(space.dof_points[:,0]**3)[:,None];before=c.copy()
            oracle=np.linalg.solve((p.T@mf@p).toarray(),p.T@mf@c)
            domain=CurvedHphiComparisonDomain(coarse,coarse,'same_vacuum',restriction_policy='binary64_roundoff')
            result=project_curved_hphi_coefficients(fine,coarse,c,domain,previous_cells=refined.native_cells)
            np.testing.assert_allclose(result.coefficients,oracle,rtol=1e-9,atol=1e-12)
            error=c-p@oracle;relative=np.sqrt(np.sum(error*(mf@error),axis=0)/np.sum(c*(mf@c),axis=0))
            np.testing.assert_allclose(result.diagnostic['relative_mass_error'],relative,rtol=1e-8,atol=1e-12)
            self.assertGreater(relative[0],1e-6)
            np.testing.assert_array_equal(c,before)

    def test_two_scale_density_and_nonuniform_shear(self):
        from superfish_ng.curved_hphi_mass_projection import project_curved_hphi_coefficients
        for axis in (False,True):
            a=geometry(axis);size=len(a.points_rz_m);c=np.ones((size,1))
            for b,factor in ((geometry(axis,scale=1.4),2**(-2.5 if axis else -.5)),(geometry(axis,shear=2.),1.)):
                domain=CurvedHphiComparisonDomain(a,b,'declared_quadratic')
                result=project_curved_hphi_coefficients(a,b,c,domain)
                np.testing.assert_allclose(result.coefficients,factor,rtol=1e-9,atol=1e-11)
                self.assertLess(max(result.diagnostic['relative_mass_error']),1e-9)

    def test_p1_and_straight_limit_reproduce_existing_coupling(self):
        from superfish_ng.curved_hphi_mass_projection import curved_hphi_mass_coupling
        from superfish_ng.hphi_mass_projection import hphi_mass_coupling
        for axis in (False,True):
            a=geometry(axis,scale=1.,shear=0.);b=refine_curved_hphi_geometry(a).geometry
            refined=refine_curved_hphi_geometry(a)
            domain=CurvedHphiComparisonDomain(a,a,'same_vacuum')
            for order in (1,2):
                result=curved_hphi_mass_coupling(a,b,domain,previous_order=order,current_order=order,current_cells=refined.native_cells)
                old=hphi_mass_coupling(a.base_mesh,b.base_mesh,previous_order=order,current_order=order)
                for name in ('previous_mass','cross_mass','current_mass'):
                    x,y=getattr(result,name),getattr(old,name)
                    self.assertLess(np.linalg.norm((x-y).toarray())/np.linalg.norm(y.toarray()),1e-10)

    def test_strict_coefficients_spaces_and_budgets(self):
        from superfish_ng.curved_hphi_mass_projection import project_curved_hphi_coefficients
        a=geometry();domain=CurvedHphiComparisonDomain(a,a,'same_vacuum');c=np.ones((len(a.points_rz_m),1))
        for value in (c.ravel(),np.empty((len(c),0)),c.astype(bool),c*float('nan'),c[:-1]):
            with self.assertRaises(ValueError):project_curved_hphi_coefficients(a,a,value,domain)
        for name,value in (('previous_order',3),('quadrature_order',True),('max_dofs',1),('max_sample_points',1),('max_columns',0)):
            with self.assertRaises(ValueError):project_curved_hphi_coefficients(a,a,c,domain,**{name:value})

# SPDX-License-Identifier: Apache-2.0
from unittest.mock import patch
import unittest
import numpy as np
from test_material_hphi_comparison import partition,request
from test_hphi_geometry_mapping import transformed
from superfish_ng.rf_materials import RFMaterialPartition,LinearRFMaterial,RFMaterialRegion
from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping
from superfish_ng.material_hphi_mass_projection import material_hphi_mass_coupling,project_material_hphi_coefficients


def polynomial(points,order):
    r,z=(32*points).T
    return np.column_stack((np.ones(len(r)),1+2*r-3*z+(r*r+r*z+2*z*z if order==2 else 0)))


class MaterialHphiMassProjectionTests(unittest.TestCase):
    def test_independent_material_moments_polynomials_and_static_constant(self):
        for axis in (False,True):
            for order in (1,2):
                a,b=partition(1,1,axis),partition(2,1,axis,True);q=request(a,b)
                c=material_hphi_mass_coupling(q,previous_order=order,current_order=order)
                values=polynomial(c.previous_space.dof_points,order);before=values.copy()
                result=project_material_hphi_coefficients(q,values,previous_order=order,current_order=order)
                np.testing.assert_allclose(result.coefficients,polynomial(c.current_space.dof_points,order),rtol=1e-10,atol=1e-10)
                expected=0.
                for mu,lower,upper in ((3.,0.,1/32),(7.,1/32,3/32)):
                    for sign,contour in [(1,a.mesh.outer_rz_m),*[(-1,h) for h in a.mesh.holes_rz_m]]:
                        r0,z0=contour.min(axis=0);r1,z1=contour.max(axis=0);height=max(0.,min(z1,upper)-max(z0,lower))
                        radial=(r1**4-r0**4)/4 if axis else np.log(r1/r0)
                        expected+=sign*mu*height*radial
                ones=values[:,0]
                self.assertAlmostEqual(float(ones@(c.previous_mass@ones))/expected,1.,delta=1e-11)
                self.assertLess(max(result.diagnostic['relative_mass_error']),1e-10)
                np.testing.assert_array_equal(values,before)
                self.assertFalse(result.coefficients.flags.writeable)
                self.assertEqual(c.previous_mass.shape[0],len(c.previous_space.dof_points))
                if axis:self.assertGreater(len(c.previous_space.axis_dofs),0)

    def test_two_scale_transport_and_reverse_cross_mass(self):
        for axis in (False,True):
            a=partition(1,0,axis);sr,sz=2.,.5
            b=RFMaterialPartition(transformed(a.mesh,lambda p:p*[sr,sz]),a.materials,a.regions)
            mapping=HphiGeometryMapping(a.mesh,b.mesh);q=request(a,b,mapping)
            c=material_hphi_mass_coupling(q);back=material_hphi_mass_coupling(request(b,a,mapping.inverse()))
            np.testing.assert_allclose(c.cross_mass.toarray(),back.cross_mass.toarray().T,rtol=1e-11,atol=1e-18)
            values=polynomial(c.previous_space.dof_points,2);projected=project_material_hphi_coefficients(q,values)
            factor=sr**-2*sz**-.5 if axis else sz**-.5
            expected=factor*polynomial(c.current_space.dof_points/[sr,sz],2)
            np.testing.assert_allclose(projected.coefficients,expected,rtol=1e-10,atol=1e-10)
            np.testing.assert_allclose(projected.diagnostic['source_squared_mass_norm'],projected.diagnostic['projected_squared_mass_norm'],rtol=1e-10)

    def test_piecewise_mapping_constant_cross_mass(self):
        for axis in (False,True):
            a=partition(1,0,axis)
            def change(p):return np.column_stack((2*p[:,0],np.where(p[:,1]<=1/32,2*p[:,1],p[:,1]+1/32)))
            b=RFMaterialPartition(transformed(a.mesh,change),a.materials,a.regions)
            mapping=HphiGeometryMapping(a.mesh,b.mesh)
            c=material_hphi_mass_coupling(request(a,b,mapping))
            back=material_hphi_mass_coupling(request(b,a,mapping.inverse()))
            r0=a.mesh.outer_rz_m[:,0].min();r1=a.mesh.outer_rz_m[:,0].max()
            radial=(r1**4-r0**4)/4 if axis else np.log(r1/r0)
            original=radial*np.array([3/32,14/32]);ratios=np.array([32.,16.]) if axis else np.array([2.,1.])
            for actual,expected in ((c.previous_mass,original.sum()),(c.cross_mass,(original*np.sqrt(ratios)).sum()),(c.current_mass,(original*ratios).sum())):
                self.assertAlmostEqual(float(actual.sum())/expected,1.,delta=1e-10)
            np.testing.assert_allclose(c.cross_mass.toarray(),back.cross_mass.toarray().T,rtol=1e-10,atol=1e-18)

    def test_coarsening_loss_zero_and_bad_inputs(self):
        for axis in (False,True):
            a=partition(1,1,axis);q=request(a,a);c=material_hphi_mass_coupling(q,previous_order=2,current_order=1)
            values=polynomial(c.previous_space.dof_points,2)[:,1:];values=np.column_stack((values,np.zeros(len(values))))
            r=project_material_hphi_coefficients(q,values,previous_order=2,current_order=1)
            self.assertGreater(r.diagnostic['relative_mass_error'][0],1e-3);self.assertEqual(r.diagnostic['relative_mass_error'][1],0.)
            np.testing.assert_allclose(c.current_mass@r.coefficients,c.cross_mass.T@values,rtol=1e-10,atol=1e-16)
            self.assertLess(max(r.diagnostic['relative_pythagoras_defect']),1e-8)
            for value in ([[True]],[[1j]],[[float('nan')]],np.zeros((1,0)),np.ones((1,1))):
                with self.assertRaises(ValueError):project_material_hphi_coefficients(q,value)
            with self.assertRaises(ValueError):project_material_hphi_coefficients(q,np.full((c.previous_mass.shape[0],1),1e-200))
        import superfish_ng.material_hphi_mass_projection as module
        with patch.object(module,'material_hphi_matrices',side_effect=AssertionError('budget first')):
            for options in ({'max_dofs':1},{'max_sample_points':1},{'previous_order':3}):
                with self.assertRaises(ValueError):material_hphi_mass_coupling(q,**options)
        with self.assertRaises(ValueError):project_material_hphi_coefficients(q,np.ones((4,3)),max_columns=2)

    def test_independent_basis_mass_and_actual_magnetic_energy(self):
        from numpy.polynomial.legendre import leggauss
        from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi
        from superfish_ng.constants import TAU,MU0
        from test_material_hphi_field_overlap import independent_grams
        g,w=leggauss(24);g=(g+1)/2;w=w/2
        x,y=np.meshgrid(g,g,indexing='ij');xi=x.ravel();eta=((1-x)*y).ravel()
        weights=(w[:,None]*w[None,:]*(1-x)).ravel()
        for axis in (False,True):
            for order in (1,2):
                p=partition(1,1,axis);c=material_hphi_mass_coupling(request(p,p),previous_order=order,current_order=order)
                space=c.previous_space;expected=np.zeros(c.previous_mass.shape)
                for cell,dofs in enumerate(space.cell_dofs):
                    vertices=p.mesh.points_rz_m[p.mesh.triangles[cell]];origin=vertices[0]
                    jac=np.column_stack((vertices[1]-origin,vertices[2]-origin))
                    nodes=(space.dof_points[dofs]-origin)@np.linalg.inv(jac).T
                    def monomials(u,v):return np.column_stack([np.ones_like(u),u,v]+([u*u,u*v,v*v] if order==2 else []))
                    basis=monomials(xi,eta)@np.linalg.inv(monomials(*nodes.T))
                    r=origin[0]+jac[0,0]*xi+jac[0,1]*eta
                    density=p.mu_r[cell]*np.linalg.det(jac)*weights*(r**3 if axis else 1/r)
                    expected[np.ix_(dofs,dofs)]+=basis.T@(density[:,None]*basis)
                scale=np.sqrt(np.diag(expected))
                for matrix in (c.previous_mass,c.cross_mass,c.current_mass):
                    self.assertLess(np.max(abs(matrix.toarray()-expected)/scale[:,None]/scale[None,:]),1e-10)
                solved=solve_material_hphi(MaterialHphiCase(p,element_order=order,modes=2))
                original=solved.coefficients.copy()
                projected=project_material_hphi_coefficients(request(p,p),original,previous_order=order,current_order=order)
                np.testing.assert_allclose(TAU*MU0*(original.T@(c.previous_mass@original)),independent_grams(solved)[1],rtol=1e-9,atol=1e-9)
                np.testing.assert_allclose(projected.coefficients,original,rtol=1e-10,atol=1e-8)
                np.testing.assert_array_equal(solved.coefficients,original)

    def test_vacuum_limit_matches_dedicated_material_path(self):
        from superfish_ng.hphi_mass_projection import hphi_mass_coupling
        for axis in (False,True):
            for order in (1,2):
                parts=[]
                for n in (1,2):
                    m=partition(n,0,axis).mesh
                    parts.append(RFMaterialPartition(m,[LinearRFMaterial('vacuum',1.,1.)],[RFMaterialRegion('all','vacuum',list(range(len(m.triangles))))]))
                result=material_hphi_mass_coupling(request(*parts),previous_order=order,current_order=order)
                old=hphi_mass_coupling(*(p.mesh for p in parts),previous_order=order,current_order=order)
                for name in ('previous_mass','cross_mass','current_mass'):
                    np.testing.assert_allclose(getattr(result,name).toarray(),getattr(old,name).toarray(),rtol=1e-10,atol=1e-18)


if __name__=='__main__':unittest.main()

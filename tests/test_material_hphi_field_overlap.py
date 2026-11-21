# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from numpy.polynomial.legendre import leggauss
from test_material_hphi_comparison import partition,request
from test_rf_materials import partition as original_partition
from test_hphi_geometry_mapping import transformed
from superfish_ng.constants import EPS0,MU0,TAU
from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi
from superfish_ng.material_hphi_rf import material_hphi_quantities
from superfish_ng.rf_materials import RFMaterialPartition
from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping
from superfish_ng.material_hphi_field_overlap import material_hphi_field_grams


def independent_grams(solution):
    # Independent tensor Gauss + local Vandermonde polynomial reconstruction.
    points,weights=leggauss(24);points=(points+1)/2;weights=weights/2
    x,y=np.meshgrid(points,points,indexing='ij');xi=x.ravel();eta=((1-x)*y).ravel()
    w=(weights[:,None]*weights[None,:]*(1-x)).ravel();n=solution.case.modes
    result=[np.zeros((n,n)),np.zeros((n,n))]
    for cell,indices in enumerate(solution.space.cell_dofs):
        vertices=solution.space.mesh.points[solution.space.mesh.triangles[cell]];origin=vertices[0]
        jac=np.column_stack((vertices[1]-origin,vertices[2]-origin));inv=np.linalg.inv(jac)
        nodes=(solution.space.dof_points[indices]-origin)@inv.T
        def monomials(u,v):return np.column_stack([np.ones_like(u),u,v]+([u*u,u*v,v*v] if len(indices)==6 else []))
        coefficients=np.linalg.solve(monomials(*nodes.T),solution.coefficients[indices])
        scalar=monomials(xi,eta)@coefficients
        dx=np.column_stack([xi*0,xi*0+1,xi*0]+([2*xi,eta,xi*0] if len(indices)==6 else []))@coefficients
        dy=np.column_stack([xi*0,xi*0,xi*0+1]+([xi*0,xi,2*eta] if len(indices)==6 else []))@coefficients
        dr=inv[0,0]*dx+inv[1,0]*dy;dz=inv[0,1]*dx+inv[1,1]*dy
        r=(origin[0]+jac[0,0]*xi+jac[0,1]*eta)[:,None]
        eps=solution.case.partition.epsilon_r[cell];mu=solution.case.partition.mu_r[cell];omega=TAU*solution.frequencies_hz
        if solution.case.axis_connected:h=r*scalar;er=r*dz/(EPS0*eps*omega);ez=-(2*scalar+r*dr)/(EPS0*eps*omega)
        else:h=scalar/r;er=dz/(r*EPS0*eps*omega);ez=-dr/(r*EPS0*eps*omega)
        measure=TAU*r*w[:,None]*np.linalg.det(jac)
        result[0]+=EPS0*eps*(er.T@(measure*er)+ez.T@(measure*ez));result[1]+=MU0*mu*(h.T@(measure*h))
    return result


class MaterialHphiFieldOverlapTests(unittest.TestCase):
    def test_independent_piecewise_energy_integrals_and_unchanged_rf(self):
        for axis in (False,True):
            for order in (1,2):
                p=partition(1,1,axis);s=solve_material_hphi(MaterialHphiCase(p,element_order=order,modes=2))
                before=[material_hphi_quantities(s,i) for i in range(2)];coefficients=s.coefficients.copy()
                grams=material_hphi_field_grams(s,s,request(p,p));expected=independent_grams(s)
                for matrices,reference in zip((grams.electric,grams.magnetic),expected):
                    for actual in matrices:np.testing.assert_allclose(actual,reference,rtol=2e-10,atol=2e-10)
                    np.testing.assert_allclose(np.diag(reference),2*s.case.normalization_j,rtol=2e-9)
                np.testing.assert_array_equal(s.coefficients,coefficients)
                self.assertEqual(before,[material_hphi_quantities(s,i) for i in range(2)])

    def test_fixed_material_scale_cross_gram_phase_and_frequency(self):
        a=partition(1);b=RFMaterialPartition(transformed(a.mesh,lambda p:2*p),a.materials,a.regions)
        old,new=[solve_material_hphi(MaterialHphiCase(p,modes=2)) for p in (a,b)]
        mapping=HphiGeometryMapping(a.mesh,b.mesh);q=request(a,b,mapping)
        new.coefficients[:,0]*=-1
        grams=material_hphi_field_grams(old,new,q);reverse=material_hphi_field_grams(new,old,request(b,a,mapping.inverse()))
        np.testing.assert_allclose(new.frequencies_hz*2,old.frequencies_hz,rtol=1e-10)
        for forward,back in zip((grams.electric,grams.magnetic),(reverse.electric,reverse.magnetic)):
            np.testing.assert_allclose(np.abs(np.diag(forward[1])),2.,rtol=1e-9)
            self.assertLess(forward[1][0,0],0)
            np.testing.assert_allclose(forward[1],back[1].T,rtol=1e-10,atol=1e-10)

    def test_uniform_material_and_vacuum_limit(self):
        from superfish_ng.axis_hphi import AxisHphiCase,solve_axis_hphi
        from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh
        from superfish_ng.hphi_field_overlap import hphi_field_grams
        for axis in (False,True):
            for order in (1,2):
                p=original_partition(axis,1,uniform=(1.,1.));s=solve_material_hphi(MaterialHphiCase(p,element_order=order,modes=2))
                vacuum=(solve_axis_hphi(AxisHphiCase(p.mesh,element_order=order,modes=2)) if axis else
                        solve_hphi_mesh(HphiMeshCase(p.mesh,element_order=order,modes=2)))
                actual=material_hphi_field_grams(s,s,request(p,p));reference=hphi_field_grams(vacuum,vacuum)
                for new,old,factor in ((actual.electric,reference.electric,EPS0),(actual.magnetic,reference.magnetic,MU0)):
                    for a,b in zip(new,old):np.testing.assert_allclose(a,factor*b,rtol=1e-9,atol=1e-9)
                material=original_partition(axis,1,uniform=(4.,9.));m=solve_material_hphi(MaterialHphiCase(material,element_order=order,modes=2))
                np.testing.assert_allclose(6*m.frequencies_hz,s.frequencies_hz,rtol=1e-10)
                weighted=material_hphi_field_grams(m,m,request(material,material))
                for matrices in (weighted.electric,weighted.magnetic):np.testing.assert_allclose(np.diag(matrices[0]),2.,rtol=1e-9)

    def test_independent_piecewise_cross_density_integral(self):
        from types import SimpleNamespace
        from superfish_ng.material_hphi_field_overlap import _integrate_fields
        from superfish_ng.material_hphi_comparison import material_hphi_overlay
        a=partition(1)
        def change(p):return np.column_stack((2*p[:,0],np.where(p[:,1]<=1/32,2*p[:,1],p[:,1]+1/32)))
        b=RFMaterialPartition(transformed(a.mesh,change),a.materials,a.regions)
        overlay=material_hphi_overlay(request(a,b,HphiGeometryMapping(a.mesh,b.mesh))).overlay
        class Integrand:
            def __init__(self,p,values):self.case=SimpleNamespace(modes=1,partition=p);self.values=values
            def fields_in_cells(self,cells,bary,mode):
                return {name:np.full(len(cells),value) for name,value in zip(('Er_quadrature_V_per_m','Ez_quadrature_V_per_m','Hphi_real_A_per_m'),self.values)}
        left,right=Integrand(a,(1.,2.,3.)),Integrand(b,(5.,6.,7.))
        result=_integrate_fields(left,right,overlay,8)
        volumes=np.pi*((4/32)**2-(1/32)**2)*np.array([1/32,2/32]);ratio=np.array([8.,4.])
        for matrices,density,aa,ab,bb in ((result[0],EPS0*np.array([2.,5.]),5.,17.,61.),
                                       (result[1],MU0*np.array([3.,7.]),9.,21.,49.)):
            expected=[aa*np.sum(density*volumes),ab*np.sum(density*volumes*np.sqrt(ratio)),bb*np.sum(density*volumes*ratio)]
            for actual,value in zip(matrices,expected):self.assertAlmostEqual(actual[0,0]/value,1.,delta=1e-13)
        with self.assertRaises(ValueError):material_hphi_field_grams(left,right,request(a,b,HphiGeometryMapping(a.mesh,b.mesh)))

    def test_strict_original_binding_and_preflight(self):
        from unittest.mock import patch
        import superfish_ng.material_hphi_field_overlap as module
        p=partition();s=solve_material_hphi(MaterialHphiCase(p,modes=2));q=request(p,p)
        with patch.object(module,'verified_material_hphi_solution',side_effect=AssertionError('preflight first')):
            with self.assertRaises(ValueError):material_hphi_field_grams(s,s,q,max_gram_modes=1)
        with self.assertRaises(ValueError):material_hphi_field_grams(s,s,q,max_sample_points=1)
        p2=partition(2)
        with self.assertRaisesRegex(ValueError,'partition'):material_hphi_field_grams(s,s,request(p2,p2))
        wrong=replace(s,space=replace(s.space,dof_points=s.space.dof_points+1.))
        with self.assertRaises(ValueError):material_hphi_field_grams(wrong,s,q)


if __name__=='__main__':unittest.main()

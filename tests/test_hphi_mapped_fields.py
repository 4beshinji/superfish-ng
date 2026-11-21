# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng.constants import C0, EPS0, MU0
from superfish_ng.coaxial import CoaxialCase, solve_coaxial
from superfish_ng.axis_hphi import AxisHphiCase, solve_axis_hphi
from superfish_ng.hphi_mesh import HphiMeshCase, solve_hphi_mesh
from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping, coaxial_dimension_mapping
from superfish_ng.hphi_field_overlap import hphi_field_grams, _declared_mesh
from superfish_ng.hphi_tuning import _refine_mesh
from superfish_ng.hphi_mass_projection import hphi_mass_coupling, project_hphi_coefficients
from test_meridional_overlap import fixture
from test_hphi_geometry_mapping import transformed


class HphiMappedFieldsTests(unittest.TestCase):
    def test_unitary_scalar_mass_independent_radial_integral(self):
        a, b = CoaxialCase(.0625,.125,.5), CoaxialCase(.078125,.15625,.75)
        mapping = coaxial_dimension_mapping(a,b)
        coupling = hphi_mass_coupling(mapping.previous,mapping.current,geometry_mapping=mapping)
        x,w = np.polynomial.legendre.leggauss(100)
        r = b.inner_radius_m+(x+1)*(b.outer_radius_m-b.inner_radius_m)/2
        sr = (b.outer_radius_m-b.inner_radius_m)/(a.outer_radius_m-a.inner_radius_m)
        old = a.inner_radius_m+(r-b.inner_radius_m)/sr
        determinant = sr*b.length_m/a.length_m
        expected = b.length_m*(b.outer_radius_m-b.inner_radius_m)/2*np.dot(w,1/np.sqrt(old*r*determinant))
        self.assertAlmostEqual(float(coupling.cross_mass.sum())/expected,1.,delta=1e-12)
        self.assertAlmostEqual(float(coupling.previous_mass.sum())/(a.length_m*np.log(a.outer_radius_m/a.inner_radius_m)),1.,delta=1e-12)
        reverse = hphi_mass_coupling(mapping.current,mapping.previous,geometry_mapping=mapping.inverse())
        np.testing.assert_allclose(coupling.cross_mass.toarray(),reverse.cross_mass.T.toarray(),rtol=2e-12,atol=1e-14)

    def test_scalar_uniform_scale_projection_q_and_u(self):
        for axis in (False,True):
            old = fixture(1,axis=axis)
            new = transformed(old,lambda p: p*2)
            mapping = HphiGeometryMapping(old,new)
            coupling = hphi_mass_coupling(old,new,geometry_mapping=mapping)
            r,z = coupling.previous_space.dof_points.T
            values = np.column_stack((np.ones(len(r)),r*z, z*z))
            result = project_hphi_coefficients(old,new,values,geometry_mapping=mapping)
            expected = values*2**(-2.5 if axis else -.5)
            np.testing.assert_allclose(result.coefficients,expected,rtol=1e-10,atol=1e-12)
            self.assertLess(max(result.diagnostic['relative_mass_error']),1e-11)
            self.assertLess(max(result.diagnostic['relative_pythagoras_defect']),1e-11)

    def test_real_fem_uniform_scale_equals_h02_in_both_fields(self):
        for axis in (False,True):
            old = fixture(1,axis=axis)
            new = transformed(old,lambda p: p*2)
            cls,solver = (AxisHphiCase,solve_axis_hphi) if axis else (HphiMeshCase,solve_hphi_mesh)
            a,b = [solver(cls(mesh,modes=3)) for mesh in (old,new)]
            original = hphi_field_grams(a,b,previous_scale=2)
            mapped = hphi_field_grams(a,b,geometry_mapping=HphiGeometryMapping(old,new))
            for family in ('electric','magnetic'):
                for left,right in zip(getattr(original,family),getattr(mapped,family)):
                    np.testing.assert_allclose(left,right,rtol=1e-9,atol=np.max(abs(left))*1e-10)
            with self.assertRaisesRegex(ValueError,'never both'):
                hphi_field_grams(a,b,previous_scale=2,geometry_mapping=HphiGeometryMapping(old,new))

    def test_coaxial_tem_independent_overlap_energy_and_reverse(self):
        a = solve_coaxial(CoaxialCase(.0625,.125,.5,nr=3,nz=12,modes=3,quadrature_order=12))
        b = solve_coaxial(CoaxialCase(.078125,.171875,.75,nr=4,nz=12,modes=3,quadrature_order=12))
        mapping = coaxial_dimension_mapping(a.case,b.case)
        forward = hphi_field_grams(a,b,geometry_mapping=mapping)
        reverse = hphi_field_grams(b,a,geometry_mapping=mapping.inverse())
        x,w = np.polynomial.legendre.leggauss(100)
        ra,rb = a.case.inner_radius_m,a.case.outer_radius_m
        rc,rd = b.case.inner_radius_m,b.case.outer_radius_m
        sr = (rd-rc)/(rb-ra)
        r = rc+(x+1)*(rd-rc)/2
        old = ra+(r-rc)/sr
        expected = (rd-rc)/2*np.dot(w,1/np.sqrt(old*r))/np.sqrt(sr*np.log(rb/ra)*np.log(rd/rc))
        for solution in (a,b):
            self.assertAlmostEqual(solution.frequencies_hz[0]/(C0/(2*solution.case.length_m)),1.,delta=4e-6)
        for family,constant in (('electric',EPS0),('magnetic',MU0)):
            aa,ab,bb = getattr(forward,family)
            np.testing.assert_allclose(constant*aa/4,np.eye(3)/2,rtol=1e-8,atol=1e-10)
            np.testing.assert_allclose(constant*bb/4,np.eye(3)/2,rtol=1e-8,atol=1e-10)
            np.testing.assert_allclose(ab,getattr(reverse,family)[1].T,rtol=1e-8,atol=np.max(abs(ab))*1e-10)
            self.assertAlmostEqual(abs(ab[0,0])/np.sqrt(aa[0,0]*bb[0,0]),expected,delta=2e-7)

    def test_nonuniform_projection_improves_under_nested_refinement(self):
        for axis in (False,True):
            old = fixture(1,axis=axis)
            origin = 0 if axis else 1/32
            def move(p):
                result = p.copy()
                result[:,0] += np.interp(p[:,0],origin+np.arange(4)/32,[0,1/256,1/256,0])
                return result
            new = transformed(old,move)
            mapping = HphiGeometryMapping(old,new)
            coupling = hphi_mass_coupling(old,new,previous_order=1,current_order=1,geometry_mapping=mapping)
            values = np.ones((len(coupling.previous_space.dof_points),1))
            coarse = project_hphi_coefficients(old,new,values,previous_order=1,current_order=1,geometry_mapping=mapping)
            fine = project_hphi_coefficients(old,_refine_mesh(new),values,previous_order=1,current_order=1,geometry_mapping=mapping)
            error = coarse.diagnostic['relative_mass_error'][0]
            self.assertGreater(error,1e-4)
            self.assertLess(fine.diagnostic['relative_mass_error'][0],error)
            self.assertLess(fine.diagnostic['relative_pythagoras_defect'][0],1e-10)
            np.testing.assert_allclose(coarse.diagnostic['source_squared_mass_norm'],fine.diagnostic['source_squared_mass_norm'],rtol=0,atol=0)

    def test_geometry_declaration_roundtrip_and_strict_rejection(self):
        mesh = fixture(1)
        mapping = HphiGeometryMapping(mesh,mesh)
        self.assertEqual(HphiGeometryMapping.from_dict(mapping.to_dict()).to_dict(),mapping.to_dict())
        for key,value in (('schema_version',True),('kind','automatic'),('extra',0),('previous',None)):
            raw = mapping.to_dict();raw[key] = value
            with self.assertRaises(ValueError): HphiGeometryMapping.from_dict(raw)

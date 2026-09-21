# SPDX-License-Identifier: Apache-2.0
"""Independent integrals and actual native Maxwell tests for curved E/H Grams."""
from dataclasses import replace
from types import SimpleNamespace
import unittest
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.curved_hphi import CurvedHphiCase,solve_curved_hphi
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain,build_curved_hphi_comparison
from superfish_ng.constants import EPS0,MU0
from test_curved_hphi_comparison import charts


def case(axis=False,n=1,scale=1.,shear=1.,holes=1):
    data,_=fixture(axis,holes,n=n,scale=scale,shear=shear)
    return CurvedHphiCase(CurvedMeridionalGeometry(**data),modes=3,quadrature_order=12)


class CurvedHphiFieldOverlapTests(unittest.TestCase):
    def test_known_vector_field_integrals_on_all_components(self):
        from superfish_ng.curved_hphi_field_overlap import _integrate_fields
        for axis in (False,True):
            c=case(axis,holes=2);g=c.geometry
            overlay=build_curved_hphi_comparison(g,g,CurvedHphiComparisonDomain(g,g,'same_vacuum'))
            def fields(cells,bary,mode):
                r=np.einsum('qi,qi->q',bary,g.base_mesh.points_rz_m[g.base_mesh.triangles[cells],0])
                return dict(Er_quadrature_V_per_m=np.zeros(len(cells)),Ez_quadrature_V_per_m=np.ones(len(cells)),Hphi_real_A_per_m=r)
            integrand=SimpleNamespace(case=SimpleNamespace(modes=1),fields_in_cells=fields)
            grams=_integrate_fields(integrand,integrand,overlay,8,100000)
            original,_=fixture(axis,2,shear=0.);mesh=original['base_mesh'];electric=magnetic=0.
            for sign,loop in [(1,mesh.outer_rz_m),*((-1,h) for h in mesh.holes_rz_m)]:
                a,z0=loop.min(axis=0);b,z1=loop.max(axis=0)
                electric+=sign*np.pi*(b*b-a*a)*(z1-z0)
                magnetic+=sign*np.pi/2*(b**4-a**4)*(z1-z0)
            for family,expected in zip(grams,(electric,magnetic)):
                for matrix in family:self.assertAlmostEqual(matrix[0,0]/expected,1.,places=12)

    def test_actual_two_scale_native_grams_and_energy(self):
        from superfish_ng.curved_hphi_field_overlap import curved_hphi_field_grams
        for axis in (False,True):
            a=solve_curved_hphi(case(axis));b=solve_curved_hphi(case(axis,scale=2.))
            before=[s.coefficients.copy() for s in (a,b)]
            domain=CurvedHphiComparisonDomain(a.case.geometry,b.case.geometry,'declared_quadratic')
            grams=curved_hphi_field_grams(a,b,domain)
            np.testing.assert_allclose(b.frequencies_hz/a.frequencies_hz,.5,rtol=1e-10)
            for family,constant in ((grams.electric,EPS0),(grams.magnetic,MU0)):
                for matrix in (family[0],family[2]):np.testing.assert_allclose(np.diag(matrix),2/constant,rtol=1e-9)
                overlap=family[1]/np.sqrt(np.diag(family[0])[:,None]*np.diag(family[2])[None,:])
                np.testing.assert_allclose(abs(overlap),np.eye(3),atol=1e-9,rtol=0)
            for s,old in zip((a,b),before):np.testing.assert_array_equal(s.coefficients,old)
            self.assertEqual(grams.diagnostic['excluded_static_dimensions'],[0,0] if axis else [1,1])
            self.assertEqual(grams.diagnostic['mode_tracking'],'not_performed')

    def test_native_refinement_and_straight_limit(self):
        from superfish_ng.curved_hphi_field_overlap import curved_hphi_field_grams
        from superfish_ng.axis_hphi import AxisHphiCase,solve_axis_hphi
        from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh
        from superfish_ng.hphi_field_overlap import hphi_field_grams
        for axis in (False,True):
            a=solve_curved_hphi(case(axis,shear=0.));b=solve_curved_hphi(case(axis,n=2,shear=0.))
            g=a.case.geometry;domain=CurvedHphiComparisonDomain(g,g,'same_vacuum')
            grams=curved_hphi_field_grams(a,b,domain,current_cells=charts(g,b.case.geometry,alpha=0.))
            native=[]
            for s in (a,b):
                cls,solve=(AxisHphiCase,solve_axis_hphi) if axis else (HphiMeshCase,solve_hphi_mesh)
                options=dict(element_order=2,modes=3)
                if not axis:options['quadrature_order']=12
                native.append(solve(cls(s.case.geometry.base_mesh,**options)))
            reference=hphi_field_grams(*native)
            for actual,expected in ((grams.electric,reference.electric),(grams.magnetic,reference.magnetic)):
                for x,y in zip(actual,expected):
                    scale=np.max(abs(y));np.testing.assert_allclose(abs(x)/scale,abs(y)/scale,atol=1e-9,rtol=0)

    def test_public_reader_rejects_modified_fields_space_and_budget(self):
        from superfish_ng.curved_hphi_field_overlap import curved_hphi_field_grams
        a=solve_curved_hphi(case());g=a.case.geometry;domain=CurvedHphiComparisonDomain(g,g,'same_vacuum')
        for changed in (replace(a,coefficients=a.coefficients*2),replace(a,frequencies_hz=a.frequencies_hz*1.01),SimpleNamespace(case=a.case)):
            with self.assertRaises(ValueError):curved_hphi_field_grams(a,changed,domain)
        for control in ('max_gram_modes','max_sample_points','max_overlay_triangles'):
            with self.assertRaises(ValueError):curved_hphi_field_grams(a,a,domain,**{control:1})
        with self.assertRaises(ValueError):curved_hphi_field_grams(a,a,domain,quadrature_order=True)
        changed=replace(a,space=replace(a.space,dof_points=a.space.dof_points*2))
        with self.assertRaisesRegex(ValueError,'space'):curved_hphi_field_grams(a,changed,domain)

    def test_nonuniform_known_density_and_saved_native_reverse(self):
        from pathlib import Path
        import tempfile
        from superfish_ng.curved_hphi_field_overlap import _integrate_fields,curved_hphi_field_grams
        from superfish_ng.curved_hphi_saved import save_curved_hphi_run,read_curved_hphi_run,_snapshot
        a=case();b=case(scale=2.,shear=.5)
        domain=CurvedHphiComparisonDomain(a.geometry,b.geometry,'declared_quadratic')
        overlay=build_curved_hphi_comparison(a.geometry,b.geometry,domain)
        def integrand(g):
            def fields(cells,bary,mode):
                r=np.einsum('qi,qi->q',bary,g.base_mesh.points_rz_m[g.base_mesh.triangles[cells],0])
                return dict(Er_quadrature_V_per_m=np.zeros(len(cells)),Ez_quadrature_V_per_m=np.ones(len(cells)),Hphi_real_A_per_m=r)
            return SimpleNamespace(case=SimpleNamespace(modes=1),fields_in_cells=fields)
        grams=_integrate_fields(integrand(a.geometry),integrand(b.geometry),overlay,8,100000)
        original,_=fixture(False,1,shear=0.);mesh=original['base_mesh'];h=0.
        for sign,loop in [(1,mesh.outer_rz_m),(-1,mesh.holes_rz_m[0])]:
            r0,z0=loop.min(axis=0);r1,z1=loop.max(axis=0);h+=sign*np.pi/2*(r1**4-r0**4)*(z1-z0)
        for family,expected,scale in ((grams[0],a.geometry.volume_m3,8.),(grams[1],h,32.)):
            for matrix,value in zip(family,(expected,expected*np.sqrt(scale),expected*scale)):
                self.assertAlmostEqual(matrix[0,0]/value,1.,places=12)
        with tempfile.TemporaryDirectory() as tmp:
            originals=[solve_curved_hphi(c) for c in (a,b)];paths=[Path(tmp)/name for name in ('previous','current')]
            for solution,path in zip(originals,paths):save_curved_hphi_run(solution.case,solution,path)
            hashes=[_snapshot(path) for path in paths]
            restored=[read_curved_hphi_run(path) for path in paths]
            forward=curved_hphi_field_grams(*restored,domain)
            backward=curved_hphi_field_grams(*restored[::-1],domain.inverse())
            for left,right in ((forward.electric,backward.electric),(forward.magnetic,backward.magnetic)):
                np.testing.assert_allclose(left[1],right[1].T,rtol=1e-12,atol=1e-6)
            self.assertEqual(hashes,[_snapshot(path) for path in paths])
            with self.assertRaisesRegex(ValueError,'quadrature'):
                curved_hphi_field_grams(*restored,domain,quadrature_order=2)

    def test_chunked_known_integrals_preserve_physical_measure(self):
        from unittest.mock import patch
        # Force one triangle per batch and retain the independent analytical
        # moments, so storage changes cannot silently discard integration cells.
        with patch('superfish_ng.curved_hphi_field_overlap._SAMPLE_MODE_BATCH',1):
            self.test_known_vector_field_integrals_on_all_components()

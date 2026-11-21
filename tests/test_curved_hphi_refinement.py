# SPDX-License-Identifier: Apache-2.0
"""Native P2 restrictions, declared binary64 rounding, and scalar mass invariants."""
from copy import deepcopy
import unittest
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain,build_curved_hphi_comparison
from superfish_ng.curved_hphi_fem import curved_hphi_matrices
from test_curved_hphi_comparison import charts


def geometry(axis=False,holes=1,n=1,scale=.7):
    data,exact=fixture(axis,holes,n=n,scale=scale)
    return CurvedMeridionalGeometry(**data),exact


class CurvedHphiRefinementTests(unittest.TestCase):
    def test_non_dyadic_refinement_requires_explicit_roundoff_contract(self):
        a,exact=geometry();b,_=geometry(n=2)
        x,_=geometry(scale=1.);y,_=geometry(n=2,scale=1.);cells=charts(x,y)
        self.assertAlmostEqual(a.volume_m3/exact['volume_m3'],1.,places=13)
        with self.assertRaisesRegex(ValueError,'quadratic restriction'):
            build_curved_hphi_comparison(a,b,CurvedHphiComparisonDomain(a,a,'same_vacuum'),current_cells=cells)
        from superfish_ng.curved_hphi_refinement import refine_curved_hphi_geometry
        refined=refine_curved_hphi_geometry(a)
        domain=CurvedHphiComparisonDomain(a,a,'same_vacuum',restriction_policy='binary64_roundoff')
        overlay=build_curved_hphi_comparison(a,refined.geometry,domain,current_cells=refined.native_cells)
        self.assertGreater(overlay.report['maximum_native_coordinate_error_bound_m'],0.)
        self.assertFalse(overlay.report['exact_native_restrictions'])
        self.assertEqual(domain.to_dict()['schema_version'],2)
        self.assertEqual(CurvedHphiComparisonDomain.from_dict(domain.to_dict()).to_dict(),domain.to_dict())
        self.assertEqual(CurvedHphiComparisonDomain(a,a,'same_vacuum').to_dict()['schema_version'],1)

    def test_all_holes_axis_scalar_mass_and_constant_preservation(self):
        from superfish_ng.curved_hphi_refinement import refine_curved_hphi_geometry
        for axis in (False,True):
            for order in (1,2):
                a,exact=geometry(axis,2)
                refined=refine_curved_hphi_geometry(a,element_order=order)
                b=refined.geometry
                self.assertEqual(len(b.cell_nodes),4*len(a.cell_nodes))
                self.assertEqual(b.validation['boundary_components'],3)
                self.assertAlmostEqual(b.area_m2/exact['area_m2'],1.,places=13)
                self.assertAlmostEqual(b.volume_m3/exact['volume_m3'],1.,places=13)
                domain=CurvedHphiComparisonDomain(a,a,'same_vacuum',restriction_policy='binary64_roundoff')
                overlay=build_curved_hphi_comparison(a,b,domain,current_cells=refined.native_cells)
                self.assertEqual(overlay.report['base_reference_areas'],[[1,2]]*len(a.cell_nodes))
                old,ko,mo,_=curved_hphi_matrices(a,order);new,kn,mn,_=curved_hphi_matrices(b,order)
                p=refined.prolongation
                np.testing.assert_allclose(p@np.ones(mo.shape[0]),1.,rtol=0,atol=1e-15)
                self.assertLess(np.linalg.norm((p.T@mn@p-mo).toarray())/np.linalg.norm(mo.toarray()),1e-10)
                self.assertLess(np.linalg.norm((p.T@kn@p-ko).toarray())/np.linalg.norm(ko.toarray()),1e-10)
                if axis:
                    self.assertTrue(np.all(new.dof_points[new.axis_dofs,0]==0))
                else:
                    ones=np.ones(mn.shape[0]);self.assertLess(np.linalg.norm(kn@ones)/np.linalg.norm(kn.data),1e-12)

    def test_roundoff_does_not_permit_geometry_changes_or_budget_bypass(self):
        from superfish_ng.curved_hphi_refinement import refine_curved_hphi_geometry
        a,_=geometry();refined=refine_curved_hphi_geometry(a)
        domain=CurvedHphiComparisonDomain(a,a,'same_vacuum',restriction_policy='binary64_roundoff')
        raw=refined.geometry.to_dict();raw['edge_midpoints_rz_m'][0][1]+=1e-8
        b=CurvedMeridionalGeometry.from_dict(raw)
        with self.assertRaisesRegex(ValueError,'roundoff'):
            build_curved_hphi_comparison(a,b,domain,current_cells=refined.native_cells)
        for name in ('max_triangles','max_dofs','max_pair_tests'):
            with self.assertRaises(ValueError):refine_curved_hphi_geometry(a,**{name:1})
        with self.assertRaises(ValueError):refine_curved_hphi_geometry(a,element_order=True)
        for key,value in (('schema_version',True),('native_restriction','guess'),('roundoff_tolerance',1.)):
            raw=domain.to_dict();raw[key]=value
            with self.assertRaises(ValueError):CurvedHphiComparisonDomain.from_dict(raw)
        # Even the rounded-native policy keeps exact reference-domain equality.
        raw=a.to_dict();raw['edge_midpoints_rz_m'][0][1]+=np.spacing(raw['edge_midpoints_rz_m'][0][1])
        b=CurvedMeridionalGeometry.from_dict(raw)
        with self.assertRaisesRegex(ValueError,'same_vacuum'):
            CurvedHphiComparisonDomain(a,b,'same_vacuum',restriction_policy='binary64_roundoff')

    def test_repeated_refinement_retains_root_geometry_and_mass(self):
        from fractions import Fraction as F
        from superfish_ng.curved_hphi_refinement import refine_curved_hphi_geometry
        for axis in (False,True):
            a,_=geometry(axis);first=refine_curved_hphi_geometry(a);second=refine_curved_hphi_geometry(first.geometry)
            combined=[]
            for child in second.native_cells:
                parent=first.native_cells[child['base_cell']]
                v=[[F(*x) for x in row] for row in parent['reference_vertices']];points=[]
                for raw in child['reference_vertices']:
                    x,y=map(lambda p:F(*p),raw)
                    p=[v[0][k]*(1-x-y)+v[1][k]*x+v[2][k]*y for k in (0,1)]
                    points.append([[x.numerator,x.denominator] for x in p])
                combined.append(dict(base_cell=parent['base_cell'],reference_vertices=points))
            domain=CurvedHphiComparisonDomain(a,a,'same_vacuum',restriction_policy='binary64_roundoff')
            result=build_curved_hphi_comparison(a,second.geometry,domain,current_cells=combined)
            self.assertEqual(result.report['base_reference_areas'],[[1,2]]*len(a.cell_nodes))
            _,_,old,_=curved_hphi_matrices(a);_,_,new,_=curved_hphi_matrices(second.geometry)
            p=second.prolongation@first.prolongation
            self.assertLess(np.linalg.norm((p.T@new@p-old).toarray())/np.linalg.norm(old.toarray()),1e-10)

    def test_large_coordinate_offset_does_not_hide_unresolved_roundoff(self):
        from superfish_ng.curved_hphi_refinement import refine_curved_hphi_geometry
        data,_=fixture(False,1,scale=.7,z_offset=64.)
        g=CurvedMeridionalGeometry(**data)
        with self.assertRaisesRegex(ValueError,'roundoff is unresolved relative to the cell size'):
            refine_curved_hphi_geometry(g)

    def test_reported_rational_error_bounds_are_outward_rounded(self):
        from fractions import Fraction as F
        from superfish_ng.curved_hphi_comparison import _upper_float
        for exact in (F(0),F(1,3),F(1,10**400),F(1,2**50)):
            bound=_upper_float(exact)
            self.assertGreaterEqual(F(bound),exact)
            if bound>0:self.assertLessEqual(F(float(np.nextafter(bound,0.))),exact)

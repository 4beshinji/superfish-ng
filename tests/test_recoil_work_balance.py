# SPDX-License-Identifier: Apache-2.0
"""Zero B with finite demagnetizing H must survive cancelling boundary work."""
import unittest
import numpy as np
from scripts.planar_recoil_reference import uniform_remanence
from scripts.off_axis_recoil_reference import blocked_flux
from superfish_ng.planar_recoil import PlanarRecoilCase,solve_planar_recoil,planar_recoil_quantities
from superfish_ng.off_axis_recoil import solve_off_axis_recoil,off_axis_recoil_quantities
from superfish_ng.magnetostatic_boundary import MagnetostaticBoundary


class RecoilWorkBalanceTests(unittest.TestCase):
    def test_planar_constant_Az_zero_B_nonzero_H_with_opposite_fixed_boundaries(self):
        for order in (1,2):
            source,_=uniform_remanence(order=order);p=source.partition;mesh=p.mesh;lo,hi=mesh.points_xy_m[:,1].min(),mesh.points_xy_m[:,1].max();groups=dict(bottom=[],top=[],sides=[])
            for i,edge in enumerate(mesh.boundary_edges):
                y=mesh.points_xy_m[edge,1];groups['bottom' if np.all(y==lo) else 'top' if np.all(y==hi) else 'sides'].append(i)
            for value in (0.,.125,-.25):
                boundaries=[MagnetostaticBoundary(name,'fixed_az',groups[name],value) for name in ('bottom','top')]+[MagnetostaticBoundary('sides','tangential_h',groups['sides'],0.)]
                case=PlanarRecoilCase(p,dict(source.current_density_z_a_per_m2),boundaries,order);s=solve_planar_recoil(case);q=planar_recoil_quantities(s)
                fields=s.fields_in_cells(np.arange(len(mesh.triangles)),np.full((len(mesh.triangles),3),1/3))
                expected_h=-p.remanent_h_a_per_m
                self.assertLess(np.max(abs(np.column_stack((fields['Bx_T'],fields['By_T']))))/.1,1e-10)
                self.assertLess(np.linalg.norm(np.column_stack((fields['Hx_A_per_m'],fields['Hy_A_per_m']))-expected_h)/np.linalg.norm(expected_h),1e-10)
                np.testing.assert_allclose(s.az_wb_per_m,value,rtol=0.,atol=1e-14)
                self.assertGreater(q['remanent_reference_constant_j_per_m'],0.)
                self.assertLess(q['b_quadratic_j_per_m']/q['remanent_reference_constant_j_per_m'],1e-20)
                self.assertAlmostEqual(q['constitutive_potential_h0_j_per_m']/q['remanent_reference_constant_j_per_m'],1.,places=12)
                self.assertLess(q['discrete_work_relative_error'],1e-9)

    def test_positive_radius_constant_psi_zero_B_nonzero_H_and_reference_independence(self):
        for order in (1,2):
            for boundary in ('fixed','tangential'):
                quantities=[]
                for value in (0.,.125,-.25):
                    case,reference=blocked_flux(order,n=1,boundary=boundary,reference_psi=value);s=solve_off_axis_recoil(case);q=off_axis_recoil_quantities(s);quantities.append(q)
                    self.assertLess(q['b_quadratic_j']/q['remanent_reference_constant_j'],1e-20)
                    self.assertAlmostEqual(q['constitutive_potential_h0_j']/q['remanent_reference_constant_j'],1.,places=12)
                    self.assertLess(q['discrete_work_relative_error'],1e-9);self.assertLess(s.relative_residual,1e-10)
                    np.testing.assert_allclose(s.psi_wb,value,rtol=0.,atol=1e-14)
                    points=case.partition.mesh.points_rz_m[case.partition.mesh.triangles].mean(axis=1);actual=s.probe_at(points)['fields'];_,_,b,h=reference['fields'](points)
                    self.assertLess(np.linalg.norm(np.column_stack((actual['Br_T'],actual['Bz_T']))-b)/reference['field_scale'],1e-10)
                    self.assertLess(np.linalg.norm(np.column_stack((actual['Hr_A_per_m'],actual['Hz_A_per_m']))-h)/np.linalg.norm(h),1e-10)
                for q in quantities[1:]:self.assertEqual(q['remanent_reference_constant_j'],quantities[0]['remanent_reference_constant_j'])

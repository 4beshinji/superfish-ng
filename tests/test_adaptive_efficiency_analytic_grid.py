# SPDX-License-Identifier: Apache-2.0
"""Independent full-volume energy, Green moments and analytic wall peaks."""
from copy import deepcopy
from dataclasses import replace
import math
import unittest
from unittest.mock import patch

import numpy as np

from superfish_ng.adaptive_efficiency_analytic_grid import build_analytic_efficiency_grid
from superfish_ng.adaptive_efficiency_plan import build_adaptive_efficiency_plan
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.config import Case
from superfish_ng.constants import EPS0, MU0, TAU
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_to_dict


class AdaptiveEfficiencyAnalyticGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        plan = build_adaptive_efficiency_plan()
        cls.inputs = {row['id']:(Case.from_dict(row['request']['case']),
                                mesh_to_dict(make_mesh(Case.from_dict(row['request']['case']))))
                      for row in plan['cases'][:2]}

    def test_full_cylinder_and_sphere_volume_electric_magnetic_energy_both_orders(self):
        for name,(case,mesh) in self.inputs.items():
            for order in (16,24):
                with self.subTest(case=name,order=order):
                    grid = build_analytic_efficiency_grid(name,case,mesh,order=order)
                    weights, fields = grid['volume_weights_m3'], grid['reference_fields']
                    radius = .1 if name=='cylinder' else .08
                    volume = math.pi*radius**2*.2 if name=='cylinder' else 4*math.pi*radius**3/3
                    self.assertLess(abs(weights.sum()/volume-1),1e-12)
                    self.assertAlmostEqual(MU0/4*np.dot(weights,fields[:,2]**2),.5,places=11)
                    self.assertAlmostEqual(EPS0/4*np.dot(weights,np.sum(fields[:,:2]**2,axis=1)),.5,places=11)
                    self.assertAlmostEqual(grid['axis_weights_m'].sum(),case.length,places=14)
                    self.assertTrue(np.all(grid['axis_points_rz_m'][:,0]==0))
                    self.assertEqual(fields.shape,(len(weights),3))
                    self.assertTrue(np.all(weights>0) and np.all(grid['native_volume_density_ratio']>0))
                    self.assertIsNone(grid['physical_error_bound'])
                    self.assertEqual(grid['physical_acceptance_status'],'NATIVE_SOURCE_DOMAIN_ID_CHECKS_REQUIRED')
                    self.assertEqual(grid['case'],case.to_dict())
                    self.assertEqual(grid['source_mesh'],mesh)

    def test_sphere_whole_native_fan_volume_matches_independent_green_integral(self):
        case,mesh = self.inputs['sphere']
        space = case_curved_space(case,make_mesh(case))
        x,w = np.polynomial.legendre.leggauss(4)
        t = (x+1)/2
        basis = np.column_stack((2*(t-.5)*(t-1),2*t*(t-.5),4*t*(1-t)))
        derivative = np.column_stack((4*t-3,4*t-1,4-8*t))
        volume = 0.
        for nodes in space.geometry.boundary_nodes:
            wall = basis@space.geometry.points_rz_m[nodes]
            dz = (derivative@space.geometry.points_rz_m[nodes])[:,1]
            volume -= math.pi*np.dot(w/2,wall[:,0]**2*dz)
        for order in (16,24):
            grid = build_analytic_efficiency_grid('sphere',case,mesh,order=order)
            mapped = np.dot(grid['volume_weights_m3'],grid['native_volume_density_ratio'])
            self.assertLess(abs(mapped/volume-1),1e-12)
            self.assertTrue(np.any(grid['native_volume_points_rz_m'] != grid['analytic_volume_points_rz_m']))
            # The complete P2 sphere bulge is retained rather than evaluating
            # analytic fields at outside coordinates or dropping those nodes.
            self.assertLess(np.max(np.hypot(grid['analytic_volume_points_rz_m'][:,0],
                                           grid['analytic_volume_points_rz_m'][:,1]-.08)),.08)
            self.assertEqual(sum(len(v) for v in grid['native_wall_parameter_partitions']),
                             len(space.geometry.boundary_nodes[space.geometry.boundary_curve_indices==1])*2)

    def test_sphere_analytic_normal_e_and_h_peaks_full_wall_loss_and_rq_conventions(self):
        case,mesh = self.inputs['sphere']
        grid = build_analytic_efficiency_grid('sphere',case,mesh,order=16)
        reference = SphereTM(.08)
        q = grid['reference_quantities']
        theta = np.linspace(0,math.pi,1001)
        fields = reference.fields(np.column_stack((.08*np.sin(theta),.08*(1+np.cos(theta)))))
        e = np.hypot(fields['Er_quadrature_V_per_m'],fields['Ez_quadrature_V_per_m'])
        h = np.abs(fields['Hphi_A_per_m'])
        eacc = abs(complex(q['voltage_real_v'],q['voltage_imag_v']))/.16
        self.assertAlmostEqual(q['epk_over_eacc'],np.max(e)/eacc,places=12)
        self.assertAlmostEqual(q['bpk_over_eacc_mt_per_mv_per_m'],MU0*np.max(h)/eacc*1e9,places=11)
        pole = reference.fields([[0.,0.]])['Ez_quadrature_V_per_m'][0]
        equator = reference.fields([[.08,.08]])['Hphi_A_per_m'][0]
        self.assertAlmostEqual(pole/(2*equator/.08/(TAU*reference.frequency_hz*EPS0)),1.,places=12)
        x,w = np.polynomial.legendre.leggauss(32)
        wall = reference.fields(np.column_stack((.08*np.sqrt(1-x*x),.08*(1+x))))
        loss = q['surface_resistance_ohm']/2*2*math.pi*.08**2*np.dot(w,wall['Hphi_A_per_m']**2)
        self.assertLess(abs(loss/q['wall_loss_w']-1),1e-12)
        self.assertEqual(q['r_over_q_accelerator_ohm'],2*q['r_over_q_circuit_ohm'])

    def test_cylinder_density_is_identity_and_reference_matches_bessel_on_axis(self):
        case,mesh = self.inputs['cylinder']
        grid = build_analytic_efficiency_grid('cylinder',case,mesh,order=16)
        np.testing.assert_array_equal(grid['native_volume_density_ratio'],np.ones(len(grid['volume_weights_m3'])))
        np.testing.assert_array_equal(grid['native_volume_points_rz_m'],grid['analytic_volume_points_rz_m'])
        self.assertEqual(len(grid['volume_weights_m3']),4*5*16**2)
        self.assertEqual(len(grid['axis_weights_m']),5*16)
        self.assertTrue(np.all(grid['reference_fields'][:,0]==0))
        self.assertTrue(np.all(grid['reference_axis_ez']==grid['reference_axis_ez'][0]))
        q = grid['reference_quantities']
        self.assertEqual(q['r_over_q_accelerator_ohm'],2*q['r_over_q_circuit_ohm'])
        self.assertGreater(q['epk_over_eacc'],0)
        self.assertGreater(q['bpk_over_eacc_mt_per_mv_per_m'],0)

    def test_changed_case_mesh_and_unsupported_order_fail_before_reference_evaluation(self):
        case,mesh = self.inputs['sphere']
        wrong = deepcopy(mesh);wrong['points'][0][0] += 1e-6
        for actual_case,actual_mesh,order,name in (
                (replace(case,name='changed'),mesh,16,'sphere'),
                (replace(case,curved_refinement_levels=1),mesh,16,'sphere'),
                (case,wrong,16,'sphere'),(case,mesh,12,'sphere'),(case,mesh,True,'sphere'),
                (case,mesh,16,'rounded-two-lobe')):
            with patch('superfish_ng.analytic_sphere.SphereTM.fields',side_effect=AssertionError('reject before fields')):
                with self.assertRaises(ValueError):
                    build_analytic_efficiency_grid(name,actual_case,actual_mesh,order=order)


if __name__=='__main__':
    unittest.main()

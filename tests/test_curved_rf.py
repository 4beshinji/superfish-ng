# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import math
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.conics import LineSegment
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.curved_solution import solve_curved
from superfish_ng.curved_rf import quantities_curved,wall_h2_integral,accelerating_voltage_curved
from superfish_ng.rf import quantities


class CurvedRFTests(unittest.TestCase):
    def case(self,tag='pec'):
        vertices=((0.,0.),(.1,0.),(.1,.08),(0.,.08))
        return Case((),curved_contour=CurvedContour(tuple(LineSegment(vertices[i],vertices[(i+1)%4])
                    for i in range(4)),('axis','pec','pec',tag),0.),curve_chord_tolerance_m=.001,
                    contour_mesh=ContourMeshControls(.03),element_order=2,modes=1)

    def test_affine_rf_and_acceleration_overrides(self):
        for tag in ('pec','electric_symmetry','magnetic_symmetry'):
            case=replace(self.case(tag),beta=.13,active_length_m=.06,
                         voltage_interval_m=(.02,.08),phase_origin_m=.03)
            actual=quantities_curved(solve_curved(case))
            expected=quantities(case,solve(case))
            for key in ('stored_energy_j','wall_loss_w','geometry_factor_ohm','q0',
                        'r_over_q_accelerator_ohm','r_over_q_circuit_ohm',
                        'voltage_real_v','voltage_imag_v','eacc_v_per_m','transit_time_factor_abs'):
                self.assertAlmostEqual(actual[key]/expected[key],1,places=8)
            self.assertEqual(actual['active_length_m'],.06)
            self.assertEqual(actual['voltage_interval_start_m'],.02)
            self.assertEqual(actual['voltage_interval_end_m'],.08)
            self.assertEqual(actual['phase_origin_m'],.03)

    def test_constant_h_over_r_surface_integral_and_reversed_edges(self):
        solution=solve_curved(self.case())
        solution.u[:,0]=1.
        expected=2*math.pi*.08**3*.1+math.pi*.08**4
        self.assertAlmostEqual(wall_h2_integral(solution)/expected,1)
        # Reverse edge orientation without changing its nodes or midpoint.
        original=solution.space.geometry
        nodes=original.boundary_nodes.copy()
        nodes[:,:2]=nodes[:,1::-1]
        solution.space=replace(solution.space,geometry=replace(original,boundary_nodes=nodes))
        self.assertAlmostEqual(wall_h2_integral(solution)/expected,1)
        v,a=accelerating_voltage_curved(solution)
        self.assertTrue(np.isfinite((v.real,v.imag,a)).all())
        for order in (True,0,1,2.5):
            with self.assertRaises(ValueError):
                wall_h2_integral(solution,quadrature_order=order)
        with self.assertRaises(ValueError):
            quantities_curved(solution,True)
        shifted=original.points_rz_m.copy()
        axis_mid=int(original.boundary_nodes[solution.space.boundary_tags=='axis'][0,2])
        shifted[axis_mid,1]+=1e-15
        solution.space=replace(solution.space,geometry=replace(original,points_rz_m=shifted))
        with self.assertRaisesRegex(ValueError,'affine'):
            accelerating_voltage_curved(solution)

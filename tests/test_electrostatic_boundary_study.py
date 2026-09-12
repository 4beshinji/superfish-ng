# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scripts.electrostatic_boundary_reference import charged_slab,charged_coax
from superfish_ng.planar_electrostatic import solve_planar_electrostatic,planar_electrostatic_quantities
from superfish_ng.electrostatic import solve_axisymmetric_electrostatic,electrostatic_quantities


class FixedChargeBoundaryTests(unittest.TestCase):
    def test_planar_fixed_volume_charge_keeps_common_field_but_potential_grows_linearly(self):
        for sign in (-1.,1.):
            previous=None
            for ratio in (2.,4.,8.):
                case,exact=charged_slab(outer_ratio=ratio,sign=sign);s=solve_planar_electrostatic(case);q=planar_electrostatic_quantities(s)
                probe=s.probe_at(exact['common_points'])['fields'];phi,e,d=exact['fields'](exact['common_points'])
                np.testing.assert_allclose(probe['potential_V'],phi,rtol=1e-10,atol=1e-11)
                np.testing.assert_allclose(probe['Ey_V_per_m'],e[:,1],rtol=1e-10,atol=1e-10)
                np.testing.assert_allclose(probe['Dy_C_per_m2'],d[:,1],rtol=1e-10,atol=1e-20)
                self.assertAlmostEqual(q['energy_j_per_m']/exact['energy'],1.,places=10)
                for key in ('electrode_reaction_charge_c_per_m','electrode_original_field_charge_c_per_m'):self.assertAlmostEqual(q[key]['ground']/exact['ground_charge'],1.,places=10)
                self.assertIsNone(q['capacitance'])
                if previous is not None:
                    old,old_ref=previous;expected=old_ref['boundary_potential_shift'](exact['outer_distance_m'])
                    np.testing.assert_allclose(np.asarray(probe['potential_V'])-old['potential_V'],expected,rtol=1e-10,atol=1e-11)
                    np.testing.assert_allclose(probe['Ey_V_per_m'],old['Ey_V_per_m'],rtol=1e-10,atol=1e-10)
                previous=probe,exact

    def test_axis_fixed_inner_charge_refines_and_remote_ground_shift_is_logarithmic(self):
        for order in (1,2):
            errors=[]
            for n in (8,16,32):
                case,exact=charged_coax(order,n,outer_ratio=4.);s=solve_axisymmetric_electrostatic(case);q=electrostatic_quantities(s)
                cells=np.arange(len(case.partition.mesh.triangles));bary=np.full((len(cells),3),1/3);points=case.partition.mesh.points_rz_m[case.partition.mesh.triangles].mean(axis=1)
                fields=s.fields_in_cells(cells,bary);ref=exact['fields'](points);electric=np.column_stack((fields['Er_V_per_m'],fields['Ez_V_per_m']))
                errors.append([abs(q['energy_j']/exact['energy']-1),np.linalg.norm(electric-ref[1])/np.linalg.norm(ref[1]),abs(q['electrode_original_field_charge_c']['ground']/exact['ground_charge']-1)])
                self.assertAlmostEqual(q['electrode_reaction_charge_c']['ground']/exact['ground_charge'],1.,places=10);self.assertIsNone(q['capacitance'])
            self.assertTrue(np.all(np.diff(errors,axis=0)<0),errors)
            self.assertLess(max(errors[-1]),.03 if order==1 else .001)
        previous=None
        for ratio in (2.,4.,8.):
            case,exact=charged_coax(2,32,outer_ratio=ratio,sign=-1.,epsilon_r=7.);s=solve_axisymmetric_electrostatic(case);probe=s.probe_at(exact['common_points'])['fields']
            if previous is not None:
                old,old_ref=previous;expected=old_ref['boundary_potential_shift'](exact['outer_distance_m'])
                np.testing.assert_allclose((np.asarray(probe['potential_V'])-old['potential_V'])/expected,1.,rtol=1e-5,atol=0.)
                np.testing.assert_allclose(probe['Er_V_per_m'],old['Er_V_per_m'],rtol=.002,atol=0.)
            previous=probe,exact

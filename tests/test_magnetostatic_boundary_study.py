# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scripts.magnetostatic_boundary_reference import current_slab,current_cylinder
from superfish_ng.planar_magnetostatic import solve_planar_magnetostatic,planar_magnetostatic_quantities
from superfish_ng.axis_magnetostatic import solve_axis_magnetostatic,axis_magnetostatic_quantities


class FixedCurrentBoundaryTests(unittest.TestCase):
    def test_planar_fixed_current_keeps_B_H_while_Az_and_energy_grow(self):
        for sign in (-1.,1.):
            previous=None
            for ratio in (2.,4.,8.):
                case,exact=current_slab(outer_ratio=ratio,sign=sign);solution=solve_planar_magnetostatic(case);q=planar_magnetostatic_quantities(solution)
                fields=solution.probe_at(exact['common_points'])['fields'];az,b,h=exact['fields'](exact['common_points'])
                np.testing.assert_allclose(fields['Az_Wb_per_m'],az,rtol=1e-10,atol=1e-13)
                np.testing.assert_allclose(fields['Bx_T'],b[:,0],rtol=1e-10,atol=1e-13)
                np.testing.assert_allclose(fields['Hx_A_per_m'],h[:,0],rtol=1e-10,atol=1e-9)
                self.assertAlmostEqual(q['energy_j_per_m']/exact['energy'],1.,places=10)
                for key in ('fixed_boundary_reaction_current_a','fixed_boundary_original_reaction_current_a'):self.assertAlmostEqual(q[key]['fixed']/exact['fixed_reaction'],1.,places=10)
                if previous is not None:
                    old,old_exact=previous;shift=old_exact['boundary_potential_shift'](exact['outer_distance_m'])
                    np.testing.assert_allclose(np.asarray(fields['Az_Wb_per_m'])-old['Az_Wb_per_m'],shift,rtol=1e-10,atol=1e-13)
                    np.testing.assert_allclose(fields['Bx_T'],old['Bx_T'],rtol=1e-10,atol=1e-13)
                previous=fields,exact

    def test_axis_return_field_changes_as_inverse_radius_squared_and_refines(self):
        for order in (1,2):
            errors=[]
            for n in (8,16,32):
                case,exact=current_cylinder(order,n,outer_ratio=4.);solution=solve_axis_magnetostatic(case);q=axis_magnetostatic_quantities(solution)
                cells=np.arange(len(case.partition.mesh.triangles));bary=np.full((len(cells),3),1/3);points=case.partition.mesh.points_rz_m[case.partition.mesh.triangles].mean(axis=1)
                fields=solution.fields_in_cells(cells,bary);ref=exact['fields'](points);b=np.column_stack((fields['Br_T'],fields['Bz_T']))
                errors.append([abs(q['energy_j']/exact['energy']-1),np.linalg.norm(b-ref[1])/np.linalg.norm(ref[1]),abs(q['fixed_boundary_original_reaction_a_m2']['fixed']/exact['fixed_reaction']-1)])
                self.assertLess(q['discrete_energy_relative_error'],1e-10)
            self.assertTrue(np.all(np.diff(errors,axis=0)<0),errors);self.assertLess(max(errors[-1]),.03 if order==1 else .002)
        previous=None
        for ratio in (2.,4.,8.):
            case,exact=current_cylinder(2,16,outer_ratio=ratio);solution=solve_axis_magnetostatic(case);probe=solution.probe_at(exact['common_points'])['fields']
            infinity=exact['infinite_fields'](exact['common_points']);finite=exact['fields'](exact['common_points'])
            np.testing.assert_allclose(finite[2][:,1]-infinity[2][:,1],exact['background_h'],rtol=1e-12,atol=1e-12)
            self.assertAlmostEqual(exact['energy']/exact['infinite_energy'],1-2/(3*ratio**2),places=13)
            if previous is not None:
                old,old_exact=previous;expected=old_exact['boundary_background_h_shift'](exact['outer_distance_m'])
                self.assertLess(np.max(abs(np.asarray(probe['Hz_A_per_m'])-old['Hz_A_per_m']-expected))/exact['intensity_scale'],1e-4)
            previous=probe,exact

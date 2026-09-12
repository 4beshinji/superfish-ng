# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.axis_magnetostatic_reference import uniform_field,cylinder_current,layered_current
from superfish_ng.axis_magnetostatic import AxisMagnetostaticCase,solve_axis_magnetostatic,axis_magnetostatic_quantities
from superfish_ng.axis_magnetostatic_boundary import AxisMagnetostaticBoundary


class AxisMagnetostaticTests(unittest.TestCase):
    def test_strict_case_source_material_and_physics(self):
        case=uniform_field()[0];raw=case.to_dict();self.assertEqual(AxisMagnetostaticCase.from_dict(raw).to_dict(),raw)
        changes=[lambda d:d.update(schema_version=True),lambda d:d.update(physics='linear_electrostatic'),lambda d:d.update(gauge='subtract_constant'),
            lambda d:d.update(element_order=True),lambda d:d.update(quadrature_order=3),lambda d:d.update(current_density_phi_a_per_m2={}),
            lambda d:d['current_density_phi_a_per_m2'].update(all=True),lambda d:d['current_density_phi_a_per_m2'].update(extra=0.),
            lambda d:d['partition']['materials'][0].update(epsilon_r=1.),lambda d:d['partition']['materials'][0].update(mu_r=-1.),
            lambda d:d['partition']['geometry'].update(type='explicit_straight_off_axis'),lambda d:d['boundaries'][1].update(potential_v=0.)]
        for change in changes:
            bad=copy.deepcopy(raw);change(bad)
            with self.assertRaises(ValueError):AxisMagnetostaticCase.from_dict(bad)
        for value in (True,float('nan'),float('inf'),1+0j,10**1000):
            bad=copy.deepcopy(raw);bad['current_density_phi_a_per_m2']['all']=value
            with self.assertRaises(ValueError):AxisMagnetostaticCase.from_dict(bad)
        with self.assertRaises(ValueError):solve_axis_magnetostatic(raw)

    def test_all_boundaries_explicit_and_axis_regular_all_h_is_unique(self):
        case=uniform_field()[0];raw=case.to_dict()
        changes=[lambda d:d['boundaries'].pop(),lambda d:d['boundaries'][1]['edge_indices'].append(10**100),
            lambda d:d['boundaries'][0].update(kind='tangential_h',tangential_h_a_per_m=0.),
            lambda d:d['boundaries'][1].update(kind='fixed_az',az_wb_per_m=0.),
            lambda d:d['boundaries'][0].update(aphi_over_r_t=0.),lambda d:d['boundaries'][1].update(id='axis')]
        for change in changes:
            bad=copy.deepcopy(raw);change(bad)
            with self.assertRaises(ValueError):AxisMagnetostaticCase.from_dict(bad)
        boundaries=list(case.boundaries);bottom=boundaries[2];boundaries[2]=AxisMagnetostaticBoundary(bottom.id,'fixed_aphi_over_r',bottom.edge_indices,0.)
        with self.assertRaisesRegex(ValueError,'share a node'):AxisMagnetostaticCase(case.partition,dict(case.current_density_phi_a_per_m2),boundaries)
        natural=uniform_field(boundary='tangential')[0];solution=solve_axis_magnetostatic(natural)
        self.assertFalse(solution.fixed_boundary_dofs);self.assertEqual(len(solution.free_dofs),len(solution.aphi_over_r_t))
        np.testing.assert_allclose(solution.aphi_over_r_t,.01,rtol=1e-12,atol=0.)

    def test_uniform_B_fixed_and_positive_natural_H_load_full_volume_flux(self):
        for order in (1,2):
            for boundary in ('fixed','tangential'):
                case,exact=uniform_field(order=order,boundary=boundary,shift=-.25);solution=solve_axis_magnetostatic(case);q=axis_magnetostatic_quantities(solution)
                np.testing.assert_allclose(solution.aphi_over_r_t,.01,rtol=1e-12,atol=0.);self.assertAlmostEqual(q['energy_j']/exact['energy_j'],1.,places=11)
                self.assertLess(abs(q['original_field_ampere_balance_a'])/(exact['intensity_scale']*.125),1e-11)
                for name,expected in exact['boundary_flux_wb'].items():self.assertLess(abs(q['boundary_original_normal_flux_wb'][name]-expected)/(exact['field_scale']*.0625**2),1e-11)
                for name,expected in exact['fixed_reaction_a_m2'].items():
                    self.assertAlmostEqual(q['fixed_boundary_reaction_a_m2'][name]/expected,1.,places=11)
                    self.assertAlmostEqual(q['fixed_boundary_original_reaction_a_m2'][name]/expected,1.,places=11)
                if boundary=='tangential':self.assertGreater(solution.boundary_load_a_m2.sum(),0.)

    def test_known_azimuthal_current_ampere_axis_and_hole_boundary_signs(self):
        for holes in (0,1,2):
            for order in (1,2):
                for sign in (-1.,1.):
                    case,exact=cylinder_current(order=order,holes=holes,current_density=sign*2e5,outer_h=sign*300.,boundary='fixed',shift=-.25)
                    solution=solve_axis_magnetostatic(case);q=axis_magnetostatic_quantities(solution);points=solution.space.dof_points;expected=exact['fields'](points)
                    np.testing.assert_allclose(solution.aphi_over_r_t,expected[0],rtol=1e-11,atol=1e-14)
                    probe=solution.probe_at(points);fields=probe['fields']
                    for name,values in [('Aphi_Wb_per_m',expected[1]),('Br_T',expected[2][:,0]),('Bz_T',expected[2][:,1])]:
                        self.assertLess(np.max(abs(np.asarray(fields[name])-values))/exact['field_scale'],1e-10)
                    self.assertAlmostEqual(q['energy_j']/exact['energy_j'],1.,places=10)
                    self.assertLess(abs(q['original_field_ampere_balance_a']/exact['source_current_a']),1e-10)
                    self.assertLess(q['divergence_free_flux_relative_error'],1e-11)
                    self.assertLess(q['discrete_current_work_relative_error'],1e-11)
                    axis=points[:,0]==0;np.testing.assert_array_equal(np.asarray(fields['Aphi_Wb_per_m'])[axis],0.);np.testing.assert_array_equal(np.asarray(fields['Br_T'])[axis],0.)

    def test_layered_mu_H_continuity_and_separate_refinement_errors(self):
        previous=None
        for n in (4,8,16):
            case,exact=layered_current(n=n);solution=solve_axis_magnetostatic(case);q=axis_magnetostatic_quantities(solution)
            cells=np.arange(len(case.partition.mesh.triangles));bary=np.tile([.2,.3,.5],(len(cells),1));points=np.einsum('qi,qij->qj',bary,case.partition.mesh.points_rz_m[case.partition.mesh.triangles])
            actual=solution.fields_in_cells(cells,bary);a,aphi,b,h=exact['fields'](points)
            errors=np.array([np.linalg.norm(actual['Aphi_over_r_T']-a)/np.linalg.norm(a),np.linalg.norm(actual['Bz_T']-b[:,1])/np.linalg.norm(b),
                np.linalg.norm(actual['Hz_A_per_m']-h[:,1])/np.linalg.norm(h),abs(q['energy_j']/exact['energy_j']-1),abs(q['original_field_ampere_balance_a']/exact['source_current_a'])])
            if previous is not None:self.assertTrue(np.all(errors<previous),(errors,previous))
            previous=errors
        interface=case.partition.interface_cells[0];edge=case.partition.interface_edges[0];point=case.partition.mesh.points_rz_m[edge].mean(axis=0)
        probe=solution.probe_at([point]);self.assertEqual(probe['cell_indices'],[int(min(interface))]);self.assertEqual(len(probe['fields']),6)
        self.assertLess(max(errors),.002)

    def test_zero_current_no_gauge_and_strict_original_field_coordinates(self):
        case=uniform_field(field_t=0.,boundary='tangential')[0];solution=solve_axis_magnetostatic(case)
        np.testing.assert_array_equal(solution.aphi_over_r_t,0.);self.assertEqual(axis_magnetostatic_quantities(solution)['energy_j'],0.)
        for points in ([[False,0.]],[[0.,True]],[[1+0j,0.]],[["0",0.]],[[-.1,0.]],[[.01,100.]]):
            with self.assertRaises(ValueError):solution.probe_at(points)
        for cells,bary in (([False],[[1.,0.,0.]]),([0.],[[1.,0.,0.]]),([0],[[False,.5,.5]]),([0],[[1.,0.,1.]])):
            with self.assertRaises(ValueError):solution.fields_in_cells(cells,bary)

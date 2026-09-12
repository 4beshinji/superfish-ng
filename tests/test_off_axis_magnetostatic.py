# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.off_axis_magnetostatic_reference import uniform_field,annular_current,layered_current
from superfish_ng.off_axis_magnetostatic import OffAxisMagnetostaticCase,solve_off_axis_magnetostatic,off_axis_magnetostatic_quantities
from superfish_ng.off_axis_magnetostatic_boundary import OffAxisMagnetostaticBoundary


class OffAxisMagnetostaticTests(unittest.TestCase):
    def test_strict_case_source_material_and_physics(self):
        case=uniform_field()[0];raw=case.to_dict();self.assertEqual(OffAxisMagnetostaticCase.from_dict(raw).to_dict(),raw)
        changes=[lambda d:d.update(schema_version=True),lambda d:d.update(physics='linear_electrostatic'),lambda d:d.update(gauge='subtract_constant'),
            lambda d:d.update(element_order=True),lambda d:d.update(quadrature_order=3),lambda d:d.update(current_density_phi_a_per_m2={}),
            lambda d:d['current_density_phi_a_per_m2'].update(all=True),lambda d:d['current_density_phi_a_per_m2'].update(extra=0.),
            lambda d:d['partition']['materials'][0].update(epsilon_r=1.),lambda d:d['partition']['materials'][0].update(mu_r=-1.),
            lambda d:d['partition']['geometry'].update(type='explicit_straight_axis_connected'),lambda d:d['boundaries'][1].update(potential_v=0.)]
        for change in changes:
            bad=copy.deepcopy(raw);change(bad)
            with self.assertRaises(ValueError):OffAxisMagnetostaticCase.from_dict(bad)
        for value in (True,float('nan'),float('inf'),1+0j,10**1000):
            bad=copy.deepcopy(raw);bad['current_density_phi_a_per_m2']['all']=value
            with self.assertRaises(ValueError):OffAxisMagnetostaticCase.from_dict(bad)
        with self.assertRaises(ValueError):solve_off_axis_magnetostatic(raw)

    def test_all_boundaries_explicit_and_reference_required(self):
        case=uniform_field()[0];raw=case.to_dict()
        changes=[lambda d:d['boundaries'].pop(),lambda d:d['boundaries'][1]['edge_indices'].append(10**100),
            lambda d:d['boundaries'][0].update(kind='axis_regularity'),lambda d:d['boundaries'][1].update(kind='fixed_az',az_wb_per_m=0.),
            lambda d:d['boundaries'][0].update(aphi_over_r_t=0.),lambda d:d['boundaries'][1].update(id='inner')]
        for change in changes:
            bad=copy.deepcopy(raw);change(bad)
            with self.assertRaises(ValueError):OffAxisMagnetostaticCase.from_dict(bad)
        boundaries=list(case.boundaries);bottom=boundaries[2];boundaries[2]=OffAxisMagnetostaticBoundary(bottom.id,'fixed_psi',bottom.edge_indices,0.)
        with self.assertRaisesRegex(ValueError,'share a node'):OffAxisMagnetostaticCase(case.partition,dict(case.current_density_phi_a_per_m2),boundaries)
        boundaries=[OffAxisMagnetostaticBoundary(b.id,'tangential_h',b.edge_indices,0.) for b in case.boundaries]
        with self.assertRaisesRegex(ValueError,'at least one fixed-psi'):OffAxisMagnetostaticCase(case.partition,dict(case.current_density_phi_a_per_m2),boundaries)

    def test_uniform_B_quadratic_fixed_and_natural_H_with_holes(self):
        for holes in (0,1,2):
            for boundary in ('fixed','tangential'):
                case,exact=uniform_field(holes=holes,boundary=boundary,shift=-.25);solution=solve_off_axis_magnetostatic(case);q=off_axis_magnetostatic_quantities(solution)
                expected=exact['fields'](solution.space.dof_points)[0]
                self.assertLess(np.linalg.norm(solution.psi_wb-expected)/np.linalg.norm(expected),1e-11)
                self.assertAlmostEqual(q['energy_j']/exact['energy_j'],1.,places=11)
                self.assertLess(abs(q['original_field_ampere_balance_a'])/(exact['intensity_scale']*.125),1e-11)
                for name,expected in exact['fixed_reaction_a'].items():
                    self.assertAlmostEqual(q['fixed_boundary_reaction_a'][name]/expected,1.,places=11)
                    self.assertAlmostEqual(q['fixed_boundary_original_reaction_a'][name]/expected,1.,places=11)
                if boundary=='tangential':self.assertGreater(solution.boundary_load_a.sum(),0.)
                if exact['boundary_flux_wb'] is not None:
                    for name,expected in exact['boundary_flux_wb'].items():self.assertLess(abs(q['boundary_original_normal_flux_wb'][name]-expected)/(exact['field_scale']*.0625**2),1e-11)

    def test_reference_shift_preserves_B_H_energy_and_changes_aphi_by_C_over_r(self):
        pair=[]
        for offset in (0.,.125):
            case,exact=annular_current(n=4,reference_psi=offset);s=solve_off_axis_magnetostatic(case);q=off_axis_magnetostatic_quantities(s)
            cells=np.arange(len(case.partition.mesh.triangles));bary=np.tile([.2,.3,.5],(len(cells),1));pair.append((s,q,s.fields_in_cells(cells,bary)))
        left,right=pair;np.testing.assert_array_equal(left[0].psi_relative_to_reference_wb,right[0].psi_relative_to_reference_wb)
        self.assertEqual(left[1]['energy_j'],right[1]['energy_j'])
        for key in ('Br_T','Bz_T','Hr_A_per_m','Hz_A_per_m'):np.testing.assert_array_equal(left[2][key],right[2][key])
        radius=np.einsum('qi,qi->q',bary,case.partition.mesh.points_rz_m[case.partition.mesh.triangles,0])
        np.testing.assert_allclose(right[2]['Aphi_Wb_per_m']-left[2]['Aphi_Wb_per_m'],.125/radius,rtol=1e-14)

    def test_annular_and_layered_current_refinement_and_reversal(self):
        for factory in (annular_current,layered_current):
            previous=None
            for n in (4,8,16):
                case,exact=factory(n=n);s=solve_off_axis_magnetostatic(case);q=off_axis_magnetostatic_quantities(s)
                cells=np.arange(len(case.partition.mesh.triangles));bary=np.tile([.2,.3,.5],(len(cells),1));points=np.einsum('qi,qij->qj',bary,case.partition.mesh.points_rz_m[case.partition.mesh.triangles])
                actual=s.fields_in_cells(cells,bary);psi,aphi,b,h=exact['fields'](points)
                errors=np.array([np.linalg.norm(actual['psi_Wb']-psi)/np.linalg.norm(psi),np.linalg.norm(actual['Bz_T']-b[:,1])/np.linalg.norm(b),np.linalg.norm(actual['Hz_A_per_m']-h[:,1])/np.linalg.norm(h),abs(q['energy_j']/exact['energy_j']-1),abs(q['original_field_ampere_balance_a']/exact['source_current_a'])])
                if previous is not None:self.assertTrue(np.all(errors<previous),(errors,previous))
                previous=errors
            self.assertLess(max(errors),.002)
            positive=solve_off_axis_magnetostatic(factory(n=2)[0]);negative=solve_off_axis_magnetostatic(factory(n=2,current_density=-2e5)[0])
            np.testing.assert_array_equal(negative.psi_wb,-positive.psi_wb)
            if factory is layered_current:
                interface=case.partition.interface_cells[0];edge=case.partition.interface_edges[0];point=case.partition.mesh.points_rz_m[edge].mean(axis=0)
                probe=s.probe_at([point]);self.assertEqual(probe['cell_indices'],[int(min(interface))]);self.assertEqual(len(probe['fields']),6)

    def test_constant_flux_zero_B_and_strict_original_field_coordinates(self):
        for order in (1,2):
            case=uniform_field(order=order,field_t=0.,reference_psi=.125)[0];s=solve_off_axis_magnetostatic(case)
            np.testing.assert_array_equal(s.psi_wb,.125);np.testing.assert_array_equal(s.psi_relative_to_reference_wb,0.);self.assertEqual(off_axis_magnetostatic_quantities(s)['energy_j'],0.)
        for points in ([[False,0.]],[[.04,True]],[[1+0j,0.]],[["0",0.]],[[0.,0.]],[[.04,100.]]):
            with self.assertRaises(ValueError):s.probe_at(points)
        for cells,bary in (([False],[[1.,0.,0.]]),([0.],[[1.,0.,0.]]),([0],[[False,.5,.5]]),([0],[[1.,0.,1.]])):
            with self.assertRaises(ValueError):s.fields_in_cells(cells,bary)

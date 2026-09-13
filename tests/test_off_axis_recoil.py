# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.off_axis_recoil_reference import uniform_remanence,interface_patch,blocked_flux,annular_current,layered_remanence
from superfish_ng.off_axis_recoil import OffAxisRecoilCase,solve_off_axis_recoil,off_axis_recoil_quantities


def field_error(solution,reference):
    p=solution.case.partition;points=p.mesh.points_rz_m[p.mesh.triangles].mean(axis=1);cells=np.arange(len(points));bary=np.full((len(points),3),1/3)
    f=solution.fields_in_cells(cells,bary);psi,ap,b,h=reference['fields'](points);expected=np.column_stack((psi,ap,b,h))
    actual=np.column_stack([f[k] for k in ('psi_Wb','Aphi_Wb_per_m','Br_T','Bz_T','Hr_A_per_m','Hz_A_per_m')]);radius=p.mesh.outer_rz_m[:,0].max()
    scale=np.array([reference['potential_scale'],reference['potential_scale']/radius,*([reference['field_scale']]*2),*([reference['intensity_scale']]*2)])
    return float(np.max(abs(actual-expected)/np.where(scale,scale,1.)))


class OffAxisRecoilSolveTests(unittest.TestCase):
    def assert_potentials(self,solution,reference,tolerance=1e-10):
        q=off_axis_recoil_quantities(solution);scale=sum(abs(v) for v in reference['potentials'].values()) or 1.
        for name,value in reference['potentials'].items():self.assertLess(abs(q[name]-value)/scale,tolerance,name)
        self.assertNotIn('energy_j',q);self.assertGreaterEqual(q['constitutive_potential_h0_j'],0.)
        self.assertLess(q['discrete_work_relative_error'],1e-9);self.assertLess(q['constitutive_potential_relative_error'],1e-9)

    def test_P2_uniform_remanence_and_psi_reference_shift_preserve_original_B_H(self):
        for boundary in ('fixed','tangential'):
            for holes in (0,1,2):
                c,e=uniform_remanence(n=1,boundary=boundary,holes=holes);s=solve_off_axis_recoil(c);self.assertLess(field_error(s,e),1e-10);self.assert_potentials(s,e)
                shifted,reference=uniform_remanence(n=1,boundary=boundary,holes=holes,reference_psi=.125);t=solve_off_axis_recoil(shifted);self.assertLess(field_error(t,reference),1e-10)
                points=c.partition.mesh.points_rz_m[c.partition.mesh.triangles[[0,-1]]].mean(axis=1);first=s.probe_at(points)['fields'];second=t.probe_at(points)['fields']
                np.testing.assert_allclose(np.array(second['psi_Wb'])-first['psi_Wb'],.125,rtol=1e-12,atol=0.)
                np.testing.assert_allclose(np.array(second['Aphi_Wb_per_m'])-first['Aphi_Wb_per_m'],.125/points[:,0],rtol=1e-12,atol=0.)
                for name in ('Br_T','Bz_T','Hr_A_per_m','Hz_A_per_m'):
                    scale=e['field_scale'] if name[0]=='B' else e['intensity_scale'];self.assertLess(np.max(abs(np.array(second[name])-first[name]))/scale,1e-10)
                self.assertEqual(t.reference_psi_wb,.125);self.assert_potentials(t,reference)

    def test_oriented_material_interface_preserves_nonzero_Bn_Ht_and_original_metadata(self):
        c,e=interface_patch(n=1,reference_psi=.125);s=solve_off_axis_recoil(c);self.assertLess(field_error(s,e),1e-10);self.assert_potentials(s,e);p=c.partition;found=False
        for edge,owners in zip(p.interface_edges,p.interface_cells):
            delta=p.mesh.points_rz_m[edge[1]]-p.mesh.points_rz_m[edge[0]]
            if not np.all(delta!=0.):continue
            tangent=delta/np.linalg.norm(delta);normal=np.array([tangent[1],-tangent[0]]);values=[]
            for cell in owners:
                bary=np.array([.5 if node in edge else 0. for node in p.mesh.triangles[cell]]);f=s.fields_in_cells([int(cell)],[bary.tolist()])
                b=np.array([f['Br_T'][0],f['Bz_T'][0]]);h=np.array([f['Hr_A_per_m'][0],f['Hz_A_per_m'][0]]);values.append([b@normal,h@tangent])
            np.testing.assert_allclose(values[0],values[1],rtol=1e-10,atol=1e-10);self.assertGreater(abs(values[0][0]),.001);self.assertGreater(abs(values[0][1]),1.);found=True;break
        self.assertTrue(found);probe=s.probe_at([p.mesh.points_rz_m[edge[0]].tolist()]);self.assertIn('mu_r_tensor',probe);self.assertIn('remanent_b_t',probe);self.assertIn('azimuthal_model',probe)

    def test_blocked_B_is_nonzero_H_and_layered_P2_constitutive_potentials_are_exact(self):
        for order in (1,2):
            for boundary in ('fixed','tangential'):
                c,e=blocked_flux(order,n=1,boundary=boundary,reference_psi=.125);s=solve_off_axis_recoil(c)
                self.assertLess(field_error(s,e),1e-10);self.assert_potentials(s,e);q=off_axis_recoil_quantities(s)
                self.assertGreater(q['constitutive_potential_h0_j'],0.);self.assertLess(q['b_quadratic_j']/q['remanent_reference_constant_j'],1e-20)
                self.assertAlmostEqual(q['constitutive_potential_h0_j']/q['remanent_reference_constant_j'],1.,places=12)
        for boundary in ('fixed','tangential'):
            c,e=layered_remanence(n=1,boundary=boundary,reference_psi=.125);s=solve_off_axis_recoil(c);self.assertLess(field_error(s,e),1e-10);self.assert_potentials(s,e)
            q=off_axis_recoil_quantities(s);flux_scale=max(abs(v) for v in e['boundary_flux_wb'].values())
            for name,value in e['boundary_flux_wb'].items():self.assertLess(abs(q['boundary_original_normal_flux_wb'][name]-value)/flux_scale,1e-10)
            for name,value in e['fixed_reaction_a'].items():self.assertLess(abs(q['fixed_boundary_original_reaction_a'][name]/value-1),1e-10)

    def test_current_refinement_improves_original_fields_with_small_residual_at_every_level(self):
        finest={}
        for order in (1,2):
            previous=None
            for n in (2,4):
                c,e=annular_current(order,n=n,holes=1);s=solve_off_axis_recoil(c);error=field_error(s,e)
                if previous is not None:self.assertLess(error,previous)
                previous=error;self.assertGreater(error,1e-9);self.assertLess(s.relative_residual,1e-10);self.assertLess(off_axis_recoil_quantities(s)['discrete_work_relative_error'],1e-9)
            finest[order]=error
        self.assertLess(finest[2],finest[1]/10)

    def test_current_remanence_boundary_superposition_and_reversal(self):
        c,_=annular_current(n=1,boundary='fixed');raw=c.to_dict();original=solve_off_axis_recoil(c);parts=[]
        for keep in ('current','remanence','boundary'):
            d=copy.deepcopy(raw)
            if keep!='current':d['current_density_phi_a_per_m2']['all']=0.
            if keep!='remanence':d['partition']['materials'][0]['remanent_b_local_t']=[0.,0.]
            if keep!='boundary':
                for b in d['boundaries']:
                    for key in ('psi_wb','tangential_h_a_per_m'):
                        if key in b:b[key]=0.
            parts.append(solve_off_axis_recoil(OffAxisRecoilCase.from_dict(d)).psi_wb)
        self.assertLess(np.linalg.norm(sum(parts)-original.psi_wb)/np.linalg.norm(original.psi_wb),1e-11)
        d=copy.deepcopy(raw);d['current_density_phi_a_per_m2']['all']*=-2;d['partition']['materials'][0]['remanent_b_local_t']=[-2*v for v in d['partition']['materials'][0]['remanent_b_local_t']]
        for b in d['boundaries']:
            for key in ('psi_wb','tangential_h_a_per_m'):
                if key in b:b[key]*=-2
        reverse=solve_off_axis_recoil(OffAxisRecoilCase.from_dict(d));np.testing.assert_array_equal(reverse.psi_wb,-2*original.psi_wb)
        self.assertAlmostEqual(off_axis_recoil_quantities(reverse)['b_quadratic_j']/off_axis_recoil_quantities(original)['b_quadratic_j'],4.,places=12)
        for array in (original.psi_wb,original.psi_relative_to_reference_wb,original.current_load_a,original.remanent_load_a,original.boundary_load_a):self.assertFalse(array.flags.writeable)

    def test_strict_case_fixed_reference_and_outside_hole_probes(self):
        c,_=uniform_remanence(n=1,holes=1);raw=c.to_dict();self.assertEqual(OffAxisRecoilCase.from_dict(raw).to_dict(),raw)
        for change in (lambda d:d.update(schema_version=True),lambda d:d.update(physics='linear_magnetostatic'),lambda d:d.update(gauge='absolute_axis_flux'),
            lambda d:d['boundaries'].pop(),lambda d:d.update(element_order=True),lambda d:d.update(quadrature_order=3),lambda d:d['current_density_phi_a_per_m2'].update(all=True)):
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):OffAxisRecoilCase.from_dict(data)
        data=copy.deepcopy(raw);data['boundaries'][0]=dict(id='inner',kind='tangential_h',edge_indices=data['boundaries'][0]['edge_indices'],tangential_h_a_per_m=0.)
        with self.assertRaisesRegex(ValueError,'fixed-psi'):OffAxisRecoilCase.from_dict(data)
        s=solve_off_axis_recoil(c)
        for points in ([[True,0.]],[[float('nan'),0.]],[[-1.,0.]],[[0.,0.]],[[10.,10.]],c.partition.mesh.holes_rz_m[0].mean(axis=0)[None,:]):
            with self.assertRaises(ValueError):s.probe_at(points)
        for cells,bary in (([True],[[1.,0.,0.]]),([0],[[True,0.,0.]]),([0],[[-.1,.5,.6]])):
            with self.assertRaises(ValueError):s.fields_in_cells(cells,bary)

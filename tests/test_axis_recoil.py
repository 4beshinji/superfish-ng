# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.axis_recoil_reference import uniform_remanence,interface_patch,cylinder_current,layered_remanence
from superfish_ng.axis_recoil import AxisRecoilCase,solve_axis_recoil,axis_recoil_quantities


def field_error(solution,reference):
    p=solution.case.partition;points=p.mesh.points_rz_m[p.mesh.triangles].mean(axis=1);cells=np.arange(len(points));bary=np.full((len(points),3),1/3)
    actual=solution.fields_in_cells(cells,bary);a,aphi,b,h=reference['fields'](points)
    expected=np.column_stack((a,aphi,b,h));values=np.column_stack([actual[k] for k in ('Aphi_over_r_T','Aphi_Wb_per_m','Br_T','Bz_T','Hr_A_per_m','Hz_A_per_m')])
    radius=p.mesh.outer_rz_m[:,0].max();scale=np.array([reference['field_scale'],reference['field_scale']*radius,*([reference['field_scale']]*2),*([reference['intensity_scale']]*2)])
    return float(np.max(abs(values-expected)/np.where(scale,scale,1.)))


class AxisRecoilSolveTests(unittest.TestCase):
    def assert_potentials(self,solution,reference,tolerance=1e-10):
        q=axis_recoil_quantities(solution);scale=sum(abs(v) for v in reference['potentials'].values()) or 1.
        for name,expected in reference['potentials'].items():self.assertLess(abs(q[name]-expected)/scale,tolerance,name)
        self.assertNotIn('energy_j',q);self.assertGreaterEqual(q['constitutive_potential_h0_j'],0.)
        self.assertLess(q['discrete_work_relative_error'],1e-9);self.assertLess(q['constitutive_potential_relative_error'],1e-9)

    def test_uniform_remanence_axis_zero_H_and_fixed_or_all_tangential_boundaries(self):
        for order in (1,2):
            for boundary in ('fixed','tangential'):
                for holes in (0,1):
                    c,e=uniform_remanence(order,n=1,boundary=boundary,holes=holes);s=solve_axis_recoil(c)
                    self.assertLess(field_error(s,e),1e-11);self.assert_potentials(s,e)
                    axis=c.partition.mesh.points_rz_m[c.partition.mesh.axis_nodes];probe=s.probe_at(axis)
                    for key in ('Aphi_Wb_per_m','Br_T','Hr_A_per_m'):np.testing.assert_array_equal(probe['fields'][key],0.)
                    q=axis_recoil_quantities(s);self.assertLess(q['constitutive_potential_b0_j'],0.)
                    self.assertLess(q['constitutive_potential_h0_j']/q['remanent_reference_constant_j'],1e-20)

    def test_oriented_off_axis_material_and_nonzero_normal_B_tangential_H_interface(self):
        for order in (1,2):
            c,e=interface_patch(order,n=1);s=solve_axis_recoil(c);self.assertLess(field_error(s,e),1e-10);self.assert_potentials(s,e)
            p=c.partition;found=False
            for edge,owners in zip(p.interface_edges,p.interface_cells):
                delta=p.mesh.points_rz_m[edge[1]]-p.mesh.points_rz_m[edge[0]]
                if not np.all(delta!=0.):continue
                tangent=delta/np.linalg.norm(delta);normal=np.array([tangent[1],-tangent[0]]);values=[]
                for cell in owners:
                    bary=np.array([.5 if node in edge else 0. for node in p.mesh.triangles[cell]])
                    f=s.fields_in_cells([int(cell)],[bary.tolist()]);b=np.array([f['Br_T'][0],f['Bz_T'][0]]);h=np.array([f['Hr_A_per_m'][0],f['Hz_A_per_m'][0]])
                    values.append((float(b@normal),float(h@tangent)))
                np.testing.assert_allclose(values[0],values[1],rtol=1e-10,atol=1e-10)
                self.assertGreater(abs(values[0][0]),.001);self.assertGreater(abs(values[0][1]),1.);found=True;break
            self.assertTrue(found)
            probe=s.probe_at([p.mesh.points_rz_m[edge[0]].tolist()]);b=np.array([[probe['fields']['Br_T'][0],probe['fields']['Bz_T'][0]]])
            from superfish_ng.constants import MU0
            h=np.linalg.solve(MU0*np.array(probe['mu_r_tensor']),b[:,:,None]-np.array(probe['remanent_b_t'])[:,:,None])[:,:,0]
            np.testing.assert_allclose(h,[[probe['fields']['Hr_A_per_m'][0],probe['fields']['Hz_A_per_m'][0]]],rtol=1e-10,atol=1e-9)

    def test_uniform_current_with_remanence_exact_linear_regular_field_and_flux(self):
        for order in (1,2):
            for holes in (0,1,2):
                for amplitude in (-1.,1.):
                    c,e=cylinder_current(order,n=1,holes=holes,amplitude=amplitude,boundary='fixed');s=solve_axis_recoil(c)
                    self.assertLess(field_error(s,e),1e-10);self.assert_potentials(s,e);q=axis_recoil_quantities(s)
                    self.assertLess(abs(q['original_field_ampere_balance_a'])/abs(e['source_current_a']),1e-10)
                    scale=max(abs(v) for v in e['boundary_flux_wb'].values())
                    for name,value in e['boundary_flux_wb'].items():self.assertLess(abs(q['boundary_original_normal_flux_wb'][name]-value)/scale,1e-10)
                    for name,value in e['fixed_reaction_a_m2'].items():self.assertLess(abs(q['fixed_boundary_original_reaction_a_m2'][name]/value-1),1e-10)

    def test_layered_rational_regular_field_refines_original_H_separately_from_residual(self):
        for order in (1,2):
            previous=None
            for n in (4,8):
                c,e=layered_remanence(order,n=n);s=solve_axis_recoil(c);error=field_error(s,e)
                if previous is not None:self.assertLess(error,previous)
                previous=error;self.assertGreater(error,1e-8);self.assertLess(s.relative_residual,1e-10)
                q=axis_recoil_quantities(s);self.assertLess(q['discrete_work_relative_error'],1e-9)

    def test_separate_current_remanence_and_boundary_superposition_and_reversal(self):
        c,_=cylinder_current(n=1,boundary='fixed');raw=c.to_dict();original=solve_axis_recoil(c);parts=[]
        for keep in ('current','remanence','boundary'):
            d=copy.deepcopy(raw)
            if keep!='current':d['current_density_phi_a_per_m2']['all']=0.
            if keep!='remanence':d['partition']['materials'][0]['remanent_b_local_t']=[0.,0.]
            if keep!='boundary':
                for b in d['boundaries']:
                    for key in ('aphi_over_r_t','tangential_h_a_per_m'):
                        if key in b:b[key]=0.
            parts.append(solve_axis_recoil(AxisRecoilCase.from_dict(d)).aphi_over_r_t)
        self.assertLess(np.linalg.norm(sum(parts)-original.aphi_over_r_t)/np.linalg.norm(original.aphi_over_r_t),1e-11)
        d=copy.deepcopy(raw);d['current_density_phi_a_per_m2']['all']*=-2
        d['partition']['materials'][0]['remanent_b_local_t']=[-2*v for v in d['partition']['materials'][0]['remanent_b_local_t']]
        for b in d['boundaries']:
            for key in ('aphi_over_r_t','tangential_h_a_per_m'):
                if key in b:b[key]*=-2
        reverse=solve_axis_recoil(AxisRecoilCase.from_dict(d));np.testing.assert_array_equal(reverse.aphi_over_r_t,-2*original.aphi_over_r_t)
        self.assertAlmostEqual(axis_recoil_quantities(reverse)['b_quadratic_j']/axis_recoil_quantities(original)['b_quadratic_j'],4.,places=12)
        for array in (original.aphi_over_r_t,original.current_load_a_m2,original.remanent_load_a_m2,original.boundary_load_a_m2):self.assertFalse(array.flags.writeable)

    def test_strict_case_and_probes_reject_unsupported_data_and_excluded_geometry(self):
        c,_=uniform_remanence(n=1,holes=1);raw=c.to_dict();self.assertEqual(AxisRecoilCase.from_dict(raw).to_dict(),raw)
        for change in (lambda d:d.update(schema_version=True),lambda d:d.update(physics='linear_magnetostatic'),lambda d:d.update(gauge='constant'),
            lambda d:d['partition']['regions'][0].update(orientation_rad=.1),lambda d:d['boundaries'].pop(),
            lambda d:d.update(element_order=True),lambda d:d.update(quadrature_order=3),lambda d:d['current_density_phi_a_per_m2'].update(all=True)):
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):AxisRecoilCase.from_dict(data)
        s=solve_axis_recoil(c)
        for points in ([[True,0.]],[[float('nan'),0.]],[[-1.,0.]],[[10.,10.]],c.partition.mesh.holes_rz_m[0].mean(axis=0)[None,:]):
            with self.assertRaises(ValueError):s.probe_at(points)
        for cells,bary in (([True],[[1.,0.,0.]]),([0],[[True,0.,0.]]),([0],[[-.1,.5,.6]])):
            with self.assertRaises(ValueError):s.fields_in_cells(cells,bary)

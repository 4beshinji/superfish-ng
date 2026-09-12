# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.planar_recoil_reference import uniform_remanence,interface_patch,layered_remanence,quadratic_current
from superfish_ng.planar_recoil import PlanarRecoilCase,solve_planar_recoil,planar_recoil_quantities
from superfish_ng.magnetostatic_boundary import MagnetostaticBoundary


def compare_fields(test,solution,reference):
    mesh=solution.case.partition.mesh;cells=np.arange(len(mesh.triangles));bary=np.tile([.2,.3,.5],(len(cells),1))
    points=np.einsum('qi,qij->qj',bary,mesh.points_xy_m[mesh.triangles]);az,b,h=reference['fields'](points);actual=solution.fields_in_cells(cells,bary)
    aa=actual['Az_Wb_per_m'];ab=np.column_stack((actual['Bx_T'],actual['By_T']));ah=np.column_stack((actual['Hx_A_per_m'],actual['Hy_A_per_m']))
    errors=[np.linalg.norm(aa-az)/(np.sqrt(len(cells))*reference['potential_scale']),np.linalg.norm(ab-b)/np.linalg.norm(b),
        np.linalg.norm(ah-h)/(np.linalg.norm(h) if np.any(h) else np.sqrt(len(cells))*reference['intensity_scale'])]
    return errors


class PlanarRecoilTests(unittest.TestCase):
    def test_strict_case_material_source_and_boundary_scope(self):
        case=interface_patch()[0];raw=case.to_dict();self.assertEqual(PlanarRecoilCase.from_dict(raw).to_dict(),raw)
        changes=[lambda d:d.update(schema_version=True),lambda d:d.update(physics='linear_magnetostatic'),lambda d:d.update(element_order=True),
            lambda d:d.update(quadrature_order=3),lambda d:d.update(gauge='automatic'),lambda d:d['partition']['materials'][0].update(mu_r=1.),
            lambda d:d['partition']['regions'][0].update(orientation_rad=True),lambda d:d['current_density_z_a_per_m2'].update(extra=0.),
            lambda d:d['current_density_z_a_per_m2'].update({'region-0':True}),lambda d:d['boundaries'].pop(),lambda d:d['boundaries'][0].update(psi_wb=0.)]
        for change in changes:
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):PlanarRecoilCase.from_dict(data)
        boundaries=[MagnetostaticBoundary(v.id,'tangential_h',v.edge_indices,0.) for v in case.boundaries]
        with self.assertRaisesRegex(ValueError,'at least one fixed-Az'):PlanarRecoilCase(case.partition,dict(case.current_density_z_a_per_m2),boundaries)
        with self.assertRaises(ValueError):solve_planar_recoil(raw)

    def test_uniform_remanence_has_original_zero_H_and_reference_potentials(self):
        for order in (1,2):
            for angle in (0.,.7):
                case,ref=uniform_remanence(order=order,angle=angle,shift=(-.25,.125));s=solve_planar_recoil(case);q=planar_recoil_quantities(s)
                self.assertLess(max(compare_fields(self,s,ref)),1e-10)
                scale=ref['potentials']['remanent_reference_constant_j_per_m']
                self.assertLess(q['constitutive_potential_h0_j_per_m']/scale,1e-20)
                self.assertAlmostEqual(q['constitutive_potential_b0_j_per_m']/scale,-1.,places=11)
                self.assertNotIn('energy_j_per_m',q);self.assertLess(q['discrete_current_relative_error'],1e-11)

    def test_nonzero_interface_normal_B_and_tangential_H_patch(self):
        for order in (1,2):
            case,ref=interface_patch(order=order,angle=.7,shift=(-.25,.125));s=solve_planar_recoil(case);q=planar_recoil_quantities(s)
            self.assertLess(max(compare_fields(self,s,ref)),1e-10)
            p=case.partition;pair=p.interface_cells[0];edge=p.interface_edges[0];point=p.mesh.points_xy_m[edge].mean(axis=0)
            fields=[]
            for cell in pair:
                triangle=p.mesh.triangles[cell];bary=np.zeros(3)
                for vertex in edge:bary[np.flatnonzero(triangle==vertex)[0]]=.5
                fields.append(s.fields_in_cells([int(cell)],[bary.tolist()]))
            for name in ('Bx_T','By_T','Hx_A_per_m','Hy_A_per_m'):
                scale=ref['field_scale'] if name.startswith('B') else 200.
                self.assertLess(abs(fields[0][name][0]-fields[1][name][0])/scale,1e-10)
            probe=s.probe_at([p.mesh.points_xy_m[edge[0]]]);self.assertEqual(probe['cell_indices'],[int(min(pair))]);self.assertIn('mu_r_tensor',probe);self.assertIn('remanent_b_t',probe);self.assertNotIn('mu_r',probe)
            scale=sum(abs(v) for v in ref['potentials'].values())
            self.assertLess(max(abs(q[k]-v) for k,v in ref['potentials'].items())/scale,1e-11)

    def test_layered_original_fields_reference_shift_and_source_reversal(self):
        reference_pair=[]
        for offset in (0.,.125):
            case,ref=layered_remanence(offset=offset,angle=.7);s=solve_planar_recoil(case);q=planar_recoil_quantities(s);reference_pair.append(s)
            self.assertLess(max(compare_fields(self,s,ref)),1e-10)
            for name,expected in ref['fixed_reaction_current_a'].items():
                self.assertAlmostEqual(q['fixed_boundary_original_reaction_current_a'][name]/expected,1.,places=10)
        np.testing.assert_array_equal(reference_pair[0].az_relative_to_reference_wb_per_m,reference_pair[1].az_relative_to_reference_wb_per_m)
        for factory in (uniform_remanence,interface_patch,layered_remanence,quadratic_current):
            positive=solve_planar_recoil(factory(amplitude=1.,offset=0.)[0]);negative=solve_planar_recoil(factory(amplitude=-1.,offset=0.)[0])
            np.testing.assert_allclose(negative.az_relative_to_reference_wb_per_m,-positive.az_relative_to_reference_wb_per_m,rtol=1e-12,atol=1e-15)
            q1=planar_recoil_quantities(positive);q2=planar_recoil_quantities(negative)
            self.assertAlmostEqual(q1['b_quadratic_j_per_m']/q2['b_quadratic_j_per_m'],1.,places=12)

    def test_quadratic_current_exact_P2_and_separate_P1_refinement(self):
        for concave in (False,True):
            case,ref=quadratic_current(concave=concave,angle=.7);s=solve_planar_recoil(case);q=planar_recoil_quantities(s)
            self.assertLess(max(compare_fields(self,s,ref)),1e-10)
            self.assertAlmostEqual(q['total_source_current_a']/ref['source_current_a'],1.,places=12)
            scale=sum(abs(v) for v in ref['potentials'].values());self.assertLess(max(abs(q[k]-v) for k,v in ref['potentials'].items())/scale,1e-11)
        previous=None
        for n in (8,16,32):
            case,ref=quadratic_current(order=1,n=n);s=solve_planar_recoil(case);q=planar_recoil_quantities(s);errors=np.array(compare_fields(self,s,ref))
            if previous is not None:self.assertTrue(np.all(errors<previous),(errors,previous))
            previous=errors
        self.assertLess(errors[0],1e-3);self.assertLess(max(errors[1:]),2e-2)

    def test_isotropic_unmagnetized_limit_and_strict_original_coordinates(self):
        from superfish_ng.magnetic_materials import LinearMagneticMaterial,MagneticRegion,PlanarMagneticPartition
        from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic,planar_magnetostatic_quantities
        case=quadratic_current()[0];raw=case.to_dict();raw['partition']['materials'][0].update(mu_r_principal=[3.,3.],remanent_b_local_t=[0.,0.]);case=PlanarRecoilCase.from_dict(raw)
        p=case.partition;oldp=PlanarMagneticPartition(p.mesh,[LinearMagneticMaterial('m0',3.)],[MagneticRegion(v.id,v.material,v.cell_indices) for v in p.regions])
        old=solve_planar_magnetostatic(PlanarMagnetostaticCase(oldp,dict(case.current_density_z_a_per_m2),case.boundaries,case.element_order))
        s=solve_planar_recoil(case);np.testing.assert_allclose(s.az_wb_per_m,old.az_wb_per_m,rtol=1e-12,atol=1e-15)
        self.assertAlmostEqual(planar_recoil_quantities(s)['b_quadratic_j_per_m']/planar_magnetostatic_quantities(old)['energy_j_per_m'],1.,places=12)
        for points in ([[False,0.]],[[0.,True]],[[1+0j,0.]],[["0",0.]],[[100.,100.]]):
            with self.assertRaises(ValueError):s.probe_at(points)
        for cells,bary in (([False],[[1.,0.,0.]]),([0.],[[1.,0.,0.]]),([0],[[False,.5,.5]]),([0],[[1.,0.,1.]])):
            with self.assertRaises(ValueError):s.fields_in_cells(cells,bary)

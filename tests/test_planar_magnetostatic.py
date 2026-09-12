# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.planar_magnetostatic_reference import layered_gap,manufactured_quadratic,rectangular_current
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic,planar_magnetostatic_quantities
from superfish_ng.magnetostatic_boundary import MagnetostaticBoundary


class PlanarMagnetostaticTests(unittest.TestCase):
    def test_strict_current_material_and_static_case(self):
        case,_=layered_gap();raw=case.to_dict();self.assertEqual(raw,PlanarMagnetostaticCase.from_dict(raw).to_dict());self.assertFalse(case.boundary_owner_indices.flags.writeable)
        with self.assertRaises(TypeError):case.current_density_z_a_per_m2['bottom']=2.
        changes=[lambda d:d.update(physics='linear_electrostatic'),lambda d:d.update(schema_version=True),lambda d:d.update(modes=1),lambda d:d.update(inductance=1.),
            lambda d:d['current_density_z_a_per_m2'].update(bottom=True),lambda d:d['current_density_z_a_per_m2'].update(bottom=10**1000),
            lambda d:d['partition']['materials'][0].update(epsilon_r=2.),lambda d:d['partition']['materials'][0].update(type='nonlinear_bh'),
            lambda d:d['boundaries'][0].update(az_wb_per_m=True),lambda d:d['boundaries'][2].update(tangential_h_a_per_m=1+1j),lambda d:d['boundaries'].pop()]
        for change in changes:
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):PlanarMagnetostaticCase.from_dict(data)
        for kind in ('axis_symmetry','electrode_potential','outward_displacement',[],None):
            with self.assertRaises(ValueError):MagnetostaticBoundary('bad',kind,[0],0.)

    def test_no_implicit_gauge_and_connected_fixed_boundaries_must_be_merged(self):
        raw=layered_gap()[0].to_dict();data=copy.deepcopy(raw)
        for boundary in data['boundaries']:
            if boundary['kind']=='fixed_az':boundary['kind']='tangential_h';boundary['tangential_h_a_per_m']=0.;del boundary['az_wb_per_m']
        with self.assertRaisesRegex(ValueError,'pure Neumann'):PlanarMagnetostaticCase.from_dict(data)
        data=copy.deepcopy(raw);fixed=data['boundaries'][0];new=copy.deepcopy(fixed);new['id']='touching';new['edge_indices']=fixed['edge_indices'][:1];fixed['edge_indices']=fixed['edge_indices'][1:];data['boundaries'].append(new)
        with self.assertRaisesRegex(ValueError,'merge connected'):PlanarMagnetostaticCase.from_dict(data)
        data=copy.deepcopy(raw);data['boundaries'][2]['edge_indices'].append(10**100)
        with self.assertRaises(ValueError):PlanarMagnetostaticCase.from_dict(data)

    def test_layered_tangential_h_continuity_original_flux_and_magnetic_energy(self):
        for order in (1,2):
            for mu in (1.,7.):
                case,exact=layered_gap(order,mu_scale=mu,rotation=[[.6,-.8],[.8,.6]],shift=(-.5,.25));s=solve_planar_magnetostatic(case);q=planar_magnetostatic_quantities(s);p=case.partition
                np.testing.assert_allclose(s.az_wb_per_m,exact['fields'](s.space.dof_points_xy_m)[0],rtol=1e-11,atol=1e-13)
                points=p.mesh.points_xy_m[p.mesh.triangles].mean(axis=1);probe=s.probe_at(points)['fields'];az,b,h=exact['fields'](points)
                for names,expected in ((('Bx_T','By_T'),b),(('Hx_A_per_m','Hy_A_per_m'),h)):
                    np.testing.assert_allclose(np.column_stack([probe[k] for k in names]),expected,rtol=1e-10,atol=1e-11)
                self.assertAlmostEqual(q['energy_j_per_m']/exact['energy_j_per_m'],1.,places=11)
                for name,value in exact['region_energy_j_per_m'].items():self.assertAlmostEqual(q['region_energy_j_per_m'][name]/value,1.,places=11)
                for key in ('fixed_boundary_reaction_current_a','fixed_boundary_original_reaction_current_a'):
                    for name,value in exact['fixed_reaction_current_a'].items():self.assertAlmostEqual(q[key][name]/value,1.,places=11)
                for name,value in exact['boundary_normal_flux_wb_per_m'].items():self.assertLess(abs(q['boundary_original_normal_flux_wb_per_m'][name]-value),1e-13)
                for edge,cells in zip(p.interface_edges,p.interface_cells):
                    point=p.mesh.points_xy_m[edge].mean(axis=0);traces=[]
                    for cell in cells:
                        vertices=p.mesh.points_xy_m[p.mesh.triangles[cell]];bary=np.linalg.solve(np.vstack((vertices.T,np.ones(3))),np.r_[point,1.]);f=s.fields_in_cells([int(cell)],[bary]);traces.append([f['Hx_A_per_m'][0],f['Hy_A_per_m'][0]])
                    np.testing.assert_allclose(traces[0],traces[1],rtol=1e-10,atol=1e-10)
                self.assertNotIn('capacitance',q);self.assertNotIn('inductance',q)

    def test_manufactured_current_ampere_and_energy_on_concave_rotated_domains(self):
        for concave in (False,True):
            for direction in ('x','y'):
                for sign in (-1.,1.):
                    case,exact=manufactured_quadratic(concave=concave,direction=direction,amplitude=sign,rotation=[[.6,-.8],[.8,.6]],shift=(-.5,.25));s=solve_planar_magnetostatic(case);q=planar_magnetostatic_quantities(s)
                    np.testing.assert_allclose(s.az_wb_per_m,exact['fields'](s.space.dof_points_xy_m)[0],rtol=1e-11,atol=1e-13)
                    points=case.partition.mesh.points_xy_m[case.partition.mesh.triangles].mean(axis=1);f=s.probe_at(points)['fields'];ref=exact['fields'](points)
                    for names,expected in ((('Bx_T','By_T'),ref[1]),(('Hx_A_per_m','Hy_A_per_m'),ref[2])):np.testing.assert_allclose(np.column_stack([f[k] for k in names]),expected,rtol=1e-10,atol=1e-10)
                    self.assertAlmostEqual(q['energy_j_per_m']/exact['energy_j_per_m'],1.,places=11);self.assertAlmostEqual(q['total_source_current_a']/exact['source_current_a'],1.,places=12)
                    self.assertLess(abs(q['original_field_ampere_balance_a']/exact['source_current_a']),1e-10);self.assertLess(q['divergence_free_flux_relative_error'],1e-12)

    def test_uniform_current_original_b_h_energy_and_boundary_circulation_refine(self):
        for order in (1,2):
            errors=[]
            for n in (8,16,32):
                case,exact=rectangular_current(order,n);s=solve_planar_magnetostatic(case);q=planar_magnetostatic_quantities(s);cells=np.arange(len(case.partition.mesh.triangles));bary=np.full((len(cells),3),1/3)
                points=case.partition.mesh.points_xy_m[case.partition.mesh.triangles].mean(axis=1);f=s.fields_in_cells(cells,bary);az,b,h=exact['fields'](points,1024)
                errors.append([np.linalg.norm(f['Az_Wb_per_m']-az)/np.linalg.norm(az),np.linalg.norm(np.column_stack((f['Bx_T'],f['By_T']))-b)/np.linalg.norm(b),
                    np.linalg.norm(np.column_stack((f['Hx_A_per_m'],f['Hy_A_per_m']))-h)/np.linalg.norm(h),abs(q['energy_j_per_m']/exact['energy_j_per_m']-1),
                    abs(q['fixed_boundary_original_reaction_current_a']['fixed']/exact['fixed_reaction_current_a']['fixed']-1)])
                self.assertAlmostEqual(q['fixed_boundary_reaction_current_a']['fixed']/exact['fixed_reaction_current_a']['fixed'],1.,places=10)
            self.assertTrue(np.all(np.diff(errors,axis=0)<0),errors);limits=[.005,.05,.05,.004,.07] if order==1 else [.0001,.0015,.0015,1e-5,.0025]
            self.assertTrue(np.all(np.array(errors[-1])<limits),(errors[-1],limits))

    def test_constant_gauge_zero_field_and_strict_original_sampling(self):
        old=None
        for offset in (-.0002,.0022):
            case,_=layered_gap(offset=offset);s=solve_planar_magnetostatic(case);q=planar_magnetostatic_quantities(s)
            if old is not None:
                np.testing.assert_allclose(s.az_wb_per_m-old[0],.0024,rtol=0.,atol=1e-15);self.assertAlmostEqual(q['energy_j_per_m']/old[1],1.,places=11)
            old=s.az_wb_per_m,q['energy_j_per_m']
        case,_=layered_gap(az_difference=0.,offset=.0003);s=solve_planar_magnetostatic(case);q=planar_magnetostatic_quantities(s);np.testing.assert_array_equal(s.az_wb_per_m,.0003);self.assertEqual(q['energy_j_per_m'],0.)
        for bad in ([[False,0.]],[[0.,True]],[[1+0j,0.]],[["0",0.]],[[100.,100.]]):
            with self.assertRaises(ValueError):s.probe_at(bad)
        for cells,bary in (([True],[[1.,0.,0.]]),([0,True],[[1.,0.,0.],[1.,0.,0.]]),([0],[[False,.5,.5]]),([0],[[1.1,-.1,0.]]),([10**100],[[1.,0.,0.]])):
            with self.assertRaises(ValueError):s.fields_in_cells(cells,bary)
        self.assertEqual(s.probe_at(np.array([[.01,.01]],dtype=float))['fields']['Bx_T'],[0.])

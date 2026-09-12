# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.planar_electrostatic_reference import parallel_plate,manufactured_quadratic,rectangular_poisson
from superfish_ng.electrostatic_boundary import ElectrostaticBoundary
from superfish_ng.planar_electrostatic import PlanarElectrostaticCase,solve_planar_electrostatic,planar_electrostatic_quantities


class PlanarElectrostaticTests(unittest.TestCase):
    def test_explicit_planar_boundaries_reject_axis_rf_and_implicit_conditions(self):
        case,_=parallel_plate();raw=case.to_dict();self.assertEqual(raw,PlanarElectrostaticCase.from_dict(raw).to_dict())
        changes=[lambda d:d.update(physics='rf'),lambda d:d.update(modes=1),lambda d:d.update(schema_version=True),
            lambda d:d['boundaries'].pop(),lambda d:d['boundaries'][0].update(potential_v=True),
            lambda d:d['partition'].update(coordinates='axisymmetric_rz'),lambda d:d['partition'].update(thickness_m=1.),
            lambda d:d['charge_density_c_per_m3'].pop('bottom')]
        for change in changes:
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):PlanarElectrostaticCase.from_dict(data)
        data=copy.deepcopy(raw);boundary=data['boundaries'][-1];boundary['kind']='axis_symmetry';del boundary['outward_displacement_c_per_m2']
        with self.assertRaisesRegex(ValueError,'no symmetry axis'):PlanarElectrostaticCase.from_dict(data)
        data=copy.deepcopy(raw)
        for boundary in data['boundaries']:
            if boundary['kind']=='electrode_potential':boundary['kind']='outward_displacement';boundary['outward_displacement_c_per_m2']=0.;del boundary['potential_v']
        with self.assertRaisesRegex(ValueError,'pure Neumann'):PlanarElectrostaticCase.from_dict(data)
        data=copy.deepcopy(raw);extra=copy.deepcopy(data['boundaries'][0]);extra['id']='touching';extra['edge_indices']=extra['edge_indices'][:1];data['boundaries'][0]['edge_indices']=data['boundaries'][0]['edge_indices'][1:];data['boundaries'].append(extra)
        with self.assertRaisesRegex(ValueError,'merge connected'):PlanarElectrostaticCase.from_dict(data)

    def test_layered_exact_fields_interface_flux_capacitance_and_region_energy(self):
        for order in (1,2):
            c,ref=parallel_plate(order);s=solve_planar_electrostatic(c);q=planar_electrostatic_quantities(s)
            np.testing.assert_allclose(s.potential_v,ref['fields'](s.space.dof_points_xy_m)[0],rtol=1e-11,atol=1e-11)
            points=c.partition.mesh.points_xy_m[c.partition.mesh.triangles].mean(axis=1);probe=s.probe_at(points);phi,e,d=ref['fields'](points)
            np.testing.assert_allclose(np.column_stack((probe['fields']['Ex_V_per_m'],probe['fields']['Ey_V_per_m'])),e,rtol=1e-11,atol=1e-10)
            np.testing.assert_allclose(np.column_stack((probe['fields']['Dx_C_per_m2'],probe['fields']['Dy_C_per_m2'])),d,rtol=1e-11,atol=1e-20)
            for key in ('from_reaction_f_per_m','from_energy_f_per_m','from_original_field_f_per_m'):self.assertAlmostEqual(q['capacitance'][key]/ref['capacitance_f_per_m'],1.,places=11)
            for name,expected in ref['region_energy_j_per_m'].items():self.assertAlmostEqual(q['region_energy_j_per_m'][name]/expected,1.,places=11)
            for name,expected in ref['electrode_charge_c_per_m'].items():
                for key in ('electrode_reaction_charge_c_per_m','electrode_original_field_charge_c_per_m'):self.assertAlmostEqual(q[key][name]/expected,1.,places=11)
            for edge,cells in zip(c.partition.interface_edges,c.partition.interface_cells):
                point=c.partition.mesh.points_xy_m[edge].mean(axis=0);traces=[]
                for cell in cells:
                    vertices=c.partition.mesh.points_xy_m[c.partition.mesh.triangles[cell]];bary=np.linalg.solve(np.vstack((vertices.T,np.ones(3))),np.r_[point,1.])
                    fields=s.fields_in_cells([int(cell)],[bary]);traces.append([fields['Ex_V_per_m'][0],fields['Dy_C_per_m2'][0]])
                np.testing.assert_allclose(traces[0],traces[1],rtol=1e-10,atol=1e-10)

    def test_constant_potential_gauge_rigid_motion_and_planar_spatial_scale(self):
        base=solve_planar_electrostatic(parallel_plate()[0]);energy=planar_electrostatic_quantities(base)['energy_j_per_m'];rotation=np.array([[.6,-.8],[.8,.6]])
        for scale in (.5,2.):
            for voltage in (-5.,5.):
                c,ref=parallel_plate(scale=scale,voltage=voltage,offset=20.,rotation=rotation,shift=(-.5,.25))
                s=solve_planar_electrostatic(c);q=planar_electrostatic_quantities(s);self.assertAlmostEqual(q['energy_j_per_m']/energy,1.,places=10)
                points=c.partition.mesh.points_xy_m[c.partition.mesh.triangles].mean(axis=1);fields=s.probe_at(points)['fields'];expected=ref['fields'](points)[1]
                np.testing.assert_allclose(np.column_stack((fields['Ex_V_per_m'],fields['Ey_V_per_m'])),expected,rtol=1e-10,atol=1e-9)
        c,_=parallel_plate(voltage=0.,offset=3.);s=solve_planar_electrostatic(c);q=planar_electrostatic_quantities(s)
        np.testing.assert_array_equal(s.potential_v,3.);self.assertEqual(q['energy_j_per_m'],0.);self.assertIsNone(q['capacitance'])

    def test_manufactured_concave_signed_charge_and_neumann_data(self):
        rotation=np.array([[.6,-.8],[.8,.6]])
        for concave in (False,True):
            for direction in ('x','y'):
                for amplitude in (-100.,100.):
                    c,ref=manufactured_quadratic(concave=concave,direction=direction,amplitude=amplitude,rotation=rotation,shift=(-.25,.5))
                    s=solve_planar_electrostatic(c);q=planar_electrostatic_quantities(s)
                    np.testing.assert_allclose(s.potential_v,ref['fields'](s.space.dof_points_xy_m)[0],rtol=1e-11,atol=1e-11)
                    self.assertAlmostEqual(q['energy_j_per_m']/ref['energy_j_per_m'],1.,places=10)
                    self.assertAlmostEqual(q['volume_charge_c_per_m']/ref['volume_charge_c_per_m'],1.,places=12)
                    self.assertLess(abs(q['original_field_gauss_balance_c_per_m']/ref['volume_charge_c_per_m']),1e-10);self.assertIsNone(q['capacitance'])

    def test_rectangular_poisson_fourier_fields_energy_and_surface_charge_refine(self):
        # Coarse independent smoke gate. The dedicated analytical validator
        # uses finer levels and separate, stricter original-field thresholds.
        for order in (1,2):
            errors=[]
            for n in (8,16,32):
                c,ref=rectangular_poisson(order,n);s=solve_planar_electrostatic(c);q=planar_electrostatic_quantities(s)
                points=c.partition.mesh.points_xy_m[c.partition.mesh.triangles].mean(axis=1);fields=s.probe_at(points)['fields'];phi,e,d=ref['fields'](points);lower=ref['fields'](points,512)
                self.assertLess(np.linalg.norm(lower[1]-e)/np.linalg.norm(e),1e-8)
                actual=np.column_stack((fields['Ex_V_per_m'],fields['Ey_V_per_m']))
                errors.append([np.linalg.norm(np.asarray(fields['potential_V'])-phi)/np.linalg.norm(phi),np.linalg.norm(actual-e)/np.linalg.norm(e),abs(q['energy_j_per_m']/ref['energy_j_per_m']-1),abs(q['electrode_original_field_charge_c_per_m']['ground']/ref['electrode_charge_c_per_m']['ground']-1)])
                self.assertAlmostEqual(q['electrode_reaction_charge_c_per_m']['ground']/ref['electrode_charge_c_per_m']['ground'],1.,places=10)
            self.assertTrue(np.all(np.diff(np.asarray(errors),axis=0)<0))
            limits=[.005,.06,.004,.07] if order==1 else [.00008,.0015,5e-6,.002]
            self.assertTrue(np.all(np.asarray(errors[-1])<limits),(errors[-1],limits))

    def test_closed_domain_probes_and_original_side_at_dielectric_interface(self):
        c,ref=parallel_plate(shift=(-.125,-.0625));s=solve_planar_electrostatic(c);p=c.partition
        edge=p.interface_edges[0];point=p.mesh.points_xy_m[edge].mean(axis=0);probe=s.probe_at([point])
        self.assertEqual(probe['cell_indices'][0],int(min(p.interface_cells[0])));self.assertLess(point[0],0.)
        for bad in ([[10.,10.]],[[True,0.]],[[complex(0),0.]],[[float('nan'),0.]]):
            with self.assertRaises(ValueError):s.probe_at(bad)
        c,_=manufactured_quadratic(concave=True);s=solve_planar_electrostatic(c)
        with self.assertRaises(ValueError):s.probe_at([[.1,.05]])

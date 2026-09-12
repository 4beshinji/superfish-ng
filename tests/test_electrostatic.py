# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.electrostatic_reference import parallel_plate,coaxial_capacitor,manufactured_quadratic
from superfish_ng.constants import EPS0
from superfish_ng.electrostatic import AxisymmetricElectrostaticCase,solve_axisymmetric_electrostatic,electrostatic_quantities


class ElectrostaticCaseTests(unittest.TestCase):
    def test_explicit_boundary_partition_and_strict_static_case(self):
        case,_=parallel_plate();raw=case.to_dict();self.assertEqual(raw,AxisymmetricElectrostaticCase.from_dict(raw).to_dict())
        self.assertFalse(case.boundary_owner_indices.flags.writeable)
        with self.assertRaises(TypeError):case.charge_density_c_per_m3['bottom']=2.
        changes=[lambda d:d.update(physics='rf'),lambda d:d.update(modes=3),lambda d:d.update(schema_version=True),
            lambda d:d['boundaries'].pop(),lambda d:d['boundaries'][0].update(potential_v=True),
            lambda d:d['boundaries'][0].update(potential_v=10**1000),lambda d:d['boundaries'][0].update(kind=[]),
            lambda d:d['boundaries'][1].update(id='lower'),lambda d:d['boundaries'][0]['edge_indices'].append(10**100),
            lambda d:d['boundaries'][0]['edge_indices'].pop(),lambda d:d['charge_density_c_per_m3'].update(bottom=True),
            lambda d:d['partition']['materials'][0].update(mu_r=1.)]
        for change in changes:
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):AxisymmetricElectrostaticCase.from_dict(data)
        data=copy.deepcopy(raw)
        for boundary in data['boundaries']:
            if boundary['kind']=='electrode_potential':boundary['kind']='outward_displacement';boundary['outward_displacement_c_per_m2']=0.;del boundary['potential_v']
        with self.assertRaisesRegex(ValueError,'pure Neumann'):AxisymmetricElectrostaticCase.from_dict(data)

    def test_shared_electrode_nodes_and_axis_are_not_implicit_boundary_conditions(self):
        raw=parallel_plate()[0].to_dict();data=copy.deepcopy(raw);electrode=data['boundaries'][0]
        new=copy.deepcopy(electrode);new['id']='touching';new['edge_indices']=electrode['edge_indices'][:1];electrode['edge_indices']=electrode['edge_indices'][1:];data['boundaries'].append(new)
        with self.assertRaisesRegex(ValueError,'merge connected'):AxisymmetricElectrostaticCase.from_dict(data)
        data=copy.deepcopy(raw);axis=data['boundaries'][-1];axis.update(kind='electrode_potential',potential_v=0.)
        with self.assertRaisesRegex(ValueError,'axis edges'):AxisymmetricElectrostaticCase.from_dict(data)


class ElectrostaticSolveTests(unittest.TestCase):
    def test_layered_parallel_plate_potential_fields_capacitance_and_region_energy(self):
        for order in (1,2):
            case,exact=parallel_plate(order);s=solve_axisymmetric_electrostatic(case);q=electrostatic_quantities(s)
            points=case.partition.mesh.points_rz_m[case.partition.mesh.triangles].mean(axis=1)
            probe=s.probe_at(points);potential,electric,displacement=exact['fields'](points)
            np.testing.assert_allclose(s.potential_v,exact['fields'](s.space.dof_points)[0],rtol=1e-11,atol=1e-11)
            np.testing.assert_allclose(probe['fields']['Ez_V_per_m'],electric[:,1],rtol=1e-11,atol=1e-10)
            np.testing.assert_allclose(probe['fields']['Dz_C_per_m2'],displacement[:,1],rtol=1e-11,atol=1e-20)
            for key in ('from_reaction_f','from_energy_f','from_original_field_f'):
                self.assertAlmostEqual(q['capacitance'][key]/exact['capacitance_f'],1.,places=11)
            for name,expected in exact['region_energy_j'].items():self.assertAlmostEqual(q['region_energy_j'][name]/expected,1.,places=11)
            for name,expected in exact['electrode_charge_c'].items():
                for key in ('electrode_reaction_charge_c','electrode_original_field_charge_c'):self.assertAlmostEqual(q[key][name]/expected,1.,places=11)
            for edge,cells in zip(case.partition.interface_edges,case.partition.interface_cells):
                point=case.partition.mesh.points_rz_m[edge].mean(axis=0);traces=[]
                for cell in cells:
                    vertices=case.partition.mesh.points_rz_m[case.partition.mesh.triangles[cell]]
                    bary=np.linalg.solve(np.vstack((vertices.T,np.ones(3))),np.r_[point,1.])
                    fields=s.fields_in_cells([int(cell)],[bary]);traces.append([fields['Er_V_per_m'][0],fields['Dz_C_per_m2'][0]])
                np.testing.assert_allclose(traces[0],traces[1],rtol=1e-10,atol=1e-10)

    def test_coaxial_original_field_surface_charge_and_energy_refine_separately(self):
        for order in (1,2):
            errors=[]
            for n in (4,8,16):
                case,exact=coaxial_capacitor(order,n);s=solve_axisymmetric_electrostatic(case);q=electrostatic_quantities(s)
                points=case.partition.mesh.points_rz_m[case.partition.mesh.triangles].mean(axis=1)
                actual=np.column_stack([s.probe_at(points)['fields'][key] for key in ('Er_V_per_m','Ez_V_per_m')]);reference=exact['fields'](points)[1]
                errors.append([abs(q['capacitance']['from_energy_f']/exact['capacitance_f']-1),np.linalg.norm(actual-reference)/np.linalg.norm(reference),
                    max(abs(q['electrode_original_field_charge_c'][name]/charge-1) for name,charge in exact['electrode_charge_c'].items())])
            self.assertTrue(np.all(np.diff(np.asarray(errors),axis=0)<0))
            self.assertLess(errors[-1][0],.0002 if order==1 else 1e-7)
            self.assertLess(errors[-1][1],.015 if order==1 else .0003)
            self.assertLess(errors[-1][2],.031 if order==1 else .0007)

    def test_manufactured_negative_volume_charge_nonzero_outward_displacement_and_energy(self):
        for direction in ('axial','radial'):
            for axis in (False,True):
                for holes in (0,2):
                    case,exact=manufactured_quadratic(direction=direction,axis=axis,holes=holes);s=solve_axisymmetric_electrostatic(case);q=electrostatic_quantities(s)
                    np.testing.assert_allclose(s.potential_v,exact['fields'](s.space.dof_points)[0],rtol=1e-11,atol=1e-11)
                    self.assertAlmostEqual(q['energy_j']/exact['energy_j'],1.,places=11)
                    self.assertAlmostEqual(q['volume_charge_c']/exact['volume_charge_c'],1.,places=12)
                    self.assertLess(abs(q['original_field_gauss_balance_c']/exact['volume_charge_c']),1e-11)
                    self.assertIsNone(q['capacitance'])
                    if direction=='axial':self.assertLess(q['specified_neumann_outward_charge_c'],0.)

    def test_voltage_gauge_and_zero_field_preserve_static_invariants(self):
        reference=None
        for offset in (-2.,20.):
            case,exact=parallel_plate(offset=offset);s=solve_axisymmetric_electrostatic(case);q=electrostatic_quantities(s)
            self.assertAlmostEqual(q['energy_j']/exact['energy_j'],1.,places=10)
            if reference is None:reference=s.potential_v
            else:np.testing.assert_allclose(s.potential_v-reference,22.,rtol=0,atol=1e-10)
        case,_=parallel_plate(voltage=0.,offset=3.);s=solve_axisymmetric_electrostatic(case);q=electrostatic_quantities(s)
        np.testing.assert_allclose(s.potential_v,3.,rtol=0,atol=1e-12)
        self.assertLess(q['energy_j'],1e-30);self.assertIsNone(q['capacitance'])

# SPDX-License-Identifier: Apache-2.0
import copy,unittest
from dataclasses import replace
import numpy as np
from superfish_ng.constants import EPS0,MU0,TAU
from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi,restore_material_hphi
from superfish_ng.material_hphi_rf import material_hphi_quantities
from superfish_ng.rf_materials import RFMaterialPartition,LinearRFMaterial
from superfish_ng.axis_hphi import AxisHphiCase,AxisAccelerationPath,solve_axis_hphi,axis_hphi_quantities
from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh,hphi_mesh_quantities
from scripts.material_hphi_reference import layered_partition,layered_reference
from test_rf_materials import partition


class MaterialHphiTests(unittest.TestCase):
    def test_strict_physics_and_only_explicit_vacuum_axis_path(self):
        case=MaterialHphiCase(partition(True,1,uniform=(1.,1.)),modes=2,acceleration=AxisAccelerationPath(.01,.08,.7,.02))
        raw=case.to_dict();self.assertEqual(MaterialHphiCase.from_dict(raw).to_dict(),raw)
        changes=[lambda x:x.update(extra=1),lambda x:x.update(schema_version=True),
            lambda x:x['model'].update(azimuthal_index=True),lambda x:x['model'].update(material='vacuum'),
            lambda x:x['fem'].update(element_order=True),lambda x:x['fem'].update(quadrature_order=3),
            lambda x:x['rf'].update(wall_relative_permeability=2),lambda x:x['rf'].update(loss_tangent=.1),
            lambda x:x['partition']['materials'][0].update(epsilon_r=4.)]
        for change in changes:
            bad=copy.deepcopy(raw);change(bad)
            with self.assertRaises(ValueError):MaterialHphiCase.from_dict(bad)
        with self.assertRaises(ValueError):replace(case,partition=partition(False,1,uniform=(1.,1.)))
        p=partition(True,0);p=RFMaterialPartition(p.mesh,[LinearRFMaterial('low',1.,1.),p.materials[1]],p.regions)
        replace(case,partition=p,acceleration=AxisAccelerationPath(.01,1/16,.7,0.))
        with self.assertRaises(ValueError):replace(case,partition=p,acceleration=AxisAccelerationPath(.01,.08,.7,0.))

    def test_uniform_material_frequency_fields_energy_and_metal_wall_scaling(self):
        for axis in (False,True):
            for order in (1,2):
                p=partition(axis,1,uniform=(1.,1.));case=MaterialHphiCase(p,element_order=order,modes=2)
                if axis:
                    case=replace(case,acceleration=AxisAccelerationPath(.01,.08,.7,.02))
                    old=solve_axis_hphi(AxisHphiCase(p.mesh,element_order=order,modes=2,acceleration=case.acceleration));rf=axis_hphi_quantities
                else:old=solve_hphi_mesh(HphiMeshCase(p.mesh,element_order=order,quadrature_order=12,modes=2));rf=hphi_mesh_quantities
                vacuum=solve_material_hphi(case);material=solve_material_hphi(replace(case,partition=partition(axis,1,uniform=(4.,9.)),acceleration=None))
                np.testing.assert_allclose(vacuum.frequencies_hz,old.frequencies_hz,rtol=1e-10)
                np.testing.assert_allclose(material.frequencies_hz*6,vacuum.frequencies_hz,rtol=1e-10)
                cells=np.arange(len(p.mesh.triangles));bary=np.full((len(cells),3),1/3)
                for mode in range(2):
                    reference=vacuum.fields_in_cells(cells,bary,mode);actual=material.fields_in_cells(cells,bary,mode)
                    sign=np.sign(reference['Hphi_real_A_per_m']@actual['Hphi_real_A_per_m'])
                    for key,factor in (('Hphi_real_A_per_m',1/3),('Er_quadrature_V_per_m',.5),('Ez_quadrature_V_per_m',.5),('Bphi_real_T',3.)):
                        self.assertLess(np.linalg.norm(sign*actual[key]-factor*reference[key])/max(np.linalg.norm(factor*reference[key]),1e-20),1e-8)
                    a=material_hphi_quantities(vacuum,mode);b=material_hphi_quantities(material,mode);original=rf(old,mode)
                    for key in ('frequency_hz','stored_energy_j','wall_loss_w','q0','geometry_factor_ohm'):
                        self.assertAlmostEqual(a[key]/original[key],1.,delta=1e-8)
                    for key,factor in (('wall_loss_w',1/(9*np.sqrt(6))),('q0',9/np.sqrt(6)),('geometry_factor_ohm',1.5)):
                        self.assertAlmostEqual(b[key]/a[key],factor,delta=1e-8)
                    for key in ('electric_energy_j','magnetic_energy_j'):self.assertAlmostEqual(b[key],.5,delta=1e-9)
                    self.assertIsNone(b['r_over_q_accelerator_ohm']);self.assertEqual(b['volume_loss_w'],0.)
                    if axis:
                        for key in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm'):self.assertAlmostEqual(a[key]/original[key],1.,delta=1e-8)

    def test_original_piecewise_polynomials_and_one_sided_material_metadata(self):
        # A manufactured field checks the evaluator, not PEC resonance/RF.
        for axis in (False,True):
            for order in (1,2):
                case=MaterialHphiCase(partition(axis,2),element_order=order,modes=1);solution=solve_material_hphi(case)
                r,z=solution.space.dof_points.T;cut=1/16;f=lambda z:1+2*np.minimum(z,cut)+5*np.maximum(z-cut,0.)
                polynomial=replace(solution,coefficients=f(z)[:,None]);p=case.partition
                for edge,cells in zip(p.interface_edges,p.interface_cells):
                    point=p.mesh.points_rz_m[edge].mean(axis=0);r,z=point
                    for cell in cells:
                        bary=np.zeros(3);tri=p.mesh.triangles[cell]
                        for vertex in edge:bary[np.flatnonzero(tri==vertex)[0]]=.5
                        fields=polynomial.fields_in_cells([int(cell)],[bary]);omega=TAU*solution.frequencies_hz[0]
                        expected=[r*f(z),r,-2*f(z)] if axis else [f(z)/r,1/r,0.]
                        actual=[fields['Hphi_real_A_per_m'][0],omega*EPS0*fields['Er_quadrature_V_per_m'][0],omega*EPS0*p.epsilon_r[cell]*fields['Ez_quadrature_V_per_m'][0]]
                        np.testing.assert_allclose(actual,expected,rtol=1e-11,atol=1e-11)
                        self.assertAlmostEqual(fields['Bphi_real_T'][0]/(MU0*p.mu_r[cell]*expected[0]),1.,delta=1e-12)
                    probe=polynomial.probe_at([point]);owner=probe['cell_indices'][0]
                    self.assertEqual(owner,int(min(cells)));self.assertEqual(probe['epsilon_r'][0],p.epsilon_r[owner])
                if axis:
                    fields=polynomial.fields_at([[0.,.073]])
                    self.assertEqual(fields['Hphi_real_A_per_m'][0],0.);self.assertEqual(fields['Er_quadrature_V_per_m'][0],0.)
                for hole in p.mesh.holes_rz_m:
                    with self.assertRaises(ValueError):polynomial.fields_at([hole.mean(axis=0)])

    def test_full_original_reconstruction_rejects_static_tampering_and_shifted_band(self):
        for axis in (False,True):
            case=MaterialHphiCase(partition(axis,1),modes=3);solution=solve_material_hphi(case)
            restored=restore_material_hphi(case,solution.coefficients,solution.frequencies_hz)
            np.testing.assert_array_equal(restored.coefficients,solution.coefficients)
            for coefficients,frequencies in ((solution.coefficients*2,solution.frequencies_hz),(solution.coefficients,solution.frequencies_hz*1.01),
                    (solution.coefficients[:,::-1],solution.frequencies_hz[::-1]),(solution.coefficients.astype(int),solution.frequencies_hz)):
                with self.assertRaises(ValueError):restore_material_hphi(case,coefficients,frequencies)
            with self.assertRaises(ValueError):restore_material_hphi(replace(case,modes=2),solution.coefficients[:,1:],solution.frequencies_hz[1:])
            if not axis:
                with self.assertRaises(ValueError):restore_material_hphi(case,solution.coefficients+1.,solution.frequencies_hz)

    def test_layered_resonance_refines_frequency_field_and_wall_separately(self):
        previous=None
        for nz in (12,24):
            solution=solve_material_hphi(MaterialHphiCase(layered_partition(nz=nz),modes=2));errors=[]
            centers=solution.case.partition.mesh.points_rz_m[solution.case.partition.mesh.triangles].mean(axis=1)
            for mode in range(2):
                expected,fields=layered_reference(mode+1);h,er,ez=fields(centers);actual=solution.fields_at(centers,mode)
                sign=np.sign(h@actual['Hphi_real_A_per_m']);rf=material_hphi_quantities(solution,mode)
                error=[abs(solution.frequencies_hz[mode]/expected['frequency_hz']-1),
                    np.linalg.norm(sign*actual['Hphi_real_A_per_m']-h)/np.linalg.norm(h),
                    np.linalg.norm(sign*actual['Er_quadrature_V_per_m']-er)/np.linalg.norm(er),
                    abs(rf['wall_loss_w']/expected['wall_loss_w']-1)]
                self.assertLess(error[0],1e-4);self.assertLess(max(error[1:]),.01)
                for index,key in enumerate(('electric_energy_j','magnetic_energy_j')):
                    np.testing.assert_allclose([r[key] for r in rf['regions']],expected[key+'_by_region'],rtol=.01)
                errors.append(error)
            errors=np.array(errors)
            if previous is not None:self.assertTrue(np.all(errors<previous))
            previous=errors

    def test_energy_conductivity_and_clipped_vacuum_voltage_are_independent(self):
        p=partition(True,1);p=RFMaterialPartition(p.mesh,[LinearRFMaterial('low',1.,1.),p.materials[1]],p.regions)
        path=AxisAccelerationPath(.011,.059,.63,.019)
        case=MaterialHphiCase(p,modes=1,acceleration=path);base=solve_material_hphi(case)
        changed=solve_material_hphi(replace(case,normalization_j=4.,conductivity_s_per_m=4*case.conductivity_s_per_m))
        a=material_hphi_quantities(base);b=material_hphi_quantities(changed)
        for key,factor in (('frequency_hz',1.),('stored_energy_j',4.),('electric_energy_j',4.),('magnetic_energy_j',4.),
                ('wall_loss_w',2.),('surface_resistance_ohm',.5),('q0',2.),('geometry_factor_ohm',1.),
                ('r_over_q_accelerator_ohm',1.),('r_over_q_circuit_ohm',1.)):
            self.assertAlmostEqual(b[key]/a[key],factor,delta=1e-9)
        # Independent Gauss integration of each original axis polynomial.
        gauss,weights=np.polynomial.legendre.leggauss(32);voltage=0j;omega=TAU*base.frequencies_hz[0]
        for edge in base.space.boundary_dofs[p.mesh.axis_edges]:
            z=base.space.dof_points[edge,1];low=max(z[:2].min(),path.z_start_m);high=min(z[:2].max(),path.z_end_m)
            if low>=high:continue
            sampled=low+(gauss+1)*(high-low)/2;t=(sampled-z[0])/(z[1]-z[0])
            polynomial=np.linalg.solve(np.column_stack((np.ones(3),[0.,1.,.5],[0.,1.,.25])),base.coefficients[edge,0])
            scalar=np.column_stack((np.ones(len(t)),t,t*t))@polynomial
            voltage+=(high-low)/2*np.dot(weights,-2j*scalar/(omega*EPS0)*np.exp(1j*omega*(sampled-path.phase_origin_m)/(path.beta*299792458.)))
        actual=complex(a['vacc_v']['real'],a['vacc_v']['imag'])
        self.assertLess(abs(actual/voltage-1),1e-12)
        self.assertAlmostEqual(a['r_over_q_accelerator_ohm']/a['r_over_q_circuit_ohm'],2.,delta=1e-12)

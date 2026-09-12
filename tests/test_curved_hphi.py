# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi import CurvedHphiCase,solve_curved_hphi,restore_curved_hphi
from superfish_ng.curved_hphi_rf import curved_hphi_quantities
from superfish_ng.axis_hphi import AxisHphiCase,AxisAccelerationPath,solve_axis_hphi,axis_hphi_quantities
from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh,hphi_mesh_quantities
from superfish_ng.constants import C0,TAU


def voltage(result):
    value=result['vacc_v'];return complex(value['real'],value['imag'])


class CurvedHphiTests(unittest.TestCase):
    def case(self,axis=False,holes=1,order=2,shear=1.,scale=1.,energy=1.,modes=2):
        data,_=fixture(axis,holes,scale=scale,shear=shear)
        path=AxisAccelerationPath(0.,3/16*scale,.8,.02*scale) if axis else None
        return CurvedHphiCase(CurvedMeridionalGeometry(**data),element_order=order,modes=modes,normalization_j=energy,acceleration=path)

    def test_affine_limit_preserves_frequencies_fields_and_every_rf_integral(self):
        quantities=('stored_energy_j','electric_energy_j','magnetic_energy_j','wall_loss_w','surface_resistance_ohm','q0','geometry_factor_ohm','volume_m3')
        for axis in (False,True):
            for holes in (0,1,2):
                for order in (1,2):
                    case=self.case(axis,holes,order,shear=0.);solution=solve_curved_hphi(case)
                    if axis:
                        old=solve_axis_hphi(AxisHphiCase(case.geometry.base_mesh,element_order=order,modes=2,acceleration=case.acceleration));rf=axis_hphi_quantities
                    else:
                        old=solve_hphi_mesh(HphiMeshCase(case.geometry.base_mesh,element_order=order,modes=2,quadrature_order=12));rf=hphi_mesh_quantities
                    np.testing.assert_allclose(solution.frequencies_hz,old.frequencies_hz,rtol=1e-10,atol=0)
                    cells=np.arange(len(case.geometry.cell_nodes));bary=np.tile([.2,.3,.5],(len(cells),1))
                    for mode in range(2):
                        phase=np.sign(solution.coefficients[:,mode]@solution.mass@old.coefficients[:,mode])
                        a=solution.fields_in_cells(cells,bary,mode);b=old.fields_in_cells(cells,bary,mode)
                        for key in a:
                            self.assertLess(np.linalg.norm(a[key]-phase*b[key])/max(np.linalg.norm(b[key]),1.),1e-9)
                        a=curved_hphi_quantities(solution,mode);b=rf(old,mode)
                        for key in quantities:self.assertAlmostEqual(a[key]/b[key],1.,places=9)
                        for key in ('wall_h2_integral_a2_by_segment','wall_h2_integral_a2_by_component','surface_area_m2_by_segment'):
                            np.testing.assert_allclose(a[key],b[key],rtol=1e-9,atol=1e-16)
                        if axis:
                            self.assertLess(abs(voltage(a)-phase*voltage(b))/max(abs(voltage(b)),1.),1e-9)
                            self.assertAlmostEqual(a['r_over_q_accelerator_ohm']/b['r_over_q_accelerator_ohm'],1.,places=9)
                        else:self.assertIsNone(a['vacc_v'])

    def test_curved_probes_restore_and_conductor_rejection(self):
        for axis in (False,True):
            case=self.case(axis,2);solution=solve_curved_hphi(case)
            restored=restore_curved_hphi(case,solution.coefficients,solution.frequencies_hz)
            np.testing.assert_array_equal(restored.coefficients,solution.coefficients)
            cells=np.arange(len(case.geometry.cell_nodes));bary=np.tile([.2,.3,.5],(len(cells),1))
            points=solution.mapped_points(cells,bary)[0]
            direct=solution.fields_in_cells(cells,bary);probes=solution.fields_at(points)
            for key in direct:self.assertLess(np.linalg.norm(direct[key]-probes[key])/max(np.linalg.norm(direct[key]),1.),1e-10)
            # The known shear maps a source hole center into the same conductor.
            original,_=fixture(axis,2,shear=0.);hole=original['base_mesh'].holes_rz_m[0];center=(hole.min(axis=0)+hole.max(axis=0))/2;center[1]+=center[0]**2
            for point in (center,[1.,1.],[-.01,0.]):
                with self.assertRaises(ValueError):solution.fields_at([point])
            if axis:
                values=solution.fields_at([[0.,.07]])
                self.assertEqual(values['Hphi_real_A_per_m'][0],0.)
                self.assertEqual(values['Er_quadrature_V_per_m'][0],0.)
                self.assertTrue(np.isfinite(values['Ez_quadrature_V_per_m'][0]))
            with self.assertRaises(ValueError):restore_curved_hphi(case,solution.coefficients*2,solution.frequencies_hz)
            with self.assertRaises(ValueError):restore_curved_hphi(case,solution.coefficients,solution.frequencies_hz*1.01)
            for cells,bary in (([True],[[1,0,0]]),([0],[[1.01,-.01,0]])):
                with self.assertRaises(ValueError):solution.fields_in_cells(cells,bary)

    def test_physical_scaling_energy_conductivity_and_axis_phase(self):
        for axis in (False,True):
            case=self.case(axis,1,modes=1);solution=solve_curved_hphi(case);a=curved_hphi_quantities(solution)
            changed=solve_curved_hphi(replace(case,normalization_j=4.,conductivity_s_per_m=4*case.conductivity_s_per_m));b=curved_hphi_quantities(changed)
            np.testing.assert_array_equal(changed.frequencies_hz,solution.frequencies_hz)
            self.assertAlmostEqual(b['stored_energy_j']/a['stored_energy_j'],4.,places=10)
            self.assertAlmostEqual(b['wall_loss_w']/a['wall_loss_w'],2.,places=10)
            self.assertAlmostEqual(b['q0']/a['q0'],2.,places=10)
            self.assertAlmostEqual(b['geometry_factor_ohm']/a['geometry_factor_ohm'],1.,places=10)
            scaled=solve_curved_hphi(self.case(axis,1,scale=2.,energy=8.,modes=1));c=curved_hphi_quantities(scaled)
            self.assertAlmostEqual(c['frequency_hz']/a['frequency_hz'],.5,places=10)
            self.assertAlmostEqual(c['q0']/a['q0'],np.sqrt(2),places=9)
            self.assertAlmostEqual(c['geometry_factor_ohm']/a['geometry_factor_ohm'],1.,places=9)
            if axis:
                self.assertLess(abs(voltage(b)/voltage(a)-2),1e-10)
                self.assertLess(abs(voltage(c)/voltage(a)-2),1e-9)
                self.assertAlmostEqual(c['r_over_q_accelerator_ohm']/a['r_over_q_accelerator_ohm'],1.,places=9)
                shifted=solve_curved_hphi(replace(case,acceleration=replace(case.acceleration,phase_origin_m=.03)))
                d=curved_hphi_quantities(shifted)
                expected=np.exp(-1j*TAU*a['frequency_hz']*.01/(case.acceleration.beta*C0))
                self.assertLess(abs(voltage(d)/voltage(a)-expected),1e-10)
                absent=solve_curved_hphi(replace(case,acceleration=None));self.assertIsNone(curved_hphi_quantities(absent)['vacc_v'])

    def test_strict_case_models_paths_and_modes(self):
        case=self.case();self.assertEqual(case.to_dict(),CurvedHphiCase.from_dict(case.to_dict()).to_dict())
        for group,key,value in ((None,'schema_version',True),(None,'modes',True),('model','azimuthal_index',1),('model','material','dielectric'),('fem','element_order',3),('rf','stored_energy_j',-1)):
            raw=case.to_dict();target=raw if group is None else raw[group];target[key]=value
            with self.assertRaises(ValueError):CurvedHphiCase.from_dict(raw)
        with self.assertRaises(ValueError):replace(case,acceleration=AxisAccelerationPath(0.,.1,1.,0.))
        with self.assertRaises(ValueError):replace(self.case(True),acceleration=AxisAccelerationPath(-.01,.1,1.,0.))
        with self.assertRaises(ValueError):solve_curved_hphi(replace(case,modes=100000))

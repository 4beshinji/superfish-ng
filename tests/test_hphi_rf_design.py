# SPDX-License-Identifier: Apache-2.0
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.constants import C0, MU0, TAU
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.axis_hphi import AxisHphiCase, AxisAccelerationPath
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.curved_hphi import CurvedHphiCase
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.material_hphi import MaterialHphiCase
from superfish_ng.hphi_native import solve_hphi, save_hphi_run, hphi_result
from superfish_ng.rf_optimization import (observe_hphi_rf_design, save_hphi_rf_design,
    read_hphi_rf_design, validate_hphi_rf_criteria)
from superfish_ng.hphi_rf_design import hphi_rf_capabilities
from scripts.curved_meridional_reference import fixture
from scripts.material_hphi_reference import layered_partition, layered_reference
from test_rf_materials import partition


def criteria(quantity='q0'):
    return dict(schema_version=1, objective=dict(quantity=quantity, direction='maximize'),
                constraints=[dict(quantity='frequency_hz', lower=0.)])


def snapshot(path):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir()}


class HphiRFDesignTests(unittest.TestCase):
    def save(self, case, directory):
        solution = solve_hphi(case); save_hphi_run(case, solution, directory)
        return solution

    def test_capability_and_strict_criteria_reject_before_native_reconstruction(self):
        case = CoaxialCase(.03125, .046875, .1875, nr=3, nz=6, modes=2)
        self.assertNotIn('r_over_q_accelerator_ohm', hphi_rf_capabilities(case)['available'])
        self.assertEqual(validate_hphi_rf_criteria(case, criteria()), criteria())
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)/'native'; self.save(case, directory)
            bad = [criteria(q) for q in ['r_over_q_accelerator_ohm', 'r_over_q_circuit_ohm',
                'epk_over_eacc', 'bpk_over_eacc_mt_per_mv_per_m', 'total_q', 'volume_loss_w', 'stored_energy_j', 'Q0']]
            for mutation in [lambda d:d.update(extra=1), lambda d:d.update(schema_version=True),
                lambda d:d['objective'].update(direction='best'),
                lambda d:d['constraints'][0].update(lower=True),
                lambda d:d['constraints'][0].update(lower=float('nan')),
                lambda d:d['constraints'][0].update(lower=2., upper=1.),
                lambda d:d['constraints'].append(copy.deepcopy(d['constraints'][0]))]:
                value=criteria();mutation(value);bad.append(value)
            with patch('superfish_ng.hphi_rf_design.read_hphi_run', side_effect=AssertionError('FEM replay entered')):
                for value in bad:
                    with self.subTest(value=value), self.assertRaises(ValueError):
                        observe_hphi_rf_design(directory, value)
                for rank in [True, 0, 3, 1.]:
                    with self.assertRaises(ValueError):observe_hphi_rf_design(directory, criteria(), rank)
            with self.assertRaises(ValueError):
                save_hphi_rf_design(directory, criteria(), directory/'observation.json')
            self.assertEqual(set(snapshot(directory)), {'case.json','mesh.npz','fields.npz','results.json','manifest.json'})

    def test_coaxial_two_scales_independent_tem_fields_wall_loss_and_no_adoption(self):
        with tempfile.TemporaryDirectory() as temporary:
            reports=[]
            for scale in (1., 2.):
                a,b,length=scale*np.array([.03125,.046875,.1875])
                case=CoaxialCase(a,b,length,nr=4,nz=24,modes=2)
                directory=Path(temporary)/str(scale);solution=self.save(case,directory)
                before=snapshot(directory);report=observe_hphi_rf_design(directory,criteria())
                self.assertEqual(snapshot(directory),before)
                frequency=C0/(2*length);c2=2/(MU0*np.pi*length*np.log(b/a))
                wall=np.pi*c2*length*(1/a+1/b)+4*np.pi*c2*np.log(b/a)
                rs=np.sqrt(np.pi*frequency*MU0/case.conductivity_s_per_m);loss=rs*wall/2
                self.assertLess(abs(report['observations']['frequency_hz']['value']/frequency-1),1e-5)
                self.assertLess(abs(report['rf']['wall_loss_w']/loss-1),.002)
                self.assertLess(abs(report['observations']['q0']['value']/(TAU*frequency/loss)-1),.002)
                points=np.array([[a*.7+b*.3,length*.31],[a*.3+b*.7,length*.73]])
                fields=solution.fields_at(points)
                expected_h=np.sqrt(c2)/points[:,0]*np.cos(np.pi*points[:,1]/length)
                sign=np.sign(np.dot(expected_h,fields['Hphi_real_A_per_m']))
                np.testing.assert_allclose(sign*fields['Hphi_real_A_per_m'],expected_h,rtol=.002)
                self.assertIsNone(report['rf']['r_over_q_accelerator_ohm'])
                self.assertIsNone(report['rf']['r_over_q_circuit_ohm'])
                self.assertEqual(report['status'],'UNVERIFIED');self.assertIsNone(report['objective']['eligible_value'])
                self.assertIsNone(report['mode_identity']);self.assertTrue(all(x['status']=='UNVERIFIED' for x in report['constraints']))
                reports.append(report)
            for name,factor in [('frequency_hz',.5),('geometry_factor_ohm',1.),('q0',np.sqrt(2)),('wall_loss_w',1/(2*np.sqrt(2)))]:
                self.assertAlmostEqual(reports[1]['observations'][name]['value']/reports[0]['observations'][name]['value'],factor,delta=1e-9)

    def test_five_native_types_preserve_full_domain_and_explicit_axis_quantities(self):
        data,_=fixture(True,1,shear=0.);mesh=data['base_mesh'];path=AxisAccelerationPath(.01,.08,.7,.02)
        positive=fixture(False,1,shear=0.)[0]['base_mesh']
        cases=[CoaxialCase(.03125,.046875,.1875,nr=3,nz=6,modes=2),
            HphiMeshCase(positive,element_order=2,quadrature_order=12,modes=2),
            AxisHphiCase(mesh,element_order=2,modes=2,acceleration=path),
            CurvedHphiCase(CurvedMeridionalGeometry(**data),element_order=2,modes=2,acceleration=path),
            MaterialHphiCase(partition(True,1,uniform=(1.,1.)),modes=2,acceleration=path)]
        with tempfile.TemporaryDirectory() as temporary:
            for index,case in enumerate(cases):
                directory=Path(temporary)/str(index);solution=self.save(case,directory)
                report=observe_hphi_rf_design(directory,criteria())
                self.assertEqual(report['case'],case.to_dict())
                self.assertEqual(report['rf'],hphi_result(solution)['modes'][0])
                self.assertAlmostEqual(report['rf']['stored_energy_j'],case.normalization_j,delta=1e-8)
                if index>=2:
                    requested=observe_hphi_rf_design(directory,criteria('r_over_q_accelerator_ohm'))
                    self.assertAlmostEqual(requested['rf']['r_over_q_accelerator_ohm']/requested['rf']['r_over_q_circuit_ohm'],2.,delta=1e-12)
                self.assertEqual(report['capabilities']['q0_loss_model'],'wall_only')

    def test_uniform_and_two_layer_material_independent_frequency_fields_and_wall(self):
        with tempfile.TemporaryDirectory() as temporary:
            vacuum=MaterialHphiCase(partition(False,1,uniform=(1.,1.)),modes=2)
            material=replace(vacuum,partition=partition(False,1,uniform=(4.,9.)))
            observations=[];solutions=[]
            for index,case in enumerate([vacuum,material]):
                directory=Path(temporary)/str(index);solutions.append(self.save(case,directory))
                observations.append(observe_hphi_rf_design(directory,criteria()))
            a,b=observations
            for name,factor in [('frequency_hz',1/6),('q0',9/np.sqrt(6)),('geometry_factor_ohm',1.5),('wall_loss_w',1/(9*np.sqrt(6)))]:
                self.assertAlmostEqual(b['observations'][name]['value']/a['observations'][name]['value'],factor,delta=1e-8)
            cells=np.arange(len(vacuum.partition.mesh.triangles));bary=np.full((len(cells),3),1/3)
            original,changed=[s.fields_in_cells(cells,bary) for s in solutions]
            sign=np.sign(original['Hphi_real_A_per_m']@changed['Hphi_real_A_per_m'])
            np.testing.assert_allclose(sign*changed['Hphi_real_A_per_m'],original['Hphi_real_A_per_m']/3,rtol=1e-8,atol=1e-8)
            case=MaterialHphiCase(layered_partition(nz=24),modes=2);directory=Path(temporary)/'layered';solution=self.save(case,directory)
            report=observe_hphi_rf_design(directory,criteria());expected,field=layered_reference(1)
            self.assertLess(abs(report['rf']['frequency_hz']/expected['frequency_hz']-1),1e-4)
            self.assertLess(abs(report['rf']['wall_loss_w']/expected['wall_loss_w']-1),.01)
            centers=case.partition.mesh.points_rz_m[case.partition.mesh.triangles].mean(axis=1)
            h,er,ez=field(centers);actual=solution.fields_at(centers);sign=np.sign(h@actual['Hphi_real_A_per_m'])
            for key,values in [('Hphi_real_A_per_m',h),('Er_quadrature_V_per_m',er)]:
                self.assertLess(np.linalg.norm(sign*actual[key]-values)/np.linalg.norm(values),.01)
            self.assertEqual(len(report['rf']['regions']),2);self.assertEqual(report['rf']['volume_loss_w'],0.)
            bad=MaterialHphiCase(partition(True,0),modes=2).to_dict();bad['acceleration']=AxisAccelerationPath(.01,.08,.7,0.).to_dict()
            from superfish_ng.hphi_native import hphi_case_from_dict
            with self.assertRaises(ValueError):hphi_case_from_dict(bad)

    def test_complete_observation_replay_move_and_forged_boolean_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'original';root.mkdir();native=root/'native'
            self.save(CoaxialCase(.03125,.046875,.1875,nr=3,nz=6,modes=2),native)
            before=snapshot(native);path=root/'observation.json';report=save_hphi_rf_design(native,criteria(),path)
            self.assertEqual(report,read_hphi_rf_design(path));self.assertEqual(snapshot(native),before)
            with self.assertRaises(FileExistsError):save_hphi_rf_design(native,criteria(),path)
            moved=Path(temporary)/'moved';shutil.move(root,moved);path=moved/'observation.json'
            self.assertEqual(report,read_hphi_rf_design(path))
            for mutation in [lambda d:d['objective'].update(eligible_value=1.),lambda d:d.update(status='CRITERIA_MET'),
                lambda d:d.update(mode_rank=True),lambda d:d['rf'].update(stored_energy_j=True),lambda d:d.update(extra=1)]:
                bad=copy.deepcopy(report);mutation(bad);path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):read_hphi_rf_design(path)
            path.write_text(json.dumps(report));(moved/'native/results.json').write_text('{}')
            with self.assertRaises(ValueError):read_hphi_rf_design(path)

    def test_late_native_change_rejected_and_original_tm_units_unchanged(self):
        import superfish_ng.hphi_rf_design as adapter
        from superfish_ng.rf_design import UNITS
        self.assertEqual(len(UNITS),6);self.assertNotIn('q0',UNITS);self.assertNotIn('wall_loss_w',UNITS)
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)/'native';self.save(CoaxialCase(.03125,.046875,.1875,nr=3,nz=6,modes=2),directory)
            original=adapter.hphi_result
            def change(solution):
                result=original(solution);path=directory/'results.json';path.write_bytes(path.read_bytes()+b' ');return result
            with patch.object(adapter,'hphi_result',side_effect=change),self.assertRaisesRegex(ValueError,'changed during observation'):
                observe_hphi_rf_design(directory,criteria())

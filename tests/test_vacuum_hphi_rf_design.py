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
from superfish_ng.constants import C0, MU0, EPS0, TAU
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.axis_hphi import AxisHphiCase, AxisAccelerationPath
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.hphi_native import solve_hphi, save_hphi_run, hphi_result
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_convergence import HphiConvergence, _project_mesh
from superfish_ng.hphi_tracking import HphiTrackingRequest
from superfish_ng.hphi_tuning import _refine_mesh
from superfish_ng.vacuum_hphi_convergence import VacuumHphiConvergence, compare_vacuum_hphi_convergence
from superfish_ng.rf_optimization import (assess_vacuum_hphi_rf_design,
    save_vacuum_hphi_rf_design, read_vacuum_hphi_rf_design)
from test_hphi_rf_design import criteria
from test_meridional_overlap import fixture


def declaration(projects):
    comparisons=[_refine_mesh(_project_mesh(p)) for p in projects]
    pairs=[HphiTrackingRequest(comparisons[i],comparisons[i+1],
        previous_mode_count=1,current_mode_count=1,previous_mode_ids=('mode-1',)) for i in range(2)]
    return VacuumHphiConvergence(HphiConvergence(projects),pairs)


def sequence():
    return declaration([HphiProject(CoaxialCase(.03125,.046875,.1875,
        nr=2*2**i,nz=6*2**i,modes=2)) for i in range(3)])


class VacuumHphiRFDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.root=Path(cls.temporary.name)
        cls.request=sequence();cls.solutions=[];cls.runs=[]
        for index,project in enumerate(cls.request.convergence.projects):
            solution=solve_hphi(project.case);run=cls.root/str(index)
            save_hphi_run(project.case,solution,run);cls.solutions.append(solution);cls.runs.append(run)
        cls.hashes=cls.snapshot()

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    @classmethod
    def snapshot(cls):
        return [{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()} for run in cls.runs]

    def test_three_actual_coaxial_levels_independent_tem_fields_wall_and_guard(self):
        report=assess_vacuum_hphi_rf_design(self.runs,self.request,criteria())
        self.assertEqual(report['status'],'CRITERIA_MET',report['assessment'])
        assessment=report['assessment'];self.assertEqual(assessment['mode_ranks'],[1,1,1])
        self.assertTrue(assessment['individual_ids_complete'])
        self.assertEqual(len([k for k in assessment['checks'] if k.startswith('wall_segment/')]),4)
        self.assertEqual(len([k for k in assessment['checks'] if k.startswith('wall_component/')]),1)
        self.assertEqual(report['objective']['eligible_value'],min(rf['q0'] for rf in assessment['selected_rf']))
        previous=None;errors=[]
        for solution,rf in zip(self.solutions,assessment['selected_rf']):
            a,b,length=solution.case.inner_radius_m,solution.case.outer_radius_m,solution.case.length_m
            f=C0/(2*length);c2=2/(MU0*np.pi*length*np.log(b/a))
            wall=np.pi*c2*length*(1/a+1/b)+4*np.pi*c2*np.log(b/a)
            loss=np.sqrt(np.pi*f*MU0/solution.case.conductivity_s_per_m)*wall/2
            rz=solution.space.mesh.points[solution.space.mesh.triangles].mean(axis=1)
            h=np.sqrt(c2)/rz[:,0]*np.cos(np.pi*rz[:,1]/length)
            er=-np.sqrt(c2)/(C0*EPS0*rz[:,0])*np.sin(np.pi*rz[:,1]/length)
            fields=solution.fields_at(rz);sign=np.sign(h@fields['Hphi_real_A_per_m'])
            error=np.array([abs(rf['frequency_hz']/f-1),
                np.linalg.norm(sign*fields['Hphi_real_A_per_m']-h)/np.linalg.norm(h),
                np.linalg.norm(sign*fields['Er_quadrature_V_per_m']-er)/np.linalg.norm(er),abs(rf['wall_loss_w']/loss-1)])
            self.assertLess(error[0],1e-4);self.assertLess(max(error[1:]),.01)
            self.assertAlmostEqual(rf['q0'],TAU*rf['frequency_hz']/rf['wall_loss_w'],delta=1e-7)
            self.assertIsNone(rf['vacc_v']);self.assertIsNone(rf['r_over_q_accelerator_ohm'])
            if previous is not None:self.assertTrue(np.all(error<previous),(error,previous))
            previous=error;errors.append(error.tolist())
        print('independent TEM f/H/Er/Pwall errors:',json.dumps(errors),flush=True)
        self.assertEqual(self.snapshot(),self.hashes)

    def test_strict_fixed_levels_and_preflight_without_fem(self):
        raw=self.request.to_dict();self.assertEqual(VacuumHphiConvergence.from_dict(raw).to_dict(),raw)
        for mutation in [lambda d:d.update(extra=1),lambda d:d.update(convergence_version=True),
            lambda d:d['convergence']['projects'][1]['case']['rf'].update(stored_energy_j=2.),
            lambda d:d.update(mode_id='invented'),lambda d:d['convergence'].update(projects=d['convergence']['projects'][:2]),
            lambda d:d['tracking_requests'][0].update(previous_mode_count=2,current_mode_count=2,previous_mode_ids=['a','b']),
            lambda d:d['tracking_requests'][0]['controls'].update(minimum_overlap=.8)]:
            bad=copy.deepcopy(raw);mutation(bad)
            with self.assertRaises(ValueError):VacuumHphiConvergence.from_dict(bad)
        for q in [criteria('r_over_q_accelerator_ohm'),criteria('total_q'),criteria('epk_over_eacc')]:
            with patch('superfish_ng.hphi_rf_design.read_hphi_run',side_effect=AssertionError('FEM replay entered')):
                with self.assertRaises(ValueError):assess_vacuum_hphi_rf_design(self.runs,self.request,q)
        with self.assertRaises(ValueError):assess_vacuum_hphi_rf_design([self.runs[0]]*3,self.request,criteria())
        with self.assertRaises(ValueError):save_vacuum_hphi_rf_design(self.runs,self.request,criteria(),self.runs[0]/'assessment.json')
        self.assertEqual(self.snapshot(),self.hashes)

    def test_guard_sample_budget_numeric_failure_and_inherited_id_cannot_win(self):
        pairs=[replace(q,controls=replace(q.controls,relative_cluster_gap=.9)) for q in self.request.tracking_requests]
        guard=assess_vacuum_hphi_rf_design(self.runs,replace(self.request,tracking_requests=pairs),criteria())
        self.assertEqual(guard['status'],'UNVERIFIED');self.assertIsNone(guard['objective']['eligible_value'])
        self.assertFalse(guard['assessment']['individual_ids_complete'])
        budget=assess_vacuum_hphi_rf_design(self.runs,replace(self.request,max_sample_points=1),criteria())
        self.assertEqual(budget['status'],'UNVERIFIED');self.assertIsNone(budget['objective']['eligible_value'])
        convergence=replace(self.request.convergence,thresholds=replace(self.request.convergence.thresholds,frequency_relative=1e-14))
        tight=assess_vacuum_hphi_rf_design(self.runs,replace(self.request,convergence=convergence),criteria())
        self.assertEqual(tight['refinement_status'],'UNVERIFIED');self.assertIsNone(tight['objective']['eligible_value'])
        self.assertFalse(tight['assessment']['checks']['frequency_relative']['passed'])
        self.assertEqual(tight['constraints'][0]['status'],'MET')
        self.assertEqual(self.snapshot(),self.hashes)

    def test_phase_reversal_preserves_original_field_and_all_rf_gates(self):
        original=compare_vacuum_hphi_convergence(self.request,self.solutions)
        flipped=list(self.solutions);flipped[1]=replace(flipped[1],coefficients=-flipped[1].coefficients)
        result=compare_vacuum_hphi_convergence(self.request,flipped)
        self.assertEqual(result['status'],'PASS')
        for a,b in zip(original['comparisons'],result['comparisons']):
            self.assertEqual(a['changes'],b['changes'])
            self.assertEqual(a['previous_phase_multiplier'],-b['previous_phase_multiplier'])
        self.assertEqual(self.snapshot(),self.hashes)

    def test_replay_move_forged_types_and_late_source_change_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'original';root.mkdir();runs=[]
            for index,source in enumerate(self.runs):
                target=root/str(index);shutil.copytree(source,target);runs.append(target)
            path=root/'assessment.json';report=save_vacuum_hphi_rf_design(runs,self.request,criteria(),path)
            moved=Path(temporary)/'moved';shutil.move(root,moved);path=moved/'assessment.json'
            self.assertEqual(report,read_vacuum_hphi_rf_design(path))
            for mutation in [lambda d:d['objective'].update(eligible_value=1.),
                lambda d:d['assessment']['checks']['frequency_relative'].update(passed=False),
                lambda d:d['assessment']['selected_rf'][0].update(stored_energy_j=True)]:
                bad=copy.deepcopy(report);mutation(bad);path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):read_vacuum_hphi_rf_design(path)
            path.write_text(json.dumps(report));(moved/'1/results.json').write_text('{}')
            with self.assertRaises(ValueError):read_vacuum_hphi_rf_design(path)
        from superfish_ng.hphi_rf_design import _snapshot
        calls=0
        def changed(directory):
            nonlocal calls
            result=_snapshot(directory);calls+=1
            if calls>3:result['results.json']='changed'
            return result
        with patch('superfish_ng.hphi_rf_design._snapshot',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed during full assessment'):
                assess_vacuum_hphi_rf_design(self.runs,self.request,criteria())
        self.assertEqual(self.snapshot(),self.hashes)


class VacuumHphiRFDomainTests(unittest.TestCase):
    def test_general_positive_radius_holes_retain_every_native_wall(self):
        projects=[HphiProject(HphiMeshCase(fixture(n,1,False,n==2),element_order=2,quadrature_order=12,modes=2)) for n in (1,2,4)]
        request=declaration(projects);solutions=[solve_hphi(p.case) for p in projects]
        result=compare_vacuum_hphi_convergence(request,solutions)
        self.assertTrue(result['individual_ids_complete'],result)
        self.assertEqual(len(result['selected_rf']),3)
        for solution,rf,walls,components in zip(solutions,result['selected_rf'],result['wall_loss_w_by_segment'],result['wall_loss_w_by_component']):
            self.assertEqual(rf,hphi_result(solution)['modes'][0])
            self.assertEqual(len(walls),8);self.assertEqual(len(components),2)
            self.assertAlmostEqual(sum(walls),rf['wall_loss_w'],delta=1e-9)
            self.assertAlmostEqual(sum(components),rf['wall_loss_w'],delta=1e-9)
        self.assertEqual(len([k for k in result['checks'] if k.startswith('wall_segment/')]),8)
        # The sharp-corner problem may remain numerically unverified; no tolerance is weakened.
        print('general hole status/gates:',result['status'],json.dumps(result['checks']),flush=True)

    def test_axis_pillbox_independent_bessel_rf_and_explicit_rq(self):
        from scipy.special import jn_zeros,j0,j1
        from scripts.axis_hphi_reference import rectangular_axis_holes
        mesh=AxisConnectedMesh(**rectangular_axis_holes(4,0));projects=[]
        for i in range(3):
            projects.append(HphiProject(AxisHphiCase(mesh,modes=2,acceleration=AxisAccelerationPath(.0,.06,.8,.01))))
            if i<2:mesh=_refine_mesh(mesh)
        request=declaration(projects);solutions=[solve_hphi(p.case) for p in projects]
        result=compare_vacuum_hphi_convergence(request,solutions)
        self.assertEqual(result['status'],'PASS',result)
        R,L=.1,.06;root=jn_zeros(0,1)[0];omega=C0*root/R;f=omega/TAU
        # TM010, peak H=A*J1(kr), U=mu0*pi*A^2*L*R^2*J1(root)^2/2.
        amplitude=np.sqrt(2/(MU0*np.pi*L*R*R*j1(root)**2))
        h2=TAU*amplitude**2*j1(root)**2*(R*L+R*R)
        loss=np.sqrt(np.pi*f*MU0/5.8e7)*h2/2
        wave=omega/(C0*.8);line=L*np.exp(1j*wave*(L/2-.01))*np.sinc(wave*L/(2*np.pi))
        voltage=-1j*amplitude*(root/R)/(omega*EPS0)*line;rq=abs(voltage)**2/omega
        previous=None;errors=[]
        for solution,rf in zip(solutions,result['selected_rf']):
            rz=solution.case.mesh.points_rz_m[solution.case.mesh.triangles].mean(axis=1)
            h=amplitude*j1(root/R*rz[:,0]);ez=-amplitude*(root/R)/(omega*EPS0)*j0(root/R*rz[:,0])
            fields=solution.fields_at(rz);sign=np.sign(h@fields['Hphi_real_A_per_m'])
            error=np.array([abs(rf['frequency_hz']/f-1),np.linalg.norm(sign*fields['Hphi_real_A_per_m']-h)/np.linalg.norm(h),
                np.linalg.norm(sign*fields['Ez_quadrature_V_per_m']-ez)/np.linalg.norm(ez),abs(rf['wall_loss_w']/loss-1),abs(rf['r_over_q_accelerator_ohm']/rq-1)])
            self.assertLess(error[0],1e-4);self.assertLess(max(error[1:]),.01)
            self.assertAlmostEqual(rf['r_over_q_accelerator_ohm']/rf['r_over_q_circuit_ohm'],2.,delta=1e-12)
            if previous is not None:self.assertTrue(np.all(error<previous),(error,previous))
            previous=error;errors.append(error.tolist())
        self.assertIn('axis_voltage_relative',result['checks']);self.assertIn('rf/r_over_q_circuit_ohm',result['checks'])
        self.assertEqual(result['wall_loss_w_by_segment'][-1][-1],0.)
        print('independent pillbox f/H/Ez/Pwall/RQ errors:',json.dumps(errors),flush=True)

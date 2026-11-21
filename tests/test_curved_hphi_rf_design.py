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
from superfish_ng.curved_hphi import solve_curved_hphi
from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain
from superfish_ng.curved_hphi_tracking import CurvedHphiTrackingRequest
from superfish_ng.curved_hphi_rf_convergence import CurvedHphiRFConvergence, compare_curved_hphi_rf_convergence
from superfish_ng.hphi_native import save_hphi_run, hphi_result
from superfish_ng.rf_optimization import (assess_curved_hphi_rf_design,
    save_curved_hphi_rf_design, read_curved_hphi_rf_design)
from test_curved_hphi_convergence import coax_request, request as curved_request
from test_curved_hphi_comparison import charts
from test_curved_hphi_field_overlap import case
from test_hphi_rf_design import criteria


def declaration(convergence,comparison_geometries,comparison_cells):
    domain=CurvedHphiComparisonDomain(convergence.reference_geometry,convergence.reference_geometry,'same_vacuum')
    pairs=[CurvedHphiTrackingRequest(domain,comparison_geometries[i],comparison_geometries[i+1],
        previous_cells=convergence.native_cells[i],current_cells=convergence.native_cells[i+1],
        previous_comparison_cells=comparison_cells[i],current_comparison_cells=comparison_cells[i+1],
        previous_mode_count=1,current_mode_count=1,previous_mode_ids=('mode-1',)) for i in range(2)]
    return CurvedHphiRFConvergence(convergence,pairs)


def sequence():
    original=coax_request(.125,levels=(4,8,16))
    comparison=coax_request(.125,levels=(8,16,32))
    return declaration(original,[p.case.geometry for p in comparison.projects],comparison.native_cells)


class CurvedHphiRFDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.root=Path(cls.temporary.name)
        cls.request=sequence();cls.solutions=[];cls.runs=[]
        for index,project in enumerate(cls.request.convergence.projects):
            solution=solve_curved_hphi(project.case);run=cls.root/str(index)
            save_hphi_run(project.case,solution,run);cls.solutions.append(solution);cls.runs.append(run)
        cls.hashes=cls.snapshot()

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    @classmethod
    def snapshot(cls):
        return [{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()} for run in cls.runs]

    def test_actual_p2_tem_frequency_original_fields_wall_loss_and_finite_guard(self):
        report=assess_curved_hphi_rf_design(self.runs,self.request,criteria())
        self.assertEqual(report['status'],'CRITERIA_MET',report['assessment'])
        assessment=report['assessment'];self.assertTrue(assessment['individual_ids_complete'])
        self.assertEqual(assessment['mode_ranks'],[1,1,1])
        self.assertTrue(all(p['tracking']['individual_ids_complete'] for p in assessment['comparisons']))
        self.assertEqual(report['objective']['eligible_value'],min(rf['q0'] for rf in assessment['selected_rf']))
        self.assertIsNone(report['physical_error_bound']);self.assertFalse(report['geometry_approximation_assessed'])
        a,b,length=.0625,.125,.125;f=C0/(2*length);c2=2/(MU0*np.pi*length*np.log(b/a))
        wall=np.pi*c2*length*(1/a+1/b)+4*np.pi*c2*np.log(b/a)
        loss=np.sqrt(np.pi*f*MU0/5.8e7)*wall/2;errors=[];previous=None
        for solution,rf,segments,components in zip(self.solutions,assessment['selected_rf'],assessment['wall_loss_w_by_segment'],assessment['wall_loss_w_by_component']):
            rz=solution.case.geometry.points_rz_m[solution.case.geometry.cell_nodes[:,:3]].mean(axis=1)
            h=np.sqrt(c2)/rz[:,0]*np.cos(np.pi*rz[:,1]/length)
            er=-np.sqrt(c2)/(C0*EPS0*rz[:,0])*np.sin(np.pi*rz[:,1]/length)
            fields=solution.fields_at(rz);sign=np.sign(h@fields['Hphi_real_A_per_m'])
            error=np.array([abs(rf['frequency_hz']/f-1),np.linalg.norm(sign*fields['Hphi_real_A_per_m']-h)/np.linalg.norm(h),
                np.linalg.norm(sign*fields['Er_quadrature_V_per_m']-er)/np.linalg.norm(er),abs(rf['wall_loss_w']/loss-1)])
            if previous is not None:self.assertTrue(np.all(error<previous),(error,previous))
            previous=error;errors.append(error.tolist())
            self.assertEqual(len(segments),4);self.assertEqual(len(components),1)
            self.assertAlmostEqual(sum(segments),rf['wall_loss_w'],delta=1e-9)
            self.assertAlmostEqual(sum(components),rf['wall_loss_w'],delta=1e-9)
            self.assertAlmostEqual(rf['q0'],TAU*rf['frequency_hz']/rf['wall_loss_w'],delta=1e-7)
            self.assertIsNone(rf['vacc_v']);self.assertIsNone(rf['r_over_q_accelerator_ohm'])
        self.assertLess(previous[0],3e-4);self.assertLess(max(previous[1:3]),.01);self.assertLess(previous[3],.001)
        print('independent quadratic-space TEM f/H/Er/Pwall errors:',json.dumps(errors),flush=True)
        self.assertEqual(self.snapshot(),self.hashes)

    def test_strict_complete_reference_native_charts_and_capability_preflight(self):
        raw=self.request.to_dict();self.assertEqual(CurvedHphiRFConvergence.from_dict(raw).to_dict(),raw)
        for mutation in [lambda d:d.update(extra=1),lambda d:d.update(convergence_version=True),
            lambda d:d['convergence']['projects'][1]['case']['rf'].update(stored_energy_j=2.),
            lambda d:d.update(mode_id='invented'),lambda d:d['convergence'].update(projects=d['convergence']['projects'][:2]),
            lambda d:d['tracking_requests'][0].update(previous_mode_count=3,current_mode_count=3,previous_mode_ids=['a','b','c']),
            lambda d:d['tracking_requests'][0]['controls'].update(minimum_overlap=.8),
            lambda d:d['tracking_requests'][0].update(previous_cells=None),
            lambda d:d['tracking_requests'][0]['domain'].update(mapping='declared_quadratic')]:
            bad=copy.deepcopy(raw);mutation(bad)
            with self.assertRaises(ValueError):CurvedHphiRFConvergence.from_dict(bad)
        for q in [criteria('r_over_q_accelerator_ohm'),criteria('total_q'),criteria('epk_over_eacc')]:
            with patch('superfish_ng.hphi_rf_design.read_hphi_run',side_effect=AssertionError('FEM replay entered')):
                with self.assertRaises(ValueError):assess_curved_hphi_rf_design(self.runs,self.request,q)
        with self.assertRaises(ValueError):assess_curved_hphi_rf_design([self.runs[0]]*3,self.request,criteria())
        with self.assertRaises(ValueError):save_curved_hphi_rf_design(self.runs,self.request,criteria(),self.runs[0]/'assessment.json')
        self.assertEqual(self.snapshot(),self.hashes)

    def test_guard_budget_and_numeric_failure_cannot_adopt_locally_met_criteria(self):
        pairs=[replace(q,controls=replace(q.controls,relative_cluster_gap=.9)) for q in self.request.tracking_requests]
        guard=assess_curved_hphi_rf_design(self.runs,replace(self.request,tracking_requests=pairs),criteria())
        self.assertEqual(guard['status'],'UNVERIFIED');self.assertIsNone(guard['objective']['eligible_value'])
        self.assertFalse(guard['assessment']['individual_ids_complete'])
        budget=[replace(q,max_sample_points=1) for q in self.request.tracking_requests]
        limited=assess_curved_hphi_rf_design(self.runs,replace(self.request,tracking_requests=budget),criteria())
        self.assertEqual(limited['status'],'UNVERIFIED');self.assertIsNone(limited['objective']['eligible_value'])
        convergence=replace(self.request.convergence,thresholds=replace(self.request.convergence.thresholds,frequency_relative=1e-14))
        tight=assess_curved_hphi_rf_design(self.runs,replace(self.request,convergence=convergence),criteria())
        self.assertEqual(tight['refinement_status'],'UNVERIFIED');self.assertIsNone(tight['objective']['eligible_value'])
        self.assertFalse(tight['assessment']['checks']['frequency_relative']['passed'])
        self.assertEqual(tight['constraints'][0]['status'],'MET')
        self.assertEqual(self.snapshot(),self.hashes)

    def test_phase_reversal_preserves_original_p2_field_and_rf_gates(self):
        original=compare_curved_hphi_rf_convergence(self.request,self.solutions)
        flipped=list(self.solutions);flipped[1]=replace(flipped[1],coefficients=-flipped[1].coefficients)
        result=compare_curved_hphi_rf_convergence(self.request,flipped)
        self.assertEqual(result['status'],'PASS')
        for a,b in zip(original['comparisons'],result['comparisons']):
            self.assertEqual(a['changes'],b['changes']);self.assertEqual(a['previous_phase_multiplier'],-b['previous_phase_multiplier'])
        self.assertEqual(self.snapshot(),self.hashes)

    def test_replay_move_type_forgery_and_late_native_change_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'original';root.mkdir();runs=[]
            for index,source in enumerate(self.runs):
                target=root/str(index);shutil.copytree(source,target);runs.append(target)
            path=root/'assessment.json';report=save_curved_hphi_rf_design(runs,self.request,criteria(),path)
            moved=Path(temporary)/'moved';shutil.move(root,moved);path=moved/'assessment.json'
            self.assertEqual(report,read_curved_hphi_rf_design(path))
            for mutation in [lambda d:d['objective'].update(eligible_value=1.),
                lambda d:d['assessment']['checks']['frequency_relative'].update(passed=False),
                lambda d:d['assessment']['selected_rf'][0].update(stored_energy_j=True)]:
                bad=copy.deepcopy(report);mutation(bad);path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):read_curved_hphi_rf_design(path)
            path.write_text(json.dumps(report));(moved/'1/results.json').write_text('{}')
            with self.assertRaises(ValueError):read_curved_hphi_rf_design(path)
        from superfish_ng.hphi_rf_design import _snapshot
        calls=0
        def changed(directory):
            nonlocal calls
            result=_snapshot(directory);calls+=1
            if calls>3:result['results.json']='changed'
            return result
        with patch('superfish_ng.hphi_rf_design._snapshot',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed during full assessment'):
                assess_curved_hphi_rf_design(self.runs,self.request,criteria())
        self.assertEqual(self.snapshot(),self.hashes)


class CurvedHphiRFDomainTests(unittest.TestCase):
    def test_genuinely_curved_axis_hole_native_charts_all_walls_and_rq(self):
        convergence=curved_request(True,holes=1)
        comparisons=[case(True,n=n,holes=1).geometry for n in (2,4,8)]
        q=declaration(convergence,comparisons,[charts(convergence.reference_geometry,g) for g in comparisons])
        solutions=[solve_curved_hphi(p.case) for p in convergence.projects]
        result=compare_curved_hphi_rf_convergence(q,solutions)
        self.assertTrue(result['individual_ids_complete'],result)
        reference=convergence.reference_geometry
        self.assertTrue(np.any(reference.edge_midpoints_rz_m!=reference.base_mesh.points_rz_m[reference.edge_vertices].mean(axis=1)))
        for solution,rf,walls,components in zip(solutions,result['selected_rf'],result['wall_loss_w_by_segment'],result['wall_loss_w_by_component']):
            self.assertEqual(rf,hphi_result(solution)['modes'][0])
            self.assertEqual(len(walls),len(reference.base_mesh.surface_area_m2_by_segment));self.assertEqual(len(components),2)
            self.assertAlmostEqual(sum(walls),rf['wall_loss_w'],delta=1e-8)
            self.assertAlmostEqual(sum(components),rf['wall_loss_w'],delta=1e-8)
            self.assertAlmostEqual(rf['r_over_q_accelerator_ohm']/rf['r_over_q_circuit_ohm'],2.,delta=1e-12)
            self.assertAlmostEqual(solution.case.geometry.volume_m3,reference.volume_m3,delta=1e-14)
        self.assertIn('axis_voltage_relative',result['checks']);self.assertIn('rf/r_over_q_circuit_ohm',result['checks'])
        print('true curved axis hole status/gates:',result['status'],json.dumps(result['checks']),flush=True)
        flipped=list(solutions);flipped[1]=replace(flipped[1],coefficients=-flipped[1].coefficients)
        changed=compare_curved_hphi_rf_convergence(q,flipped)
        for a,b in zip(result['comparisons'],changed['comparisons']):
            self.assertEqual(a['changes'],b['changes']);self.assertEqual(a['previous_phase_multiplier'],-b['previous_phase_multiplier'])
        # The full curved domain is retained even if this coarse sequence misses RF/field targets.

    def test_genuinely_curved_positive_hole_fixed_energy_uniform_scale_laws(self):
        convergence=curved_request(False,holes=1)
        comparisons=[case(False,n=n,holes=1).geometry for n in (2,4,8)]
        q=declaration(convergence,comparisons,[charts(convergence.reference_geometry,g) for g in comparisons])
        solutions=[solve_curved_hphi(p.case) for p in convergence.projects]
        result=compare_curved_hphi_rf_convergence(q,solutions)
        self.assertTrue(result['individual_ids_complete'],result)
        self.assertEqual(len(result['selected_rf']),3)
        self.assertTrue(all(rf['vacc_v'] is None for rf in result['selected_rf']))
        for walls,components in zip(result['wall_loss_w_by_segment'],result['wall_loss_w_by_component']):
            self.assertEqual(len(components),2);self.assertAlmostEqual(sum(walls),sum(components),delta=1e-8)
        # A physical scaling invariant on the genuine whole curved domain,
        # independently scaled coordinates including every midpoint and hole.
        original=solutions[0];raw=original.case.geometry.to_dict()
        for key in ('points_rz_m','outer_rz_m'):raw['base_mesh'][key]=(2*np.asarray(raw['base_mesh'][key])).tolist()
        raw['base_mesh']['holes_rz_m']=[(2*np.asarray(h)).tolist() for h in raw['base_mesh']['holes_rz_m']]
        raw['edge_midpoints_rz_m']=(2*np.asarray(raw['edge_midpoints_rz_m'])).tolist()
        from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
        scaled=solve_curved_hphi(replace(original.case,geometry=CurvedMeridionalGeometry.from_dict(raw)))
        a,b=(hphi_result(s)['modes'][0] for s in (original,scaled))
        for name,factor in [('frequency_hz',.5),('geometry_factor_ohm',1.),('q0',np.sqrt(2)),('wall_loss_w',1/(2*np.sqrt(2)))]:
            self.assertAlmostEqual(b[name]/a[name],factor,delta=1e-9)
        cells=np.arange(len(original.case.geometry.cell_nodes));bary=np.full((len(cells),3),1/3)
        x,y=[s.fields_in_cells(cells,bary) for s in (original,scaled)];sign=np.sign(x['Hphi_real_A_per_m']@y['Hphi_real_A_per_m'])
        for name in ('Er_quadrature_V_per_m','Ez_quadrature_V_per_m','Hphi_real_A_per_m'):
            np.testing.assert_allclose(sign*y[name],x[name]/(2*np.sqrt(2)),rtol=1e-8,atol=1e-8)
        print('true curved positive hole status/gates:',result['status'],json.dumps(result['checks']),flush=True)

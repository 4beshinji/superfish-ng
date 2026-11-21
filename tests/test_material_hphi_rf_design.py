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
from superfish_ng.hphi_project import HphiProject
from superfish_ng.material_hphi import MaterialHphiCase, solve_material_hphi
from superfish_ng.material_hphi_saved import save_material_hphi_run
from superfish_ng.material_hphi_tracking import MaterialHphiTrackingRequest
from superfish_ng.material_hphi_comparison import MaterialHphiComparison
from superfish_ng.material_hphi_convergence import MaterialHphiConvergence, compare_material_hphi_convergence
from superfish_ng.hphi_rf_design import _evaluate_hphi_envelopes
from superfish_ng.rf_optimization import (assess_material_hphi_rf_design,
    save_material_hphi_rf_design, read_material_hphi_rf_design)
from scripts.material_hphi_reference import layered_partition, layered_reference
from test_hphi_rf_design import criteria


def declaration(a,b):
    return MaterialHphiComparison(a,b,'same_domain',
        [dict(previous_id=m.id,current_id=m.id) for m in a.materials],
        [dict(previous_id=r.id,current_id=r.id) for r in a.regions])


def sequence():
    partitions=[layered_partition(nr=2**i,nz=12*2**i) for i in range(4)]
    projects=[HphiProject(MaterialHphiCase(p,modes=3)) for p in partitions[:3]]
    pairs=[MaterialHphiTrackingRequest(declaration(partitions[i],partitions[i+1]),
        declaration(partitions[i],partitions[i+1]),declaration(partitions[i+1],partitions[i+2])) for i in range(2)]
    return MaterialHphiConvergence(projects,pairs)


class MaterialHphiRFDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.root=Path(cls.temporary.name)
        cls.request=sequence();cls.solutions=[];cls.runs=[]
        for index,project in enumerate(cls.request.projects):
            solution=solve_material_hphi(project.case);run=cls.root/str(index)
            save_material_hphi_run(project.case,solution,run);cls.solutions.append(solution);cls.runs.append(run)
        cls.hashes=cls.snapshot()

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    @classmethod
    def snapshot(cls):
        return [{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()} for run in cls.runs]

    def test_actual_three_levels_separate_physical_invariants_and_all_region_wall_gates(self):
        report=assess_material_hphi_rf_design(self.runs,self.request,criteria())
        self.assertEqual(report['status'],'CRITERIA_MET',report['assessment']['checks'])
        assessment=report['assessment'];self.assertEqual(assessment['mode_ranks'],[1,1,1])
        self.assertTrue(assessment['individual_ids_complete'])
        self.assertTrue(all(c['tracking']['individual_ids_complete'] for c in assessment['comparisons']))
        self.assertTrue(any(k.startswith('region/') for k in assessment['checks']))
        self.assertTrue(any(k.startswith('wall_h2_integral_a2_by_component/') for k in assessment['checks']))
        self.assertTrue(any(k.startswith('wall_h2_integral_a2_by_segment/') for k in assessment['checks']))
        self.assertEqual(report['objective']['eligible_value'],min(rf['q0'] for rf in assessment['selected_rf']))
        self.assertIsNone(report['physical_error_bound'])
        expected,field=layered_reference(1);previous=None
        for solution,rf in zip(self.solutions,assessment['selected_rf']):
            centers=solution.case.partition.mesh.points_rz_m[solution.case.partition.mesh.triangles].mean(axis=1)
            h,er,ez=field(centers);actual=solution.fields_at(centers);sign=np.sign(h@actual['Hphi_real_A_per_m'])
            errors=np.array([abs(rf['frequency_hz']/expected['frequency_hz']-1),
                np.linalg.norm(sign*actual['Hphi_real_A_per_m']-h)/np.linalg.norm(h),
                np.linalg.norm(sign*actual['Er_quadrature_V_per_m']-er)/np.linalg.norm(er),
                abs(rf['wall_loss_w']/expected['wall_loss_w']-1)])
            self.assertLess(errors[0],1e-4);self.assertLess(max(errors[1:]),.01)
            if previous is not None:self.assertTrue(np.all(errors<previous),(errors,previous))
            previous=errors
        self.assertEqual(self.snapshot(),self.hashes)

    def test_strict_original_case_partition_guard_and_preflight_before_reconstruction(self):
        raw=self.request.to_dict();self.assertEqual(MaterialHphiConvergence.from_dict(raw).to_dict(),raw)
        for mutation in [lambda d:d.update(extra=1),lambda d:d.update(convergence_version=True),
            lambda d:d['projects'][1]['case']['rf'].update(stored_energy_j=2.),
            lambda d:d['projects'][1]['case']['partition']['materials'][0].update(epsilon_r=4.),
            lambda d:d.update(mode_id='invented'),lambda d:d.update(projects=d['projects'][:2]),
            lambda d:d['tracking_requests'][0].update(previous_mode_count=3,current_mode_count=3,
                previous_mode_ids=['a','b','c']),
            lambda d:d['tracking_requests'][0]['controls'].update(minimum_overlap=.8)]:
            bad=copy.deepcopy(raw);mutation(bad)
            with self.assertRaises(ValueError):MaterialHphiConvergence.from_dict(bad)
        for q in [criteria('r_over_q_accelerator_ohm'),criteria('total_q'),criteria('epk_over_eacc')]:
            with patch('superfish_ng.hphi_rf_design.read_hphi_run',side_effect=AssertionError('FEM replay entered')):
                with self.assertRaises(ValueError):assess_material_hphi_rf_design(self.runs,self.request,q)
        with self.assertRaises(ValueError):assess_material_hphi_rf_design([self.runs[0]]*3,self.request,criteria())
        with self.assertRaises(ValueError):replace(self.request,projects=[self.request.projects[0]]*3)
        self.assertEqual(self.snapshot(),self.hashes)

    def test_finite_guard_budget_tight_numeric_gate_and_id_replacement_never_adopt(self):
        pairs=[replace(q,controls=replace(q.controls,relative_cluster_gap=.9)) for q in self.request.tracking_requests]
        guard=assess_material_hphi_rf_design(self.runs,replace(self.request,tracking_requests=pairs),criteria())
        self.assertEqual(guard['status'],'UNVERIFIED');self.assertIsNone(guard['objective']['eligible_value'])
        self.assertFalse(guard['assessment']['individual_ids_complete'])
        budget=[replace(q,max_sample_points=1) for q in self.request.tracking_requests]
        limited=assess_material_hphi_rf_design(self.runs,replace(self.request,tracking_requests=budget),criteria())
        self.assertEqual(limited['status'],'UNVERIFIED');self.assertIsNone(limited['objective']['eligible_value'])
        tight=assess_material_hphi_rf_design(self.runs,replace(self.request,thresholds=replace(self.request.thresholds,frequency_relative=1e-14)),criteria())
        self.assertEqual(tight['refinement_status'],'UNVERIFIED');self.assertIsNone(tight['objective']['eligible_value'])
        self.assertFalse(tight['assessment']['checks']['frequency_relative']['passed'])
        reordered=list(self.request.tracking_requests);reordered[1]=replace(reordered[1],previous_mode_ids=['mode-2','mode-1'])
        with self.assertRaisesRegex(ValueError,'inherited individual IDs'):
            assess_material_hphi_rf_design(self.runs,replace(self.request,tracking_requests=reordered),criteria())
        self.assertEqual(self.snapshot(),self.hashes)

    def test_inclusive_envelope_and_unconverged_local_met_cannot_win(self):
        case=self.request.projects[0].case
        rows=[dict(q0=x,frequency_hz=10.) for x in [2.,3.,4.]]
        q=criteria();q['constraints']=[dict(quantity='q0',lower=2.,upper=4.)]
        report=_evaluate_hphi_envelopes(case,q,'TARGETS_MET',rows)
        self.assertEqual(report['status'],'CRITERIA_MET');self.assertEqual(report['objective']['eligible_value'],2.)
        q['objective']['direction']='minimize'
        self.assertEqual(_evaluate_hphi_envelopes(case,q,'TARGETS_MET',rows)['objective']['eligible_value'],4.)
        local=_evaluate_hphi_envelopes(case,q,'UNVERIFIED',rows)
        self.assertEqual(local['constraints'][0]['status'],'MET');self.assertEqual(local['status'],'UNVERIFIED')
        self.assertIsNone(local['objective']['eligible_value'])
        for bounds,status in [({'upper':3.},'CONSTRAINTS_UNRESOLVED'),({'upper':1.},'CONSTRAINTS_VIOLATED')]:
            q['constraints']=[dict(quantity='q0',**bounds)]
            report=_evaluate_hphi_envelopes(case,q,'TARGETS_MET',rows)
            self.assertEqual(report['status'],status);self.assertIsNone(report['objective']['eligible_value'])
        self.assertIsNone(_evaluate_hphi_envelopes(case,q,'TARGETS_MET',rows[:2])['objective']['eligible_value'])

    def test_common_phase_reversal_preserves_separate_original_field_differences(self):
        original=compare_material_hphi_convergence(self.request,self.solutions)
        flipped=list(self.solutions);flipped[1]=replace(flipped[1],coefficients=-flipped[1].coefficients)
        result=compare_material_hphi_convergence(self.request,flipped)
        self.assertEqual(result['status'],'PASS')
        for a,b in zip(original['comparisons'],result['comparisons']):
            self.assertEqual(a['changes'],b['changes'])
            self.assertEqual(a['previous_phase_multiplier'],-b['previous_phase_multiplier'])
        self.assertEqual(self.snapshot(),self.hashes)

    def test_saved_assessment_complete_replay_move_and_forged_adoption_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'original';root.mkdir();runs=[]
            for index,source in enumerate(self.runs):
                target=root/str(index);shutil.copytree(source,target);runs.append(target)
            path=root/'assessment.json';report=save_material_hphi_rf_design(runs,self.request,criteria(),path)
            moved=Path(temporary)/'moved';shutil.move(root,moved);path=moved/'assessment.json'
            self.assertEqual(report,read_material_hphi_rf_design(path))
            for mutation in [lambda d:d['objective'].update(eligible_value=1.),
                lambda d:d['assessment']['checks']['frequency_relative'].update(passed=False),
                lambda d:d['assessment']['selected_rf'][0].update(stored_energy_j=True)]:
                bad=copy.deepcopy(report);mutation(bad);path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):read_material_hphi_rf_design(path)
            path.write_text(json.dumps(report));(moved/'1/results.json').write_text('{}')
            with self.assertRaises(ValueError):read_material_hphi_rf_design(path)
        self.assertEqual(self.snapshot(),self.hashes)


class MaterialHphiRFRegionRoleTests(unittest.TestCase):
    def test_fixed_region_volume_roles_cannot_be_swapped_through_aliases(self):
        from superfish_ng.rf_materials import RFMaterialPartition, RFMaterialRegion, LinearRFMaterial
        def partition(nr,nz,swap=False):
            p=layered_partition(nr,nz)
            return RFMaterialPartition(p.mesh,[LinearRFMaterial('vacuum',1.,1.)],
                [RFMaterialRegion(r.id,'vacuum',p.regions[1-i if swap else i].cell_indices)
                 for i,r in enumerate(p.regions)])
        def comparison(a,b,swap=False):
            return MaterialHphiComparison(a,b,'same_domain',
                [dict(previous_id='vacuum',current_id='vacuum')],
                [dict(previous_id=r.id,current_id=b.regions[1-i if swap else i].id)
                 for i,r in enumerate(a.regions)])
        def request(parts,swap=False):
            a,b,c,d=parts
            pairs=[MaterialHphiTrackingRequest(comparison(a,b,swap),comparison(a,b,swap),comparison(b,c)),
                MaterialHphiTrackingRequest(comparison(b,c),comparison(b,c),comparison(c,d))]
            return MaterialHphiConvergence([HphiProject(MaterialHphiCase(p,modes=3)) for p in (a,b,c)],pairs)
        fixed=[partition(2**i,3*2**i) for i in range(4)]
        accepted=request(fixed)
        self.assertEqual(accepted.mode_id,'mode-1')
        # Equal epsilon/mu do not make the declared unequal-volume region roles interchangeable.
        swapped=[fixed[0],*[partition(2**i,3*2**i,True) for i in range(1,4)]]
        self.assertAlmostEqual(swapped[1].region_volume_m3[0]/fixed[0].region_volume_m3[0],.5,delta=1e-14)
        with self.assertRaisesRegex(ValueError,'identity correspondence for fixed material and region IDs'):
            request(swapped,True)

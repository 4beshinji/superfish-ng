# SPDX-License-Identifier: Apache-2.0
"""Design feasibility must not reward unresolved fields or favorable endpoints."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from superfish_ng import Case, solve
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history, extend_mode_history
from superfish_ng.surface_convergence import LIMITS
from superfish_ng.rf_design import (validate_design_criteria, _evaluate_design,
    save_rf_design, read_rf_design, replay_rf_design)


def criteria():
    return dict(schema_version=1, objective=dict(quantity='r_over_q_accelerator_ohm', direction='maximize'),
        constraints=[dict(quantity='frequency_hz', lower=.5, upper=2.),
                     dict(quantity='epk_over_eacc', upper=2.)])


def evidence():
    return dict(status='TARGETS_MET', rows=[dict(intervals={k:[1.,1.] for k in LIMITS}) for _ in range(3)])


class RFDesignTests(unittest.TestCase):
    def test_whole_envelope_inclusive_constraints_and_conservative_objective(self):
        r=criteria();a=evidence()
        a['rows'][0]['intervals']['r_over_q_accelerator_ohm']=[.9,1.1]
        self.assertEqual(_evaluate_design(r,a)['objective']['eligible_value'],.9)
        r['objective']['direction']='minimize'
        self.assertEqual(_evaluate_design(r,a)['objective']['eligible_value'],1.1)
        a['rows'][0]['intervals']['epk_over_eacc']=[1.,2.]
        self.assertEqual(_evaluate_design(r,a)['status'],'CRITERIA_MET')
        a['rows'][0]['intervals']['epk_over_eacc']=[1.,2.1]
        report=_evaluate_design(r,a)
        self.assertEqual(report['status'],'CONSTRAINTS_UNRESOLVED')
        self.assertIsNone(report['objective']['eligible_value'])
        for row in a['rows']:row['intervals']['epk_over_eacc']=[2.1,2.2]
        self.assertEqual(_evaluate_design(r,a)['status'],'CONSTRAINTS_VIOLATED')

    def test_unverified_or_missing_evidence_never_has_a_favorable_value(self):
        for status in ('UNVERIFIED','NOT_CONVERGED','SINGULAR_GEOMETRY','UNVERIFIED_GEOMETRY'):
            a=evidence();a['status']=status
            report=_evaluate_design(criteria(),a)
            self.assertEqual(report['status'],'UNVERIFIED')
            self.assertIsNone(report['objective']['eligible_value'])
        for interval in (None,[float('nan'),1.],[2.,1.],[-1.,1.]):
            a=evidence();a['rows'][-1]['intervals']['r_over_q_accelerator_ohm']=interval
            self.assertIsNone(_evaluate_design(criteria(),a)['objective']['eligible_value'])
        a=evidence();a['rows'].pop()
        self.assertEqual(_evaluate_design(criteria(),a)['status'],'UNVERIFIED')

    def test_circuit_definition_and_maxwell_scaling_of_criteria(self):
        r=criteria();a=evidence()
        for row in a['rows']:row['intervals']['r_over_q_accelerator_ohm']=[.1,.3]
        r['objective']['quantity']='r_over_q_circuit_ohm'
        r['constraints'].append(dict(quantity='r_over_q_circuit_ohm',lower=.01))
        result=_evaluate_design(r,a)
        lo,hi=result['observed_envelopes']['r_over_q_circuit_ohm']
        self.assertLessEqual(Fraction(lo),Fraction(.1)/2)
        self.assertGreaterEqual(Fraction(hi),Fraction(.3)/2)
        for row in a['rows']:row['intervals']['frequency_hz']=[.5,.5]
        r['constraints'][0].update(lower=.25,upper=1.)
        scaled=_evaluate_design(r,a)
        self.assertEqual(scaled['status'],result['status'])
        self.assertEqual(scaled['objective'],result['objective'])

    def test_strict_criteria_no_units_aliases_duplicate_or_implicit_defaults(self):
        for change in ({'schema_version':True},{'constraints':[]},{'unknown':1},
                       {'objective':dict(quantity='RQ',direction='maximize')},
                       {'objective':dict(quantity=[],direction='minimize')}):
            with self.subTest(change=change),self.assertRaises(ValueError):validate_design_criteria(dict(criteria(),**change))
        for constraint in (dict(quantity='frequency_hz'),dict(quantity=[],lower=1.),
                           dict(quantity='frequency_hz',upper=None),dict(quantity='frequency_hz',upper=True),
                           dict(quantity='frequency_hz',upper=10**400),dict(quantity='frequency_hz',lower=2.,upper=1.),
                           dict(quantity='frequency_hz',upper=-1.),dict(quantity='frequency_hz',upper=1.,unit='MHz')):
            r=criteria();r['constraints']=[constraint]
            with self.subTest(constraint=constraint),self.assertRaises(ValueError):validate_design_criteria(r)
        r=criteria();r['constraints'].append(deepcopy(r['constraints'][0]))
        with self.assertRaises(ValueError):validate_design_criteria(r)

    def test_native_refinement_replay_and_forged_acceptance_rejected(self):
        raw=Case.load('examples/curved_ellipse.json').to_dict()
        raw['mesh']['geometry_order']=2;raw['mesh']['contour_mesh'].update(max_edge_m=.08,min_angle_deg=5.)
        raw['geometry']['chord_tolerance_m']=.008;case=Case.from_dict(raw)
        controls=dict(mapping='curved_same_domain',sample_order=3,minimum_overlap=.98,
            minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        r=criteria();r['constraints'][0]=dict(quantity='frequency_hz',lower=1.)
        r['constraints'][1]['upper']=1e10
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for level in range(3):
                c=replace(case,curved_refinement_levels=level);save_run(c,solve(c),root/str(level))
            history=start_mode_history(build_saved_mode_tracking(dict(schema_version=1,
                previous_run=str(root/'0'),current_run=str(root/'1'),previous_ids=['mode'],controls=controls)))
            history=extend_mode_history(history,dict(current_run=str(root/'2'),controls=controls))
            report=save_rf_design(history,'mode',r,root/'design.json')
            self.assertEqual(read_rf_design(root/'design.json'),report)
            self.assertEqual(report['status'],'UNVERIFIED')
            self.assertIsNone(report['objective']['eligible_value'])
            changed=deepcopy(report);changed['status']='CRITERIA_MET'
            with self.assertRaisesRegex(ValueError,'differs'):replay_rf_design(changed)
            changed=deepcopy(report);changed['assessment']['rows'][0]['intervals']['frequency_hz']=[1.,1.]
            with self.assertRaisesRegex(ValueError,'differs'):replay_rf_design(changed)
            with self.assertRaises(FileExistsError):save_rf_design(history,'mode',r,root/'design.json')

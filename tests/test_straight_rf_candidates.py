# SPDX-License-Identifier: Apache-2.0
"""Independent polygon moments for owned multivariable RF candidates."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.contour import Contour
from superfish_ng.project import Project
from test_straight_tuning_geometry import request as tune_request, boundary


def request(kind='stepped_profile'):
    tune=tune_request(kind)
    law=deepcopy(tune['shape_law'])
    for binding in law['bindings']:
        binding['expression']['args'][1]['variable']=('radial' if binding['coordinate']=='r' else 'axial')
    return dict(schema_version=1,document_type='straight_rf_candidate_request',
        project=tune['project'],shape_law=law,controls=tune['controls'],max_candidates=8,
        variables=[dict(name=name,unit='1',lower=.9,upper=1.1) for name in ('radial','axial')])


class StraightRFCandidateTests(unittest.TestCase):
    def test_independent_anisotropic_moments_and_original_boundary(self):
        from superfish_ng.rf_optimization_geometry import prepare_straight_rf_candidates
        for kind in ('profile','stepped_profile','contour'):
            with self.subTest(kind=kind):
                r=request(kind);original=deepcopy(r);base=boundary(Project.from_dict(r['project']).case)
                result=prepare_straight_rf_candidates(r,[[1.1,.9]])
                candidate=result['candidates'][0]
                self.assertEqual(candidate['status'],'GEOMETRY_VERIFIED')
                trial=Project.from_dict(candidate['project']);polygon=boundary(trial.case)
                expected=Contour(tuple((z*.9,h*1.1) for z,h in base.vertices_zr_m),base.edge_tags)
                self.assertEqual(polygon,expected)
                self.assertAlmostEqual(polygon.area_m2/base.area_m2,1.1*.9)
                self.assertAlmostEqual(polygon.volume_m3/base.volume_m3,1.1**2*.9)
                self.assertEqual(trial.case.model,Project.from_dict(r['project']).case.model)
                self.assertIsNone(candidate['assessment']);self.assertIsNone(candidate['mode_id'])
                self.assertEqual(result['fem_calls_attempted'],0);self.assertEqual(r,original)

    def test_variable_binding_and_attempt_order_resume_replay(self):
        from superfish_ng.rf_optimization_geometry import prepare_straight_rf_candidates as prepare,replay_straight_rf_candidates as replay
        for kind in ('profile','stepped_profile','contour'):
            with self.subTest(kind=kind):
                r=request(kind);values=[[1.,1.],[1.1,.9],[.9,1.1]]
                complete=prepare(r,values);prefix=prepare(r,values[:1]);original=deepcopy(prefix)
                self.assertEqual(prepare(r,values[1:],checkpoint=prefix),complete)
                self.assertEqual(prefix,original);self.assertEqual(replay(json.loads(json.dumps(complete))),complete)
                reordered=deepcopy(r);reordered['variables'].reverse()
                reordered['shape_law']['bindings'].reverse();reordered['shape_law']['case_boundary_vertices'].reverse()
                other=prepare(reordered,[list(reversed(v)) for v in reversed(values)])
                for a,b in zip(complete['candidates'],reversed(other['candidates'])):
                    self.assertEqual(a['project'],b['project']);self.assertEqual(a['comparison_mesh'],b['comparison_mesh'])
                for key in ('project','comparison_mesh','assessment','mode_id'):
                    bad=deepcopy(complete);bad['candidates'][0][key]={}
                    with self.subTest(key=key),self.assertRaises(ValueError):replay(bad)
                bad=deepcopy(r);bad['max_candidates']+=1
                with self.assertRaisesRegex(ValueError,'resume request'):prepare(bad,[],checkpoint=prefix)

    def test_dimensioned_cross_terms_match_reparameterized_physical_points(self):
        from superfish_ng.rf_optimization_geometry import straight_candidate_project as candidate
        r=request('profile');unit=deepcopy(r)
        unit['variables'][0].update(name='radius',unit='m',lower=.072,upper=.088)
        reference=r['shape_law']['reference_comparison_mesh']['points']
        for binding in unit['shape_law']['bindings']:
            if binding['coordinate']=='r':
                binding['expression']=dict(op='mul',args=[dict(constant=reference[binding['vertex']][0]/.08,unit='1'),dict(variable='radius')])
        # A genuine radial/axial cross term preserves the zero-valued axis.
        for original,converted in zip(r['shape_law']['bindings'],unit['shape_law']['bindings']):
            if original['coordinate']=='r':
                original['expression']=dict(op='mul',args=[original['expression'],dict(variable='axial')])
                converted['expression']=dict(op='mul',args=[converted['expression'],dict(variable='axial')])
        a,ma=candidate(r,[1.1,.9]);b,mb=candidate(unit,[.088,.9])
        np.testing.assert_allclose(ma['points'],mb['points'],rtol=0,atol=3e-17)
        np.testing.assert_allclose(boundary(a.case).vertices_zr_m,boundary(b.case).vertices_zr_m,rtol=0,atol=3e-17)

    def test_invalid_interior_records_no_objective_and_consumes_budget_before_fem(self):
        from superfish_ng.rf_optimization_geometry import prepare_straight_rf_candidates as prepare
        r=request('contour');binding=r['shape_law']['bindings'][0];old=binding['expression']
        binding['expression']=dict(op='if',args=[dict(op='lt',args=[dict(op='abs',args=[dict(op='sub',args=[dict(variable='radial'),dict(constant=1.,unit='1')])]),dict(constant=.01,unit='1')]),dict(constant=-.001,unit='m'),old])
        with patch('superfish_ng.jobs.execute_project',side_effect=AssertionError('geometry preparation must not solve')):
            result=prepare(r,[[.9,1.],[1.,1.],[1.1,1.]])
        self.assertEqual([c['status'] for c in result['candidates']],['GEOMETRY_VERIFIED','INVALID_GEOMETRY','GEOMETRY_VERIFIED'])
        self.assertEqual(result['candidates_attempted'],3)
        bad=result['candidates'][1];self.assertIsNone(bad['project']);self.assertIsNone(bad['assessment']);self.assertIsNone(bad['mode_id']);self.assertTrue(bad['error'])
        r['max_candidates']=2
        with patch('superfish_ng.straight_rf_candidates.straight_candidate_project',side_effect=AssertionError('budget before construction')):
            with self.assertRaisesRegex(ValueError,'budget'):prepare(r,[[.9,1.],[1.,1.],[1.1,1.]])

    def test_strict_native_law_sector_values_and_old_execution_capability(self):
        from superfish_ng.rf_optimization_geometry import validate_straight_candidate_request as validate,straight_candidate_project as candidate
        r=request();invalid=[]
        for mutate in (
            lambda x:x.update(schema_version=True),lambda x:x.update(criteria={}),
            lambda x:x.update(max_candidates=True),lambda x:x['variables'][0].update(lower=float('nan')),
            lambda x:x['variables'][0].update(unit='mm'),lambda x:x['variables'][0].update(name='axial'),
            lambda x:x['shape_law']['case_boundary_vertices'].pop(),
            lambda x:x['shape_law']['bindings'][0].update(expression=dict(variable='undeclared')),
            lambda x:x['controls'].update(comparison_meshes=[]),
            lambda x:x['project']['case']['model'].update(polarization='TE'),
            lambda x:x['project'].update(mesh_data=x['shape_law']['reference_comparison_mesh']),
        ):
            bad=deepcopy(r);mutate(bad);invalid.append(bad)
        extra=deepcopy(r);extra['variables'].append(dict(name='unused',unit='1',lower=0.,upper=1.));invalid.append(extra)
        for bad in invalid:
            with self.subTest(bad=bad),self.assertRaises(ValueError):validate(bad)
        for values in ([1.],[1.,True],[1.,float('inf')],[1.,1.2],{'radial':1.,'axial':1.}):
            with self.subTest(values=values),self.assertRaises(ValueError):candidate(r,values)
        from test_rf_optimization import request as optimization_request
        from superfish_ng.rf_optimization import validate_optimization_request
        old=optimization_request();old['project']=r['project']
        with self.assertRaisesRegex(ValueError,'curved P2'):validate_optimization_request(old)

    def test_native_step_maxwell_frequency_fields_and_rf_scale(self):
        from superfish_ng.rf_optimization_geometry import straight_candidate_project as candidate
        from superfish_ng import solve
        from superfish_ng.sampling import FieldSampler
        from superfish_ng.rf import quantities
        r=request();r['project']['case']['mesh'].update(nr=14,nz=20)
        r['project']['case']['solver']['modes']=1
        a,ma=candidate(r,[1.,1.]);b,mb=candidate(r,[1.1,1.1]);sa=solve(a.case);sb=solve(b.case)
        np.testing.assert_allclose(np.asarray(mb['points']),np.asarray(ma['points'])*1.1,rtol=0,atol=0)
        points=sa.mesh.points[sa.mesh.triangles].mean(axis=1)
        fa=FieldSampler.from_solution(sa).evaluate(points);fb=FieldSampler.from_solution(sb).evaluate(points*1.1)
        sign=np.sign(fa['Hphi_A_per_m']@fb['Hphi_A_per_m']);errors={}
        for name in ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'):
            error=np.linalg.norm(fb[name]*sign*1.1**1.5-fa[name])/np.linalg.norm(fa[name]);errors[name]=float(error)
            self.assertLess(error,1e-8)
        qa=quantities(a.case,sa);qb=quantities(b.case,sb)
        self.assertAlmostEqual(qb['frequency_hz']/qa['frequency_hz'],1/1.1,places=10)
        self.assertAlmostEqual(qb['q0']/qa['q0'],np.sqrt(1.1),places=9)
        for name in ('geometry_factor_ohm','r_over_q_accelerator_ohm','r_over_q_circuit_ohm'):
            self.assertAlmostEqual(qb[name]/qa[name],1.,places=9)
        self.assertEqual(a.case.model,b.case.model)
        self.assertAlmostEqual(qb['r_over_q_accelerator_ohm'],2*qb['r_over_q_circuit_ohm'],places=9)
        print('candidate actual step Maxwell field relative errors:',json.dumps(errors),flush=True)

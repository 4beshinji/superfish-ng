# SPDX-License-Identifier: Apache-2.0
"""Fixed RF comparison inputs, strict types and pre-solve source ownership."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from superfish_ng import curved_rf_goal_efficiency_plan as plans
from superfish_ng.curved_rf_adaptive_refinement import validate_request as validate_v5
from superfish_ng.curved_adaptive_refinement import validate_request as validate_v4

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = 'examples/curved_rf_goal_efficiency/plan.json'
FIXED = json.loads((ROOT/PLAN_PATH).read_text())


class CurvedRFGoalEfficiencyPlanTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        for target in ('superfish_ng.solver.solve', 'superfish_ng.curved_solution.eigsh',
                       'superfish_ng.curved_rf_adaptive_refinement.solve',
                       'superfish_ng.curved_adaptive_refinement.solve',
                       'superfish_ng.mesh.make_mesh'):
            stack.enter_context(patch(target, side_effect=AssertionError('no solve or remesh in fixed inputs')))

    def copy_inputs(self, root):
        paths = [PLAN_PATH, *(r['path'] for r in FIXED['input_sources']),
                 *(r['request']['path'] for r in FIXED['cases'])]
        for relative in paths:
            p = root/relative
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/relative, p)

    def test_exact_fixed_plan_has_36_fresh_rows_and_no_acceptance(self):
        plan = plans.build_curved_rf_goal_efficiency_plan()
        self.assertEqual(plan, FIXED)
        self.assertEqual(len(plan), 13)
        self.assertEqual(plan['new_fem_solves'], 0)
        self.assertEqual(plan['physical_acceptance_status'], 'NOT_RUN')
        self.assertIsNone(plan['physical_error_bound'])
        self.assertEqual(len({r['id'] for r in plan['executions']}), 36)
        for i, case in enumerate(plan['cases']):
            rows = plan['executions'][6*i:6*i+6]
            self.assertEqual([(r['repetition'], r['method']) for r in rows],
                             [(1,'uniform'),(1,'rf_goal'),(1,'uniform_when_rf_passes'),
                              (2,'uniform_when_rf_passes'),(2,'rf_goal'),(2,'uniform')])
            self.assertTrue(all(r['case_id']==case['id'] and r['status']=='NOT_RUN' for r in rows))
        self.assertEqual(sum(c['max_events']*6 for c in plan['cases']), 336)

    def test_all_36_requests_preserve_case_mesh_ids_and_explicit_policy(self):
        for row in FIXED['executions']:
            with self.subTest(execution=row['id']):
                request = plans.request_for_curved_rf_goal_efficiency_execution(row)
                case = next(c for c in FIXED['cases'] if c['id']==row['case_id'])
                original = json.loads((ROOT/case['request']['path']).read_text())
                expected = deepcopy(original)
                if row['method']=='uniform':
                    expected.pop('surface_refinement_policy')
                    expected['schema_version']=4
                    normalized = validate_v4(request)
                else:
                    expected['surface_refinement_policy']=row['method']
                    normalized = validate_v5(request)
                self.assertEqual(request, expected)
                self.assertEqual(normalized, validate_v5(original))
                self.assertEqual(request['initial_ids'], original['initial_ids'])
                self.assertEqual(request['initial_mesh'], original['initial_mesh'])
                self.assertEqual(normalized.normalization_j, float(case['scale']**2))

    def test_original_si_similarity_and_all_topology_are_preserved(self):
        for family in ('sphere','prolate','rounded-two-lobe'):
            values=[]
            for scale in (1,2):
                row=next(r for r in FIXED['executions'] if r['case_id']==f'{family}-scale-{scale}' and r['method']=='rf_goal')
                values.append(plans.request_for_curved_rf_goal_efficiency_execution(row))
            a,b=values
            np.testing.assert_array_equal(np.array(a['initial_mesh']['points'])*2,b['initial_mesh']['points'])
            for key in set(a['initial_mesh'])-{'points'}:
                self.assertEqual(a['initial_mesh'][key],b['initial_mesh'][key])
            ca,cb=validate_v5(a),validate_v5(b)
            self.assertEqual(cb.acceleration_parameters[0],2*ca.acceleration_parameters[0])
            self.assertEqual(cb.acceleration_parameters[1],tuple(2*v for v in ca.acceleration_parameters[1]))
            self.assertEqual(cb.normalization_j,4*ca.normalization_j)
            self.assertEqual(cb.curved_contour.edge_tags,ca.curved_contour.edge_tags)
            self.assertEqual((ca.modes,ca.element_order,ca.geometry_order,ca.quadrature_order),
                             (cb.modes,cb.element_order,cb.geometry_order,cb.quadrature_order))

    def test_raw_json_rejects_duplicate_nonfinite_huge_and_invalid_inputs(self):
        raw=(ROOT/PLAN_PATH).read_text()
        self.assertEqual(plans.parse_curved_rf_goal_efficiency_plan(raw),FIXED)
        bad = [raw.replace('"schema_version": 1','"schema_version": 1, "schema_version": 1',1),
               raw.replace('"wall_limit_seconds": 3600','"wall_limit_seconds": NaN'),
               raw.replace('"wall_limit_seconds": 3600','"wall_limit_seconds": Infinity'),
               raw.replace('"wall_limit_seconds": 3600','"wall_limit_seconds": 1e999'),
               raw.replace('"wall_limit_seconds": 3600','"wall_limit_seconds": '+('9'*6000)),
               '['*2000+']'*2000,'{',None,raw.encode()]
        for value in bad:
            with self.subTest(kind=type(value).__name__), self.assertRaises(ValueError):
                plans.parse_curved_rf_goal_efficiency_plan(value)
        duplicate=raw.replace('"memory_limit_bytes": 34359738368','"memory_limit_bytes": 34359738368, "memory_limit_bytes": 34359738368')
        self.assertNotEqual(duplicate,raw)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            plans.parse_curved_rf_goal_efficiency_plan(duplicate)

    def test_strict_key_sets_types_limits_and_unknown_policies(self):
        changes=[(['schema_version'],True),(['new_fem_solves'],0.0),(['expected_native_executions'],36.0),
                 (['resources','blas_threads'],True),(['resources','wall_limit_seconds'],float('inf')),
                 (['resources','memory_limit_bytes'],10**1000),(['limits','geometry_factor_ohm'],.05),
                 (['limits','r_over_q_circuit_ohm'],None),(['normalization','energy_j'],'1'),
                 (['cases',0,'scale'],1.0),(['cases',0,'request','bytes'],6830.0),
                 (['cases',0,'id'],''),(['cases',0,'reference_status'],'PASS'),
                 (['executions',0,'method'],'residual_fallback'),(['executions',0,'repetition'],True)]
        for path,value in changes:
            with self.subTest(path=path):
                p=deepcopy(FIXED); node=p
                for key in path[:-1]: node=node[key]
                node[path[-1]]=value
                with patch.object(plans,'validate_v5') as validate:
                    with self.assertRaises(ValueError): plans.validate_curved_rf_goal_efficiency_plan(p)
                    validate.assert_not_called()
        for parent in ((),('cases',0),('cases',0,'request'),('executions',0),('resources',)):
            for operation in ('add','remove'):
                with self.subTest(parent=parent,operation=operation):
                    p=deepcopy(FIXED);node=p
                    for key in parent: node=node[key]
                    if operation=='add':node['silent_fallback']=False
                    else:node.pop(next(iter(node)))
                    with self.assertRaises(ValueError): plans.validate_curved_rf_goal_efficiency_plan(p)

    def test_missing_extra_reordered_duplicate_rows_and_nonlist_are_rejected(self):
        for name in ('cases','executions','input_sources'):
            for operation in ('drop','extra','swap','duplicate','tuple'):
                with self.subTest(name=name,operation=operation):
                    p=deepcopy(FIXED);rows=p[name]
                    if operation=='drop': rows.pop()
                    elif operation=='extra': rows.append(deepcopy(rows[-1]))
                    elif operation=='swap': rows[0],rows[1]=rows[1],rows[0]
                    elif operation=='duplicate': rows[1]=deepcopy(rows[0])
                    else: p[name]=tuple(rows)
                    with self.assertRaises(ValueError): plans.validate_curved_rf_goal_efficiency_plan(p)

    def test_execution_is_whole_fixed_row_not_just_id(self):
        row=FIXED['executions'][0]
        values=[None,row['id'],dict(row,repetition=True),dict(row,status='PASS'),
                dict(row,request={}),dict(row,case_id='prolate-scale-1'),dict(row,id='missing')]
        for value in values:
            with self.subTest(value=value),patch.object(plans,'validate_v5') as validate:
                with self.assertRaises(ValueError): plans.request_for_curved_rf_goal_efficiency_execution(value)
                validate.assert_not_called()

    def test_returned_values_and_caller_inputs_do_not_alias(self):
        source=deepcopy(FIXED)
        a=plans.validate_curved_rf_goal_efficiency_plan(source)
        a['cases'][0]['request']['path']='changed'
        self.assertEqual(source,FIXED)
        self.assertEqual(plans.build_curved_rf_goal_efficiency_plan(),FIXED)
        row=deepcopy(FIXED['executions'][1]); before=deepcopy(row)
        a=plans.request_for_curved_rf_goal_efficiency_execution(row)
        a['initial_mesh']['points'][0][0]=99
        a['case']['rf']['normalization_j']=100
        b=plans.request_for_curved_rf_goal_efficiency_execution(row)
        self.assertNotEqual(a['initial_mesh'],b['initial_mesh'])
        self.assertEqual(row,before)
        self.assertEqual(b['case']['rf']['normalization_j'],1.)

    def test_source_bytes_missing_files_and_rehashed_replacement_are_rejected(self):
        bindings=[{'path':PLAN_PATH},*FIXED['input_sources'],*(c['request'] for c in FIXED['cases'])]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.copy_inputs(root)
            for binding in bindings:
                p=root/binding['path'];original=p.read_bytes()
                for operation in ('change','missing'):
                    with self.subTest(path=binding['path'],operation=operation):
                        if operation=='change':p.write_bytes(original+b' ')
                        else:p.unlink()
                        with patch.object(plans,'validate_v5') as validate:
                            with self.assertRaises(ValueError): plans.build_curved_rf_goal_efficiency_plan(base_directory=root)
                            validate.assert_not_called()
                        p.write_bytes(original)
            p=root/FIXED['cases'][0]['request']['path'];value=json.loads(p.read_text())
            value['initial_mesh']['points'][0][0]=.001
            raw=(json.dumps(value)+'\n').encode();p.write_bytes(raw)
            changed=deepcopy(FIXED)
            changed['cases'][0]['request'].update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
            with self.assertRaises(ValueError): plans.validate_curved_rf_goal_efficiency_plan(changed,base_directory=root)
            (root/PLAN_PATH).write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'fixed.*plan.*(bytes|sha256)'):
                plans.build_curved_rf_goal_efficiency_plan(base_directory=root)

    def test_declared_escape_paths_are_rejected_without_following_them(self):
        for name in ('../missing.json','/tmp/missing.json','examples/../missing.json','',
                     'examples//missing.json','examples\\missing.json'):
            p=deepcopy(FIXED);p['cases'][0]['request']['path']=name
            with self.subTest(name=name),patch.object(plans,'validate_v5') as validate:
                with self.assertRaises(ValueError):plans.validate_curved_rf_goal_efficiency_plan(p)
                validate.assert_not_called()

    def test_symlink_directories_files_and_nonregular_inputs_are_rejected(self):
        for mode in ('file','directory','root','fifo'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'copy';root.mkdir();self.copy_inputs(root)
                target=root/FIXED['cases'][0]['request']['path']
                if mode=='file':
                    target.unlink();target.symlink_to(ROOT/FIXED['cases'][0]['request']['path'])
                elif mode=='directory':
                    directory=target.parent; moved=directory.with_name('moved');directory.rename(moved);directory.symlink_to(moved,target_is_directory=True)
                elif mode=='root':
                    link=Path(temp)/'linked';link.symlink_to(root,target_is_directory=True);root=link
                else:
                    target.unlink();os.mkfifo(target)
                with self.assertRaisesRegex(ValueError,'regular|symlink|directory'):
                    plans.build_curved_rf_goal_efficiency_plan(base_directory=root)

    def test_source_change_during_public_validation_is_not_cached(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.copy_inputs(root)
            target=root/FIXED['input_sources'][0]['path'];original=target.read_bytes()
            calls=0
            def mutate(request):
                nonlocal calls
                calls+=1
                case=validate_v5(request)
                if calls==1:target.write_bytes(original+b' ')
                return case
            with patch.object(plans,'validate_v5',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'bytes|sha256'):
                    plans.build_curved_rf_goal_efficiency_plan(base_directory=root)
            target.write_bytes(original)
            self.assertEqual(plans.build_curved_rf_goal_efficiency_plan(base_directory=root),FIXED)


if __name__=='__main__':
    unittest.main()

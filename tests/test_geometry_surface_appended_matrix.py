# SPDX-License-Identifier: Apache-2.0
"""Explicit later FEM windows must retain original Cases and actual ancestry."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from superfish_ng import Case
from superfish_ng.curved_refinement import refine_curved_space
from superfish_ng.geometry_surface_matrix import build_geometry_surface_matrix, _descriptor
from test_geometry_surface_fields import manufactured_fields

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'docs/n01_geometry_surface_cases.json'


class AppendedGeometryMatrixTests(unittest.TestCase):
    def request(self):
        return dict(schema_version=4,document_type='geometry_surface_matrix_request',
            plan_request=dict(schema_version=1,document_type='geometry_surface_plan_request',
                catalog=str(CATALOG),catalog_sha256=hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
                case_ids=['N01-prolate-new'],reference_directory=str(ROOT)),runs=[[None]*3 for _ in range(3)],
            uniform_fem_levels=[2,3,4],identity_prefix_runs=[None,None],
            native_tracking_resources=dict(sample_budget=16777216,sampling='uniform_parent_p2'))

    def test_declared_window_keeps_original_plan_and_unknowns_without_solving(self):
        request=self.request();descriptor,paths=_descriptor(request,ROOT)
        for row in descriptor['expected_cases']:
            self.assertEqual([Case.from_dict(c).curved_refinement_levels for c in row],[2,3,4])
        for row in descriptor['plan']['cases'][0]['matrix']:
            self.assertEqual([Case.from_dict(p['case']).curved_refinement_levels for p in row],[0,1,2])
        with patch('superfish_ng.solve',side_effect=AssertionError('saved diagnostic cannot solve')):
            report=build_geometry_surface_matrix(request)
        self.assertEqual(report['status'],'UNVERIFIED')
        self.assertEqual(report['uniform_fem_levels'],[2,3,4])
        self.assertEqual(report['identity_prefix']['status'],'UNVERIFIED')
        self.assertEqual(report['new_fem_solves'],0)
        self.assertEqual(report['supplied_native_points'],0)
        self.assertEqual(report['supplied_identity_prefix_points'],0)
        self.assertEqual(report['native_tracking_resources'],request['native_tracking_resources'])

    def test_strict_window_prefix_and_resources_preserve_older_versions(self):
        original=self.request()
        for levels in ([1,3,4],[2,2,3],[True,2,3],[-1,0,1],[6,7,8],[2,3],(2,3,4)):
            bad=deepcopy(original);bad['uniform_fem_levels']=levels
            if isinstance(levels,list) and len(levels)==3 and all(type(i) is int for i in levels) and levels[0]>=0:
                bad['identity_prefix_runs']=[None]*levels[0]
            with self.assertRaises(ValueError):_descriptor(bad,ROOT)
        for prefix in ([None],['same','same']):
            bad=deepcopy(original);bad['identity_prefix_runs']=prefix
            with self.assertRaises(ValueError):_descriptor(bad,ROOT)
        bad=deepcopy(original);bad['runs'][0][0]='same';bad['identity_prefix_runs']=['same',None]
        with self.assertRaises(ValueError):_descriptor(bad,ROOT)
        for budget in (True,0,16777217):
            bad=deepcopy(original);bad['native_tracking_resources']['sample_budget']=budget
            with self.assertRaises(ValueError):_descriptor(bad,ROOT)
        old=deepcopy(original);old['schema_version']=3
        del old['uniform_fem_levels'];del old['identity_prefix_runs']
        with self.assertRaisesRegex(ValueError,'8388608'):_descriptor(old,ROOT)
        old['native_tracking_resources']['sample_budget']=8388608
        descriptor,paths=_descriptor(old,ROOT)
        self.assertEqual(descriptor['uniform_fem_levels'],[0,1,2])

    def family(self):
        base=manufactured_fields();r,z=base.space.geometry.points_rz_m.T
        base=replace(base,case=replace(base.case,modes=2),u=np.column_stack((np.ones(len(r)),z-base.case.length/2)),
            frequencies_hz=np.array([1e9,1.1e9]))
        first=refine_curved_space(base.space)
        child=replace(base,case=replace(base.case,curved_refinement_levels=1),space=first.space,
            u=(first.prolongation@base.u)[:,::-1])
        second=refine_curved_space(child.space)
        grandchild=replace(child,case=replace(child.case,curved_refinement_levels=2),space=second.space,
            u=second.prolongation@child.u)
        return base,child,grandchild

    def test_actual_prefix_fields_carry_rank_exchange_not_original_rank_labels(self):
        from superfish_ng.geometry_surface_matrix import _prefix_identity
        base,child,grandchild=self.family()
        resources=self.request()['native_tracking_resources']
        report=_prefix_identity([base,child],grandchild,['target','guard'],'target',resources,16777216)
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(report['current_ids'],['guard','target'])
        self.assertEqual(len(report['comparisons']),2)
        self.assertEqual(report['comparisons'][0]['current_mode_index'],2)
        self.assertEqual(report['comparisons'][1]['current_mode_index'],2)
        # Prefix field accuracy is recorded separately from Hphi identification.
        self.assertEqual(report['comparisons'][0]['status'],'FAIL')

    def test_missing_or_degenerate_ancestry_keeps_individual_ids_unknown(self):
        from superfish_ng.geometry_surface_matrix import _prefix_identity
        base,child,grandchild=self.family();resources=self.request()['native_tracking_resources']
        for prefix in ([None,child],[base,None]):
            report=_prefix_identity(prefix,grandchild,['target','guard'],'target',resources,16777216)
            self.assertEqual(report['status'],'UNVERIFIED');self.assertIsNone(report['current_ids'])
        degenerate=replace(child,frequencies_hz=np.array([1e9,1e9]))
        report=_prefix_identity([base,degenerate],grandchild,['target','guard'],'target',resources,16777216)
        self.assertEqual(report['status'],'UNVERIFIED');self.assertIsNone(report['current_ids'])

    def test_resource_cap_is_explicit_and_does_not_change_field_limits(self):
        from superfish_ng.geometry_surface_fields import compare_geometry_surface_fields
        base,child,grandchild=self.family();resources=self.request()['native_tracking_resources']
        with self.assertRaisesRegex(ValueError,'8388608'):
            compare_geometry_surface_fields(base,child,['target','guard'],mapping='curved_same_domain',native_resources=resources)
        report=compare_geometry_surface_fields(base,child,['target','guard'],mapping='curved_same_domain',
            native_resources=resources,native_resource_budget_limit=16777216)
        self.assertEqual(report['native_controls']['sample_order'],10)
        self.assertEqual(report['native_controls']['maximum_sample_budget'],16777216)
        self.assertEqual(report['field_gates']['native_axis_relative_l2'],.01)
        with self.assertRaises(ValueError):
            compare_geometry_surface_fields(base,child,['target','guard'],mapping='curved_same_domain',
                native_resource_budget_limit=True,native_resources=resources)

    def test_exclusive_replay_and_cli_keep_the_window_prefix_and_cap(self):
        from superfish_ng.geometry_surface_matrix import save_geometry_surface_matrix,read_geometry_surface_matrix
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'matrix.json';request=self.request()
            report=save_geometry_surface_matrix(request,path)
            self.assertEqual(read_geometry_surface_matrix(path),report)
            with self.assertRaises(FileExistsError):save_geometry_surface_matrix(request,path)
            req=root/'request.json';req.write_text(json.dumps(request))
            process=subprocess.run([sys.executable,'scripts/validate_geometry_surface_convergence.py',
                '--matrix-request',str(req),'--out',str(root/'cli')],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(process.returncode,3,process.stderr)
            self.assertEqual(json.loads((root/'cli/matrix.json').read_text()),report)
            altered=deepcopy(report);altered['request']['native_tracking_resources']['sample_budget']-=1
            path.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError,'replay differs'):read_geometry_surface_matrix(path)

    def test_entire_prefix_case_and_source_are_checked_before_sampling(self):
        request=self.request();request['identity_prefix_runs']=['origin0','origin1']
        wrong=manufactured_fields()
        with (patch('superfish_ng.geometry_surface_matrix._native_snapshot',return_value={}),
              patch('superfish_ng.geometry_surface_matrix.read_solution',return_value=wrong),
              patch('superfish_ng.geometry_surface_matrix._prefix_identity',side_effect=AssertionError('must reject before sampling'))):
            with self.assertRaisesRegex(ValueError,'complete original identity prefix Case'):
                build_geometry_surface_matrix(request)
        descriptor,_=_descriptor(request,ROOT)
        cases=[Case.from_dict(c) for c in descriptor['identity_prefix_cases']]
        originals=[replace(wrong,case=c,source_mesh_data={'different':i}) for i,c in enumerate(cases)]
        with (patch('superfish_ng.geometry_surface_matrix._native_snapshot',return_value={}),
              patch('superfish_ng.geometry_surface_matrix.read_solution',side_effect=originals),
              patch('superfish_ng.geometry_surface_matrix._prefix_identity',side_effect=AssertionError('must reject before sampling'))):
            with self.assertRaisesRegex(ValueError,'exact original source mesh'):build_geometry_surface_matrix(request)


if __name__=='__main__':unittest.main()

# SPDX-License-Identifier: Apache-2.0
"""Explicit mesh schedules, physical boundaries and actual midpoint replay."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.studies import Study,execute_study
from test_curved_harmonic_study import harmonic_study_document,controls
from test_curved_project_remesh import remesh_fixture
from test_curved_harmonic_deformation import space


def remesh_study_document(values=None):
    raw=harmonic_study_document([0.,1.] if values is None else values)
    source,plan,_=remesh_fixture()
    raw.update(study_version=4,kind='curved_remesh_sweep',project=source.to_dict(),
        mesh_schedule=dict(schema_version=1,breakpoints=[.75],plans=[{'kind':'original'},{'kind':'replace','plan':plan}]))
    return raw


class CurvedRemeshStudyTests(unittest.TestCase):
    def test_schedule_uses_actual_values_with_right_hand_cutovers_and_fixed_domain(self):
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        values=[1.,.75,.5,0.,1.];raw=remesh_study_document(values);before=deepcopy(raw)
        study=Study.from_dict(raw);projects=study.projects()
        self.assertEqual(study.to_dict(),raw);self.assertEqual(raw,before)
        self.assertEqual([len(p.mesh_data['triangles']) for p in projects],[28,28,26,26,28])
        self.assertEqual(projects[0].to_dict(),projects[-1].to_dict())
        baseline=boundary_moments(space(projects[3]))
        for x,p in zip(values,projects):
            moment=boundary_moments(space(p));ratio=1+x/8
            self.assertAlmostEqual(moment['signed_area_m2']/baseline['signed_area_m2'],ratio,places=12)
            self.assertAlmostEqual(moment['signed_volume_m3']/baseline['signed_volume_m3'],ratio**2,places=12)
            self.assertTrue(all(s.split_pattern for s in p.case.curved_refinement_steps if s.kind=='marked'))

    def test_comparison_maps_come_from_original_geometry_even_with_other_fem_meshes(self):
        from superfish_ng.study_shape_tracking import pair_controls
        study=Study.from_dict(remesh_study_document());projects=study.projects()
        result=pair_controls(study,controls(),0.,1.,projects=projects)
        a,b=result['comparison_meshes']
        self.assertEqual(len(a['source_mesh']['triangles']),26)
        self.assertEqual(len(b['source_mesh']['triangles']),26)
        self.assertNotEqual(b['source_mesh'],projects[1].mesh_data)
        self.assertEqual(a['curved_refinement_steps'],b['curved_refinement_steps'])
        midpoint=pair_controls(study,controls(),0.,.5)
        self.assertNotEqual(midpoint['comparison_meshes'][1],b)

    def test_real_study_independent_spectra_and_derived_saved_tracking_replay(self):
        from superfish_ng.study_mode_tracking import build_study_mode_tracking,replay_study_mode_tracking
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);study=Study.from_dict(remesh_study_document())
            report=execute_study(study,root/'study')
            self.assertEqual(report['numerical_status'],'UNVERIFIED');self.assertEqual(report['comparisons'],[])
            self.assertEqual(report['mode_tracking'],'not performed; independent spectra')
            self.assertIn('value-based initial mesh schedule',report['geometry_refinement'])
            request=dict(schema_version=1,study_run=str(root/'study'),initial_ids=['A'],step_controls=[controls()])
            tracked=build_study_mode_tracking(request)
            self.assertEqual(tracked['status'],'PASS');self.assertEqual(replay_study_mode_tracking(tracked),tracked)
            self.assertNotIn('comparison_meshes',tracked['request']['step_controls'][0])
            meshes=tracked['history']['steps'][0]['request']['controls']['comparison_meshes']
            self.assertNotEqual(meshes[0]['source_mesh']['points'],meshes[1]['source_mesh']['points'])
            bad=deepcopy(tracked);bad['history']['steps'][0]['request']['controls']['comparison_meshes'][1]['source_mesh']['points'][1][0]+=.001
            with self.assertRaises(ValueError):replay_study_mode_tracking(bad)

    def test_tracked_checkpoint_reuses_points_and_preserves_shape_laws(self):
        from superfish_ng.tracked_study import execute_tracked_study,replay_tracked_study
        request=dict(schema_version=1,study=remesh_study_document(),initial_ids=['A'],step_controls=[controls()])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_tracked_study(request,root/'first',max_new_points=1)
            self.assertEqual(first['status'],'PAUSED')
            final=execute_tracked_study(request,root/'rest',checkpoint=first)
            self.assertEqual(final['status'],'COMPLETE');self.assertEqual(final['point_runs'][0],first['point_runs'][0])
            self.assertEqual(replay_tracked_study(final),final)
            bad=deepcopy(request);bad['study']['mesh_schedule']['breakpoints']=[.25]
            with self.assertRaises(ValueError):execute_tracked_study(bad,root/'bad',checkpoint=first)
            self.assertFalse((root/'bad').exists())

    def test_adaptive_midpoint_is_derived_after_pause_without_reusing_endpoint_mesh(self):
        from superfish_ng.adaptive_study import execute_adaptive_study,replay_adaptive_study
        request=dict(schema_version=1,study=remesh_study_document(),initial_ids=['A'],
            step_controls=[dict(controls(),minimum_overlap=1.)],adaptive=dict(max_depth=1,max_attempts=4,minimum_parameter_step=.001))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_adaptive_study(request,root/'first',max_new_attempts=1)
            self.assertEqual(first['status'],'PAUSED');self.assertEqual(first['attempts'][0]['decision'],'BISECT')
            final=execute_adaptive_study(request,root/'rest',checkpoint=first)
            self.assertEqual(final['status'],'UNVERIFIED');self.assertEqual(final['points'][:2],first['points'])
            self.assertEqual(final['points'][2]['value'],.5);self.assertEqual(final['attempts'][1]['decision'],'STOP')
            endpoints=final['attempts'][0]['correspondence']['request']['controls']['comparison_meshes']
            midpoints=final['attempts'][1]['correspondence']['request']['controls']['comparison_meshes']
            self.assertEqual(endpoints[0],midpoints[0]);self.assertNotEqual(endpoints[1],midpoints[1])
            from superfish_ng.saved import read_solution
            counts=[len(read_solution(Path(p['run'])/'solution').source_mesh_data['triangles']) for p in final['points']]
            self.assertEqual(counts,[26,28,26])
            self.assertTrue(all(len(m['source_mesh']['triangles'])==26 for pair in (endpoints,midpoints) for m in pair))
            self.assertEqual(replay_adaptive_study(final),final)
            bad=deepcopy(final);bad['request']['study']['mesh_schedule']['breakpoints']=[.25]
            with self.assertRaises(ValueError):replay_adaptive_study(bad)

    def test_strict_schedule_versions_and_ownership(self):
        raw=remesh_study_document();plan=raw['mesh_schedule']['plans'][1]
        invalid=[dict(raw,study_version=v) for v in (True,1,2,3,5)]
        invalid += [dict(raw,kind='curved_harmonic_sweep'),dict(raw,mesh_schedule=None),dict(raw,affine_coefficients={})]
        schedules=[{},dict(schema_version=True,breakpoints=[],plans=[plan])]
        for cuts in ([True],[float('nan')],[10**400],[1.,0.],[.75,.75],'0.75'):
            schedules.append(dict(schema_version=1,breakpoints=cuts,plans=[{'kind':'original'},plan]))
        for plans in ([],[plan],[{'kind':'original'},{'kind':'original'}],[{'kind':'auto'},plan],
                      [{'kind':'original','plan':{}},plan],[{'kind':'replace'},plan],[{'kind':'replace','plan':{}},plan]):
            schedules.append(dict(schema_version=1,breakpoints=[.75],plans=plans))
        invalid += [dict(raw,mesh_schedule=value) for value in schedules]
        missing=deepcopy(raw);del missing['mesh_schedule'];invalid.append(missing)
        for bad in invalid:
            with self.subTest(schedule=bad.get('mesh_schedule')),self.assertRaises(ValueError):Study.from_dict(bad)
        study=Study.from_dict(raw);raw['mesh_schedule']['breakpoints'][0]=42
        self.assertEqual(study.mesh_schedule['breakpoints'],[.75])
        exported=study.to_dict();exported['mesh_schedule']['plans'][1]['plan']['source_mesh']['points'][0][0]=42
        self.assertNotEqual(study.to_dict(),exported)
        with self.assertRaisesRegex(ValueError,'mesh_schedule requires'):
            replace(study,kind='curved_harmonic_sweep')

    def test_units_and_single_plan_schedule_keep_actual_parameter_semantics(self):
        raw=remesh_study_document([.5,.75]);unit=deepcopy(raw)
        unit['parameter_unit']='m';unit['values']=[v/10 for v in raw['values']]
        unit['mesh_schedule']['breakpoints']=[.075]
        unit['geometry_coefficients']={k:[c*10**i for i,c in enumerate(cs)] for k,cs in unit['geometry_coefficients'].items()}
        for a,b in zip(Study.from_dict(raw).projects(),Study.from_dict(unit).projects()):
            self.assertEqual(a.mesh_data['triangles'],b.mesh_data['triangles'])
            np.testing.assert_allclose(a.mesh_data['points'],b.mesh_data['points'],rtol=0,atol=2e-15)
        raw['mesh_schedule']['breakpoints']=[];raw['mesh_schedule']['plans']=raw['mesh_schedule']['plans'][1:]
        self.assertEqual([len(p.mesh_data['triangles']) for p in Study.from_dict(raw).projects()],[28,28])

    def test_unused_plan_and_invalid_late_geometry_reject_before_output(self):
        raw=remesh_study_document([0.,.5]);bad=deepcopy(raw)
        bad['mesh_schedule']['plans'][1]['plan']['source_mesh']['triangles'][0]=[0,0,0]
        invalid=[bad,dict(raw,values=[0.,-10.])]
        with tempfile.TemporaryDirectory() as tmp:
            for i,document in enumerate(invalid):
                target=Path(tmp)/str(i)
                with self.assertRaises(ValueError):execute_study(Study.from_dict(document),target)
                self.assertFalse(target.exists())
        from superfish_ng.study_shape_tracking import pair_controls
        with self.assertRaisesRegex(ValueError,'without comparison_meshes'):
            pair_controls(Study.from_dict(raw),dict(controls(),comparison_meshes=[]),0.,.5)

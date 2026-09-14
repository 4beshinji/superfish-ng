# SPDX-License-Identifier: Apache-2.0
"""TE partition changes preserve sector volume, actual fields and ancestry."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import solve
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study
from superfish_ng.tuning import _request, _project, execute_tune, replay_tune
from superfish_ng.curved_partition_schedule import build_partition_schedule
from superfish_ng.curved_project_remesh import remesh_curved_project
from test_te_symmetry_harmonic_workflows import symmetry_harmonic_study
from test_te_symmetry_piecewise_tracking import half_fixture
from test_curved_partition_schedule import partition
from test_curved_harmonic_study import controls
from test_curved_harmonic_deformation import space
from test_expression_tuning import c, op, X


def fixture(reflected=True, tag='magnetic_symmetry', side='z_max', levels=1):
    cases, maps, chart = half_fixture(side, tag)
    base = Project(replace(cases[0], curved_refinement_levels=levels),
                   reflect_full=reflected, mesh_data=maps[0]['source_mesh'])
    mesh = deepcopy(base.mesh_data)
    # Split the axis edge; each chart still covers the same source half-domain.
    mesh['points'].append([0., .05])
    mesh['triangles'] = [[0, 2, 5], [5, 2, 1], [0, 3, 2], [0, 4, 3]]
    mesh['boundary_edges'] = [[0, 5], [5, 1]] + mesh['boundary_edges'][1:]
    mesh['boundary_tags'] = ['axis'] + mesh['boundary_tags']
    second = replace(base, mesh_data=mesh)
    plans = dict(schema_version=1, breakpoints=[.125], max_pair_tests=300000,
                 partitions=[partition(base, chart, levels), partition(second, chart+[[0., .05]], levels)])
    remesh = dict(schema_version=1, source_mesh=mesh, curved_refinement_levels=levels,
                  minimum_corner_angle_deg=.1)
    return base, plans, remesh


def study_request():
    base, _, plan = fixture()
    raw = symmetry_harmonic_study()
    raw.update(study_version=4, kind='curved_remesh_sweep', project=base.to_dict(), values=[0., .25],
               mesh_schedule=dict(schema_version=1, breakpoints=[.125],
                                  plans=[dict(kind='original'), dict(kind='replace', plan=plan)]))
    return raw


def tune_request():
    base, schedule, _ = fixture(levels=2)
    expr = op('add', c(.08, 'm'), op('mul', c(.0064, 'm'), op('sub', op('exp', X), c(1))))
    return dict(schema_version=8, project=base.to_dict(), geometry_kind='curved_harmonic',
                parameter='x', parameter_unit='1', bounds=[0., .25], mesh_schedule=schedule,
                bindings=[dict(path='/case/geometry/curves/'+p, expression=deepcopy(expr))
                          for p in ('2/end_zr_m/1', '3/start_zr_m/1')],
                rf_coordinates='fixed', minimum_corner_angle_deg=1., target_hz=1e9,
                frequency_tolerance_hz=1e6, mesh_frequency_tolerance_hz=1e6,
                parameter_tolerance=1e-8, max_trials=8, initial_ids=['TE'], mode_id='TE',
                controls=controls(), refinement_scale=2)


class TESymmetryPartitionWorkflowTests(unittest.TestCase):
    def test_all_sectors_preserve_independent_volume_across_partitions(self):
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        from superfish_ng.curved_reflection import reflect_curved_space
        from superfish_ng.fem import triangle_quadrature
        rule=list(triangle_quadrature(5)); q=np.array([b[1:] for b,w in rule]); weights=np.array([w for b,w in rule])
        expected=np.pi*.08**2*.1
        for side in ('z_min', 'z_max'):
            for tag in ('magnetic_symmetry', 'electric_symmetry'):
                for reflected in (False, True):
                    with self.subTest(side=side, tag=tag, reflected=reflected):
                        base,schedule,plan=fixture(reflected,tag,side)
                        projects=(*build_partition_schedule(base,schedule), remesh_curved_project(base,plan))
                        self.assertEqual([len(p.mesh_data['triangles']) for p in projects],[3,4,4])
                        for p in projects:
                            self.assertEqual(p.reflect_full,reflected)
                            self.assertEqual(getattr(p.case,side),tag)
                            half=space(p)
                            self.assertAlmostEqual(-boundary_moments(half)['signed_volume_m3']/expected,1.,places=12)
                            if reflected:
                                full=reflect_curved_space(p.case,half,coefficient_parity=1 if tag=='magnetic_symmetry' else -1)
                                actual=full.space
                                volume=sum(2*np.pi*(m.evaluate(q)['points_rz_m'][:,0]*m.evaluate(q)['determinant_m2'])@weights for m in actual.geometry.local_maps)
                                self.assertAlmostEqual(volume/(2*expected),1.,places=12)

    def test_study_switch_uses_real_fields_and_saved_replay(self):
        from superfish_ng.study_mode_tracking import build_study_mode_tracking,replay_study_mode_tracking
        study=Study.from_dict(study_request())
        self.assertEqual([len(p.mesh_data['triangles']) for p in study.projects()],[3,4])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);execute_study(study,root/'study')
            result=build_study_mode_tracking(dict(schema_version=1,study_run=str(root/'study'),initial_ids=['TE'],step_controls=[controls()]))
            self.assertEqual(result['status'],'PASS');self.assertEqual(replay_study_mode_tracking(result),result)
            mapping=result['history']['steps'][0]['tracking']['physical_mapping']
            self.assertEqual(mapping['field'],'Ephi_V_per_m');self.assertTrue(mapping['symmetry_sector']['reflected'])
            expected=[2*np.pi*.1*.08**2*(1+.08*x+(.08*x)**2/3) for x in study.values]
            np.testing.assert_allclose(mapping['axisymmetric_volumes_m3'],expected,rtol=1e-12)

    def test_tune_switch_resume_and_original_partition_refinement(self):
        r=tune_request();p=_project(r,0.,'search')
        r['target_hz']=float(solve(p.case,mesh_data=p.mesh_data).frequencies_hz[0])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_tune(r,root/'first',max_new_trials=2)
            final=execute_tune(r,root/'rest',checkpoint=first)
            self.assertEqual(final['status'],'TUNED',final['decision']);self.assertEqual(replay_tune(final),final)
            self.assertEqual(first['trial_sources_sha256'],final['trial_sources_sha256'][:2])
            self.assertEqual([len(_project(r,t['value'],t['phase']).mesh_data['triangles']) for t in final['trials']],[3,4,3])
            for trial in final['trials'][1:]:
                mapping=trial['tracking']['tracking']['physical_mapping']
                self.assertTrue(mapping['symmetry_sector']['reflected'])
                self.assertEqual(mapping['field'],'Ephi_V_per_m')
            bad=deepcopy(final);bad['request']['mesh_schedule']['breakpoints']=[.3]
            with self.assertRaises(ValueError):replay_tune(bad)

    def test_marked_replacements_freeze_their_own_history_and_volume(self):
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        base,schedule,plan=fixture(levels=0)
        for entry in [*schedule['partitions'],plan]:
            entry.pop('curved_refinement_levels')
            entry['curved_refinement_steps']=[dict(kind='marked',marked_cells=[0],minimum_corner_angle_deg=.1)]
        projects=(*build_partition_schedule(base,schedule),remesh_curved_project(base,plan))
        for p in projects:
            self.assertTrue(p.case.curved_refinement_steps[0].split_pattern)
            self.assertTrue(p.reflect_full)
            self.assertAlmostEqual(-boundary_moments(space(p))['signed_volume_m3']/(np.pi*.08**2*.1),1.,places=12)

    def test_invalid_replacement_tags_and_rf_fail_before_output(self):
        base,schedule,plan=fixture()
        bad=deepcopy(schedule);bad['partitions'][1]['source_mesh']['boundary_tags'][2]='pec'
        with self.assertRaises(ValueError):build_partition_schedule(base,bad)
        bad=deepcopy(plan);bad['source_mesh']['boundary_tags'][2]='pec'
        with self.assertRaises(ValueError):remesh_curved_project(base,bad)
        request=tune_request();request['rf_coordinates']='axis_fraction'
        with self.assertRaisesRegex(ValueError,'TE.*fixed'):_request(request)
        raw=study_request();raw['geometry_coefficients'].update({'/curves/1/end_zr_m/0':[.1,.01],'/curves/2/start_zr_m/0':[.1,.01]})
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'invalid'
            with self.assertRaises(ValueError):execute_study(Study.from_dict(raw),target)
            self.assertFalse(target.exists())

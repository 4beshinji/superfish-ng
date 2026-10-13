# SPDX-License-Identifier: Apache-2.0
"""Complete generation replay, strict derived metadata and atomic CLI output."""
from copy import deepcopy
from dataclasses import replace
from functools import lru_cache
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from superfish_ng.project import Project, parse_json
from test_curved_boundary_remesh import fixture, space, measurements
from test_curved_remesh_generation import generation_settings


@lru_cache(maxsize=None)
def original_document(name='nonaffine', version=2):
    from superfish_ng.curved_remesh_generation import build_curved_remesh_generation
    project, settings = fixture(name)
    if version == 1:
        settings = generation_settings()
    return build_curved_remesh_generation(project, settings)


def document(name='nonaffine', version=2):
    return deepcopy(original_document(name, version))


class CurvedBoundaryRemeshSavedTests(unittest.TestCase):
    def test_rectangle_validation_matches_closed_form_uniform_geometry(self):
        validation = document('rectangle')['validation']
        # The original right triangles have legs R=.1, L=.2. Three uniform
        # restrictions divide lengths by 8 and areas by 64, retaining angles.
        self.assertEqual(validation['prefix_triangle_counts'], [2, 8, 32, 128])
        self.assertEqual(validation['prefix_boundary_edge_counts'], [4, 8, 16, 32])
        self.assertAlmostEqual(validation['final_max_chord_edge_m'], np.hypot(.1, .2)/8, places=15)
        self.assertAlmostEqual(validation['final_max_chord_triangle_area_m2'], .1*.2/2/64, places=17)
        expected = float(np.degrees(np.arctan(.1/.2)))
        self.assertAlmostEqual(validation['final_minimum_chord_angle_deg'], expected, places=11)
        self.assertAlmostEqual(validation['final_minimum_corner_angle_deg'], expected, places=11)

    def test_full_replay_both_settings_versions_and_independent_prefix_measurements(self):
        from superfish_ng.curved_remesh_generation import replay_curved_remesh_generation
        from superfish_ng.curved_project_remesh import remesh_curved_project
        from superfish_ng.curved_marked_refinement import _minimum_corner_angle
        for name, version in (('rectangle', 2), ('nonaffine', 2), ('nonaffine', 1)):
            with self.subTest(name=name, version=version), patch('superfish_ng.solver.solve', side_effect=AssertionError('unexpected FEM')):
                saved = document(name, version)
                before = deepcopy(saved)
                result = replay_curved_remesh_generation(parse_json(json.dumps(saved, allow_nan=False)))
                self.assertEqual(result, saved)
                self.assertEqual(saved, before)
                self.assertIsNone(result['physical_error_bound'])
                source = Project.from_dict(result['source_project'])
                target = remesh_curved_project(source, result['plan'])
                case = target.case
                stages = [replace(case, curved_refinement_levels=i, curved_refinement_steps=())
                          for i in range(case.curved_refinement_levels+1)]
                stages += [replace(case, curved_refinement_steps=case.curved_refinement_steps[:i])
                           for i in range(1, len(case.curved_refinement_steps)+1)]
                natives = [space(replace(target, case=stage)) for stage in stages]
                validation = result['validation']
                self.assertEqual(validation['prefix_triangle_counts'], [len(s.geometry.cell_nodes) for s in natives])
                self.assertEqual(validation['prefix_boundary_edge_counts'], [len(s.geometry.boundary_nodes) for s in natives])
                self.assertEqual(validation['seed_triangle_count'], len(target.mesh_data['triangles']))
                areas, _, _, lengths = measurements(natives[-1])
                self.assertEqual(validation['final_max_chord_edge_m'], float(lengths.max()))
                self.assertEqual(validation['final_max_chord_triangle_area_m2'], float(areas.max()))
                self.assertEqual(validation['final_minimum_corner_angle_deg'], _minimum_corner_angle(natives[-1].geometry.local_maps))
                self.assertEqual(validation['status'], 'GEOMETRY_VERIFIED')
                # Legacy generation measures final values without reinterpreting
                # its size settings as new final-native constraints.
                self.assertEqual(result['settings']['schema_version'], version)

    def test_implicit_source_and_browser_number_spelling_roundtrip(self):
        from superfish_ng.curved_remesh_generation import build_curved_remesh_generation, replay_curved_remesh_generation
        project, settings = fixture()
        project = replace(project, mesh_data=None, case=replace(project.case, curved_refinement_steps=()))
        before = deepcopy(project.to_dict())
        saved = build_curved_remesh_generation(project, settings)
        self.assertEqual(saved['source_project'], before)
        self.assertEqual(project.to_dict(), before)
        self.assertEqual(replay_curved_remesh_generation(saved), saved)
        def browser_numbers(value):
            if type(value) is dict:return {k: browser_numbers(v) for k, v in value.items()}
            if type(value) is list:return [browser_numbers(v) for v in value]
            if type(value) is float and value.is_integer():return int(value)
            return value
        browser = browser_numbers(document('rectangle'))
        self.assertEqual(replay_curved_remesh_generation(browser), document('rectangle'))

    def test_closed_header_and_validation_keys_fail_before_regeneration(self):
        from superfish_ng.curved_remesh_generation import replay_curved_remesh_generation
        original = document('rectangle')
        invalid = [None, [], dict(original, unknown=1), dict(original, schema_version=True),
                   dict(original, schema_version=2), dict(original, document_type='other'),
                   dict(original, physical_error_bound=0)]
        for field in original:
            bad = deepcopy(original); del bad[field]; invalid.append(bad)
        for field in original['validation']:
            bad = deepcopy(original); del bad['validation'][field]; invalid.append(bad)
        bad = deepcopy(original); bad['validation']['unknown'] = 1; invalid.append(bad)
        with patch('superfish_ng.curved_remesh_generation.build_curved_remesh_generation', side_effect=AssertionError('regenerated invalid header')):
            for bad in invalid:
                with self.subTest(value=bad), self.assertRaises(ValueError):
                    replay_curved_remesh_generation(bad)

    def test_all_derived_sections_reject_tampering_and_integer_type_substitution(self):
        from superfish_ng.curved_remesh_generation import replay_curved_remesh_generation
        original = document('rectangle')
        invalid = []
        for field, value in original['validation'].items():
            bad = deepcopy(original)
            if type(value) is dict:bad['validation'][field]['maximum_coefficient_distance_m'] = 1.
            elif type(value) is list:bad['validation'][field][-1] += 1
            elif type(value) is str:bad['validation'][field] = 'PASS'
            else:bad['validation'][field] += 1
            invalid.append(bad)
        for value in (True, 2.0):
            bad = deepcopy(original); bad['validation']['seed_triangle_count'] = value; invalid.append(bad)
        bad = deepcopy(original); bad['validation']['prefix_boundary_edge_counts'][0] = 4.; invalid.append(bad)
        bad = deepcopy(original); bad['plan']['source_mesh']['points'][1][0] += .001; invalid.append(bad)
        bad = deepcopy(original); bad['plan']['curved_refinement_steps'][0]['split_pattern']['parent_topology_sha256'] = '0'*64; invalid.append(bad)
        bad = deepcopy(original); bad['plan']['curved_refinement_steps'].pop(); invalid.append(bad)
        for bad in invalid:
            with self.subTest(plan=bad['plan'], validation=bad['validation']), self.assertRaisesRegex(ValueError, 'reconstruction'):
                replay_curved_remesh_generation(bad)
        self.assertEqual(original, document('rectangle'))

    def test_changed_source_requests_and_raw_nested_duplicates_are_revalidated(self):
        from superfish_ng.curved_remesh_generation import replay_curved_remesh_generation
        original = document('rectangle')
        changes = [('max_boundary_edges', 3), ('max_triangles', 1), ('max_rounds', 0),
                   ('max_chord_edge_m', float('nan')), ('boundary_policy', 'reproject_analytic')]
        for key, value in changes:
            bad = deepcopy(original); bad['settings'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                replay_curved_remesh_generation(bad)
        bad = deepcopy(original); bad['source_project']['mesh_data']['boundary_tags'][0] = 'pec'
        with self.assertRaises(ValueError):replay_curved_remesh_generation(bad)
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key: schema_version'):
            parse_json(json.dumps(original).replace('"schema_version": 2', '"schema_version": 2,"schema_version": 2', 1))
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key: kind'):
            parse_json('{"plan":{"steps":[{"kind":"uniform","kind":"uniform"}]}}')
        with self.assertRaises(TypeError):replay_curved_remesh_generation(original, max_triangles=100000)

    def test_replayed_plan_enters_existing_study_with_original_shape_mapping(self):
        from superfish_ng.curved_remesh_generation import replay_curved_remesh_generation
        from superfish_ng.studies import Study
        from superfish_ng.study_shape_tracking import pair_controls
        from test_curved_remesh_study import remesh_study_document
        from test_curved_harmonic_study import controls
        saved = replay_curved_remesh_generation(document())
        raw = remesh_study_document()
        self.assertEqual(raw['project'], saved['source_project'])
        raw['mesh_schedule']['plans'][1]['plan'] = saved['plan']
        study = Study.from_dict(parse_json(json.dumps(raw)))
        self.assertEqual(study.to_dict(), raw)
        projects = study.projects()
        maps = pair_controls(study, controls(), 0., 1., projects=projects)['comparison_meshes']
        self.assertEqual(len(maps[0]['source_mesh']['triangles']), 26)
        self.assertEqual(len(maps[1]['source_mesh']['triangles']), 26)
        self.assertEqual(len(projects[1].mesh_data['triangles']), 8)
        self.assertEqual(len(space(projects[1]).geometry.boundary_nodes), 28)
        again = Study.from_dict(study.to_dict()).projects()
        for left, right in zip(projects, again):
            self.assertEqual(left.to_dict(), right.to_dict())
            np.testing.assert_array_equal(space(left).geometry.points_rz_m, space(right).geometry.points_rz_m)

    def test_cli_document_plan_replay_exclusive_and_failure_outputs(self):
        from superfish_ng.cli import main
        project, settings = fixture('rectangle')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); project.save(root/'project.json')
            (root/'settings.json').write_text(json.dumps(settings))
            before = (root/'project.json').read_bytes()
            args = ['generate-curved-remesh-plan', str(root/'project.json'), '--settings', str(root/'settings.json')]
            self.assertEqual(main(args+['--format', 'document', '--out', str(root/'document.json')]), 0)
            self.assertEqual(parse_json((root/'document.json').read_text()), document('rectangle'))
            self.assertEqual(main(args+['--out', str(root/'plan.json')]), 0)
            replay = ['replay-curved-remesh-generation', str(root/'document.json')]
            self.assertEqual(main(replay), 0)
            self.assertEqual(main(replay+['--out', str(root/'replayed-plan.json')]), 0)
            self.assertEqual((root/'replayed-plan.json').read_bytes(), (root/'plan.json').read_bytes())
            doc_before = (root/'document.json').read_bytes()
            self.assertEqual(main(args+['--format', 'document', '--out', str(root/'document.json')]), 2)
            self.assertEqual(main(replay+['--out', str(root/'plan.json')]), 2)
            self.assertEqual((root/'document.json').read_bytes(), doc_before)
            (root/'bad.json').write_text('{"schema_version":1,"schema_version":1}')
            self.assertEqual(main(['replay-curved-remesh-generation', str(root/'bad.json'), '--out', str(root/'no-plan.json')]), 2)
            self.assertFalse((root/'no-plan.json').exists())
            (root/'settings.json').write_text(json.dumps(dict(settings, max_boundary_edges=3)))
            self.assertEqual(main(args+['--format', 'document', '--out', str(root/'no-document.json')]), 2)
            self.assertFalse((root/'no-document.json').exists())
            self.assertEqual((root/'project.json').read_bytes(), before)

    def test_cli_interrupt_and_atomic_publication_leave_no_partial_output(self):
        from superfish_ng.cli import main
        from superfish_ng.curved_remesh_generation import _write_generation_json
        project, settings = fixture('rectangle')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); project.save(root/'project.json')
            (root/'settings.json').write_text(json.dumps(settings))
            args = ['generate-curved-remesh-plan', str(root/'project.json'), '--settings', str(root/'settings.json'),
                    '--format', 'document', '--out', str(root/'interrupted.json')]
            with patch('superfish_ng.curved_remesh_generation.build_curved_remesh_generation', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):main(args)
            self.assertFalse((root/'interrupted.json').exists())
            before = sorted(p.name for p in root.iterdir())
            for failure in (OSError('publication failure'), KeyboardInterrupt()):
                with patch('os.link', side_effect=failure), self.assertRaises(type(failure)):
                    _write_generation_json(root/'partial.json', document('rectangle'))
                self.assertFalse((root/'partial.json').exists())
                self.assertEqual(sorted(p.name for p in root.iterdir()), before)
            with self.assertRaises(ValueError):_write_generation_json(root/'nonfinite.json', {'value': float('nan')})
            self.assertFalse((root/'nonfinite.json').exists())

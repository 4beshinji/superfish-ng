# SPDX-License-Identifier: Apache-2.0
"""Real planar shape tuning, independent cutoff invariants and owned replay."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from superfish_ng.constants import C0
from superfish_ng.planar import solve_planar, planar_quantities
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_project import PlanarProject
from superfish_ng.planar_piecewise_shape import PlanarPiecewiseShapeLaw
from superfish_ng.planar_saved import read_planar_run
from superfish_ng.planar_tracking import PlanarTrackingControls
from superfish_ng.planar_tuning import execute_planar_tune, read_planar_tune, replay_planar_tune
from superfish_ng.planar_tuning_saved import _snapshot_trial, _owned_assemble
from test_planar_tracking_exact_affine import rectangle
from test_planar_tuning import request


def shape_request(width=1., height=.5, end_width=1.125, *, nonaffine=True, nx=8):
    project = PlanarProject(PlanarPolygonCase(rectangle(nx, nx, width, height), modes=3))
    dx = end_width-width
    law = PlanarPiecewiseShapeLaw(project.case.mesh,
        [[[0., float(2*dx*max(x/width-.5, 0.) if nonaffine else dx*x/width)], [0.]]
         for x, y in project.case.mesh.points_xy_m], [0., 1.])
    raw = request()
    raw.update(schema_version=4, project=project.to_dict(), parameter='deformation', bounds=[0., 1.],
               shape_law=law.to_dict(), initial_ids=['first'], mode_id='first',
               target_hz=C0/(width+end_width), frequency_tolerance_hz=2e4,
               mesh_frequency_tolerance_hz=2e4,
               identity_recovery=dict(anchor_selection='latest_resolved_trial', controls=raw['controls']))
    return raw


def crossing_request(end_width=.214):
    raw = shape_request(.18, .2, end_width, nonaffine=False, nx=8)
    raw.update(initial_ids=['y', 'x'], mode_id='x', target_hz=C0/(2*end_width),
               frequency_tolerance_hz=2e5, mesh_frequency_tolerance_hz=2e5,
               controls=PlanarTrackingControls(relative_cluster_gap=.08).to_dict(),
               identity_recovery=dict(anchor_selection='fixed_trial', anchor_trial_index=0,
                                      controls=PlanarTrackingControls().to_dict()))
    return raw


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def rehash_trial(root, checkpoint, index):
    trial = root/f'trial-{index+1:03d}'
    native = trial/'solution'; manifest = json.loads((native/'manifest.json').read_text())
    for name in manifest['files']:
        manifest['files'][name] = hashlib.sha256((native/name).read_bytes()).hexdigest()
    save(native/'manifest.json', manifest)
    job = json.loads((trial/'manifest.json').read_text())
    for name in job['files']:
        job['files'][name] = hashlib.sha256((trial/name).read_bytes()).hexdigest()
    save(trial/'manifest.json', job)
    checkpoint['trial_sources_sha256'][index] = _snapshot_trial(trial)


class PlanarPiecewiseTuningTests(unittest.TestCase):
    def test_nonaffine_real_bracket_independent_mesh_move_cli_and_owned_resume(self):
        raw = shape_request()
        original = deepcopy(raw)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = execute_planar_tune(raw, root/'first', max_new_trials=2)
            self.assertEqual(first['status'], 'PAUSED')
            self.assertEqual(first['decision']['next_trial']['phase'], 'search')
            self.assertEqual(first['decision']['next_trial']['value'], .5)
            saved = (root/'first/checkpoint-002.json').read_bytes()
            hashes = first['trial_sources_sha256']
            (root/'first').rename(root/'first-moved')
            moved = read_planar_tune(root/'first-moved/checkpoint-002.json')
            self.assertEqual(moved['trials'], first['trials'])
            middle = execute_planar_tune(raw, root/'middle', checkpoint=moved, max_new_trials=1)
            self.assertEqual(middle['decision']['next_trial']['phase'], 'refinement')
            self.assertEqual(middle['trial_sources_sha256'][:2], hashes)
            self.assertEqual(saved, (root/'first-moved/checkpoint-002.json').read_bytes())
            (root/'first-moved').rename(root/'ancestor-unavailable')
            (root/'middle').rename(root/'middle-moved')
            path = root/'middle-moved/checkpoint-003.json'
            process = subprocess.run([sys.executable, '-m', 'superfish_ng', 'resume-tune-planar',
                str(path), '--out', str(root/'final')], text=True, capture_output=True, timeout=300)
            self.assertEqual(process.returncode, 0, process.stdout+process.stderr)
            self.assertIn('TUNED', process.stdout)
            final = read_planar_tune(root/'final/checkpoint-004.json')
            self.assertEqual(final['status'], 'TUNED')
            self.assertEqual(final['schema_version'], 2)
            self.assertEqual(final['trials'][:3], middle['trials'])
            self.assertEqual(final['trial_sources_sha256'][:3], middle['trial_sources_sha256'])
            for i, run in enumerate(final['trial_runs']):
                self.assertEqual(Path(run).parent, root/'final')
                self.assertEqual(_snapshot_trial(run), final['trial_sources_sha256'][i])
                if i < 3:
                    old = read_planar_run(root/'middle-moved'/f'trial-{i+1:03d}'/'solution')
                    new = read_planar_run(Path(run)/'solution')
                    np.testing.assert_array_equal(old.coefficients, new.coefficients)
            native = read_planar_run(root/'final/trial-004/solution')
            # The deformation has two distinct cell stretches, while its
            # boundary remains an exact rectangle with an analytical TE10.
            native_width = 1.0625
            self.assertAlmostEqual(native.case.mesh.area_m2, native_width*.5, places=14)
            independent = solve_planar(replace(native.case, mesh=rectangle(16, 16, native_width, .5, flipped=True)))
            analytic = C0/(2*native_width)
            coarse = final['trials'][-2]['frequency_hz']
            fine = native.frequencies_hz[0]
            self.assertLess(abs(fine-analytic), abs(coarse-analytic))
            self.assertLess(abs(fine-analytic)/analytic, 3e-6)
            self.assertLess(abs(independent.frequencies_hz[0]-analytic)/analytic, 3e-6)
            self.assertLess(abs(fine-independent.frequencies_hz[0])/analytic, 3e-6)
            qa, qb = [planar_quantities(s) for s in (native, independent)]
            self.assertLess(abs(qa['geometry_factor_ohm']/qb['geometry_factor_ohm']-1), 3e-4)
            self.assertEqual(final['trials'][-1]['tracking']['result_version'], 10)
            self.assertTrue(final['decision']['mesh_difference_met'])
            self.assertTrue(final['decision']['refined_target_met'])
            # Tighten only the independently declared mesh gate, using the
            # same verified native data; never rewrite a saved decision.
            strict = dict(raw, mesh_frequency_tolerance_hz=1e-6)
            failed_gate = _owned_assemble(strict, final['trial_runs'])
            self.assertEqual(failed_gate['status'], 'REFINEMENT_FAILED')
            self.assertTrue(failed_gate['decision']['refined_target_met'])
            self.assertFalse(failed_gate['decision']['mesh_difference_met'])
            (root/'final').rename(root/'final-moved')
            process = subprocess.run([sys.executable, '-m', 'superfish_ng', 'replay-tune-planar',
                str(root/'final-moved/checkpoint-004.json')], text=True, capture_output=True, timeout=300)
            self.assertEqual(process.returncode, 0, process.stdout+process.stderr)
            with patch('superfish_ng.planar_tuning_saved.execute_planar_project', side_effect=AssertionError('new solve')):
                terminal = read_planar_tune(root/'final-moved/checkpoint-004.json')
                self.assertEqual(replay_planar_tune(terminal), terminal)
            with self.assertRaisesRegex(ValueError, 'PAUSED'):
                execute_planar_tune(raw, root/'terminal', checkpoint=terminal)
            self.assertFalse((root/'terminal').exists())
        self.assertEqual(raw, original)

    def test_nonaffine_tm_tuning_matches_independent_dirichlet_cutoff(self):
        raw = shape_request(nx=12)
        project = PlanarProject.from_dict(raw['project'])
        raw['project'] = replace(project, case=replace(project.case, polarization='tm')).to_dict()
        width, height = 1.0625, .5
        raw['target_hz'] = C0/2*np.sqrt(1/width**2+1/height**2)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = execute_planar_tune(raw, root/'tm')
            self.assertEqual(result['status'], 'TUNED')
            self.assertEqual([v['phase'] for v in result['trials']], ['search', 'search', 'search', 'refinement'])
            fine = read_planar_run(root/'tm/trial-004/solution')
            independent = solve_planar(replace(fine.case, mesh=rectangle(24, 24, width, height, flipped=True)))
            analytic = raw['target_hz']
            coarse = result['trials'][-2]['frequency_hz']
            self.assertLess(abs(fine.frequencies_hz[0]-analytic), abs(coarse-analytic))
            self.assertLess(abs(fine.frequencies_hz[0]/analytic-1), 3e-6)
            self.assertLess(abs(independent.frequencies_hz[0]/analytic-1), 3e-6)
            self.assertLess(abs(fine.frequencies_hz[0]-independent.frequencies_hz[0])/analytic, 3e-6)
            quantities = planar_quantities(fine)
            self.assertAlmostEqual(quantities['electric_energy_j_per_m'], .5, places=11)
            self.assertAlmostEqual(quantities['magnetic_energy_j_per_m'], .5, places=11)
            self.assertEqual(result['trials'][-1]['tracking']['result_version'], 10)
            self.assertEqual(read_planar_tune(root/'tm/checkpoint-004.json'), result)

    def test_similarity_limit_real_tuning_and_rf_scaling(self):
        raw = shape_request(end_width=2., nonaffine=False)
        project = PlanarProject.from_dict(raw['project'])
        law = PlanarPiecewiseShapeLaw(project.case.mesh,
            [[[0., float(x)], [0., float(y)]] for x, y in project.case.mesh.points_xy_m], [0., 1.])
        raw.update(shape_law=law.to_dict(), target_hz=C0/4)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = execute_planar_tune(raw, root/'similarity')
            self.assertEqual(result['status'], 'TUNED')
            self.assertEqual([v['phase'] for v in result['trials']], ['search', 'search', 'refinement'])
            old, new = [read_planar_run(Path(v)/'solution') for v in result['trial_runs'][:2]]
            self.assertAlmostEqual(new.frequencies_hz[0]/old.frequencies_hz[0], .5, delta=2e-12)
            qa, qb = [planar_quantities(s) for s in (old, new)]
            self.assertAlmostEqual(qb['geometry_factor_ohm']/qa['geometry_factor_ohm'], 1., delta=2e-11)
            self.assertAlmostEqual(qb['q0']/qa['q0'], np.sqrt(2), delta=2e-11)
            self.assertEqual(old.case.normalization_j_per_m, new.case.normalization_j_per_m)
            self.assertLess(abs(result['trials'][-1]['frequency_hz']/raw['target_hz']-1), 3e-6)
            self.assertEqual(read_planar_tune(root/'similarity/checkpoint-003.json'), result)

    def test_actual_search_final_and_earlier_anchor_recovery_survive_copy(self):
        raw = crossing_request()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = execute_planar_tune(raw, root/'first', max_new_trials=2)
            self.assertEqual(first['status'], 'PAUSED')
            self.assertEqual(first['trials'][1]['tracking']['current_mode_ids'], [None, None])
            self.assertEqual(first['trials'][1]['current_mode_ids'], ['x', 'y'])
            final = execute_planar_tune(raw, root/'final', checkpoint=first)
            (root/'first').rename(root/'source-unavailable')
            final = read_planar_tune(root/'final/checkpoint-003.json')
            self.assertEqual(final['status'], 'TUNED')
            self.assertEqual(final['trial_sources_sha256'][:2], first['trial_sources_sha256'])
            for trial in final['trials'][1:]:
                event = trial['identity_recovery']
                self.assertEqual(event['status'], 'PASS')
                self.assertEqual(event['anchor_trial_index'], 0)
                self.assertEqual(trial['current_mode_ids'], ['x', 'y'])
            self.assertEqual(final['trials'][-1]['identity_recovery']['parent_trial_index'], 1)

    def test_true_degeneracy_guard_or_missing_anchor_never_evaluates_frequency(self):
        initial = shape_request(.2, .2, .22, nonaffine=False, nx=8)
        initial.update(initial_ids=['y', 'x'], mode_id='x')
        guard = deepcopy(initial); guard.update(initial_ids=['first'], mode_id='first')
        current = crossing_request(.2)
        missing = crossing_request(); missing['identity_recovery']['anchor_trial_index'] = 5
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, raw, count in [('initial', initial, 1), ('guard', guard, 1), ('current', current, 2), ('missing', missing, 2)]:
                with self.subTest(name=name):
                    result = execute_planar_tune(raw, root/name)
                    self.assertEqual(result['status'], 'UNVERIFIED')
                    self.assertEqual(len(result['trials']), count)
                    self.assertIsNone(result['trials'][-1]['frequency_hz'])
                    self.assertIsNone(result['trials'][-1]['target_error_hz'])
                    self.assertFalse(result['can_resume'])
                    self.assertEqual(read_planar_tune(root/name/f'checkpoint-{count:03d}.json'), result)
                    if name == 'guard':
                        self.assertTrue(result['trials'][0]['initial_tracking']['guard_overlap'])

    def test_rehashed_native_law_parent_or_result_changes_are_rejected(self):
        raw = shape_request()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); execute_planar_tune(raw, root/'source', max_new_trials=2)
            for kind in ('coefficient', 'mesh', 'rf', 'law', 'parent', 'result'):
                with self.subTest(kind=kind):
                    target = root/kind; shutil.copytree(root/'source', target)
                    path = target/'checkpoint-002.json'; doc = json.loads(path.read_text())
                    if kind in ('coefficient', 'mesh'):
                        name = 'fields.npz' if kind == 'coefficient' else 'mesh.npz'
                        native = target/'trial-002/solution'/name
                        with np.load(native, allow_pickle=False) as arrays:
                            data = {key: arrays[key].copy() for key in arrays.files}
                        if kind == 'coefficient': data['coefficients'][0] *= 1.001
                        else: data['points_xy_m'][1, 0] += 1e-5
                        np.savez_compressed(native, **data); rehash_trial(target, doc, 1)
                    elif kind == 'rf':
                        native = target/'trial-002/solution/results.json'
                        result = json.loads(native.read_text()); result['modes'][0]['geometry_factor_ohm'] *= 1.001
                        save(native, result); rehash_trial(target, doc, 1)
                    elif kind == 'law':
                        # Rebind both copies and all recorded metadata to an
                        # altered declared vertex displacement; native physics must
                        # still match the law-generated Project at each trial.
                        law = doc['request']['shape_law']
                        law['displacement_xy_m_coefficients'][6][0][0] += .001
                        save(target/'request.json', doc['request'])
                    elif kind == 'parent': doc['trials'][1]['parent_index'] = 1
                    else: doc['trials'][1]['frequency_hz'] *= 1.001
                    save(path, doc)
                    with self.assertRaises(ValueError): read_planar_tune(path)

    def test_failed_new_trial_keeps_owned_prefix_and_original_immutable(self):
        raw = shape_request()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = execute_planar_tune(raw, root/'first', max_new_trials=1)
            saved = (root/'first/checkpoint-001.json').read_bytes()
            with patch('superfish_ng.planar_tuning_saved.execute_planar_project', side_effect=RuntimeError('injected new solve failure')):
                with self.assertRaisesRegex(RuntimeError, 'injected'):
                    execute_planar_tune(raw, root/'failed', checkpoint=first)
            failure = json.loads((root/'failed/failure-002.json').read_text())
            self.assertEqual(failure['status'], 'FAILED'); self.assertNotIn('frequency_hz', failure)
            self.assertEqual(failure['preceding_trial_runs'], ['trial-001'])
            self.assertEqual(saved, (root/'first/checkpoint-001.json').read_bytes())
            (root/'first').rename(root/'source-unavailable')
            owned = read_planar_tune(root/'failed/checkpoint-001.json')
            self.assertEqual(owned['trials'], first['trials'])
            self.assertEqual(owned['trial_sources_sha256'], first['trial_sources_sha256'])
            resumed = execute_planar_tune(raw, root/'resumed', checkpoint=owned)
            self.assertEqual(resumed['status'], 'TUNED')

    def test_owned_path_names_links_budget_and_request_binding_are_strict(self):
        raw = shape_request()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); result = execute_planar_tune(raw, root/'source', max_new_trials=1)
            original = deepcopy(result)
            for runs in (True, None, {}, 1):
                doc = dict(result, trial_runs=runs)
                save(root/'source/malformed.json', doc)
                with self.subTest(malformed=runs), self.assertRaises(ValueError):
                    read_planar_tune(root/'source/malformed.json')
            for runs in ([result['trial_runs'][0]+'/../trial-001'], ['../source/trial-001'],
                         ['execution/trial-001'], ['trial-001/'], ['trial-002'], [result['trial_runs'][0]]*2):
                doc = dict(result, trial_runs=runs)
                with self.subTest(runs=runs), self.assertRaises(ValueError):
                    replay_planar_tune(doc, base_directory=root/'source')
            alias = root/'alias'; alias.symlink_to(root/'source', target_is_directory=True)
            with self.assertRaises(ValueError): read_planar_tune(alias/'checkpoint-001.json')
            path = root/'source/checkpoint-001.json'
            doc = json.loads(path.read_text()); doc['trial_runs'] = result['trial_runs']; save(path, doc)
            with self.assertRaisesRegex(ValueError, 'relative'): read_planar_tune(path)
            (root/'source/trial-001/unexpected.txt').write_text('undeclared')
            with self.assertRaisesRegex(ValueError, 'exactly'): replay_planar_tune(result)
            (root/'source/trial-001/unexpected.txt').unlink()
            different = dict(raw, target_hz=raw['target_hz']*1.001)
            with self.assertRaisesRegex(ValueError, 'differs'):
                execute_planar_tune(different, root/'bad-request', checkpoint=original)
            self.assertFalse((root/'bad-request').exists())
            with self.assertRaises(FileExistsError): execute_planar_tune(raw, root/'source')
            self.assertEqual(replay_planar_tune(result), result)


if __name__ == '__main__':
    unittest.main()

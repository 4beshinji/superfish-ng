# SPDX-License-Identifier: Apache-2.0
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from superfish_ng.cli import main
from superfish_ng.constants import C0
from superfish_ng.hphi_native import read_hphi_run
from superfish_ng.hphi_tuning import (
    execute_hphi_tune,
    read_hphi_tune,
    replay_hphi_tune,
)
from superfish_ng.hphi_tracking import HphiTrackingControls
from superfish_ng.hphi_project import HphiProject
from superfish_ng.coaxial import CoaxialCase


def request():
    return dict(
        format='superfish_ng_hphi_tune',
        schema_version=1,
        project=HphiProject(CoaxialCase(.025, .05, .18, nr=3, nz=8, modes=3)).to_dict(),
        parameter='uniform_scale',
        mapping=dict(kind='uniform_scale'),
        bounds=[1., 2.],
        target_hz=C0/(2*.18*1.5),
        frequency_tolerance_hz=1e6,
        parameter_tolerance=1e-6,
        max_trials=20,
        initial_ids=['fundamental'],
        mode_id='fundamental',
        controls=HphiTrackingControls().to_dict(),
        refinement_levels=1,
        max_triangles=10000,
        max_dofs=10000,
        mesh_frequency_tolerance_hz=1e6,
    )


class HphiTuneSavedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.request = request()
        cls.first = execute_hphi_tune(cls.request, cls.root/'first', max_new_trials=2)
        cls.pre_refinement = execute_hphi_tune(
            cls.request, cls.root/'pre-refinement', checkpoint=cls.first, max_new_trials=1
        )
        cls.final = execute_hphi_tune(cls.request, cls.root/'final', checkpoint=cls.pre_refinement)
        unverified_request = copy.deepcopy(cls.request)
        unverified_request['controls']['relative_cluster_gap'] = .9
        cls.unverified = execute_hphi_tune(unverified_request, cls.root/'unverified')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_owned_layout_replay_and_resume(self):
        self.assertEqual(self.first['status'], 'PAUSED')
        self.assertEqual(len(self.first['trial_runs']), 2)
        self.assertEqual(self.pre_refinement['status'], 'PAUSED')
        self.assertEqual(len(self.pre_refinement['trial_runs']), 3)
        self.assertEqual(self.final['status'], 'TUNED')
        self.assertEqual(len(self.final['trial_runs']), 4)
        self.assertEqual(self.unverified['status'], 'UNVERIFIED')
        self.assertFalse(self.unverified['can_resume'])
        for index, run in enumerate(self.final['trial_runs'], 1):
            trial = Path(run)
            self.assertEqual(trial.name, f'trial-{index:03d}')
            self.assertEqual({p.name for p in trial.iterdir()}, {'project.json', 'solution'})
            self.assertEqual(
                {p.name for p in (trial/'solution').iterdir()},
                {'case.json', 'mesh.npz', 'fields.npz', 'results.json', 'manifest.json'},
            )
        self.assertEqual(read_hphi_tune(self.root/'first/checkpoint-002.json'), self.first)
        self.assertEqual(read_hphi_tune(self.root/'pre-refinement/checkpoint-003.json'), self.pre_refinement)
        self.assertEqual(read_hphi_tune(self.root/'final/checkpoint-004.json'), self.final)
        self.assertEqual(read_hphi_tune(self.root/'unverified/checkpoint-001.json'), self.unverified)

    def test_replay_does_not_call_solver_and_keeps_rf_sources(self):
        source = Path(self.final['trial_runs'][0])/'solution'
        solution = read_hphi_run(source)
        self.assertEqual(len(solution.frequencies_hz), 3)
        with patch('superfish_ng.hphi_tuning_saved.solve_hphi', side_effect=AssertionError('replay solved')):
            self.assertEqual(read_hphi_tune(self.root/'final/checkpoint-004.json'), self.final)

    def test_resume_output_survives_moving_original_output(self):
        original = self.root/'pre-refinement'
        moved = self.root/'pre-refinement-moved'
        original.rename(moved)
        try:
            self.assertEqual(read_hphi_tune(self.root/'final/checkpoint-004.json'), self.final)
        finally:
            moved.rename(original)

    def test_native_tampering_and_request_change_are_rejected(self):
        fields = Path(self.final['trial_runs'][0])/'solution'/'fields.npz'
        original = fields.read_bytes()
        try:
            fields.write_bytes(original + b'changed')
            with self.assertRaises(ValueError):
                read_hphi_tune(self.root/'final/checkpoint-004.json')
        finally:
            fields.write_bytes(original)
        changed = copy.deepcopy(self.final)
        changed['request']['target_hz'] *= 2
        with self.assertRaises(ValueError):
            replay_hphi_tune(changed)
        with self.assertRaisesRegex(ValueError, 'request differs'):
            execute_hphi_tune(changed['request'], self.root/'rejected', checkpoint=self.first)
        self.assertFalse((self.root/'rejected').exists())

    def test_cli_tune_resume_and_replay_names_and_exit_codes(self):
        request_path = self.root/'request.json'
        request_path.write_text(json.dumps(self.request), encoding='utf-8')
        first_solution = read_hphi_run(Path(self.final['trial_runs'][0])/'solution')
        with patch('superfish_ng.hphi_tuning_saved.solve_hphi', return_value=first_solution):
            self.assertEqual(main([
                'tune-hphi', str(request_path), '--out', str(self.root/'cli-first'),
                '--max-new-trials', '1',
            ]), 0)
        cli_checkpoint = self.root/'cli-first/checkpoint-001.json'
        with patch('superfish_ng.hphi_tuning_saved.solve_hphi', side_effect=AssertionError('replay solved')):
            self.assertEqual(main(['replay-tune-hphi', str(cli_checkpoint)]), 0)
        third_solution = read_hphi_run(Path(self.final['trial_runs'][2])/'solution')
        with patch('superfish_ng.hphi_tuning_saved.solve_hphi', return_value=third_solution):
            self.assertEqual(main([
                'resume-tune-hphi', str(self.root/'first/checkpoint-002.json'),
                '--out', str(self.root/'cli-rest'), '--max-new-trials', '1',
            ]), 0)
        self.assertEqual(read_hphi_tune(self.root/'cli-rest/checkpoint-003.json')['status'], 'PAUSED')
        invalid_path = self.root/'invalid-request.json'
        invalid = copy.deepcopy(self.request)
        invalid['parameter'] = 'stored_energy_j'
        invalid_path.write_text(json.dumps(invalid), encoding='utf-8')
        self.assertEqual(main([
            'tune-hphi', str(invalid_path), '--out', str(self.root/'cli-invalid'),
        ]), 2)
        self.assertFalse((self.root/'cli-invalid').exists())


if __name__ == '__main__':
    unittest.main()

# SPDX-License-Identifier: Apache-2.0
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng.cli import main
from superfish_ng.hphi_tuning import read_hphi_tune, replay_hphi_tune
from test_hphi_shape_tuning import coaxial_request


class HphiShapeTuneSavedTests(unittest.TestCase):
    def test_actual_cli_owned_resume_solver_free_replay_and_tampering(self):
        q = coaxial_request()
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            root = Path(tmp)
            request = root/'request.json';request.write_text(json.dumps(q))
            self.assertEqual(main(['tune-hphi',str(request),'--out',str(root/'first'),'--max-new-trials','2']),0)
            first = read_hphi_tune(root/'first/checkpoint-002.json')
            self.assertEqual(first['status'],'PAUSED')
            self.assertEqual(main(['resume-tune-hphi',str(root/'first/checkpoint-002.json'),'--out',str(root/'final')]),0)
            final_path = root/'final/checkpoint-004.json'
            final = read_hphi_tune(final_path)
            self.assertEqual(final['status'],'TUNED')
            self.assertEqual(final['scope'],'coaxial_dimensions')
            self.assertEqual(final['request'],q)
            self.assertEqual(final['trials'][:2],first['trials'])
            self.assertEqual(final['trial_sources_sha256'][:2],first['trial_sources_sha256'])
            for old,new in zip(first['trial_runs'],final['trial_runs']):
                for p in Path(old).rglob('*'):
                    if p.is_file():self.assertEqual(p.read_bytes(),(Path(new)/p.relative_to(old)).read_bytes())
            (root/'first').rename(root/'moved-original')
            with patch('superfish_ng.hphi_tuning_saved.solve_hphi',side_effect=AssertionError('replay must not solve')):
                self.assertEqual(main(['replay-tune-hphi',str(final_path)]),0)
            for key,value in (('scope','vacuum_uniform_scale'),('request',{**q,'parameter':'outer_radius_m'})):
                bad = copy.deepcopy(final);bad[key] = value
                with self.assertRaises(ValueError):replay_hphi_tune(bad)
            data = Path(final['trial_runs'][0])/'solution/fields.npz'
            data.write_bytes(data.read_bytes()+b'changed')
            with self.assertRaises(ValueError):read_hphi_tune(final_path)

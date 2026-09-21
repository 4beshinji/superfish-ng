# SPDX-License-Identifier: Apache-2.0
"""CLI checkpoints and worker refinement preserve recovered Hphi identities."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng.cli import main
from superfish_ng.jobs import JobManager
from superfish_ng.hphi_tuning import read_hphi_tune, replay_hphi_tune
from test_hphi_tuning_identity_recovery import request


class HphiTuneRecoverySavedTests(unittest.TestCase):
    def test_cli_search_worker_refinement_owned_replay_and_event_tampering(self):
        with ExitStack() as cleanup, redirect_stdout(io.StringIO()):
            artifact=os.environ.get('SUPERFISH_HPHI_RECOVERY_TEST_OUT')
            if artifact:
                root=Path(artifact).resolve();root.mkdir(parents=True,exist_ok=False)
            else:
                root=Path(cleanup.enter_context(tempfile.TemporaryDirectory()))
            q=request();path=root/'request.json';path.write_text(json.dumps(q,indent=2)+'\n')
            self.assertEqual(main(['tune-hphi',str(path),'--out',str(root/'first'),'--max-new-trials','3']),0)
            first=read_hphi_tune(root/'first/checkpoint-003.json')
            self.assertEqual(first['status'],'PAUSED')
            self.assertEqual(first['trials'][2]['identity_recovery']['status'],'PASS')
            manager=JobManager(root/'workspace');cleanup.callback(manager.close)
            identifier=manager.start_hphi_tune(q,checkpoint=first)
            self.assertEqual(manager.processes[identifier].wait(timeout=900),0)
            final_path=manager.directory(identifier)/'hphi-tune-results.json'
            final=read_hphi_tune(final_path)
            self.assertEqual(final['status'],'TUNED')
            self.assertEqual(final['request'],q)
            self.assertEqual(final['trials'][:3],first['trials'])
            self.assertEqual(final['trial_sources_sha256'][:3],first['trial_sources_sha256'])
            self.assertEqual(final['trials'][3]['identity_recovery']['anchor_trial_index'],2)
            for old,new in zip(first['trial_runs'],final['trial_runs']):
                for item in Path(old).rglob('*'):
                    if item.is_file():self.assertEqual(item.read_bytes(),(Path(new)/item.relative_to(old)).read_bytes())
            before={str(p):p.read_bytes() for run in final['trial_runs'] for p in Path(run).rglob('*') if p.is_file()}
            (root/'first').rename(root/'moved-original')
            with patch('superfish_ng.hphi_tuning_saved.solve_hphi',side_effect=AssertionError('no new candidate on replay')):
                self.assertEqual(main(['replay-tune-hphi',str(final_path)]),0)
            changed=deepcopy(final);changed['trials'][3]['identity_recovery']['anchor_trial_index']=0
            with self.assertRaisesRegex(ValueError,'checkpoint differs'):replay_hphi_tune(changed)
            changed=deepcopy(final);changed['request']['identity_recovery']['anchor_selection']='fixed_trial'
            changed['request']['identity_recovery']['anchor_trial_index']=0
            with self.assertRaises(ValueError):replay_hphi_tune(changed)
            self.assertEqual(before,{p:Path(p).read_bytes() for p in before})
            (root/'accepted.json').write_text(json.dumps(dict(status='PASS',job=identifier,
                checkpoint=str(final_path),request=q,decision=final['decision'],native_files_unchanged=len(before)),indent=2)+'\n')

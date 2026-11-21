# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import numpy as np
from test_planar_curved_tuning import small_request,workspace


class PlanarCurvedOwnedTuningTests(unittest.TestCase):
    def test_original_native_scale_and_portable_owner_survive_source_removal(self):
        from superfish_ng.planar_curved_tuning_saved import execute_owned_planar_curved_tune,read_owned_planar_curved_tune
        raw=small_request()
        with workspace('owned-scale') as root:
            first=execute_owned_planar_curved_tune(raw,root/'first',max_new_trials=1)
            original={p.relative_to(root/'first/trial-001').as_posix():p.read_bytes()
                for p in (root/'first/trial-001').rglob('*') if p.is_file()}
            second=execute_owned_planar_curved_tune(raw,root/'second',checkpoint=first,max_new_trials=1)
            self.assertEqual(second['status'],'PAUSED')
            self.assertAlmostEqual(second['trials'][0]['frequency_hz']/second['trials'][1]['frequency_hz'],1.4,places=10)
            for relative,data in original.items():self.assertEqual((root/'second/trial-001'/relative).read_bytes(),data)
            portable=json.loads((root/'second/checkpoint-002.json').read_text())
            self.assertEqual(portable['trial_runs'],['trial-001','trial-002'])
            (root/'first').rename(root/'original-unavailable')
            (root/'second').rename(root/'relocated')
            with patch('superfish_ng.planar_curved_tuning_saved.execute_planar_project',side_effect=AssertionError('replay solved')):
                moved=read_owned_planar_curved_tune(root/'relocated/checkpoint-002.json')
            self.assertEqual(moved['trials'],second['trials'])
            self.assertEqual(moved['trial_sources_sha256'],second['trial_sources_sha256'])
            self.assertEqual(moved['trial_runs'],[str(root/'relocated'/f'trial-{i:03d}') for i in (1,2)])

    def test_failed_new_solve_keeps_zero_or_completed_owned_prefix(self):
        from superfish_ng.planar_curved_tuning_saved import execute_owned_planar_curved_tune,read_owned_planar_curved_tune
        raw=small_request()
        with workspace('failed-owned') as root:
            first=execute_owned_planar_curved_tune(raw,root/'first',max_new_trials=1)
            before={str(p):p.read_bytes() for p in (root/'first').rglob('*') if p.is_file()}
            for name,prefix in (('initial',None),('continued',first)):
                with patch('superfish_ng.planar_curved_tuning_saved.execute_planar_project',side_effect=RuntimeError('new trial failed')):
                    with self.assertRaisesRegex(RuntimeError,'new trial failed'):
                        execute_owned_planar_curved_tune(raw,root/name,checkpoint=prefix)
                count=0 if prefix is None else 1
                saved=root/name/f'checkpoint-{count:03d}.json'
                replay=read_owned_planar_curved_tune(saved)
                self.assertEqual(replay['trials'],[] if prefix is None else first['trials'])
                self.assertTrue(replay['can_resume'])
                failure=json.loads((root/name/f'failure-{count+1:03d}.json').read_text())
                self.assertEqual(failure['preceding_trial_runs'],[] if count==0 else ['trial-001'])
                self.assertNotIn('frequency_hz',failure)
            for path,data in before.items():self.assertEqual(Path(path).read_bytes(),data)
            (root/'first').rename(root/'original-unavailable')
            resumed=execute_owned_planar_curved_tune(raw,root/'resumed',
                checkpoint=root/'continued/checkpoint-001.json',max_new_trials=1)
            self.assertEqual(len(resumed['trials']),2)
            self.assertEqual(resumed['trials'][0],first['trials'][0])

    def test_strict_owner_paths_request_claim_and_report_tampering(self):
        from superfish_ng.planar_curved_tuning_saved import execute_owned_planar_curved_tune,read_owned_planar_curved_tune,replay_owned_planar_curved_tune
        raw=small_request()
        with workspace('strict-owned') as root:
            report=execute_owned_planar_curved_tune(raw,root/'owner',max_new_trials=1)
            for field,value in (('schema_version',True),('can_resume',1),('extra',0),
                    ('trial_runs',None),('trial_runs',['../owner/trial-001']),('trial_runs',['trial-001/']),
                    ('trial_runs',['execution/trial-001']),('trial_runs',['trial-002'])):
                bad=deepcopy(report);bad[field]=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                    replay_owned_planar_curved_tune(bad,base_directory=root/'owner')
            alias=root/'alias';alias.symlink_to(root/'owner',target_is_directory=True)
            with self.assertRaises(ValueError):read_owned_planar_curved_tune(alias/'checkpoint-001.json')
            output_alias=root/'output-alias';output_alias.symlink_to(root/'output',target_is_directory=True)
            with self.assertRaises(ValueError):execute_owned_planar_curved_tune(raw,output_alias)
            request_file=root/'owner/request.json';before=request_file.read_bytes()
            changed=deepcopy(raw);changed['target_hz']*=2
            request_file.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'request copy'):replay_owned_planar_curved_tune(report)
            request_file.write_bytes(before)
            for relative in ('worker.claim','solution/fields.npz'):
                file=root/'owner/trial-001'/relative;data=file.read_bytes();file.write_bytes(data+b'changed')
                with self.assertRaisesRegex(ValueError,'source hashes'):replay_owned_planar_curved_tune(report)
                file.write_bytes(data)
            extra=root/'owner/trial-001/undeclared.txt';extra.write_text('unexpected')
            with self.assertRaisesRegex(ValueError,'exactly'):replay_owned_planar_curved_tune(report)
            extra.unlink()
            bad=deepcopy(report);bad['trials'][0]['frequency_hz']+=1
            with self.assertRaisesRegex(ValueError,'complete original native replay'):replay_owned_planar_curved_tune(bad)
            with self.assertRaisesRegex(ValueError,'request differs'):
                execute_owned_planar_curved_tune(changed,root/'rejected',checkpoint=report)
            self.assertFalse((root/'rejected').exists())
            with self.assertRaises(FileExistsError):execute_owned_planar_curved_tune(raw,root/'owner')

    def test_raw_multi_directory_prefix_import_is_explicit_and_byte_exact(self):
        from superfish_ng.planar_curved_tuning import execute_planar_curved_tune
        from superfish_ng.planar_curved_tuning_saved import execute_owned_planar_curved_tune,import_owned_planar_curved_tune,read_owned_planar_curved_tune
        raw=small_request()
        with workspace('raw-import') as root:
            first=execute_planar_curved_tune(raw,root/'first',max_new_trials=1)
            second=execute_planar_curved_tune(raw,root/'second',checkpoint=first,max_new_trials=1)
            before=[{p.relative_to(Path(run)).as_posix():p.read_bytes() for p in Path(run).rglob('*') if p.is_file()}
                for run in second['trial_runs']]
            with self.assertRaisesRegex(ValueError,'expected owned'):
                execute_owned_planar_curved_tune(raw,root/'implicit',checkpoint=second)
            self.assertFalse((root/'implicit').exists())
            with patch('superfish_ng.planar_curved_tuning_saved.execute_planar_project',side_effect=AssertionError('import solved')):
                owned=import_owned_planar_curved_tune(root/'second/checkpoint-002.json',root/'imported')
            self.assertEqual(owned['trials'],second['trials'])
            for run,files in zip(owned['trial_runs'],before):
                for relative,data in files.items():self.assertEqual((Path(run)/relative).read_bytes(),data)
            (root/'first').rename(root/'first-unavailable');(root/'second').rename(root/'second-unavailable')
            (root/'imported').rename(root/'moved')
            replay=read_owned_planar_curved_tune(root/'moved/checkpoint-002.json')
            self.assertEqual(replay['trials'],second['trials'])
            recopied=import_owned_planar_curved_tune(root/'moved/checkpoint-002.json',root/'recopied')
            self.assertEqual(recopied['trials'],replay['trials'])
            self.assertEqual(recopied['trial_sources_sha256'],replay['trial_sources_sha256'])

    def test_terminal_true_doublet_cannot_resume_into_a_new_owner(self):
        from superfish_ng.planar_curved_tuning_saved import execute_owned_planar_curved_tune
        raw=small_request('te')
        with workspace('terminal-owned') as root:
            terminal=execute_owned_planar_curved_tune(raw,root/'terminal')
            self.assertEqual(terminal['status'],'UNVERIFIED')
            self.assertIsNone(terminal['trials'][0]['frequency_hz'])
            with self.assertRaisesRegex(ValueError,'only a verified PAUSED'):
                execute_owned_planar_curved_tune(raw,root/'rejected',checkpoint=terminal)
            self.assertFalse((root/'rejected').exists())

    def test_rehashed_native_energy_or_rebound_law_still_require_physical_replay(self):
        from superfish_ng.planar_curved_tuning_saved import execute_owned_planar_curved_tune,read_owned_planar_curved_tune
        from test_planar_piecewise_tuning import rehash_trial,save
        raw=small_request()
        with workspace('rehashed-owned') as root:
            first=execute_owned_planar_curved_tune(raw,root/'original',max_new_trials=1)
            for kind in ('energy','law'):
                owner=root/kind;shutil.copytree(root/'original',owner)
                path=owner/'checkpoint-001.json';document=json.loads(path.read_text())
                if kind=='energy':
                    fields=owner/'trial-001/solution/fields.npz'
                    with np.load(fields) as archive:data={key:archive[key].copy() for key in archive.files}
                    original=data['coefficients'].copy();data['coefficients']*=1.01
                    # Eigenvector amplitude changes U' by 1.0201 while f and
                    # algebraic eigenspace remain identical; hashes are no proof.
                    np.testing.assert_allclose(np.sum(data['coefficients']**2,axis=0)/np.sum(original**2,axis=0),1.0201,rtol=1e-13)
                    np.savez_compressed(fields,**data);rehash_trial(owner,document,0)
                else:
                    document['request']['shape_law']['shape_law']['linear_xy_coefficients'][0][0][1]=1.01
                    save(owner/'request.json',document['request'])
                save(path,document)
                with self.subTest(kind=kind),self.assertRaises(ValueError):read_owned_planar_curved_tune(path)
            self.assertEqual(read_owned_planar_curved_tune(root/'original/checkpoint-001.json'),first)

    def test_actual_accepted_circle_and_recovered_ellipse_import_move_and_replay(self):
        from superfish_ng.planar_curved_tuning_saved import import_owned_planar_curved_tune,read_owned_planar_curved_tune
        evidence=os.environ.get('SUPERFISH_CURVED_OWNED_ACCEPTED_ROOT')
        if not evidence:self.skipTest('dedicated accepted circle/TE native evidence root required')
        with workspace('accepted-native') as root:
            for name,relative in [('circle','initial-acceptance/circle/rest/checkpoint-004.json'),
                                  ('ellipse','te-acceptance/ellipse/run/checkpoint-003.json')]:
                source=Path(evidence)/relative
                raw=json.loads(source.read_text())
                before=[{p.relative_to(Path(run)).as_posix():p.read_bytes() for p in Path(run).rglob('*') if p.is_file()}
                    for run in raw['trial_runs']]
                with patch('superfish_ng.planar_curved_tuning_saved.execute_planar_project',side_effect=AssertionError('import solved')):
                    owned=import_owned_planar_curved_tune(source,root/name)
                    self.assertEqual(owned['status'],'TUNED')
                    self.assertEqual(owned['trials'],raw['trials'])
                    for run,files in zip(owned['trial_runs'],before):
                        for relative,data in files.items():self.assertEqual((Path(run)/relative).read_bytes(),data)
                    moved=root/f'{name}-moved';(root/name).rename(moved)
                    replay=read_owned_planar_curved_tune(moved/f'checkpoint-{len(before):03d}.json')
                    self.assertEqual(replay['trials'],raw['trials'])
                    self.assertEqual(replay['status'],'TUNED')
                    if name=='ellipse':
                        self.assertEqual(replay['trials'][-1]['identity_recovery']['anchor_trial_index'],0)
                        self.assertEqual(replay['trials'][-1]['current_mode_ids'],['odd-x','even-x'])
                    self.assertFalse(replay['can_resume'])

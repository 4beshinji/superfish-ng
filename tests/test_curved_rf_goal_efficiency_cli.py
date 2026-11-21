# SPDX-License-Identifier: Apache-2.0
"""Dedicated command transport: terminal costs, failures and exclusive output."""
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('rf_goal_cli', ROOT/'scripts/run_curved_rf_goal_efficiency.py')
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


class RFGoalCommandTests(unittest.TestCase):
    def test_unknown_row_and_existing_output_fail_before_process(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(cli, 'run_measured_process') as process:
            out = Path(tmp)/'new'
            with self.assertRaises(ValueError):cli.run_invocation(cli.fresh_invocation('unknown'), out)
            row = cli.build_curved_rf_goal_efficiency_plan()['executions'][0]
            for archives in ([], False, 'archive'):
                with self.assertRaises(ValueError):cli.fresh_invocation(row['id'], source_archives=archives)
            with self.assertRaises(FileExistsError):cli.run_invocation(cli.fresh_invocation(row['id']), Path(tmp))
            process.assert_not_called()
            self.assertFalse(out.exists())

    def test_invocation_hash_duplicate_keys_and_unknown_fields_fail_before_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'invocation.json'
            path.write_text('{"action":"run","action":"resume"}')
            with self.assertRaises(ValueError):cli.read_invocation(path, cli.digest(path))
            path.write_text('{}')
            with self.assertRaises(ValueError):cli.read_invocation(path, '0'*64)
            row = cli.build_curved_rf_goal_efficiency_plan()['executions'][0]
            value = cli.fresh_invocation(row['id']);value['unknown'] = 1
            with self.assertRaises(ValueError):cli.validate_invocation(value)
            for limit in (True, 0, 1.5):
                value = cli.fresh_invocation(row['id']);value['max_new_events'] = limit
                with self.assertRaises(ValueError):cli.validate_invocation(value)

    def test_outer_receipt_covers_result_write_and_preserves_write_exception(self):
        from superfish_ng import curved_rf_goal_efficiency_worker as worker
        row = cli.build_curved_rf_goal_efficiency_plan()['executions'][0]
        invocation = cli.fresh_invocation(row['id'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);path = root/'invocation.json'
            cli.publish_rf_goal_json(path, invocation)
            def execute(execution, directory, **kwargs):
                directory.mkdir()
                worker._write(directory/'result.json', dict(status='PAUSED'))
                return dict(status='PAUSED')
            original = worker._write
            with patch.object(cli, 'execute_curved_rf_goal_efficiency_worker', side_effect=execute):
                cli.worker_command(path, cli.digest(path), root/'native', None)
            receipt = json.loads((root/'worker-terminal.json').read_text())
            self.assertEqual(receipt['status'], 'RETURNED')
            self.assertEqual(receipt['result_publication']['status'], 'COMPLETED')
            self.assertGreaterEqual(receipt['invocation_wall_seconds'], receipt['result_publication']['wall_seconds'])
            self.assertIs(worker._write, original)
            (root/'worker-terminal.json').unlink()
            error = OSError('disk full')
            with patch.object(cli, 'execute_curved_rf_goal_efficiency_worker', side_effect=execute), patch.object(worker, '_write', side_effect=error) as writer:
                with self.assertRaises(OSError) as caught:cli.worker_command(path, cli.digest(path), root/'other-native', None)
                self.assertIs(caught.exception, error)
                self.assertIs(worker._write, writer)
            receipt = json.loads((root/'worker-terminal.json').read_text())
            self.assertEqual(receipt['status'], 'FAILED')
            self.assertEqual(receipt['result_publication']['status'], 'FAILED')
            self.assertEqual(receipt['exception_type'], 'OSError')

    def test_manifest_keeps_failed_process_partial_bytes_and_detects_additions(self):
        row = cli.build_curved_rf_goal_efficiency_plan()['executions'][0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'new'
            def fail(argv, out, **kwargs):
                out.mkdir();(out/'stderr.log').write_text('actual failure')
                (root/'native').mkdir();(root/'native'/'.partial').write_bytes(b'{')
                result = dict(status='PROCESS_FAILED', exit_code=7, wall_seconds=.2, peak_rss_bytes=100)
                cli.publish_rf_goal_json(out/'process.json', result)
                return result
            with patch.object(cli, 'run_measured_process', side_effect=fail):
                manifest = cli.run_invocation(cli.fresh_invocation(row['id']), root)
            self.assertEqual(manifest['status'], 'PROCESS_FAILED')
            self.assertIsNone(manifest['numerical_status'])
            self.assertIsNone(manifest['physical_error_bound'])
            self.assertIn('native/.partial', manifest['files'])
            cli.verify_bundle(root/'manifest.json', cli.digest(root/'manifest.json'))
            (root/'unrecorded').write_text('new')
            with self.assertRaises(ValueError):cli.verify_bundle(root/'manifest.json', cli.digest(root/'manifest.json'))

    def test_source_change_and_zero_exit_without_result_are_not_accepted(self):
        row = cli.build_curved_rf_goal_efficiency_plan()['executions'][0]
        with tempfile.TemporaryDirectory() as tmp:
            def exited(argv, out, **kwargs):
                out.mkdir();receipt = dict(status='PROCESS_EXITED', exit_code=0, wall_seconds=.1, peak_rss_bytes=100)
                cli.publish_rf_goal_json(out/'process.json', receipt)
                return receipt
            with patch.object(cli, 'run_measured_process', side_effect=exited), patch.object(cli, 'source_hashes', side_effect=[{'a':'old'}, {'a':'new'}]):
                manifest = cli.run_invocation(cli.fresh_invocation(row['id']), Path(tmp)/'new')
            self.assertEqual(manifest['status'], 'SOURCE_CHANGED')
            self.assertEqual(manifest['source_audit']['changed'], ['a'])
            self.assertIsNone(manifest['numerical_status'])
            with patch.object(cli, 'run_measured_process', side_effect=exited):
                manifest = cli.run_invocation(cli.fresh_invocation(row['id']), Path(tmp)/'missing')
            self.assertEqual(manifest['status'], 'WORKER_RESULT_MISSING')

    def test_replay_command_preserves_verification_and_exclusive_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = dict(status='FULL_NATIVE_FIELDS_AND_DECISIONS_REPLAYED', new_eigensolves=0)
            out = Path(tmp)/'report.json'
            with patch.object(cli, 'read_curved_rf_goal_efficiency', return_value=report) as replay, redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(['replay','--journal','/original','--sha256','0'*64,'--out',str(out)]), 0)
                self.assertEqual(json.loads(out.read_text()), report)
                with self.assertRaises(FileExistsError):cli.main(['replay','--journal','/original','--sha256','0'*64,'--out',str(out)])
                self.assertEqual(replay.call_count, 1)

    def test_success_requires_final_write_coverage_and_missing_receipt_remains_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);process = dict(status='PROCESS_EXITED', exit_code=0, wall_seconds=3.)
            self.assertEqual(cli.bundle_state(root, process, {}, False), 'WORKER_RECEIPT_MISSING')
            receipt = dict(schema_version=1, document_type='curved_rf_goal_efficiency_worker_terminal',
                status='RETURNED', exception_type=None, invocation_wall_seconds=2., submission_wall_seconds=2.5,
                result_publication=dict(status='COMPLETED', wall_seconds=1.))
            path = root/'worker-terminal.json';path.write_text(json.dumps(receipt))
            self.assertEqual(cli.bundle_state(root, process, {}, False), 'PROCESS_EXITED')
            for field, value in (('wall_seconds',4.), ('wall_seconds',True), ('status','FAILED')):
                bad = deepcopy(receipt);bad['result_publication'][field] = value
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):cli.bundle_state(root, process, {}, False)


if __name__ == '__main__':unittest.main()

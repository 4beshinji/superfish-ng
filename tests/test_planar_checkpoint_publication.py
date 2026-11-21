# SPDX-License-Identifier: Apache-2.0
"""A visible checkpoint is complete even when its producer is interrupted."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from superfish_ng.planar_tuning_saved import _write


class PlanarCheckpointPublicationTests(unittest.TestCase):
    def test_interrupted_serialization_never_publishes_partial_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'checkpoint-001.json'
            def interrupted(document, stream, **options):
                stream.write('{"trials": ['); stream.flush()
                self.assertFalse(target.exists(), 'partial JSON became publicly visible')
                raise KeyboardInterrupt('producer interrupted before publication')
            with patch('superfish_ng.planar_tuning_saved.json.dump', side_effect=interrupted):
                with self.assertRaises(KeyboardInterrupt):
                    _write(target, {'trials': [1]})
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_complete_payload_is_exact_and_refuses_existing_target(self):
        document = {'name': '元の場', 'trials': list(range(1000))}
        expected = (json.dumps(document, indent=2, allow_nan=False)+'\n').encode()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'checkpoint-001.json'
            _write(target, document)
            self.assertEqual(target.read_bytes(), expected)
            self.assertEqual(json.loads(target.read_bytes()), document)
            with self.assertRaises(FileExistsError):
                _write(target, {'replacement': True})
            self.assertEqual(target.read_bytes(), expected)
            self.assertEqual(list(Path(directory).iterdir()), [target])

    def test_nonfinite_serialization_leaves_no_public_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'checkpoint-001.json'
            with self.assertRaises(ValueError):
                _write(target, {'partial': 1, 'invalid': float('nan')})
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_killed_producer_cannot_leave_a_visible_partial_checkpoint(self):
        import subprocess
        import sys
        code = '''
import json, sys, time
from pathlib import Path
from superfish_ng.planar_tuning_saved import _write

def paused_dump(document, stream, **options):
    stream.write('{"trials": ['); stream.flush()
    Path(sys.argv[2]).write_text('partial serialization reached')
    time.sleep(60)
json.dump = paused_dump
_write(Path(sys.argv[1]), {'trials': [1]})
'''
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'checkpoint-001.json'
            marker = Path(directory)/'producer-ready'
            process = subprocess.Popen([sys.executable, '-c', code, str(target), str(marker)])
            try:
                import time
                deadline = time.monotonic()+10
                while not marker.exists() and time.monotonic() < deadline:
                    self.assertIsNone(process.poll())
                    time.sleep(.01)
                self.assertTrue(marker.exists())
                process.kill(); process.wait(timeout=10)
                self.assertFalse(target.exists(), 'killed producer left a published partial checkpoint')
            finally:
                if process.poll() is None:
                    process.kill(); process.wait(timeout=10)

    def test_legacy_failure_payload_preserves_absent_trailing_newline(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'failure-001.json'
            document = {'status': 'FAILED', 'error': '元の診断'}
            _write(target, document, trailing_newline=False)
            self.assertEqual(target.read_bytes(), json.dumps(document, indent=2, allow_nan=False).encode())

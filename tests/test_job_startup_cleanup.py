# SPDX-License-Identifier: Apache-2.0
"""A failed application startup must relinquish its OS workspace lock."""
import fcntl
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from superfish_ng.jobs import JobManager
from superfish_ng.gui import create_server, serve


class JobStartupCleanupTests(unittest.TestCase):
    def assert_workspace_released(self, root):
        # Open a separate file description: the kernel, not manager state,
        # decides whether this workspace can be acquired immediately.
        with (root / '.manager.lock').open('a+') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def capture_failure(self, action, expected):
        try:
            action()
        except expected as error:
            # Keep the actual traceback alive so garbage collection cannot
            # hide a leaked descriptor from an unsuccessful constructor.
            return error
        self.fail('startup should have failed')

    def test_live_manager_keeps_exclusive_ownership_until_close(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = JobManager(root)
            try:
                with self.assertRaises(BlockingIOError):
                    self.assert_workspace_released(root)
                with self.assertRaisesRegex(ValueError, 'running application'):
                    JobManager(root)
                with self.assertRaises(BlockingIOError):
                    self.assert_workspace_released(root)
            finally:
                manager.close()
            manager.close()
            self.assert_workspace_released(root)

    def test_invalid_saved_state_releases_lock_without_modifying_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = root / 'broken'
            job.mkdir()
            state = job / 'job.json'
            state.write_text('{invalid json')
            error = self.capture_failure(lambda: JobManager(root), json.JSONDecodeError)
            self.assertEqual(state.read_text(), '{invalid json')
            self.assert_workspace_released(root)
            state.write_text('{"status":"cancelled"}')
            manager = JobManager(root)
            manager.close()
            self.assertIsNotNone(error.__traceback__)

    def test_failed_recovery_and_interrupt_release_lock(self):
        for failure in (OSError('recovery write denied'), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                job = root / 'pending'
                job.mkdir()
                state = job / 'job.json'
                original = '{"status":"running","kind":"planar_solve"}'
                state.write_text(original)
                with patch('superfish_ng.jobs._state', side_effect=failure):
                    error = self.capture_failure(lambda: JobManager(root), type(failure))
                self.assertEqual(state.read_text(), original)
                self.assert_workspace_released(root)
                manager = JobManager(root)
                try:
                    self.assertEqual(manager.status('pending')['status'], 'interrupted')
                    self.assertEqual(manager.status('pending')['kind'], 'planar_solve')
                finally:
                    manager.close()
                self.assertIsNotNone(error.__traceback__)

    @patch('importlib.util.find_spec', return_value=True)
    def test_gui_cache_and_server_failure_release_lock(self, _plot_extra):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / '.plot-cache'
            cache.write_text('user-owned file')
            error = self.capture_failure(lambda: create_server(root), FileExistsError)
            self.assertEqual(cache.read_text(), 'user-owned file')
            self.assert_workspace_released(root)
            self.assertIsNotNone(error.__traceback__)
            cache.unlink()
            for failure in (OSError('address unavailable'), KeyboardInterrupt()):
                with self.subTest(failure=type(failure).__name__):
                    with patch('superfish_ng.gui.ThreadingHTTPServer', side_effect=failure):
                        error = self.capture_failure(lambda: create_server(root), type(failure))
                    self.assert_workspace_released(root)
                    self.assertIsNotNone(error.__traceback__)

    def test_browser_failure_closes_server_and_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = JobManager(root)
            from unittest.mock import Mock
            server = Mock(manager=manager, launch_url='http://127.0.0.1:1/#local')
            with patch('superfish_ng.gui.create_server', return_value=server), patch(
                'superfish_ng.gui.webbrowser.open', side_effect=OSError('browser unavailable')
            ), patch('builtins.print'):
                error = self.capture_failure(lambda: serve(root), OSError)
            server.server_close.assert_called_once_with()
            server.serve_forever.assert_not_called()
            self.assert_workspace_released(root)
            self.assertIsNotNone(error.__traceback__)
            manager.close()

    def test_server_close_error_still_releases_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = JobManager(root)
            from unittest.mock import Mock
            server = Mock(manager=manager, launch_url='http://127.0.0.1:1/#local')
            server.serve_forever.side_effect = KeyboardInterrupt()
            server.server_close.side_effect = OSError('socket close failed')
            with patch('superfish_ng.gui.create_server', return_value=server), patch('builtins.print'):
                error = self.capture_failure(lambda: serve(root, open_browser=False), OSError)
            self.assertEqual(str(error), 'socket close failed')
            self.assert_workspace_released(root)
            manager.close()


if __name__ == '__main__':
    unittest.main()

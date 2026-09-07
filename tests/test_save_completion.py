# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from superfish_ng import Case, solve
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution


class SaveCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = Case(((0., .1), (.2, .1)), nr=4, nz=5, modes=2)
        cls.solution = solve(cls.case)

    def test_failure_after_fields_never_reads_as_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'run'
            with patch('superfish_ng.io.write_vtk', side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):
                    save_run(self.case, self.solution, out)
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                read_solution(out)
            self.assertFalse((out/'save_complete.json').exists())
            with self.assertRaises(FileExistsError):
                save_run(self.case, self.solution, out)

    def test_publication_failure_and_preexisting_file_are_not_overwritten(self):
        import os
        real_link = os.link
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'run'
            def collision(source, target, *args, **kwargs):
                if Path(target).name == 'fields.npz':
                    Path(target).write_bytes(b'user content')
                return real_link(source, target, *args, **kwargs)
            with patch('superfish_ng.io.os.link', side_effect=collision):
                with self.assertRaises(FileExistsError):
                    save_run(self.case, self.solution, out)
            self.assertEqual((out/'fields.npz').read_bytes(), b'user content')
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                read_solution(out)

    def test_missing_completion_or_required_entry_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'run'
            save_run(self.case, self.solution, out)
            marker = out/'save_complete.json'
            original = marker.read_text()
            report = json.loads(marker.read_text())
            del report['files']['mode_002.vtk']
            marker.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'required'):
                read_solution(out)
            report = json.loads(original)
            report['files']['../outside'] = '0'*64
            marker.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'required'):
                read_solution(out)
            marker.write_text(original)
            (out/'mode_001.vtk').unlink()
            (out/'mode_001.vtk').symlink_to(out/'mode_002.vtk')
            with self.assertRaisesRegex(ValueError, 'disagree'):
                read_solution(out)
            marker.unlink()
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                read_solution(out)

    def test_existing_directory_and_symlink_are_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'run'; out.mkdir()
            (out/'mine').write_text('preserve')
            alias = Path(tmp)/'alias'; alias.symlink_to(out, target_is_directory=True)
            for path in [out, alias]:
                with self.assertRaises(FileExistsError):
                    save_run(self.case, self.solution, path)
            self.assertEqual(list(out.iterdir()), [out/'mine'])

    def test_legacy_read_and_new_byte_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'run'
            expected = save_run(self.case, self.solution, out)
            self.assertEqual(read_solution(out).results['modes'], expected['modes'])
            original_csv = (out/'modes.csv').read_bytes()
            (out/'modes.csv').write_text('damaged')
            with self.assertRaisesRegex(ValueError, 'disagree'):
                read_solution(out)
            # Recreate pre-protocol file layout; old structural checks remain.
            (out/'modes.csv').write_bytes(original_csv)
            (out/'save_protocol.json').unlink(); (out/'save_complete.json').unlink()
            expected.pop('save_protocol_version')
            (out/'results.json').write_text(json.dumps(expected))
            self.assertEqual(read_solution(out).case, self.case)

    def test_real_process_death_leaves_unreadable_partial_result(self):
        code = '''
import os, signal, sys
from superfish_ng import Case,solve
import superfish_ng.io as output
c=Case(((0.,.1),(.2,.1)),nr=4,nz=5,modes=1)
def stop(*args): os.kill(os.getpid(), signal.SIGKILL)
output.write_vtk=stop
output.save_run(c,solve(c),sys.argv[1])
'''
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'run'
            result = subprocess.run([sys.executable, '-c', code, str(out)], capture_output=True, timeout=30)
            self.assertLess(result.returncode, 0)
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                read_solution(out)

    def test_failure_at_each_file_stage_and_completion_publication(self):
        from superfish_ng.mesh_input import mesh_to_dict
        solution = solve(self.case, mesh_data=mesh_to_dict(self.solution.mesh))
        original_open = Path.open
        for filename in ['save_protocol.json', 'mesh.json', 'case.json', 'results.json',
                         'mode_001.vtk', 'modes.csv', 'save_complete.json']:
            with self.subTest(file=filename), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)/'run'
                def fail(path, *args, **kwargs):
                    if path.name == filename:
                        raise OSError('injected output failure')
                    return original_open(path, *args, **kwargs)
                with patch.object(Path, 'open', fail):
                    with self.assertRaises(OSError):
                        save_run(self.case, solution, out)
                with self.assertRaisesRegex(ValueError, 'incomplete'):
                    read_solution(out)
        for function in ['np.savez_compressed', 'np.savetxt']:
            with self.subTest(function=function), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)/'run'
                with patch('superfish_ng.io.'+function, side_effect=OSError('injected output failure')):
                    with self.assertRaises(OSError):
                        save_run(self.case, solution, out)
                with self.assertRaisesRegex(ValueError, 'incomplete'):
                    read_solution(out)

    def test_readers_refuse_until_publication_and_concurrent_writer_loses(self):
        import os
        from concurrent.futures import ThreadPoolExecutor
        original_link = os.link
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'run'
            def observe(source, target):
                with self.assertRaisesRegex(ValueError, 'incomplete'):
                    read_solution(out)
                return original_link(source, target)
            def save():
                try:
                    save_run(self.case, self.solution, out)
                    return 'complete'
                except FileExistsError:
                    return 'lost race'
            with patch('superfish_ng.io.os.link', side_effect=observe), ThreadPoolExecutor(2) as pool:
                futures = [pool.submit(save), pool.submit(save)]
                self.assertEqual(sorted(f.result() for f in futures), ['complete', 'lost race'])
            self.assertEqual(read_solution(out).case, self.case)

    def test_external_mesh_import_preserves_completion_and_avoids_solve(self):
        import shutil
        from superfish_ng.mesh_input import mesh_to_dict
        from superfish_ng.jobs import JobManager
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'source'
            solution = solve(self.case, mesh_data=mesh_to_dict(self.solution.mesh))
            save_run(self.case, solution, source)
            manager = JobManager(Path(tmp)/'workspace')
            try:
                original_copy = shutil.copyfile
                def copy_before_completion(source, target):
                    self.assertFalse((Path(target).parent/'save_complete.json').exists())
                    return original_copy(source, target)
                with patch('superfish_ng.jobs.solve', side_effect=AssertionError('must not solve')), \
                        patch('shutil.copyfile', side_effect=copy_before_completion):
                    identifier = manager.import_result(source)
                self.assertEqual(manager.status(identifier)['source_completion'], 'verified direct-save completion')
                copied = manager.directory(identifier)/'solution'
                self.assertEqual(read_solution(copied).case, self.case)
                self.assertEqual((copied/'mesh.json').read_bytes(), (source/'mesh.json').read_bytes())
            finally:
                manager.close()

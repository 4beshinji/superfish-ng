# SPDX-License-Identifier: Apache-2.0
"""Distribution boundary tests use synthetic fixtures, never legacy assets."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('package_script', Path(__file__).resolve().parents[1] / 'scripts/package.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class PackageTests(unittest.TestCase):
    def test_archive_contains_only_project_and_has_valid_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'workspace'
            (root / 'src' / 'superfish_ng').mkdir(parents=True)
            (root / 'src' / 'superfish_ng' / '__init__.py').write_text('# fixture\n')
            (root / 'README.md').write_text('project\n')
            (root / 'private-notes.txt').write_text('private\n')
            (root / 'SUPERFISH').mkdir()
            (root / 'SUPERFISH' / 'fixture.txt').write_text('excluded fixture\n')
            (root / '.wine-superfish').symlink_to(root / 'SUPERFISH', target_is_directory=True)
            out = Path(directory) / 'project.zip'
            with patch.object(package, 'ROOT', root), patch('sys.argv', ['package.py', '--out', str(out)]):
                package.main()
            with zipfile.ZipFile(out) as archive:
                self.assertEqual(set(archive.namelist()), {
                    'superfish-ng/README.md', 'superfish-ng/src/superfish_ng/__init__.py',
                    'superfish-ng/MANIFEST.sha256',
                })
                manifest = archive.read('superfish-ng/MANIFEST.sha256').decode()
                for line in manifest.splitlines():
                    digest, name = line.split('  ', 1)
                    self.assertEqual(digest, package.hashlib.sha256(archive.read('superfish-ng/' + name)).hexdigest())

    def test_project_symlinks_rejected_including_directory_and_dangling_links(self):
        for relative, target_is_directory in [('src', True), ('src/link', True), ('src/file.py', False)]:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                link = root / relative
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(root / 'missing-target', target_is_directory=target_is_directory)
                with self.assertRaisesRegex(ValueError, 'symlink is not permitted'):
                    list(package.project_files(root))

    def test_caches_and_generated_files_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ['src/__pycache__/cached.pyc', 'src/project.egg-info/PKG-INFO', 'out/result.json', 'scripts/generated.zip']:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture')
            self.assertEqual(list(package.project_files(root)), [])


if __name__ == '__main__':
    unittest.main()

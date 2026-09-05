# SPDX-License-Identifier: Apache-2.0
"""Create a portable deterministic ZIP with a file SHA-256 manifest.

Use --out outside this repository. Reproduction requires identical file bytes
and compatible zlib; this is a content snapshot, not a signed release.
"""
import argparse
import hashlib
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git','.venv','__pycache__','build','dist','out','.pytest_cache','validation-ci'}
PROJECT_FILES = {
    '.gitignore', '.python-version', 'AGENTS.md', 'CHANGELOG.md', 'CONTRIBUTING.md',
    'LICENSE', 'MANIFEST.in', 'NOTICE', 'README.md', 'pyproject.toml',
    'requirements-reproduce.txt',
}
PROJECT_DIRS = {'.github', 'benchmarks', 'docs', 'examples', 'scripts', 'src', 'tests'}


def project_files(root):
    """Only traverse project directories; never read adjacent user assets or links."""
    for name in sorted(PROJECT_FILES | PROJECT_DIRS):
        path = root / name
        if path.is_symlink():
            raise ValueError(f'symlink is not permitted: {name}')
        if not path.exists():
            continue
        if name in PROJECT_FILES:
            if not path.is_file():
                raise ValueError(f'expected project file: {name}')
            yield path
            continue
        if not path.is_dir():
            raise ValueError(f'expected project directory: {name}')
        for directory, dirs, files in os.walk(path, followlinks=False):
            parent = Path(directory)
            for child in dirs + files:
                if (parent / child).is_symlink():
                    raise ValueError(f'symlink is not permitted: {(parent / child).relative_to(root)}')
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not d.endswith('.egg-info'))
            for filename in sorted(files):
                item = parent / filename
                if item.suffix not in {'.pyc', '.pyo', '.zip'} and filename != 'MANIFEST.sha256':
                    if not item.is_file():
                        raise ValueError(f'expected regular file: {item.relative_to(root)}')
                    yield item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error('output already exists')
    if out.is_relative_to(ROOT):
        parser.error('choose an output path outside the repository')
    entries = {}
    try:
        for p in project_files(ROOT):
            entries[p.relative_to(ROOT).as_posix()] = p.read_bytes()
    except ValueError as exc:
        parser.error(str(exc))
    manifest = ''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n' for name,data in entries.items())
    entries['MANIFEST.sha256'] = manifest.encode()
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(entries.items()):
            info = zipfile.ZipInfo('superfish-ng/'+name,date_time=(2026,9,5,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(out) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f'ZIP CRC failure: {bad}')
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_suffix(out.suffix+'.sha256').write_text(f'{digest}  {out.name}\n')
    print(f'{out}: {len(entries)} files, {out.stat().st_size} bytes, SHA256 {digest}')


if __name__ == '__main__':
    main()

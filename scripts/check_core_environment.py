# SPDX-License-Identifier: Apache-2.0
"""Check the installed core-only dependency contract, without launching HTTP."""
import argparse
import hashlib
import importlib.metadata
import importlib.resources
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='new evidence directory')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    if importlib.util.find_spec('matplotlib') is not None:
        parser.error('core-only check requires an isolated environment without Matplotlib')
    commands = []
    for name, arguments, expected in (
        ('capabilities', ['capabilities'], 0),
        ('gui-refusal', ['gui', '--no-browser', '--workspace', str(args.out/'workspace')], 2),
    ):
        result = subprocess.run([sys.executable, '-m', 'superfish_ng', *arguments],
                                capture_output=True, text=True)
        (args.out/f'{name}.stdout').write_text(result.stdout, encoding='utf-8')
        (args.out/f'{name}.stderr').write_text(result.stderr, encoding='utf-8')
        if result.returncode != expected:
            raise RuntimeError(f'{name} returned {result.returncode}, expected {expected}')
        if name == 'capabilities':
            if not isinstance(json.loads(result.stdout), dict):
                raise ValueError('capabilities must return a JSON object')
        elif 'GUI plotting requires the plot extra: uv pip install' not in result.stderr:
            raise ValueError('GUI dependency refusal must explain how to install plot')
        commands.append(dict(name=name, exit_code=result.returncode))
    if (args.out/'workspace').exists():
        raise ValueError('GUI dependency refusal must precede workspace creation')
    assets = importlib.resources.files('superfish_ng').joinpath('web')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in assets.iterdir() if p.is_file()}
    if not {'index.html', 'hphi.html', 'hphi.js', 'static.html', 'static.js'} <= hashes.keys():
        raise ValueError('installed package is missing required GUI resources')
    report = dict(passed=True, scope='core dependency/CLI refusal and installed assets; no numerical validation',
                  python=sys.version, executable=sys.executable, matplotlib=None,
                  versions={name: importlib.metadata.version(name)
                            for name in ('superfish-ng', 'numpy', 'scipy')},
                  commands=commands, web_sha256=hashes)
    (args.out/'environment.json').write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(f'PASS: core CLI, explicit GUI refusal, {len(hashes)} installed web resources')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

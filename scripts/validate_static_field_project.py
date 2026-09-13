# SPDX-License-Identifier: Apache-2.0
"""Verify static Project transport against independently accepted native FEM runs."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from superfish_ng.static_field_project import StaticFieldProject

FAMILIES = ('electrostatic', 'planar-electrostatic', 'planar-magnetostatic', 'axis-magnetostatic',
            'off-axis-magnetostatic', 'planar-recoil', 'axis-recoil', 'off-axis-recoil',
            'planar-bh', 'axis-bh', 'off-axis-bh')


def fingerprints():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src', 'tests', 'scripts', 'examples')
            for p in sorted((ROOT / folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def references(root):
    selected = []
    for family in FAMILIES:
        suffix = '-trial' if family.endswith('bh') else '-refined' if family == 'axis-recoil' else ''
        directory = root / (family + '-native-independent' + suffix + '-20260913')
        assert json.loads((directory / 'report.json').read_text())['status'] == 'PASS'
        candidates = []
        for path in sorted((directory / 'api-native').glob('*/case.json')):
            case = json.loads(path.read_text())
            geometry = case['partition']['mesh' if family == 'electrostatic' else 'geometry']
            points = geometry.get('points_xy_m', geometry.get('points_rz_m'))
            candidates.append((len(points), str(path.parent), case))
        candidates.sort(key=lambda row: (row[0], row[1]))
        chosen = []
        orders = (1,) if family.endswith('bh') else (1, 2)
        for order in orders:
            chosen.append(next(row for row in candidates if row[2]['element_order'] == order))
        # A third distinct accepted boundary/material/scale condition, without altering its mesh.
        for row in candidates:
            if row not in chosen:
                chosen.append(row)
            if len(chosen) == 3:
                break
        assert len(chosen) == 3
        selected.extend((family, Path(path), case) for _, path, case in chosen)
    assert len(selected) == 33
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic(); before = fingerprints(); selected = references(args.reference_root.resolve())
    preserved, originals, records = {}, {}, []; calls = 0
    def retain(path): preserved[str(path.relative_to(out))] = hashlib.sha256(path.read_bytes()).hexdigest()
    def cli(name, arguments, expected=0):
        nonlocal calls
        calls += 1
        result = subprocess.run([sys.executable, '-m', 'superfish_ng', 'normalize-static-project', *map(str, arguments)],
            cwd=ROOT, env={**os.environ, 'OPENBLAS_NUM_THREADS':'1', 'PYTHONPATH':str(ROOT/'src')},
            capture_output=True, text=True, timeout=120)
        (out / (name + '.stdout')).write_text(result.stdout); (out / (name + '.stderr')).write_text(result.stderr)
        assert result.returncode == expected, (name, result.returncode, result.stderr)
        return result.stdout
    for index, (family, source, original_case) in enumerate(selected):
        native = {p.name:p.read_bytes() for p in source.iterdir()}
        assert len(native) == 5
        for name, raw in native.items(): originals[str(source / name)] = hashlib.sha256(raw).hexdigest()
        module_name = family.replace('-', '_')
        model = importlib.import_module('superfish_ng.' + module_name)
        saved = importlib.import_module('superfish_ng.' + module_name + '_saved')
        solver = getattr(model, 'solve_axisymmetric_electrostatic' if family == 'electrostatic' else 'solve_' + module_name)
        reader = getattr(saved, 'read_' + module_name + '_run')
        saver = getattr(saved, 'save_' + module_name + '_run')
        result_of = getattr(saved, module_name + '_result')
        verified = reader(source)
        expected_result = json.loads(native['results.json'])
        assert result_of(verified) == expected_result
        directory = out / f'{index:02d}-{family}'; directory.mkdir()
        for unit in ('m', 'mm'):
            project = StaticFieldProject(verified.case, unit)
            api, roundtrip, from_case, from_project = [directory / (unit + '-' + name + '.json')
                for name in ('api', 'roundtrip', 'cli-case', 'cli-project')]
            project.save(api); loaded = StaticFieldProject.load(api); loaded.save(roundtrip)
            assert loaded.case.to_dict() == original_case and roundtrip.read_bytes() == api.read_bytes()
            output = cli(f'{index}-{unit}-case', [source/'case.json', '--out', from_case, '--display-length-unit', unit])
            assert output.encode() == api.read_bytes() == from_case.read_bytes()
            output = cli(f'{index}-{unit}-project', [api, '--out', from_project])
            assert output.encode() == api.read_bytes() == from_project.read_bytes()
            actual = solver(loaded.case)
            assert result_of(actual) == expected_result
            target = directory / (unit + '-native'); saver(loaded.case, actual, target)
            actual_native = {p.name:p.read_bytes() for p in target.iterdir()}
            assert actual_native == native, (family, source.name, unit, [n for n in native if actual_native.get(n) != native[n]])
            for path in [api, roundtrip, from_case, from_project, *target.iterdir()]: retain(path)
            records.append(dict(family=family, source=str(source), element_order=original_case['element_order'],
                                display_length_unit=unit, full_case_unchanged=True, full_fem_result_identical=True,
                                all_five_native_files_identical=True, api_cli_json_and_bytes_identical=True))
        print('DONE', index, family, source.name, flush=True)
    last = out / f'{len(selected)-1:02d}-{selected[-1][0]}'
    cli('overwrite', [last/'m-api.json', '--out', last/'m-cli-project.json'], 2)
    bad = json.loads((last/'m-api.json').read_text()); bad['extra'] = 1
    invalid = out / 'invalid-project.json'; invalid.write_text(json.dumps(bad))
    cli('invalid', [invalid, '--out', out/'invalid-output.json'], 2)
    assert not (out/'invalid-output.json').exists()
    for name, digest in preserved.items(): assert hashlib.sha256((out/name).read_bytes()).hexdigest() == digest
    for name, digest in originals.items(): assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
    assert fingerprints() == before and len(originals) == 165 and len(preserved) == 594 and calls == 134
    report = dict(status='PASS', case_families=11, source_cases=33, project_cases=66, actual_wrapped_fem_solves=66,
                  original_native_replays=33, cli_calls=calls, reference_files_unchanged=len(originals),
                  preserved_files=len(preserved), project_files=264, recomputed_native_files=330,
                  records=records, source_sha256=before, seconds=time.monotonic()-started,
                  interpretation='Accepted native FEM Cases retain SI/materials/boundaries/gauges/orders and produce identical complete results and all five native file bytes after m/mm Project transport. API/CLI input normalization does not solve or certify convergence. Dedicated static worker/GUI/Study remain separate work.')
    (out/'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print({k:v for k,v in report.items() if k not in ('records','source_sha256')})


if __name__ == '__main__':
    main()

# SPDX-License-Identifier: Apache-2.0
"""Compare real GUI newer pairs and history to independent saved API results."""
import argparse
import json
from pathlib import Path
import numpy as np
from superfish_ng.jobs import _implementation_hashes, read_job
from superfish_ng.planar_saved import read_planar_run
from superfish_ng.planar_tracking_jobs import read_planar_tracking, _snapshot
from superfish_ng.planar_tracking_history_saved import read_planar_history, history_snapshot
from validate_planar_piecewise_gui import compare_native, snapshot


def compare_spectrum(first, second):
    read_planar_run(first); read_planar_run(second)
    before, after = snapshot(first), snapshot(second)
    if before != after:
        raise AssertionError('complete native bytes differ between API and GUI')
    count = 0
    for name in ('fields.npz', 'mesh.npz'):
        with np.load(first/name, allow_pickle=False) as a, np.load(second/name, allow_pickle=False) as b:
            if set(a.files) != set(b.files):
                raise AssertionError('native array names differ')
            for key in a.files:
                if a[key].dtype != b[key].dtype or not np.array_equal(a[key], b[key]):
                    raise AssertionError('native array differs: '+key)
                count += 1
    return count


def audit(root, browser, output):
    root, browser = Path(root).resolve(), Path(browser).resolve()
    report = json.loads((browser/'report.json').read_text())
    if not report['passed'] or report['source_changed_during_run'] or report['external_requests']:
        raise AssertionError('browser acceptance failed')
    implementation = _implementation_hashes()
    if implementation != json.loads((root/'implementation-before.json').read_text()):
        raise AssertionError('implementation differs from frozen integration source')
    for path, digest in report['source_sha256'].items():
        relative = Path(path).relative_to(Path('src/superfish_ng')).as_posix()
        if implementation[relative] != digest:
            raise AssertionError('browser source differs from integration source')
    fixture = json.loads((root/'fixture.json').read_text())
    source = Path(fixture['source'])
    source_before = snapshot(source)
    workspace = root/'workspace'
    history_directory = workspace/report['final_history']
    owned_before = history_snapshot(history_directory)
    history = read_planar_history(history_directory)
    if history != json.loads((browser/'history-result.json').read_text()):
        raise AssertionError('full exported history differs from owned physical replay')
    if history['status'] != 'PASS' or history['current_mode_ids'] != ['first']:
        raise AssertionError('history does not preserve final individual identity')
    identifiers = [report[key] for key in ('pair9', 'pair10', 'final_pair')]
    arrays = 0
    for index, identifier in enumerate(identifiers, 1):
        api, gui = root/f'api-pair-{index:03d}', workspace/identifier
        expected = read_planar_tracking(api)
        if read_planar_tracking(gui) != expected or history['steps'][index-1] != expected:
            raise AssertionError('full requests, field comparison or identity decision differ')
        owned = history_directory/f'step-{index-1:04d}'
        if _snapshot(gui) != _snapshot(owned):
            raise AssertionError('owned history changed original pair bytes')
        for side in ('previous', 'current'):
            arrays += compare_spectrum(api/side, gui/side)
    imported = workspace/report['imported_job']
    read_job(imported)
    final = compare_native(source/'trial-004', imported)
    arrays += final['arrays_equal']
    if (source_before != snapshot(source) or owned_before != history_snapshot(history_directory)
            or implementation != _implementation_hashes()):
        raise AssertionError('source, owned ancestry or implementation changed during audit')
    result = dict(passed=True, full_api_gui_pairs_equal=3, versions=[9, 10, 10],
                  full_exported_owned_history_equal=True, owned_pair_bytes_equal=True,
                  arrays_compared=arrays, final_project_case_rf_equal=True,
                  implementation_unchanged=True, source_and_ancestry_unchanged=True,
                  new_fem_solves=0)
    with Path(output).open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    audit(args.root, args.browser, args.out)

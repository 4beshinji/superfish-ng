# SPDX-License-Identifier: Apache-2.0
"""Audit real browser results against independent API trials and owned natives.

No new eigenproblem is solved here. Both executions must already exist, and
every saved native is physically restored by the dedicated planar readers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

from superfish_ng.constants import C0
from superfish_ng.jobs import _implementation_hashes, read_job
from superfish_ng.planar_saved import read_planar_run
from superfish_ng.planar_tuning import read_planar_tune, replay_planar_tune
from superfish_ng.project import parse_json
from superfish_ng.planar_tuning_jobs import RESULT
from superfish_ng.planar_tuning_saved import _snapshot_trial


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def compare_native(first, second):
    """Check complete arrays and RF, allowing only execution metadata to differ."""
    first, second = Path(first), Path(second)
    a, b = read_planar_run(first/'solution'), read_planar_run(second/'solution')
    if a.case.to_dict() != b.case.to_dict():
        raise AssertionError('native Cases differ')
    count = 0
    for name in ('fields.npz', 'mesh.npz'):
        with np.load(first/'solution'/name, allow_pickle=False) as x, np.load(second/'solution'/name, allow_pickle=False) as y:
            if set(x.files) != set(y.files):
                raise AssertionError('native array names differ')
            for key in x.files:
                if x[key].dtype != y[key].dtype or not np.array_equal(x[key], y[key]):
                    raise AssertionError(f'native array differs: {name}/{key}')
                count += 1
    for name in ('project.json', 'solution/case.json', 'solution/results.json'):
        if json.loads((first/name).read_text()) != json.loads((second/name).read_text()):
            raise AssertionError(f'complete Project/Case/RF differs: {name}')
    return dict(arrays_equal=count, project_case_rf_equal=True,
                modes=len(a.frequencies_hz), native_source=str(first), native_target=str(second))


def audit(root, browser_directory, api_directory, output):
    root, browser_directory, api_directory = [Path(v).resolve() for v in (root, browser_directory, api_directory)]
    before = snapshot(browser_directory)
    implementation = _implementation_hashes()
    report = json.loads((browser_directory/'report.json').read_text())
    if not report['passed'] or report['source_changed_during_run'] or report['external_requests']:
        raise AssertionError('browser did not pass with stable source and zero external requests')
    for path, digest in report['source_sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise AssertionError('browser evidence differs from current implementation')
    workspace = root/'workspace'
    gui_directory = workspace/report['resumed_job']
    if read_job(gui_directory)['tuning_status'] != 'TUNED':
        raise AssertionError('GUI job is not verified TUNED')
    gui = read_planar_tune(gui_directory/RESULT)
    def exported_checkpoint(name):
        # GUI downloads identify runtime trial owners; they are replay envelopes.
        return replay_planar_tune(parse_json((browser_directory/name).read_text()))

    exported = exported_checkpoint('final-checkpoint.json')
    if exported != gui:
        raise AssertionError('GUI-exported full checkpoint differs from API physical replay')
    api = read_planar_tune(api_directory/f'checkpoint-{len(gui["trials"]):03d}.json')
    for key in ('request', 'trials', 'decision', 'status', 'scope', 'can_resume'):
        if api[key] != gui[key]:
            raise AssertionError(f'independent API and GUI differ: {key}')
    pairs = [compare_native(a, b) for a, b in zip(api['trial_runs'], gui['trial_runs'])]
    imported = workspace/report['imported_job']
    read_job(imported)
    pairs.append(compare_native(gui['trial_runs'][-1], imported))
    first = read_planar_tune(workspace/report['first_job']/RESULT)
    for index, run in enumerate(first['trial_runs']):
        if _snapshot_trial(run) != gui['trial_sources_sha256'][index]:
            raise AssertionError('resumed owned prefix differs from original bytes')
    cancel = exported_checkpoint('cancelled-checkpoint.json')
    resumed = exported_checkpoint('cancel-resumed-checkpoint.json')
    if cancel['trials'] != resumed['trials'][:1] or cancel['trial_sources_sha256'] != resumed['trial_sources_sha256'][:1]:
        raise AssertionError('cancelled prefix decisions/natives changed during resume')
    unverified = exported_checkpoint('unverified-checkpoint.json')
    if unverified['status'] != 'UNVERIFIED' or unverified['trials'][-1]['frequency_hz'] is not None or unverified['can_resume']:
        raise AssertionError('unverified target was evaluated or resumed')
    native = read_planar_run(Path(gui['trial_runs'][-1])/'solution')
    points = native.case.mesh.points_xy_m
    width = float(np.max(points[:, 0])-np.min(points[:, 0]))
    analytic = C0/(2*width)
    relative = abs(native.frequencies_hz[0]/analytic-1)
    if relative >= 3e-6:
        raise AssertionError('independent TE10 analytical cutoff gate failed')
    if before != snapshot(browser_directory) or implementation != _implementation_hashes():
        raise AssertionError('evidence or implementation changed during audit')
    result = dict(passed=True, independent_api_gui_trials=len(gui['trials']),
                  native_pairs=pairs, arrays_compared=sum(p['arrays_equal'] for p in pairs),
                  full_request_decisions_equal=True, copied_prefix_bytes_equal=True,
                  cancel_prefix_bytes_decisions_equal=True, unverified_null=True,
                  analytic_te10_hz=analytic, analytic_relative_error=float(relative),
                  implementation_unchanged=True, new_fem_solves=0,
                  browser_report_sha256=before['report.json'])
    with Path(output).open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--browser', required=True, type=Path)
    parser.add_argument('--api', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    audit(args.root, args.browser, args.api, args.out)


if __name__ == '__main__':
    main()

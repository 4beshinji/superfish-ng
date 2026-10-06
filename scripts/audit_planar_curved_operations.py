# SPDX-License-Identifier: Apache-2.0
"""Read-only P08 evidence audit; no solve, replay or GUI execution.

The numerical source and tests are bound to the recorded operation checks.
Only the two subsequent GUI form files may differ. This is a local evidence
audit, not a continuous-error estimate or acceptance of the whole backlog.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(directory):
    operations = json.loads((directory/'operations-source-and-checks.json').read_text())
    changed = [name for name, value in operations['source_sha256'].items() if digest(Path(name)) != value]
    expected_changes = {'src/superfish_ng/web/planar.js', 'src/superfish_ng/web/planar.html'}
    if set(changed) != expected_changes:
        raise ValueError('P08 numerical/operation source or tests changed after their selected checks')
    for name in operations['unchanged_dedicated_math_files']:
        if digest(Path(name)) != operations['source_sha256'][name]:
            raise ValueError('accepted curved FEM/RF mathematics changed')
    for name, value in operations['logs'].items():
        if digest(directory/name) != value:
            raise ValueError('recorded operation check log changed')
    selected = (directory/'operations-direct-consumers.log').read_text()
    corrected = (directory/'operations-corrected-cases.log').read_text()
    original = (directory/'operations-tests.log').read_text()
    if 'Ran 48 tests in 32.964s\n\nOK' not in selected or 'Ran 2 tests in 5.490s\n\nOK' not in corrected:
        raise ValueError('selected successful unit evidence is missing')
    successful = [line.split()[0] for line in original.splitlines() if line.endswith(' ... ok')]
    if len(successful) != 7 or 'FAILED (failures=2)' not in original:
        raise ValueError('original successes and preserved two test-input failures disagree')
    reports = {}
    native = {}
    for name, count in (('browser-curved', 15), ('browser-legacy-planar-corrected', 13), ('browser-server-replay', 7)):
        report = json.loads((directory/name/'report.json').read_text())
        if (report['passed'] is not True or report['source_changed_during_run'] is not False
                or report['external_requests'] or len(report['checks']) != count
                or any(item['passed'] is not True for item in report['checks'])):
            raise ValueError('real browser acceptance, stable source or local-only evidence failed')
        if any(digest(Path(path)) != value for path, value in report['source_sha256'].items()):
            raise ValueError('accepted browser source changed')
        reports[name] = dict(checks=count, report_sha256=digest(directory/name/'report.json'))
    first = json.loads((directory/'browser-curved/report.json').read_text())
    replay = json.loads((directory/'browser-server-replay/report.json').read_text())
    if replay['original_report_sha256'] != reports['browser-curved']['report_sha256']:
        raise ValueError('server restart is not bound to the original browser execution')
    for pol in ('te', 'tm'):
        reference = directory/'browser-fixtures'/f'{pol}-native'
        hashes = {path.name: digest(path) for path in reference.iterdir()}
        if len(hashes) != 5 or hashes != first['reference_native_sha256'][pol]:
            raise ValueError('independent original API native changed')
        for name in ('browser-curved', 'browser-server-replay'):
            downloads = directory/name/f'{pol}-downloads'
            if any(digest(downloads/filename) != value for filename, value in hashes.items()):
                raise ValueError('GUI native coefficients/geometry/full RF bytes differ from original API')
        native[pol] = hashes
    states = [json.loads(path.read_text()) for path in (directory/'gui-workspace').glob('*/job.json')]
    if not states or any(state['status'] in ('queued', 'running') for state in states):
        raise ValueError('owned numerical jobs are not terminal')
    if list((Path('/tmp')/f'superfish-ng-browser-{os.getuid()}').glob('slot-*')):
        raise ValueError('owned browser slots have not been reclaimed')
    # Redirected audit stdout is still being written, and certificates are
    # audit outputs rather than original solver/browser evidence.
    excluded = [path.name for path in directory.glob('final-p08-*') if path.is_file()]
    files = {str(path.relative_to(directory)): digest(path) for path in directory.rglob('*')
             if path.is_file() and not (path.parent == directory and path.name.startswith('final-p08-'))}
    validators = ['scripts/audit_planar_curved_operations.py', 'scripts/verify_gui_planar.mjs',
        'scripts/verify_gui_planar_curved.mjs', 'scripts/verify_gui_planar_curved_replay.mjs']
    return dict(P08_complete=True, whole_123_card_goal_complete=False,
        new_operation_tests=9, direct_consumer_tests=48, real_browser_checks=35,
        preserved_initial_failures=['native-baseline.log', 'operations-baseline.log', 'operations-tests.log',
            'browser-baseline/report.json', 'browser-legacy-planar/report.json', 'gui-server.log'],
        numerical_replay_in_this_audit=0, full_validate_run=False, seed_validation_run=False,
        browser_reports=reports, original_native_sha256=native, owned_terminal_jobs=len(states),
        validator_sha256={name: digest(Path(name)) for name in validators},
        acceptance_audit_outputs_excluded=excluded, original_evidence_sha256=files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.directory)
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(f"PASS: P08 native/operations + {result['real_browser_checks']} real browser checks; whole goal remains active")


if __name__ == '__main__':
    main()

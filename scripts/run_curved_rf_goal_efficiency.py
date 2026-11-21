#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run/resume one fixed RF-goal row, or replay its saved journal without FEM.

This dedicated transport preserves process failures and development pauses.
It does not execute the fixed 36-row acceptance benchmark or certify accuracy.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))

from superfish_ng.adaptive_efficiency_process import run_measured_process
from superfish_ng.completion import digest
from superfish_ng.curved_rf_goal_efficiency_bundle import read_json_binding, file_inventory, bundle_state, verify_bundle
from superfish_ng.config import integer, keys
from superfish_ng.curved_rf_goal_efficiency_io import publish_rf_goal_json
from superfish_ng.curved_rf_goal_efficiency_plan import (
    build_curved_rf_goal_efficiency_plan, request_for_curved_rf_goal_efficiency_execution)
from superfish_ng.curved_rf_goal_efficiency_resume import resume_curved_rf_goal_efficiency_worker
from superfish_ng.curved_rf_goal_efficiency_saved import read_curved_rf_goal_efficiency
from superfish_ng.curved_rf_goal_efficiency_worker import execute_curved_rf_goal_efficiency_worker
from superfish_ng.project import parse_json


def source_hashes():
    return {p.relative_to(ROOT).as_posix(): digest(p)
            for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def environment():
    import numpy
    import scipy
    return dict(python=sys.version, executable=sys.executable, numpy=numpy.__version__,
                scipy=scipy.__version__, platform=platform.platform(),
                cpuinfo=Path('/proc/cpuinfo').read_text(), meminfo=Path('/proc/meminfo').read_text(),
                blas_threads=os.environ.get('OPENBLAS_NUM_THREADS'), gpu_used=False,
                commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
                utc=datetime.now(timezone.utc).isoformat())


def fresh_invocation(execution_id, *, max_new_events=None, source_archives=None):
    if source_archives is not None and type(source_archives) is not dict:
        raise ValueError('source_archives must be a mapping')
    rows = build_curved_rf_goal_efficiency_plan()['executions']
    selected = next((row for row in rows if row['id'] == execution_id), None)
    if selected is None:raise ValueError('execution-id must name one of the fixed 36 rows')
    return dict(schema_version=1, action='run', execution=selected, max_new_events=max_new_events, source_archives=deepcopy({} if source_archives is None else source_archives))


def validate_invocation(value):
    if type(value) is not dict:raise ValueError('RF command invocation must be an object')
    common = ('schema_version','action','max_new_events')
    if value.get('action') == 'run':
        fields = common+('execution','source_archives')
        keys(value, fields, fields, 'RF command invocation')
        if type(value['source_archives']) is not dict:raise ValueError('source_archives must be a mapping')
        request_for_curved_rf_goal_efficiency_execution(value['execution'])
    elif value.get('action') == 'resume':
        fields = common+('journal','sha256','implementation_archives','interruption_files')
        keys(value, fields, fields, 'RF resume invocation')
        for name in ('implementation_archives','interruption_files'):
            if type(value[name]) is not dict:raise ValueError(name+' must be a mapping')
        if type(value['journal']) is not str or not Path(value['journal']).is_absolute():
            raise ValueError('RF resume journal requires an absolute path')
        raw = read_json_binding(value['journal'], value['sha256'])
        if type(raw) is not dict:raise ValueError('RF resume journal must be an object')
        request_for_curved_rf_goal_efficiency_execution(raw['execution'])
    else:raise ValueError('RF command action must be run or resume')
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise ValueError('RF command schema_version must be integer 1')
    if value['max_new_events'] is not None:integer(value['max_new_events'], 'max_new_events')
    return deepcopy(value)


def read_invocation(path, sha):
    return validate_invocation(read_json_binding(path, sha))


def new_output(path):
    path = Path(path).absolute()
    if path.exists() or path.is_symlink():raise FileExistsError(path)
    if any(p.is_symlink() for p in path.parents):raise ValueError('RF output parents must not be symlinks')
    return path


def worker_command(path, sha, out, submission_origin):
    """Outer wall includes final result publication, which the native cost excludes."""
    from superfish_ng import curved_rf_goal_efficiency_worker as worker
    invocation = read_invocation(path, sha)
    original = worker._write
    publication = None
    started = time.perf_counter()
    status = 'FAILED';exception_type = None
    def measured_write(target, value):
        nonlocal publication
        if Path(target).name != 'result.json':return original(target, value)
        begin = time.perf_counter();write_status = 'FAILED'
        try:
            result = original(target, value);write_status = 'COMPLETED'
            return result
        finally:
            publication = dict(status=write_status, wall_seconds=time.perf_counter()-begin)
    worker._write = measured_write
    try:
        if invocation['action'] == 'run':
            report = execute_curved_rf_goal_efficiency_worker(invocation['execution'], out,
                max_new_events=invocation['max_new_events'], submission_origin=submission_origin, source_archives=invocation['source_archives'])
        else:
            report = resume_curved_rf_goal_efficiency_worker(invocation['journal'], out,
                expected_sha256=invocation['sha256'], implementation_archives=invocation['implementation_archives'],
                interruption_files=invocation['interruption_files'], max_new_events=invocation['max_new_events'],
                submission_origin=submission_origin)
        status = 'RETURNED'
        print(report['status'], flush=True)
    except BaseException as error:
        exception_type = type(error).__name__
        raise
    finally:
        # Do not overwrite a replacement made by another owner.
        if worker._write is measured_write:worker._write = original
        ended = time.perf_counter()
        receipt = dict(schema_version=1, document_type='curved_rf_goal_efficiency_worker_terminal',
            status=status, exception_type=exception_type, invocation_wall_seconds=ended-started,
            submission_wall_seconds=None if submission_origin is None else ended-submission_origin,
            result_publication=publication,
            scope='inclusive worker invocation through result publication/return or exception; '
                  'result publication is a subset, never add it to wall; receipt write and interpreter exit covered by supervisor')
        try:publish_rf_goal_json(Path(out).parent/'worker-terminal.json', receipt)
        except BaseException as recording_error:
            if exception_type is not None:
                # Preserve the original exception; traceback/logs remain external.
                print('RF terminal recording also failed: '+str(recording_error), file=sys.stderr)
            else:raise


def run_invocation(invocation, out):
    invocation = validate_invocation(invocation);out = new_output(out)
    if os.environ.get('OPENBLAS_NUM_THREADS') != '1':
        raise ValueError('RF fixed process requires OPENBLAS_NUM_THREADS=1 before Python startup')
    before = source_hashes();out.mkdir(parents=True, exist_ok=False)
    publish_rf_goal_json(out/'invocation.json', invocation)
    publish_rf_goal_json(out/'environment.json', environment())
    publish_rf_goal_json(out/'sources-before.json', before)
    origin = time.perf_counter()
    argv = [sys.executable, str(Path(__file__).resolve()), '_worker', '--invocation', str(out/'invocation.json'),
            '--sha256', digest(out/'invocation.json'), '--out', str(out/'native'), '--submission-origin', repr(origin)]
    try:
        process = run_measured_process(argv, out/'process', cwd=ROOT,
                                      wall_limit_seconds=3600, memory_limit_bytes=32*1024**3)
    finally:
        # On supervisor exceptions its finally block has already reaped the child.
        after = source_hashes()
        publish_rf_goal_json(out/'sources-after.json', after)
        process_path = out/'process'/'process.json'
        process = parse_json(process_path.read_text()) if process_path.is_file() else None
        audit = dict(status='UNCHANGED' if before == after else 'CHANGED',
            changed=sorted(k for k in before.keys() & after.keys() if before[k] != after[k]),
            added=sorted(after.keys()-before.keys()), deleted=sorted(before.keys()-after.keys()),
            scope='endpoint inventory/content audit; no continuous mutation monitor')
        result = out/'native'/'result.json'
        journal = parse_json(result.read_text()) if result.is_file() else None
        state = bundle_state(out, process, journal, before != after)
        manifest = dict(schema_version=1, document_type='curved_rf_goal_efficiency_process_bundle', status=state,
            source_audit=audit, process=process, numerical_status=None if journal is None else journal['status'],
            files=file_inventory(out), physical_error_bound=None,
            scope='one fixed row; process exit/source audit are not scientific acceptance; '
                  'all completed/partial local bytes and logs bound after terminal reap; independent full replay is separate')
        publish_rf_goal_json(out/'manifest.json', manifest)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run');run.add_argument('--execution-id', required=True)
    resume = commands.add_parser('resume');resume.add_argument('--journal', required=True);resume.add_argument('--sha256', required=True)
    resume.add_argument('--interruption-files');resume.add_argument('--interruption-files-sha256')
    replay = commands.add_parser('replay')
    original = replay.add_mutually_exclusive_group(required=True)
    original.add_argument('--journal');original.add_argument('--bundle')
    replay.add_argument('--sha256', required=True)
    for command in (run,resume,replay):
        command.add_argument('--source-archives');command.add_argument('--source-archives-sha256')
    for command in (run,resume):command.add_argument('--max-new-events', type=int)
    worker = commands.add_parser('_worker');worker.add_argument('--invocation', required=True)
    worker.add_argument('--sha256', required=True);worker.add_argument('--submission-origin', type=float, required=True)
    for command in (run,resume,replay,worker):command.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    if args.command == '_worker':
        worker_command(args.invocation, args.sha256, Path(args.out), args.submission_origin);return 0
    archives = {}
    if args.command in ('run','resume','replay'):
        if bool(args.source_archives) != bool(args.source_archives_sha256):parser.error('source archives require both path and SHA256')
        if args.source_archives:archives = read_json_binding(args.source_archives, args.source_archives_sha256)
    if args.command == 'replay':
        out = new_output(args.out)
        if args.bundle:
            manifest = verify_bundle(args.bundle, args.sha256)
            root = Path(args.bundle).absolute().parent;path = root/'native'/'result.json'
            if not path.is_file():
                complete = sorted((root/'native').glob('checkpoint-*.json'));path = complete[-1] if complete else None
            result = dict(status='PROCESS_BUNDLE_BYTES_VERIFIED', bundle=manifest, journal_replay=None, new_eigensolves=0)
            if path is not None:result['journal_replay'] = read_curved_rf_goal_efficiency(path, expected_sha256=digest(path), implementation_archives=archives)
        else:result = read_curved_rf_goal_efficiency(args.journal, expected_sha256=args.sha256, implementation_archives=archives)
        publish_rf_goal_json(out, result);print(result['status']);return 0
    if args.command == 'run':invocation = fresh_invocation(args.execution_id, max_new_events=args.max_new_events, source_archives=archives)
    else:
        if bool(args.interruption_files) != bool(args.interruption_files_sha256):parser.error('interruption files require both path and SHA256')
        interruptions = {} if not args.interruption_files else read_json_binding(args.interruption_files, args.interruption_files_sha256)
        invocation = dict(schema_version=1, action='resume', journal=str(Path(args.journal).absolute()), sha256=args.sha256,
                          implementation_archives=archives, interruption_files=interruptions, max_new_events=args.max_new_events)
    manifest = run_invocation(invocation, args.out);print(manifest['status'])
    return 0 if manifest['status'] == 'PROCESS_EXITED' else 1


if __name__ == '__main__':sys.exit(main())

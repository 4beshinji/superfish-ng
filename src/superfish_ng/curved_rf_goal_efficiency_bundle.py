# SPDX-License-Identifier: Apache-2.0
"""Closed RF-goal process inventories shared by the CLI and resume reader.

Byte/cost verification does not replay physics or certify historical timings.
Completed checkpoints and partial artifacts remain explicitly different.
"""
import math
from pathlib import Path
import stat

from .adaptive_efficiency_reference import _bound_file
from .completion import digest
from .config import keys
from .curved_rf_goal_efficiency_saved import _same_saved
from .project import parse_json


def read_json_binding(path, sha):
    path = _bound_file(path, sha, {})
    value = parse_json(path.read_text(encoding='utf-8'))
    _bound_file(path, sha, {})
    return value

def file_inventory(root):
    """Bind partial staging and logs as evidence, never as complete checkpoints."""
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise ValueError('RF process bundle must not contain symlinks')
        if path.is_dir():continue
        if not stat.S_ISREG(path.stat().st_mode):raise ValueError('RF process bundle requires regular files')
        relative = path.relative_to(root).as_posix()
        if relative == 'manifest.json':continue
        sha = digest(path)
        _bound_file(path, sha, {})
        files[relative] = sha
    return files

def bundle_state(root, process, journal, source_changed):
    state = 'PROCESS_RECEIPT_MISSING' if process is None else process['status']
    if state == 'PROCESS_EXITED':
        if type(process.get('exit_code')) is not int or process['exit_code'] != 0:
            raise ValueError('exited RF process requires integer exit code zero')
        if journal is None:state = 'WORKER_RESULT_MISSING'
        else:
            terminal = root/'worker-terminal.json'
            if not terminal.is_file():state = 'WORKER_RECEIPT_MISSING'
            else:
                receipt = parse_json(terminal.read_text())
                publication = receipt.get('result_publication')
                if (receipt.get('document_type') != 'curved_rf_goal_efficiency_worker_terminal' or
                        type(receipt.get('schema_version')) is not int or receipt['schema_version'] != 1 or
                        receipt.get('status') != 'RETURNED' or receipt.get('exception_type') is not None or
                        type(publication) is not dict or publication.get('status') != 'COMPLETED'):
                    raise ValueError('RF successful process must retain returned worker and complete result publication')
                values = [publication.get('wall_seconds'), receipt.get('invocation_wall_seconds'), process.get('wall_seconds')]
                if any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in values) or values != sorted(values):
                    raise ValueError('RF result write must lie within invocation and process walls')
                submission = receipt.get('submission_wall_seconds')
                if type(submission) not in (int,float) or not math.isfinite(submission) or submission < values[1]:
                    raise ValueError('RF submission wall must cover worker invocation')
    return 'SOURCE_CHANGED' if source_changed else state

def verify_bundle(path, sha):
    manifest = read_json_binding(path, sha);root = Path(path).absolute().parent
    fields = ('schema_version','document_type','status','source_audit','process','numerical_status','files','physical_error_bound','scope')
    keys(manifest, fields, fields, 'RF process bundle')
    if (type(manifest['schema_version']) is not int or manifest['schema_version'] != 1 or
            manifest['document_type'] != 'curved_rf_goal_efficiency_process_bundle' or manifest['physical_error_bound'] is not None):
        raise ValueError('RF process bundle schema differs')
    _same_saved(manifest['files'], file_inventory(root), 'RF process bundle full inventory')
    process_path = root/'process'/'process.json'
    process = parse_json(process_path.read_text()) if process_path.is_file() else None
    _same_saved(manifest['process'], process, 'RF original terminal process')
    before = parse_json((root/'sources-before.json').read_text());after = parse_json((root/'sources-after.json').read_text())
    audit = manifest['source_audit']
    expected = dict(status='UNCHANGED' if before == after else 'CHANGED',
        changed=sorted(k for k in before.keys() & after.keys() if before[k] != after[k]),
        added=sorted(after.keys()-before.keys()), deleted=sorted(before.keys()-after.keys()), scope=audit['scope'])
    _same_saved(audit, expected, 'RF original source audit')
    result = root/'native'/'result.json'
    journal = parse_json(result.read_text()) if result.is_file() else None
    state = bundle_state(root, process, journal, before != after)
    _same_saved(manifest['status'], state, 'RF original bundle status')
    _same_saved(manifest['numerical_status'], None if journal is None else journal['status'], 'RF original numerical status')
    _bound_file(path, sha, {})
    return manifest

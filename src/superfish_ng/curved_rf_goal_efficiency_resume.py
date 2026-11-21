# SPDX-License-Identifier: Apache-2.0
"""Verified RF-goal continuation in a new directory, retaining all prior costs."""
from copy import deepcopy
import math
from pathlib import Path
import time

from .adaptive_efficiency_reference import _bound_file
from .adaptive_efficiency_timing import PhaseRecorder
from .completion import digest
from .config import integer, keys
from .curved_rf_goal_efficiency_saved import read_curved_rf_goal_efficiency, _same_saved
from .curved_rf_goal_efficiency_worker import _execute_worker_events
from .curved_rf_goal_efficiency_reference import load_curved_rf_goal_efficiency_reference, _verify_reference_bindings
from .jobs import _implementation_hashes
from .project import parse_json


RESUME_SCOPE='resumed fixed RF-goal branch; immutable original prefix and separate measured continuation segment'
ORIGIN_FIELDS=('journal_path','journal_sha256','event_count','implementation_aliases','interruption_files')


def _origin_metadata(origin, total_events, *, terminal_without_new_events=False):
    keys(origin,ORIGIN_FIELDS+('implementation_archives',),ORIGIN_FIELDS,'RF resume origin')
    integer(origin['event_count'],'resume original event_count')
    if origin['event_count']>total_events or (origin['event_count']==total_events and not terminal_without_new_events):
        raise ValueError('RF resumed journal must add events or retain its explicit initial terminal budget stop')
    if type(origin['implementation_aliases']) is not dict or type(origin['interruption_files']) is not dict:
        raise ValueError('RF resume origin requires explicit source aliases and interruption file bindings')
    if type(origin.get('implementation_archives',{})) is not dict:
        raise ValueError('RF resume source archives require a SHA256-to-path mapping')
    if any(type(p) is not str or not Path(p).is_absolute() for p in origin['interruption_files']):
        raise ValueError('RF interruption file bindings require absolute path strings')


def _verify_interruption(parent, origin, bound):
    files=origin['interruption_files']
    if len(files)==1 and Path(next(iter(files))).name=='manifest.json':
        _verify_terminated_bundle(parent,origin,bound)
        return
    if 'observed_cost' in parent:
        if files:raise ValueError('completed development pause must not invent interruption files')
        return
    if len(files)!=2 or {Path(p).name for p in files}!={'failure.json','process.json'}:
        raise ValueError('interrupted RF checkpoint requires original failure.json and terminal process.json bindings')
    parsed={}
    for path,sha in files.items():
        path=_bound_file(path,sha,bound);parsed[path.name]=parse_json(path.read_text())
        if path.name=='failure.json' and path.parent!=Path(origin['journal_path']).parent:
            raise ValueError('RF interruption must retain the original worker failure directory')
    failure=parsed['failure.json'];process=parsed['process.json'];n=origin['event_count']
    if (failure.get('status')!='FAILED' or failure.get('error_type')!='KeyboardInterrupt' or
            failure.get('checkpoint_level_runs',failure.get('preceding_level_runs'))!=parent['level_runs'] or
            type(failure.get('native_solves_attempted')) is not int or
            type(failure.get('native_solves_completed')) is not int or
            not n<=failure['native_solves_completed']<=failure['native_solves_attempted']<=n+1 or
            type(failure.get('observed_cost')) is not dict):
        raise ValueError('RF interrupted prefix requires its actual KeyboardInterrupt, attempted/completed counts and partial costs')
    if 'last_complete_checkpoint' in failure:
        _same_saved(failure['last_complete_checkpoint'],dict(path=origin['journal_path'],sha256=origin['journal_sha256']),
                    'RF last fully published checkpoint')
    if (process.get('document_type')!='adaptive_efficiency_process_cost' or process.get('status')!='PROCESS_FAILED' or
            type(process.get('exit_code')) is not int or process['exit_code']==0):
        raise ValueError('RF interrupted prefix requires its measured terminal failed process')


def _verify_terminated_bundle(parent, origin, bound):
    """A killed worker cannot write failure.json; bind its closed supervisor bundle.

    No absent phase time or in-flight solve count is invented. All partial bytes
    and the actual non-success process costs stay in the original manifest.
    """
    from .curved_rf_goal_efficiency_bundle import verify_bundle
    files=origin['interruption_files'];path,sha=next(iter(files.items()))
    path=_bound_file(path,sha,bound);manifest=verify_bundle(path,sha);root=path.parent
    process=manifest['process']
    if (manifest['source_audit']['status']!='UNCHANGED' or type(process) is not dict or
            type(process.get('schema_version')) is not int or process['schema_version']!=1 or
            process.get('document_type')!='adaptive_efficiency_process_cost' or
            process.get('status') not in ('PROCESS_FAILED','WALL_LIMIT','MEMORY_LIMIT','INTERRUPTED') or
            type(process.get('exit_code')) is not int or process['exit_code'] not in (-15,-9)):
        raise ValueError('RF killed prefix requires an unchanged bundle and actual terminal SIGTERM/SIGKILL')
    native=root/'native';journal=Path(origin['journal_path'])
    invocation=parse_json((root/'invocation.json').read_text())
    if type(invocation.get('schema_version')) is not int or invocation['schema_version']!=1:
        raise ValueError('RF killed process requires its original fixed invocation schema')
    checkpoints=sorted(native.glob('checkpoint-*.json'))
    latest=native/'result.json' if (native/'result.json').is_file() else checkpoints[-1] if checkpoints else None
    fallback=(latest is None and invocation.get('action')=='resume' and
              invocation.get('journal')==str(journal) and invocation.get('sha256')==origin['journal_sha256'])
    if not fallback and (journal.parent!=native or journal!=latest):
        raise ValueError('RF killed resume must use the last completely published journal in its original native directory')
    if latest is not None and latest.name!='result.json' and latest.name!=f"checkpoint-{origin['event_count']:03d}.json":
        raise ValueError('RF last complete checkpoint filename must retain its actual event count')
    _bound_file(journal,origin['journal_sha256'],bound)
    _same_saved(parse_json(journal.read_text()),parent,'RF terminated original complete prefix')
    if not fallback:_same_saved(invocation.get('max_new_events'),parent['development_event_limit'],'RF terminated development event limit')
    elif invocation.get('max_new_events') is not None:integer(invocation['max_new_events'],'RF terminated resume max_new_events')
    if invocation.get('action')=='run':
        fields=('schema_version','action','max_new_events','execution','source_archives')
        keys(invocation,fields,fields,'RF terminated invocation')
        if type(invocation['source_archives']) is not dict:raise ValueError('RF terminated source archives must be a mapping')
        _same_saved(invocation.get('execution'),parent['execution'],'RF terminated fixed execution')
    elif invocation.get('action')=='resume':
        fields=('schema_version','action','max_new_events','journal','sha256','implementation_archives','interruption_files')
        keys(invocation,fields,fields,'RF terminated resume invocation')
        if type(invocation['implementation_archives']) is not dict or type(invocation['interruption_files']) is not dict:
            raise ValueError('RF terminated resume archive/interruption inputs must be mappings')
        if not fallback:
            if type(parent.get('resume_origin')) is not dict:raise ValueError('RF terminated resumed checkpoint must retain its original resume origin')
            original=parent['resume_origin']
            for field,key in (('journal','journal_path'),('sha256','journal_sha256'),('implementation_archives','implementation_archives'),('interruption_files','interruption_files')):
                _same_saved(invocation.get(field),original.get(key,{}),'RF terminated original resume '+field)
    else:raise ValueError('RF killed process action does not match its original journal')
    argv=process.get('request',{}).get('argv')
    if (type(argv) is not list or len(argv)!=11 or any(type(arg) is not str for arg in argv) or
            Path(argv[1]).name!='run_curved_rf_goal_efficiency.py' or
            argv[2:10]!=['_worker','--invocation',str(root/'invocation.json'),'--sha256',digest(root/'invocation.json'),
                         '--out',str(native),'--submission-origin']):
        raise ValueError('RF terminal process must name this exact invocation hash and native output')
    cwd=process.get('request',{}).get('cwd')
    if type(cwd) is not str or not Path(cwd).is_absolute() or Path(argv[1])!=Path(cwd)/'scripts/run_curved_rf_goal_efficiency.py':
        raise ValueError('RF killed process must name the dedicated script in its recorded repository cwd')
    for relative,h in manifest['files'].items():_bound_file(root/relative,h,bound)
    _bound_file(path,sha,{})


def verify_resume_origin(document, *, bindings=None, implementation_archives=None):
    """Reconstruct the original journal and require byte-for-byte prefix values."""
    origin=document['resume_origin']
    no_new=(document.get('status') in ('REFINEMENT_LIMIT','TRACKING_BUDGET') and
            type(document.get('planning_stop')) is dict and document['planning_stop'].get('stage')=='initial_resume_plan')
    _origin_metadata(origin,len(document['events']),terminal_without_new_events=no_new);bound={}
    path=_bound_file(origin['journal_path'],origin['journal_sha256'],bound)
    raw=parse_json(path.read_text())
    if type(raw.get('events')) is not list or len(raw['events'])!=origin['event_count']:
        raise ValueError('RF resume origin changed its original prefix length')
    if raw.get('status')!='PAUSED':raise ValueError('RF resume origin must be PAUSED before recursive reconstruction')
    archives=deepcopy(origin.get('implementation_archives',{}))
    if implementation_archives is not None:
        if type(implementation_archives) is not dict:raise ValueError('RF implementation archives require a mapping')
        archives.update(implementation_archives)
    result=read_curved_rf_goal_efficiency(path,expected_sha256=origin['journal_sha256'],bindings=bindings,
                                        implementation_aliases=origin['implementation_aliases'],implementation_archives=archives)
    parent=result['document'];bound.update(result['bound_inputs'])
    if parent['status']!='PAUSED':raise ValueError('only an independently verified PAUSED benchmark prefix can continue')
    for name in ('execution','request'):_same_saved(document[name],parent[name],'RF resume original '+name)
    try:_same_saved(document['reference_bound_inputs'],parent['reference_bound_inputs'],'RF resume original reference bindings')
    except ValueError:
        # The parent reader derived this context from the pinned inputs after
        # complete physical replay; a journal cannot supply its own context.
        context=result.get('reference_binding_context')
        if context is None:raise
        bound.update(_verify_reference_bindings(document['reference_bound_inputs'],context,archives))
    for name in ('events','level_runs','native_sources','event_records','observations'):
        _same_saved(document[name][:origin['event_count']],parent[name],'RF immutable original '+name)
    _verify_interruption(parent,origin,bound)
    return bound


def resume_curved_rf_goal_efficiency_worker(path, directory, *, expected_sha256, bindings=None,
                                          implementation_aliases=None, implementation_archives=None, interruption_files=None,
                                          max_new_events=None, submission_origin=None):
    """Continue a verified pause or terminal SIGINT/TERM/KILL prefix; never overwrite.

    Historical costs stay in the original bound journal. New prefixes measure
    only this invocation, including the full original journal verification.
    """
    if max_new_events is not None:integer(max_new_events,'max_new_events')
    if submission_origin is not None and (type(submission_origin) not in (int,float) or not math.isfinite(submission_origin) or
                                         not 0<submission_origin<=time.perf_counter()):
        raise ValueError('submission_origin requires a finite past shared monotonic timestamp')
    directory=Path(directory).absolute()
    if directory.exists():raise FileExistsError(directory)
    if any(p.is_symlink() for p in (directory,*directory.parents)):
        raise ValueError('RF resume output requires a new directory without symlinks')
    recorder=PhaseRecorder();implementation=_implementation_hashes()
    with recorder.phase('original_prefix_full_replay'):
        verified=read_curved_rf_goal_efficiency(path,expected_sha256=expected_sha256,bindings=bindings,
                                               implementation_aliases=implementation_aliases,implementation_archives=implementation_archives)
    parent=verified['document'];n=len(parent['events']);bound=verified['bound_inputs']
    if parent['status']!='PAUSED' or n>=parent['request']['max_levels']:
        raise ValueError('RF continuation requires a PAUSED benchmark prefix within its original event budget')
    origin=dict(journal_path=str(Path(path).absolute()),journal_sha256=expected_sha256,event_count=n,
                implementation_aliases=deepcopy(implementation_aliases or {}),implementation_archives=deepcopy(implementation_archives or {}),
                interruption_files=deepcopy(interruption_files or {}))
    _origin_metadata(origin,n+1);_verify_interruption(parent,origin,bound)
    with recorder.phase('reference_verification'):
        reference=load_curved_rf_goal_efficiency_reference(parent['execution']['case_id'],bindings=bindings,source_archives=implementation_archives)
    bound.update(_verify_reference_bindings(parent['reference_bound_inputs'],reference,implementation_archives))
    return _execute_worker_events(parent['execution'],parent['request'],directory,reference,recorder,implementation,
                                  max_new_events=max_new_events,submission_origin=submission_origin,prefix=parent,
                                  resume_origin=origin,retained_inputs=bound)

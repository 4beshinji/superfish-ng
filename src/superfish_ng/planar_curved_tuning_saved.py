# SPDX-License-Identifier: Apache-2.0
"""Portable ownership of complete Cartesian P2 tuning native prefixes.

Copying a verified native preserves its creator metadata; it does not assert
that the receiving owner solved it. Public replay recomputes the full history.
Only byte-stable, physically verified fields are reused during an execution.
"""
from copy import deepcopy
from pathlib import Path
from .config import integer,keys
from .project import parse_json
from .saved_mode_tracking import _canonical
from .jobs import _digest,_implementation_hashes
from .planar_jobs import execute_planar_project
from .planar_tuning_saved import _snapshot_trial,_resolve_trial_runs,_request_copy,_copy_trial,_write
from .planar_curved_tuning import (validate_planar_curved_tune,_json_types,_TuneState,_result,
    _reconstruct,_replay_state,_trial,_native,_assess)

FORMAT='superfish_ng_owned_planar_curved_tune_checkpoint'
CHECKPOINT_KEYS=('format','schema_version','request','trial_runs','trial_sources_sha256','trials',
    'decision','status','can_resume','parameter_unit','frequency_unit','scope')


def _stable(runs,sources):
    if [_snapshot_trial(p) for p in runs]!=sources:
        raise ValueError('owned curved tune sources changed during verification or execution')


def _checkpoint(request,state,sources):
    result=_result(request,state)
    result.update(format=FORMAT,trial_sources_sha256=deepcopy(sources))
    return result


def _verified(document,base_directory=None):
    document=deepcopy(document);_json_types(document)
    keys(document,CHECKPOINT_KEYS,CHECKPOINT_KEYS,'owned curved planar tune checkpoint')
    if (document['format']!=FORMAT or type(document['schema_version']) is not int or document['schema_version']!=1):
        raise ValueError('expected owned curved planar tune checkpoint schema_version 1')
    if type(document['can_resume']) is not bool or type(document['trials']) is not list or type(document['trial_sources_sha256']) is not list:
        raise ValueError('owned curved checkpoint requires boolean can_resume and list trials/sources')
    runs=_resolve_trial_runs(document['trial_runs'],base_directory)
    owner=base_directory if base_directory is not None else Path(runs[0]).parent if runs else None
    if owner is None:raise ValueError('zero-trial owned checkpoint requires an explicit owner directory')
    _request_copy(owner,document['request'])
    sources=[_snapshot_trial(p) for p in runs]
    # Fail a changed byte before spending any physical replay work.
    if sources!=document['trial_sources_sha256']:raise ValueError('owned curved checkpoint source hashes differ from native files')
    implementation=_implementation_hashes()
    state=_reconstruct(document['request'],runs)
    expected=_checkpoint(document['request'],state,sources)
    document['trial_runs']=runs
    if _canonical(document)!=_canonical(expected):raise ValueError('owned curved checkpoint differs from complete original native replay')
    _stable(runs,sources);_request_copy(owner,document['request'])
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during owned curved replay')
    return state,sources


def replay_owned_planar_curved_tune(document,*,base_directory=None):
    state,sources=_verified(document,base_directory)
    return _checkpoint(document['request'],state,sources)


def _read_document(path):
    path=Path(path).absolute()
    if path!=path.resolve() or path.is_symlink() or not path.is_file():
        raise ValueError('curved checkpoint must be a regular file without symbolic-link components')
    before=_digest(path);document=parse_json(path.read_text(encoding='utf-8'))
    return path,before,document


def _read_owned(path,base_directory=None):
    path,before,document=_read_document(path)
    # On-disk portable documents use only ordered direct-child names.
    keys(document,CHECKPOINT_KEYS,CHECKPOINT_KEYS,'owned curved planar tune checkpoint')
    runs=document['trial_runs']
    if type(runs) is not list or runs!=[f'trial-{i+1:03d}' for i in range(len(runs))]:
        raise ValueError('saved owned curved paths must be ordered relative trial names')
    state,sources=_verified(document,path.parent if base_directory is None else base_directory)
    if before!=_digest(path):raise ValueError('owned curved checkpoint changed during complete replay')
    return document['request'],state,sources


def read_owned_planar_curved_tune(path,*,base_directory=None):
    request,state,sources=_read_owned(path,base_directory)
    return _checkpoint(request,state,sources)


def _portable(result):
    document=deepcopy(result)
    document['trial_runs']=[Path(p).name for p in result['trial_runs']]
    return document


def _destination(directory):
    directory=Path(directory).absolute()
    if directory!=directory.resolve():raise ValueError('owned curved output must have no symbolic-link components')
    directory.mkdir(parents=True,exist_ok=False)
    return directory


def _copy_verified(request,state,sources,directory):
    """Transfer the verified fields only after all copied original bytes agree."""
    _stable(state.runs,sources)
    directory=_destination(directory);_write(directory/'request.json',request)
    runs=[]
    for index,(source,hashes) in enumerate(zip(state.runs,sources)):
        target=directory/f'trial-{index+1:03d}';_copy_trial(source,target,hashes);runs.append(str(target))
    _stable(state.runs,sources);_stable(runs,sources);_request_copy(directory,request)
    copied=_TuneState(list(state.trials),list(state.records),list(state.solutions),runs,deepcopy(state.hashes))
    result=_checkpoint(request,copied,sources)
    _write(directory/f'checkpoint-{len(runs):03d}.json',_portable(result))
    return directory,copied


def _raw_verified(document):
    _json_types(document)
    keys(document,CHECKPOINT_KEYS,CHECKPOINT_KEYS,'raw curved planar tune checkpoint')
    runs=document['trial_runs']
    if type(runs) is not list or any(type(p) is not str for p in runs):raise ValueError('raw curved paths must be a list of strings')
    for index,value in enumerate(runs):
        path=Path(value)
        if (not path.is_absolute() or value!=str(path.resolve()) or path.name!=f'trial-{index+1:03d}'):
            raise ValueError('raw curved trial paths must be absolute canonical ordered trial names')
    sources=[_snapshot_trial(p) for p in runs]
    implementation=_implementation_hashes();state=_replay_state(document)
    _stable(runs,sources)
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during raw curved replay')
    return state,sources


def import_owned_planar_curved_tune(checkpoint,directory):
    """Own a fully verified raw/owned prefix without solving any new trial."""
    implementation=_implementation_hashes()
    path=before=None
    if isinstance(checkpoint,(str,Path)):path,before,document=_read_document(checkpoint)
    else:document=deepcopy(checkpoint)
    _json_types(document);keys(document,CHECKPOINT_KEYS,CHECKPOINT_KEYS,'curved tune import')
    if document['format']==FORMAT:
        if path is not None:request,state,sources=_read_owned(path)
        else:state,sources=_verified(document);request=document['request']
    elif document['format']=='superfish_ng_planar_curved_tune_checkpoint':
        state,sources=_raw_verified(document);request=document['request']
    else:raise ValueError('curved import requires a complete raw or owned curved tune checkpoint')
    if path is not None and before!=_digest(path):raise ValueError('source curved checkpoint changed during import')
    request=parse_json(_canonical(request));_,copied=_copy_verified(request,state,sources,directory)
    if path is not None and before!=_digest(path):raise ValueError('source curved checkpoint changed during copying')
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during curved import')
    return _checkpoint(request,copied,sources)


def execute_owned_planar_curved_tune(request,directory,*,max_new_trials=None,checkpoint=None):
    """Resume into a fresh owner and save the complete prefix before new work."""
    request=deepcopy(request);validate_planar_curved_tune(request);request=parse_json(_canonical(request))
    if max_new_trials is not None:integer(max_new_trials,'max_new_trials')
    if checkpoint is None:state=_TuneState([],[],[],[],[]);sources=[]
    else:
        if isinstance(checkpoint,(str,Path)):old_request,state,sources=_read_owned(checkpoint)
        else:state,sources=_verified(checkpoint);old_request=checkpoint['request']
        if _canonical(old_request)!=_canonical(request):raise ValueError('owned curved resume request differs from checkpoint')
        if _result(request,state)['status']!='PAUSED':raise ValueError('only a verified PAUSED owned curved tune can resume')
    implementation=_implementation_hashes()
    directory,state=_copy_verified(request,state,sources,directory)
    count=0;previous=_checkpoint(request,state,sources)
    while previous['can_resume'] and (max_new_trials is None or count<max_new_trials):
        index=len(state.runs);recipe=previous['decision']['next_trial'];run=directory/f'trial-{index+1:03d}'
        try:
            _stable(state.runs,sources);_request_copy(directory,request)
            current=_trial(request,recipe['value'],recipe['phase'])
            execute_planar_project(current.project,run)
            source=_snapshot_trial(run);solution,hashes=_native(str(run),current.project)
            trial=_assess(request,state.trials,state.records,state.solutions,current,solution)
            candidate=_TuneState(state.trials+[trial],state.records+[current],state.solutions+[solution],state.runs+[str(run)],state.hashes+[hashes])
            new_sources=sources+[source]
            _stable(candidate.runs,new_sources);_request_copy(directory,request)
            if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during owned curved execution')
            result=_checkpoint(request,candidate,new_sources)
            _write(directory/f'checkpoint-{index+1:03d}.json',_portable(result))
        except Exception as error:
            _write(directory/f'failure-{index+1:03d}.json',dict(request=request,attempt=recipe,
                trial_run=run.name,preceding_trial_runs=[Path(p).name for p in state.runs],status='FAILED',
                error_type=type(error).__name__,error=str(error),
                scope='failed trial is not a frequency evaluation; preceding owned checkpoint remains replayable'))
            raise
        state=candidate;sources=new_sources;previous=result;count+=1
    _stable(state.runs,sources);_request_copy(directory,request)
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during owned curved execution')
    return previous

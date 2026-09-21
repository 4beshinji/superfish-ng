# SPDX-License-Identifier: Apache-2.0
"""Owned original curved tuning checkpoints, physical replay and fresh-output resume."""
from copy import deepcopy
from pathlib import Path
from .config import integer,keys
from .project import parse_json
from .hphi_project import HphiProject
from .curved_hphi import solve_curved_hphi
from .curved_hphi_saved import save_curved_hphi_run,read_curved_hphi_run
from .curved_hphi_shape_tuning import CurvedHphiShapeLaw
from .curved_hphi_tuning import validate_curved_hphi_tune,curved_hphi_tune_decision,_trial,_assess_trial
from .hphi_tuning import _json_types
from .hphi_tuning_saved import (CHECKPOINT_KEYS,_snapshot_trial,_resolve_trial_runs,_copy_trial,_check_request_copy)
from .saved_mode_tracking import _canonical
from .jobs import _implementation_hashes,_write_json

SCOPE='original_curved_full_quadratic_hphi_tuning'


def _checkpoint(request,runs,sources,trials):
    decision=curved_hphi_tune_decision(request,trials)
    return dict(format='superfish_ng_curved_hphi_tune_checkpoint',schema_version=1,
        request=deepcopy(request),trial_runs=list(runs),trial_sources_sha256=deepcopy(sources),
        trials=deepcopy(trials),decision=decision,status=decision['status'],
        can_resume=decision['status']=='PAUSED',scope=SCOPE)


def _stable(runs,sources):
    if [_snapshot_trial(run) for run in runs]!=sources:
        raise ValueError('curved tune owned sources changed during verification or execution')


def _request_copy(base,request):
    if base is not None:
        if not (Path(base)/'request.json').is_file():raise ValueError('curved tune owner requires request.json')
        _check_request_copy(base,request)


def _recompute(request,runs):
    """Rebuild every trial from its owned Project and native FEM/RF files."""
    request=deepcopy(request);project=validate_curved_hphi_tune(request)
    law=CurvedHphiShapeLaw.from_dict(request['shape_law'])
    runs=_resolve_trial_runs(list(runs))
    if len(runs)>request['max_trials']+1:raise ValueError('curved tune paths exceed search plus final trial budget')
    trials=[];sources=[];records=[];solutions=[]
    for run in runs:
        decision=curved_hphi_tune_decision(request,trials)
        if decision['status']!='PAUSED':raise ValueError('curved tune contains trials after a terminal decision')
        candidate=decision['next_trial'];record=_trial(request,project,law,candidate['value'],candidate['phase'])
        source=_snapshot_trial(run);owned=HphiProject.load(Path(run)/'project.json')
        if owned.to_dict()!=record.project.to_dict():raise ValueError('curved tune owned Project differs from declared trial')
        solution=read_curved_hphi_run(Path(run)/'solution')
        trial,restored=_assess_trial(request,trials,records,solutions,record,solution)
        trials.append(trial);sources.append(source);records.append(record);solutions.append(restored)
        _stable(runs[:len(sources)],sources)
    _stable(runs,sources)
    return _checkpoint(request,runs,sources,trials),records,solutions


def _verified(document,base_directory=None):
    document=deepcopy(document);_json_types(document)
    keys(document,CHECKPOINT_KEYS,CHECKPOINT_KEYS,'curved Hphi tune checkpoint')
    if (document['format']!='superfish_ng_curved_hphi_tune_checkpoint' or type(document['schema_version']) is not int
            or document['schema_version']!=1 or document['scope']!=SCOPE):
        raise ValueError('expected curved Hphi tune checkpoint schema_version 1')
    if type(document['can_resume']) is not bool or type(document['trials']) is not list or type(document['trial_sources_sha256']) is not list:
        raise ValueError('curved tune checkpoint requires boolean can_resume and list trials/sources')
    runs=_resolve_trial_runs(document['trial_runs'],base_directory)
    base=base_directory if base_directory is not None else Path(runs[0]).parent if runs else None
    _request_copy(base,document['request'])
    expected,records,solutions=_recompute(document['request'],runs)
    document['trial_runs']=runs
    if _canonical(document)!=_canonical(expected):raise ValueError('curved tune checkpoint differs from owned native replay')
    _request_copy(base,document['request']);_stable(runs,expected['trial_sources_sha256'])
    return expected,records,solutions


def replay_curved_hphi_tune(document,*,base_directory=None):
    """Recompute native RF, identities, recovery and decisions; do not solve a new trial."""
    return _verified(document,base_directory)[0]


def _read(path):
    path=Path(path).absolute()
    if path!=path.resolve() or path.is_symlink() or not path.is_file():
        raise ValueError('curved tune checkpoint must be a regular file without symbolic-link components')
    document=parse_json(path.read_text(encoding='utf-8'))
    base=path.parent/'execution' if (path.parent/'execution').is_dir() else path.parent
    return _verified(document,base)


def read_curved_hphi_tune(path):return _read(path)[0]


def _write_checkpoint(directory,checkpoint):
    portable=deepcopy(checkpoint)
    portable['trial_runs']=[Path(run).name for run in checkpoint['trial_runs']]
    _write_json(directory/f'checkpoint-{len(checkpoint["trial_runs"]):03d}.json',portable)


def execute_curved_hphi_tune(request,directory,*,max_new_trials=None,checkpoint=None):
    """Own completed trials; resume copies verified sources into a fresh directory.

    Execution reuses only in-memory assessments of just-verified source bytes.
    All owned hashes are checked before/after every new trial. Public replay
    recomputes the complete history rather than trusting these assessments.
    """
    request=deepcopy(request);project=validate_curved_hphi_tune(request)
    request=parse_json(_canonical(request));law=CurvedHphiShapeLaw.from_dict(request['shape_law'])
    if max_new_trials is not None:integer(max_new_trials,'max_new_trials')
    records=[];solutions=[]
    if checkpoint is None:previous=_checkpoint(request,[],[],[])
    else:
        previous,records,solutions=(_read(checkpoint) if isinstance(checkpoint,(str,Path)) else _verified(checkpoint))
        if _canonical(previous['request'])!=_canonical(request):raise ValueError('curved tune resume request differs from checkpoint')
        if previous['status']!='PAUSED' or not previous['can_resume']:raise ValueError('only verified PAUSED curved tuning can resume')
    implementation=_implementation_hashes();directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False)
    _write_json(directory/'request.json',request)
    old_runs=list(previous['trial_runs']);runs=[];sources=deepcopy(previous['trial_sources_sha256']);trials=deepcopy(previous['trials'])
    for index,(source,hashes) in enumerate(zip(old_runs,sources)):
        target=directory/f'trial-{index+1:03d}';_copy_trial(source,target,hashes);runs.append(str(target))
    _stable(old_runs,sources);_stable(runs,sources)
    previous=_checkpoint(request,runs,sources,trials);_write_checkpoint(directory,previous)
    count=0
    while previous['status']=='PAUSED' and (max_new_trials is None or count<max_new_trials):
        candidate=previous['decision']['next_trial'];index=len(runs);run=directory/f'trial-{index+1:03d}'
        try:
            _stable(runs,sources);_request_copy(directory,request)
            record=_trial(request,project,law,candidate['value'],candidate['phase'])
            run.mkdir(exist_ok=False);record.project.save(run/'project.json')
            solution=solve_curved_hphi(record.project.case)
            save_curved_hphi_run(record.project.case,solution,run/'solution')
            source=_snapshot_trial(run);owned=HphiProject.load(run/'project.json')
            if owned.to_dict()!=record.project.to_dict():raise ValueError('curved tune Project changed during execution')
            restored=read_curved_hphi_run(run/'solution')
            trial,restored=_assess_trial(request,trials,records,solutions,record,restored)
            new_runs=runs+[str(run)];new_sources=sources+[source]
            _stable(new_runs,new_sources);_request_copy(directory,request)
            if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during curved tune execution')
            result=_checkpoint(request,new_runs,new_sources,trials+[trial]);_write_checkpoint(directory,result)
        except Exception as error:
            _write_json(directory/f'failure-{index+1:03d}.json',dict(document_type='curved_hphi_tune_failure',request=request,
                attempt=candidate,trial_run=str(run),preceding_trial_runs=runs,status='FAILED',error_type=type(error).__name__,
                error=str(error),scope='failed trial is not a frequency evaluation; preceding checkpoints remain separate'))
            raise
        runs=new_runs;sources=new_sources;trials.append(trial);records.append(record);solutions.append(restored)
        previous=result;count+=1
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during curved tune execution')
    _stable(runs,sources);_request_copy(directory,request)
    return previous

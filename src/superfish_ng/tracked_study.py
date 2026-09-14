# SPDX-License-Identifier: Apache-2.0
"""Sequential FEM Study execution with immutable, replayable tracking checkpoints."""
from copy import deepcopy
import json
from pathlib import Path
from .config import keys
from .project import Project, parse_json
from .studies import Study
from .jobs import execute_project, read_job, _implementation_hashes
from .completion import digest
from .saved import read_solution
from .saved_mode_tracking import build_saved_mode_tracking, validate_tracking_controls, _canonical
from .mode_tracking_history import start_mode_history, extend_mode_history
from .study_shape_tracking import pair_controls


def _request(request):
    fields=('schema_version','study','initial_ids','step_controls')
    keys(request,fields,fields,'tracked Study execution request')
    if type(request['schema_version']) is not int or request['schema_version']!=1:
        raise ValueError('tracked Study execution requires schema_version 1')
    _canonical(request)
    study=Study.from_dict(request['study']);projects=study.projects()
    ids=request['initial_ids']
    if (type(ids) is not list or len(ids)!=projects[0].case.modes
            or any(type(x) is not str or not x.strip() for x in ids) or len(set(ids))!=len(ids)):
        raise ValueError('initial_ids requires one distinct nonempty string per initial mode rank')
    controls=request['step_controls']
    if type(controls) is not list or len(controls)!=len(projects)-1:
        raise ValueError('step_controls requires one object per adjacent Study point pair')
    for i,(control,previous,current) in enumerate(zip(controls,study.values,study.values[1:])):
        pair_controls(study,control,previous,current,projects=projects[i:i+2])
    return study,projects


def _point_sources(directory,project):
    if not directory.is_absolute() or directory.is_symlink():
        raise ValueError('tracked Study points require absolute, non-symlink native Job directories')
    before={p.relative_to(directory).as_posix():digest(p) for p in directory.rglob('*') if p.is_file()}
    if read_job(directory)['status']!='complete':raise ValueError('tracked Study point is incomplete; cannot skip it')
    if _canonical(Project.load(directory/'project.json').to_dict())!=_canonical(project.to_dict()):
        raise ValueError('tracked Study point project differs from declared order/value')
    read_solution(directory/'solution')
    after={p.relative_to(directory).as_posix():digest(p) for p in directory.rglob('*') if p.is_file()}
    if before!=after:raise ValueError('tracked Study point sources changed during verification')
    return before


def _assemble(request,runs):
    study,projects=_request(request)
    if type(runs) is not list or not 1<=len(runs)<=len(projects) or any(type(x) is not str for x in runs):
        raise ValueError('tracked Study requires an ordered nonempty prefix of point directories')
    if len(set(runs))!=len(runs):raise ValueError('tracked Study point directories must be distinct')
    sources=[];history=None;records=[]
    for i,run in enumerate(runs):
        if history is not None and not history['can_extend']:
            raise ValueError('tracked Study continues after an unverified correspondence')
        directory=Path(run);sources.append(_point_sources(directory,projects[i]))
        if i==1:
            pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(Path(runs[0])/'solution'),
                current_run=str(directory/'solution'),previous_ids=request['initial_ids'],controls=pair_controls(study,request['step_controls'][0],study.values[0],study.values[1],projects=projects[:2])))
            history=start_mode_history(pair)
        elif i>1:
            history=extend_mode_history(history,dict(current_run=str(directory/'solution'),controls=pair_controls(study,request['step_controls'][i-1],study.values[i-1],study.values[i],projects=projects[i-1:i+1])))
        records.append(dict(index=i,value=study.values[i],status='INITIAL' if i==0 else history['status'],
            current_mode_ids=request['initial_ids'] if i==0 else history['current_mode_ids']))
    for i in range(len(runs),len(projects)):
        records.append(dict(index=i,value=study.values[i],status='NOT_COMPUTED',current_mode_ids=None))
    if sources!=[_point_sources(Path(run),projects[i]) for i,run in enumerate(runs)]:
        raise ValueError('tracked Study sources changed during tracking')
    status='UNVERIFIED' if history is not None and not history['can_extend'] else 'COMPLETE' if len(runs)==len(projects) else 'PAUSED'
    return dict(schema_version=1,document_type='tracked_study_checkpoint',request=deepcopy(request),point_runs=list(runs),
        point_sources_sha256=sources,history=history,point_results=records,status=status,
        can_resume=status=='PAUSED',
        scope='sequential native FEM solves with sampled correspondence; not a convergence or continuous-branch certificate')


def replay_tracked_study(document):
    fields=('schema_version','document_type','request','point_runs','point_sources_sha256','history','point_results','status','can_resume','scope')
    keys(document,fields,fields,'tracked Study checkpoint')
    expected=_assemble(document['request'],document['point_runs'])
    if _canonical(document)!=_canonical(expected):raise ValueError('tracked Study checkpoint replay differs from saved data or sources')
    return expected


def read_tracked_study(path):
    return replay_tracked_study(parse_json(Path(path).read_text(encoding='utf-8')))


def execute_tracked_study(request,directory,*,max_new_points=None,checkpoint=None):
    """Solve a prefix into NEW output; resume only an unchanged verified checkpoint.

    Each completed point publishes an exclusive checkpoint. A later solve failure
    leaves the preceding checkpoint usable; failed output is never overwritten.
    """
    request=deepcopy(request)
    _,projects=_request(request)
    if max_new_points is not None and (type(max_new_points) is not int or max_new_points<1):
        raise ValueError('max_new_points must be a positive integer')
    runs=[];previous=None
    if checkpoint is not None:
        previous=replay_tracked_study(checkpoint)
        if _canonical(previous['request'])!=_canonical(request):raise ValueError('resume request differs from checkpoint; thresholds and IDs cannot be changed')
        if not previous['can_resume']:raise ValueError('only a verified PAUSED tracked Study can resume')
        runs=list(previous['point_runs'])
    implementation=_implementation_hashes()
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False)
    limit=len(projects) if max_new_points is None else min(len(projects),len(runs)+max_new_points)
    for i in range(len(runs),limit):
        run=directory/f'point-{i+1:03d}'
        execute_project(projects[i],run)
        runs.append(str(run));result=_assemble(request,runs)
        if previous is not None and result['point_sources_sha256'][:len(previous['point_runs'])]!=previous['point_sources_sha256']:
            raise ValueError('prior checkpoint sources changed during execution')
        if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during tracked Study execution')
        with (directory/f'checkpoint-{i+1:03d}.json').open('x',encoding='utf-8') as stream:
            stream.write(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
        previous=result
        if result['status']!='PAUSED':break
    return result

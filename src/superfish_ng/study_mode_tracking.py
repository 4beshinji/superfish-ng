# SPDX-License-Identifier: Apache-2.0
"""Ordered tracking over a verified completed native Study, without skipping points."""
from copy import deepcopy
import json
from pathlib import Path
from .config import keys
from .project import Project,parse_json
from .studies import Study
from .jobs import read_job
from .completion import digest
from .saved import read_solution
from .saved_mode_tracking import build_saved_mode_tracking,_canonical,validate_tracking_controls
from .mode_tracking_history import start_mode_history,extend_mode_history
from .study_shape_tracking import pair_controls


def _study_inputs(directory):
    sources={name:digest(directory/name) for name in ('study.json','study-results.json','manifest.json','job.json')}
    state=read_job(directory)
    if state['status']!='complete' or state.get('kind')!='study':
        raise ValueError('study tracking requires a completed native Study; incomplete or failed points are never skipped')
    study=Study.from_dict(parse_json((directory/'study.json').read_text()))
    report=parse_json((directory/'study-results.json').read_text())
    if not isinstance(report,dict):raise ValueError('saved Study results must be an object')
    if _canonical(report.get('study'))!=_canonical(study.to_dict()):raise ValueError('saved Study declaration differs from study-results')
    points=report.get('points')
    if type(points) is not list or len(points)!=len(study.values):raise ValueError('Study point count differs from declared values')
    runs=[];jobs={}
    for i,(point,project) in enumerate(zip(points,study.projects())):
        name=f'point-{i+1:03d}'
        if not isinstance(point,dict):raise ValueError('saved Study point must be an object')
        if point.get('directory')!=name or _canonical(point.get('value'))!=_canonical(study.values[i]):
            raise ValueError('Study point order, directory or parameter value differs from its declaration')
        path=directory/name
        jobs[f'{name}/job.json']=digest(path/'job.json')
        if path.is_symlink() or read_job(path)['status']!='complete':raise ValueError('Study contains an incomplete or redirected point; no point may be skipped')
        saved_project=Project.load(path/'project.json')
        if _canonical(saved_project.to_dict())!=_canonical(project.to_dict()):raise ValueError('Study point project differs from its declared parameter value')
        from .te import is_te
        if is_te(project.case):
            from .te_saved import read_te_run
            read_te_run(path/'solution')
            result=parse_json((path/'solution/results.json').read_text())
            case_hash=digest(path/'solution/case.json')
        else:
            solution=read_solution(path/'solution');result=solution.results;case_hash=result['case_sha256']
        if point.get('case_sha256')!=case_hash or _canonical(point.get('modes'))!=_canonical(result['modes']):
            raise ValueError('Study point summary differs from its native saved fields')
        runs.append(str((path/'solution').resolve()))
    sources.update(jobs)
    if any(digest(directory/name)!=value for name,value in sources.items()):raise ValueError('Study sources changed during validation')
    return study,runs,sources


def build_study_mode_tracking(request,*,base_directory=None):
    fields=('schema_version','study_run','initial_ids','step_controls')
    keys(request,fields,fields,'Study tracking request')
    if type(request['schema_version']) is not int or request['schema_version']!=1:raise ValueError('Study tracking request requires schema_version 1')
    _canonical(request)
    if type(request['study_run']) is not str or not request['study_run'].strip():raise ValueError('study_run must name a completed Study directory')
    root=Path.cwd() if base_directory is None else Path(base_directory);directory=Path(request['study_run'])
    directory=(directory if directory.is_absolute() else root/directory).resolve()
    study,runs,before=_study_inputs(directory)
    controls=request['step_controls']
    if type(controls) is not list or len(controls)!=len(runs)-1:raise ValueError('step_controls requires one explicit control object per adjacent Study point pair')
    controls=[pair_controls(study,control,previous,current) for control,previous,current in zip(controls,study.values,study.values[1:])]
    pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=runs[0],current_run=runs[1],previous_ids=request['initial_ids'],controls=controls[0]))
    history=start_mode_history(pair)
    for i in range(2,len(runs)):
        if not history['can_extend']:break
        history=extend_mode_history(history,dict(current_run=runs[i],controls=controls[i-1]))
    visited=len(history['steps'])+1
    records=[dict(index=0,value=study.values[0],status='INITIAL',current_mode_ids=list(request['initial_ids']))]
    for i in range(1,len(runs)):
        if i<visited:
            tracking=history['steps'][i-1]['tracking']
            records.append(dict(index=i,value=study.values[i],status=tracking['status'],current_mode_ids=tracking['current_mode_ids']))
        else:records.append(dict(index=i,value=study.values[i],status='NOT_VISITED',current_mode_ids=None))
    _,after_runs,after=_study_inputs(directory)
    if before!=after or runs!=after_runs:raise ValueError('Study sources changed during tracking; retry with stable saved results')
    normalized=deepcopy(request);normalized['study_run']=str(directory)
    return dict(schema_version=1,document_type='study_mode_tracking',request=normalized,study_sources_sha256=before,
        status=history['status'],history=history,point_results=records,visited_point_indices=list(range(visited)),
        unvisited_point_indices=list(range(visited,len(runs))),
        scope='ordered native Study point correspondence; stops at the first unverified pair; no change to independent spectra, convergence status or continuous-branch guarantees')


def save_study_mode_tracking(request,path,*,base_directory=None):
    result=build_study_mode_tracking(request,base_directory=base_directory)
    with Path(path).open('x',encoding='utf-8') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


def replay_study_mode_tracking(document):
    fields=('schema_version','document_type','request','study_sources_sha256','status','history','point_results','visited_point_indices','unvisited_point_indices','scope')
    keys(document,fields,fields,'saved Study tracking')
    request=document['request']
    if not isinstance(request,dict) or type(request.get('study_run')) is not str or not Path(request['study_run']).is_absolute():
        raise ValueError('saved Study tracking requires an absolute study_run; regenerate from its request')
    expected=build_study_mode_tracking(request)
    if _canonical(expected)!=_canonical(document):raise ValueError('Study tracking replay differs from saved data or source identities')
    return expected


def read_study_mode_tracking(path):return replay_study_mode_tracking(parse_json(Path(path).read_text(encoding='utf-8')))

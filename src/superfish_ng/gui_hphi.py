# SPDX-License-Identifier: Apache-2.0
"""Explicit Hphi GUI operations on dedicated Projects and verified jobs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from .config import keys
from .jobs import _implementation_hashes, read_job
from .hphi_jobs import _native_hashes, KIND
from .hphi_project import HphiProject
from .project import parse_json

ACTIONS = {
    'hphi-normalize-tune': ['request'], 'hphi-start-tune': ['request','max_new_trials'],
    'hphi-resume-tune': ['document','max_new_trials'], 'hphi-replay-tune': ['document'],
    'hphi-tune-result': ['id'], 'hphi-tune-checkpoints': ['id'],
    'hphi-open-tune-checkpoint': ['id','index'], 'hphi-tune-trial': ['document','index'],
    'hphi-normalize-history': ['document'], 'hphi-start-history': ['document','step_ids'],
    'hphi-extend-history': ['id','next_id'], 'hphi-history-result': ['id'],
    'hphi-history-source': ['id','index','side'],
    'hphi-normalize-tracking': ['document'], 'hphi-start-tracking': ['previous_id','current_id','document'],
    'hphi-tracking-result': ['id'], 'hphi-tracking-side': ['id','side'], 'hphi-repeat-tracking': ['id','document'],
    'hphi-normalize-convergence': ['document'], 'hphi-start-convergence': ['document'],
    'hphi-convergence-result': ['id'], 'hphi-convergence-point': ['id','index'],
    'hphi-normalize-study': ['document'], 'hphi-start-study': ['document'],
    'hphi-study-result': ['id'], 'hphi-study-point': ['id','index'],
    'hphi-normalize': ['document'], 'hphi-start': ['document'],
    'hphi-import': ['path'], 'hphi-result': ['id'],
    'hphi-plot': ['id','mode','mesh','length_unit'],
    'hphi-probe': ['id','mode','points_rz_m'],
    'hphi-probe-metadata': ['id','mode','points_rz_m'],
    'hphi-download': ['id','file'],
}


def hphi_response(manager, action, data, render_lock, plot_cache):
    """Return payload and media type; caller enforces local session authentication."""
    if action not in ACTIONS: raise ValueError('unknown hphi operation')
    if action in ('hphi-normalize-tune','hphi-start-tune','hphi-resume-tune','hphi-replay-tune',
                  'hphi-tune-result','hphi-tune-checkpoints','hphi-open-tune-checkpoint','hphi-tune-trial'):
        from .gui_hphi_tuning import hphi_tuning_response
        return hphi_tuning_response(manager, action, data), 'application/json; charset=utf-8'
    if action in ('hphi-normalize-history','hphi-start-history','hphi-extend-history','hphi-history-result','hphi-history-source'):
        return hphi_history_response(manager,action,data)
    if action in ('hphi-normalize-tracking','hphi-start-tracking','hphi-tracking-result','hphi-tracking-side','hphi-repeat-tracking'):
        return hphi_tracking_response(manager,action,data)
    if action in ('hphi-normalize-convergence','hphi-start-convergence','hphi-convergence-result','hphi-convergence-point'):
        return hphi_convergence_response(manager,action,data)
    if action in ('hphi-normalize-study','hphi-start-study','hphi-study-result','hphi-study-point'):
        return hphi_study_response(manager,action,data)
    required = ['document'] if action in ('hphi-normalize', 'hphi-start') else ['path'] if action=='hphi-import' else ['id']
    if action in ('hphi-probe', 'hphi-probe-metadata'): required += ['points_rz_m']
    if action=='hphi-download': required += ['file']
    keys(data, ACTIONS[action], required, 'hphi request')
    media = 'application/json; charset=utf-8'
    if action in ('hphi-normalize', 'hphi-start'):
        document = parse_json(data['document']) if isinstance(data['document'], str) else data['document']
        project = HphiProject.from_dict(document)
        return ({'id': manager.start_hphi(project)} if action=='hphi-start' else project.to_dict()), media
    if action=='hphi-import':
        return {'id': manager.import_hphi_result(data['path'])}, media
    directory = manager.directory(data['id'])
    state = manager.status(data['id'], verify=True)
    if state.get('kind')!=KIND or state.get('status')!='complete':
        raise ValueError('select a complete, verified hphi job')
    native = directory/'solution'
    before = _native_hashes(native)
    project = HphiProject.load(directory/'project.json')
    if action=='hphi-result':
        payload = dict(project=project.to_dict(), state=state,
                       result=parse_json((native/'results.json').read_text()), files=sorted(before))
    elif action=='hphi-download':
        if data['file'] not in before: raise ValueError('unknown hphi native file')
        payload=(native/data['file']).read_bytes();media='application/octet-stream'
    else:
        mode = data.get('mode', 1)
        if type(mode) is not int or not 1 <= mode <= project.case.modes:
            raise ValueError('mode must be a valid one-based mode number')
        plot = action=='hphi-plot'
        spec = dict(view='plot' if plot else 'probe', native_sha256=before,
                    implementation_sha256=_implementation_hashes(), mode=mode)
        if plot:
            mesh = data.get('mesh', False);unit=data.get('length_unit', project.display_length_unit)
            if type(mesh) is not bool or unit not in ('m','mm'):
                raise ValueError('hphi plot requires boolean mesh and length_unit m or mm')
            from importlib.metadata import version
            spec.update(mesh=mesh,length_unit=unit,matplotlib=version('matplotlib'),numpy=version('numpy'),scipy=version('scipy'))
        else:
            spec['points_rz_m']=data['points_rz_m']
        tag=hashlib.sha256(json.dumps(spec,sort_keys=True,allow_nan=False).encode()).hexdigest()
        path=directory/f'hphi-{tag}.{ "png" if plot else "csv" }'
        metadata_path=path.with_suffix(path.suffix+'.json')
        with render_lock:
            if not path.exists():
                if plot:
                    args=[sys.executable,'-m','superfish_ng','plot-hphi',str(native),'--out',str(path),'--mode',str(mode),'--length-unit',unit]
                    if mesh:args+=['--mesh']
                    done=subprocess.run(args,capture_output=True,text=True,timeout=120,
                        env={**os.environ,'OPENBLAS_NUM_THREADS':'1','MPLCONFIGDIR':str(plot_cache)})
                    if done.returncode:raise ValueError(done.stderr.strip() or 'hphi plot failed')
                else:
                    from .hphi_display import export_hphi_probe
                    export_hphi_probe(native,path,data['points_rz_m'],mode)
            if path.is_symlink() or metadata_path.is_symlink():raise ValueError('hphi view cache must not contain links')
            metadata=parse_json(metadata_path.read_text());payload=path.read_bytes()
            if (metadata['native_sha256']!=before or metadata['mode']!=mode
                    or metadata['data_sha256']!=hashlib.sha256(payload).hexdigest()):
                raise ValueError('hphi view cache integrity failure')
            if action=='hphi-probe-metadata':payload=metadata
            else:media='image/png' if plot else 'text/csv; charset=utf-8'
    if _native_hashes(native)!=before or manager.status(data['id'], verify=True)!=state:
        raise ValueError('hphi job changed while preparing GUI response')
    return payload, media



def hphi_study_response(manager, action, data):
    from .hphi_study import HphiStudy
    from .hphi_study_jobs import read_hphi_study, _snapshot
    required=['document'] if action.endswith(('normalize-study','start-study')) else ['id']
    if action=='hphi-study-point':required.append('index')
    keys(data,ACTIONS[action],required,'hphi Study request')
    media='application/json; charset=utf-8'
    if 'document' in required:
        raw=parse_json(data['document']) if isinstance(data['document'],str) else data['document']
        study=HphiStudy.from_dict(raw)
        return ({'id':manager.start_hphi_study(study)} if action=='hphi-start-study' else study.to_dict()),media
    directory=manager.directory(data['id']);study=HphiStudy.load(directory/'study.json');before=_snapshot(directory,study)
    result=read_hphi_study(directory)
    if action=='hphi-study-result':
        payload=dict(study=study.to_dict(),result=result,state=manager.status(data['id'],verify=True))
    else:
        index=data['index']
        if type(index) is not int or not 0<=index<len(result['points']):raise ValueError('hphi Study point index is out of range')
        if before!=_snapshot(directory,study):raise ValueError('hphi Study changed before point import')
        payload={'id':manager.import_hphi_result(directory/result['points'][index]['directory'])}
    if before!=_snapshot(directory,study):raise ValueError('hphi Study changed during GUI response')
    return payload,media


def _dedicated_gui_operation(manager, data, *, kind, request_format):
    """Select a dedicated parser from the owned job or explicit request format."""
    if 'id' in data:
        return manager.status(data['id'], verify=False).get('kind') == kind
    raw=data.get('document')
    if isinstance(raw,str):raw=parse_json(raw)
    return isinstance(raw,dict) and raw.get('format') == request_format


def hphi_tracking_response(manager,action,data):
    from .hphi_tracking import HphiTrackingRequest
    from .hphi_tracking_jobs import read_hphi_tracking,_snapshot
    start=manager.start_hphi_tracking
    if _dedicated_gui_operation(manager,data,kind='material_hphi_tracking',request_format='superfish_ng_material_hphi_tracking_request'):
        from .material_hphi_tracking import MaterialHphiTrackingRequest as HphiTrackingRequest
        from .material_hphi_tracking_jobs import read_material_hphi_tracking as read_hphi_tracking,_snapshot
        start=manager.start_material_hphi_tracking
    if _dedicated_gui_operation(manager,data,kind='curved_hphi_tracking',request_format='superfish_ng_curved_hphi_tracking_request'):
        from .curved_hphi_tracking import CurvedHphiTrackingRequest as HphiTrackingRequest
        from .curved_hphi_tracking_jobs import read_curved_hphi_tracking as read_hphi_tracking,_snapshot
        start=manager.start_curved_hphi_tracking
    keys(data,ACTIONS[action],ACTIONS[action],'Hphi tracking request');media='application/json; charset=utf-8'
    request=None
    if 'document' in data:
        raw=parse_json(data['document']) if isinstance(data['document'],str) else data['document']
        request=HphiTrackingRequest.from_dict(raw)
    if action=='hphi-normalize-tracking':return request.to_dict(),media
    if action=='hphi-start-tracking':
        return {'id':start(manager.directory(data['previous_id']),manager.directory(data['current_id']),request)},media
    directory=manager.directory(data['id']);before=_snapshot(directory);result=read_hphi_tracking(directory)
    if action=='hphi-tracking-result':
        payload=dict(request=result['request'],result=result,state=manager.status(data['id'],verify=True),
            projects={side:HphiProject.load(directory/side/'project.json').to_dict() for side in ('previous','current')},
            sources=parse_json((directory/'sources.json').read_text()))
    elif action=='hphi-tracking-side':
        if data['side'] not in ('previous','current'):raise ValueError('Hphi tracking side must be previous or current')
        if before!=_snapshot(directory):raise ValueError('Hphi tracking changed before original side import')
        payload={'id':manager.import_hphi_result(directory/data['side'])}
    else:
        if before!=_snapshot(directory):raise ValueError('Hphi tracking changed before repeat execution')
        payload={'id':start(directory/'previous',directory/'current',request)}
    if before!=_snapshot(directory):raise ValueError('Hphi tracking changed during GUI response')
    return payload,media



def hphi_convergence_response(manager,action,data):
    from .hphi_convergence import HphiConvergence
    from .hphi_convergence_jobs import read_hphi_convergence_job,_snapshot,_point_name
    required=['document'] if action in ('hphi-normalize-convergence','hphi-start-convergence') else ['id']
    if action=='hphi-convergence-point':required.append('index')
    keys(data,ACTIONS[action],required,'Hphi convergence request');media='application/json; charset=utf-8'
    if 'document' in required:
        raw=parse_json(data['document']) if isinstance(data['document'],str) else data['document']
        request=HphiConvergence.from_dict(raw)
        return ({'id':manager.start_hphi_convergence(request)} if action=='hphi-start-convergence' else request.to_dict()),media
    directory=manager.directory(data['id']);request=HphiConvergence.load(directory/'convergence.json');before=_snapshot(directory,request)
    result=read_hphi_convergence_job(directory)
    if action=='hphi-convergence-result':payload=dict(request=request.to_dict(),result=result,state=manager.status(data['id'],verify=True))
    else:
        index=data['index']
        if type(index) is not int or not 0<=index<len(request.projects):raise ValueError('Hphi convergence level index is out of range')
        if before!=_snapshot(directory,request):raise ValueError('Hphi convergence changed before level import')
        payload={'id':manager.import_hphi_result(directory/_point_name(index))}
    if before!=_snapshot(directory,request):raise ValueError('Hphi convergence changed during GUI response')
    return payload,media


def hphi_history_response(manager, action, data):
    from .hphi_tracking_history import HphiTrackingHistoryRequest
    from .hphi_tracking_history_saved import read_hphi_history, history_snapshot
    from .hphi_tracking import HphiTrackingRequest
    start=manager.start_hphi_history;extend=manager.extend_hphi_history;pair_kind='hphi_tracking'
    if _dedicated_gui_operation(manager,data,kind='material_hphi_tracking_history',request_format='superfish_ng_material_hphi_tracking_history_request'):
        from .material_hphi_tracking_history import MaterialHphiTrackingHistoryRequest as HphiTrackingHistoryRequest
        from .material_hphi_tracking_history_saved import read_material_hphi_history as read_hphi_history, history_snapshot
        from .material_hphi_tracking import MaterialHphiTrackingRequest as HphiTrackingRequest
        start=manager.start_material_hphi_history;extend=manager.extend_material_hphi_history;pair_kind='material_hphi_tracking'
    if _dedicated_gui_operation(manager,data,kind='curved_hphi_tracking_history',request_format='superfish_ng_curved_hphi_tracking_history_request'):
        from .curved_hphi_tracking_history import CurvedHphiTrackingHistoryRequest as HphiTrackingHistoryRequest
        from .curved_hphi_tracking_history_saved import read_curved_hphi_history as read_hphi_history, history_snapshot
        from .curved_hphi_tracking import CurvedHphiTrackingRequest as HphiTrackingRequest
        start=manager.start_curved_hphi_history;extend=manager.extend_curved_hphi_history;pair_kind='curved_hphi_tracking'
    keys(data,ACTIONS[action],ACTIONS[action],'hphi tracking history request')
    media='application/json; charset=utf-8'
    def pair_path(identifier):
        state=manager.status(identifier,verify=True)
        if state.get('status')!='complete' or state.get('kind')!=pair_kind:
            raise ValueError('select a complete verified hphi tracking pair')
        return manager.directory(identifier)
    if action in ('hphi-normalize-history','hphi-start-history'):
        raw=parse_json(data['document']) if isinstance(data['document'],str) else data['document']
        request=HphiTrackingHistoryRequest.from_dict(raw)
        if action=='hphi-normalize-history':return request.to_dict(),media
        identifiers=data['step_ids']
        if type(identifiers) is not list or len(identifiers)!=request.step_count:
            raise ValueError('step_ids must contain exactly step_count tracking pair IDs')
        return {'id':start([pair_path(identifier) for identifier in identifiers],request)},media
    directory=manager.directory(data['id'])
    if action=='hphi-extend-history':
        return {'id':extend(directory,pair_path(data['next_id']))},media
    before=history_snapshot(directory);result=read_hphi_history(directory)
    if action=='hphi-history-result':
        payload=dict(request=result['request'],result=result,state=manager.status(data['id'],verify=True),sources=parse_json((directory/'sources.json').read_text()))
        payload['step_requests']=[HphiTrackingRequest.load(directory/f'step-{index:04d}'/'tracking.json').to_dict() for index in range(result['request']['step_count'])]
    else:
        if before!=history_snapshot(directory):raise ValueError('hphi history changed before source import')
        index=data['index'];side=data['side']
        if type(index) is not int or not 0<=index<result['request']['step_count']:
            raise ValueError('Hphi history step index is out of range')
        if side not in ('previous','current'):raise ValueError('Hphi history side must be previous or current')
        payload={'id':manager.import_hphi_result(directory/f'step-{index:04d}'/side)}
    if before!=history_snapshot(directory):raise ValueError('hphi history changed during GUI response')
    return payload,media

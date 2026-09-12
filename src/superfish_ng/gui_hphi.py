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


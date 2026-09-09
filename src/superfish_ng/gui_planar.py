# SPDX-License-Identifier: Apache-2.0
"""Explicit Cartesian GUI operations on dedicated Projects and verified jobs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from .config import keys
from .jobs import _implementation_hashes, read_job
from .planar_jobs import _native_hashes, KIND
from .planar_project import PlanarProject
from .project import parse_json

ACTIONS = {
    'planar-normalize-study': ['document'], 'planar-start-study': ['document'],
    'planar-study-result': ['id'], 'planar-study-point': ['id', 'index'],
    'planar-normalize': ['document'], 'planar-start': ['document'],
    'planar-import': ['path'], 'planar-result': ['id'],
    'planar-plot': ['id', 'mode', 'mesh', 'length_unit'],
    'planar-probe': ['id', 'mode', 'points_xy_m'],
    'planar-probe-metadata': ['id', 'mode', 'points_xy_m'],
    'planar-download': ['id', 'file'],
}


def planar_response(manager, action, data, render_lock, plot_cache):
    """Return payload and media type; caller enforces local session authentication."""
    if action not in ACTIONS: raise ValueError('unknown planar operation')
    if action in ('planar-normalize-study','planar-start-study','planar-study-result','planar-study-point'):
        return planar_study_response(manager,action,data)
    required = ['document'] if action in ('planar-normalize', 'planar-start') else ['path'] if action=='planar-import' else ['id']
    if action in ('planar-probe', 'planar-probe-metadata'): required += ['points_xy_m']
    if action=='planar-download': required += ['file']
    keys(data, ACTIONS[action], required, 'planar request')
    media = 'application/json; charset=utf-8'
    if action in ('planar-normalize', 'planar-start'):
        document = parse_json(data['document']) if isinstance(data['document'], str) else data['document']
        project = PlanarProject.from_dict(document)
        return ({'id': manager.start_planar(project)} if action=='planar-start' else project.to_dict()), media
    if action=='planar-import':
        return {'id': manager.import_planar_result(data['path'])}, media
    directory = manager.directory(data['id'])
    state = manager.status(data['id'], verify=True)
    if state.get('kind')!=KIND or state.get('status')!='complete':
        raise ValueError('select a complete, verified planar job')
    native = directory/'solution'
    before = _native_hashes(native)
    project = PlanarProject.load(directory/'project.json')
    if action=='planar-result':
        payload = dict(project=project.to_dict(), state=state,
                       result=parse_json((native/'results.json').read_text()), files=sorted(before))
    elif action=='planar-download':
        if data['file'] not in before: raise ValueError('unknown planar native file')
        payload=(native/data['file']).read_bytes();media='application/octet-stream'
    else:
        mode = data.get('mode', 1)
        if type(mode) is not int or not 1 <= mode <= project.case.modes:
            raise ValueError('mode must be a valid one-based mode number')
        plot = action=='planar-plot'
        spec = dict(view='plot' if plot else 'probe', native_sha256=before,
                    implementation_sha256=_implementation_hashes(), mode=mode)
        if plot:
            mesh = data.get('mesh', False);unit=data.get('length_unit', project.display_length_unit)
            if type(mesh) is not bool or unit not in ('m','mm'):
                raise ValueError('planar plot requires boolean mesh and length_unit m or mm')
            from importlib.metadata import version
            spec.update(mesh=mesh,length_unit=unit,matplotlib=version('matplotlib'),numpy=version('numpy'),scipy=version('scipy'))
        else:
            spec['points_xy_m']=data['points_xy_m']
        tag=hashlib.sha256(json.dumps(spec,sort_keys=True,allow_nan=False).encode()).hexdigest()
        path=directory/f'planar-{tag}.{ "png" if plot else "csv" }'
        metadata_path=path.with_suffix(path.suffix+'.json')
        with render_lock:
            if not path.exists():
                if plot:
                    args=[sys.executable,'-m','superfish_ng','plot-planar',str(native),'--out',str(path),'--mode',str(mode),'--length-unit',unit]
                    if mesh:args+=['--mesh']
                    done=subprocess.run(args,capture_output=True,text=True,timeout=120,
                        env={**os.environ,'OPENBLAS_NUM_THREADS':'1','MPLCONFIGDIR':str(plot_cache)})
                    if done.returncode:raise ValueError(done.stderr.strip() or 'planar plot failed')
                else:
                    from .planar_display import export_planar_probe
                    export_planar_probe(native,path,data['points_xy_m'],mode)
            if path.is_symlink() or metadata_path.is_symlink():raise ValueError('planar view cache must not contain links')
            metadata=parse_json(metadata_path.read_text());payload=path.read_bytes()
            if (metadata['native_sha256']!=before or metadata['mode']!=mode
                    or metadata['data_sha256']!=hashlib.sha256(payload).hexdigest()):
                raise ValueError('planar view cache integrity failure')
            if action=='planar-probe-metadata':payload=metadata
            else:media='image/png' if plot else 'text/csv; charset=utf-8'
    if _native_hashes(native)!=before or manager.status(data['id'], verify=True)!=state:
        raise ValueError('planar job changed while preparing GUI response')
    return payload, media


def planar_study_response(manager, action, data):
    from .planar_study import PlanarStudy
    from .planar_study_jobs import read_planar_study, _snapshot
    required=['document'] if action.endswith(('normalize-study','start-study')) else ['id']
    if action=='planar-study-point':required.append('index')
    keys(data,ACTIONS[action],required,'planar Study request')
    media='application/json; charset=utf-8'
    if 'document' in required:
        raw=parse_json(data['document']) if isinstance(data['document'],str) else data['document']
        study=PlanarStudy.from_dict(raw)
        return ({'id':manager.start_planar_study(study)} if action=='planar-start-study' else study.to_dict()),media
    directory=manager.directory(data['id']);study=PlanarStudy.load(directory/'study.json');before=_snapshot(directory,study)
    result=read_planar_study(directory)
    if action=='planar-study-result':
        payload=dict(study=study.to_dict(),result=result,state=manager.status(data['id'],verify=True))
    else:
        index=data['index']
        if type(index) is not int or not 0<=index<len(result['points']):raise ValueError('planar Study point index is out of range')
        if before!=_snapshot(directory,study):raise ValueError('planar Study changed before point import')
        payload={'id':manager.import_planar_result(directory/result['points'][index]['directory'])}
    if before!=_snapshot(directory,study):raise ValueError('planar Study changed during GUI response')
    return payload,media

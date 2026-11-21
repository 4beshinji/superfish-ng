# SPDX-License-Identifier: Apache-2.0
"""Owned original Cartesian P2 comparison operands with complete native replay."""
from pathlib import Path
import shutil
from .config import keys
from .project import parse_json
from .jobs import _digest,_implementation_hashes
from .saved_mode_tracking import _canonical
from .planar_jobs import NATIVE,_native_hashes,_job_hashes,verify_planar_job
from .planar_tuning_saved import _write
from .planar_curved import PlanarCurvedCase
from .planar_curved_saved import read_planar_curved_run
from .planar_curved_tracking import PlanarCurvedTrackingRequest,track_planar_curved_modes
from .planar_curved_tuning import _json_types

FORMAT='superfish_ng_owned_planar_curved_tracking'


def _regular(path,directory=False):
    path=Path(path).absolute()
    if path!=path.resolve() or path.is_symlink() or not (path.is_dir() if directory else path.is_file()):
        raise ValueError('curved tracking requires regular paths without symbolic-link components')
    return path


def _load(path):return parse_json(_regular(path).read_text(encoding='utf-8'))


def _source_snapshot(path,kind,*,strict=False):
    path=_regular(path,True)
    if kind=='planar_curved_native':result=_native_hashes(path);directories=set()
    elif kind=='planar_curved_job':
        result=_job_hashes(path);directories={'solution'}
        if (path/'worker.claim').exists() or (path/'worker.claim').is_symlink():result['worker.claim']=_digest(_regular(path/'worker.claim'))
    else:raise ValueError('curved tracking source kind must be native or completed job')
    for name in result:_regular(path/name)
    if strict:
        entries={p.relative_to(path).as_posix() for p in path.rglob('*')}
        if entries!=set(result)|directories:raise ValueError('owned curved operand requires exactly its declared original files')
    return {name:result[name] for name in sorted(result)}


def _source(path,kind=None,*,strict=False):
    path=_regular(path,True)
    if kind is None:kind='planar_curved_job' if (path/'job.json').exists() else 'planar_curved_native'
    before=_source_snapshot(path,kind,strict=strict)
    solution=(verify_planar_job(path,_load(path/'job.json'),_load(path/'manifest.json'))
              if kind=='planar_curved_job' else read_planar_curved_run(path))
    if type(solution.case) is not PlanarCurvedCase:raise ValueError('dedicated curved tracking requires complete Case schema_version 3')
    if before!=_source_snapshot(path,kind,strict=strict):raise ValueError('curved operand changed during native verification')
    return solution,dict(path=str(path),kind=kind,files=before)


def _check_sources(document,directory):
    _json_types(document)
    names=['format','sources_version','previous','current'];keys(document,names,names,'owned curved tracking sources')
    if document['format']!='superfish_ng_planar_curved_tracking_sources' or type(document['sources_version']) is not int or document['sources_version']!=1:
        raise ValueError('expected curved tracking sources_version 1')
    for side in ('previous','current'):
        source=document[side];keys(source,['path','kind','files'],['path','kind','files'],'curved operand source')
        if type(source['path']) is not str or not source['path']:raise ValueError('curved source path requires a nonempty informational origin')
        actual=_source_snapshot(directory/side,source['kind'],strict=True)
        if source['files']!=actual:raise ValueError('owned curved operand differs from its original source hashes')


def _input_hashes(directory):
    directory=_regular(directory,True)
    if {p.name for p in directory.iterdir()}!={'tracking.json','sources.json','tracking-results.json','manifest.json','previous','current'}:
        raise ValueError('owned curved pair requires exactly request, sources, result, manifest and both operands')
    sources=_load(directory/'sources.json');_check_sources(sources,directory)
    result={name:_digest(_regular(directory/name)) for name in ('tracking.json','sources.json')}
    for side in ('previous','current'):
        result.update({f'{side}/{name}':value for name,value in sources[side]['files'].items()})
    return result


def curved_tracking_snapshot(directory):
    directory=Path(directory);result=_input_hashes(directory)
    for name in ('tracking-results.json','manifest.json'):_load(directory/name);result[name]=_digest(directory/name)
    return result


def _read_verified(directory):
    directory=_regular(directory,True);before=curved_tracking_snapshot(directory)
    manifest=_load(directory/'manifest.json')
    names=['format','saved_version','files','implementation_sha256','source_changed_during_run']
    keys(manifest,names,names,'owned curved pair manifest')
    implementation=manifest['implementation_sha256']
    if (manifest['format']!=FORMAT or type(manifest['saved_version']) is not int or manifest['saved_version']!=1
            or manifest['source_changed_during_run'] is not False or type(implementation) is not dict or not implementation
            or any(type(k) is not str or type(v) is not str or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for k,v in implementation.items())):
        raise ValueError('owned curved pair requires stable implementation provenance version 1')
    if manifest['files']!={k:v for k,v in before.items() if k!='manifest.json'}:raise ValueError('curved manifest must bind the complete request and both original operands')
    request=PlanarCurvedTrackingRequest.load(directory/'tracking.json')
    sources=_load(directory/'sources.json');current_implementation=_implementation_hashes()
    solutions=[_source(directory/side,sources[side]['kind'],strict=True)[0] for side in ('previous','current')]
    expected=track_planar_curved_modes(*solutions,request)
    if _canonical(expected)!=_canonical(_load(directory/'tracking-results.json')):raise ValueError('owned curved tracking differs from complete original E/H and finite-guard replay')
    if before!=curved_tracking_snapshot(directory):raise ValueError('owned curved pair changed during complete replay')
    if current_implementation!=_implementation_hashes():raise RuntimeError('implementation changed during curved pair replay')
    return expected,solutions


def read_owned_planar_curved_tracking(directory):return _read_verified(directory)[0]


def execute_owned_planar_curved_tracking(previous,current,request,directory):
    """Compare verified source fields, then own all exact bytes in a new pair."""
    if type(request) is not PlanarCurvedTrackingRequest:raise ValueError('expected PlanarCurvedTrackingRequest')
    request=PlanarCurvedTrackingRequest.from_dict(request.to_dict());implementation=_implementation_hashes()
    operands=[_source(p) for p in (previous,current)]
    result=track_planar_curved_modes(*(o[0] for o in operands),request)
    directory=Path(directory).absolute()
    if directory!=directory.resolve():raise ValueError('curved pair output must have no symbolic-link components')
    directory.mkdir(parents=True,exist_ok=False)
    request.save(directory/'tracking.json')
    sources=dict(format='superfish_ng_planar_curved_tracking_sources',sources_version=1,
        previous=operands[0][1],current=operands[1][1])
    _write(directory/'sources.json',sources);_write(directory/'tracking-results.json',result)
    for side,(_,source) in zip(('previous','current'),operands):
        target=directory/side;target.mkdir()
        if _source_snapshot(source['path'],source['kind'])!=source['files']:raise ValueError('curved source changed before copying')
        for name in source['files']:
            destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(Path(source['path'])/name,destination)
        if (_source_snapshot(source['path'],source['kind'])!=source['files']
                or _source_snapshot(target,source['kind'],strict=True)!=source['files']):
            raise ValueError('curved source changed during exact operand copying')
    for _,source in operands:
        if _source_snapshot(source['path'],source['kind'])!=source['files']:
            raise ValueError('curved source changed during complete operand copying')
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during curved pair execution')
    # The manifest itself is created last; input helper expects its presence.
    inputs={name:_digest(directory/name) for name in ('tracking.json','sources.json','tracking-results.json')}
    for side in ('previous','current'):inputs.update({f'{side}/{name}':value for name,value in sources[side]['files'].items()})
    _write(directory/'manifest.json',dict(format=FORMAT,saved_version=1,files=inputs,
        implementation_sha256=implementation,source_changed_during_run=False))
    if {k:v for k,v in curved_tracking_snapshot(directory).items() if k!='manifest.json'}!=inputs:
        raise ValueError('curved pair changed during completion')
    for _,source in operands:
        if _source_snapshot(source['path'],source['kind'])!=source['files']:
            raise ValueError('curved source changed during completion')
    return result

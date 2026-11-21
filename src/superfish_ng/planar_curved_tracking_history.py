# SPDX-License-Identifier: Apache-2.0
"""Owned ordered Cartesian P2 comparisons and earlier-native ID recovery."""
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import shutil
from .config import integer,keys
from .project import parse_json
from .jobs import _digest,_implementation_hashes
from .saved_mode_tracking import _canonical
from .planar_jobs import NATIVE
from .planar_tuning_saved import _write
from .planar_tracking_history import _current_groups,_canonical_groups
from .planar_curved_tracking import PlanarCurvedTrackingRequest
from .planar_curved_identity_recovery import PlanarCurvedIdentityRecoveryRequest,recover_planar_curved_modes
from .planar_curved_tracking_saved import (_regular,_load,curved_tracking_snapshot,_read_verified)


@dataclass(frozen=True)
class PlanarCurvedTrackingHistoryRequest:
    step_count:int
    max_steps:int=100
    identity_recoveries:tuple=()

    def __post_init__(self):
        integer(self.step_count,'curved history step_count');integer(self.max_steps,'curved history max_steps')
        if self.step_count>self.max_steps:raise ValueError('curved history step_count exceeds max_steps')
        if type(self.identity_recoveries) not in (list,tuple):raise ValueError('curved history recoveries require an ordered array')
        events=[];last=-1
        for event in self.identity_recoveries:
            keys(event,['after_step_index','request'],['after_step_index','request'],'curved history recovery placement')
            index=integer(event['after_step_index'],'after_step_index',0)
            if not last<index<self.step_count:raise ValueError('curved history recovery steps must increase within the history')
            recovery=PlanarCurvedIdentityRecoveryRequest.from_dict(event['request'])
            if recovery.anchor_snapshot_index>index:raise ValueError('curved history recovery anchor must precede its current snapshot')
            events.append(dict(after_step_index=index,request=recovery.to_dict()));last=index
        object.__setattr__(self,'identity_recoveries',tuple(events))

    def to_dict(self):
        return dict(format='superfish_ng_planar_curved_tracking_history_request',history_version=1,
            step_count=self.step_count,max_steps=self.max_steps,identity_recoveries=deepcopy(list(self.identity_recoveries)))

    @classmethod
    def from_dict(cls,data):
        names=['format','history_version','step_count','max_steps','identity_recoveries'];keys(data,names,names,'curved history request')
        if (data['format']!='superfish_ng_planar_curved_tracking_history_request' or type(data['history_version']) is not int
                or data['history_version']!=1 or type(data['identity_recoveries']) is not list):
            raise ValueError('expected curved history_version 1 with an explicit recovery array')
        return cls(data['step_count'],data['max_steps'],data['identity_recoveries'])

    @classmethod
    def load(cls,path):return cls.from_dict(_load(path))

    def save(self,path):_write(path,self.to_dict())


def _native_part(snapshot,directory,side):
    sources=_load(Path(directory)/'sources.json')
    prefix=side+'/' + ('solution/' if sources[side]['kind']=='planar_curved_job' else '')
    return {name:snapshot[prefix+name] for name in NATIVE}


def _link(previous,current,previous_snapshot,current_snapshot,previous_directory,current_directory):
    if previous['status']!='PASS':raise ValueError('curved history cannot continue after an UNVERIFIED correspondence')
    if _native_part(previous_snapshot,previous_directory,'current')!=_native_part(current_snapshot,current_directory,'previous'):
        raise ValueError('curved history original native continuity differs between adjacent steps')
    request=current['request']
    if request['previous_mode_count']!=previous['request']['current_mode_count']:
        raise ValueError('curved history tracked band count differs between adjacent steps')
    if request['previous_mode_ids'] is not None:
        if not previous['individual_ids_complete'] or request['previous_mode_ids']!=previous['current_mode_ids']:
            raise ValueError('curved history IDs differ or replace an unresolved ID set')
    elif _canonical_groups(request['previous_identity_groups'])!=_current_groups(previous):
        raise ValueError('curved history inherited ID group continuity differs')


def verify_planar_curved_history_steps(paths,request):
    """Replay all operands, chains and recoveries; original bands stay intact."""
    if type(request) is not PlanarCurvedTrackingHistoryRequest:raise ValueError('expected PlanarCurvedTrackingHistoryRequest')
    request=PlanarCurvedTrackingHistoryRequest.from_dict(request.to_dict())
    if type(paths) not in (list,tuple) or len(paths)!=request.step_count:raise ValueError('curved history requires exactly step_count owned pairs')
    directories=[_regular(p,True) for p in paths]
    if len(set(directories))!=len(directories):raise ValueError('curved history pair directories must be distinct')
    implementation=_implementation_hashes();before=[curved_tracking_snapshot(p) for p in directories]
    steps=[];positions=[];events=[];effective=None
    placements={e['after_step_index']:e['request'] for e in request.identity_recoveries}
    for index,path in enumerate(directories):
        current,solutions=_read_verified(path)
        if steps:_link(effective,current,before[index-1],before[index],directories[index-1],path)
        else:
            initial=current['request'];ids=initial['previous_mode_ids']
            if ids is None:
                ids=[None]*initial['previous_mode_count']
                for group in initial['previous_identity_groups']:
                    if len(group['indices'])==1:ids[group['indices'][0]-1]=group['ids'][0]
            resolved=all(type(value) is str for value in ids) and all(len(group)==1
                for group in current['spectral_resolution_groups'][0] if min(group)<=initial['previous_mode_count'])
            positions.append(dict(ids=ids,resolved=resolved,solution=solutions[0],
                files=_native_part(before[0],path,'previous')))
        steps.append(current);effective=current
        if index in placements:
            recovery=PlanarCurvedIdentityRecoveryRequest.from_dict(placements[index])
            anchor=positions[recovery.anchor_snapshot_index]
            if not anchor['resolved'] or list(recovery.comparison.previous_mode_ids)!=anchor['ids']:
                raise ValueError('curved recovery anchor does not bind its actual earlier resolved IDs')
            event=recover_planar_curved_modes(anchor['solution'],solutions[0],solutions[1],
                PlanarCurvedTrackingRequest.from_dict(current['request']),recovery,current_snapshot_index=index+1)
            if _canonical(event['inherited'])!=_canonical(current):raise ValueError('curved recovery inherited comparison changed during replay')
            event.update(after_step_index=index,anchor_native_sha256=anchor['files']);events.append(event)
            effective=dict(current,status=event['status'],individual_ids_complete=False,current_mode_ids=[None]*current['request']['current_mode_count'])
            if event['assessment'] is not None:
                assessment=event['assessment']
                effective.update(current_mode_ids=assessment['current_mode_ids'],individual_ids_complete=assessment['individual_ids_complete'],
                    matches=[dict(current_indices=g['indices'],previous_ids=g['ids']) for g in assessment['current_identity_groups']])
        positions.append(dict(ids=effective['current_mode_ids'],resolved=effective['status']=='PASS' and effective['individual_ids_complete'],
            solution=solutions[1],files=_native_part(before[index],path,'current')))
    if before!=[curved_tracking_snapshot(p) for p in directories]:raise ValueError('curved history ancestry changed during complete replay')
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during curved ancestry replay')
    passed=effective['status']=='PASS';can_extend=passed and request.step_count<request.max_steps
    return dict(format='superfish_ng_planar_curved_tracking_history_result',history_version=1,request=request.to_dict(),
        status=effective['status'],can_extend=can_extend,
        stop_reason=None if can_extend else 'history max_steps reached; extension forbidden' if passed else 'last correspondence is UNVERIFIED; extension forbidden',
        individual_ids_complete=effective['individual_ids_complete'],current_mode_ids=effective['current_mode_ids'],
        current_identity_groups=_current_groups(effective) if passed else None,current_mode_count=effective['request']['current_mode_count'],
        step_sha256=before,steps=steps,identity_recoveries=events,
        scope='fully replayed original Cartesian P2 native chain with explicit earlier-anchor E/H recovery inside inherited ID sets; no continuous-path identity, continuum or surface-peak certificate')


def _paths(directory,request):return [directory/f'step-{index:04d}' for index in range(request.step_count)]


def _inputs(directory):
    directory=_regular(directory,True);request=PlanarCurvedTrackingHistoryRequest.load(directory/'history.json')
    expected={'history.json','sources.json','history-results.json','manifest.json',*[p.name for p in _paths(directory,request)]}
    if {p.name for p in directory.iterdir()}!=expected:raise ValueError('curved history requires exactly its declared ordered steps and metadata')
    sources=_load(directory/'sources.json');names=['format','sources_version','steps'];keys(sources,names,names,'curved history sources')
    if (sources['format']!='superfish_ng_planar_curved_history_sources' or type(sources['sources_version']) is not int
            or sources['sources_version']!=1 or type(sources['steps']) is not list or len(sources['steps'])!=request.step_count):
        raise ValueError('curved history sources differ from requested steps')
    result={name:_digest(directory/name) for name in ('history.json','sources.json')}
    for path,source in zip(_paths(directory,request),sources['steps']):
        keys(source,['path','files'],['path','files'],'curved history step source')
        if type(source['path']) is not str or not source['path']:raise ValueError('curved history requires an informational step origin')
        snapshot=curved_tracking_snapshot(path)
        if source['files']!=snapshot:raise ValueError('owned curved step differs from its full original snapshot')
        result.update({f'{path.name}/{name}':value for name,value in snapshot.items()})
    return result


def curved_history_snapshot(directory):
    directory=Path(directory);result=_inputs(directory)
    for name in ('history-results.json','manifest.json'):_load(directory/name);result[name]=_digest(directory/name)
    return result


def read_owned_planar_curved_history(directory):
    directory=_regular(directory,True);before=curved_history_snapshot(directory);manifest=_load(directory/'manifest.json')
    names=['format','saved_version','files','implementation_sha256','source_changed_during_run'];keys(manifest,names,names,'curved history manifest')
    implementation=manifest['implementation_sha256']
    if (manifest['format']!='superfish_ng_owned_planar_curved_tracking_history' or type(manifest['saved_version']) is not int
            or manifest['saved_version']!=1 or manifest['source_changed_during_run'] is not False
            or type(implementation) is not dict or not implementation or any(type(k) is not str or type(v) is not str or len(v)!=64
                or any(c not in '0123456789abcdef' for c in v) for k,v in implementation.items())):
        raise ValueError('curved history requires stable implementation provenance version 1')
    if manifest['files']!={k:v for k,v in before.items() if k!='manifest.json'}:raise ValueError('curved history manifest must bind all owned ancestry')
    request=PlanarCurvedTrackingHistoryRequest.load(directory/'history.json')
    expected=verify_planar_curved_history_steps(_paths(directory,request),request)
    if _canonical(expected)!=_canonical(_load(directory/'history-results.json')):raise ValueError('curved history differs from complete original ancestry replay')
    if before!=curved_history_snapshot(directory):raise ValueError('curved history changed during full replay')
    return expected


def execute_owned_planar_curved_history(paths,request,directory):
    implementation=_implementation_hashes();result=verify_planar_curved_history_steps(paths,request)
    request=PlanarCurvedTrackingHistoryRequest.from_dict(result['request']);paths=[_regular(p,True) for p in paths]
    directory=Path(directory).absolute()
    if directory!=directory.resolve():raise ValueError('curved history output must have no symbolic-link components')
    directory.mkdir(parents=True,exist_ok=False);request.save(directory/'history.json')
    sources=dict(format='superfish_ng_planar_curved_history_sources',sources_version=1,
        steps=[dict(path=str(path),files=snapshot) for path,snapshot in zip(paths,result['step_sha256'])])
    _write(directory/'sources.json',sources);_write(directory/'history-results.json',result)
    for index,(path,snapshot) in enumerate(zip(paths,result['step_sha256'])):
        if curved_tracking_snapshot(path)!=snapshot:raise ValueError('curved history source changed before copying')
        target=directory/f'step-{index:04d}';target.mkdir()
        for name in snapshot:
            destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path/name,destination)
        if curved_tracking_snapshot(path)!=snapshot or curved_tracking_snapshot(target)!=snapshot:raise ValueError('curved history source changed during copying')
    for path,snapshot in zip(paths,result['step_sha256']):
        if curved_tracking_snapshot(path)!=snapshot:raise ValueError('curved history source changed during complete step copying')
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during curved history execution')
    inputs={name:_digest(directory/name) for name in ('history.json','sources.json','history-results.json')}
    for index,snapshot in enumerate(result['step_sha256']):inputs.update({f'step-{index:04d}/{name}':value for name,value in snapshot.items()})
    _write(directory/'manifest.json',dict(format='superfish_ng_owned_planar_curved_tracking_history',saved_version=1,
        files=inputs,implementation_sha256=implementation,source_changed_during_run=False))
    if {k:v for k,v in curved_history_snapshot(directory).items() if k!='manifest.json'}!=inputs:raise ValueError('curved history changed during completion')
    for path,snapshot in zip(paths,result['step_sha256']):
        if curved_tracking_snapshot(path)!=snapshot:raise ValueError('curved history source changed during completion')
    return result


def extend_owned_planar_curved_history(history,next_pair,directory,*,recovery=None):
    history=_regular(history,True);before=curved_history_snapshot(history);previous=read_owned_planar_curved_history(history)
    if not previous['can_extend']:raise ValueError(previous['stop_reason'])
    old=PlanarCurvedTrackingHistoryRequest.from_dict(previous['request']);events=list(old.identity_recoveries)
    if recovery is not None:
        if type(recovery) is not PlanarCurvedIdentityRecoveryRequest:raise ValueError('expected PlanarCurvedIdentityRecoveryRequest')
        events.append(dict(after_step_index=old.step_count,request=recovery.to_dict()))
    request=PlanarCurvedTrackingHistoryRequest(old.step_count+1,old.max_steps,events)
    result=execute_owned_planar_curved_history([*_paths(history,old),next_pair],request,directory)
    if before!=curved_history_snapshot(history):raise ValueError('curved source history changed during extension')
    return result


def recover_owned_planar_curved_history(history,recovery,directory):
    history=_regular(history,True);before=curved_history_snapshot(history);previous=read_owned_planar_curved_history(history)
    old=PlanarCurvedTrackingHistoryRequest.from_dict(previous['request']);last=previous['steps'][-1]
    if (last['status']!='PASS' or last['individual_ids_complete']
            or any(e['after_step_index']==old.step_count-1 for e in old.identity_recoveries)):
        raise ValueError('curved history recovery requires an unresolved passed final subspace without an earlier recovery event')
    if type(recovery) is not PlanarCurvedIdentityRecoveryRequest:raise ValueError('expected PlanarCurvedIdentityRecoveryRequest')
    request=PlanarCurvedTrackingHistoryRequest(old.step_count,old.max_steps,
        [*old.identity_recoveries,dict(after_step_index=old.step_count-1,request=recovery.to_dict())])
    result=execute_owned_planar_curved_history(_paths(history,old),request,directory)
    if before!=curved_history_snapshot(history):raise ValueError('curved source history changed during recovery')
    return result

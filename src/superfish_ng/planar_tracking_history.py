# SPDX-License-Identifier: Apache-2.0
"""Full saved-spectrum and identity continuity for ordered planar tracking."""
from dataclasses import dataclass
from pathlib import Path
import json
from .config import integer, keys
from .project import parse_json
from .planar_tracking_jobs import _snapshot, read_planar_tracking
from .planar_identity_recovery import PlanarIdentityRecoveryRequest, recover_planar_modes
from .planar_tracking import PlanarTrackingRequest
from .planar_saved import read_planar_run


@dataclass(frozen=True)
class PlanarTrackingHistoryRequest:
    step_count: int
    max_steps: int = 100
    identity_recoveries: tuple = ()

    def __post_init__(self):
        integer(self.step_count, 'history step_count')
        integer(self.max_steps, 'history max_steps')
        if self.step_count > self.max_steps:
            raise ValueError('planar history step_count exceeds max_steps')
        if type(self.identity_recoveries) not in (list, tuple):
            raise ValueError('planar history identity_recoveries must be an ordered array')
        events = []; last = -1
        for event in self.identity_recoveries:
            keys(event, ['after_step_index', 'request'], ['after_step_index', 'request'], 'planar history recovery placement')
            index = event['after_step_index']; integer(index, 'after_step_index', 0)
            if not last < index < self.step_count:
                raise ValueError('planar history recovery steps must increase within the history')
            recovery = PlanarIdentityRecoveryRequest.from_dict(event['request'])
            if recovery.anchor_snapshot_index > index:
                raise ValueError('planar history recovery anchor must precede its current snapshot')
            events.append(dict(after_step_index=index, request=recovery.to_dict())); last = index
        object.__setattr__(self, 'identity_recoveries', tuple(events))

    def to_dict(self):
        result = dict(format='superfish_ng_planar_tracking_history_request', history_version=1,
                    step_count=self.step_count, max_steps=self.max_steps)
        if self.identity_recoveries:
            result.update(history_version=2, identity_recoveries=json.loads(json.dumps(self.identity_recoveries)))
        return result

    @classmethod
    def from_dict(cls, data):
        names=['format','history_version','step_count','max_steps']
        if type(data) is dict and type(data.get('history_version')) is int and data['history_version'] == 2:
            names.append('identity_recoveries')
        keys(data,names,names,'planar tracking history request')
        if (data['format']!='superfish_ng_planar_tracking_history_request'
                or type(data['history_version']) is not int or data['history_version'] not in (1, 2)):
            raise ValueError('expected superfish_ng_planar_tracking_history_request history_version 1 or 2')
        events = data.get('identity_recoveries', ())
        if data['history_version'] == 2 and (type(events) is not list or not events):
            raise ValueError('planar history version 2 requires nonempty identity_recoveries')
        return cls(data['step_count'],data['max_steps'],events)

    @classmethod
    def load(cls, path):
        return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def save(self, path):
        with Path(path).open('x',encoding='utf-8') as stream:
            stream.write(json.dumps(self.to_dict(),ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def _current_groups(result):
    return sorted([dict(indices=match['current_indices'],ids=sorted(match['previous_ids']))
                   for match in result['matches']],key=lambda group:group['indices'][0])


def _canonical_groups(groups):
    return sorted([dict(indices=group['indices'],ids=sorted(group['ids']))
                   for group in groups],key=lambda group:group['indices'][0])


def _native_part(snapshot, side):
    prefix=side+'/'
    return {name[len(prefix):]:value for name,value in snapshot.items() if name.startswith(prefix)}


def _verify_link(previous, current, previous_snapshot, current_snapshot):
    if previous['status']!='PASS':
        raise ValueError('planar history cannot continue after an UNVERIFIED correspondence')
    if _native_part(previous_snapshot,'current')!=_native_part(current_snapshot,'previous'):
        raise ValueError('planar history native spectrum continuity differs between adjacent steps')
    request=current['request']
    if request['previous_mode_count']!=previous['request']['current_mode_count']:
        raise ValueError('planar history tracked band count differs between adjacent steps')
    if request['previous_mode_ids'] is not None:
        if (not previous['individual_ids_complete']
                or request['previous_mode_ids']!=previous['current_mode_ids']):
            raise ValueError('planar history individual IDs differ or replace an unresolved ID set')
    elif _canonical_groups(request['previous_identity_groups'])!=_current_groups(previous):
        raise ValueError('planar history ID group continuity differs between adjacent steps')


def verify_planar_history_steps(paths, request):
    """Replay every complete pair before validating the discrete ordered chain.

    A passed subspace can continue as an ID set. An unresolved final pair is
    retained as evidence but blocks further extension. This proves only the
    owned saved-spectrum chain, not a continuous physical path between samples.
    """
    if not isinstance(request,PlanarTrackingHistoryRequest):
        raise ValueError('expected PlanarTrackingHistoryRequest')
    request=PlanarTrackingHistoryRequest.from_dict(request.to_dict())
    if type(paths) not in (list,tuple) or len(paths)!=request.step_count:
        raise ValueError('planar history requires exactly step_count saved tracking directories')
    directories=[Path(path) for path in paths]
    # The full snapshots include both native copies and every pair document.
    before=[_snapshot(path) for path in directories]
    verified=[]; effective=None; positions=[]; recoveries=[]
    placements={event['after_step_index']: event['request'] for event in request.identity_recoveries}
    for index,path in enumerate(directories):
        current=read_planar_tracking(path)
        if verified:
            _verify_link(effective,current,before[index-1],before[index])
        else:
            initial = current['request']; ids = initial['previous_mode_ids']
            if ids is None:
                ids = [None]*initial['previous_mode_count']
                for group in initial['previous_identity_groups']:
                    if len(group['indices']) == 1:
                        ids[group['indices'][0]-1] = group['ids'][0]
            resolved = all(type(value) is str for value in ids) and all(
                len(group) == 1 for group in current['spectral_resolution_groups'][0]
                if min(group) <= initial['previous_mode_count'])
            positions.append(dict(ids=ids, resolved=resolved, directory=path/'previous',
                                  files=_native_part(before[0], 'previous')))
        verified.append(current)
        effective=current
        if index in placements:
            recovery=PlanarIdentityRecoveryRequest.from_dict(placements[index])
            anchor=positions[recovery.anchor_snapshot_index]
            if not anchor['resolved'] or list(recovery.comparison.previous_mode_ids) != anchor['ids']:
                raise ValueError('planar history recovery anchor does not bind its earlier resolved IDs')
            event=recover_planar_modes(read_planar_run(anchor['directory']), read_planar_run(path/'previous'),
                read_planar_run(path/'current'), PlanarTrackingRequest.from_dict(current['request']), recovery,
                current_snapshot_index=index+1)
            if json.dumps(event['inherited'],sort_keys=True) != json.dumps(current,sort_keys=True):
                raise ValueError('planar history recovery inherited comparison changed')
            event.update(after_step_index=index, anchor_native_sha256=anchor['files'])
            recoveries.append(event)
            effective=dict(current, status=event['status'], individual_ids_complete=False)
            if event['assessment'] is not None:
                assessment=event['assessment']
                effective.update(current_mode_ids=assessment['current_mode_ids'],
                    individual_ids_complete=assessment['individual_ids_complete'],
                    matches=[dict(current_indices=g['indices'],previous_ids=g['ids'])
                             for g in assessment['current_identity_groups']])
        positions.append(dict(ids=effective['current_mode_ids'],
                              resolved=effective['status']=='PASS' and effective['individual_ids_complete'],
                              directory=path/'current', files=_native_part(before[index], 'current')))
    if before!=[_snapshot(path) for path in directories]:
        raise ValueError('planar history ancestry changed during full replay')
    last=effective;passed=last['status']=='PASS'
    can_extend=passed and request.step_count<request.max_steps
    stop_reason=(None if can_extend else 'history max_steps budget reached; extension is forbidden' if passed
                 else 'last correspondence is UNVERIFIED; history extension is forbidden')
    result = dict(format='superfish_ng_planar_tracking_history_result',history_version=1,
                request=request.to_dict(),status=last['status'],can_extend=can_extend,
                stop_reason=stop_reason,
                individual_ids_complete=last['individual_ids_complete'],
                current_mode_ids=last['current_mode_ids'],
                current_identity_groups=_current_groups(last) if passed else None,
                current_mode_count=last['request']['current_mode_count'],
                step_sha256=before,steps=verified,
                scope='ordered fully replayed planar native snapshots and identity groups; no continuous-path identity or physical error bound')
    if request.identity_recoveries:
        result.update(history_version=2, identity_recoveries=recoveries,
                      scope='ordered owned planar native snapshots with explicit earlier-anchor recovery inside inherited ID sets; no continuous-path identity or physical error bound')
    return result

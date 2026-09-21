# SPDX-License-Identifier: Apache-2.0
"""Full saved-spectrum and identity continuity for ordered hphi tracking."""
from dataclasses import dataclass
from pathlib import Path
import json
from .config import integer, keys
from .project import parse_json
from .curved_hphi_tracking_jobs import _snapshot, read_curved_hphi_tracking


@dataclass(frozen=True)
class CurvedHphiTrackingHistoryRequest:
    step_count: int
    max_steps: int = 100
    recoveries: object = None

    def __post_init__(self):
        integer(self.step_count, 'history step_count')
        integer(self.max_steps, 'history max_steps')
        if self.step_count > self.max_steps:
            raise ValueError('hphi history step_count exceeds max_steps')
        if self.recoveries is not None:
            from .curved_hphi_identity_recovery import CurvedHphiIdentityRecoveryRequest
            if type(self.recoveries) is not list or not self.recoveries:
                raise ValueError('recovered Hphi history requires nonempty recovery placements')
            normalized=[];last=-1
            for placement in self.recoveries:
                keys(placement,['after_step_index','request'],['after_step_index','request'],'Hphi recovery placement')
                index=integer(placement['after_step_index'],'after_step_index',0)
                if not last<index<self.step_count:
                    raise ValueError('recovery placements must be increasing distinct indices within the history')
                recovery=CurvedHphiIdentityRecoveryRequest.from_dict(placement['request'])
                if recovery.anchor_snapshot_index>=index+1:
                    raise ValueError('recovery anchor must precede its current history snapshot')
                normalized.append(dict(after_step_index=index,request=recovery.to_dict()));last=index
            object.__setattr__(self,'recoveries',normalized)

    def to_dict(self):
        data=dict(format='superfish_ng_curved_hphi_tracking_history_request', history_version=1,
                  step_count=self.step_count, max_steps=self.max_steps)
        if self.recoveries is not None:
            data.update(history_version=2,recoveries=json.loads(json.dumps(self.recoveries)))
        return data

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data,dict):raise ValueError('Hphi history request must be an object')
        version=data.get('history_version')
        if type(version) is not int or version not in (1,2):
            raise ValueError('expected Hphi history_version 1 or 2')
        names=['format','history_version','step_count','max_steps']+(['recoveries'] if version==2 else [])
        keys(data,names,names,'hphi tracking history request')
        if data['format']!='superfish_ng_curved_hphi_tracking_history_request':
            raise ValueError('expected superfish_ng_curved_hphi_tracking_history_request')
        if version==2 and data['recoveries'] is None:
            raise ValueError('history_version 2 requires explicit recovery placements')
        return cls(data['step_count'],data['max_steps'],data.get('recoveries'))

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
    # Import-job bookkeeping and display units may differ. The actual saved
    # spectrum must be byte-identical across adjacent steps. Every Project
    # and job document is independently bound by the full pair replay.
    prefix=side+'/solution/'
    native={name[len(prefix):]:value for name,value in snapshot.items() if name.startswith(prefix)}
    if set(native)!={'case.json','mesh.npz','fields.npz','results.json','manifest.json'}:
        raise ValueError('Hphi history requires a complete five-file native spectrum')
    return native


def _verify_link(previous, current, previous_snapshot, current_snapshot, previous_groups=None):
    if previous['status']!='PASS':
        raise ValueError('hphi history cannot continue after an UNVERIFIED correspondence')
    if _native_part(previous_snapshot,'current')!=_native_part(current_snapshot,'previous'):
        raise ValueError('hphi history native spectrum continuity differs between adjacent steps')
    request=current['request']
    if request['previous_mode_count']!=previous['request']['current_mode_count']:
        raise ValueError('hphi history tracked band count differs between adjacent steps')
    if request['previous_mode_ids'] is not None:
        if (not previous['individual_ids_complete']
                or request['previous_mode_ids']!=previous['current_mode_ids']):
            raise ValueError('hphi history individual IDs differ or replace an unresolved ID set')
    elif _canonical_groups(request['previous_identity_groups'])!=(previous_groups if previous_groups is not None else _current_groups(previous)):
        raise ValueError('hphi history ID group continuity differs between adjacent steps')


def verify_curved_hphi_history_steps(paths, request):
    """Replay every complete pair before validating the discrete ordered chain.

    A passed subspace can continue as an ID set. An unresolved final pair is
    retained as evidence but blocks further extension. This proves only the
    owned saved-spectrum chain, not a continuous physical path between samples.
    """
    if not isinstance(request,CurvedHphiTrackingHistoryRequest):
        raise ValueError('expected CurvedHphiTrackingHistoryRequest')
    request=CurvedHphiTrackingHistoryRequest.from_dict(request.to_dict())
    if type(paths) not in (list,tuple) or len(paths)!=request.step_count:
        raise ValueError('hphi history requires exactly step_count saved tracking directories')
    directories=[Path(path) for path in paths]
    if request.recoveries is not None:
        from .curved_hphi_recovered_history import verify_recovered_curved_hphi_history_steps
        return verify_recovered_curved_hphi_history_steps(directories,request)
    # The full snapshots include both native copies and every pair document.
    before=[_snapshot(path) for path in directories]
    verified=[]
    for index,path in enumerate(directories):
        current=read_curved_hphi_tracking(path)
        if verified:
            _verify_link(verified[-1],current,before[index-1],before[index])
        verified.append(current)
    if before!=[_snapshot(path) for path in directories]:
        raise ValueError('hphi history ancestry changed during full replay')
    last=verified[-1];passed=last['status']=='PASS'
    can_extend=passed and request.step_count<request.max_steps
    stop_reason=(None if can_extend else 'history max_steps budget reached; extension is forbidden' if passed
                 else 'last correspondence is UNVERIFIED; history extension is forbidden')
    return dict(format='superfish_ng_curved_hphi_tracking_history_result',history_version=1,
                request=request.to_dict(),status=last['status'],can_extend=can_extend,
                stop_reason=stop_reason,
                individual_ids_complete=last['individual_ids_complete'],
                current_mode_ids=last['current_mode_ids'],
                current_identity_groups=_current_groups(last) if passed else None,
                current_mode_count=last['request']['current_mode_count'],
                step_sha256=before,steps=verified,
                scope='ordered fully replayed hphi native snapshots and identity groups; no continuous-path identity or physical error bound')

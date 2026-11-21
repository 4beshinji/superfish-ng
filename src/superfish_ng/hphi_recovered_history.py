# SPDX-License-Identifier: Apache-2.0
"""Replay owned Hphi history recovery placements without losing native ancestry."""
from .hphi_native import read_hphi_run
from .hphi_tracking import HphiTrackingRequest
from .hphi_tracking_jobs import _snapshot, read_hphi_tracking
from .hphi_tracking_history import _current_groups, _native_part, _verify_link
from .hphi_identity_recovery import HphiIdentityRecoveryRequest, recover_hphi_modes


def verify_recovered_hphi_history_steps(directories, request):
    before=[_snapshot(path) for path in directories]
    placements={item['after_step_index']:item['request'] for item in request.recoveries}
    verified=[];events=[];positions=[];effective=None;groups=None
    for index,path in enumerate(directories):
        current=read_hphi_tracking(path)
        if effective is not None:
            _verify_link(effective,current,before[index-1],before[index],previous_groups=groups)
        else:
            initial=current['request']
            ids=initial['previous_mode_ids']
            positions.append(dict(status='PASS',individual_ids_complete=ids is not None,
                                  current_mode_ids=ids,location=path/'previous'/'solution',
                                  native_sha256=_native_part(before[0],'previous')))
        verified.append(current)
        effective=current
        groups=_current_groups(current) if current['status']=='PASS' else None
        if index in placements:
            recovery=HphiIdentityRecoveryRequest.from_dict(placements[index])
            anchor=positions[recovery.anchor_snapshot_index]
            if anchor['status']!='PASS' or not anchor['individual_ids_complete']:
                raise ValueError('Hphi history recovery anchor lacks verified individual IDs')
            if list(recovery.comparison.previous_mode_ids)!=anchor['current_mode_ids']:
                raise ValueError('recovery anchor IDs differ from the owned history snapshot')
            native_request=HphiTrackingRequest.load(path/'tracking.json')
            event=recover_hphi_modes(read_hphi_run(anchor['location']),
                read_hphi_run(path/'previous'/'solution'),read_hphi_run(path/'current'/'solution'),
                native_request,recovery,current_snapshot_index=index+1)
            if event['inherited']!=current:
                raise ValueError('inherited correspondence changed during recovery replay')
            event.update(after_step_index=index,anchor_native_sha256=anchor['native_sha256'],
                         current_native_sha256=_native_part(before[index],'current'))
            events.append(event)
            assessment=event['assessment']
            if assessment is not None:
                effective={**current,**{key:assessment[key] for key in
                    ('status','individual_ids_complete','current_mode_ids')}}
                groups=assessment['current_identity_groups']
            else:
                effective={**current,'status':'UNVERIFIED','individual_ids_complete':False,
                           'current_mode_ids':[None]*current['request']['current_mode_count']}
        positions.append(dict(status=effective['status'],individual_ids_complete=effective['individual_ids_complete'],
            current_mode_ids=effective['current_mode_ids'],location=path/'current'/'solution',
            native_sha256=_native_part(before[index],'current')))
    if before!=[_snapshot(path) for path in directories]:
        raise ValueError('Hphi history ancestry changed during recovery replay')
    passed=effective['status']=='PASS'
    can_extend=passed and request.step_count<request.max_steps
    stop_reason=(None if can_extend else 'history max_steps budget reached; extension is forbidden' if passed
                 else 'last correspondence or identity recovery is UNVERIFIED; history extension is forbidden')
    return dict(format='superfish_ng_hphi_tracking_history_result',history_version=2,
        request=request.to_dict(),status=effective['status'],can_extend=can_extend,stop_reason=stop_reason,
        individual_ids_complete=effective['individual_ids_complete'],current_mode_ids=effective['current_mode_ids'],
        current_identity_groups=groups if passed else None,
        current_mode_count=effective['request']['current_mode_count'],step_sha256=before,steps=verified,
        identity_recoveries=events,
        scope='owned sampled native-field chain with explicit earlier-anchor identity recovery; '
              'not a continuous-path branch identity or physical error bound')

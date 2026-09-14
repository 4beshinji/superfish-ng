# SPDX-License-Identifier: Apache-2.0
"""Bind original target numbers to the accepted adaptive history before recovery."""
from .config import keys
from .study_identity_recovery import recovery_requests
from .mode_identity_recovery import recover_mode_history


def declared_recovery_requests(study,plans):
    if type(plans) is not list or not plans:
        raise ValueError('identity_recoveries requires a nonempty list of original-target recovery requests')
    converted=[]
    for plan in plans:
        fields=('target_index','anchor_target_index','controls')
        keys(plan,fields,fields,'adaptive Study identity recovery')
        converted.append(dict(point_index=plan['target_index'],anchor_snapshot_index=plan['anchor_target_index'],controls=plan['controls']))
    controls=recovery_requests(study,converted)
    return {target:dict(anchor_target_index=request['anchor_snapshot_index'],controls=request['controls']) for target,request in controls.items()}


def recover_at_target(history,request,target_index,current,points,accepted,values):
    anchor_target=request['anchor_target_index']
    anchors=[index for index in accepted if points[index]['value']==values[anchor_target]]
    if len(anchors)!=1:raise ValueError('recovery anchor target must already be present once in the accepted history')
    anchor_point=anchors[0];snapshot=accepted.index(anchor_point)
    recovered=recover_mode_history(history,dict(anchor_snapshot_index=snapshot,controls=request['controls']))
    event=recovered['identity_recoveries'][-1]
    return recovered,dict(target_index=target_index,anchor_target_index=anchor_target,anchor_point_index=anchor_point,
        anchor_snapshot_index=snapshot,current_point_index=current,status=event['status'],event=event)

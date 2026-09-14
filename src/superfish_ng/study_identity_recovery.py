# SPDX-License-Identifier: Apache-2.0
"""Validate scheduled recovery and derive maps from its actual Study point pair."""
from .config import keys
from .mode_identity_recovery import _request
from .study_shape_tracking import pair_controls


def recovery_requests(study,plans,*,projects=None):
    if type(plans) is not list or not plans:
        raise ValueError('identity_recoveries requires a nonempty list of explicit recovery points')
    previous=0;result={}
    for plan in plans:
        names=('point_index','anchor_snapshot_index','controls')
        keys(plan,names,names,'Study identity recovery')
        point=plan['point_index'];anchor=plan['anchor_snapshot_index']
        if type(point) is not int or not previous<point<len(study.values):
            raise ValueError('recovery point_index must be distinct, increasing and inside the Study after its initial point')
        if type(anchor) is not int or not 0<=anchor<point:
            raise ValueError('recovery anchor_snapshot_index must precede its Study point_index')
        pair=None if projects is None else [projects[anchor],projects[point]]
        control=pair_controls(study,plan['controls'],study.values[anchor],study.values[point],projects=pair)
        recovery=dict(anchor_snapshot_index=anchor,controls=control);_request(recovery)
        result[point]=recovery;previous=point
    return result

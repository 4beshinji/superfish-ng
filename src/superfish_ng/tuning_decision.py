# SPDX-License-Identifier: Apache-2.0
"""Pure bracket decisions on verified trials and caller-normalized controls.

The caller owns physics validation, identity recovery, native replay and mesh
budget stops. This module neither reads files nor solves or verifies fields.
"""
import math


def decide_next_trial(request, trials):
    """Return the existing stop/next-trial dictionary without modifying inputs."""
    def stop(status,**data):return dict(status=status,next_trial=None,**data)
    def next_trial(value,phase='search',parent=None):
        return dict(status='PAUSED',next_trial=dict(value=value,phase=phase,parent_index=parent))
    if not trials:return next_trial(request['bounds'][0])
    if trials[-1]['status']=='UNVERIFIED':
        reason=('explicit individual identity recovery is unverified' if trials[-1].get('identity_recovery')
                else 'sampled correspondence does not resolve all individual identities')
        return stop('UNVERIFIED',reason=reason)
    if len(trials)==1:return next_trial(request['bounds'][1],parent=0)
    last=trials[-1]
    if last['phase']=='refinement':
        difference=abs(last['frequency_hz']-trials[last['parent_index']]['frequency_hz'])
        target=abs(last['target_error_hz'])<=request['frequency_tolerance_hz']
        mesh=difference<=request['mesh_frequency_tolerance_hz']
        return stop('TUNED' if target and mesh else 'REFINEMENT_FAILED',value=last['value'],
            refined_target_met=target,mesh_difference_met=mesh,mesh_frequency_difference_hz=difference,
            reason='two-mesh frequency difference is a diagnostic, not a discretization-error bound')
    best=min(range(len(trials)),key=lambda i:abs(trials[i]['target_error_hz']))
    if abs(trials[best]['target_error_hz'])<=request['frequency_tolerance_hz']:
        return next_trial(trials[best]['value'],'refinement',best)
    lower,upper=0,1
    if math.copysign(1.,trials[0]['target_error_hz'])==math.copysign(1.,trials[1]['target_error_hz']):
        return stop('UNBRACKETED',reason='endpoint frequencies do not bracket the target on the sampled identified mode')
    for i in range(2,len(trials)):
        if math.copysign(1.,trials[i]['target_error_hz'])==math.copysign(1.,trials[lower]['target_error_hz']):lower=i
        else:upper=i
    bracket=[trials[lower]['value'],trials[upper]['value']]
    if len(trials)>=request['max_trials']:return stop('ITERATION_LIMIT',bracket=bracket)
    middle=bracket[0]/2+bracket[1]/2
    if bracket[1]-bracket[0]<=request['parameter_tolerance'] or not bracket[0]<middle<bracket[1]:
        return stop('PARAMETER_LIMIT',bracket=bracket,reason='parameter interval exhausted without frequency tolerance acceptance')
    return next_trial(middle,parent=len(trials)-1)

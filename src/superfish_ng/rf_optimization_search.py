# SPDX-License-Identifier: Apache-2.0
"""Deterministic bounded coordinate search; no solver or surrogate evaluations."""
from fractions import Fraction


def restoration_value(request, assessment):
    if assessment is None or (assessment['refinement_status'] != 'TARGETS_MET' or assessment['status']=='UNVERIFIED'):
        return None
    distances=[]
    for check in assessment['constraints']:
        interval=check['observed_envelope']
        if interval is None:return None
        constraint=check['constraint'];scale=Fraction(request['constraint_scales'][constraint['quantity']])
        distance=Fraction(0)
        if 'lower' in constraint:distance=max(distance,Fraction(constraint['lower'])-Fraction(interval[0]))
        if 'upper' in constraint:distance=max(distance,Fraction(interval[1])-Fraction(constraint['upper']))
        distances.append(distance/scale)
    return max(distances)


def improves(request, candidate, incumbent):
    a=restoration_value(request,candidate);b=restoration_value(request,incumbent)
    if a is None:return False
    if b is None:return True
    if a != b:return a < b
    if a != 0:return False
    x=candidate['objective']['eligible_value'];y=incumbent['objective']['eligible_value']
    if x is None or y is None:return False
    gain=Fraction(x)-Fraction(y)
    if request['criteria']['objective']['direction']=='minimize':gain=-gain
    return gain > Fraction(request['objective_improvement'])


def decision(request, trials):
    """Reconstruct each poll, accepted center and stop from the ordered evidence."""
    variables=request['variables'];initial=[v['initial'] for v in variables]
    def next_trial(values,phase,parent,reason=None):
        return dict(status='PAUSED',next_trial=dict(values=values,phase=phase,parent_index=parent),search_stop=reason)
    if not trials:return next_trial(initial,'search',None)
    center=0;steps=[v['step'] for v in variables];direction=0;visited={tuple(initial)};index=1
    while True:
        reason=None
        if index>=request['max_trials']-1:reason='TRIAL_LIMIT'
        if direction==2*len(variables):
            if all(step<=v['tolerance'] for step,v in zip(steps,variables)):reason=reason or 'PARAMETER_LIMIT'
            else:
                steps=[max(step/2,v['tolerance']) for step,v in zip(steps,variables)];direction=0
        if reason is not None:
            if index==len(trials):return next_trial(list(trials[center]['values']),'final',center,reason)
            final=trials[index]
            if index!=len(trials)-1:raise ValueError('optimization trials continue after final verification')
            assessment=final['assessment']
            status=('FINAL_UNVERIFIED' if assessment is None or assessment['status']=='UNVERIFIED' else
                    'SEARCH_COMPLETE' if assessment['status']=='CRITERIA_MET' else 'FINAL_CRITERIA_FAILED')
            return dict(status=status,next_trial=None,search_stop=reason,incumbent_index=center,
                final_index=index,final_criteria_met=status=='SEARCH_COMPLETE',
                initial_objective=trials[0]['assessment']['objective'] if trials[0]['assessment'] else None,
                final_objective=assessment['objective'] if assessment else None)
        axis=direction//2;sign=1 if direction%2==0 else -1;direction+=1
        value=list(trials[center]['values']);v=variables[axis]
        value[axis]=min(v['upper'],max(v['lower'],value[axis]+sign*steps[axis]))
        if tuple(value) in visited:continue
        if index==len(trials):return next_trial(value,'search',center)
        visited.add(tuple(value))
        if improves(request,trials[index]['assessment'],trials[center]['assessment']):center=index;direction=0
        index+=1

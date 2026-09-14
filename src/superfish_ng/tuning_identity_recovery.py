# SPDX-License-Identifier: Apache-2.0
"""Explicit earlier-trial recovery before a scalar root frequency is evaluated."""
from copy import deepcopy
from pathlib import Path
from .config import keys,integer
from .mode_identity_recovery import assess_identity_recovery
from .mode_tracking_history import _current_groups
from .saved_mode_tracking import build_saved_mode_tracking


def base_request(request):
    return request['tune_request'] if isinstance(request,dict) and request.get('schema_version')==6 else request


def validate_request(request):
    from .tuning import _request
    fields=('schema_version','tune_request','identity_recovery')
    keys(request,fields,fields,'tune identity recovery request')
    base=request['tune_request']
    if not isinstance(base,dict) or type(base.get('schema_version')) is not int or base['schema_version'] not in (1,2,3,4,5,7,8):
        raise ValueError('tune_request must be a complete tune request of version 1 through 5, 7 or 8; nested recovery requests are forbidden')
    project=_request(base);policy=request['identity_recovery']
    fields=('anchor_selection','controls')
    if isinstance(policy,dict) and policy.get('anchor_selection')=='fixed_trial':fields+=('anchor_trial_index',)
    keys(policy,fields,fields,'tune identity recovery policy')
    if policy['anchor_selection'] not in ('fixed_trial','latest_resolved_trial'):
        raise ValueError('anchor_selection must be fixed_trial or latest_resolved_trial')
    if policy['anchor_selection']=='fixed_trial':
        integer(policy['anchor_trial_index'],'anchor_trial_index',0)
        if policy['anchor_trial_index']>=base['max_trials']:
            raise ValueError('anchor_trial_index must precede the last possible refinement trial')
    controls=policy['controls']
    if isinstance(controls,dict) and 'cluster_transition_policy' in controls:
        raise ValueError('individual identity recovery forbids cluster union policies')
    # Reuse each geometry version's strict controls and derived-map contract.
    _request(dict(base,controls=controls))
    return project


def recover_trial(request,trials,projects,runs,trial,pair):
    from .tuning import pair_controls
    policy=request['identity_recovery'];current=len(trials)
    anchor=policy['anchor_trial_index'] if policy['anchor_selection']=='fixed_trial' else current-1
    if anchor>=current:
        raise ValueError('identity recovery anchor must be an already evaluated earlier trial')
    previous=trials[anchor]
    if previous['status'] not in ('INITIAL','PASS') or any(x is None for x in previous['current_mode_ids']):
        raise ValueError('identity recovery anchor must have resolved individual IDs')
    base=dict(base_request(request),controls=deepcopy(policy['controls']))
    controls=pair_controls(base,previous['value'],trial['value'],projects[anchor],projects[current])
    comparison=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(Path(runs[anchor])/'solution'),
        current_run=str(Path(runs[current])/'solution'),previous_ids=previous['current_mode_ids'],controls=controls))
    if comparison['sources'][1]!=pair['sources'][1]:
        raise ValueError('current native source changed during tune identity recovery')
    assessment=assess_identity_recovery(comparison['tracking'],_current_groups(pair))
    return dict(schema_version=1,document_type='tune_identity_recovery',anchor_trial_index=anchor,current_trial_index=current,
        comparison=comparison,assessment=assessment,status=assessment['status'],
        scope='explicit earlier-trial sampled field reidentification within inherited ID sets; not a continuous-branch certificate')

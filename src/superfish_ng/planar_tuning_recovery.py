# SPDX-License-Identifier: Apache-2.0
"""Earlier-trial planar ID recovery before a scalar tuning evaluation."""
from .config import integer, keys
from .planar_tracking import PlanarTrackingControls, PlanarTrackingRequest
from .planar_identity_recovery import PlanarIdentityRecoveryRequest, recover_planar_modes


def validate_planar_recovery_policy(request):
    policy = request['identity_recovery']
    names = ['anchor_selection', 'controls']
    if type(policy) is dict and policy.get('anchor_selection') == 'fixed_trial':
        names.append('anchor_trial_index')
    keys(policy, names, names, 'planar tune identity recovery')
    if policy['anchor_selection'] not in ('fixed_trial', 'latest_resolved_trial'):
        raise ValueError('planar recovery anchor_selection must be fixed_trial or latest_resolved_trial')
    if policy['anchor_selection'] == 'fixed_trial':
        integer(policy['anchor_trial_index'], 'anchor_trial_index', 0)
        if policy['anchor_trial_index'] >= request['max_trials']:
            raise ValueError('planar recovery anchor must precede the last possible refinement trial')
    return PlanarTrackingControls.from_dict(policy['controls'])


def recover_planar_tune_trial(request, trials, solutions, current, trial, inherited_request):
    from .planar_tuning import planar_tune_mapping
    resolved = [i for i, previous in enumerate(trials)
                if previous['status'] in ('INITIAL', 'PASS')
                and all(type(value) is str for value in previous['current_mode_ids'])]
    policy = request['identity_recovery']
    anchor = (policy['anchor_trial_index'] if policy['anchor_selection'] == 'fixed_trial'
              else resolved[-1] if resolved else None)
    event = dict(format='superfish_ng_planar_tune_identity_recovery', recovery_version=1,
                 anchor_trial_index=anchor, parent_trial_index=trial['parent_index'],
                 current_trial_index=len(trials), phase=trial['phase'], status='UNVERIFIED',
                 recovery=None, stop_reason=None)
    if anchor is None or anchor not in resolved:
        event['stop_reason'] = 'recovery requires an earlier completed trial with verified individual IDs'
        return event
    comparison = PlanarTrackingRequest(len(request['initial_ids']), len(request['initial_ids']),
        trials[anchor]['current_mode_ids'], mapping=planar_tune_mapping(request, trials[anchor], trial),
        controls=PlanarTrackingControls.from_dict(policy['controls']))
    recovery = recover_planar_modes(solutions[anchor], solutions[trial['parent_index']], current,
        inherited_request, PlanarIdentityRecoveryRequest(anchor, comparison), current_snapshot_index=len(trials))
    event.update(recovery=recovery, status=recovery['status'], stop_reason=recovery['stop_reason'])
    return event

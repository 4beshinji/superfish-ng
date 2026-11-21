# SPDX-License-Identifier: Apache-2.0
"""Explicit earlier-trial Hphi reidentification before scalar evaluation."""
from .config import integer, keys
from .hphi_tracking import HphiTrackingControls, HphiTrackingRequest, _track_hphi_modes
from .hphi_field_overlap import _declared_mesh
from .hphi_identity_recovery import _assess
from .hphi_shape_tuning import shape_comparison_mapping


def validate_recovery_policy(request):
    policy=request['identity_recovery']
    fields=['anchor_selection','controls']
    if isinstance(policy,dict) and policy.get('anchor_selection')=='fixed_trial':
        fields.append('anchor_trial_index')
    keys(policy,fields,fields,'Hphi tune identity recovery policy')
    if policy['anchor_selection'] not in ('fixed_trial','latest_resolved_trial'):
        raise ValueError('Hphi recovery anchor_selection must be fixed_trial or latest_resolved_trial')
    if policy['anchor_selection']=='fixed_trial':
        index=integer(policy['anchor_trial_index'],'anchor_trial_index',0)
        if index>=request['max_trials']:
            raise ValueError('anchor_trial_index must precede the last possible refinement trial')
    return HphiTrackingControls.from_dict(policy['controls'])


def recover_tune_trial(request, trials, solutions, current, trial, inherited):
    """Called only with the freshly recomputed inherited E/H correspondence.

    Saved execution reconstructs every earlier trial from owned native fields
    before reaching this function. No caller-authored tracking report enters
    the public tune/replay interface.
    """
    from .hphi_tuning import _refine_mesh, trial_hphi_project
    if inherited['status']!='PASS' or inherited['individual_ids_complete']:
        raise ValueError('Hphi tune recovery requires a verified unresolved individual ID set')
    policy=request['identity_recovery'];index=len(trials)
    resolved=[i for i,t in enumerate(trials) if t['status'] in ('INITIAL','PASS')
              and all(type(name) is str for name in t['current_mode_ids'])]
    anchor=(policy['anchor_trial_index'] if policy['anchor_selection']=='fixed_trial'
            else resolved[-1] if resolved else None)
    event=dict(format='superfish_ng_hphi_tune_identity_recovery',recovery_version=1,
        anchor_trial_index=anchor,current_trial_index=index,parent_trial_index=trial['parent_index'],
        phase=trial['phase'],status='UNVERIFIED',comparison=None,assessment=None,stop_reason=None,
        scope='owned earlier-trial sampled E/H reidentification within inherited ID sets; '
              'search/refinement parent is distinct from anchor; no continuous-branch certificate')
    if anchor is None or not 0<=anchor<index:
        event['stop_reason']='recovery requires an earlier completed anchor trial'
        return event
    if anchor not in resolved:
        event['stop_reason']='selected earlier anchor trial lacks confirmed individual IDs'
        return event
    previous=solutions[anchor];ids=trials[anchor]['current_mode_ids']
    try:
        comparison_request=HphiTrackingRequest(_refine_mesh(_declared_mesh(previous)),
            _refine_mesh(_declared_mesh(current)),previous_mode_count=len(ids),
            current_mode_count=len(request['initial_ids']),previous_mode_ids=ids,
            controls=HphiTrackingControls.from_dict(policy['controls']))
        if request['mapping']['kind']=='uniform_scale':
            comparison=_track_hphi_modes(previous,current,comparison_request,
                previous_scale=trial['value']/trials[anchor]['value'])
        else:
            mapping=shape_comparison_mapping(request,
                trial_hphi_project(request,trials[anchor]['value'],'search'),
                trial_hphi_project(request,trial['value'],'search'))
            comparison=_track_hphi_modes(previous,current,comparison_request,geometry_mapping=mapping)
        groups=[dict(indices=m['current_indices'],ids=m['previous_ids']) for m in inherited['matches']]
        assessment=_assess(comparison,groups,len(request['initial_ids']))
        event.update(comparison=comparison,assessment=assessment,status=assessment['status'],
            stop_reason=None if assessment['status']=='PASS' else '; '.join(assessment['reasons']))
    except ValueError as error:
        event['stop_reason']=str(error)
    return event

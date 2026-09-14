# SPDX-License-Identifier: Apache-2.0
"""Explicit individual reidentification against an earlier resolved native field."""
from copy import deepcopy
from pathlib import Path
from .config import keys
from .mode_tracking import _identity_groups
from .saved_mode_tracking import build_saved_mode_tracking, replay_mode_tracking, validate_tracking_controls, _canonical, _snapshot


def assess_identity_recovery(comparison, current_groups):
    """Accept an individual anchor match only inside every inherited ID set."""
    count=len(comparison['current_frequencies_hz'])
    groups=_identity_groups(current_groups,count)
    candidates=comparison['current_mode_ids']
    checks=[]
    for group in groups:
        observed=[candidates[i-1] for i in group['indices']]
        observed=sorted(observed) if all(type(x) is str for x in observed) else None
        checks.append(dict(indices=group['indices'],expected_ids=group['ids'],candidate_ids=observed,
                           consistent=observed==group['ids']))
    resolved=comparison['status']=='PASS' and comparison['individual_ids_complete']
    passed=resolved and all(c['consistent'] for c in checks)
    old_ids=[None]*count
    for group in groups:
        if len(group['indices'])==1:old_ids[group['indices'][0]-1]=group['ids'][0]
    return dict(status='PASS' if passed else 'UNVERIFIED',candidate_mode_ids=candidates,
        current_mode_ids=list(candidates) if passed else old_ids,
        current_identity_groups=[dict(indices=[i+1],ids=[name]) for i,name in enumerate(candidates)] if passed else groups,
        individual_ids_complete=passed,group_checks=checks,
        reasons=[] if passed else (['anchor comparison does not resolve all individual IDs'] if not resolved else [])+
            (['candidate IDs cross an inherited identity-set boundary'] if any(not c['consistent'] for c in checks) else []))


def _state(pair):
    report=pair['tracking']
    groups=sorted([dict(indices=m['current_indices'],ids=m['previous_ids']) for m in report['matches']],key=lambda g:g['indices'][0])
    return dict(source=pair['sources'][1],status=pair['status'],current_mode_ids=report['current_mode_ids'],
                current_identity_groups=groups,individual_ids_complete=report['individual_ids_complete'])


def _request(request):
    keys(request,('anchor_snapshot_index','controls'),('anchor_snapshot_index','controls'),'individual identity recovery request')
    index=request['anchor_snapshot_index']
    if type(index) is not int or index<0:raise ValueError('anchor_snapshot_index must be a nonnegative integer')
    controls=request['controls'];validate_tracking_controls(controls)
    if 'cluster_transition_policy' in controls:
        raise ValueError('individual identity recovery forbids cluster union policies; supply individual comparison controls')


def _recover(state,positions,request,after):
    _request(request)
    if state['status']!='PASS' or state['individual_ids_complete']:
        raise ValueError('identity recovery requires a verified history with unresolved individual ID sets')
    index=request['anchor_snapshot_index']
    if index>=len(positions):raise ValueError('anchor_snapshot_index must precede the recovery snapshot')
    anchor=positions[index]
    if anchor['status']!='PASS' or not anchor['individual_ids_complete']:
        raise ValueError('the selected anchor snapshot does not have verified individual IDs')
    comparison=build_saved_mode_tracking(dict(schema_version=1,previous_run=anchor['source']['directory'],
        current_run=state['source']['directory'],previous_ids=anchor['current_mode_ids'],controls=deepcopy(request['controls'])))
    if comparison['sources']!=[anchor['source'],state['source']]:
        raise ValueError('anchor or current native source changed during identity recovery')
    assessment=assess_identity_recovery(comparison['tracking'],state['current_identity_groups'])
    event=dict(schema_version=1,document_type='mode_identity_recovery',after_step_index=after,request=deepcopy(request),
        comparison=comparison,assessment=assessment,status=assessment['status'],
        scope='explicit earlier-to-current sampled field reidentification within inherited ID sets; not a continuous-branch certificate through degeneracy')
    updated=dict(state,**{k:assessment[k] for k in ('status','current_mode_ids','current_identity_groups','individual_ids_complete')})
    return event,updated


def _walk(steps,events):
    if type(steps) is not list or not steps:raise ValueError('recovered mode history requires nonempty steps')
    if type(events) is not list or not events:raise ValueError('version 3 history requires identity recovery events')
    requests={};previous=-1
    for event in events:
        keys(event,('after_step_index','request'),('after_step_index','request'),'identity recovery placement')
        index=event['after_step_index']
        if type(index) is not int or not previous<index<len(steps):
            raise ValueError('recovery step indices must be distinct, increasing and within the history')
        _request(event['request']);requests[index]=event['request'];previous=index
    pairs=[replay_mode_tracking(step) for step in steps]
    snapshots={source['directory']:source for pair in pairs for source in pair['sources']}
    first=pairs[0];request=first['request']
    groups=([dict(indices=[i+1],ids=[name]) for i,name in enumerate(request['previous_ids'])]
            if request['schema_version']==1 else first['tracking']['previous_identity_groups'])
    ids=[None]*len(first['tracking']['previous_frequencies_hz'])
    for group in groups:
        if len(group['indices'])==1:ids[group['indices'][0]-1]=group['ids'][0]
    state=dict(source=first['sources'][0],status='PASS',current_mode_ids=ids,current_identity_groups=groups,
               individual_ids_complete=all(x is not None for x in ids))
    positions=[state];recoveries=[]
    for index,pair in enumerate(pairs):
        if state['status']!='PASS':raise ValueError('history continues after an unverified comparison or recovery')
        request=pair['request']
        continuous=(state['individual_ids_complete'] and request['previous_ids']==state['current_mode_ids']
                    if request['schema_version']==1 else pair['tracking']['previous_identity_groups']==state['current_identity_groups'])
        if pair['sources'][0]!=state['source'] or not continuous:
            raise ValueError('history source or recovered stable ID continuity differs between steps')
        state=_state(pair)
        if index in requests:
            event,state=_recover(state,positions,requests[index],index);recoveries.append(event)
        positions.append(state)
    if any(_snapshot(Path(path))!=source for path,source in snapshots.items()):
        raise ValueError('mode history sources changed during identity recovery replay')
    passed=state['status']=='PASS'
    return dict(schema_version=3,document_type='mode_tracking_history',steps=pairs,identity_recoveries=recoveries,
        status=state['status'],can_extend=passed,
        stop_reason=None if passed else 'last correspondence or explicit identity recovery is unverified; retain the earlier history',
        current_run=state['source']['directory'],current_mode_ids=state['current_mode_ids'],
        current_identity_groups=state['current_identity_groups'],individual_ids_complete=state['individual_ids_complete'],
        scope='ordered saved-field comparisons with explicit earlier-anchor identity recovery; sampled steps do not prove a continuous physical branch between samples')


def _placements(history):
    return [dict(after_step_index=e['after_step_index'],request=e['request']) for e in history.get('identity_recoveries',[])]


def recover_mode_history(document,request):
    from .mode_tracking_history import replay_mode_history
    _request(request);history=replay_mode_history(document)
    if not history['can_extend']:raise ValueError('identity recovery requires a verified history; retain the unresolved history separately')
    events=_placements(history)+[dict(after_step_index=len(history['steps'])-1,request=deepcopy(request))]
    return _walk(history['steps'],events)


def replay_recovered_mode_history(document):
    fields=('schema_version','document_type','steps','identity_recoveries','status','can_extend','stop_reason',
            'current_run','current_mode_ids','current_identity_groups','individual_ids_complete','scope')
    keys(document,fields,fields,'recovered mode tracking history')
    events=document['identity_recoveries']
    if type(events) is not list:raise ValueError('identity_recoveries must be a list')
    for event in events:
        names=('schema_version','document_type','after_step_index','request','comparison','assessment','status','scope')
        keys(event,names,names,'saved individual identity recovery')
    expected=_walk(document['steps'],_placements(document))
    if _canonical(expected)!=_canonical(document):raise ValueError('individual identity recovery history replay differs from saved data')
    return expected


def extend_recovered_mode_history(document,request,*,base_directory=None):
    history=replay_recovered_mode_history(document)
    keys(request,('current_run','controls'),('current_run','controls'),'mode history extension request')
    if not history['can_extend']:raise ValueError('cannot extend history after an unresolved identity recovery')
    pair=build_saved_mode_tracking(dict(schema_version=2,previous_run=history['current_run'],current_run=request['current_run'],
        previous_groups=history['current_identity_groups'],controls=deepcopy(request['controls'])),base_directory=base_directory)
    return _walk(history['steps']+[pair],_placements(history))

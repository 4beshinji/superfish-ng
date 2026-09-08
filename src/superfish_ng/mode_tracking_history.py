# SPDX-License-Identifier: Apache-2.0
"""Replayable ordered correspondences with explicit stop conditions."""
from copy import deepcopy
from pathlib import Path
import json
from .config import keys
from .project import parse_json
from .saved_mode_tracking import build_saved_mode_tracking, replay_mode_tracking, _canonical


def _assemble(steps):
    last=steps[-1]
    resolved=last['status']=='PASS' and last['tracking']['individual_ids_complete']
    return dict(schema_version=1,document_type='mode_tracking_history',steps=steps,
                status='PASS' if resolved else 'UNVERIFIED',can_extend=resolved,
                stop_reason=None if resolved else 'last correspondence is unverified or only a subspace; individual IDs cannot be propagated',
                current_run=last['request']['current_run'],current_mode_ids=last['tracking']['current_mode_ids'],
                scope='ordered saved-field comparisons; sampled steps do not prove a continuous physical branch between samples')


def start_mode_history(pair):
    return _assemble([replay_mode_tracking(pair)])


def replay_mode_history(document):
    fields=('schema_version','document_type','steps','status','can_extend','stop_reason','current_run','current_mode_ids','scope')
    keys(document,fields,fields,'mode tracking history')
    steps=document['steps']
    if type(steps) is not list or not steps:raise ValueError('mode tracking history requires a nonempty steps list')
    verified=[]
    for step in steps:
        checked=replay_mode_tracking(step)
        if verified:
            previous=_assemble(verified)
            if not previous['can_extend']:raise ValueError('history continues after unresolved individual IDs')
            if (checked['sources'][0]!=verified[-1]['sources'][1]
                    or checked['request']['previous_ids']!=previous['current_mode_ids']):
                raise ValueError('history source or stable ID continuity differs between steps')
        verified.append(checked)
    expected=_assemble(verified)
    if _canonical(expected)!=_canonical(document):raise ValueError('mode tracking history replay differs from saved data')
    return expected


def extend_mode_history(document,request,*,base_directory=None):
    history=replay_mode_history(document)
    if not history['can_extend']:raise ValueError('cannot extend history with unresolved individual IDs; retain this history and investigate the last step')
    fields=('current_run','controls')
    keys(request,fields,fields,'mode history extension request')
    pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=history['current_run'],
        current_run=request['current_run'],previous_ids=history['current_mode_ids'],controls=deepcopy(request['controls'])),
        base_directory=base_directory)
    if pair['sources'][0]!=history['steps'][-1]['sources'][1]:raise ValueError('history source changed before extension')
    # Recheck every earlier source too: appending must not bless stale ancestry.
    replay_mode_history(history)
    return _assemble(history['steps']+[pair])


def save_mode_history(document,path):
    verified=replay_mode_history(document)
    with Path(path).open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(verified,indent=2,allow_nan=False)+'\n')
    return verified


def read_mode_history(path):
    return replay_mode_history(parse_json(Path(path).read_text(encoding='utf-8')))

# SPDX-License-Identifier: Apache-2.0
"""GUI transport for the shared saved surface-refinement assessment."""
import json
from .config import keys
from .project import parse_json
from .surface_convergence import assess_surface_convergence,replay_surface_convergence


def surface_convergence_response(action,data):
    fields={'assess-surface-convergence':('document','mode_id'),'replay-surface-convergence':('document',),
        'assess-affine-surface-convergence':('document','mode_id'),'replay-affine-surface-convergence':('document',)}
    if action not in fields:raise ValueError('unknown surface convergence operation')
    keys(data,fields[action],fields[action],'GUI surface convergence')
    document=data['document']
    if isinstance(document,str):document=parse_json(document)
    if action in ('assess-affine-surface-convergence','replay-affine-surface-convergence'):
        from .affine_surface_convergence import assess_affine_surface_convergence,replay_affine_surface_convergence
        result=assess_affine_surface_convergence(document,data['mode_id']) if action=='assess-affine-surface-convergence' else replay_affine_surface_convergence(document)
    elif action=='assess-surface-convergence':
        if isinstance(document,dict) and document.get('document_type')=='study_mode_tracking':
            from .study_mode_tracking import replay_study_mode_tracking
            document=replay_study_mode_tracking(document)['history']
        result=assess_surface_convergence(document,data['mode_id'])
    else:result=replay_surface_convergence(document)
    return dict(document=result,serialized=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

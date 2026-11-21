# SPDX-License-Identifier: Apache-2.0
"""N06 source-bound whole-grid references; no native eigensolve or fitting."""
from copy import deepcopy
import json
from pathlib import Path
import re

import numpy as np

from .adaptive_efficiency_analytic_grid import build_analytic_efficiency_grid
from .adaptive_efficiency_domain import _native_files
from .adaptive_efficiency_fields import COMPONENTS
from .adaptive_efficiency_plan import build_adaptive_efficiency_plan
from .completion import digest
from .config import Case, keys
from .mesh import make_mesh
from .mesh_input import mesh_to_dict
from .project import parse_json
from .saved import read_solution


def _bound_file(path, expected, bound):
    path=Path(path).absolute()
    if (type(expected) is not str or not re.fullmatch('[0-9a-f]{64}',expected) or
            any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file()):
        raise ValueError('reference requires a regular nonlinked file and complete SHA256: '+str(path))
    if digest(path)!=expected:
        raise ValueError('reference SHA256 differs: '+str(path))
    if str(path) in bound and bound[str(path)]!=expected:
        raise ValueError('reference has conflicting byte bindings: '+str(path))
    bound[str(path)]=expected
    return path


def _read_binding(binding,bound):
    keys(binding,('path','sha256'),('path','sha256'),'efficiency reference file binding')
    path=_bound_file(binding['path'],binding['sha256'],bound)
    value=parse_json(path.read_text())
    _bound_file(path,binding['sha256'],bound)
    return path,value


def verify_reference_bytes(reference):
    for path,sha in reference['bound_inputs'].items():
        _bound_file(path,sha,{})


def load_efficiency_reference(case_id,bindings,*,base_directory=None):
    """Validate packages and retain every Gauss node/reference guard mode.

    Expected manifest SHAs must come from the accepted preparation. Analytical
    arrays and RF are also independently regenerated from fixed mathematics.
    Rounded fields retain the saved N03 provenance/IDs and empirical peak scope.
    The caller must independently bind each native domain and actual tracked IDs.
    """
    if case_id not in ('cylinder','sphere','rounded-two-lobe'):
        raise ValueError('efficiency reference requires one of the three fixed N05 cases')
    keys(bindings,('analytic_manifest','rounded_manifest','rounded_matrix'),(), 'efficiency reference bindings')
    required=('rounded_manifest','rounded_matrix') if case_id=='rounded-two-lobe' else ('analytic_manifest',)
    if any(k not in bindings for k in required):
        raise ValueError('missing required efficiency reference manifest/matrix binding')
    repo=Path(base_directory) if base_directory is not None else Path(__file__).resolve().parents[2]
    plan=build_adaptive_efficiency_plan(base_directory=repo)
    row=next(r for r in plan['cases'] if r['id']==case_id)
    case=Case.from_dict(row['request']['case'])
    source=row['request']['initial_mesh']
    if source is None:source=mesh_to_dict(make_mesh(case))
    bound={};grids=[];anchor=None
    if case_id!='rounded-two-lobe':
        path,manifest=_read_binding(bindings['analytic_manifest'],bound)
        if (manifest.get('document_type')!='n06_fixed_analytic_reference_grids' or
                manifest.get('status')!='REFERENCE_PREPARATION_ACCEPTED' or
                manifest['fixed_input_sources']!=plan['input_sources']):
            raise ValueError('analytic reference requires accepted full fixed-N05 preparation')
        if not {'src/superfish_ng/analytic.py','src/superfish_ng/analytic_sphere.py',
                'src/superfish_ng/adaptive_efficiency_analytic_grid.py'} <= set(manifest['source_sha256']):
            raise ValueError('analytic reference lacks its actual mathematical product-source bindings')
        for relative,sha in manifest['source_sha256'].items():
            if Path(relative).is_absolute() or '..' in Path(relative).parts:
                raise ValueError('invalid product-source reference path')
            _bound_file(repo/relative,sha,bound)
        selected=[r for r in manifest['grids'] if r['case_id']==case_id]
        if [r['order'] for r in selected]!=[16,24]:
            raise ValueError('reference requires both full Gauss16/24 grids')
        for grid in selected:
            metadata_path,meta=_read_binding(dict(path=str(path.parent/grid['path']),sha256=grid['sha256']),bound)
            if meta['case']!=case.to_dict() or meta['source_mesh']!=source:
                raise ValueError('analytic reference changed complete original Case/source')
            expected=build_analytic_efficiency_grid(case_id,case,source,order=grid['order'])
            fields_path=_bound_file(path.parent/grid['field_path'],grid['field_sha256'],bound)
            with np.load(fields_path,allow_pickle=False) as archive:
                arrays={k:archive[k].copy() for k in archive.files}
            original_arrays={k:v for k,v in expected.items() if isinstance(v,np.ndarray)}
            if set(arrays)!=set(original_arrays) or any(not np.array_equal(v,original_arrays[k]) for k,v in arrays.items()):
                raise ValueError('analytic full reference arrays differ from independent fixed mathematics')
            if meta['reference_quantities']!=expected['reference_quantities']:
                raise ValueError('analytic reference RF/peak quantities differ from independent mathematics')
            grids.append(dict(order=grid['order'],points=arrays['native_volume_points_rz_m'],
                              axis=arrays['axis_points_rz_m'],weights=arrays['volume_weights_m3'],
                              axis_weights=arrays['axis_weights_m'],density=arrays['native_volume_density_ratio'],
                              reference_fields=arrays['reference_fields'],reference_axis_ez=arrays['reference_axis_ez'],
                              quantities=deepcopy(meta['reference_quantities']),all_reference_arrays=arrays,
                              reference_field_path=str(fields_path),reference_field_sha256=grid['field_sha256']))
    else:
        path,manifest=_read_binding(bindings['rounded_manifest'],bound)
        _,matrix=_read_binding(bindings['rounded_matrix'],bound)
        if (manifest.get('document_type')!='n06_reused_reference_grids' or manifest.get('case_id')!='N01-rounded-two-lobe' or
                manifest['component_order']!=list(COMPONENTS) or manifest['normalization_j']!=1. or manifest['beta']!=1. or
                manifest['reference_maxh_m']!=[.005,.0025,.00125] or matrix['status']!='PASS'):
            raise ValueError('rounded reference requires original accepted N03 full-grid matrix/three-h convention')
        for name,sha in manifest['bound_inputs'].items():_bound_file(name,sha,bound)
        ids=row['request']['initial_ids']
        if any(current!=ids for group in matrix['mode_ids_by_node'] for current in group):
            raise ValueError('rounded reference does not retain actual original individual-mode IDs')
        anchor_path=Path(matrix['request']['runs'][2][0])
        snapshots={s['directory']:s['sha256'] for s in matrix['sources']}
        native_sha=_native_files(anchor_path)
        if native_sha!=snapshots[str(anchor_path)]:
            raise ValueError('rounded original initial native bytes differ from accepted matrix')
        for name,sha in native_sha.items():_bound_file(anchor_path/name,sha,bound)
        anchor=read_solution(anchor_path)
        if anchor.case!=case or anchor.source_mesh_data!=source:
            raise ValueError('rounded anchor differs from original complete Case/source')
        if any(c['status']!='PASS' for c in manifest['original_reference_two_changes']):
            raise ValueError('rounded independent reference two intervals are unconfirmed')
        if [r['order'] for r in manifest['grids']]!=[16,24]:
            raise ValueError('rounded reference requires both original full quadrature orders')
        for grid in manifest['grids']:
            fields_path=_bound_file(path.parent/grid['path'],grid['sha256'],bound)
            with np.load(fields_path,allow_pickle=False) as archive:arrays={k:archive[k].copy() for k in archive.files}
            count=grid['volume_sample_count'];axis_count=grid['axis_sample_count']
            fields=arrays['reference_fields_levels']
            if (fields.shape!=(3,count+axis_count,5,3) or grid['reference_selected_ids']!=[ids,ids,ids] or
                    not np.isfinite(fields).all()):
                raise ValueError('rounded reference dropped original full nodes, h levels or guard modes')
            target=int(arrays['reference_target_indices'][-1])
            if not 0<=target<5 or arrays['reference_selected_indices'][-1,ids.index('target')]!=target:
                raise ValueError('rounded reference target ID disagrees with actual reference selection')
            grids.append(dict(order=grid['order'],points=arrays['fixed_native_volume_points_rz_m'],
                              axis=arrays['axis_points_rz_m'],weights=arrays['volume_weights_m3'],
                              axis_weights=arrays['axis_weights_m'],density=arrays['native_volume_density_ratio'],
                              reference_fields=fields[-1,:count,target],reference_axis_ez=fields[-1,count:,target,1],
                              quantities=deepcopy(manifest['original_reference_quantities'][-1]),all_reference_arrays=arrays,
                              reference_field_path=str(fields_path),reference_field_sha256=grid['sha256']))
    for grid in grids:
        n=len(grid['weights']);a=len(grid['axis_weights'])
        if (grid['points'].shape!=(n,2) or grid['axis'].shape!=(a,2) or grid['density'].shape!=(n,) or
                grid['reference_fields'].shape!=(n,3) or grid['reference_axis_ez'].shape!=(a,) or
                any(not np.isfinite(grid[k]).all() for k in ('points','axis','weights','axis_weights','density','reference_fields','reference_axis_ez')) or
                any(np.any(grid[k]<=0) for k in ('weights','axis_weights','density')) or np.any(grid['axis'][:,0]!=0)):
            raise ValueError('efficiency reference has missing or invalid full volume/axis samples')
    result=dict(case_id=case_id,request=deepcopy(row['request']),case=case,source_mesh=deepcopy(source),
                grids=grids,bound_inputs=bound,rounded_anchor=anchor,initial_ids=deepcopy(row['request']['initial_ids']),
                physical_error_bound=None,scope='verified original full supplied reference grids; actual native source/domain/IDs remain separate')
    verify_reference_bytes(result)
    return result

# SPDX-License-Identifier: Apache-2.0
"""Reference geometry and analytical fields for the fixed RF-goal comparison.

These builders do not solve native eigenproblems or certify native accuracy.
The prolate map preserves every supplied point on the original quadratic domain;
the caller must still bind a complete quadrature grid and independent fields.
"""
from copy import deepcopy
import math
from pathlib import Path

import numpy as np

from .adaptive_efficiency_analytic_grid import build_analytic_efficiency_grid
from .adaptive_efficiency_fields import COMPONENTS
from .analytic_sphere import SphereTM
from .config import Case
from .constants import MU0
from .curved_rf_goal_efficiency_plan import (build_curved_rf_goal_efficiency_plan,
                                           request_for_curved_rf_goal_efficiency_execution)
from .curved_space import case_curved_space
from .mesh_input import mesh_from_dict


_PREPARED_PATH = 'examples/curved_rf_goal_efficiency/prepared_references.json'
_PREPARED_SHA256 = '7cbab5bc82845bb9932d3a2bdea25ef24ae7fa91ad9104f36c0b9168aa0a2962'


def _fixed_request(case_id, family):
    if type(case_id) is not str or case_id not in (family+'-scale-1', family+'-scale-2'):
        raise ValueError(f'reference requires a fixed {family} case id including scale 1 or 2')
    plan = build_curved_rf_goal_efficiency_plan()
    row = next(r for r in plan['executions'] if r['case_id']==case_id and r['method']=='rf_goal')
    request = request_for_curved_rf_goal_efficiency_execution(row)
    return request, Case.from_dict(request['case']), int(case_id[-1])


def build_sphere_rf_goal_reference(case_id, *, order=16):
    """Evaluate the independent sphere solution at every full-volume/axis point.

    Scale two is evaluated from SphereTM at radius 0.16 m and U=4 J, not from a
    native FEM eigenfield or a fitted amplitude. Only the geometric Gauss grid is
    scaled from the already validated full N05 sphere construction.
    """
    if type(order) is not int or order not in (16,24):
        raise ValueError('RF goal sphere reference requires Gauss order 16 or 24')
    request, case, scale = _fixed_request(case_id, 'sphere')
    original, original_case, _ = _fixed_request('sphere-scale-1', 'sphere')
    grid = build_analytic_efficiency_grid('sphere', original_case, original['initial_mesh'], order=order)
    points = grid['analytic_volume_points_rz_m']*scale
    native = grid['native_volume_points_rz_m']*scale
    axis = grid['axis_points_rz_m']*scale
    radius = .08*scale
    reference = SphereTM(radius, beta=case.beta, conductivity_s_per_m=case.conductivity_s_per_m,
                         normalization_j=case.normalization_j)
    values = reference.fields(points)
    fields = np.column_stack([values[k] for k in COMPONENTS])
    axis_ez = reference.fields(axis)['Ez_quadrature_V_per_m']
    quantities = reference.quantities()
    eacc = abs(complex(quantities['voltage_real_v'], quantities['voltage_imag_v']))/case.length
    pole = reference.fields([[0.,0.]])['Ez_quadrature_V_per_m'][0]
    equator = reference.fields([[radius,radius]])['Hphi_A_per_m'][0]
    quantities['epk_over_eacc'] = float(abs(pole)/eacc)
    quantities['bpk_over_eacc_mt_per_mv_per_m'] = float(MU0*abs(equator)/eacc*1e9)
    return dict(case_id=case_id, request=deepcopy(request), case=case.to_dict(),
                source_mesh=deepcopy(request['initial_mesh']), order=order,
                analytic_volume_points_rz_m=points, native_volume_points_rz_m=native,
                volume_weights_m3=grid['volume_weights_m3']*scale**3,
                native_volume_density_ratio=grid['native_volume_density_ratio'].copy(),
                axis_points_rz_m=axis, axis_weights_m=grid['axis_weights_m']*scale,
                reference_fields=fields, reference_axis_ez=axis_ez, reference_quantities=quantities,
                native_wall_parameter_partitions=deepcopy(grid['native_wall_parameter_partitions']),
                component_order=list(COMPONENTS), analytic_volume_m3=4*math.pi*radius**3/3,
                physical_error_bound=None, native_accuracy_status='NOT_RUN',
                scope='independent SphereTM on full Gauss16/24 native and analytical volumes and physical axis; native identity/accuracy remain separate')


def _positive_quadratic(c):
    candidates = [0.,1.]
    if c[2] != 0:
        vertex = -c[1]/(2*c[2])
        if 0 < vertex < 1:
            candidates.append(float(vertex))
    value = min(c[0]+t*(c[1]+t*c[2]) for t in candidates)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('native prolate boundary is not a positive full polar fan')
    return float(value)


def map_prolate_rf_goal_points(case_id, points_rz_m):
    """Map all interior analytical prolate points through the actual P2 wall.

    Returns the exact original point ordering and the positive volume-density
    ratio. Boundary coverage is checked independently of whether a segment holds
    a supplied point. A caller cannot infer quadrature coverage from this map.
    """
    request, case, scale = _fixed_request(case_id, 'prolate')
    raw = np.asarray(points_rz_m)
    if (raw.dtype.kind not in 'iuf' or raw.ndim != 2 or raw.shape[1:] != (2,) or
            not len(raw) or not np.isfinite(raw).all()):
        raise ValueError('prolate reference points require a nonempty finite real N by 2 array')
    points = raw.astype(float)
    curve = case.curved_contour.to_dict()['curves'][1]
    center, radial_center = curve['center_zr_m']; a,b = curve['semiaxes_m']
    if (radial_center != 0 or curve['start_rad'] != 0 or curve['sweep_rad'] != math.pi or
            curve['rotation_rad'] != 0):
        raise ValueError('fixed prolate reference requires its original full unrotated conic')
    rho = np.hypot(points[:,0]/b, (points[:,1]-center)/a)
    theta = np.arctan2(points[:,0]/b, (points[:,1]-center)/a)
    if np.any((rho<=0)|(rho>=1)|(theta<=0)|(theta>=math.pi)):
        raise ValueError('prolate reference volume points must all lie strictly inside the analytical polar fan')
    geometry = case_curved_space(case, mesh_from_dict(case, request['initial_mesh'])).geometry
    target = np.empty_like(points); density = np.empty(len(points)); filled = np.zeros(len(points),bool)
    coverage = []; minimum = math.inf
    for index in np.flatnonzero(geometry.boundary_curve_indices==1):
        first,last = geometry.boundary_parameters[index]; span = last-first
        if abs(span) <= 512*np.finfo(float).eps:
            raise ValueError('prolate native boundary interval is unresolved at roundoff scale')
        coverage.append(sorted((float(first),float(last))))
        nodes = geometry.points_rz_m[geometry.boundary_nodes[index]]
        c0 = nodes[0].copy(); c0[1] -= center
        c1 = -3*nodes[0]-nodes[1]+4*nodes[2]
        c2 = 2*nodes[0]+2*nodes[1]-4*nodes[2]
        cross = np.array((c0[1]*c1[0]-c0[0]*c1[1],
                          2*(c0[1]*c2[0]-c0[0]*c2[1]),
                          c1[1]*c2[0]-c1[0]*c2[1]))/(span*math.pi)
        minimum = min(minimum, _positive_quadratic(cross))
        select = (theta/math.pi>=min(first,last)-1e-14)&(theta/math.pi<=max(first,last)+1e-14)&(~filled)
        if not np.any(select):
            continue
        t = (theta[select]/math.pi-first)/span
        basis = np.column_stack((2*(t-.5)*(t-1),2*t*(t-.5),4*t*(1-t)))
        derivative = np.column_stack((4*t-3,4*t-1,4-8*t))
        wall = basis@nodes; d = derivative@nodes/(span*math.pi)
        wall_cross = (wall[:,1]-center)*d[:,0]-wall[:,0]*d[:,1]
        target[select,0] = rho[select]*wall[:,0]
        target[select,1] = center+rho[select]*(wall[:,1]-center)
        density[select] = wall[:,0]/(b*np.sin(theta[select]))*wall_cross/(a*b)
        filled[select] = True
    coverage.sort()
    if (not coverage or abs(coverage[0][0])>1e-13 or abs(coverage[-1][1]-1)>1e-13 or
            any(abs(p[1]-q[0])>1e-13 for p,q in zip(coverage,coverage[1:])) or
            not filled.all() or not np.isfinite(target).all() or not np.isfinite(density).all() or np.any(density<=0)):
        raise ValueError('prolate native full polar map has an uncovered interval or invalid point/density')
    return dict(case_id=case_id, request=deepcopy(request), native_volume_points_rz_m=target,
                native_volume_density_ratio=density, native_wall_parameter_partitions=coverage,
                minimum_polar_cross_m2=minimum, scale=scale, supplied_point_count=len(points),
                coverage_status='ALL_SUPPLIED_POINTS_MAPPED', physical_error_bound=None,
                scope='complete original P2 boundary and all supplied interior points; independent quadrature/field/source/ID checks remain required')


def _bindings(supplied):
    from .curved_rf_goal_efficiency_plan import _read_bound
    from .project import parse_json
    from .config import keys
    root = Path(__file__).resolve().parents[2]
    registry = parse_json(_read_bound(root, dict(path=_PREPARED_PATH, sha256=_PREPARED_SHA256, bytes=3383)).decode())
    expected = registry['bindings']
    if supplied is None:
        supplied = {key:dict(path=str(root/value['path']), sha256=value['sha256']) for key,value in expected.items()}
    keys(supplied, tuple(expected), tuple(expected), 'fixed RF goal reference bindings')
    for key,value in supplied.items():
        keys(value, ('path','sha256'), ('path','sha256'), key)
        if type(value['path']) is not str or not value['path'] or value['sha256'] != expected[key]['sha256']:
            raise ValueError('RF goal reference requires the fixed prepared manifest SHA256: '+key)
    return deepcopy(supplied), {str(root/_PREPARED_PATH):_PREPARED_SHA256}, registry['historical_source_aliases']


def _historical_source(path, expected, bound, aliases):
    from .adaptive_efficiency_reference import _bound_file
    from .completion import digest
    path=Path(path)
    if any(p.is_symlink() for p in (path,*path.parents)):
        raise ValueError('RF reference historical source requires a regular path without symlinks: '+str(path))
    if path.is_file() and digest(path)==expected:
        return _bound_file(path,expected,bound)
    alias=aliases.get(str(path))
    if alias is None or alias['sha256']!=expected:
        raise ValueError('RF reference historical source is missing or changed: '+str(path))
    root=Path(__file__).resolve().parents[2]
    return _bound_file(root/alias['path'],expected,bound)


def _original_n06_reference(family, bindings, bound, aliases):
    """Reuse original bytes with explicit same-content historical source paths.

    N06's original reader demands its entire old source tree in place. Later UI
    and remesh work changed eight of those files. Their reviewed git blobs are
    read as provenance at new paths, never executed or substituted as current
    numerical code. No field, source hash or original N06 rule is weakened.
    """
    from .adaptive_efficiency_reference import _read_binding, _bound_file
    from .adaptive_efficiency_domain import _native_files
    from .saved import read_solution
    root=Path(__file__).resolve().parents[2]
    request,case,_=_fixed_request(family+'-scale-1',family)
    if family=='sphere':
        path,manifest=_read_binding(bindings['analytic_manifest'],bound)
        if manifest['document_type']!='n06_fixed_analytic_reference_grids' or manifest['status']!='REFERENCE_PREPARATION_ACCEPTED':
            raise ValueError('sphere requires the original accepted N06 mathematical reference')
        for relative,h in manifest['source_sha256'].items():
            if Path(relative).is_absolute() or '..' in Path(relative).parts:
                raise ValueError('invalid historical sphere source path')
            _historical_source(root/relative,h,bound,aliases)
        grids=[]
        for entry in (g for g in manifest['grids'] if g['case_id']=='sphere'):
            _,meta=_read_binding(dict(path=str(path.parent/entry['path']),sha256=entry['sha256']),bound)
            if meta['case']!=case.to_dict() or meta['source_mesh']!=request['initial_mesh']:
                raise ValueError('sphere reference differs from whole original RF Case/source')
            file=_bound_file(path.parent/entry['field_path'],entry['field_sha256'],bound)
            with np.load(file,allow_pickle=False) as z:arrays={k:z[k].copy() for k in z.files}
            expected=build_sphere_rf_goal_reference('sphere-scale-1',order=entry['order'])
            expected_arrays={k:v for k,v in expected.items() if isinstance(v,np.ndarray)}
            if (set(arrays)!=set(expected_arrays) or any(not np.array_equal(v,expected_arrays[k]) for k,v in arrays.items()) or
                    meta['reference_quantities']!=expected['reference_quantities']):
                raise ValueError('sphere original arrays/RF differ from independent full-domain mathematics')
            grids.append(dict(order=entry['order'],all_reference_arrays=arrays,
                              reference_field_path=str(file),reference_field_sha256=entry['field_sha256']))
    else:
        path,manifest=_read_binding(bindings['rounded_manifest'],bound)
        _,matrix=_read_binding(bindings['rounded_matrix'],bound)
        if (manifest['document_type']!='n06_reused_reference_grids' or manifest['reference_maxh_m']!=[.005,.0025,.00125] or
                manifest['component_order']!=list(COMPONENTS) or manifest['normalization_j']!=1. or manifest['beta']!=1. or matrix['status']!='PASS'):
            raise ValueError('rounded requires original N03/N06 whole-grid three-h conventions')
        for p,h in manifest['bound_inputs'].items():_historical_source(p,h,bound,aliases)
        if any(ids!=request['initial_ids'] for group in matrix['mode_ids_by_node'] for ids in group):
            raise ValueError('rounded original individual-mode IDs differ')
        anchor=Path(matrix['request']['runs'][2][0]);snapshot={s['directory']:s['sha256'] for s in matrix['sources']}
        actual=_native_files(anchor)
        if actual!=snapshot[str(anchor)]:raise ValueError('rounded original anchor bytes differ')
        for p,h in actual.items():_bound_file(anchor/p,h,bound)
        native=read_solution(anchor)
        if native.case!=case or native.source_mesh_data!=request['initial_mesh']:
            raise ValueError('rounded anchor differs from original RF Case/source')
        if any(c['status']!='PASS' for c in manifest['original_reference_two_changes']):
            raise ValueError('rounded reference original two changes UNVERIFIED')
        grids=[]
        for entry in manifest['grids']:
            file=_bound_file(path.parent/entry['path'],entry['sha256'],bound)
            with np.load(file,allow_pickle=False) as z:arrays={k:z[k].copy() for k in z.files}
            _modern_arrays(arrays,entry['volume_sample_count'],entry['axis_sample_count'])
            if entry['reference_selected_ids']!=[request['initial_ids']]*3:
                raise ValueError('rounded reference omitted an original target/guard ID')
            grids.append(dict(order=entry['order'],all_reference_arrays=arrays,
                              reference_field_path=str(file),reference_field_sha256=entry['sha256']))
    if [g['order'] for g in grids]!=[16,24]:
        raise ValueError('original N06 reference requires both complete Gauss grids')
    return dict(grids=grids,case=case,source_mesh=request['initial_mesh']),manifest


def _modern_arrays(arrays, n, a):
    shapes = dict(analytic_volume_points_rz_m=(n,2), volume_weights_m3=(n,),
                  axis_points_rz_m=(a,2), axis_weights_m=(a,),
                  fixed_native_volume_points_rz_m=(n,2), native_volume_density_ratio=(n,),
                  reference_fields_levels=(3,n+a,5,3), reference_selected_indices=(3,3),
                  reference_target_indices=(3,), reference_frequencies_hz_levels=(3,5))
    if type(n) is not int or type(a) is not int or n<=0 or a<=0 or set(arrays)!=set(shapes):
        raise ValueError('modern RF reference UNVERIFIED: complete original array keys/counts required')
    for key,shape in shapes.items():
        value=np.asarray(arrays[key])
        indices=key in ('reference_selected_indices','reference_target_indices')
        if (value.shape!=shape or value.dtype.kind not in ('iu' if indices else 'iuf') or
                not np.isfinite(value).all()):
            raise ValueError('modern RF reference UNVERIFIED: missing nodes/modes or invalid array '+key)
    if (any(np.any(arrays[key]<=0) for key in ('volume_weights_m3','axis_weights_m','native_volume_density_ratio','reference_frequencies_hz_levels')) or
            np.any(arrays['axis_points_rz_m'][:,0]!=0)):
        raise ValueError('modern RF reference UNVERIFIED: all positive weights and physical axis required')
    selected=arrays['reference_selected_indices'];targets=arrays['reference_target_indices']
    if (np.any((selected<0)|(selected>=5)) or np.any((targets<0)|(targets>=5)) or
            any(len(set(row))!=3 for row in selected) or not np.array_equal(selected[:,0],targets)):
        raise ValueError('modern RF reference UNVERIFIED: actual target and all guard selections required')


def _reference_two_changes(arrays, quantities):
    from .adaptive_efficiency_accuracy import LIMITS, _error
    n=len(arrays['volume_weights_m3']);w=arrays['volume_weights_m3'];aw=arrays['axis_weights_m']
    fields=arrays['reference_fields_levels'];target=arrays['reference_target_indices'];result=[]
    for k in (0,1):
        a=fields[k,:,target[k]];b=fields[k+1,:,target[k+1]]
        overlap=float(np.dot(w*a[:n,2],b[:n,2]))
        if not math.isfinite(overlap) or overlap==0:
            raise ValueError('reference two changes UNVERIFIED: no common magnetic sign')
        sign=1 if overlap>0 else -1
        changes=dict(electric_relative_l2=_error(a[:n,:2],b[:n,:2],w[:,None],sign),
                     magnetic_relative_l2=_error(a[:n,2],b[:n,2],w,sign),
                     axis_ez_relative_l2=_error(a[n:,1],b[n:,1],aw,sign))
        for q in quantities[k:k+2]:
            if (any(type(q.get(key)) not in (int,float) or not math.isfinite(q[key]) or q[key]<=0 for key in list(LIMITS)[:6]) or
                    abs(q['r_over_q_accelerator_ohm']/(2*q['r_over_q_circuit_ohm'])-1)>1e-12):
                raise ValueError('reference RF UNVERIFIED: complete positive quantities and both R/Q conventions required')
        changes.update({key:abs(quantities[k+1][key]/quantities[k][key]-1) for key in list(LIMITS)[:6]})
        result.append(dict(relative_changes=changes,single_sign=sign,
                           status='PASS' if all(v<=LIMITS[key] for key,v in changes.items()) else 'UNVERIFIED'))
    if any(row['status']!='PASS' for row in result):
        raise ValueError('independent three-h reference two changes UNVERIFIED')
    return result


def _scaled_modern_arrays(arrays, scale):
    result={k:v.copy() for k,v in arrays.items()}
    for key in ('analytic_volume_points_rz_m','fixed_native_volume_points_rz_m','axis_points_rz_m'):
        result[key]*=scale
    result['volume_weights_m3']*=scale**3
    result['axis_weights_m']*=scale
    result['reference_fields_levels']/=math.sqrt(scale)
    result['reference_frequencies_hz_levels']/=scale
    return result


def load_curved_rf_goal_efficiency_reference(case_id, *, bindings=None):
    """Read the fixed complete references for one of the six original requests.

    Fixed prepared-manifest SHAs prevent replacing fields by recomputing a
    caller's manifest hash. Every supplied mode/node is retained. This verifies
    references only; the fresh native initial mode must still be identified from
    its actual fields, not a rank or the reference's symbolic label.
    """
    from .adaptive_efficiency_accuracy import LIMITS
    from .adaptive_efficiency_reference import _read_binding, _bound_file, verify_reference_bytes
    family=next((name for name in ('sphere','prolate','rounded-two-lobe')
                 if type(case_id) is str and case_id in (name+'-scale-1',name+'-scale-2')), None)
    if family is None:
        raise ValueError('RF goal reference requires one of the six fixed case ids')
    request,case,scale=_fixed_request(case_id,family)
    bindings,bound,aliases=_bindings(bindings)
    grids=[]
    if family=='sphere':
        old,_=_original_n06_reference('sphere',bindings,bound,aliases)
        for original in old['grids']:
            data=build_sphere_rf_goal_reference(case_id,order=original['order'])
            if scale==1:
                for key in ('reference_fields','reference_axis_ez','native_volume_points_rz_m','volume_weights_m3','axis_points_rz_m','axis_weights_m','native_volume_density_ratio'):
                    if not np.array_equal(data[key], original['all_reference_arrays'][key]):
                        raise ValueError('sphere reference differs from original full N06 mathematics/grid')
            arrays={k:v for k,v in data.items() if isinstance(v,np.ndarray)}
            grids.append(dict(order=data['order'],points=data['native_volume_points_rz_m'],
                              axis=data['axis_points_rz_m'],weights=data['volume_weights_m3'],axis_weights=data['axis_weights_m'],
                              density=data['native_volume_density_ratio'],reference_fields=data['reference_fields'],
                              reference_axis_ez=data['reference_axis_ez'],quantities=data['reference_quantities'],
                              all_reference_arrays=arrays,reference_two_changes=None,
                              reference_field_path=original['reference_field_path'],reference_field_sha256=original['reference_field_sha256']))
    else:
        if family=='rounded-two-lobe':
            old,manifest=_original_n06_reference(family,bindings,bound,aliases)
            originals=[(g,g['all_reference_arrays'],manifest['original_reference_quantities']) for g in old['grids']]
            base_request,base_case,_=_fixed_request(family+'-scale-1',family)
            if base_case!=old['case'] or base_request['initial_mesh']!=old['source_mesh']:
                raise ValueError('rounded reference differs from complete original RF Case/source mesh')
        else:
            path,manifest=_read_binding(bindings['prolate_manifest'],bound)
            if (manifest.get('status')!='REFERENCE_DATA_PREPARED' or manifest['reference_maxh_m']!=[.005,.0025,.00125] or
                    manifest['component_order']!=list(COMPONENTS) or manifest['normalization_j']!=1. or manifest['beta']!=1.):
                raise ValueError('prolate reference requires the complete original three-h/five-mode preparation')
            for p,h in manifest['bound_inputs'].items():_bound_file(p,h,bound)
            originals=[]
            for entry in manifest['grids']:
                file=_bound_file(path.parent/entry['path'],entry['sha256'],bound)
                with np.load(file,allow_pickle=False) as z:arrays={k:z[k].copy() for k in z.files}
                originals.append((dict(entry,reference_field_path=str(file),reference_field_sha256=entry['sha256']),arrays,entry['reference_quantities']))
        if [g['order'] for g,_,_ in originals]!=[16,24]:
            raise ValueError('modern RF reference UNVERIFIED: both complete Gauss16/24 grids required')
        for original,arrays,quantities in originals:
            n=len(arrays['volume_weights_m3']);a=len(arrays['axis_weights_m'])
            _modern_arrays(arrays,n,a)
            transformed=_scaled_modern_arrays(arrays,scale)
            q=deepcopy(quantities)
            for value in q:value['frequency_hz']/=scale
            changes=_reference_two_changes(transformed,q)
            if family=='prolate':
                mapped=map_prolate_rf_goal_points(case_id,transformed['analytic_volume_points_rz_m'])
                if (not np.array_equal(mapped['native_volume_points_rz_m'],transformed['fixed_native_volume_points_rz_m']) or
                        not np.array_equal(mapped['native_volume_density_ratio'],transformed['native_volume_density_ratio'])):
                    raise ValueError('prolate reference grid differs from the actual complete coarse RF P2 domain')
            target=int(transformed['reference_target_indices'][-1]);fields=transformed['reference_fields_levels']
            grids.append(dict(order=original['order'],points=transformed['fixed_native_volume_points_rz_m'],
                              axis=transformed['axis_points_rz_m'],weights=transformed['volume_weights_m3'],axis_weights=transformed['axis_weights_m'],
                              density=transformed['native_volume_density_ratio'],reference_fields=fields[-1,:n,target],
                              reference_axis_ez=fields[-1,n:,target,1],quantities=q[-1],reference_quantities_levels=q,
                              all_reference_arrays=transformed,reference_two_changes=changes,
                              reference_selected_ids=[['target','guard-2','guard-3']]*3,
                              reference_field_path=original['reference_field_path'],reference_field_sha256=original['reference_field_sha256']))
        for interval in (0,1):
            a,b=[grid['reference_two_changes'][interval]['relative_changes'] for grid in grids]
            if any(abs(a[key]-b[key])>LIMITS[key] for key in a):
                raise ValueError('reference Gauss16/24 error differences UNVERIFIED')
    result=dict(case_id=case_id,request=deepcopy(request),case=case,source_mesh=deepcopy(request['initial_mesh']),
                initial_ids=deepcopy(request['initial_ids']),grids=grids,bound_inputs=bound,
                independent_reference_kind='SphereTM' if family=='sphere' else 'N03_modern_three_h_five_modes',
                historical_source_aliases=deepcopy(aliases),
                native_id_reference_labels={i:('target' if i=='fundamental' else i) for i in request['initial_ids']},
                reference_status='REFERENCE_DATA_VERIFIED',native_accuracy_status='NOT_RUN',physical_error_bound=None,
                scale_rule='U=a^2 J; coordinates a, E/H a^-1/2, frequency a^-1, volume weights a^3, axis weights a; original raw inputs remain scale one',
                scope='fixed complete reference data, all modes/points and three-h changes; native source/physical ID/accuracy/efficiency remain separate')
    verify_reference_bytes(result)
    return result

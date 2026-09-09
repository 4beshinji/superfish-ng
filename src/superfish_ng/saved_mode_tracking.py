# SPDX-License-Identifier: Apache-2.0
"""Recompute saved mode correspondences from byte-identified native FEM results."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from . import __version__
from .config import keys
from .completion import digest
from .project import parse_json
from .saved import read_solution
from .mode_tracking import track_cylindrical_modes


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def _snapshot(directory):
    from .config import Case
    from .te import is_te
    if is_te(Case.load(directory/'case.json')):
        from .te_saved import _names
        names = _names(Case.load(directory/'case.json')) | {'te_complete.json'}
        result={}
        for name in sorted(names):
            path=directory/name
            if not path.is_file() or path.is_symlink():
                raise ValueError(f'TE tracking requires complete regular native files: {path}')
            result[name]=digest(path)
        return dict(directory=str(directory),sha256=result)
    required=('case.json','results.json','fields.npz')
    optional=('mesh.json','save_protocol.json','save_complete.json')
    result={}
    for name in required+tuple(n for n in optional if (directory/n).exists()):
        path=directory/name
        if not path.is_file() or path.is_symlink():raise ValueError(f'tracking source requires a regular native result file: {path}')
        result[name]=digest(path)
    return dict(directory=str(directory),sha256=result)


def validate_tracking_controls(controls):
    """Validate every step configuration before a Study may stop early."""
    names=('mapping','sample_order','minimum_overlap','minimum_assignment_margin','relative_cluster_gap','minimum_relative_singular_value')
    if isinstance(controls,dict) and controls.get('mapping')=='nested_affine':
        names=tuple(name for name in names if name!='sample_order')+('marked_cells',)
    if isinstance(controls,dict) and controls.get('mapping')=='nested_curved':
        names=tuple(name for name in names if name!='sample_order')
    if isinstance(controls,dict) and controls.get('mapping')=='piecewise_remesh':names+=('comparison_meshes',)
    if isinstance(controls,dict) and controls.get('mapping')=='affine_remesh':names+=('affine_map',)
    if isinstance(controls,dict) and controls.get('mapping')=='paired_mesh':names+=('vertex_pairs',)
    if isinstance(controls,dict) and ('cluster_transition_policy' in controls or 'minimum_cluster_link' in controls):
        names+=('cluster_transition_policy','minimum_cluster_link')
        if controls.get('cluster_transition_policy') not in ('retain_subspace','retain_connected_subspace'):raise ValueError('cluster_transition_policy must be retain_subspace or retain_connected_subspace')
    keys(controls,names,names,'mode tracking controls')
    from .mode_tracking import _control
    mapping=controls['mapping']
    if mapping not in ('normalized_cylinder','normalized_profile','paired_mesh','same_domain','affine_remesh','piecewise_remesh','curved_same_domain','nested_affine','nested_curved'):raise ValueError('mapping must name a supported cylinder/profile, paired, same-domain, affine/piecewise, curved or nested_affine/nested_curved correspondence')
    if mapping=='nested_affine':
        marked=controls['marked_cells']
        if type(marked) is not list or not marked or any(type(i) is not int or i<0 for i in marked) or len(set(marked))!=len(marked):
            raise ValueError('nested_affine marked_cells requires distinct nonnegative integer cell indices')
    elif mapping!='nested_curved':
        order=controls['sample_order'];limit=32 if mapping in ('paired_mesh','same_domain','affine_remesh','piecewise_remesh','curved_same_domain') else 256
        if type(order) is not int or not 2<=order<=limit:raise ValueError(f'sample_order must be an integer from 2 to {limit}')
    _control(controls['minimum_overlap'],'minimum_overlap')
    _control(controls['minimum_assignment_margin'],'minimum_assignment_margin',zero=True)
    _control(controls['relative_cluster_gap'],'relative_cluster_gap',zero=True,one=False)
    _control(controls['minimum_relative_singular_value'],'minimum_relative_singular_value')
    if 'minimum_cluster_link' in controls:_control(controls['minimum_cluster_link'],'minimum_cluster_link')
    if mapping=='piecewise_remesh':
        from .piecewise_remesh_tracking import validate_comparison_meshes
        validate_comparison_meshes(controls['comparison_meshes'])
    if mapping=='affine_remesh':
        from .affine_remesh_tracking import validate_affine_map
        validate_affine_map(controls['affine_map'])
    if mapping=='paired_mesh':
        pairs=controls['vertex_pairs']
        if type(pairs) is not list or any(type(p) is not list or len(p)!=2 or any(type(i) is not int or i<0 for i in p) for p in pairs):
            raise ValueError('vertex_pairs must list zero-based integer vertex pairs')


def build_saved_mode_tracking(request,*,base_directory=None):
    if not isinstance(request,dict):raise ValueError('mode tracking request must be an object')
    version=request.get('schema_version')
    if type(version) is not int or version not in (1,2):raise ValueError('mode tracking request requires schema_version 1 or 2')
    identity='previous_ids' if version==1 else 'previous_groups'
    fields=('schema_version','previous_run','current_run',identity,'controls')
    keys(request,fields,fields,'mode tracking request')
    _canonical(request)
    controls=request['controls']
    validate_tracking_controls(controls)
    normalized=deepcopy(request);root=Path.cwd() if base_directory is None else Path(base_directory)
    directories=[]
    for name in ('previous_run','current_run'):
        value=request[name]
        if type(value) is not str or not value.strip():raise ValueError(f'{name} requires a nonempty native saved-result directory')
        path=Path(value);path=(path if path.is_absolute() else root/path).resolve()
        directories.append(path);normalized[name]=str(path)
    before=[_snapshot(path) for path in directories]
    from .config import Case
    from .te import is_te
    polarizations=[is_te(Case.load(path/'case.json')) for path in directories]
    if any(polarizations):
        if not all(polarizations):
            raise ValueError('mixed TE/TM tracking is unsupported; use two results with the same polarization')
        if controls['mapping'] != 'normalized_cylinder':
            raise ValueError('TE saved tracking currently requires normalized_cylinder mapping')
        from .te_saved import read_te_run
        solutions=[read_te_run(path) for path in directories]
    else:
        solutions=[read_solution(path) for path in directories]
    tracker=track_cylindrical_modes
    if controls['mapping']=='normalized_profile':
        from .profile_mode_tracking import track_profile_modes
        tracker=track_profile_modes
    elif controls['mapping']=='paired_mesh':
        from .paired_mesh_tracking import track_paired_mesh_modes
        tracker=track_paired_mesh_modes
    elif controls['mapping']=='same_domain':
        from .same_domain_tracking import track_same_domain_modes
        tracker=track_same_domain_modes
    elif controls['mapping']=='affine_remesh':
        from .affine_remesh_tracking import track_affine_remesh_modes
        tracker=track_affine_remesh_modes
    elif controls['mapping']=='piecewise_remesh':
        from .piecewise_remesh_tracking import track_piecewise_remesh_modes
        tracker=track_piecewise_remesh_modes
    elif controls['mapping']=='curved_same_domain':
        from .curved_same_domain_tracking import track_curved_same_domain_modes
        tracker=track_curved_same_domain_modes
    elif controls['mapping']=='nested_affine':
        from .nested_affine_tracking import track_nested_affine_modes
        tracker=track_nested_affine_modes
    elif controls['mapping']=='nested_curved':
        from .nested_curved_tracking import track_nested_curved_modes
        tracker=track_nested_curved_modes
    report=tracker(*solutions,request.get('previous_ids'),**controls,
        **({'previous_identity_groups':request['previous_groups']} if version==2 else {}))
    if before!=[_snapshot(path) for path in directories]:
        raise ValueError('tracking source changed during field sampling; use stable saved results and retry')
    return dict(schema_version=version,document_type='saved_mode_tracking',software_version=__version__,
                request=normalized,request_sha256=hashlib.sha256(_canonical(normalized).encode()).hexdigest(),
                sources=before,tracking=report,status=report['status'],
                scope='replayed native saved-field correspondence; source byte identities required; not a continuous tracking history or FEM convergence certificate')


def save_mode_tracking(request,path,*,base_directory=None):
    document=build_saved_mode_tracking(request,base_directory=base_directory)
    text=json.dumps(document,indent=2,allow_nan=False)+'\n'
    with Path(path).open('x',encoding='utf-8') as stream:stream.write(text)
    return document


def replay_mode_tracking(document):
    fields=('schema_version','document_type','software_version','request','request_sha256','sources','tracking','status','scope')
    keys(document,fields,fields,'saved mode tracking')
    request=document['request']
    if not isinstance(request,dict):raise ValueError('saved tracking request must be an object')
    for key in ('previous_run','current_run'):
        if type(request.get(key)) is not str or not Path(request[key]).is_absolute():
            raise ValueError('saved mode tracking requires absolute source paths; regenerate from the request')
    expected=build_saved_mode_tracking(request)
    if _canonical(document)!=_canonical(expected):
        raise ValueError('mode tracking replay differs from saved data or source identities; regenerate from the source request')
    return expected


def read_mode_tracking(path):
    return replay_mode_tracking(parse_json(Path(path).read_text(encoding='utf-8')))

# SPDX-License-Identifier: Apache-2.0
"""Bind a saved N06 native domain to the complete original Case/source mesh.

Domain verification is separate from field accuracy, mode IDs, ancestry and
resource/convergence acceptance. Original whole-boundary criteria are reused.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from .adaptive_refinement import _request
from .completion import digest
from .curved_same_domain_tracking import compare_quadratic_space_boundaries
from .curved_solution import CurvedSolution
from .curved_space import case_curved_space
from .mesh import make_mesh
from .mesh_input import mesh_from_dict,mesh_to_dict
from .same_domain_tracking import _same_boundary
from .saved import read_solution


def _native_files(directory):
    if any(p.is_symlink() for p in (directory,*directory.parents)):
        raise ValueError('efficiency native source requires a directory without symlinks')
    if not directory.is_dir():
        raise ValueError('efficiency native source requires an existing directory')
    files={}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError('efficiency native source contains a symlink: '+str(path))
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError('efficiency native source requires regular files: '+str(path))
        files[str(path.relative_to(directory))]=digest(path)
    return files


def verify_efficiency_saved_domain(request,directory):
    """Verify a complete saved domain without new FEM, fitting or reprojection.

    Curved histories may differ only in their numerical refinement fields;
    the exact initial source and whole P2 boundary must remain unchanged.
    Affine complete Case and whole tagged straight boundaries must coincide.
    A refined affine run alone cannot establish original mesh ancestry: the
    caller must check its first run and actual nested tracking separately.
    All native files, including CSV/VTK/completion metadata, are pinned before
    and after strict original reconstruction. No caller-supplied ID is trusted.
    """
    request=deepcopy(request)
    case=_request(request)
    model=None if case.model is None else case.model.to_dict()
    if (case.element_order!=2 or case.curved_refinement_levels or case.curved_refinement_steps or
            model is None or case.z_min!='pec' or case.z_max!='pec' or
            (model['physics'],model['coordinates'],model['polarization'],model['azimuthal_index'])!=
            ('rf_eigenmode','axisymmetric','tm',0) or
            model['materials']!=[dict(id='vacuum',type='vacuum')] or
            model['regions']!=[dict(id='cavity',material='vacuum',domain='interior')]):
        raise ValueError('efficiency domain requires original fresh closed vacuum axis-connected m=0 TM P2')
    directory=Path(directory).absolute()
    before=_native_files(directory)
    saved=read_solution(directory)
    current_case=saved.case
    if getattr(saved,'reflection_source_case',None) is not None:
        raise ValueError('efficiency domain requires direct full native fields, not reflected source sectors')
    base_case=replace(current_case,curved_refinement_levels=0,curved_refinement_steps=()) if case.geometry_order==2 else current_case
    if base_case!=case:
        raise ValueError('saved efficiency domain differs from the complete original Case; only curved numerical refinement history may change')
    initial=make_mesh(case) if request['initial_mesh'] is None else mesh_from_dict(case,request['initial_mesh'])
    source=mesh_to_dict(initial)
    source_sha=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    native_mesh_exact=None
    source_exact=None
    if case.geometry_order==2:
        if not isinstance(saved,CurvedSolution):
            raise ValueError('efficiency native container disagrees with original curved P2 geometry')
        if saved.source_mesh_data!=source:
            raise ValueError('saved curved efficiency initial source mesh differs from the complete original source')
        source_exact=True
        initial_space=case_curved_space(case,initial)
        boundary=compare_quadratic_space_boundaries(case,initial_space,current_case,saved.space)
        if boundary['common_interval_count']<=0:
            raise ValueError('efficiency whole P2 boundary has no verified intervals')
        geometry_kind='whole P2 native boundary on every original curve-parameter interval'
        ancestry='original initial curved source exact; numerical history is reconstructed by original strict reader; individual IDs/parent tracking not checked'
    else:
        native_mesh_exact=mesh_to_dict(saved.mesh)==source
        tolerance=_same_boundary(SimpleNamespace(mesh=initial),saved)
        boundary=dict(roundoff_tolerance_m=tolerance,
                      criterion='complete tagged segment coverage in both directions, allowing subdivision; original same-domain criterion')
        geometry_kind='whole straight native boundary including axis and every PEC segment'
        ancestry='refined affine run alone does not prove original source ancestry; verify first saved mesh and actual nested parent tracking separately'
    after=_native_files(directory)
    if after!=before:
        raise ValueError('efficiency native sources changed during domain validation')
    return dict(status='DOMAIN_VERIFIED',base_case=case.to_dict(),initial_source_mesh=source,
                initial_source_mesh_canonical_sha256=source_sha,initial_source_mesh_exact_match=source_exact,
                native_mesh_exact_initial_match=native_mesh_exact,boundary=boundary,geometry_kind=geometry_kind,
                native_directory=str(directory),native_files_sha256=before,native_sources_unchanged=True,
                individual_mode_identity_status='NOT_CHECKED',refinement_ancestry_scope=ancestry,
                physical_error_bound=None,
                scope='complete original Case/source and whole native boundary only; no eigen/field/RF accuracy, ID, budget or two-uniform-interval acceptance')

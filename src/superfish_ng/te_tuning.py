# SPDX-License-Identifier: Apache-2.0
"""TE profile tuning guards and native readers, without TM field aliases."""
from pathlib import Path
from .te import is_te



def validate_te_affine_sector(project,laws):
    """Require a single source sector and a plane-preserving polynomial law."""
    from .te import validate_te_case
    case=project.case
    validate_te_case(case)
    ends=(case.z_min,case.z_max)
    if (sum(t!='pec' for t in ends)>1 or
            any(t not in ('axis','pec','electric_symmetry','magnetic_symmetry') for t in case.curved_contour.edge_tags)):
        raise ValueError('TE affine geometry requires PEC/axis and at most one symmetry end')
    if project.reflect_full and ends==('pec','pec'):
        raise ValueError('TE reflected affine geometry requires one source symmetry plane')
    if ends!=('pec','pec'):
        shear=laws.get('axial_shear') if isinstance(laws,dict) else None
        if type(shear) is not list or not shear or any(c!=0 for c in shear):
            raise ValueError('TE symmetry affine law requires identically zero axial shear to preserve the symmetry plane')


def validate_te_request(request,project):
    case=project.case
    mapping=request['controls'].get('mapping') if isinstance(request['controls'],dict) else None
    curved=request['schema_version'] in (4,5,8) or (request['schema_version']==7 and request.get('geometry_kind')=='curved_harmonic')
    if curved:
        affine=request['schema_version']==4
        if (case.curved_contour is None or case.geometry_order!=2 or project.sections is not None
                or mapping!=('affine_remesh' if affine else 'piecewise_remesh')):
            raise ValueError('TE curved tuning requires native P2 geometry and the matching affine_remesh or piecewise_remesh mapping')
        if affine:
            validate_te_affine_sector(project,request['affine_coefficients'])
        else:
            from .curved_same_domain_tracking import _te_end_conditions
            _te_end_conditions([case,case])
        if request['rf_coordinates']!='fixed':
            raise ValueError('TE curved tuning requires fixed RF metadata; accelerating coordinates are not applicable')
        return
    if (request['schema_version'] not in (1,2,3,7) or
            (request['schema_version']==7 and request['geometry_kind']!='profile') or
            project.sections is not None or case.geometry_order!=1 or case.geometry_type!='profile' or
            (mapping=='normalized_cylinder' and any(r!=case.profile[0][1] for _,r in case.profile)) or
            sum(t!='pec' for t in (case.z_min,case.z_max))>1 or
            mapping not in ('normalized_cylinder','normalized_profile')):
        raise ValueError('TE tuning/tracking integration is pending for this geometry or mapping; use a straight positive-radius profile, normalized_profile (or normalized_cylinder for cylinders) and at most one symmetry end')
    if project.reflect_full and case.z_min==case.z_max=='pec':
        raise ValueError('TE reflected tuning requires one source symmetry plane')


def read_trial_solution(directory,project):
    if is_te(project.case):
        from .te_saved import read_te_run
        return read_te_run(directory)
    from .saved import read_solution
    return read_solution(directory)


def trial_sources(directory,project):
    """Keep the old TM verifier and add complete TE-native job verification."""
    if not is_te(project.case):
        from .tracked_study import _point_sources
        return _point_sources(directory,project)
    from .completion import digest
    from .jobs import read_job
    from .project import Project
    from .saved_mode_tracking import _canonical
    directory=Path(directory)
    if not directory.is_absolute() or directory.is_symlink():
        raise ValueError('TE tune trials require absolute non-symlink native Job directories')
    before={p.relative_to(directory).as_posix():digest(p) for p in directory.rglob('*') if p.is_file()}
    if read_job(directory)['status']!='complete':raise ValueError('TE tune trial is incomplete')
    if _canonical(Project.load(directory/'project.json').to_dict())!=_canonical(project.to_dict()):
        raise ValueError('TE tune trial Project differs from its declared value')
    read_trial_solution(directory/'solution',project)
    after={p.relative_to(directory).as_posix():digest(p) for p in directory.rglob('*') if p.is_file()}
    if before!=after:raise ValueError('TE tune trial sources changed during verification')
    return before


def scope_note(project):
    if not is_te(project.case):return ''
    sector=project.case.z_min!='pec' or project.case.z_max!='pec'
    return ('; TE Ephi electric-field identities, accelerating quantities not applicable' +
            ('; source symmetry-sector frequency order, not full-spectrum ranks' if sector else ''))

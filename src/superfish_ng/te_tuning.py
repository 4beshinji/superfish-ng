# SPDX-License-Identifier: Apache-2.0
"""TE profile tuning guards and native readers, without TM field aliases."""
from pathlib import Path
from .te import is_te


def validate_te_request(request,project):
    case=project.case
    mapping=request['controls'].get('mapping') if isinstance(request['controls'],dict) else None
    curved=request['schema_version']==5 or (request['schema_version']==7 and request.get('geometry_kind')=='curved_harmonic')
    if curved:
        if (case.curved_contour is None or case.geometry_order!=2 or project.sections is not None or project.reflect_full
                or any(t not in ('axis','pec') for t in case.curved_contour.edge_tags) or mapping!='piecewise_remesh'):
            raise ValueError('TE curved tuning requires direct native P2 closed PEC/axis geometry and piecewise_remesh')
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

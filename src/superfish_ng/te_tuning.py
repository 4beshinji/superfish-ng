# SPDX-License-Identifier: Apache-2.0
"""TE cylinder tuning guards and native readers, without TM field aliases."""
from pathlib import Path
from .te import is_te


def validate_te_request(request,project):
    case=project.case
    if (request['schema_version'] not in (1,2,3,7) or
            (request['schema_version']==7 and request['geometry_kind']!='profile') or
            project.sections is not None or case.geometry_order!=1 or case.geometry_type!='profile' or
            any(r!=case.profile[0][1] for _,r in case.profile) or
            sum(t!='pec' for t in (case.z_min,case.z_max))>1 or
            not isinstance(request['controls'],dict) or request['controls'].get('mapping')!='normalized_cylinder'):
        raise ValueError('TE tuning/tracking integration is pending for this geometry or mapping; use a straight constant-radius profile, normalized_cylinder and at most one symmetry end')
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

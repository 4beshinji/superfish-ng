# SPDX-License-Identifier: Apache-2.0
"""TE-specific native verification and import for ordinary local solve jobs."""
import json
import os
from pathlib import Path
import shutil
import time
import uuid
from .completion import digest
from .config import Case
from .project import Project, parse_json
from .saved_mode_tracking import _canonical
from .te import is_te
from .te_saved import read_te_run, _run_names


def verify_te_job_if_present(directory, manifest):
    """Bind the declared project and full TE native result before accepting a job."""
    directory = Path(directory)
    result_dir = directory/'solution'
    data = parse_json((directory/'project.json').read_text())
    results = parse_json((result_dir/'results.json').read_text())
    case_data = data.get('case', data)
    declared = case_data.get('model', {}).get('polarization') == 'te'
    if not (declared or (result_dir/'te_complete.json').exists() or results.get('physics') == 'axisymmetric_m0_te'):
        return
    project = Project.from_dict(data)
    if not is_te(project.case):
        raise ValueError('TE job output requires a TE project declaration')
    required = {'project.json', *(f'solution/{name}' for name in _run_names(result_dir,project.case)), 'solution/te_complete.json'}
    if not required.issubset(manifest['files']):
        raise ValueError('TE job manifest is missing native completion, geometry or required output')
    solution = read_te_run(result_dir)
    reflected=solution.reflection_source_case is not None
    expected_source=solution.reflection_source_case if reflected else solution.case
    if reflected != project.reflect_full or expected_source != project.case:
        raise ValueError('TE saved case differs from the job project')
    if project.mesh_data is not None and _canonical(project.mesh_data) != _canonical(solution.source_mesh_data):
        raise ValueError('TE saved source mesh differs from the explicit project mesh')
    for name in sorted(required):
        path=directory/name
        if path.is_symlink() or not path.is_file() or digest(path)!=manifest['files'][name]:
            raise ValueError('TE job files changed during verification: '+name)
    manifest_path=directory/'manifest.json'
    if manifest_path.is_symlink() or _canonical(parse_json(manifest_path.read_text()))!=_canonical(manifest):
        raise ValueError('TE job completion manifest changed during verification')


def import_te_result(manager, source, solution_dir, managed_project=None):
    """Import verified TE bytes with completion last and a reproducible source mesh."""
    from .jobs import _prepare, _state, _write_json, read_job
    source, solution_dir = Path(source), Path(solution_dir)
    managed = managed_project is not None
    case = Case.load(solution_dir/'case.json')
    names = _run_names(solution_dir,case) | {'te_complete.json'}
    paths = [solution_dir/name for name in sorted(names)]
    if managed:
        paths += [source/name for name in ('project.json', 'manifest.json', 'job.json')]
    def snapshot():
        if any(p.is_symlink() or not p.is_file() for p in paths):
            raise ValueError('TE import source is incomplete or linked')
        return {str(p): digest(p) for p in paths}
    before = snapshot()
    saved = read_te_run(solution_dir)
    if managed:
        if read_job(source)['status'] != 'complete':
            raise ValueError('TE source job is not complete')
        project = Project.load(source/'project.json')
        if _canonical(project.to_dict()) != _canonical(managed_project.to_dict()):
            raise ValueError('TE source project changed before import')
    else:
        project = Project(saved.reflection_source_case or saved.case, reflect_full=saved.reflection_source_case is not None, mesh_data=saved.source_mesh_data)
    if snapshot() != before:
        raise ValueError('TE import source changed during verification')
    identifier = time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10]
    directory = manager.directory(identifier)
    _prepare(project, directory)
    try:
        target = directory/'solution'
        target.mkdir()
        for name in sorted(names-{'te_complete.json'}):
            path = solution_dir/name
            if path.is_symlink():
                raise ValueError('TE import source became linked')
            shutil.copyfile(path, target/name)
        if snapshot() != before:
            raise ValueError('TE import source changed during copying')
        temporary = target/'.import-te-completion.tmp'
        shutil.copyfile(solution_dir/'te_complete.json', temporary)
        os.link(temporary, target/'te_complete.json')
        temporary.unlink()
        read_te_run(target)
        if snapshot() != before:
            raise ValueError('TE import source changed during publication')
        files = {'project.json': digest(directory/'project.json')}
        files.update({f'solution/{name}': digest(target/name) for name in names})
        _write_json(directory/'manifest.json', dict(manifest_version=1, files=files, imported_from=str(source)))
        (directory/'log.txt').write_text('Imported saved TE output; no new FEM solve.\n')
        _state(directory, 'complete', stage='imported saved result', origin='imported',
               source_completion='verified manifest' if managed else 'verified TE native completion', numerical_validation='not_checked')
        read_job(directory)
    except Exception as exc:
        _state(directory, 'failed', error=str(exc))
        raise
    return identifier

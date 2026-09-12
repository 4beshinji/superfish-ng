# SPDX-License-Identifier: Apache-2.0
"""Owned Hphi convergence levels with complete original FEM and diagnostic replay."""
import hashlib,json,os,tempfile
from pathlib import Path
from .config import keys
from .project import parse_json
from .jobs import _implementation_hashes
from .hphi_convergence import HphiConvergence,compare_hphi_convergence
from .hphi_project import HphiProject
from .hphi_native import solve_hphi,save_hphi_run,read_hphi_run
from .coaxial_saved import FILES


def _load(path):
    if path.is_symlink() or not path.is_file():raise ValueError('Hphi convergence metadata must be regular files')
    return parse_json(path.read_text(encoding='utf-8'))


def _publish(path,data):
    with tempfile.TemporaryDirectory(prefix='.hphi-convergence-',dir=path.parent) as directory:
        stage=Path(directory)/path.name;stage.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8');os.link(stage,path)


def _level(index):return f'level-{index:04d}'


def _hashes(directory,request):
    if directory.is_symlink() or not directory.is_dir():raise ValueError('Hphi convergence must use an owned regular directory')
    names=['convergence.json','convergence-results.json'];expected={_level(i) for i in range(len(request.projects))}
    if {p.name for p in directory.iterdir() if p.name.startswith('level-')}!=expected:raise ValueError('Hphi convergence level set differs from the request')
    for level in sorted(expected):
        if (directory/level).is_symlink() or not (directory/level).is_dir() or (directory/level/'solution').is_symlink():raise ValueError('Hphi convergence levels must be owned directories')
        names.append(level+'/project.json');names.extend(level+'/solution/'+name for name in (*sorted(FILES),'manifest.json'))
    result={}
    for name in names:
        path=directory/name
        if path.is_symlink() or not path.is_file():raise ValueError('Hphi convergence requires every owned native file')
        result[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def read_hphi_convergence(directory):
    directory=Path(directory);manifest=_load(directory/'manifest.json')
    if manifest.get('kind')=='hphi_convergence':
        from .hphi_convergence_jobs import read_hphi_convergence_job
        return read_hphi_convergence_job(directory)
    names=['format','manifest_version','files','implementation_sha256','source_changed_during_run'];keys(manifest,names,names,'Hphi convergence manifest')
    if manifest['format']!='superfish_ng_hphi_convergence_manifest' or type(manifest['manifest_version']) is not int or manifest['manifest_version']!=1:
        raise ValueError('expected superfish_ng_hphi_convergence_manifest version 1')
    implementation=manifest['implementation_sha256']
    if not isinstance(implementation,dict) or not implementation or any(not isinstance(k,str) or not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for k,v in implementation.items()) or manifest['source_changed_during_run'] is not False:
        raise ValueError('Hphi convergence requires stable execution provenance')
    request=HphiConvergence.from_dict(_load(directory/'convergence.json'));before=_hashes(directory,request)
    if manifest['files']!=before:raise ValueError('Hphi convergence manifest must bind the request, result and every native level')
    solutions=[]
    for index,project in enumerate(request.projects):
        level=directory/_level(index)
        if HphiProject.from_dict(_load(level/'project.json'))!=project:raise ValueError('Hphi convergence level Project differs from the declared mesh sequence')
        solutions.append(read_hphi_run(level/'solution'))
    result=compare_hphi_convergence(request,solutions);saved=_load(directory/'convergence-results.json')
    if json.dumps(result,sort_keys=True,allow_nan=False)!=json.dumps(saved,sort_keys=True,allow_nan=False):raise ValueError('Hphi convergence result disagrees with full original-field replay')
    if _hashes(directory,request)!=before or _load(directory/'manifest.json')!=manifest:raise ValueError('Hphi convergence changed during verification')
    return result


def execute_hphi_convergence(request,directory):
    if not isinstance(request,HphiConvergence):raise ValueError('expected HphiConvergence')
    request=HphiConvergence.from_dict(request.to_dict());directory=Path(directory);implementation=_implementation_hashes()
    directory.mkdir(parents=True,exist_ok=False);request.save(directory/'convergence.json');request_bytes=(directory/'convergence.json').read_bytes();solutions=[]
    for index,project in enumerate(request.projects):
        level=directory/_level(index);level.mkdir();project.save(level/'project.json')
        solution=solve_hphi(project.case);save_hphi_run(project.case,solution,level/'solution');solutions.append(solution)
    result=compare_hphi_convergence(request,solutions);_publish(directory/'convergence-results.json',result)
    hashes=_hashes(directory,request)
    if (directory/'convergence.json').read_bytes()!=request_bytes or _implementation_hashes()!=implementation:raise ValueError('Hphi convergence request or implementation changed during execution')
    _publish(directory/'manifest.json',dict(format='superfish_ng_hphi_convergence_manifest',manifest_version=1,files=hashes,implementation_sha256=implementation,source_changed_during_run=False))
    replayed=read_hphi_convergence(directory)
    if _implementation_hashes()!=implementation:raise ValueError('Hphi convergence implementation changed during completion')
    return replayed

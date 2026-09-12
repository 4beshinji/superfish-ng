# SPDX-License-Identifier: Apache-2.0
"""Check public capability metadata against real CLI and native interfaces."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.curved_meridional_reference import fixture
from superfish_ng.model import capabilities
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.axis_hphi import AxisHphiCase,AxisAccelerationPath
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi import CurvedHphiCase
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_native import solve_hphi,save_hphi_run,read_hphi_run,hphi_result
from superfish_ng.hphi_jobs import _native_hashes


def cases(order=2):
    yield CoaxialCase(.025,.05,.18,nr=3,nz=4,modes=2,element_order=order)
    yield HphiMeshCase(fixture(False,1,shear=0.)[0]['base_mesh'],modes=2,element_order=order)
    path=AxisAccelerationPath(.01,.16,.8,.02)
    yield AxisHphiCase(fixture(True,1,shear=0.)[0]['base_mesh'],modes=2,element_order=order,acceleration=path)
    for axis in (False,True):
        yield CurvedHphiCase(CurvedMeridionalGeometry(**fixture(axis,1,shear=1.)[0]),modes=2,element_order=order,acceleration=path if axis else None)


def commands(data):
    if isinstance(data,dict):
        for key,value in data.items():
            if key in ('commands','operations'):yield from value
            elif isinstance(value,(dict,list)):yield from commands(value)
    elif isinstance(data,list):
        for value in data:yield from commands(value)


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();inv=capabilities();operations=[];native={};records=[]
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1')
    def cli(command):
        result=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,command)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
        (out/f'cli-{len(operations):03d}.log').write_text(result.stdout+result.stderr);operations.append(list(map(str,command)));assert result.returncode==0,result.stderr
        return result.stdout
    assert json.loads(cli(['capabilities']))==inv
    advertised=sorted(set(commands(inv)))
    for command in advertised:cli([command,'--help'])
    families={f['case_format']:f for f in inv['hphi_rf']['case_families']}
    for index,case in enumerate(cases()):
        row=families[case.to_dict()['format']];name=f'case-{index}';case_file=out/f'{name}.json';case_file.write_text(json.dumps(case.to_dict())+'\n')
        solution=solve_hphi(case);api=out/f'{name}-api';result=save_hphi_run(case,solution,api)
        assert result['format']==row['result_format'] and result['schema_version'] in row['result_schema_versions']
        native_run=out/f'{name}-cli';assert json.loads(cli([row['commands'][0],case_file,'--out',native_run]))==result
        cli([row['commands'][1],native_run]);assert _native_hashes(api)==_native_hashes(native_run)
        restored=read_hphi_run(native_run);np.testing.assert_array_equal(restored.coefficients,solution.coefficients)
        project_file=out/f'{name}-project.json';HphiProject(case).save(project_file);job=out/f'{name}-job'
        cli(['execute-hphi-project',project_file,'--out',job]);assert _native_hashes(job/'solution')==_native_hashes(native_run)
        if isinstance(case,CurvedHphiCase):points=solution.mapped_points([0],[[.2,.3,.5]])[0].tolist()
        else:points=solution.space.mesh.points[solution.space.mesh.triangles[[0]]].mean(axis=1).tolist()
        point_file=out/f'{name}-points.json';point_file.write_text(json.dumps(points)+'\n');probe=out/f'{name}-probe.json'
        cli([row['commands'][2],native_run,'--points',point_file,'--out',probe])
        value=json.loads(probe.read_text());assert len(value['fields'])==18 and value['native_sha256']==_native_hashes(native_run)
        for key,expected in solution.fields_at(points).items():np.testing.assert_allclose(value['fields'][key],expected,rtol=1e-12,atol=0)
        for directory in (api,native_run,job/'solution'):
            native.update({str((directory/key).relative_to(out)):digest for key,digest in _native_hashes(directory).items()})
        records.append(dict(case_format=row['case_format'],native_manifest=json.loads((native_run/'manifest.json').read_text())['format'],api_cli_project_native_identical=True))
    for path,digest in native.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    report=dict(status='PASS',hphi_cases=len(records),advertised_commands=len(advertised),native_files_unchanged=len(native),
        cli_commands=operations,records=records,capabilities=inv,source_sha256=before,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','capabilities','cli_commands','source_sha256')})


if __name__=='__main__':main()

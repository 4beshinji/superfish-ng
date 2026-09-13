# SPDX-License-Identifier: Apache-2.0
"""Planar nonlinear B-H native/CLI comparison on independently checked Cases."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh
from superfish_ng.nonlinear_magnetic import MagneticNonlinearFailure
from superfish_ng.planar_bh_saved import (save_planar_bh_run,read_planar_bh_run,planar_bh_result,export_planar_bh_probe,
    save_planar_bh_failure,read_planar_bh_failure,_snapshot,_failure_snapshot)
from superfish_ng.model import capabilities


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    reference=args.reference.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic()
    source_report=json.loads((reference/'report.json').read_text());assert source_report['status']=='PASS' and source_report['cases']==96 and source_report['successful_cases']==88 and source_report['expected_failures']==8
    changes={'src/superfish_ng/cli.py','src/superfish_ng/model.py','src/superfish_ng/capability_inventory.py'}
    assert all(before[k]==v for k,v in source_report['source_sha256'].items() if k not in changes)
    originals={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in reference.iterdir() if p.is_file()};native_hashes={};records=[];failure_records=[];commands=[]
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1')
    def cli(command,expected=0):
        result=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,command)],cwd=ROOT,env=env,capture_output=True,text=True)
        (out/f'cli-{len(commands):03d}.log').write_text(result.stdout+result.stderr);commands.append(dict(arguments=list(map(str,command)),returncode=result.returncode));assert result.returncode==expected,result.stderr
        return result.stdout
    inventory=capabilities();assert json.loads(cli(['capabilities']))==inventory;description=inventory['planar_bh']
    for command in description['commands']:cli([command,'--help'])
    assert all(description[k] is False for k in ('project','gui','study'));assert description['cli_exit_codes']==dict(success=0,nonlinear_failure=1,input_or_native_error=2)
    selected=[];failures=[]
    for record in source_report['records']:
        name=record['name'];kind=record['kind']
        if kind=='failure':failures.append(record)
        elif ((kind in ('uniform','layered') and '-s0.5-h1.0-' in name) or (kind=='current' and '-n8-s0.5-' in name)
            or (kind=='linear' and '-s0.5-' in name) or (kind=='zero' and '-offset0.125-' in name)):selected.append(record)
    assert len(selected)==24 and len(failures)==8
    for record in selected:
        name=record['name'];input_path=reference/(name+'.json');case=PlanarBHCase.from_dict(json.loads(input_path.read_text()));s=solve_planar_bh(case);p=case.partition
        api=out/'api-native'/name;result=save_planar_bh_run(case,s,api);restored=read_planar_bh_run(api)
        assert planar_bh_result(restored)==result;np.testing.assert_array_equal(restored.az_relative_to_reference_wb_per_m,s.az_relative_to_reference_wb_per_m)
        assert result['quantities']==record['quantities'] and result['nonlinear_iteration']==record['iteration'];assert result['physics']==case.to_dict()['physics']=='nonlinear_isotropic_magnetostatic'
        binary=out/'cli-native'/name;assert json.loads(cli(['solve-planar-bh',input_path,'--out',binary]))==result
        assert json.loads(cli(['replay-planar-bh',binary]))==result;assert _snapshot(binary)==_snapshot(api)
        assert case.to_dict()['format']==description['case_format'] and result['format']==description['result_format'];assert json.loads((binary/'manifest.json').read_text())['format']==description['native_manifest_format']
        points=p.mesh.points_xy_m[p.mesh.triangles[[0,-1]]].mean(axis=1)
        if len(p.interface_edges):points=np.vstack((points,p.mesh.points_xy_m[p.interface_edges[0,0]]))
        point_file=out/f'{name}.points.json';point_file.write_text(json.dumps(points.tolist())+'\n');expected=s.probe_at(points);probe=export_planar_bh_probe(api,out/f'{name}.api-probe.json',points)
        for key,value in expected.items():assert probe[key]==value
        cli_probe=out/f'{name}.cli-probe.json';cli(['probe-planar-bh',binary,'--points',point_file,'--out',cli_probe]);assert json.loads(cli_probe.read_text())==probe
        assert len(probe['fields'])==5 and 'phasor' not in probe['conventions'] and 'mu_r' not in probe
        b=np.column_stack((probe['fields']['Bx_T'],probe['fields']['By_T']));h=np.column_stack((probe['fields']['Hx_A_per_m'],probe['fields']['Hy_A_per_m']))
        expected_h=np.zeros_like(h)
        for i,cell in enumerate(probe['cell_indices']):
            material=p.materials[p.cell_material_indices[cell]];magnitude=np.linalg.norm(b[i]);assert 0<=magnitude<=material.b_t[-1]
            if magnitude:expected_h[i]=np.interp(magnitude,material.b_t,material.h_a_per_m)*b[i]/magnitude
            assert probe['material_provenance'][i]==material.provenance
        assert np.linalg.norm(h-expected_h)/(1.+np.linalg.norm(h))<1e-11
        for directory in (api,binary):native_hashes.update({str((directory/file).relative_to(out)):hashlib.sha256(data).hexdigest() for file,data in _snapshot(directory).items()})
        records.append(dict(name=name,kind=record['kind'],native_files_identical=True,probe_json_identical=True,iteration_history_identical=True));print('DONE',name,flush=True)
    for record in failures:
        name=record['name'];input_path=reference/(name+'.json');case=PlanarBHCase.from_dict(json.loads(input_path.read_text()))
        try:solve_planar_bh(case)
        except MagneticNonlinearFailure as exc:failure=exc
        else:raise AssertionError('expected independently checked nonlinear failure')
        assert failure.report==record['failure'];api=out/'api-failure'/name;result=save_planar_bh_failure(case,failure,api)
        assert read_planar_bh_failure(api)==result;binary=out/'cli-failure'/name
        assert json.loads(cli(['solve-planar-bh',input_path,'--out',binary],expected=1))==result
        assert json.loads(cli(['replay-planar-bh',binary],expected=1))==result;assert _failure_snapshot(binary)==_failure_snapshot(api)
        assert json.loads((binary/'manifest.json').read_text())['format']==description['failure_manifest_format']
        for directory in (api,binary):native_hashes.update({str((directory/file).relative_to(out)):hashlib.sha256(data).hexdigest() for file,data in _failure_snapshot(directory).items()})
        failure_records.append(dict(name=name,reason=result['reason'],native_files_identical=True,last_valid_is_null=result['last_valid_relative_coefficients'] is None));print('DONE',name,flush=True)
    binary=out/'cli-native'/records[0]['name'];outside=out/'outside-points.json';outside.write_text('[[100,100]]\n')
    cli(['probe-planar-bh',binary,'--points',outside,'--out',out/'rejected-probe.json'],expected=2);assert not (out/'rejected-probe.json').exists()
    cli(['solve-planar-bh',reference/f'{records[0]["name"]}.json','--out',binary],expected=2)
    cli(['probe-planar-bh',binary,'--points',outside,'--mode','1','--out',out/'rejected-mode.json'],expected=2);assert not (out/'rejected-mode.json').exists()
    boolean=out/'boolean-points.json';boolean.write_text('[[false,0]]\n');cli(['probe-planar-bh',binary,'--points',boolean,'--out',out/'rejected-boolean.json'],expected=2);assert not (out/'rejected-boolean.json').exists()
    failed=out/'cli-failure'/failure_records[0]['name'];cli(['probe-planar-bh',failed,'--points',outside,'--out',out/'rejected-failure-probe.json'],expected=2);assert not (out/'rejected-failure-probe.json').exists()
    cli(['solve-planar-bh',reference/f'{failure_records[0]["name"]}.json','--out',failed],expected=2)
    invalid=out/'invalid-case.json';data=json.loads((reference/f'{records[0]["name"]}.json').read_text());data['element_order']=2;invalid.write_text(json.dumps(data))
    cli(['solve-planar-bh',invalid,'--out',out/'invalid-case-native'],expected=2);assert not (out/'invalid-case-native').exists()
    for path,digest in native_hashes.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    for path,digest in originals.items():assert hashlib.sha256((reference/path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    report=dict(status='PASS',cases=len(records),failure_cases=len(failure_records),native_saves=2*len(records),failure_saves=2*len(failure_records),records=records,failure_records=failure_records,cli_commands=commands,
        native_files_unchanged=len(native_hashes),reference_files_unchanged=len(originals),original_physics='unchanged planar nonlinear solver/fields/integrals and exact successful quantities or failure histories from independent validation',
        api_cli_native='five success or three failure files byte-identical per Case',api_cli_probe='full JSON identical, including original fields, table/provenance metadata and source hashes',source_sha256=before,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','failure_records','cli_commands','source_sha256')})


if __name__=='__main__':main()

# SPDX-License-Identifier: Apache-2.0
"""Off-axis magnetostatic native/CLI replay of analytically validated source problems."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from superfish_ng.off_axis_magnetostatic import OffAxisMagnetostaticCase,solve_off_axis_magnetostatic
from superfish_ng.off_axis_magnetostatic_saved import save_off_axis_magnetostatic_run,read_off_axis_magnetostatic_run,off_axis_magnetostatic_result,export_off_axis_magnetostatic_probe,_snapshot
from superfish_ng.constants import MU0
from superfish_ng.model import capabilities


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    reference=args.reference.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic()
    source_report=json.loads((reference/'report.json').read_text());assert source_report['status']=='PASS' and source_report['cases']==88 and source_report['uniform_cases']==32 and source_report['annular_cases']==24 and source_report['zero_field_cases']==8 and source_report['layered_cases']==24
    changed={'src/superfish_ng/cli.py','src/superfish_ng/model.py','src/superfish_ng/capability_inventory.py'}
    assert all(before[k]==v for k,v in source_report['source_sha256'].items() if k not in changed)
    originals={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in reference.iterdir() if p.is_file()};native_hashes={};records=[];commands=[]
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1')
    def cli(command,expected=0):
        result=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,command)],cwd=ROOT,env=env,capture_output=True,text=True)
        (out/f'cli-{len(commands):03d}.log').write_text(result.stdout+result.stderr)
        commands.append(dict(arguments=list(map(str,command)),returncode=result.returncode));assert result.returncode==expected,result.stderr
        return result.stdout
    inventory=capabilities();assert json.loads(cli(['capabilities']))==inventory;description=inventory['off_axis_magnetostatic']
    for command in description['commands']:cli([command,'--help'])
    assert all(description[k] is False for k in ('project','gui','study'))
    selected=[]
    for record in source_report['records']:
        name=record['name']
        if ((name.startswith('uniform-') and '-s0.5-mu1.0-' in name)
            or (name.startswith('annular-') and ('-p1-n8-' in name or '-p2-n4-' in name))
            or (name.startswith('layered-') and ('-p1-n8-' in name or '-p2-n4-' in name))):selected.append(record)
    assert len(selected)==24
    for record in selected:
        name=record['name'];input_path=reference/(name+'.json');case=OffAxisMagnetostaticCase.from_dict(json.loads(input_path.read_text()));s=solve_off_axis_magnetostatic(case);p=case.partition
        api=out/'api-native'/name;result=save_off_axis_magnetostatic_run(case,s,api);restored=read_off_axis_magnetostatic_run(api)
        assert off_axis_magnetostatic_result(restored)==result;np.testing.assert_array_equal(restored.psi_relative_to_reference_wb,s.psi_relative_to_reference_wb)
        assert result['quantities']==record['quantities'];assert result['physics']==case.to_dict()['physics']=='linear_magnetostatic'
        binary=out/'cli-native'/name;emitted=json.loads(cli(['solve-off-axis-magnetostatic',input_path,'--out',binary]));assert emitted==result
        assert json.loads(cli(['replay-off-axis-magnetostatic',binary]))==result;assert _snapshot(binary)==_snapshot(api)
        assert case.to_dict()['format']==description['case_format'] and result['format']==description['result_format']
        assert json.loads((binary/'manifest.json').read_text())['format']==description['native_manifest_format']
        points=p.mesh.points_rz_m[p.mesh.triangles[[0,-1]]].mean(axis=1)
        if len(p.interface_edges):points=np.vstack((points,p.mesh.points_rz_m[p.interface_edges[0]].mean(axis=0)))
        point_file=out/f'{name}.points.json';point_file.write_text(json.dumps(points.tolist())+'\n')
        expected=s.probe_at(points);probe=export_off_axis_magnetostatic_probe(api,out/f'{name}.api-probe.json',points)
        for key,value in expected.items():assert probe[key]==value
        cli_probe=out/f'{name}.cli-probe.json';cli(['probe-off-axis-magnetostatic',binary,'--points',point_file,'--out',cli_probe]);assert json.loads(cli_probe.read_text())==probe
        assert len(probe['fields'])==6 and 'phasor' not in probe['conventions']
        for coordinate in ('r','z'):
            np.testing.assert_array_equal(probe['fields'][f'H{coordinate}_A_per_m'],((1./MU0)/np.asarray(probe['mu_r']))*np.asarray(probe['fields'][f'B{coordinate}_T']))
        if len(p.interface_edges):assert probe['cell_indices'][2]==int(min(p.interface_cells[0]))
        for directory in (api,binary):native_hashes.update({str((directory/file).relative_to(out)):hashlib.sha256(data).hexdigest() for file,data in _snapshot(directory).items()})
        records.append(dict(name=name,element_order=case.element_order,holes=len(p.mesh.holes_rz_m),polygon_vertices=len(p.mesh.outer_rz_m),native_files_identical=True,probe_json_identical=True));print('DONE',name,flush=True)
    binary=out/'cli-native'/records[0]['name'];outside=out/'outside-points.json';outside.write_text('[[100,100]]\n')
    cli(['probe-off-axis-magnetostatic',binary,'--points',outside,'--out',out/'rejected-probe.json'],expected=2);assert not (out/'rejected-probe.json').exists()
    cli(['solve-off-axis-magnetostatic',reference/f'{records[0]["name"]}.json','--out',binary],expected=2)
    cli(['probe-off-axis-magnetostatic',binary,'--points',outside,'--mode','1','--out',out/'rejected-mode.json'],expected=2);assert not (out/'rejected-mode.json').exists()
    boolean=out/'boolean-points.json';boolean.write_text('[[false,0]]\n')
    cli(['probe-off-axis-magnetostatic',binary,'--points',boolean,'--out',out/'rejected-boolean.json'],expected=2);assert not (out/'rejected-boolean.json').exists()
    for path,digest in native_hashes.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    for path,digest in originals.items():assert hashlib.sha256((reference/path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    report=dict(status='PASS',cases=len(records),native_saves=2*len(records),records=records,cli_commands=commands,
        native_files_unchanged=len(native_hashes),reference_files_unchanged=len(originals),
        original_physics='unchanged off-axis magnetostatic solver/field/integral source and exact quantities from independent analytical validation',
        api_cli_native='five files byte-identical per case',api_cli_probe='full JSON identical, including one-sided psi/Aphi/B/H and explicit reference, material metadata and source hashes',
        source_sha256=before,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','cli_commands','source_sha256')})


if __name__=='__main__':main()

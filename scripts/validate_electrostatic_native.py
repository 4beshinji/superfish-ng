# SPDX-License-Identifier: Apache-2.0
"""Electrostatic native/CLI replay of analytically validated source problems."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from superfish_ng.electrostatic import AxisymmetricElectrostaticCase,solve_axisymmetric_electrostatic
from superfish_ng.electrostatic_saved import save_electrostatic_run,read_electrostatic_run,electrostatic_result,export_electrostatic_probe,_snapshot
from superfish_ng.constants import EPS0
from superfish_ng.model import capabilities


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    reference=args.reference.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic()
    source_report=json.loads((reference/'report.json').read_text());assert source_report['status']=='PASS' and source_report['cases']==104 and source_report['layered_cases']==32 and source_report['manufactured_cases']==48 and source_report['coaxial_cases']==24
    changed={'src/superfish_ng/cli.py','src/superfish_ng/model.py','src/superfish_ng/capability_inventory.py'}
    assert all(before[k]==v for k,v in source_report['source_sha256'].items() if k not in changed)
    originals={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in reference.iterdir() if p.is_file()};native_hashes={};records=[];commands=[]
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1')
    def cli(command,expected=0):
        result=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,command)],cwd=ROOT,env=env,capture_output=True,text=True)
        (out/f'cli-{len(commands):03d}.log').write_text(result.stdout+result.stderr)
        commands.append(dict(arguments=list(map(str,command)),returncode=result.returncode));assert result.returncode==expected,result.stderr
        return result.stdout
    inventory=capabilities();assert json.loads(cli(['capabilities']))==inventory;description=inventory['axisymmetric_electrostatic']
    for command in description['commands']:cli([command,'--help'])
    assert all(description[k] is False for k in ('project','gui','study'))
    selected=[]
    for record in source_report['records']:
        name=record['name']
        if ((name.startswith('layer-') and '-eps1.0-' in name and not name.endswith('-shift'))
            or (name.startswith('manufactured-') and '-s0.5-a100.0' in name)
            or (name.startswith('coax-') and '-eps1.0-n16' in name)):selected.append(record)
    assert len(selected)==24
    for record in selected:
        name=record['name'];input_path=reference/(name+'.json');case=AxisymmetricElectrostaticCase.from_dict(json.loads(input_path.read_text()));s=solve_axisymmetric_electrostatic(case);p=case.partition
        api=out/'api-native'/name;result=save_electrostatic_run(case,s,api);restored=read_electrostatic_run(api)
        assert electrostatic_result(restored)==result;np.testing.assert_array_equal(restored.potential_relative_to_reference_v,s.potential_relative_to_reference_v)
        assert result['quantities']==record['quantities']
        binary=out/'cli-native'/name;emitted=json.loads(cli(['solve-electrostatic',input_path,'--out',binary]));assert emitted==result
        assert json.loads(cli(['replay-electrostatic',binary]))==result;assert _snapshot(binary)==_snapshot(api)
        assert case.to_dict()['format']==description['case_format'] and result['format']==description['result_format']
        assert json.loads((binary/'manifest.json').read_text())['format']==description['native_manifest_format']
        points=p.mesh.points_rz_m[p.mesh.triangles[[0,-1]]].mean(axis=1)
        if len(p.interface_edges):points=np.vstack((points,p.mesh.points_rz_m[p.interface_edges[0]].mean(axis=0)))
        if hasattr(p.mesh,'axis_interval_m'):points=np.vstack((points,[[0.,sum(p.mesh.axis_interval_m)/2]]))
        point_file=out/f'{name}.points.json';point_file.write_text(json.dumps(points.tolist())+'\n')
        expected=s.probe_at(points);probe=export_electrostatic_probe(api,out/f'{name}.api-probe.json',points)
        for key,value in expected.items():assert probe[key]==value
        cli_probe=out/f'{name}.cli-probe.json';cli(['probe-electrostatic',binary,'--points',point_file,'--out',cli_probe]);assert json.loads(cli_probe.read_text())==probe
        assert len(probe['fields'])==5 and 'phasor' not in probe['conventions']
        for coordinate in ('r','z'):
            np.testing.assert_array_equal(probe['fields'][f'D{coordinate}_C_per_m2'],EPS0*np.asarray(probe['epsilon_r'])*np.asarray(probe['fields'][f'E{coordinate}_V_per_m']))
        if len(p.interface_edges):assert probe['cell_indices'][2]==int(min(p.interface_cells[0]))
        for directory in (api,binary):native_hashes.update({str((directory/file).relative_to(out)):hashlib.sha256(data).hexdigest() for file,data in _snapshot(directory).items()})
        records.append(dict(name=name,element_order=case.element_order,holes=len(p.mesh.holes_rz_m),native_files_identical=True,probe_json_identical=True));print('DONE',name,flush=True)
    binary=out/'cli-native'/records[0]['name'];outside=out/'outside-points.json';outside.write_text('[[100,100]]\n')
    cli(['probe-electrostatic',binary,'--points',outside,'--out',out/'rejected-probe.json'],expected=2);assert not (out/'rejected-probe.json').exists()
    cli(['solve-electrostatic',reference/f'{records[0]["name"]}.json','--out',binary],expected=2)
    cli(['probe-electrostatic',binary,'--points',outside,'--mode','1','--out',out/'rejected-mode.json'],expected=2);assert not (out/'rejected-mode.json').exists()
    for path,digest in native_hashes.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    for path,digest in originals.items():assert hashlib.sha256((reference/path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    report=dict(status='PASS',cases=len(records),native_saves=2*len(records),records=records,cli_commands=commands,
        native_files_unchanged=len(native_hashes),reference_files_unchanged=len(originals),
        original_physics='unchanged electrostatic solver/field/integral source and exact quantities from independent analytical validation',
        api_cli_native='five files byte-identical per case',api_cli_probe='full JSON identical, including one-sided Phi/E/D, material metadata and source hashes',
        source_sha256=before,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','cli_commands','source_sha256')})


if __name__=='__main__':main()

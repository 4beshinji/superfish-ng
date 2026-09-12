# SPDX-License-Identifier: Apache-2.0
"""Curved Hphi native/CLI replay against independently validated RF cases."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from superfish_ng.curved_hphi import CurvedHphiCase,solve_curved_hphi
from superfish_ng.curved_hphi_saved import save_curved_hphi_run,read_curved_hphi_run,curved_hphi_result,export_curved_hphi_probe,_snapshot
from superfish_ng.constants import MU0


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    reference=args.reference.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic()
    source_report=json.loads((reference/'report.json').read_text());assert source_report['status']=='PASS' and source_report['fem_cases']==48 and source_report['rf_modes']==144
    assert all(before[k]==v for k,v in source_report['source_sha256'].items() if k!='src/superfish_ng/cli.py')
    originals={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in reference.iterdir() if p.is_file()};native_hashes={};records=[];commands=[]
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1')
    def cli(command,expected=0):
        result=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,command)],cwd=ROOT,env=env,capture_output=True,text=True)
        log=out/f'cli-{len(commands):03d}.log';log.write_text(result.stdout+result.stderr)
        commands.append(dict(arguments=list(map(str,command)),returncode=result.returncode));assert result.returncode==expected,result.stderr
        return result.stdout
    for axis in (False,True):
        for holes in (0,1,2):
            for order in (1,2):
                for scale,shear in ((.5,1.),(2.,-1.)):
                    name=f'axis-{int(axis)}-holes-{holes}-p-{order}-shear-{shear}-scale-{scale}'
                    input_path=reference/f'{name}.case.json';case=CurvedHphiCase.load(input_path);solution=solve_curved_hphi(case)
                    api=out/'api-native'/name;result=save_curved_hphi_run(case,solution,api)
                    assert result['modes']==json.loads((reference/f'{name}.results.json').read_text())
                    restored=read_curved_hphi_run(api);assert curved_hphi_result(restored)==result
                    np.testing.assert_array_equal(restored.coefficients,solution.coefficients)
                    binary=out/'cli-native'/name
                    emitted=json.loads(cli(['solve-curved-hphi',input_path,'--out',binary]));assert emitted==result
                    assert json.loads(cli(['replay-curved-hphi',binary]))==result
                    assert _snapshot(binary)==_snapshot(api)
                    cells=np.array([0,len(case.geometry.cell_nodes)-1]);bary=np.tile([.2,.3,.5],(2,1))
                    points=solution.mapped_points(cells,bary)[0]
                    if axis:points=np.vstack((points,[[0.,sum(case.geometry.base_mesh.axis_interval_m)/2]]))
                    point_file=out/f'{name}.points.json';point_file.write_text(json.dumps(points.tolist())+'\n')
                    api_probe=out/f'{name}.api-probe.json';probe=export_curved_hphi_probe(api,api_probe,points)
                    cli_probe=out/f'{name}.cli-probe.json';cli(['probe-curved-hphi',binary,'--points',point_file,'--out',cli_probe])
                    assert json.loads(cli_probe.read_text())==probe
                    for coordinate in ('r','phi','z'):
                        for phase in ('real','quadrature'):
                            np.testing.assert_array_equal(probe['fields'][f'B{coordinate}_{phase}_T'],MU0*np.asarray(probe['fields'][f'H{coordinate}_{phase}_A_per_m']))
                    if axis:
                        assert probe['fields']['Hphi_real_A_per_m'][-1]==probe['fields']['Er_quadrature_V_per_m'][-1]==0.
                    for directory in (api,binary):native_hashes.update({str((directory/name).relative_to(out)):hashlib.sha256(data).hexdigest() for name,data in _snapshot(directory).items()})
                    records.append(dict(name=name,axis=axis,holes=holes,element_order=order,scale=scale,shear=shear,native_files_identical=True,probe_json_identical=True))
            print('DONE',axis,holes,flush=True)
    binary=out/'cli-native'/records[0]['name'];outside=out/'outside-points.json';outside.write_text('[[100,100]]\n')
    cli(['probe-curved-hphi',binary,'--points',outside,'--out',out/'rejected-probe.json'],expected=2);assert not (out/'rejected-probe.json').exists()
    cli(['solve-curved-hphi',reference/f'{records[0]["name"]}.case.json','--out',binary],expected=2)
    for path,digest in native_hashes.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    for path,digest in originals.items():assert hashlib.sha256((reference/path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    report=dict(status='PASS',cases=len(records),native_saves=2*len(records),records=records,cli_commands=commands,
        native_files_unchanged=len(native_hashes),reference_files_unchanged=len(originals),original_rf='full JSON equals prior independent physical-field RF',
        api_cli_native='five files byte-identical per case',api_cli_probe='full JSON identical including E/H/B conventions and source hashes',
        source_sha256=before,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','cli_commands','source_sha256')})


if __name__=='__main__':main()

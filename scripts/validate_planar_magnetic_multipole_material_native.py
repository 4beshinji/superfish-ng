# SPDX-License-Identifier: Apache-2.0
"""Source-native preservation and API/CLI multipole replay against actual FEM references."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh
from superfish_ng.planar_recoil import PlanarRecoilCase,solve_planar_recoil
from superfish_ng.planar_bh_saved import save_planar_bh_run
from superfish_ng.planar_recoil_saved import save_planar_recoil_run
from superfish_ng.planar_magnetostatic_saved import save_planar_magnetostatic_run,_snapshot
from superfish_ng.planar_magnetic_multipole_saved import export_planar_magnetic_multipoles,replay_planar_magnetic_multipoles


def fingerprints():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--old-native',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);start=time.monotonic();before=fingerprints();reference=args.reference.resolve();source_report=json.loads((reference/'report.json').read_text());assert source_report['status']=='PASS' and source_report['cases']==72
    selected=[row for row in source_report['records'] if '-s0.5-' in row['name'] and (row['kind']=='exterior_material' or row['kind']=='linear_limit' and 'theta0.0-' in row['name'] or row['kind']=='P1_refinement' and '-n32-' not in row['name'])];assert len(selected)==24

    preserved={};reference_files={};records=[];calls=0
    def retain(path):preserved[str(path.relative_to(out))]=hashlib.sha256(path.read_bytes()).hexdigest()
    def cli(name,arguments,code=0):
        nonlocal calls
        calls+=1;environment=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1');completed=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,arguments)],cwd=ROOT,env=environment,capture_output=True,text=True,timeout=180)
        (out/(name+'.stdout')).write_text(completed.stdout);(out/(name+'.stderr')).write_text(completed.stderr);assert completed.returncode==code,(name,completed.returncode,completed.stderr);return json.loads(completed.stdout) if code==0 else None
    for index,row in enumerate(selected):
        name=row['name'];input_path=reference/(name+'.json');expected_path=reference/(name+'.result.json')
        for path in (input_path,expected_path):reference_files[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        original=json.loads(input_path.read_text());case_type=PlanarBHCase if original['case']['physics']=='nonlinear_isotropic_magnetostatic' else PlanarRecoilCase;case=case_type.from_dict(original['case']);request=dict(format='superfish_ng_planar_magnetic_multipole_request',schema_version=1,frame=original['frame'],maximum_order=original['maximum_order'],angular_samples=original['angular_samples']);expected=json.loads(expected_path.read_text());directory=out/name;directory.mkdir();run=directory/'source';solution=solve_planar_bh(case) if type(case) is PlanarBHCase else solve_planar_recoil(case);publish=save_planar_bh_run if type(case) is PlanarBHCase else save_planar_recoil_run;publish(case,solution,run);native=_snapshot(run)
        for path in run.iterdir():retain(path)
        req=directory/'request.json';req.write_text(json.dumps(request,indent=2)+'\n');retain(req)
        first=directory/'api.json';second=directory/'repeat.json';target=directory/'cli.json';result=export_planar_magnetic_multipoles(run,first,request);assert result['extraction']==expected and result['schema_version']==2 and result['source_physics']==case.to_dict()['physics'];assert export_planar_magnetic_multipoles(run,second,request)==result and first.read_bytes()==second.read_bytes();assert replay_planar_magnetic_multipoles(run,first)==result
        actual=cli(f'{index}-extract',['extract-planar-magnetic-multipoles',run,'--request',req,'--out',target]);assert actual==result and first.read_bytes()==target.read_bytes()
        for j,path in enumerate((first,target)):assert cli(f'{index}-replay-{j}',['replay-planar-magnetic-multipoles',run,path])==result
        for path in (first,second,target):retain(path)
        assert _snapshot(run)==native
        records.append(dict(name=name,kind=row['kind'],coefficient_error=row['coefficient_error'],field_error=row['field_error'],native_files=5,reports=3,cli_calls=3,all_four_traces_and_full_json_identical=True));print('DONE',name,flush=True)
    last=out/selected[-1]['name'];cli('overwrite',['extract-planar-magnetic-multipoles',last/'source','--request',last/'request.json','--out',last/'cli.json'],2)
    invalid=out/'invalid-request.json';bad=json.loads((last/'request.json').read_text());bad['maximum_order']=True;invalid.write_text(json.dumps(bad));cli('invalid',['extract-planar-magnetic-multipoles',last/'source','--request',invalid,'--out',out/'invalid-output.json'],2);assert not (out/'invalid-output.json').exists()
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    for name,digest in reference_files.items():assert hashlib.sha256((reference/name).read_bytes()).hexdigest()==digest
    old_native=args.old_native.resolve();old_report=json.loads((old_native/'report.json').read_text());assert old_report['status']=='PASS' and old_report['cases']==24;old_files={}
    for index,row in enumerate(old_report['records']):
        directory=old_native/row['name'];run=directory/'source'
        for path in run.iterdir():old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        for name in ('api.json','repeat.json','cli.json'):
            path=directory/name;old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();expected=json.loads(path.read_text());actual=replay_planar_magnetic_multipoles(run,path);assert actual==expected and actual['schema_version']==1
        assert cli(f'old-{index}-replay',['replay-planar-magnetic-multipoles',run,directory/'cli.json'])==expected
    for name,digest in old_files.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    assert fingerprints()==before and calls==98 and len(old_files)==192
    report=dict(status='PASS',cases=24,exact_cases=16,p1_cases=8,native_files_unchanged=120,report_files=72,request_files=24,preserved_files=len(preserved),reference_files_unchanged=len(reference_files),cli_calls=calls,old_scalar_reports_identical=72,old_scalar_cli_replays=24,old_files_unchanged=len(old_files),records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='Same original FEM and all four Fourier traces as independent analytic/refinement reference; API/CLI exact JSON and bytes, unchanged source natives, and explicit replay. B-H/recoil source and linear nonremanent aperture explicit. Old scalar report/CLI version 1 unchanged. No continuum accuracy certification, GUI or force/torque.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()

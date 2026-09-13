# SPDX-License-Identifier: Apache-2.0
"""Exact source/native/API/CLI force and optional displaced-FEM report comparisons."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic
from superfish_ng.planar_magnetostatic_saved import save_planar_magnetostatic_run,_snapshot
from superfish_ng.planar_magnetic_force_saved import export_planar_magnetic_force,replay_planar_magnetic_force


def fingerprints():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);reference=args.reference.resolve();source_report=json.loads((reference/'report.json').read_text());assert source_report['status']=='PASS' and source_report['cases']==56;start=time.monotonic();before=fingerprints();preserved={};reference_files={};records=[];calls=0
    selected=[row for row in source_report['records'] if row['kind']=='analytic_symmetry' and '-theta0.0-s0.5-I10.0' in row['name'] or row['kind']=='linear_material_body' and '-mu3.0' in row['name']];assert len(selected)==8
    def retain(path):preserved[str(path.relative_to(out))]=hashlib.sha256(path.read_bytes()).hexdigest()
    def cli(name,args,code=0):
        nonlocal calls
        calls+=1;environment=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1');p=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,args)],cwd=ROOT,env=environment,capture_output=True,text=True,timeout=300);(out/(name+'.stdout')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr);assert p.returncode==code,(name,p.returncode,p.stderr);return json.loads(p.stdout) if code==0 else None
    for index,row in enumerate(selected):
        name=row['name'];paths=[reference/(name+suffix) for suffix in ('.json','.stress.json','.work.json')]
        for path in paths:reference_files[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        original=json.loads(paths[0].read_text());expected_force=json.loads(paths[1].read_text());expected_work=json.loads(paths[2].read_text());virtual=index in (0,3,5,6);steps=dict(translation_steps_m=[r['step'] for r in expected_work['records'] if r['kind']=='x'],rotation_steps_rad=[r['step'] for r in expected_work['records'] if r['kind']=='rotation']) if virtual else None
        request=dict(format='superfish_ng_planar_magnetic_force_request',schema_version=1,body_region_ids=original['body_region_ids'],weights=original['weights'],origin_xy_m=original['origin_xy_m'],virtual_work=steps);directory=out/name;directory.mkdir();case=PlanarMagnetostaticCase.from_dict(original['case']);run=directory/'source';solution=solve_planar_magnetostatic(case);save_planar_magnetostatic_run(case,solution,run);native=_snapshot(run)
        for path in run.iterdir():retain(path)
        req=directory/'request.json';req.write_text(json.dumps(request,indent=2)+'\n');retain(req);first=directory/'api.json';second=directory/'repeat.json';target=directory/'cli.json';report=export_planar_magnetic_force(run,first,request);assert report['force']==expected_force and report['virtual_work']==(expected_work if virtual else None);assert export_planar_magnetic_force(run,second,request)==report and second.read_bytes()==first.read_bytes();assert replay_planar_magnetic_force(run,first)==report
        actual=cli(f'{index}-analyze',['analyze-planar-magnetic-force',run,'--request',req,'--out',target]);assert actual==report and target.read_bytes()==first.read_bytes()
        for j,path in enumerate((first,target)):assert cli(f'{index}-replay-{j}',['replay-planar-magnetic-force',run,path])==report
        for path in (first,second,target):retain(path)
        assert _snapshot(run)==native;records.append(dict(name=name,kind=row['kind'],order=row['order'],pair=row['pair'],virtual_work=virtual,full_stress_and_requested_work_json_identical=True,native_files=5,reports=3,cli_calls=3));print('DONE',name,'virtual',virtual,flush=True)
    last=out/selected[-1]['name'];cli('overwrite',['analyze-planar-magnetic-force',last/'source','--request',last/'request.json','--out',last/'cli.json'],2);invalid=out/'invalid-request.json';bad=json.loads((last/'request.json').read_text());bad['weights'][0]=False;invalid.write_text(json.dumps(bad));cli('invalid',['analyze-planar-magnetic-force',last/'source','--request',invalid,'--out',out/'invalid-output.json'],2);assert not (out/'invalid-output.json').exists()
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    for name,digest in reference_files.items():assert hashlib.sha256((reference/name).read_bytes()).hexdigest()==digest
    assert fingerprints()==before and calls==26 and len(preserved)==72 and len(reference_files)==24
    report=dict(status='PASS',cases=8,virtual_work_cases=4,stress_only_cases=4,native_files_unchanged=40,report_files=24,request_files=8,preserved_files=len(preserved),reference_files_unchanged=len(reference_files),cli_calls=calls,records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='P1/P2 single/coupled currents and scalar-magnetic bodies, identical original stress and requested actual-FEM work references, exact API/CLI JSON and bytes, unchanged source native. Null explicitly omits work; no continuum accuracy certification, BH/recoil/axisymmetric force or GUI.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()

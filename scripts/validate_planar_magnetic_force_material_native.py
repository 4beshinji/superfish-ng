# SPDX-License-Identifier: Apache-2.0
"""Material force/native/CLI equivalence, retained actual failures, and scalar report compatibility."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from superfish_ng.constants import MU0
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh
from superfish_ng.planar_recoil import PlanarRecoilCase,solve_planar_recoil
from superfish_ng.planar_bh_saved import save_planar_bh_run
from superfish_ng.planar_recoil_saved import save_planar_recoil_run
from superfish_ng.planar_magnetostatic_saved import _snapshot
from superfish_ng.planar_magnetic_force import planar_magnetic_force
from superfish_ng.planar_magnetic_force_saved import export_planar_magnetic_force,replay_planar_magnetic_force


def fingerprints():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('out','reference','old-native'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);reference=args.reference.resolve();old=args.old_native.resolve();parent=json.loads((reference/'report.json').read_text());assert parent['status']=='PASS' and parent['cases']==50 and parent['failed_cases']==12;start=time.monotonic();before=fingerprints();records=[];preserved={};reference_files={};calls=0
    def retain(path):preserved[str(path.relative_to(out))]=hashlib.sha256(path.read_bytes()).hexdigest()
    def cli(label,arguments,code):
        nonlocal calls
        calls+=1;p=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,arguments)],cwd=ROOT,env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1'),capture_output=True,text=True,timeout=300);(out/(label+'.stdout')).write_text(p.stdout);(out/(label+'.stderr')).write_text(p.stderr);assert p.returncode==code,(label,p.returncode,p.stderr);return json.loads(p.stdout) if code in (0,1) else None
    selected=[row for row in parent['records'] if row['kind']=='linear_limit' and row['name'].startswith('bh-') and '-theta0.0-' in row['name'] or row['kind']=='magnetic_moment' and '-theta0.0-' in row['name'] or row['kind']=='material_stress_work' and '-theta0.3-' in row['name'] and (row['name'].startswith('bh-') or '-sign1.0' in row['name'])];assert len(selected)==12
    scenarios=[]
    for index,row in enumerate(selected):
        name=row['name'];paths=[reference/(name+suffix) for suffix in ('.json','.stress.json','.work.json')]
        for path in paths:reference_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        request=json.loads(paths[0].read_text());stress=json.loads(paths[1].read_text());work=json.loads(paths[2].read_text());virtual=index in (0,3,4,7,8,11);case=(PlanarBHCase if request['case']['format']=='superfish_ng_planar_bh_case' else PlanarRecoilCase).from_dict(request['case']);steps=dict(translation_steps_m=work['translation_steps_m'],rotation_steps_rad=work['rotation_steps_rad']) if virtual else None
        scenarios.append(dict(name=name,case=case,request=dict(format='superfish_ng_planar_magnetic_force_request',schema_version=1,body_region_ids=request['body_region_ids'],weights=request['weights'],origin_xy_m=request['origin_xy_m'],virtual_work=steps),expected_force=stress,expected_work=work if virtual else None,code=0,kind=row['kind']))
    for row in parent['failures']:
        if row['mode']=='baseline':continue
        path=reference/(row['name']+'.json');reference_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();work=json.loads(path.read_text());case=PlanarBHCase.from_dict(work['source_case']);solution=solve_planar_bh(case);stress=planar_magnetic_force(solution,work['body_region_ids'],work['weights'],work['origin_xy_m']);length=np.ptp(case.partition.mesh.points_xy_m,axis=0).max();scale=.25**2*length/MU0;assert np.linalg.norm(stress['force_xy_n_per_m'])/scale<1e-9 and abs(stress['torque_z_nm_per_m'])/(scale*length)<1e-9
        request=dict(format='superfish_ng_planar_magnetic_force_request',schema_version=1,body_region_ids=work['body_region_ids'],weights=work['weights'],origin_xy_m=work['origin_xy_m'],virtual_work=dict(translation_steps_m=work['translation_steps_m'],rotation_steps_rad=work['rotation_steps_rad']));scenarios.append(dict(name=row['name'],case=case,request=request,expected_force=stress,expected_work=work,code=1,kind=row['mode']))
    assert len(scenarios)==20
    for index,scenario in enumerate(scenarios):
        name=scenario['name'];directory=out/name;directory.mkdir();case=scenario['case'];source=directory/'source';solution=(solve_planar_bh if type(case) is PlanarBHCase else solve_planar_recoil)(case);(save_planar_bh_run if type(case) is PlanarBHCase else save_planar_recoil_run)(case,solution,source);native=_snapshot(source)
        for path in source.iterdir():retain(path)
        request=scenario['request'];req=directory/'request.json';req.write_text(json.dumps(request,indent=2)+'\n');retain(req);api=directory/'api.json';repeat=directory/'repeat.json';target=directory/'cli.json';result=export_planar_magnetic_force(source,api,request);assert result['schema_version']==2 and result['source_physics']==case.to_dict()['physics'];assert result['force']==scenario['expected_force'] and result['virtual_work']==scenario['expected_work'];assert result['status']==('virtual_work_failed' if scenario['code']==1 else 'complete');assert export_planar_magnetic_force(source,repeat,request)==result and repeat.read_bytes()==api.read_bytes();assert replay_planar_magnetic_force(source,api)==result
        actual=cli(f'{index}-analyze',['analyze-planar-magnetic-force',source,'--request',req,'--out',target],scenario['code']);assert actual==result and target.read_bytes()==api.read_bytes()
        for j,path in enumerate((api,target)):assert cli(f'{index}-replay-{j}',['replay-planar-magnetic-force',source,path],scenario['code'])==result
        if scenario['code']==1:
            assert result['stress_virtual_work_comparison'][-1]['difference'] is None and result['stress_virtual_work_comparison'][-1]['virtual_work_value'] is None
            if scenario['kind']=='later_rotation':assert all(r['difference'] is not None for r in result['stress_virtual_work_comparison'][:-1])
        for path in (api,repeat,target):retain(path)
        assert _snapshot(source)==native;records.append(dict(name=name,kind=scenario['kind'],source_physics=case.to_dict()['physics'],order=case.element_order,virtual_work=request['virtual_work'] is not None,status=result['status'],exit_code=scenario['code'],native_files=5,reports=3));print('DONE',name,result['status'],flush=True)
    last=out/scenarios[-1]['name'];cli('overwrite',['analyze-planar-magnetic-force',last/'source','--request',last/'request.json','--out',last/'cli.json'],2);invalid=out/'invalid-request.json';request=json.loads((last/'request.json').read_text());request['weights'][0]=False;invalid.write_text(json.dumps(request));cli('invalid',['analyze-planar-magnetic-force',last/'source','--request',invalid,'--out',out/'invalid-output.json'],2);assert not (out/'invalid-output.json').exists()
    old_files={};old_report=json.loads((old/'report.json').read_text());assert old_report['status']=='PASS' and old_report['cases']==8
    for index,row in enumerate(old_report['records']):
        directory=old/row['name'];source=directory/'source'
        for path in source.iterdir():old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        request=directory/'request.json';old_files[str(request)]=hashlib.sha256(request.read_bytes()).hexdigest()
        for name in ('api.json','repeat.json','cli.json'):
            path=directory/name;old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();result=replay_planar_magnetic_force(source,path);assert result==json.loads(path.read_text()) and result['schema_version']==1
        assert cli(f'old-{index}-replay',['replay-planar-magnetic-force',source,directory/'cli.json'],0)==result;print('UNCHANGED scalar',row['name'],flush=True)
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    for collection in (reference_files,old_files):
        for name,digest in collection.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    assert fingerprints()==before and calls==70 and len(preserved)==180 and len(reference_files)==44 and len(old_files)==72
    report=dict(status='PASS',cases=20,complete_cases=12,complete_work_cases=6,stress_only_cases=6,retained_failure_cases=8,native_files_unchanged=100,report_files=60,request_files=20,preserved_files=len(preserved),reference_files_unchanged=len(reference_files),old_scalar_reports_identical=24,old_scalar_native_files_unchanged=40,old_files_unchanged=len(old_files),cli_calls=calls,records=records,source_sha256=before,seconds=time.monotonic()-start,interpretation='Original B-H/recoil source, complete or null work and actual displaced Newton failure, full API/CLI JSON/bytes and exact repeat failure; unchanged scalar version-1 reports and exit codes. Workflow completion/failure is separate from continuum force accuracy; no GUI or axisymmetric force acceptance.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()

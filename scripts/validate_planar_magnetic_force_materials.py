# SPDX-License-Identifier: Apache-2.0
"""Independent Lorentz/moment and material symmetry checks, retaining prior force reports."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.planar_magnetic_force_material_reference import material_body
from superfish_ng.constants import MU0
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh
from superfish_ng.planar_recoil import solve_planar_recoil
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic
from superfish_ng.planar_magnetic_force import planar_magnetic_force as force,planar_magnetic_virtual_work as work
from superfish_ng.planar_magnetic_force_saved import replay_planar_magnetic_force


def fingerprints():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--old-force',type=Path,required=True);parser.add_argument('--old-native',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);start=time.monotonic();before=fingerprints();records=[];preserved={};families=[];max_exact=max_origin=max_symmetry=0.
    def save(name,value):
        path=out/name;path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');preserved[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    def run(name,kind,case,body,w,origin,ref,order,pair=False,permanent=False,material=False):
        nonlocal max_exact,max_origin,max_symmetry
        original=case.to_dict();save(name+'.json',dict(case=original,body_region_ids=list(body),weights=w.tolist(),origin_xy_m=origin.tolist()));solution=(solve_planar_bh if type(case) is PlanarBHCase else solve_planar_recoil)(case);result=force(solution,body,w,origin);save(name+'.stress.json',result);assert result['schema_version']==2 and result['source_physics']==original['physics'];actual=np.asarray(result['force_xy_n_per_m'])
        weighted=nodal=None
        if material:
            scale=.25**2*ref['length_m']/MU0;error=float(np.linalg.norm(actual)/scale);assert error<1e-9,(name,error);max_symmetry=max(max_symmetry,error)
            if kind=='bh':
                error=abs(result['torque_z_nm_per_m'])/(scale*ref['length_m']);assert error<1e-9;max_symmetry=max(max_symmetry,error)
            torque_scale=scale*ref['length_m']
        else:
            error=float(np.linalg.norm(actual-ref['force_xy_n_per_m'])/ref['force_scale']);weighted=abs(result['torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale'];nodal=abs(result['nodal_rotation_stress_torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale'];assert max(error,nodal)<1e-9,(name,error,nodal);max_exact=max(max_exact,error,nodal);torque_scale=ref['torque_scale']
            if order==2 or not (permanent or pair):assert weighted<1e-9,(name,weighted);max_exact=max(max_exact,weighted)
        assert max(result['quadrature_relative_differences'])<1e-12
        shift=np.array([.13,-.17])*ref['length_m'];shifted=force(solution,body,w,origin+shift);correction=shift[0]*actual[1]-shift[1]*actual[0];origin_error=max(abs(shifted[k]-result[k]+correction)/torque_scale for k in ('torque_z_nm_per_m','nodal_rotation_stress_torque_z_nm_per_m'));assert origin_error<1e-9,(name,origin_error);max_origin=max(max_origin,origin_error);save(name+'.shifted-origin.json',shifted);assert case.to_dict()==original
        row=dict(name=name,kind=kind,order=order,pair=pair,permanent=permanent,material_symmetry_only=material,force_or_symmetry_error=error,weighted_torque_error=weighted,nodal_torque_error=nodal,origin_error=origin_error,weighted_torque_nm_per_m=result['torque_z_nm_per_m'],nodal_torque_nm_per_m=result['nodal_rotation_stress_torque_z_nm_per_m']);records.append(row);print('DONE',name,flush=True);return row
    for kind,order in (('bh',1),('recoil',1),('recoil',2)):
        for pair in (False,True):
            for angle in (0.,.3):
                for sign,scale in ((1.,.5),(-1.,2.)):
                    case,body,w,c,ref=material_body(kind,order=order,pair=pair,rotation_rad=angle,scale=scale,current_a=10*sign);run(f'{kind}-linear-P{order}-pair{pair}-theta{angle}-s{scale}-sign{sign}',kind,case,body,w,c,ref,order,pair=pair)
    for order in (1,2):
        for angle in (0.,.3):
            for sign,scale in ((1.,.5),(-1.,2.)):
                rows=[]
                for n in (8,16,32):
                    case,body,w,c,ref=material_body('recoil',permanent=True,order=order,n=n,rotation_rad=angle,scale=scale,remanence_t=.1*sign);row=run(f'recoil-moment-P{order}-n{n}-theta{angle}-s{scale}-sign{sign}','recoil',case,body,w,c,ref,order,permanent=True);rows.append(row)
                    if order==1 and len(rows)>1:assert row['weighted_torque_error']<rows[-2]['weighted_torque_error']
                assert rows[-1]['weighted_torque_error']<(.02 if order==1 else 1e-9);families.append(dict(order=order,angle=angle,scale=scale,sign=sign,rows=rows,criterion='strict P1 improvement and finest .02' if order==1 else 'P2 exact moment invariant 1e-9 on every mesh'))
    for kind in ('bh','recoil'):
        for angle in (0.,.3):
            for scale in (.5,2.):
                order=1 if kind=='bh' else 2;case,body,w,c,ref=material_body(kind,nonlinear=True,principal=(2.,5.),permanent=kind=='recoil',current_a=0.,order=order,rotation_rad=angle,scale=scale);run(f'{kind}-material-symmetry-theta{angle}-s{scale}',kind,case,body,w,c,ref,order,material=True)
    for order in (1,2):
        for outer in (.875,.95,1.):
            case,body,w,c,ref=material_body('recoil',permanent=True,order=order,weight_outer=outer);run(f'recoil-weight-P{order}-outer{outer}','recoil',case,body,w,c,ref,order,permanent=True)
    old_force=args.old_force.resolve();old_native=args.old_native.resolve();old_files={};old_report=json.loads((old_force/'report.json').read_text());assert old_report['status']=='PASS' and old_report['cases']==56;old_work=0
    for path in old_force.iterdir():
        if path.name!='report.json' and path.suffix=='.json':old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    for row in old_report['records']:
        name=row['name'];request=json.loads((old_force/(name+'.json')).read_text());case=PlanarMagnetostaticCase.from_dict(request['case']);solution=solve_planar_magnetostatic(case);body=request['body_region_ids'];w=request['weights'];origin=request['origin_xy_m'];result=force(solution,body,w,origin);assert result==json.loads((old_force/(name+'.stress.json')).read_text()) and result['schema_version']==1
        if row['work_error'] is not None:
            expected=json.loads((old_force/(name+'.work.json')).read_text());translation=[r['step'] for r in expected['records'] if r['kind']=='x'];rotation=[r['step'] for r in expected['records'] if r['kind']=='rotation'];assert work(case,body,w,origin,translation,rotation)==expected;old_work+=1
        print('UNCHANGED scalar',name,flush=True)
    native_report=json.loads((old_native/'report.json').read_text());assert native_report['status']=='PASS' and native_report['cases']==8
    for row in native_report['records']:
        directory=old_native/row['name'];source=directory/'source'
        for path in source.iterdir():old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        for name in ('api.json','repeat.json','cli.json'):
            path=directory/name;old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();assert replay_planar_magnetic_force(source,path)==json.loads(path.read_text())
        print('UNCHANGED native',row['name'],flush=True)
    for name,digest in old_files.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    assert fingerprints()==before and len(records)==62 and len(families)==8 and old_work==40 and len(preserved)==186 and len(old_files)==275
    report=dict(status='PASS',cases=len(records),linear_limit_cases=24,permanent_mesh_cases=24,material_symmetry_cases=8,weight_cases=6,mesh_families=families,max_exact_error=max_exact,max_origin_error=max_origin,max_material_symmetry_error=max_symmetry,old_scalar_force_identical=56,old_scalar_work_identical=40,old_scalar_native_reports_identical=24,old_files_unchanged=len(old_files),preserved_files=len(preserved),records=records,source_sha256=before,seconds=time.monotonic()-start,interpretation='Actual B-H/recoil FEM; all weight gradients in declared vacuum. Independent Lorentz/moment invariants and nonlinear/anisotropic body symmetries; weighted and nodal torques remain distinct. Scalar force, work and native unchanged; no material virtual-work or continuum error bound.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256','mesh_families')})


if __name__=='__main__':main()

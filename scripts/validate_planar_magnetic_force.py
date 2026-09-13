# SPDX-License-Identifier: Apache-2.0
"""Independent Lorentz symmetries and actual displaced-FEM work for magnetic forces."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.planar_magnetic_force_reference import current_body
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic
from superfish_ng.planar_magnetic_force import planar_magnetic_force,planar_magnetic_virtual_work


def fingerprints():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);start=time.monotonic();before=fingerprints();records=[];preserved={};families=[];maximum_exact=maximum_work=maximum_origin=0.;work_cases=0;work_solves=0;baselines={}
    def save(name,value):
        path=out/name;path.write_text(json.dumps(value,indent=2)+'\n');preserved[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    def run(name,case,body,w,origin,ref,pair,order,kind,virtual):
        nonlocal maximum_exact,maximum_work,maximum_origin,work_cases,work_solves
        original=case.to_dict();save(name+'.json',dict(case=original,body_region_ids=list(body),weights=w.tolist(),origin_xy_m=origin.tolist()));solution=solve_planar_magnetostatic(case);result=planar_magnetic_force(solution,body,w,origin);save(name+'.stress.json',result)
        actual=np.asarray(result['force_xy_n_per_m']);force_error=float(np.linalg.norm(actual-ref['force_xy_n_per_m'])/ref['force_scale']);weighted_error=abs(result['torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale'];nodal_error=abs(result['nodal_rotation_stress_torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale']
        if kind!='linear_material_body':
            assert force_error<1e-9 and nodal_error<1e-9,(name,force_error,nodal_error);maximum_exact=max(maximum_exact,force_error,nodal_error)
            if order==2 or not pair:assert weighted_error<1e-9,(name,weighted_error);maximum_exact=max(maximum_exact,weighted_error)
        assert max(result['quadrature_relative_differences'])<1e-12
        shift=np.array([.13,-.17])*ref['length_m'];shifted=planar_magnetic_force(solution,body,w,origin+shift);correction=shift[0]*actual[1]-shift[1]*actual[0]
        origin_error=max(abs(shifted[key]-result[key]+correction)/ref['torque_scale'] for key in ('torque_z_nm_per_m','nodal_rotation_stress_torque_z_nm_per_m'));assert origin_error<1e-9,(name,origin_error);maximum_origin=max(maximum_origin,origin_error);save(name+'.shifted-origin.json',shifted)
        work_error=None
        if virtual:
            length=ref['length_m'];work=planar_magnetic_virtual_work(case,body,w,origin,[1e-4*length,5e-5*length],[1e-3,5e-4]);save(name+'.work.json',work);work_cases+=1;work_solves+=sum(len(row['trials']) for row in work['records']);work_error=0.;targets=dict(x=actual[0],y=actual[1],rotation=result['nodal_rotation_stress_torque_z_nm_per_m'])
            for row in work['records']:
                scale=ref['torque_scale'] if row['kind']=='rotation' else ref['force_scale'];error=abs(row['negative_potential_derivative']-targets[row['kind']])/scale;assert error<1e-5,(name,row['kind'],row['step'],error);work_error=max(work_error,error)
                for trial in row['trials']:
                    changed=PlanarMagnetostaticCase.from_dict(trial['case']);assert changed.boundaries==case.boundaries
                    for i,region in enumerate(case.partition.regions):
                        old=case.current_density_z_a_per_m2[region.id]*case.partition.region_area_m2[i];new=changed.current_density_z_a_per_m2[region.id]*changed.partition.region_area_m2[i];assert abs(new-old)<=1e-12*max(1.,abs(old))
            maximum_work=max(maximum_work,work_error)
        assert case.to_dict()==original
        row=dict(name=name,kind=kind,order=order,pair=pair,force_error=force_error,weighted_torque_error=weighted_error,nodal_torque_error=nodal_error,origin_error=origin_error,work_error=work_error,weighted_minus_nodal_torque_nm_per_m=-result['nodal_minus_weighted_torque_nm_per_m']);records.append(row);print('DONE',name,flush=True);return row
    for pair in (False,True):
        for order in (1,2):
            for angle in (0.,.3):
                for scale in (.5,2.):
                    for current in (10.,-10.):
                        case,body,w,origin,ref=current_body(pair=pair,order=order,rotation_rad=angle,scale=scale,current_a=current,offset=.125 if current<0 else 0.);name=f'symmetric-pair{pair}-P{order}-theta{angle}-s{scale}-I{current}';row=run(name,case,body,w,origin,ref,pair,order,'analytic_symmetry',True)
                        if pair and order==1:baselines[angle,scale,current]=row
    for angle in (0.,.3):
        for scale in (.5,2.):
            for current in (10.,-10.):
                rows=[baselines[angle,scale,current]]
                for n in (16,32):
                    case,body,w,origin,ref=current_body(n=n,pair=True,order=1,rotation_rad=angle,scale=scale,current_a=current,offset=.125 if current<0 else 0.);name=f'refinement-n{n}-theta{angle}-s{scale}-I{current}';row=run(name,case,body,w,origin,ref,True,1,'P1_refinement',False);assert row['weighted_torque_error']<rows[-1]['weighted_torque_error'];rows.append(row)
                assert rows[-1]['weighted_torque_error']<.02;families.append(dict(angle=angle,scale=scale,current_a=current,rows=rows,weighted_torque_limit=.02))
    for pair in (False,True):
        for order in (1,2):
            for permeability in (3.,7.):
                case,body,w,origin,ref=current_body(pair=pair,order=order,current_a=1000.);data=case.to_dict();data['partition']['materials'].append(dict(id='body-linear',type='linear_isotropic_magnetic_material',mu_r=permeability))
                for region in data['partition']['regions']:
                    if region['id'] in body:region['material']='body-linear'
                case=PlanarMagnetostaticCase.from_dict(data);run(f'material-pair{pair}-P{order}-mu{permeability}',case,body,w,origin,ref,pair,order,'linear_material_body',True)
    weights=[]
    for outer in (.875,.95,1.):
        case,body,w,origin,ref=current_body(order=2,pair=True,weight_outer=outer);solution=solve_planar_magnetostatic(case);result=planar_magnetic_force(solution,body,w,origin);save(f'weight-{outer}.json',dict(case=case.to_dict(),result=result));assert abs(result['torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale']<1e-9;weights.append(dict(outer=outer,force_xy_n_per_m=result['force_xy_n_per_m'],weighted_torque_z_nm_per_m=result['torque_z_nm_per_m'],nodal_torque_z_nm_per_m=result['nodal_rotation_stress_torque_z_nm_per_m']))
    assert len(records)==56 and len(families)==8 and work_cases==40 and work_solves==480 and fingerprints()==before
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',cases=56,analytic_symmetry_cases=32,p1_refinement_cases=16,linear_material_cases=8,work_cases=work_cases,displaced_fem_solves=work_solves,mesh_families=families,weight_study=weights,max_exact_error=maximum_exact,max_nodal_stress_vs_work_error=maximum_work,max_torque_origin_error=maximum_origin,preserved_files=len(preserved),records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='Original FEM Maxwell force and two explicitly distinct stress torques; independent analytic Lorentz symmetries, P1 mesh convergence, unchanged-boundary/fixed-current actual displaced FEM stationary potentials. No continuum error bound, smoothing, fitted force correction, legacy execution, BH/recoil or axisymmetric force extension.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256','mesh_families','weight_study')})


if __name__=='__main__':main()

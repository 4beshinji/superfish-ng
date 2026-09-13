# SPDX-License-Identifier: Apache-2.0
"""Actual material virtual work against Lorentz/moment, stress, reference energies and failures."""
import argparse,hashlib,json,sys,time
from dataclasses import replace
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.planar_magnetic_force_material_reference import material_body
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh
from superfish_ng.planar_recoil import PlanarRecoilCase,solve_planar_recoil
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic
from superfish_ng.nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure
from superfish_ng.planar_magnetic_force import planar_magnetic_force as force,planar_magnetic_virtual_work as scalar_work
from superfish_ng.planar_magnetic_force_saved import replay_planar_magnetic_force
from superfish_ng.planar_magnetic_material_virtual_work import material_planar_magnetic_virtual_work as work,PlanarMagneticVirtualWorkFailure


def fingerprints():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def solve(case):return (solve_planar_bh if type(case) is PlanarBHCase else solve_planar_recoil)(case)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('out','old-force','old-native','material-force'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);start=time.monotonic();before=fingerprints();records=[];preserved={};failures=[];max_work=max_analytic=max_reference=max_current=max_volume=max_origin=0.;shift_cases=0
    def save(name,value):
        path=out/name;path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');preserved[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    def run(name,kind,case,body,w,c,ref,analytic,shift=False):
        nonlocal max_work,max_analytic,max_reference,max_current,max_volume,max_origin,shift_cases
        original=case.to_dict();save(name+'.json',dict(case=original,body_region_ids=list(body),weights=w.tolist(),origin_xy_m=c.tolist()));stress=force(solve(case),body,w,c);save(name+'.stress.json',stress);scale=ref['length_m']/.125;result=work(case,body,w,c,[1e-5*scale,5e-6*scale],[1e-3,5e-4]);save(name+'.work.json',result);assert result['status']=='complete' and result['failure'] is None and result['schema_version']==2;targets={'x':stress['force_xy_n_per_m'][0],'y':stress['force_xy_n_per_m'][1],'rotation':stress['nodal_rotation_stress_torque_z_nm_per_m']};expected={'x':ref['force_xy_n_per_m'][0],'y':ref['force_xy_n_per_m'][1],'rotation':ref['torque_z_nm_per_m']};worst=0.;reference_error=0.
        for row in result['records']:
            unit_scale=ref['torque_scale'] if row['kind']=='rotation' else ref['force_scale'];difference=abs(row['negative_potential_derivative']-targets[row['kind']])/unit_scale;assert difference<1e-5,(name,row['kind'],row['step'],difference);worst=max(worst,difference)
            if analytic:
                error=abs(row['negative_potential_derivative']-expected[row['kind']])/unit_scale;assert error<1e-5,(name,error);max_analytic=max(max_analytic,error)
            for trial in row['trials']:
                changed=type(case).from_dict(trial['case']);assert changed.boundaries==case.boundaries
                for i,(old,new) in enumerate(zip(case.partition.regions,changed.partition.regions)):
                    ratio=abs(changed.partition.region_area_m2[i]/case.partition.region_area_m2[i]-1.);assert ratio<1e-12;max_volume=max(max_volume,ratio);current=case.current_density_z_a_per_m2[old.id]*case.partition.region_area_m2[i];new_current=changed.current_density_z_a_per_m2[old.id]*changed.partition.region_area_m2[i];error=abs(new_current-current)/max(1.,abs(current));assert error<1e-12;max_current=max(max_current,error)
                    if type(case) is PlanarRecoilCase:
                        angle=trial['sign']*row['step'] if row['kind']=='rotation' and old.id in body else 0.;assert new.orientation_rad==old.orientation_rad+angle
                if type(case) is PlanarBHCase:assert trial['iteration_report']['status']=='converged' and trial['iteration_report']['history']
                else:
                    constant=trial['remanent_reference_constant_j_per_m'];base=result['baseline']['remanent_reference_constant_j_per_m'];error=abs(constant-base)/max(abs(base),1.);assert error<1e-12
                    identity=abs(trial['constitutive_potential_h0_j_per_m']-trial['constitutive_potential_j_per_m']-constant)/max(abs(constant),1.);assert identity<1e-12
            if type(case) is PlanarRecoilCase:
                values=[v['constitutive_potential_h0_j_per_m']-v['source_and_boundary_work_j_per_m'] for v in row['trials']];alternative=-(values[1]-values[0])/(2*row['step']);error=abs(alternative-row['negative_potential_derivative'])/unit_scale;assert error<1e-5;reference_error=max(reference_error,error)
        assert case.to_dict()==original;max_work=max(max_work,worst);max_reference=max(max_reference,reference_error)
        if shift:
            delta=np.array([.13,-.17])*ref['length_m'];moved=work(case,body,w,c+delta,[1e-5*scale,5e-6*scale],[1e-3,5e-4]);save(name+'.shifted-work.json',moved);correction=delta[0]*targets['y']-delta[1]*targets['x'];shift_cases+=1
            for old,new in zip(result['records'],moved['records']):
                expected_value=old['negative_potential_derivative']-(correction if old['kind']=='rotation' else 0.);unit_scale=ref['torque_scale'] if old['kind']=='rotation' else ref['force_scale'];error=abs(new['negative_potential_derivative']-expected_value)/unit_scale;assert error<1e-5,(name,'origin',error);max_origin=max(max_origin,error)
        row=dict(name=name,kind=kind,source_physics=case.to_dict()['physics'],order=case.element_order,analytic=analytic,max_stress_work_error=worst,max_reference_potential_derivative_error=reference_error,shifted_origin=shift);records.append(row);print('DONE',name,flush=True)
    for kind,order in (('bh',1),('recoil',1),('recoil',2)):
        for pair in (False,True):
            for angle in (0.,.3):
                for sign,scale in ((1.,.5),(-1.,2.)):
                    case,body,w,c,ref=material_body(kind,order=order,pair=pair,rotation_rad=angle,scale=scale,current_a=10*sign);run(f'{kind}-linear-P{order}-pair{pair}-theta{angle}-s{scale}-sign{sign}','linear_limit',case,body,w,c,ref,True,shift=kind=='bh' and not pair and angle==0.)
    for order in (1,2):
        for angle in (0.,.3):
            for sign,scale in ((1.,.5),(-1.,2.)):
                case,body,w,c,ref=material_body('recoil',permanent=True,order=order,rotation_rad=angle,scale=scale,remanence_t=.1*sign);run(f'recoil-moment-P{order}-theta{angle}-s{scale}-sign{sign}','magnetic_moment',case,body,w,c,ref,True,shift=order==2 and angle==0.)
    for kind,order in (('bh',1),('recoil',1),('recoil',2)):
        for angle in (0.,.3):
            for sign,scale in ((1.,.5),(-1.,2.)):
                case,body,w,c,ref=material_body(kind,nonlinear=True,principal=(2.,5.),permanent=kind=='recoil',current_a=1000.*sign,remanence_t=.1*sign,order=order,rotation_rad=angle,scale=scale);run(f'{kind}-material-P{order}-theta{angle}-s{scale}-sign{sign}','material_stress_work',case,body,w,c,ref,False)
    for order in (1,2):
        for outer in (.875,.95,1.):
            case,body,w,c,ref=material_body('recoil',permanent=True,order=order,weight_outer=outer);run(f'recoil-weight-P{order}-outer{outer}','weight',case,body,w,c,ref,True)
    for angle in (0.,.3):
        for scale in (.5,2.):
            case,body,w,c,ref=material_body('bh',nonlinear=True,order=1,current_a=0.,rotation_rad=angle,scale=scale);solution=solve(case)
            for mode in ('baseline','first_displacement','later_rotation'):
                limited=replace(case,controls=MagneticNewtonControls(max_iterations=1),initial_az_relative_to_reference_wb_per_m=None if mode=='baseline' else solution.az_relative_to_reference_wb_per_m.tolist());translations=[1e-4*scale,5e-5*scale] if mode!='later_rotation' else [1e-6*scale,5e-7*scale];rotations=[.001,.0005] if mode!='later_rotation' else [.01,.005]
                try:work(limited,body,w,c,translations,rotations)
                except PlanarMagneticVirtualWorkFailure as exc:failure=exc.report
                else:raise AssertionError('intended actual nonlinear failure converged')
                name=f'failure-{mode}-theta{angle}-s{scale}';save(name+'.json',failure);assert failure['status']=='failed' and failure['failure']['nonlinear_failure']['reason']=='iteration_limit';expected_kind={'baseline':'baseline','first_displacement':'x','later_rotation':'rotation'}[mode];assert failure['failure']['kind']==expected_kind
                if mode=='baseline':assert failure['baseline'] is None and failure['records']==[]
                else:
                    assert failure['baseline'] is not None and failure['records'][-1]['negative_potential_derivative'] is None
                    if mode=='later_rotation':assert len(failure['records'])==5 and all(row['negative_potential_derivative'] is not None and len(row['trials'])==2 for row in failure['records'][:-1])
                try:solve_planar_bh(PlanarBHCase.from_dict(failure['failure']['case']))
                except MagneticNonlinearFailure as exc:assert exc.report==failure['failure']['nonlinear_failure']
                else:raise AssertionError('retained failed Case converged on replay')
                failures.append(dict(name=name,mode=mode,angle=angle,scale=scale,completed_pairs=sum(row['negative_potential_derivative'] is not None for row in failure['records'])));print('RETAINED',name,flush=True)
    old_files={}
    def preserve(directory):
        for path in directory.iterdir():
            if path.name!='report.json' and path.suffix=='.json':old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    material=args.material_force.resolve();report=json.loads((material/'report.json').read_text());assert report['status']=='PASS' and report['cases']==62;preserve(material)
    for row in report['records']:
        request=json.loads((material/(row['name']+'.json')).read_text());cls=PlanarBHCase if request['case']['format']=='superfish_ng_planar_bh_case' else PlanarRecoilCase;case=cls.from_dict(request['case']);assert force(solve(case),request['body_region_ids'],request['weights'],request['origin_xy_m'])==json.loads((material/(row['name']+'.stress.json')).read_text())
    print('UNCHANGED material stress 62',flush=True)
    old=args.old_force.resolve();report=json.loads((old/'report.json').read_text());assert report['status']=='PASS' and report['cases']==56;preserve(old);old_work=0
    for row in report['records']:
        name=row['name'];request=json.loads((old/(name+'.json')).read_text());case=PlanarMagnetostaticCase.from_dict(request['case']);body=request['body_region_ids'];weights=request['weights'];c=request['origin_xy_m'];assert force(solve_planar_magnetostatic(case),body,weights,c)==json.loads((old/(name+'.stress.json')).read_text())
        if row['work_error'] is not None:
            expected=json.loads((old/(name+'.work.json')).read_text());assert scalar_work(case,body,weights,c,[r['step'] for r in expected['records'] if r['kind']=='x'],[r['step'] for r in expected['records'] if r['kind']=='rotation'])==expected;old_work+=1
        print('UNCHANGED scalar',name,flush=True)
    native=args.old_native.resolve();report=json.loads((native/'report.json').read_text());assert report['status']=='PASS' and report['cases']==8
    for row in report['records']:
        directory=native/row['name'];source=directory/'source'
        for path in source.iterdir():old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        for name in ('api.json','repeat.json','cli.json'):
            path=directory/name;old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();assert replay_planar_magnetic_force(source,path)==json.loads(path.read_text())
        print('UNCHANGED native',row['name'],flush=True)
    for name,digest in old_files.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    assert fingerprints()==before and len(records)==50 and shift_cases==4 and len(failures)==12 and old_work==40 and len(preserved)==166 and len(old_files)==461
    report=dict(status='PASS',cases=50,shifted_work_cases=4,successful_displaced_fem_solves=648,failed_cases=12,failures=failures,max_stress_work_error=max_work,max_analytic_work_error=max_analytic,max_reference_potential_derivative_error=max_reference,max_current_preservation_error=max_current,max_region_area_error=max_volume,max_origin_work_error=max_origin,old_material_stress_identical=62,old_scalar_force_identical=56,old_scalar_work_identical=40,old_scalar_native_reports_identical=24,old_files_unchanged=len(old_files),preserved_files=len(preserved),records=records,source_sha256=before,seconds=time.monotonic()-start,interpretation='Actual B-H/recoil displaced FEM with co-rotating material axes/remanence and true constitutive potential; independent Lorentz/moment, nodal stress and potential-reference checks; original and displaced actual Newton failures retained with no derivative for a failed pair. Scalar/material stress and scalar native unchanged; no continuum error bound or material native acceptance.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256','failures')})


if __name__=='__main__':main()

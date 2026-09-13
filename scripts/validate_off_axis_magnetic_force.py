# SPDX-License-Identifier: Apache-2.0
"""Full-ring finite-current Lorentz force, independent axial work and separate diagnostics."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.off_axis_magnetic_force_reference import axial_current_body
from superfish_ng.off_axis_magnetostatic import OffAxisMagnetostaticCase,solve_off_axis_magnetostatic
from superfish_ng.off_axis_magnetic_force import off_axis_magnetic_force as force,off_axis_magnetic_virtual_work as work


def fingerprints():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];preserved={};maximum_exact=maximum_work=maximum_quadrature=maximum_current=maximum_volume=0.;work_cases=0;gauge_results=[]
    def save(name,value):
        path=out/name;path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');preserved[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    def run(name,kind,case,body,w,ref,virtual):
        nonlocal maximum_exact,maximum_work,maximum_quadrature,maximum_current,maximum_volume,work_cases
        original=case.to_dict();save(name+'.json',dict(case=original,body_region_ids=list(body),weights=w.tolist()));solution=solve_off_axis_magnetostatic(case);result=force(solution,body,w);save(name+'.stress.json',result);error=abs(result['force_z_n']-ref['force_z_n'])/ref['force_scale_n']
        if ref['analytic_applicable']:assert error<1e-9,(name,error);maximum_exact=max(maximum_exact,error)
        assert result['quadrature_relative_difference']<1e-10,(name,result['quadrature_relative_difference']);maximum_quadrature=max(maximum_quadrature,result['quadrature_relative_difference']);work_error=None;baseline=None
        if virtual:
            scale=ref['length_m']/.125;trial=work(case,body,w,[1e-5*scale,5e-6*scale]);save(name+'.work.json',trial);work_cases+=1;work_error=0.;baseline=trial['baseline']
            for row in trial['records']:
                difference=abs(row['negative_potential_derivative_n']-result['force_z_n'])/ref['force_scale_n'];assert difference<1e-5,(name,row['step_m'],difference);work_error=max(work_error,difference)
                if ref['analytic_applicable']:assert abs(row['negative_potential_derivative_n']-ref['force_z_n'])/ref['force_scale_n']<1e-5
                for displaced in row['trials']:
                    changed=OffAxisMagnetostaticCase.from_dict(displaced['case']);assert changed.boundaries==case.boundaries;np.testing.assert_array_equal(changed.partition.mesh.points_rz_m[:,0],case.partition.mesh.points_rz_m[:,0]);edges=np.unique(case.partition.mesh.boundary_edges);np.testing.assert_array_equal(changed.partition.mesh.points_rz_m[edges],case.partition.mesh.points_rz_m[edges])
                    for i,region in enumerate(case.partition.regions):
                        old=case.current_density_phi_a_per_m2[region.id]*case.partition.region_area_m2[i];new=changed.current_density_phi_a_per_m2[region.id]*changed.partition.region_area_m2[i];current_error=abs(new-old)/max(1.,abs(old));volume_error=abs(changed.partition.region_volume_m3[i]/case.partition.region_volume_m3[i]-1.);assert current_error<1e-12 and volume_error<1e-12;maximum_current=max(maximum_current,current_error);maximum_volume=max(maximum_volume,volume_error)
            maximum_work=max(maximum_work,work_error)
        assert case.to_dict()==original;row=dict(name=name,kind=kind,order=case.element_order,quadrature_order=case.quadrature_order,analytic_applicable=ref['analytic_applicable'],analytic_force_z_n=ref['force_z_n'] if ref['analytic_applicable'] else None,force_z_n=result['force_z_n'],force_error=error if ref['analytic_applicable'] else None,quadrature_difference=result['quadrature_relative_difference'],work_error=work_error,baseline=baseline);records.append(row);print('DONE',name,flush=True);return row
    for order in (1,2):
        for scale in (.5,2.):
            for current in (10.,-10.):
                for external in (1.,-1.):
                    case,body,w,ref=axial_current_body(order=order,scale=scale,current_a=current,external_radial_constant_t_m=.0625*scale*external,shift_z_m=.25*scale if current<0 else 0.,reference_psi_wb=.125 if external>0 else 0.);run(f'analytic-P{order}-s{scale}-I{current}-Csign{external}','finite_current_lorentz',case,body,w,ref,True)
    for order in (1,2):
        for scale in (.5,2.):
            for mu in (3.,7.):
                case,body,w,ref=axial_current_body(order=order,scale=scale,current_a=1000.,external_radial_constant_t_m=.0625*scale,body_mu_r=mu,shift_z_m=-.25*scale);run(f'material-P{order}-s{scale}-mu{mu}','linear_material_body',case,body,w,ref,True)
    for order in (1,2):
        for n in (8,16,32):
            case,body,w,ref=axial_current_body(order=order,n=n);run(f'mesh-P{order}-n{n}','mesh',case,body,w,ref,False)
        for outer in (.875,.95,1.):
            case,body,w,ref=axial_current_body(order=order,weight_outer=outer);run(f'weight-P{order}-outer{outer}','weight',case,body,w,ref,False)
        for q in (4,8,16,32):
            case,body,w,ref=axial_current_body(order=order,n=16,quadrature_order=q);run(f'quadrature-P{order}-q{q}','quadrature',case,body,w,ref,False)
        rows=[]
        for offset in (0.,.125,-.25):
            case,body,w,ref=axial_current_body(order=order,reference_psi_wb=offset,shift_z_m=-.125);rows.append(run(f'reference-P{order}-psi{offset}','psi_reference',case,body,w,ref,True))
        assert rows[0]['baseline']['source_and_boundary_work_j']!=rows[1]['baseline']['source_and_boundary_work_j'];gauge_results.append(dict(order=order,rows=rows))
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    assert fingerprints()==before and len(records)==50 and work_cases==30 and len(preserved)==130
    report=dict(status='PASS',cases=50,analytic_cases=42,linear_material_cases=8,work_cases=30,displaced_fem_solves=120,mesh_cases=6,weight_cases=6,quadrature_cases=8,psi_reference_cases=6,max_analytic_force_error=maximum_exact,max_stress_work_error=maximum_work,max_quadrature_difference=maximum_quadrature,max_current_preservation_error=maximum_current,max_volume_preservation_error=maximum_volume,preserved_files=len(preserved),records=records,gauge_series=gauge_results,source_sha256=before,seconds=time.monotonic()-start,interpretation='Actual positive-radius P1/P2 FEM full-ring axial force N, independent finite-current Lorentz law and separate actual axial displacements. Weight, mesh, quadrature and psi reference series remain separate; no radial net force, meridional torque, continuum error bound or axis-connected/BH/recoil acceptance.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','gauge_series','source_sha256')})


if __name__=='__main__':main()

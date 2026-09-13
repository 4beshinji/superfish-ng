# SPDX-License-Identifier: Apache-2.0
"""Actual FEM dipole/quadrupole extraction, mesh and circle-sampling comparisons."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.planar_magnetic_multipole_reference import quadrupole,uniform_dipole
from scripts.validate_planar_magnetic_multipoles import relative
from superfish_ng.planar_magnetic_multipoles import PlanarMagneticMultipoleSeries as Series
from superfish_ng.planar_magnetic_multipole_extraction import extract_planar_magnetic_multipoles as extract
from superfish_ng.planar_magnetostatic import solve_planar_magnetostatic,PlanarMagnetostaticCase


def fingerprints():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def errors(report,reference):
    series=Series.from_dict(report['series']);coefficients=np.asarray(series.normal_t)+1j*np.asarray(series.skew_t);expected=np.r_[reference['coefficients_t'],np.zeros(len(coefficients)-2,dtype=complex)]
    field=max(relative(trace['b_xy_t'],reference['fields'](trace['points_xy_m'])) for trace in report['traces'])
    return relative(coefficients,expected),field


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);start=time.monotonic();before=fingerprints();records=[];preserved={};families=[];maximum_exact=0.;maximum_covariance=0.;baselines={}
    def run(name,kind,case,frame,ref,samples):
        path=out/(name+'.json');request=dict(case=case.to_dict(),frame=frame.to_dict(),maximum_order=8,angular_samples=samples);path.write_text(json.dumps(request,indent=2)+'\n');preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();assert PlanarMagnetostaticCase.from_dict(request['case']).to_dict()==case.to_dict()
        solution=solve_planar_magnetostatic(case);relative_before=solution.az_relative_to_reference_wb_per_m.copy();report=extract(solution,frame,8,samples);np.testing.assert_array_equal(solution.az_relative_to_reference_wb_per_m,relative_before);values=errors(report,ref)
        result=out/(name+'.result.json');result.write_text(json.dumps(report,indent=2)+'\n');preserved[result.name]=hashlib.sha256(result.read_bytes()).hexdigest();row=dict(name=name,kind=kind,coefficient_error=values[0],field_error=values[1],angular_difference=report['angular_coefficient_relative_difference'],radial_difference=report['radial_coefficient_relative_difference'],negative_harmonic_rms_t=report['traces'][1]['negative_harmonic_rms_t'],truncated_field_relative_error=report['traces'][1]['truncated_field_relative_error']);records.append(row);print('DONE',name,flush=True);return report,values,row
    for kind in ('dipole','quadrupole'):
        for variant in (1,2):
            for angle in (0.,.3,-.7):
                for scale in (.5,2.):
                    for strength in (1.,-7.):
                        factory=uniform_dipole if kind=='dipole' else quadrupole;n=4 if kind=='dipole' else 2*variant;order=variant if kind=='dipole' else 2;mu=1. if strength==1. else 3.;offset=0. if strength==1. else .125;case,frame,ref=factory(n=n,order=order,rotation_rad=angle,scale=scale,strength=strength,mu_r=mu,offset=offset)
                        name=f'{kind}-variant{variant}-theta{angle}-s{scale}-b{strength}';report,values,_=run(name,kind,case,frame,ref,128);assert max(values)<1e-10,(name,values);maximum_exact=max(maximum_exact,*values)
                        series=Series.from_dict(report['series']);normalized=np.r_[series.normal_t,series.skew_t]/strength;key=kind,variant
                        if key not in baselines:baselines[key]=normalized
                        covariance=relative(normalized,baselines[key]);assert covariance<1e-10;maximum_covariance=max(maximum_covariance,covariance)
    for angle in (0.,.3):
        for scale in (.5,2.):
            for strength in (1.,-7.):
                rows=[]
                for n in (8,16,32):
                    case,frame,ref=quadrupole(n=n,order=1,rotation_rad=angle,scale=scale,strength=strength,mu_r=2.,offset=0. if strength==1. else .125);name=f'P1-quadrupole-n{n}-theta{angle}-s{scale}-b{strength}';report,values,row=run(name,'P1_refinement',case,frame,ref,512);rows.append(row)
                    if len(rows)>1:assert row['coefficient_error']<rows[-2]['coefficient_error'] and row['field_error']<rows[-2]['field_error'],(name,rows)
                assert max(values)<.02,(name,values);families.append(dict(angle=angle,scale=scale,strength=strength,rows=rows,coefficient_and_field_limits=[.02,.02]))
    case,frame,ref=quadrupole(n=16,order=1,offset=0.);solution=solve_planar_magnetostatic(case);angular=[]
    for count in (64,128,256,512):
        result=extract(solution,frame,8,count);values=errors(result,ref);angular.append(dict(samples=count,coefficient_error=values[0],field_error=values[1],angular_difference=result['angular_coefficient_relative_difference'],radial_difference=result['radial_coefficient_relative_difference'],truncated_field_relative_error=result['traces'][1]['truncated_field_relative_error']))
    assert len(records)==72 and len(families)==8 and fingerprints()==before
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',cases=72,exact_cases=48,p1_refinement_cases=24,mesh_families=families,angular_study=angular,max_exact_error=maximum_exact,max_coefficient_covariance_error=maximum_covariance,records=records,preserved_files=len(preserved),source_sha256=before,seconds=time.monotonic()-start,
        interpretation='Original actual linear FEM B and harmonic coefficients checked separately against analytic dipole/quadrupole fields. P1 mesh and circle-sampling changes remain separate; no general field-error bound, force or torque.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256','mesh_families','angular_study')})


if __name__=='__main__':main()

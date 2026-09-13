# SPDX-License-Identifier: Apache-2.0
"""Declared linear apertures in actual B-H/recoil FEM, with preserved scalar reports."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.planar_magnetic_multipole_material_reference import linear_limit,exterior_material
from scripts.validate_planar_magnetic_multipoles import relative
from scripts.validate_planar_magnetic_multipole_extraction import errors
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh
from superfish_ng.planar_recoil import PlanarRecoilCase,solve_planar_recoil
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic
from superfish_ng.planar_magnetic_multipoles import PlanarMagneticMultipoleFrame as Frame
from superfish_ng.planar_magnetic_multipole_extraction import extract_planar_magnetic_multipoles as extract
from superfish_ng.planar_magnetic_multipole_saved import replay_planar_magnetic_multipoles


def fingerprints():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--old-extraction',type=Path,required=True);parser.add_argument('--old-native',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);start=time.monotonic();before=fingerprints();records=[];preserved={};families=[];maximum_exact=maximum_covariance=0.;baselines={}
    def run(name,kind,case,frame,ref,samples):
        path=out/(name+'.json');request=dict(case=case.to_dict(),frame=frame.to_dict(),maximum_order=8,angular_samples=samples);path.write_text(json.dumps(request,indent=2)+'\n');preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();assert type(case).from_dict(request['case']).to_dict()==case.to_dict()
        solution=solve_planar_bh(case) if type(case) is PlanarBHCase else solve_planar_recoil(case);report=extract(solution,frame,8,samples);assert report['schema_version']==2 and report['source_physics']==case.to_dict()['physics'];values=errors(report,ref);result=out/(name+'.result.json');result.write_text(json.dumps(report,indent=2)+'\n');preserved[result.name]=hashlib.sha256(result.read_bytes()).hexdigest();row=dict(name=name,kind=kind,coefficient_error=values[0],field_error=values[1],angular_difference=report['angular_coefficient_relative_difference'],radial_difference=report['radial_coefficient_relative_difference']);records.append(row);print('DONE',name,flush=True);return report,values,row
    for kind,field,order in (('bh','dipole',1),('recoil','dipole',1),('recoil','dipole',2),('recoil','quadrupole',2)):
        for angle in (0.,.3):
            for scale in (.5,2.):
                for strength in (1.,-1.):
                    case,frame,ref=linear_limit(kind,field,n=4,order=order,rotation_rad=angle,scale=scale,strength=strength,offset=.125 if strength<0 else 0.);name=f'{kind}-{field}-P{order}-theta{angle}-s{scale}-b{strength}';report,values,_=run(name,'linear_limit',case,frame,ref,128);assert max(values)<1e-9,(name,values);maximum_exact=max(maximum_exact,*values);normalized=np.r_[report['series']['normal_t'],report['series']['skew_t']]/strength;key=kind,field,order
                    if key not in baselines:baselines[key]=normalized
                    difference=relative(normalized,baselines[key]);assert difference<1e-9;maximum_covariance=max(maximum_covariance,difference)
    for kind in ('bh','recoil'):
        for angle in (0.,.3):
            for scale in (.5,2.):
                for amplitude in (1.,-1.):
                    order=2 if kind=='recoil' and amplitude<0 else 1;case,frame,ref=exterior_material(kind,n=4,order=order,scale=scale,amplitude=amplitude,angle=angle,offset=.125 if amplitude<0 else 0.);name=f'{kind}-exterior-P{order}-theta{angle}-s{scale}-b{amplitude}';report,values,_=run(name,'exterior_material',case,frame,ref,128);assert max(values)<1e-9,(name,values);maximum_exact=max(maximum_exact,*values)
    for angle in (0.,.3):
        for scale in (.5,2.):
            for strength in (1.,-1.):
                rows=[]
                for n in (8,16,32):
                    case,frame,ref=linear_limit('bh','quadrupole',n=n,order=1,rotation_rad=angle,scale=scale,strength=strength,offset=.125 if strength<0 else 0.);name=f'bh-quadrupole-P1-n{n}-theta{angle}-s{scale}-b{strength}';report,values,row=run(name,'P1_refinement',case,frame,ref,512);rows.append(row)
                    if len(rows)>1:assert row['coefficient_error']<rows[-2]['coefficient_error'] and row['field_error']<rows[-2]['field_error']
                assert max(values)<.02;families.append(dict(angle=angle,scale=scale,strength=strength,rows=rows,limits=[.02,.02]))
    old_files={};old_extraction=args.old_extraction.resolve();old_native=args.old_native.resolve();reference=json.loads((old_extraction/'report.json').read_text());assert reference['status']=='PASS' and reference['cases']==72
    for row in reference['records']:
        name=row['name'];paths=[old_extraction/(name+'.json'),old_extraction/(name+'.result.json')]
        for path in paths:old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        request=json.loads(paths[0].read_text());case=PlanarMagnetostaticCase.from_dict(request['case']);fresh=extract(solve_planar_magnetostatic(case),Frame.from_dict(request['frame']),request['maximum_order'],request['angular_samples']);assert fresh==json.loads(paths[1].read_text()) and fresh['schema_version']==1
    native_reference=json.loads((old_native/'report.json').read_text());assert native_reference['status']=='PASS' and native_reference['cases']==24
    for row in native_reference['records']:
        directory=old_native/row['name'];run=directory/'source'
        for path in run.iterdir():old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        for name in ('api.json','repeat.json','cli.json'):
            path=directory/name;old_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();assert replay_planar_magnetic_multipoles(run,path)==json.loads(path.read_text())
    for name,digest in old_files.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    assert fingerprints()==before and len(records)==72 and len(families)==8 and len(old_files)==336
    report=dict(status='PASS',cases=72,exact_cases=48,p1_cases=24,mesh_families=families,max_exact_error=maximum_exact,max_linear_limit_covariance_error=maximum_covariance,old_scalar_extractions_identical=72,old_scalar_native_reports_identical=72,old_files_unchanged=len(old_files),preserved_files=len(preserved),records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='Actual B-H/recoil FEM in a declared homogeneous linear isotropic nonremanent source-free disk, with exterior nonlinear/anisotropic/remanent material retained; independent analytic fields and coefficients; mesh error separate; scalar extraction/report version 1 unchanged; no force/torque or continuum bound.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256','mesh_families')})


if __name__=='__main__':main()

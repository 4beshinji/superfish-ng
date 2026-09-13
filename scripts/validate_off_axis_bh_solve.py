# SPDX-License-Identifier: Apache-2.0
"""Off-axis nonlinear original fields, integral errors, collocation and failures."""
import argparse,hashlib,json,sys,time
from dataclasses import replace
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.off_axis_bh_reference import radial_field,current_annulus,radial_layers,field_l2_errors,independent_current_bvp
from superfish_ng.off_axis_bh import OffAxisBHCase,solve_off_axis_bh,off_axis_bh_quantities
from superfish_ng.nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure
from superfish_ng.off_axis_magnetic_materials import OffAxisMagneticPartition
from superfish_ng.magnetic_materials import LinearMagneticMaterial
from superfish_ng.off_axis_magnetostatic import OffAxisMagnetostaticCase,solve_off_axis_magnetostatic,off_axis_magnetostatic_quantities
from superfish_ng.constants import MU0,TAU


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def errors(s,ref):
    values=field_l2_errors(s,ref);q=off_axis_bh_quantities(s);potential=[abs(q[key]/ref['potentials'][key]-1.) if ref['potentials'][key] else abs(q[key]) for key in ('energy_j','coenergy_j')]
    mesh=s.case.partition.mesh;edges=mesh.points_rz_m[mesh.boundary_edges];perimeter=float(np.linalg.norm(edges[:,1]-edges[:,0],axis=1).sum());radius=ref['model']['radius_m'];bscale=ref['field_scales'][2];hscale=ref['field_scales'][3]
    current_scale=perimeter*hscale+abs(ref['source_current_a']) or 1.;reaction_scale=TAU*perimeter*hscale or 1.;flux_scale=TAU*radius**2*bscale or 1.
    ampere=abs(q['original_field_ampere_balance_a'])/current_scale;reaction=max((abs(q['fixed_boundary_original_reaction_a'][name]-value)/reaction_scale for name,value in ref['fixed_reaction_a'].items()),default=0.)
    flux=max(abs(q['boundary_original_normal_flux_wb'][name]-value)/flux_scale for name,value in ref['boundary_flux_wb'].items())
    assert abs(q['total_source_current_a']-ref['source_current_a'])/current_scale<1e-11
    return [*values,*potential,float(ampere),float(reaction)],float(flux),q


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic()
    records=[];preserved={};families=[];bvps=[];baseline={};counts=dict(radial_field=0,layered=0,current=0,linear=0,zero=0,failure=0);maximum_exact=maximum_covariance=maximum_linear=0.;rejected=0
    def input_case(name,case):
        path=out/(name+'.json');path.write_text(json.dumps(case.to_dict(),indent=2,allow_nan=False)+'\n');preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();assert OffAxisBHCase.from_dict(json.loads(path.read_text())).to_dict()==case.to_dict()
    def save(name,kind,**result):
        records.append(dict(name=name,kind=kind,**result));counts[kind]+=1;(out/'progress.json').write_text(json.dumps(dict(completed=len(records),last=name),indent=2)+'\n');print('DONE',name,flush=True)
    def covariance(key,s,sign,scale):
        normalized=s.psi_relative_to_reference_wb/(sign*scale**2)
        if key not in baseline:baseline[key]=normalized.copy()
        den=np.linalg.norm(normalized);return float(np.linalg.norm(normalized-baseline[key])/den) if den else float(np.linalg.norm(normalized-baseline[key]))
    for holes in (0,1,2):
        for layers in (False,True):
            for scale in (.5,2.):
                for hscale in (1.,7.):
                    sign=1. if hscale==1. else -1.;shift=0. if hscale==1. else -.25;offset=0. if hscale==1. else .125;name=f'radial-field-holes{holes}-layers{layers}-s{scale}-h{hscale}'
                    case,ref=radial_field(n=2,scale=scale,h_scale=hscale,amplitude=sign,shift=shift,holes=holes,radial_materials=layers,offset=offset);input_case(name,case);s=solve_off_axis_bh(case);values,flux,q=errors(s,ref)
                    assert max(*values,flux)<1e-10,(name,values,flux);maximum_exact=max(maximum_exact,*values,flux);diff=covariance((holes,layers),s,sign,scale);assert diff<1e-10;maximum_covariance=max(maximum_covariance,diff)
                    save(name,'radial_field',status='converged',errors=values,flux_relative_error=flux,quantities=q,iteration=s.iteration_report)
    limits=[1e-3,1e-3,.02,.02,1e-3,1e-3,.02,.02]
    for kind,factory in (('layered',radial_layers),('current',current_annulus)):
        for boundary in ('fixed','tangential'):
            for scale in (.5,2.):
                for hscale in (1.,7.):
                    sign=1. if hscale==1. else -1.;shift=0. if hscale==1. else -.25;offset=0. if hscale==1. else .125;rows=[]
                    for n in (8,16,32):
                        name=f'{kind}-{boundary}-n{n}-s{scale}-h{hscale}';case,ref=factory(n=n,scale=scale,h_scale=hscale,amplitude=sign,boundary=boundary,shift=shift,offset=offset);input_case(name,case);s=solve_off_axis_bh(case);values,flux,q=errors(s,ref)
                        save(name,kind,status='converged',errors=values,flux_relative_error=flux,quantities=q,iteration=s.iteration_report);rows.append(dict(n=n,errors=values,flux_relative_error=flux,quadrature=q['quadrature_comparison']))
                        if len(rows)>1:assert all(a<b for a,b in zip(values[:4],rows[-2]['errors'][:4])),(name,rows)
                    assert all(a<b for a,b in zip(values,limits)) and flux<2e-3,(name,values,flux)
                    families.append(dict(kind=kind,boundary=boundary,scale=scale,h_scale=hscale,rows=rows,limits=limits))
                    if kind=='current':bvps.append(dict(boundary=boundary,scale=scale,h_scale=hscale,**independent_current_bvp(case,ref)))
    for boundary in ('fixed','tangential'):
        for scale in (.5,2.):
            for sign in (-1.,1.):
                name=f'linear-{boundary}-s{scale}-sign{sign}';case,ref=current_annulus(n=4,scale=scale,amplitude=sign,linear=True,boundary=boundary,quadrature_order=16);input_case(name,case);p=case.partition
                oldp=OffAxisMagneticPartition(p.mesh,[LinearMagneticMaterial(m.id,1/(MU0*m.h_a_per_m[1]/m.b_t[1])) for m in p.materials],p.regions);old=solve_off_axis_magnetostatic(OffAxisMagnetostaticCase(oldp,dict(case.current_density_phi_a_per_m2),case.boundaries,1,16));s=solve_off_axis_bh(case);values,flux,q=errors(s,ref);oq=off_axis_magnetostatic_quantities(old)
                difference=max(float(np.linalg.norm(s.psi_relative_to_reference_wb-old.psi_relative_to_reference_wb)/np.linalg.norm(old.psi_relative_to_reference_wb)),abs(q['energy_j']/oq['energy_j']-1.),abs(q['coenergy_j']/q['energy_j']-1.));assert difference<1e-10 and s.iteration_report['iterations']==1;maximum_linear=max(maximum_linear,difference)
                save(name,'linear',status='converged',errors=values,flux_relative_error=flux,quantities=q,iteration=s.iteration_report,old_linear_difference=difference)
    for holes in (0,1):
        for shift in (0.,-.25):
            for offset in (0.,.125):
                name=f'zero-holes{holes}-shift{shift}-offset{offset}';case,ref=radial_field(n=2,amplitude=0.,holes=holes,radial_materials=bool(holes),shift=shift,offset=offset);input_case(name,case);s=solve_off_axis_bh(case);values,flux,q=errors(s,ref)
                np.testing.assert_array_equal(s.psi_relative_to_reference_wb,0.);np.testing.assert_array_equal(s.psi_wb,offset)
                ap_roundoff=32*np.finfo(float).eps*abs(offset)/ref['model']['inner_radius_m']*np.sqrt(case.partition.mesh.volume_m3)
                assert max(values[0],*values[2:],flux)==0. and values[1]<=ap_roundoff and s.iteration_report['iterations']==0
                save(name,'zero',status='converged',errors=values,flux_relative_error=flux,aphi_absolute_roundoff_bound=ap_roundoff,quantities=q,iteration=s.iteration_report)
    for scale in (.5,2.):
        for mode,strength in (('iterations',1.),('iterations',2.),('range',1.),('initial',1.)):
            name=f'failure-{mode}-{strength}-s{scale}';case,_=current_annulus(n=2,scale=scale,amplitude=strength)
            if mode=='iterations':case=replace(case,controls=MagneticNewtonControls(max_iterations=1));reason='iteration_limit'
            elif mode=='initial':
                initial=np.zeros(len(case.partition.mesh.points_rz_m));initial[1]=100.;case=replace(case,initial_psi_relative_to_reference_wb=initial.tolist());reason='invalid_initial_field'
            else:
                raw=case.to_dict();next(b for b in raw['boundaries'] if b.get('tangential_h_a_per_m',0.)!=0.)['tangential_h_a_per_m']=1e9;raw['controls']['max_backtracks']=3;case=OffAxisBHCase.from_dict(raw);reason='line_search_limit'
            input_case(name,case)
            try:solve_off_axis_bh(case)
            except MagneticNonlinearFailure as exc:
                failure=exc.report;assert failure['schema_version']==2 and failure['coefficient_field']=='psi_relative_to_reference_wb' and 'last_valid_relative_coefficients' not in failure;assert failure['reason']==reason and (failure['last_valid_coefficients'] is None)==(mode=='initial');json.dumps(failure,allow_nan=False);save(name,'failure',status='expected_failure',failure=failure)
            else:raise AssertionError('expected retained nonlinear failure')
    assert len(records)==96 and counts==dict(radial_field=24,layered=24,current=24,linear=8,zero=8,failure=8) and len(bvps)==8 and fingerprints()==before
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',cases=96,successful_cases=88,expected_failures=8,case_counts=counts,max_exact_error=maximum_exact,max_coefficient_scaling_error=maximum_covariance,max_linear_limit_error=maximum_linear,rejected_trials=sum(v['event']=='trial' and not v['accepted'] for row in records if row['status']=='converged' for v in row['iteration']['history']),
        refinement_families=families,independent_bvp_comparisons=bvps,records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='Original nonlinear off-axis psi/Aphi/B/H, full-3D U/Ustar, H circulation/reaction and B flux separately checked. Declared quadrature and q+4 residual differences remain separate from Newton and mesh errors. Independent 1D collocation does not certify general 2D mesh accuracy. Expected failures retain histories; no legacy comparison.')
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256','refinement_families','independent_bvp_comparisons')})


if __name__=='__main__':main()

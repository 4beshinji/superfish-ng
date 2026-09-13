# SPDX-License-Identifier: Apache-2.0
"""Independent planar nonlinear fields, convex objective, collocation and failures."""
import argparse,hashlib,json,sys,time
from dataclasses import replace
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.planar_bh_reference import uniform_field,layered_field,current_slab,field_l2_errors,independent_current_bvp
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh,planar_bh_quantities
from superfish_ng.nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure
from superfish_ng.magnetic_materials import PlanarMagneticPartition,LinearMagneticMaterial
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic,planar_magnetostatic_quantities
from superfish_ng.constants import MU0


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def errors(s,reference):
    fields=field_l2_errors(s,reference);q=planar_bh_quantities(s);potential=[abs(q[name]/reference['potentials'][name]-1.) if reference['potentials'][name] else abs(q[name]) for name in ('energy_j_per_m','coenergy_j_per_m')]
    mesh=s.case.partition.mesh;edges=mesh.points_xy_m[mesh.boundary_edges];perimeter=float(np.linalg.norm(edges[:,1]-edges[:,0],axis=1).sum());current_scale=perimeter*reference['intensity_scale']+abs(reference['source_current_a']) or 1.
    ampere=abs(q['original_field_ampere_balance_a'])/current_scale;reaction_scale=perimeter*reference['intensity_scale'] or 1.
    reaction=max(abs(q['fixed_boundary_original_reaction_current_a'][name]-value)/reaction_scale for name,value in reference['fixed_reaction_a'].items())
    flux_scale=perimeter*reference['field_scale'] or 1.;flux=max(abs(q['boundary_original_normal_flux_wb_per_m'][name]-value)/flux_scale for name,value in reference['boundary_flux_wb_per_m'].items())
    assert abs(q['total_source_current_a']-reference['source_current_a'])/current_scale<1e-11
    return [*fields,*potential,float(ampere),float(reaction)],float(flux),q


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();start=time.monotonic();records=[];preserved={};families=[];bvps=[];baseline={};counts=dict(uniform=0,layered=0,current=0,linear=0,zero=0,failure=0);maximum_exact=maximum_covariance=maximum_linear=0.;rejected=0
    def save(name,case,kind,**result):
        path=out/(name+'.json');path.write_text(json.dumps(case.to_dict(),indent=2)+'\n');preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();assert PlanarBHCase.from_dict(json.loads(path.read_text())).to_dict()==case.to_dict()
        records.append(dict(name=name,kind=kind,**result));counts[kind]+=1;(out/'progress.json').write_text(json.dumps(dict(completed=len(records),last=name),indent=2)+'\n');print('DONE',name,flush=True)
    def covariance(key,s,scale,sign):
        normalized=s.az_relative_to_reference_wb_per_m/(scale*sign)
        if key not in baseline:baseline[key]=normalized.copy()
        denominator=np.linalg.norm(normalized);return float(np.linalg.norm(normalized-baseline[key])/denominator) if denominator else float(np.linalg.norm(normalized-baseline[key]))
    for kind,factory in (('uniform',uniform_field),('layered',layered_field)):
        for strength in ((.375,1.5) if kind=='uniform' else (1.,)):
            for boundary in ('fixed','tangential'):
                for scale in (.5,2.):
                    for hscale in (1.,7.):
                        for sign in (-1.,1.):
                            kwargs=dict(b_t=sign*strength) if kind=='uniform' else dict(amplitude=sign)
                            name=f'{kind}-{strength}-{boundary}-s{scale}-h{hscale}-sign{sign}'
                            case,ref=factory(n=2,scale=scale,h_scale=hscale,boundary=boundary,offset=.125 if hscale==7. else 0.,angle=.713 if hscale==7. else 0.,shift=(-.25,.125) if hscale==7. else (0.,0.),**kwargs)
                            s=solve_planar_bh(case);values,flux,q=errors(s,ref);assert max(*values,flux)<1e-10;maximum_exact=max(maximum_exact,*values,flux)
                            diff=covariance((kind,strength,boundary),s,scale,sign);assert diff<1e-10;maximum_covariance=max(maximum_covariance,diff)
                            rejected+=sum(v['event']=='trial' and not v['accepted'] for v in s.iteration_report['history'])
                            save(name,case,kind,status='converged',errors=values,flux_relative_error=flux,quantities=q,iteration=s.iteration_report)
    limits=[1e-3,.02,.02,1e-3,1e-3,.02,.02]
    for boundary in ('fixed','tangential'):
        for scale in (.5,2.):
            for hscale in (1.,7.):
                sign=-1. if hscale==7. else 1.;rows=[]
                for n in (8,16,32):
                    name=f'current-{boundary}-n{n}-s{scale}-h{hscale}';case,ref=current_slab(n=n,scale=scale,h_scale=hscale,amplitude=sign,boundary=boundary,offset=.125 if hscale==7. else 0.,angle=.713 if hscale==7. else 0.,shift=(-.25,.125) if hscale==7. else (0.,0.))
                    s=solve_planar_bh(case);values,flux,q=errors(s,ref);objective=q['energy_j_per_m']-float(s.az_relative_to_reference_wb_per_m@(s.current_load_a+s.boundary_load_a));potential_scale=sum(ref['potentials'].values());gap=(objective-ref['relative_objective_j_per_m'])/potential_scale
                    rounding=64*np.finfo(float).eps*(abs(objective)+abs(ref['relative_objective_j_per_m']))/potential_scale
                    assert gap>=-rounding,(gap,rounding)
                    if rows:assert all(a<b for a,b in zip(values[:3],rows[-1]['errors'][:3])) and gap<=rows[-1]['relative_convex_objective_gap']+rounding
                    diff=covariance(('current',boundary,n),s,scale,sign);assert diff<1e-10;maximum_covariance=max(maximum_covariance,diff)
                    row=dict(n=n,errors=values,flux_relative_error=flux,relative_convex_objective_gap=gap,objective_roundoff_allowance=rounding);rows.append(row);save(name,case,'current',status='converged',**row,quantities=q,iteration=s.iteration_report)
                assert all(a<b for a,b in zip(values,limits)) and flux<2e-3,(values,flux)
                families.append(dict(boundary=boundary,scale=scale,h_scale=hscale,rows=rows,limits=limits));bvps.append(dict(boundary=boundary,scale=scale,h_scale=hscale,**independent_current_bvp(case,ref)))
    for boundary in ('fixed','tangential'):
        for scale in (.5,2.):
            for sign in (-1.,1.):
                name=f'linear-{boundary}-s{scale}-sign{sign}';case,ref=current_slab(n=4,scale=scale,amplitude=sign,boundary=boundary,linear=True,offset=.125)
                s=solve_planar_bh(case);p=case.partition;oldp=PlanarMagneticPartition(p.mesh,[LinearMagneticMaterial(m.id,1/(MU0*(m.h_a_per_m[1]/m.b_t[1]))) for m in p.materials],p.regions)
                old=solve_planar_magnetostatic(PlanarMagnetostaticCase(oldp,dict(case.current_density_z_a_per_m2),case.boundaries,1));oq=planar_magnetostatic_quantities(old);values,flux,q=errors(s,ref)
                diff=max(float(np.linalg.norm(s.az_relative_to_reference_wb_per_m-old.az_relative_to_reference_wb_per_m)/np.linalg.norm(old.az_relative_to_reference_wb_per_m)),abs(q['energy_j_per_m']/oq['energy_j_per_m']-1.));assert diff<1e-10 and s.iteration_report['iterations']==1;maximum_linear=max(maximum_linear,diff)
                save(name,case,'linear',status='converged',errors=values,flux_relative_error=flux,linear_limit_relative_difference=diff,quantities=q,iteration=s.iteration_report)
    for boundary in ('fixed','tangential'):
        for offset in (0.,.125):
            for angle in (0.,.713):
                name=f'zero-{boundary}-offset{offset}-angle{angle}';case,ref=uniform_field(n=2,b_t=0.,boundary=boundary,offset=offset,angle=angle,shift=(-.25,.125));s=solve_planar_bh(case);values,flux,q=errors(s,ref)
                np.testing.assert_array_equal(s.az_relative_to_reference_wb_per_m,0.);np.testing.assert_array_equal(s.az_wb_per_m,offset);assert max(*values,flux)==0. and s.iteration_report['iterations']==0
                save(name,case,'zero',status='converged',errors=values,flux_relative_error=flux,quantities=q,iteration=s.iteration_report)
    for scale in (.5,2.):
        for mode,strength,reason in (('iterations',.75,'iteration_limit'),('iterations',1.5,'iteration_limit'),('range',.75,'line_search_limit'),('initial',.75,'invalid_initial_field')):
            name=f'failure-{mode}-{strength}-s{scale}';case,_=uniform_field(n=2,scale=scale,b_t=strength)
            if mode=='iterations':case=replace(case,controls=MagneticNewtonControls(max_iterations=1))
            elif mode=='range':
                raw=case.to_dict();next(v for v in raw['boundaries'] if v['id']=='top')['tangential_h_a_per_m']=-1e9;raw['controls']['max_backtracks']=3;case=PlanarBHCase.from_dict(raw)
            else:
                values=np.zeros(len(case.partition.mesh.points_xy_m));fixed=set(case.partition.mesh.boundary_edges[list(case.boundaries[0].edge_indices)].ravel());values[next(i for i in range(len(values)) if i not in fixed)]=100*scale;case=replace(case,initial_az_relative_to_reference_wb_per_m=values.tolist())
            try:solve_planar_bh(case)
            except MagneticNonlinearFailure as exc:
                failure=exc.report;assert failure['reason']==reason and failure['status']=='failed';assert json.loads(json.dumps(failure,allow_nan=False))==failure
                assert (failure['last_valid_relative_coefficients'] is None)==(mode=='initial')
                if mode=='range':assert any(v.get('reason')=='invalid_material_trial' for v in failure['history'])
                save(name,case,'failure',status='expected_failure',failure=failure)
            else:raise AssertionError('invalid or unconverged nonlinear solve returned success')
    assert len(records)==96 and counts==dict(uniform=32,layered=16,current=24,linear=8,zero=8,failure=8) and len(bvps)==8 and rejected>0 and fingerprints()==before
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',cases=len(records),case_counts=counts,successful_cases=88,expected_failures=8,max_exact_error=maximum_exact,max_coefficient_scaling_error=maximum_covariance,max_linear_limit_error=maximum_linear,
        rejected_uniform_trials=rejected,refinement_families=families,independent_bvp_comparisons=bvps,records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='Original nonlinear P1 Az/B/H, U/Ustar, original H circulation/reaction and B flux checked separately. Convex variational gap and independent 1D collocation do not certify general 2D mesh accuracy. Expected failures retain histories; no extrapolation, hysteresis or legacy comparison.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256','refinement_families','independent_bvp_comparisons')})


if __name__=='__main__':main()

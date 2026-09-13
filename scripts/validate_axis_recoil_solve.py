# SPDX-License-Identifier: Apache-2.0
"""Independent axis recoil original fields, potentials, flux and refinement."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.axis_recoil_reference import uniform_remanence,interface_patch,cylinder_current,layered_remanence
from superfish_ng.axis_recoil import solve_axis_recoil,axis_recoil_quantities,AxisRecoilCase
from superfish_ng.constants import TAU


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def errors(solution,reference):
    p=solution.case.partition;vertices=p.mesh.points_rz_m[p.mesh.triangles];delta=vertices[:,1:]-vertices[:,0,None,:]
    det=delta[:,0,0]*delta[:,1,1]-delta[:,0,1]*delta[:,1,0];cells=np.arange(len(vertices));volume=0.
    nodes,weights=np.polynomial.legendre.leggauss(4);nodes=(nodes+1)/2;weights=weights/2;numerator=np.zeros(4);denominator=np.zeros(4)
    for i,x in enumerate(nodes):
        for j,y0 in enumerate(nodes):
            y=y0*(1-x);bary=np.array([1-x-y,x,y]);points=np.einsum('i,tij->tj',bary,vertices);measure=TAU*points[:,0]*det*weights[i]*weights[j]*(1-x);volume+=float(measure.sum())
            f=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)));a,ap,b,h=reference['fields'](points)
            actual=[np.asarray(f['Aphi_over_r_T'])[:,None],np.asarray(f['Aphi_Wb_per_m'])[:,None],np.column_stack((f['Br_T'],f['Bz_T'])),np.column_stack((f['Hr_A_per_m'],f['Hz_A_per_m']))]
            expected=[a[:,None],ap[:,None],b,h]
            for k,(v,e) in enumerate(zip(actual,expected)):
                numerator[k]+=float(measure@np.sum((v-e)**2,axis=1));denominator[k]+=float(measure@np.sum(e**2,axis=1))
    if denominator[3]==0.:denominator[3]=volume*reference['intensity_scale']**2
    relative=np.sqrt(numerator/np.where(denominator,denominator,1.)).tolist();q=axis_recoil_quantities(solution)
    potential_scale=sum(abs(v) for v in reference['potentials'].values()) or 1.
    potential=max(abs(q[name]-value)/potential_scale for name,value in reference['potentials'].items())
    edges=p.mesh.points_rz_m[p.mesh.boundary_edges];perimeter=float(np.linalg.norm(edges[:,1]-edges[:,0],axis=1).sum());radius=p.mesh.outer_rz_m[:,0].max()
    current_scale=perimeter*reference['intensity_scale']+abs(reference['source_current_a']) or 1.
    ampere=abs(q['original_field_ampere_balance_a'])/current_scale
    reaction_scale=TAU*radius**2*perimeter*reference['intensity_scale'] or 1.
    reaction=max((abs(q['fixed_boundary_original_reaction_a_m2'][name]-value)/reaction_scale for name,value in reference['fixed_reaction_a_m2'].items()),default=0.)
    flux_scale=TAU*radius**2*reference['field_scale'] or 1.
    flux=max(abs(q['boundary_original_normal_flux_wb'][name]-value)/flux_scale for name,value in reference['boundary_flux_wb'].items())
    assert abs(q['total_source_current_a']-reference['source_current_a'])/current_scale<1e-11
    return [*relative,float(potential),float(ampere),float(reaction)],float(flux),q


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();start=time.monotonic();records=[];preserved={};families=[];pairs={};counts=dict(uniform=0,patch=0,current=0,layered=0,zero=0);maximum_exact=maximum_covariance=0.
    def save(name,case,solution,reference,kind):
        values,flux,q=errors(solution,reference);record=dict(name=name,kind=kind,element_order=case.element_order,errors=values,flux_relative_error=flux,quantities=q)
        path=out/(name+'.json');path.write_text(json.dumps(dict(case=case.to_dict(),**record),indent=2)+'\n');preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();records.append(record);counts[kind]+=1
        assert AxisRecoilCase.from_dict(json.loads(path.read_text())['case']).to_dict()==case.to_dict()
        (out/'progress.json').write_text(json.dumps(dict(completed=len(records),last=name),indent=2)+'\n');print('DONE',name,values,flux,flush=True)
        return values,flux
    for kind,factory in (('uniform',uniform_remanence),('patch',interface_patch),('current',cylinder_current)):
        for order in (1,2):
            for boundary in ('fixed','tangential'):
                for holes in ((0,) if kind=='uniform' else (1,) if kind=='patch' else (1,2)):
                    for scale in (.5,2.):
                        for mu_scale in (1.,7.):
                            amplitude=1. if mu_scale==1. else -1.;shift=0. if mu_scale==1. else -.25
                            name=f'{kind}-p{order}-{boundary}-h{holes}-s{scale}-mu{mu_scale}'
                            case,reference=factory(order,n=2,scale=scale,mu_scale=mu_scale,amplitude=amplitude,boundary=boundary,shift=shift,holes=holes);solution=solve_axis_recoil(case)
                            values,flux=save(name,case,solution,reference,kind);assert max(*values,flux)<1e-10;maximum_exact=max(maximum_exact,*values,flux)
                            key=kind,order,boundary,holes
                            normalized=solution.aphi_over_r_t/amplitude
                            if key not in pairs:pairs[key]=normalized.copy()
                            else:
                                difference=float(np.linalg.norm(normalized-pairs[key])/np.linalg.norm(pairs[key]));assert difference<1e-10;maximum_covariance=max(maximum_covariance,difference)
    for order in (1,2):
        levels=(8,16,32) if order==1 else (4,8,16);limits=[1e-3,1e-3,.02,.02,1e-3,.02,.02] if order==1 else [2e-5,2e-5,.001,.001,2e-5,.002,.002]
        for scale in (.5,2.):
            for mu_scale in (1.,7.):
                rows=[]
                for n in levels:
                    amplitude=1. if mu_scale==1. else -1.;shift=0. if mu_scale==1. else -.25;name=f'layered-p{order}-n{n}-s{scale}-mu{mu_scale}'
                    case,reference=layered_remanence(order,n,scale,mu_scale,amplitude,shift);solution=solve_axis_recoil(case);values,flux=save(name,case,solution,reference,'layered');rows.append(dict(n=n,errors=values,flux_relative_error=flux))
                    if len(rows)>1:
                        # No fixed-a edges exist in this family; its reaction error is exactly zero.
                        assert all(a<b for a,b in zip(values[:6],rows[-2]['errors'][:6]))
                assert all(a<b for a,b in zip(values,limits)) and flux<(2e-3 if order==1 else 2e-5)
                families.append(dict(order=order,scale=scale,mu_scale=mu_scale,rows=rows,limits=limits))
    for order in (1,2):
        for boundary in ('fixed','tangential'):
            for holes in (0,1):
                name=f'zero-p{order}-{boundary}-h{holes}';case,reference=uniform_remanence(order,n=1,amplitude=0.,boundary=boundary,holes=holes);solution=solve_axis_recoil(case);values,flux=save(name,case,solution,reference,'zero')
                np.testing.assert_array_equal(solution.aphi_over_r_t,0.);assert max(*values,flux)==0.
    assert len(records)==96 and counts==dict(uniform=16,patch=16,current=32,layered=24,zero=8) and fingerprints()==before
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',cases=len(records),case_counts=counts,max_exact_error=maximum_exact,max_coefficient_scaling_error=maximum_covariance,refinement_families=families,
        records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='original a/Aphi/B/H, fixed-reference constitutive potentials[J], original H circulation/reaction and normal B flux[Wb] checked separately; a small algebraic residual is not a field-accuracy certificate; synthetic linear recoil materials')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256','refinement_families')})


if __name__=='__main__':main()

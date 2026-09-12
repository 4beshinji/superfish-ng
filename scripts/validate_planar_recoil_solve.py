# SPDX-License-Identifier: Apache-2.0
"""Independent recoil patches, constitutive potentials, current and P1 refinement."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.planar_recoil_reference import uniform_remanence,interface_patch,layered_remanence,quadratic_current
from superfish_ng.planar_recoil import PlanarRecoilCase,solve_planar_recoil,planar_recoil_quantities


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
        for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def field_errors(solution,reference):
    mesh=solution.case.partition.mesh;vertices=mesh.points_xy_m[mesh.triangles];cells=np.arange(len(vertices))
    u=vertices[:,1]-vertices[:,0];v=vertices[:,2]-vertices[:,0];det=u[:,0]*v[:,1]-u[:,1]*v[:,0]
    nodes,weights=np.polynomial.legendre.leggauss(4);nodes=(nodes+1)/2;weights=weights/2
    numerator=np.zeros(3);denominator=np.zeros(3);area=0.
    for x,wx in zip(nodes,weights):
        for t,wt in zip(nodes,weights):
            y=(1-x)*t;bary=np.tile([1-x-y,x,y],(len(cells),1));points=np.einsum('qi,qij->qj',bary,vertices)
            az,b,h=reference['fields'](points);actual=solution.fields_in_cells(cells,bary)
            values=(actual['Az_Wb_per_m'],np.column_stack((actual['Bx_T'],actual['By_T'])),np.column_stack((actual['Hx_A_per_m'],actual['Hy_A_per_m'])))
            measure=det*wx*wt*(1-x);area+=float(measure.sum())
            for i,(a,e) in enumerate(zip(values,(az,b,h))):
                square=(a-e)**2;norm=e**2
                if square.ndim==2:square=square.sum(axis=1);norm=norm.sum(axis=1)
                numerator[i]+=float(measure@square);denominator[i]+=float(measure@norm)
    denominator[0]=area*reference['potential_scale']**2
    if denominator[2]==0.:denominator[2]=area*reference['intensity_scale']**2
    assert np.all(denominator>0.)
    return np.sqrt(numerator/denominator).tolist()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];pairs={};convergence=[];preserved={}
    maximum_exact=maximum_scaling=0.;counts=dict(uniform=0,interface=0,layered=0,quadratic=0,refinement=0,zero=0)
    def run(name,case,reference):
        s=solve_planar_recoil(case);q=planar_recoil_quantities(s);errors=field_errors(s,reference)
        pscale=sum(abs(v) for v in reference['potentials'].values());potentials={k:float(abs(q[k]-v)/pscale) for k,v in reference['potentials'].items()}
        current_scale=max(abs(reference['source_current_a']),reference['intensity_scale']*max(reference['width'],reference['height']))
        reaction=max(abs(q['fixed_boundary_original_reaction_current_a'][k]-v)/current_scale for k,v in reference['fixed_reaction_current_a'].items())
        discrete=max(abs(q['fixed_boundary_reaction_current_a'][k]-v)/current_scale for k,v in reference['fixed_reaction_current_a'].items())
        flux_scale=reference['field_scale']*max(reference['width'],reference['height'])
        flux=max(abs(q['boundary_original_normal_flux_wb_per_m'][k]-v)/flux_scale for k,v in reference['boundary_normal_flux_wb_per_m'].items())
        ampere=abs(q['original_field_ampere_balance_a'])/current_scale;source=abs(q['total_source_current_a']-reference['source_current_a'])/current_scale
        path=out/(name+'.json');path.write_text(json.dumps(case.to_dict(),indent=2)+'\n');assert PlanarRecoilCase.from_dict(json.loads(path.read_text())).to_dict()==case.to_dict();preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        row=dict(name=name,dofs=len(s.az_wb_per_m),az_b_h_errors=errors,potential_scaled_errors=potentials,original_h_reaction_scaled_error=float(reaction),discrete_reaction_scaled_error=float(discrete),original_ampere_scaled_error=float(ampere),boundary_flux_scaled_error=float(flux),source_current_scaled_error=float(source),quantities=q)
        records.append(row)
        with (out/'progress.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
        return s,row
    def exact_error(row):return max(*row['az_b_h_errors'],*row['potential_scaled_errors'].values(),*[row[k] for k in ('original_h_reaction_scaled_error','discrete_reaction_scaled_error','original_ampere_scaled_error','boundary_flux_scaled_error','source_current_scaled_error')])
    def scaling(key,solution,factor):
        value=solution.az_relative_to_reference_wb_per_m/factor
        if key not in pairs:pairs[key]=value.copy();return 0.
        difference=float(np.linalg.norm(value-pairs[key])/np.linalg.norm(pairs[key]));assert difference<1e-10,(key,difference);return difference
    for family,factory in (('uniform',uniform_remanence),('interface',interface_patch),('layered',layered_remanence)):
        for order in (1,2):
            for scale in (.5,2.):
                for mu in (1.,7.):
                    for motion in (0,1):
                        sign=1. if motion==0 else -1.;name=f'{family}-p{order}-s{scale}-mu{mu}-motion{motion}'
                        case,reference=factory(order=order,scale=scale,mu_scale=mu,angle=motion*.7,shift=(0.,0.) if motion==0 else (-.25,.125),amplitude=sign,offset=.002)
                        solution,row=run(name,case,reference);error=exact_error(row);assert error<1e-10,(name,error);maximum_exact=max(maximum_exact,error);counts[family]+=1
                        maximum_scaling=max(maximum_scaling,scaling((family,order),solution,sign*scale))
    for concave in (False,True):
        for scale in (.5,2.):
            for mu in (1.,7.):
                for motion in (0,1):
                    sign=1. if motion==0 else -1.;name=f'quadratic-p2-concave{int(concave)}-s{scale}-mu{mu}-motion{motion}'
                    case,reference=quadratic_current(concave=concave,scale=scale,mu_scale=mu,angle=motion*.7,shift=(-.25,.125),amplitude=sign)
                    solution,row=run(name,case,reference);error=exact_error(row);assert error<1e-10,(name,error);maximum_exact=max(maximum_exact,error);counts['quadratic']+=1
                    maximum_scaling=max(maximum_scaling,scaling(('quadratic',concave),solution,sign*scale**2))
    for concave in (False,True):
        for scale in (.5,2.):
            for mu in (1.,7.):
                previous=None;rows=[];sign=-1. if scale==.5 else 1.
                for n in (8,16,64):
                    name=f'refinement-p1-n{n}-concave{int(concave)}-s{scale}-mu{mu}'
                    case,reference=quadratic_current(order=1,n=n,concave=concave,scale=scale,mu_scale=mu,angle=.7,shift=(-.25,.125),amplitude=sign)
                    solution,row=run(name,case,reference);errors=np.array(row['az_b_h_errors']+[max(row['potential_scaled_errors'].values()),row['original_h_reaction_scaled_error']])
                    if previous is not None:assert np.all(errors<previous),(name,errors.tolist(),previous.tolist())
                    previous=errors;rows.append(dict(n=n,errors=errors.tolist()));counts['refinement']+=1
                    maximum_scaling=max(maximum_scaling,scaling(('refinement',concave,n),solution,sign*scale**2))
                limits=[1e-3,2e-2,2e-2,1e-3,2e-2];assert np.all(previous<limits),(name,previous.tolist(),limits)
                convergence.append(dict(concave=concave,scale=scale,mu_scale=mu,rows=rows,limits=limits))
    for order in (1,2):
        for offset in (0.,.125):
            for angle in (0.,.7):
                name=f'zero-p{order}-offset{offset}-angle{angle}';case,_=uniform_remanence(order=order,amplitude=0.,offset=offset,angle=angle);s=solve_planar_recoil(case);q=planar_recoil_quantities(s)
                np.testing.assert_array_equal(s.az_wb_per_m,offset);np.testing.assert_array_equal(s.az_relative_to_reference_wb_per_m,0.)
                assert q['b_quadratic_j_per_m']==q['constitutive_potential_h0_j_per_m']==q['remanent_reference_constant_j_per_m']==0.
                path=out/(name+'.json');path.write_text(json.dumps(case.to_dict(),indent=2)+'\n');preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();records.append(dict(name=name,quantities=q,zero_fields=True));counts['zero']+=1
    assert counts==dict(uniform=16,interface=16,layered=16,quadratic=16,refinement=24,zero=8) and len(records)==96 and fingerprints()==before
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    result=dict(status='PASS',cases=len(records),case_counts=counts,max_exact_error=maximum_exact,max_coefficient_scaling_error=maximum_scaling,refinement_families=convergence,records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='Synthetic linear recoil patches and current polynomial. Original H includes remanence subtraction. Field errors, declared-reference constitutive potentials, current/reaction and flux are separate. No absolute magnet internal energy or legacy comparison.')
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()

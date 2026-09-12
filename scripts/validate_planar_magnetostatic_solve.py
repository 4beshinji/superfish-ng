# SPDX-License-Identifier: Apache-2.0
"""Planar magnetic analytical Az/B/H, circulation, normal flux and energy."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.planar_magnetostatic_reference import layered_gap,manufactured_quadratic,rectangular_current
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic,planar_magnetostatic_quantities


REFERENCE_CACHE={}


def field_errors(solution,exact,rectangle=None):
    mesh=solution.case.partition.mesh;vertices=mesh.points_xy_m[mesh.triangles];cells=np.arange(len(vertices))
    jac=(vertices[:,1:]-vertices[:,:1]).transpose(0,2,1);det=np.linalg.det(jac)
    g,w=np.polynomial.legendre.leggauss(4);g=(g+1)/2;w=w/2
    numerator=np.zeros(3);denominator=np.zeros(3);truncation=np.zeros(3)
    for ix,(x,wx) in enumerate(zip(g,w)):
        for it,(t,wt) in enumerate(zip(g,w)):
            y=(1-x)*t;bary=np.array([1-x-y,x,y]);points=np.einsum('i,tij->tj',bary,vertices);weight=det*wx*wt*(1-x)
            actual=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)))
            if rectangle is None:reference=exact['fields'](points);lower=reference
            else:
                n,scale,mu=rectangle;key=n,ix,it;factors=(mu*scale**2,mu*scale,scale)
                if key not in REFERENCE_CACHE:
                    high=exact['fields'](points,4096);low=exact['fields'](points,2048)
                    REFERENCE_CACHE[key]=(points/scale,tuple(a/b for a,b in zip(high,factors)),tuple(a/b for a,b in zip(low,factors)))
                saved_points,high,low=REFERENCE_CACHE[key];np.testing.assert_array_equal(saved_points,points/scale)
                reference=tuple(a*b for a,b in zip(high,factors));lower=tuple(a*b for a,b in zip(low,factors))
            values=(actual['Az_Wb_per_m'],np.column_stack((actual['Bx_T'],actual['By_T'])),np.column_stack((actual['Hx_A_per_m'],actual['Hy_A_per_m'])))
            for i,(value,ref,coarse) in enumerate(zip(values,reference,lower)):
                delta=(value-ref)**2;power=ref**2;difference=(ref-coarse)**2
                numerator[i]+=weight@(delta if i==0 else delta.sum(axis=1));denominator[i]+=weight@(power if i==0 else power.sum(axis=1));truncation[i]+=weight@(difference if i==0 else difference.sum(axis=1))
    return np.sqrt(numerator/denominator).tolist(),np.sqrt(truncation/denominator).tolist()


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];preserved={};pairs={};convergence=[]
    maximum_exact=maximum_shift=maximum_scale=maximum_flux=0.;maximum_truncation=np.zeros(3);layered=manufactured=current=0
    def run(name,case,exact,rectangle=None):
        solution=solve_planar_magnetostatic(case);q=planar_magnetostatic_quantities(solution);errors,truncation=field_errors(solution,exact,rectangle)
        energy=float(abs(q['energy_j_per_m']/exact['energy_j_per_m']-1));current_scale=max(abs(exact.get('source_current_a',0.)),sum(abs(v) for v in exact['fixed_reaction_current_a'].values()))
        reaction=max(abs(q['fixed_boundary_reaction_current_a'][name]-value)/current_scale for name,value in exact['fixed_reaction_current_a'].items())
        surface=max(abs(q['fixed_boundary_original_reaction_current_a'][name]-value)/current_scale for name,value in exact['fixed_reaction_current_a'].items())
        path=out/(name+'.json');path.write_text(json.dumps(case.to_dict(),indent=2)+'\n');assert PlanarMagnetostaticCase.from_dict(json.loads(path.read_text())).to_dict()==case.to_dict()
        preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        row=dict(name=name,dofs=len(solution.az_wb_per_m),az_b_h_l2_relative_errors=errors,reference_az_b_h_truncation_difference=truncation,
            energy_relative_error=energy,constraint_reaction_scaled_error=float(reaction),original_h_circulation_scaled_error=float(surface),quantities=q)
        records.append(row)
        with (out/'progress.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
        return solution,row
    motions=((None,(0.,0.),-.0002),(np.array([[.6,-.8],[.8,.6]]),(-.5,.25),.0022))
    for order in (1,2):
        for scale in (.5,2.):
            for mu in (1.,7.):
                for az_difference in (-.0025,.0025):
                    for motion,(rotation,shift,offset) in enumerate(motions):
                        name=f'layer-p{order}-s{scale}-mu{mu}-az{az_difference}-motion{motion}'
                        case,exact=layered_gap(order=order,scale=scale,mu_scale=mu,az_difference=az_difference,rotation=rotation,shift=shift,offset=offset)
                        solution,row=run(name,case,exact);q=row['quantities'];layered+=1
                        errors=row['az_b_h_l2_relative_errors']+[row['energy_relative_error'],row['constraint_reaction_scaled_error'],row['original_h_circulation_scaled_error']]
                        errors += [abs(q['region_energy_j_per_m'][k]/v-1) for k,v in exact['region_energy_j_per_m'].items()]
                        flux_error=max(abs(q['boundary_original_normal_flux_wb_per_m'][k]-v) for k,v in exact['boundary_normal_flux_wb_per_m'].items())/abs(az_difference)
                        errors.append(flux_error);maximum_flux=max(maximum_flux,flux_error)
                        maximum_exact=max(maximum_exact,*errors);assert max(errors)<1e-10,(name,errors)
                        key=order,scale,mu,az_difference
                        if motion==0:pairs[key]=(solution.az_wb_per_m.copy(),q['energy_j_per_m'])
                        else:
                            potential,energy=pairs[key];difference=max(float(np.max(np.abs(solution.az_wb_per_m-potential-.0024)))/.0024,abs(q['energy_j_per_m']/energy-1))
                            maximum_shift=max(maximum_shift,difference);assert difference<1e-10,(name,difference)
                        scale_key=order,mu,az_difference,motion,'energy'
                        if scale==.5:pairs[scale_key]=q['energy_j_per_m']
                        else:
                            difference=abs(q['energy_j_per_m']/pairs[scale_key]-1)
                            maximum_scale=max(maximum_scale,difference);assert difference<1e-10,(name,difference)
    for concave in (False,True):
        for direction in ('x','y'):
            for scale in (.5,2.):
                for amplitude in (-1.,1.):
                    for motion,(rotation,shift,_) in enumerate(motions):
                        name=f'manufactured-concave{int(concave)}-{direction}-s{scale}-a{amplitude}-motion{motion}'
                        case,exact=manufactured_quadratic(concave=concave,direction=direction,scale=scale,amplitude=amplitude,rotation=rotation,shift=shift)
                        solution,row=run(name,case,exact);q=row['quantities'];manufactured+=1
                        errors=row['az_b_h_l2_relative_errors']+[row['energy_relative_error'],row['constraint_reaction_scaled_error'],row['original_h_circulation_scaled_error'],
                            abs(q['total_source_current_a']/exact['source_current_a']-1),abs(q['original_field_ampere_balance_a']/exact['source_current_a'])]
                        errors.append(q['divergence_free_flux_relative_error']);maximum_exact=max(maximum_exact,*errors);assert max(errors)<1e-10,(name,errors)
    limits={1:[.0005,.015,.015,.0005,.018],2:[1e-5,.0005,.0005,5e-6,.002]}
    for order,levels in ((1,(32,64,128)),(2,(16,32,80))):
        for scale in (.5,2.):
            for mu in (1.,7.):
                rows=[];previous=None
                for n in levels:
                    name=f'current-p{order}-n{n}-s{scale}-mu{mu}'
                    case,exact=rectangular_current(order=order,n=n,scale=scale,mu_r=mu,source_curvature=mu)
                    solution,row=run(name,case,exact,rectangle=(n,scale,mu));q=row['quantities'];current+=1
                    errors=np.array(row['az_b_h_l2_relative_errors']+[row['energy_relative_error'],row['original_h_circulation_scaled_error']])
                    assert row['constraint_reaction_scaled_error']<1e-10,(name,row['constraint_reaction_scaled_error'])
                    truncation=row['reference_az_b_h_truncation_difference'];maximum_truncation=np.maximum(maximum_truncation,truncation)
                    assert max(truncation)<1e-7,(name,truncation)
                    if previous is not None:assert np.all(errors<previous),(name,errors.tolist(),previous.tolist())
                    previous=errors;rows.append(dict(n=n,errors=errors.tolist()))
                    scale_key=order,n,mu,'current'
                    if scale==.5:pairs[scale_key]=(solution.az_wb_per_m.copy(),q['energy_j_per_m'])
                    else:
                        potential,energy=pairs[scale_key];factor=scale/.5
                        difference=max(float(np.linalg.norm(solution.az_wb_per_m-factor**2*potential)/np.linalg.norm(solution.az_wb_per_m)),abs(q['energy_j_per_m']/(energy*factor**4)-1))
                        maximum_scale=max(maximum_scale,difference);assert difference<1e-10,(name,difference)
                    mu_key=order,n,scale,'fixed-current'
                    if mu==1.:pairs[mu_key]=(solution.az_wb_per_m.copy(),q['energy_j_per_m'],q['total_source_current_a'])
                    else:
                        old_az,old_energy,old_current=pairs[mu_key]
                        difference=max(float(np.linalg.norm(solution.az_wb_per_m/mu-old_az)/np.linalg.norm(old_az)),abs(q['energy_j_per_m']/(mu*old_energy)-1),abs(q['total_source_current_a']/old_current-1))
                        maximum_scale=max(maximum_scale,difference);assert difference<1e-10,(name,difference)
                assert np.all(previous<limits[order]),(name,previous.tolist(),limits[order])
                convergence.append(dict(order=order,scale=scale,mu_r=mu,rows=rows,final_limits=limits[order]))
    assert layered==32 and manufactured==32 and current==24 and len(records)==88
    assert fingerprints()==before
    for path,digest in preserved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',cases=len(records),layered_cases=layered,manufactured_cases=manufactured,current_cases=current,
        max_exact_relative_error=maximum_exact,max_gauge_rigid_difference=maximum_shift,max_scale_difference=maximum_scale,
        max_reference_az_b_h_truncation_difference=maximum_truncation.tolist(),reference_truncation_limit=1e-7,
        max_boundary_flux_relative_error=maximum_flux,refinement_families=convergence,case_sha256=preserved,source_sha256=before,
        seconds=time.monotonic()-start,records=records,
        interpretation='Synthetic finite-domain magnetostatics per metre of uniform extrusion. Original-cell Az/B/H and boundary H circulation are tested separately. Fourier 2048/4096 differences are sampled truncation diagnostics, not rigorous error bounds. Fixed current source in rectangle; Az and B scale with mu, H is invariant. No legacy or external solver reference.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','records','case_sha256')},indent=2))


if __name__=='__main__':main()

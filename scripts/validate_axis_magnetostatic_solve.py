# SPDX-License-Identifier: Apache-2.0
"""Independent axis magnetic fields, current, full energy and flux refinement."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.axis_magnetostatic_reference import uniform_field,cylinder_current,layered_current
from superfish_ng.axis_magnetostatic import AxisMagnetostaticCase,solve_axis_magnetostatic,axis_magnetostatic_quantities
from superfish_ng.constants import TAU


def field_errors(solution,exact):
    mesh=solution.case.partition.mesh;vertices=mesh.points_rz_m[mesh.triangles];cells=np.arange(len(vertices))
    u=vertices[:,1]-vertices[:,0];v=vertices[:,2]-vertices[:,0];det=u[:,0]*v[:,1]-u[:,1]*v[:,0]
    gauss,weights=np.polynomial.legendre.leggauss(4);gauss=(gauss+1)/2;weights=weights/2
    numerator=np.zeros(4);denominator=np.zeros(4)
    for x,wx in zip(gauss,weights):
        for t,wt in zip(gauss,weights):
            y=(1-x)*t;bary=np.tile([1-x-y,x,y],(len(cells),1));points=np.einsum('qi,qij->qj',bary,vertices)
            a,aphi,b,h=exact['fields'](points);field=solution.fields_in_cells(cells,bary)
            actual=(field['Aphi_over_r_T'],field['Aphi_Wb_per_m'],np.column_stack((field['Br_T'],field['Bz_T'])),np.column_stack((field['Hr_A_per_m'],field['Hz_A_per_m'])))
            measure=TAU*points[:,0]*det*wx*wt*(1-x)
            for i,(left,right) in enumerate(zip(actual,(a,aphi,b,h))):
                square=(left-right)**2;reference=right**2
                if square.ndim==2:square=square.sum(axis=1);reference=reference.sum(axis=1)
                numerator[i]+=float(measure@square);denominator[i]+=float(measure@reference)
    assert np.all(denominator>0)
    return np.sqrt(numerator/denominator).tolist()


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];preserved={};pairs={};convergence=[]
    maximum_exact=maximum_scale=maximum_flux=0.;uniform=cylinder=layered=0
    def run(name,case,exact):
        solution=solve_axis_magnetostatic(case);q=axis_magnetostatic_quantities(solution);errors=field_errors(solution,exact)
        energy=abs(q['energy_j']/exact['energy_j']-1);length=float(np.ptp(case.partition.mesh.outer_rz_m[:,1]))
        current_scale=max(abs(exact['source_current_a']),exact['intensity_scale']*length)
        circulation=abs(q['original_field_ampere_balance_a'])/current_scale
        fixed_scale=max([abs(v) for v in exact['fixed_reaction_a_m2'].values()]+[exact['intensity_scale']*case.partition.mesh.volume_m3])
        reaction=max([abs(q['fixed_boundary_reaction_a_m2'][k]-v)/fixed_scale for k,v in exact['fixed_reaction_a_m2'].items()]+[0.])
        original=max([abs(q['fixed_boundary_original_reaction_a_m2'][k]-v)/fixed_scale for k,v in exact['fixed_reaction_a_m2'].items()]+[0.])
        flux=0.
        if exact['boundary_flux_wb'] is not None:
            denominator=max(abs(v) for v in exact['boundary_flux_wb'].values())
            flux=max(abs(q['boundary_original_normal_flux_wb'][k]-v)/denominator for k,v in exact['boundary_flux_wb'].items())
        source=abs(q['total_source_current_a']-exact['source_current_a'])/current_scale
        path=out/(name+'.json');path.write_text(json.dumps(case.to_dict(),indent=2)+'\n');assert AxisMagnetostaticCase.from_dict(json.loads(path.read_text())).to_dict()==case.to_dict()
        preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        row=dict(name=name,dofs=len(solution.aphi_over_r_t),a_aphi_b_h_l2_relative_errors=errors,energy_relative_error=float(energy),
            original_ampere_scaled_error=float(circulation),constraint_reaction_scaled_error=float(reaction),original_weighted_h_scaled_error=float(original),
            boundary_flux_relative_error=float(flux),source_current_scaled_error=float(source),quantities=q)
        records.append(row)
        with (out/'progress.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
        return solution,row
    def exact_check(row):
        return max(*row['a_aphi_b_h_l2_relative_errors'],*[row[k] for k in ('energy_relative_error','original_ampere_scaled_error','constraint_reaction_scaled_error','original_weighted_h_scaled_error','boundary_flux_relative_error','source_current_scaled_error')])
    def scaling(key,solution,normalized_energy,coefficient_factor):
        a=solution.aphi_over_r_t/coefficient_factor
        if key not in pairs:pairs[key]=(a.copy(),normalized_energy);return 0.
        old,energy=pairs[key];difference=max(float(np.linalg.norm(a-old)/np.linalg.norm(old)),abs(normalized_energy/energy-1));assert difference<1e-10,(key,difference)
        return difference
    for order in (1,2):
        for scale in (.5,2.):
            for mu in (1.,7.):
                for sign in (-1.,1.):
                    for boundary in ('fixed','tangential'):
                        name=f'uniform-p{order}-s{scale}-mu{mu}-sign{sign}-{boundary}'
                        case,exact=uniform_field(order=order,scale=scale,mu_r=mu,field_t=sign*.02,boundary=boundary,shift=0. if boundary=='fixed' else -.25)
                        solution,row=run(name,case,exact);error=exact_check(row);maximum_exact=max(maximum_exact,error);assert error<1e-10,(name,error)
                        maximum_scale=max(maximum_scale,scaling(('uniform',order,sign,boundary),solution,row['quantities']['energy_j']*mu/scale**3,1.));uniform+=1
    for order in (1,2):
        for holes in (0,2):
            for scale in (.5,2.):
                for mu in (1.,7.):
                    for sign in (-1.,1.):
                        name=f'cylinder-p{order}-holes{holes}-s{scale}-mu{mu}-sign{sign}'
                        case,exact=cylinder_current(order=order,holes=holes,scale=scale,mu_r=mu,current_density=sign*2e5,outer_h=sign*300*scale,boundary='fixed' if holes else 'tangential',shift=-.25)
                        solution,row=run(name,case,exact);error=exact_check(row);maximum_exact=max(maximum_exact,error);assert error<1e-10,(name,error)
                        maximum_scale=max(maximum_scale,scaling(('cylinder',order,holes,sign),solution,row['quantities']['energy_j']/(mu*scale**5),mu*scale));cylinder+=1
    limits={1:[1e-3,1e-3,2e-2,2e-2,1e-3,2e-2],2:[1e-5,1e-5,1e-3,1e-3,1e-5,2e-3]}
    for order,levels in ((1,(16,32,64)),(2,(8,16,32))):
        for scale in (.5,2.):
            for mu in (1.,7.):
                rows=[];previous=None
                for n in levels:
                    name=f'layer-p{order}-n{n}-s{scale}-mu{mu}'
                    case,exact=layered_current(order=order,n=n,scale=scale,mu_scale=mu,shift=-.25)
                    solution,row=run(name,case,exact);layered+=1
                    errors=np.array(row['a_aphi_b_h_l2_relative_errors']+[row['energy_relative_error'],row['original_ampere_scaled_error']])
                    if previous is not None:assert np.all(errors<previous),(name,errors.tolist(),previous.tolist())
                    previous=errors;rows.append(dict(n=n,errors=errors.tolist(),boundary_flux_relative_error=row['boundary_flux_relative_error']))
                    maximum_scale=max(maximum_scale,scaling(('layer',order,n),solution,row['quantities']['energy_j']/(mu*scale**5),mu*scale))
                assert np.all(previous<limits[order]),(name,previous.tolist(),limits[order])
                assert row['boundary_flux_relative_error']<({1:2e-3,2:2e-5}[order]),(name,row['boundary_flux_relative_error'])
                maximum_flux=max(maximum_flux,row['boundary_flux_relative_error']);convergence.append(dict(order=order,scale=scale,mu_scale=mu,rows=rows,final_limits=limits[order]))
    assert uniform==32 and cylinder==32 and layered==24 and len(records)==88 and fingerprints()==before
    for path,digest in preserved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',cases=len(records),uniform_cases=uniform,cylinder_cases=cylinder,layered_cases=layered,
        max_exact_relative_error=maximum_exact,max_scale_difference=maximum_scale,max_finest_boundary_flux_relative_error=maximum_flux,
        refinement_families=convergence,records=records,source_sha256=before,case_sha256=preserved,seconds=time.monotonic()-start,
        interpretation='Synthetic finite axis-connected magnetic domains. Original a/Aphi/B/H, full J energy, Wb flux and H circulation are evaluated separately. Jphi current[A] is distinct from reaction[A m^2]. Analytic cylindrical and piecewise radial fields are verification only; no legacy, external solver or FEM correction.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256','case_sha256')})


if __name__=='__main__':main()

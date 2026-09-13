# SPDX-License-Identifier: Apache-2.0
"""Independent positive-radius recoil fields, gauge, potentials and refinement."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.off_axis_recoil_reference import uniform_remanence,interface_patch,blocked_flux,annular_current,layered_remanence
from superfish_ng.off_axis_recoil import solve_off_axis_recoil,off_axis_recoil_quantities,OffAxisRecoilCase
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
            actual=[np.asarray(f['psi_Wb'])[:,None],np.asarray(f['Aphi_Wb_per_m'])[:,None],np.column_stack((f['Br_T'],f['Bz_T'])),np.column_stack((f['Hr_A_per_m'],f['Hz_A_per_m']))]
            expected=[a[:,None],ap[:,None],b,h]
            for k,(v,e) in enumerate(zip(actual,expected)):
                numerator[k]+=float(measure@np.sum((v-e)**2,axis=1));denominator[k]+=float(measure@np.sum(e**2,axis=1))
    radius=p.mesh.outer_rz_m[:,0].max()
    # Declared field scales keep arbitrary reference psi out of the error denominator.
    denominator[0]=volume*reference['potential_scale']**2;denominator[1]=volume*(reference['potential_scale']/radius)**2
    if denominator[2]==0.:denominator[2]=volume*reference['field_scale']**2
    if denominator[3]==0.:denominator[3]=volume*reference['intensity_scale']**2
    relative=np.sqrt(numerator/np.where(denominator,denominator,1.)).tolist();q=off_axis_recoil_quantities(solution)
    potential_scale=sum(abs(v) for v in reference['potentials'].values()) or 1.
    potential=max(abs(q[name]-value)/potential_scale for name,value in reference['potentials'].items())
    edges=p.mesh.points_rz_m[p.mesh.boundary_edges];perimeter=float(np.linalg.norm(edges[:,1]-edges[:,0],axis=1).sum());radius=p.mesh.outer_rz_m[:,0].max()
    current_scale=perimeter*reference['intensity_scale']+abs(reference['source_current_a']) or 1.
    ampere=abs(q['original_field_ampere_balance_a'])/current_scale
    reaction_scale=TAU*perimeter*reference['intensity_scale'] or 1.
    reaction=max((abs(q['fixed_boundary_original_reaction_a'][name]-value)/reaction_scale for name,value in reference['fixed_reaction_a'].items()),default=0.)
    flux_scale=TAU*radius**2*reference['field_scale'] or 1.
    flux=max(abs(q['boundary_original_normal_flux_wb'][name]-value)/flux_scale for name,value in reference['boundary_flux_wb'].items())
    assert abs(q['total_source_current_a']-reference['source_current_a'])/current_scale<1e-11
    return [*relative,float(potential),float(ampere),float(reaction)],float(flux),q


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();start=time.monotonic();records=[];preserved={};families=[];pairs={};counts=dict(uniform=0,patch=0,layered=0,blocked=0,current=0,refinement=0,zero=0);maximum_exact=maximum_covariance=0.
    def save(name,case,solution,reference,kind):
        values,flux,q=errors(solution,reference);record=dict(name=name,kind=kind,element_order=case.element_order,errors=values,flux_relative_error=flux,quantities=q)
        # Keep reusable Case input separate from analytical diagnostics in report.json.
        path=out/(name+'.json');path.write_text(json.dumps(case.to_dict(),indent=2)+'\n');preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();records.append(record);counts[kind]+=1
        assert OffAxisRecoilCase.from_dict(json.loads(path.read_text())).to_dict()==case.to_dict()
        (out/'progress.json').write_text(json.dumps(dict(completed=len(records),last=name),indent=2)+'\n');print('DONE',name,values,flux,flush=True)
        return values,flux
    for kind,factory in (('uniform',uniform_remanence),('patch',interface_patch),('layered',layered_remanence),('blocked',blocked_flux)):
        for order in ((1,2) if kind=='blocked' else (2,)):
            for boundary in ('fixed','tangential'):
                for scale in (.5,2.):
                    for mu_scale in (1.,7.):
                        amplitude=1. if mu_scale==1. else -1.;shift=0. if mu_scale==1. else -.25;reference_psi=0. if mu_scale==1. else .125
                        holes=1 if kind in ('uniform','patch') else 0;name=f'{kind}-p{order}-{boundary}-h{holes}-s{scale}-mu{mu_scale}'
                        case,reference=factory(order,n=2,scale=scale,mu_scale=mu_scale,amplitude=amplitude,boundary=boundary,shift=shift,holes=holes,reference_psi=reference_psi);solution=solve_off_axis_recoil(case)
                        values,flux=save(name,case,solution,reference,kind);assert max(*values,flux)<1e-10;maximum_exact=max(maximum_exact,*values,flux)
                        key=kind,order,boundary;normalized=solution.psi_relative_to_reference_wb/(amplitude*scale**2)
                        if key not in pairs:pairs[key]=normalized.copy()
                        else:
                            physical_scale=reference['potential_scale']/scale**2*np.sqrt(len(normalized))
                            difference=float(np.linalg.norm(normalized-pairs[key])/physical_scale);assert difference<1e-10;maximum_covariance=max(maximum_covariance,difference)
    for geometry,factory in (('current',annular_current),('uniform',uniform_remanence),('layered',layered_remanence)):
        for order in ((1,2) if geometry=='current' else (1,)):
            levels=(8,16,32) if order==1 else (4,8,16);limits=[1e-3,1e-3,.02,.02,1e-3,.02,.02] if order==1 else [2e-5,2e-5,.001,.001,2e-5,.002,.002]
            for scale in (.5,2.):
                for mu_scale in (1.,7.):
                    rows=[]
                    for n in levels:
                        amplitude=1. if mu_scale==1. else -1.;shift=0. if mu_scale==1. else -.25;reference_psi=0. if mu_scale==1. else .125
                        name=f'{geometry}-refinement-p{order}-n{n}-s{scale}-mu{mu_scale}'
                        case,reference=factory(order,n=n,scale=scale,mu_scale=mu_scale,amplitude=amplitude,shift=shift,holes=1 if geometry=='current' else 0,reference_psi=reference_psi)
                        solution=solve_off_axis_recoil(case);values,flux=save(name,case,solution,reference,'current' if geometry=='current' else 'refinement');rows.append(dict(n=n,errors=values,flux_relative_error=flux))
                        if len(rows)>1:assert all(a<b for a,b in zip(values,rows[-2]['errors']))
                    assert all(a<b for a,b in zip(values,limits)) and flux<(2e-3 if order==1 else 2e-5)
                    families.append(dict(geometry=geometry,order=order,scale=scale,mu_scale=mu_scale,rows=rows,limits=limits))
    for order in (1,2):
        for boundary in ('fixed','tangential'):
            for reference_psi in (0.,.125):
                name=f'zero-p{order}-{boundary}-reference{reference_psi}';case,reference=uniform_remanence(order,n=1,amplitude=0.,boundary=boundary,reference_psi=reference_psi);solution=solve_off_axis_recoil(case);values,flux=save(name,case,solution,reference,'zero')
                np.testing.assert_array_equal(solution.psi_relative_to_reference_wb,0.);np.testing.assert_array_equal(solution.psi_wb,reference_psi)
                assert values[0]==0. and max(*values[2:],flux)==0.
                # Aphi=C/r is nonzero even with exactly zero B/H. Independent
                # three-term radius sums have binary64 rounding differences.
                radius_min=case.partition.mesh.points_rz_m[:,0].min()
                rounding_bound=32*np.finfo(float).eps*abs(reference_psi)/radius_min*np.sqrt(case.partition.mesh.volume_m3)
                assert values[1]<=rounding_bound
    assert len(records)==96 and counts==dict(uniform=8,patch=8,layered=8,blocked=16,current=24,refinement=24,zero=8) and fingerprints()==before
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',cases=len(records),case_counts=counts,max_exact_error=maximum_exact,max_coefficient_scaling_error=maximum_covariance,refinement_families=families,
        records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='original psi/Aphi/B/H, reference-aware constitutive potentials[J], original H circulation/reaction and normal B flux[Wb] checked separately; declared psi scale excludes arbitrary gauge offset; no excluded-axis absolute flux; synthetic linear recoil materials')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256','refinement_families')})


if __name__=='__main__':main()

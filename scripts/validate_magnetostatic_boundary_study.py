# SPDX-License-Identifier: Apache-2.0
"""Separate fixed-current boundary-distance effects from magnetic FEM error."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.magnetostatic_boundary_reference import current_slab,current_cylinder
from superfish_ng.constants import TAU
from superfish_ng.axis_magnetostatic import AxisMagnetostaticCase,solve_axis_magnetostatic,axis_magnetostatic_quantities
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic,planar_magnetostatic_quantities
from superfish_ng.axis_magnetostatic_saved import save_axis_magnetostatic_run,export_axis_magnetostatic_probe,_snapshot
from superfish_ng.planar_magnetostatic_saved import save_planar_magnetostatic_run,export_planar_magnetostatic_probe


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def field_errors(solution,exact,axis):
    mesh=solution.case.partition.mesh;vertices=(mesh.points_rz_m if axis else mesh.points_xy_m)[mesh.triangles];cells=np.arange(len(vertices));det=np.linalg.det((vertices[:,1:]-vertices[:,:1]).transpose(0,2,1))
    g,w=np.polynomial.legendre.leggauss(4);g=(g+1)/2;w=w/2;numerator=np.zeros(3);denominator=np.zeros(3)
    components=('r','z') if axis else ('x','y');aphi_error=aphi_norm=0.
    for x,wx in zip(g,w):
        for t,wt in zip(g,w):
            y=(1-x)*t;bary=np.array([1-x-y,x,y]);points=np.einsum('i,tij->tj',bary,vertices);weight=det*wx*wt*(1-x)
            if axis:weight=weight*TAU*points[:,0]
            actual=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)));reference=exact['fields'](points)
            values=(actual['Aphi_over_r_T' if axis else 'Az_Wb_per_m'],np.column_stack([actual[f'B{c}_T'] for c in components]),np.column_stack([actual[f'H{c}_A_per_m'] for c in components]))
            if axis:
                aphi_error+=weight@((points[:,0]*(values[0]-reference[0]))**2);aphi_norm+=weight@((points[:,0]*reference[0])**2)
            for i,(value,ref) in enumerate(zip(values,reference)):
                delta=(value-ref)**2;power=ref**2;numerator[i]+=weight@(delta if i==0 else delta.sum(axis=1));denominator[i]+=weight@(power if i==0 else power.sum(axis=1))
    return np.sqrt(numerator/denominator).tolist(),float(np.sqrt(aphi_error/aphi_norm)) if axis else None

def example_cli(out):
    commands=[];hashes={};env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1')
    def cli(args):
        result=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,args)],cwd=ROOT,env=env,capture_output=True,text=True);commands.append(dict(arguments=list(map(str,args)),returncode=result.returncode))
        (out/f'example-cli-{len(commands):02d}.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stderr;return result.stdout
    for axis in (False,True):
        label='axis' if axis else 'planar';source=ROOT/'examples/magnetostatic'/('axis_current_cylinder.json' if axis else 'planar_current_slab.json');case,reference=(current_cylinder(n=4,outer_ratio=4.) if axis else current_slab(n=4));assert json.loads(source.read_text())==case.to_dict()
        solve=solve_axis_magnetostatic if axis else solve_planar_magnetostatic;save=save_axis_magnetostatic_run if axis else save_planar_magnetostatic_run;probe=export_axis_magnetostatic_probe if axis else export_planar_magnetostatic_probe
        api=out/f'{label}-api';binary=out/f'{label}-cli';solution=solve(case);result=save(case,solution,api);suffix='axis-magnetostatic' if axis else 'planar-magnetostatic'
        assert json.loads(cli(['solve-'+suffix,source,'--out',binary]))==result;assert json.loads(cli(['replay-'+suffix,binary]))==result;assert _snapshot(api)==_snapshot(binary)

        mesh=case.partition.mesh;points=(mesh.points_rz_m if axis else mesh.points_xy_m)[mesh.triangles[[0,-1]]].mean(axis=1);point_file=out/f'{label}-points.json';point_file.write_text(json.dumps(points.tolist())+'\n')
        expected=probe(api,out/f'{label}-api-probe.json',points);target=out/f'{label}-cli-probe.json';cli(['probe-'+suffix,binary,'--points',point_file,'--out',target]);assert json.loads(target.read_text())==expected
        for directory in (api,binary):hashes.update({str((directory/name).relative_to(out)):hashlib.sha256(data).hexdigest() for name,data in _snapshot(directory).items()})
    assert len(commands)==6 and len(hashes)==20
    for path,digest in hashes.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    return dict(examples=2,native_saves=4,native_files_unchanged=20,cli_commands=commands,api_cli_native='five files byte-identical',api_cli_probe='complete JSON identical')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic()
    records=[];families=[];boundary_changes=[];preserved={};scalings={};maximum_scaling=0.
    limits={1:[3e-3,3e-2,3e-2,3e-3,3e-2],2:[2e-5,1e-3,1e-3,2e-5,2e-3]}
    for axis,fixture,solve,quantities in ((False,current_slab,solve_planar_magnetostatic,planar_magnetostatic_quantities),(True,current_cylinder,solve_axis_magnetostatic,axis_magnetostatic_quantities)):
        geometry='axis' if axis else 'planar';energy_key='energy_j' if axis else 'energy_j_per_m';coordinates=('r','z') if axis else ('x','y')
        potential_key='Aphi_over_r_T' if axis else 'Az_Wb_per_m'
        reaction_key='fixed_boundary_reaction_a_m2' if axis else 'fixed_boundary_reaction_current_a'
        original_key='fixed_boundary_original_reaction_a_m2' if axis else 'fixed_boundary_original_reaction_current_a'
        for order,levels in ((1,(8,16,32)),(2,(4,8,32))):
            for mu in (1.,7.):
                for sign in (-1.,1.):
                    previous_boundary=None
                    for outer in (2.,4.,8.):
                        previous=None;previous_aphi=None;rows=[]
                        for n in levels:
                            name=f'{geometry}-p{order}-mu{mu}-sign{sign}-outer{outer}-n{n}'
                            case,exact=fixture(order,n,outer,mu,sign);solution=solve(case);q=quantities(solution);errors,aphi_error=field_errors(solution,exact,axis)
                            errors += [abs(q[energy_key]/exact['energy']-1),abs(q[original_key]['fixed']/exact['fixed_reaction']-1)]
                            reaction=abs(q[reaction_key]['fixed']/exact['fixed_reaction']-1)
                            assert reaction<1e-10 and abs(q['total_source_current_a']/exact['source_current']-1)<1e-10,(name,reaction)
                            values=np.asarray(errors)
                            if previous is not None:
                                active=np.asarray(previous)>1e-10
                                assert np.all(values[active]<np.asarray(previous)[active]) and np.all(values[~active]<1e-10),(name,errors,previous)
                            if not axis and order==2:assert max(errors)<1e-10,(name,errors)
                            if previous_aphi is not None:
                                assert aphi_error<(previous_aphi if previous_aphi>1e-10 else 1e-10),(name,aphi_error,previous_aphi)
                            previous=errors;previous_aphi=aphi_error;rows.append(dict(n=n,errors=errors,aphi_relative_error=aphi_error))
                            path=out/(name+'.json');path.write_text(json.dumps(case.to_dict(),indent=2)+'\n')
                            cls=AxisMagnetostaticCase if axis else PlanarMagnetostaticCase;assert cls.from_dict(json.loads(path.read_text())).to_dict()==case.to_dict();preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
                            probe=solution.probe_at(exact['common_points'])['fields'];magnetic=np.column_stack([probe[f'B{c}_T'] for c in coordinates]);intensity=np.column_stack([probe[f'H{c}_A_per_m'] for c in coordinates]);potential=np.array(probe[potential_key])
                            scale_key=axis,order,n,outer,sign
                            if mu==1.:scalings[scale_key]=(potential,magnetic,intensity,q[energy_key])
                            else:
                                old_a,old_b,old_h,old_u=scalings[scale_key]
                                difference=max(np.linalg.norm(potential/mu-old_a)/np.linalg.norm(old_a),np.linalg.norm(magnetic/mu-old_b)/np.linalg.norm(old_b),np.linalg.norm(intensity-old_h)/np.linalg.norm(old_h),abs(q[energy_key]/(mu*old_u)-1))
                                maximum_scaling=max(maximum_scaling,float(difference));assert difference<1e-10,(name,difference)
                            remote=None
                            if axis:
                                infinity=exact['infinite_fields'](exact['common_points']);finite=exact['fields'](exact['common_points'])
                                # The first two declared probe points lie in the fixed current core.
                                remote=dict(infinite_radius_energy_j=exact['infinite_energy'],finite_radius_energy_j=exact['energy'],
                                    analytic_energy_relative_change=exact['energy']/exact['infinite_energy']-1,background_h_a_per_m=exact['background_h'],
                                    common_source_points=exact['common_points'][:2].tolist(),
                                    common_source_H_fem_vs_finite_scaled_error=float(np.max(abs(intensity[:2]-finite[2][:2]))/exact['intensity_scale']),
                                    common_source_H_fem_vs_infinite_scaled_error=float(np.max(abs(intensity[:2]-infinity[2][:2]))/exact['intensity_scale']),
                                    analytic_finite_vs_infinite_H_scaled_difference=abs(exact['background_h'])/exact['intensity_scale'])
                            row=dict(name=name,geometry=geometry,order=order,mu_r=mu,sign=sign,outer_ratio=outer,n=n,
                                potential_b_h_energy_surface_relative_errors=errors,aphi_relative_error=aphi_error,reaction_relative_error=reaction,
                                quantities=q,common_points=exact['common_points'].tolist(),common_probe=probe,radial_infinite_reference=remote)
                            records.append(row)
                            with (out/'progress.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
                        assert np.all(np.asarray(previous)<limits[order]),(name,previous,limits[order])
                        if axis:assert aphi_error<limits[order][0],(name,aphi_error,limits[order][0])
                        families.append(dict(geometry=geometry,order=order,mu_r=mu,sign=sign,outer_ratio=outer,rows=rows,final_limits=limits[order]))
                        if previous_boundary is not None:
                            old_a,old_b,old_h,old_ref=previous_boundary
                            if axis:
                                h_shift=old_ref['boundary_background_h_shift'](exact['outer_distance_m']);mu_absolute=exact['field_scale']/exact['intensity_scale'];potential_shift=mu_absolute*h_shift/2
                                expected_b=np.zeros_like(magnetic);expected_b[:,1]=mu_absolute*h_shift;expected_h=np.zeros_like(intensity);expected_h[:,1]=h_shift
                            else:
                                potential_shift=old_ref['boundary_potential_shift'](exact['outer_distance_m']);h_shift=0.;expected_b=np.zeros_like(magnetic);expected_h=np.zeros_like(intensity)
                            a_error=float(np.max(abs(potential-old_a-potential_shift))/exact['potential_scale'])
                            b_error=float(np.max(abs(magnetic-old_b-expected_b))/exact['field_scale']);h_error=float(np.max(abs(intensity-old_h-expected_h))/exact['intensity_scale'])
                            tolerance=5e-3 if order==1 else 1e-4;assert max(a_error,b_error,h_error)<tolerance,(name,a_error,b_error,h_error,tolerance)
                            boundary_changes.append(dict(geometry=geometry,order=order,mu_r=mu,sign=sign,from_distance_m=old_ref['outer_distance_m'],to_distance_m=exact['outer_distance_m'],
                                potential_shift=potential_shift,potential_unit='T' if axis else 'Wb/m',analytic_H_shift_a_per_m=h_shift,
                                potential_shift_scaled_error=a_error,B_shift_scaled_error=b_error,H_shift_scaled_error=h_error,limit=tolerance,interpretation=exact['interpretation']))
                        previous_boundary=potential,magnetic,intensity,exact
    examples=example_cli(out);assert len(records)==144 and len(families)==48 and len(boundary_changes)==32
    for path,digest in preserved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    report=dict(status='PASS',cases=len(records),fixed_boundary_refinement_families=len(families),separate_boundary_changes=len(boundary_changes),max_mu_scaling_relative_error=maximum_scaling,
        source_sha256=before,case_sha256=preserved,records=records,refinement_families=families,boundary_changes=boundary_changes,examples=examples,seconds=time.monotonic()-start,
        interpretation='Synthetic fixed-current finite-domain problems. Planar common B/H remains fixed as Az offset and energy grow. Axis fixed outer Aphi/r induces a physical return H proportional to b^-2; its radial-infinite reference has the same finite length and end Ht conditions. Finite-boundary FEM error and remote-boundary effects are separate; no general open-boundary solver or legacy comparison.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('source_sha256','case_sha256','records','refinement_families','boundary_changes')})


if __name__=='__main__':main()

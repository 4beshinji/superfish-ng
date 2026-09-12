# SPDX-License-Identifier: Apache-2.0
"""Separate fixed-charge boundary-distance dependence from FEM refinement."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.electrostatic_boundary_reference import charged_slab,charged_coax
from scripts.electrostatic_reference import parallel_plate as axis_plate
from scripts.planar_electrostatic_reference import parallel_plate as planar_plate
from superfish_ng.constants import TAU
from superfish_ng.electrostatic import AxisymmetricElectrostaticCase,solve_axisymmetric_electrostatic,electrostatic_quantities
from superfish_ng.planar_electrostatic import PlanarElectrostaticCase,solve_planar_electrostatic,planar_electrostatic_quantities
from superfish_ng.electrostatic_saved import save_electrostatic_run,electrostatic_result,export_electrostatic_probe,_snapshot
from superfish_ng.planar_electrostatic_saved import save_planar_electrostatic_run,planar_electrostatic_result,export_planar_electrostatic_probe


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def field_errors(solution,exact,axis):
    mesh=solution.case.partition.mesh;vertices=(mesh.points_rz_m if axis else mesh.points_xy_m)[mesh.triangles];cells=np.arange(len(vertices));det=np.linalg.det((vertices[:,1:]-vertices[:,:1]).transpose(0,2,1))
    g,w=np.polynomial.legendre.leggauss(4);g=(g+1)/2;w=w/2;numerator=np.zeros(3);denominator=np.zeros(3)
    components=('r','z') if axis else ('x','y')
    for x,wx in zip(g,w):
        for t,wt in zip(g,w):
            y=(1-x)*t;bary=np.array([1-x-y,x,y]);points=np.einsum('i,tij->tj',bary,vertices);weight=det*wx*wt*(1-x)
            if axis:weight=weight*TAU*points[:,0]
            actual=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)));reference=exact['fields'](points)
            values=(actual['potential_V'],np.column_stack([actual[f'E{c}_V_per_m'] for c in components]),np.column_stack([actual[f'D{c}_C_per_m2'] for c in components]))
            for i,(value,ref) in enumerate(zip(values,reference)):
                delta=(value-ref)**2;power=ref**2;numerator[i]+=weight@(delta if i==0 else delta.sum(axis=1));denominator[i]+=weight@(power if i==0 else power.sum(axis=1))
    return np.sqrt(numerator/denominator).tolist()


def example_cli(out):
    commands=[];hashes={};env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1')
    def cli(args):
        result=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,args)],cwd=ROOT,env=env,capture_output=True,text=True);commands.append(dict(arguments=list(map(str,args)),returncode=result.returncode))
        (out/f'example-cli-{len(commands):02d}.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stderr;return result.stdout
    for axis in (False,True):
        label='axisymmetric' if axis else 'planar';source=ROOT/'examples/electrostatic'/f'{label}_capacitor.json';case,reference=(axis_plate(n=1) if axis else planar_plate(n=2));assert json.loads(source.read_text())==case.to_dict()
        solve=solve_axisymmetric_electrostatic if axis else solve_planar_electrostatic;save=save_electrostatic_run if axis else save_planar_electrostatic_run;probe=export_electrostatic_probe if axis else export_planar_electrostatic_probe
        api=out/f'{label}-api';binary=out/f'{label}-cli';solution=solve(case);result=save(case,solution,api);suffix='electrostatic' if axis else 'planar-electrostatic'
        assert json.loads(cli(['solve-'+suffix,source,'--out',binary]))==result;assert json.loads(cli(['replay-'+suffix,binary]))==result;assert _snapshot(api)==_snapshot(binary)
        capacitance=result['quantities']['capacitance'];key='from_energy_f' if axis else 'from_energy_f_per_m';expected='capacitance_f' if axis else 'capacitance_f_per_m';assert abs(capacitance[key]/reference[expected]-1)<1e-10
        mesh=case.partition.mesh;points=(mesh.points_rz_m if axis else mesh.points_xy_m)[mesh.triangles[[0,-1]]].mean(axis=1);point_file=out/f'{label}-points.json';point_file.write_text(json.dumps(points.tolist())+'\n')
        expected=probe(api,out/f'{label}-api-probe.json',points);target=out/f'{label}-cli-probe.json';cli(['probe-'+suffix,binary,'--points',point_file,'--out',target]);assert json.loads(target.read_text())==expected
        for directory in (api,binary):hashes.update({str((directory/name).relative_to(out)):hashlib.sha256(data).hexdigest() for name,data in _snapshot(directory).items()})
    assert len(commands)==6 and len(hashes)==20
    for path,digest in hashes.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    return dict(examples=2,native_saves=4,native_files_unchanged=20,cli_commands=commands,api_cli_native='five files byte-identical',api_cli_probe='complete JSON identical')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();start=time.monotonic();records=[];families=[];boundary_changes=[];preserved={};scalings={};maximum_scaling=0.
    limits={1:[1e-3,.02,.02,1e-3,.04],2:[1e-5,.002,.002,1e-6,.004]}
    for axis,fixture,solve,quantities in ((False,charged_slab,solve_planar_electrostatic,planar_electrostatic_quantities),(True,charged_coax,solve_axisymmetric_electrostatic,electrostatic_quantities)):
        geometry='axisymmetric' if axis else 'planar';energy_key='energy_j' if axis else 'energy_j_per_m';charge_suffix='c' if axis else 'c_per_m';coordinates=('r','z') if axis else ('x','y')
        for order,levels in ((1,(16,32,64)),(2,(8,16,32))):
            for epsilon in (1.,7.):
                for sign in (-1.,1.):
                    previous_boundary=None
                    for outer in (2.,4.,8.):
                        previous=None;rows=[]
                        for n in levels:
                            name=f'{geometry}-p{order}-eps{epsilon}-sign{sign}-outer{outer}-n{n}'
                            case,exact=fixture(order,n,outer,epsilon,sign);solution=solve(case);q=quantities(solution);errors=field_errors(solution,exact,axis)
                            errors += [abs(q[energy_key]/exact['energy']-1),abs(q['electrode_original_field_charge_'+charge_suffix]['ground']/exact['ground_charge']-1)]
                            reaction=abs(q['electrode_reaction_charge_'+charge_suffix]['ground']/exact['ground_charge']-1);assert reaction<1e-10,(name,reaction);assert q['capacitance'] is None
                            if axis or order==1:
                                if previous is not None:assert np.all(np.array(errors[:4])<previous[:4]),(name,errors,previous)
                            else:assert max(errors)<1e-10,(name,errors)
                            previous=errors;rows.append(dict(n=n,errors=errors))
                            path=out/(name+'.json');path.write_text(json.dumps(case.to_dict(),indent=2)+'\n');cls=AxisymmetricElectrostaticCase if axis else PlanarElectrostaticCase;assert cls.from_dict(json.loads(path.read_text())).to_dict()==case.to_dict();preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
                            probe=solution.probe_at(exact['common_points'])['fields'];electric=np.column_stack([probe[f'E{c}_V_per_m'] for c in coordinates]);displacement=np.column_stack([probe[f'D{c}_C_per_m2'] for c in coordinates]);potential=np.array(probe['potential_V'])
                            scale_key=axis,order,n,outer,sign
                            if epsilon==1.:scalings[scale_key]=(potential,electric,displacement,q[energy_key])
                            else:
                                old_phi,old_e,old_d,old_u=scalings[scale_key];difference=max(np.linalg.norm(epsilon*potential-old_phi)/np.linalg.norm(old_phi),np.linalg.norm(epsilon*electric-old_e)/np.linalg.norm(old_e),np.linalg.norm(displacement-old_d)/np.linalg.norm(old_d),abs(epsilon*q[energy_key]/old_u-1));maximum_scaling=max(maximum_scaling,float(difference));assert difference<1e-10,(name,difference)
                            row=dict(name=name,geometry=geometry,order=order,epsilon_r=epsilon,sign=sign,outer_ratio=outer,n=n,phi_e_d_energy_surface_relative_errors=errors,reaction_relative_error=reaction,quantities=q,common_points=exact['common_points'].tolist(),common_probe=probe)
                            records.append(row)
                            with (out/'progress.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
                        assert np.all(np.array(previous)<limits[order]),(name,previous,limits[order]);families.append(dict(geometry=geometry,order=order,epsilon_r=epsilon,sign=sign,outer_ratio=outer,rows=rows,final_limits=limits[order]))
                        if previous_boundary is not None:
                            old_phi,old_e,old_ref=previous_boundary;shift=old_ref['boundary_potential_shift'](exact['outer_distance_m']);shift_error=float(np.max(np.abs((potential-old_phi)/shift-1)));field_difference=float(np.linalg.norm(electric-old_e)/np.linalg.norm(old_e));shift_limit=1e-3 if order==1 else 1e-5;field_limit=.04 if order==1 else .004
                            assert shift_error<shift_limit and field_difference<field_limit,(name,shift_error,field_difference)
                            boundary_changes.append(dict(geometry=geometry,order=order,epsilon_r=epsilon,sign=sign,from_distance_m=old_ref['outer_distance_m'],to_distance_m=exact['outer_distance_m'],analytic_common_potential_shift_v=shift,common_potential_shift_relative_error=shift_error,common_field_relative_difference=field_difference,limits=[shift_limit,field_limit],interpretation=exact['interpretation']))
                        previous_boundary=potential,electric,exact
    examples=example_cli(out);assert len(records)==144 and len(families)==48 and len(boundary_changes)==32
    for path,digest in preserved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    report=dict(status='PASS',cases=len(records),fixed_boundary_refinement_families=len(families),separate_boundary_changes=len(boundary_changes),max_epsilon_scaling_relative_error=maximum_scaling,
        source_sha256=before,case_sha256=preserved,records=records,refinement_families=families,boundary_changes=boundary_changes,examples=examples,seconds=time.monotonic()-start,
        interpretation='Synthetic fixed-charge finite-domain problems. Boundary-distance dependence and FEM error at each fixed boundary are distinct. Common fields remain fixed while absolute potentials diverge linearly/logarithmically as remote ground recedes. No exact-open-boundary solver, error bound, or legacy comparison.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('source_sha256','case_sha256','records','refinement_families','boundary_changes')})


if __name__=='__main__':main()

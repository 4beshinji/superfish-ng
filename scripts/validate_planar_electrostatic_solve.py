# SPDX-License-Identifier: Apache-2.0
"""Planar electrostatic analytical fields/integrals and unchanged axis native replay."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.planar_electrostatic_reference import parallel_plate,manufactured_quadratic,rectangular_poisson
from superfish_ng.planar_electrostatic import PlanarElectrostaticCase,solve_planar_electrostatic,planar_electrostatic_quantities
from superfish_ng.electrostatic_saved import read_electrostatic_run,electrostatic_result,_snapshot


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
                n,scale,epsilon=rectangle;key=n,ix,it;factors=(scale**2,scale,epsilon*scale)
                if key not in REFERENCE_CACHE:
                    high=exact['fields'](points,4096);low=exact['fields'](points,2048)
                    REFERENCE_CACHE[key]=(points/scale,tuple(a/b for a,b in zip(high,factors)),tuple(a/b for a,b in zip(low,factors)))
                saved_points,high,low=REFERENCE_CACHE[key];np.testing.assert_array_equal(saved_points,points/scale)
                reference=tuple(a*b for a,b in zip(high,factors));lower=tuple(a*b for a,b in zip(low,factors))
            values=(actual['potential_V'],np.column_stack((actual['Ex_V_per_m'],actual['Ey_V_per_m'])),np.column_stack((actual['Dx_C_per_m2'],actual['Dy_C_per_m2'])))
            for i,(value,ref,coarse) in enumerate(zip(values,reference,lower)):
                delta=(value-ref)**2;power=ref**2;difference=(ref-coarse)**2
                numerator[i]+=weight@(delta if i==0 else delta.sum(axis=1));denominator[i]+=weight@(power if i==0 else power.sum(axis=1));truncation[i]+=weight@(difference if i==0 else difference.sum(axis=1))
    return np.sqrt(numerator/denominator).tolist(),np.sqrt(truncation/denominator).tolist()


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def replay_axis_reference(reference,before):
    report=json.loads((reference/'report.json').read_text());assert report['status']=='PASS' and report['cases']==24
    changed={'src/superfish_ng/electrostatic.py','src/superfish_ng/electrostatic_boundary.py'}
    assert all(before[p]==h for p,h in report['source_sha256'].items() if p not in changed)
    hashes={};count=0
    for row in report['records']:
        name=row['name'];api=reference/'api-native'/name;cli=reference/'cli-native'/name;original=_snapshot(api);assert original==_snapshot(cli)
        solution=read_electrostatic_run(api);assert electrostatic_result(solution)==json.loads(original['results.json'])
        old_probe=json.loads((reference/f'{name}.api-probe.json').read_text());new_probe=solution.probe_at(old_probe['points_rz_m'])
        for key,value in new_probe.items():assert value==old_probe[key]
        for directory in (api,cli):
            for path,data in _snapshot(directory).items():hashes[str((directory/path).relative_to(reference))]=hashlib.sha256(data).hexdigest()
        assert _snapshot(api)==original;count+=1
    for path,digest in hashes.items():assert hashlib.sha256((reference/path).read_bytes()).hexdigest()==digest
    assert count==24 and len(hashes)==240
    return dict(native_replays=count,native_files_unchanged=len(hashes),probe_json_unchanged=count,
        scope='only static numeric input guards changed in inherited axis solver; full old Poisson/native quantities and original probes are identical')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--axis-native-reference',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];preserved={};pairs={};convergence=[]
    maximum_exact=maximum_shift=maximum_scale=0.;maximum_truncation=np.zeros(3);layered=manufactured=poisson=0
    def run(name,case,exact,rectangle=None):
        solution=solve_planar_electrostatic(case);q=planar_electrostatic_quantities(solution);errors,truncation=field_errors(solution,exact,rectangle)
        energy=float(abs(q['energy_j_per_m']/exact['energy_j_per_m']-1));charge_scale=max(abs(exact.get('volume_charge_c_per_m',0.)),sum(abs(v) for v in exact['electrode_charge_c_per_m'].values()))
        reaction=max(abs(q['electrode_reaction_charge_c_per_m'][name]-value)/charge_scale for name,value in exact['electrode_charge_c_per_m'].items())
        surface=max(abs(q['electrode_original_field_charge_c_per_m'][name]-value)/charge_scale for name,value in exact['electrode_charge_c_per_m'].items())
        path=out/(name+'.json');path.write_text(json.dumps(case.to_dict(),indent=2)+'\n');assert PlanarElectrostaticCase.from_dict(json.loads(path.read_text())).to_dict()==case.to_dict()
        preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        row=dict(name=name,dofs=len(solution.potential_v),phi_e_d_l2_relative_errors=errors,reference_phi_e_d_truncation_difference=truncation,
            energy_relative_error=energy,electrode_reaction_scaled_error=float(reaction),electrode_original_field_scaled_error=float(surface),quantities=q)
        records.append(row)
        with (out/'progress.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
        return solution,row
    motions=((None,(0.,0.),-2.),(np.array([[.6,-.8],[.8,.6]]),(-.5,.25),20.))
    for order in (1,2):
        for scale in (.5,2.):
            for epsilon in (1.,7.):
                for voltage in (-5.,5.):
                    for motion,(rotation,shift,offset) in enumerate(motions):
                        name=f'layer-p{order}-s{scale}-eps{epsilon}-v{voltage}-motion{motion}'
                        case,exact=parallel_plate(order=order,scale=scale,epsilon_scale=epsilon,voltage=voltage,rotation=rotation,shift=shift,offset=offset)
                        solution,row=run(name,case,exact);q=row['quantities'];layered+=1
                        errors=row['phi_e_d_l2_relative_errors']+[row['energy_relative_error'],row['electrode_reaction_scaled_error'],row['electrode_original_field_scaled_error']]
                        errors += [abs(q['region_energy_j_per_m'][k]/v-1) for k,v in exact['region_energy_j_per_m'].items()]
                        errors += [abs(q['capacitance'][k]/exact['capacitance_f_per_m']-1) for k in ('from_reaction_f_per_m','from_energy_f_per_m','from_original_field_f_per_m')]
                        maximum_exact=max(maximum_exact,*errors);assert max(errors)<1e-10,(name,errors)
                        key=order,scale,epsilon,voltage
                        if motion==0:pairs[key]=(solution.potential_v.copy(),q['energy_j_per_m'])
                        else:
                            potential,energy=pairs[key];difference=max(float(np.max(np.abs(solution.potential_v-potential-22.)))/22.,abs(q['energy_j_per_m']/energy-1))
                            maximum_shift=max(maximum_shift,difference);assert difference<1e-10,(name,difference)
                        scale_key=order,epsilon,voltage,motion,'capacitance'
                        if scale==.5:pairs[scale_key]=q['capacitance']['from_energy_f_per_m']
                        else:
                            difference=abs(q['capacitance']['from_energy_f_per_m']/pairs[scale_key]-1)
                            maximum_scale=max(maximum_scale,difference);assert difference<1e-10,(name,difference)
    for concave in (False,True):
        for direction in ('x','y'):
            for scale in (.5,2.):
                for amplitude in (-100.,100.):
                    for motion,(rotation,shift,_) in enumerate(motions):
                        name=f'manufactured-concave{int(concave)}-{direction}-s{scale}-a{amplitude}-motion{motion}'
                        case,exact=manufactured_quadratic(concave=concave,direction=direction,scale=scale,amplitude=amplitude,rotation=rotation,shift=shift)
                        solution,row=run(name,case,exact);q=row['quantities'];manufactured+=1
                        errors=row['phi_e_d_l2_relative_errors']+[row['energy_relative_error'],row['electrode_reaction_scaled_error'],row['electrode_original_field_scaled_error'],
                            abs(q['volume_charge_c_per_m']/exact['volume_charge_c_per_m']-1),abs(q['original_field_gauss_balance_c_per_m']/exact['volume_charge_c_per_m'])]
                        assert q['capacitance'] is None;maximum_exact=max(maximum_exact,*errors);assert max(errors)<1e-10,(name,errors)
    limits={1:[.0005,.015,.015,.0005,.018],2:[1e-5,.0005,.0005,5e-6,.002]}
    for order,levels in ((1,(32,64,128)),(2,(16,32,80))):
        for scale in (.5,2.):
            for epsilon in (1.,7.):
                rows=[];previous=None
                for n in levels:
                    name=f'poisson-p{order}-n{n}-s{scale}-eps{epsilon}'
                    case,exact=rectangular_poisson(order=order,n=n,scale=scale,epsilon_r=epsilon)
                    solution,row=run(name,case,exact,rectangle=(n,scale,epsilon));q=row['quantities'];poisson+=1
                    errors=np.array(row['phi_e_d_l2_relative_errors']+[row['energy_relative_error'],row['electrode_original_field_scaled_error']])
                    assert row['electrode_reaction_scaled_error']<1e-10,(name,row['electrode_reaction_scaled_error'])
                    truncation=row['reference_phi_e_d_truncation_difference'];maximum_truncation=np.maximum(maximum_truncation,truncation)
                    assert max(truncation)<1e-7,(name,truncation)
                    if previous is not None:assert np.all(errors<previous),(name,errors.tolist(),previous.tolist())
                    previous=errors;rows.append(dict(n=n,errors=errors.tolist()))
                    scale_key=order,n,epsilon,'poisson'
                    if scale==.5:pairs[scale_key]=(solution.potential_v.copy(),q['energy_j_per_m'])
                    else:
                        potential,energy=pairs[scale_key];factor=scale/.5
                        difference=max(float(np.linalg.norm(solution.potential_v-factor**2*potential)/np.linalg.norm(solution.potential_v)),abs(q['energy_j_per_m']/(energy*factor**4)-1))
                        maximum_scale=max(maximum_scale,difference);assert difference<1e-10,(name,difference)
                assert np.all(previous<limits[order]),(name,previous.tolist(),limits[order])
                convergence.append(dict(order=order,scale=scale,epsilon_r=epsilon,rows=rows,final_limits=limits[order]))
    axis_replay=replay_axis_reference(args.axis_native_reference.resolve(),before)
    assert layered==32 and manufactured==32 and poisson==24 and len(records)==88
    assert fingerprints()==before
    for path,digest in preserved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',cases=len(records),layered_cases=layered,manufactured_cases=manufactured,poisson_cases=poisson,
        max_exact_relative_error=maximum_exact,max_gauge_rigid_difference=maximum_shift,max_scale_difference=maximum_scale,
        max_reference_phi_e_d_truncation_difference=maximum_truncation.tolist(),reference_truncation_limit=1e-7,
        refinement_families=convergence,axis_native_replay=axis_replay,case_sha256=preserved,source_sha256=before,
        seconds=time.monotonic()-start,records=records,
        interpretation='Synthetic finite-domain electrostatics per metre of uniform extrusion. Original-cell Phi/E/D and surface charge are tested separately. Fourier 2048/4096 differences are sampled truncation diagnostics, not rigorous error bounds. No legacy or external solver reference.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','records','case_sha256')},indent=2))


if __name__=='__main__':main()

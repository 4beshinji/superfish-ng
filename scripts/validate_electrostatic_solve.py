# SPDX-License-Identifier: Apache-2.0
"""Analytical electrostatic Phi/E/D, dielectric layers, charge and capacitance."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.electrostatic_reference import parallel_plate,coaxial_capacitor,manufactured_quadratic
from superfish_ng.electrostatic import AxisymmetricElectrostaticCase,solve_axisymmetric_electrostatic,electrostatic_quantities


def field_errors(solution,exact):
    # Independent tensor Gauss/Duffy rule over original triangles. The
    # analytical E and D are independent of nodal FEM interpolation.
    mesh=solution.case.partition.mesh;vertices=mesh.points_rz_m[mesh.triangles];cells=np.arange(len(vertices))
    jac=(vertices[:,1:]-vertices[:,:1]).transpose(0,2,1);det=np.linalg.det(jac)
    g,w=np.polynomial.legendre.leggauss(10);g=(g+1)/2;w=w/2
    numerator=np.zeros(3);denominator=np.zeros(3)
    for x,wx in zip(g,w):
        for t,wt in zip(g,w):
            y=(1-x)*t;bary=np.array([1-x-y,x,y]);points=np.einsum('i,tij->tj',bary,vertices)
            weight=2*np.pi*points[:,0]*det*wx*wt*(1-x)
            actual=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)))
            phi,e,d=exact['fields'](points)
            electric=np.column_stack((actual['Er_V_per_m'],actual['Ez_V_per_m']));displacement=np.column_stack((actual['Dr_C_per_m2'],actual['Dz_C_per_m2']))
            for i,(value,reference) in enumerate(((actual['potential_V'],phi),(electric,e),(displacement,d))):
                delta=(value-reference)**2;power=reference**2
                numerator[i]+=weight@(delta if i==0 else delta.sum(axis=1));denominator[i]+=weight@(power if i==0 else power.sum(axis=1))
    return [float(v) for v in np.sqrt(numerator/denominator)]


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];preserved={};pairs={}
    maximum_exact=maximum_shift=maximum_scale=0.;layered=manufactured=coaxial=0;convergence=[]
    def run(name,case,exact):
        solution=solve_axisymmetric_electrostatic(case);q=electrostatic_quantities(solution);errors=field_errors(solution,exact)
        energy=float(abs(q['energy_j']/exact['energy_j']-1))
        charge_scale=max(abs(exact.get('volume_charge_c',0.)),sum(abs(v) for v in exact['electrode_charge_c'].values()))
        reaction=max(abs(q['electrode_reaction_charge_c'][key]-value)/charge_scale for key,value in exact['electrode_charge_c'].items())
        surface=max(abs(q['electrode_original_field_charge_c'][key]-value)/charge_scale for key,value in exact['electrode_charge_c'].items())
        path=out/(name+'.json');path.write_text(json.dumps(case.to_dict(),indent=2)+'\n')
        assert AxisymmetricElectrostaticCase.from_dict(json.loads(path.read_text())).to_dict()==case.to_dict()
        preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        record=dict(name=name,dofs=len(solution.potential_v),phi_e_d_l2_relative_errors=errors,energy_relative_error=energy,
            electrode_reaction_scaled_error=float(reaction),electrode_original_field_scaled_error=float(surface),quantities=q)
        records.append(record)
        with (out/'progress.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
        return solution,record
    for order in (1,2):
        for scale in (.5,2.):
            for epsilon_scale in (1.,7.):
                for voltage in (-5.,5.):
                    name=f'layer-p{order}-s{scale}-eps{epsilon_scale}-v{voltage}'
                    case,exact=parallel_plate(order,scale=scale,voltage=voltage,epsilon_scale=epsilon_scale)
                    solution,row=run(name,case,exact);layered+=1
                    values=[*row['phi_e_d_l2_relative_errors'],row['energy_relative_error'],row['electrode_reaction_scaled_error'],row['electrode_original_field_scaled_error']]
                    for key,value in exact['region_energy_j'].items():values.append(abs(row['quantities']['region_energy_j'][key]/value-1))
                    assert max(values)<1e-10;maximum_exact=max(maximum_exact,*values)
                    shifted_case,shifted_exact=parallel_plate(order,scale=scale,voltage=voltage,offset=20.,epsilon_scale=epsilon_scale)
                    shifted,shifted_row=run(name+'-shift',shifted_case,shifted_exact);layered+=1
                    shift=float(np.max(abs(shifted.potential_v-solution.potential_v-22.))/22.)
                    assert shift<1e-11 and abs(shifted_row['quantities']['energy_j']/row['quantities']['energy_j']-1)<1e-11;maximum_shift=max(maximum_shift,shift)
                    key=order,epsilon_scale,voltage
                    if key not in pairs:pairs[key]=row['quantities']['capacitance']['from_energy_f']
                    else:
                        difference=abs(row['quantities']['capacitance']['from_energy_f']/pairs[key]/4-1);assert difference<1e-11;maximum_scale=max(maximum_scale,float(difference))
        print('LAYERED',order,flush=True)
    for axis in (False,True):
        for holes in (0,1,2):
            for direction in ('axial','radial'):
                for scale in (.5,2.):
                    for amplitude in (-100.,100.):
                        name=f'manufactured-axis{int(axis)}-holes{holes}-{direction}-s{scale}-a{amplitude}'
                        case,exact=manufactured_quadratic(axis=axis,holes=holes,direction=direction,scale=scale,amplitude=amplitude,offset=3.)
                        solution,row=run(name,case,exact);manufactured+=1
                        values=[*row['phi_e_d_l2_relative_errors'],row['energy_relative_error'],row['electrode_reaction_scaled_error'],row['electrode_original_field_scaled_error'],
                            abs(row['quantities']['volume_charge_c']/exact['volume_charge_c']-1),abs(row['quantities']['original_field_gauss_balance_c']/exact['volume_charge_c'])]
                        assert max(values)<1e-10;maximum_exact=max(maximum_exact,*values)
            print('MANUFACTURED',axis,holes,flush=True)
    for order in (1,2):
        for scale in (.5,2.):
            for epsilon in (1.,7.):
                rows=[];levels=(16,32,64)
                for n in levels:
                    name=f'coax-p{order}-s{scale}-eps{epsilon}-n{n}';case,exact=coaxial_capacitor(order,n,scale=scale,epsilon_r=epsilon)
                    solution,row=run(name,case,exact);coaxial+=1
                    q=row['quantities'];values=[*row['phi_e_d_l2_relative_errors'],row['energy_relative_error'],row['electrode_original_field_scaled_error']]
                    assert abs(q['capacitance']['from_reaction_f']/q['capacitance']['from_energy_f']-1)<1e-10
                    rows.append(values)
                assert np.all(np.diff(np.asarray(rows),axis=0)<0)
                limits=[.0002,.009,.009,.00005,.008] if order==1 else [2e-7,.00005,.00005,3e-9,.0001]
                assert np.all(np.asarray(rows[-1])<limits),(order,scale,epsilon,rows[-1],limits)
                convergence.append(dict(element_order=order,scale=scale,epsilon_r=epsilon,refinements=list(levels),phi_e_d_energy_surface_errors=rows,limits=limits))
                print('COAX',order,scale,epsilon,flush=True)
    assert fingerprints()==before
    for path,digest in preserved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    result=dict(status='PASS',cases=len(records),layered_cases=layered,manufactured_cases=manufactured,coaxial_cases=coaxial,
        analytical_maximum_relative_error=maximum_exact,maximum_gauge_shift_relative_difference=maximum_shift,maximum_capacitance_spatial_scale_relative_difference=maximum_scale,
        case_roundtrips=len(preserved),coaxial_refinement_families=convergence,records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='declared finite axisymmetric dielectric/electrode problems; analytical fields, charge and energy checked separately; no open-boundary or global discretization-error bound')
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('records','source_sha256','coaxial_refinement_families')})


if __name__=='__main__':main()

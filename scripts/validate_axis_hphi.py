# SPDX-License-Identifier: Apache-2.0
"""Independent axis-hole FEM fields, all wall RF, complex axis voltage and SI scaling."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from axis_hphi_reference import rectangular_axis_holes,reference
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.axis_hphi import AxisHphiCase,AxisAccelerationPath,solve_axis_hphi,axis_hphi_quantities
from superfish_ng.axis_hphi_saved import save_axis_hphi_run,read_axis_hphi_run
from superfish_ng.constants import TAU
from superfish_ng.fem import triangle_quadrature
from superfish_ng.high_order import basis_p2

LIMITS={
    1:dict(frequency_hz=1e-3,electric_relative_l2=.035,magnetic_relative_l2=.003,
        geometry_factor_ohm=.01,q0=.01,wall_loss_w=.01,wall_segments_relative_error=.01,
        axis_voltage_relative_error=.02,r_over_q_accelerator_ohm=.02,r_over_q_circuit_ohm=.02,
        stored_energy_j=1e-8,electric_energy_j=1e-8,magnetic_energy_j=1e-8),
    2:dict(frequency_hz=1e-4,electric_relative_l2=.01,magnetic_relative_l2=.001,
        geometry_factor_ohm=.005,q0=.005,wall_loss_w=.005,wall_segments_relative_error=.005,
        axis_voltage_relative_error=.005,r_over_q_accelerator_ohm=.005,r_over_q_circuit_ohm=.005,
        stored_energy_j=1e-8,electric_energy_j=1e-8,magnetic_energy_j=1e-8)}


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts}


def compare(data,solution):
    expected,walls,voltage,fields=reference(data,solution.case.normalization_j,solution.case.conductivity_s_per_m)
    space=solution.space;vertices=space.mesh.points[space.mesh.triangles];cells=np.arange(len(vertices))
    # A frequency nearest neighbour can have the wrong field. Identify this
    # analytical fixture by its full-vacuum magnetic inner product and guards.
    projection=np.zeros(len(solution.coefficients));reference_mass=0.
    for bary,weight in triangle_quadrature(8):
        basis=bary if solution.case.element_order==1 else basis_p2(bary,solution.gradients)[0]
        rz=np.einsum('tij,i->tj',vertices,bary);h,_,_=fields(rz);r=rz[:,0]
        np.add.at(projection,space.cell_dofs.ravel(),((weight*solution.determinants*r*r*h)[:,None]*basis).ravel())
        reference_mass+=np.sum(weight*solution.determinants*r*h*h)
    coefficients=solution.coefficients
    overlap=abs(coefficients.T@projection)/np.sqrt(reference_mass*np.sum(coefficients*(solution.mass@coefficients),axis=0))
    ranked=np.sort(overlap);mode=int(np.argmax(overlap));assert ranked[-1]>.7 and ranked[-1]-ranked[-2]>.3,overlap
    ratios=solution.frequencies_hz/expected['frequency_hz'];assert 0<mode<len(ratios)-1
    gap=float(min(ratios[mode]-ratios[mode-1],ratios[mode+1]-ratios[mode]));assert gap>.001,('target guards unresolved',gap)
    hnorm=np.zeros(3);enorm=np.zeros(3)
    for bary,weight in triangle_quadrature(7):
        rz=np.einsum('tij,i->tj',vertices,bary);h,er,ez=fields(rz)
        actual=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)),mode)
        ah=actual['Hphi_real_A_per_m'];ar=actual['Er_quadrature_V_per_m'];az=actual['Ez_quadrature_V_per_m']
        measure=TAU*rz[:,0]*weight*solution.determinants
        hnorm+=[measure@(ah*ah),measure@(h*h),measure@(ah*h)]
        enorm+=[measure@(ar*ar+az*az),measure@(er*er+ez*ez),measure@(ar*er+az*ez)]
    sign=1 if hnorm[2]>=0 else -1
    herr=np.sqrt(max(0.,(hnorm[0]+hnorm[1]-2*sign*hnorm[2])/hnorm[1]))
    eerr=np.sqrt(max(0.,(enorm[0]+enorm[1]-2*sign*enorm[2])/enorm[1]))
    rf=axis_hphi_quantities(solution,mode);errors={key:float(abs(rf[key]/value-1)) for key,value in expected.items()}
    positive=walls>0;actual_walls=np.array(rf['wall_h2_integral_a2_by_segment'])
    assert np.array_equal(actual_walls[~positive],walls[~positive])
    wall_errors=abs(actual_walls[positive]/walls[positive]-1)
    numerical_voltage=complex(rf['vacc_v']['real'],rf['vacc_v']['imag'])
    errors.update(electric_relative_l2=float(eerr),magnetic_relative_l2=float(herr),
        wall_segments_relative_error=float(max(wall_errors)),axis_voltage_relative_error=float(abs(sign*numerical_voltage-voltage)/abs(voltage)))
    return dict(mode_index=mode,analytic_magnetic_overlap=float(overlap[mode]),next_overlap=float(ranked[-2]),relative_guard_gap=gap,
        quantities=rf,reference=expected,analytic_voltage_v=dict(real=voltage.real,imag=voltage.imag),errors=errors,
        all_frequency_ratios=ratios.tolist(),analytic_wall_integrals_a2=walls.tolist(),positive_wall_errors=wall_errors.tolist())


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--diagnostic-only',action='store_true',help='one scale, no native; cannot accept the complete solve/native stage')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();start=time.monotonic();records=[]
    for holes in (1,2):
        for order,levels in ((1,(32,64)),(2,(8,16))):
            for scale in ((1.,) if args.diagnostic_only else (1.,2.)):
                previous=None
                for level,n in enumerate(levels):
                    label=f'holes{holes}-p{order}-s{scale:g}-n{n}';print('START',label,flush=True)
                    data=rectangular_axis_holes(n,holes,scale)
                    case=AxisHphiCase(AxisConnectedMesh(**data),element_order=order,modes=32,normalization_j=scale**3,
                        acceleration=AxisAccelerationPath(0.,.06*scale,1.,0.))
                    solution=solve_axis_hphi(case);comparison=compare(data,solution);native_hashes=None
                    if not args.diagnostic_only:
                        folder=out/label;save_axis_hphi_run(case,solution,folder);replayed=read_axis_hphi_run(folder)
                        np.testing.assert_array_equal(replayed.coefficients,solution.coefficients)
                        native_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
                    record=dict(holes=holes,order=order,scale=scale,n=n,final=bool(level),dofs=len(solution.coefficients),
                        **comparison,native_sha256=native_hashes)
                    records.append(record);(out/'progress.json').write_text(json.dumps(dict(records=records),indent=2)+'\n')
                    print('DONE',label,record['errors'],flush=True)
                    if level:
                        for key,limit in LIMITS[order].items():
                            assert record['errors'][key]<limit,(label,key,record['errors'][key],limit)
                            if key not in ('stored_energy_j','electric_energy_j','magnetic_energy_j'):
                                assert record['errors'][key]<previous['errors'][key],(label,'no decrease',key)
                        assert np.all(np.array(record['positive_wall_errors'])<np.array(previous['positive_wall_errors'])),(label,'wall segment error did not decrease')
                    previous=record
    similarity=[]
    if not args.diagnostic_only:
        for first in [r for r in records if r['scale']==1]:
            second=next(r for r in records if all(r[key]==first[key] for key in ('holes','order','n')) and r['scale']==2)
            assert first['mode_index']==second['mode_index']
            for key,factor in dict(frequency_hz=.5,stored_energy_j=8.,geometry_factor_ohm=1.,q0=np.sqrt(2),wall_loss_w=2**1.5,
                r_over_q_accelerator_ohm=1.,r_over_q_circuit_ohm=1.).items():
                similarity.append(abs(second['quantities'][key]/(first['quantities'][key]*factor)-1))
        assert max(similarity)<1e-8
    after=fingerprints();assert before==after
    result=dict(status='DIAGNOSTIC_ONLY' if args.diagnostic_only else 'PASS',
        scope='one/two rectangular PEC holes; P1/P2 regular-axis FEM; all wall segments and declared complex axis voltage',
        records=records,limits=LIMITS,max_similarity_relative_error=None if not similarity else float(max(similarity)),
        source_sha256=after,source_unchanged=True,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],len(records),'FEM runs',flush=True)


if __name__=='__main__':main()

# SPDX-License-Identifier: Apache-2.0
"""Independent one/two-hole Hphi mode, all PEC losses and similarity checks."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from hphi_mesh_reference import rectangular_holes, reference
from superfish_ng.constants import TAU
from superfish_ng.fem import triangle_quadrature
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.hphi_mesh import HphiMeshCase, solve_hphi_mesh, hphi_mesh_quantities
from superfish_ng.hphi_mesh_saved import save_hphi_mesh_run, read_hphi_mesh_run


LIMITS = {
    1: dict(frequency_hz=1e-3,electric_relative_l2=.035,magnetic_relative_l2=.003,
            geometry_factor_ohm=.01,q0=.01,wall_loss_w=.01,wall_segments_relative_error=.01,stored_energy_j=1e-8),
    2: dict(frequency_hz=1e-4,electric_relative_l2=.01,magnetic_relative_l2=.001,
            geometry_factor_ohm=.005,q0=.005,wall_loss_w=.005,wall_segments_relative_error=.005,stored_energy_j=1e-8)}


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def compare(data,solution):
    expected,walls,fields = reference(data,solution.case.normalization_j,solution.case.conductivity_s_per_m)
    ratios = solution.frequencies_hz/expected['frequency_hz']
    mode = int(np.argmin(abs(ratios-1)))
    assert 0 < mode < len(ratios)-1, ('analytic target requires guards below and above',ratios)
    gap = float(min(ratios[mode]-ratios[mode-1],ratios[mode+1]-ratios[mode]))
    assert gap > .03, ('individual target is not independently separated',gap)
    space=solution.space; vertices=space.mesh.points[space.mesh.triangles]; cells=np.arange(len(vertices))
    hnorm=np.zeros(3); enorm=np.zeros(3)
    for bary,weight in triangle_quadrature(7):
        rz=np.einsum('tij,i->tj',vertices,bary); h,e=fields(rz)
        actual=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)),mode)
        ah=actual['Hphi_real_A_per_m']; ar=actual['Er_quadrature_V_per_m']; az=actual['Ez_quadrature_V_per_m']
        measure=TAU*rz[:,0]*weight*space.determinants
        hnorm += [measure@(ah*ah),measure@(h*h),measure@(ah*h)]
        enorm += [measure@(ar*ar+az*az),measure@(e*e),measure@(ar*e)]
    sign=1 if hnorm[2] >= 0 else -1
    herr=np.sqrt(max(0.,(hnorm[0]+hnorm[1]-2*sign*hnorm[2])/hnorm[1]))
    eerr=np.sqrt(max(0.,(enorm[0]+enorm[1]-2*sign*enorm[2])/enorm[1]))
    rf=hphi_mesh_quantities(solution,mode)
    errors={key:float(abs(rf[key]/value-1)) for key,value in expected.items()}
    errors.update(electric_relative_l2=float(eerr),magnetic_relative_l2=float(herr),
                  wall_segments_relative_error=float(max(abs(np.array(rf['wall_h2_integral_a2_by_segment'])/walls-1))))
    return dict(mode_index=mode,relative_guard_gap=gap,quantities=rf,reference=expected,errors=errors,
                all_frequency_ratios=ratios.tolist(),analytic_wall_integrals_a2=walls.tolist())


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();start=time.monotonic();records=[]
    for holes in (1,2):
        for order,levels in ((1,(16,32)),(2,(6,12))):
            for scale in (1.,2.):
                previous=None
                for level,n in enumerate(levels):
                    label=f'holes{holes}-p{order}-s{scale:g}-n{n}'
                    print('START',label,flush=True)
                    data=rectangular_holes(n,holes,scale)
                    case=HphiMeshCase(MeridionalMesh(**data),element_order=order,modes=9,normalization_j=scale**3)
                    solution=solve_hphi_mesh(case);comparison=compare(data,solution)
                    folder=out/label;save_hphi_mesh_run(case,solution,folder);replayed=read_hphi_mesh_run(folder)
                    np.testing.assert_array_equal(replayed.coefficients,solution.coefficients)
                    record=dict(holes=holes,order=order,scale=scale,n=n,final=bool(level),dofs=len(solution.coefficients),
                                **comparison,matrix_quadrature=solution.quadrature_diagnostic,
                                native_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()})
                    records.append(record);(out/'progress.json').write_text(json.dumps(dict(records=records),indent=2)+'\n')
                    print('DONE',label,record['errors'],flush=True)
                    if level:
                        for key,limit in LIMITS[order].items():
                            assert record['errors'][key] < limit,(label,key,record['errors'][key],limit)
                            if key != 'stored_energy_j':assert record['errors'][key] < previous[key],(label,'no decrease',key)
                    previous=record['errors']
    similarity=[]
    for first in [r for r in records if r['scale']==1]:
        second=next(r for r in records if all(r[key]==first[key] for key in ('holes','order','n')) and r['scale']==2)
        assert first['mode_index']==second['mode_index']
        for key,factor in dict(frequency_hz=.5,stored_energy_j=8.,geometry_factor_ohm=1.,q0=np.sqrt(2),wall_loss_w=2**1.5).items():
            similarity.append(abs(second['quantities'][key]/(first['quantities'][key]*factor)-1))
    assert max(similarity)<1e-8
    after=fingerprints();assert before==after
    result=dict(status='PASS',scope='one/two rectangular conductor holes; actual FEM and all declared PEC segments',
                records=records,limits=LIMITS,max_similarity_relative_error=float(max(similarity)),
                source_sha256=after,source_unchanged=True,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(records),'FEM/native runs',flush=True)


if __name__=='__main__':main()

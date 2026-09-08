# SPDX-License-Identifier: Apache-2.0
"""Independent spectrum, volume and Maxwell scaling across native remeshes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking
from superfish_ng.analytic import tm0np_frequency


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={}
    controls=dict(mapping='same_domain',minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
    for kind in ('cylinder','folded'):
        spectra=[];overlaps=[];rf=[];counts=[];volume_errors=[]
        for scale in (1.,2.):
            names=[];frequencies=[];quantities=[]
            for stage in (0,1):
                if kind=='cylinder':
                    case=Case(((0.,scale*.1),(scale*.08,scale*.1)),nr=10+stage*3,nz=12+stage*5,modes=2,element_order=2)
                    volume=np.pi*(scale*.1)**2*(scale*.08)
                else:
                    data=Case.load(ROOT/'examples/contour_folded.json').to_dict()
                    data['geometry']['vertices_zr_m']=[[scale*z,scale*r] for z,r in data['geometry']['vertices_zr_m']]
                    data['mesh']['contour_mesh'].update(max_edge_m=scale*(.025 if stage==0 else .018),min_angle_deg=5.)
                    case=Case.from_dict(data)
                    polygon=np.array(data['geometry']['vertices_zr_m']);following=np.roll(polygon,-1,axis=0)
                    volume=abs(np.pi/3*np.sum((polygon[:,0]*following[:,1]-following[:,0]*polygon[:,1])*(polygon[:,1]+following[:,1])))
                solution=solve(case);name=f'{kind}-{int(scale)}-{stage}';save_run(case,solution,out/name);names.append(name)
                frequencies.append(solution.frequencies_hz.tolist())
                quantities.append(json.loads((out/name/'results.json').read_text())['modes'])
            rows=[]
            for q in (3,5):
                request=dict(schema_version=1,previous_run=names[0],current_run=names[1],previous_ids=[f'ID{i}' for i in range(len(frequencies[0]))],controls=dict(controls,sample_order=q))
                (out/f'{kind}-{int(scale)}-{q}-request.json').write_text(json.dumps(request,indent=2)+'\n')
                path=out/f'{kind}-{int(scale)}-{q}-pair.json';pair=save_mode_tracking(request,path,base_directory=out)
                assert read_mode_tracking(path)==pair and pair['status']=='PASS'
                rows.append([m['minimum_principal_overlap'] for m in pair['tracking']['matches']])
                volume_errors.extend(abs(v/volume-1) for v in pair['tracking']['physical_mapping']['axisymmetric_volumes_m3'])
                counts.append(pair['tracking']['physical_mapping']['triangle_counts'])
            spectra.append(frequencies);rf.append(quantities);overlaps.append(rows)
        similarity={key:0. for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        for a,b in zip(rf[0],rf[1],strict=True):
            for x,y in zip(a,b,strict=True):
                for key in similarity:similarity[key]=max(similarity[key],abs(y[key]*(2 if key=='frequency_hz' else 1)/x[key]-1))
        overlap_scale=float(np.max(np.abs(np.array(overlaps[0])-overlaps[1])))
        quadrature_delta=float(np.max(np.abs(np.array(overlaps)[:,0]-np.array(overlaps)[:,1])))
        analytical=[]
        if kind=='cylinder':
            expected=[tm0np_frequency(.1,.08,1,p) for p in (0,1)]
            analytical=[abs(f/e-1) for row in spectra[0] for f,e in zip(row,expected,strict=True)]
        passed=(max(similarity.values())<2e-9 and overlap_scale<2e-10 and quadrature_delta<1e-4
            and max(volume_errors)<2e-12 and all(a!=b for a,b in counts) and (not analytical or max(analytical)<.002))
        checks[kind]=dict(passed=passed,similarity_relative_errors=similarity,overlap_scale_difference=overlap_scale,quadrature_overlap_difference=quadrature_delta,
            volume_relative_errors=volume_errors,frequency_analytical_relative_errors=analytical,overlaps=overlaps,triangle_counts=counts)
    passed=all(c['passed'] for c in checks.values()) and before==hashes()
    report=dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=before!=hashes(),
        scope='native P2 independent remeshes of cylinder and synthetic folded polygon; analytic spectrum/volume and Maxwell scale invariance; quadrature order check is not a rigorous integration error bound or physical convergence acceptance')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(f'Same domain {"PASS" if passed else "FAIL"}: {out}')
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())

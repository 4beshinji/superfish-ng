# SPDX-License-Identifier: Apache-2.0
"""Bessel spectrum, analytic volume and Maxwell scaling of declared affine maps."""
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
from superfish_ng.analytic import tm0np_frequency
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={}
    for kind in ('cylinder','sheared_triangle'):
        a,c,b=(1.2,.8,0.) if kind=='cylinder' else (1.1,.9,.1)
        affine=dict(radial_scale=a,axial_scale=c,axial_shear=b)
        rows=[];overlaps=[];volume_errors=[];frequency_errors=[];counts=[]
        for scale in (1.,2.):
            names=[];quantities=[]
            for stage in (0,1):
                if kind=='cylinder':
                    radius=.1*scale*(a if stage else 1);length=.08*scale*(c if stage else 1)
                    case=Case(((0.,radius),(length,radius)),nr=10+3*stage,nz=12+5*stage,modes=1,element_order=2)
                    volume=np.pi*radius**2*length
                else:
                    data=Case.load(ROOT/'examples/contour_folded.json').to_dict()
                    vertices=np.array([[0.,0.],[.12,0.],[.06,.08]])*scale
                    if stage:vertices=np.column_stack((c*vertices[:,0]+b*vertices[:,1],a*vertices[:,1]))
                    data['geometry']['vertices_zr_m']=vertices.tolist();data['geometry']['edge_tags']=['axis','pec','pec']
                    data['mesh']['contour_mesh'].update(max_edge_m=scale*(.025 if stage==0 else .018),min_angle_deg=5.)
                    case=Case.from_dict(data);volume=np.pi*(.08*scale)**2*(.12*scale)/3*(a*a*c if stage else 1)
                name=f'{kind}-{int(scale)}-{stage}';solution=solve(case);save_run(case,solution,out/name);names.append(name)
                quantities.append(json.loads((out/name/'results.json').read_text())['modes'][0])
                if kind=='cylinder':frequency_errors.append(abs(solution.frequencies_hz[0]/tm0np_frequency(radius,length,1,0)-1))
                if stage==0:old_volume=volume
            sample_results=[]
            for order in (3,5):
                controls=dict(mapping='affine_remesh',affine_map=affine,sample_order=order,minimum_overlap=.98,
                    minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
                request=dict(schema_version=1,previous_run=names[0],current_run=names[1],previous_ids=['fundamental'],controls=controls)
                (out/f'{kind}-{int(scale)}-{order}-request.json').write_text(json.dumps(request,indent=2)+'\n')
                path=out/f'{kind}-{int(scale)}-{order}-pair.json';pair=save_mode_tracking(request,path,base_directory=out)
                assert read_mode_tracking(path)==pair and pair['status']=='PASS'
                m=pair['tracking']['physical_mapping'];counts.append(m['triangle_counts'])
                volume_errors.extend(abs(v/e-1) for v,e in zip(m['physical_axisymmetric_volumes_m3'],(old_volume,volume),strict=True))
                sample_results.append(pair['tracking']['matches'][0]['minimum_principal_overlap'])
            rows.append(quantities);overlaps.append(sample_results)
        similarity={key:max(abs(y[key]*(2 if key=='frequency_hz' else 1)/x[key]-1) for x,y in zip(rows[0],rows[1],strict=True))
            for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        quadrature=max(abs(x-y) for x,y in overlaps);scale_error=max(abs(x-y) for x,y in zip(*overlaps))
        passed=(max(similarity.values())<2e-9 and quadrature<1e-4 and scale_error<2e-10 and max(volume_errors)<2e-12
            and all(x!=y for x,y in counts) and (not frequency_errors or max(frequency_errors)<.002))
        checks[kind]=dict(passed=bool(passed),similarity_relative_errors=similarity,overlaps=overlaps,quadrature_overlap_difference=quadrature,
            overlap_scale_difference=scale_error,volume_relative_errors=volume_errors,frequency_analytical_relative_errors=frequency_errors,triangle_counts=counts)
    passed=all(c['passed'] for c in checks.values()) and before==hashes()
    report=dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=before!=hashes(),
        scope='native P2 independent remeshes, anisotropic cylinder and sheared synthetic triangle; explicit affine correspondence, Bessel spectrum, analytic volume and uniform scale invariance; not physical convergence or non-affine mapping acceptance')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(f'Affine remesh {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())

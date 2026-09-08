# SPDX-License-Identifier: Apache-2.0
"""Non-affine profile/folded remeshes with independent volume and scale checks."""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.io import save_run
from superfish_ng.analytic import tm0np_frequency
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking


def volume(case):
    if case.contour is None:
        return np.pi/3*sum((zb-za)*(ra*ra+ra*rb+rb*rb) for (za,ra),(zb,rb) in zip(case.profile,case.profile[1:]))
    p=np.array(case.contour.vertices_zr_m);q=np.roll(p,-1,axis=0)
    return abs(np.pi/3*np.sum((p[:,0]*q[:,1]-q[:,0]*p[:,1])*(p[:,1]+q[:,1])))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={}
    for kind in ('profile','folded'):
        rows=[];overlaps=[];volumes=[];counts=[];bessel=[]
        for scale in (1.,2.):
            if kind=='profile':
                old=Case(((0.,scale*.1),(scale*.05,scale*.1),(scale*.1,scale*.1)),nr=10,nz=12,modes=1,element_order=2)
                new=replace(old,profile=((0.,scale*.1),(scale*.045,scale*.09),(scale*.1,scale*.1)),nr=13,nz=17)
                reference=mesh_to_dict(make_mesh(replace(old,nr=2,nz=2)));mapped=deepcopy(reference)
                for p in mapped['points']:
                    if p[1]==scale*.05:p[0]*=.9;p[1]=scale*.045
            else:
                data=Case.load(ROOT/'examples/contour_folded.json').to_dict()
                data['geometry']['vertices_zr_m']=[[scale*z,scale*r] for z,r in data['geometry']['vertices_zr_m']]
                data['mesh']['contour_mesh'].update(max_edge_m=scale*.02,min_angle_deg=5.)
                old=Case.from_dict(data)
                reference_data=deepcopy(data);reference_data['mesh']['contour_mesh']['max_edge_m']=scale*.025
                reference=mesh_to_dict(make_mesh(Case.from_dict(reference_data)));mapped=deepcopy(reference)
                for p in mapped['points']:p[0]*=1+.1*p[1]/(scale*.09)
                data['geometry']['vertices_zr_m']=[[z,r*(1+.1*z/(scale*.09))] for z,r in data['geometry']['vertices_zr_m']]
                data['mesh']['contour_mesh']['max_edge_m']=scale*.015;new=Case.from_dict(data)
            cases=[old,new];names=[];quantities=[]
            for stage,case in enumerate(cases):
                name=f'{kind}-{int(scale)}-{stage}';solution=solve(case);save_run(case,solution,out/name);names.append(name)
                quantities.append(json.loads((out/name/'results.json').read_text())['modes'][0])
                if kind=='profile' and stage==0:bessel.append(float(abs(solution.frequencies_hz[0]/tm0np_frequency(scale*.1,scale*.1,1,0)-1)))
            values=[]
            for order in (6,10):
                controls=dict(mapping='piecewise_remesh',comparison_meshes=[reference,mapped],sample_order=order,minimum_overlap=.95,
                    minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
                request=dict(schema_version=1,previous_run=names[0],current_run=names[1],previous_ids=['fundamental'],controls=controls)
                (out/f'{kind}-{int(scale)}-{order}-request.json').write_text(json.dumps(request,indent=2)+'\n')
                path=out/f'{kind}-{int(scale)}-{order}-pair.json';pair=save_mode_tracking(request,path,base_directory=out)
                assert read_mode_tracking(path)==pair and pair['status']=='PASS'
                m=pair['tracking']['physical_mapping'];counts.append([m['comparison_triangle_count'],*m['solver_triangle_counts']])
                volumes.extend(float(abs(v/volume(case)-1)) for v,case in zip(m['axisymmetric_volumes_m3'],cases,strict=True))
                values.append(pair['tracking']['matches'][0]['minimum_principal_overlap'])
            rows.append(quantities);overlaps.append(values)
        similarity={key:max(abs(y[key]*(2 if key=='frequency_hz' else 1)/x[key]-1) for x,y in zip(rows[0],rows[1],strict=True))
            for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        quadrature=max(abs(x-y) for x,y in overlaps);scaled=max(abs(x-y) for x,y in zip(*overlaps))
        passed=max(similarity.values())<2e-9 and quadrature<1e-4 and scaled<2e-10 and max(volumes)<2e-12 and all(r<a and r<b and a!=b for r,a,b in counts) and (not bessel or max(bessel)<.002)
        checks[kind]=dict(passed=passed,similarity_relative_errors=similarity,overlaps=overlaps,quadrature_overlap_difference=quadrature,
            overlap_scale_difference=scaled,volume_relative_errors=volumes,initial_cylinder_bessel_relative_errors=bessel,triangle_counts_reference_previous_current=counts)
    passed=all(c['passed'] for c in checks.values()) and before==hashes()
    report=dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=before!=hashes(),
        scope='native P2 non-affine profile and synthetic folded deformation, independent comparison and solver meshes; analytic volume, initial cylinder Bessel and uniform Maxwell scaling; not physical convergence, curved maps or inferred correspondence acceptance')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(f'Piecewise remesh {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())

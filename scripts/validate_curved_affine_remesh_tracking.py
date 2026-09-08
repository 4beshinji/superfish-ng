# SPDX-License-Identifier: Apache-2.0
"""Native anisotropic curved remeshes: volume, sphere and Maxwell scaling."""
import argparse
import copy
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
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={};a,c=1.2,.8
    for kind in ('sphere','ellipsoid'):
        rows=[];overlaps=[];volumes=[];sphere_errors=[];counts=[];bounds=[];reciprocity=[]
        for scale in (1.,2.):
            data=Case.load(ROOT/'examples/curved_ellipse.json').to_dict()
            data['mesh'].update(geometry_order=2);data['mesh']['contour_mesh'].update(max_edge_m=scale*.04,min_angle_deg=5.)
            data['geometry']['curves'][0]['end_zr_m']=[scale*.2,0.]
            data['geometry']['curves'][1]['center_zr_m']=[scale*.1,0.]
            radial=scale*(.1 if kind=='sphere' else .08)
            data['geometry']['curves'][1]['semiaxes_m']=[scale*.1,radial]
            data['geometry']['chord_tolerance_m']=scale*.002;data['geometry']['join_tolerance_m']=scale*1e-14
            base=Case.from_dict(data);old=solve(base)
            new=copy.deepcopy(data);g=new['geometry']
            g['curves'][0]['end_zr_m'][0]*=c;g['curves'][1]['center_zr_m'][0]*=c
            g['curves'][1]['semiaxes_m'][0]*=c;g['curves'][1]['semiaxes_m'][1]*=a
            g['chord_tolerance_m']*=max(a,c);new['mesh']['curved_refinement_levels']=1
            mesh=copy.deepcopy(old.source_mesh_data);mesh['points']=(np.array(mesh['points'])*[a,c]).tolist()
            current=solve(Case.from_dict(new),mesh_data=mesh);names=[];quantities=[]
            for stage,solution in enumerate((old,current)):
                name=f'{kind}-{int(scale)}-{stage}';save_run(solution.case,solution,out/name);names.append(name)
                quantities.append(json.loads((out/name/'results.json').read_text())['modes'][0])
            if kind=='sphere':sphere_errors.append(float(abs(old.frequencies_hz[0]/SphereTM(scale*.1).frequency_hz-1)))
            values=[]
            for order in (3,5):
                controls=dict(mapping='affine_remesh',affine_map=dict(radial_scale=a,axial_scale=c,axial_shear=0.),sample_order=order,
                    minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
                request=dict(schema_version=1,previous_run=names[0],current_run=names[1],previous_ids=['fundamental'],controls=controls)
                (out/f'{kind}-{int(scale)}-{order}-request.json').write_text(json.dumps(request,indent=2)+'\n')
                path=out/f'{kind}-{int(scale)}-{order}-pair.json';pair=save_mode_tracking(request,path,base_directory=out)
                assert read_mode_tracking(path)==pair and pair['status']=='PASS'
                inverse=dict(controls,affine_map=dict(radial_scale=1/a,axial_scale=1/c,axial_shear=0.))
                reverse=save_mode_tracking(dict(request,previous_run=names[1],current_run=names[0],controls=inverse),out/f'{kind}-{int(scale)}-{order}-inverse.json',base_directory=out)
                assert reverse['status']=='PASS'
                overlap=pair['tracking']['matches'][0]['minimum_principal_overlap'];values.append(overlap)
                reciprocity.append(abs(overlap-reverse['tracking']['matches'][0]['minimum_principal_overlap']))
                m=pair['tracking']['physical_mapping'];counts.append(m['triangle_counts']);bounds.append(m['boundary_coincidence'])
                measured=m['physical_axisymmetric_volumes_m3'];reference=m['reference_axisymmetric_volumes_m3'];analytic=4*np.pi/3*(scale*.1)*radial**2
                volumes.append(dict(reference_relative_difference=abs(reference[1]/reference[0]-1),ratio_relative_error=abs(measured[1]/measured[0]/(a*a*c)-1),
                    analytical_relative_errors=[float(abs(v/expected-1)) for v,expected in zip(measured,(analytic,analytic*a*a*c))]))
            rows.append(quantities);overlaps.append(values)
        similarity={key:max(abs(y[key]*(2 if key=='frequency_hz' else 1)/x[key]-1) for x,y in zip(rows[0],rows[1],strict=True))
            for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        quadrature=max(abs(x-y) for x,y in overlaps);scaled=max(abs(x-y) for x,y in zip(*overlaps))
        passed=(max(similarity.values())<2e-9 and quadrature<1e-4 and scaled<2e-10 and max(reciprocity)<2e-12
            and max(max(v['reference_relative_difference'],v['ratio_relative_error']) for v in volumes)<2e-12
            and max(e for v in volumes for e in v['analytical_relative_errors'])<.002
            and all(y==4*x for x,y in counts) and (not sphere_errors or max(sphere_errors)<.002))
        checks[kind]=dict(passed=passed,similarity_relative_errors=similarity,overlaps=overlaps,quadrature_overlap_difference=quadrature,
            overlap_scale_difference=scaled,reciprocity_differences=reciprocity,volumes=volumes,sphere_frequency_relative_errors=sphere_errors,triangle_counts=counts,boundary_checks=bounds)
    passed=all(c['passed'] for c in checks.values()) and before==hashes()
    report=dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=before!=hashes(),
        scope='native curved P2 diagonal affine deformation and fixed-boundary subdivision; sphere and synthetic ellipsoid; sphere frequency, analytic volume, uniform Maxwell scaling and reciprocal saved tracking; shear has separate polynomial adapter tests, not native eigenmode acceptance; not general boundary reapproximation or physical RF convergence acceptance')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(f'Curved affine remesh {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())

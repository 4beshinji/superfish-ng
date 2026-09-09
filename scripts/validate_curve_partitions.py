# SPDX-License-Identifier: Apache-2.0
"""Fixed native partition affine geometry, volume, FEM and Maxwell invariants."""
import argparse
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.affine_conics import transform_curve
from superfish_ng.affine_remesh_tracking import track_affine_remesh_modes
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.rf import quantities
from validate_curved_rf_adaptive import fingerprints


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();rows=[]
    for scale in (1.,2.):
        raw=Case.load(ROOT/'examples/curved_ellipse.json').to_dict()
        raw['geometry']['join_tolerance_m']*=scale
        raw['geometry']['curves'][0]['end_zr_m'][0]*=scale
        raw['geometry']['curves'][1]['center_zr_m'][0]*=scale
        raw['geometry']['curves'][1]['semiaxes_m']=[v*scale for v in raw['geometry']['curves'][1]['semiaxes_m']]
        raw['geometry'].update(chord_tolerance_m=.008*scale,segments_per_curve=[1,4])
        raw['mesh']['geometry_order']=2;raw['mesh']['contour_mesh'].update(max_edge_m=.08*scale,min_angle_deg=5.)
        case=Case.from_dict(raw);old=solve(case);reference=quantities(case,old)
        for a,c in ((2.,.5),(.5,2.),(2.,2.)):
            mapping=dict(radial_scale=a,axial_scale=c,axial_shear=0.)
            contour=replace(case.curved_contour,
                join_tolerance_m=case.curved_contour.join_tolerance_m*max(a,c),
                curves=tuple(transform_curve(curve,mapping) for curve in case.curved_contour.curves))
            target=replace(case,curved_contour=contour,contour=None,curve_chord_tolerance_m=.1*scale)
            mesh=deepcopy(old.source_mesh_data);mesh['points']=(np.array(mesh['points'])*[a,c]).tolist()
            new=solve(target,mesh_data=mesh)
            points_error=float(np.max(np.abs(new.space.geometry.points_rz_m-old.space.geometry.points_rz_m*[a,c])))/scale
            determinants=[]
            for x,y in zip(old.space.geometry.local_maps,new.space.geometry.local_maps):
                p=x.evaluate([[.2,.3],[.5,.1]]);q=y.evaluate([[.2,.3],[.5,.1]])
                determinants.extend(np.abs(q['determinant_m2']/(p['determinant_m2']*a*c)-1).tolist())
            tracking=track_affine_remesh_modes(old,new,['A'],mapping='affine_remesh',affine_map=mapping,sample_order=5,
                minimum_overlap=.8,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
            run=out/f'scale-{scale:g}-radial-{a:g}-axial-{c:g}';save_run(target,new,run);saved=read_solution(run)
            assert saved.case.curve_segments_per_curve==(1,4)
            np.testing.assert_array_equal(saved.space.geometry.points_rz_m,new.space.geometry.points_rz_m)
            similarity=None
            if a==c:
                rf=quantities(target,new);similarity={key:abs(rf[key]*(a if key=='frequency_hz' else 1)/reference[key]-1)
                    for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
                assert max(similarity.values())<1e-10
            assert points_error<1e-12 and max(determinants)<1e-11 and tracking['status']=='PASS'
            rows.append(dict(scale=scale,affine_map=mapping,points_scaled_absolute_error=points_error,
                determinant_relative_error=max(determinants),tracking_status=tracking['status'],similarity=similarity,saved_geometry_exact=True))
    assert before==fingerprints()
    (out/'validation.json').write_text(json.dumps(dict(passed=True,rows=rows,source_sha256=before,source_unchanged=True,
        scope='six explicit fixed quadratic partitions; sampled determinant and exact saved geometry, actual FEM tracking, homogeneous Maxwell scaling; not general shape convergence'),indent=2)+'\n')
    print('Fixed curve partitions PASS');return 0


if __name__=='__main__':raise SystemExit(main())

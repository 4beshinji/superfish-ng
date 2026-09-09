# SPDX-License-Identifier: Apache-2.0
"""Independent affine volume, native Job replay and Maxwell/analytic checks."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
import math
import numpy as np
from scipy.special import jn_zeros
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.project import Project
from superfish_ng.curved_project_transform import transform_curved_project,relative_affine_map
from superfish_ng.conics import LineSegment
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.jobs import execute_project
from superfish_ng.saved import read_solution
from superfish_ng.rf import quantities
from superfish_ng.constants import C0
from validate_curved_rf_adaptive import fingerprints


def line_case(points):
    curves=tuple(LineSegment(p,q) for p,q in zip(points,points[1:]+points[:1]))
    return Case((),curved_contour=CurvedContour(curves,('axis',)+('pec',)*(len(points)-1),1e-14),
        curve_chord_tolerance_m=.001,contour_mesh=ContourMeshControls(.015,min_angle_deg=5.),
        element_order=2,geometry_order=2,quadrature_order=12,modes=1)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();rows=[]
    cases={}
    for name in ('ellipse','hyperbola'):
        raw=Case.load(ROOT/f'examples/curved_{name}.json').to_dict()
        raw['mesh']['geometry_order']=2;raw['mesh']['contour_mesh'].update(max_edge_m=.04,min_angle_deg=5.)
        raw['geometry']['chord_tolerance_m']=.002
        cases[name]=Case.from_dict(raw)
    cases['cylinder']=line_case(((0.,0.),(.2,0.),(.2,.1),(0.,.1)))
    cases['cone']=line_case(((0.,0.),(.2,0.),(.1,.08)))
    for name,case in cases.items():
        old=solve(case);reference=quantities(case,old)
        base=Project(case,mesh_data=old.source_mesh_data)
        maps=[dict(radial_scale=2.,axial_scale=2.,axial_shear=0.),
              dict(radial_scale=1.2,axial_scale=.8,axial_shear=.3 if name=='cone' else 0.)]
        previous=None
        for i,mapping in enumerate(maps):
            target=transform_curved_project(base,mapping,rf_coordinates='axial')
            run=out/f'{name}-{i}';execute_project(target,run);saved=read_solution(run/'solution')
            a,c,b=(mapping[k] for k in ('radial_scale','axial_scale','axial_shear'))
            expected=np.column_stack((old.space.geometry.points_rz_m[:,0]*a,
                old.space.geometry.points_rz_m[:,0]*b+old.space.geometry.points_rz_m[:,1]*c))
            point_error=float(np.max(abs(saved.space.geometry.points_rz_m-expected)))
            volume_error=abs(target.case.curved_contour.volume_m3/(case.curved_contour.volume_m3*a*a*c)-1)
            assert point_error<1e-12 and volume_error<1e-11
            q=quantities(target.case,saved);similarity=None;analytic=None
            if a==c and b==0:
                similarity={k:abs(q[k]*(a if k=='frequency_hz' else 1)/reference[k]-1)
                    for k in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm')}
                assert max(similarity.values())<1e-10
            if name=='cylinder':
                exact=C0*float(jn_zeros(0,1)[0])/(2*math.pi*.1*a)
                analytic=abs(q['frequency_hz']/exact-1);assert analytic<1e-5
            tracking=None
            if previous is not None:
                from superfish_ng.affine_remesh_tracking import track_affine_remesh_modes
                relative=relative_affine_map(maps[i-1],mapping)
                tracking=track_affine_remesh_modes(previous,saved,['A'],mapping='affine_remesh',affine_map=relative,
                    sample_order=5,minimum_overlap=.8,minimum_assignment_margin=.05,
                    relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)['status']
                assert tracking=='PASS'
            previous=saved
            rows.append(dict(case=name,affine_map=mapping,point_error_m=point_error,volume_relative_error=volume_error,
                similarity=similarity,cylinder_analytic_frequency_error=analytic,relative_trial_tracking=tracking))
    assert fingerprints()==before
    (out/'validation.json').write_text(json.dumps(dict(passed=True,rows=rows,source_sha256=before,source_unchanged=True,
        scope='native line/ellipse/hyperbola Project transform, actual Job/replay, cone shear, volume scaling, four homogeneous Maxwell comparisons and two cylinder analytic frequencies; not general physical convergence'),indent=2)+'\n')
    print('Curved Project transform PASS')


if __name__=='__main__':main()

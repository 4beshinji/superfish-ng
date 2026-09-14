# SPDX-License-Identifier: Apache-2.0
"""Bessel mode-rank crossing through the harmonic shape Study comparison path."""
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tests')]
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.conics import LineSegment
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.frozen_curved_refinement import freeze_curved_refinement
from superfish_ng.studies import Study,execute_study
from superfish_ng.analytic import pillbox_spectrum
from superfish_ng.study_mode_tracking import build_study_mode_tracking,replay_study_mode_tracking
from test_curved_harmonic_study import harmonic_study_document,controls
from validate_large_curved_mesh_selection import fingerprints


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--remesh-study',action='store_true',help='cross ranks while changing to an independently generated initial mesh')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();before=fingerprints()
    vertices=((0.,0.),(.055,0.),(.055,.1),(0.,.1))
    contour=CurvedContour(tuple(LineSegment(vertices[i],vertices[(i+1)%4]) for i in range(4)),('axis','pec','pec','pec'),1e-14)
    case=Case((),curved_contour=contour,geometry_order=2,element_order=2,modes=3,
        curve_chord_tolerance_m=.001,curve_segments_per_curve=(1,1,1,1),contour_mesh=ContourMeshControls(.015),
        curved_refinement_steps=(Step('marked',(0,),1.),))
    raw=harmonic_study_document([1.,1.4]);raw.update(project=freeze_curved_refinement(Project(case)).to_dict(),parameter='length_scale',rf_coordinates='axis_fraction')
    raw['geometry_coefficients']={f'/curves/{index}/{end}_zr_m/0':[0.,.055] for index,end in ((0,'end'),(1,'start'),(1,'end'),(2,'start'))}
    if args.remesh_study:
        from dataclasses import replace
        from superfish_ng.mesh import make_mesh
        from superfish_ng.mesh_input import mesh_to_dict
        other=make_mesh(replace(case,contour_mesh=ContourMeshControls(.012),curved_refinement_steps=()))
        plan=dict(schema_version=1,source_mesh=mesh_to_dict(other),curved_refinement_levels=1,minimum_corner_angle_deg=1.)
        raw.update(study_version=4,kind='curved_remesh_sweep',mesh_schedule=dict(schema_version=1,breakpoints=[1.2],
            plans=[dict(kind='original'),dict(kind='replace',plan=plan)]))
    report=execute_study(Study.from_dict(raw),out/'study');rows=[]
    for point in report['points']:
        exact=pillbox_spectrum(.1,.055*point['value'],3)
        errors=[abs(mode['frequency_hz']/reference[0]-1) for mode,reference in zip(point['modes'],exact)]
        assert max(errors)<.003
        from superfish_ng.saved import read_solution
        native=read_solution(out/'study'/point['directory']/'solution')
        rows.append(dict(value=point['value'],source_triangles=len(native.source_mesh_data['triangles']),final_triangles=len(native.space.geometry.cell_nodes),analytical_mode_labels=[r[1] for r in exact],frequency_relative_errors=errors))
    request=dict(schema_version=1,study_run=str(out/'study'),initial_ids=rows[0]['analytical_mode_labels'],step_controls=[dict(controls(),minimum_overlap=.98,sample_order=8)])
    tracked=build_study_mode_tracking(request)
    assert tracked['status']=='PASS' and replay_study_mode_tracking(tracked)==tracked
    assert rows[0]['analytical_mode_labels']!=rows[1]['analytical_mode_labels']
    assert tracked['point_results'][1]['current_mode_ids']==rows[1]['analytical_mode_labels']
    if args.remesh_study:assert rows[0]['source_triangles']!=rows[1]['source_triangles']
    (out/'tracking.json').write_text(json.dumps(tracked,indent=2)+'\n')
    assert fingerprints()==before
    final=dict(status='PASS',study_kind=raw['kind'],scope='three analytical cylinder modes crossing ranks via declared geometry laws, harmonic mesh motion and curved piecewise comparison; not general branch recovery',
        rows=rows,tracked_ids=tracked['point_results'][1]['current_mode_ids'],new_fem_solves=2,source_files_unchanged=len(before),seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(final,indent=2)+'\n');(out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n');print(json.dumps(final))


if __name__=='__main__':main()

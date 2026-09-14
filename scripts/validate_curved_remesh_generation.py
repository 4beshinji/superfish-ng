# SPDX-License-Identifier: Apache-2.0
"""Generated curved interiors: CLI, independent geometry/Maxwell, RF and replay."""
import argparse
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tests')]
from superfish_ng.project import Project
from superfish_ng.studies import Study,execute_study
from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
from superfish_ng.curved_project_remesh import remesh_curved_project
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.study_mode_tracking import build_study_mode_tracking,replay_study_mode_tracking
from superfish_ng.saved import read_solution
from superfish_ng.jobs import execute_project
from superfish_ng.analytic import pillbox_tm010
from superfish_ng import Case
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.conics import LineSegment
from superfish_ng.mesh_controls import ContourMeshControls
from test_curved_harmonic_study import controls
from validate_curved_harmonic_study import worker
from validate_large_curved_mesh_selection import fingerprints,boundary_moments


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--workers-only',action='store_true')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic()
    settings_path=ROOT/'examples/curved_remesh_generation/settings.json';source_path=ROOT/'examples/curved_project_remesh/source-project.json'
    source=Project.load(source_path);settings=json.loads(settings_path.read_text())
    run=subprocess.run([sys.executable,'-m','superfish_ng','generate-curved-remesh-plan',str(source_path),'--settings',str(settings_path),'--out',str(out/'generated-plan.json')],capture_output=True,text=True,cwd=ROOT)
    (out/'generate-cli.log').write_text(run.stdout+run.stderr);assert run.returncode==0,run.stderr
    plan=json.loads((out/'generated-plan.json').read_text());assert generate_curved_remesh_plan(source,settings)==plan
    original=json.loads((ROOT/'examples/curved_remesh_study.json').read_text());original['mesh_schedule']['plans'][1]['plan']=plan
    (out/'generated-study.json').write_text(json.dumps(original,indent=2)+'\n')
    if args.workers_only:
        counts=[len(source.mesh_data['triangles']),len(plan['source_mesh']['triangles']),len(source.mesh_data['triangles'])]
        report=dict(status='PASS',new_fem_solves=3,worker=worker(out,original,counts),expected_initial_cells=counts,
                    scope='generated plan through real adaptive worker close/recreate/resume/full verification; not abnormal crash recovery')
    else:
        large=transform_curved_project(source,dict(radial_scale=2.,axial_scale=2.,axial_shear=0.),rf_coordinates='axial')
        large=replace(large,case=replace(large.case,contour_mesh=replace(large.case.contour_mesh,max_edge_m=2*source.case.contour_mesh.max_edge_m)))
        double=deepcopy(original);double['project']=large.to_dict();double['geometry_coefficients']={p:[2*c for c in cs] for p,cs in original['geometry_coefficients'].items()}
        scaled_settings=dict(settings,max_chord_edge_m=2*settings['max_chord_edge_m'],max_chord_triangle_area_m2=4*settings['max_chord_triangle_area_m2'])
        double['mesh_schedule']['plans'][1]['plan']=generate_curved_remesh_plan(large,scaled_settings)
        rows=[];solutions=[];overlaps=[]
        for label,raw in (('base',original),('double',double)):
            report=execute_study(Study.from_dict(raw),out/label)
            assert report['comparisons']==[] and report['numerical_status']=='UNVERIFIED'
            native=[read_solution(out/label/p['directory']/'solution') for p in report['points']];solutions.append(native)
            moments=[boundary_moments(s.space) for s in native]
            for key,factor in (('signed_area_m2',1.125),('signed_volume_m3',1.125**2)):
                assert abs(moments[1][key]/moments[0][key]/factor-1)<2e-13
            tracked=build_study_mode_tracking(dict(schema_version=1,study_run=str(out/label),initial_ids=['A'],step_controls=[controls()]))
            assert tracked['status']=='PASS' and replay_study_mode_tracking(tracked)==tracked
            (out/f'{label}-tracking.json').write_text(json.dumps(tracked,indent=2)+'\n')
            overlaps.append(tracked['history']['steps'][0]['tracking']['matches'][0]['minimum_principal_overlap'])
            rows.append(dict(label=label,moments=moments,rf=[p['modes'][0] for p in report['points']],base_cells=[len(s.source_mesh_data['triangles']) for s in native],final_cells=[len(s.space.geometry.cell_nodes) for s in native]))
        scaling=[]
        for point in range(2):
            a,b=solutions[0][point],solutions[1][point]
            np.testing.assert_array_equal(a.space.geometry.cell_nodes,b.space.geometry.cell_nodes)
            np.testing.assert_allclose(b.space.geometry.points_rz_m,2*a.space.geometry.points_rz_m,rtol=0,atol=4e-15)
            errors={key:abs(rows[1]['rf'][point][key]*(2 if key=='frequency_hz' else 1)/rows[0]['rf'][point][key]-1) for key in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs')}
            fields={};q=np.array([[.2,.2],[.3,.4],[.15,.6]])
            groups=[[s.fields_in_cell(cell,q) for cell in range(len(s.space.geometry.cell_nodes))] for s in (a,b)]
            for key in ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'):
                x,y=[np.concatenate([field[key] for field in group]) for group in groups]
                fields[key]=float(np.linalg.norm(x-2**1.5*y)/np.linalg.norm(x))
            assert max(errors.values())<2e-9 and max(fields.values())<2e-9
            scaling.append(dict(point=point,rf_relative_errors=errors,field_relative_errors=fields))
        vertices=((0.,0.),(.055,0.),(.055,.1),(0.,.1))
        contour=CurvedContour(tuple(LineSegment(vertices[i],vertices[(i+1)%4]) for i in range(4)),('axis','pec','pec','pec'),1e-14)
        case=Case((),curved_contour=contour,geometry_order=2,element_order=2,modes=1,curve_chord_tolerance_m=.001,
                  curve_segments_per_curve=(1,1,1,1),contour_mesh=ContourMeshControls(.015))
        exact=pillbox_tm010(.1,.055);analytical=[]
        for i,area in enumerate((.0001,.000025)):
            request=dict(settings,max_chord_edge_m=.025,max_chord_triangle_area_m2=area)
            replacement=generate_curved_remesh_plan(Project(case),request);project=remesh_curved_project(Project(case),replacement)
            target=out/f'cylinder-{i}';execute_project(project,target);native=read_solution(target/'solution');rf=native.results['modes'][0]
            error={key:abs(rf[key]/exact[key]-1) for key in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs')}
            assert error['frequency_hz']<.003 and max(v for k,v in error.items() if k!='frequency_hz')<.01
            analytical.append(dict(max_chord_triangle_area_m2=area,base_cells=len(replacement['source_mesh']['triangles']),final_cells=len(native.space.geometry.cell_nodes),relative_errors=error))
        report=dict(status='PASS',new_fem_solves=6,rows=rows,scaling=scaling,tracking_overlaps=overlaps,analytical_cylinder=analytical,
                    scope='independently generated interiors, explicit plans, native Study/replay, Green geometry/Maxwell fields and analytic cylinder f/RF; no general error bound')
    assert fingerprints()==before
    report.update(source_files_unchanged=len(before),seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','new_fem_solves','seconds')}))


if __name__=='__main__':main()

# SPDX-License-Identifier: Apache-2.0
"""Validate explicit initial mesh replacement with native fields and invariants."""
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
from superfish_ng.curved_project_remesh import remesh_curved_project
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.curved_harmonic_deformation import deform_curved_project
from superfish_ng.curved_same_domain_tracking import compare_quadratic_space_boundaries
from superfish_ng.saved import read_solution
from superfish_ng.jobs import execute_project,read_job
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking
from superfish_ng.study_shape_tracking import comparison_mesh
from superfish_ng.analytic import pillbox_tm010
from superfish_ng import Case
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.conics import LineSegment
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_to_dict
from test_curved_project_remesh import remesh_fixture
from test_curved_harmonic_deformation import space
from test_curved_piecewise_remesh_tracking import CONTROLS
from validate_large_curved_mesh_selection import fingerprints,boundary_moments


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    out=parser.parse_args().out.resolve();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();before=fingerprints();source,plan,geometry=remesh_fixture()
    source.save(out/'source-project.json');(out/'remesh-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    command=[sys.executable,'-m','superfish_ng','remesh-curved-project',str(out/'source-project.json'),
             '--plan',str(out/'remesh-plan.json'),'--out',str(out/'replacement-project.json')]
    cli=subprocess.run(command,cwd=ROOT,capture_output=True,text=True);(out/'cli.log').write_text(cli.stdout+cli.stderr)
    assert cli.returncode==0
    replacement=Project.load(out/'replacement-project.json')
    assert replacement.to_dict()==remesh_curved_project(source,plan).to_dict()
    scale=dict(radial_scale=2.,axial_scale=2.,axial_shear=0.)
    source2=transform_curved_project(source,scale,rf_coordinates='axial')
    candidate=replace(source,case=replace(source.case,curved_refinement_steps=()),mesh_data=deepcopy(plan['source_mesh']))
    candidate2=transform_curved_project(candidate,scale,rf_coordinates='axial')
    plan2=deepcopy(plan);plan2['source_mesh']=candidate2.mesh_data
    replacement2=remesh_curved_project(source2,plan2)
    moved=[deform_curved_project(p,geometry,rf_coordinates='fixed',minimum_corner_angle_deg=1.) for p in (source,replacement)]
    projects=[source,replacement,source2,replacement2,*moved]
    labels=['original-1','replacement-1','original-2','replacement-2','moved-original','moved-replacement']
    solutions=[];rows=[]
    for label,project in zip(labels,projects):
        result=execute_project(project,out/label);assert result['status']=='complete'
        native=read_solution(out/label/'solution');solutions.append(native)
        rows.append(dict(label=label,base_cells=len(project.mesh_data['triangles']),cells=len(native.space.geometry.cell_nodes),
            moments=boundary_moments(native.space),rf=native.results['modes'][0]))
        assert read_job(out/label)['status']=='complete'
    for a,b in ((0,1),(2,3),(4,5)):
        compare_quadratic_space_boundaries(projects[a].case,solutions[a].space,projects[b].case,solutions[b].space)
        for key in rows[a]['moments']:assert abs(rows[a]['moments'][key]/rows[b]['moments'][key]-1)<2e-13
    scaling=[]
    for a,b in ((0,2),(1,3)):
        errors={'frequency_hz':abs(2*rows[b]['rf']['frequency_hz']/rows[a]['rf']['frequency_hz']-1)}
        for key in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs'):
            errors[key]=abs(rows[b]['rf'][key]/rows[a]['rf'][key]-1)
        fields={};q=np.array([[.2,.2],[.3,.4],[.15,.6]])
        groups=[[s.fields_in_cell(cell,q) for cell in range(len(s.space.geometry.cell_nodes))] for s in (solutions[a],solutions[b])]
        for key in ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'):
            x,y=[np.concatenate([field[key] for field in group]) for group in groups]
            fields[key]=float(np.linalg.norm(2**1.5*y-x)/np.linalg.norm(x))
        assert max(errors.values())<2e-9 and max(fields.values())<2e-9
        assert abs(rows[b]['moments']['signed_volume_m3']/rows[a]['moments']['signed_volume_m3']/8-1)<2e-13
        scaling.append(dict(label=labels[a],rf_relative_errors=errors,field_relative_errors=fields))
    tracking=[]
    for a,b,controls in ((0,1,dict(CONTROLS,mapping='curved_same_domain')),
                          (0,5,dict(CONTROLS,comparison_meshes=[comparison_mesh(source),comparison_mesh(moved[0])]))):
        path=out/f'tracking-{a}-{b}.json'
        document=save_mode_tracking(dict(schema_version=1,previous_run=str(out/labels[a]/'solution'),current_run=str(out/labels[b]/'solution'),
            previous_ids=['A'],controls=controls),path)
        assert document['status']=='PASS' and read_mode_tracking(path)==document
        tracking.append(dict(source=labels[a],target=labels[b],minimum_overlap=document['tracking']['matches'][0]['minimum_principal_overlap']))
    # A separate cylindrical analytical reference checks frequency and RF,
    # rather than treating remeshing equality as discretization accuracy.
    vertices=((0.,0.),(.055,0.),(.055,.1),(0.,.1))
    contour=CurvedContour(tuple(LineSegment(vertices[i],vertices[(i+1)%4]) for i in range(4)),('axis','pec','pec','pec'),1e-14)
    case=Case((),curved_contour=contour,geometry_order=2,element_order=2,modes=1,
        curve_chord_tolerance_m=.001,curve_segments_per_curve=(1,1,1,1),contour_mesh=ContourMeshControls(.015),curved_refinement_levels=1)
    cylinder=Project(case,mesh_data=mesh_to_dict(make_mesh(case)))
    independent=replace(case,curved_refinement_levels=0,contour_mesh=replace(case.contour_mesh,max_edge_m=.012))
    cylinder_plan=dict(schema_version=1,source_mesh=mesh_to_dict(make_mesh(independent)),curved_refinement_levels=1,minimum_corner_angle_deg=1.)
    rebuilt=remesh_curved_project(cylinder,cylinder_plan)
    exact=pillbox_tm010(.1,.055);analytical=[]
    for label,project in (('cylinder-original',cylinder),('cylinder-replacement',rebuilt)):
        execute_project(project,out/label);native=read_solution(out/label/'solution');rf=native.results['modes'][0]
        errors={key:abs(rf[key]/exact[key]-1) for key in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs')}
        assert errors['frequency_hz']<.003
        assert max(value for key,value in errors.items() if key!='frequency_hz')<.01
        analytical.append(dict(label=label,base_cells=len(project.mesh_data['triangles']),cells=len(native.space.geometry.cell_nodes),relative_errors=errors))
    assert before==fingerprints()
    report=dict(status='PASS',new_fem=8,rows=rows,scaling=scaling,tracking=tracking,analytical_cylinder=analytical,
        source_files_unchanged=len(before),seconds=time.monotonic()-started,
        scope='explicit initial mesh and new frozen history on an identical represented quadratic boundary; CLI, native replay, independent Green/Maxwell and cylindrical f/RF; not an automatic correspondence or general error bound')
    (out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n');(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','new_fem','tracking','analytical_cylinder','seconds')}))


if __name__=='__main__':main()

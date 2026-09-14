# SPDX-License-Identifier: Apache-2.0
"""Affine Study: independent geometry/scaling, analytical rank crossing and bisection."""
import argparse
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study,execute_study
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.conics import LineSegment
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.frozen_curved_refinement import freeze_curved_refinement
from superfish_ng.saved import read_solution
from superfish_ng.analytic import pillbox_spectrum
from superfish_ng.study_mode_tracking import build_study_mode_tracking,replay_study_mode_tracking
from superfish_ng.adaptive_study import execute_adaptive_study,replay_adaptive_study
from test_curved_affine_study import affine_study_document,controls
from test_frozen_curved_refinement import native_space
from validate_large_curved_mesh_selection import fingerprints,boundary_moments


def verify_workers(out):
    from superfish_ng.jobs import JobManager
    started=time.monotonic();before=fingerprints();manager=JobManager(out/'workspace');records=[]
    def wait(identifier):
        deadline=time.monotonic()+300
        while time.monotonic()<deadline:
            state=manager.status(identifier)
            if state['status'] not in ('queued','running'):
                state=manager.status(identifier,verify=True)
                assert state['status']=='complete',state
                return state
            time.sleep(.1)
        raise AssertionError(f'Study worker remains active: {identifier}')
    try:
        for adaptive in (False,True):
            raw=affine_study_document([1.,1.5] if adaptive else [1.,2.])
            control=controls()
            if adaptive:
                raw['affine_coefficients']=dict(radial_scale=[1.],axial_scale=[0.,1.],axial_shear=[0.]);control['minimum_overlap']=1.
            request=dict(schema_version=1,study=raw,initial_ids=['A'],step_controls=[control])
            if adaptive:request['adaptive']=dict(max_depth=1,max_attempts=4,minimum_parameter_step=.001)
            prefix='adaptive' if adaptive else 'tracked';filename=f'{prefix}-study-results.json'
            (out/f'{prefix}-request.json').write_text(json.dumps(request,indent=2)+'\n')
            first=(manager.start_adaptive_study(request,max_new_attempts=1) if adaptive else manager.start_tracked_study(request,max_new_points=1))
            state=wait(first);assert state['tracking_status']=='PAUSED'
            checkpoint=json.loads((manager.directory(first)/filename).read_text())
            manager.close();manager=JobManager(out/'workspace')
            second=(manager.start_adaptive_study(request,checkpoint=checkpoint) if adaptive else manager.start_tracked_study(request,checkpoint=checkpoint))
            state=wait(second);assert state['tracking_status']==('UNVERIFIED' if adaptive else 'COMPLETE')
            result=json.loads((manager.directory(second)/filename).read_text())
            if adaptive:
                assert result['points'][:2]==checkpoint['points']
                assert result['attempts'][-1]['correspondence']['request']['controls']['affine_map']['axial_scale']==1.25
            else:assert result['point_runs'][0]==checkpoint['point_runs'][0]
            manager.close();manager=JobManager(out/'workspace')
            assert manager.status(second,verify=True)['tracking_status']==state['tracking_status']
            records.append(dict(kind=prefix,first_job=first,second_job=second,final_state=state,original_request_preserved=result['request']==request))
            print(f'{prefix} worker pause/restart/resume: {state["tracking_status"]}',flush=True)
    finally:manager.close()
    assert fingerprints()==before
    report=dict(status='PASS',scope='real curved affine tracked/adaptive workers, manager restart and unchanged checkpoint ancestry',records=records,
        dedicated_new_fem_solves=5,source_files_unchanged=len(before),seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('status','dedicated_new_fem_solves','seconds')}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--workers-only',action='store_true',help='verify new affine requests through worker pause/restart/resume instead of repeating numerical fixtures')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    if args.workers_only:return verify_workers(out)
    start=time.monotonic();before=fingerprints()
    original=affine_study_document()
    source=Study.from_dict(original).project;space=native_space(source);moments=boundary_moments(space);_,mass=assemble_curved(space,quadrature_order=12)
    rows=[];unit_results=[]
    for unit in ('1','m'):
        raw=deepcopy(original);raw['parameter_unit']=unit
        if unit=='m':
            raw['values']=[.1,.2]
            raw['affine_coefficients']={key:[value*10**i for i,value in enumerate(coefficients)] for key,coefficients in raw['affine_coefficients'].items()}
        request=out/f'study-{unit}.json';request.write_text(json.dumps(raw,indent=2)+'\n')
        target=out/f'cli-{unit}'
        result=subprocess.run([sys.executable,'-m','superfish_ng','study',str(request),'--out',str(target)],capture_output=True,text=True)
        (out/f'cli-{unit}.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stderr
        report=json.loads((target/'study-results.json').read_text());assert report['comparisons']==[] and report['numerical_status']=='UNVERIFIED'
        solutions=[]
        for i,point in enumerate(report['points']):
            solution=read_solution(target/point['directory']/'solution');solutions.append(solution)
            x=(1.,2.)[i];a,c,b=2*x,.5*x,0.
            expected=np.column_stack((a*space.geometry.points_rz_m[:,0],b*space.geometry.points_rz_m[:,0]+c*space.geometry.points_rz_m[:,1]))
            np.testing.assert_allclose(solution.space.geometry.points_rz_m,expected,rtol=0,atol=2e-15)
            np.testing.assert_array_equal(solution.space.geometry.cell_nodes,space.geometry.cell_nodes)
            assert solution.case.curved_refinement_steps==source.case.curved_refinement_steps
            actual=boundary_moments(solution.space)
            assert abs(actual['signed_area_m2']/moments['signed_area_m2']/(a*c)-1)<1e-12
            assert abs(actual['signed_volume_m3']/moments['signed_volume_m3']/(a*a*c)-1)<1e-12
            _,target_mass=assemble_curved(solution.space,quadrature_order=12)
            error=float(np.linalg.norm((target_mass-a**4*c*mass).toarray())/np.linalg.norm((a**4*c*mass).toarray()));assert error<1e-12
            rows.append(dict(unit=unit,value=raw['values'][i],mass_relative_error=error,boundary_moments=actual,rf=point['modes'][0]))
        unit_results.append(solutions)
    scaling=[]
    for solutions in unit_results:
        old,new=solutions;left,right=[solution.results['modes'][0] for solution in solutions]
        errors={key:abs(right[key]*(2 if key=='frequency_hz' else 1)/left[key]-1) for key in
            ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs')}
        assert max(errors.values())<2e-9
        field_errors={};q=np.array([[.2,.2],[.3,.4],[.15,.6]])
        fields=[[solution.fields_in_cell(cell,q) for cell in range(len(space.geometry.cell_nodes))] for solution in solutions]
        for key in ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'):
            a,b=[np.concatenate([field[key] for field in group]) for group in fields]
            field_errors[key]=float(np.linalg.norm(a-2**1.5*b)/np.linalg.norm(a))
        assert max(field_errors.values())<2e-9
        scaling.append(dict(rf_relative_errors=errors,field_relative_errors=field_errors))
    for first,second in zip(*unit_results):
        assert first.case==second.case
        np.testing.assert_array_equal(first.u,second.u)
    # A smooth ellipsoid under shear protrudes past its axis endpoints and is
    # correctly rejected by Case. This cone keeps that physical z-range valid.
    cone_vertices=((0.,0.),(.2,0.),(.1,.1))
    cone=CurvedContour(tuple(LineSegment(cone_vertices[i],cone_vertices[(i+1)%3]) for i in range(3)),('axis','pec','pec'),1e-14)
    cone_case=Case((),curved_contour=cone,geometry_order=2,element_order=2,modes=1,
        curve_chord_tolerance_m=.001,curve_segments_per_curve=(1,1,1),contour_mesh=ContourMeshControls(.035),
        curved_refinement_steps=(Step('marked',(0,),1.),))
    raw=affine_study_document();raw['project']=freeze_curved_refinement(Project(cone_case)).to_dict()
    raw['affine_coefficients']['axial_shear']=[0.,.125]
    (out/'sheared-cone-study.json').write_text(json.dumps(raw,indent=2)+'\n')
    study=Study.from_dict(raw);base=native_space(study.project);base_moments=boundary_moments(base)
    _,base_mass=assemble_curved(base,quadrature_order=12);sheared=[]
    for value,project in zip(study.values,study.projects()):
        actual=native_space(project);a,c,b=2*value,.5*value,.125*value
        coordinates=base.geometry.points_rz_m
        expected=np.column_stack((a*coordinates[:,0],b*coordinates[:,0]+c*coordinates[:,1]))
        np.testing.assert_allclose(actual.geometry.points_rz_m,expected,rtol=0,atol=2e-15)
        actual_moments=boundary_moments(actual)
        assert abs(actual_moments['signed_volume_m3']/base_moments['signed_volume_m3']/(a*a*c)-1)<1e-12
        _,actual_mass=assemble_curved(actual,quadrature_order=12)
        error=float(np.linalg.norm((actual_mass-a**4*c*base_mass).toarray())/np.linalg.norm((a**4*c*base_mass).toarray()));assert error<1e-12
        sheared.append(dict(value=value,mass_relative_error=error,moments=actual_moments,scope='geometry and assembly; no separate cone eigensolve'))
    vertices=((0.,0.),(.055,0.),(.055,.1),(0.,.1))
    contour=CurvedContour(tuple(LineSegment(vertices[i],vertices[(i+1)%4]) for i in range(4)),('axis','pec','pec','pec'),1e-14)
    case=Case((),curved_contour=contour,geometry_order=2,element_order=2,modes=3,
        curve_chord_tolerance_m=.001,curve_segments_per_curve=(1,1,1,1),contour_mesh=ContourMeshControls(.015),
        curved_refinement_steps=(Step('marked',(0,),1.),))
    raw=affine_study_document([1.,1.4]);raw['project']=freeze_curved_refinement(Project(case)).to_dict()
    raw['affine_coefficients']=dict(radial_scale=[1.],axial_scale=[0.,1.],axial_shear=[0.])
    cylinder=execute_study(Study.from_dict(raw),out/'cylinder')
    analytical=[]
    for point in cylinder['points']:
        exact=pillbox_spectrum(.1,.055*point['value'],3)
        errors=[abs(mode['frequency_hz']/reference[0]-1) for mode,reference in zip(point['modes'],exact)]
        assert max(errors)<.003
        analytical.append(dict(value=point['value'],labels=[r[1] for r in exact],frequency_relative_errors=errors))
    tracked=build_study_mode_tracking(dict(schema_version=1,study_run=str(out/'cylinder'),initial_ids=analytical[0]['labels'],step_controls=[dict(controls(),minimum_overlap=.98,sample_order=8)]))
    assert tracked['status']=='PASS' and replay_study_mode_tracking(tracked)==tracked
    assert analytical[0]['labels']!=analytical[1]['labels']
    assert tracked['point_results'][1]['current_mode_ids']==analytical[1]['labels']
    (out/'cylinder-tracking.json').write_text(json.dumps(tracked,indent=2)+'\n')
    raw=affine_study_document([1.,1.5]);raw['affine_coefficients']=dict(radial_scale=[1.],axial_scale=[0.,1.],axial_shear=[0.])
    request=dict(schema_version=1,study=raw,initial_ids=['A'],step_controls=[dict(controls(),minimum_overlap=1.)],
        adaptive=dict(max_depth=1,max_attempts=4,minimum_parameter_step=.001))
    adaptive=execute_adaptive_study(request,out/'adaptive');assert replay_adaptive_study(adaptive)==adaptive
    assert adaptive['attempts'][0]['decision']=='BISECT'
    pair_rows=[]
    for attempt in adaptive['attempts']:
        a,b=[adaptive['points'][attempt[key]]['value'] for key in ('previous_point','current_point')]
        mapping=attempt['correspondence']['request']['controls']['affine_map']
        assert abs(mapping['radial_scale']-1)<1e-14 and abs(mapping['axial_scale']-b/a)<1e-14 and mapping['axial_shear']==0
        pair_rows.append(dict(previous_value=a,current_value=b,map=mapping,decision=attempt['decision'],correspondence_status=attempt['correspondence']['status']))
    assert any(point['value']==1.25 for point in adaptive['points'])
    assert fingerprints()==before
    report=dict(status='PASS',scope='declared affine shape Study, independent geometry/Maxwell scaling, unit equivalence, analytical mode-rank crossing and actual inserted-point maps; no physical convergence certificate',
        rows=rows,scaling=scaling,sheared_cone_geometry=sheared,cylinder=analytical,cylinder_tracking_status=tracked['status'],
        adaptive_status=adaptive['status'],adaptive_pairs=pair_rows,dedicated_new_fem_solves=6+len(adaptive['points']),
        source_files_unchanged=len(before),seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('status','cylinder','adaptive_status','adaptive_pairs','dedicated_new_fem_solves','seconds')}))


if __name__=='__main__':main()

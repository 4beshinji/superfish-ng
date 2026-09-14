# SPDX-License-Identifier: Apache-2.0
"""Independent curved shape Study laws, geometry, RF scaling and worker replay."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tests')]
from superfish_ng.studies import Study
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.saved import read_solution
from superfish_ng.study_mode_tracking import build_study_mode_tracking,replay_study_mode_tracking
from superfish_ng.jobs import JobManager
from test_curved_harmonic_study import harmonic_study_document,controls
from validate_large_curved_mesh_selection import fingerprints,boundary_moments


def worker(out,document=None):
    request=dict(schema_version=1,study=harmonic_study_document() if document is None else document,initial_ids=['A'],step_controls=[dict(controls(),minimum_overlap=1.)],
        adaptive=dict(max_depth=1,max_attempts=4,minimum_parameter_step=.001))
    (out/'request.json').write_text(json.dumps(request,indent=2)+'\n')
    manager=JobManager(out/'workspace')
    def wait(identifier):
        deadline=time.monotonic()+600
        while time.monotonic()<deadline:
            state=manager.status(identifier)
            if state['status'] not in ('queued','running'):
                state=manager.status(identifier,verify=True);assert state['status']=='complete',state
                return state
            time.sleep(.1)
        raise AssertionError(f'adaptive worker remains active: {identifier}')
    try:
        first=manager.start_adaptive_study(request,max_new_attempts=1);state=wait(first)
        assert state['tracking_status']=='PAUSED'
        checkpoint=json.loads((manager.directory(first)/'adaptive-study-results.json').read_text())
        assert checkpoint['attempts'][0]['decision']=='BISECT'
        manager.close();manager=JobManager(out/'workspace')
        second=manager.start_adaptive_study(request,checkpoint=checkpoint);state=wait(second)
        result=json.loads((manager.directory(second)/'adaptive-study-results.json').read_text())
        assert state['tracking_status']=='UNVERIFIED' and result['points'][:2]==checkpoint['points']
        assert result['points'][2]['value']==.5 and result['attempts'][1]['decision']=='STOP'
        first_mesh=result['attempts'][0]['correspondence']['request']['controls']['comparison_meshes'][1]
        second_mesh=result['attempts'][1]['correspondence']['request']['controls']['comparison_meshes'][1]
        assert first_mesh!=second_mesh and result['request']==request
        if request['study']['kind']=='curved_remesh_sweep':
            counts=[len(read_solution(Path(p['run'])/'solution').source_mesh_data['triangles']) for p in result['points']]
            assert counts==[26,28,26],counts
            assert len(first_mesh['source_mesh']['triangles'])==len(second_mesh['source_mesh']['triangles'])==26
        manager.close();manager=JobManager(out/'workspace')
        assert manager.status(second,verify=True)['tracking_status']=='UNVERIFIED'
        return dict(first_job=first,second_job=second,status=state,original_points_preserved=True,actual_midpoint=.5,
            endpoint_and_midpoint_meshes_differ=True,new_fem_solves=3)
    finally:manager.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--workers-only',action='store_true')
    parser.add_argument('--remesh-study',action='store_true',help='validate Study v4 value-based initial mesh replacement')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();before=fingerprints()
    from test_curved_remesh_study import remesh_study_document
    original=remesh_study_document() if args.remesh_study else harmonic_study_document()
    if args.workers_only:
        report=dict(status='PASS',scope='real adaptive worker pause/JobManager recreation/resume/full revalidation; not an abnormal crash recovery test',worker=worker(out,original),new_fem_solves=3)
    else:
        variants=[('base',original)]
        unit=deepcopy(original);unit['values']=[0.,.1];unit['parameter_unit']='m'
        unit['geometry_coefficients']={k:[c*10**i for i,c in enumerate(cs)] for k,cs in unit['geometry_coefficients'].items()};variants.append(('metres',unit))
        if args.remesh_study:unit['mesh_schedule']['breakpoints']=[v/10 for v in unit['mesh_schedule']['breakpoints']]
        large=deepcopy(original);large['project']=transform_curved_project(Study.from_dict(original).project,
            dict(radial_scale=2.,axial_scale=2.,axial_shear=0.),rf_coordinates='axial').to_dict()
        large['geometry_coefficients']={k:[2*c for c in cs] for k,cs in large['geometry_coefficients'].items()};variants.append(('double',large))
        if args.remesh_study:
            for entry in large['mesh_schedule']['plans']:
                if entry['kind']=='replace':
                    mesh=entry['plan']['source_mesh'];mesh['points']=[[2*c for c in point] for point in mesh['points']]
        rows=[];solutions=[];tracking=[]
        for name,raw in variants:
            request=out/f'{name}.json';request.write_text(json.dumps(raw,indent=2)+'\n');target=out/name
            result=subprocess.run([sys.executable,'-m','superfish_ng','study',str(request),'--out',str(target)],capture_output=True,text=True,cwd=ROOT)
            (out/f'{name}-cli.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stderr
            report=json.loads((target/'study-results.json').read_text());assert report['comparisons']==[] and report['numerical_status']=='UNVERIFIED'
            group=[];geometry=[]
            for point in report['points']:
                native=read_solution(target/point['directory']/'solution');group.append(native);geometry.append(boundary_moments(native.space))
            for key,factor in (('signed_area_m2',1.125),('signed_volume_m3',1.125**2)):
                assert abs(geometry[1][key]/geometry[0][key]/factor-1)<1e-12
            tracked=build_study_mode_tracking(dict(schema_version=1,study_run=str(target),initial_ids=['A'],step_controls=[controls()]))
            assert tracked['status']=='PASS' and replay_study_mode_tracking(tracked)==tracked
            (out/f'{name}-tracking.json').write_text(json.dumps(tracked,indent=2)+'\n')
            tracking.append(tracked['history']['steps'][0]['tracking']['matches'][0]['minimum_principal_overlap'])
            rows.append(dict(name=name,geometry=geometry,rf=[p['modes'][0] for p in report['points']],triangles=[len(s.space.geometry.cell_nodes) for s in group]))
            solutions.append(group)
        comparisons=[]
        for variant,scale in ((1,1.),(2,2.)):
            for point in range(2):
                old,new=solutions[0][point],solutions[variant][point]
                np.testing.assert_array_equal(old.space.geometry.cell_nodes,new.space.geometry.cell_nodes)
                np.testing.assert_allclose(new.space.geometry.points_rz_m,scale*old.space.geometry.points_rz_m,rtol=0,atol=4e-15)
                error={k:abs(rows[variant]['rf'][point][k]*(scale if k=='frequency_hz' else 1)/rows[0]['rf'][point][k]-1) for k in
                    ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs')}
                q=np.array([[.2,.2],[.3,.4],[.15,.6]]);groups=[[s.fields_in_cell(cell,q) for cell in range(len(s.space.geometry.cell_nodes))] for s in (old,new)]
                fields={}
                for key in ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'):
                    a,b=[np.concatenate([f[key] for f in group]) for group in groups]
                    fields[key]=float(np.linalg.norm(a-scale**1.5*b)/np.linalg.norm(a))
                assert max(error.values())<2e-9 and max(fields.values())<2e-9
                comparisons.append(dict(variant=rows[variant]['name'],point=point,rf_relative_errors=error,field_relative_errors=fields))
        report=dict(status='PASS',scope='real CLI shape Study, independent Green ratios, unit equivalence, Maxwell RF/field scaling and full saved tracking; no continuum physical error bound',
            rows=rows,comparisons=comparisons,tracking_overlaps=tracking,new_fem_solves=6)
    assert fingerprints()==before
    report.update(study_kind=original['kind'],seconds=time.monotonic()-started,source_files_unchanged=len(before))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','new_fem_solves','seconds')}))


if __name__=='__main__':main()

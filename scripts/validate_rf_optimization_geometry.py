# SPDX-License-Identifier: Apache-2.0
"""Real multivariate RF searches with independent Green and Maxwell invariants."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from superfish_ng.project import Project
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.rf_optimization import read_rf_optimization,replay_rf_optimization
from superfish_ng.saved import read_solution
from superfish_ng.rf import quantities
from validate_large_curved_mesh_selection import fingerprints,boundary_moments


def variant(original,scale,dimensionless):
    request=deepcopy(original)
    if scale!=1:
        request['project']=transform_curved_project(Project.from_dict(request['project']),
            dict(radial_scale=scale,axial_scale=scale,axial_shear=0.),rf_coordinates='axial').to_dict()
        for variable in request['variables']:
            if variable['unit']=='m':
                for key in ('lower','upper','initial','step','tolerance'):variable[key]*=scale
        for terms in request['geometry_terms'].values():
            for term in terms:term['coefficient']*=scale/scale**term['powers'][0]
        request['objective_improvement']/=scale
    if dimensionless:
        variable=request['variables'][0];variable.update(name='radius_factor',unit='1')
        for key in ('lower','upper','initial','step','tolerance'):variable[key]/=.08
        for terms in request['geometry_terms'].values():
            for term in terms:term['coefficient']*=.08**term['powers'][0]
    return request


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();before=fingerprints();original=json.loads((ROOT/'examples/optimization/curved_geometry_rf.json').read_text())
    reports=[];solutions=[];rows=[];new_fem=0
    for name,scale,dimensionless in (('base',1.,False),('dimensionless',1.,True),('double',2.,False)):
        request=variant(original,scale,dimensionless);path=out/f'{name}.json';path.write_text(json.dumps(request,indent=2)+'\n')
        first=out/name/'first';rest=out/name/'rest'
        for i,command in enumerate((['optimize-rf',str(path),'--out',str(first),'--max-new-trials','1'],
            ['replay-rf-optimization',str(first/'checkpoint-001.json')],
            ['resume-rf-optimization',str(first/'checkpoint-001.json'),'--out',str(rest)])):
            result=subprocess.run([sys.executable,'-m','superfish_ng',*command],capture_output=True,text=True,cwd=ROOT)
            (out/f'{name}-cli-{i}.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stderr
        report=read_rf_optimization(rest/'checkpoint-004.json');reports.append(report);new_fem+=report['completed_fem_solves']
        assert report['status']=='SEARCH_COMPLETE' and report['completed_fem_solves']==12
        assert report['decision']['search_stop']=='TRIAL_LIMIT'
        assert report['trials'][1]['values'][0]>report['trials'][0]['values'][0]
        assert report['trials'][2]['values'][1]!=report['trials'][1]['values'][1]
        assert report['trials'][-1]['assessment']['objective']['eligible_value']<report['trials'][0]['assessment']['objective']['eligible_value']
        group=[];data=[];prefix=request['project']['case']['mesh']['curved_refinement_steps']
        for trial,directory in zip(report['trials'],report['trial_directories']):
            levels=[];level_rows=[]
            assessment=trial['assessment']['assessment'];assert assessment['refinement_sequence']['fixed_prefix']==prefix
            counts=[1,2,3] if trial['phase']=='final' else [0,1,2]
            assert [r['refinement_level'] for r in assessment['rows']]==counts
            for level,count in enumerate(counts):
                native=read_solution(Path(directory)/f'level-{level}/solution');levels.append(native)
                assert native.case.to_dict()['mesh']['curved_refinement_steps']==prefix+[dict(kind='uniform')]*count
                level_rows.append(dict(triangles=len(native.space.geometry.cell_nodes),dofs=len(native.u),moments=boundary_moments(native.space),rf=quantities(native.case,native)))
            for row in level_rows[1:]:
                for key in row['moments']:assert abs(row['moments'][key]/level_rows[0]['moments'][key]-1)<2e-12
            group.append(levels);data.append(level_rows)
        reference=data[0][0]['moments']
        for trial,levels in zip(report['trials'],data):
            radius=trial['values'][0]*(.08 if dimensionless else 1);ratio=radius/(.08*scale)
            for row in levels:
                for key,power in (('signed_area_m2',1),('signed_volume_m3',2)):
                    assert abs(row['moments'][key]/reference[key]/ratio**power-1)<2e-12
        forged=deepcopy(report);forged['trials'][-1]['tracking']['request']['controls']['comparison_meshes'][1]['curved_refinement_steps']=[]
        try:replay_rf_optimization(forged)
        except ValueError:pass
        else:raise AssertionError('forged comparison history passed replay')
        rows.append(dict(name=name,status=report['status'],values=[t['values'] for t in report['trials']],levels=data));solutions.append(group)
        print(f'{name}: 12 FEM and both variable polls PASS',flush=True)
    comparisons=[]
    for variant_index,scale in ((1,1.),(2,2.)):
        for trial in range(4):
            for level in range(3):
                old,new=solutions[0][trial][level],solutions[variant_index][trial][level]
                np.testing.assert_array_equal(old.space.geometry.cell_nodes,new.space.geometry.cell_nodes)
                np.testing.assert_allclose(scale*old.space.geometry.points_rz_m,new.space.geometry.points_rz_m,rtol=0,atol=5e-15)
                rf={k:abs(rows[variant_index]['levels'][trial][level]['rf'][k]*(scale if k=='frequency_hz' else 1)/rows[0]['levels'][trial][level]['rf'][k]-1)
                    for k in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs')}
                intervals=[]
                for key,interval in reports[0]['trials'][trial]['assessment']['assessment']['rows'][level]['intervals'].items():
                    other=reports[variant_index]['trials'][trial]['assessment']['assessment']['rows'][level]['intervals'][key]
                    intervals.extend(abs(y*(scale if key=='frequency_hz' else 1)/x-1) for x,y in zip(interval,other))
                groups=[[s.fields_in_cell(c,np.array([[.2,.3],[.4,.2]])) for c in range(len(s.space.geometry.cell_nodes))] for s in (old,new)]
                fields={}
                for key in ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'):
                    a,b=[np.concatenate([f[key] for f in g]) for g in groups]
                    fields[key]=float(np.linalg.norm(a-scale**1.5*b)/np.linalg.norm(a))
                assert max(list(rf.values())+list(fields.values())+intervals)<2e-9
                comparisons.append(dict(variant=rows[variant_index]['name'],trial=trial,level=level,rf_relative_errors=rf,field_relative_errors=fields,max_interval_relative_error=max(intervals)))
    assert fingerprints()==before
    report=dict(status='PASS',new_fem_solves=new_fem,rows=rows,comparisons=comparisons,seconds=time.monotonic()-started,source_sha256=before,source_unchanged=True,
        scope='three multivariate non-affine searches, both design-variable polls, CLI pause/resume and native replay, independent Green/Maxwell RF and field scaling with frozen histories; no continuum error or optimality certificate')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ('status','new_fem_solves','seconds')}))


if __name__=='__main__':main()

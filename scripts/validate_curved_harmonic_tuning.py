# SPDX-License-Identifier: Apache-2.0
"""Native non-affine tunes, Green/Maxwell invariants and analytical rank crossing."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tests')]
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.project import Project
from superfish_ng.tuning import execute_tune,replay_tune
from superfish_ng.saved import read_solution
from superfish_ng.rf import quantities
from superfish_ng.constants import C0
from validate_large_curved_mesh_selection import fingerprints,boundary_moments


def cli(out,*args):
    result=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,args)],capture_output=True,text=True,cwd=ROOT)
    with (out/'cli.log').open('a') as stream:stream.write(json.dumps(list(map(str,args)))+'\n'+result.stdout+result.stderr)
    assert result.returncode==0,result.stderr


def crossing_request():
    from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
    from superfish_ng.frozen_curved_refinement import freeze_curved_refinement
    from dataclasses import replace
    from validate_curved_tuning import request
    old=request();project=Project.from_dict(old['project'])
    old['project']=freeze_curved_refinement(replace(project,case=replace(project.case,
        curved_refinement_steps=(Step('marked',(0,),1.),)))).to_dict()
    old.update(schema_version=5,rf_coordinates='axis_fraction',minimum_corner_angle_deg=1.)
    old.pop('affine_coefficients')
    old['controls']['mapping']='piecewise_remesh'
    old['geometry_coefficients']={f'/curves/{index}/{end}_zr_m/0':[0.,1.] for index,end in ((0,'end'),(1,'start'),(1,'end'),(2,'start'))}
    return old


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();before=fingerprints();original=json.loads((ROOT/'examples/tuning/curved_harmonic.json').read_text())
    rows=[];solutions=[];comparisons=[];new_fem=0
    for name,scale,unit in (('base',1.,'1'),('metres',1.,'m'),('double',2.,'1')):
        request=deepcopy(original)
        if scale!=1:
            request['project']=transform_curved_project(Project.from_dict(request['project']),
                dict(radial_scale=scale,axial_scale=scale,axial_shear=0.),rf_coordinates='axial').to_dict()
            request['geometry_coefficients']={p:[scale*c for c in cs] for p,cs in request['geometry_coefficients'].items()}
            for key in ('target_hz','frequency_tolerance_hz','mesh_frequency_tolerance_hz'):request[key]/=scale
        if unit=='m':
            request.update(parameter_unit='m',bounds=[0.,.1],parameter_tolerance=request['parameter_tolerance']/10)
            request['geometry_coefficients']={p:[c*10**i for i,c in enumerate(cs)] for p,cs in request['geometry_coefficients'].items()}
        path=out/f'{name}.json';path.write_text(json.dumps(request,indent=2)+'\n')
        cli(out,'tune',path,'--out',out/name/'first','--max-new-trials','2')
        first=out/name/'first/checkpoint-002.json'
        cli(out,'resume-tune',first,'--out',out/name/'rest')
        result=json.loads((out/name/'rest/checkpoint-004.json').read_text())
        assert result['status']=='TUNED' and len(result['trials'])==4
        assert abs(result['decision']['value']/(.05 if unit=='m' else .5)-1)<1e-12
        cli(out,'replay-tune',out/name/'rest/checkpoint-004.json')
        group=[read_solution(Path(run)/'solution') for run in result['trial_runs']];solutions.append(group);new_fem+=len(group)
        moments=[boundary_moments(s.space) for s in group]
        for i,trial in enumerate(result['trials']):
            x=trial['value']*(10 if unit=='m' else 1);ratio=1+x/8
            for key,power in (('signed_area_m2',1),('signed_volume_m3',2)):
                assert abs(moments[i][key]/moments[0][key]/ratio**power-1)<1e-12
        assert group[-1].case.curved_contour==group[-2].case.curved_contour
        assert len(group[-1].space.geometry.cell_nodes)==4*len(group[-2].space.geometry.cell_nodes)
        rows.append(dict(name=name,status=result['status'],values=[t['value'] for t in result['trials']],
            moments=moments,rf=[quantities(s.case,s) for s in group],
            solver_triangles=[len(s.space.geometry.cell_nodes) for s in group],
            overlaps=[t['tracking']['tracking']['matches'][0]['minimum_principal_overlap'] for t in result['trials'][1:]]))
        print(f'{name}: 4 native trials PASS',flush=True)
    for variant,scale in ((1,1.),(2,2.)):
        for i,(old,new) in enumerate(zip(solutions[0],solutions[variant])):
            rf={k:abs(rows[variant]['rf'][i][k]*(scale if k=='frequency_hz' else 1)/rows[0]['rf'][i][k]-1)
                for k in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs')}
            q=np.array([[.2,.2],[.3,.4]]);groups=[[s.fields_in_cell(c,q) for c in range(len(s.space.geometry.cell_nodes))] for s in (old,new)]
            fields={}
            for key in ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'):
                a,b=[np.concatenate([f[key] for f in g]) for g in groups]
                fields[key]=float(np.linalg.norm(a-scale**1.5*b)/np.linalg.norm(a))
            assert max(rf.values())<2e-9 and max(fields.values())<2e-9,(rf,fields)
            comparisons.append(dict(variant=rows[variant]['name'],trial=i,rf_relative_errors=rf,field_relative_errors=fields))
    request=crossing_request();(out/'crossing.json').write_text(json.dumps(request,indent=2)+'\n')
    first=execute_tune(request,out/'crossing/first',max_new_trials=2)
    result=execute_tune(request,out/'crossing/rest',checkpoint=first);new_fem+=len(result['trials'])
    assert result['status']=='TUNED' and replay_tune(result)==result
    ranks=[t['current_mode_ids'].index('TM011') for t in first['trials']];assert ranks==[2,1],ranks
    errors=[abs(t['frequency_hz']/(C0/(2*math.pi)*math.hypot(2.404825557695773/.1,math.pi/t['value']))-1) for t in result['trials']]
    assert max(errors)<1e-4 and errors[-1]<1e-5,errors
    # Valid endpoint domains, but a negative radial semiaxis at the next midpoint.
    invalid=deepcopy(original)
    for curve in (1,2):invalid['geometry_coefficients'][f'/curves/{curve}/semiaxes_m/1']=[.08,-.5,.51]
    checkpoint=execute_tune(invalid,out/'invalid/first',max_new_trials=2);new_fem+=2
    assert checkpoint['decision']['next_trial']['value']==.5
    try:execute_tune(invalid,out/'invalid/rest',checkpoint=checkpoint)
    except ValueError:pass
    else:raise AssertionError('negative interior radius was accepted')
    assert (out/'invalid/rest/failure-003.json').is_file() and not (out/'invalid/rest/checkpoint-003.json').exists()
    assert replay_tune(checkpoint)==checkpoint
    assert fingerprints()==before
    report=dict(status='PASS',rows=rows,comparisons=comparisons,crossing=dict(initial_ranks=ranks,frequency_relative_errors=errors,status=result['status']),
        invalid_interior=dict(prior_checkpoint_preserved=True,failed_trial_not_evaluated=True),new_fem_solves=new_fem,
        seconds=time.monotonic()-started,source_files_unchanged=len(before),
        scope='three non-affine native tunes with fixed histories, CLI pause/resume/replay, independent Green and Maxwell RF/field laws, separate Bessel rank crossing, invalid-interior preservation; example target came from a preliminary FEM, not an accuracy reference; no global-root or physical-error certificate')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','new_fem_solves','seconds')}))


if __name__=='__main__':main()

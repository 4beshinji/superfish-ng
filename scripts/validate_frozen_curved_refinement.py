# SPDX-License-Identifier: Apache-2.0
"""Frozen split choices: affine covariance, Maxwell scaling and real tuning."""
import argparse
from pathlib import Path
import json
import subprocess
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from test_frozen_curved_refinement import marked_project,native_space
from superfish_ng import solve
from superfish_ng.frozen_curved_refinement import freeze_curved_refinement
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.project import Project
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.tuning import execute_tune,replay_tune
from validate_large_curved_mesh_selection import fingerprints,boundary_moments


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);started=time.monotonic();before=fingerprints()
    source=marked_project();source_before=source.to_dict();frozen=freeze_curved_refinement(source)
    source.save(out/'source-project.json');frozen.save(out/'frozen-project.json')
    process=subprocess.run([sys.executable,'-m','superfish_ng','freeze-curved-refinement',str(out/'source-project.json'),'--out',str(out/'cli-frozen.json')],capture_output=True,text=True)
    (out/'cli.log').write_text(process.stdout+process.stderr);assert process.returncode==0,process.stderr
    assert Project.load(out/'cli-frozen.json').to_dict()==frozen.to_dict()
    base=native_space(frozen);_,base_mass=assemble_curved(base,quadrature_order=12);base_moments=boundary_moments(base)
    rows=[];solutions=[]
    for name,a,c in [('base',1.,1.),('anisotropic',2.,.5),('double',2.,2.),('double-anisotropic',4.,1.)]:
        project=transform_curved_project(frozen,dict(radial_scale=a,axial_scale=c,axial_shear=0.),rf_coordinates='axial')
        project.save(out/f'{name}-project.json');space=native_space(project)
        assert project.case.curved_refinement_steps==frozen.case.curved_refinement_steps
        for key in ('cell_nodes','boundary_nodes','boundary_curve_indices'):
            np.testing.assert_array_equal(getattr(space.geometry,key),getattr(base.geometry,key))
        np.testing.assert_allclose(space.geometry.points_rz_m,base.geometry.points_rz_m*[a,c],rtol=0,atol=2e-15)
        _,mass=assemble_curved(space,quadrature_order=12)
        mass_difference=float(np.linalg.norm((mass-a**4*c*base_mass).toarray())/np.linalg.norm((a**4*c*base_mass).toarray()))
        assert mass_difference<1e-12
        moments=boundary_moments(space)
        assert abs(moments['signed_area_m2']/base_moments['signed_area_m2']/(a*c)-1)<1e-12
        assert abs(moments['signed_volume_m3']/base_moments['signed_volume_m3']/(a*a*c)-1)<1e-12
        solution=solve(project.case,mesh_data=project.mesh_data);result=save_run(project.case,solution,out/name)
        restored=read_solution(out/name)
        np.testing.assert_array_equal(restored.u,solution.u)
        np.testing.assert_array_equal(restored.space.geometry.cell_nodes,space.geometry.cell_nodes)
        rows.append(dict(name=name,cells=len(space.geometry.cell_nodes),mass_relative_difference=mass_difference,moments=moments,rf=result['modes'][0]))
        solutions.append(solution)
    scaling=[]
    for first,second in ((0,2),(1,3)):
        errors={key:abs(rows[second]['rf'][key]*(2 if key=='frequency_hz' else 1)/rows[first]['rf'][key]-1)
                for key in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs')}
        assert max(errors.values())<2e-9
        q=np.array([[.2,.2],[.3,.4],[.15,.6]]);field_error=0.
        for cell in range(len(base.geometry.cell_nodes)):
            old,new=[solutions[i].fields_in_cell(cell,q) for i in (first,second)]
            for key in ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'):
                field_error=max(field_error,float(np.linalg.norm(old[key]-2**1.5*new[key])/max(np.linalg.norm(old[key]),1e-300)))
        assert field_error<2e-9
        scaling.append(dict(pair=[first,second],rf_relative_errors=errors,maximum_field_relative_difference=field_error))
    request=dict(schema_version=4,project=frozen.to_dict(),parameter='shape_scale',parameter_unit='1',
        affine_coefficients=dict(radial_scale=[0.,2.],axial_scale=[0.,.5],axial_shear=[0.]),rf_coordinates='axial',
        bounds=[1.,1.2],target_hz=float(solutions[1].frequencies_hz[0])/1.1,frequency_tolerance_hz=5e4,
        parameter_tolerance=1e-8,max_trials=12,initial_ids=['A'],mode_id='A',
        controls=dict(mapping='affine_remesh',sample_order=5,minimum_overlap=.8,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8),refinement_scale=2,mesh_frequency_tolerance_hz=5e4)
    (out/'tune-request.json').write_text(json.dumps(request,indent=2)+'\n')
    tuned=execute_tune(request,out/'tune');assert tuned['status']=='TUNED',tuned['decision']
    assert replay_tune(tuned)==tuned
    assert abs(tuned['decision']['value']-1.1)<1e-12
    for run in tuned['trial_runs']:
        actual=read_solution(Path(run)/'solution')
        assert actual.case.curved_refinement_steps[:len(frozen.case.curved_refinement_steps)]==frozen.case.curved_refinement_steps
    assert source.to_dict()==source_before and fingerprints()==before
    report=dict(status='PASS',scope='captured marked choices and preserved reference restrictions under declared affine geometry; native saved replay, covariance, independent moments, Maxwell scaling and real tuning; no general discretization error bound',
        rows=rows,scaling=scaling,tuning_status=tuned['status'],tuning_decision=tuned['decision'],
        tuning_trials=len(tuned['trials']),dedicated_new_fem_solves=4+len(tuned['trials']),cli_matches_python=True,
        source_files_unchanged=len(before),seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');(out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],seconds=report['seconds'],tuning_status=tuned['status'],trials=len(tuned['trials']),scaling=scaling)))


if __name__=='__main__':main()

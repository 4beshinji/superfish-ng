# SPDX-License-Identifier: Apache-2.0
"""Verify nonlinear numbered mesh deformation with native fields and scaling."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tests')]
from superfish_ng.project import Project
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.jobs import execute_project
from superfish_ng.saved import read_solution
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking
from test_curved_harmonic_deformation import deformation_fixture,folded_deformation_fixture,space
from test_curved_piecewise_remesh_tracking import CONTROLS
from validate_large_curved_mesh_selection import fingerprints,boundary_moments


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    out=parser.parse_args().out.resolve();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();before=fingerprints()
    source,geometry=deformation_fixture();source.save(out/'source-1.json')
    (out/'geometry-1.json').write_text(json.dumps(geometry,indent=2)+'\n')
    def cli(source_path,geometry_path,target):
        command=[sys.executable,'-m','superfish_ng','deform-curved-project',str(source_path),
            '--geometry',str(geometry_path),'--rf-coordinates','axis_fraction','--minimum-corner-angle-deg','1','--out',str(target)]
        result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
        (out/(target.stem+'-cli.log')).write_text(result.stdout+result.stderr)
        return result
    assert cli(out/'source-1.json',out/'geometry-1.json',out/'target-1.json').returncode==0
    target=Project.load(out/'target-1.json')
    affine=dict(radial_scale=2.,axial_scale=2.,axial_shear=0.)
    source2=transform_curved_project(source,affine,rf_coordinates='axial');source2.save(out/'source-2.json')
    expected2=transform_curved_project(target,affine,rf_coordinates='axial')
    (out/'geometry-2.json').write_text(json.dumps(expected2.case.to_dict()['geometry'],indent=2)+'\n')
    assert cli(out/'source-2.json',out/'geometry-2.json',out/'target-2.json').returncode==0
    target2=Project.load(out/'target-2.json');projects=(source,target,source2,target2)
    np.testing.assert_allclose(target2.mesh_data['points'],2*np.asarray(target.mesh_data['points']),rtol=0,atol=2e-15)
    rows=[];solutions=[]
    for label,project in zip(('source-1','target-1','source-2','target-2'),projects):
        s=space(project);moments=boundary_moments(s)
        result=execute_project(project,out/label)
        native=read_solution(out/label/'solution');solutions.append(native)
        rows.append(dict(label=label,base_triangles=len(project.mesh_data['triangles']),triangles=len(s.geometry.cell_nodes),
            boundary_moments=moments,frequency_hz=native.frequencies_hz.tolist(),rf=native.results['modes'][0]))
    comparisons=[]
    for first,second in ((0,1),(2,3)):
        documents=[dict(schema_version=2,source_mesh=p.mesh_data,curved_refinement_steps=p.case.to_dict()['mesh']['curved_refinement_steps']) for p in (projects[first],projects[second])]
        request=dict(schema_version=1,previous_run=str(out/rows[first]['label']/'solution'),current_run=str(out/rows[second]['label']/'solution'),
            previous_ids=['A'],controls=dict(CONTROLS,comparison_meshes=documents))
        filename=out/f'tracking-{first}.json';report=save_mode_tracking(request,filename)
        assert report['status']=='PASS' and read_mode_tracking(filename)==report
        comparisons.append(report['tracking']['matches'][0]['minimum_principal_overlap'])
        for key,factor in (('signed_area_m2',1.125),('signed_volume_m3',1.125**2)):
            assert abs(rows[second]['boundary_moments'][key]/rows[first]['boundary_moments'][key]/factor-1)<1e-12
    scaling=[]
    for a,b in ((0,2),(1,3)):
        old,new=solutions[a],solutions[b]
        error=dict(frequency=float(np.max(abs(2*new.frequencies_hz/old.frequencies_hz-1))))
        for key in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs'):
            error[key]=abs(rows[b]['rf'][key]/rows[a]['rf'][key]-1)
        fields={};q=np.array([[.2,.2],[.3,.4],[.15,.6]])
        groups=[[s.fields_in_cell(cell,q) for cell in range(len(s.space.geometry.cell_nodes))] for s in (old,new)]
        for key in ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'):
            x,y=[np.concatenate([field[key] for field in group]) for group in groups]
            fields[key]=float(np.linalg.norm(y*2**1.5-x)/np.linalg.norm(x))
        _,m0=assemble_curved(old.space,quadrature_order=12);_,m1=assemble_curved(new.space,quadrature_order=12)
        mass=float(np.linalg.norm((m1-32*m0).toarray())/np.linalg.norm((32*m0).toarray()))
        assert max(error.values())<2e-9 and max(fields.values())<2e-9 and mass<1e-12
        scaling.append(dict(source=rows[a]['label'],rf_relative_errors=error,field_relative_errors=fields,mass_relative_error=mass))
    folded,bad=folded_deformation_fixture();folded.save(out/'folded-source.json')
    (out/'folded-geometry.json').write_text(json.dumps(bad,indent=2)+'\n')
    failure=cli(out/'folded-source.json',out/'folded-geometry.json',out/'folded-target.json')
    assert failure.returncode!=0 and 'Jacobian' in failure.stderr and not (out/'folded-target.json').exists()
    assert fingerprints()==before
    report=dict(status='PASS',scope='declared nonlinear numbered mesh deformation with CLI, native fields/replay, independent Green measures and Maxwell scaling; not a physical error bound',
        rows=rows,scaling=scaling,tracking_overlaps=comparisons,folded_cli_exit_code=failure.returncode,new_fem_solves=4,
        source_files_unchanged=len(before),seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','tracking_overlaps','new_fem_solves','seconds')}))


if __name__=='__main__':main()

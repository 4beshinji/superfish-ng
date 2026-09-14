# SPDX-License-Identifier: Apache-2.0
"""Independent physical-region integrals and actual FEM after selection transfer."""
import argparse
from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from test_curved_piecewise_remesh_tracking import curved_comparison_fixture
from test_curved_comparison_correspondence import renumber_source
from superfish_ng import solve
from superfish_ng.project import Project
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh_input import mesh_from_dict
from superfish_ng.curved_selection_transfer import transfer_curved_cell_selection,replay_curved_selection_transfer
from superfish_ng.curved_comparison_correspondence import infer_curved_comparison_correspondence
from superfish_ng.io import save_run
from validate_large_curved_mesh_selection import fingerprints


def space(project,base=False):
    case=replace(project.case,curved_refinement_levels=0,curved_refinement_steps=()) if base else project.case
    return case_curved_space(case,mesh_from_dict(case,project.mesh_data))


def fixture(scale):
    cases,maps=curved_comparison_fixture(scale)
    previous=Project(replace(cases[0],curved_refinement_steps=(Step('uniform'),Step('marked',(0,),1.))),mesh_data=maps[0]['source_mesh'])
    target_mesh,_=renumber_source(maps[1]['source_mesh'])
    uniform=[Project(replace(case,curved_refinement_steps=(Step('uniform'),)),mesh_data=mesh)
        for case,mesh in zip(cases,(maps[0]['source_mesh'],target_mesh))]
    pairing=infer_curved_comparison_correspondence(cases,[space(p) for p in uniform],boundary_pairing='ordered_curve_vertices')
    # Select material child 1 on the other side, independently of its cyclic
    # root vertex order. Multiplying a renumbered root ID by four is insufficient.
    marked=pairing['current_cell_for_previous'][1]
    current=Project(replace(cases[1],curved_refinement_steps=(Step('uniform'),Step('marked',(marked,),1.))),mesh_data=target_mesh)
    return previous,current


def moments(nodes,triangle=((0.,0.),(1.,0.),(0.,1.))):
    """Separate P2 basis/partials and tensor Gauss-Duffy area/volume/r³ mass."""
    nodes=np.asarray(nodes);a,b,c=np.asarray(triangle,float)
    t,w=np.polynomial.legendre.leggauss(8);t=(t+1)/2;w=w/2
    s,v=np.meshgrid(t,t,indexing='ij');weights=np.outer(w,w)*(1-s)
    q=a+s[...,None]*(b-a)+(1-s[...,None])*v[...,None]*(c-a)
    x,y=q.reshape(-1,2).T;l=1-x-y
    basis=np.array([l*(2*l-1),x*(2*x-1),y*(2*y-1),4*l*x,4*x*y,4*y*l]).T
    dx=np.array([1-4*l,4*x-1,np.zeros_like(x),4*(l-x),4*y,-4*y]).T
    dy=np.array([1-4*l,np.zeros_like(x),4*y-1,-4*x,4*x,4*(l-y)]).T
    p=basis@nodes;u=dx@nodes;v=dy@nodes
    determinant=u[:,0]*v[:,1]-u[:,1]*v[:,0]
    reference=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
    measure=weights.ravel()*reference*determinant;r=p[:,0]
    return np.array([np.sum(measure),2*np.pi*np.sum(measure*r),np.sum(measure*r**3)])


def region_check(previous,current,document,contained):
    old,new=space(previous),space(current);roots=(space(previous,True),space(current,True))
    selected=document['request']['selected_cells'];native=sum((moments(old.geometry.points_rz_m[old.geometry.cell_nodes[i]]) for i in selected),np.zeros(3))
    totals=[np.zeros(3),np.zeros(3)];node_map=np.asarray(document['base_correspondence']['current_node_for_previous'])
    for overlap in document['selection']['overlaps']:
        root=overlap['base_cell'];old_nodes=roots[0].geometry.cell_nodes[root]
        arrays=(roots[0].geometry.points_rz_m[old_nodes],roots[1].geometry.points_rz_m[node_map[old_nodes]])
        polygon=np.array([[float(Fraction(*value)) for value in point] for point in overlap['reference_vertices']])
        for i in range(1,len(polygon)-1):
            for side,nodes in enumerate(arrays):totals[side]+=moments(nodes,polygon[[0,i,i+1]])
    error=float(np.max(np.abs(totals[0]/native-1)));assert error<3e-12
    cover=sum((moments(new.geometry.points_rz_m[new.geometry.cell_nodes[i]]) for i in document['selection']['selected_cells']),np.zeros(3))
    inside=sum((moments(new.geometry.points_rz_m[new.geometry.cell_nodes[i]]) for i in contained['selection']['selected_cells']),np.zeros(3))
    assert np.all(cover>=totals[1]*(1-3e-12)) and np.all(inside<=totals[1]*(1+3e-12))
    return dict(component_names=['physical_area_m2','axisymmetric_volume_m3','Hphi_equals_r_mass_m5'],
        source_native=native.tolist(),source_overlay=totals[0].tolist(),mapped_target_overlay=totals[1].tolist(),
        target_cover=cover.tolist(),target_contained=inside.tolist(),source_relative_difference=error)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);start=time.monotonic();before=fingerprints();rows=[];solutions=[];documents=[]
    request=dict(schema_version=1,selected_cells=[0,2,6],boundary_pairing='ordered_curve_vertices',coverage_policy='intersects',max_pair_tests=100000)
    for scale in (1,2):
        previous,current=fixture(scale)
        document=transfer_curved_cell_selection(previous,current,request);assert replay_curved_selection_transfer(document)==document
        contained=transfer_curved_cell_selection(previous,current,dict(request,coverage_policy='contained'))
        assert document['selection']['partially_covered_cells']
        geometry=region_check(previous,current,document,contained)
        selected=document['selection']['selected_cells'];assert selected
        refined=replace(current,case=replace(current.case,curved_refinement_steps=current.case.curved_refinement_steps+(Step('marked',tuple(selected),1.),)))
        for name,project in (('previous',previous),('current',current),('refined',refined)):project.save(out/f'scale-{scale}-{name}-project.json')
        for name,data in (('transfer',document),('contained',contained)):(out/f'scale-{scale}-{name}.json').write_text(json.dumps(data,indent=2)+'\n')
        stages=[solve(p.case,mesh_data=p.mesh_data) for p in (current,refined)];rf=[]
        for name,solution in zip(('current','refined'),stages):rf.append(save_run(solution.case,solution,out/f'scale-{scale}-{name}')['modes'][0])
        assert stages[1].frequencies_hz[0]<=stages[0].frequencies_hz[0]*(1+1e-10)
        rows.append(dict(scale=scale,geometry=geometry,rf=rf,selected_cells=selected,partial_cells=document['selection']['partially_covered_cells'],
            source_cells=document['selection']['previous_final_cell_count'],target_cells=document['selection']['current_final_cell_count'],refined_cells=len(stages[1].space.geometry.cell_nodes)))
        solutions.append(stages);documents.append(document)
    assert documents[0]['selection']==documents[1]['selection']
    for key in ('source_native','source_overlay','mapped_target_overlay','target_cover','target_contained'):
        np.testing.assert_allclose(rows[1]['geometry'][key],np.asarray(rows[0]['geometry'][key])*[4,8,32],rtol=3e-12,atol=0)
    similarity=[]
    for stage in (0,1):
        a,b=solutions[0][stage],solutions[1][stage]
        errors={key:abs(rows[1]['rf'][stage][key]*(2 if key=='frequency_hz' else 1)/rows[0]['rf'][stage][key]-1)
            for key in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs')}
        assert max(errors.values())<2e-9
        np.testing.assert_array_equal(a.space.geometry.cell_nodes,b.space.geometry.cell_nodes)
        field_error=0.;q=np.array([[.2,.2],[.3,.4],[.15,.6]])
        for cell in range(len(a.space.geometry.cell_nodes)):
            old,new=a.fields_in_cell(cell,q),b.fields_in_cell(cell,q)
            for key in ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'):
                field_error=max(field_error,float(np.linalg.norm(old[key]-2**1.5*new[key])/max(np.linalg.norm(old[key]),1e-300)))
        assert field_error<2e-9;similarity.append(dict(rf_relative_errors=errors,maximum_field_relative_error=field_error))
    (out/'request.json').write_text(json.dumps(request,indent=2)+'\n')
    commands=[['transfer-curved-selection',str(out/'scale-1-previous-project.json'),str(out/'scale-1-current-project.json'),'--request',str(out/'request.json'),'--out',str(out/'cli-transfer.json')],
              ['replay-curved-selection-transfer',str(out/'cli-transfer.json')]]
    for i,command in enumerate(commands):
        result=subprocess.run([sys.executable,'-m','superfish_ng',*command],capture_output=True,text=True)
        (out/f'cli-{i}.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stderr
    assert json.loads((out/'cli-transfer.json').read_text())==documents[0]
    assert fingerprints()==before
    report=dict(status='PASS',rows=rows,similarity=similarity,new_fem_solves=4,source_files_unchanged=len(before),seconds=time.monotonic()-start)
    (out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n');(out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status='PASS',seconds=report['seconds'],new_fem_solves=4,similarity=similarity)))


if __name__=='__main__':main()

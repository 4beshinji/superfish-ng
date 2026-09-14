# SPDX-License-Identifier: Apache-2.0
"""Independent curved comparison meshes: volume, Maxwell scaling and replay."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from test_curved_piecewise_remesh_tracking import curved_comparison_fixture,CONTROLS
from superfish_ng import solve
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history
from validate_large_curved_mesh_selection import boundary_moments,fingerprints


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();before=fingerprints();rows=[];solutions=[];requests=[]
    for scale in (1,2):
        cases,maps=curved_comparison_fixture(scale)
        stages=[solve(cases[0],mesh_data=maps[0]['source_mesh']),
                solve(replace(cases[1],curved_refinement_levels=1),mesh_data=maps[1]['source_mesh'])]
        names=[f'scale-{scale}-{name}' for name in ('old','new')]
        rf=[];geometry=[]
        for name,solution in zip(names,stages):
            saved=save_run(solution.case,solution,out/name);rf.append(saved['modes'][0])
            geometry.append(boundary_moments(solution.space))
        analytic=[4*np.pi/3*(.08*scale)**2*(.1*scale),2*np.pi/3*(.09*scale)**2*(.08+.12)*scale]
        for values,exact in zip(geometry,analytic):assert abs(abs(values['signed_volume_m3'])/exact-1)<.002
        reports=[]
        for order in (4,8):
            controls=dict(CONTROLS,sample_order=order,comparison_meshes=maps)
            request=dict(schema_version=1,previous_run=names[0],current_run=names[1],previous_ids=['fundamental'],controls=controls)
            path=out/f'scale-{scale}-order-{order}-pair.json'
            pair=save_mode_tracking(request,path,base_directory=out);assert pair['status']=='PASS'
            assert read_mode_tracking(path)==pair
            reverse=extend_mode_history(start_mode_history(pair),dict(current_run=names[0],controls=dict(controls,comparison_meshes=maps[::-1])),base_directory=out)
            assert reverse['status']=='PASS' and reverse['current_mode_ids']==['fundamental']
            a=pair['tracking']['matches'][0]['minimum_principal_overlap']
            b=reverse['steps'][1]['tracking']['matches'][0]['minimum_principal_overlap'];assert abs(a-b)<2e-12
            mapping=pair['tracking']['physical_mapping']
            for measured,moments in zip(mapping['axisymmetric_volumes_m3'],geometry):
                assert abs(measured/abs(moments['signed_volume_m3'])-1)<1e-12
            assert abs(mapping['axisymmetric_volumes_m3'][1]/mapping['axisymmetric_volumes_m3'][0]/1.125**2-1)<1e-12
            reports.append(dict(order=order,overlap=a,reciprocity_difference=abs(a-b),physical_mapping=mapping))
            requests.append((request,path))
        assert abs(reports[0]['overlap']-reports[1]['overlap'])<1e-4
        (out/f'scale-{scale}-comparison-meshes.json').write_text(json.dumps(maps,indent=2)+'\n')
        rows.append(dict(scale=scale,rf=rf,geometry=geometry,analytic_volume_m3=analytic,comparisons=reports))
        solutions.append(stages)
    similarity=[]
    for side in (0,1):
        a,b=solutions[0][side],solutions[1][side]
        errors={key:abs(rows[1]['rf'][side][key]*(2 if key=='frequency_hz' else 1)/rows[0]['rf'][side][key]-1)
                for key in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs')}
        assert max(errors.values())<2e-9
        np.testing.assert_array_equal(a.space.geometry.cell_nodes,b.space.geometry.cell_nodes)
        np.testing.assert_allclose(a.space.geometry.points_rz_m*2,b.space.geometry.points_rz_m,rtol=0,atol=1e-15)
        relative_fields={key:0. for key in ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m')}
        q=np.array([[.2,.2],[.3,.4],[.15,.6]])
        for cell in range(len(a.space.geometry.cell_nodes)):
            old=a.fields_in_cell(cell,q);new=b.fields_in_cell(cell,q)
            for key in relative_fields:
                error=float(np.linalg.norm(old[key]-2**1.5*new[key])/max(np.linalg.norm(old[key]),1e-300))
                relative_fields[key]=max(relative_fields[key],error)
        assert max(relative_fields.values())<2e-9
        replay=quantities_curved(b,include_surface_peaks=False)
        assert abs(replay['stored_energy_j']-1)<1e-12
        assert abs(replay['electric_energy_j']/replay['magnetic_energy_j']-1)<1e-10
        similarity.append(dict(rf_relative_errors=errors,field_relative_errors=relative_fields))
    for order in range(2):assert abs(rows[0]['comparisons'][order]['overlap']-rows[1]['comparisons'][order]['overlap'])<2e-10
    # Exercise the existing CLI entry without substituting canned field data.
    request,path=requests[1];request_path=out/'cli-request.json'
    request_path.write_text(json.dumps(request,indent=2)+'\n')
    cli_out=out/'cli-pair.json'
    result=subprocess.run([sys.executable,'-m','superfish_ng','track-modes',str(request_path),'--out',str(cli_out)],capture_output=True,text=True)
    (out/'cli.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stderr
    assert json.loads(cli_out.read_text())==json.loads(path.read_text())
    assert fingerprints()==before
    report=dict(status='PASS',scope='two synthetic joined-ellipse domains with nonlinear curved comparison maps, independent FEM histories; Maxwell scaling and whole-boundary volume, no general physical error bound',
                rows=rows,similarity=similarity,new_fem_solves=4,cli_matches_python=True,source_files_unchanged=len(before),seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    (out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],seconds=report['seconds'],new_fem_solves=4,similarity=similarity)))


if __name__=='__main__':main()

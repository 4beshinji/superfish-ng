# SPDX-License-Identifier: Apache-2.0
"""Revalidate browser deformation geometry and actual GUI/CLI native fields."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
from unittest.mock import patch
import numpy as np
from superfish_ng.project import Project
from superfish_ng.jobs import read_job
from superfish_ng.saved import read_solution
from superfish_ng.rf import quantities
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh_input import mesh_from_dict
from validate_large_curved_mesh_selection import fingerprints,boundary_moments


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('browser','cli-run','workspace','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();before=fingerprints()
    report=json.loads((args.browser/'report.json').read_text());assert report['passed'] and not report['external_requests']
    preview=json.loads((args.browser/'preview.json').read_text());shown=json.loads((args.browser/'result.json').read_text())
    candidates=[p.parent for p in args.workspace.glob('*/job.json')
                if json.loads(p.read_text()).get('created_unix')==shown['state']['created_unix']]
    assert len(candidates)==1;gui_run=candidates[0]
    source=Project.from_dict(preview['source']['project']);target=Project.from_dict(preview['target']['project'])
    assert json.loads(preview['serialized'])==target.to_dict()
    assert Project.load(args.cli_run/'project.json').to_dict()==target.to_dict()==Project.load(gui_run/'project.json').to_dict()
    assert source.case.curved_refinement_steps==target.case.curved_refinement_steps
    assert source.mesh_data['triangles']==target.mesh_data['triangles']
    spaces=[case_curved_space(p.case,mesh_from_dict(p.case,p.mesh_data)) for p in (source,target)]
    for name,space in zip(('source','target'),spaces):
        np.testing.assert_array_equal(preview[name]['native_boundary']['edges_rz_m'],space.geometry.points_rz_m[space.geometry.boundary_nodes])
        assert preview[name]['native_boundary']['cell_count']==len(space.geometry.cell_nodes)
    moments=[boundary_moments(space) for space in spaces]
    for key,ratio in [('signed_area_m2',1.125),('signed_volume_m3',1.125**2)]:
        assert abs(moments[1][key]/moments[0][key]/ratio-1)<2e-13
    native_files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for root in (args.cli_run,gui_run)
                  for p in root.rglob('*') if p.is_file()}
    with patch('superfish_ng.curved_solution.solve_curved',side_effect=AssertionError('replay cannot solve')):
        solutions=[]
        for root in (args.cli_run,gui_run):
            assert read_job(root)['status']=='complete'
            solutions.append(read_solution(root/'solution'))
        a,b=solutions
        np.testing.assert_array_equal(a.frequencies_hz,b.frequencies_hz)
        np.testing.assert_array_equal(a.u,b.u)
        np.testing.assert_array_equal(b.space.geometry.points_rz_m,spaces[1].geometry.points_rz_m)
        for index,mode in enumerate(shown['result']['modes']):
            q=quantities(b.case,b,index)
            for key,value in q.items():
                if isinstance(value,(int,float)) and not isinstance(value,bool):
                    assert math.isclose(mode[key],value,rel_tol=2e-12,abs_tol=1e-13),(key,mode[key],value)
                else:assert mode[key]==value,key
            energy=mode['stored_energy_j'];omega=2*math.pi*mode['frequency_hz']
            assert math.isclose(energy,mode['electric_energy_j']+mode['magnetic_energy_j'],rel_tol=2e-13)
            assert math.isclose(energy,b.case.normalization_j,rel_tol=2e-13)
            # PHYSICS.md: accelerator V²/(omega U), circuit V²/(2 omega U).
            assert math.isclose(mode['r_over_q_circuit_ohm'],mode['r_over_q_accelerator_ohm']/2,rel_tol=2e-13)
            assert math.isclose(mode['r_over_q_accelerator_ohm'],mode['vacc_v']**2/(omega*energy),rel_tol=2e-13)
    assert native_files=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in native_files}
    assert before==fingerprints()
    result=dict(status='PASS',new_fem=0,gui_run=str(gui_run.resolve()),cli_run=str(args.cli_run.resolve()),
        source_files=len(before),native_files_unchanged=len(native_files),seconds=time.monotonic()-start,
        cell_count=len(spaces[1].geometry.cell_nodes),boundary_green_moments=moments,
        frequency_and_coefficient_arrays='exactly equal',all_displayed_native_rf_quantities='recomputed from original saved fields',
        independent_rf_checks=['electric plus magnetic energy','normalization','two R/Q definitions','accelerator R/Q from voltage, frequency and energy'],
        scope='GUI preparation, native boundary and saved fields; not continuum accuracy or a new eigensolve')
    (args.out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    (args.out/'native-sha256.json').write_text(json.dumps(native_files,indent=2)+'\n')
    (args.out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()

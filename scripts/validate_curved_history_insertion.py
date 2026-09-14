# SPDX-License-Identifier: Apache-2.0
"""Check GUI history insertion against native geometry and saved FEM fields."""
import argparse
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import time
from unittest.mock import patch
import numpy as np
from superfish_ng import Case, make_mesh
from superfish_ng.curved_space import case_curved_space
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.mesh_input import mesh_from_dict
from superfish_ng.project import Project
from superfish_ng.saved import read_solution
from validate_large_curved_mesh_selection import boundary_moments, fingerprints


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--browser-directory',type=Path,required=True)
    parser.add_argument('--saved-solution',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();before=fingerprints();folder=args.browser_directory
    documents={name:(folder/name).read_bytes() for name in
               ('report.json','mesh-documents.json','built-project.json','large-built-project.json','result.json')}
    browser=json.loads(documents['report.json']);assert browser['passed'] and not browser['external_requests']
    changed=[p for p,h in browser['source_sha256'].items() if before.get(p)!=h]
    # CSS affects layout, not the native numbering/arrays under this validator.
    # Record any later style edits; browser visual checks must cover them separately.
    assert all(p.endswith('.css') for p in changed),changed
    source=Case.load(args.case)
    built=Project.from_dict(json.loads(documents['built-project.json']))
    expected=replace(source,curved_refinement_steps=(source.curved_refinement_steps[0],Step('marked',(0,),5.),*source.curved_refinement_steps[1:]))
    assert built.case==expected
    cache={}
    def space(project):
        key=json.dumps(project.to_dict(),sort_keys=True)
        if key not in cache:
            mesh=make_mesh(project.case) if project.mesh_data is None else mesh_from_dict(project.case,project.mesh_data)
            cache[key]=case_curved_space(project.case,mesh)
        return cache[key]
    initial=replace(source,curved_refinement_steps=(),curved_refinement_levels=0)
    base_moments=boundary_moments(space(Project(initial)))
    checked=[]
    for entry in json.loads(documents['mesh-documents.json']):
        project=Project.from_dict(entry['project']);native=space(project);mesh=entry['mesh']
        assert Case.from_dict(mesh['case'])==project.case and mesh['cell_index_origin']==0
        np.testing.assert_array_equal(mesh['points_rz_m'],native.geometry.points_rz_m)
        np.testing.assert_array_equal(mesh['cell_nodes'],native.geometry.cell_nodes)
        checked.append(len(native.geometry.cell_nodes))
    large=Project.from_dict(json.loads(documents['large-built-project.json']))
    assert large.case.curved_refinement_steps==(Step('uniform'),)*4+(Step('marked',(0,),5.),Step('uniform'))
    assert replace(large.case,curved_refinement_steps=(),curved_refinement_levels=0)==initial
    moments={}
    for name,project in [('small',built),('large',large)]:
        native=space(project);values=boundary_moments(native);moments[name]=values
        for key,value in values.items():assert abs(value/base_moments[key]-1)<1e-12,(name,key,values)
    saved_bytes={str(p):p.read_bytes() for p in args.saved_solution.iterdir() if p.is_file()}
    with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('saved replay must not solve')):
        solution=read_solution(args.saved_solution)
    assert solution.case==expected
    native=space(built)
    np.testing.assert_array_equal(solution.space.geometry.points_rz_m,native.geometry.points_rz_m)
    np.testing.assert_array_equal(solution.space.geometry.cell_nodes,native.geometry.cell_nodes)
    rf=quantities_curved(solution,include_surface_peaks=False)
    browser_rf=json.loads(documents['result.json'])['result']['modes'][0]
    keys=('frequency_hz','stored_energy_j','electric_energy_j','magnetic_energy_j','q0','vacc_v','eacc_v_per_m','r_over_q_accelerator_ohm','r_over_q_circuit_ohm')
    for key in keys:assert math.isclose(rf[key],browser_rf[key],rel_tol=1e-12),(key,rf[key],browser_rf[key])
    assert abs(rf['stored_energy_j']/expected.normalization_j-1)<1e-12
    assert abs(rf['electric_energy_j']/rf['magnetic_energy_j']-1)<1e-10
    assert rf['r_over_q_accelerator_ohm']==2*rf['r_over_q_circuit_ohm']
    assert math.isclose(rf['r_over_q_accelerator_ohm'],rf['vacc_v']**2/(2*math.pi*rf['frequency_hz']*rf['stored_energy_j']),rel_tol=1e-14)
    assert all(Path(p).read_bytes()==data for p,data in saved_bytes.items())
    assert all((folder/name).read_bytes()==data for name,data in documents.items())
    assert fingerprints()==before
    report=dict(status='PASS',scope='GUI prefix numbering, ordered insertion and unchanged physical domain; saved FEM replay and RF conventions, not a discretization error bound',
                displayed_cell_counts=checked,unique_spaces=len(cache),final_cells={name:len(space(project).geometry.cell_nodes) for name,project in [('small',built),('large',large)]},
                base_boundary_moments=base_moments,final_boundary_moments=moments,rf={key:rf[key] for key in keys},
                source_files_unchanged=len(before),style_files_changed_since_browser=changed,seconds=time.monotonic()-started,
                browser_file_sha256={name:hashlib.sha256(data).hexdigest() for name,data in documents.items()})
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()

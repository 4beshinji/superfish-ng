# SPDX-License-Identifier: Apache-2.0
"""Reconstruct browser selections and compare saved FEM with an independent run."""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import time
from unittest.mock import patch
import numpy as np
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.curved_selection_transfer import replay_curved_selection_transfer,transfer_curved_cell_selection
from superfish_ng.project import Project
from superfish_ng.saved import read_solution
from validate_curved_selection_transfer import region_check
from validate_large_curved_mesh_selection import fingerprints


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('browser','numerical','saved-solution','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();before=fingerprints()
    paths=[args.browser/name for name in ('report.json','large-transfer.json','built-project.json','result.json','downloads/curved-selection-transfer.json')]
    paths += [p for root in (args.saved_solution,args.numerical/'scale-1-refined') for p in root.rglob('*') if p.is_file()]
    saved={str(p):sha256(p.read_bytes()).hexdigest() for p in paths}
    browser=json.loads((args.browser/'report.json').read_text())
    assert browser['passed'] and not browser['external_requests']
    assert all(before[path]==value for path,value in browser['source_sha256'].items())
    selections=[]
    for name in ('downloads/curved-selection-transfer.json','large-transfer.json'):
        document=replay_curved_selection_transfer(json.loads((args.browser/name).read_text()))
        previous=Project.from_dict(document['previous_project']);current=Project.from_dict(document['current_project'])
        contained=transfer_curved_cell_selection(previous,current,dict(document['request'],coverage_policy='contained'))
        geometry=region_check(previous,current,document,contained)
        selections.append(dict(file=name,previous_cells=document['selection']['previous_final_cell_count'],
            current_cells=document['selection']['current_final_cell_count'],selected_cells=len(document['selection']['selected_cells']),
            partial_cells=len(document['selection']['partially_covered_cells']),geometry=geometry))
    with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('saved comparison must not solve')):
        gui=read_solution(args.saved_solution);independent=read_solution(args.numerical/'scale-1-refined')
    built=Project.from_dict(json.loads((args.browser/'built-project.json').read_text()))
    assert gui.case==built.case==independent.case
    for a,b in ((gui.frequencies_hz,independent.frequencies_hz),(gui.u,independent.u),
                (gui.space.geometry.points_rz_m,independent.space.geometry.points_rz_m),
                (gui.space.geometry.cell_nodes,independent.space.geometry.cell_nodes)):
        np.testing.assert_array_equal(a,b)
    rf=quantities_curved(gui,include_surface_peaks=False)
    displayed=json.loads((args.browser/'result.json').read_text())['result']['modes'][0]
    keys=('frequency_hz','stored_energy_j','electric_energy_j','magnetic_energy_j','q0','vacc_v','eacc_v_per_m',
          'r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs')
    for key in keys:assert math.isclose(rf[key],displayed[key],rel_tol=1e-12),(key,rf[key],displayed[key])
    assert abs(rf['stored_energy_j']/gui.case.normalization_j-1)<1e-12
    assert abs(rf['electric_energy_j']/rf['magnetic_energy_j']-1)<1e-10
    assert rf['r_over_q_accelerator_ohm']==2*rf['r_over_q_circuit_ohm']
    assert math.isclose(rf['r_over_q_accelerator_ohm'],rf['vacc_v']**2/(2*math.pi*rf['frequency_hz']*rf['stored_energy_j']),rel_tol=1e-14)
    assert all(sha256(Path(path).read_bytes()).hexdigest()==value for path,value in saved.items())
    assert fingerprints()==before
    numerical_before=json.loads((args.numerical/'source-sha256.json').read_text())
    report=dict(status='PASS',new_fem_solves=0,selections=selections,rf={k:rf[k] for k in keys},
        saved_native_arrays_exactly_equal=True,unchanged_artifact_count=len(saved),
        source_files_unchanged=len(before),
        source_changes_since_numerical=[p for p in sorted(set(before)|set(numerical_before)) if before.get(p)!=numerical_before.get(p)],
        seconds=time.monotonic()-started)
    (args.out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    (args.out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    (args.out/'artifact-sha256.json').write_text(json.dumps(saved,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()

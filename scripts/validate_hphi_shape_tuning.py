#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual nonuniform holed-vacuum tuning, owned restart and independent TEM check."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from scripts.hphi_mesh_reference import rectangular_holes
from superfish_ng.constants import C0
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_tracking import HphiTrackingControls
from superfish_ng.hphi_tuning import execute_hphi_tune, read_hphi_tune, replay_hphi_tune
from superfish_ng.hphi_native import read_hphi_run
from superfish_ng.cli import main as cli


def request():
    data = rectangular_holes(4,1)
    def coordinates(p):
        p = np.asarray(p)
        return np.column_stack((np.round((p[:,0]-.025)/.075*12)/128+1/32,
                                np.round(p[:,1]/.18*12)/32))
    for key in ('outer_rz_m','points_rz_m'):data[key] = coordinates(data[key])
    data['holes_rz_m'] = [coordinates(h) for h in data['holes_rz_m']]
    mesh = MeridionalMesh(**data)
    displacement = np.column_stack((np.interp(mesh.points_rz_m[:,0],np.arange(1,5)/32,[0,1/2048,1/2048,0]),
                                    mesh.points_rz_m[:,1]/8))
    return dict(format='superfish_ng_hphi_tune',schema_version=2,
        project=HphiProject(HphiMeshCase(mesh,modes=6,quadrature_order=12)).to_dict(),
        parameter='deformation',mapping=dict(kind='general_piecewise_affine',reference_value=1.,
            displacements_rz_m=displacement.tolist(),acceleration_policy='transport_on_axis'),
        bounds=[1.,2.],target_hz=3*C0/(2*.375*1.0625),frequency_tolerance_hz=1e6,
        parameter_tolerance=1e-6,max_trials=12,initial_ids=['mode-1','mode-2','mode-3','mode-4'],mode_id='mode-4',
        controls=HphiTrackingControls().to_dict(),refinement_levels=1,max_triangles=10000,max_dofs=10000,
        mesh_frequency_tolerance_hz=1e6)


def validate(directory):
    directory.mkdir(parents=True,exist_ok=False)
    q = request()
    (directory/'request.json').write_text(json.dumps(q,indent=2)+'\n')
    first = execute_hphi_tune(q,directory/'first',max_new_trials=2)
    if first['status'] != 'PAUSED':
        raise AssertionError(f'initial two trials must pass: {first["status"]}')
    final = execute_hphi_tune(q,directory/'resumed',checkpoint=first)
    (directory/'result.json').write_text(json.dumps(final,indent=2)+'\n')
    if final['status'] != 'TUNED':
        raise AssertionError(f'nonuniform tuning failed: {final["status"]}')
    checks = []
    for index,(trial,path) in enumerate(zip(final['trials'],final['trial_runs'])):
        solution = read_hphi_run(Path(path)/'solution')
        mode = trial['current_mode_ids'].index(q['mode_id'])
        length = .375*(1+(trial['value']-1)/8)
        exact_frequency = 3*C0/(2*length)
        frequency_error = abs(solution.frequencies_hz[mode]/exact_frequency-1)
        # q=cos(3*pi*z/L) satisfies natural PEC on every vertical wall and on
        # horizontal hole faces at z=L/3 and 2L/3. Identify it by its full q
        # mass overlap, independently of frequency order or the tracked ID.
        exact_q = np.cos(3*np.pi*solution.space.dof_points[:,1]/length)
        actual_q = solution.coefficients[:,mode]
        mass = solution.mass
        overlap = abs(actual_q@(mass@exact_q))/np.sqrt((actual_q@(mass@actual_q))*(exact_q@(mass@exact_q)))
        if frequency_error > 3e-4 or overlap < .999:
            raise AssertionError(f'analytic holed TEM mismatch: f={frequency_error}, q={overlap}')
        checks.append(dict(index=index,rank=mode+1,frequency_hz=float(solution.frequencies_hz[mode]),
            reference_hz=exact_frequency,relative_frequency_error=float(frequency_error),q_mass_overlap=float(overlap)))
    if final['trials'][:2] != first['trials'] or final['trial_sources_sha256'][:2] != first['trial_sources_sha256']:
        raise AssertionError('resumed ancestry changed')
    for old,new in zip(first['trial_runs'],final['trial_runs']):
        for p in Path(old).rglob('*'):
            if p.is_file() and p.read_bytes() != (Path(new)/p.relative_to(old)).read_bytes():
                raise AssertionError('owned Project/native copy changed')
    (directory/'first').rename(directory/'moved-original')
    checkpoint = directory/'resumed'/f'checkpoint-{len(final["trials"]):03d}.json'
    with patch('superfish_ng.hphi_tuning_saved.solve_hphi',side_effect=AssertionError('replay called solver')):
        if read_hphi_tune(checkpoint) != final or cli(['replay-tune-hphi',str(checkpoint)]) != 0:
            raise AssertionError('owned replay mismatch')
    changed = deepcopy(final)
    changed['request']['mapping']['displacements_rz_m'][0][1] += 1e-4
    try:replay_hphi_tune(changed)
    except ValueError:pass
    else:raise AssertionError('changed shape law accepted')
    report = dict(status='PASS',case='synthetic holed vacuum, not a measured cavity',trials=checks,
        final_decision=final['decision'],owned_native_prefix_unchanged=True,source_move_replay=True,
        changed_shape_law_rejected=True,frequency_tolerance=3e-4,minimum_q_mass_overlap=.999)
    (directory/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    validate(parser.parse_args().out.resolve())

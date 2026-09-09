# SPDX-License-Identifier: Apache-2.0
"""Bessel spectrum, Maxwell scaling and energy invariants for native TE sweeps."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from scipy.special import jn_zeros
from validate_curved_te import fingerprint
from superfish_ng import Case
from superfish_ng.constants import C0, TAU
from superfish_ng.model import Model
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study
from superfish_ng.te_saved import read_te_run
from superfish_ng.study_mode_tracking import build_study_mode_tracking, replay_study_mode_tracking

parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
out = parser.parse_args().out.resolve()
out.mkdir(parents=True, exist_ok=False)
before = fingerprint()
roots = jn_zeros(1, 3)
aspect = float(np.pi*np.sqrt(8/(roots[1]**2-roots[0]**2)))
controls = dict(mapping='normalized_cylinder', sample_order=24, minimum_overlap=.98,
                minimum_assignment_margin=.05, relative_cluster_gap=.001,
                minimum_relative_singular_value=1e-8)
rows, baseline = [], {}
for order in (1, 2):
    for scale in (1., 2.):
        radius = .1*scale
        case = Case(((0., radius), (radius*aspect, radius)), nr=96 if order == 1 else 64, nz=144 if order == 1 else 96,
                    element_order=order, modes=6, model=Model(polarization='te'))
        values = [float(radius*aspect*x) for x in (.97, 1.03)]
        study = Study(Project(case), 'sweep', '/case/geometry/points_zr_m/1/0', values)
        path = out/f'p{order}-scale{scale:g}'
        result = execute_study(study, path)
        assert result['numerical_status'] == 'UNVERIFIED'
        assert result['mode_tracking'] == 'not performed; independent spectra'
        labels, errors, frequencies = [], [], []
        for point, length in zip(result['points'], values):
            spectrum = sorted((C0/TAU*np.hypot(root/radius, n*np.pi/length), p, n)
                              for p, root in enumerate(roots, 1) for n in range(1, 7))[:6]
            labels.append([f'r{p}z{n}' for f, p, n in spectrum])
            frequencies.append([m['frequency_hz'] for m in point['modes']])
            for mode, (frequency, p, n) in zip(point['modes'], spectrum):
                errors.append(abs(mode['frequency_hz']/frequency-1))
                assert mode['r_over_q_accelerator_ohm'] is None
                assert mode['r_over_q_circuit_ohm'] is None
        assert max(errors) < (8e-4 if order == 1 else 1e-5), errors
        request = dict(schema_version=1, study_run=str(path), initial_ids=labels[0],
                       step_controls=[controls])
        tracking = build_study_mode_tracking(request)
        assert tracking['status'] == 'PASS'
        assert tracking['history']['current_mode_ids'] == labels[1]
        assert replay_study_mode_tracking(tracking) == tracking
        request_path = out/f'{path.name}-request.json'
        request_path.write_text(json.dumps(request))
        saved = out/f'{path.name}-tracking.json'
        for args in [('track-study-modes', str(request_path), '--out', str(saved)),
                     ('replay-study-mode-tracking', str(saved))]:
            run = subprocess.run([sys.executable, '-m', 'superfish_ng', *args], capture_output=True, text=True)
            assert run.returncode == 0, run.stdout+run.stderr
        assert json.loads(saved.read_text()) == tracking
        frequencies = np.array(frequencies)
        if scale == 1:
            baseline[order] = frequencies
        else:
            np.testing.assert_allclose(frequencies*scale, baseline[order], rtol=1e-10, atol=0)
        # Separate sweep: field amplitude follows sqrt(U), f and G do not.
        normalized = Study(Project(case), 'sweep', '/case/rf/normalization_j', [1., 4.])
        norm_path = out/f'{path.name}-normalization'
        report = execute_study(normalized, norm_path)
        a, b = [read_te_run(norm_path/p['directory']/'solution') for p in report['points']]
        np.testing.assert_allclose(np.abs(b.coefficients_v_per_m2), 2*np.abs(a.coefficients_v_per_m2), rtol=1e-10, atol=1e-6)
        for x, y in zip(*(p['modes'] for p in report['points'])):
            for key in ('frequency_hz', 'geometry_factor_ohm', 'q0'):
                np.testing.assert_allclose(y[key], x[key], rtol=1e-10)
            for key in ('stored_energy_j', 'wall_loss_w'):
                np.testing.assert_allclose(y[key], 4*x[key], rtol=1e-10)
        rows.append(dict(order=order, scale=scale, maximum_frequency_relative_error=max(errors)))
        print(rows[-1], flush=True)
assert fingerprint() == before
(out/'report.json').write_text(json.dumps(dict(passed=True, new_fem_solves=16,
    cli_tracking_and_replay_cases=4, rows=rows, source_sha256=before), indent=2))

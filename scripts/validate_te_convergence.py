# SPDX-License-Identifier: Apache-2.0
"""Independent cylinder checks for TE Study refinement gates and scaling."""
import argparse
import json
from pathlib import Path
import numpy as np
from validate_te import analytic
from validate_curved_te import fingerprint
from superfish_ng import Case
from superfish_ng.model import Model
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study, compare_refinement
from superfish_ng.te import TEFieldSampler
from superfish_ng.te_saved import read_te_run

parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
out = parser.parse_args().out.resolve()
out.mkdir(parents=True, exist_ok=False)
before = fingerprint()
rows, baseline = [], {}
for order in (1, 2):
    for scale in (1., 2.):
        radius, length = .1*scale, .2*scale
        case = Case(((0., radius), (length, radius)), nr=12, nz=18, modes=2,
                    element_order=order, model=Model(polarization='te'))
        run = out/f'p{order}-scale{scale:g}'
        report = execute_study(Study(Project(case), 'mesh_convergence', 'mesh_scale', [1, 2, 4]), run)
        exact, evaluate = analytic(radius, length, 1., 2)
        x, w = np.polynomial.legendre.leggauss(96)
        rho = (x+1)/2
        points = np.array([(radius*r, length*z) for r in rho for z in rho])
        weights = (w[:, None]*w[None, :]*rho[:, None]).ravel()
        levels = []
        for point in report['points']:
            saved = read_te_run(run/point['directory']/'solution')
            sampler = TEFieldSampler(saved)
            modes = []
            for mode, reference in enumerate(exact):
                actual = sampler.evaluate(points, mode)
                fields, geometry_factor = evaluate(reference, points)
                sign = 1 if np.dot(weights, actual['Ephi_V_per_m']*fields['Ephi_V_per_m']) >= 0 else -1
                electric = np.sqrt(np.dot(weights, (sign*actual['Ephi_V_per_m']-fields['Ephi_V_per_m'])**2)/np.dot(weights, fields['Ephi_V_per_m']**2))
                magnetic = np.sqrt(sum(np.dot(weights, (sign*actual[k]-fields[k])**2) for k in ('Hr_quadrature_A_per_m', 'Hz_quadrature_A_per_m'))/sum(np.dot(weights, fields[k]**2) for k in ('Hr_quadrature_A_per_m', 'Hz_quadrature_A_per_m')))
                q = point['modes'][mode]
                assert q['r_over_q_accelerator_ohm'] is None
                modes.append(dict(frequency=abs(q['frequency_hz']/reference[0]-1), electric=float(electric),
                                  magnetic=float(magnetic), geometry_factor=abs(q['geometry_factor_ohm']/geometry_factor-1)))
            levels.append(dict(value=point['value'], modes=modes))
        for mode in range(2):
            for key in ('frequency', 'electric', 'magnetic', 'geometry_factor'):
                errors = [level['modes'][mode][key] for level in levels]
                assert all(b < a for a, b in zip(errors, errors[1:])), (order, scale, key, errors)
        if order == 1:
            assert report['numerical_status'] != 'PASS'
            assert any(not m['gates']['magnetic_field'] or not m['gates']['rf'] for m in report['comparisons'][-1]['modes'])
        else:
            assert report['numerical_status'] == 'PASS', report['comparisons'][-1]
            for mode in levels[-1]['modes']:
                assert mode['frequency'] < 1e-4 and mode['electric'] < .01 and mode['magnetic'] < .01 and mode['geometry_factor'] < .005
        p, q = report['points'][-2:]
        assert compare_refinement(run/p['directory']/'solution', run/q['directory']/'solution') == report['comparisons'][-1]
        frequencies = np.array([[m['frequency_hz'] for m in point['modes']] for point in report['points']])
        if scale == 1:
            baseline[order] = frequencies, report['numerical_status']
        else:
            np.testing.assert_allclose(frequencies*scale, baseline[order][0], rtol=1e-10, atol=0)
            assert report['numerical_status'] == baseline[order][1]
        row = dict(order=order, scale=scale, numerical_status=report['numerical_status'], levels=levels)
        rows.append(row)
        (out/'partial.json').write_text(json.dumps(rows, indent=2))
        print(order, scale, report['numerical_status'], flush=True)
assert before == fingerprint()
(out/'report.json').write_text(json.dumps(dict(passed=True, new_fem_solves=12,
    rows=rows, source_sha256=before), indent=2))

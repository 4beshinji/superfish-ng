# SPDX-License-Identifier: Apache-2.0
"""Prepare scoped Cartesian black-box decks; no reference physics is accepted.

The executable, version-specific polarization interpretation and output units
must be established independently before these candidate decks become a
comparison. This tool never executes Wine or substitutes an analytic solver.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from superfish_ng.constants import C0
from superfish_ng.planar import PlanarCase

FORMAT = 'superfish_ng_planar_reference_preparation'
REFERENCE_REASON = ('reference not executed; Cartesian boundary/polarization, '
                    'signed components and per-length output units need 7.17 verification')


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def candidate_inputs(case, indices, dx_cm, target_hz):
    """Return independently authored, full-rectangle AF/SEG/IN7/INI candidates.

    NBS=1 for the candidate Hz Neumann problem and NBS=0 for the candidate
    complementary Dirichlet problem are hypotheses, not accepted 7.17 physics.
    A frequency guess is only a search hint; the mode needs actual E/H matching.
    """
    if type(case) is not PlanarCase:
        raise ValueError('preparation supports an explicit vacuum Cartesian rectangle only')
    m, n = indices
    if (type(m) is not int or type(n) is not int or min(m, n) < 0
            or m + n == 0 or (case.polarization == 'tm' and min(m, n) == 0)):
        raise ValueError('invalid positive rectangular TE/TM modal indices')
    import math
    if not math.isfinite(dx_cm) or dx_cm <= 0 or not math.isfinite(target_hz) or target_hz <= 0:
        raise ValueError('positive finite mesh spacing and frequency hint required')
    a, b = case.width_m * 100, case.height_m * 100
    boundary = 1 if case.polarization == 'te' else 0
    # Choose a nonnodal longitudinal-scalar drive position for this analytic label.
    xdrive = a / (3 * max(m, 1))
    ydrive = b / (3 * max(n, 1))
    af = ('Independent synthetic Cartesian cutoff candidate; physics UNVERIFIED\n'
          f'$reg kprob=1, icylin=0, conv=1, dx={dx_cm:.12g},\n'
          f'freq={target_hz * .997 / 1e6:.12g}, xdri={xdrive:.12g}, ydri={ydrive:.12g},\n'
          f'nbslo={boundary}, nbsup={boundary}, nbslf={boundary}, nbsrt={boundary}, epsik=1e-10 $\n'
          + ''.join(f'$po x={x:.12g}, y={y:.12g} $\n'
                    for x, y in [(0, 0), (0, b), (a, b), (a, 0), (0, 0)]))
    lines = [(0, b / 3, a, b / 3), (a / 3, 0, a / 3, b),
             (0, 0, 0, b), (0, b, a, b), (a, 0, a, b), (0, 0, a, 0)]
    in7 = ''.join('line plotfiles\n' + ' '.join(f'{v:.12g}' for v in line)
                  + '\n400\n' for line in lines) + 'end\n'
    return {'cavity.af': af, 'cavity.seg': 'FieldSegments\n1 2 3 4\nEndData\nEnd\n',
            'cavity.in7': in7,
            'SF.INI': '[Global]\nTAPE40=C\nStoreTempDataInRAM=No\n[SF7]\nDecimalPlaces=10\nExpandedTable=No\n'}


def prepare(out, *, project_root=ROOT, source_catalog=None):
    """Write a new ignored output tree and a strict, non-PASS case manifest."""
    out = Path(out).resolve()
    project_root = Path(project_root).resolve()
    allowed = project_root / 'out'
    if out == allowed or not out.is_relative_to(allowed):
        raise ValueError('raw reference preparation must be a new subdirectory of project out/')
    catalog = None
    if source_catalog is not None:
        from planar_reference_sources import load_source_catalog
        catalog = load_source_catalog(source_catalog, project_root)
    out.mkdir(parents=True, exist_ok=False)
    report = {'format': FORMAT, 'schema_version': 1, 'status': 'UNVERIFIED',
              'passed': False, 'new_legacy_runs': 0, 'new_ng_solves': 0,
              'scope': 'synthetic vacuum closed PEC rectangular cutoff; TE10/TE01/TM11; two scales',
              'reference_version': {'expected': '7.17', 'observed': None, 'status': 'UNVERIFIED'},
              'reason': REFERENCE_REASON,
              'limits': {'frequency_relative': 1e-4, 'fields_relative_l2': .01,
                         'geometry_factor_relative': .005, 'timeout_seconds_per_process': 120},
              'mode_matching': 'joint signed E/H comparison with one common phase; no rank or frequency-only assignment',
              'surface': 'separate wall integral and sampled peak; no peak accuracy inferred from f or G',
              'normalization': 'NG peak exp(+i omega t), Uprime=1 J/m; legacy conversion UNVERIFIED',
              'accelerating_quantities': {'status': 'N/A', 'reason': 'cutoff section without a finite accelerating path'},
              'output_redistribution': False, 'files': {}, 'cases': []}
    for scale in (1, 2):
        for polarization, m, n in [('te', 1, 0), ('te', 0, 1), ('tm', 1, 1)]:
            a, b = .31 * scale, .2 * scale
            target = C0 / 2 * ((m / a)**2 + (n / b)**2)**.5
            name = f'{polarization}{m}{n}-scale{scale}'
            item = {'id': name, 'synthetic': True, 'polarization': polarization,
                    'analytic_label': [m, n], 'analytic_target_hz': target,
                    'legacy_polarization_candidate': {'status': 'UNVERIFIED',
                        'icylin': 0, 'all_outer_nbs': 1 if polarization == 'te' else 0,
                        'hypothesis': 'Hz Neumann TE / complementary scalar Dirichlet TM; actual 7.17 fields must confirm'},
                    'analytic_role': 'independent search hint and invariant; never the NG solution',
                    'mode_correspondence': {'status': 'UNVERIFIED', 'ng_mode_index': None, 'reference_mode': None},
                    'gates': {q: {'status': 'UNVERIFIED', 'reason': REFERENCE_REASON}
                              for q in ['frequency', 'fields', 'rf_integrals', 'surface_fields']},
                    'acceptance_axes': {q: {'status': 'UNVERIFIED', 'reason': 'no legacy comparison or general AF conversion performed'}
                                        for q in 'FIONW'}, 'levels': []}
            for level in (16, 32, 64):
                folder = out / name / f'level-{level}'
                folder.mkdir(parents=True)
                case = PlanarCase(a, b, polarization, nx=level, ny=level,
                                  modes=4, name=f'Independent {name} comparison candidate')
                write_json(folder / 'ng-case.json', case.to_dict())
                dx_cm = min(a, b) * 100 / level
                for filename, contents in candidate_inputs(case, (m, n), dx_cm, target).items():
                    with (folder / filename).open('x', encoding='utf-8') as stream:
                        stream.write(contents)
                relative = folder.relative_to(out).as_posix()
                project_relative = folder.relative_to(project_root).as_posix()
                item['levels'].append({'level': level, 'path': relative, 'sf_dx_cm': dx_cm,
                                       'ng_mesh': {'nx': level, 'ny': level, 'element_order': 2},
                                       'reference_run': {'status': 'NOT_RUN', 'exit_code': None,
                                                         'expected_command': ['wine', r'C:\LANL\AUTOFISH.EXE', 'cavity.af'],
                                                         'working_directory': relative,
                                                         'timeout_seconds': 120},
                                       'ng_run': {'status': 'NOT_RUN', 'exit_code': None,
                                                  'working_directory': str(project_root),
                                                  'expected_command': ['uv', 'run', '--no-sync', 'python', '-m',
                                                                       'superfish_ng', 'solve-planar', f'{project_relative}/ng-case.json',
                                                                       '--out', f'{project_relative}/ng-result']}})
            item['both_sides_refinement'] = {'status': 'UNVERIFIED', 'reason': 'three input levels prepared; neither solver executed'}
            report['cases'].append(item)
    if catalog is not None:
        from planar_reference_sources import append_source_cases
        append_source_cases(report, out, catalog, project_root)
    for path in sorted(out.rglob('*')):
        if path.is_file():
            report['files'][path.relative_to(out).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(out / 'comparison.json', report)
    return report

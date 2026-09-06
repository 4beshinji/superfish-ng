# SPDX-License-Identifier: Apache-2.0
"""Reproducible NG surface-field diagnostics, without solver corrections.

The synthetic necked cavity is evaluated with sharp corners and with tangent
3 mm fillets. This does not substitute for a Wine surface-field comparison.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import scipy
from scipy.special import j0
from superfish_ng import Case, solve
from superfish_ng.analytic import pillbox_tm_mode
from superfish_ng.constants import EPS0, TAU
from superfish_ng.geometry import linearize_profile
from superfish_ng.mesh import element_geometry
from superfish_ng.rf import quantities
from compare_superfish import write_deck


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def fillet_case(base, radius_m=.003, chord_m=1e-6):
    """Trim each interior corner and insert a tangent circular minor arc.

    This bounded diagnostic supports strictly increasing-z, noncollinear
    segments and rejects overlapping fillets. Both turn directions are kept.
    """
    if not np.isfinite(radius_m) or radius_m <= 0:
        raise ValueError('fillet radius must be finite and positive')
    vertices = np.array(base.profile)
    delta = np.diff(vertices, axis=0)
    length = np.linalg.norm(delta, axis=1)
    directions = delta / length[:, None]
    turns = np.arctan2(directions[:-1, 0]*directions[1:, 1]
                      - directions[:-1, 1]*directions[1:, 0],
                      np.sum(directions[:-1]*directions[1:], axis=1))
    if np.any(np.abs(turns) < 1e-12):
        raise ValueError('fillet diagnostic requires noncollinear interior corners')
    trims = radius_m*np.tan(np.abs(turns)/2)
    if np.any(np.r_[0., trims] + np.r_[trims, 0.] >= length):
        raise ValueError('fillet radius overlaps neighboring fillets or endpoints')
    points, arcs = [base.profile[0]], []
    for i, (trim, turn) in enumerate(zip(trims, turns), 1):
        points.append(tuple(vertices[i]-trim*directions[i-1]))
        points.append(tuple(vertices[i]+trim*directions[i]))
        arcs.append((len(points)-1, radius_m, 'ccw' if turn > 0 else 'cw'))
    points.append(base.profile[-1])
    return replace(base, profile=tuple(points), geometry_type='arc_profile',
                   arcs=tuple(arcs), arc_chord_tolerance_m=chord_m,
                   name='synthetic necked cavity with tangent 3 mm fillets; not measured')


def surface_data(solution):
    """Endpoint fields from the owning PEC triangle, never vertex averaged."""
    mesh, u = solution.mesh, solution.u[:, 0]
    pec = mesh.boundary_tags == 'pec'
    edges, cells = mesh.boundary_edges[pec], mesh.boundary_cells[pec]
    ends = mesh.points[edges]
    vertices, _, grad = element_geometry(mesh)
    du = np.einsum('ti,tij->tj', u[mesh.triangles], grad)[cells]
    omega = TAU*solution.frequencies_hz[0]
    er = -ends[:, :, 0]*du[:, None, 1]/(omega*EPS0)
    ez = (2*u[edges]+ends[:, :, 0]*du[:, None, 0])/(omega*EPS0)
    fields = np.stack((er, ez), axis=-1)
    cell_vertices = vertices[cells]
    diameter = np.max(np.linalg.norm(cell_vertices-np.roll(cell_vertices, 1, axis=1), axis=2), axis=1)
    return ends, fields, diameter


def probe_surface(ends, fields, diameter, point_rz):
    """All one-sided traces at a surface coordinate, including mesh vertices."""
    delta = ends[:, 1]-ends[:, 0]
    h = np.linalg.norm(delta, axis=1)
    offset = np.asarray(point_rz)-ends[:, 0]
    t = np.sum(offset*delta, axis=1)/h**2
    distance = np.abs(offset[:, 0]*delta[:, 1]-offset[:, 1]*delta[:, 0])/h
    match = (distance < 1e-11) & (t >= -1e-10) & (t <= 1+1e-10)
    if not match.any():
        raise ValueError('surface probe does not lie on a PEC mesh edge')
    fraction = np.clip(t[match], 0, 1)
    value = (1-fraction[:, None])*fields[match, 0]+fraction[:, None]*fields[match, 1]
    magnitude = np.linalg.norm(value, axis=1)
    tangent = delta[match]/h[match, None]
    return {'point_rz_m': list(point_rz), 'e_min_v_per_m': float(magnitude.min()),
            'e_max_v_per_m': float(magnitude.max()),
            'tangential_e_max_v_per_m': float(np.max(np.abs(np.sum(value*tangent, axis=1)))),
            'trace_count': int(match.sum()), 'edge_h_max_m': float(h[match].max()),
            'cell_diameter_max_m': float(diameter[match].max())}


def sharp_probes(base):
    vertices = np.array(base.profile)
    result = []
    for i, corner in enumerate(vertices[1:-1], 1):
        for side, neighbor in [('before', vertices[i-1]), ('after', vertices[i+1])]:
            direction = (neighbor-corner)/np.linalg.norm(neighbor-corner)
            for distance in [.0005, .001, .002, .004, .008]:
                result.append({'corner_index': i, 'side': side, 'distance_m': distance,
                               'point_rz_m': (corner+distance*direction)[::-1].tolist()})
    return result


def run_case(case, folder, probes=(), analytic=None):
    folder.mkdir()
    write_json(folder/'case.json', case.to_dict())
    start = time.perf_counter()
    solution = solve(case)
    q = quantities(case, solution)
    ends, fields, diameter = surface_data(solution)
    magnitude = np.linalg.norm(fields, axis=2)
    edge, endpoint = np.unravel_index(np.argmax(magnitude), magnitude.shape)
    probe_rows = [dict(p, **{k: v for k, v in probe_surface(ends, fields, diameter, p['point_rz_m']).items()
                           if k != 'point_rz_m'}) for p in probes]
    row = {'nr': case.nr, 'nz': case.nz, 'triangulation': case.triangulation,
           'nodes': len(solution.mesh.points), 'triangles': len(solution.mesh.triangles),
           'seconds': time.perf_counter()-start, 'quantities': q,
           'peak_point_rz_m': ends[edge, endpoint].tolist(),
           'peak_edge_h_m': float(np.linalg.norm(ends[edge, 1]-ends[edge, 0])),
           'peak_cell_diameter_m': float(diameter[edge]), 'probes': probe_rows}
    if analytic:
        exact_e = analytic['e0_v_per_m']*np.abs(j0(analytic['radial_wave_number_per_m']*ends[:, :, 0]))
        row['analytic'] = {
            'peak_relative_error': abs(q['epk_surface_estimate_v_per_m']/analytic['e0_v_per_m']-1),
            'surface_max_absolute_error_over_e0': float(np.max(np.abs(magnitude-exact_e))/analytic['e0_v_per_m']),
            'frequency_relative_error': abs(q['frequency_hz']/analytic['frequency_hz']-1)}
    np.savez_compressed(folder/'surface.npz', endpoints_rz_m=ends, electric_er_ez_v_per_m=fields,
                        owner_cell_diameter_m=diameter)
    write_json(folder/'result.json', row)
    print(f'{folder.name}: nodes={row["nodes"]} Epk={q["epk_surface_estimate_v_per_m"]:.8g} V/m '
          f'Epk/Eacc={q["epk_over_eacc_estimate"]:.7f}', flush=True)
    return row


def source_hashes():
    paths = sorted((ROOT/'src/superfish_ng').glob('*.py')) + [Path(__file__).resolve()]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--levels', type=int, nargs='+', default=[24, 48, 96, 192, 384])
    parser.add_argument('--rounded-levels', type=int, nargs='+', default=[48, 96, 192])
    args = parser.parse_args()
    for levels in (args.levels, args.rounded_levels):
        if len(levels) < 3 or min(levels) < 2 or sorted(set(levels)) != levels:
            parser.error('levels must contain at least three strictly increasing integers >= 2')
    out = args.out.resolve()
    if not out.is_relative_to(ROOT/'out') or out == ROOT/'out':
        parser.error('diagnostic output must be a new directory under project out/')
    out.mkdir(parents=True, exist_ok=False)
    base = replace(Case.load(ROOT/'examples/shaped_cell.json'), modes=1,
                   conductivity_s_per_m=1/1.7241e-8)
    probes = sharp_probes(base)
    report = {'status': 'NG_DIAGNOSTICS_ONLY_WINE_UNVERIFIED',
              'normalization': 'peak phasors, stored energy 1 J; no field smoothing',
              'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__},
              'source_sha256': source_hashes(), 'runs': {},
              'limitations': ['No Wine surface data: no ranking of solver accuracy.',
                             'Sharp corner peaks need not have a finite limit.',
                             'Last mesh changes are diagnostics, not rigorous error bounds.',
                             'Rounded geometry is a new synthetic control, not the historical sharp geometry.']}
    write_json(out/'probe_coordinates.json', probes)
    for triangulation in ['diagonal', 'crossed']:
        key = 'sharp_'+triangulation
        report['runs'][key] = []
        for n in args.levels:
            case = replace(base, nr=n, nz=round(n*base.length/.105), triangulation=triangulation)
            report['runs'][key].append(run_case(case, out/f'{key}-{n}', probes))
            write_json(out/'report.json', report)
    # Control: an exact TM010 field over both endplates and the cylindrical wall.
    report['runs']['pillbox'] = []
    exact = pillbox_tm_mode(.075, .08)
    for n in [24, 48, 96]:
        case = Case(((0., .075), (.08, .075)), nr=n, nz=round(n*.08/.075), modes=1)
        report['runs']['pillbox'].append(run_case(case, out/f'pillbox-{n}', analytic=exact))
    for tolerance in [1e-6, .25e-6]:
        arc = fillet_case(base, chord_m=tolerance)
        # Use the same radially fitted mesher as the sharp experiment. Save the
        # exact arc input separately; the solve consumes its explicit polygon.
        write_json(out/f'fillets-{tolerance:g}.json', arc.to_dict())
        polygon = replace(base, profile=linearize_profile(arc), name=arc.name)
        key = f'rounded-chord-{tolerance:g}'
        report['runs'][key] = []
        for n in args.rounded_levels:
            case = replace(polygon, nr=n, nz=round(n*base.length/.105))
            report['runs'][key].append(run_case(case, out/f'{key}-{n}'))
            write_json(out/'report.json', report)
    # Fresh input decks can later be run in the authorized Wine installation.
    # Export the identical polygon, avoiding an unverified clockwise arc export.
    for name, case in [('sharp', base), ('rounded-polygon', polygon)]:
        for dx in [.2, .1, .05, .025]:
            folder = out/f'wine-input-{name}-dx{dx}'
            folder.mkdir()
            write_deck(case, folder, dx, 1270.)
    report['source_changed_during_run'] = source_hashes() != report['source_sha256']
    write_json(out/'report.json', report)
    return int(report['source_changed_during_run'])


if __name__ == '__main__':
    raise SystemExit(main())

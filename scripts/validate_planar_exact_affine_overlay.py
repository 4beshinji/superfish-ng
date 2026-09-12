# SPDX-License-Identifier: Apache-2.0
"""Independent rectangle eigenfields/RF for exact affine overlay geometry.

Different boundary densities, TE/TM, P1/P2, two refinements and two SI scales.
Closed-form sine/cosine fields and side-wall integrals are validation references
only. This checks a geometry API, not mode identification or saved tracking.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from superfish_ng.constants import C0, EPS0, MU0
from superfish_ng.fem import triangle_quadrature
from superfish_ng.planar import solve_planar, planar_quantities
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_saved import save_planar_run, read_planar_run
from superfish_ng.planar_tracking_exact_affine import exact_affine_polygon_overlay
from superfish_ng.planar_tracking_fields import _electric_grams


def rectangle(n, width, height, flip, reflected):
    points = np.array([(width*i/n, height*j/n) for j in range(n+1) for i in range(n+1)])
    cells = []
    for j in range(n):
        for i in range(n):
            a = j*(n+1)+i
            b, d = a+1, a+n+1
            c = d+1
            cells.extend([(a, b, d), (b, c, d)] if flip else [(a, b, c), (a, c, d)])
    polygon = np.array([[0., 0.], [width, 0.], [width, height], [0., height]])
    if reflected:
        points[:, 0] *= -1
        polygon[:, 0] *= -1
        polygon = polygon[::-1]
        cells = np.asarray(cells)[:, [0, 2, 1]]
    return PlanarMesh.create(polygon, points, cells)


def analytic_rf(width, height, polarization, energy, conductivity):
    kx, ky = np.pi/width, (np.pi/height if polarization == 'tm' else 0.)
    omega = C0*np.hypot(kx, ky)
    if polarization == 'te':
        geometry = omega*MU0*width*height*.5/(2*height+width)
    else:
        geometry = omega*MU0*(kx*kx+ky*ky)*width*height/(4*(height*kx*kx+width*ky*ky))
    q0 = geometry/np.sqrt(omega*MU0/(2*conductivity))
    return dict(frequency_hz=omega/(2*np.pi), geometry_factor_ohm=geometry,
                q0=q0, wall_loss_w_per_m=omega*energy/q0)


def field_errors(solution, width, height, reflected):
    case = solution.case
    space = solution.space
    cells = np.arange(len(space.triangles))
    vertices = space.points_xy_m[space.triangles]
    pol = case.polarization
    kx, ky = np.pi/width, (np.pi/height if pol == 'tm' else 0.)
    omega = C0*np.hypot(kx, ky)
    norm = width*height*(.25 if pol == 'tm' else .5)
    amplitude = np.sqrt(2*case.normalization_j_per_m/((EPS0 if pol == 'tm' else MU0)*norm))
    products = np.zeros((2, 3))
    for bary, weight in triangle_quadrature(8):
        xy = np.einsum('j,njk->nk', bary, vertices)
        x, y = xy.T
        if reflected:
            x = -x
        if pol == 'tm':
            scalar = amplitude*np.sin(kx*x)*np.sin(ky*y)
            dx = amplitude*kx*np.cos(kx*x)*np.sin(ky*y)
            dy = amplitude*ky*np.sin(kx*x)*np.cos(ky*y)
        else:
            scalar = amplitude*np.cos(kx*x)
            dx = -amplitude*kx*np.sin(kx*x)
            dy = np.zeros_like(dx)
        if reflected:
            dx = -dx
        actual = solution.fields_in_cells(cells, np.tile(bary, (len(cells), 1)), 0)
        if pol == 'tm':
            reference = [scalar[:, None], np.column_stack((dy, -dx))/(omega*MU0)]
            numerical = [actual['Ez_real_V_per_m'][:, None],
                         np.column_stack((actual['Hx_quadrature_A_per_m'], actual['Hy_quadrature_A_per_m']))]
        else:
            reference = [np.column_stack((-dy, dx))/(omega*EPS0), scalar[:, None]]
            numerical = [np.column_stack((actual['Ex_quadrature_V_per_m'], actual['Ey_quadrature_V_per_m'])),
                         actual['Hz_real_A_per_m'][:, None]]
        weights = weight*space.determinants
        for i, (actual_field, exact_field) in enumerate(zip(numerical, reference)):
            products[i] += [np.sum(weights*np.sum(actual_field**2, axis=1)),
                           np.sum(weights*np.sum(exact_field**2, axis=1)),
                           np.sum(weights*np.sum(actual_field*exact_field, axis=1))]
    # One eigenvector phase for E and H; amplitudes follow U' analytically.
    phase = 1. if products[0 if pol == 'tm' else 1, 2] >= 0 else -1.
    return dict(zip(('electric_relative_l2', 'magnetic_relative_l2'),
        [float(np.sqrt(max(0., (a+b-2*phase*c)/b))) for a, b, c in products]))


def fingerprints():
    root = Path(__file__).resolve().parents[1]
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src', 'tests', 'scripts', 'examples')
            for p in sorted((root/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    source = fingerprints()
    rows = []
    # These are limited geometry/field checks, not general physical accuracy
    # acceptance. Refinement must also improve each analytical error.
    limits = {1: dict(frequency_hz=.003, geometry_factor_ohm=.02, q0=.02, wall_loss_w_per_m=.025,
                      electric_relative_l2=.06, magnetic_relative_l2=.06, gram_error=.003),
              2: dict(frequency_hz=.0001, geometry_factor_ohm=.005, q0=.005, wall_loss_w_per_m=.005,
                      electric_relative_l2=.002, magnetic_relative_l2=.002, gram_error=.0001)}
    matrix = [[-1., 0.], [0., 1.]]
    transport = np.array([[1., 0.], [0., -1.]])
    for pol in ('te', 'tm'):
        for order in (1, 2):
            for scale in (1., 2.):
                sequence = []
                for n in (16, 32):
                    width, height = .5*scale, .25*scale
                    solutions, errors, rf_rows = [], [], []
                    for side, grid, flip, reflected in (('previous', n, False, False), ('current', n*3//2, True, True)):
                        case = PlanarPolygonCase(rectangle(grid, width, height, flip, reflected), pol, order, 1,
                                                 normalization_j_per_m=scale**2)
                        solution = solve_planar(case)
                        native = args.out/f'{pol}-p{order}-s{scale:g}-n{n}-{side}'
                        save_planar_run(case, solution, native)
                        saved = read_planar_run(native)
                        np.testing.assert_array_equal(saved.coefficients, solution.coefficients)
                        rf = planar_quantities(saved)
                        reference = analytic_rf(width, height, pol, case.normalization_j_per_m, case.conductivity_s_per_m)
                        error = {key: abs(rf[key]/value-1.) for key, value in reference.items()}
                        error.update(field_errors(saved, width, height, reflected))
                        errors.append(error)
                        rf_rows.append(rf)
                        solutions.append(saved)
                    overlay = exact_affine_polygon_overlay(solutions[0].case.mesh, solutions[1].case.mesh, linear_xy=matrix)
                    grams = _electric_grams(*solutions, overlay, 5, current_to_previous_rotation=transport)
                    correlation = float(grams[1][0, 0]/np.sqrt(grams[0][0, 0]*grams[2][0, 0]))
                    row = dict(polarization=pol, order=order, scale=scale, n=n, current_n=n*3//2,
                               errors=errors, quantities=rf_rows, gram_error=abs(abs(correlation)-1.),
                               overlay_triangles=len(overlay.previous_cells))
                    rows.append(row)
                    sequence.append(row)
                    print(pol, order, scale, n, row['gram_error'], errors, flush=True)
                for side in (0, 1):
                    for key, value in sequence[-1]['errors'][side].items():
                        assert value < limits[order][key], (pol, order, scale, side, key, value)
                        assert value < sequence[0]['errors'][side][key], (pol, order, scale, side, key, 'did not improve')
                assert sequence[-1]['gram_error'] < limits[order]['gram_error'], sequence[-1]
                assert sequence[-1]['gram_error'] < sequence[0]['gram_error'], sequence
    similarity_error = 0.
    for first in [row for row in rows if row['scale'] == 1.]:
        second = next(row for row in rows if row['scale'] == 2. and all(row[k] == first[k] for k in ('polarization', 'order', 'n')))
        for a, b in zip(first['quantities'], second['quantities']):
            for key, ratio in (('frequency_hz', .5), ('geometry_factor_ohm', 1.), ('q0', np.sqrt(2.)),
                               ('wall_loss_w_per_m', np.sqrt(2.)), ('stored_energy_j_per_m', 4.)):
                similarity_error = max(similarity_error, abs(b[key]/a[key]/ratio-1.))
    assert similarity_error < 1e-10, similarity_error
    assert source == fingerprints(), 'source changed during validation'
    report = dict(passed=True, seconds=time.perf_counter()-started, rows=rows, limits=limits,
                  max_similarity_relative_error=similarity_error, source_sha256=source,
                  scope='exact affine geometry API; no tracking IDs, request dispatch, CLI or GUI acceptance')
    (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('PASS', report['seconds'], similarity_error)


if __name__ == '__main__':
    main()

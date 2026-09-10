# SPDX-License-Identifier: Apache-2.0
"""Independent analytic validation of declared affine + independently remeshed tracking.

Reflection is an exact isometry of the eigenproblem; a rectangular anisotropic
stretch maps Cartesian eigenfunctions onto analytic eigenfunctions. A shear is
a declared numerical correspondence only and is checked by exact moments and
by polynomial fields transported through the declared adjugate. These
references verify the mapping, overlay and transport; they never replace a
FEM solve.
"""
import argparse
from dataclasses import replace
import hashlib
import json
import time
from pathlib import Path
import numpy as np
from superfish_ng.constants import C0, EPS0, MU0
from superfish_ng.fem import triangle_quadrature
from superfish_ng.planar import solve_planar
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_tracking import PlanarTrackingRequest, track_planar_modes
from superfish_ng.planar_tracking_fields import _electric_grams
from superfish_ng.planar_tracking_affine_remesh import (
    PolygonAffineRemeshMapping, polygon_affine_remesh_overlay)

ROTATION90 = np.array([[0., -1.], [1., 0.]])


class TriangleReference:
    """Antisymmetric/symmetric right-isosceles eigenfunctions of leg A."""

    def __init__(self, leg):
        self.leg = leg

    def modes(self, polarization, count):
        seen, result = set(), []
        for number, m, n in sorted((m*m+n*n, m, n) for m in range(1, 7) for n in range(0, m+1)
                                   if polarization == 'te' or 0 < n < m):
            if number not in seen:
                seen.add(number)
                result.append((number, m, n))
            if len(result) == count:
                break
        return result

    def fields(self, points, mode, polarization):
        _, m, n = mode
        x, y = points.T
        A = self.leg
        mx, ny = m*np.pi/A, n*np.pi/A
        if polarization == 'tm':
            q = np.sin(mx*x)*np.sin(ny*y)-np.sin(ny*x)*np.sin(mx*y)
            dx = mx*np.cos(mx*x)*np.sin(ny*y)-ny*np.cos(ny*x)*np.sin(mx*y)
            dy = ny*np.sin(mx*x)*np.cos(ny*y)-mx*np.sin(ny*x)*np.cos(mx*y)
            norm = A*A/4
        else:
            q = np.cos(mx*x)*np.cos(ny*y)+np.cos(ny*x)*np.cos(mx*y)
            dx = -mx*np.sin(mx*x)*np.cos(ny*y)-ny*np.sin(ny*x)*np.cos(mx*y)
            dy = -ny*np.cos(mx*x)*np.sin(ny*y)-mx*np.cos(ny*x)*np.sin(mx*y)
            norm = A*A/2 if (m == 0 or n == 0 or m == n) else A*A/4
        factor = np.sqrt(2/(norm*(EPS0 if polarization == 'tm' else MU0)))
        return q*factor, np.column_stack((dx, dy))*factor

    def exact_frequency(self, mode):
        number, _, _ = mode
        return C0/(2*self.leg)*np.sqrt(number)


class RectangleReference:
    """Cartesian Dirichlet/Neumann eigenfunctions of a rectangle."""

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def modes(self, polarization, count):
        values = []
        for m in range(0, 9):
            for n in range(0, 9):
                if polarization == 'te' and (m, n) == (0, 0):
                    continue
                if polarization == 'tm' and (m == 0 or n == 0):
                    continue
                values.append((C0/2*np.sqrt((m/self.width)**2+(n/self.height)**2), m, n))
        return sorted(values)[:count]

    def fields(self, points, mode, polarization):
        _, m, n = mode
        x, y = points.T
        mx, ny = m*np.pi/self.width, n*np.pi/self.height
        if polarization == 'tm':
            q = np.sin(mx*x)*np.sin(ny*y)
            dx = mx*np.cos(mx*x)*np.sin(ny*y)
            dy = ny*np.sin(mx*x)*np.cos(ny*y)
        else:
            q = np.cos(mx*x)*np.cos(ny*y)
            dx = -mx*np.sin(mx*x)*np.cos(ny*y)
            dy = -ny*np.cos(mx*x)*np.sin(ny*y)
        return q, np.column_stack((dx, dy))


def structured(level, flip):
    A = .2
    coordinates = [(i, j) for i in range(level+1) for j in range(i+1)]
    lookup = {v: k for k, v in enumerate(coordinates)}
    points = np.array(coordinates, dtype=float)*(A/level)
    cells = []
    for i in range(level):
        for j in range(i+1):
            if j == i:
                cells.append([lookup[(i, j)], lookup[(i+1, j)], lookup[(i+1, j+1)]])
            elif flip:
                cells.append([lookup[(i, j)], lookup[(i+1, j)], lookup[(i, j+1)]])
                cells.append([lookup[(i+1, j)], lookup[(i+1, j+1)], lookup[(i, j+1)]])
            else:
                cells.append([lookup[(i, j)], lookup[(i+1, j)], lookup[(i+1, j+1)]])
                cells.append([lookup[(i, j)], lookup[(i+1, j+1)], lookup[(i, j+1)]])
    polygon = points[[lookup[(0, 0)], lookup[(level, 0)], lookup[(level, level)]]]
    return PlanarMesh.create(polygon, points, cells)


def rectangle(nx, ny, width, height, flip):
    points = np.array([[width*i/nx, height*j/ny] for j in range(ny+1) for i in range(nx+1)])
    cells = []
    for j in range(ny):
        for i in range(nx):
            a, b, d = j*(nx+1)+i, j*(nx+1)+i+1, (j+1)*(nx+1)+i
            c = d+1
            cells.extend([(a, b, d), (b, c, d)] if flip else [(a, b, c), (a, c, d)])
    polygon = points[[0, nx, (nx+1)*(ny+1)-1, ny*(nx+1)]]
    return PlanarMesh.create(polygon, points, cells)


def circle_reflection(angle):
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    return rotation@np.diag([-1., 1.])@rotation.T


def analytic_grams(reference, mapping, polarization, modes, overlay, order=8):
    """Declared-correspondence integrals of the analytic eigenfunctions.

    AAA is the previous self-Gram at the pullback in the current frame, the
    independent measure check. All current blocks use the analytic field after
    the declared adjugate transport, exactly as _electric_grams does. Under
    the declared law the transported current equals the previous field.
    """
    matrix, translation = mapping._effective(False)
    inverse = np.linalg.inv(matrix)
    transport = mapping.current_to_previous_linear
    count = len(modes)
    aaa = np.zeros((count, count))
    aba = np.zeros((count, count))
    bbb = np.zeros((count, count))
    for bary, weight in triangle_quadrature(order):
        xy = np.einsum('j,njk->nk', bary, overlay.reference_vertices)
        back = (xy-translation)@inverse.T
        weights = weight*overlay.reference_determinants
        if polarization == 'tm':
            old = [reference.fields(back, mode, 'tm')[0] for mode in modes]
            new = list(old)
        else:
            old, new = [], []
            for mode in modes:
                _, gradient = reference.fields(back, mode, 'te')
                old.append(gradient@ROTATION90.T)
                new.append((gradient@inverse)@ROTATION90.T)
        transported = (list(new) if polarization == 'tm'
                       else [np.einsum('ij,nj->ni', transport, field) for field in new])
        for i in range(count):
            for j in range(count):
                if polarization == 'tm':
                    aaa[i, j] += np.sum(weights*old[i]*old[j])
                    bbb[i, j] += np.sum(weights*transported[i]*transported[j])
                    aba[i, j] += np.sum(weights*old[i]*transported[j])
                else:
                    aaa[i, j] += np.sum(weights*(old[i]*old[j]).sum(axis=1))
                    bbb[i, j] += np.sum(weights*(transported[i]*transported[j]).sum(axis=1))
                    aba[i, j] += np.sum(weights*(old[i]*transported[j]).sum(axis=1))
    return aaa, aba, bbb


def normalized(grams):
    return grams[1]/np.sqrt(np.diag(grams[0]))[:, None]/np.sqrt(np.diag(grams[2]))[None, :]


def fem_analytic_row(previous, current, mapping, reference, modes, polarization, overlay):
    grams = _electric_grams(previous, current, overlay, 5,
                            current_to_previous_rotation=mapping.current_to_previous_linear)
    count = len(modes)
    grams = tuple(gram[:count, :count] for gram in grams)
    aaa, aba, bbb = analytic_grams(reference, mapping, polarization, modes, overlay)
    identity = np.max(np.abs(aaa/np.sqrt(np.diag(aaa))[:, None]/np.sqrt(np.diag(aaa))[None, :]
                             -np.eye(count)))
    analytic_cross = aba/np.sqrt(np.diag(aaa))[:, None]/np.sqrt(np.diag(bbb))[None, :]
    fem_cross = normalized(grams)
    # Eigenvector signs are arbitrary per mode; compare the absolute correspondence.
    error = np.max(np.abs(np.abs(analytic_cross)-np.abs(fem_cross)))
    return float(identity), float(error), grams


def nearest_frequency_error(frequencies, references):
    errors = [min(abs(value/exact-1.) for exact in references) for value in frequencies]
    nearest = [int(np.argmin([abs(value/exact-1.) for exact in references])) for value in frequencies]
    return errors, nearest


parser = argparse.ArgumentParser(description='Independent analytic affine/remesh tracking validation')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--p1-levels', nargs='+', type=int, default=[16, 32])
parser.add_argument('--p2-levels', nargs='+', type=int, default=[8, 16])
args = parser.parse_args()
if any(levels != sorted(set(levels)) or min(levels) < 3 for levels in (args.p1_levels, args.p2_levels)):
    parser.error('mesh levels must be unique increasing integers >= 3')
ROOT = Path(__file__).resolve().parents[1]
OUT = args.out
OUT.mkdir(parents=True, exist_ok=False)
source = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
          for folder in ('src', 'tests', 'scripts', 'examples') for path in sorted((ROOT/folder).rglob('*'))
          if path.is_file() and '__pycache__' not in path.parts}
started = time.monotonic()
reflection = PolygonAffineRemeshMapping(circle_reflection(.6).tolist(), (0., 0.))
stretch = PolygonAffineRemeshMapping([[.9, 0.], [0., 1.05]], (.02, -.01))
reorder = PolygonAffineRemeshMapping([[1.3, 0.], [0., .8]], (.02, -.01))
shear = PolygonAffineRemeshMapping([[1., .1], [0., 1.]], (0., 0.))
rows, shear_rows = [], []
print('section reflection', flush=True)
for order, levels in ((1, args.p1_levels), (2, args.p2_levels)):
    reference = TriangleReference(.2)
    for polarization in ('te', 'tm'):
        modes = reference.modes(polarization, 3)
        count, ids = 2, ['mode-0', 'mode-1']
        for level in levels:
            base = structured(level, False)
            current_mesh = reflection.transform_mesh(structured(level, True))
            previous = solve_planar(PlanarPolygonCase(base, polarization, order, len(modes)))
            current = solve_planar(PlanarPolygonCase(current_mesh, polarization, order, len(modes)))
            result = track_planar_modes(previous, current,
                                        PlanarTrackingRequest(count, count, ids, mapping=reflection))
            overlay = polygon_affine_remesh_overlay(base, current_mesh, reflection)
            identity, cross_error, _ = fem_analytic_row(
                previous, current, reflection, reference, modes, polarization, overlay)
            frequency_errors = [abs(previous.frequencies_hz[index]/reference.exact_frequency(mode)-1)
                                for index, mode in enumerate(modes)]
            frequency_errors += [abs(current.frequencies_hz[index]/reference.exact_frequency(mode)-1)
                                 for index, mode in enumerate(modes)]
            row = dict(section='reflection', order=order, polarization=polarization, level=level,
                       triangles=len(current_mesh.triangles), status=result['status'],
                       result_version=result['result_version'],
                       analytic_identity_residual=identity, analytic_fem_cross_error=cross_error,
                       minimum_overlap=float(min(match['minimum_principal_overlap']
                                                 for match in result['matches'])) if result['matches'] else 0.,
                       maximum_frequency_error=float(np.max(frequency_errors)),
                       overlay_triangles=len(overlay.reference_determinants))
            rows.append(row)
            print(json.dumps(row), flush=True)
            (OUT/'partial.json').write_text(json.dumps(rows, indent=2)+'\n')
print('section anisotropic rectangle', flush=True)
width, height = .31, .20
for order, densities in ((1, [(8, 6), (16, 12)]), (2, [(8, 6), (16, 12)])):
    for polarization in ('te', 'tm'):
        base_reference = RectangleReference(width, height)
        modes = base_reference.modes(polarization, 6)
        count = 4 if polarization == 'te' else 3
        ids = [f'mode-{index}' for index in range(count)]
        for nx, ny in densities:
            current_mesh = stretch.transform_mesh(rectangle(nx, ny, width, height, True))
            previous = solve_planar(PlanarPolygonCase(rectangle(nx, ny, width, height, False),
                                                      polarization, order, len(modes)))
            current = solve_planar(PlanarPolygonCase(current_mesh, polarization, order, len(modes)))
            span = RectangleReference(width*.9, height*1.05)
            current_errors, nearest = nearest_frequency_error(
                current.frequencies_hz[:count], [value for value, _, _ in span.modes(polarization, 14)])
            base_errors, _ = nearest_frequency_error(
                previous.frequencies_hz[:count],
                [value for value, _, _ in base_reference.modes(polarization, 14)])
            result = track_planar_modes(previous, current,
                                        PlanarTrackingRequest(count, count, ids, mapping=stretch))
            overlay = polygon_affine_remesh_overlay(previous.case.mesh, current_mesh, stretch)
            identity, cross_error, _ = fem_analytic_row(
                previous, current, stretch, base_reference, modes[:count], polarization, overlay)
            row = dict(section='anisotropic', order=order, polarization=polarization,
                       density=[nx, ny], scale=[.9, 1.05], triangles=len(current_mesh.triangles),
                       status=result['status'], result_version=result['result_version'],
                       analytic_identity_residual=identity, analytic_fem_cross_error=cross_error,
                       maximum_frequency_error=float(max(current_errors+base_errors)),
                       distinct_nearest=len(set(nearest)) == count,
                       minimum_overlap=float(min(match['minimum_principal_overlap']
                                                 for match in result['matches'])) if result['matches'] else 0.,
                       rank_permutation=[match['current_indices'][0] for match in result['matches']])
            rows.append(row)
            print(json.dumps(row), flush=True)
            (OUT/'partial.json').write_text(json.dumps(rows, indent=2)+'\n')
print('section anisotropic rank crossing', flush=True)
for order, level in ((2, 16),):
    for polarization in ('te', 'tm'):
        base_reference = RectangleReference(width, height)
        modes = base_reference.modes(polarization, 7)
        count = 4
        current_mesh = reorder.transform_mesh(rectangle(16, 12, width, height, True))
        previous = solve_planar(PlanarPolygonCase(rectangle(16, 12, width, height, False),
                                                  polarization, order, len(modes)))
        current = solve_planar(PlanarPolygonCase(current_mesh, polarization, order, len(modes)))
        result = track_planar_modes(previous, current,
                                    PlanarTrackingRequest(count, count,
                                                          [f'mode-{index}' for index in range(count)],
                                                          mapping=reorder))
        row = dict(section='rank-crossing', order=order, polarization=polarization, level=level,
                   status=result['status'], result_version=result['result_version'],
                   rank_permutation=[match['current_indices'][0] for match in result['matches']],
                   individual_ids_complete=result['individual_ids_complete'])
        rows.append(row)
        print(json.dumps(row), flush=True)
print('section shear polynomial transport', flush=True)
functions = [lambda points: points[:, 0]+.3*points[:, 1],
             lambda points: .2+points[:, 0]**2-.5*points[:, 0]*points[:, 1],
             lambda points: -.1*points[:, 1]**2+.4*points[:, 0]]
for mapping in (shear, PolygonAffineRemeshMapping([[1., -.25], [0., 1.]], (.03, .01))):
    for polarization in ('te', 'tm'):
        for order, level in ((1, 16), (2, 8)):
            base = structured(level, False)
            current_mesh = mapping.transform_mesh(structured(level, True))
            previous = solve_planar(PlanarPolygonCase(base, polarization, order, 3))
            current = solve_planar(PlanarPolygonCase(current_mesh, polarization, order, 3))
            matrix, translation = mapping._effective(False)
            inverse = np.linalg.inv(matrix)
            overlay = polygon_affine_remesh_overlay(base, current_mesh, mapping)
            dofs = current.space.dof_points_xy_m
            back = (dofs-translation)@inverse.T
            values = np.column_stack([function(previous.space.dof_points_xy_m) for function in functions])
            old = replace(previous, coefficients=values, frequencies_hz=np.ones(3))
            new = replace(current, coefficients=np.column_stack([function(back) for function in functions]),
                          frequencies_hz=np.ones(3))
            grams = _electric_grams(old, new, overlay, 5,
                                    current_to_previous_rotation=mapping.current_to_previous_linear)
            transportation_error = float(np.max(np.abs(grams[1]-grams[0]))
                                         /max(np.max(np.abs(grams[0])), 1e-300))
            vertices = previous.case.mesh.points_xy_m[previous.case.mesh.triangles]
            determinants = np.linalg.det(np.stack((vertices[:, 1]-vertices[:, 0],
                                                   vertices[:, 2]-vertices[:, 0]), axis=-1))
            det = abs(np.linalg.det(matrix))
            moment_error = 0.
            for px, py in ((2, 0), (0, 3), (2, 1), (1, 2)):
                direct = 0.
                for bary, weight in triangle_quadrature(8):
                    xy = np.einsum('j,tjk->tk', bary, vertices)
                    mapped = xy@matrix.T+translation
                    direct += np.sum(weight*determinants*det*mapped[:, 0]**px*mapped[:, 1]**py)
                layered = 0.
                for bary, weight in triangle_quadrature(8):
                    xy = np.einsum('j,njk->nk', bary, overlay.reference_vertices)
                    layered += np.sum(weight*overlay.reference_determinants*xy[:, 0]**px*xy[:, 1]**py)
                moment_error = max(moment_error, abs(layered/direct-1.))
            result = track_planar_modes(previous, current,
                                        PlanarTrackingRequest(2, 2, ['mode-0', 'mode-1'], mapping=mapping))
            row = dict(section='shear', order=order, level=level, polarization=polarization,
                       shear=list(mapping.linear_xy), status=result['status'],
                       polynomial_transport_error=transportation_error, moment_error=moment_error,
                       overlay_triangles=len(overlay.reference_determinants))
            shear_rows.append(row)
            print(json.dumps(row), flush=True)
            (OUT/'partial.json').write_text(json.dumps(rows+shear_rows, indent=2)+'\n')
invertible = PolygonAffineRemeshMapping([[1., .25], [0., 1.]], (.03, -.02))
rejections = []
for name, action in [
        ('non-invertible linear part', lambda: PolygonAffineRemeshMapping([[1., 1.], [1., 1.]])),
        ('wrong declared shear', lambda: polygon_affine_remesh_overlay(
            structured(6, False), invertible.transform_mesh(structured(5, True)),
            PolygonAffineRemeshMapping([[1., .2], [0., 1.]], (.03, -.02)))),
        ('denser independent boundary', lambda: polygon_affine_remesh_overlay(
            structured(6, False), structured(8, True),
            PolygonAffineRemeshMapping([[1., 0.], [0., 1.]], (0., 0.)))),
        ('unreflected candidate', lambda: polygon_affine_remesh_overlay(
            structured(6, False), reflection.transform_mesh(structured(6, True)),
            PolygonAffineRemeshMapping([[1., 0.], [0., 1.]], (0., 0.)))),
        ('candidate budget', lambda: polygon_affine_remesh_overlay(
            structured(4, False), structured(4, True),
            PolygonAffineRemeshMapping([[1., 0.], [0., 1.]], (0., 0.), max_candidate_tests=1))),
        ('input triangle budget', lambda: polygon_affine_remesh_overlay(
            structured(4, False), structured(4, True),
            PolygonAffineRemeshMapping([[1., 0.], [0., 1.]], (0., 0.)), max_overlay_triangles=2))]:
    try:
        action()
        rejections.append(dict(name=name, rejected=False))
    except ValueError as exc:
        rejections.append(dict(name=name, rejected=True, reason=str(exc)))
assert source == {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in source}
finest_reflection = [row for row in rows if row['section'] == 'reflection'
                     and ((row['order'] == 1 and row['level'] == args.p1_levels[-1])
                          or (row['order'] == 2 and row['level'] == args.p2_levels[-1]))]
anisotropic = [row for row in rows if row['section'] == 'anisotropic']
rank_crossing = [row for row in rows if row['section'] == 'rank-crossing']
passed = (all(row['status'] == 'PASS' and row['result_version'] == 6 for row in finest_reflection)
          and all(row['analytic_identity_residual'] < 5e-9
                  and row['analytic_fem_cross_error'] < (5e-3 if row['order'] == 2 else 5e-2)
                  and row['maximum_frequency_error'] < (1e-3 if row['order'] == 2 else 1e-1)
                  for row in finest_reflection)
          and all(row['status'] == 'PASS' and row['result_version'] == 6
                  for row in anisotropic if row['density'] == [16, 12])
          and all(row['analytic_identity_residual'] < 5e-9
                  and row['analytic_fem_cross_error'] < (5e-3 if row['order'] == 2 else 5e-2)
                  and row['maximum_frequency_error'] < (5e-3 if row['order'] == 2 else 5e-2)
                  and row['distinct_nearest'] for row in anisotropic if row['density'] == [16, 12])
          and all(row['status'] == 'PASS' for row in rank_crossing if row['polarization'] == 'te')
          and any(row['rank_permutation'] != [1, 2, 3, 4] for row in rank_crossing if row['polarization'] == 'te')
          and all(row['polynomial_transport_error'] < (1e-4 if row['order'] == 1 else 1e-10)
                  and row['moment_error'] < 1e-9 for row in shear_rows)
          and all(item['rejected'] for item in rejections))
(OUT/'report.json').write_text(json.dumps(dict(passed=passed, rows=rows, shear_rows=shear_rows,
                                               rejections=rejections, seconds=time.monotonic()-started,
                                               source_sha256=source, source_unchanged=True), indent=2)+'\n')
if not passed:
    raise SystemExit('independent affine/remesh tracking gates not all met; refine without relaxing the limits')

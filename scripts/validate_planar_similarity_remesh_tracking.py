# SPDX-License-Identifier: Apache-2.0
"""Independent analytic validation of similarity + independently remeshed tracking.

Right-triangle Cartesian cutoff eigenfunctions are independent references.
They verify the mapping and overlay; they never replace a FEM solve.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np
from superfish_ng.constants import C0, EPS0, MU0
from superfish_ng.fem import triangle_quadrature
from superfish_ng.planar import planar_quantities, solve_planar
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_tracking import PlanarTrackingRequest, track_planar_modes
from superfish_ng.planar_tracking_fields import _electric_grams
from superfish_ng.planar_tracking_similarity_remesh import (
    PolygonSimilarityRemeshMapping, polygon_similarity_remesh_overlay)

A = .2


def analytic(points, m, n, pol):
    x, y = points.T
    mx, ny = m*np.pi/A, n*np.pi/A
    if pol == 'tm':
        q = np.sin(mx*x)*np.sin(ny*y)-np.sin(ny*x)*np.sin(mx*y)
        dx = mx*np.cos(mx*x)*np.sin(ny*y)-ny*np.cos(ny*x)*np.sin(mx*y)
        dy = ny*np.sin(mx*x)*np.cos(ny*y)-mx*np.sin(ny*x)*np.cos(mx*y)
        norm = A*A/4
    else:
        q = np.cos(mx*x)*np.cos(ny*y)+np.cos(ny*x)*np.cos(mx*y)
        dx = -mx*np.sin(mx*x)*np.cos(ny*y)-ny*np.sin(ny*x)*np.cos(mx*y)
        dy = -ny*np.cos(mx*x)*np.sin(ny*y)-mx*np.cos(ny*x)*np.sin(mx*y)
        norm = A*A/2 if n == 0 or m == n else A*A/4
    factor = np.sqrt(2/(norm*(EPS0 if pol == 'tm' else MU0)))
    return q*factor, np.column_stack((dx, dy))*factor


def structured(level, flip):
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


def scalar_points(values, mapping, reverse=False):
    inverse = reverse != mapping.inverse
    c, sine = np.cos(mapping.rotation_radians), np.sin(mapping.rotation_radians)
    tx, ty = mapping.translation_xy_m
    x, y = values.T
    if inverse:
        x, y = x-tx, y-ty
        return np.column_stack(((c*x+sine*y)/mapping.scale, (-sine*x+c*y)/mapping.scale))
    return np.column_stack((mapping.scale*(c*x-sine*y)+tx, mapping.scale*(sine*x+c*y)+ty))


def modes_for(pol, count):
    seen, result = set(), []
    for number, m, n in sorted((m*m+n*n, m, n) for m in range(1, 7) for n in range(0, m+1)
                               if pol == 'te' or 0 < n < m):
        if number not in seen:
            seen.add(number)
            result.append((number, m, n))
        if len(result) == count:
            break
    return result


def gram_rows(previous, current, mapping, pol, modes):
    """Independent analytic and product FEM normalized Gram matrices.

    Both eigenfunctions are pulled back to the previous frame through the
    declared mapping, so the analytic reference is the base-domain Gram scaled
    by the constant Jacobian. The current vector is rotated to the previous
    frame only inside the product FEM path.
    """
    overlay = polygon_similarity_remesh_overlay(previous.case.mesh, current.case.mesh, mapping)
    rotation = mapping.current_to_previous_rotation
    mesh_vertices = current.case.mesh.points_xy_m[current.case.mesh.triangles]
    analytic_gram = np.zeros((len(modes), len(modes)))
    for i, (_, m, n) in enumerate(modes):
        for j, (_, p, q) in enumerate(modes):
            total = 0.
            for bary, weight in triangle_quadrature(8):
                xy = np.einsum('j,tjk->tk', bary, mesh_vertices)
                back = scalar_points(xy, mapping, reverse=True)
                scalar_m, gradient_m = analytic(back, m, n, pol)
                scalar_p, gradient_p = analytic(back, p, q, pol)
                if pol == 'te':
                    total += np.sum(weight*current.space.determinants*(
                        gradient_m[:, 0]*gradient_p[:, 0]+gradient_m[:, 1]*gradient_p[:, 1]))
                else:
                    total += np.sum(weight*current.space.determinants*scalar_m*scalar_p)
            analytic_gram[i, j] = total
    norms = np.sqrt(np.diag(analytic_gram))
    normalized_analytic = analytic_gram/norms[:, None]/norms[None, :]
    grams = _electric_grams(previous, current, overlay, 5, current_to_previous_rotation=rotation)
    normalized_fem = np.asarray(grams[1])/np.sqrt(np.diag(grams[0]))[:, None]/np.sqrt(np.diag(grams[2]))[None, :]
    return normalized_analytic, normalized_fem, overlay


parser = argparse.ArgumentParser(description='Independent analytic composed similarity/remesh tracking validation')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--p1-levels', nargs='+', type=int, default=[16, 32])
parser.add_argument('--p2-levels', nargs='+', type=int, default=[8, 16])
args = parser.parse_args()
if any(levels != sorted(set(levels)) or min(levels) < 3 for levels in (args.p1_levels, args.p2_levels)):
    parser.error('mesh levels must be unique increasing integers >= 3')
ROOT = Path(__file__).resolve().parents[1]
OUT = args.out
OUT.mkdir(parents=True, exist_ok=False)
source = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
          for folder in ('src', 'tests', 'scripts', 'examples') for p in sorted((ROOT/folder).rglob('*'))
          if p.is_file() and '__pycache__' not in p.parts}
started = time.monotonic()
mappings = [PolygonSimilarityRemeshMapping(.7, .31, (.04, -.03)),
            PolygonSimilarityRemeshMapping(1.4, -.217, (-.02, .05), inverse=True)]
rows = []
for order, levels in ((1, args.p1_levels), (2, args.p2_levels)):
    for pol in ('te', 'tm'):
        modes = modes_for(pol, 3)
        for level in levels:
            base = structured(level, False)
            for mapping in mappings:
                current_mesh = PlanarMesh.create(
                    scalar_points(base.polygon_xy_m, mapping),
                    scalar_points(base.points_xy_m, mapping),
                    structured(level, True).triangles)
                previous = solve_planar(PlanarPolygonCase(base, pol, order, len(modes)))
                current = solve_planar(PlanarPolygonCase(current_mesh, pol, order, len(modes)))
                count = 2
                ids = [f'mode-{i}' for i in range(count)]
                result = track_planar_modes(previous, current, PlanarTrackingRequest(count, count, ids, mapping=mapping))
                normalized_analytic, normalized_fem, overlay = gram_rows(previous, current, mapping, pol, modes)
                effective = mapping.scale if not mapping.inverse else 1/mapping.scale
                frequency_errors = []
                for i, (number, m, n) in enumerate(modes):
                    exact = C0/(2*A)*np.sqrt(number)
                    frequency_errors.append(abs(previous.frequencies_hz[i]/exact-1))
                    frequency_errors.append(abs(current.frequencies_hz[i]/(exact/effective)-1))
                qa, qb = planar_quantities(previous), planar_quantities(current)
                row = dict(order=order, polarization=pol, level=level, inverse=bool(mapping.inverse),
                           triangles=len(current_mesh.triangles), status=result['status'],
                           result_version=result['result_version'],
                           maximum_analytic_overlap_residual=float(np.max(np.abs(normalized_analytic-np.eye(len(modes))))),
                           maximum_fem_overlap_error=float(np.max(np.abs(np.abs(normalized_fem)-np.eye(len(modes))))),
                           maximum_frequency_error=float(np.max(frequency_errors)),
                           geometry_factor_error=abs(qb['geometry_factor_ohm']/qa['geometry_factor_ohm']-1),
                           q0_error=abs(qb['q0']/qa['q0']-np.sqrt(effective)),
                           wall_loss_error=abs(qb['wall_loss_w_per_m']/qa['wall_loss_w_per_m']-1/effective**1.5),
                           overlay_triangles=len(overlay.reference_determinants))
                rows.append(row)
                print(json.dumps(row), flush=True)
                (OUT/'partial.json').write_text(json.dumps(rows, indent=2)+'\n')
forward = mappings[0]
wrong = PolygonSimilarityRemeshMapping(.8, .31, (.04, -.03))
rejections = []
for name, action in [
        ('denser boundary', lambda: polygon_similarity_remesh_overlay(
            structured(6, False), structured(8, True), PolygonSimilarityRemeshMapping(1., 0., (0., 0.)))),
        ('wrong declared scale', lambda: polygon_similarity_remesh_overlay(
            structured(6, False), PlanarMesh.create(
                scalar_points(structured(6, True).polygon_xy_m, forward),
                scalar_points(structured(6, True).points_xy_m, forward),
                structured(6, True).triangles), wrong))]:
    try:
        action()
        rejections.append(dict(name=name, rejected=False))
    except ValueError as exc:
        rejections.append(dict(name=name, rejected=True, reason=str(exc)))
assert source == {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source}
finest = [row for row in rows
          if (row['order'] == 1 and row['level'] == args.p1_levels[-1])
          or (row['order'] == 2 and row['level'] == args.p2_levels[-1])]
passed = (all(row['status'] == 'PASS' and row['result_version'] == 5 for row in rows)
          and all(row['maximum_fem_overlap_error'] < (5e-3 if row['order'] == 2 else 5e-2)
                  and row['maximum_analytic_overlap_residual'] < 1e-9
                  and row['maximum_frequency_error'] < (1e-3 if row['order'] == 2 else 1e-1)
                  and row['geometry_factor_error'] < (1e-2 if row['order'] == 2 else 5e-2)
                  and row['q0_error'] < (1e-2 if row['order'] == 2 else 5e-2)
                  and row['wall_loss_error'] < (1e-2 if row['order'] == 2 else 5e-2) for row in finest)
          and all(item['rejected'] for item in rejections))
(OUT/'report.json').write_text(json.dumps(dict(passed=passed, rows=rows, rejections=rejections,
                                               seconds=time.monotonic()-started, source_sha256=source,
                                               source_unchanged=True), indent=2)+'\n')
if not passed:
    raise SystemExit('independent composed tracking gates not all met; refine without relaxing the limits')

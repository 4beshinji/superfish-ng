#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""P06 independent circle geometry/area forms, without RF mode acceptance.

Synthetic four-ring domains. Matrix eigenvalues diagnose the Neumann static
kernel and Dirichlet positivity only; this is not P07 f/field/G convergence.
"""
import argparse
import json
import math
from pathlib import Path
import time
import numpy as np
from scipy.sparse.linalg import eigsh
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.planar_curved import PlanarCurvedDomain, PlanarCurvedCase
from superfish_ng.planar_curved_fem import planar_curved_matrices


def circle_domain(radius, count):
    points = [[0., 0.]]
    for ring in range(1, 5):
        angles = 2*np.pi*np.arange(count)/count
        points.extend(np.column_stack([np.cos(angles), np.sin(angles)])*radius*ring/4)
    cells = [[0, i+1, (i+1) % count+1] for i in range(count)]
    for ring in range(1, 4):
        for i in range(count):
            j = (i+1) % count
            a, b = 1+(ring-1)*count+i, 1+(ring-1)*count+j
            c, d = 1+ring*count+i, 1+ring*count+j
            cells.extend([[a, c, d], [a, d, b]])
    edges = sorted({tuple(sorted((cell[i], cell[j]))) for cell in cells for i, j in ((0, 1), (1, 2), (2, 0))})
    vertices = np.array(points)
    lookup = {edge: len(vertices)+i for i, edge in enumerate(edges)}
    points = np.vstack([vertices, [vertices[list(edge)].mean(axis=0) for edge in edges]])
    quadratic = [[*cell, *[lookup[tuple(sorted((cell[i], cell[j]))) ] for i, j in ((0, 1), (1, 2), (2, 0))]] for cell in cells]
    boundary = []
    for i in range(count):
        a, b = 1+3*count+i, 1+3*count+(i+1) % count
        mid = lookup[tuple(sorted((a, b)))]
        angle = 2*np.pi*(i+.5)/count
        points[mid] = radius*np.array([np.cos(angle), np.sin(angle)])
        boundary.append([a, b, mid])
    return PlanarCurvedDomain(points, quadratic, boundary)


def check_domain(radius, count):
    domain = circle_domain(radius, count)
    half_angle = np.pi/count
    expected_p2_area = count*radius**2*np.sin(half_angle)*(4-np.cos(half_angle))/3
    area_exact_error = abs(domain.area_m2/expected_p2_area-1)
    assert area_exact_error <= 1e-12
    length12 = domain.boundary_length_m(quadrature_order=12)
    length16 = domain.boundary_length_m(quadrature_order=16)
    length_order_error = abs(length12/length16-1)
    assert length_order_error <= 1e-12
    # Independent analytic radial-distance extremum for the actual quadratic
    # circular segment, attained when (2t-1)^2=1/2.
    ratio2 = 1-(1-np.cos(half_angle))**2/4
    parameter = (1+1/math.sqrt(2))/2
    edgepoint = domain.boundary_evaluate(0, [parameter])['points_xy_m'][0]
    assert abs(float(edgepoint@edgepoint)/radius**2-ratio2) <= 1e-12
    form_reports = []
    matrices = None
    for polarization in ('te', 'tm'):
        space, k, m, free = planar_curved_matrices(PlanarCurvedCase(domain, polarization, modes=1))
        one = np.ones(len(space.points_xy_m))
        mass_error = abs(float(one@m@one)/domain.area_m2-1)
        kernel = float(np.linalg.norm(k@one)/np.linalg.norm(k.data))
        assert mass_error <= 1e-12 and kernel <= 1e-12
        # These spectral invariants are separate from discretization error.
        eigenvalues, vectors = eigsh(k[free][:, free], M=m[free][:, free], k=2,
            sigma=-1/radius**2, which='LM', tol=1e-11, v0=np.linspace(.3, 1., len(free)))
        eigenvalues = eigenvalues[np.argsort(eigenvalues)]
        if polarization == 'te':
            assert abs(eigenvalues[0]*radius**2) <= 1e-10
            assert eigenvalues[1]*radius**2 > 1e-3
        else:
            assert eigenvalues[0]*radius**2 > 1e-3
            assert np.intersect1d(free, domain.boundary_nodes.ravel()).size == 0
        form_reports.append(dict(polarization=polarization, free_dofs=len(free), mass_area_relative_error=mass_error,
            constant_kernel_relative_norm=kernel, lowest_two_eigenvalues_scaled=(eigenvalues*radius**2).tolist()))
        if matrices is None:
            matrices = k, m
    return dict(radius_m=radius, angular_segments=count, cells=len(domain.cell_nodes), nodes=len(domain.points_xy_m),
        area_m2=domain.area_m2, perimeter_m=length12, exact_p2_area_relative_error=area_exact_error,
        perimeter_order_relative_difference=length_order_error,
        true_circle_area_relative_error=abs(domain.area_m2/(np.pi*radius**2)-1),
        true_circle_perimeter_relative_error=abs(length12/(2*np.pi*radius)-1),
        true_circle_boundary_distance_over_radius=1-math.sqrt(ratio2),
        geometry=dict(domain.geometry_diagnostics), forms=form_reports), matrices


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    before = _implementation_hashes()
    (args.out/'implementation-before.json').write_text(json.dumps(before, indent=2)+'\n')
    started = time.monotonic()
    records = []
    old = {}
    scale_reports = []
    try:
        for radius in (.01, .02):
            for count in (16, 32, 64):
                report, matrices = check_domain(radius, count)
                records.append(report)
                if radius == .01:
                    old[count] = matrices
                else:
                    k, m = matrices
                    original_k, original_m = old[count]
                    errors = dict(angular_segments=count,
                        stiffness_relative=float(np.linalg.norm((k-original_k).data)/np.linalg.norm(k.data)),
                        mass_relative=float(np.linalg.norm((m/4-original_m).data)/np.linalg.norm(m.data/4)))
                    assert errors['stiffness_relative'] <= 1e-12 and errors['mass_relative'] <= 1e-12
                    scale_reports.append(errors)
                print(f"radius={radius} N={count}: geometry and TE/TM forms PASS", flush=True)
        for radius in (.01, .02):
            subset = [record for record in records if record['radius_m'] == radius]
            for key in ('true_circle_area_relative_error', 'true_circle_perimeter_relative_error', 'true_circle_boundary_distance_over_radius'):
                assert all(a[key] > b[key] for a, b in zip(subset, subset[1:]))
                assert subset[-1][key] <= 1e-4
        after = _implementation_hashes()
        assert before == after
        result = dict(passed=True, scope='P06 geometry and area forms; P07 frequency/fields/RF unaccepted',
            elapsed_s=time.monotonic()-started, product_files_unchanged=len(after),
            spectral_invariant_eigensystems=12, records=records, scale_reports=scale_reports)
        (args.out/'implementation-after.json').write_text(json.dumps(after, indent=2)+'\n')
        (args.out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({key: value for key, value in result.items() if key not in ('records', 'scale_reports')}, indent=2))
    except Exception:
        (args.out/'failed-evidence.json').write_text(json.dumps(dict(records=records, elapsed_s=time.monotonic()-started), indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()

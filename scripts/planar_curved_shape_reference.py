# SPDX-License-Identifier: Apache-2.0
"""Synthetic ellipse and corner inputs with independent geometry invariants.

Reference-only: neither geometry checks nor the local corner harmonic provide
global eigenvalues. The production solver always receives explicit P2 maps.
"""
import math
import numpy as np
from scipy.integrate import quad
from superfish_ng.planar_curved import PlanarCurvedDomain
from validate_planar_curved_fem import circle_domain


def ellipse_domain(count, *, scale=1., angle=np.pi/7, center=(-.03, .01)):
    axes = np.array([.02, .012])*scale
    base = circle_domain(1., count)
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    points = (base.points_xy_m*axes)@rotation.T+np.array(center)
    return PlanarCurvedDomain(points, base.cell_nodes, base.boundary_nodes, 100000000)


def ellipse_geometry(domain, count, *, scale=1.):
    a, b = .02*scale, .012*scale
    true_area = np.pi*a*b
    # Independent 1D arclength of the true ellipse, without the P2 edge rule.
    true_perimeter, error = quad(lambda t: math.hypot(a*math.sin(t), b*math.cos(t)),
        0., 2*np.pi, epsabs=1e-13*scale, epsrel=1e-13)
    actual_perimeter = domain.boundary_length_m(quadrature_order=20)
    half_angle = np.pi/count
    exact_p2_area = count*a*b*np.sin(half_angle)*(4-np.cos(half_angle))/3
    # The affine image has Hausdorff distance no greater than ||A|| times
    # the circular quadratic radial defect; this is an upper bound, not a
    # falsely claimed exact nearest-distance formula for the ellipse.
    distance_bound = 1-math.sqrt(1-(1-math.cos(half_angle))**2/4)
    values = dict(true_area_m2=true_area, true_perimeter_m=true_perimeter,
        true_perimeter_integration_error_m=error,
        exact_P2_area_relative_error=abs(domain.area_m2/exact_p2_area-1),
        true_area_relative_error=abs(domain.area_m2/true_area-1),
        true_perimeter_relative_error=abs(actual_perimeter/true_perimeter-1),
        true_boundary_distance_upper_bound_over_major_axis=distance_bound)
    values['geometry_gates_passed'] = all(values[name] <= 1e-4 for name in
        ('true_area_relative_error', 'true_perimeter_relative_error', 'true_boundary_distance_upper_bound_over_major_axis'))
    if values['exact_P2_area_relative_error'] > 1e-12:
        raise ValueError('ellipse P2 area does not match the independent affine-circle formula')
    return values


def corner_domain(length, *, divisions=4, grading=3):
    """L-shaped Cartesian mesh graded toward its 3pi/2 corner at the origin."""
    if isinstance(divisions, bool) or not isinstance(divisions, int) or divisions < 1:
        raise ValueError('corner divisions must be a positive integer')
    if isinstance(grading, bool) or not isinstance(grading, int) or grading < 1:
        raise ValueError('corner grading must be a positive integer')
    coordinates = np.arange(-divisions, divisions+1)/divisions
    coordinates = np.sign(coordinates)*abs(coordinates)**grading*length
    lookup, vertices, cells = {}, [], []

    def node(i, j):
        if (i, j) not in lookup:
            lookup[i, j] = len(vertices)
            vertices.append([coordinates[i], coordinates[j]])
        return lookup[i, j]

    for i in range(2*divisions):
        for j in range(2*divisions):
            if i >= divisions and j >= divisions:
                continue
            a, b, c, d = node(i, j), node(i+1, j), node(i+1, j+1), node(i, j+1)
            cells.extend(((a, b, c), (a, c, d)))
    points = list(vertices)
    mids, incidence, quadratic = {}, {}, []
    for cell in cells:
        row = list(cell)
        for i, j in ((0, 1), (1, 2), (2, 0)):
            start, end = cell[i], cell[j]
            key = tuple(sorted((start, end)))
            if key not in mids:
                mids[key] = len(points)
                points.append((np.array(vertices[start])+vertices[end])/2)
            row.append(mids[key])
            incidence.setdefault(key, []).append((start, end, mids[key]))
        quadratic.append(row)
    exterior = {entries[0][0]: entries[0] for entries in incidence.values() if len(entries) == 1}
    start = lookup[0, 0]
    boundary, current = [], start
    for _ in exterior:
        edge = exterior[current]
        boundary.append(edge)
        current = edge[1]
    if current != start:
        raise ValueError('corner mesh boundary failed to close')
    return PlanarCurvedDomain(points, quadratic, boundary, 100000000)


def corner_harmonic_integrals(length, *, inner_radius=0.):
    """Known r^(2/3) harmonic on the 3pi/2 wedge, NOT an L-domain eigenfield.

    At theta=0 the normal derivative has magnitude (2/3) r^(-1/3).
    Both the volume gradient norm and sidewall squared derivative are finite;
    the point gradient diverges as the excluded inner radius tends to zero.
    """
    alpha, sector = 2/3, 3*np.pi/2
    if length <= 0 or not 0 <= inner_radius < length:
        raise ValueError('corner harmonic requires 0 <= inner_radius < length')
    # Independent adaptive improper quadrature vs explicit antiderivatives.
    wall, _ = quad(lambda r: alpha**2*r**(2*alpha-2), inner_radius, length,
        epsabs=1e-13, epsrel=1e-12)
    gradient, _ = quad(lambda r: sector*alpha**2*r**(2*alpha-1), inner_radius, length,
        epsabs=1e-13, epsrel=1e-12)
    exact_wall = alpha**2*(length**(2*alpha-1)-inner_radius**(2*alpha-1))/(2*alpha-1)
    exact_gradient = sector*alpha/2*(length**(2*alpha)-inner_radius**(2*alpha))
    return dict(wall_squared_derivative_integral=wall, gradient_squared_area_integral=gradient,
        wall_relative_error=abs(wall/exact_wall-1), gradient_relative_error=abs(gradient/exact_gradient-1),
        gradient_at_inner_radius=None if inner_radius == 0 else alpha*inner_radius**(alpha-1),
        scope='local wedge harmonic only; no finite corner peak or global L-domain eigenvalue')

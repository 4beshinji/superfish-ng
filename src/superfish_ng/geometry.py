# SPDX-License-Identifier: Apache-2.0
"""Independent circular geometry in (z,r), with explicit minor-arc direction."""
import numpy as np


def profile_area(case):
    """Exact meridian area for lines and specified circular minor arcs."""
    if case.contour is not None:
        return case.contour.area_m2
    area = sum((b[0]-a[0])*(a[1]+b[1])/2 for a, b in zip(case.profile, case.profile[1:]))
    for index, radius, direction in case.arcs:
        _, _, sweep = arc_geometry(case.profile[index-1], case.profile[index], radius, direction)
        area -= radius**2*(sweep-np.sin(sweep))/2
    return float(area)


def arc_geometry(start, end, radius, direction):
    a, b = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    if (a.shape != (2,) or b.shape != (2,) or not np.isfinite([a, b]).all()
            or not np.isfinite(radius) or radius <= 0 or direction not in ('cw', 'ccw')):
        raise ValueError('arc requires finite endpoints, positive radius and cw/ccw direction')
    delta = b-a
    chord = np.linalg.norm(delta)
    if chord <= 0 or chord > 2*radius:
        raise ValueError('arc endpoints must be distinct and no farther apart than its diameter')
    orientation = 1 if direction == 'ccw' else -1
    center = (a+b)/2+orientation*np.sqrt(max(0., radius**2-(chord/2)**2))*np.array([-delta[1], delta[0]])/chord
    angle = float(np.arctan2(*(a-center)[::-1]))
    sweep = float(orientation*2*np.arcsin(min(1., chord/(2*radius))))
    return center, angle, sweep


def linearize_profile(case):
    """Retain exact vertices and bound each arc chord's sagitta by the input tol.

    Only z-monotone minor arcs staying at positive r are admitted. The original
    radius/direction remain in Case; this function produces the meshing polygon.
    """
    if case.contour is not None:
        raise ValueError('general contour is not a single-valued radius profile')
    if case.geometry_type != 'arc_profile':
        return case.profile
    arcs = {index: (radius, direction) for index, radius, direction in case.arcs}
    result = [case.profile[0]]
    for i, (start, end) in enumerate(zip(case.profile, case.profile[1:]), 1):
        if i not in arcs:
            result.append(end)
            continue
        radius, direction = arcs[i]
        center, angle, sweep = arc_geometry(start, end, radius, direction)
        low, high = sorted((angle, angle+sweep))
        critical = np.arange(np.floor((low-np.pi/2)/np.pi), np.ceil((high-np.pi/2)/np.pi)+1)*np.pi+np.pi/2
        angles = np.concatenate(([angle, angle+sweep], critical[(critical >= low) & (critical <= high)]))
        if np.any(-np.sin(angles)*np.sign(sweep) < -64*np.finfo(float).eps):
            raise ValueError('arc must be monotone in z; reentrant z contours are unsupported')
        if np.min(center[1]+radius*np.sin(angles)) <= 0:
            raise ValueError('arc intersects or crosses the symmetry axis')
        maximum_angle = min(np.pi, 4*np.arcsin(np.sqrt(min(.5, case.arc_chord_tolerance_m/(2*radius)))))
        count = max(1, int(np.ceil(abs(sweep)/maximum_angle)))
        if count > 20000:
            raise ValueError('arc tolerance requests over 20000 segments per arc; use a larger tolerance')
        parameters = angle+sweep*np.arange(1, count)/count
        interior = center+radius*np.column_stack((np.cos(parameters), np.sin(parameters)))
        result.extend(tuple(point) for point in interior)
        result.append(end)
    if any(b[0] < a[0] for a, b in zip(result, result[1:])):
        raise ValueError('arc discretization reverses z at machine precision')
    return tuple(result)

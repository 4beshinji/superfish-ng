# SPDX-License-Identifier: Apache-2.0
"""Complete Cartesian P2 reference partitions and original native maps.

Geometry only: no eigenfield, projection, mode identity or error estimate is
generated. Both physical domains remain xy; no radial/axisymmetric adapter is
used. Binary64 coordinates denote exact rationals for restriction checks.
"""
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction as F
import numpy as np
from .config import integer, keys
from .planar_curved import PlanarCurvedDomain
from .planar_curved_geometry import _map_coefficients, strict_array, _closed_reference_mask
from .planar_curved_refinement import _evaluate
from .planar_tracking_overlap import _clip, _cross

UNIT = ((F(0), F(0)), (F(1), F(0)), (F(0), F(1)))
EDGES = ((0, 1), (1, 2), (2, 0))


class PlanarCurvedComparisonBudgetExceeded(ValueError):
    """The declared complete geometry comparison was not verified."""
    status = 'UNVERIFIED'


def _encode(value):
    return [value.numerator, value.denominator]


def _vertices(points):
    return [[_encode(x), _encode(y)] for x, y in points]


def _upper(value):
    rounded = float(value)
    return float(np.nextafter(rounded, np.inf)) if F(rounded) < value else rounded


@dataclass(frozen=True)
class PlanarCurvedComparisonDomain:
    previous: PlanarCurvedDomain
    current: PlanarCurvedDomain
    mapping: str = 'same_domain'
    restriction_policy: str = 'exact'
    max_geometry_boxes_per_domain: int = 100000

    def __post_init__(self):
        if self.mapping not in ('same_domain', 'declared_quadratic'):
            raise ValueError('curved planar mapping must be same_domain or declared_quadratic')
        if self.restriction_policy not in ('exact', 'binary64_roundoff'):
            raise ValueError('curved planar restriction_policy must be exact or binary64_roundoff')
        integer(self.max_geometry_boxes_per_domain, 'max_geometry_boxes_per_domain')
        if self.max_geometry_boxes_per_domain > 100000000:
            raise ValueError('max_geometry_boxes_per_domain must not exceed 100000000')
        for name in ('previous', 'current'):
            geometry = getattr(self, name)
            if type(geometry) is not PlanarCurvedDomain:
                raise ValueError('curved planar comparison requires full PlanarCurvedDomain objects')
            object.__setattr__(self, name, PlanarCurvedDomain.from_dict(geometry.to_dict(),
                max_geometry_boxes=self.max_geometry_boxes_per_domain))
        a, b = self.previous, self.current
        if (a.points_xy_m.shape != b.points_xy_m.shape or not np.array_equal(a.cell_nodes, b.cell_nodes)
                or not np.array_equal(a.boundary_nodes, b.boundary_nodes)):
            raise ValueError('declared quadratic reference domains require matching complete P2 topology and PEC boundary')
        if self.mapping == 'same_domain' and a != b:
            raise ValueError('same_domain requires identical full quadratic coordinates, including every midpoint')

    def to_dict(self):
        return dict(format='superfish_ng_planar_curved_comparison_domain', schema_version=1,
            mapping=self.mapping, restriction_policy=self.restriction_policy,
            max_geometry_boxes_per_domain=self.max_geometry_boxes_per_domain,
            previous=self.previous.to_dict(), current=self.current.to_dict())

    @classmethod
    def from_dict(cls, data):
        names = ['format', 'schema_version', 'mapping', 'restriction_policy',
                 'max_geometry_boxes_per_domain', 'previous', 'current']
        keys(data, names, names, 'curved planar comparison domain')
        if (data['format'] != 'superfish_ng_planar_curved_comparison_domain'
                or type(data['schema_version']) is not int or data['schema_version'] != 1):
            raise ValueError('expected curved planar comparison domain schema_version 1')
        budget = integer(data['max_geometry_boxes_per_domain'], 'max_geometry_boxes_per_domain')
        if budget > 100000000:
            raise ValueError('max_geometry_boxes_per_domain must not exceed 100000000')
        return cls(*(PlanarCurvedDomain.from_dict(data[name], max_geometry_boxes=budget)
            for name in ('previous', 'current')), data['mapping'], data['restriction_policy'], budget)

    def inverse(self):
        return type(self)(self.current, self.previous, self.mapping, self.restriction_policy,
                          self.max_geometry_boxes_per_domain)


class _PairBudget:
    def __init__(self, limit):
        self.limit, self.used = limit, 0

    def charge(self):
        if self.used == self.limit:
            raise PlanarCurvedComparisonBudgetExceeded('complete curved planar comparison exceeds max_pair_tests')
        self.used += 1


def _fraction(raw):
    if type(raw) is not list or len(raw) != 2 or any(type(v) is not int for v in raw) or raw[1] <= 0:
        raise ValueError('reference coordinates require [integer numerator, positive integer denominator]')
    return F(*raw)


def _partition(reference, native, declarations, domain, budget, max_triangles):
    if type(native) is not PlanarCurvedDomain:
        raise ValueError('curved planar native geometry must be PlanarCurvedDomain')
    native = PlanarCurvedDomain.from_dict(native.to_dict(),
        max_geometry_boxes=domain.max_geometry_boxes_per_domain)
    if len(native.cell_nodes) > max_triangles:
        raise PlanarCurvedComparisonBudgetExceeded('curved planar native partition exceeds max_triangles')
    if declarations is None:
        if len(native.cell_nodes) != len(reference.cell_nodes):
            raise ValueError('different native partitions require one explicit rational chart per native cell')
        declarations = [dict(base_cell=i, reference_vertices=_vertices(UNIT)) for i in range(len(native.cell_nodes))]
    if type(declarations) is not list or len(declarations) != len(native.cell_nodes):
        raise ValueError('one explicit rational chart per native cell is required')
    polynomials = [_map_coefficients(reference.points_xy_m[cell]) for cell in reference.cell_nodes]
    charts, groups, error_bounds, relative_bounds = [], defaultdict(list), [], []
    for cell, (nodes, declaration) in enumerate(zip(native.cell_nodes, declarations)):
        keys(declaration, ['base_cell', 'reference_vertices'], ['base_cell', 'reference_vertices'], 'curved planar native chart')
        owner = integer(declaration['base_cell'], 'base_cell', 0)
        if owner >= len(reference.cell_nodes):
            raise ValueError('base_cell lies outside the complete reference domain')
        raw = declaration['reference_vertices']
        if type(raw) is not list or len(raw) != 3 or any(type(p) is not list or len(p) != 2 for p in raw):
            raise ValueError('reference_vertices requires three rational xy coordinate pairs')
        vertices = tuple(tuple(_fraction(v) for v in point) for point in raw)
        if any(x < 0 or y < 0 or x+y > 1 for x, y in vertices) or _cross(*vertices) <= 0:
            raise ValueError('native chart must be a positive triangle inside its reference cell')
        samples = vertices+tuple(tuple((vertices[i][axis]+vertices[j][axis])/2 for axis in (0, 1)) for i, j in EDGES)
        expected = [_evaluate(polynomials[owner], point) for point in samples]
        actual = [tuple(F(float(v)) for v in point) for point in native.points_xy_m[nodes]]
        errors = [[a-b for a, b in zip(left, right)] for left, right in zip(actual, expected)]
        if domain.restriction_policy == 'exact' and any(v for row in errors for v in row):
            raise ValueError(f'native cell {cell} is not the exact quadratic restriction, including midpoints')
        controls = errors[:3]+[[2*errors[3+k][axis]-(errors[i][axis]+errors[j][axis])/2
                    for axis in (0, 1)] for k, (i, j) in enumerate(EDGES)]
        bounds = [max(abs(row[axis]) for row in controls) for axis in (0, 1)]
        extent = max(max(p[axis] for p in actual)-min(p[axis] for p in actual) for axis in (0, 1))
        if max(bounds) > 512*F(1, 2**52)*extent:
            raise ValueError('UNVERIFIED: native quadratic restriction roundoff exceeds local cell resolution')
        error_bounds.append([_upper(v) for v in bounds])
        relative_bounds.append(_upper(max(bounds)/extent))
        charts.append((owner, vertices))
        groups[owner].append((cell, vertices))
    for owner in range(len(reference.cell_nodes)):
        rows = groups[owner]
        if sum((_cross(*vertices) for _, vertices in rows), F(0)) != 1:
            raise ValueError('native charts do not completely cover every reference cell')
        for i, (_, a) in enumerate(rows):
            for _, b in rows[i+1:]:
                budget.charge()
                polygon = _clip(a, b)
                if any(_cross(polygon[0], polygon[k], polygon[k+1]) != 0 for k in range(1, len(polygon)-1)):
                    raise ValueError('native reference charts have overlapping positive areas')
    # Each actual PEC edge must restrict an exterior reference edge, with
    # oriented rational intervals covering that entire edge exactly once.
    exterior = {(int(cell), int(local)) for cell, local in zip(reference.boundary_cells, reference.boundary_local_edges)}
    intervals = defaultdict(list)
    for cell, local in zip(native.boundary_cells, native.boundary_local_edges):
        owner, vertices = charts[int(cell)]
        i, j = EDGES[int(local)]
        a, b = vertices[i], vertices[j]
        for edge, (u, v) in enumerate(EDGES):
            if (owner, edge) in exterior and _cross(UNIT[u], UNIT[v], a) == _cross(UNIT[u], UNIT[v], b) == 0:
                parameter = (lambda p: p[0]) if edge == 0 else (lambda p: p[1]) if edge == 1 else (lambda p: 1-p[1])
                left, right = parameter(a), parameter(b)
                if not 0 <= left < right <= 1:
                    raise ValueError('native PEC boundary has invalid reference orientation')
                intervals[owner, edge].append((left, right))
                break
        else:
            raise ValueError('native boundary does not preserve the full reference PEC wall')
    if set(intervals) != exterior:
        raise ValueError('native partition omits a reference PEC wall')
    for parts in intervals.values():
        end = F(0)
        for left, right in sorted(parts):
            if left != end:
                raise ValueError('reference PEC wall intervals have a gap or overlap')
            end = right
        if end != 1:
            raise ValueError('reference PEC wall intervals are incomplete')
    return native, tuple(charts), groups, error_bounds, relative_bounds


def _local_vertices(vertices, parent):
    a, b, c = parent
    determinant = _cross(a, b, c)
    return tuple((_cross(a, p, c)/determinant, _cross(a, b, p)/determinant) for p in vertices)


def _mapped_reference(points, vertices):
    triangle = np.array(vertices, dtype=float)
    result = triangle[0]+points@(triangle[1:]-triangle[0])
    # A closed rational chart and a verified closed input imply membership.
    # Only unresolved floating boundary arithmetic takes the exact fallback;
    # exterior inputs never enter this function.
    for index in np.flatnonzero(~_closed_reference_mask(result)):
        x, y = map(lambda v: F(float(v)), points[index])
        weights = (1-x-y, x, y)
        exact = tuple(sum((weight*vertex[axis] for weight, vertex in zip(weights, vertices)), F(0)) for axis in (0, 1))
        if min(exact) < 0 or sum(exact) > 1:
            raise ValueError('common reference point escaped its original native cell')
        row = [float(v) for v in exact]
        if sum(exact) == 1:
            row[0] = 1-(1-row[0])
            row[1] = 1-row[0]
        if not _closed_reference_mask(np.array([row]))[0]:
            raise ValueError('UNVERIFIED: native reference point is unresolved in floating arithmetic')
        result[index] = row
    return result


@dataclass(frozen=True)
class PlanarCurvedComparison:
    domain: PlanarCurvedComparisonDomain
    native_domains: tuple
    triangles: tuple
    report: dict

    def evaluate(self, side, reference_points):
        """Actual native xy/area and original reference xy/area, kept distinct."""
        if type(side) is not int or side not in (0, 1):
            raise ValueError('comparison side must be 0 or 1')
        q = strict_array(reference_points, 2, 'curved comparison reference points')
        if not np.all(_closed_reference_mask(q)):
            raise ValueError('curved comparison points must lie in the closed reference triangle')
        reference = (self.domain.previous, self.domain.current)[side]
        native = self.native_domains[side]
        result = []
        for owner, vertices, previous, current, parents in self.triangles:
            cell = (previous, current)[side]
            native_vertices = _local_vertices(vertices, parents[side])
            local = _mapped_reference(q, native_vertices)
            base = _mapped_reference(q, vertices)
            actual = native.elements[cell].evaluate(local)
            original = reference.elements[owner].evaluate(base)
            measures = [actual['determinant_m2']*float(_cross(*native_vertices)),
                        original['determinant_m2']*float(_cross(*vertices))]
            if any(not np.isfinite(m).all() or np.any(m <= 0) for m in measures):
                raise ValueError('UNVERIFIED: curved comparison area is unresolved in floating SI arithmetic')
            result.append(dict(native_cell=cell, native_reference_points=local,
                points_xy_m=actual['points_xy_m'], determinant_m2=measures[0],
                reference_points_xy_m=original['points_xy_m'], reference_determinant_m2=measures[1]))
        return result


def build_planar_curved_comparison(previous, current, domain, *, previous_cells=None,
                                   current_cells=None, max_pair_tests=2000000, max_triangles=250000):
    """Verify full restrictions, PEC intervals and both exact chart coverages.

    The pair budget is global across both self-overlap checks and their common
    intersections. Geometry box budgets apply separately to each full domain.
    Failure returns no partial geometry acceptance or straight fallback.
    """
    integer(max_pair_tests, 'max_pair_tests')
    integer(max_triangles, 'max_triangles')
    if type(domain) is not PlanarCurvedComparisonDomain:
        raise ValueError('an explicit PlanarCurvedComparisonDomain is required')
    domain = PlanarCurvedComparisonDomain.from_dict(domain.to_dict())
    budget = _PairBudget(max_pair_tests)
    prepared = [_partition(reference, native, charts, domain, budget, max_triangles)
                for reference, native, charts in zip((domain.previous, domain.current),
                    (previous, current), (previous_cells, current_cells))]
    covered = [defaultdict(F), defaultdict(F)]
    totals, triangles = defaultdict(F), []
    for owner in range(len(domain.previous.cell_nodes)):
        for old, a in prepared[0][2][owner]:
            for new, b in prepared[1][2][owner]:
                budget.charge()
                polygon = _clip(a, b)
                if len(polygon) < 3:
                    continue
                polygon = [p for i, p in enumerate(polygon) if _cross(polygon[i-1], p, polygon[(i+1) % len(polygon)]) != 0]
                if len(polygon) < 3:
                    continue
                start = min(range(len(polygon)), key=polygon.__getitem__)
                polygon = polygon[start:]+polygon[:start]
                for i in range(1, len(polygon)-1):
                    vertices = (polygon[0], polygon[i], polygon[i+1])
                    determinant = _cross(*vertices)
                    if determinant <= 0:
                        raise ValueError('common curved chart has nonpositive orientation')
                    if len(triangles) == max_triangles:
                        raise PlanarCurvedComparisonBudgetExceeded('complete curved planar intersections exceed max_triangles')
                    triangles.append((owner, vertices, old, new, (a, b)))
                    covered[0][old] += determinant
                    covered[1][new] += determinant
                    totals[owner] += determinant
    for side, (_, charts, _, _, _) in enumerate(prepared):
        if any(covered[side][cell] != _cross(*vertices) for cell, (_, vertices) in enumerate(charts)):
            raise ValueError('common curved charts do not exactly cover every original native cell')
    if any(totals[owner] != 1 for owner in range(len(domain.previous.cell_nodes))):
        raise ValueError('common curved charts do not exactly cover every reference cell')
    triangles.sort(key=lambda row: (row[0], row[1]))
    report = dict(status='GEOMETRY_VERIFIED', mapping=domain.mapping, triangle_count=len(triangles),
        pair_tests=budget.used, max_pair_tests=max_pair_tests, max_triangles=max_triangles,
        max_geometry_boxes_per_domain=domain.max_geometry_boxes_per_domain,
        base_reference_areas=[_encode(totals[i]/2) for i in range(len(domain.previous.cell_nodes))],
        native_cell_reference_coverage=[[_encode(covered[side][i]/2) for i in range(len(p[1]))] for side, p in enumerate(prepared)],
        reference_area_m2=[geometry.area_m2 for geometry in (domain.previous, domain.current)],
        native_area_m2=[p[0].area_m2 for p in prepared],
        restriction_policy=domain.restriction_policy,
        exact_native_restrictions=not any(value for p in prepared for row in p[3] for value in row),
        native_coordinate_error_bounds_m=[p[3] for p in prepared],
        maximum_original_map_relative_bounds=[max(p[4]) for p in prepared],
        maximum_roundoff_cell_extent_epsilon_factor=512,
        triangles=[dict(base_cell=o, reference_vertices=_vertices(v), previous_cell=a, current_cell=b)
                   for o, v, a, b, _ in triangles],
        scope='complete xy quadratic reference/native geometry, original native area and rational coverage; no field identity, quadrature accuracy or continuum error bound')
    return PlanarCurvedComparison(domain, tuple(p[0] for p in prepared), tuple(triangles), report)

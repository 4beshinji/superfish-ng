# SPDX-License-Identifier: Apache-2.0
"""Explicit common reference charts for independently connected native P2 maps."""
from dataclasses import dataclass
from fractions import Fraction as F
from math import isfinite
import numpy as np
from .config import integer
from .curved_selection_transfer import UNIT, _prepare, _lineage
from .curved_comparison_correspondence import _boundary_partitions
from .curved_space import case_curved_space
from .mesh_input import mesh_from_dict
from .planar_tracking_overlap import _cross
from .reference_partition import intersect_reference_triangulations, _encode


def _chart(points, base, max_pair_tests):
    corners = base.geometry.cell_nodes[:, :3]
    count = int(corners.max())+1
    if type(points) is not list or len(points) != count:
        raise ValueError('reference_vertices must give one coordinate pair per initial mesh vertex')
    values = []
    for p in points:
        if not isinstance(p, (list, tuple)) or len(p) != 2 or any(
                type(x) not in (int, float, F) or (type(x) is float and not isfinite(x)) for x in p):
            raise ValueError('reference vertices require finite dimensionless coordinate pairs')
        values.append(tuple(F(x) for x in p))
    if len(set(values)) != count:
        raise ValueError('distinct native vertices must have distinct reference coordinates')
    edges = sorted({tuple(sorted((int(row[i]), int(row[(i+1) % 3])))) for row in corners for i in range(3)})
    tests = len(edges)*(len(edges)-1)//2
    if tests > max_pair_tests:
        raise ValueError('reference chart edge checks exceed max_pair_tests')
    def on(a, b, p):
        return _cross(a, b, p) == 0 and all(min(a[k], b[k]) <= p[k] <= max(a[k], b[k]) for k in (0, 1))
    for i, edge in enumerate(edges):
        a, b = [values[k] for k in edge]
        for other in edges[i+1:]:
            c, d = [values[k] for k in other]
            shared = set(edge) & set(other)
            if shared:
                if any(on(a, b, values[k]) for k in set(other)-shared) or any(on(c, d, values[k]) for k in set(edge)-shared):
                    raise ValueError('reference chart edges overlap beyond shared vertices')
            elif ((min(a[0], b[0]) <= max(c[0], d[0]) and min(c[0], d[0]) <= max(a[0], b[0]))
                  and (min(a[1], b[1]) <= max(c[1], d[1]) and min(c[1], d[1]) <= max(a[1], b[1]))
                  and _cross(a, b, c)*_cross(a, b, d) <= 0 and _cross(c, d, a)*_cross(c, d, b) <= 0):
                raise ValueError('nonincident reference chart edges intersect or touch')
    return values, tests


def _boundary(case, base, chart):
    from .te import is_te
    allowed={'axis','pec'}
    if is_te(case):
        from .curved_same_domain_tracking import _te_end_conditions
        _te_end_conditions([case,case])
        allowed.update(('electric_symmetry','magnetic_symmetry'))
    result = []
    for entries in _boundary_partitions(case, base, 512*np.finfo(float).eps):
        tags = {x[5] for x in entries}
        if len(tags) != 1 or not tags <= allowed:
            raise ValueError('reference charts require closed PEC and axis boundaries')
        vertices = [chart[entries[0][2]]]
        for entry in entries:
            if vertices[-1] != chart[entry[2]]:
                raise ValueError('reference boundary curve is discontinuous')
            vertices.append(chart[entry[3]])
        reduced = []
        for p in vertices:
            while len(reduced) >= 2 and _cross(reduced[-2], reduced[-1], p) == 0:
                a, b = reduced[-2:]
                if sum((b[k]-a[k])*(p[k]-b[k]) for k in (0, 1)) <= 0:
                    raise ValueError('reference curve backtracks')
                reduced.pop()
            reduced.append(p)
        result.append(dict(tag=next(iter(tags)), vertices=[[_encode(x) for x in p] for p in reduced]))
    return result


@dataclass(frozen=True)
class CurvedReferencePartition:
    maps: tuple
    report: dict

    def evaluate(self, side, q):
        if type(side) is not int or side not in (0, 1):
            raise ValueError('reference partition side must be 0 or 1')
        q = np.asarray(q, dtype=float)
        if q.ndim != 2 or q.shape[1] != 2 or not np.isfinite(q).all() or np.any(q < 0) or np.any(q.sum(axis=1) > 1):
            raise ValueError('quadrature coordinates must lie inside the unit reference triangle')
        bary = np.column_stack((1-q.sum(axis=1), q))
        prefix = 'previous' if side == 0 else 'current'
        data = []
        for row in self.report['triangles']:
            points = [[F(*v) for v in p] for p in row[prefix+'_barycentric']]
            parent_q = tuple(tuple(p[1:]) for p in points)
            det = float(_cross(*parent_q))
            if not np.isfinite(det) or det <= 0:
                raise ValueError('reference parent transform is unresolved in floating arithmetic')
            evaluation = self.maps[side][row[prefix+'_cell']].evaluate(bary @ np.array(parent_q, dtype=float))
            data.append(dict(points_rz_m=evaluation['points_rz_m'], determinant_m2=evaluation['determinant_m2']*det))
        return data


def build_curved_reference_partition(previous, current, *, reference_vertices, max_pair_tests, max_triangles):
    """Bind declared vertex charts to actual P2 maps and fixed native histories.

    Each ordered physical curve has the same oriented reference polyline and
    tag on both sides. Additional collinear boundary vertices are permitted.
    Physical curve fractions need not agree: the vertex charts declare their
    correspondence. No physical curve is reprojected during subdivision.
    """
    integer(max_pair_tests, 'max_pair_tests'); integer(max_triangles, 'max_triangles')
    if type(reference_vertices) is not list or len(reference_vertices) != 2:
        raise ValueError('reference_vertices must contain previous and current charts')
    prepared = [_prepare(p, allow_te=True) for p in (previous, current)]
    reference = []; boundaries = []; maps = []; counts = []; edge_tests = 0
    for (project, base, limit), points in zip(prepared, reference_vertices):
        if project.mesh_data is None:
            raise ValueError('explicit reference charts require an explicit initial source mesh')
        chart, tested = _chart(points, base, max_pair_tests-edge_tests)
        edge_tests += tested
        boundaries.append(_boundary(project.case, base, chart))
        lineage = _lineage(project, base, min(limit, max_triangles), [(i, UNIT) for i in range(len(base.geometry.cell_nodes))])
        triangles = []
        for owner, vertices in lineage:
            a, b, c = [chart[int(node)] for node in base.geometry.cell_nodes[owner, :3]]
            triangles.append(tuple(tuple(a[k]+x*(b[k]-a[k])+y*(c[k]-a[k]) for k in (0, 1)) for x, y in vertices))
        reference.append(triangles)
        space = case_curved_space(project.case, mesh_from_dict(project.case, project.mesh_data))
        if len(space.geometry.cell_nodes) != len(lineage):
            raise ValueError('reference lineage does not match final native P2 cells')
        maps.append(tuple(space.geometry.local_maps)); counts.append(len(lineage))
    if boundaries[0] != boundaries[1]:
        raise ValueError('ordered reference curve polylines and boundary tags must agree')
    remaining = max_pair_tests-edge_tests
    if remaining <= 0:
        raise ValueError('reference chart edge checks exhausted max_pair_tests')
    report = intersect_reference_triangulations(*reference, max_pair_tests=remaining, max_triangles=max_triangles)
    report.update(final_cell_counts=counts, reference_boundary=boundaries[0], chart_edge_pair_tests=edge_tests,
                  total_pair_tests=edge_tests+report['pair_tests'], boundary_pairing='declared_reference_polylines',
                  scope='explicit common vertex charts and independently reconstructed native P2 maps; complete reference coverage; no inferred physical correspondence or quadrature error bound')
    return CurvedReferencePartition(tuple(maps), report)

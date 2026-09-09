# SPDX-License-Identifier: Apache-2.0
"""Explicit xy triangulations of a declared simple PEC polygon.

This geometry contract is independent of axisymmetric Case/mesh readers.
It does not yet enable polygon RF cases in the product solver.
"""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from .config import keys


def _xy(value, name):
    try:
        raw = np.asarray(value, dtype=object)
        if raw.ndim != 2 or raw.shape[1] != 2 or len(raw) < 3:
            raise ValueError(f'{name} must contain at least three xy pairs')
        if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)) for v in raw.flat):
            raise ValueError(f'{name} requires numeric xy coordinates, not strings or booleans')
        result = raw.astype(float)
    except (TypeError, OverflowError) as exc:
        raise ValueError(f'{name} requires finite xy coordinates') from exc
    if not np.isfinite(result).all():
        raise ValueError(f'{name} requires finite xy coordinates')
    if len(np.unique(result, axis=0)) != len(result):
        raise ValueError(f'{name} contains duplicate coordinates; do not repeat the closing vertex')
    return result


def _orient(a, b, c):
    """Sign on the actual binary64 coordinates, with exact fallback near zero."""
    u = b-a; v = c-a
    left, right = u[0]*v[1], u[1]*v[0]
    det = left-right
    if abs(det) > 16*np.finfo(float).eps*(abs(left)+abs(right)):
        return 1 if det > 0 else -1
    ax, ay, bx, by, cx, cy = map(lambda x: Fraction(float(x)), (*a, *b, *c))
    exact = (bx-ax)*(cy-ay)-(by-ay)*(cx-ax)
    return (exact > 0)-(exact < 0)


def _on_segment(a, b, p):
    return _orient(a, b, p) == 0 and np.all(p >= np.minimum(a,b)) and np.all(p <= np.maximum(a,b))


def _check_edges(points, edges, name):
    """AABB sweep; all remaining candidates receive a segment predicate."""
    endpoints = points[edges]
    low, high = endpoints.min(axis=1), endpoints.max(axis=1)
    active = []
    for index in np.argsort(low[:,0], kind='stable'):
        active = [j for j in active if high[j,0] >= low[index,0]]
        a, b = endpoints[index]
        for j in active:
            if high[j,1] < low[index,1] or high[index,1] < low[j,1]:
                continue
            c, d = endpoints[j]
            common = set(edges[index]) & set(edges[j])
            if common:
                shared = common.pop()
                other_a = next(v for v in edges[index] if v != shared)
                other_b = next(v for v in edges[j] if v != shared)
                p, q, r = points[[shared,other_a,other_b]]
                if _orient(p,q,r) == 0 and (_on_segment(p,q,r) or _on_segment(p,r,q)):
                    raise ValueError(f'{name} edges overlap at vertex {shared}')
                continue
            s, t, u, v = _orient(a,b,c), _orient(a,b,d), _orient(c,d,a), _orient(c,d,b)
            if (s*t < 0 and u*v < 0) or any((sign == 0 and _on_segment(x,y,p)) for sign,x,y,p in ((s,a,b,c),(t,a,b,d),(u,c,d,a),(v,c,d,b))):
                raise ValueError(f'{name} edges intersect or form an unshared T junction: {j}, {index}')
        active.append(index)


@dataclass(frozen=True)
class PlanarMesh:
    polygon_xy_m: np.ndarray
    points_xy_m: np.ndarray
    triangles: np.ndarray
    boundary_edges: np.ndarray
    boundary_cells: np.ndarray
    boundary_local_vertices: np.ndarray
    area_m2: float

    @classmethod
    def create(cls, polygon_xy_m, points_xy_m, triangles):
        polygon = _xy(polygon_xy_m, 'planar polygon')
        points = _xy(points_xy_m, 'planar mesh points')
        raw = np.asarray(triangles, dtype=object)
        if raw.ndim != 2 or raw.shape[1] != 3 or not len(raw) or any(isinstance(v,(bool,np.bool_)) or not isinstance(v,(int,np.integer)) for v in raw.flat):
            raise ValueError('planar triangles must be nonempty integer triples')
        if any(v < 0 or v >= len(points) for v in raw.flat):
            raise ValueError('planar triangle index out of range')
        cells = raw.astype(np.int64)
        if any(len(set(row)) != 3 for row in cells):
            raise ValueError('planar triangle repeats a vertex')
        if len(np.unique(np.sort(cells,axis=1),axis=0)) != len(cells):
            raise ValueError('duplicate planar triangle')
        if len(np.unique(cells)) != len(points):
            raise ValueError('planar mesh contains unused points')
        # Translate before area arithmetic; reject overflow rather than normalize
        # silently into a different SI geometry.
        origin = polygon[0]
        p = polygon-origin; q = points-origin
        if not np.isfinite(p).all() or not np.isfinite(q).all():
            raise ValueError('planar coordinate differences exceed finite SI arithmetic')
        span = float(np.max(np.ptp(np.vstack((p,q)),axis=0)))
        if not np.isfinite(span) or span <= 0 or not np.isfinite(span*span) or span*span == 0:
            raise ValueError('planar geometry scale is outside finite area arithmetic')
        pn, qn = p/span, q/span
        polygon_edges = np.column_stack((np.arange(len(p)),np.roll(np.arange(len(p)),-1)))
        _check_edges(polygon, polygon_edges, 'declared polygon')
        polygon_area = float(np.sum(pn[:,0]*np.roll(pn[:,1],-1)-pn[:,1]*np.roll(pn[:,0],-1))/2)
        if polygon_area <= 0:
            raise ValueError('planar polygon must have positive area and counterclockwise orientation')
        vertices = qn[cells]
        delta1, delta2 = vertices[:,1]-vertices[:,0], vertices[:,2]-vertices[:,0]
        det = delta1[:,0]*delta2[:,1]-delta1[:,1]*delta2[:,0]
        if not np.isfinite(det).all() or np.any(det <= 0):
            raise ValueError('planar triangles require finite positive Jacobians')
        if any(_orient(*points[row]) <= 0 for row in cells):
            raise ValueError('planar triangle orientation is not positive on the input coordinates')
        cancellation = abs(delta1[:,0]*delta2[:,1])+abs(delta1[:,1]*delta2[:,0])
        if np.any(det <= 64*np.finfo(float).eps*cancellation):
            raise ValueError('planar triangle Jacobian is numerically unresolved; improve mesh shape or coordinate representation')
        incidence = {}
        links = [dict() for _ in points]
        for ci, row in enumerate(cells):
            for i,j in ((0,1),(1,2),(2,0)):
                a,b = int(row[i]),int(row[j])
                incidence.setdefault(tuple(sorted((a,b))),[]).append((ci,i,j,a,b))
            for i in range(3):
                a,b,c = map(int,(row[i],row[(i+1)%3],row[(i+2)%3]))
                links[a].setdefault(b,set()).add(c);links[a].setdefault(c,set()).add(b)
        adjacency = [set() for _ in cells]; boundary = []
        for entries in incidence.values():
            if len(entries) == 1:
                boundary.append(entries[0])
            elif len(entries) == 2:
                a,b = entries
                if a[3:] != b[3:][::-1]:
                    raise ValueError('planar shared edge has inconsistent orientation')
                adjacency[a[0]].add(b[0]);adjacency[b[0]].add(a[0])
            else:
                raise ValueError('planar edge has more than two incident triangles')
        def connected(graph):
            reached = set(); todo = [next(iter(graph))]
            while todo:
                node = todo.pop()
                if node not in reached:
                    reached.add(node); todo.extend(graph[node]-reached)
            return len(reached) == len(graph)
        if not connected(dict(enumerate(adjacency))):
            raise ValueError('planar triangles must form one edge-connected region')
        if len(points)-len(incidence)+len(cells) != 1 or not boundary:
            raise ValueError('planar mesh must be a disk without holes')
        successors = {}; predecessors = {}
        for ci,i,j,a,b in boundary:
            if a in successors or b in predecessors:
                raise ValueError('planar boundary is not a single manifold cycle')
            successors[a] = b; predecessors[b] = a
        if successors.keys() != predecessors.keys():
            raise ValueError('planar boundary is not closed')
        for vertex, link in enumerate(links):
            degrees = [len(neighbors) for neighbors in link.values()]
            expected = 2 if vertex in successors else 0
            if not connected(link) or degrees.count(1) != expected or any(d not in (1,2) for d in degrees):
                raise ValueError('planar vertex link is not a disk neighborhood')
        start = next(iter(successors)); cycle = [start]; current = successors[start]
        while current != start and len(cycle) <= len(successors):
            cycle.append(current); current = successors[current]
        if len(cycle) != len(successors):
            raise ValueError('planar mesh has multiple boundary cycles')
        _check_edges(points, np.asarray(list(incidence)), 'planar mesh')
        lookup = {tuple(point): i for i,point in enumerate(points)}
        try:
            corners = [lookup[tuple(point)] for point in polygon]
        except KeyError as exc:
            raise ValueError('each declared polygon corner must be an explicit mesh point') from exc
        if any(corner not in successors for corner in corners):
            raise ValueError('declared polygon corners must lie on the mesh boundary')
        # Every boundary edge belongs to exactly one monotone polygon segment.
        # 64 eps permits only roundoff from affine construction, not a user
        # geometry tolerance. Intersections above still use exact predicates.
        covered = set(); eps = 64*np.finfo(float).eps
        for i,a in enumerate(corners):
            b = corners[(i+1)%len(corners)]; direction = qn[b]-qn[a]
            norm2 = float(direction@direction); last = 0.; current = a
            while current != b:
                if current in covered:
                    raise ValueError('mesh boundary does not follow the declared polygon order')
                covered.add(current); current = successors[current]
                offset = qn[current]-qn[a]
                parameter = float(offset@direction/norm2)
                distance = abs(direction[0]*offset[1]-direction[1]*offset[0])/np.sqrt(norm2)
                if distance > eps or parameter <= last or parameter > 1+eps:
                    raise ValueError('mesh boundary does not cover the declared polygon segments')
                last = parameter
        if covered != successors.keys():
            raise ValueError('mesh boundary has undeclared segments')
        mesh_area = float(np.sum(det)/2)
        if abs(mesh_area-polygon_area) > eps*max(mesh_area,polygon_area):
            raise ValueError('planar triangle area does not cover the declared polygon')
        area = mesh_area*span**2
        if not np.isfinite(area) or area <= 0:
            raise ValueError('planar area is outside finite SI arithmetic')
        boundary.sort(key=lambda entry:(entry[3],entry[4]))
        arrays = [polygon.copy(),points.copy(),cells.copy(),np.asarray([e[3:] for e in boundary]),np.asarray([e[0] for e in boundary]),np.asarray([e[1:3] for e in boundary])]
        for array in arrays: array.setflags(write=False)
        return cls(*arrays,area)

    @classmethod
    def from_dict(cls, data):
        required = ['format','schema_version','coordinates','boundary','polygon_xy_m','points_xy_m','triangles']
        keys(data,required,required,'planar explicit mesh')
        if data['format'] != 'superfish_ng_planar_mesh' or type(data['schema_version']) is not int or data['schema_version'] != 1:
            raise ValueError('expected superfish_ng_planar_mesh schema_version 1')
        if data['coordinates'] != 'cartesian' or data['boundary'] != 'pec':
            raise ValueError('planar explicit mesh requires Cartesian xy and a single PEC boundary')
        return cls.create(data['polygon_xy_m'],data['points_xy_m'],data['triangles'])

    def to_dict(self):
        return dict(format='superfish_ng_planar_mesh',schema_version=1,coordinates='cartesian',boundary='pec',polygon_xy_m=self.polygon_xy_m.tolist(),points_xy_m=self.points_xy_m.tolist(),triangles=self.triangles.tolist())

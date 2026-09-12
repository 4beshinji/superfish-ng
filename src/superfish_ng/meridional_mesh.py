# SPDX-License-Identifier: Apache-2.0
"""Connected straight (r,z) triangulations outside the axis, with PEC holes.

Outer contour is counterclockwise; holes are clockwise. Coordinates and
boundary coverage are checked on the actual binary64 input, not a CAD tolerance.
The Cartesian disk-only PlanarMesh contract is unchanged.
"""
from dataclasses import dataclass, field
from fractions import Fraction
import numpy as np
from .config import keys
from .coaxial import _numeric_coordinates
from .planar_mesh import _orient, _on_segment, _check_edges


def _rz(value, name):
    result = _numeric_coordinates(value, 2, name).copy()
    if len(result) < 3 or len(np.unique(result, axis=0)) != len(result):
        raise ValueError(f'{name} requires at least three distinct points; omit the repeated closing vertex')
    if np.any(result[:,0] <= 0):
        raise ValueError(f'{name} requires r > 0; axis-connected vacuum needs its separate regularity contract')
    return result


def _signed_area(polygon):
    origin = [Fraction(float(v)) for v in polygon[0]]
    p = [[Fraction(float(v))-o for v,o in zip(row,origin)] for row in polygon]
    return sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(p,p[1:]+p[:1]))/2


def _inside(point, polygon):
    winding = 0
    for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
        if _on_segment(a,b,point): return False
        side = _orient(a,b,point)
        if a[1] <= point[1] < b[1] and side > 0: winding += 1
        if b[1] <= point[1] < a[1] and side < 0: winding -= 1
    return winding != 0


def _connected(graph):
    if not graph: return False
    reached = set(); todo = [next(iter(graph))]
    while todo:
        node = todo.pop()
        if node not in reached:
            reached.add(node); todo.extend(graph[node]-reached)
    return len(reached) == len(graph)


@dataclass(frozen=True, eq=False)
class MeridionalMesh:
    outer_rz_m: np.ndarray
    holes_rz_m: tuple
    points_rz_m: np.ndarray
    triangles: np.ndarray
    boundary_edges: np.ndarray = field(init=False)
    boundary_cells: np.ndarray = field(init=False)
    boundary_local_vertices: np.ndarray = field(init=False)
    boundary_components: np.ndarray = field(init=False)
    boundary_segments: np.ndarray = field(init=False)
    area_m2: float = field(init=False)
    volume_m3: float = field(init=False)
    surface_area_m2_by_segment: np.ndarray = field(init=False)
    euler_characteristic: int = field(init=False)

    def __post_init__(self):
        outer = _rz(self.outer_rz_m,'meridional outer contour')
        if not isinstance(self.holes_rz_m,(list,tuple)):
            raise ValueError('holes_rz_m must be an explicit list of clockwise PEC contours')
        holes = tuple(_rz(h,'meridional hole') for h in self.holes_rz_m)
        points = _rz(self.points_rz_m,'meridional mesh points')
        raw = np.asarray(self.triangles,dtype=object)
        if (raw.ndim != 2 or raw.shape[1] != 3 or not 1 <= len(raw) <= 250000
            or any(isinstance(v,(bool,np.bool_)) or not isinstance(v,(int,np.integer)) for v in raw.flat)):
            raise ValueError('meridional triangles require 1 to 250000 integer triples')
        if any(v < 0 or v >= len(points) for v in raw.flat):
            raise ValueError('meridional triangle index out of range')
        cells = raw.astype(np.int64)
        if (any(len(set(row)) != 3 for row in cells)
            or len(np.unique(np.sort(cells,axis=1),axis=0)) != len(cells)):
            raise ValueError('meridional triangles contain a repeated vertex or duplicate cell')
        if len(np.unique(cells)) != len(points):
            raise ValueError('meridional mesh contains unused points')
        contours = (outer,*holes); polygon_points = np.vstack(contours)
        if len(np.unique(polygon_points,axis=0)) != len(polygon_points):
            raise ValueError('meridional contours touch or duplicate a vertex')
        polygon_edges = []; offset = 0
        for contour in contours:
            polygon_edges.extend((offset+i,offset+(i+1)%len(contour)) for i in range(len(contour)))
            offset += len(contour)
        _check_edges(polygon_points,np.array(polygon_edges),'meridional contours')
        areas = [_signed_area(p) for p in contours]
        if areas[0] <= 0 or any(a >= 0 for a in areas[1:]):
            raise ValueError('outer contour must be counterclockwise and holes clockwise, with nonzero area')
        for i,hole in enumerate(holes):
            if not _inside(hole[0],outer):
                raise ValueError('meridional hole must be strictly inside the outer contour')
            if any(_inside(hole[0],other) for j,other in enumerate(holes) if j != i):
                raise ValueError('nested meridional holes/conductors are unsupported')
        span = float(np.max(np.ptp(points,axis=0)))
        if not np.isfinite(span) or span <= 0 or not np.isfinite(span*span) or span*span == 0:
            raise ValueError('meridional geometry is outside finite SI area arithmetic')
        normalized = (points-points[0])/span
        vertices = normalized[cells]; u = vertices[:,1]-vertices[:,0]; v = vertices[:,2]-vertices[:,0]
        det = u[:,0]*v[:,1]-u[:,1]*v[:,0]
        cancellation = abs(u[:,0]*v[:,1])+abs(u[:,1]*v[:,0])
        if (not np.isfinite(det).all() or np.any(det <= 0)
            or np.any(det <= 64*np.finfo(float).eps*cancellation)
            or any(_orient(*points[row]) <= 0 for row in cells)):
            raise ValueError('meridional triangles need resolved positive Jacobians; improve shape or coordinates')
        incidence = {}; links = [dict() for _ in points]
        for cell,row in enumerate(cells):
            for i,j in ((0,1),(1,2),(2,0)):
                a,b = int(row[i]),int(row[j])
                incidence.setdefault(tuple(sorted((a,b))),[]).append((cell,i,j,a,b))
            for i in range(3):
                a,b,c = map(int,(row[i],row[(i+1)%3],row[(i+2)%3]))
                links[a].setdefault(b,set()).add(c); links[a].setdefault(c,set()).add(b)
        adjacency = [set() for _ in cells]; boundary = []
        for owners in incidence.values():
            if len(owners) == 1: boundary.append(owners[0])
            elif len(owners) == 2:
                a,b = owners
                if a[3:] != b[3:][::-1]:
                    raise ValueError('meridional shared edge has inconsistent orientation')
                adjacency[a[0]].add(b[0]); adjacency[b[0]].add(a[0])
            else: raise ValueError('meridional edge has more than two incident triangles')
        if not _connected(dict(enumerate(adjacency))):
            raise ValueError('meridional vacuum must be one edge-connected region')
        euler = len(points)-len(incidence)+len(cells)
        if euler != 1-len(holes) or not boundary:
            raise ValueError('meridional mesh Euler characteristic disagrees with the declared holes')
        successors = {}; predecessors = {}
        for cell,i,j,a,b in boundary:
            if a in successors or b in predecessors:
                raise ValueError('meridional boundary contains a pinched/nonmanifold vertex')
            successors[a] = b; predecessors[b] = a
        if successors.keys() != predecessors.keys():
            raise ValueError('meridional boundary is not closed')
        for vertex,link in enumerate(links):
            degrees = [len(neighbors) for neighbors in link.values()]
            if (not _connected(link) or degrees.count(1) != (2 if vertex in successors else 0)
                or any(d not in (1,2) for d in degrees)):
                raise ValueError('meridional vertex link is not a disk neighborhood')
        remaining = set(successors); cycles = 0
        while remaining:
            start = min(remaining); current = start
            while current in remaining:
                remaining.remove(current); current = successors[current]
            if current != start: raise ValueError('meridional boundary cycles merge')
            cycles += 1
        if cycles != len(contours):
            raise ValueError('meridional boundary cycle count differs from declared contours')
        _check_edges(points,np.array(list(incidence)),'meridional mesh')
        lookup = {tuple(p):i for i,p in enumerate(points)}
        covered = {}; segment = 0
        for component,contour in enumerate(contours):
            try: corners = [lookup[tuple(p)] for p in contour]
            except KeyError as exc:
                raise ValueError('each meridional contour corner must be an explicit mesh point') from exc
            if any(v not in successors for v in corners):
                raise ValueError('declared meridional corner is not a mesh boundary vertex')
            for a,b in zip(corners,corners[1:]+corners[:1]):
                current = a; axis = int(np.argmax(abs(points[b]-points[a])))
                direction = 1 if points[b,axis] > points[a,axis] else -1
                while current != b:
                    if current in covered:
                        raise ValueError('meridional boundary does not follow the declared contour order')
                    covered[current] = (component,segment); following = successors[current]
                    if (not _on_segment(points[a],points[b],points[following])
                        or direction*(points[following,axis]-points[current,axis]) <= 0):
                        raise ValueError('meridional boundary must exactly cover each declared segment; declare rounded bends explicitly')
                    current = following
                segment += 1
        if covered.keys() != successors.keys():
            raise ValueError('meridional mesh has undeclared boundary segments')
        area = float(np.sum(det)*span**2/2); expected_area = float(sum(areas))
        if expected_area <= 0 or abs(area-expected_area) > 64*np.finfo(float).eps*max(area,expected_area):
            raise ValueError('meridional triangles do not cover the declared vacuum area')
        volume = float(np.pi*np.sum(det*span**2*points[cells,0].mean(axis=1)))
        if not np.isfinite(volume) or volume <= 0:
            raise ValueError('meridional volume is outside finite positive SI arithmetic')
        boundary.sort(key=lambda entry:(entry[3],entry[4]))
        edges = np.array([row[3:] for row in boundary],dtype=np.int64)
        components = np.array([covered[row[3]][0] for row in boundary],dtype=np.int64)
        segments = np.array([covered[row[3]][1] for row in boundary],dtype=np.int64)
        endpoints = points[edges]
        measures = 2*np.pi*endpoints[:,:,0].mean(axis=1)*np.linalg.norm(endpoints[:,1]-endpoints[:,0],axis=1)
        surface = np.bincount(segments,weights=measures,minlength=segment)
        if not np.isfinite(surface).all() or np.any(surface <= 0):
            raise ValueError('meridional surface area is outside positive SI arithmetic')
        values = dict(outer_rz_m=outer,holes_rz_m=holes,points_rz_m=points,triangles=cells,
                      boundary_edges=edges,boundary_cells=np.array([row[0] for row in boundary],dtype=np.int64),
                      boundary_local_vertices=np.array([row[1:3] for row in boundary],dtype=np.int64),
                      boundary_components=components,boundary_segments=segments,area_m2=area,volume_m3=volume,
                      surface_area_m2_by_segment=surface,euler_characteristic=euler)
        for value in [*values.values(),*holes]:
            if isinstance(value,np.ndarray): value.setflags(write=False)
        for name,value in values.items(): object.__setattr__(self,name,value)

    def to_dict(self):
        return dict(format='superfish_ng_meridional_mesh',schema_version=1,coordinates='r,z in metres',boundary='all_pec',
                    outer_rz_m=self.outer_rz_m.tolist(),holes_rz_m=[h.tolist() for h in self.holes_rz_m],
                    points_rz_m=self.points_rz_m.tolist(),triangles=self.triangles.tolist())

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','coordinates','boundary','outer_rz_m','holes_rz_m','points_rz_m','triangles']
        keys(data,names,names,'meridional mesh')
        if (data['format'] != 'superfish_ng_meridional_mesh' or type(data['schema_version']) is not int
            or data['schema_version'] != 1 or data['coordinates'] != 'r,z in metres' or data['boundary'] != 'all_pec'):
            raise ValueError('expected meridional mesh schema 1, r,z in metres and all_pec')
        return cls(**{name:data[name] for name in names[4:]})

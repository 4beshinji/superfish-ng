# SPDX-License-Identifier: Apache-2.0
"""Explicit quadratic meridional geometry, with an unchanged chord topology.

This defines polynomial geometry only: it is neither a curved Hphi solver nor
an exact conic representation. All input coordinates are interpreted as binary64.
"""
from dataclasses import dataclass, field
from fractions import Fraction as F
from math import factorial, pi
from types import MappingProxyType
import numpy as np
from .config import keys
from .coaxial import _numeric_coordinates
from .meridional_mesh import MeridionalMesh
from .axis_connected_mesh import AxisConnectedMesh
from .mesh import Mesh
from .high_order import quadratic_space
from .quadratic_geometry import QuadraticTriangle
from .curved_space import check_curved_edges


_POWERS = ((0,0),(1,0),(0,1),(2,0),(1,1),(0,2))


def _polynomial(values):
    p,q,r,s,t,u = map(lambda v:F(float(v)),values)
    return dict(zip(_POWERS,(p,-3*p-q+4*s,-3*p-r+4*u,
                            2*p+2*q-4*s,4*(p-s+t-u),2*p+2*r-4*u)))


def _derivative(p,axis):
    result = {}
    for powers,value in p.items():
        if powers[axis]:
            new = list(powers); new[axis]-=1
            result[tuple(new)] = value*powers[axis]
    return result


def _product(p,q):
    result = {}
    for (a,b),v in p.items():
        for (c,d),w in q.items():
            key=(a+c,b+d); result[key]=result.get(key,F(0))+v*w
    return result


def _minimum(p):
    """Exact quadratic minimum on the closed reference triangle."""
    c,a,b,d,e,f = [p.get(key,F(0)) for key in _POWERS]
    candidates = [(F(0),F(0)),(F(1),F(0)),(F(0),F(1))]
    for (x,y),(u,v) in (((0,0),(1,0)),((0,0),(0,1)),((1,0),(-1,1))):
        linear=a*u+b*v+2*d*x*u+e*(x*v+y*u)+2*f*y*v
        square=d*u*u+e*u*v+f*v*v
        if square>0:
            t=-linear/(2*square)
            if 0<t<1: candidates.append((x+t*u,y+t*v))
    determinant=4*d*f-e*e
    if d>0 and determinant>0:
        x,y=(e*b-2*f*a)/determinant,(e*a-2*d*b)/determinant
        if x>0 and y>0 and x+y<1: candidates.append((x,y))
    return min(c+a*x+b*y+d*x*x+e*x*y+f*y*y for x,y in candidates)


def _integral(p):
    return sum((v*F(factorial(a)*factorial(b),factorial(a+b+2))
                for (a,b),v in p.items()),F(0))


def _edge_polynomial(values):
    a,b,m = map(lambda v:F(float(v)),values)
    return { (0,0):a,(1,0):-3*a-b+4*m,(2,0):2*a+2*b-4*m }


def _edge_integral(p):
    return sum((v/F(a+1) for (a,b),v in p.items()),F(0))


def _positive_edge_interior(p):
    c,a,d = (p.get((n,0),F(0)) for n in (0,1,2))
    if c<0 or c+a+d<0 or (c==0 and a==0 and d==0): return False
    if d>0:
        t=-a/(2*d)
        if 0<t<1 and c+a*t+d*t*t<=0: return False
    return True


@dataclass(frozen=True,eq=False)
class CurvedMeridionalGeometry:
    base_mesh: object
    edge_vertices: object
    edge_midpoints_rz_m: object
    max_boxes_per_pair: int = 10000
    points_rz_m: np.ndarray = field(init=False)
    cell_nodes: np.ndarray = field(init=False)
    boundary_nodes: np.ndarray = field(init=False)
    boundary_tags: np.ndarray = field(init=False)
    area_m2: float = field(init=False)
    volume_m3: float = field(init=False)
    validation: object = field(init=False)

    def __post_init__(self):
        if type(self.base_mesh) not in (MeridionalMesh,AxisConnectedMesh):
            raise ValueError('curved meridional geometry requires a validated explicit chord mesh')
        if type(self.max_boxes_per_pair) is not int or self.max_boxes_per_pair<1:
            raise ValueError('max_boxes_per_pair must be a positive integer')
        base=type(self.base_mesh).from_dict(self.base_mesh.to_dict())
        axis=isinstance(base,AxisConnectedMesh)
        edges=np.unique(np.sort(base.triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
        raw=np.asarray(self.edge_vertices,dtype=object)
        if (raw.shape!=edges.shape or any(isinstance(v,(bool,np.bool_)) or not isinstance(v,(int,np.integer)) for v in raw.flat)
            or not np.array_equal(raw,edges)):
            raise ValueError('edge_vertices must list every chord edge once in lexicographic order, with each start < end')
        mids=_numeric_coordinates(self.edge_midpoints_rz_m,2,'edge_midpoints_rz_m').copy()
        if mids.shape!=edges.shape:
            raise ValueError('edge_midpoints_rz_m must contain exactly one finite (r,z) row per declared edge')
        tags=base.boundary_tags.copy() if axis else np.full(len(base.boundary_edges),'pec',dtype='U20')
        axis_nodes=base.axis_nodes if axis else np.array([],dtype=np.int64)
        mesh=Mesh(base.points_rz_m,base.triangles,base.boundary_edges,tags,base.boundary_cells,axis_nodes)
        space=quadratic_space(mesh)
        points=np.vstack((base.points_rz_m,mids))
        cells=space.cell_dofs.copy(); boundary=space.boundary_dofs.copy()
        if axis:
            rows=boundary[tags=='axis']
            if not np.array_equal(points[rows[:,2]],points[rows[:,:2]].mean(axis=1)):
                raise ValueError('declared axis edges must retain their exact straight midpoint coordinates')
        area=F(0); moment=F(0); minimum_radius=None; minimum_jacobian=None
        for index,nodes in enumerate(cells):
            coordinates=points[nodes]
            r,z=(_polynomial(coordinates[:,i]) for i in (0,1))
            lower=_minimum(r)
            if lower<0 or (not axis and lower<=0):
                raise ValueError(f'curved cell {index} has nonpositive/negative radius between its geometry nodes')
            minimum_radius=lower if minimum_radius is None else min(minimum_radius,lower)
            determinant=_product(_derivative(r,0),_derivative(z,1))
            for power,value in _product(_derivative(r,1),_derivative(z,0)).items():
                determinant[power]=determinant.get(power,F(0))-value
            jacobian=_minimum(determinant)
            if jacobian<=0:
                raise ValueError(f'curved cell {index} has a nonpositive Jacobian over the reference triangle')
            QuadraticTriangle(coordinates)  # Also reject numerically unresolved maps.
            minimum_jacobian=jacobian if minimum_jacobian is None else min(minimum_jacobian,jacobian)
            area+=_integral(determinant);moment+=_integral(_product(r,determinant))
        component_area=[F(0) for _ in range(1+len(base.holes_rz_m))]
        component_moment=[F(0) for _ in component_area]
        for nodes,tag,component in zip(boundary,tags,base.boundary_components):
            r,z=(_edge_polynomial(points[nodes,i]) for i in (0,1))
            if tag!='axis' and not _positive_edge_interior(r):
                raise ValueError('non-axis curved boundary touches or crosses the axis between its nodes')
            dz=_derivative(z,0)
            component_area[component]+=_edge_integral(_product(r,dz))
            component_moment[component]+=_edge_integral(_product(_product(r,r),dz))/2
        if component_area[0]<=0 or any(a>=0 for a in component_area[1:]):
            raise ValueError('curved outer and hole boundary orientations must retain their roles')
        if sum(component_area)!=area or sum(component_moment)!=moment:
            raise ValueError('curved cell and oriented full-boundary moments disagree')
        report=check_curved_edges(points,cells,boundary,max_boxes=self.max_boxes_per_pair,hole_count=len(base.holes_rz_m))
        area_float=float(area);volume_float=2*pi*float(moment)
        if not np.isfinite((area_float,volume_float)).all() or min(area_float,volume_float)<=0:
            raise ValueError('curved area/volume is outside finite positive SI arithmetic')
        report=dict(report,boundary_components=len(component_area),axis_connected=axis,
                    minimum_radius_m=float(minimum_radius),minimum_jacobian_m2=float(minimum_jacobian),
                    boundary_area_by_component_m2=[float(a) for a in component_area],
                    exact_cell_boundary_moments_equal=True,
                    scope='explicit quadratic polynomial geometry; no conic or FEM accuracy claim')
        for array in (edges,mids,points,cells,boundary,tags): array.setflags(write=False)
        for name,value in dict(base_mesh=base,edge_vertices=edges,edge_midpoints_rz_m=mids,
            points_rz_m=points,cell_nodes=cells,boundary_nodes=boundary,boundary_tags=tags,
            area_m2=area_float,volume_m3=volume_float,validation=MappingProxyType(report)).items():
            object.__setattr__(self,name,value)

    def to_dict(self):
        return dict(format='superfish_ng_curved_meridional_geometry',schema_version=1,
                    coordinates='r,z in metres',geometry='quadratic_polynomial',
                    base_mesh=self.base_mesh.to_dict(),edge_vertices=self.edge_vertices.tolist(),
                    edge_midpoints_rz_m=self.edge_midpoints_rz_m.tolist(),max_boxes_per_pair=self.max_boxes_per_pair)

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','coordinates','geometry','base_mesh','edge_vertices','edge_midpoints_rz_m','max_boxes_per_pair']
        keys(data,names,names,'curved meridional geometry')
        if (data['format']!='superfish_ng_curved_meridional_geometry' or type(data['schema_version']) is not int
            or data['schema_version']!=1 or data['coordinates']!='r,z in metres' or data['geometry']!='quadratic_polynomial'):
            raise ValueError('expected curved meridional geometry schema 1 with explicit quadratic_polynomial SI geometry')
        if not isinstance(data['base_mesh'],dict): raise ValueError('base_mesh must be an explicit meridional mesh object')
        name=data['base_mesh'].get('format')
        types={'superfish_ng_meridional_mesh':MeridionalMesh,'superfish_ng_axis_connected_mesh':AxisConnectedMesh}
        if name not in types: raise ValueError('base_mesh must be a positive-radius or axis-connected meridional mesh')
        return cls(types[name].from_dict(data['base_mesh']),**{name:data[name] for name in names[5:]})

# SPDX-License-Identifier: Apache-2.0
"""Fixed-material common cells and complete, paired one-sided interfaces."""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from .config import integer,keys
from .rf_materials import RFMaterialPartition
from .hphi_geometry_mapping import HphiGeometryMapping
from .hphi_mapped_overlap import mapped_hphi_overlay,_triangles,_barycentric,_compose
from .meridional_overlap import meridional_overlay
from .planar_tracking_overlap import _cross
from .planar_tracking_remesh import _rational_points


def _pairs(values,previous,current,label):
    if type(values) not in (list,tuple):raise ValueError(label+' requires explicit ID pairs')
    pairs=[]
    for value in values:
        keys(value,['previous_id','current_id'],['previous_id','current_id'],label)
        if any(type(value[k]) is not str for k in value):raise ValueError(label+' IDs must be strings')
        pairs.append((value['previous_id'],value['current_id']))
    if (len(pairs)!=len(previous) or len(pairs)!=len(current)
            or {a for a,b in pairs}!=set(previous) or {b for a,b in pairs}!=set(current)):
        raise ValueError(label+' must be a complete bijection over both declared ID sets')
    return tuple(pairs)


@dataclass(frozen=True,eq=False)
class MaterialHphiComparison:
    previous_partition: RFMaterialPartition
    current_partition: RFMaterialPartition
    mapping: object
    material_pairs: object
    region_pairs: object

    def __post_init__(self):
        for name in ('previous_partition','current_partition'):
            p=getattr(self,name)
            if type(p) is not RFMaterialPartition:raise ValueError('material comparison requires complete RFMaterialPartition objects')
            object.__setattr__(self,name,RFMaterialPartition.from_dict(p.to_dict()))
        a,b=self.previous_partition,self.current_partition
        if type(a.mesh) is not type(b.mesh):raise ValueError('material comparison must preserve the axis/positive-radius mesh type')
        mapping=self.mapping
        if type(mapping) is HphiGeometryMapping:
            mapping=HphiGeometryMapping.from_dict(mapping.to_dict())
        elif type(mapping) is not str or mapping!='same_domain':
            raise ValueError('material comparison requires same_domain or an explicit HphiGeometryMapping')
        object.__setattr__(self,'mapping',mapping)
        materials=[{m.id:m for m in p.materials} for p in (a,b)]
        regions=[{r.id:r for r in p.regions} for p in (a,b)]
        mp=_pairs(self.material_pairs,*materials,'material_pairs');rp=_pairs(self.region_pairs,*regions,'region_pairs')
        for x,y in mp:
            ma,mb=materials[0][x],materials[1][y]
            if (ma.epsilon_r,ma.mu_r)!=(mb.epsilon_r,mb.mu_r):
                raise ValueError('material comparison requires exactly fixed epsilon_r and mu_r')
        material_map=dict(mp)
        for x,y in rp:
            if material_map[regions[0][x].material]!=regions[1][y].material:
                raise ValueError('region correspondence disagrees with material correspondence')
        # Own immutable pairs, without retaining mutable caller dictionaries.
        object.__setattr__(self,'material_pairs',mp);object.__setattr__(self,'region_pairs',rp)

    def to_dict(self):
        return dict(format='superfish_ng_material_hphi_comparison',schema_version=1,
            previous_partition=self.previous_partition.to_dict(),current_partition=self.current_partition.to_dict(),
            mapping=self.mapping.to_dict() if type(self.mapping) is HphiGeometryMapping else self.mapping,
            **{name:[dict(previous_id=a,current_id=b) for a,b in getattr(self,name)] for name in ('material_pairs','region_pairs')})

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','previous_partition','current_partition','mapping','material_pairs','region_pairs']
        keys(data,names,names,'material Hphi comparison')
        if data['format']!='superfish_ng_material_hphi_comparison' or type(data['schema_version']) is not int or data['schema_version']!=1:
            raise ValueError('expected material Hphi comparison schema_version 1')
        for name in ('material_pairs','region_pairs'):
            if type(data[name]) is not list:raise ValueError(name+' must be a JSON array')
        mapping=data['mapping']
        if isinstance(mapping,dict):mapping=HphiGeometryMapping.from_dict(mapping)
        return cls(*(RFMaterialPartition.from_dict(data[n]) for n in ('previous_partition','current_partition')),
                   mapping,data['material_pairs'],data['region_pairs'])


@dataclass(frozen=True)
class MaterialInterfaceOverlay:
    previous_edges: np.ndarray
    current_edges: np.ndarray
    previous_cells: np.ndarray
    current_cells: np.ndarray
    mapping_cells: np.ndarray
    previous_vertices_rz_m: np.ndarray
    current_vertices_rz_m: np.ndarray


@dataclass(frozen=True)
class MaterialHphiOverlay:
    comparison: MaterialHphiComparison
    overlay: object
    previous_region_indices: np.ndarray
    current_region_indices: np.ndarray
    interfaces: MaterialInterfaceOverlay


def _point(a,b,t):return tuple(x+t*(y-x) for x,y in zip(a,b))


def _clip_edge(a,b,triangle):
    lo,hi=Fraction(0),Fraction(1)
    for x,y in zip(triangle,triangle[1:]+triangle[:1]):
        start=_cross(x,y,a);delta=_cross(x,y,b)-start
        if delta>0:lo=max(lo,-start/delta)
        elif delta<0:hi=min(hi,-start/delta)
        elif start<0:return None
    return (lo,hi) if lo<hi else None


def _parameter(p,a,b):
    k=0 if a[0]!=b[0] else 1
    return (p[k]-a[k])/(b[k]-a[k])


def _edge_overlap(a,b,c,d):
    if _cross(a,b,c) or _cross(a,b,d):return None
    t,u=_parameter(c,a,b),_parameter(d,a,b)
    lo,hi=max(Fraction(0),min(t,u)),min(Fraction(1),max(t,u))
    return (lo,hi) if lo<hi else None


def _complete_intervals(intervals,label):
    end=Fraction(0)
    for lo,hi in sorted(intervals):
        if lo!=end or hi<=lo:raise ValueError(label+' interface has a gap or overlapping ownership')
        end=hi
    if end!=1:raise ValueError(label+' interface is not completely covered')


def _interfaces(comparison,region_map,max_tests,max_parts):
    a,b=comparison.previous_partition,comparison.current_partition
    points=[_rational_points(p.mesh.points_rz_m) for p in (a,b)]
    edges=[[(ps[int(i)],ps[int(j)]) for i,j in p.interface_edges] for p,ps in zip((a,b),points)]
    mapping=comparison.mapping
    controls=None if type(mapping) is str else (_triangles(mapping.previous),_triangles(mapping.current))
    budget=0;fragments=[]
    for i,(x,y) in enumerate(edges[0]):
        if controls is None:
            if len(fragments)>=max_parts:raise ValueError('material interfaces exceed max_interface_pieces')
            fragments.append((i,-1,Fraction(0),Fraction(1),x,y,x,y));continue
        seen={}
        for control,tri in enumerate(controls[0]):
            budget+=1
            if budget>max_tests:raise ValueError('material interfaces exceed max_interface_tests')
            interval=_clip_edge(x,y,tri)
            if interval is None:continue
            lo,hi=interval;old=(_point(x,y,lo),_point(x,y,hi))
            new=tuple(_compose(_barycentric(old,tri),controls[1][control]))
            if interval in seen:
                if seen[interval]!=new:raise ValueError('material interface mapping is discontinuous')
                continue
            seen[interval]=new
            if len(fragments)>=max_parts:raise ValueError('material interfaces exceed max_interface_pieces')
            fragments.append((i,control,lo,hi,*old,*new))
        _complete_intervals(list(seen),'mapped previous')
    covered_a=[[] for _ in edges[0]];covered_b=[[] for _ in edges[1]];parts=[[] for _ in range(7)]
    for i,control,lo,hi,x,y,u,v in fragments:
        for j,(c,d) in enumerate(edges[1]):
            budget+=1
            if budget>max_tests:raise ValueError('material interfaces exceed max_interface_tests')
            interval=_edge_overlap(u,v,c,d)
            if interval is None:continue
            s,t=interval;current=(_point(u,v,s),_point(u,v,t));previous=(_point(x,y,s),_point(x,y,t))
            acells=a.interface_cells[i];bcells=b.interface_cells[j]
            expected=region_map[a.cell_region_indices[acells]]
            actual=b.cell_region_indices[bcells]
            if set(expected)!=set(actual):raise ValueError('material interface region sides do not correspond')
            bcells=bcells[[int(np.flatnonzero(actual==owner)[0]) for owner in expected]]
            covered_a[i].append((lo+s*(hi-lo),lo+t*(hi-lo)))
            covered_b[j].append(tuple(sorted(_parameter(p,c,d) for p in current)))
            if len(parts[0])>=max_parts:raise ValueError('material interfaces exceed max_interface_pieces')
            for part,value in zip(parts,(i,j,acells,bcells,control,previous,current)):part.append(value)
    for intervals in covered_a:_complete_intervals(intervals,'previous')
    for intervals in covered_b:_complete_intervals(intervals,'current')
    shapes=[(-1,),(-1,),(-1,2),(-1,2),(-1,),(-1,2,2),(-1,2,2)]
    arrays=[np.asarray(p,dtype=np.int64 if i<5 else float).reshape(shapes[i]) for i,p in enumerate(parts)]
    if any(not np.isfinite(v).all() for v in arrays):raise ValueError('material interfaces are unresolved in floating arithmetic')
    if any(np.any(np.all(v[:,0]==v[:,1],axis=1)) for v in arrays[5:]):
        raise ValueError('material interface endpoints collapse in floating arithmetic')
    for v in arrays:v.setflags(write=False)
    return MaterialInterfaceOverlay(*arrays)


def material_hphi_overlay(comparison,*,max_candidate_tests=2000000,max_overlay_triangles=250000,
                          max_interface_tests=2000000,max_interface_pieces=250000):
    """Verify complete region volumes and both sides of every mapped interface.

    Coordinates are exact binary64 rationals during all coverage checks.
    Volume and interface search budgets are separate explicit bounds. Returned
    interface cell pairs are ordered by the previous side's two region IDs.
    No material averaging, FEM solve, field transport or mode tracking occurs.
    """
    if type(comparison) is not MaterialHphiComparison:raise ValueError('expected explicit MaterialHphiComparison')
    for name,value in [('max_candidate_tests',max_candidate_tests),('max_overlay_triangles',max_overlay_triangles),
                       ('max_interface_tests',max_interface_tests),('max_interface_pieces',max_interface_pieces)]:integer(value,name)
    q=MaterialHphiComparison.from_dict(comparison.to_dict());a,b=q.previous_partition,q.current_partition
    mapping=q.mapping
    if type(mapping) is str:
        overlay=meridional_overlay(a.mesh,b.mesh,max_candidate_tests=max_candidate_tests,max_overlay_triangles=max_overlay_triangles)
    else:
        overlay=mapped_hphi_overlay(a.mesh,b.mesh,mapping,max_candidate_tests=max_candidate_tests,max_overlay_triangles=max_overlay_triangles)
    current_ids={r.id:i for i,r in enumerate(b.regions)};correspondence=dict(q.region_pairs)
    region_map=np.array([current_ids[correspondence[r.id]] for r in a.regions],dtype=np.int64)
    ar=a.cell_region_indices[overlay.previous_cells];br=b.cell_region_indices[overlay.current_cells]
    if np.any(region_map[ar]!=br):raise ValueError('material region mismatch on a positive-area common cell; preserve every interface')
    interfaces=_interfaces(q,region_map,max_interface_tests,max_interface_pieces)
    for v in (ar,br):v.setflags(write=False)
    return MaterialHphiOverlay(q,overlay,ar,br,interfaces)

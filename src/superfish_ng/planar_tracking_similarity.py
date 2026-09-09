# SPDX-License-Identifier: Apache-2.0
"""Declared proper similarity and original-element integration for planar meshes.

The inverse flag reverses the declared operation without recomputing rounded
inverse coefficients. This is geometry validation, not mode correspondence.
"""
from dataclasses import dataclass
import numpy as np
from .config import integer,keys
from .planar_mesh import PlanarMesh
from .planar_refinement import refine_planar_mesh,REFERENCE,SPLIT
from .planar_tracking_overlap import PlanarTrackingOverlay

@dataclass(frozen=True)
class PolygonSimilarityMapping:
    scale:float
    rotation_radians:float
    translation_xy_m:tuple
    previous_refinements:int=0
    current_refinements:int=0
    inverse:bool=False
    def __post_init__(self):
        if type(self.inverse) is not bool:raise ValueError('inverse must be boolean')
        for name in ('scale','rotation_radians'):
            value=getattr(self,name)
            if type(value) not in (int,float) or not np.isfinite(value):raise ValueError(name+' must be finite')
        if self.scale<=0:raise ValueError('scale must be positive')
        if type(self.translation_xy_m) not in (list,tuple) or len(self.translation_xy_m)!=2 or any(type(x) not in (int,float) or not np.isfinite(x) for x in self.translation_xy_m):raise ValueError('translation requires two finite SI coordinates')
        object.__setattr__(self,'translation_xy_m',tuple(self.translation_xy_m))
        for name in ('previous_refinements','current_refinements'):
            integer(getattr(self,name),name,0)
            if getattr(self,name)>8:raise ValueError('at most eight refinements')
        if self.previous_refinements and self.current_refinements:raise ValueError('only one mesh can be finer')
    @property
    def rotation(self):
        c,s=np.cos(self.rotation_radians),np.sin(self.rotation_radians)
        return np.array([[c,-s],[s,c]])
    def to_dict(self):
        return dict(name='polygon_similarity', scale=self.scale, rotation_radians=self.rotation_radians,
                    translation_xy_m=list(self.translation_xy_m), inverse=self.inverse,
                    previous_refinements=self.previous_refinements, current_refinements=self.current_refinements)

    @classmethod
    def from_dict(cls, data):
        names=['name','scale','rotation_radians','translation_xy_m','inverse',
               'previous_refinements','current_refinements']
        keys(data,names,names,'polygon similarity mapping')
        if data['name']!='polygon_similarity':raise ValueError('expected polygon_similarity mapping')
        if type(data['translation_xy_m']) is not list:raise ValueError('translation_xy_m must be a JSON list')
        return cls(data['scale'],data['rotation_radians'],data['translation_xy_m'],
                   data['previous_refinements'],data['current_refinements'],data['inverse'])

    @property
    def current_to_previous_rotation(self):
        """Column-vector rotation taking the current electric field to the previous frame."""
        return self.rotation if self.inverse else self.rotation.T

    def transform_mesh(self,mesh, *, reverse=False):
        """Apply this declared operation, or its opposite, to a validated mesh."""
        if not isinstance(mesh,PlanarMesh):raise ValueError('expected PlanarMesh')
        if type(reverse) is not bool:raise ValueError('reverse must be boolean')
        inverse=reverse!=self.inverse
        def points(value):return (value-self.translation_xy_m)@self.rotation/self.scale if inverse else self.scale*(value@self.rotation.T)+self.translation_xy_m
        return PlanarMesh.create(points(mesh.polygon_xy_m),points(mesh.points_xy_m),mesh.triangles)


    def _scalar_transform_mesh(self,mesh, *, reverse=False):
        """Explicit component arithmetic, also used by ordinary JSON producers.

        This is a fixed alternative evaluation order, never a fitted map.
        """
        inverse=reverse!=self.inverse
        c, sine=self.rotation[0,0],self.rotation[1,0]
        tx,ty=self.translation_xy_m
        def points(values):
            x,y=values.T
            if inverse:
                x,y=x-tx,y-ty
                return np.column_stack(((c*x+sine*y)/self.scale,(-sine*x+c*y)/self.scale))
            return np.column_stack((self.scale*(c*x-sine*y)+tx,self.scale*(sine*x+c*y)+ty))
        return PlanarMesh.create(points(mesh.polygon_xy_m),points(mesh.points_xy_m),mesh.triangles)


def _refined(mesh,levels,budget):
    for _ in range(levels):mesh=refine_planar_mesh(mesh,max_triangles=budget)
    return mesh

def _same_local_mesh(a,b):
    if a.points_xy_m.shape!=b.points_xy_m.shape or not np.array_equal(a.triangles,b.triangles):raise ValueError('declared numbering and connectivity differ')
    edges=np.unique(np.sort(a.triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
    lengths=np.linalg.norm(a.points_xy_m[edges[:,1]]-a.points_xy_m[edges[:,0]],axis=1);local=np.full(len(a.points_xy_m),np.inf)
    np.minimum.at(local,edges[:,0],lengths);np.minimum.at(local,edges[:,1],lengths)
    boundary=np.linalg.norm(np.roll(a.polygon_xy_m,-1,axis=0)-a.polygon_xy_m,axis=1);boundary=np.minimum(boundary,np.roll(boundary,1))
    for name,scale in [('points_xy_m',local),('polygon_xy_m',boundary)]:
        x,y=getattr(a,name),getattr(b,name)
        if x.shape!=y.shape or not np.all(np.abs(x-y)<=16*np.finfo(float).eps*scale[:,None]):raise ValueError('declared coordinates differ at local mesh precision')

def _exact_mesh(a,b):return all(np.array_equal(getattr(a,k),getattr(b,k)) for k in ('points_xy_m','polygon_xy_m','triangles'))

def polygon_similarity_overlay(previous,current,mapping, *, max_overlay_triangles=250000):
    """Evaluate original polynomials on a common partition in previous physical area.

    Coordinate error is capped by the shortest incident edge, including near
    zero coordinates. Exact alternative construction orders do not permit fits.
    The reference mesh is rebuilt from the previous original mesh, never from
    subtraction of large translated current coordinates.
    """
    if not isinstance(mapping,PolygonSimilarityMapping):raise ValueError('expected PolygonSimilarityMapping')
    if any(not isinstance(mesh,PlanarMesh) for mesh in (previous,current)):raise ValueError('expected two PlanarMesh objects')
    mapping=PolygonSimilarityMapping.from_dict(mapping.to_dict())
    budget=max_overlay_triangles
    integer(budget,'max_overlay_triangles');previous=PlanarMesh.create(previous.polygon_xy_m,previous.points_xy_m,previous.triangles);current=PlanarMesh.create(current.polygon_xy_m,current.points_xy_m,current.triangles)
    reverse=bool(mapping.previous_refinements);coarse,fine=(current,previous) if reverse else (previous,current);levels=mapping.previous_refinements if reverse else mapping.current_refinements;count=len(coarse.triangles)*4**levels
    if count>budget or count!=len(fine.triangles):raise ValueError('declared triangle count or max_overlay_triangles budget differs')
    expected=_refined(mapping.transform_mesh(coarse,reverse=reverse),levels,budget)
    try:_same_local_mesh(expected,fine)
    except ValueError:
        matched=False
        for transform in (mapping.transform_mesh,mapping._scalar_transform_mesh):
            # Both transform-before-refinement and refinement-before-transform
            # are recognized by exact arrays, without expanding local tolerance.
            if (_exact_mesh(_refined(transform(coarse,reverse=reverse),levels,budget),fine)
                    or _exact_mesh(transform(_refined(coarse,levels,budget),reverse=reverse),fine)
                    or (levels==0 and _exact_mesh(transform(fine,reverse=not reverse),coarse))):
                matched=True
                break
        if not matched:
            if not reverse:raise
            base=PlanarMesh.create(previous.polygon_xy_m,previous.points_xy_m[:len(current.points_xy_m)],current.triangles)
            if not _exact_mesh(_refined(base,levels,budget),previous):raise
            if not _exact_mesh(mapping._scalar_transform_mesh(base),current):
                _same_local_mesh(mapping.transform_mesh(base),current)
    parents=np.arange(len(coarse.triangles));bary=np.tile(np.eye(3),(len(parents),1,1))
    for _ in range(levels):
        bary=np.einsum('cij,njk->ncik',REFERENCE[SPLIT],bary).reshape(-1,3,3);parents=np.repeat(parents,4)
    identity=np.tile(np.eye(3),(count,1,1));indices=np.arange(count)
    reference=previous if reverse else _refined(previous,levels,budget)
    vertices=reference.points_xy_m[reference.triangles];u,v=vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0];det=u[:,0]*v[:,1]-u[:,1]*v[:,0]
    if not np.isfinite(det).all() or np.any(det<=0):raise ValueError('invalid previous reference area')
    arrays=((indices,parents,identity,bary) if reverse else (parents,indices,bary,identity))+ (vertices,det)
    for array in arrays:array.setflags(write=False)
    return PlanarTrackingOverlay(*arrays)

# SPDX-License-Identifier: Apache-2.0
"""Validated single polygon boundary in (z,r); no implicit geometry repair."""
from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class Contour:
    vertices_zr_m: tuple
    edge_tags: tuple

    def __post_init__(self):
        raw=self.vertices_zr_m
        if not isinstance(raw,(tuple,list)) or len(raw)<3:
            raise ValueError('contour requires at least three vertices')
        for point in raw:
            if not isinstance(point,(tuple,list)) or len(point)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in point):
                raise ValueError('contour vertices must be finite [z,r] pairs')
        p=np.array(raw,dtype=float)
        if not isinstance(self.edge_tags,(tuple,list)):
            raise ValueError("contour edge_tags must be a sequence")
        tags=tuple(self.edge_tags)
        if len(tags)!=len(p) or any(t not in ('axis','pec','electric_symmetry','magnetic_symmetry') for t in tags):
            raise ValueError('contour needs one supported tag per edge')
        if p[:,0].min()!=0 or p[:,0].max()<=0 or np.any(p[:,1]<0):
            raise ValueError('contour requires z from zero to positive L and nonnegative r')
        scale=float(np.max(p)); q=p/scale; tol=128*np.finfo(float).eps
        following=np.roll(q,-1,axis=0)
        cross=lambda a,b: float(a[0]*b[1]-a[1]*b[0])
        def on(a,b,c):
            return abs(cross(b-a,c-a))<=tol and np.all(c>=np.minimum(a,b)-tol) and np.all(c<=np.maximum(a,b)+tol)
        for i,(a,b) in enumerate(zip(q,following)):
            if np.linalg.norm(b-a)<=tol:raise ValueError(f'contour edge {i} is zero or numerically degenerate')
            c=q[(i+2)%len(q)]
            if abs(cross(b-a,c-b))<=tol and np.dot(b-a,c-b)<0:
                raise ValueError(f'contour adjacent edges {i}/{(i+1)%len(q)} overlap')
            for j in range(i+1,len(q)):
                if j==i+1 or (i==0 and j==len(q)-1):continue
                c,d=q[j],following[j]
                o=[cross(b-a,c-a),cross(b-a,d-a),cross(d-c,a-c),cross(d-c,b-c)]
                if (o[0]*o[1]<0 and o[2]*o[3]<0) or on(a,b,c) or on(a,b,d) or on(c,d,a) or on(c,d,b):
                    raise ValueError(f'contour edges {i}/{j} intersect or touch')
        axis=q[:,1]==0
        starts=np.count_nonzero(axis & ~np.roll(axis,1))
        if starts!=1 or np.count_nonzero(axis)<2 or set(p[axis,0][[np.argmin(p[axis,0]),np.argmax(p[axis,0])]])!={0.,float(p[:,0].max())}:
            raise ValueError('contour axis must be one connected chain spanning z=0 to L')
        for i,(a,b) in enumerate(zip(p,np.roll(p,-1,axis=0))):
            if (a[1]==b[1]==0)!=(tags[i]=='axis'):
                raise ValueError(f'contour edge {i} has an invalid axis tag')
            if tags[i].endswith('_symmetry') and not (a[0]==b[0] and a[0] in (0,p[:,0].max())):
                raise ValueError(f'contour symmetry edge {i} is not a flat end')
        signed=sum(cross(a,b) for a,b in zip(q,following))/2
        if abs(signed)<=tol:raise ValueError('contour area is numerically degenerate')
        if signed<0:
            indices=list(range(len(p)-1,-1,-1));p=p[indices]
            tags=tuple(tags[(i-1)%len(tags)] for i in indices)
        start=np.flatnonzero(np.all(p==[0,0],axis=1))
        if len(start)!=1:raise ValueError('contour axis must contain origin')
        index=int(start[0]);p=np.roll(p,-index,axis=0);tags=tags[index:]+tags[:index]
        object.__setattr__(self,'vertices_zr_m',tuple(map(tuple,p.tolist())))
        object.__setattr__(self,'edge_tags',tags)

    @property
    def area_m2(self):
        p=np.array(self.vertices_zr_m);b=np.roll(p,-1,axis=0)
        return float(np.sum(p[:,0]*b[:,1]-b[:,0]*p[:,1])/2)

    @property
    def volume_m3(self):
        p=np.array(self.vertices_zr_m);b=np.roll(p,-1,axis=0)
        return float(math.pi/3*np.sum((p[:,1]+b[:,1])*(p[:,0]*b[:,1]-b[:,0]*p[:,1])))

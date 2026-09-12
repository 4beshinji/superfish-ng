# SPDX-License-Identifier: Apache-2.0
"""Dyadic synthetic holes under (r,z) -> (r,z+alpha*r*r), det DF = 1."""
import numpy as np
from scripts.hphi_mesh_reference import rectangular_holes
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.axis_connected_mesh import AxisConnectedMesh


def fixture(axis=False,holes=1,n=1,scale=1.,shear=1.,z_offset=0.):
    raw=rectangular_holes(n,holes);strips=5 if holes==2 else 3
    def dyadic(points):
        p=np.asarray(points).copy()
        p[:,0]=(np.rint((p[:,0]-.025)/(.075/(strips*n)))/n+(0 if axis else 1))/16
        p[:,1]=np.rint(p[:,1]/(.18/(3*n)))/n/16
        return p*scale
    data=dict(outer_rz_m=dyadic(raw['outer_rz_m']),holes_rz_m=[dyadic(h) for h in raw['holes_rz_m']],
              points_rz_m=dyadic(raw['points_rz_m']),triangles=raw['triangles'])
    cls=AxisConnectedMesh if axis else MeridionalMesh
    original=cls(**data);alpha=shear/scale
    def transform(p):
        q=np.asarray(p).copy();q[:,1]+=alpha*q[:,0]**2+z_offset;return q
    edges=np.unique(np.sort(original.triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
    mapped=transform(original.points_rz_m);loops=[]
    for component in range(1+holes):
        pairs=original.boundary_edges[original.boundary_components==component]
        successor={int(a):int(b) for a,b in pairs};start=min(successor);loop=[start]
        while successor[loop[-1]]!=start:loop.append(successor[loop[-1]])
        assert len(loop)==len(successor)
        loops.append(mapped[loop])
    base=cls(loops[0],loops[1:],mapped,original.triangles)
    mids=transform(original.points_rz_m[edges].mean(axis=1))
    # The shear has determinant 1 and leaves r unchanged; integrate each source rectangle.
    a,z0=original.outer_rz_m[0];b,z1=original.outer_rz_m[2]
    area=(b-a)*(z1-z0);moment=(b*b-a*a)*(z1-z0)/2
    for h in original.holes_rz_m:
        a,z0=h[0];b,z1=h[2];area-=(b-a)*(z1-z0);moment-=(b*b-a*a)*(z1-z0)/2
    return dict(base_mesh=base,edge_vertices=edges,edge_midpoints_rz_m=mids),dict(
        area_m2=area,volume_m3=2*np.pi*moment,alpha_per_m=alpha)


def form_invariants(axis,holes,n,scale,shear,z_offset):
    """Integrals on original rectangles; the shear preserves area and radius."""
    data,_=fixture(axis,holes,n,scale,0.,0.);base=data['base_mesh'];alpha=shear/scale
    rectangles=[(base.outer_rz_m,1),*((h,-1) for h in base.holes_rz_m)]
    powers=(1,3) if axis else (-1,1)
    integral={p:0. for p in powers};z_mass=0.
    for polygon,sign in rectangles:
        a,z0=polygon.min(axis=0);b,z1=polygon.max(axis=0);length=z1-z0
        def radial(p):return np.log(b/a) if p==-1 else (b**(p+1)-a**(p+1))/(p+1)
        for power in powers:integral[power]+=sign*length*radial(power)
        if not axis:
            za,zb=z0+z_offset,z1+z_offset
            z_mass+=sign*((zb**3-za**3)/3*radial(-1)+alpha*(zb**2-za**2)*radial(1)+alpha**2*length*radial(3))
    return dict(radial_integrals=integral,z_mass=z_mass)

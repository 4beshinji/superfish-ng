# SPDX-License-Identifier: Apache-2.0
"""Original declared quadratic coax geometry used by tuning and crossing tests."""
import numpy as np
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi import CurvedHphiCase


def coax(length,shear=0.,n=4):
    p=np.array([[.0625+.0625*i/n,length*j/n] for j in range(n+1) for i in range(n+1)])
    cells=[]
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;b=a+1;d=a+n+1;c=d+1
            cells.extend(((a,b,c),(a,c,d)))
    cells=np.array(cells);edges=np.unique(np.sort(cells[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
    def mapped(points):
        q=points.copy();q[:,1]+=shear*q[:,0]**2;return q
    boundary=(list(range(n+1))+[j*(n+1)+n for j in range(1,n+1)]
              +[n*(n+1)+i for i in range(n-1,-1,-1)]+[j*(n+1) for j in range(n-1,0,-1)])
    loop=p[boundary]
    base=MeridionalMesh(mapped(loop),[],mapped(p),cells)
    return CurvedHphiCase(CurvedMeridionalGeometry(base,edges,mapped(p[edges].mean(axis=1))),modes=3)


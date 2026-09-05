# SPDX-License-Identifier: Apache-2.0
"""Independent Galerkin assembly of Hphi=r*u; no legacy routines.

Kij = integral r [(2Ni+r Ni,r)(2Nj+r Nj,r)+r^2 Ni,z Nj,z] dr dz
Mij = integral r^3 Ni Nj dr dz. K u = (omega/c)^2 M u.
Natural boundary is PEC, NOT d_n Hphi=0 at radial/sloping walls.
"""
import numpy as np
from scipy.sparse import coo_matrix
from .mesh import element_geometry


def triangle_quadrature(order=4):
    """Duffy product Gauss rule; order=4 integrates our degree-5 mass exactly."""
    x, w = np.polynomial.legendre.leggauss(order)
    x, w = (x+1)/2, w/2
    for a, wa in zip(x, w):
        for b, wb in zip(x, w):
            yield np.array([(1-a)*(1-b), a, (1-a)*b]), wa*wb*(1-a)


def assemble(mesh):
    p, det, grad = element_geometry(mesh)
    k = np.zeros((len(p), 3, 3))
    m = np.zeros_like(k)
    for n, w in triangle_quadrature():
        r = p[:, :, 0] @ n
        b = 2*n[None, :] + r[:, None]*grad[:, :, 0]
        d = r[:, None]*grad[:, :, 1]
        k += (w*det*r)[:, None, None]*(b[:, :, None]*b[:, None, :] + d[:, :, None]*d[:, None, :])
        m += (w*det*r**3)[:, None, None]*np.outer(n, n)
    rows = np.repeat(mesh.triangles, 3, axis=1).ravel()
    cols = np.tile(mesh.triangles, (1, 3)).ravel()
    shape = (len(mesh.points),)*2
    return tuple(coo_matrix((v.ravel(), (rows, cols)), shape=shape).tocsr() for v in (k, m))

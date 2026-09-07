# SPDX-License-Identifier: Apache-2.0
"""Local quadratic triangle maps with whole-reference-cell Jacobian checks.

Node order: vertices (0,0),(1,0),(0,1), then edge midpoints 01,12,20.
This geometry core does not by itself certify a conforming global mesh.
"""
from dataclasses import dataclass
import numpy as np
from .high_order import basis_p2

_REFERENCE_GRAD = np.array(((-1.,-1.),(1.,0.),(0.,1.)))
_REFERENCE_NODES = np.array(((0.,0.),(1.,0.),(0.,1.),(.5,0.),(.5,.5),(0.,.5)))
_VANDERMONDE = np.column_stack((np.ones(6),_REFERENCE_NODES,
                                _REFERENCE_NODES[:,0]**2,
                                _REFERENCE_NODES[:,0]*_REFERENCE_NODES[:,1],
                                _REFERENCE_NODES[:,1]**2))


def quadratic_minimum(coefficients):
    """Minimum of c+a*x+b*y+d*x²+e*x*y+f*y² on x,y>=0, x+y<=1."""
    c,a,b,d,e,f = coefficients
    candidates = [(0.,0.),(1.,0.),(0.,1.)]
    for start,direction in (((0.,0.),(1.,0.)),((0.,0.),(0.,1.)),((1.,0.),(-1.,1.))):
        x,y = start; u,v = direction
        linear = a*u+b*v+2*d*x*u+e*(x*v+y*u)+2*f*y*v
        square = d*u*u+e*u*v+f*v*v
        if square>0:
            t = -linear/(2*square)
            if 0<t<1:
                candidates.append((x+t*u,y+t*v))
    hessian = np.array(((2*d,e),(e,2*f)))
    eigenvalues = np.linalg.eigvalsh(hessian)
    if eigenvalues[0]>0:
        if eigenvalues[0] <= 128*np.finfo(float).eps*eigenvalues[-1]:
            raise ValueError('quadratic minimum UNVERIFIED: ill-conditioned interior stationary point')
        stationary = np.linalg.solve(hessian,-np.array((a,b)))
        if np.all(stationary>0) and stationary.sum()<1:
            candidates.append(tuple(stationary))
    values = [c+a*x+b*y+d*x*x+e*x*y+f*y*y for x,y in candidates]
    index = int(np.argmin(values))
    return float(values[index]),candidates[index]


def _product_linear(a,b):
    return np.array((a[0]*b[0],a[0]*b[1]+a[1]*b[0],a[0]*b[2]+a[2]*b[0],
                     a[1]*b[1],a[1]*b[2]+a[2]*b[1],a[2]*b[2]))


@dataclass(frozen=True)
class QuadraticTriangle:
    points_rz_m: object

    def __post_init__(self):
        raw = np.asarray(self.points_rz_m)
        if raw.dtype.kind not in 'iuf' or raw.shape!=(6,2) or not np.isfinite(raw).all():
            raise ValueError('quadratic geometry requires six finite (r,z) nodes')
        points = raw.astype(float).copy()
        scale = float(np.max(np.ptp(points,axis=0)))
        if not np.isfinite(scale) or scale<=0:
            raise ValueError('quadratic geometry has zero or invalid scale')
        coefficients = np.linalg.solve(_VANDERMONDE,(points-points[0])/scale)
        dx = np.array((coefficients[1],2*coefficients[3],coefficients[4]))
        dy = np.array((coefficients[2],coefficients[4],2*coefficients[5]))
        determinant = _product_linear(dx[:,0],dy[:,1])-_product_linear(dx[:,1],dy[:,0])
        padding = 512*np.finfo(float).eps*max(1.,np.sum(abs(determinant)))
        c,a,b,d,e,f = determinant
        # Convex-hull bound in the quadratic Bernstein basis also handles
        # nearly affine maps with roundoff-sized, ill-conditioned Hessians.
        minimum = min(c,c+a+d,c+b+f,c+a/2,c+b/2,c+(a+b+e)/2)
        location = None
        if minimum<=padding:
            minimum,location = quadratic_minimum(determinant)
        if minimum<=padding:
            raise ValueError('quadratic Jacobian nonpositive or UNVERIFIED over reference triangle')
        if not np.isfinite(scale*scale) or scale*scale==0:
            raise ValueError('quadratic geometry determinant exceeds floating-point range')
        points.setflags(write=False)
        object.__setattr__(self,'points_rz_m',points)
        object.__setattr__(self,'determinant_lower_bound_m2',(minimum-padding)*scale*scale)
        object.__setattr__(self,'minimum_location',location)

    def evaluate(self, reference_points):
        raw = np.asarray(reference_points)
        if raw.dtype.kind not in 'iuf' or raw.ndim!=2 or raw.shape[1]!=2 or not len(raw):
            raise ValueError('reference points require nonempty N by 2 coordinates')
        points = raw.astype(float)
        if not np.isfinite(points).all() or np.any(points<0) or np.any(points.sum(axis=1)>1):
            raise ValueError('reference points must lie in the closed unit triangle')
        values,gradients = [],[]
        for x,y in points:
            value,gradient = basis_p2(np.array((1-x-y,x,y)),_REFERENCE_GRAD)
            values.append(value); gradients.append(gradient)
        values,gradients = np.asarray(values),np.asarray(gradients)
        # J[physical coordinate, reference coordinate].
        jacobian = np.einsum('ia,qib->qab',self.points_rz_m-self.points_rz_m[0],gradients)
        determinant = np.linalg.det(jacobian)
        physical_gradients = np.einsum('qia,qab->qib',gradients,np.linalg.inv(jacobian))
        return dict(points_rz_m=values@self.points_rz_m,jacobian=jacobian,
                    determinant_m2=determinant,basis_values=values,basis_gradients=physical_gradients)

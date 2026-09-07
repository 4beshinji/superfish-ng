# SPDX-License-Identifier: Apache-2.0
"""Physical-coordinate probes for quadratic maps with conservative outside checks."""
import numpy as np
from .quadratic_geometry import QuadraticTriangle,_VANDERMONDE
from .curved_solution import CurvedSolution


class QuadraticLocator:
    def __init__(self,mapping):
        if not isinstance(mapping,QuadraticTriangle):
            raise ValueError('inverse map requires a validated QuadraticTriangle')
        self.origin=mapping.points_rz_m[0]
        self.scale=float(np.max(np.ptp(mapping.points_rz_m,axis=0)))
        self.coefficients=np.linalg.solve(_VANDERMONDE,(mapping.points_rz_m-self.origin)/self.scale)
        self.padding=512*np.finfo(float).eps
        self.root=np.array(((0.,0.),(1.,0.),(0.,1.)))
        self.lower,self.upper=self._bounds(self.root)

    def _values(self,points):
        x,y=np.asarray(points).T
        return np.column_stack((np.ones_like(x),x,y,x*x,x*y,y*y))@self.coefficients

    def _bounds(self,triangle):
        samples=np.vstack((triangle,(triangle+triangle[[1,2,0]])/2))
        values=self._values(samples)
        controls=np.vstack((values[:3],2*values[3:]-.5*values[[0,1,2]]-.5*values[[1,2,0]]))
        return controls.min(axis=0)-self.padding,controls.max(axis=0)+self.padding

    def _newton(self,target,start,iterations):
        point=np.asarray(start,dtype=float).copy()
        c=self.coefficients
        for _ in range(iterations):
            residual=self._values([point])[0]-target
            norm=float(np.linalg.norm(residual))
            if norm<=self.padding:
                bary=np.array((1-point.sum(),*point))
                if bary.min()>=-self.padding:
                    bary=np.maximum(bary,0.)
                    bary/=bary.sum()
                    result=bary[1:]
                    # Preserve the public closed reference triangle without extrapolation.
                    if result.sum()>1:
                        result[1]=1-result[0]
                    if np.linalg.norm(self._values([result])[0]-target)<=2*self.padding:
                        return result
                return None
            x,y=point
            jacobian=np.column_stack((c[1]+2*x*c[3]+y*c[4],c[2]+x*c[4]+2*y*c[5]))
            try:
                delta=np.linalg.solve(jacobian,residual)
            except np.linalg.LinAlgError:
                return None
            for factor in (1.,.5,.25,.125,.0625,.03125,.015625,.0078125):
                candidate=point-factor*delta
                if np.isfinite(candidate).all() and np.linalg.norm(self._values([candidate])[0]-target)<norm:
                    point=candidate
                    break
            else:
                return None
        return None

    def inverse(self,physical_point,*,max_iterations=30,max_boxes=1024):
        raw=np.asarray(physical_point)
        if raw.dtype.kind not in 'iuf' or raw.shape!=(2,) or not np.isfinite(raw).all():
            raise ValueError('inverse point must be two finite physical coordinates')
        if type(max_iterations) is not int or max_iterations<1 or type(max_boxes) is not int or max_boxes<1:
            raise ValueError('inverse limits must be positive integers')
        target=(raw-self.origin)/self.scale
        if np.any(target<self.lower) or np.any(target>self.upper):
            return None
        # Affine corners are only an initial guess, never an inclusion test.
        corners=self._values(self.root)
        try:
            initial=np.linalg.solve((corners[1:]-corners[0]).T,target-corners[0])
        except np.linalg.LinAlgError:
            initial=np.array((1/3,1/3))
        result=self._newton(target,initial,max_iterations)
        if result is not None:
            return result
        pending=[self.root]
        checked=0
        while pending:
            if checked>=max_boxes:
                raise ValueError('curved inverse UNVERIFIED: subdivision budget exhausted')
            triangle=pending.pop();checked+=1
            low,high=self._bounds(triangle)
            if np.any(target<low) or np.any(target>high):
                continue
            result=self._newton(target,triangle.mean(axis=0),max_iterations)
            if result is not None:
                return result
            if np.max(high-low)<=4*self.padding:
                raise ValueError('curved inverse UNVERIFIED: boundary or roundoff resolution')
            a,b,c=triangle
            ab,bc,ca=(a+b)/2,(b+c)/2,(c+a)/2
            pending.extend(np.array(t) for t in ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)))
        return None


class CurvedFieldSampler:
    def __init__(self,solution):
        if not isinstance(solution,CurvedSolution):
            raise ValueError('curved sampler requires a CurvedSolution')
        self.solution=solution
        self.locators=[QuadraticLocator(m) for m in solution.space.geometry.local_maps]
        self.lower=np.array([l.origin+l.scale*l.lower for l in self.locators])
        self.upper=np.array([l.origin+l.scale*l.upper for l in self.locators])

    def evaluate(self,points_rz_m,mode=0,outside='raise',*,max_iterations=30,max_boxes=1024):
        raw=np.asarray(points_rz_m)
        if raw.dtype.kind not in 'iuf' or raw.ndim!=2 or raw.shape[1]!=2 or not len(raw) or not np.isfinite(raw).all():
            raise ValueError('curved probes require a nonempty finite N by 2 (r,z) array')
        if type(mode) is not int or not 0<=mode<len(self.solution.frequencies_hz):
            raise ValueError('mode must be a valid zero-based integer')
        if outside not in ('raise','nan'):
            raise ValueError('outside must be raise or nan')
        if type(max_iterations) is not int or max_iterations<1 or type(max_boxes) is not int or max_boxes<1:
            raise ValueError('inverse limits must be positive integers')
        points=raw.astype(float)
        fields={key:np.full(len(points),np.nan) for key in
                ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m')}
        inside=np.zeros(len(points),dtype=bool)
        for index,point in enumerate(points):
            candidates=np.flatnonzero(np.all(point>=self.lower,axis=1)&np.all(point<=self.upper,axis=1))
            unresolved=[]
            for cell in candidates:
                try:
                    reference=self.locators[cell].inverse(point,max_iterations=max_iterations,max_boxes=max_boxes)
                except ValueError as exc:
                    unresolved.append(str(exc));continue
                if reference is None:
                    continue
                result=self.solution.fields_in_cell(int(cell),[reference],mode)
                for key in fields:
                    fields[key][index]=result[key][0]
                inside[index]=True
                break
            if not inside[index]:
                if unresolved:
                    raise ValueError(f'curved probe {index} UNVERIFIED: '+unresolved[0])
                if outside=='raise':
                    raise ValueError(f'curved probe {index} lies outside the mapped mesh')
        fields['inside']=inside
        return fields

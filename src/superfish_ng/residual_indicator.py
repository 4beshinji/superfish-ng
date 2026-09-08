# SPDX-License-Identifier: Apache-2.0
"""Weighted strong/flux residual indicators for affine and curved TM fields.

These are refinement priorities, not certified bounds on any physical error.
See docs/RESIDUAL_INDICATOR.md for the axis weight and boundary derivation.
"""
import math
import numpy as np
from .fem import triangle_quadrature
from .high_order import basis_p2, quadratic_space
from .mesh import element_geometry
from .mesh_input import mesh_from_dict, mesh_to_dict


def _components(mesh, order, u, eigenvalue):
    """Return unnormalized squared volume, interior and natural-wall parts."""
    p,det,grad=element_geometry(mesh)
    space=quadratic_space(mesh) if order==2 else None
    dofs=space.cell_dofs if space else mesh.triangles
    coefficients=u[dofs]
    lap_basis=np.concatenate((4*np.sum(grad*grad,axis=2),
        np.stack([8*np.sum(grad[:,i]*grad[:,j],axis=1) for i,j in ((0,1),(1,2),(2,0))],axis=1)),axis=1) if order==2 else np.zeros_like(coefficients)
    lap=np.sum(coefficients*lap_basis,axis=1)
    h2=np.max(np.sum((p[:,[1,2,0]]-p)**2,axis=2),axis=1)
    volume=np.zeros(len(p));interior=np.zeros(len(p));boundary=np.zeros(len(p))
    for n,w in triangle_quadrature(order=5):
        values,derivative=basis_p2(n,grad) if space else (n,grad)
        r=p[:,:,0]@n
        value=coefficients@values
        dr=np.sum(coefficients*derivative[:,:,0],axis=1)
        residual=r*lap+3*dr+eigenvalue*r*value
        volume+=h2*w*det*r*residual**2
    owners={}
    for cell,triangle in enumerate(mesh.triangles):
        for i,j in ((0,1),(1,2),(2,0)):
            key=tuple(sorted((int(triangle[i]),int(triangle[j]))))
            owners.setdefault(key,[]).append((cell,i,j))
    tags={tuple(sorted(edge)):tag for edge,tag in zip(mesh.boundary_edges,mesh.boundary_tags)}
    x,w=np.polynomial.legendre.leggauss(4);x=(x+1)/2;w=w/2
    for edge,adjacent in owners.items():
        tag=tags.get(edge)
        if tag in ('axis','magnetic_symmetry'):continue
        a,b=mesh.points[list(edge)];length=float(np.linalg.norm(b-a))
        flux=np.zeros(len(x))
        for cell,i,j in adjacent:
            tangent=p[cell,j]-p[cell,i]
            normal=np.array([tangent[1],-tangent[0]])/length
            for q,t in enumerate(x):
                n=np.zeros(3)
                n[i],n[j]=(1-t,t) if mesh.triangles[cell,i]==edge[0] else (t,1-t)
                values,derivative=basis_p2(n,grad[cell]) if space else (n,grad[cell])
                r=(1-t)*a[0]+t*b[0]
                flux[q]+=r*(coefficients[cell]@derivative@normal)
                if len(adjacent)==1:flux[q]+=2*normal[0]*(coefficients[cell]@values)
        radii=(1-x)*a[0]+x*b[0]
        contribution=length**2*float(w@(radii*flux**2))
        target=interior if len(adjacent)==2 else boundary
        for cell,_,_ in adjacent:target[cell]+=contribution/len(adjacent)
    return volume,interior,boundary


def residual_indicator(case, solution, *, mode=0):
    """Estimate a zero-based mode's local residual on its validated fixed mesh.

    Mode rank is not a persistent mode identity. Track modes across solves before
    using this function in a multi-mode adaptive workflow.
    """
    if case.geometry_order == 2:
        from .curved_residual_indicator import curved_residual_indicator
        return curved_residual_indicator(case, solution, mode=mode)
    if case.geometry_order!=1 or solution.element_order!=case.element_order:
        raise ValueError('residual indicator requires matching straight P1/P2 case and solution')
    if type(mode) is not int or not 0<=mode<len(solution.eigenvalues):
        raise ValueError('mode must be an available zero-based integer index')
    mesh=mesh_from_dict(case,mesh_to_dict(solution.mesh))
    space=quadratic_space(mesh) if case.element_order==2 else None
    count=len(space.dof_points) if space else len(mesh.points)
    coefficients=np.asarray(solution.u)
    if coefficients.shape!=(count,len(solution.eigenvalues)) or np.iscomplexobj(coefficients) or not np.all(np.isfinite(coefficients)):
        raise ValueError('solution coefficients must be finite real values in the matching FEM space')
    u=coefficients[:,mode].astype(float,copy=True);amplitude=float(np.max(np.abs(u)))
    eigenvalue=float(solution.eigenvalues[mode])
    if not amplitude>0 or not math.isfinite(eigenvalue) or eigenvalue<=0:
        raise ValueError('residual indicator requires a nonzero field and positive finite eigenvalue')
    boundary_dofs=space.boundary_dofs if space else mesh.boundary_edges
    if np.any(u[np.unique(boundary_dofs[mesh.boundary_tags=='magnetic_symmetry'])]!=0):
        raise ValueError('magnetic_symmetry coefficients must satisfy the essential zero constraint')
    # Normalize before squaring so arbitrary phasor amplitudes do not overflow.
    u/=amplitude
    energy=float(u@(solution.stiffness@u))
    if not math.isfinite(energy) or energy<=0:
        raise ValueError('field energy must be positive and finite')
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        try:parts=[a/energy for a in _components(mesh,case.element_order,u,eigenvalue)]
        except FloatingPointError as exc:raise ValueError('residual indicator exceeds supported numeric range') from exc
    cells=sum(parts)
    if not np.all(np.isfinite(cells)) or np.any(cells<0):
        raise ValueError('residual indicator must be finite and nonnegative')
    try:total=math.fsum(cells)
    except OverflowError as exc:raise ValueError('residual indicator sum exceeds supported numeric range') from exc
    if not math.isfinite(total):raise ValueError('residual indicator sum exceeds supported numeric range')
    return dict(schema_version=1,mode_index=mode,element_order=case.element_order,
        relative_indicator=math.sqrt(total),cell_relative_squared=cells.tolist(),
        volume_relative_squared=parts[0].tolist(),interior_relative_squared=parts[1].tolist(),
        boundary_relative_squared=parts[2].tolist(),normalization='squared contributions divided by u.T K u',
        physical_error_bound=None,scope='fixed straight geometry; residual priority, not frequency/RF/peak certification')


def mark_bulk(cell_squared, fraction):
    """Smallest descending prefix covering fraction of total squared indicator.

    Equal priorities use increasing cell index. Zeros are never selected.
    """
    if isinstance(fraction,(bool,np.bool_)) or not isinstance(fraction,(int,float)) or not math.isfinite(fraction) or not 0<fraction<=1:
        raise ValueError('bulk fraction must be finite and in (0, 1]')
    if (not isinstance(cell_squared,(list,tuple,np.ndarray))
            or isinstance(cell_squared,np.ndarray) and cell_squared.ndim!=1
            or not len(cell_squared)):
        raise ValueError('cell squared indicators must be a nonempty one-dimensional sequence')
    if any(isinstance(v,(bool,np.bool_)) or not isinstance(v,(int,float,np.integer,np.floating)) for v in cell_squared):
        raise ValueError('cell squared indicators must be real numbers, not booleans')
    values=np.asarray(cell_squared,dtype=float)
    if values.ndim!=1 or not np.all(np.isfinite(values)) or np.any(values<0):
        raise ValueError('cell squared indicators must be finite and nonnegative')
    largest=float(np.max(values))
    if largest==0:return []
    indices=sorted(np.flatnonzero(values>0).tolist(),key=lambda i:(-values[i],i))
    if fraction==1:return indices
    values=values/largest
    target=fraction*math.fsum(values);prefix=[];total=0.;correction=0.
    for index in indices:
        prefix.append(index)
        y=float(values[index])-correction;t=total+y;correction=(t-total)-y;total=t
        if total>=target:return prefix
    return prefix

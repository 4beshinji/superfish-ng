# SPDX-License-Identifier: Apache-2.0
"""Synthetic planar H(B) fields from independent inverse-curve integration."""
import numpy as np
from scripts.planar_electrostatic_reference import rectangle
from scripts.validate_bh_curve import decimal_reference
from superfish_ng.bh_curve import MonotoneBHCurve
from superfish_ng.magnetic_materials import MagneticRegion
from superfish_ng.planar_bh_materials import PlanarBHPartition
from superfish_ng.planar_bh import PlanarBHCase
from superfish_ng.magnetostatic_boundary import MagnetostaticBoundary


def _curve(index,h_scale=1.,linear=False):
    b=np.array([0.,.25,.5,1.,4.]);h=([400*b,1200*b] if linear else [np.array([0.,100.,250.,1500.,100000.]),np.array([0.,80.,500.,1800.,50000.])])[index]
    return MonotoneBHCurve(f'm{index}',tuple(b),tuple(h*h_scale),'Synthetic table for independent static validation; no measured or legacy material')


def _inverse(curve,h):
    h=np.asarray(h);magnitude=abs(h)
    if np.any(magnitude>curve.h_a_per_m[-1]):raise ValueError('independent reference H is outside the declared table')
    return np.sign(h)*np.interp(magnitude,curve.h_a_per_m,curve.b_t)


def _intensity(curve,b):
    b=np.asarray(b)
    if np.any(abs(b)>curve.b_t[-1]):raise ValueError('independent reference B is outside the declared table')
    return np.sign(b)*np.interp(abs(b),curve.b_t,curve.h_a_per_m)


def _coenergy_of_h(curve,h):
    h=np.asarray(h);b=_inverse(curve,h)
    return np.array([decimal_reference(curve,float(abs(v)))[2] for v in b.flat]).reshape(h.shape)


def _partition(n,scale,angle,shift,layered,h_scale,linear):
    rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]]);mesh,local,width,height,_,_=rectangle(n,scale,rotation=rotation,shift=shift)
    labels=(local[mesh.triangles][:,:,1].mean(axis=1)>=height/2).astype(int) if layered else np.zeros(len(mesh.triangles),dtype=int)
    materials=[_curve(i,h_scale,linear) for i in range(labels.max()+1)];regions=[MagneticRegion(f'r{i}',f'm{i}',np.flatnonzero(labels==i).tolist()) for i in range(len(materials))]
    return PlanarBHPartition(mesh,materials,regions),local,width,height,rotation,np.asarray(shift)


def _boundaries(p,local,width,height,potential,intensity,boundary):
    assert boundary in ('fixed','tangential');groups=dict(bottom=[],top=[],left=[],right=[])
    for i,edge in enumerate(p.mesh.boundary_edges):
        x,y=local[edge].mean(axis=0);groups['bottom' if y==0. else 'top' if y==height else 'left' if x==0. else 'right'].append(i)
    result=[MagnetostaticBoundary('bottom','fixed_az',groups['bottom'],float(potential(0.)))]
    result.append(MagnetostaticBoundary('top','fixed_az',groups['top'],float(potential(height))) if boundary=='fixed' else MagnetostaticBoundary('top','tangential_h',groups['top'],-float(intensity(height))))
    result += [MagnetostaticBoundary(name,'tangential_h',groups[name],0.) for name in ('left','right')]
    return result


def _reference(case,potential,bfield,hfield,potentials,width,height,rotation,shift,source=0.):
    def fields(points):
        x,y=((np.asarray(points)-shift)@rotation).T;b=np.asarray(bfield(y));h=np.asarray(hfield(y))
        return np.asarray(potential(y)),np.column_stack((b,0*y))@rotation.T,np.column_stack((h,0*y))@rotation.T
    difference=float(potential(height)-potential(0.));reaction=dict(bottom=-width*float(hfield(0.)))
    if next(b for b in case.boundaries if b.id=='top').kind=='fixed_az':reaction['top']=width*float(hfield(height))
    return case,dict(fields=fields,potentials=potentials,source_current_a=source,fixed_reaction_a=reaction,
        boundary_flux_wb_per_m=dict(bottom=0.,top=0.,left=-difference,right=difference),
        field_scale=max(abs(float(bfield(0.))),abs(float(bfield(height)))),intensity_scale=max(abs(float(hfield(0.))),abs(float(hfield(height)))),
        potential_scale=max(abs(float(bfield(0.))),abs(float(bfield(height))))*height,width=width,height=height,rotation=rotation,shift=shift,
        potential_y=potential,b_y=bfield,h_y=hfield)


def uniform_field(n=4,scale=1.,h_scale=1.,b_t=.75,boundary='tangential',offset=0.,angle=0.,shift=(0.,0.),linear=False):
    p,local,width,height,q,shift=_partition(n,scale,angle,shift,False,h_scale,linear);h=float(_intensity(p.materials[0],b_t));potential=lambda y:offset+b_t*np.asarray(y)
    bfield=lambda y:np.zeros_like(np.asarray(y),dtype=float)+b_t;hfield=lambda y:np.zeros_like(np.asarray(y),dtype=float)+h
    case=PlanarBHCase(p,dict(r0=0.),_boundaries(p,local,width,height,potential,hfield,boundary),name='synthetic-uniform-nonlinear-BH')
    _,w,co,_,_=decimal_reference(p.materials[0],abs(b_t));potentials=dict(energy_j_per_m=width*height*w,coenergy_j_per_m=width*height*co)
    return _reference(case,potential,bfield,hfield,potentials,width,height,q,shift)


def layered_field(n=4,scale=1.,h_scale=1.,amplitude=1.,boundary='tangential',offset=0.,angle=0.,shift=(0.,0.),linear=False):
    p,local,width,height,q,shift=_partition(n,scale,angle,shift,True,h_scale,linear);h=875*amplitude*h_scale;b=np.array([float(_inverse(m,h)) for m in p.materials]);cut=height/2
    potential=lambda y:offset+b[0]*np.minimum(np.asarray(y),cut)+b[1]*np.maximum(np.asarray(y)-cut,0.)
    bfield=lambda y:np.where(np.asarray(y)<cut,b[0],b[1]);hfield=lambda y:np.zeros_like(np.asarray(y),dtype=float)+h
    case=PlanarBHCase(p,dict(r0=0.,r1=0.),_boundaries(p,local,width,height,potential,hfield,boundary),name='synthetic-layered-nonlinear-BH')
    w=co=0.
    for material,value in zip(p.materials,b):
        _,u,v,_,_=decimal_reference(material,abs(float(value)));w+=width*height/2*u;co+=width*height/2*v
    return _reference(case,potential,bfield,hfield,dict(energy_j_per_m=w,coenergy_j_per_m=co),width,height,q,shift)


def current_slab(n=4,scale=1.,h_scale=1.,amplitude=1.,boundary='tangential',offset=0.,angle=0.,shift=(0.,0.),linear=False):
    p,local,width,height,q,shift=_partition(n,scale,angle,shift,False,h_scale,linear);m=p.materials[0];j=20000*amplitude*h_scale/scale;top=125*amplitude*h_scale;bottom=top+j*height
    hfield=lambda y:bottom-j*np.asarray(y);bfield=lambda y:_inverse(m,hfield(y))
    # Coenergy is an even function of signed H; its H derivative is signed B.
    potential=lambda y:offset+(_coenergy_of_h(m,bottom)-_coenergy_of_h(m,hfield(y)))/j
    case=PlanarBHCase(p,dict(r0=j),_boundaries(p,local,width,height,potential,hfield,boundary),name='synthetic-current-nonlinear-BH')
    cuts=[0.,height]
    for value in m.h_a_per_m[1:-1]:
        for sign in (-1.,1.):
            y=(bottom-sign*value)/j
            if 0.<y<height:cuts.append(float(y))
    cuts=sorted(cuts);nodes,weights=np.polynomial.legendre.leggauss(3);energy=coenergy=integral_relative_az=0.
    for a,b in zip(cuts[:-1],cuts[1:]):
        y=(a+b)/2+(b-a)/2*nodes
        integral_relative_az+=width*(b-a)/2*float(weights@(potential(y)-offset))
        for value,weight in zip(bfield(y),weights):
            _,u,v,_,_=decimal_reference(m,abs(float(value)));energy+=width*(b-a)/2*weight*u;coenergy+=width*(b-a)/2*weight*v
    case,reference=_reference(case,potential,bfield,hfield,dict(energy_j_per_m=energy,coenergy_j_per_m=coenergy),width,height,q,shift,j*width*height)
    boundary_work=top*width*float(potential(height)-offset) if boundary=='tangential' else 0.
    reference.update(current_density=j,boundary=boundary,material=m,
        relative_objective_j_per_m=energy-j*integral_relative_az-boundary_work)
    return case,reference


def field_l2_errors(solution,reference):
    """Compare original FEM fields with the independent continuum fields above."""
    p=solution.case.partition;vertices=p.mesh.points_xy_m[p.mesh.triangles];delta=vertices[:,1:]-vertices[:,0,None,:];det=delta[:,0,0]*delta[:,1,1]-delta[:,0,1]*delta[:,1,0]
    cells=np.arange(len(vertices));nodes,weights=np.polynomial.legendre.leggauss(4);nodes=(nodes+1)/2;weights=weights/2;numerator=np.zeros(3);denominator=np.zeros(3);area=0.
    for i,x in enumerate(nodes):
        for j,t in enumerate(nodes):
            y=t*(1-x);bary=np.array([1-x-y,x,y]);points=np.einsum('i,tij->tj',bary,vertices);measure=weights[i]*weights[j]*(1-x)*det;area+=float(measure.sum())
            f=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)));az,b,h=reference['fields'](points)
            actual=[np.asarray(f['Az_Wb_per_m'])[:,None],np.column_stack((f['Bx_T'],f['By_T'])),np.column_stack((f['Hx_A_per_m'],f['Hy_A_per_m']))]
            expected=[az[:,None],b,h]
            for k,(a,e) in enumerate(zip(actual,expected)):
                numerator[k]+=float(measure@np.sum((a-e)**2,axis=1));denominator[k]+=float(measure@np.sum(e**2,axis=1))
    denominator[0]=area*reference['potential_scale']**2
    return np.sqrt(numerator/np.where(denominator,denominator,1.)).tolist()


def independent_current_bvp(case,reference):
    """Separate 1D collocation solve of A'=B(H), H'=-J; no FEM assembly."""
    from scipy.integrate import solve_bvp
    height=reference['height'];material=case.partition.materials[0];j=case.current_density_z_a_per_m2['r0'];bottom=next(b for b in case.boundaries if b.id=='bottom');top=next(b for b in case.boundaries if b.id=='top')
    hscale=max(abs(j*height),abs(top.value) if top.kind=='tangential_h' else 0.,material.h_a_per_m[1]);ascale=height*material.b_t[-1]
    x=np.linspace(0.,1.,9);initial=np.zeros((2,len(x)))
    if top.kind=='fixed_az':initial[0]=x*(top.value-bottom.value)/ascale
    else:initial[1]=-top.value/hscale
    def ode(x,y):return np.vstack((height/ascale*_inverse(material,hscale*y[1]),np.full(len(x),-height*j/hscale)))
    def boundary(ya,yb):return np.array([ya[0],yb[0]-(top.value-bottom.value)/ascale if top.kind=='fixed_az' else yb[1]+top.value/hscale])
    attempts=[]
    for attempt in range(4):
        answer=solve_bvp(ode,boundary,x,initial,tol=1e-10,bc_tol=1e-11,max_nodes=4096)
        attempts.append(dict(status=answer.status,nodes=len(answer.x),iterations=answer.niter,max_ode_residual=float(max(answer.rms_residuals))))
        if answer.success:break
        # Locate table-slope transitions from this independent BVP iterate.
        # H_y=-J gives their positions once the current iterate's H(0) is
        # known. Restart with those events as mesh boundaries; no FEM field
        # or analytic-reference initial H is used, and tolerances are unchanged.
        h0=hscale*answer.y[1,0];events=[]
        for knot in material.h_a_per_m[1:-1]:
            for sign in (-1.,1.):
                coordinate=(h0-sign*knot)/(j*height)
                if 0.<coordinate<1.:events.append(coordinate)
        x=np.unique(np.r_[np.linspace(0.,1.,9),events]);initial=answer.sol(x)
    assert answer.success and answer.status==0,answer.message
    points=np.linspace(0.,1.,257);state=answer.sol(points);az=bottom.value+ascale*state[0];h=hscale*state[1];b=_inverse(material,h);y=height*points
    exact_az=reference['potential_y'](y);exact_h=reference['h_y'](y);exact_b=reference['b_y'](y)
    errors=[float(np.linalg.norm(az-exact_az)/(np.sqrt(len(y))*reference['potential_scale'])),float(np.linalg.norm(b-exact_b)/np.linalg.norm(exact_b)),float(np.linalg.norm(h-exact_h)/np.linalg.norm(exact_h))]
    assert max(errors)<1e-8 and max(abs(boundary(answer.y[:,0],answer.y[:,-1])))<=1e-11
    return dict(method='SciPy solve_bvp, separate dimensionless 1D collocation A_y=B(H), H_y=-J',nodes=len(answer.x),iterations=answer.niter,max_ode_residual=float(max(answer.rms_residuals)),errors_az_b_h=errors,attempts=attempts,
        interpretation='independent one-dimensional boundary-value comparison only; not a general 2D or axisymmetric external-solver validation')

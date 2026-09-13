# SPDX-License-Identifier: Apache-2.0
"""Independent radial flux integrals and synthetic axis nonlinear equilibria."""
import numpy as np
from scripts.electrostatic_reference import rectangle
from scripts.curved_meridional_reference import fixture
from scripts.planar_bh_reference import _curve
from scripts.validate_bh_curve import decimal_reference
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.axis_bh_materials import AxisBHPartition
from superfish_ng.magnetic_materials import MagneticRegion
from superfish_ng.axis_bh import AxisBHCase
from superfish_ng.axis_magnetostatic_boundary import AxisMagnetostaticBoundary
from superfish_ng.constants import TAU


def _mesh(n,scale,shift,holes=0):
    m=fixture(True,holes,n=max(1,n//2),scale=scale,shear=0.)[0]['base_mesh'] if holes else rectangle(True,n,2*n,scale)[0]
    t=np.array([0.,shift]);return AxisConnectedMesh(m.outer_rz_m+t,[h+t for h in m.holes_rz_m],m.points_rz_m+t,m.triangles)


def _inverse(curve,h):
    values=np.asarray(h,dtype=float)
    if np.any(abs(values)>curve.h_a_per_m[-1]):raise ValueError('independent H query outside the declared table')
    return np.sign(values)*np.interp(abs(values),curve.h_a_per_m,curve.b_t)


def _intensity(curve,b):
    values=np.asarray(b,dtype=float)
    if np.any(abs(values)>curve.b_t[-1]):raise ValueError('independent B query outside the declared table')
    return np.sign(values)*np.interp(abs(values),curve.b_t,curve.h_a_per_m)


def _partition(mesh,curves,labels):
    return AxisBHPartition(mesh,curves,[MagneticRegion(f'r{i}',m.id,np.flatnonzero(labels==i).tolist()) for i,m in enumerate(curves)])


def _boundaries(mesh,fields,outer_a):
    radius=float(mesh.outer_rz_m[:,0].max());axis=[];outer=[];natural={}
    for i,edge in enumerate(mesh.boundary_edges):
        v,w=mesh.points_rz_m[edge];mid=(v+w)/2;tangent=(w-v)/np.linalg.norm(w-v)
        if mid[0]==0.:axis.append(i)
        elif mid[0]==radius and outer_a is not None:outer.append(i)
        else:
            h=fields([mid])[3][0];value=float(h@tangent);natural.setdefault((value,tuple(tangent)),[]).append(i)
    result=[AxisMagnetostaticBoundary('axis','axis_regularity',axis)]
    if outer:result.append(AxisMagnetostaticBoundary('outer','fixed_aphi_over_r',outer,outer_a))
    result.extend(AxisMagnetostaticBoundary(f'natural-{i}','tangential_h',edges,value) for i,((value,_),edges) in enumerate(natural.items()))
    return result


def _flux_and_reaction(case,flux_function,fields):
    mesh=case.partition.mesh;flux={b.id:0. for b in case.boundaries};reaction={b.id:0. for b in case.boundaries if b.kind=='fixed_aphi_over_r'}
    for boundary in case.boundaries:
        for edge in boundary.edge_indices:
            v,w=mesh.points_rz_m[mesh.boundary_edges[edge]]
            if v[1]==w[1]:flux[boundary.id]-=TAU*float(flux_function(w[0])-flux_function(v[0]))
            elif v[0]==w[0]:
                if boundary.kind=='fixed_aphi_over_r':reaction[boundary.id]+=TAU*v[0]**2*float(fields([(v+w)/2])[3][0,1])*(w[1]-v[1])
            else:raise ValueError('independent analytic boundary fixture requires rectangular edges')
    return flux,reaction


def _reference(case,fields,flux_function,potentials,current,model):
    flux,reaction=_flux_and_reaction(case,flux_function,fields);mesh=case.partition.mesh;radius=float(mesh.outer_rz_m[:,0].max());samples=fields(np.column_stack((np.tile(np.linspace(0.,radius,257),2),np.repeat([mesh.outer_rz_m[:,1].min(),mesh.outer_rz_m[:,1].max()],257))))
    scales=[float(np.max(abs(samples[0]))),float(np.max(abs(samples[1]))),float(np.max(np.linalg.norm(samples[2],axis=1))),float(np.max(np.linalg.norm(samples[3],axis=1)))]
    return dict(fields=fields,potentials=potentials,source_current_a=current,boundary_flux_wb=flux,fixed_reaction_a_m2=reaction,field_scales=scales,model=dict(model,radius_m=radius,length_m=float(np.ptp(mesh.outer_rz_m[:,1]))))


def uniform_field(n=2,scale=1.,h_scale=1.,amplitude=1.,boundary='tangential',shift=0.,holes=0,axial_layers=False,quadrature_order=8):
    mesh=_mesh(n,scale,shift,holes);cut=shift+scale/16;labels=(mesh.points_rz_m[mesh.triangles][:,:,1].mean(axis=1)>=cut).astype(int) if axial_layers else np.zeros(len(mesh.triangles),dtype=int)
    curves=[_curve(i,h_scale,False) for i in range(int(labels.max())+1)];p=_partition(mesh,curves,labels);bz=.75*amplitude
    def fields(points):
        r,z=np.asarray(points).T;owners=(z>=cut).astype(int) if axial_layers else np.zeros(len(r),dtype=int);h=np.array([float(_intensity(curves[i],bz)) for i in owners]);a=np.full(len(r),bz/2)
        return a,r*a,np.column_stack((0*r,0*r+bz)),np.column_stack((0*r,h))
    case=AxisBHCase(p,{r.id:0. for r in p.regions},_boundaries(mesh,fields,bz/2 if boundary=='fixed' else None),quadrature_order=quadrature_order)
    potentials=np.zeros(2)
    for i,m in enumerate(curves):
        volume=0.
        for index,triangle in enumerate(mesh.triangles):
            if labels[index]!=i:continue
            v=mesh.points_rz_m[triangle];volume+=TAU*np.linalg.det((v[1:]-v[0]).T)*float(v[:,0].mean())/2
        potentials+=volume*np.array(decimal_reference(m,abs(bz))[1:3])
    return case,_reference(case,fields,lambda r:bz*np.asarray(r)**2/2,dict(energy_j=float(potentials[0]),coenergy_j=float(potentials[1])),0.,dict(kind='uniform',axial_layers=axial_layers,holes=holes))


def _integrate_radial(function,left,right,breaks):
    nodes,weights=np.polynomial.legendre.leggauss(3);edges=[left,*sorted(v for v in breaks if left<v<right),right];result=0.
    for a,b in zip(edges[:-1],edges[1:]):
        points=(a+b)/2+(b-a)*nodes/2;result+=float(weights@function(points))*(b-a)/2
    return result


def current_cylinder(n=4,scale=1.,h_scale=1.,amplitude=1.,boundary='tangential',shift=0.,single_interval=False,linear=False,quadrature_order=12):
    mesh=_mesh(n,scale,shift);radius=float(mesh.outer_rz_m[:,0].max());length=float(np.ptp(mesh.outer_rz_m[:,1]));curve=_curve(0,h_scale,linear)
    inner,outer=(1250.,500.) if single_interval else (1400.,50.);inner*=amplitude*h_scale;outer*=amplitude*h_scale;current=(inner-outer)/radius
    breaks=sorted((inner-h)/current for h in [*curve.h_a_per_m,*(-np.array(curve.h_a_per_m))] if 0<(inner-h)/current<radius)
    def flux_scalar(r):return _integrate_radial(lambda x:x*_inverse(curve,inner-current*x),0.,float(r),breaks)
    def flux(r):
        values=np.asarray(r);unique,indices=np.unique(values,return_inverse=True);return np.array([flux_scalar(v) for v in unique])[indices].reshape(values.shape)
    def fields(points):
        r,z=np.asarray(points).T;h=inner-current*r;b=_inverse(curve,h);f=flux(r);a=np.full(len(r),float(_inverse(curve,inner))/2);positive=r>0;a[positive]=f[positive]/r[positive]**2
        return a,r*a,np.column_stack((0*r,b)),np.column_stack((0*r,h))
    p=_partition(mesh,[curve],np.zeros(len(mesh.triangles),dtype=int));outer_a=float(flux(radius)/radius**2)
    case=AxisBHCase(p,dict(r0=current),_boundaries(mesh,fields,outer_a if boundary=='fixed' else None),quadrature_order=quadrature_order)
    potentials=[]
    for component in (1,2):
        potentials.append(TAU*length*_integrate_radial(lambda r:r*np.array([decimal_reference(curve,abs(float(v)))[component] for v in _inverse(curve,inner-current*r)]),0.,radius,breaks))
    return case,_reference(case,fields,flux,dict(energy_j=potentials[0],coenergy_j=potentials[1]),current*radius*length,dict(kind='current',single_interval=single_interval,linear=linear,inner_h_a_per_m=inner,outer_h_a_per_m=outer,breaks_r_m=breaks))


def radial_layers(n=8,scale=1.,h_scale=1.,amplitude=1.,boundary='tangential',shift=0.,quadrature_order=12):
    if n%2:raise ValueError('radial reference requires an even mesh count')
    mesh=_mesh(n,scale,shift);radius=float(mesh.outer_rz_m[:,0].max());cut=radius/2;length=float(np.ptp(mesh.outer_rz_m[:,1]));labels=(mesh.points_rz_m[mesh.triangles][:,:,0].mean(axis=1)>=cut).astype(int)
    curves=[_curve(i,h_scale,False) for i in range(2)];h=875.*amplitude*h_scale;b=np.array([float(_inverse(m,h)) for m in curves]);p=_partition(mesh,curves,labels)
    def flux(r):
        values=np.asarray(r);return (b[0]*np.minimum(values,cut)**2+b[1]*np.maximum(values**2-cut**2,0.))/2
    def fields(points):
        r,z=np.asarray(points).T;owners=(r>=cut).astype(int);f=flux(r);a=np.full(len(r),b[0]/2);positive=r>0;a[positive]=f[positive]/r[positive]**2
        return a,r*a,np.column_stack((0*r,b[owners])),np.column_stack((0*r,0*r+h))
    outer_a=float(flux(radius)/radius**2);case=AxisBHCase(p,dict(r0=0.,r1=0.),_boundaries(mesh,fields,outer_a if boundary=='fixed' else None),quadrature_order=quadrature_order)
    volumes=np.pi*length*np.array([cut**2,radius**2-cut**2]);potentials=sum(v*np.array(decimal_reference(m,abs(float(induction)))[1:3]) for v,m,induction in zip(volumes,curves,b))
    return case,_reference(case,fields,flux,dict(energy_j=float(potentials[0]),coenergy_j=float(potentials[1])),0.,dict(kind='radial_layers',cut_r_m=cut))


def field_l2_errors(solution,reference):
    mesh=solution.case.partition.mesh;vertices=mesh.points_rz_m[mesh.triangles];det=np.linalg.det(np.transpose(vertices[:,1:]-vertices[:,0,None,:],(0,2,1)));cells=np.arange(len(vertices));squares=np.zeros(4);den=np.zeros(4)
    nodes,weights=np.polynomial.legendre.leggauss(6);nodes=(nodes+1)/2;weights=weights/2
    for x,wx in zip(nodes,weights):
        for y,wy in zip(nodes,weights):
            bary=np.array([(1-x)*(1-y),x,(1-x)*y]);points=np.einsum('i,tia->ta',bary,vertices);measure=TAU*points[:,0]*det*wx*wy*(1-x);fields=solution.fields_in_cells(cells,np.broadcast_to(bary,(len(cells),3)))
            actual=[fields['Aphi_over_r_T'],fields['Aphi_Wb_per_m'],np.column_stack((fields['Br_T'],fields['Bz_T'])),np.column_stack((fields['Hr_A_per_m'],fields['Hz_A_per_m']))]
            for i,(a,b) in enumerate(zip(actual,reference['fields'](points))):
                squares[i]+=float(measure@((a-b)**2 if a.ndim==1 else np.sum((a-b)**2,axis=1)));den[i]+=float(measure@(b*b if b.ndim==1 else np.sum(b*b,axis=1)))
    return [float(np.sqrt(a/b)) if b else float(np.sqrt(a)) for a,b in zip(squares,den)]


def independent_current_bvp(case,reference):
    from scipy.integrate import solve_bvp
    model=reference['model'];assert model['kind']=='current';radius=model['radius_m'];current=case.current_density_phi_a_per_m2['r0'];curve=case.partition.materials[0]
    # The state is flux=r^2*a and H. Its ODE is nonsingular at the axis.
    outer=next((b.value for b in case.boundaries if b.kind=='fixed_aphi_over_r'),None)
    outer_h=next((b.value for b in case.boundaries if b.kind=='tangential_h' and np.all(case.partition.mesh.points_rz_m[case.partition.mesh.boundary_edges[list(b.edge_indices)],0]==radius)),None)
    hscale=max(abs(current*radius),abs(outer_h or 0.),curve.h_a_per_m[1]);bscale=curve.b_t[-1]
    def ode(x,y):return np.vstack((x*_inverse(curve,y[1]*hscale)/bscale,np.full_like(x,-current*radius/hscale)))
    def boundary(left,right):return np.array([left[0],right[0]-outer/bscale if outer is not None else right[1]-outer_h/hscale])
    nodes=np.linspace(0.,1.,9);initial=np.zeros((2,len(nodes)))
    if outer is not None:initial[0]=(outer/bscale)*nodes**2
    else:initial[1]=outer_h/hscale
    attempts=[]
    for attempt in range(4):
        answer=solve_bvp(ode,boundary,nodes,initial,tol=1e-10,bc_tol=1e-11,max_nodes=4096)
        attempts.append(dict(status=int(answer.status),nodes=len(answer.x),iterations=int(answer.niter),max_ode_residual=float(max(answer.rms_residuals))))
        if answer.success:break
        h0=float(answer.y[1,0]*hscale);events=[(h0-h)/(current*radius) for h in [*curve.h_a_per_m,*(-np.array(curve.h_a_per_m))] if 0<(h0-h)/(current*radius)<1]
        nodes=np.unique(np.r_[np.linspace(0.,1.,9),events]);initial=answer.sol(nodes)
    if not answer.success:raise ValueError('independent axis BVP did not converge: '+str(attempts))
    x=np.linspace(0.,1.,257);state=answer.sol(x);r=radius*x;h=state[1]*hscale;b=_inverse(curve,h);a=np.full(len(x),float(_inverse(curve,h[0]))/2);positive=x>0;a[positive]=state[0,positive]*bscale/x[positive]**2
    actual=[a,r*a,np.column_stack((0*x,b)),np.column_stack((0*x,h))];expected=reference['fields'](np.column_stack((r,np.full(len(r),case.partition.mesh.outer_rz_m[:,1].min()))));errors=[]
    for aa,bb in zip(actual,expected):errors.append(float(np.linalg.norm(aa-bb)/np.linalg.norm(bb)))
    assert max(errors)<1e-8
    return dict(method='independent nonsingular 1D SciPy collocation of (r^2*a)_r=r*B(H), H_r=-Jphi',nodes=len(answer.x),iterations=int(answer.niter),max_ode_residual=float(max(answer.rms_residuals)),errors_a_aphi_b_h=errors,attempts=attempts,interpretation='one-dimensional boundary-value comparison, not a general 2D independent-solver certification')

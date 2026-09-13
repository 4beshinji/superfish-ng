# SPDX-License-Identifier: Apache-2.0
"""Independent radial flux integrals and synthetic off-axis nonlinear equilibria."""
import numpy as np
from types import SimpleNamespace
from scripts.validate_off_axis_bh_forms import radial_energy_reference
from scripts.electrostatic_reference import rectangle
from scripts.curved_meridional_reference import fixture
from scripts.planar_bh_reference import _curve
from scripts.validate_bh_curve import decimal_reference
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.off_axis_bh_materials import OffAxisBHPartition
from superfish_ng.magnetic_materials import MagneticRegion
from superfish_ng.off_axis_bh import OffAxisBHCase
from superfish_ng.off_axis_magnetostatic_boundary import OffAxisMagnetostaticBoundary
from superfish_ng.constants import TAU


def _mesh(n,scale,shift,holes=0):
    m=fixture(False,holes,n=max(1,n//2),scale=scale,shear=0.)[0]['base_mesh'] if holes else rectangle(False,n,2*n,scale)[0]
    t=np.array([0.,shift]);return MeridionalMesh(m.outer_rz_m+t,[h+t for h in m.holes_rz_m],m.points_rz_m+t,m.triangles)


def _inverse(curve,h):
    values=np.asarray(h,dtype=float)
    if np.any(abs(values)>curve.h_a_per_m[-1]):raise ValueError('independent H query outside the declared table')
    return np.sign(values)*np.interp(abs(values),curve.h_a_per_m,curve.b_t)


def _intensity(curve,b):
    values=np.asarray(b,dtype=float)
    if np.any(abs(values)>curve.b_t[-1]):raise ValueError('independent B query outside the declared table')
    return np.sign(values)*np.interp(abs(values),curve.b_t,curve.h_a_per_m)


def _partition(mesh,curves,labels):
    return OffAxisBHPartition(mesh,curves,[MagneticRegion(f'r{i}',m.id,np.flatnonzero(labels==i).tolist()) for i,m in enumerate(curves)])


def _boundaries(mesh,fields,outer_psi,offset):
    inner=float(mesh.outer_rz_m[:,0].min());outer=float(mesh.outer_rz_m[:,0].max());left=[];right=[];natural={}
    for i,edge in enumerate(mesh.boundary_edges):
        v,w=mesh.points_rz_m[edge];mid=(v+w)/2;tangent=(w-v)/np.linalg.norm(w-v)
        if mid[0]==inner:left.append(i)
        elif mid[0]==outer and outer_psi is not None:right.append(i)
        else:
            value=float(fields([mid])[3][0]@tangent);natural.setdefault((value,tuple(tangent)),[]).append(i)
    result=[OffAxisMagnetostaticBoundary('inner','fixed_psi',left,offset)]
    if right:result.append(OffAxisMagnetostaticBoundary('outer','fixed_psi',right,outer_psi))
    result.extend(OffAxisMagnetostaticBoundary(f'natural-{i}','tangential_h',edges,value) for i,((value,_),edges) in enumerate(natural.items()))
    return result


def _flux_and_reaction(case,fields):
    mesh=case.partition.mesh;flux={b.id:0. for b in case.boundaries};reaction={b.id:0. for b in case.boundaries if b.kind=='fixed_psi'}
    for boundary in case.boundaries:
        for edge in boundary.edge_indices:
            v,w=mesh.points_rz_m[mesh.boundary_edges[edge]];flux[boundary.id]-=TAU*float(np.diff(fields([v,w])[0])[0])
            if boundary.kind=='fixed_psi':
                assert v[0]==w[0];reaction[boundary.id]+=TAU*float(fields([(v+w)/2])[3][0,1])*(w[1]-v[1])
    return flux,reaction


def _reference(case,fields,potentials,current,model,flux=None,reaction=None):
    if flux is None:flux,reaction=_flux_and_reaction(case,fields)
    mesh=case.partition.mesh;inner=float(mesh.outer_rz_m[:,0].min());radius=float(mesh.outer_rz_m[:,0].max());points=np.column_stack((np.tile(np.linspace(inner,radius,257),2),np.repeat([mesh.outer_rz_m[:,1].min(),mesh.outer_rz_m[:,1].max()],257)))
    samples=list(fields(points));offset=next(b.value for b in case.boundaries if b.kind=='fixed_psi');samples[0]=samples[0]-offset;samples[1]=samples[1]-offset/points[:,0]
    scales=[float(np.max(abs(samples[0]))),float(np.max(abs(samples[1]))),float(np.max(np.linalg.norm(samples[2],axis=1))),float(np.max(np.linalg.norm(samples[3],axis=1)))]
    return dict(fields=fields,potentials=potentials,source_current_a=current,boundary_flux_wb=flux,fixed_reaction_a=reaction,field_scales=scales,model=dict(model,inner_radius_m=inner,radius_m=radius,length_m=float(np.ptp(mesh.outer_rz_m[:,1]))))


def radial_field(n=2,scale=1.,h_scale=1.,amplitude=1.,shift=0.,holes=0,radial_materials=False,offset=0.,quadrature_order=24):
    mesh=_mesh(n,scale,shift,holes);inner=float(mesh.outer_rz_m[:,0].min());outer=float(mesh.outer_rz_m[:,0].max());cut=(inner+outer)/2
    if holes:cut=2*scale/16
    labels=(mesh.points_rz_m[mesh.triangles][:,:,0].mean(axis=1)>=cut).astype(int) if radial_materials else np.zeros(len(mesh.triangles),dtype=int)
    # Wide affine intervals allow an exact P1 1/r field and an independent
    # logarithmic U/Ustar without a table-knot integration error in this case.
    from superfish_ng.bh_curve import MonotoneBHCurve
    curves=[MonotoneBHCurve(f'm{i}',(0.,.001,4.),(0.,(4.+i)*h_scale,(4000.+2000*i)*h_scale),'Synthetic wide affine H(B), no measured material') for i in range(int(labels.max())+1)]
    p=_partition(mesh,curves,labels);c=.4*inner*amplitude;bottom=float(mesh.outer_rz_m[:,1].min())
    def fields(points):
        r,z=np.asarray(points).T;owners=(r>=cut).astype(int) if radial_materials else np.zeros(len(r),dtype=int);br=c/r;hr=np.array([float(_intensity(curves[i],b)) for i,b in zip(owners,br)]);psi=offset-c*(z-bottom)
        return psi,psi/r,np.column_stack((br,0*r)),np.column_stack((hr,0*r))
    horizontal={};vertical=[]
    for i,edge in enumerate(mesh.boundary_edges):
        v,w=mesh.points_rz_m[edge]
        if v[1]==w[1]:horizontal.setdefault(float(v[1]),[]).append(i)
        else:assert v[0]==w[0];vertical.append(i)
    boundaries=[OffAxisMagnetostaticBoundary(f'fixed-{i}','fixed_psi',edges,offset-c*(z-bottom)) for i,(z,edges) in enumerate(sorted(horizontal.items()))]
    boundaries.append(OffAxisMagnetostaticBoundary('sides','tangential_h',vertical,0.));case=OffAxisBHCase(p,{v.id:0. for v in p.regions},boundaries,quadrature_order=quadrature_order)
    potentials=np.zeros(2)
    if c:
        for polygon,sign in [(mesh.outer_rz_m,1),*((hole,-1) for hole in mesh.holes_rz_m)]:
            lo=polygon.min(axis=0);hi=polygon.max(axis=0)
            for i,m in enumerate(curves):
                a=max(lo[0],cut) if i else lo[0];b=min(hi[0],cut) if radial_materials and i==0 else hi[0]
                if a>=b:continue
                rectangle=np.array([[a,lo[1]],[b,lo[1]],[b,hi[1]],[a,hi[1]]]);dummy=SimpleNamespace(materials=[m],mesh=SimpleNamespace(outer_rz_m=rectangle,holes_rz_m=[]));potentials+=sign*radial_energy_reference(dummy,c)
    flux={v.id:0. for v in boundaries};reaction={v.id:0. for v in boundaries if v.kind=='fixed_psi'}
    for boundary in boundaries:
        for edge in boundary.edge_indices:
            v,w=mesh.points_rz_m[mesh.boundary_edges[edge]];flux[boundary.id]-=TAU*float(np.diff(fields([v,w])[0])[0])
            if boundary.kind=='fixed_psi' and c:
                a,b=sorted([float(v[0]),float(w[0])]);cuts=[a,*([cut] if a<cut<b else []),b];integral=0.
                for left,right in zip(cuts,cuts[1:]):
                    owner=int(radial_materials and (left+right)/2>=cut);curve=curves[owner];nu=(curve.h_a_per_m[2]-curve.h_a_per_m[1])/(curve.b_t[2]-curve.b_t[1]);intercept=curve.h_a_per_m[1]-nu*curve.b_t[1]
                    integral+=np.sign(c)*(nu*abs(c)*np.log(right/left)+intercept*(right-left))
                reaction[boundary.id]+=TAU*np.sign(w[0]-v[0])*integral
    return case,_reference(case,fields,dict(energy_j=float(potentials[0]),coenergy_j=float(potentials[1])),0.,dict(kind='radial_field',radial_materials=radial_materials,holes=holes,offset_psi_wb=offset),flux,reaction)


def _integrate_radial(function,left,right,breaks):
    nodes,weights=np.polynomial.legendre.leggauss(3);edges=[left,*sorted(v for v in breaks if left<v<right),right];result=0.
    for a,b in zip(edges[:-1],edges[1:]):
        points=(a+b)/2+(b-a)*nodes/2;result+=float(weights@function(points))*(b-a)/2
    return result


def current_annulus(n=4,scale=1.,h_scale=1.,amplitude=1.,boundary='tangential',shift=0.,linear=False,offset=0.,quadrature_order=12):
    mesh=_mesh(n,scale,shift);left=float(mesh.outer_rz_m[:,0].min());radius=float(mesh.outer_rz_m[:,0].max());width=radius-left;length=float(np.ptp(mesh.outer_rz_m[:,1]));curve=_curve(0,h_scale,linear)
    inner=1400.*amplitude*h_scale;outer=50.*amplitude*h_scale;current=(inner-outer)/width
    breaks=sorted(left+(inner-h)/current for h in [*curve.h_a_per_m,*(-np.array(curve.h_a_per_m))] if left<left+(inner-h)/current<radius)
    def flux_scalar(r):return _integrate_radial(lambda x:x*_inverse(curve,inner-current*(x-left)),left,float(r),breaks)
    def flux(r):
        values=np.asarray(r);unique,indices=np.unique(values,return_inverse=True);return np.array([flux_scalar(v) for v in unique])[indices].reshape(values.shape)
    def fields(points):
        r,z=np.asarray(points).T;h=inner-current*(r-left);b=_inverse(curve,h);psi=offset+flux(r)
        return psi,psi/r,np.column_stack((0*r,b)),np.column_stack((0*r,h))
    p=_partition(mesh,[curve],np.zeros(len(mesh.triangles),dtype=int));outer_psi=float(offset+flux(radius));case=OffAxisBHCase(p,dict(r0=current),_boundaries(mesh,fields,outer_psi if boundary=='fixed' else None,offset),quadrature_order=quadrature_order)
    potentials=[]
    for component in (1,2):potentials.append(TAU*length*_integrate_radial(lambda r:r*np.array([decimal_reference(curve,abs(float(v)))[component] for v in _inverse(curve,inner-current*(r-left))]),left,radius,breaks))
    return case,_reference(case,fields,dict(energy_j=potentials[0],coenergy_j=potentials[1]),current*width*length,dict(kind='current',linear=linear,inner_h_a_per_m=inner,outer_h_a_per_m=outer,breaks_r_m=breaks,offset_psi_wb=offset))


def radial_layers(n=8,scale=1.,h_scale=1.,amplitude=1.,boundary='tangential',shift=0.,offset=0.,quadrature_order=12):
    if n%2:raise ValueError('radial reference requires an even mesh count')
    mesh=_mesh(n,scale,shift);left=float(mesh.outer_rz_m[:,0].min());radius=float(mesh.outer_rz_m[:,0].max());cut=(left+radius)/2;length=float(np.ptp(mesh.outer_rz_m[:,1]));labels=(mesh.points_rz_m[mesh.triangles][:,:,0].mean(axis=1)>=cut).astype(int)
    curves=[_curve(i,h_scale,False) for i in range(2)];h=875.*amplitude*h_scale;b=np.array([float(_inverse(m,h)) for m in curves]);p=_partition(mesh,curves,labels)
    def flux(r):
        values=np.asarray(r);return (b[0]*(np.minimum(values,cut)**2-left**2)+b[1]*np.maximum(values**2-cut**2,0.))/2
    def fields(points):
        r,z=np.asarray(points).T;owners=(r>=cut).astype(int);psi=offset+flux(r)
        return psi,psi/r,np.column_stack((0*r,b[owners])),np.column_stack((0*r,0*r+h))
    outer_psi=float(offset+flux(radius));case=OffAxisBHCase(p,dict(r0=0.,r1=0.),_boundaries(mesh,fields,outer_psi if boundary=='fixed' else None,offset),quadrature_order=quadrature_order)
    volumes=np.pi*length*np.array([cut**2-left**2,radius**2-cut**2]);potentials=sum(v*np.array(decimal_reference(m,abs(float(induction)))[1:3]) for v,m,induction in zip(volumes,curves,b))
    return case,_reference(case,fields,dict(energy_j=float(potentials[0]),coenergy_j=float(potentials[1])),0.,dict(kind='radial_layers',cut_r_m=cut,offset_psi_wb=offset))


def field_l2_errors(solution,reference):
    mesh=solution.case.partition.mesh;vertices=mesh.points_rz_m[mesh.triangles];det=np.linalg.det(np.transpose(vertices[:,1:]-vertices[:,0,None,:],(0,2,1)));cells=np.arange(len(vertices));squares=np.zeros(4);den=np.zeros(4)
    nodes,weights=np.polynomial.legendre.leggauss(6);nodes=(nodes+1)/2;weights=weights/2
    for x,wx in zip(nodes,weights):
        for y,wy in zip(nodes,weights):
            bary=np.array([(1-x)*(1-y),x,(1-x)*y]);points=np.einsum('i,tia->ta',bary,vertices);measure=TAU*points[:,0]*det*wx*wy*(1-x);fields=solution.fields_in_cells(cells,np.broadcast_to(bary,(len(cells),3)))
            actual=[fields['psi_Wb'],fields['Aphi_Wb_per_m'],np.column_stack((fields['Br_T'],fields['Bz_T'])),np.column_stack((fields['Hr_A_per_m'],fields['Hz_A_per_m']))]
            for i,(a,b) in enumerate(zip(actual,reference['fields'](points))):
                squares[i]+=float(measure@((a-b)**2 if a.ndim==1 else np.sum((a-b)**2,axis=1)));den[i]+=float(measure.sum())*reference['field_scales'][i]**2
    return [float(np.sqrt(a/b)) if b else float(np.sqrt(a)) for a,b in zip(squares,den)]


def independent_current_bvp(case,reference):
    from scipy.integrate import solve_bvp
    model=reference['model'];assert model['kind']=='current';left=model['inner_radius_m'];radius=model['radius_m'];width=radius-left;current=case.current_density_phi_a_per_m2['r0'];curve=case.partition.materials[0]
    offset=next(b.value for b in case.boundaries if b.id=='inner');outer=next((b.value-offset for b in case.boundaries if b.id=='outer'),None)
    outer_h=next((b.value for b in case.boundaries if b.kind=='tangential_h' and np.all(case.partition.mesh.points_rz_m[case.partition.mesh.boundary_edges[list(b.edge_indices)],0]==radius)),None)
    hscale=max(abs(current*width),abs(outer_h or 0.),curve.h_a_per_m[1]);bscale=curve.b_t[-1];fscale=width*radius*bscale
    def ode(x,y):return np.vstack(((left+width*x)/radius*_inverse(curve,y[1]*hscale)/bscale,np.full_like(x,-current*width/hscale)))
    def boundary(a,b):return np.array([a[0],b[0]-outer/fscale if outer is not None else b[1]-outer_h/hscale])
    nodes=np.linspace(0.,1.,9);initial=np.zeros((2,len(nodes)))
    if outer is not None:initial[0]=(outer/fscale)*nodes
    else:initial[1]=outer_h/hscale
    attempts=[]
    for attempt in range(4):
        answer=solve_bvp(ode,boundary,nodes,initial,tol=1e-10,bc_tol=1e-11,max_nodes=4096)
        attempts.append(dict(status=int(answer.status),nodes=len(answer.x),iterations=int(answer.niter),max_ode_residual=float(max(answer.rms_residuals))))
        if answer.success:break
        h0=float(answer.y[1,0]*hscale);events=[(h0-h)/(current*width) for h in [*curve.h_a_per_m,*(-np.array(curve.h_a_per_m))] if 0<(h0-h)/(current*width)<1]
        nodes=np.unique(np.r_[np.linspace(0.,1.,9),events]);initial=answer.sol(nodes)
    if not answer.success:raise ValueError('independent off-axis BVP did not converge: '+str(attempts))
    x=np.linspace(0.,1.,257);state=answer.sol(x);r=left+width*x;h=state[1]*hscale;b=_inverse(curve,h);psi=offset+state[0]*fscale
    actual=[psi,psi/r,np.column_stack((0*x,b)),np.column_stack((0*x,h))];expected=reference['fields'](np.column_stack((r,np.full(len(r),case.partition.mesh.outer_rz_m[:,1].min()))));errors=[]
    for i,(aa,bb) in enumerate(zip(actual,expected)):errors.append(float(np.linalg.norm(aa-bb)/(np.sqrt(len(x))*reference['field_scales'][i])))
    assert max(errors)<1e-8
    return dict(method='independent 1D SciPy collocation of psi_r=r*B(H), H_r=-Jphi',nodes=len(answer.x),iterations=int(answer.niter),max_ode_residual=float(max(answer.rms_residuals)),errors_psi_aphi_b_h=errors,attempts=attempts,interpretation='one-dimensional boundary-value comparison from declared fixed-psi/Ht values; not a general 2D independent-solver certification')

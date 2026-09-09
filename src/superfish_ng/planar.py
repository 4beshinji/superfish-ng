# SPDX-License-Identifier: Apache-2.0
"""Vacuum Cartesian TE/TM cutoff FEM; area measure, peak phasors, J/m.

The longitudinal direction is z, beta_z=0. TM uses real Ez with Dirichlet
PEC; TE uses real Hz with Neumann PEC and excludes the constant nullspace.
No axisymmetric geometry, radial weights or accelerating-voltage convention
is reused. See docs/PLANAR_RF_PLAN.md.
"""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import eigsh
from .config import keys, positive, integer
from .constants import C0, EPS0, MU0, TAU
from .fem import triangle_quadrature
from .high_order import basis_p2


@dataclass(frozen=True)
class PlanarCase:
    width_m: float
    height_m: float
    polarization: str = 'te'
    nx: int = 24
    ny: int = 24
    element_order: int = 2
    modes: int = 4
    normalization_j_per_m: float = 1.
    conductivity_s_per_m: float = 5.8e7
    name: str = 'planar cutoff'

    def __post_init__(self):
        for name in ('width_m','height_m','normalization_j_per_m','conductivity_s_per_m'):
            object.__setattr__(self,name,positive(getattr(self,name),name))
        for name in ('nx','ny'):integer(getattr(self,name),name,2)
        integer(self.element_order,'element_order')
        integer(self.modes,'modes')
        if self.element_order not in (1,2):raise ValueError('planar element_order must be 1 or 2')
        if self.polarization not in ('te','tm'):raise ValueError('planar polarization must be te or tm')
        if not isinstance(self.name,str) or not self.name.strip():raise ValueError('planar name must be nonempty')
        if not np.isfinite(self.width_m*self.height_m) or self.width_m*self.height_m == 0:
            raise ValueError('planar rectangle area is outside finite SI arithmetic')

    @classmethod
    def from_dict(cls,data):
        required=['format','schema_version','name','model','geometry','mesh','rf','modes']
        keys(data,required,required,'planar case')
        if data['format']!='superfish_ng_planar_case' or type(data['schema_version']) is not int or data['schema_version']!=1:
            raise ValueError('expected superfish_ng_planar_case schema_version 1')
        model=data['model'];names=['physics','coordinates','polarization','propagation_constant_per_m','material','boundary']
        keys(model,names,names,'planar model')
        for key,expected in [('physics','rf_eigenmode'),('coordinates','cartesian'),('material','vacuum'),('boundary','pec')]:
            if model[key]!=expected:raise ValueError(f'planar model.{key}: only {expected} is implemented')
        beta=model['propagation_constant_per_m']
        if type(beta) not in (int,float) or beta!=0:raise ValueError('planar cutoff requires propagation_constant_per_m=0')
        g=data['geometry'];keys(g,['type','width_m','height_m'],['type','width_m','height_m'],'planar geometry')
        if g['type']!='rectangle':raise ValueError('planar automatic mesh currently requires a rectangle; general/curved/multiply connected domains are unsupported')
        mesh=data['mesh'];names=['nx','ny','element_order'];keys(mesh,names,names,'planar mesh')
        rf=data['rf'];names=['stored_energy_j_per_m','conductivity_s_per_m'];keys(rf,names,names,'planar rf')
        return cls(g['width_m'],g['height_m'],model['polarization'],**mesh,modes=data['modes'],
            normalization_j_per_m=rf['stored_energy_j_per_m'],conductivity_s_per_m=rf['conductivity_s_per_m'],name=data['name'])

    @classmethod
    def load(cls,path):
        from .project import parse_json
        return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def to_dict(self):
        return dict(format='superfish_ng_planar_case',schema_version=1,name=self.name,
            model=dict(physics='rf_eigenmode',coordinates='cartesian',polarization=self.polarization,
                propagation_constant_per_m=0,material='vacuum',boundary='pec'),
            geometry=dict(type='rectangle',width_m=self.width_m,height_m=self.height_m),
            mesh=dict(nx=self.nx,ny=self.ny,element_order=self.element_order),modes=self.modes,
            rf=dict(stored_energy_j_per_m=self.normalization_j_per_m,conductivity_s_per_m=self.conductivity_s_per_m))


@dataclass
class PlanarSpace:
    points_xy_m: np.ndarray
    triangles: np.ndarray
    dof_points_xy_m: np.ndarray
    cell_dofs: np.ndarray
    boundary_edges: np.ndarray
    boundary_cells: np.ndarray
    boundary_local_vertices: np.ndarray
    boundary_dofs: np.ndarray
    determinants: np.ndarray
    gradients: np.ndarray


def planar_matrices(case):
    if not isinstance(case,PlanarCase):raise ValueError('planar FEM requires an explicit PlanarCase')
    nx,ny=case.nx,case.ny
    x,y=np.meshgrid(np.linspace(0,case.width_m,nx+1),np.linspace(0,case.height_m,ny+1))
    points=np.column_stack((x.ravel(),y.ravel()))
    j,i=np.meshgrid(np.arange(ny),np.arange(nx),indexing='ij');p=(j*(nx+1)+i).ravel();q=p+nx+1
    cells=np.stack((np.column_stack((p,p+1,q+1)),np.column_stack((p,q+1,q))),axis=1).reshape(-1,3)
    boundary=[];owners=[];local=[]
    for i in range(nx):
        boundary.extend(((i,i+1),(ny*(nx+1)+i+1,ny*(nx+1)+i)))
        owners.extend((2*i,2*((ny-1)*nx+i)+1));local.extend(((0,1),(1,2)))
    for j in range(ny):
        p=j*(nx+1)
        boundary.extend(((p+nx,p+2*nx+1),(p+nx+1,p)))
        owners.extend((2*(j*nx+nx-1),2*j*nx+1));local.extend(((1,2),(2,0)))
    boundary=np.asarray(boundary,dtype=np.int64)
    dofs=cells;dof_points=points;boundary_dofs=boundary
    if case.element_order==2:
        edges,inverse=np.unique(np.sort(cells[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0,return_inverse=True)
        dofs=np.column_stack((cells,len(points)+inverse.reshape(-1,3)))
        dof_points=np.vstack((points,points[edges].mean(axis=1)))
        lookup={tuple(edge):len(points)+k for k,edge in enumerate(edges)}
        boundary_dofs=np.column_stack((boundary,[lookup[tuple(sorted(edge))] for edge in boundary]))
    vertices=points[cells];jac=np.stack((vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]),axis=2)
    det=np.linalg.det(jac)
    if not np.isfinite(det).all() or np.any(det<=0):raise ValueError('planar triangle Jacobian is not finite positive')
    grad=np.einsum('ij,tjk->tik',np.array([[-1.,-1.],[1.,0.],[0.,1.]]),np.linalg.inv(jac))
    dim=dofs.shape[1];k=np.zeros((len(cells),dim,dim));m=np.zeros_like(k)
    for bary,w in triangle_quadrature(4):
        v,g=(bary,grad) if case.element_order==1 else basis_p2(bary,grad)
        k+=(w*det)[:,None,None]*np.einsum('tik,tjk->tij',g,g)
        m+=(w*det)[:,None,None]*np.outer(v,v)
    rows=np.repeat(dofs,dim,axis=1).ravel();cols=np.tile(dofs,(1,dim)).ravel()
    k,m=[coo_matrix((a.ravel(),(rows,cols)),shape=(len(dof_points),)*2).tocsr() for a in (k,m)]
    if not np.isfinite(k.data).all() or not np.isfinite(m.data).all():raise ValueError('planar matrix arithmetic overflow')
    space=PlanarSpace(points,cells,dof_points,dofs,boundary,np.asarray(owners),np.asarray(local),boundary_dofs,det,grad)
    free=np.setdiff1d(np.arange(len(dof_points)),np.unique(boundary_dofs)) if case.polarization=='tm' else np.arange(len(dof_points))
    return space,k,m,free


def _eigenpairs(case,k,m,free):
    count=case.modes+(case.polarization=='te')
    if count>len(free):raise ValueError('requested planar modes exceed available positive FEM degrees of freedom; refine the mesh or request fewer modes')
    kk,mm=k[free][:,free],m[free][:,free]
    scale=max(case.width_m,case.height_m)
    if count==len(free) and len(free)>256:
        raise ValueError('full planar spectrum on a large mesh is unsupported; request fewer positive modes')
    if len(free)<=64 or count==len(free):
        values,vectors=eigh(kk.toarray(),mm.toarray(),subset_by_index=(0,count-1))
    else:
        values,vectors=eigsh(kk,k=count,M=mm,sigma=-1/scale**2,which='LM',tol=1e-11,v0=np.linspace(1,2,len(free)))
    order=np.argsort(values);values,vectors=values[order],vectors[:,order]
    if case.polarization=='te':
        ones=np.ones(len(free));area=ones@(mm@ones)
        overlap=abs(ones@(mm@vectors[:,0]))/np.sqrt(area)
        if abs(values[0])*scale**2>1e-8 or abs(overlap-1)>1e-8:
            raise ValueError('planar TE constant nullspace was not resolved; no positive spectrum accepted')
        values,vectors=values[1:],vectors[:,1:]
    if not np.isfinite(values).all() or np.any(values<=0):raise ValueError('invalid positive planar cutoff spectrum')
    return values,vectors


@dataclass
class PlanarSolution:
    case: PlanarCase
    space: PlanarSpace
    stiffness: object
    mass: object
    free_dofs: np.ndarray
    eigenvalues: np.ndarray
    frequencies_hz: np.ndarray
    coefficients: np.ndarray
    residuals: np.ndarray
    orthogonality_error: float

    def fields_in_cells(self,cell_indices,barycentric,mode=0):
        integer(mode,'mode',0)
        if mode>=self.case.modes:raise ValueError('planar mode index is out of range')
        cells=np.asarray(cell_indices);bary=np.asarray(barycentric,dtype=float)
        if (cells.ndim!=1 or cells.dtype.kind not in 'iu' or np.any(cells<0) or np.any(cells>=len(self.space.triangles))
                or bary.shape!=(len(cells),3) or not np.isfinite(bary).all() or np.any(bary<-1e-12)
                or not np.allclose(bary.sum(axis=1),1,rtol=0,atol=1e-12)):
            raise ValueError('planar field evaluation requires valid cell indices and barycentric points')
        gradients=self.space.gradients[cells]
        if self.case.element_order==1:v,g=bary,gradients
        else:
            v=np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
            g=np.concatenate(((4*bary-1)[:,:,None]*gradients,np.stack([4*(bary[:,i,None]*gradients[:,j]+bary[:,j,None]*gradients[:,i]) for i,j in ((0,1),(1,2),(2,0))],axis=1)),axis=1)
        c=self.coefficients[self.space.cell_dofs[cells],mode]
        scalar=np.einsum('ti,ti->t',v,c);derivative=np.einsum('tij,ti->tj',g,c)
        result={f'{field}{axis}_{phase}_{unit}':np.zeros(len(cells)) for field,unit in (('E','V_per_m'),('H','A_per_m')) for axis in 'xyz' for phase in ('real','quadrature')}
        omega=TAU*self.frequencies_hz[mode]
        if self.case.polarization=='tm':
            result.update(Ez_real_V_per_m=scalar,Hx_quadrature_A_per_m=derivative[:,1]/(omega*MU0),Hy_quadrature_A_per_m=-derivative[:,0]/(omega*MU0))
        else:
            result.update(Hz_real_A_per_m=scalar,Ex_quadrature_V_per_m=-derivative[:,1]/(omega*EPS0),Ey_quadrature_V_per_m=derivative[:,0]/(omega*EPS0))
        return result


def _restore(case,space,k,m,free,coefficients,frequencies,*,verify_spectrum):
    c=np.asarray(coefficients);f=np.asarray(frequencies)
    if (c.dtype.kind!='f' or f.dtype.kind!='f' or c.shape!=(k.shape[0],case.modes) or f.shape!=(case.modes,)
            or not np.isfinite(c).all() or not np.isfinite(f).all() or np.any(f<=0) or np.any(np.diff(f)<0)):
        raise ValueError('invalid planar coefficients or ordered positive frequencies')
    constrained=np.setdiff1d(np.arange(k.shape[0]),free)
    if np.any(c[constrained]!=0):raise ValueError('planar TM PEC coefficients must be zero')
    material=EPS0 if case.polarization=='tm' else MU0
    orth=float(np.max(abs(c.T@(m@c)*material/(2*case.normalization_j_per_m)-np.eye(case.modes))))
    values=(TAU*f/C0)**2;residual=[]
    for i,value in enumerate(values):
        kv,mv=(k@c[:,i])[free],(m@c[:,i])[free]
        residual.append(np.linalg.norm(kv-value*mv)/(np.linalg.norm(kv)+value*np.linalg.norm(mv)))
    if case.polarization=='te':
        ones=np.ones(len(c));null_overlap=np.max(abs(ones@(m@c)))/np.sqrt((ones@(m@ones))*2*case.normalization_j_per_m/material)
        if not np.isfinite(null_overlap) or null_overlap>1e-8:raise ValueError('planar TE positive modes contain a constant component')
    if not np.isfinite(residual).all() or max(residual)>1e-7 or not np.isfinite(orth) or orth>1e-8:
        raise ValueError('planar FEM residual or unit-length normalization/orthogonality failed')
    if verify_spectrum:
        expected,_=_eigenpairs(case,k,m,free)
        if not np.allclose(values,expected,rtol=1e-9,atol=0):raise ValueError('planar saved spectrum does not contain the requested lowest positive modes')
    return PlanarSolution(case,space,k,m,free,values,f,c,np.asarray(residual),orth)


def solve_planar(case):
    space,k,m,free=planar_matrices(case);values,vectors=_eigenpairs(case,k,m,free)
    material=EPS0 if case.polarization=='tm' else MU0
    coefficients=np.zeros((k.shape[0],case.modes));coefficients[free]=vectors*np.sqrt(2*case.normalization_j_per_m/material)
    for i in range(case.modes):
        if coefficients[np.argmax(abs(coefficients[:,i])),i]<0:coefficients[:,i]*=-1
    return _restore(case,space,k,m,free,coefficients,C0/TAU*np.sqrt(values),verify_spectrum=False)


class PlanarFieldSampler:
    def __init__(self,solution):self.solution=solution

    def evaluate(self,points_xy_m,mode=0):
        try:
            raw=np.asarray(points_xy_m,dtype=object)
            if raw.ndim!=2 or raw.shape[1]!=2 or any(isinstance(v,(bool,np.bool_)) or not isinstance(v,(int,float,np.integer,np.floating)) for v in raw.flat):
                raise ValueError('planar probes require an array of numeric [x_m,y_m] pairs')
            points=raw.astype(float)
        except (TypeError,OverflowError) as exc:
            raise ValueError('planar probes require finite numeric xy coordinates') from exc
        case=self.solution.case
        if (points.ndim!=2 or points.shape[1]!=2 or not np.isfinite(points).all()
                or np.any(points<0) or np.any(points>[case.width_m,case.height_m])):
            raise ValueError('planar probe points must be finite xy coordinates inside the rectangle')
        grid=points/[case.width_m/case.nx,case.height_m/case.ny]
        ij=np.minimum(np.floor(grid).astype(int),[case.nx-1,case.ny-1]);x,y=(grid-ij).T
        second=y>x;cells=2*(ij[:,1]*case.nx+ij[:,0])+second
        bary=np.where(second[:,None],np.column_stack((1-y,x,y-x)),np.column_stack((1-x,x-y,y)))
        return self.solution.fields_in_cells(cells,bary,mode)


def planar_quantities(solution,mode=0):
    case=solution.case;integer(mode,'mode',0)
    if mode>=case.modes:raise ValueError('planar mode index is out of range')
    c=solution.coefficients[:,mode];f=solution.frequencies_hz[mode];omega=TAU*f
    scalar=float(c@(solution.mass@c));gradient=float(c@(solution.stiffness@c))
    if case.polarization=='tm':ue=EPS0*scalar/4;um=gradient/(4*omega**2*MU0)
    else:um=MU0*scalar/4;ue=gradient/(4*omega**2*EPS0)
    space=solution.space;points=space.points_xy_m[space.boundary_edges]
    tangent=points[:,1]-points[:,0];length=np.linalg.norm(tangent,axis=1);tangent/=length[:,None]
    nodes,weights=np.polynomial.legendre.leggauss(5);wall=0.
    for node,weight in zip((nodes+1)/2,weights/2):
        bary=np.zeros((len(points),3));rows=np.arange(len(points))
        bary[rows,space.boundary_local_vertices[:,0]]=1-node;bary[rows,space.boundary_local_vertices[:,1]]=node
        fields=solution.fields_in_cells(space.boundary_cells,bary,mode)
        if case.polarization=='te':ht=fields['Hz_real_A_per_m']
        else:ht=fields['Hx_quadrature_A_per_m']*tangent[:,0]+fields['Hy_quadrature_A_per_m']*tangent[:,1]
        wall+=float(np.sum(weight*length*ht**2))
    rs=np.sqrt(np.pi*f*MU0/case.conductivity_s_per_m);loss=rs*wall/2;energy=ue+um
    if not np.isfinite([ue,um,loss]).all() or min(ue,um,loss)<=0:raise ValueError('invalid positive planar RF energy or PEC wall loss')
    return dict(frequency_hz=float(f),stored_energy_j_per_m=energy,electric_energy_j_per_m=ue,magnetic_energy_j_per_m=um,
        wall_loss_w_per_m=loss,surface_resistance_ohm=float(rs),q0=omega*energy/loss,geometry_factor_ohm=2*omega*energy/wall,
        r_over_q_accelerator_ohm=None,r_over_q_circuit_ohm=None,vacc_v=None,eacc_v_per_m=None,
        accelerating_quantities_reason='cutoff cross-section per unit longitudinal length; no finite accelerating path is declared')

# SPDX-License-Identifier: Apache-2.0
"""Vacuum closed coaxial m=0 Hphi FEM, with q=r*Hphi and its static nullspace.

K=integral grad(q).grad(v)/r dr dz; M=integral q*v/r dr dz.
All four walls are PEC (natural Neumann for q). The constant q represents
static circulation, not an RF resonance. Only the positive spectrum is saved.
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
from .high_order import basis_p2, quadratic_space
from .mesh import Mesh, element_geometry


@dataclass(frozen=True)
class CoaxialCase:
    inner_radius_m: float
    outer_radius_m: float
    length_m: float
    nr: int = 16
    nz: int = 32
    element_order: int = 2
    quadrature_order: int = 8
    modes: int = 4
    normalization_j: float = 1.
    conductivity_s_per_m: float = 5.8e7
    name: str = 'closed vacuum coaxial resonator'

    def __post_init__(self):
        for name in ('inner_radius_m','outer_radius_m','length_m','normalization_j','conductivity_s_per_m'):
            object.__setattr__(self,name,positive(getattr(self,name),name))
        if self.inner_radius_m >= self.outer_radius_m:
            raise ValueError('coaxial radii require 0 < inner_radius_m < outer_radius_m')
        for name in ('nr','nz'):integer(getattr(self,name),name,2)
        integer(self.modes,'modes')
        integer(self.element_order,'element_order')
        integer(self.quadrature_order,'quadrature_order',4)
        if self.element_order not in (1,2):raise ValueError('coaxial element_order must be 1 or 2')
        if self.quadrature_order > 32:raise ValueError('coaxial quadrature_order must be between 4 and 32')
        if 2*self.nr*self.nz > 250000:raise ValueError('coaxial mesh exceeds 250000 triangles; reduce nr or nz')
        if not isinstance(self.name,str) or not self.name.strip():raise ValueError('coaxial name must be nonempty')
        if not np.isfinite(self.volume_m3) or self.volume_m3 <= 0:
            raise ValueError('coaxial volume is outside finite positive SI arithmetic')

    @property
    def volume_m3(self):
        return np.pi*(self.outer_radius_m-self.inner_radius_m)*(self.outer_radius_m+self.inner_radius_m)*self.length_m

    def to_dict(self):
        return dict(format='superfish_ng_coaxial_case',schema_version=1,name=self.name,
            model=dict(physics='rf_eigenmode',coordinates='axisymmetric',azimuthal_index=0,
                       field_family='Hphi',material='vacuum',boundary='closed_pec'),
            geometry=dict(type='coaxial_cylinder',inner_radius_m=self.inner_radius_m,
                          outer_radius_m=self.outer_radius_m,length_m=self.length_m),
            mesh=dict(nr=self.nr,nz=self.nz,element_order=self.element_order,quadrature_order=self.quadrature_order),
            modes=self.modes,rf=dict(stored_energy_j=self.normalization_j,conductivity_s_per_m=self.conductivity_s_per_m))

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','name','model','geometry','mesh','modes','rf']
        keys(data,names,names,'coaxial case')
        if data['format']!='superfish_ng_coaxial_case' or type(data['schema_version']) is not int or data['schema_version']!=1:
            raise ValueError('expected superfish_ng_coaxial_case schema_version 1')
        expected=dict(physics='rf_eigenmode',coordinates='axisymmetric',azimuthal_index=0,
                      field_family='Hphi',material='vacuum',boundary='closed_pec')
        model=data['model'];keys(model,list(expected),list(expected),'coaxial model')
        for name,value in expected.items():
            if type(model[name]) is not type(value) or model[name]!=value:
                raise ValueError(f'coaxial model.{name}: only {value!r} is implemented')
        g=data['geometry'];names=['type','inner_radius_m','outer_radius_m','length_m']
        keys(g,names,names,'coaxial geometry')
        if g['type']!='coaxial_cylinder':raise ValueError('coaxial automatic mesh requires coaxial_cylinder; general inner conductors and holes are unsupported')
        mesh=data['mesh'];names=['nr','nz','element_order','quadrature_order'];keys(mesh,names,names,'coaxial mesh')
        rf=data['rf'];names=['stored_energy_j','conductivity_s_per_m'];keys(rf,names,names,'coaxial rf')
        return cls(g['inner_radius_m'],g['outer_radius_m'],g['length_m'],**mesh,modes=data['modes'],
                   normalization_j=rf['stored_energy_j'],conductivity_s_per_m=rf['conductivity_s_per_m'],name=data['name'])

    @classmethod
    def load(cls,path):
        from .project import parse_json
        return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))


@dataclass
class CoaxialSpace:
    mesh: Mesh
    dof_points: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray
    boundary_local_vertices: np.ndarray
    determinants: np.ndarray
    gradients: np.ndarray


def _space(case):
    r,z=np.meshgrid(np.linspace(case.inner_radius_m,case.outer_radius_m,case.nr+1),np.linspace(0,case.length_m,case.nz+1))
    points=np.column_stack((r.ravel(),z.ravel()))
    j,i=np.meshgrid(np.arange(case.nz),np.arange(case.nr),indexing='ij')
    p=(j*(case.nr+1)+i).ravel();q=p+case.nr+1
    cells=np.stack((np.column_stack((p,p+1,q+1)),np.column_stack((p,q+1,q))),axis=1).reshape(-1,3)
    incidence={}
    for cell,tri in enumerate(cells):
        for ia,ib in ((0,1),(1,2),(2,0)):
            edge=tuple(sorted((int(tri[ia]),int(tri[ib]))))
            incidence.setdefault(edge,[]).append((cell,ia,ib))
    boundary=[(edge,owners[0]) for edge,owners in incidence.items() if len(owners)==1]
    edges=np.array([edge for edge,_ in boundary],dtype=np.int64)
    owners=np.array([data[0] for _,data in boundary],dtype=np.int64)
    local=np.array([data[1:] for _,data in boundary],dtype=np.int64)
    tags=np.full(len(edges),'pec',dtype='U20')
    mesh=Mesh(points,cells,edges,tags,owners,np.array([],dtype=np.int64))
    _,det,grad=element_geometry(mesh)
    if np.any(points[:,0]<=0):raise ValueError('coaxial mesh must be strictly outside the axis')
    if case.element_order==2:
        quadratic=quadratic_space(mesh)
        dof_points,dofs,boundary_dofs=quadratic.dof_points,quadratic.cell_dofs,quadratic.boundary_dofs
    else:dof_points,dofs,boundary_dofs=points,cells,edges
    return CoaxialSpace(mesh,dof_points,dofs,boundary_dofs,local,det,grad)


def _assemble(space,element_order,quadrature_order):
    vertices=space.mesh.points[space.mesh.triangles];dofs=space.cell_dofs;dimension=dofs.shape[1]
    k=np.zeros((len(dofs),dimension,dimension));m=np.zeros_like(k)
    for bary,weight in triangle_quadrature(quadrature_order):
        values,gradients=(bary,space.gradients) if element_order==1 else basis_p2(bary,space.gradients)
        radius=vertices[:,:,0]@bary
        measure=weight*space.determinants/radius
        k+=measure[:,None,None]*np.einsum('tik,tjk->tij',gradients,gradients)
        m+=measure[:,None,None]*np.outer(values,values)
    rows=np.repeat(dofs,dimension,axis=1).ravel();columns=np.tile(dofs,(1,dimension)).ravel()
    matrices=tuple(coo_matrix((v.ravel(),(rows,columns)),shape=(len(space.dof_points),)*2).tocsr() for v in (k,m))
    if any(not np.isfinite(a.data).all() for a in matrices):raise ValueError('coaxial matrix arithmetic overflow')
    return matrices


def coaxial_matrices(case):
    if not isinstance(case,CoaxialCase):raise ValueError('coaxial FEM requires an explicit CoaxialCase')
    space=_space(case);k,m=_assemble(space,case.element_order,case.quadrature_order)
    high=_assemble(space,case.element_order,case.quadrature_order+4)
    differences=[float(np.linalg.norm((a-b).data)/np.linalg.norm(b.data)) for a,b in zip((k,m),high)]
    if not np.isfinite(differences).all() or max(differences)>5e-10:
        raise ValueError('coaxial 1/r quadrature is unresolved; refine nr or increase quadrature_order')
    return space,k,m,dict(orders=[case.quadrature_order,case.quadrature_order+4],
        stiffness_relative_difference=differences[0],mass_relative_difference=differences[1],
        interpretation='finite quadrature comparison; not a discretization error bound')


def _eigenpairs(case,k,m):
    count=case.modes+1;dimension=k.shape[0]
    if count>dimension:raise ValueError('requested coaxial modes exceed positive FEM dimension; refine the mesh or request fewer modes')
    scale=max(case.length_m,case.outer_radius_m-case.inner_radius_m)
    if count==dimension and dimension>256:raise ValueError('full large coaxial spectrum is unsupported; request fewer modes')
    if dimension<=64 or count==dimension:
        values,vectors=eigh(k.toarray(),m.toarray(),subset_by_index=(0,count-1))
    else:
        values,vectors=eigsh(k,k=count,M=m,sigma=-1/scale**2,which='LM',tol=1e-11,v0=np.linspace(1,2,dimension))
    ordering=np.argsort(values);values,vectors=values[ordering],vectors[:,ordering]
    constant=np.ones(dimension);mass=float(constant@(m@constant))
    overlap=abs(constant@(m@vectors[:,0]))/np.sqrt(mass)
    if abs(values[0])*scale**2>1e-8 or abs(overlap-1)>1e-8:
        raise ValueError('coaxial static circulation nullspace was not resolved; positive spectrum refused')
    if not np.isfinite(values).all() or np.any(values[1:]<=0):raise ValueError('invalid positive coaxial FEM spectrum')
    return values[1:],vectors[:,1:]


@dataclass
class CoaxialSolution:
    case: CoaxialCase
    space: CoaxialSpace
    stiffness: object
    mass: object
    eigenvalues: np.ndarray
    frequencies_hz: np.ndarray
    coefficients: np.ndarray
    residuals: np.ndarray
    orthogonality_error: float
    nullspace_overlap: float
    quadrature_diagnostic: dict

    def fields_in_cells(self,cell_indices,barycentric,mode=0):
        integer(mode,'mode',0)
        if mode>=self.case.modes:raise ValueError('coaxial mode index is out of range')
        cells=np.asarray(cell_indices);bary=_numeric_coordinates(barycentric,3,'coaxial barycentric points')
        if (cells.ndim!=1 or cells.dtype.kind not in 'iu' or np.any(cells<0) or np.any(cells>=len(self.space.mesh.triangles))
            or bary.shape!=(len(cells),3) or not np.isfinite(bary).all() or np.any(bary<-1e-12)
            or not np.allclose(bary.sum(axis=1),1,rtol=0,atol=1e-12)):
            raise ValueError('coaxial fields require valid original cell indices and barycentric points')
        grad=self.space.gradients[cells]
        if self.case.element_order==1:values,gradients=bary,grad
        else:
            values=np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
            gradients=np.concatenate(((4*bary-1)[:,:,None]*grad,
                np.stack([4*(bary[:,i,None]*grad[:,j]+bary[:,j,None]*grad[:,i]) for i,j in ((0,1),(1,2),(2,0))],axis=1)),axis=1)
        c=self.coefficients[self.space.cell_dofs[cells],mode]
        q=np.einsum('ti,ti->t',values,c);dq=np.einsum('tij,ti->tj',gradients,c)
        radius=np.einsum('ti,ti->t',bary,self.space.mesh.points[self.space.mesh.triangles[cells],0])
        omega=TAU*self.frequencies_hz[mode]
        result={f'{field}{axis}_{phase}_{unit}':np.zeros(len(cells)) for field,unit in (('E','V_per_m'),('H','A_per_m'))
                for axis in ('r','phi','z') for phase in ('real','quadrature')}
        result.update(Hphi_real_A_per_m=q/radius,Er_quadrature_V_per_m=dq[:,1]/(omega*EPS0*radius),
                      Ez_quadrature_V_per_m=-dq[:,0]/(omega*EPS0*radius))
        return result

    def fields_at(self,points_rz_m,mode=0):
        points=_numeric_coordinates(points_rz_m,2,'coaxial [r_m,z_m] probes');case=self.case
        if (not np.isfinite(points).all() or np.any(points<[case.inner_radius_m,0])
            or np.any(points>[case.outer_radius_m,case.length_m])):
            raise ValueError('coaxial probes must lie in the annular vacuum; the acceleration axis is outside this domain')
        grid=(points-[case.inner_radius_m,0])/[(case.outer_radius_m-case.inner_radius_m)/case.nr,case.length_m/case.nz]
        ij=np.minimum(np.floor(grid).astype(int),[case.nr-1,case.nz-1]);r,z=(grid-ij).T
        second=z>r;cells=2*(ij[:,1]*case.nr+ij[:,0])+second
        bary=np.where(second[:,None],np.column_stack((1-z,r,z-r)),np.column_stack((1-r,r-z,z)))
        return self.fields_in_cells(cells,bary,mode)


def _numeric_coordinates(value,columns,label):
    try:
        # Already typed numeric arrays cannot hide a bool/string mixed into a
        # Python row. Keep bulk quadrature evaluation in NumPy.
        typed=isinstance(value,np.ndarray) and value.dtype.kind in 'fiu'
        raw=value if typed else np.asarray(value,dtype=object)
        if (raw.ndim!=2 or raw.shape[1]!=columns
            or (not typed and any(isinstance(v,(bool,np.bool_)) or not isinstance(v,(int,float,np.integer,np.floating)) for v in raw.flat))):
            raise ValueError(f'{label} require numeric rows of length {columns}')
        result=raw.astype(float)
    except (TypeError,OverflowError) as exc:
        raise ValueError(f'{label} require finite numeric coordinates') from exc
    if not np.isfinite(result).all():raise ValueError(f'{label} require finite numeric coordinates')
    return result


def _restore_coaxial(case,space,k,m,diagnostic,coefficients,frequencies,*,verify_spectrum):
    c=np.asarray(coefficients);f=np.asarray(frequencies)
    if (c.dtype.kind!='f' or f.dtype.kind!='f' or c.shape!=(k.shape[0],case.modes) or f.shape!=(case.modes,)
        or not np.isfinite(c).all() or not np.isfinite(f).all() or np.any(f<=0) or np.any(np.diff(f)<0)):
        raise ValueError('invalid coaxial coefficients or ordered positive frequencies')
    norm=case.normalization_j/(MU0*np.pi)
    orth=float(np.max(abs(c.T@(m@c)/norm-np.eye(case.modes))))
    constant=np.ones(len(c));null=float(np.max(abs(constant@(m@c)))/np.sqrt((constant@(m@constant))*norm))
    values=(TAU*f/C0)**2;residual=[]
    for mode,value in enumerate(values):
        kv,mv=k@c[:,mode],m@c[:,mode]
        residual.append(np.linalg.norm(kv-value*mv)/(np.linalg.norm(kv)+value*np.linalg.norm(mv)))
    if not np.isfinite([orth,null,*residual]).all() or orth>1e-8 or null>1e-8 or max(residual)>1e-8:
        raise ValueError('coaxial coefficients fail energy, orthogonality, static-nullspace or FEM residual validation')
    if verify_spectrum:
        expected,_=_eigenpairs(case,k,m)
        if not np.allclose(values,expected,rtol=1e-8,atol=0):raise ValueError('coaxial frequencies are not the lowest positive FEM spectrum')
    return CoaxialSolution(case,space,k,m,values,f.copy(),c.copy(),np.array(residual),orth,null,diagnostic)


def solve_coaxial(case):
    space,k,m,diagnostic=coaxial_matrices(case)
    values,vectors=_eigenpairs(case,k,m)
    vectors*=np.sqrt(case.normalization_j/(MU0*np.pi))
    for mode in range(case.modes):
        if vectors[np.argmax(abs(vectors[:,mode])),mode]<0:vectors[:,mode]*=-1
    return _restore_coaxial(case,space,k,m,diagnostic,vectors,C0/TAU*np.sqrt(values),verify_spectrum=False)


def coaxial_quantities(solution,mode=0):
    if not isinstance(solution,CoaxialSolution):raise ValueError('coaxial RF requires a CoaxialSolution')
    case=solution.case;integer(mode,'mode',0)
    if mode>=case.modes:raise ValueError('coaxial mode index is out of range')
    f=float(solution.frequencies_hz[mode]);omega=TAU*f;space=solution.space
    cells=np.arange(len(space.mesh.triangles));vertices=space.mesh.points[space.mesh.triangles]
    ue=0.;um=0.
    for bary,w in triangle_quadrature(case.quadrature_order+4):
        fields=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)),mode)
        measure=TAU*(vertices[:,:,0]@bary)*w*space.determinants
        ue+=EPS0/4*float(measure@(fields['Er_quadrature_V_per_m']**2+fields['Ez_quadrature_V_per_m']**2))
        um+=MU0/4*float(measure@(fields['Hphi_real_A_per_m']**2))
    points=space.mesh.points[space.mesh.boundary_edges];length=np.linalg.norm(points[:,1]-points[:,0],axis=1)
    surfaces=dict(inner_conductor=np.all(points[:,:,0]==case.inner_radius_m,axis=1),
                  outer_conductor=np.all(points[:,:,0]==case.outer_radius_m,axis=1),
                  z_min_end_plate=np.all(points[:,:,1]==0,axis=1),
                  z_max_end_plate=np.all(points[:,:,1]==case.length_m,axis=1))
    walls={name:0. for name in surfaces};nodes,weights=np.polynomial.legendre.leggauss(case.quadrature_order+4)
    for node,w in zip((nodes+1)/2,weights/2):
        bary=np.zeros((len(points),3));rows=np.arange(len(points))
        bary[rows,space.boundary_local_vertices[:,0]]=1-node;bary[rows,space.boundary_local_vertices[:,1]]=node
        h=solution.fields_in_cells(space.mesh.boundary_cells,bary,mode)['Hphi_real_A_per_m']
        radius=np.einsum('ti,ti->t',bary,space.mesh.points[space.mesh.triangles[space.mesh.boundary_cells],0])
        integrand=TAU*w*length*radius*h*h
        for name,mask in surfaces.items():walls[name]+=float(integrand[mask].sum())
    wall=sum(walls.values());energy=ue+um;rs=float(np.sqrt(np.pi*f*MU0/case.conductivity_s_per_m));loss=rs*wall/2
    if not np.isfinite([ue,um,wall,loss]).all() or min(ue,um,wall,loss)<=0:raise ValueError('invalid positive coaxial RF energy or wall loss')
    return dict(frequency_hz=f,stored_energy_j=energy,electric_energy_j=ue,magnetic_energy_j=um,
        wall_loss_w=loss,surface_resistance_ohm=rs,q0=omega*energy/loss,geometry_factor_ohm=2*omega*energy/wall,
        wall_h2_integral_a2_by_surface=walls,volume_m3=float(case.volume_m3),
        r_over_q_accelerator_ohm=None,r_over_q_circuit_ohm=None,vacc_v=None,eacc_v_per_m=None,
        accelerating_quantities_reason='the z axis lies inside the inner conductor; no vacuum acceleration path is declared')

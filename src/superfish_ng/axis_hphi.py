# SPDX-License-Identifier: Apache-2.0
"""Regular u=Hphi/r vacuum FEM on explicit axis-connected domains with PEC holes."""
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.linalg import eigh
from scipy.sparse import diags
from scipy.sparse.linalg import eigsh, ArpackNoConvergence
from .config import keys, integer, positive
from .constants import C0, EPS0, MU0, TAU
from .coaxial import _numeric_coordinates
from .axis_connected_mesh import AxisConnectedMesh
from .axis_connected_fem import axis_connected_matrices
from .mesh import element_geometry
from .fem import triangle_quadrature
from .planar_polygon import PolygonLocator
from .quadratic_rf import quadratic_voltage


@dataclass(frozen=True)
class AxisAccelerationPath:
    z_start_m: float
    z_end_m: float
    beta: float
    phase_origin_m: float

    def __post_init__(self):
        for name in ('z_start_m','z_end_m','phase_origin_m'):
            value=getattr(self,name)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not np.isfinite(value):
                raise ValueError(f'acceleration {name} must be a finite SI number')
            object.__setattr__(self,name,float(value))
        object.__setattr__(self,'beta',positive(self.beta,'acceleration beta'))
        if self.beta>1 or not self.z_start_m<self.z_end_m or not np.isfinite(self.z_end_m-self.z_start_m):
            raise ValueError('axis acceleration requires start < end and 0 < beta <= 1')

    def to_dict(self):
        return dict(path='axis',z_start_m=self.z_start_m,z_end_m=self.z_end_m,
                    beta=self.beta,phase_origin_m=self.phase_origin_m)

    @classmethod
    def from_dict(cls,data):
        names=['path','z_start_m','z_end_m','beta','phase_origin_m']
        keys(data,names,names,'axis acceleration')
        if data['path']!='axis':raise ValueError('only an explicit vacuum axis acceleration path is implemented')
        return cls(**{name:data[name] for name in names[1:]})


@dataclass(frozen=True, eq=False)
class AxisHphiCase:
    mesh: AxisConnectedMesh
    element_order: int = 2
    modes: int = 6
    normalization_j: float = 1.
    conductivity_s_per_m: float = 5.8e7
    name: str = 'axis-connected vacuum Hphi resonator'
    acceleration: AxisAccelerationPath | None = None

    def __post_init__(self):
        if not isinstance(self.mesh,AxisConnectedMesh):
            raise ValueError('AxisHphiCase requires a validated AxisConnectedMesh; automatic generation is unsupported')
        for name in ('element_order','modes'): integer(getattr(self,name),name)
        if self.element_order not in (1,2):
            raise ValueError('axis-connected Hphi requires P1 or P2')
        for name in ('normalization_j','conductivity_s_per_m'):
            object.__setattr__(self,name,positive(getattr(self,name),name))
        if not isinstance(self.name,str) or not self.name.strip(): raise ValueError('axis-connected Hphi name must be nonempty')

        if self.acceleration is not None:
            if not isinstance(self.acceleration,AxisAccelerationPath):
                raise ValueError('acceleration must be an explicit AxisAccelerationPath or null')
            self.acceleration.__post_init__()
            a,b=self.mesh.axis_interval_m
            if not a <= self.acceleration.z_start_m < self.acceleration.z_end_m <= b:
                raise ValueError('acceleration interval must lie within the declared vacuum axis')

    @property
    def length_m(self): return float(np.ptp(self.mesh.points_rz_m[:,1]))
    @property
    def inner_radius_m(self): return float(np.min(self.mesh.points_rz_m[:,0]))
    @property
    def outer_radius_m(self): return float(np.max(self.mesh.points_rz_m[:,0]))

    def to_dict(self):
        return dict(format='superfish_ng_axis_hphi_case',schema_version=1,name=self.name,
            model=dict(physics='rf_eigenmode',coordinates='axisymmetric',azimuthal_index=0,
                       field_family='Hphi',material='vacuum',boundary='closed_pec'),
            mesh=self.mesh.to_dict(),fem=dict(element_order=self.element_order),
            acceleration=None if self.acceleration is None else self.acceleration.to_dict(),
            modes=self.modes,rf=dict(stored_energy_j=self.normalization_j,conductivity_s_per_m=self.conductivity_s_per_m))

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','name','model','mesh','fem','modes','rf','acceleration']; keys(data,names,names,'axis-connected Hphi case')
        if data['format'] != 'superfish_ng_axis_hphi_case' or type(data['schema_version']) is not int or data['schema_version'] != 1:
            raise ValueError('expected superfish_ng_axis_hphi_case schema_version 1')
        expected=dict(physics='rf_eigenmode',coordinates='axisymmetric',azimuthal_index=0,
                      field_family='Hphi',material='vacuum',boundary='closed_pec')
        keys(data['model'],list(expected),list(expected),'axis-connected Hphi model')
        for name,value in expected.items():
            if type(data['model'][name]) is not type(value) or data['model'][name] != value:
                raise ValueError(f'axis-connected Hphi model.{name}: only {value!r} is implemented')
        names=['element_order']; keys(data['fem'],names,names,'axis-connected Hphi FEM')
        names=['stored_energy_j','conductivity_s_per_m']; keys(data['rf'],names,names,'axis-connected Hphi RF')
        acceleration=None if data['acceleration'] is None else AxisAccelerationPath.from_dict(data['acceleration'])
        return cls(AxisConnectedMesh.from_dict(data['mesh']),acceleration=acceleration,**data['fem'],modes=data['modes'],name=data['name'],
                   normalization_j=data['rf']['stored_energy_j'],conductivity_s_per_m=data['rf']['conductivity_s_per_m'])

    @classmethod
    def load(cls,path):
        from .project import parse_json
        return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))



def axis_hphi_matrices(case):
    if not isinstance(case,AxisHphiCase):raise ValueError('explicit AxisHphiCase required')
    return axis_connected_matrices(case.mesh,case.element_order)


def _eigenpairs(case,k,m):
    count,dimension=case.modes,k.shape[0]
    if count>dimension or (count==dimension and dimension>256):
        raise ValueError('axis Hphi mode count exceeds supported FEM dimension; refine or request fewer modes')
    d=1/np.sqrt(m.diagonal());scale=diags(d);a,b=(scale@v@scale for v in (k,m))
    try:
        if dimension<=64 or count==dimension:
            values,vectors=eigh(a.toarray(),b.toarray(),subset_by_index=(0,count-1))
        else:
            values,vectors=eigsh(a,k=count,M=b,sigma=0.,which='LM',tol=1e-11,maxiter=10000,
                v0=np.random.default_rng(20260905).normal(size=dimension))
    except ArpackNoConvergence as exc:
        raise ValueError('axis Hphi eigensolver did not converge; refine or recondition the mesh') from exc
    ordering=np.argsort(values);values,vectors=values[ordering],d[:,None]*vectors[:,ordering]
    if not np.isfinite(values).all() or np.any(values<=0):
        raise ValueError('axis-connected Hphi space requires a positive spectrum; no static mode may be discarded')
    vectors/=np.sqrt(np.sum(vectors*(m@vectors),axis=0))
    return values,vectors


@dataclass
class AxisHphiSolution:
    case: AxisHphiCase
    space: object
    stiffness: object
    mass: object
    eigenvalues: np.ndarray
    frequencies_hz: np.ndarray
    coefficients: np.ndarray
    residuals: np.ndarray
    orthogonality_error: float
    determinants: np.ndarray
    gradients: np.ndarray
    def fields_in_cells(self,cell_indices,barycentric,mode=0):
        integer(mode,'mode',0)
        if mode>=self.case.modes:raise ValueError('axis Hphi mode index is out of range')
        cells=np.asarray(cell_indices);bary=_numeric_coordinates(barycentric,3,'axis Hphi barycentric points')
        if (cells.ndim!=1 or cells.dtype.kind not in 'iu' or np.any(cells<0) or np.any(cells>=len(self.space.mesh.triangles))
            or bary.shape!=(len(cells),3) or not np.isfinite(bary).all() or np.any(bary<-1e-12)
            or not np.allclose(bary.sum(axis=1),1,rtol=0,atol=1e-12)):
            raise ValueError('axis Hphi fields require valid original cell indices and barycentric points')
        grad=self.gradients[cells]
        if self.case.element_order==1:values,gradients=bary,grad
        else:
            values=np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
            gradients=np.concatenate(((4*bary-1)[:,:,None]*grad,
                np.stack([4*(bary[:,i,None]*grad[:,j]+bary[:,j,None]*grad[:,i]) for i,j in ((0,1),(1,2),(2,0))],axis=1)),axis=1)
        c=self.coefficients[self.space.cell_dofs[cells],mode]
        u=np.einsum('ti,ti->t',values,c);du=np.einsum('tij,ti->tj',gradients,c)
        radius=np.einsum('ti,ti->t',bary,self.space.mesh.points[self.space.mesh.triangles[cells],0])
        omega=TAU*self.frequencies_hz[mode]
        result={f'{field}{axis}_{phase}_{unit}':np.zeros(len(cells)) for field,unit in (('E','V_per_m'),('H','A_per_m'))
                for axis in ('r','phi','z') for phase in ('real','quadrature')}
        result.update(Hphi_real_A_per_m=radius*u,Er_quadrature_V_per_m=radius*du[:,1]/(omega*EPS0),
                      Ez_quadrature_V_per_m=-(2*u+radius*du[:,0])/(omega*EPS0))
        if any(not np.isfinite(v).all() for v in result.values()):
            raise ValueError('axis Hphi fields exceed finite SI arithmetic')
        return result
    def fields_at(self,points_rz_m,mode=0):
        points = _numeric_coordinates(points_rz_m,2,'axis Hphi [r_m,z_m] probes')
        if np.any(points[:,0]<0):raise ValueError('axis Hphi probes require nonnegative physical radius')
        locator = PolygonLocator(SimpleNamespace(points_xy_m=self.space.mesh.points,triangles=self.space.mesh.triangles))
        try: cells,bary = locator.locate(points)
        except ValueError as exc:
            raise ValueError('Hphi probe is outside resolved vacuum, including any inner conductor') from exc
        return self.fields_in_cells(cells,bary,mode)


def restore_axis_hphi(case,space,k,m,coefficients,frequencies,*,verify_spectrum=True):
    c=np.asarray(coefficients);f=np.asarray(frequencies)
    if (c.dtype.kind!='f' or f.dtype.kind!='f' or c.shape!=(k.shape[0],case.modes) or f.shape!=(case.modes,)
        or not np.isfinite(c).all() or not np.isfinite(f).all() or np.any(f<=0) or np.any(np.diff(f)<0)):
        raise ValueError('invalid axis Hphi coefficients or ordered positive frequencies')
    norm=case.normalization_j/(MU0*np.pi)
    orth=float(np.max(abs(c.T@(m@c)/norm-np.eye(case.modes))))
    values=(TAU*f/C0)**2;residual=[]
    for mode,value in enumerate(values):
        kv,mv=k@c[:,mode],m@c[:,mode]
        residual.append(np.linalg.norm(kv-value*mv)/(np.linalg.norm(kv)+value*np.linalg.norm(mv)))
    if not np.isfinite([orth,*residual]).all() or orth>1e-8 or max(residual)>1e-8:
        raise ValueError('axis Hphi coefficients fail energy, orthogonality or FEM residual validation')
    if verify_spectrum:
        expected,_=_eigenpairs(case,k,m)
        if not np.allclose(values,expected,rtol=1e-8,atol=0):
            raise ValueError('axis Hphi frequencies are not the lowest positive FEM spectrum')
    _,det,grad=element_geometry(space.mesh)
    return AxisHphiSolution(case,space,k,m,values,f.copy(),c.copy(),np.array(residual),orth,det,grad)


def solve_axis_hphi(case):
    if not isinstance(case,AxisHphiCase):raise ValueError('explicit AxisHphiCase required')
    case=AxisHphiCase.from_dict(case.to_dict());space,k,m=axis_hphi_matrices(case)
    values,vectors=_eigenpairs(case,k,m)
    vectors*=np.sqrt(case.normalization_j/(MU0*np.pi))
    for mode in range(case.modes):
        if vectors[np.argmax(abs(vectors[:,mode])),mode]<0:vectors[:,mode]*=-1
    return restore_axis_hphi(case,space,k,m,vectors,C0/TAU*np.sqrt(values),verify_spectrum=False)

def axis_hphi_quantities(solution,mode=0):
    if not isinstance(solution,AxisHphiSolution): raise ValueError('axis Hphi RF requires AxisHphiSolution')
    case = solution.case; integer(mode,'mode',0)
    if mode >= case.modes: raise ValueError('axis Hphi mode index out of range')
    space = solution.space; declared = case.mesh
    cells = np.arange(len(space.mesh.triangles)); vertices = space.mesh.points[space.mesh.triangles]
    ue = 0.; um = 0.
    for bary,weight in triangle_quadrature(5):
        fields = solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)),mode)
        measure = TAU*(vertices[:,:,0]@bary)*weight*solution.determinants
        ue += EPS0/4*float(measure@(fields['Er_quadrature_V_per_m']**2+fields['Ez_quadrature_V_per_m']**2))
        um += MU0/4*float(measure@fields['Hphi_real_A_per_m']**2)
    endpoints = space.mesh.points[space.mesh.boundary_edges]
    length = np.linalg.norm(endpoints[:,1]-endpoints[:,0],axis=1)
    walls = np.zeros(len(declared.surface_area_m2_by_segment))
    nodes,weights = np.polynomial.legendre.leggauss(5)
    for node,weight in zip((nodes+1)/2,weights/2):
        bary = np.zeros((len(endpoints),3)); rows = np.arange(len(endpoints))
        bary[rows,declared.boundary_local_vertices[:,0]] = 1-node; bary[rows,declared.boundary_local_vertices[:,1]] = node
        h = solution.fields_in_cells(space.mesh.boundary_cells,bary,mode)['Hphi_real_A_per_m']
        radius = np.einsum('ti,ti->t',bary,space.mesh.points[space.mesh.triangles[space.mesh.boundary_cells],0])
        walls += np.bincount(declared.boundary_segments,weights=TAU*weight*length*radius*h*h,minlength=len(walls))
    components = []; offset = 0
    for contour in (declared.outer_rz_m,*declared.holes_rz_m):
        components.append(float(walls[offset:offset+len(contour)].sum())); offset += len(contour)
    f = float(solution.frequencies_hz[mode]); omega = TAU*f; energy = ue+um
    rs = float(np.sqrt(np.pi*f*MU0/case.conductivity_s_per_m)); wall = float(walls.sum()); loss = rs*wall/2
    if not np.isfinite([ue,um,*walls,loss]).all() or min(ue,um,wall,loss) <= 0:
        raise ValueError('invalid axis Hphi energy or total wall loss')
    result=dict(frequency_hz=f,stored_energy_j=energy,electric_energy_j=ue,magnetic_energy_j=um,
        wall_loss_w=loss,surface_resistance_ohm=rs,q0=omega*energy/loss,geometry_factor_ohm=2*omega*energy/wall,
        wall_h2_integral_a2_by_segment=walls.tolist(),wall_h2_integral_a2_by_component=components,
        volume_m3=declared.volume_m3,surface_area_m2_by_segment=declared.surface_area_m2_by_segment.tolist(),
        r_over_q_accelerator_ohm=None,r_over_q_circuit_ohm=None,vacc_v=None,eacc_v_per_m=None,
        accelerating_quantities_reason='no acceleration path is declared')

    if case.acceleration is not None:
        path=case.acceleration;edges=space.boundary_dofs[declared.axis_edges]
        ends=space.dof_points[edges[:,:2],1]
        values=-2*solution.coefficients[edges,mode]/(omega*EPS0)
        if case.element_order==1:values=np.column_stack((values,values.mean(axis=1)))
        voltage,absolute=quadratic_voltage(ends,values,omega/(path.beta*C0),
            interval=(path.z_start_m,path.z_end_m),phase_origin=path.phase_origin_m)
        voltage*=1j;rq=abs(voltage)**2/(omega*energy)
        if not np.isfinite([voltage.real,voltage.imag,absolute,rq,abs(voltage)/(path.z_end_m-path.z_start_m)]).all():
            raise ValueError('axis acceleration exceeds finite SI arithmetic')
        result.update(vacc_v=dict(real=voltage.real,imag=voltage.imag),
            eacc_v_per_m=abs(voltage)/(path.z_end_m-path.z_start_m),
            r_over_q_accelerator_ohm=rq,r_over_q_circuit_ohm=rq/2,
            accelerating_quantities_reason=None,axis_absolute_voltage_v=absolute)
    if not np.isfinite([result[key] for key in ('q0','geometry_factor_ohm','stored_energy_j','wall_loss_w')]).all():
        raise ValueError('axis Hphi RF exceeds finite SI arithmetic')
    return result

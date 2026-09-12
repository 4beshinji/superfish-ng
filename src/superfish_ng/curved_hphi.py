# SPDX-License-Identifier: Apache-2.0
"""Explicit quadratic-geometry vacuum Hphi eigenmodes, with original fields."""
from dataclasses import dataclass,field
from pathlib import Path
import numpy as np
from .config import keys,integer,positive
from .constants import C0,EPS0,MU0,TAU
from .axis_connected_mesh import AxisConnectedMesh
from .axis_hphi import AxisAccelerationPath,_eigenpairs as _axis_eigenpairs
from .coaxial import _numeric_coordinates,_eigenpairs as _positive_eigenpairs
from .curved_meridional_geometry import CurvedMeridionalGeometry,_polynomial,_minimum
from .curved_hphi_fem import curved_hphi_matrices
from .quadratic_geometry import QuadraticTriangle
from .curved_sampling import QuadraticLocator


@dataclass(frozen=True,eq=False)
class CurvedHphiCase:
    geometry: CurvedMeridionalGeometry
    element_order: int = 2
    quadrature_order: int = 12
    modes: int = 6
    normalization_j: float = 1.
    conductivity_s_per_m: float = 5.8e7
    name: str = 'explicit curved vacuum Hphi resonator'
    acceleration: AxisAccelerationPath | None = None
    bounds_rz_m: tuple = field(init=False)

    def __post_init__(self):
        if type(self.geometry) is not CurvedMeridionalGeometry:
            raise ValueError('CurvedHphiCase requires explicit validated quadratic meridional geometry')
        geometry=CurvedMeridionalGeometry.from_dict(self.geometry.to_dict())
        object.__setattr__(self,'geometry',geometry)
        if type(self.element_order) is not int or self.element_order not in (1,2):
            raise ValueError('curved Hphi element_order must be P1 or P2')
        if type(self.quadrature_order) is not int or not 2<=self.quadrature_order<=32:
            raise ValueError('curved Hphi quadrature_order must be an integer from 2 to 32')
        integer(self.modes,'curved Hphi modes')
        for name in ('normalization_j','conductivity_s_per_m'):object.__setattr__(self,name,positive(getattr(self,name),name))
        if not isinstance(self.name,str) or not self.name.strip():raise ValueError('curved Hphi name must be nonempty')
        if self.acceleration is not None:
            if not isinstance(geometry.base_mesh,AxisConnectedMesh) or type(self.acceleration) is not AxisAccelerationPath:
                raise ValueError('curved Hphi acceleration requires an explicit path on a connected vacuum axis')
            self.acceleration.__post_init__();a,b=geometry.base_mesh.axis_interval_m
            if not a<=self.acceleration.z_start_m<self.acceleration.z_end_m<=b:
                raise ValueError('curved acceleration interval must lie within the unchanged vacuum axis')
        bounds=[]
        for coordinate in (0,1):
            polynomials=[_polynomial(geometry.points_rz_m[nodes,coordinate]) for nodes in geometry.cell_nodes]
            low=min(_minimum(p) for p in polynomials)
            high=-min(_minimum({key:-v for key,v in p.items()}) for p in polynomials)
            bounds.append((float(low),float(high)))
        if not np.isfinite(bounds).all() or not all(a<b for a,b in bounds):
            raise ValueError('curved Hphi coordinate bounds exceed finite SI arithmetic')
        object.__setattr__(self,'bounds_rz_m',tuple(bounds))

    @property
    def axis_connected(self):return isinstance(self.geometry.base_mesh,AxisConnectedMesh)
    @property
    def inner_radius_m(self):return self.bounds_rz_m[0][0]
    @property
    def outer_radius_m(self):return self.bounds_rz_m[0][1]
    @property
    def length_m(self):return self.bounds_rz_m[1][1]-self.bounds_rz_m[1][0]

    def to_dict(self):
        return dict(format='superfish_ng_curved_hphi_case',schema_version=1,name=self.name,
            model=dict(physics='rf_eigenmode',coordinates='axisymmetric',azimuthal_index=0,
                       field_family='Hphi',material='vacuum',boundary='closed_pec'),
            geometry=self.geometry.to_dict(),fem=dict(element_order=self.element_order,quadrature_order=self.quadrature_order),
            modes=self.modes,rf=dict(stored_energy_j=self.normalization_j,conductivity_s_per_m=self.conductivity_s_per_m),
            acceleration=None if self.acceleration is None else self.acceleration.to_dict())

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','name','model','geometry','fem','modes','rf','acceleration'];keys(data,names,names,'curved Hphi case')
        if data['format']!='superfish_ng_curved_hphi_case' or type(data['schema_version']) is not int or data['schema_version']!=1:
            raise ValueError('expected superfish_ng_curved_hphi_case schema_version 1')
        expected=dict(physics='rf_eigenmode',coordinates='axisymmetric',azimuthal_index=0,field_family='Hphi',material='vacuum',boundary='closed_pec')
        keys(data['model'],list(expected),list(expected),'curved Hphi model')
        for name,value in expected.items():
            if type(data['model'][name]) is not type(value) or data['model'][name]!=value:
                raise ValueError(f'curved Hphi model.{name}: only {value!r} is implemented')
        keys(data['fem'],['element_order','quadrature_order'],['element_order','quadrature_order'],'curved Hphi FEM')
        keys(data['rf'],['stored_energy_j','conductivity_s_per_m'],['stored_energy_j','conductivity_s_per_m'],'curved Hphi RF')
        path=None if data['acceleration'] is None else AxisAccelerationPath.from_dict(data['acceleration'])
        return cls(CurvedMeridionalGeometry.from_dict(data['geometry']),**data['fem'],modes=data['modes'],name=data['name'],
            normalization_j=data['rf']['stored_energy_j'],conductivity_s_per_m=data['rf']['conductivity_s_per_m'],acceleration=path)

    @classmethod
    def load(cls,path):
        from .project import parse_json
        return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))


@dataclass
class CurvedHphiSolution:
    case: CurvedHphiCase
    space: object
    stiffness: object
    mass: object
    eigenvalues: np.ndarray
    frequencies_hz: np.ndarray
    coefficients: np.ndarray
    residuals: np.ndarray
    orthogonality_error: float
    nullspace_overlap: float | None
    quadrature_diagnostic: dict

    def __post_init__(self):
        self.local_maps=tuple(QuadraticTriangle(self.space.geometry.points_rz_m[n]) for n in self.space.geometry.cell_nodes)
        self._locators=None

    def mapped_points(self,cell_indices,barycentric):
        cells=np.asarray(cell_indices);bary=_numeric_coordinates(barycentric,3,'curved Hphi barycentric points')
        if (cells.ndim!=1 or cells.dtype.kind not in 'iu' or not len(cells) or np.any(cells<0) or np.any(cells>=len(self.local_maps))
            or bary.shape!=(len(cells),3) or np.any(bary<0) or not np.allclose(bary.sum(axis=1),1,rtol=0,atol=1e-13)):
            raise ValueError('curved Hphi fields require original cell indices and closed reference-triangle points')
        size=3 if self.case.element_order==1 else 6
        points=np.empty((len(cells),2));values=np.empty((len(cells),size));grad=np.empty((len(cells),size,2));det=np.empty(len(cells))
        for cell in np.unique(cells):
            selected=np.flatnonzero(cells==cell);mapped=self.local_maps[cell].evaluate(bary[selected,1:])
            points[selected]=mapped['points_rz_m'];det[selected]=mapped['determinant_m2']
            if self.case.element_order==2:
                values[selected]=mapped['basis_values'];grad[selected]=mapped['basis_gradients']
            else:
                values[selected]=bary[selected]
                grad[selected]=np.einsum('ia,qab->qib',np.array([[-1.,-1.],[1.,0.],[0.,1.]]),np.linalg.inv(mapped['jacobian']))
        return points,values,grad,det

    def fields_in_cells(self,cell_indices,barycentric,mode=0):
        integer(mode,'curved Hphi mode',0)
        if mode>=self.case.modes:raise ValueError('curved Hphi mode index is out of range')
        points,values,grad,det=self.mapped_points(cell_indices,barycentric)
        c=self.coefficients[self.space.cell_dofs[np.asarray(cell_indices)],mode]
        scalar=np.einsum('qi,qi->q',values,c);derivative=np.einsum('qia,qi->qa',grad,c)
        r=points[:,0];omega=TAU*self.frequencies_hz[mode]
        fields={f'{field}{axis}_{phase}_{unit}':np.zeros(len(points)) for field,unit in (('E','V_per_m'),('H','A_per_m'))
                for axis in ('r','phi','z') for phase in ('real','quadrature')}
        if self.case.axis_connected:
            fields.update(Hphi_real_A_per_m=r*scalar,Er_quadrature_V_per_m=r*derivative[:,1]/(omega*EPS0),
                          Ez_quadrature_V_per_m=-(2*scalar+r*derivative[:,0])/(omega*EPS0))
        else:
            if np.any(r<=0):raise ValueError('positive-radius curved Hphi field reached the axis')
            fields.update(Hphi_real_A_per_m=scalar/r,Er_quadrature_V_per_m=derivative[:,1]/(omega*EPS0*r),
                          Ez_quadrature_V_per_m=-derivative[:,0]/(omega*EPS0*r))
        if any(not np.isfinite(v).all() for v in fields.values()):raise ValueError('curved Hphi fields exceed finite SI arithmetic')
        return fields

    def fields_at(self,points_rz_m,mode=0,*,max_iterations=30,max_boxes=1024):
        points=_numeric_coordinates(points_rz_m,2,'curved Hphi [r_m,z_m] probes')
        if not len(points) or np.any(points[:,0]<0):raise ValueError('curved Hphi probes require nonempty nonnegative-radius points')
        if type(max_iterations) is not int or max_iterations<1 or type(max_boxes) is not int or max_boxes<1:
            raise ValueError('curved inverse limits must be positive integers')
        if self._locators is None:
            locators=[QuadraticLocator(m) for m in self.local_maps]
            self._locators=(locators,np.array([l.origin+l.scale*l.lower for l in locators]),np.array([l.origin+l.scale*l.upper for l in locators]))
        locators,lower,upper=self._locators;cells=[];bary=[]
        for index,point in enumerate(points):
            if self.case.axis_connected and point[0]==0:
                # Axis maps are explicitly affine: invert their z interval
                # directly so Newton roundoff cannot create a nonzero Hphi/Er.
                g=self.space.geometry;base=g.base_mesh
                edges=np.flatnonzero(g.boundary_tags=='axis')
                ends=g.points_rz_m[g.boundary_nodes[edges,:2],1]
                matching=edges[(ends.min(axis=1)<=point[1])&(point[1]<=ends.max(axis=1))]
                if not len(matching):raise ValueError(f'curved Hphi probe {index} lies outside the declared vacuum axis')
                edge=min(matching,key=lambda e:int(base.boundary_cells[e]))
                cell=int(base.boundary_cells[edge]);a,b=base.boundary_local_vertices[edge]
                za,zb=g.points_rz_m[g.boundary_nodes[edge,:2],1];t=(point[1]-za)/(zb-za)
                row=np.zeros(3);row[a]=1-t;row[b]=t
                cells.append(cell);bary.append(row);continue
            unresolved=[];found=False
            for cell in np.flatnonzero(np.all(point>=lower,axis=1)&np.all(point<=upper,axis=1)):
                try:reference=locators[cell].inverse(point,max_iterations=max_iterations,max_boxes=max_boxes)
                except ValueError as exc:unresolved.append(str(exc));continue
                if reference is not None:
                    cells.append(cell);bary.append([1-reference.sum(),*reference]);found=True;break
            if not found:
                if unresolved:raise ValueError(f'curved Hphi probe {index} UNVERIFIED: {unresolved[0]}')
                raise ValueError(f'curved Hphi probe {index} lies outside the mapped vacuum, including any inner conductor')
        return self.fields_in_cells(np.asarray(cells),np.asarray(bary),mode)


def _restore_curved_hphi(case,space,k,m,diagnostic,coefficients,frequencies,*,verify_spectrum=True):
    c=np.asarray(coefficients);f=np.asarray(frequencies)
    if (c.dtype.kind!='f' or f.dtype.kind!='f' or c.shape!=(k.shape[0],case.modes) or f.shape!=(case.modes,)
        or not np.isfinite(c).all() or not np.isfinite(f).all() or np.any(f<=0) or np.any(np.diff(f)<0)):
        raise ValueError('invalid curved Hphi coefficients or ordered positive frequencies')
    norm=case.normalization_j/(MU0*np.pi);orth=float(np.max(abs(c.T@(m@c)/norm-np.eye(case.modes))))
    null=None
    if not case.axis_connected:
        one=np.ones(len(c));null=float(np.max(abs(one@(m@c)))/np.sqrt((one@(m@one))*norm))
        if not np.isfinite(null) or null>1e-8:raise ValueError('curved Hphi coefficients contain static circulation')
    values=(TAU*f/C0)**2;residual=[]
    for mode,value in enumerate(values):
        kv,mv=k@c[:,mode],m@c[:,mode]
        residual.append(np.linalg.norm(kv-value*mv)/(np.linalg.norm(kv)+value*np.linalg.norm(mv)))
    if not np.isfinite([orth,*residual]).all() or orth>1e-8 or max(residual)>1e-8:
        raise ValueError('curved Hphi coefficients fail energy, orthogonality or original FEM residual validation')
    if verify_spectrum:
        expected,_=(_axis_eigenpairs if case.axis_connected else _positive_eigenpairs)(case,k,m)
        if not np.allclose(values,expected,rtol=1e-8,atol=0):raise ValueError('curved Hphi frequencies are not the lowest positive FEM spectrum')
    return CurvedHphiSolution(case,space,k,m,values,f.copy(),c.copy(),np.array(residual),orth,null,diagnostic)


def solve_curved_hphi(case):
    if type(case) is not CurvedHphiCase:raise ValueError('explicit CurvedHphiCase required')
    case=CurvedHphiCase.from_dict(case.to_dict())
    space,k,m,diagnostic=curved_hphi_matrices(case.geometry,case.element_order,quadrature_order=case.quadrature_order)
    values,vectors=(_axis_eigenpairs if case.axis_connected else _positive_eigenpairs)(case,k,m)
    vectors*=np.sqrt(case.normalization_j/(MU0*np.pi))
    for mode in range(case.modes):
        if vectors[np.argmax(abs(vectors[:,mode])),mode]<0:vectors[:,mode]*=-1
    return _restore_curved_hphi(case,space,k,m,diagnostic,vectors,C0/TAU*np.sqrt(values),verify_spectrum=False)


def restore_curved_hphi(case,coefficients,frequencies):
    """Rebuild the declared FEM and verify its lowest positive stored spectrum."""
    if type(case) is not CurvedHphiCase:raise ValueError('explicit CurvedHphiCase required')
    case=CurvedHphiCase.from_dict(case.to_dict())
    space,k,m,diagnostic=curved_hphi_matrices(case.geometry,case.element_order,quadrature_order=case.quadrature_order)
    return _restore_curved_hphi(case,space,k,m,diagnostic,coefficients,frequencies,verify_spectrum=True)

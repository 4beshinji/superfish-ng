# SPDX-License-Identifier: Apache-2.0
"""Piecewise lossless material Hphi FEM, original one-sided E/H/B and energy."""
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from .config import keys,integer,positive
from .constants import C0,EPS0,MU0,TAU
from .rf_materials import RFMaterialPartition
from .material_hphi_fem import material_hphi_matrices
from .axis_connected_mesh import AxisConnectedMesh
from .axis_hphi import AxisAccelerationPath,_eigenpairs as _axis_eigenpairs
from .coaxial import _numeric_coordinates,_eigenpairs as _positive_eigenpairs
from .mesh import element_geometry
from .planar_polygon import PolygonLocator


@dataclass(frozen=True,eq=False)
class MaterialHphiCase:
    partition: RFMaterialPartition
    element_order: int = 2
    quadrature_order: int = 12
    modes: int = 6
    normalization_j: float = 1.
    conductivity_s_per_m: float = 5.8e7
    name: str = 'piecewise lossless material Hphi resonator'
    acceleration: AxisAccelerationPath | None = None

    def __post_init__(self):
        if type(self.partition) is not RFMaterialPartition:
            raise ValueError('MaterialHphiCase requires an explicit RFMaterialPartition')
        object.__setattr__(self,'partition',RFMaterialPartition.from_dict(self.partition.to_dict()))
        for name in ('element_order','quadrature_order','modes'):integer(getattr(self,name),'material Hphi '+name)
        if self.element_order not in (1,2) or not 4<=self.quadrature_order<=32:
            raise ValueError('material Hphi requires P1/P2 and quadrature_order from 4 to 32')
        for name in ('normalization_j','conductivity_s_per_m'):object.__setattr__(self,name,positive(getattr(self,name),name))
        if type(self.name) is not str or not self.name.strip():raise ValueError('material Hphi name must be nonempty')
        if self.acceleration is not None:
            if not self.axis_connected or type(self.acceleration) is not AxisAccelerationPath:
                raise ValueError('material Hphi acceleration requires an explicit vacuum-axis interval')
            self.acceleration.__post_init__();a,b=self.partition.mesh.axis_interval_m
            path=self.acceleration
            if not a<=path.z_start_m<path.z_end_m<=b:
                raise ValueError('acceleration interval must lie within the declared axis')
            mesh=self.partition.mesh;edges=mesh.axis_edges
            ends=mesh.points_rz_m[mesh.boundary_edges[edges],1]
            intersects=np.maximum(ends.min(axis=1),path.z_start_m)<np.minimum(ends.max(axis=1),path.z_end_m)
            owners=mesh.boundary_cells[edges[intersects]]
            if not len(owners) or np.any(self.partition.epsilon_r[owners]!=1) or np.any(self.partition.mu_r[owners]!=1):
                raise ValueError('acceleration requires vacuum epsilon_r=mu_r=1 on every axis segment in the interval')

    @property
    def axis_connected(self):return isinstance(self.partition.mesh,AxisConnectedMesh)
    @property
    def length_m(self):return float(np.ptp(self.partition.mesh.points_rz_m[:,1]))
    @property
    def inner_radius_m(self):return float(self.partition.mesh.points_rz_m[:,0].min())
    @property
    def outer_radius_m(self):return float(self.partition.mesh.points_rz_m[:,0].max())

    def to_dict(self):
        return dict(format='superfish_ng_material_hphi_case',schema_version=1,name=self.name,
            model=dict(physics='rf_eigenmode',coordinates='axisymmetric',azimuthal_index=0,field_family='Hphi',
                       material='piecewise_lossless_linear_isotropic',boundary='closed_pec'),
            partition=self.partition.to_dict(),fem=dict(element_order=self.element_order,quadrature_order=self.quadrature_order),
            modes=self.modes,rf=dict(stored_energy_j=self.normalization_j,conductivity_s_per_m=self.conductivity_s_per_m,
                                    wall_relative_permeability=1.),
            acceleration=None if self.acceleration is None else self.acceleration.to_dict())

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','name','model','partition','fem','modes','rf','acceleration'];keys(data,names,names,'material Hphi case')
        if data['format']!='superfish_ng_material_hphi_case' or type(data['schema_version']) is not int or data['schema_version']!=1:
            raise ValueError('expected superfish_ng_material_hphi_case schema_version 1')
        expected=dict(physics='rf_eigenmode',coordinates='axisymmetric',azimuthal_index=0,field_family='Hphi',
                      material='piecewise_lossless_linear_isotropic',boundary='closed_pec')
        keys(data['model'],list(expected),list(expected),'material Hphi model')
        for name,value in expected.items():
            if type(data['model'][name]) is not type(value) or data['model'][name]!=value:
                raise ValueError(f'material Hphi model.{name}: only {value!r} is implemented')
        names=['element_order','quadrature_order'];keys(data['fem'],names,names,'material Hphi FEM')
        names=['stored_energy_j','conductivity_s_per_m','wall_relative_permeability'];keys(data['rf'],names,names,'material Hphi RF')
        if positive(data['rf']['wall_relative_permeability'],'wall_relative_permeability')!=1:
            raise ValueError('material Hphi wall loss supports only nonmagnetic wall metal, wall_relative_permeability=1')
        path=None if data['acceleration'] is None else AxisAccelerationPath.from_dict(data['acceleration'])
        return cls(RFMaterialPartition.from_dict(data['partition']),**data['fem'],modes=data['modes'],name=data['name'],
            normalization_j=data['rf']['stored_energy_j'],conductivity_s_per_m=data['rf']['conductivity_s_per_m'],acceleration=path)

    @classmethod
    def load(cls,path):
        from .project import parse_json
        return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))


@dataclass
class MaterialHphiSolution:
    case: MaterialHphiCase
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
        _,self.determinants,self.gradients=element_geometry(self.space.mesh)
        self._locator=PolygonLocator(SimpleNamespace(points_xy_m=self.space.mesh.points,triangles=self.space.mesh.triangles))

    def fields_in_cells(self,cell_indices,barycentric,mode=0):
        integer(mode,'material Hphi mode',0)
        if mode>=self.case.modes:raise ValueError('material Hphi mode index is out of range')
        cells=np.asarray(cell_indices);bary=_numeric_coordinates(barycentric,3,'material Hphi barycentric points')
        if (cells.ndim!=1 or cells.dtype.kind not in 'iu' or not len(cells) or np.any(cells<0) or np.any(cells>=len(self.space.mesh.triangles))
            or bary.shape!=(len(cells),3) or np.any(bary<-1e-12) or not np.allclose(bary.sum(axis=1),1,rtol=0,atol=1e-12)):
            raise ValueError('material Hphi fields require original cell indices and closed reference-triangle points')
        gradient=self.gradients[cells]
        if self.case.element_order==1:values,derivatives=bary,gradient
        else:
            values=np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
            derivatives=np.concatenate(((4*bary-1)[:,:,None]*gradient,
                np.stack([4*(bary[:,i,None]*gradient[:,j]+bary[:,j,None]*gradient[:,i]) for i,j in ((0,1),(1,2),(2,0))],axis=1)),axis=1)
        c=self.coefficients[self.space.cell_dofs[cells],mode]
        scalar=np.einsum('qi,qi->q',values,c);derivative=np.einsum('qia,qi->qa',derivatives,c)
        r=np.einsum('qi,qi->q',bary,self.space.mesh.points[self.space.mesh.triangles[cells],0])
        omega=TAU*self.frequencies_hz[mode];eps=self.case.partition.epsilon_r[cells];mu=self.case.partition.mu_r[cells]
        fields={f'{field}{axis}_{phase}_{unit}':np.zeros(len(cells))
                for field,unit in (('E','V_per_m'),('H','A_per_m'),('B','T')) for axis in ('r','phi','z') for phase in ('real','quadrature')}
        if self.case.axis_connected:
            fields.update(Hphi_real_A_per_m=r*scalar,Er_quadrature_V_per_m=r*derivative[:,1]/(omega*EPS0*eps),
                          Ez_quadrature_V_per_m=-(2*scalar+r*derivative[:,0])/(omega*EPS0*eps))
        else:
            if np.any(r<=0):raise ValueError('positive-radius material Hphi field reached the axis')
            fields.update(Hphi_real_A_per_m=scalar/r,Er_quadrature_V_per_m=derivative[:,1]/(omega*EPS0*eps*r),
                          Ez_quadrature_V_per_m=-derivative[:,0]/(omega*EPS0*eps*r))
        fields['Bphi_real_T']=MU0*mu*fields['Hphi_real_A_per_m']
        if any(not np.isfinite(v).all() for v in fields.values()):raise ValueError('material Hphi fields exceed finite SI arithmetic')
        return fields

    def locate_points(self,points_rz_m):
        points=_numeric_coordinates(points_rz_m,2,'material Hphi [r_m,z_m] probes')
        if not len(points) or np.any(points[:,0]<0):raise ValueError('material Hphi probes require nonempty nonnegative-radius points')
        try:cells,bary=self._locator.locate(points)
        except ValueError as exc:raise ValueError('material Hphi probe is outside the declared material domain, including any conductor') from exc
        # PolygonLocator establishes exact membership first. A point on the
        # physical axis has exactly zero radial barycentric contribution.
        for index in np.flatnonzero(points[:,0]==0):
            vertices=self.space.mesh.points[self.space.mesh.triangles[cells[index]]]
            axis=np.flatnonzero(vertices[:,0]==0)
            if len(axis)==2:
                a,b=axis;t=(points[index,1]-vertices[a,1])/(vertices[b,1]-vertices[a,1]);bary[index]=0.;bary[index,a]=1-t;bary[index,b]=t
            elif len(axis)==1:bary[index]=0.;bary[index,axis[0]]=1.
        return points,cells,bary

    def fields_at(self,points_rz_m,mode=0):
        _,cells,bary=self.locate_points(points_rz_m)
        return self.fields_in_cells(cells,bary,mode)

    def probe_at(self,points_rz_m,mode=0):
        points,cells,bary=self.locate_points(points_rz_m);p=self.case.partition;owners=p.cell_region_indices[cells]
        return dict(points_rz_m=points.tolist(),cell_indices=cells.tolist(),barycentric=bary.tolist(),
            region_ids=[p.regions[i].id for i in owners],material_ids=[p.regions[i].material for i in owners],
            epsilon_r=p.epsilon_r[cells].tolist(),mu_r=p.mu_r[cells].tolist(),
            fields={k:v.tolist() for k,v in self.fields_in_cells(cells,bary,mode).items()},
            convention='peak exp(+i*omega*t); field=real+i*quadrature; Hphi real; Er/Ez quadrature; B=mu0*mu_r(cell)*H',
            interface_policy='lowest original cell index at shared edges; one-sided values, no averaging')


def _restore_material_hphi(case,space,k,m,diagnostic,coefficients,frequencies,*,verify_spectrum=True):
    c=np.asarray(coefficients);f=np.asarray(frequencies)
    if (c.dtype.kind!='f' or f.dtype.kind!='f' or c.shape!=(k.shape[0],case.modes) or f.shape!=(case.modes,)
        or not np.isfinite(c).all() or not np.isfinite(f).all() or np.any(f<=0) or np.any(np.diff(f)<0)):
        raise ValueError('invalid material Hphi coefficients or ordered positive frequencies')
    norm=case.normalization_j/(MU0*np.pi);orth=float(np.max(abs(c.T@(m@c)/norm-np.eye(case.modes))))
    null=None
    if not case.axis_connected:
        one=np.ones(len(c));null=float(np.max(abs(one@(m@c)))/np.sqrt((one@(m@one))*norm))
        if not np.isfinite(null) or null>1e-8:raise ValueError('material Hphi coefficients contain static circulation')
    values=(TAU*f/C0)**2;residual=[]
    for mode,value in enumerate(values):
        kv,mv=k@c[:,mode],m@c[:,mode]
        residual.append(np.linalg.norm(kv-value*mv)/(np.linalg.norm(kv)+value*np.linalg.norm(mv)))
    if not np.isfinite([orth,*residual]).all() or orth>1e-8 or max(residual)>1e-8:
        raise ValueError('material Hphi coefficients fail energy, orthogonality or original FEM residual validation')
    if verify_spectrum:
        expected,_=(_axis_eigenpairs if case.axis_connected else _positive_eigenpairs)(case,k,m)
        if not np.allclose(values,expected,rtol=1e-8,atol=0):raise ValueError('material Hphi frequencies are not the lowest positive FEM spectrum')
    return MaterialHphiSolution(case,space,k,m,values,f.copy(),c.copy(),np.array(residual),orth,null,diagnostic)


def solve_material_hphi(case):
    if type(case) is not MaterialHphiCase:raise ValueError('explicit MaterialHphiCase required')
    case=MaterialHphiCase.from_dict(case.to_dict());space,k,m,diagnostic=material_hphi_matrices(case.partition,case.element_order,quadrature_order=case.quadrature_order)
    values,vectors=(_axis_eigenpairs if case.axis_connected else _positive_eigenpairs)(case,k,m)
    vectors*=np.sqrt(case.normalization_j/(MU0*np.pi))
    for mode in range(case.modes):
        if vectors[np.argmax(abs(vectors[:,mode])),mode]<0:vectors[:,mode]*=-1
    return _restore_material_hphi(case,space,k,m,diagnostic,vectors,C0/TAU*np.sqrt(values),verify_spectrum=False)


def restore_material_hphi(case,coefficients,frequencies):
    if type(case) is not MaterialHphiCase:raise ValueError('explicit MaterialHphiCase required')
    case=MaterialHphiCase.from_dict(case.to_dict());space,k,m,diagnostic=material_hphi_matrices(case.partition,case.element_order,quadrature_order=case.quadrature_order)
    return _restore_material_hphi(case,space,k,m,diagnostic,coefficients,frequencies)

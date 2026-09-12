# SPDX-License-Identifier: Apache-2.0
"""Axis-connected magnetostatics in a=Aphi/r with original SI fields and flux."""
from dataclasses import dataclass,field
from types import SimpleNamespace,MappingProxyType
import numpy as np
from scipy.sparse.linalg import spsolve
from .config import keys,integer
from .constants import TAU
from .axis_magnetic_materials import AxisMagneticPartition
from .axis_magnetostatic_boundary import AxisMagnetostaticBoundary,finite_signed,validate_axis_magnetic_boundaries
from .magnetostatic_boundary import magnetic_field_coordinates
from .coaxial import _numeric_coordinates
from .magnetostatic_fem import axis_magnetostatic_forms
from .mesh import element_geometry
from .fem import triangle_quadrature
from .planar_polygon import PolygonLocator


@dataclass(frozen=True,eq=False)
class AxisMagnetostaticCase:
    partition: AxisMagneticPartition
    current_density_phi_a_per_m2: dict
    boundaries: tuple
    element_order: int = 2
    quadrature_order: int = 4
    name: str = 'axis magnetostatic'
    boundary_owner_indices: np.ndarray = field(init=False,repr=False)

    def __post_init__(self):
        if type(self.partition) is not AxisMagneticPartition:raise ValueError('explicit axis magnetic partition required')
        partition=AxisMagneticPartition.from_dict(self.partition.to_dict());object.__setattr__(self,'partition',partition)
        names=[r.id for r in partition.regions];data=dict(self.current_density_phi_a_per_m2) if isinstance(self.current_density_phi_a_per_m2,MappingProxyType) else self.current_density_phi_a_per_m2
        keys(data,names,names,'axis magnetostatic current_density_phi_a_per_m2 by region')
        current={name:finite_signed(data[name],'azimuthal current density Jphi for '+name+' [A/m^2]') for name in names}
        object.__setattr__(self,'current_density_phi_a_per_m2',MappingProxyType(current))
        boundaries,owners=validate_axis_magnetic_boundaries(partition.mesh,self.boundaries)
        object.__setattr__(self,'boundaries',boundaries);object.__setattr__(self,'boundary_owner_indices',owners)
        integer(self.element_order,'axis magnetostatic element_order');integer(self.quadrature_order,'axis magnetostatic quadrature_order')
        if self.element_order not in (1,2) or not 4<=self.quadrature_order<=32:raise ValueError('axis magnetostatic Case requires P1/P2 and quadrature_order from 4 to 32')
        if type(self.name) is not str or not self.name.strip():raise ValueError('axis magnetostatic name must be nonempty')

    def to_dict(self):
        return dict(format='superfish_ng_axis_magnetostatic_case',schema_version=1,physics='linear_magnetostatic',
            name=self.name,partition=self.partition.to_dict(),current_density_phi_a_per_m2=dict(self.current_density_phi_a_per_m2),
            boundaries=[b.to_dict() for b in self.boundaries],element_order=self.element_order,quadrature_order=self.quadrature_order)

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','physics','name','partition','current_density_phi_a_per_m2','boundaries','element_order','quadrature_order']
        keys(data,names,names,'axis magnetostatic Case')
        if (data['format']!='superfish_ng_axis_magnetostatic_case' or type(data['schema_version']) is not int
            or data['schema_version']!=1 or data['physics']!='linear_magnetostatic'):
            raise ValueError('expected superfish_ng_axis_magnetostatic_case version 1, linear_magnetostatic physics')
        if type(data['boundaries']) is not list:raise ValueError('axis magnetostatic boundaries must be a JSON list')
        return cls(AxisMagneticPartition.from_dict(data['partition']),data['current_density_phi_a_per_m2'],
            tuple(AxisMagnetostaticBoundary.from_dict(b) for b in data['boundaries']),data['element_order'],data['quadrature_order'],data['name'])


def _edge_quadrature(space,index):
    mesh=space.partition.mesh;edge=mesh.boundary_edges[index];owner=mesh.boundary_cells[index]
    a,b=mesh.points_rz_m[edge];delta=b-a;length=np.linalg.norm(delta)
    nodes,weights=np.polynomial.legendre.leggauss(4);t=(nodes+1)/2;weights=weights/2
    local=mesh.boundary_local_vertices[index];bary=np.zeros((len(t),3));bary[:,local[0]]=1-t;bary[:,local[1]]=t
    radius=((1-t[:,None])*a+t[:,None]*b)[:,0]
    values=bary if space.element_order==1 else np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
    # Domain on the left in r,z coordinates; holes have clockwise tangents.
    outward=np.array([delta[1],-delta[0]])/length
    return owner,bary,values,length*weights,radius,outward


@dataclass(eq=False)
class AxisMagnetostaticSolution:
    case: AxisMagnetostaticCase
    space: object
    stiffness: object
    volume_load_a_m2: np.ndarray
    boundary_load_a_m2: np.ndarray
    aphi_over_r_t: np.ndarray
    free_dofs: np.ndarray
    fixed_boundary_dofs: dict
    assembly_report: dict
    relative_residual: float

    def __post_init__(self):
        _,self._determinants,self._gradients=element_geometry(self.space.mesh)
        self._locator=PolygonLocator(SimpleNamespace(points_xy_m=self.space.mesh.points,triangles=self.space.mesh.triangles))

    def fields_in_cells(self,cell_indices,barycentric):
        cells,bary=magnetic_field_coordinates(cell_indices,barycentric,len(self.space.cell_dofs));gradient=self._gradients[cells]
        if self.case.element_order==1:values,derivatives=bary,gradient
        else:
            values=np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
            derivatives=np.concatenate(((4*bary-1)[:,:,None]*gradient,
                np.stack([4*(bary[:,i,None]*gradient[:,j]+bary[:,j,None]*gradient[:,i]) for i,j in ((0,1),(1,2),(2,0))],axis=1)),axis=1)
        coefficients=self.aphi_over_r_t[self.space.cell_dofs[cells]];regular=np.einsum('qi,qi->q',values,coefficients)
        gradient=np.einsum('qia,qi->qa',derivatives,coefficients);radius=np.einsum('qi,qi->q',bary,self.space.mesh.points[self.space.mesh.triangles[cells],0])
        magnetic=np.column_stack((-radius*gradient[:,1],2*regular+radius*gradient[:,0]));intensity=self.case.partition.reluctivity_m_per_h[cells,None]*magnetic
        fields=dict(Aphi_over_r_T=regular,Aphi_Wb_per_m=radius*regular,Br_T=magnetic[:,0],Bz_T=magnetic[:,1],Hr_A_per_m=intensity[:,0],Hz_A_per_m=intensity[:,1])
        if any(not np.isfinite(v).all() for v in fields.values()):raise ValueError('axis magnetostatic fields exceed finite SI arithmetic')
        return fields

    def probe_at(self,points_rz_m):
        points=_numeric_coordinates(points_rz_m,2,'axis magnetostatic probe coordinates')
        if points.dtype.kind not in 'fi' or points.ndim!=2 or points.shape[1]!=2 or not len(points) or not np.isfinite(points).all() or np.any(points[:,0]<0):
            raise ValueError('axis magnetostatic probes require finite [r_m,z_m] points with nonnegative radius')
        try:cells,bary=self._locator.locate(points)
        except ValueError as exc:raise ValueError('axis magnetostatic probe is outside the magnetic domain, including any excluded hole') from exc
        p=self.case.partition;owners=p.cell_region_indices[cells]
        return dict(points_rz_m=points.tolist(),cell_indices=cells.tolist(),barycentric=bary.tolist(),
            region_ids=[p.regions[i].id for i in owners],material_ids=[p.regions[i].material for i in owners],mu_r=p.mu_r[cells].tolist(),
            fields={k:v.tolist() for k,v in self.fields_in_cells(cells,bary).items()},
            convention='a=Aphi/r[T], Aphi=r*a[Wb/m], Br=-r*d_z(a)[T], Bz=2*a+r*d_r(a)[T], H=reluctivity(cell)*B[A/m]',
            interface_policy='lowest original cell index at shared edges; one-sided values, no averaging')


def solve_axis_magnetostatic(case):
    if type(case) is not AxisMagnetostaticCase:raise ValueError('explicit AxisMagnetostaticCase required')
    case=AxisMagnetostaticCase.from_dict(case.to_dict())
    space,k,volume,report=axis_magnetostatic_forms(case.partition,dict(case.current_density_phi_a_per_m2),case.element_order,quadrature_order=case.quadrature_order)
    boundary_load=np.zeros(len(volume));coefficients=np.zeros(len(volume));fixed=np.zeros(len(volume),dtype=bool);fixed_boundaries={}
    for boundary in case.boundaries:
        if boundary.kind=='fixed_aphi_over_r':
            dofs=np.unique(space.boundary_dofs[list(boundary.edge_indices)]);fixed[dofs]=True;coefficients[dofs]=boundary.value;fixed_boundaries[boundary.id]=dofs
        elif boundary.kind=='tangential_h':
            for edge in boundary.edge_indices:
                owner,_,values,line,radius,_=_edge_quadrature(space,edge)
                np.add.at(boundary_load,space.cell_dofs[owner],boundary.value*(values.T@(TAU*radius**2*line)))
    free=np.flatnonzero(~fixed);total=volume+boundary_load
    if len(free):coefficients[free]=spsolve(k[free][:,free],total[free]-(k@coefficients)[free])
    force=k@coefficients;denominator=np.linalg.norm(force)+np.linalg.norm(total)
    residual=float(np.linalg.norm((force-total)[free])/denominator) if denominator else 0.
    if not np.isfinite(coefficients).all() or not np.isfinite(residual) or residual>1e-10:
        raise ValueError('axis magnetic solve failed finite free-DOF residual validation')
    for array in (coefficients,volume,boundary_load,free,*fixed_boundaries.values()):array.setflags(write=False)
    solution=AxisMagnetostaticSolution(case,space,k,volume,boundary_load,coefficients,free,MappingProxyType(fixed_boundaries),report,residual)
    axis_magnetostatic_quantities(solution)
    return solution


def axis_magnetostatic_quantities(solution):
    if type(solution) is not AxisMagnetostaticSolution:raise ValueError('AxisMagnetostaticSolution required')
    s=solution;case=s.case;p=case.partition;cells=np.arange(len(p.mesh.triangles));vertices=p.mesh.points_rz_m[p.mesh.triangles]
    cell_energy=np.zeros(len(cells));constant_test=constant_scale=0.
    for bary,weight in triangle_quadrature(case.quadrature_order+4):
        fields=s.fields_in_cells(cells,np.tile(bary,(len(cells),1)));measure=TAU*(vertices[:,:,0]@bary)*weight*s._determinants
        cell_energy+=.5*p.reluctivity_m_per_h*(fields['Br_T']**2+fields['Bz_T']**2)*measure
        constant_test+=float(2*fields['Hz_A_per_m']@measure);constant_scale+=float(2*abs(fields['Hz_A_per_m'])@measure)
    energy=float(cell_energy.sum());region_energy=np.bincount(p.cell_region_indices,weights=cell_energy,minlength=len(p.regions))
    reaction=s.stiffness@s.aphi_over_r_t-s.volume_load_a_m2-s.boundary_load_a_m2
    fixed_reaction={name:float(reaction[dofs].sum()) for name,dofs in s.fixed_boundary_dofs.items()};fixed_original=dict.fromkeys(fixed_reaction,0.)
    circulation={b.id:0. for b in case.boundaries};flux=dict.fromkeys(circulation,0.);weighted_h=dict.fromkeys(circulation,0.);flux_scale=0.
    for index in range(len(p.mesh.boundary_edges)):
        owner,bary,_,line,radius,normal=_edge_quadrature(s.space,index);fields=s.fields_in_cells(np.full(len(bary),owner,dtype=int),bary)
        tangent=np.array([-normal[1],normal[0]]);ht=fields['Hr_A_per_m']*tangent[0]+fields['Hz_A_per_m']*tangent[1]
        boundary=case.boundaries[case.boundary_owner_indices[index]];circulation[boundary.id]+=float(line@ht)
        weighted=float((TAU*radius**2*line)@ht);weighted_h[boundary.id]+=weighted
        if boundary.kind=='fixed_aphi_over_r':fixed_original[boundary.id]+=weighted
        surface=TAU*radius*line;flux[boundary.id]+=float(surface@(fields['Br_T']*normal[0]+fields['Bz_T']*normal[1]))
        flux_scale+=float(surface@np.hypot(fields['Br_T'],fields['Bz_T']))
    current=float(sum(case.current_density_phi_a_per_m2[r.id]*area for r,area in zip(p.regions,p.region_area_m2)))
    source_work=float(s.aphi_over_r_t@s.volume_load_a_m2);boundary_work=float(s.aphi_over_r_t@s.boundary_load_a_m2)
    fixed_work=sum(b.value*fixed_reaction[b.id] for b in case.boundaries if b.kind=='fixed_aphi_over_r')
    energy_scale=2*energy+abs(source_work)+abs(boundary_work)+abs(fixed_work)
    energy_error=float(abs(2*energy-source_work-boundary_work-fixed_work)/energy_scale) if energy_scale else 0.
    moment_balance=constant_test-float(s.volume_load_a_m2.sum())-float(s.boundary_load_a_m2.sum())-sum(fixed_reaction.values())
    moment_scale=constant_scale+float(abs(s.volume_load_a_m2).sum())+float(abs(s.boundary_load_a_m2).sum())+sum(abs(v) for v in fixed_reaction.values())
    moment_error=abs(moment_balance)/moment_scale if moment_scale else abs(moment_balance)
    divergence_error=float(abs(sum(flux.values()))/flux_scale) if flux_scale else float(abs(sum(flux.values())))
    if not np.isfinite([energy,energy_error,moment_error,divergence_error,current]).all() or max(energy_error,moment_error,divergence_error)>1e-9:
        raise ValueError('axis magnetic energy/current-work identity or divergence-free flux is unresolved')
    return dict(energy_j=energy,region_energy_j={r.id:float(v) for r,v in zip(p.regions,region_energy)},total_source_current_a=current,
        fixed_boundary_reaction_a_m2=fixed_reaction,fixed_boundary_original_reaction_a_m2=fixed_original,
        boundary_original_h_circulation_a=circulation,boundary_original_weighted_h_a_m2=weighted_h,original_field_ampere_balance_a=sum(circulation.values())+current,
        boundary_original_normal_flux_wb=flux,total_boundary_normal_flux_wb=sum(flux.values()),divergence_free_flux_relative_error=divergence_error,
        source_work_j=source_work,boundary_load_work_j=boundary_work,fixed_boundary_work_j=fixed_work,discrete_energy_relative_error=energy_error,
        constant_test_h_volume_a_m2=constant_test,discrete_current_work_balance_a_m2=moment_balance,discrete_current_work_relative_error=moment_error,
        free_dof_relative_residual=s.relative_residual,
        energy_convention='static full-3D integral |B|^2/(2*mu0*mu_r) dV [J], dV=2*pi*r dr dz; no RF phasor',
        circulation_convention='domain-left tangent in r,z; (curl H)_phi=d_z(Hr)-d_r(Hz)=Jphi; H circulation plus cross-section Jphi current is zero, including axis H',
        reaction_convention='fixed Aphi/r reaction is positive 2*pi*integral r^2*Ht ds [A m^2], conjugate to a[T], not an Ampere current [A]',
        flux_convention='2*pi*integral r*original B dot outward normal ds [Wb]; full surface of revolution',
        interpretation='finite axis-connected domain; regular a has no constant gauge kernel; discrete work identities do not bound original B/H, flux or circulation discretization error; no winding inductance is inferred')

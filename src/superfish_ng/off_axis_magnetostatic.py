# SPDX-License-Identifier: Apache-2.0
"""Positive-radius reduced-flux solve, original Aphi/B/H and full 3D quantities."""
from dataclasses import dataclass,field
from types import SimpleNamespace,MappingProxyType
import numpy as np
from scipy.sparse.linalg import spsolve
from .config import keys,integer
from .off_axis_magnetic_materials import OffAxisMagneticPartition
from .off_axis_magnetostatic_boundary import OffAxisMagnetostaticBoundary
from .magnetostatic_boundary import finite_signed,magnetic_field_coordinates
from .constants import TAU
from .coaxial import _numeric_coordinates
from .off_axis_magnetostatic_fem import off_axis_magnetostatic_forms
from .mesh import element_geometry
from .fem import triangle_quadrature
from .planar_polygon import PolygonLocator


def _validate_off_axis_boundaries(mesh,boundaries):
    if not isinstance(boundaries,(list,tuple)) or not boundaries or any(type(b) is not OffAxisMagnetostaticBoundary for b in boundaries):
        raise ValueError('explicit OffAxisMagnetostaticBoundary values are required for every off-axis boundary edge')
    boundaries=tuple(OffAxisMagnetostaticBoundary.from_dict(b.to_dict()) for b in boundaries)
    if len({b.id for b in boundaries})!=len(boundaries):raise ValueError('off-axis magnetostatic boundary IDs must be unique')
    owners=np.full(len(mesh.boundary_edges),-1,dtype=np.int64);fixed_boundary_nodes={};fixed_boundaries=0
    for i,boundary in enumerate(boundaries):
        edges=np.asarray(boundary.edge_indices,dtype=np.int64)
        if np.any(edges>=len(owners)) or np.any(owners[edges]!=-1):raise ValueError('off-axis boundary edges must be in range and assigned exactly once')
        owners[edges]=i
        if boundary.kind=='fixed_psi':
            fixed_boundaries+=1
            for node in np.unique(mesh.boundary_edges[edges]):
                if node in fixed_boundary_nodes:raise ValueError('fixed-psi boundaries share a node; merge connected fixed-psi edges under one boundary ID')
                fixed_boundary_nodes[node]=boundary.id
    if np.any(owners<0):raise ValueError('every off-axis magnetostatic boundary must be explicit; no implicit ground or external boundary')
    if not fixed_boundaries:raise ValueError('at least one fixed-psi off-axis boundary is required; pure Neumann/gauge is unsupported')
    owners.setflags(write=False)
    return boundaries,owners


@dataclass(frozen=True,eq=False)
class OffAxisMagnetostaticCase:
    partition: OffAxisMagneticPartition
    current_density_phi_a_per_m2: dict
    boundaries: tuple
    element_order: int = 2
    quadrature_order: int = 16
    name: str = 'magnetostatic'
    boundary_owner_indices: np.ndarray = field(init=False,repr=False)

    def __post_init__(self):
        if type(self.partition) is not OffAxisMagneticPartition:raise ValueError('explicit positive-radius magnetic partition required')
        partition=OffAxisMagneticPartition.from_dict(self.partition.to_dict());object.__setattr__(self,'partition',partition)
        names=[r.id for r in partition.regions];data=dict(self.current_density_phi_a_per_m2) if isinstance(self.current_density_phi_a_per_m2,MappingProxyType) else self.current_density_phi_a_per_m2
        keys(data,names,names,'magnetostatic current_density_phi_a_per_m2 by region')
        current={name:finite_signed(data[name],'current density Jphi for '+name+' [A/m^2]') for name in names}
        object.__setattr__(self,'current_density_phi_a_per_m2',MappingProxyType(current))
        boundaries,owners=_validate_off_axis_boundaries(partition.mesh,self.boundaries)
        object.__setattr__(self,'boundaries',boundaries);object.__setattr__(self,'boundary_owner_indices',owners)
        integer(self.element_order,'magnetostatic element_order');integer(self.quadrature_order,'magnetostatic quadrature_order')
        if self.element_order not in (1,2) or not 4<=self.quadrature_order<=32:raise ValueError('magnetostatic Case requires P1/P2 and quadrature_order from 4 to 32')
        if type(self.name) is not str or not self.name.strip():raise ValueError('magnetostatic name must be nonempty')

    def to_dict(self):
        return dict(format='superfish_ng_off_axis_magnetostatic_case',schema_version=1,physics='linear_magnetostatic',
            name=self.name,partition=self.partition.to_dict(),current_density_phi_a_per_m2=dict(self.current_density_phi_a_per_m2),
            boundaries=[b.to_dict() for b in self.boundaries],element_order=self.element_order,quadrature_order=self.quadrature_order)

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','physics','name','partition','current_density_phi_a_per_m2','boundaries','element_order','quadrature_order']
        keys(data,names,names,'off-axis magnetostatic Case')
        if (data['format']!='superfish_ng_off_axis_magnetostatic_case' or type(data['schema_version']) is not int
            or data['schema_version']!=1 or data['physics']!='linear_magnetostatic'):
            raise ValueError('expected superfish_ng_off_axis_magnetostatic_case version 1, linear_magnetostatic physics')
        if type(data['boundaries']) is not list:raise ValueError('magnetostatic boundaries must be a JSON list')
        return cls(OffAxisMagneticPartition.from_dict(data['partition']),data['current_density_phi_a_per_m2'],
            tuple(OffAxisMagnetostaticBoundary.from_dict(b) for b in data['boundaries']),data['element_order'],data['quadrature_order'],data['name'])


def _edge_quadrature(space,index,order=20):
    mesh=space.partition.mesh;edge=mesh.boundary_edges[index];owner=mesh.boundary_cells[index]
    a,b=mesh.points_rz_m[edge];delta=b-a;length=np.linalg.norm(delta)
    nodes,weights=np.polynomial.legendre.leggauss(order);t=(nodes+1)/2;weights=weights/2
    local=mesh.boundary_local_vertices[index];bary=np.zeros((len(t),3));bary[:,local[0]]=1-t;bary[:,local[1]]=t
    values=bary if space.element_order==1 else np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
    # The oriented polygon boundary keeps the magnetic domain on its left.
    outward=np.array([delta[1],-delta[0]])/length
    return owner,bary,values,length*weights,outward


@dataclass(eq=False)
class OffAxisMagnetostaticSolution:
    case: OffAxisMagnetostaticCase
    space: object
    stiffness: object
    volume_load_a: np.ndarray
    boundary_load_a: np.ndarray
    psi_wb: np.ndarray
    psi_relative_to_reference_wb: np.ndarray
    reference_psi_wb: float
    free_dofs: np.ndarray
    fixed_boundary_dofs: dict
    assembly_report: dict
    relative_residual: float

    def __post_init__(self):
        _,self._determinants,self._gradients=element_geometry(self.space.mesh)
        self._locator=PolygonLocator(SimpleNamespace(points_xy_m=self.space.mesh.points,triangles=self.space.mesh.triangles))

    def fields_in_cells(self,cell_indices,barycentric):
        cells,bary=magnetic_field_coordinates(cell_indices,barycentric,len(self.space.cell_dofs))
        gradient=self._gradients[cells]
        if self.case.element_order==1:values,derivatives=bary,gradient
        else:
            values=np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
            derivatives=np.concatenate(((4*bary-1)[:,:,None]*gradient,
                np.stack([4*(bary[:,i,None]*gradient[:,j]+bary[:,j,None]*gradient[:,i]) for i,j in ((0,1),(1,2),(2,0))],axis=1)),axis=1)
        coefficients=self.psi_relative_to_reference_wb[self.space.cell_dofs[cells]]
        potential=self.reference_psi_wb+np.einsum('qi,qi->q',values,coefficients);gradient=np.einsum('qia,qi->qa',derivatives,coefficients)
        radius=np.einsum('qi,qi->q',bary,self.space.mesh.points[self.space.mesh.triangles[cells],0])
        magnetic=np.column_stack((-gradient[:,1],gradient[:,0]))/radius[:,None];intensity=self.case.partition.reluctivity_m_per_h[cells,None]*magnetic
        fields=dict(psi_Wb=potential,Aphi_Wb_per_m=potential/radius,Br_T=magnetic[:,0],Bz_T=magnetic[:,1],Hr_A_per_m=intensity[:,0],Hz_A_per_m=intensity[:,1])
        if any(not np.isfinite(v).all() for v in fields.values()):raise ValueError('magnetostatic fields exceed finite SI arithmetic')
        return fields

    def probe_at(self,points_rz_m):
        points=_numeric_coordinates(points_rz_m,2,'magnetostatic probe coordinates')
        if points.dtype.kind not in 'fi' or points.ndim!=2 or points.shape[1]!=2 or not len(points) or not np.isfinite(points).all():
            raise ValueError('magnetostatic probes require finite [r_m,z_m] points')
        try:cells,bary=self._locator.locate(points)
        except ValueError as exc:raise ValueError('magnetostatic probe is outside the declared magnetic polygon') from exc
        p=self.case.partition;owners=p.cell_region_indices[cells]
        return dict(points_rz_m=points.tolist(),cell_indices=cells.tolist(),barycentric=bary.tolist(),
            region_ids=[p.regions[i].id for i in owners],material_ids=[p.regions[i].material for i in owners],mu_r=p.mu_r[cells].tolist(),
            fields={k:v.tolist() for k,v in self.fields_in_cells(cells,bary).items()},
            convention='static psi=r*Aphi[Wb], Br=-d_z(psi)/r, Bz=d_r(psi)/r[T], H=B/(mu0*mu_r(cell))[A/m]; excluded-axis absolute flux is not inferred',
            interface_policy='lowest original cell index at shared edges; one-sided values, no averaging')


def solve_off_axis_magnetostatic(case):
    if type(case) is not OffAxisMagnetostaticCase:raise ValueError('explicit OffAxisMagnetostaticCase required')
    case=OffAxisMagnetostaticCase.from_dict(case.to_dict())
    space,k,volume,report=off_axis_magnetostatic_forms(case.partition,dict(case.current_density_phi_a_per_m2),case.element_order,quadrature_order=case.quadrature_order)
    boundary_load=np.zeros(len(volume));potential=np.zeros(len(volume));fixed=np.zeros(len(volume),dtype=bool);fixed_boundaries={}
    reference=next(b.value for b in case.boundaries if b.kind=='fixed_psi')
    for boundary in case.boundaries:
        if boundary.kind=='fixed_psi':
            dofs=np.unique(space.boundary_dofs[list(boundary.edge_indices)]);fixed[dofs]=True;potential[dofs]=boundary.value-reference;fixed_boundaries[boundary.id]=dofs
        elif boundary.kind=='tangential_h':
            for edge in boundary.edge_indices:
                owner,_,values,measure,_=_edge_quadrature(space,edge,case.quadrature_order+4)
                np.add.at(boundary_load,space.cell_dofs[owner],TAU*boundary.value*(values.T@measure))
    free=np.flatnonzero(~fixed);total=volume+boundary_load
    if len(free):potential[free]=spsolve(k[free][:,free],total[free]-(k@potential)[free])
    force=k@potential;denominator=np.linalg.norm(force)+np.linalg.norm(total)
    residual=float(np.linalg.norm((force-total)[free])/denominator) if denominator else 0.
    if not np.isfinite(potential).all() or not np.isfinite(residual) or residual>1e-10:
        raise ValueError('magnetostatic linear solve failed finite free-DOF residual validation')
    absolute_potential=potential+reference
    if not np.isfinite(absolute_potential).all():raise ValueError('absolute magnetostatic potential exceeds finite SI arithmetic')
    for array in (potential,absolute_potential,volume,boundary_load,free,*fixed_boundaries.values()):array.setflags(write=False)
    solution=OffAxisMagnetostaticSolution(case,space,k,volume,boundary_load,absolute_potential,potential,reference,free,MappingProxyType(fixed_boundaries),report,residual)
    off_axis_magnetostatic_quantities(solution)  # Check magnetic energy/current identities before returning.
    return solution



def off_axis_magnetostatic_quantities(solution):
    if type(solution) is not OffAxisMagnetostaticSolution:raise ValueError('OffAxisMagnetostaticSolution required')
    s=solution;case=s.case;p=case.partition;cells=np.arange(len(p.mesh.triangles));cell_energy=np.zeros(len(cells))
    for bary,weight in triangle_quadrature(case.quadrature_order+4):
        fields=s.fields_in_cells(cells,np.tile(bary,(len(cells),1)));radius=p.mesh.points_rz_m[p.mesh.triangles,0]@bary;measure=TAU*radius*weight*s._determinants
        cell_energy+=.5*p.reluctivity_m_per_h*(fields['Br_T']**2+fields['Bz_T']**2)*measure
    energy=float(cell_energy.sum());region_energy=np.bincount(p.cell_region_indices,weights=cell_energy,minlength=len(p.regions))
    reaction=s.stiffness@s.psi_relative_to_reference_wb-s.volume_load_a-s.boundary_load_a
    fixed_reaction={name:float(reaction[dofs].sum()) for name,dofs in s.fixed_boundary_dofs.items()}
    fixed_original={name:0. for name in s.fixed_boundary_dofs};circulation={b.id:0. for b in case.boundaries};flux=dict.fromkeys(circulation,0.);specified=0.;flux_scale=0.
    for index in range(len(p.mesh.boundary_edges)):
        owner,bary,_,measure,normal=_edge_quadrature(s.space,index,case.quadrature_order+4);fields=s.fields_in_cells(np.full(len(bary),owner,dtype=int),bary);tangent=np.array([-normal[1],normal[0]])
        line_integral=float(measure@(fields['Hr_A_per_m']*tangent[0]+fields['Hz_A_per_m']*tangent[1]))
        radius=bary@p.mesh.points_rz_m[p.mesh.triangles[owner],0];surface=TAU*radius*measure
        normal_flux=float(surface@(fields['Br_T']*normal[0]+fields['Bz_T']*normal[1]));flux_scale+=float(surface@np.hypot(fields['Br_T'],fields['Bz_T']))
        boundary=case.boundaries[case.boundary_owner_indices[index]];circulation[boundary.id]+=line_integral;flux[boundary.id]+=normal_flux
        if boundary.kind=='fixed_psi':fixed_original[boundary.id]+=TAU*line_integral
        else:specified+=boundary.value*float(measure.sum())
    current=float(sum(case.current_density_phi_a_per_m2[r.id]*v for r,v in zip(p.regions,p.region_area_m2)))
    balance=sum(fixed_reaction.values())/TAU+current+specified
    absolute=sum(abs(v) for v in fixed_reaction.values())/TAU+sum(abs(case.current_density_phi_a_per_m2[r.id]*v) for r,v in zip(p.regions,p.region_area_m2))+abs(specified)
    current_error=float(abs(balance)/absolute) if absolute else float(abs(balance))
    source_work=float(s.psi_wb@s.volume_load_a);boundary_work=float(s.psi_wb@s.boundary_load_a)
    fixed_work=sum(b.value*fixed_reaction[b.id] for b in case.boundaries if b.kind=='fixed_psi');energy_scale=2*energy+abs(source_work)+abs(boundary_work)+abs(fixed_work)
    energy_error=float(abs(2*energy-source_work-boundary_work-fixed_work)/energy_scale) if energy_scale else 0.
    divergence_error=float(abs(sum(flux.values()))/flux_scale) if flux_scale else float(abs(sum(flux.values())))
    if not np.isfinite([energy,current_error,energy_error,divergence_error]).all() or max(current_error,energy_error,divergence_error)>1e-9:
        raise ValueError('magnetostatic discrete current/energy identity or divergence-free flux is unresolved')
    return dict(energy_j=energy,region_energy_j={r.id:float(v) for r,v in zip(p.regions,region_energy)},total_source_current_a=current,
        specified_tangential_h_integral_a=specified,fixed_boundary_reaction_a=fixed_reaction,fixed_boundary_original_reaction_a=fixed_original,
        boundary_original_h_circulation_a=circulation,original_field_ampere_balance_a=sum(circulation.values())+current,
        boundary_original_normal_flux_wb=flux,total_boundary_normal_flux_wb=sum(flux.values()),divergence_free_flux_relative_error=divergence_error,
        discrete_current_balance_a=balance,discrete_current_relative_error=current_error,source_work_j=source_work,boundary_load_work_j=boundary_work,
        fixed_boundary_work_j=fixed_work,discrete_energy_relative_error=energy_error,free_dof_relative_residual=s.relative_residual,reference_psi_wb=s.reference_psi_wb,
        energy_convention='static integral |B|^2/(2*mu0*mu_r) 2*pi*r drdz [J], no RF phasor',
        circulation_convention='domain on left in (r,z), curl(H)_phi=d_z(Hr)-d_r(Hz)=Jphi; fixed-psi reaction is +2*pi integral Ht ds [A]; sum(Ht ds)+source current=0',
        flux_convention='original 2*pi*r B dot outward normal ds [Wb]; equals -2*pi change in psi along the domain-left oriented boundary; no excluded-axis absolute flux',
        interpretation='finite declared external boundaries; discrete reaction and energy identities do not bound original B/H or boundary-circulation discretization error; no winding inductance is inferred')

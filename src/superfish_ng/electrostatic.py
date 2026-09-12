# SPDX-License-Identifier: Apache-2.0
"""Axisymmetric linear electrostatic Poisson solve with explicit electrodes."""
from dataclasses import dataclass,field
from types import SimpleNamespace,MappingProxyType
import numpy as np
from scipy.sparse.linalg import spsolve
from .config import keys,integer
from .constants import EPS0,TAU
from .dielectrics import AxisymmetricDielectricPartition
from .electrostatic_boundary import ElectrostaticBoundary,finite_signed,validate_boundaries
from .electrostatic_fem import axisymmetric_electrostatic_forms
from .mesh import element_geometry
from .fem import triangle_quadrature
from .planar_polygon import PolygonLocator


@dataclass(frozen=True,eq=False)
class AxisymmetricElectrostaticCase:
    partition: AxisymmetricDielectricPartition
    charge_density_c_per_m3: dict
    boundaries: tuple
    element_order: int = 2
    quadrature_order: int = 4
    name: str = 'electrostatic'
    boundary_owner_indices: np.ndarray = field(init=False,repr=False)

    def __post_init__(self):
        if type(self.partition) is not AxisymmetricDielectricPartition:raise ValueError('explicit axisymmetric dielectric partition required')
        partition=AxisymmetricDielectricPartition.from_dict(self.partition.to_dict());object.__setattr__(self,'partition',partition)
        names=[r.id for r in partition.regions];data=dict(self.charge_density_c_per_m3) if isinstance(self.charge_density_c_per_m3,MappingProxyType) else self.charge_density_c_per_m3
        keys(data,names,names,'electrostatic charge_density_c_per_m3 by region')
        charge={name:finite_signed(data[name],'charge density for '+name+' [C/m^3]') for name in names}
        object.__setattr__(self,'charge_density_c_per_m3',MappingProxyType(charge))
        boundaries,owners=validate_boundaries(partition.mesh,self.boundaries)
        object.__setattr__(self,'boundaries',boundaries);object.__setattr__(self,'boundary_owner_indices',owners)
        integer(self.element_order,'electrostatic element_order');integer(self.quadrature_order,'electrostatic quadrature_order')
        if self.element_order not in (1,2) or not 4<=self.quadrature_order<=32:raise ValueError('electrostatic Case requires P1/P2 and quadrature_order from 4 to 32')
        if type(self.name) is not str or not self.name.strip():raise ValueError('electrostatic name must be nonempty')

    def to_dict(self):
        return dict(format='superfish_ng_axisymmetric_electrostatic_case',schema_version=1,physics='linear_electrostatic',
            name=self.name,partition=self.partition.to_dict(),charge_density_c_per_m3=dict(self.charge_density_c_per_m3),
            boundaries=[b.to_dict() for b in self.boundaries],element_order=self.element_order,quadrature_order=self.quadrature_order)

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','physics','name','partition','charge_density_c_per_m3','boundaries','element_order','quadrature_order']
        keys(data,names,names,'axisymmetric electrostatic Case')
        if (data['format']!='superfish_ng_axisymmetric_electrostatic_case' or type(data['schema_version']) is not int
            or data['schema_version']!=1 or data['physics']!='linear_electrostatic'):
            raise ValueError('expected superfish_ng_axisymmetric_electrostatic_case version 1, linear_electrostatic physics')
        if type(data['boundaries']) is not list:raise ValueError('electrostatic boundaries must be a JSON list')
        return cls(AxisymmetricDielectricPartition.from_dict(data['partition']),data['charge_density_c_per_m3'],
            tuple(ElectrostaticBoundary.from_dict(b) for b in data['boundaries']),data['element_order'],data['quadrature_order'],data['name'])


def _edge_quadrature(space,index):
    mesh=space.partition.mesh;edge=mesh.boundary_edges[index];owner=mesh.boundary_cells[index]
    a,b=mesh.points_rz_m[edge];delta=b-a;length=np.linalg.norm(delta)
    nodes,weights=np.polynomial.legendre.leggauss(4);t=(nodes+1)/2;weights=weights/2
    local=mesh.boundary_local_vertices[index];bary=np.zeros((len(t),3));bary[:,local[0]]=1-t;bary[:,local[1]]=t
    radius=((1-t[:,None])*a+t[:,None]*b)[:,0]
    values=bary if space.element_order==1 else np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
    # Oriented domain boundary keeps material on its left, including holes.
    outward=np.array([delta[1],-delta[0]])/length
    return owner,bary,values,TAU*radius*length*weights,outward


@dataclass(eq=False)
class AxisymmetricElectrostaticSolution:
    case: AxisymmetricElectrostaticCase
    space: object
    stiffness: object
    volume_load_c: np.ndarray
    boundary_load_c: np.ndarray
    potential_v: np.ndarray
    potential_relative_to_reference_v: np.ndarray
    reference_potential_v: float
    free_dofs: np.ndarray
    electrode_dofs: dict
    assembly_report: dict
    relative_residual: float

    def __post_init__(self):
        _,self._determinants,self._gradients=element_geometry(self.space.mesh)
        self._locator=PolygonLocator(SimpleNamespace(points_xy_m=self.space.mesh.points,triangles=self.space.mesh.triangles))

    def fields_in_cells(self,cell_indices,barycentric):
        cells=np.asarray(cell_indices);bary=np.asarray(barycentric)
        if (cells.ndim!=1 or cells.dtype.kind not in 'iu' or not len(cells) or np.any(cells>=len(self.space.cell_dofs)) or np.any(cells<0)
            or bary.dtype.kind not in 'fi' or bary.shape!=(len(cells),3) or not np.isfinite(bary).all()
            or np.any(bary<-1e-12) or not np.allclose(bary.sum(axis=1),1.,rtol=0,atol=1e-12)):
            raise ValueError('electrostatic fields require original cell indices and closed reference-triangle coordinates')
        gradient=self._gradients[cells]
        if self.case.element_order==1:values,derivatives=bary,gradient
        else:
            values=np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
            derivatives=np.concatenate(((4*bary-1)[:,:,None]*gradient,
                np.stack([4*(bary[:,i,None]*gradient[:,j]+bary[:,j,None]*gradient[:,i]) for i,j in ((0,1),(1,2),(2,0))],axis=1)),axis=1)
        coefficients=self.potential_relative_to_reference_v[self.space.cell_dofs[cells]]
        potential=self.reference_potential_v+np.einsum('qi,qi->q',values,coefficients);electric=-np.einsum('qia,qi->qa',derivatives,coefficients)
        displacement=EPS0*self.case.partition.epsilon_r[cells,None]*electric
        fields=dict(potential_V=potential,Er_V_per_m=electric[:,0],Ez_V_per_m=electric[:,1],Dr_C_per_m2=displacement[:,0],Dz_C_per_m2=displacement[:,1])
        if any(not np.isfinite(v).all() for v in fields.values()):raise ValueError('electrostatic fields exceed finite SI arithmetic')
        return fields

    def probe_at(self,points_rz_m):
        points=np.asarray(points_rz_m)
        if points.dtype.kind not in 'fi' or points.ndim!=2 or points.shape[1]!=2 or not len(points) or not np.isfinite(points).all() or np.any(points[:,0]<0):
            raise ValueError('electrostatic probes require finite [r_m,z_m] points')
        try:cells,bary=self._locator.locate(points)
        except ValueError as exc:raise ValueError('electrostatic probe is outside the declared dielectric domain, including any excluded conductor') from exc
        p=self.case.partition;owners=p.cell_region_indices[cells]
        return dict(points_rz_m=points.tolist(),cell_indices=cells.tolist(),barycentric=bary.tolist(),
            region_ids=[p.regions[i].id for i in owners],material_ids=[p.regions[i].material for i in owners],epsilon_r=p.epsilon_r[cells].tolist(),
            fields={k:v.tolist() for k,v in self.fields_in_cells(cells,bary).items()},
            convention='static real Phi[V], E=-grad(Phi)[V/m], D=epsilon0*epsilon_r(cell)*E[C/m^2]',
            interface_policy='lowest original cell index at shared edges; one-sided values, no averaging')


def solve_axisymmetric_electrostatic(case):
    if type(case) is not AxisymmetricElectrostaticCase:raise ValueError('explicit AxisymmetricElectrostaticCase required')
    case=AxisymmetricElectrostaticCase.from_dict(case.to_dict())
    space,k,volume,report=axisymmetric_electrostatic_forms(case.partition,dict(case.charge_density_c_per_m3),case.element_order,quadrature_order=case.quadrature_order)
    boundary_load=np.zeros(len(volume));potential=np.zeros(len(volume));fixed=np.zeros(len(volume),dtype=bool);electrodes={}
    reference=next(b.value for b in case.boundaries if b.kind=='electrode_potential')
    for boundary in case.boundaries:
        if boundary.kind=='electrode_potential':
            dofs=np.unique(space.boundary_dofs[list(boundary.edge_indices)]);fixed[dofs]=True;potential[dofs]=boundary.value-reference;electrodes[boundary.id]=dofs
        elif boundary.kind=='outward_displacement':
            for edge in boundary.edge_indices:
                owner,_,values,measure,_=_edge_quadrature(space,edge)
                np.add.at(boundary_load,space.cell_dofs[owner],-boundary.value*(values.T@measure))
    free=np.flatnonzero(~fixed);total=volume+boundary_load
    if len(free):potential[free]=spsolve(k[free][:,free],total[free]-(k@potential)[free])
    force=k@potential;denominator=np.linalg.norm(force)+np.linalg.norm(total)
    residual=float(np.linalg.norm((force-total)[free])/denominator) if denominator else 0.
    if not np.isfinite(potential).all() or not np.isfinite(residual) or residual>1e-10:
        raise ValueError('electrostatic linear solve failed finite free-DOF residual validation')
    absolute_potential=potential+reference
    if not np.isfinite(absolute_potential).all():raise ValueError('absolute electrostatic potential exceeds finite SI arithmetic')
    for array in (potential,absolute_potential,volume,boundary_load,free,*electrodes.values()):array.setflags(write=False)
    solution=AxisymmetricElectrostaticSolution(case,space,k,volume,boundary_load,absolute_potential,potential,reference,free,MappingProxyType(electrodes),report,residual)
    electrostatic_quantities(solution)  # Check discrete energy/charge identities before returning.
    return solution


def electrostatic_quantities(solution):
    if type(solution) is not AxisymmetricElectrostaticSolution:raise ValueError('AxisymmetricElectrostaticSolution required')
    s=solution;case=s.case;p=case.partition;cells=np.arange(len(p.mesh.triangles));vertices=p.mesh.points_rz_m[p.mesh.triangles]
    cell_energy=np.zeros(len(cells))
    for bary,weight in triangle_quadrature(case.quadrature_order+4):
        fields=s.fields_in_cells(cells,np.tile(bary,(len(cells),1)));measure=TAU*(vertices[:,:,0]@bary)*weight*s._determinants
        cell_energy+=.5*EPS0*p.epsilon_r*(fields['Er_V_per_m']**2+fields['Ez_V_per_m']**2)*measure
    energy=float(cell_energy.sum());region_energy=np.bincount(p.cell_region_indices,weights=cell_energy,minlength=len(p.regions))
    reaction=s.stiffness@s.potential_relative_to_reference_v-s.volume_load_c-s.boundary_load_c
    electrode_reaction={name:float(reaction[dofs].sum()) for name,dofs in s.electrode_dofs.items()}
    electrode_field={name:0. for name in s.electrode_dofs};boundary_flux={b.id:0. for b in case.boundaries};specified=0.
    for index in range(len(p.mesh.boundary_edges)):
        owner,bary,_,measure,normal=_edge_quadrature(s.space,index);fields=s.fields_in_cells(np.full(len(bary),owner,dtype=int),bary)
        flux=float(measure@(fields['Dr_C_per_m2']*normal[0]+fields['Dz_C_per_m2']*normal[1]))
        boundary=case.boundaries[case.boundary_owner_indices[index]];boundary_flux[boundary.id]+=flux
        if boundary.kind=='electrode_potential':electrode_field[boundary.id]-=flux
        elif boundary.kind=='outward_displacement':specified+=boundary.value*float(measure.sum())
    charge=float(sum(case.charge_density_c_per_m3[r.id]*v for r,v in zip(p.regions,p.region_volume_m3)))
    balance=sum(electrode_reaction.values())+charge-specified
    absolute=sum(abs(v) for v in electrode_reaction.values())+sum(abs(case.charge_density_c_per_m3[r.id]*v) for r,v in zip(p.regions,p.region_volume_m3))+abs(specified)
    charge_error=float(abs(balance)/absolute) if absolute else float(abs(balance))
    source_work=float(s.potential_v@s.volume_load_c);boundary_work=float(s.potential_v@s.boundary_load_c)
    electrode_work=sum(b.value*electrode_reaction[b.id] for b in case.boundaries if b.kind=='electrode_potential')
    energy_scale=2*energy+abs(source_work)+abs(boundary_work)+abs(electrode_work)
    energy_error=float(abs(2*energy-source_work-boundary_work-electrode_work)/energy_scale) if energy_scale else 0.
    if not np.isfinite([energy,charge_error,energy_error]).all() or max(charge_error,energy_error)>1e-9:
        raise ValueError('electrostatic discrete charge or energy identity is unresolved')
    terminals=[b for b in case.boundaries if b.kind=='electrode_potential'];capacitance=None
    if (len(terminals)==2 and terminals[0].value!=terminals[1].value and all(v==0 for v in case.charge_density_c_per_m3.values())
        and all(b.value==0 for b in case.boundaries if b.kind=='outward_displacement')):
        high=max(terminals,key=lambda b:b.value);low=min(terminals,key=lambda b:b.value);voltage=high.value-low.value
        capacitance=dict(high_electrode=high.id,low_electrode=low.id,potential_difference_v=voltage,
            from_reaction_f=electrode_reaction[high.id]/voltage,from_energy_f=2*energy/voltage**2,
            from_original_field_f=electrode_field[high.id]/voltage,
            interpretation='two fixed-potential terminals, no volume charge, all other non-axis boundaries zero outward Dn')
    return dict(energy_j=energy,region_energy_j={r.id:float(v) for r,v in zip(p.regions,region_energy)},
        volume_charge_c=charge,specified_neumann_outward_charge_c=specified,electrode_reaction_charge_c=electrode_reaction,
        electrode_original_field_charge_c=electrode_field,boundary_original_outward_flux_c=boundary_flux,
        original_field_gauss_balance_c=sum(boundary_flux.values())-charge,discrete_charge_balance_c=balance,
        discrete_charge_relative_error=charge_error,source_work_j=source_work,boundary_load_work_j=boundary_work,
        electrode_work_j=electrode_work,discrete_energy_relative_error=energy_error,free_dof_relative_residual=s.relative_residual,
        capacitance=capacitance,reference_potential_v=s.reference_potential_v,energy_convention='static full-3D integral epsilon*|E|^2/2',
        interpretation='discrete charge/energy identities do not bound field or surface-flux discretization error; finite declared external boundaries')

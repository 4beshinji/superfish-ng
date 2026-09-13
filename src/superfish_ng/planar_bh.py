# SPDX-License-Identifier: Apache-2.0
"""Planar P1 nonlinear isotropic magnetic solve, original fields and work."""
from dataclasses import dataclass,field
from types import MappingProxyType,SimpleNamespace
import numpy as np
from scipy.sparse.linalg import spsolve
from .config import keys,integer
from .bh_curve import _real_array
from .planar_bh_materials import PlanarBHPartition
from .planar_bh_fem import planar_bh_space,planar_bh_cell_state,_assemble
from .nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure,damped_magnetic_newton
from .magnetostatic_boundary import MagnetostaticBoundary,finite_signed,magnetic_field_coordinates
from .planar_magnetostatic import _validate_planar_boundaries,_edge_quadrature
from .coaxial import _numeric_coordinates
from .planar_polygon import PolygonLocator


@dataclass(frozen=True,eq=False)
class PlanarBHCase:
    partition: PlanarBHPartition
    current_density_z_a_per_m2: dict
    boundaries: tuple
    element_order: int=1
    controls: MagneticNewtonControls=field(default_factory=MagneticNewtonControls)
    initial_az_relative_to_reference_wb_per_m: tuple|None=None
    name: str='planar-nonlinear-magnetic'
    boundary_owner_indices: np.ndarray=field(init=False,repr=False)

    def __post_init__(self):
        if type(self.partition) is not PlanarBHPartition:raise ValueError('explicit PlanarBHPartition required')
        p=PlanarBHPartition.from_dict(self.partition.to_dict());object.__setattr__(self,'partition',p)
        names=[r.id for r in p.regions];data=dict(self.current_density_z_a_per_m2) if isinstance(self.current_density_z_a_per_m2,MappingProxyType) else self.current_density_z_a_per_m2
        keys(data,names,names,'planar B-H current_density_z_a_per_m2 by region');current={name:finite_signed(data[name],'current density Jz for '+name+' [A/m^2]') for name in names};object.__setattr__(self,'current_density_z_a_per_m2',MappingProxyType(current))
        boundaries,owners=_validate_planar_boundaries(p.mesh,self.boundaries);object.__setattr__(self,'boundaries',boundaries);object.__setattr__(self,'boundary_owner_indices',owners)
        integer(self.element_order,'planar B-H element_order')
        if self.element_order!=1:raise ValueError('planar nonlinear B-H Case requires P1; nonlinear P2 integration is unsupported')
        if type(self.controls) is not MagneticNewtonControls:raise ValueError('explicit MagneticNewtonControls required')
        object.__setattr__(self,'controls',MagneticNewtonControls.from_dict(self.controls.to_dict()))
        if type(self.name) is not str or not self.name.strip():raise ValueError('planar B-H Case name must be nonempty')
        initial=self.initial_az_relative_to_reference_wb_per_m
        if initial is not None:
            if not isinstance(initial,(list,tuple)):raise ValueError('initial relative Az must be an explicit list or tuple, or null')
            values=_real_array(initial,'initial relative Az [Wb/m]')
            if values.shape!=(len(p.mesh.points_xy_m),):raise ValueError('initial relative Az requires one coefficient per P1 vertex')
            reference=next(b.value for b in boundaries if b.kind=='fixed_az')
            for b in boundaries:
                if b.kind=='fixed_az' and not np.all(values[np.unique(p.mesh.boundary_edges[list(b.edge_indices)])]==b.value-reference):raise ValueError('initial relative Az must match every fixed-Az boundary relative to the first fixed value')
            object.__setattr__(self,'initial_az_relative_to_reference_wb_per_m',tuple(map(float,values)))

    def to_dict(self):
        return dict(format='superfish_ng_planar_bh_case',schema_version=1,physics='nonlinear_isotropic_magnetostatic',name=self.name,
            partition=self.partition.to_dict(),current_density_z_a_per_m2=dict(self.current_density_z_a_per_m2),boundaries=[b.to_dict() for b in self.boundaries],
            element_order=self.element_order,controls=self.controls.to_dict(),initial_az_relative_to_reference_wb_per_m=None if self.initial_az_relative_to_reference_wb_per_m is None else list(self.initial_az_relative_to_reference_wb_per_m))

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','physics','name','partition','current_density_z_a_per_m2','boundaries','element_order','controls','initial_az_relative_to_reference_wb_per_m'];keys(data,names,names,'planar B-H Case')
        if data['format']!='superfish_ng_planar_bh_case' or type(data['schema_version']) is not int or data['schema_version']!=1 or data['physics']!='nonlinear_isotropic_magnetostatic':raise ValueError('expected superfish_ng_planar_bh_case version 1, nonlinear_isotropic_magnetostatic physics')
        if type(data['boundaries']) is not list:raise ValueError('planar B-H boundaries require a JSON list')
        initial=data['initial_az_relative_to_reference_wb_per_m']
        if initial is not None and type(initial) is not list:raise ValueError('initial relative Az requires a JSON list or null')
        return cls(PlanarBHPartition.from_dict(data['partition']),data['current_density_z_a_per_m2'],[MagnetostaticBoundary.from_dict(v) for v in data['boundaries']],data['element_order'],MagneticNewtonControls.from_dict(data['controls']),initial,data['name'])


@dataclass(eq=False)
class PlanarBHSolution:
    case: PlanarBHCase
    space: object
    tangent: object
    internal_load_a: np.ndarray
    current_load_a: np.ndarray
    boundary_load_a: np.ndarray
    az_wb_per_m: np.ndarray
    az_relative_to_reference_wb_per_m: np.ndarray
    reference_az_wb_per_m: float
    free_dofs: np.ndarray
    fixed_boundary_dofs: dict
    assembly_report: dict
    iteration_report: dict
    relative_residual: float

    def __post_init__(self):self._locator=PolygonLocator(SimpleNamespace(points_xy_m=self.space.mesh.points,triangles=self.space.mesh.triangles))

    def fields_in_cells(self,cell_indices,barycentric):
        cells,bary=magnetic_field_coordinates(cell_indices,barycentric,len(self.space.cell_dofs));coefficients=self.az_relative_to_reference_wb_per_m[self.space.cell_dofs[cells]]
        potential=self.reference_az_wb_per_m+np.einsum('qi,qi->q',bary,coefficients)
        gradient_coefficients=(self.az_relative_to_reference_wb_per_m-self.az_relative_to_reference_wb_per_m[0])[self.space.cell_dofs[cells]]
        b=np.einsum('qi,qia->qa',gradient_coefficients,self.space.curls[cells]);state=self.case.partition.evaluate_cells(cells,b);h=state['h_a_per_m']
        fields=dict(Az_Wb_per_m=potential,Bx_T=b[:,0],By_T=b[:,1],Hx_A_per_m=h[:,0],Hy_A_per_m=h[:,1])
        if any(not np.isfinite(v).all() for v in fields.values()):raise ValueError('planar B-H fields exceed finite SI arithmetic')
        return fields

    def probe_at(self,points_xy_m):
        points=_numeric_coordinates(points_xy_m,2,'planar B-H probe coordinates')
        if points.dtype.kind not in 'fi' or points.ndim!=2 or points.shape[1]!=2 or not len(points) or not np.isfinite(points).all():raise ValueError('planar B-H probes require finite [x_m,y_m] points')
        try:cells,bary=self._locator.locate(points)
        except ValueError as exc:raise ValueError('planar B-H probe is outside the declared polygon') from exc
        p=self.case.partition;owners=p.cell_region_indices[cells];fields=self.fields_in_cells(cells,bary);state=p.evaluate_cells(cells,np.column_stack((fields['Bx_T'],fields['By_T'])))
        return dict(points_xy_m=points.tolist(),cell_indices=cells.tolist(),barycentric=bary.tolist(),region_ids=[p.regions[i].id for i in owners],
            material_ids=[p.regions[i].material for i in owners],material_provenance=[p.materials[i].provenance for i in p.cell_material_indices[cells]],
            table_interval_indices=state['interval_indices'].tolist(),secant_reluctivity_m_per_h=state['secant_reluctivity_m_per_h'].tolist(),differential_reluctivity_m_per_h=state['differential_reluctivity_m_per_h'].tolist(),
            fields={name:value.tolist() for name,value in fields.items()},convention='static P1 Az[Wb/m], B=curl(Az ez)[T], original H=h(|B|)*B/|B|[A/m]; no extrapolation',
            interface_policy='lowest original cell at exactly represented shared points; original one-sided B/H, no averaging')


def solve_planar_bh(case):
    if type(case) is not PlanarBHCase:raise ValueError('explicit PlanarBHCase required')
    case=PlanarBHCase.from_dict(case.to_dict());space=planar_bh_space(case.partition,case.element_order);n=len(space.dof_points_xy_m)
    densities=np.array([case.current_density_z_a_per_m2[r.id] for r in case.partition.regions]);seed,_,current,_=_assemble(space,np.zeros(n),densities)
    boundary_load=np.zeros(n);potential=np.zeros(n);fixed=np.zeros(n,dtype=bool);fixed_boundaries={};reference=next(b.value for b in case.boundaries if b.kind=='fixed_az')
    for boundary in case.boundaries:
        if boundary.kind=='fixed_az':
            dofs=np.unique(space.boundary_dofs[list(boundary.edge_indices)]);fixed[dofs]=True;potential[dofs]=boundary.value-reference;fixed_boundaries[boundary.id]=dofs
        else:
            for edge in boundary.edge_indices:
                dofs=space.boundary_dofs[edge];points=space.dof_points_xy_m[dofs];length=np.linalg.norm(points[1]-points[0]);np.add.at(boundary_load,dofs,-boundary.value*length/2)
    free=np.flatnonzero(~fixed);total=current+boundary_load
    context=dict(case=case.to_dict(),coefficient_unit='Wb/m',residual_unit='A',energy_unit='J/m',reference_az_wb_per_m=reference,coefficient_convention='relative to the first fixed-Az boundary; fixed DOFs retained')
    if case.initial_az_relative_to_reference_wb_per_m is None:
        if len(free):potential[free]=spsolve(seed[free][:,free],-(seed@potential)[free])
    else:potential=np.array(case.initial_az_relative_to_reference_wb_per_m)
    if not np.isfinite(potential).all() or not np.isfinite(total).all():raise MagneticNonlinearFailure('invalid_initial_arithmetic','fixed boundary extension or total load is nonfinite',context,case.controls,[],None)
    def assemble(values):
        tangent,g,_,q=_assemble(space,values,densities);return tangent,g,q
    potential,k,g,report,residual,iteration=damped_magnetic_newton(assemble,potential,free,total,case.controls,energy_key='energy_j_per_m',context=context)
    absolute=potential+reference
    if not np.isfinite(absolute).all():raise MagneticNonlinearFailure('invalid_absolute_potential','absolute Az exceeds finite SI arithmetic',context,case.controls,iteration['history'],potential)
    for values in (potential,absolute,g,current,boundary_load,free,*fixed_boundaries.values()):values.setflags(write=False)
    solution=PlanarBHSolution(case,space,k,g,current,boundary_load,absolute,potential,reference,free,MappingProxyType(fixed_boundaries),report,iteration,residual)
    planar_bh_quantities(solution)
    return solution


def planar_bh_quantities(solution):
    if type(solution) is not PlanarBHSolution:raise ValueError('PlanarBHSolution required')
    s=solution;case=s.case;p=case.partition;densities=np.array([case.current_density_z_a_per_m2[r.id] for r in p.regions]);_,g,current,report=_assemble(s.space,s.az_relative_to_reference_wb_per_m,densities)
    for b in case.boundaries:
        if b.kind=='fixed_az' and not np.all(s.az_relative_to_reference_wb_per_m[s.fixed_boundary_dofs[b.id]]==b.value-s.reference_az_wb_per_m):raise ValueError('planar B-H coefficients violate fixed-Az boundary values')
    reaction=g-current-s.boundary_load_a;fixed_reaction={name:float(reaction[dofs].sum()) for name,dofs in s.fixed_boundary_dofs.items()};fixed_original=dict.fromkeys(fixed_reaction,0.)
    circulation={b.id:0. for b in case.boundaries};flux=dict.fromkeys(circulation,0.);specified=flux_scale=0.
    for index in range(len(p.mesh.boundary_edges)):
        owner,bary,_,measure,normal=_edge_quadrature(s.space,index);fields=s.fields_in_cells(np.full(len(bary),owner,dtype=int),bary);tangent=np.array([-normal[1],normal[0]])
        line=float(measure@(fields['Hx_A_per_m']*tangent[0]+fields['Hy_A_per_m']*tangent[1]));normal_flux=float(measure@(fields['Bx_T']*normal[0]+fields['By_T']*normal[1]));flux_scale+=float(measure@np.hypot(fields['Bx_T'],fields['By_T']))
        boundary=case.boundaries[case.boundary_owner_indices[index]];circulation[boundary.id]+=line;flux[boundary.id]+=normal_flux
        if boundary.kind=='fixed_az':fixed_original[boundary.id]-=line
        else:specified+=boundary.value*float(measure.sum())
    source_current=report['total_current_a'];balance=sum(fixed_reaction.values())+source_current-specified
    current_scale=float(abs(g).sum()+abs(current).sum()+abs(s.boundary_load_a).sum());current_error=abs(balance)/current_scale if current_scale else abs(balance)
    source_work=float(s.az_wb_per_m@current);boundary_work=float(s.az_wb_per_m@s.boundary_load_a);fixed_work=sum(b.value*fixed_reaction[b.id] for b in case.boundaries if b.kind=='fixed_az')
    work=report['energy_j_per_m']+report['coenergy_j_per_m'];difference=abs(work-source_work-boundary_work-fixed_work);work_scale=work+abs(source_work)+abs(boundary_work)+abs(fixed_work);work_error=difference/work_scale if work_scale else difference
    if work_error>1e-9:
        term_scale=work+float(abs(s.az_wb_per_m)@abs(current))+float(abs(s.az_wb_per_m)@abs(s.boundary_load_a))+sum(abs(b.value)*float(abs(reaction[s.fixed_boundary_dofs[b.id]]).sum()) for b in case.boundaries if b.kind=='fixed_az')
        if term_scale:work_error=difference/term_scale
    divergence_error=abs(sum(flux.values()))/flux_scale if flux_scale else abs(sum(flux.values()))
    scale=float(np.linalg.norm(g)+np.linalg.norm(current+s.boundary_load_a));residual=float(np.linalg.norm(reaction[s.free_dofs]))/scale if scale else float(np.linalg.norm(reaction[s.free_dofs]))
    if not np.isfinite([current_error,work_error,divergence_error,residual]).all() or max(current_error,work_error,divergence_error)>1e-9 or residual>case.controls.relative_residual_tolerance:raise ValueError('planar B-H nonlinear residual, work/current or divergence-free flux validation failed')
    return dict(energy_j_per_m=report['energy_j_per_m'],coenergy_j_per_m=report['coenergy_j_per_m'],bdoth_integral_j_per_m=report['bdoth_integral_j_per_m'],
        region_energy_j_per_m=report['region_energy_j_per_m'],region_coenergy_j_per_m=report['region_coenergy_j_per_m'],total_source_current_a=source_current,
        specified_tangential_h_integral_a=specified,fixed_boundary_reaction_current_a=fixed_reaction,fixed_boundary_original_reaction_current_a=fixed_original,
        boundary_original_h_circulation_a=circulation,original_field_ampere_balance_a=sum(circulation.values())-source_current,
        boundary_original_normal_flux_wb_per_m=flux,total_boundary_normal_flux_wb_per_m=sum(flux.values()),divergence_free_flux_relative_error=divergence_error,
        discrete_current_balance_a=balance,discrete_current_relative_error=current_error,source_work_j_per_m=source_work,boundary_load_work_j_per_m=boundary_work,fixed_boundary_work_j_per_m=fixed_work,
        discrete_work_relative_error=work_error,legendre_relative_error=report['legendre_relative_error'],free_dof_relative_residual=residual,reference_az_wb_per_m=s.reference_az_wb_per_m,
        energy_convention='reversible isotropic U=integral h(b) db dA, Ustar=integral b(h) dh dA [J/m]; internal work=U+Ustar; no RF phasor',
        circulation_convention='domain-left boundary tangent; curl(H)_z=Jz; fixed-Az reaction is minus original H line integral',
        flux_convention='original B dot outward normal integrated along each boundary [Wb/m]',
        interpretation='declared finite boundaries; nonlinear residual and discrete identities do not bound original B/H or boundary-circulation discretization error; no extrapolation, hysteresis, force or inductance inferred')

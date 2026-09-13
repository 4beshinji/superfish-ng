# SPDX-License-Identifier: Apache-2.0
"""Off-axis P1 nonlinear isotropic magnetic solve, original fields and work."""
from dataclasses import dataclass,field
from types import MappingProxyType,SimpleNamespace
import numpy as np
from scipy.sparse.linalg import spsolve
from .config import keys,integer
from .bh_curve import _real_array
from .off_axis_bh_materials import OffAxisBHPartition
from .off_axis_bh_fem import off_axis_bh_space,off_axis_bh_state,_assemble,_relative_difference
from .nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure,damped_magnetic_newton
from .magnetostatic_boundary import finite_signed,magnetic_field_coordinates
from .off_axis_recoil import _validate_off_axis_boundaries,_edge_quadrature
from .off_axis_magnetostatic_boundary import OffAxisMagnetostaticBoundary
from .constants import TAU
from .coaxial import _numeric_coordinates
from .planar_polygon import PolygonLocator


@dataclass(frozen=True,eq=False)
class OffAxisBHCase:
    partition: OffAxisBHPartition
    current_density_phi_a_per_m2: dict
    boundaries: tuple
    element_order: int=1
    quadrature_order: int=12
    controls: MagneticNewtonControls=field(default_factory=MagneticNewtonControls)
    initial_psi_relative_to_reference_wb: tuple|None=None
    name: str='off-axis-nonlinear-magnetic'
    boundary_owner_indices: np.ndarray=field(init=False,repr=False)

    def __post_init__(self):
        if type(self.partition) is not OffAxisBHPartition:raise ValueError('explicit OffAxisBHPartition required')
        p=OffAxisBHPartition.from_dict(self.partition.to_dict());object.__setattr__(self,'partition',p)
        names=[r.id for r in p.regions];data=dict(self.current_density_phi_a_per_m2) if isinstance(self.current_density_phi_a_per_m2,MappingProxyType) else self.current_density_phi_a_per_m2
        keys(data,names,names,'off-axis B-H current_density_phi_a_per_m2 by region');current={name:finite_signed(data[name],'current density Jphi for '+name+' [A/m^2]') for name in names};object.__setattr__(self,'current_density_phi_a_per_m2',MappingProxyType(current))
        boundaries,owners=_validate_off_axis_boundaries(p.mesh,self.boundaries);object.__setattr__(self,'boundaries',boundaries);object.__setattr__(self,'boundary_owner_indices',owners)
        integer(self.element_order,'off-axis B-H element_order')
        if self.element_order!=1:raise ValueError('off-axis nonlinear B-H Case requires P1; nonlinear P2 integration is unsupported')
        integer(self.quadrature_order,'off-axis B-H quadrature_order')
        if not 4<=self.quadrature_order<=32:raise ValueError('off-axis B-H quadrature_order requires 4 to 32')
        if type(self.controls) is not MagneticNewtonControls:raise ValueError('explicit MagneticNewtonControls required')
        object.__setattr__(self,'controls',MagneticNewtonControls.from_dict(self.controls.to_dict()))
        if type(self.name) is not str or not self.name.strip():raise ValueError('off-axis B-H Case name must be nonempty')
        initial=self.initial_psi_relative_to_reference_wb
        if initial is not None:
            if not isinstance(initial,(list,tuple)):raise ValueError('initial relative psi must be an explicit list or tuple, or null')
            values=_real_array(initial,'initial relative psi [Wb]')
            if values.shape!=(len(p.mesh.points_rz_m),):raise ValueError('initial relative psi requires one coefficient per P1 vertex')
            reference=next(b.value for b in boundaries if b.kind=='fixed_psi')
            for b in boundaries:
                if b.kind=='fixed_psi' and not np.all(values[np.unique(p.mesh.boundary_edges[list(b.edge_indices)])]==b.value-reference):raise ValueError('initial relative psi must match every fixed-psi boundary relative to the first fixed value')
            object.__setattr__(self,'initial_psi_relative_to_reference_wb',tuple(map(float,values)))

    def to_dict(self):
        return dict(format='superfish_ng_off_axis_bh_case',schema_version=1,physics='nonlinear_isotropic_magnetostatic',name=self.name,
            partition=self.partition.to_dict(),current_density_phi_a_per_m2=dict(self.current_density_phi_a_per_m2),boundaries=[b.to_dict() for b in self.boundaries],
            element_order=self.element_order,quadrature_order=self.quadrature_order,controls=self.controls.to_dict(),initial_psi_relative_to_reference_wb=None if self.initial_psi_relative_to_reference_wb is None else list(self.initial_psi_relative_to_reference_wb))

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','physics','name','partition','current_density_phi_a_per_m2','boundaries','element_order','quadrature_order','controls','initial_psi_relative_to_reference_wb'];keys(data,names,names,'off-axis B-H Case')
        if data['format']!='superfish_ng_off_axis_bh_case' or type(data['schema_version']) is not int or data['schema_version']!=1 or data['physics']!='nonlinear_isotropic_magnetostatic':raise ValueError('expected superfish_ng_off_axis_bh_case version 1, nonlinear_isotropic_magnetostatic physics')
        if type(data['boundaries']) is not list:raise ValueError('off-axis B-H boundaries require a JSON list')
        initial=data['initial_psi_relative_to_reference_wb']
        if initial is not None and type(initial) is not list:raise ValueError('initial relative psi requires a JSON list or null')
        return cls(OffAxisBHPartition.from_dict(data['partition']),data['current_density_phi_a_per_m2'],[OffAxisMagnetostaticBoundary.from_dict(v) for v in data['boundaries']],data['element_order'],data['quadrature_order'],MagneticNewtonControls.from_dict(data['controls']),initial,data['name'])


@dataclass(eq=False)
class OffAxisBHSolution:
    case: OffAxisBHCase
    space: object
    tangent: object
    internal_load_a: np.ndarray
    current_load_a: np.ndarray
    boundary_load_a: np.ndarray
    psi_wb: np.ndarray
    psi_relative_to_reference_wb: np.ndarray
    reference_psi_wb: float
    free_dofs: np.ndarray
    fixed_boundary_dofs: dict
    assembly_report: dict
    iteration_report: dict
    relative_residual: float

    def __post_init__(self):self._locator=PolygonLocator(SimpleNamespace(points_xy_m=self.space.mesh.points,triangles=self.space.mesh.triangles))

    def fields_in_cells(self,cell_indices,barycentric):
        state=off_axis_bh_state(self.space,self.psi_relative_to_reference_wb,cell_indices,barycentric)
        potential=state['psi_wb']+self.reference_psi_wb;b=state['b_t'];h=state['h_a_per_m']
        fields=dict(psi_Wb=potential,Aphi_Wb_per_m=potential/state['radius_m'],Br_T=b[:,0],Bz_T=b[:,1],Hr_A_per_m=h[:,0],Hz_A_per_m=h[:,1])
        if any(not np.isfinite(v).all() for v in fields.values()):raise ValueError('off-axis B-H fields exceed finite SI arithmetic')
        return fields

    def probe_at(self,points_rz_m):
        points=_numeric_coordinates(points_rz_m,2,'off-axis B-H probe coordinates')
        if points.dtype.kind not in 'fi' or points.ndim!=2 or points.shape[1]!=2 or not len(points) or not np.isfinite(points).all():raise ValueError('off-axis B-H probes require finite [r_m,z_m] points')
        try:cells,bary=self._locator.locate(points)
        except ValueError as exc:raise ValueError('off-axis B-H probe is outside the declared polygon') from exc
        p=self.case.partition;owners=p.cell_region_indices[cells];fields=self.fields_in_cells(cells,bary);state=p.evaluate_cells(cells,np.column_stack((fields['Br_T'],fields['Bz_T'])))
        return dict(points_rz_m=points.tolist(),cell_indices=cells.tolist(),barycentric=bary.tolist(),region_ids=[p.regions[i].id for i in owners],
            material_ids=[p.regions[i].material for i in owners],material_provenance=[p.materials[i].provenance for i in p.cell_material_indices[cells]],
            table_interval_indices=state['interval_indices'].tolist(),secant_reluctivity_m_per_h=state['secant_reluctivity_m_per_h'].tolist(),differential_reluctivity_m_per_h=state['differential_reluctivity_m_per_h'].tolist(),
            azimuthal_model=p.to_dict()['azimuthal_model'],fields={name:value.tolist() for name,value in fields.items()},convention='static P1 psi=r*Aphi[Wb], B=(-psi_z/r,psi_r/r)[T], original H=h(|B|)*B/|B|[A/m]; no extrapolation or excluded-axis absolute flux',
            interface_policy='lowest original cell at exactly represented shared points; original one-sided B/H, no averaging')


def solve_off_axis_bh(case):
    if type(case) is not OffAxisBHCase:raise ValueError('explicit OffAxisBHCase required')
    case=OffAxisBHCase.from_dict(case.to_dict());space=off_axis_bh_space(case.partition,case.element_order);n=len(space.dof_points)
    densities=np.array([case.current_density_phi_a_per_m2[r.id] for r in case.partition.regions]);seed,_,current,_=_assemble(space,np.zeros(n),densities,case.quadrature_order)
    boundary_load=np.zeros(n);potential=np.zeros(n);fixed=np.zeros(n,dtype=bool);fixed_boundaries={};reference=next(b.value for b in case.boundaries if b.kind=='fixed_psi')
    for boundary in case.boundaries:
        if boundary.kind=='fixed_psi':
            dofs=np.unique(space.boundary_dofs[list(boundary.edge_indices)]);fixed[dofs]=True;potential[dofs]=boundary.value-reference;fixed_boundaries[boundary.id]=dofs
        else:
            for edge in boundary.edge_indices:
                owner,_,values,measure,_=_edge_quadrature(space,edge,4)
                np.add.at(boundary_load,space.cell_dofs[owner],TAU*boundary.value*(values.T@measure))
    free=np.flatnonzero(~fixed);total=current+boundary_load
    context=dict(case=case.to_dict(),coefficient_unit='Wb',residual_unit='A',energy_unit='J',reference_psi_wb=reference,coefficient_convention='relative to first fixed-psi boundary; fixed DOFs retained, excluded-axis absolute flux undetermined',quadrature_order=case.quadrature_order)
    if case.initial_psi_relative_to_reference_wb is None:
        if len(free):potential[free]=spsolve(seed[free][:,free],-(seed@potential)[free])
    else:potential=np.array(case.initial_psi_relative_to_reference_wb)
    if not np.isfinite(potential).all() or not np.isfinite(total).all():raise MagneticNonlinearFailure('invalid_initial_arithmetic','fixed boundary extension or total load is nonfinite',context,case.controls,[],None,coefficient_field='psi_relative_to_reference_wb')
    def assemble(values):
        tangent,g,_,q=_assemble(space,values,densities,case.quadrature_order);return tangent,g,q
    potential,k,g,report,residual,iteration=damped_magnetic_newton(assemble,potential,free,total,case.controls,energy_key='energy_j',context=context,coefficient_field='psi_relative_to_reference_wb')
    absolute=potential+reference
    if not np.isfinite(absolute).all():raise MagneticNonlinearFailure('invalid_absolute_potential','absolute psi exceeds finite SI arithmetic',context,case.controls,iteration['history'],potential,coefficient_field='psi_relative_to_reference_wb')
    for values in (potential,absolute,g,current,boundary_load,free,*fixed_boundaries.values()):values.setflags(write=False)
    solution=OffAxisBHSolution(case,space,k,g,current,boundary_load,absolute,potential,reference,free,MappingProxyType(fixed_boundaries),report,iteration,residual)
    report['quadrature_comparison']=_integration_comparison(solution,k,g,current,report);off_axis_bh_quantities(solution)
    return solution


def _integration_comparison(s,k,g,current,report):
    case=s.case;densities=np.array([case.current_density_phi_a_per_m2[r.id] for r in case.partition.regions]);hk,hg,hf,hq=_assemble(s.space,s.psi_relative_to_reference_wb,densities,case.quadrature_order+4)
    total=current+s.boundary_load_a;scale=float(np.linalg.norm(hg)+np.linalg.norm(total));high_residual=float(np.linalg.norm((hg-total)[s.free_dofs]))/scale if scale else 0.
    return dict(orders=[case.quadrature_order,case.quadrature_order+4],tangent_relative_difference=float(np.linalg.norm((k-hk).data)/max(np.linalg.norm(k.data),np.linalg.norm(hk.data))),
        internal_load_relative_difference=_relative_difference(g,hg),current_load_relative_difference=_relative_difference(current,hf),energy_relative_difference=_relative_difference(report['energy_j'],hq['energy_j']),coenergy_relative_difference=_relative_difference(report['coenergy_j'],hq['coenergy_j']),
        free_dof_relative_residual_at_comparison_order=high_residual,comparison_energy_j=hq['energy_j'],comparison_coenergy_j=hq['coenergy_j'],
        interpretation='same coefficients evaluated at q+4, without another Newton solve; diagnostic only, not a field-error bound or a replacement of declared fixed-quadrature convergence')


def off_axis_bh_quantities(solution):
    if type(solution) is not OffAxisBHSolution:raise ValueError('OffAxisBHSolution required')
    s=solution;case=s.case;p=case.partition;densities=np.array([case.current_density_phi_a_per_m2[r.id] for r in p.regions]);k,g,current,report=_assemble(s.space,s.psi_relative_to_reference_wb,densities,case.quadrature_order)
    for b in case.boundaries:
        if b.kind=='fixed_psi' and not np.all(s.psi_relative_to_reference_wb[s.fixed_boundary_dofs[b.id]]==b.value-s.reference_psi_wb):raise ValueError('off-axis B-H coefficients violate fixed-psi boundary values')
    reaction=g-current-s.boundary_load_a;fixed_reaction={name:float(reaction[dofs].sum()) for name,dofs in s.fixed_boundary_dofs.items()};fixed_original=dict.fromkeys(fixed_reaction,0.)
    circulation={b.id:0. for b in case.boundaries};flux=dict.fromkeys(circulation,0.);specified=flux_scale=0.
    for index in range(len(p.mesh.boundary_edges)):
        owner,bary,_,measure,normal=_edge_quadrature(s.space,index,case.quadrature_order+4);fields=s.fields_in_cells(np.full(len(bary),owner,dtype=int),bary);tangent=np.array([-normal[1],normal[0]])
        line=float(measure@(fields['Hr_A_per_m']*tangent[0]+fields['Hz_A_per_m']*tangent[1]));radius=bary@p.mesh.points_rz_m[p.mesh.triangles[owner],0];surface=TAU*radius*measure
        normal_flux=float(surface@(fields['Br_T']*normal[0]+fields['Bz_T']*normal[1]));flux_scale+=float(surface@np.hypot(fields['Br_T'],fields['Bz_T']))
        boundary=case.boundaries[case.boundary_owner_indices[index]];circulation[boundary.id]+=line;flux[boundary.id]+=normal_flux
        if boundary.kind=='fixed_psi':fixed_original[boundary.id]+=TAU*line
        else:specified+=boundary.value*float(measure.sum())
    source_current=report['total_source_current_a'];balance=sum(fixed_reaction.values())/TAU+source_current+specified
    current_scale=float(abs(g).sum()+abs(current).sum()+abs(s.boundary_load_a).sum())/TAU;current_error=abs(balance)/current_scale if current_scale else abs(balance)
    source_work=float(s.psi_wb@current);boundary_work=float(s.psi_wb@s.boundary_load_a);fixed_work=sum(b.value*fixed_reaction[b.id] for b in case.boundaries if b.kind=='fixed_psi')
    work=report['energy_j']+report['coenergy_j'];difference=abs(work-source_work-boundary_work-fixed_work);work_scale=work+abs(source_work)+abs(boundary_work)+abs(fixed_work);work_error=difference/work_scale if work_scale else difference
    if work_error>1e-9:
        term_scale=work+float(abs(s.psi_wb)@abs(current))+float(abs(s.psi_wb)@abs(s.boundary_load_a))+sum(abs(b.value)*float(abs(reaction[s.fixed_boundary_dofs[b.id]]).sum()) for b in case.boundaries if b.kind=='fixed_psi')
        if term_scale:work_error=difference/term_scale
    divergence_error=abs(sum(flux.values()))/flux_scale if flux_scale else abs(sum(flux.values()))
    scale=float(np.linalg.norm(g)+np.linalg.norm(current+s.boundary_load_a));residual=float(np.linalg.norm(reaction[s.free_dofs]))/scale if scale else float(np.linalg.norm(reaction[s.free_dofs]))
    if not np.isfinite([current_error,work_error,divergence_error,residual]).all() or max(current_error,work_error,divergence_error)>1e-9 or residual>case.controls.relative_residual_tolerance:raise ValueError('off-axis B-H nonlinear residual, work/current or divergence-free flux validation failed')
    return dict(energy_j=report['energy_j'],coenergy_j=report['coenergy_j'],bdoth_integral_j=report['bdoth_integral_j'],region_energy_j=report['region_energy_j'],region_coenergy_j=report['region_coenergy_j'],total_source_current_a=source_current,
        specified_tangential_h_integral_a=specified,fixed_boundary_reaction_a=fixed_reaction,fixed_boundary_original_reaction_a=fixed_original,
        boundary_original_h_circulation_a=circulation,original_field_ampere_balance_a=sum(circulation.values())+source_current,
        boundary_original_normal_flux_wb=flux,total_boundary_normal_flux_wb=sum(flux.values()),divergence_free_flux_relative_error=divergence_error,
        discrete_current_balance_a=balance,discrete_current_relative_error=current_error,source_work_j=source_work,boundary_load_work_j=boundary_work,fixed_boundary_work_j=fixed_work,
        discrete_work_relative_error=work_error,legendre_relative_error=report['legendre_relative_error'],free_dof_relative_residual=residual,reference_psi_wb=s.reference_psi_wb,
        quadrature_comparison=_integration_comparison(s,k,g,current,report),boundary_field_quadrature_order=case.quadrature_order+4,
        energy_convention='reversible isotropic U=integral h(b) db dV, Ustar=integral b(h) dh dV [J]; internal work=U+Ustar; no RF phasor',
        circulation_convention='domain-left r,z tangent; curl(H)_phi=d_z(Hr)-d_r(Hz)=Jphi; circulation plus source current is zero',
        reaction_convention='fixed-psi reaction is positive 2*pi integral Ht ds [A], conjugate to psi[Wb]',
        flux_convention='original 2*pi*r B dot outward normal ds [Wb]; minus 2*pi change of psi along boundary; no excluded-axis absolute flux',
        interpretation='declared fixed quadrature and finite boundaries; psi reference changes preserve B/H and energies; nonlinear residual is not a quadrature or field-error bound; no extrapolation, hysteresis, force or inductance inferred')

# SPDX-License-Identifier: Apache-2.0
"""Axis P1 nonlinear magnetic solve with separate integration diagnostics."""
from dataclasses import dataclass,field
from types import MappingProxyType,SimpleNamespace
import numpy as np
from scipy.sparse.linalg import spsolve
from .config import keys,integer
from .constants import TAU
from .bh_curve import _real_array
from .axis_bh_materials import AxisBHPartition
from .axis_bh_fem import axis_bh_space,axis_bh_state,_assemble,_relative_difference
from .nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure,damped_magnetic_newton
from .axis_magnetostatic_boundary import AxisMagnetostaticBoundary,finite_signed,validate_axis_magnetic_boundaries
from .coaxial import _numeric_coordinates
from .planar_polygon import PolygonLocator


@dataclass(frozen=True,eq=False)
class AxisBHCase:
    partition: AxisBHPartition
    current_density_phi_a_per_m2: dict
    boundaries: tuple
    element_order: int=1
    quadrature_order: int=12
    controls: MagneticNewtonControls=field(default_factory=MagneticNewtonControls)
    initial_aphi_over_r_t: tuple|None=None
    name: str='axis-nonlinear-magnetic'
    boundary_owner_indices: np.ndarray=field(init=False,repr=False)

    def __post_init__(self):
        if type(self.partition) is not AxisBHPartition:raise ValueError('explicit AxisBHPartition required')
        p=AxisBHPartition.from_dict(self.partition.to_dict());object.__setattr__(self,'partition',p)
        names=[r.id for r in p.regions];data=dict(self.current_density_phi_a_per_m2) if isinstance(self.current_density_phi_a_per_m2,MappingProxyType) else self.current_density_phi_a_per_m2
        keys(data,names,names,'axis B-H current_density_phi_a_per_m2 by region');current={name:finite_signed(data[name],'current density Jphi for '+name+' [A/m^2]') for name in names};object.__setattr__(self,'current_density_phi_a_per_m2',MappingProxyType(current))
        boundaries,owners=validate_axis_magnetic_boundaries(p.mesh,self.boundaries);object.__setattr__(self,'boundaries',boundaries);object.__setattr__(self,'boundary_owner_indices',owners)
        integer(self.element_order,'axis B-H element_order');integer(self.quadrature_order,'axis B-H quadrature_order')
        if self.element_order!=1 or not 4<=self.quadrature_order<=32:raise ValueError('axis nonlinear B-H Case requires P1 and quadrature_order from 4 to 32')
        if type(self.controls) is not MagneticNewtonControls:raise ValueError('explicit MagneticNewtonControls required')
        object.__setattr__(self,'controls',MagneticNewtonControls.from_dict(self.controls.to_dict()))
        if type(self.name) is not str or not self.name.strip():raise ValueError('axis B-H Case name must be nonempty')
        initial=self.initial_aphi_over_r_t
        if initial is not None:
            if not isinstance(initial,(list,tuple)):raise ValueError('initial Aphi/r must be an explicit list or tuple, or null')
            values=_real_array(initial,'initial Aphi/r [T]')
            if values.shape!=(len(p.mesh.points_rz_m),):raise ValueError('initial Aphi/r requires one coefficient per P1 vertex, including the axis')
            for b in boundaries:
                if b.kind=='fixed_aphi_over_r' and not np.all(values[np.unique(p.mesh.boundary_edges[list(b.edge_indices)])]==b.value):raise ValueError('initial Aphi/r must match every fixed boundary value')
            object.__setattr__(self,'initial_aphi_over_r_t',tuple(map(float,values)))

    def to_dict(self):
        return dict(format='superfish_ng_axis_bh_case',schema_version=1,physics='nonlinear_isotropic_magnetostatic',name=self.name,
            partition=self.partition.to_dict(),current_density_phi_a_per_m2=dict(self.current_density_phi_a_per_m2),boundaries=[b.to_dict() for b in self.boundaries],
            element_order=self.element_order,quadrature_order=self.quadrature_order,controls=self.controls.to_dict(),initial_aphi_over_r_t=None if self.initial_aphi_over_r_t is None else list(self.initial_aphi_over_r_t))

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','physics','name','partition','current_density_phi_a_per_m2','boundaries','element_order','quadrature_order','controls','initial_aphi_over_r_t'];keys(data,names,names,'axis B-H Case')
        if data['format']!='superfish_ng_axis_bh_case' or type(data['schema_version']) is not int or data['schema_version']!=1 or data['physics']!='nonlinear_isotropic_magnetostatic':raise ValueError('expected superfish_ng_axis_bh_case version 1, nonlinear_isotropic_magnetostatic physics')
        if type(data['boundaries']) is not list:raise ValueError('axis B-H boundaries require a JSON list')
        initial=data['initial_aphi_over_r_t']
        if initial is not None and type(initial) is not list:raise ValueError('initial Aphi/r requires a JSON list or null')
        return cls(AxisBHPartition.from_dict(data['partition']),data['current_density_phi_a_per_m2'],[AxisMagnetostaticBoundary.from_dict(v) for v in data['boundaries']],data['element_order'],data['quadrature_order'],MagneticNewtonControls.from_dict(data['controls']),initial,data['name'])


def _edge_quadrature(space,index,order):
    mesh=space.partition.mesh;owner=mesh.boundary_cells[index];a,b=mesh.points_rz_m[mesh.boundary_edges[index]];delta=b-a;length=np.linalg.norm(delta)
    nodes,weights=np.polynomial.legendre.leggauss(order);t=(nodes+1)/2;line=length*weights/2
    local=mesh.boundary_local_vertices[index];bary=np.zeros((len(t),3));bary[:,local[0]]=1-t;bary[:,local[1]]=t
    radius=(1-t)*a[0]+t*b[0];normal=np.array([delta[1],-delta[0]])/length
    return owner,bary,line,radius,normal


@dataclass(eq=False)
class AxisBHSolution:
    case: AxisBHCase
    space: object
    tangent: object
    internal_load_a_m2: np.ndarray
    current_load_a_m2: np.ndarray
    boundary_load_a_m2: np.ndarray
    aphi_over_r_t: np.ndarray
    free_dofs: np.ndarray
    fixed_boundary_dofs: dict
    assembly_report: dict
    iteration_report: dict
    relative_residual: float

    def __post_init__(self):self._locator=PolygonLocator(SimpleNamespace(points_xy_m=self.space.mesh.points,triangles=self.space.mesh.triangles))

    def fields_in_cells(self,cell_indices,barycentric):
        state=axis_bh_state(self.space,self.aphi_over_r_t,cell_indices,barycentric);b=state['b_t'];h=state['h_a_per_m']
        return dict(Aphi_over_r_T=state['a_t'],Aphi_Wb_per_m=state['aphi_wb_per_m'],Br_T=b[:,0],Bz_T=b[:,1],Hr_A_per_m=h[:,0],Hz_A_per_m=h[:,1])

    def probe_at(self,points_rz_m):
        points=_numeric_coordinates(points_rz_m,2,'axis B-H probe coordinates')
        if points.dtype.kind not in 'fi' or points.ndim!=2 or points.shape[1]!=2 or not len(points) or not np.isfinite(points).all() or np.any(points[:,0]<0.):raise ValueError('axis B-H probes require finite [r_m,z_m] points with nonnegative radius')
        try:cells,bary=self._locator.locate(points)
        except ValueError as exc:raise ValueError('axis B-H probe is outside the magnetic domain or inside an excluded hole') from exc
        p=self.case.partition;owners=p.cell_region_indices[cells];state=axis_bh_state(self.space,self.aphi_over_r_t,cells,bary)
        return dict(points_rz_m=points.tolist(),cell_indices=cells.tolist(),barycentric=bary.tolist(),region_ids=[p.regions[i].id for i in owners],material_ids=[p.regions[i].material for i in owners],
            material_provenance=[p.materials[i].provenance for i in p.cell_material_indices[cells]],table_interval_indices=state['interval_indices'].tolist(),secant_reluctivity_m_per_h=state['secant_reluctivity_m_per_h'].tolist(),differential_reluctivity_m_per_h=state['differential_reluctivity_m_per_h'].tolist(),
            azimuthal_model=p.to_dict()['azimuthal_model'],fields={name:value.tolist() for name,value in self.fields_in_cells(cells,bary).items()},
            convention='a=Aphi/r[T], Br=-r*a_z, Bz=2*a+r*a_r[T], original isotropic H=h(|B|)*B/|B|[A/m]; all axis DOFs retained',
            interface_policy='lowest original cell at exactly represented shared points; original one-sided B/H, no averaging')


def _integration_comparison(s,k,g,current,report):
    case=s.case;densities=np.array([case.current_density_phi_a_per_m2[r.id] for r in case.partition.regions]);hk,hg,hf,hq=_assemble(s.space,s.aphi_over_r_t,densities,case.quadrature_order+4)
    total=current+s.boundary_load_a_m2;scale=float(np.linalg.norm(hg)+np.linalg.norm(total));high_residual=float(np.linalg.norm((hg-total)[s.free_dofs]))/scale if scale else 0.
    return dict(orders=[case.quadrature_order,case.quadrature_order+4],tangent_relative_difference=float(np.linalg.norm((k-hk).data)/max(np.linalg.norm(k.data),np.linalg.norm(hk.data))),
        internal_load_relative_difference=_relative_difference(g,hg),current_load_relative_difference=_relative_difference(current,hf),energy_relative_difference=_relative_difference(report['energy_j'],hq['energy_j']),coenergy_relative_difference=_relative_difference(report['coenergy_j'],hq['coenergy_j']),
        free_dof_relative_residual_at_comparison_order=high_residual,comparison_energy_j=hq['energy_j'],comparison_coenergy_j=hq['coenergy_j'],
        interpretation='same coefficients evaluated at q+4, without another Newton solve; diagnostic only, not a field-error bound or a replacement of the declared fixed-quadrature convergence')


def solve_axis_bh(case):
    if type(case) is not AxisBHCase:raise ValueError('explicit AxisBHCase required')
    case=AxisBHCase.from_dict(case.to_dict());space=axis_bh_space(case.partition,case.element_order);n=len(space.dof_points)
    densities=np.array([case.current_density_phi_a_per_m2[r.id] for r in case.partition.regions]);seed,_,current,_=_assemble(space,np.zeros(n),densities,case.quadrature_order)
    boundary_load=np.zeros(n);coefficients=np.zeros(n);fixed=np.zeros(n,dtype=bool);fixed_boundaries={}
    for boundary in case.boundaries:
        if boundary.kind=='fixed_aphi_over_r':
            dofs=np.unique(space.boundary_dofs[list(boundary.edge_indices)]);fixed[dofs]=True;coefficients[dofs]=boundary.value;fixed_boundaries[boundary.id]=dofs
        elif boundary.kind=='tangential_h':
            for edge in boundary.edge_indices:
                owner,bary,line,radius,_=_edge_quadrature(space,edge,4);np.add.at(boundary_load,space.cell_dofs[owner],boundary.value*(bary.T@(TAU*radius**2*line)))
    free=np.flatnonzero(~fixed);total=current+boundary_load
    context=dict(case=case.to_dict(),coefficient_unit='T',residual_unit='A m^2',energy_unit='J',coefficient_convention='regular a=Aphi/r; all axis and fixed DOFs retained, no constant gauge shift',quadrature_order=case.quadrature_order)
    if case.initial_aphi_over_r_t is None:
        if len(free) and np.any(fixed):coefficients[free]=spsolve(seed[free][:,free],-(seed@coefficients)[free])
    else:coefficients=np.array(case.initial_aphi_over_r_t)
    if not np.isfinite(coefficients).all() or not np.isfinite(total).all():raise MagneticNonlinearFailure('invalid_initial_arithmetic','fixed boundary extension or total load is nonfinite',context,case.controls,[],None,coefficient_field='aphi_over_r_t')
    def assemble(values):
        k,g,_,q=_assemble(space,values,densities,case.quadrature_order);return k,g,q
    coefficients,k,g,report,residual,iteration=damped_magnetic_newton(assemble,coefficients,free,total,case.controls,energy_key='energy_j',context=context,coefficient_field='aphi_over_r_t')
    for values in (coefficients,g,current,boundary_load,free,*fixed_boundaries.values()):values.setflags(write=False)
    solution=AxisBHSolution(case,space,k,g,current,boundary_load,coefficients,free,MappingProxyType(fixed_boundaries),report,iteration,residual)
    report['quadrature_comparison']=_integration_comparison(solution,k,g,current,report);axis_bh_quantities(solution)
    return solution


def axis_bh_quantities(solution):
    if type(solution) is not AxisBHSolution:raise ValueError('AxisBHSolution required')
    s=solution;case=s.case;p=case.partition;densities=np.array([case.current_density_phi_a_per_m2[r.id] for r in p.regions]);k,g,current,report=_assemble(s.space,s.aphi_over_r_t,densities,case.quadrature_order)
    for b in case.boundaries:
        if b.kind=='fixed_aphi_over_r' and not np.all(s.aphi_over_r_t[s.fixed_boundary_dofs[b.id]]==b.value):raise ValueError('axis B-H coefficients violate fixed Aphi/r boundary values')
    reaction=g-current-s.boundary_load_a_m2;fixed_reaction={name:float(reaction[dofs].sum()) for name,dofs in s.fixed_boundary_dofs.items()};fixed_original=dict.fromkeys(fixed_reaction,0.)
    circulation={b.id:0. for b in case.boundaries};flux=dict.fromkeys(circulation,0.);weighted_h=dict.fromkeys(circulation,0.);flux_scale=0.
    for index in range(len(p.mesh.boundary_edges)):
        owner,bary,line,radius,normal=_edge_quadrature(s.space,index,case.quadrature_order+4);fields=s.fields_in_cells(np.full(len(bary),owner,dtype=int),bary);tangent=np.array([-normal[1],normal[0]])
        ht=fields['Hr_A_per_m']*tangent[0]+fields['Hz_A_per_m']*tangent[1];boundary=case.boundaries[case.boundary_owner_indices[index]];circulation[boundary.id]+=float(line@ht)
        weighted=float((TAU*radius**2*line)@ht);weighted_h[boundary.id]+=weighted
        if boundary.kind=='fixed_aphi_over_r':fixed_original[boundary.id]+=weighted
        surface=TAU*radius*line;flux[boundary.id]+=float(surface@(fields['Br_T']*normal[0]+fields['Bz_T']*normal[1]));flux_scale+=float(surface@np.hypot(fields['Br_T'],fields['Bz_T']))
    source_work=float(s.aphi_over_r_t@current);boundary_work=float(s.aphi_over_r_t@s.boundary_load_a_m2);fixed_work=sum(b.value*fixed_reaction[b.id] for b in case.boundaries if b.kind=='fixed_aphi_over_r')
    work=report['energy_j']+report['coenergy_j'];difference=abs(work-source_work-boundary_work-fixed_work);work_scale=work+abs(source_work)+abs(boundary_work)+abs(fixed_work);work_error=difference/work_scale if work_scale else difference
    if work_error>1e-9:
        term_scale=work+float(abs(s.aphi_over_r_t)@abs(current))+float(abs(s.aphi_over_r_t)@abs(s.boundary_load_a_m2))+sum(abs(b.value)*float(abs(reaction[s.fixed_boundary_dofs[b.id]]).sum()) for b in case.boundaries if b.kind=='fixed_aphi_over_r')
        if term_scale:work_error=difference/term_scale
    moment=report['twice_axial_h_volume_integral_a_m2']-float(current.sum())-float(s.boundary_load_a_m2.sum())-sum(fixed_reaction.values());moment_scale=float(abs(g).sum()+abs(current).sum()+abs(s.boundary_load_a_m2).sum()+sum(abs(v) for v in fixed_reaction.values()));moment_error=abs(moment)/moment_scale if moment_scale else abs(moment)
    divergence_error=abs(sum(flux.values()))/flux_scale if flux_scale else abs(sum(flux.values()));scale=float(np.linalg.norm(g)+np.linalg.norm(current+s.boundary_load_a_m2));residual=float(np.linalg.norm(reaction[s.free_dofs]))/scale if scale else float(np.linalg.norm(reaction[s.free_dofs]))
    if not np.isfinite([work_error,moment_error,divergence_error,residual]).all() or max(work_error,moment_error,divergence_error)>1e-9 or residual>case.controls.relative_residual_tolerance:raise ValueError('axis B-H nonlinear residual, work/current test or divergence-free flux validation failed')
    return dict(energy_j=report['energy_j'],coenergy_j=report['coenergy_j'],bdoth_integral_j=report['bdoth_integral_j'],region_energy_j=report['region_energy_j'],region_coenergy_j=report['region_coenergy_j'],
        total_source_current_a=report['total_source_current_a'],fixed_boundary_reaction_a_m2=fixed_reaction,fixed_boundary_original_reaction_a_m2=fixed_original,
        boundary_original_h_circulation_a=circulation,boundary_original_weighted_h_a_m2=weighted_h,original_field_ampere_balance_a=sum(circulation.values())+report['total_source_current_a'],
        boundary_original_normal_flux_wb=flux,total_boundary_normal_flux_wb=sum(flux.values()),divergence_free_flux_relative_error=divergence_error,
        source_work_j=source_work,boundary_load_work_j=boundary_work,fixed_boundary_work_j=fixed_work,discrete_work_relative_error=work_error,legendre_relative_error=report['legendre_relative_error'],
        constant_test_h_volume_a_m2=report['twice_axial_h_volume_integral_a_m2'],discrete_current_work_balance_a_m2=moment,discrete_current_work_relative_error=moment_error,free_dof_relative_residual=residual,
        quadrature_comparison=_integration_comparison(s,k,g,current,report),boundary_field_quadrature_order=case.quadrature_order+4,
        energy_convention='reversible isotropic U=integral h(b) db dV, Ustar=integral b(h) dh dV [J]; internal work=U+Ustar',
        circulation_convention='domain-left r,z tangent; curl(H)_phi=d_z(Hr)-d_r(Hz)=Jphi; H circulation plus cross-section current is zero, including axis H',
        reaction_convention='fixed Aphi/r reaction is positive 2*pi integral r^2 Ht ds [A m^2], conjugate to a[T], distinct from current[A]',flux_convention='2*pi integral r B dot outward normal ds [Wb]',
        interpretation='declared fixed quadrature and finite boundaries; nonlinear residual is not a quadrature or field-error bound; regular a has no constant gauge; no extrapolation, hysteresis, force or inductance inferred')

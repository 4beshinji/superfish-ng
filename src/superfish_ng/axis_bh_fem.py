# SPDX-License-Identifier: Apache-2.0
"""Nonlinear axis P1 forms in a=Aphi/r[T], with explicit quadrature diagnostics."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from .axis_bh_materials import AxisBHPartition
from .bh_curve import _real_array
from .config import integer,keys
from .constants import TAU
from .magnetostatic_boundary import finite_signed,magnetic_field_coordinates
from .mesh import Mesh,element_geometry
from .fem import triangle_quadrature


@dataclass(frozen=True)
class AxisBHSpace:
    partition: AxisBHPartition
    mesh: Mesh
    element_order: int
    dof_points: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray
    axis_dofs: np.ndarray
    determinant_m2: np.ndarray
    gradients_per_m: np.ndarray


def axis_bh_space(partition,element_order=1):
    if type(partition) is not AxisBHPartition:raise ValueError('explicit AxisBHPartition required')
    integer(element_order,'axis B-H element_order')
    if element_order!=1:raise ValueError('axis nonlinear B-H forms require P1; P2 nonlinear integration is unsupported')
    partition=AxisBHPartition.from_dict(partition.to_dict());p=partition.mesh
    mesh=Mesh(p.points_rz_m,p.triangles,p.boundary_edges,p.boundary_tags,p.boundary_cells,p.axis_nodes);_,det,grad=element_geometry(mesh)
    for array in (mesh.points,mesh.triangles,mesh.boundary_edges,mesh.axis_nodes,det,grad):array.setflags(write=False)
    return AxisBHSpace(partition,mesh,1,mesh.points,mesh.triangles,mesh.boundary_edges,p.axis_nodes,det,grad)


def _coefficients(space,values):
    if type(space) is not AxisBHSpace:raise ValueError('explicit AxisBHSpace required')
    values=_real_array(values,'axis P1 a=Aphi/r [T]')
    if values.shape!=(len(space.dof_points),):raise ValueError('axis P1 a requires one coefficient per vertex, including every axis vertex')
    return values


def _sample_state(space,coefficients,cells,bary):
    radius=np.einsum('qi,qi->q',space.mesh.points[space.cell_dofs[cells],0],bary);derivatives=space.gradients_per_m[cells]
    curls=np.stack((-radius[:,None]*derivatives[:,:,1],2*bary+radius[:,None]*derivatives[:,:,0]),axis=-1)
    local=coefficients[space.cell_dofs[cells]];a=np.einsum('qi,qi->q',local,bary)
    with np.errstate(over='ignore',invalid='ignore'):
        b=np.einsum('qi,qia->qa',local,curls);aphi=radius*a
    if not np.isfinite(b).all() or not np.isfinite(a).all() or not np.isfinite(aphi).all():raise ValueError('axis B-H field exceeds finite SI arithmetic')
    state=space.partition.evaluate_cells(cells,b)
    return dict(state,b_t=b,a_t=a,aphi_wb_per_m=aphi,radius_m=radius),curls


def axis_bh_state(space,coefficients,cell_indices,barycentric):
    values=_coefficients(space,coefficients);cells,bary=magnetic_field_coordinates(cell_indices,barycentric,len(space.cell_dofs))
    return _sample_state(space,values,cells,bary)[0]


def _assemble(space,coefficients,densities,quadrature_order):
    coefficients=_coefficients(space,coefficients);integer(quadrature_order,'axis B-H quadrature_order')
    if not 4<=quadrature_order<=36:raise ValueError('axis B-H assembly quadrature_order requires 4 to 36')
    p=space.partition;dofs=space.cell_dofs;cells=np.arange(len(dofs));n=len(space.dof_points);current=densities[p.cell_region_indices]
    # Original P1 B is affine. Its norm reaches a maximum at a triangle
    # vertex, so these checks also cover field values between quadrature nodes.
    for vertex in np.eye(3):_sample_state(space,coefficients,cells,np.broadcast_to(vertex,(len(cells),3)))
    local_k=np.zeros((len(cells),3,3));local_g=np.zeros((len(cells),3));local_f=np.zeros_like(local_g)
    cell_energy=np.zeros(len(cells));cell_coenergy=np.zeros_like(cell_energy);cell_bdoth=np.zeros_like(cell_energy);constant_work=np.zeros_like(cell_energy)
    intervals={r.id:set() for r in p.regions}
    for bary,weight in triangle_quadrature(quadrature_order):
        state,curls=_sample_state(space,coefficients,cells,np.broadcast_to(bary,(len(cells),3)));radius=state['radius_m'];measure=TAU*radius*weight*space.determinant_m2
        with np.errstate(over='ignore',under='ignore',invalid='ignore'):
            local_k+=measure[:,None,None]*np.einsum('tia,tab,tjb->tij',curls,state['tangent_reluctivity_m_per_h'],curls)
            local_g+=measure[:,None]*np.einsum('tia,ta->ti',curls,state['h_a_per_m'])
            local_f+=(measure*radius*current)[:,None]*bary[None,:]
            cell_energy+=measure*state['energy_density_j_per_m3'];cell_coenergy+=measure*state['coenergy_density_j_per_m3']
            cell_bdoth+=measure*np.sum(state['b_t']*state['h_a_per_m'],axis=1);constant_work+=2*measure*state['h_a_per_m'][:,1]
        for i,r in enumerate(p.regions):intervals[r.id].update(map(int,np.unique(state['interval_indices'][p.cell_region_indices==i])))
    if any(not np.isfinite(v).all() for v in (local_k,local_g,local_f,cell_energy,cell_coenergy,cell_bdoth,constant_work)):raise ValueError('axis B-H forms exceed finite SI arithmetic')
    rows=np.repeat(dofs,3,axis=1).ravel();columns=np.tile(dofs,(1,3)).ravel();k=coo_matrix((local_k.ravel(),(rows,columns)),shape=(n,n)).tocsr()
    g=np.bincount(dofs.ravel(),weights=local_g.ravel(),minlength=n);f=np.bincount(dofs.ravel(),weights=local_f.ravel(),minlength=n)
    if not np.isfinite(k.data).all() or np.any(k.diagonal()<=0.) or not np.isfinite(g).all() or not np.isfinite(f).all():raise ValueError('axis B-H assembly exceeds finite positive SI arithmetic')
    energy=float(cell_energy.sum());coenergy=float(cell_coenergy.sum());bdoth=float(cell_bdoth.sum());work=float(coefficients@g);expected_constant=float(constant_work.sum());constant_scale=float(abs(local_g).sum()+abs(constant_work).sum())
    scale=energy+coenergy;work_error=abs(work-bdoth)/scale if scale else abs(work-bdoth);legendre_error=abs(bdoth-scale)/scale if scale else abs(bdoth-scale)
    constant_error=abs(float(g.sum())-expected_constant)/constant_scale if constant_scale else abs(float(g.sum())-expected_constant)
    norm=float(np.linalg.norm(k.data));symmetry=float(np.linalg.norm((k-k.T).data)/norm)
    radii=space.mesh.points[space.mesh.triangles,0];moment=TAU*space.determinant_m2/2*(np.sum(radii*radii,axis=1)+radii[:,0]*radii[:,1]+radii[:,1]*radii[:,2]+radii[:,2]*radii[:,0])/6
    cell_source=current*moment;source_scale=float(abs(cell_source).sum());source_work=float(cell_source.sum());source_error=abs(float(f.sum())-source_work)/source_scale if source_scale else abs(float(f.sum())-source_work)
    if np.any((current!=0.)&(cell_source==0.)):raise ValueError('axis B-H current radial moment is unresolved in SI arithmetic')
    source_current=np.array([densities[i]*area for i,area in enumerate(p.region_area_m2)])
    if not np.isfinite([energy,coenergy,bdoth,work,constant_error,expected_constant,work_error,legendre_error,symmetry,source_work,source_error,*source_current]).all() or max(constant_error,work_error,legendre_error,symmetry,source_error)>1e-10:
        raise ValueError('axis B-H energy, constant-a test or current work identities are numerically unresolved')
    if np.any(coefficients!=0.) and (energy<=0. or coenergy<=0.):raise ValueError('axis B-H nonzero field energy is unresolved in SI arithmetic')
    owners=p.cell_region_indices
    report=dict(energy_j=energy,coenergy_j=coenergy,bdoth_integral_j=bdoth,internal_work_j=work,discrete_work_relative_error=work_error,legendre_relative_error=legendre_error,
        constant_a_test_relative_error=constant_error,constant_a_internal_load_a_m2=float(g.sum()),twice_axial_h_volume_integral_a_m2=expected_constant,tangent_symmetry_relative_error=symmetry,
        total_source_current_a=float(source_current.sum()),region_source_current_a={v.id:float(source_current[i]) for i,v in enumerate(p.regions)},
        total_current_radial_moment_a_m2=source_work,sum_current_load_a_m2=float(f.sum()),current_work_relative_error=source_error,
        region_current_radial_moment_a_m2={v.id:float(cell_source[owners==i].sum()) for i,v in enumerate(p.regions)},
        region_energy_j={v.id:float(cell_energy[owners==i].sum()) for i,v in enumerate(p.regions)},region_coenergy_j={v.id:float(cell_coenergy[owners==i].sum()) for i,v in enumerate(p.regions)},
        table_intervals_used={name:sorted(value) for name,value in intervals.items()},element_order=1,quadrature_order=quadrature_order,
        coefficient_unit='T',tangent_unit='m^4/H',internal_load_unit='A m^2',current_load_unit='A m^2',energy_unit='J',volume_measure='2*pi*r dr dz',
        constitutive_relation='H=h(|B|)*B/|B|; isotropic monotone piecewise-linear H(B), explicit one-sided knot tangent; no extrapolation',
        axis_dofs_retained=len(space.axis_dofs),constant_a_is_gauge=False,boundary_conditions_applied=False,nonlinear_iteration_performed=False,
        integration='fixed positive triangle quadrature; original P1 B is affine, nonlinear H/tangent/energy generally are not polynomials',
        interpretation='regular a=Aphi/r forms; constant a gives uniform Bz=2a; work=U+Ustar, not generally 2U; no boundary solve or discretization-error bound')
    return k,g,f,report


def _relative_difference(a,b):
    scale=max(float(np.linalg.norm(a)),float(np.linalg.norm(b)));return float(np.linalg.norm(a-b))/scale if scale else 0.


def axis_bh_forms(partition,coefficients,current_density_phi_a_per_m2,element_order=1,*,quadrature_order=12):
    space=axis_bh_space(partition,element_order);integer(quadrature_order,'axis B-H quadrature_order')
    if not 4<=quadrature_order<=32:raise ValueError('axis B-H quadrature_order requires 4 to 32; a separate q+4 comparison is reported')
    names=[r.id for r in space.partition.regions];keys(current_density_phi_a_per_m2,names,names,'axis B-H current_density_phi_a_per_m2 by region')
    densities=np.array([finite_signed(current_density_phi_a_per_m2[name],'azimuthal current Jphi for '+name+' [A/m^2]') for name in names])
    k,g,f,q=_assemble(space,coefficients,densities,quadrature_order);hk,hg,hf,hq=_assemble(space,coefficients,densities,quadrature_order+4)
    q['quadrature_comparison']=dict(orders=[quadrature_order,quadrature_order+4],tangent_relative_difference=float(np.linalg.norm((k-hk).data)/max(np.linalg.norm(k.data),np.linalg.norm(hk.data))),
        internal_load_relative_difference=_relative_difference(g,hg),current_load_relative_difference=_relative_difference(f,hf),
        energy_relative_difference=_relative_difference(q['energy_j'],hq['energy_j']),coenergy_relative_difference=_relative_difference(q['coenergy_j'],hq['coenergy_j']),
        interpretation='diagnostic only; a difference between two quadrature rules is not a field error bound or a nonlinear convergence test')
    return space,k,g,f,q

# SPDX-License-Identifier: Apache-2.0
"""P1 nonlinear planar magnetic internal load, tangent and source weak forms."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from .bh_curve import _real_array
from .planar_bh_materials import PlanarBHPartition
from .magnetostatic_boundary import finite_signed
from .config import keys,integer
from .mesh import Mesh,element_geometry


@dataclass(frozen=True)
class PlanarBHSpace:
    partition: PlanarBHPartition
    mesh: Mesh
    element_order: int
    dof_points_xy_m: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray
    cell_areas_m2: np.ndarray
    curls: np.ndarray


def planar_bh_space(partition,element_order=1):
    if type(partition) is not PlanarBHPartition:raise ValueError('explicit PlanarBHPartition required')
    integer(element_order,'planar B-H element_order')
    if element_order!=1:raise ValueError('planar nonlinear B-H forms currently require P1; P2 nonlinear material integration is unsupported')
    partition=PlanarBHPartition.from_dict(partition.to_dict());p=partition.mesh
    mesh=Mesh(p.points_xy_m,p.triangles,p.boundary_edges,np.full(len(p.boundary_edges),'boundary',dtype='U20'),p.boundary_cells,np.array([],dtype=np.int64))
    _,det,grad=element_geometry(mesh);areas=det/2;curls=np.stack((grad[:,:,1],-grad[:,:,0]),axis=-1)
    for array in (mesh.points,mesh.triangles,mesh.boundary_edges,areas,curls):array.setflags(write=False)
    return PlanarBHSpace(partition,mesh,1,mesh.points,mesh.triangles,mesh.boundary_edges,areas,curls)


def planar_bh_cell_state(space,az_wb_per_m):
    if type(space) is not PlanarBHSpace:raise ValueError('explicit PlanarBHSpace required')
    coefficients=_real_array(az_wb_per_m,'P1 Az [Wb/m]')
    if coefficients.shape!=(len(space.dof_points_xy_m),):raise ValueError('P1 Az requires exactly one real value per mesh vertex')
    with np.errstate(over='ignore',invalid='ignore'):
        relative=coefficients-coefficients[0];b=np.einsum('ti,tia->ta',relative[space.cell_dofs],space.curls)
    if not np.isfinite(relative).all() or not np.isfinite(b).all():raise ValueError('P1 Az differences or cell B exceed finite SI arithmetic')
    state=space.partition.evaluate_cells(np.arange(len(space.cell_dofs)),b)
    return dict(state,b_t=b,az_relative_to_reference_wb_per_m=relative,reference_az_wb_per_m=float(coefficients[0]))


def _assemble(space,coefficients,densities):
    state=planar_bh_cell_state(space,coefficients);p=space.partition;area=space.cell_areas_m2;dofs=space.cell_dofs;n=len(space.dof_points_xy_m)
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):
        local_k=area[:,None,None]*np.einsum('tia,tab,tjb->tij',space.curls,state['tangent_reluctivity_m_per_h'],space.curls)
        local_g=area[:,None]*np.einsum('tia,ta->ti',space.curls,state['h_a_per_m'])
        cell_current=area*densities[p.cell_region_indices];local_f=np.repeat((cell_current/3)[:,None],3,axis=1)
        cell_energy=area*state['energy_density_j_per_m3'];cell_coenergy=area*state['coenergy_density_j_per_m3']
    if (any(not np.isfinite(v).all() for v in (local_k,local_g,local_f,cell_energy,cell_coenergy))
        or np.any((state['magnitude_b_t']>0.)&((cell_energy<=0.)|(cell_coenergy<=0.)))
        or np.any((densities[p.cell_region_indices]!=0.)&(cell_current==0.))):raise ValueError('planar B-H forms are unresolved in finite SI arithmetic')
    rows=np.repeat(dofs,3,axis=1).ravel();columns=np.tile(dofs,(1,3)).ravel();k=coo_matrix((local_k.ravel(),(rows,columns)),shape=(n,n)).tocsr()
    g=np.bincount(dofs.ravel(),weights=local_g.ravel(),minlength=n);f=np.bincount(dofs.ravel(),weights=local_f.ravel(),minlength=n)
    if not np.isfinite(k.data).all() or np.any(k.diagonal()<=0.) or not np.isfinite(g).all() or not np.isfinite(f).all():raise ValueError('planar B-H assembly exceeds finite positive SI arithmetic')
    energy=float(cell_energy.sum());coenergy=float(cell_coenergy.sum());work=float(state['az_relative_to_reference_wb_per_m']@g)
    bdoth=float(area@np.sum(state['b_t']*state['h_a_per_m'],axis=1));scale=energy+coenergy
    work_error=abs(work-bdoth)/scale if scale else abs(work-bdoth);legendre_error=abs(bdoth-scale)/scale if scale else abs(bdoth-scale)
    norm=float(np.linalg.norm(k.data));kernel=float(np.linalg.norm(k@np.ones(n))/norm);symmetry=float(np.linalg.norm((k-k.T).data)/norm)
    gscale=float(abs(g).sum());zero_sum=abs(float(g.sum()))/gscale if gscale else 0.
    source=float(cell_current.sum());source_scale=float(abs(cell_current).sum());source_error=abs(float(f.sum())-source)/source_scale if source_scale else abs(float(f.sum())-source)
    if not np.isfinite([energy,coenergy,bdoth,work,work_error,legendre_error,kernel,symmetry,zero_sum,source,source_error]).all() or max(work_error,legendre_error,kernel,symmetry,zero_sum,source_error)>1e-10:
        raise ValueError('planar B-H work, gauge or current identities are numerically unresolved')
    owners=p.cell_region_indices;region_energy=np.bincount(owners,weights=cell_energy,minlength=len(p.regions));region_coenergy=np.bincount(owners,weights=cell_coenergy,minlength=len(p.regions));region_current=np.bincount(owners,weights=cell_current,minlength=len(p.regions))
    report=dict(energy_j_per_m=energy,coenergy_j_per_m=coenergy,bdoth_integral_j_per_m=bdoth,internal_work_j_per_m=work,
        discrete_work_relative_error=work_error,legendre_relative_error=legendre_error,constant_kernel_relative_error=kernel,tangent_symmetry_relative_error=symmetry,internal_zero_sum_relative_error=zero_sum,current_conservation_relative_error=source_error,
        total_current_a=source,region_current_a={v.id:float(region_current[i]) for i,v in enumerate(p.regions)},
        region_energy_j_per_m={v.id:float(region_energy[i]) for i,v in enumerate(p.regions)},region_coenergy_j_per_m={v.id:float(region_coenergy[i]) for i,v in enumerate(p.regions)},
        table_intervals_used={v.id:np.unique(state['interval_indices'][owners==i]).tolist() for i,v in enumerate(p.regions)},
        element_order=1,coefficient_unit='Wb/m',tangent_unit='m/H',internal_load_unit='A',current_load_unit='A',measure='dx*dy per metre of uniform extrusion',
        constitutive_relation='H=h(|B|)*B/|B|; isotropic monotone piecewise-linear H(B), explicit one-sided node tangent; no extrapolation',
        potentials='U=integral h(b) db dA; Ustar=integral b(h) dh dA [J/m]; Az dot internal_load=U+Ustar, generally not 2U',
        integration='P1 constant original cell B/H/tangent, exact cell-area integration; no nonlinear quadrature approximation',
        constant_Az_gauge_kernel_retained=True,boundary_conditions_applied=False,nonlinear_iteration_performed=False,
        interpretation='internal load and derivative only; no solve, field discretization-error bound, hysteresis, force or RF phasor')
    return k,g,f,report


def planar_bh_forms(partition,az_wb_per_m,current_density_z_a_per_m2,element_order=1):
    space=planar_bh_space(partition,element_order);names=[r.id for r in space.partition.regions]
    keys(current_density_z_a_per_m2,names,names,'planar B-H current_density_z_a_per_m2 by region')
    densities=np.array([finite_signed(current_density_z_a_per_m2[name],'current density for '+name+' [A/m^2]') for name in names])
    return (space,*_assemble(space,az_wb_per_m,densities))

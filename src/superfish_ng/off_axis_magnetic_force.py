# SPDX-License-Identifier: Apache-2.0
"""Full-ring axial Maxwell force and independent displaced-FEM work for r>0."""
import hashlib,json
import numpy as np
from .constants import MU0,TAU
from .bh_curve import _real_array
from .off_axis_magnetostatic import OffAxisMagnetostaticCase,OffAxisMagnetostaticSolution,solve_off_axis_magnetostatic,off_axis_magnetostatic_quantities


def _request(case,body_region_ids,weights):
    if type(case) is not OffAxisMagnetostaticCase:raise ValueError('axial force requires an explicit positive-radius linear scalar OffAxisMagnetostaticCase; axis-connected, recoil/B-H and planar sources require different contracts')
    p=case.partition;mesh=p.mesh
    if not isinstance(body_region_ids,(list,tuple)) or not body_region_ids or any(type(v) is not str for v in body_region_ids) or len(set(body_region_ids))!=len(body_region_ids):raise ValueError('axial-force body_region_ids must be a nonempty distinct string sequence')
    if not set(body_region_ids)<=set(r.id for r in p.regions):raise ValueError('axial-force body_region_ids contains an unknown region')
    w=_real_array(weights,'axial-force P1 weights')
    if w.shape!=(len(mesh.points_rz_m),) or np.any(w<0.) or np.any(w>1.):raise ValueError('axial force requires one finite weight in [0,1] per original mesh vertex')
    if np.any(w[np.unique(mesh.boundary_edges)]!=0.):raise ValueError('axial-force weights must vanish on every outer and hole boundary')
    values=w[mesh.triangles];current=np.array([case.current_density_phi_a_per_m2[r.id] for r in p.regions])[p.cell_region_indices];body=np.array([r.id in body_region_ids for r in p.regions])[p.cell_region_indices];varying=np.any(values!=values[:,0,None],axis=1)
    if np.any(values[body]!=1.):raise ValueError('axial-force weights must equal one throughout every body cell')
    if np.any((p.mu_r[varying]!=1.)|(current[varying]!=0.)):raise ValueError('axial-force weight gradients require strictly vacuum mu_r=1 and Jphi=0 cells')
    fixed_other=(~body)&((p.mu_r!=1.)|(current!=0.))
    if np.any(values[fixed_other]!=0.):raise ValueError('other current or nonvacuum regions must have weight zero')
    if not np.any(varying):raise ValueError('axial force requires a nonempty surrounding vacuum weight transition')
    return w,body,varying


def _verified(solution):
    if type(solution) is not OffAxisMagnetostaticSolution:raise ValueError('axial force requires an explicit positive-radius linear scalar OffAxisMagnetostaticSolution')
    fresh=solve_off_axis_magnetostatic(solution.case)
    if solution.reference_psi_wb!=fresh.reference_psi_wb or any(not np.array_equal(getattr(solution,key),getattr(fresh,key)) for key in ('psi_wb','psi_relative_to_reference_wb')):raise ValueError('axial-force source coefficients disagree with actual FEM replay')
    return fresh


def _stress_integral(solution,w,order):
    mesh=solution.case.partition.mesh;vertices=mesh.points_rz_m[mesh.triangles];a=vertices[:,1]-vertices[:,0];b=vertices[:,2]-vertices[:,0];det=a[:,0]*b[:,1]-a[:,1]*b[:,0];values=w[mesh.triangles];gradient=((values[:,1]-values[:,0])[:,None]*np.column_stack((b[:,1],-b[:,0]))+(values[:,2]-values[:,0])[:,None]*np.column_stack((-a[:,1],a[:,0])))/det[:,None];cells=np.arange(len(vertices));contributions=np.zeros(len(cells));absolute=0.
    nodes,weights=np.polynomial.legendre.leggauss(order);nodes=(nodes+1)/2;weights=weights/2
    for i,x in enumerate(nodes):
        for j,t in enumerate(nodes):
            y=(1-x)*t;bary=np.array([1-x-y,x,y]);radius=np.einsum('i,ti->t',bary,vertices[:,:,0]);fields=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)));br=fields['Br_T'];bz=fields['Bz_T']
            with np.errstate(over='ignore',invalid='ignore'):
                density=-TAU*radius/MU0*(bz*br*gradient[:,0]+.5*(bz*bz-br*br)*gradient[:,1]);part=weights[i]*weights[j]*(1-x)*det*density
            if not np.isfinite(part).all():raise ValueError('full-ring axial force exceeds finite SI arithmetic')
            contributions+=part;absolute+=float(abs(part).sum())
    if not np.isfinite(contributions).all() or not np.isfinite(absolute):raise ValueError('axial-force integral accumulation exceeds finite N arithmetic')
    return contributions,absolute


def off_axis_magnetic_force(solution,body_region_ids,weights):
    fresh=_verified(solution);w,body,varying=_request(fresh.case,body_region_ids,weights);order=fresh.case.quadrature_order;parts,absolute=_stress_integral(fresh,w,order);other,_=_stress_integral(fresh,w,order+4);value=float(parts.sum());difference=float((other-parts).sum());scale=max(absolute,abs(value));relative=abs(difference)/scale if scale else 0.
    if not np.isfinite([value,difference,relative]).all():raise ValueError('axial-force total or diagnostic exceeds finite SI arithmetic')
    return dict(format='superfish_ng_off_axis_magnetic_force',schema_version=1,source_case_sha256=hashlib.sha256(json.dumps(fresh.case.to_dict(),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),source_relative_psi_sha256=hashlib.sha256(fresh.psi_relative_to_reference_wb.tobytes()).hexdigest(),body_region_ids=list(body_region_ids),weights=w.tolist(),body_cell_indices=np.flatnonzero(body).tolist(),vacuum_transition_cells=np.flatnonzero(varying).tolist(),force_z_n=value,cell_force_z_n=parts.tolist(),absolute_integral_scale_n=absolute,quadrature_orders=[order,order+4],quadrature_difference_n=difference,quadrature_relative_difference=relative,
        conventions='static original FEM Br/Bz, psi=r*Aphi [Wb], r>0; T=(B tensor B-|B|^2 I/2)/mu0 in vacuum; Fz=-integral 2*pi*r*(Tzr*dw/dr+Tzz*dw/dz) dr dz [N] for the full annular body, not force per unit length',
        interpretation='explicit body and continuous P1 vacuum weight; original field without smoothing. Global transverse force and axial torque vanish by axisymmetry; radial stress is not a net transverse vector force. Mesh, weight and quadrature differences are separate diagnostics, not a continuum error bound. Axis-connected, recoil/B-H and curved sources require separate verification.')


def _displaced_case(case,w,step):
    points=case.partition.mesh.points_rz_m;moved=points+w[:,None]*np.array([0.,step])
    if not np.isfinite(moved).all():raise ValueError('virtual axial displacement exceeds finite SI geometry')
    if np.array_equal(moved,points):raise ValueError('virtual axial displacement is not resolved in SI coordinates')
    data=case.to_dict();data['partition']['geometry']['points_rz_m']=moved.tolist();trial=OffAxisMagnetostaticCase.from_dict(data)
    for i,region in enumerate(case.partition.regions):data['current_density_phi_a_per_m2'][region.id]=case.current_density_phi_a_per_m2[region.id]*case.partition.region_area_m2[i]/trial.partition.region_area_m2[i]
    return OffAxisMagnetostaticCase.from_dict(data)


def _stationary_potential(solution):
    energy=off_axis_magnetostatic_quantities(solution)['energy_j'];source_work=float(solution.psi_wb@(solution.volume_load_a+solution.boundary_load_a));potential=energy-source_work
    if not np.isfinite([energy,source_work,potential]).all():raise ValueError('full-ring stationary potential exceeds finite J arithmetic')
    return dict(stationary_potential_j=potential,energy_j=energy,source_and_boundary_work_j=source_work)


def off_axis_magnetic_virtual_work(case,body_region_ids,weights,translation_steps_m):
    w,body,varying=_request(case,body_region_ids,weights);steps=_real_array(translation_steps_m,'virtual axial translation steps [m]')
    if steps.ndim!=1 or not 2<=len(steps)<=8 or np.any(steps<=0.) or np.any(steps[1:]>=steps[:-1]):raise ValueError('virtual axial translation requires 2..8 strictly decreasing positive finite steps')
    base=solve_off_axis_magnetostatic(case);records=[]
    for step in steps:
        trials=[]
        for sign in (-1.,1.):
            trial=_displaced_case(case,w,sign*step);solution=solve_off_axis_magnetostatic(trial);trials.append(dict(sign=sign,case=trial.to_dict(),**_stationary_potential(solution),relative_residual=solution.relative_residual,relative_psi_sha256=hashlib.sha256(solution.psi_relative_to_reference_wb.tobytes()).hexdigest()))
        derivative=-(trials[1]['stationary_potential_j']-trials[0]['stationary_potential_j'])/(2*step)
        if not np.isfinite(derivative):raise ValueError('virtual axial-work derivative exceeds finite N arithmetic')
        records.append(dict(kind='z',step_m=float(step),negative_potential_derivative_n=float(derivative),trials=trials))
    return dict(format='superfish_ng_off_axis_magnetic_virtual_work',schema_version=1,source_case=case.to_dict(),body_region_ids=list(body_region_ids),weights=w.tolist(),translation_steps_m=steps.tolist(),baseline=_stationary_potential(base),records=records,
        interpretation='separate actual FEM +/- axial body translation, radial coordinates and exterior fixed; integrated azimuthal currents integral Jphi dr dz [A] preserved per region; -d(U-psi dot (J load+Ht load))/dz is full-ring force [N]. No meridional rotation is treated as a 3D rigid-body rotation. Step differences are not continuum error bounds; no axis-connected or recoil/B-H extension.')

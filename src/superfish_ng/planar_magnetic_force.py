# SPDX-License-Identifier: Apache-2.0
"""Original planar FEM Maxwell stress and independent finite-displacement work."""
import hashlib,json
from fractions import Fraction
import numpy as np
from .constants import MU0
from .planar_bh import PlanarBHCase,PlanarBHSolution,solve_planar_bh
from .planar_recoil import PlanarRecoilCase,PlanarRecoilSolution,solve_planar_recoil
from .bh_curve import _real_array
from .planar_magnetostatic import PlanarMagnetostaticCase,PlanarMagnetostaticSolution,solve_planar_magnetostatic,planar_magnetostatic_quantities


def _vacuum_cells(case):
    p=case.partition
    if type(case) is PlanarMagnetostaticCase:return p.mu_r==1.
    materials={m.id:m for m in p.materials};region_vacuum=[]
    for region in p.regions:
        material=materials[region.material]
        if type(case) is PlanarBHCase:
            vacuum=all(Fraction(h)/Fraction(b)==Fraction(1./MU0) for b,h in zip(material.b_t[1:],material.h_a_per_m[1:]))
        else:vacuum=material.mu_r_principal==(1.,1.) and material.remanent_b_local_t==(0.,0.)
        region_vacuum.append(vacuum)
    return np.asarray(region_vacuum)[p.cell_region_indices]


def _request(case,body_region_ids,weights,origin_xy_m):
    if type(case) not in (PlanarMagnetostaticCase,PlanarBHCase,PlanarRecoilCase):raise ValueError('force requires an explicit planar scalar, B-H or recoil Case')
    p=case.partition;mesh=p.mesh
    if not isinstance(body_region_ids,(list,tuple)) or not body_region_ids or any(type(v) is not str for v in body_region_ids) or len(set(body_region_ids))!=len(body_region_ids):raise ValueError('force body_region_ids must be a nonempty distinct string sequence')
    if not set(body_region_ids)<=set(r.id for r in p.regions):raise ValueError('force body_region_ids contains an unknown region')
    w=_real_array(weights,'force P1 weights');origin=_real_array(origin_xy_m,'force torque origin [m]')
    if w.shape!=(len(mesh.points_xy_m),) or np.any(w<0.) or np.any(w>1.):raise ValueError('force requires one finite weight in [0,1] per original mesh vertex')
    if origin.shape!=(2,):raise ValueError('force torque origin requires exactly [x_m,y_m]')
    if np.any(w[np.unique(mesh.boundary_edges)]!=0.):raise ValueError('force weights must vanish on the whole outer boundary')
    values=w[mesh.triangles];current=np.array([case.current_density_z_a_per_m2[r.id] for r in p.regions])[p.cell_region_indices];body=np.array([r.id in body_region_ids for r in p.regions])[p.cell_region_indices];varying=np.any(values!=values[:,0,None],axis=1)
    if np.any(values[body]!=1.):raise ValueError('force weights must equal one throughout every body cell')
    vacuum=_vacuum_cells(case)
    if np.any((~vacuum[varying])|(current[varying]!=0.)):raise ValueError('force weight gradients require strictly vacuum mu_r=1 and Jz=0 cells')
    fixed_other=(~body)&((~vacuum)|(current!=0.))
    if np.any(values[fixed_other]!=0.):raise ValueError('other current or nonvacuum regions must have weight zero')
    if not np.any(varying):raise ValueError('force requires a nonempty surrounding vacuum weight transition')
    return w,origin,body,varying


def _verified(solution):
    solvers={PlanarMagnetostaticSolution:solve_planar_magnetostatic,PlanarBHSolution:solve_planar_bh,PlanarRecoilSolution:solve_planar_recoil}
    if type(solution) not in solvers:raise ValueError('force requires an explicit planar scalar, B-H or recoil FEM solution')
    fresh=solvers[type(solution)](solution.case)
    if solution.reference_az_wb_per_m!=fresh.reference_az_wb_per_m or any(not np.array_equal(getattr(solution,k),getattr(fresh,k)) for k in ('az_wb_per_m','az_relative_to_reference_wb_per_m')):raise ValueError('force source coefficients disagree with actual FEM replay')
    return fresh


def _stress_integral(solution,w,origin,order):
    mesh=solution.case.partition.mesh;triangles=mesh.points_xy_m[mesh.triangles];a=triangles[:,1]-triangles[:,0];b=triangles[:,2]-triangles[:,0];det=a[:,0]*b[:,1]-a[:,1]*b[:,0]
    values=w[mesh.triangles];gradient=((values[:,1]-values[:,0])[:,None]*np.column_stack((b[:,1],-b[:,0]))+(values[:,2]-values[:,0])[:,None]*np.column_stack((-a[:,1],a[:,0])))/det[:,None]
    lever_vertices=triangles-origin;rotation_velocity=values[:,:,None]*np.stack((-lever_vertices[:,:,1],lever_vertices[:,:,0]),axis=2)
    shape_one=np.column_stack((b[:,1],-b[:,0]))/det[:,None];shape_two=np.column_stack((-a[:,1],a[:,0]))/det[:,None]
    rotation_gradient=np.einsum('ta,tb->tab',rotation_velocity[:,1]-rotation_velocity[:,0],shape_one)+np.einsum('ta,tb->tab',rotation_velocity[:,2]-rotation_velocity[:,0],shape_two)
    nodes,weights=np.polynomial.legendre.leggauss(order);nodes=(nodes+1)/2;weights=weights/2;cells=np.arange(len(triangles));force=np.zeros((len(cells),2));torque=np.zeros(len(cells));nodal_torque=np.zeros(len(cells));absolute=np.zeros(4)
    for i,x in enumerate(nodes):
        for j,t in enumerate(nodes):
            y=t*(1-x);bary=np.array([1-x-y,x,y]);points=np.einsum('i,tij->tj',bary,triangles);measure=weights[i]*weights[j]*(1-x)*det;fields=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)));magnetic=np.column_stack((fields['Bx_T'],fields['By_T']))
            with np.errstate(over='ignore',invalid='ignore'):
                density=-(magnetic*np.einsum('ti,ti->t',magnetic,gradient)[:,None]-.5*np.einsum('ti,ti->t',magnetic,magnetic)[:,None]*gradient)/MU0
                nodal_density=-(np.einsum('ti,tij,tj->t',magnetic,rotation_gradient,magnetic)-.5*np.einsum('ti,ti->t',magnetic,magnetic)*np.trace(rotation_gradient,axis1=1,axis2=2))/MU0
                nodal_twist=measure*nodal_density
                lever=points-origin;moment=lever[:,0]*density[:,1]-lever[:,1]*density[:,0];contribution=measure[:,None]*density;twist=measure*moment
            if not np.isfinite(contribution).all() or not np.isfinite(twist).all() or not np.isfinite(nodal_twist).all():raise ValueError('Maxwell force/torque exceeds finite SI arithmetic')
            force+=contribution;torque+=twist;nodal_torque+=nodal_twist;absolute[:2]+=abs(contribution).sum(axis=0);absolute[2]+=abs(twist).sum();absolute[3]+=abs(nodal_twist).sum()
    return force,torque,absolute,nodal_torque


def planar_magnetic_force(solution,body_region_ids,weights,origin_xy_m):
    fresh=_verified(solution);w,origin,body,varying=_request(fresh.case,body_region_ids,weights,origin_xy_m);force,torque,absolute,nodal=_stress_integral(fresh,w,origin,3);other,other_t,_,other_nodal=_stress_integral(fresh,w,origin,4);total=np.r_[force.sum(axis=0),torque.sum(),nodal.sum()];difference=np.r_[(other-force).sum(axis=0),(other_t-torque).sum(),(other_nodal-nodal).sum()];scale=np.maximum(absolute,abs(total));relative=np.divide(abs(difference),scale,out=np.zeros(4),where=scale>0.)
    result=dict(format='superfish_ng_planar_magnetic_force',schema_version=1,source_case_sha256=hashlib.sha256(json.dumps(fresh.case.to_dict(),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),
        body_region_ids=list(body_region_ids),weights=w.tolist(),origin_xy_m=origin.tolist(),body_cell_indices=np.flatnonzero(body).tolist(),vacuum_transition_cells=np.flatnonzero(varying).tolist(),
        force_xy_n_per_m=total[:2].tolist(),torque_z_nm_per_m=float(total[2]),nodal_rotation_stress_torque_z_nm_per_m=float(total[3]),nodal_minus_weighted_torque_nm_per_m=float(total[3]-total[2]),cell_nodal_rotation_stress_torque_z_nm_per_m=nodal.tolist(),cell_force_xy_n_per_m=force.tolist(),cell_torque_z_nm_per_m=torque.tolist(),absolute_integral_scales=absolute.tolist(),diagnostic_quantity_order=['Fx_N_per_m','Fy_N_per_m','weighted_torque_Nm_per_m','nodal_rotation_torque_Nm_per_m'],quadrature_orders=[3,4],quadrature_relative_differences=relative.tolist(),
        conventions='static real original FEM B; vacuum T=(B tensor B-|B|^2 I/2)/mu0; F/L=-integral T grad(w) dA [N/m]; torque/L=-integral ((x-origin) cross T grad(w))z dA [N m/m]; nodal rotation torque=-integral T:grad(P1(w*(-(y-origin_y),x-origin_x))) dA [N m/m], matched to actual nodal geometry variation; no RF phasor or implicit length',
        interpretation='declared body and continuous P1 weight; all transitions in vacuum without current; original field, weight/mesh and quadrature differences remain separate; no continuum error bound or material/axisymmetric extension')
    if type(fresh) is not PlanarMagnetostaticSolution:
        result.update(schema_version=2,source_physics=fresh.case.to_dict()['physics'],vacuum_material_policy='B-H: every declared H/B ratio exactly equals the input-float vacuum 1/MU0; recoil: declared principal mu_r=(1,1) and remanent B=(0,0); every varying-weight cell also has Jz=0',
            interpretation='original verified B-H/recoil FEM B; all weight transitions are declared vacuum without current; nonlinear, anisotropic or remanent body remains in the actual source solve; weighted and nodal rotation stress torques retained separately; weight, mesh and quadrature diagnostics are not continuum error bounds; material virtual work and axisymmetry are unsupported')
    return result



def _displaced_case(case,w,body,origin,translation,angle):
    mesh=case.partition.mesh;points=mesh.points_xy_m;turn=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]]);moved=points+w[:,None]*(translation+(points-origin)@(turn-np.eye(2)).T)
    if not np.isfinite(moved).all():raise ValueError('virtual displacement exceeds finite SI geometry')
    data=case.to_dict();data['partition']['geometry']['points_xy_m']=moved.tolist();trial=PlanarMagnetostaticCase.from_dict(data)
    # Preserve declared integrated currents under floating-point rigid motion.
    # Transition cells have zero current; other source regions are fixed.
    for index,region in enumerate(case.partition.regions):data['current_density_z_a_per_m2'][region.id]=case.current_density_z_a_per_m2[region.id]*(case.partition.region_area_m2[index]/trial.partition.region_area_m2[index])
    return PlanarMagnetostaticCase.from_dict(data)


def _stationary_potential(solution):
    energy=planar_magnetostatic_quantities(solution)['energy_j_per_m'];source_work=float(solution.az_wb_per_m@(solution.volume_load_a+solution.boundary_load_a));value=energy-source_work
    if not np.isfinite(value):raise ValueError('virtual-work stationary potential exceeds finite J/m arithmetic')
    return value,energy,source_work


def planar_magnetic_virtual_work(case,body_region_ids,weights,origin_xy_m,translation_steps_m,rotation_steps_rad):
    if type(case) is not PlanarMagnetostaticCase:raise ValueError('virtual work currently requires a linear scalar PlanarMagnetostaticCase; material rotation and nonlinear failure handling are unsupported')
    w,origin,body,varying=_request(case,body_region_ids,weights,origin_xy_m);translation_steps=_real_array(translation_steps_m,'virtual translation steps [m]');rotation_steps=_real_array(rotation_steps_rad,'virtual rotation steps [rad]')
    for steps,name in ((translation_steps,'translation'),(rotation_steps,'rotation')):
        if steps.ndim!=1 or not 2<=len(steps)<=8 or np.any(steps<=0.) or np.any(steps[1:]>=steps[:-1]):raise ValueError('virtual '+name+' requires 2..8 strictly decreasing positive finite steps')
    base=solve_planar_magnetostatic(case);baseline=_stationary_potential(base);records=[]
    for kind,steps in (('x',translation_steps),('y',translation_steps),('rotation',rotation_steps)):
        for step in steps:
            trials=[]
            for sign in (-1.,1.):
                displacement=np.zeros(2);angle=sign*step if kind=='rotation' else 0.
                if kind!='rotation':displacement[0 if kind=='x' else 1]=sign*step
                trial=_displaced_case(case,w,body,origin,displacement,angle);solution=solve_planar_magnetostatic(trial);potential,energy,source_work=_stationary_potential(solution)
                if np.array_equal(trial.partition.mesh.points_xy_m,case.partition.mesh.points_xy_m):raise ValueError('virtual displacement is not resolved in SI coordinates')
                trials.append(dict(sign=sign,case=trial.to_dict(),stationary_potential_j_per_m=potential,energy_j_per_m=energy,source_and_boundary_work_j_per_m=source_work,relative_residual=solution.relative_residual,
                    relative_az_sha256=hashlib.sha256(solution.az_relative_to_reference_wb_per_m.tobytes()).hexdigest()))
            derivative=-(trials[1]['stationary_potential_j_per_m']-trials[0]['stationary_potential_j_per_m'])/(2*step)
            if not np.isfinite(derivative):raise ValueError('virtual-work derivative exceeds finite SI arithmetic')
            records.append(dict(kind=kind,step=float(step),negative_potential_derivative=float(derivative),unit='N m/m' if kind=='rotation' else 'N/m',trials=trials))
    return dict(format='superfish_ng_planar_magnetic_virtual_work',schema_version=1,body_region_ids=list(body_region_ids),weights=w.tolist(),origin_xy_m=origin.tolist(),baseline_stationary_potential_j_per_m=baseline[0],records=records,
        interpretation='separate actual FEM solves of rigid body +/- translation/rotation with fixed exterior boundary, other sources/materials, and integrated currents; -d(U-Az dot (J load+Ht load))/dq; original geometry is deformed only through a surrounding vacuum mesh; rotation is interpolated from original vertex displacements through each original triangle, so compare to nodal_rotation_stress_torque rather than assuming the quadratic scalar-weight rotation is the same discrete variation; step differences are not continuum error bounds')

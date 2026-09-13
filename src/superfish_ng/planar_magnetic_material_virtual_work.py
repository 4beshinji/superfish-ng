# SPDX-License-Identifier: Apache-2.0
"""Actual material FEM displacements, co-rotating remanence, and retained failures."""
import copy,hashlib
import numpy as np
from .bh_curve import _real_array
from .planar_bh import PlanarBHCase,solve_planar_bh,planar_bh_quantities
from .planar_recoil import PlanarRecoilCase,solve_planar_recoil,planar_recoil_quantities
from .nonlinear_magnetic import MagneticNonlinearFailure
from .planar_magnetic_force import _request


class PlanarMagneticVirtualWorkFailure(ValueError):
    """A nonlinear baseline or displacement failed; report retains completed work."""
    def __init__(self,report):
        self.report=copy.deepcopy(report)
        failure=report['failure'];super().__init__('material magnetic virtual work failed at '+failure['kind']+': '+failure['nonlinear_failure']['reason']+'; inspect the retained Case, history and last valid coefficients')


def _displaced_material_case(case,body_region_ids,w,origin,translation,angle):
    points=case.partition.mesh.points_xy_m;turn=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]]);moved=points+w[:,None]*(translation+(points-origin)@(turn-np.eye(2)).T)
    if not np.isfinite(moved).all():raise ValueError('material virtual displacement exceeds finite SI geometry')
    if np.array_equal(moved,points):raise ValueError('material virtual displacement is not resolved in SI coordinates')
    data=case.to_dict();data['partition']['geometry']['points_xy_m']=moved.tolist()
    if type(case) is PlanarRecoilCase and angle!=0.:
        for region in data['partition']['regions']:
            if region['id'] in body_region_ids:
                old=region['orientation_rad'];region['orientation_rad']=old+angle
                if region['orientation_rad']==old:raise ValueError('virtual material rotation is not resolved in the declared orientation [rad]')
    trial=type(case).from_dict(data)
    for index,region in enumerate(case.partition.regions):data['current_density_z_a_per_m2'][region.id]=case.current_density_z_a_per_m2[region.id]*(case.partition.region_area_m2[index]/trial.partition.region_area_m2[index])
    return type(case).from_dict(data)


def _material_potential(solution):
    if type(solution.case) is PlanarBHCase:
        q=planar_bh_quantities(solution);energy=q['energy_j_per_m'];reference='B=0, true integral of reversible H(B)';extra={}
    else:
        q=planar_recoil_quantities(solution);energy=q['constitutive_potential_b0_j_per_m'];reference='B=0, integral of B.nu.B/2-B.nu.Brem';extra=dict(constitutive_potential_h0_j_per_m=q['constitutive_potential_h0_j_per_m'],remanent_reference_constant_j_per_m=q['remanent_reference_constant_j_per_m'])
    source_work=float(solution.az_wb_per_m@(solution.current_load_a+solution.boundary_load_a));value=energy-source_work
    if not np.isfinite([value,energy,source_work]).all():raise ValueError('material stationary potential exceeds finite J/m arithmetic')
    return dict(stationary_potential_j_per_m=value,constitutive_potential_j_per_m=energy,constitutive_reference=reference,source_and_boundary_work_j_per_m=source_work,**extra)


def material_planar_magnetic_virtual_work(case,body_region_ids,weights,origin_xy_m,translation_steps_m,rotation_steps_rad):
    if type(case) not in (PlanarBHCase,PlanarRecoilCase):raise ValueError('material virtual work requires an explicit planar B-H P1 or recoil P1/P2 Case')
    w,origin,body,varying=_request(case,body_region_ids,weights,origin_xy_m);translation_steps=_real_array(translation_steps_m,'material virtual translation steps [m]');rotation_steps=_real_array(rotation_steps_rad,'material virtual rotation steps [rad]')
    for steps,name in ((translation_steps,'translation'),(rotation_steps,'rotation')):
        if steps.ndim!=1 or not 2<=len(steps)<=8 or np.any(steps<=0.) or np.any(steps[1:]>=steps[:-1]):raise ValueError('material virtual '+name+' requires 2..8 strictly decreasing positive finite steps')
    solver=solve_planar_bh if type(case) is PlanarBHCase else solve_planar_recoil
    result=dict(format='superfish_ng_planar_magnetic_virtual_work',schema_version=2,status='pending',source_physics=case.to_dict()['physics'],source_case=case.to_dict(),body_region_ids=list(body_region_ids),weights=w.tolist(),origin_xy_m=origin.tolist(),translation_steps_m=translation_steps.tolist(),rotation_steps_rad=rotation_steps.tolist(),baseline=None,records=[],failure=None,
        interpretation='separate actual material FEM +/- nodal geometry displacements; selected body moves rigidly, exterior and other sources/materials fixed; integrated currents preserved; recoil principal tensor and remanent B co-rotate with each body region. -d(Uconstitutive-Az dot (J load+Ht load))/dq, with no second remanence-work subtraction. Rotation matches nodal_rotation_stress_torque; scalar-weight torque differs in P1. Failure retains completed trials and no derivative for a failed pair. Step, mesh and quadrature differences are not continuum error bounds.')
    def solve_trial(trial,kind,step,sign):
        try:return solver(trial)
        except MagneticNonlinearFailure as exc:
            result.update(status='failed',failure=dict(kind=kind,step=step,sign=sign,case=trial.to_dict(),nonlinear_failure=exc.report))
            raise PlanarMagneticVirtualWorkFailure(result) from exc
    base=solve_trial(case,'baseline',None,None);result['baseline']=dict(case=base.case.to_dict(),**_material_potential(base),relative_residual=base.relative_residual,relative_az_sha256=hashlib.sha256(base.az_relative_to_reference_wb_per_m.tobytes()).hexdigest(),iteration_report=base.iteration_report if type(case) is PlanarBHCase else None)
    for kind,steps in (('x',translation_steps),('y',translation_steps),('rotation',rotation_steps)):
        for step in steps:
            row=dict(kind=kind,step=float(step),negative_potential_derivative=None,unit='N m/m' if kind=='rotation' else 'N/m',trials=[]);result['records'].append(row)
            for sign in (-1.,1.):
                displacement=np.zeros(2);angle=sign*step if kind=='rotation' else 0.
                if kind!='rotation':displacement[0 if kind=='x' else 1]=sign*step
                trial=_displaced_material_case(case,body_region_ids,w,origin,displacement,angle);solution=solve_trial(trial,kind,float(step),sign)
                row['trials'].append(dict(sign=sign,case=trial.to_dict(),**_material_potential(solution),relative_residual=solution.relative_residual,relative_az_sha256=hashlib.sha256(solution.az_relative_to_reference_wb_per_m.tobytes()).hexdigest(),iteration_report=solution.iteration_report if type(case) is PlanarBHCase else None))
            derivative=-(row['trials'][1]['stationary_potential_j_per_m']-row['trials'][0]['stationary_potential_j_per_m'])/(2*step)
            if not np.isfinite(derivative):raise ValueError('material virtual-work derivative exceeds finite SI arithmetic')
            row['negative_potential_derivative']=float(derivative)
    result['status']='complete';return result

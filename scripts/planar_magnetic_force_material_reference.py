# SPDX-License-Identifier: Apache-2.0
"""Synthetic current and remanent bodies, with independent symmetry/moment references."""
import numpy as np
from scripts.planar_magnetic_force_reference import current_body
from superfish_ng.constants import MU0
from superfish_ng.bh_curve import MonotoneBHCurve
from superfish_ng.magnetic_materials import MagneticRegion
from superfish_ng.planar_bh_materials import PlanarBHPartition
from superfish_ng.planar_bh import PlanarBHCase
from superfish_ng.recoil_materials import LinearRecoilMaterial,OrientedMagneticRegion,PlanarRecoilPartition
from superfish_ng.planar_recoil import PlanarRecoilCase


def material_body(kind='bh',permanent=False,nonlinear=False,principal=(1.,1.),remanence_t=.1,**kwargs):
    if permanent:kwargs.update(current_a=0.,pair=False)
    case,body,w,origin,ref=current_body(**kwargs);p=case.partition
    if kind=='bh':
        if permanent:raise ValueError('B-H model has no permanent remanence')
        b=(0.,.25,.5,1.,8.);air=MonotoneBHCurve('air',b,tuple(x/MU0 for x in b),'Synthetic exact vacuum H=B/MU0 over all declared points')
        solid=MonotoneBHCurve('solid',b,tuple(x/MU0 for x in b) if not nonlinear else tuple(np.array([0.,.025,.075,.5,7.5])/MU0),'Synthetic reversible body table; no measured structure')
        regions=[MagneticRegion(r.id,'air' if r.id=='air' else 'solid',r.cell_indices) for r in p.regions]
        converted=PlanarBHCase(PlanarBHPartition(p.mesh,[air,solid],regions),dict(case.current_density_z_a_per_m2),case.boundaries,1,name='synthetic-BH-current-body')
    elif kind=='recoil':
        angle=kwargs.get('rotation_rad',0.);air=LinearRecoilMaterial('air',(1.,1.),(0.,0.));solid=LinearRecoilMaterial('solid',principal,(0.,remanence_t) if permanent else (0.,0.))
        regions=[OrientedMagneticRegion(r.id,'air' if r.id=='air' else 'solid',r.cell_indices,angle) for r in p.regions]
        converted=PlanarRecoilCase(PlanarRecoilPartition(p.mesh,[air,solid],regions),dict(case.current_density_z_a_per_m2),case.boundaries,case.element_order,name='synthetic-recoil-magnetic-body')
    else:raise ValueError('expected bh or recoil material reference')
    if permanent:
        length=ref['length_m'];torque=-(length/4)**2*remanence_t*kwargs.get('external_b_t',.25)/MU0
        ref.update(force_xy_n_per_m=np.zeros(2),torque_z_nm_per_m=torque,force_scale=abs(torque)/length,torque_scale=abs(torque),interpretation='synthetic symmetric square with mu_rec=1; m/L=area*Brem/MU0; external torque=(m cross B)z/L; self force/torque vanish at this symmetric orientation')
    return converted,body,w,origin,ref

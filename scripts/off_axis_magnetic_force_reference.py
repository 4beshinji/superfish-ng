# SPDX-License-Identifier: Apache-2.0
"""Synthetic finite annular current in Br=C/r: full-ring Lorentz force, actual FEM only."""
import numpy as np
from scripts.planar_magnetic_force_reference import current_body
from superfish_ng.constants import MU0,TAU
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.magnetic_materials import LinearMagneticMaterial,MagneticRegion
from superfish_ng.off_axis_magnetic_materials import OffAxisMagneticPartition
from superfish_ng.off_axis_magnetostatic_boundary import OffAxisMagnetostaticBoundary
from superfish_ng.off_axis_magnetostatic import OffAxisMagnetostaticCase


def axial_current_body(n=8,order=2,scale=1.,current_a=10.,external_radial_constant_t_m=.0625,shift_z_m=0.,reference_psi_wb=.125,body_mu_r=1.,quadrature_order=16,weight_outer=.95):
    planar,body,w,c,ref=current_body(n=n,order=order,scale=scale,current_a=current_a,weight_outer=weight_outer);p=planar.partition;shift=np.array([0.,shift_z_m]);mesh=MeridionalMesh(p.mesh.polygon_xy_m+shift,[],p.mesh.points_xy_m+shift,p.mesh.triangles)
    materials=[LinearMagneticMaterial('vacuum',1.),LinearMagneticMaterial('body',body_mu_r)];regions=[MagneticRegion(r.id,'vacuum' if r.id=='air' else 'body',r.cell_indices) for r in p.regions];partition=OffAxisMagneticPartition(mesh,materials,regions);lo=mesh.points_rz_m.min(axis=0);hi=mesh.points_rz_m.max(axis=0);groups={name:[] for name in ('bottom','top','inner','outer')}
    for i,edge in enumerate(mesh.boundary_edges):
        r,z=mesh.points_rz_m[edge].mean(axis=0);groups['bottom' if z==lo[1] else 'top' if z==hi[1] else 'inner' if r==lo[0] else 'outer'].append(i)
    constant=external_radial_constant_t_m;boundaries=[OffAxisMagnetostaticBoundary('bottom','fixed_psi',groups['bottom'],reference_psi_wb),OffAxisMagnetostaticBoundary('top','fixed_psi',groups['top'],reference_psi_wb-constant*(hi[1]-lo[1]))]+[OffAxisMagnetostaticBoundary(name,'tangential_h',groups[name],0.) for name in ('inner','outer')]
    case=OffAxisMagnetostaticCase(partition,dict(planar.current_density_z_a_per_m2),boundaries,order,quadrature_order,name='synthetic-symmetric-annular-current-in-radial-field');expected=-TAU*constant*current_a
    return case,body,w,dict(force_z_n=expected,force_scale_n=abs(expected) if expected else TAU*constant**2/MU0,length_m=ref['length_m'],external_radial_constant_t_m=constant,current_a=current_a,analytic_applicable=body_mu_r==1.,interpretation='synthetic positive-radius full annular body, Br=C/r external field; z-reflection cancels self axial force; Fz=-2*pi*C*integral Jphi dr dz in vacuum-permeability body. Non-unit body mu uses separate actual-work comparison, not this analytic force.')

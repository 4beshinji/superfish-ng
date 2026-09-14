# SPDX-License-Identifier: Apache-2.0
"""Declared origin/axis-preserving affine pullback of independent FEM meshes."""
from types import SimpleNamespace
import math
import numpy as np
from .config import keys,positive
from .curved_solution import CurvedSolution
from .high_order import quadratic_space
from .same_domain_tracking import track_same_domain_modes


def validate_affine_map(value):
    names=('radial_scale','axial_scale','axial_shear');keys(value,names,names,'affine_map')
    a=positive(value['radial_scale'],'radial_scale');c=positive(value['axial_scale'],'axial_scale')
    b=value['axial_shear']
    if isinstance(b,bool) or not isinstance(b,(int,float)) or not math.isfinite(b):raise ValueError('axial_shear must be finite')
    b=float(b)
    if not math.isfinite(a*a*c) or a*a*c<=0 or not math.isfinite(b/a/c):
        raise ValueError('affine_map volume ratio or inverse is outside the finite numerical range')
    return a,b,c


def track_affine_remesh_modes(previous,current,previous_ids,*,mapping,sample_order,affine_map,**controls):
    """Map old (r,z) to new (a*r,b*r+c*z); never infer the correspondence.

    The axisymmetric volume ratio a*a*c is constant. Pulling back mesh
    coordinates and evaluating r_old*u_new gives Hphi_new/a, a constant
    amplitude factor removed by subspace normalization. No FEM solve occurs.
    """
    if mapping!='affine_remesh':raise ValueError('explicit mapping must be affine_remesh')
    a,b,c=validate_affine_map(affine_map)
    from .te import TESolution,is_te
    te=[is_te(s.case) if hasattr(s,'case') else False for s in (previous,current)]
    if any(te) and not all(te):raise ValueError('mixed TE/TM affine correspondence is unsupported')
    if any(te) and any(s.case.geometry_order!=2 for s in (previous,current)):
        raise ValueError('TE affine correspondence requires native curved P2 fields')
    if any(isinstance(s,(CurvedSolution,TESolution)) for s in (previous,current)):
        from .curved_same_domain_tracking import _track_curved_modes
        report=_track_curved_modes(previous,current,previous_ids,sample_order=sample_order,affine=(a,b,c),**controls)
        physical=report['physical_mapping'];volumes=physical.pop('axisymmetric_volumes_m3')
        report['comparison_description']='declared r_new=a*r_old, z_new=b*r_old+c*z_old; whole quadratic boundary coincidence after pullback; '+('Ephi' if all(te) else 'Hphi')+'_new/a; symmetric independent curved-mesh quadrature in old physical volume'
        physical.update(name=mapping,affine_map=dict(radial_scale=a,axial_scale=c,axial_shear=b),physical_volume_ratio=a*a*c,
            reference_axisymmetric_volumes_m3=volumes,physical_axisymmetric_volumes_m3=[volumes[0],volumes[1]*a*a*c],
            current_field_multiplier='1/radial_scale, constant removed by subspace normalization',
            scope='declared origin/axis-preserving affine map; corresponding native primitive indices and parameters; coincident pulled-back quadratic boundary; independent curved P2 connectivity; not inferred or non-affine correspondence, reprojected boundary equality, or physical convergence acceptance')
        return report
    points=np.empty_like(current.mesh.points)
    with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
        points[:,0]=current.mesh.points[:,0]/a
        points[:,1]=(current.mesh.points[:,1]-b*points[:,0])/c
    if not np.isfinite(points).all():raise ValueError('affine inverse produces nonfinite mesh coordinates')
    mesh=SimpleNamespace(**dict(vars(current.mesh),points=points))
    space=quadratic_space(mesh) if current.element_order==2 else None
    if space is not None and not np.array_equal(space.cell_dofs,current.space.cell_dofs):
        raise ValueError('affine pullback must preserve the native P2 coefficient connectivity')
    pulled=SimpleNamespace(mesh=mesh,space=space,element_order=current.element_order,u=current.u,frequencies_hz=current.frequencies_hz)
    try:report=track_same_domain_modes(previous,pulled,previous_ids,mapping='same_domain',sample_order=sample_order,**controls)
    except ValueError as exc:
        if 'boundary differs' in str(exc):raise ValueError('affine_map does not match the full physical boundary; check scale and shear') from exc
        raise
    report['comparison_description']='declared r_new=a*r_old, z_new=b*r_old+c*z_old; Hphi_new/a pulled to old physical domain; symmetric independent-mesh volume quadrature; constant volume ratio removed by normalization'
    physical=report['physical_mapping'];volumes=physical.pop('axisymmetric_volumes_m3')
    physical.update(name=mapping,affine_map=dict(radial_scale=a,axial_scale=c,axial_shear=b),physical_volume_ratio=a*a*c,
        reference_axisymmetric_volumes_m3=volumes,physical_axisymmetric_volumes_m3=[volumes[0],volumes[1]*a*a*c],
        current_field_multiplier='1/radial_scale, constant removed by subspace normalization',
        scope='declared origin/axis-preserving affine map of polygonal domains; positive radial/axial scale and finite axial shear; independent P1/P2 meshes; not inferred or non-affine correspondence, continuous-branch proof, or physical convergence acceptance')
    return report

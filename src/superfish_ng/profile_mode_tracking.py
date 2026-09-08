# SPDX-License-Identifier: Apache-2.0
"""Volume-normalized magnetic-field comparison on positive radius profiles."""
import numpy as np
from .mode_tracking import track_sampled_mode_subspaces
from .sampling import FieldSampler


def track_profile_modes(previous,current,previous_ids,*,mapping,sample_order,**controls):
    """Compare Hphi * R(z)/Rmax on r=rho R(L zeta), z=L zeta.

    The physical measure is 2*pi*L*R(z)^2*rho d_rho d_zeta.
    Multiplication by R/Rmax retains its variable factor; the constant
    2*pi*L*Rmax^2 cancels independently under mode normalization.
    """
    if mapping!='normalized_profile':raise ValueError('explicit mapping must be normalized_profile')
    if type(sample_order) is not int or not 2<=sample_order<=256:
        raise ValueError('sample_order must be an integer from 2 to 256 per reference interval')
    profiles=[];knots=[]
    for solution in (previous,current):
        case=solution.case
        if case.geometry_type!='profile' or not case.profile or case.z_min!='pec' or case.z_max!='pec':
            raise ValueError('normalized_profile requires a positive continuous profile with closed PEC ends; stepped, folded and curved contours need another mapping')
        profile=np.asarray(case.profile,dtype=float);normalized=profile[:,0]/case.length
        if (not np.isfinite(normalized).all() or np.any(np.diff(normalized)<=0)
                or np.any(profile[:,1]<=0)):
            raise ValueError('profile reference knots must remain distinct and radii positive')
        profiles.append(profile);knots.extend(normalized.tolist())
    breaks=np.unique(knots)
    count=(len(breaks)-1)*sample_order**2
    if count>262144:raise ValueError('profile tracking exceeds 262144 common samples; reduce sample_order or profile breakpoints')
    nodes,weights=np.polynomial.legendre.leggauss(sample_order);nodes=(nodes+1)/2;weights=weights/2
    axial=np.concatenate([a+(b-a)*nodes for a,b in zip(breaks,breaks[1:])])
    axial_weights=np.concatenate([(b-a)*weights for a,b in zip(breaks,breaks[1:])])
    rho,zeta=np.meshgrid(nodes,axial,indexing='ij')
    reference=np.column_stack((rho.ravel(),zeta.ravel()))
    measure=(weights[:,None]*axial_weights[None,:]*rho).ravel()
    samples=[]
    for solution,profile in zip((previous,current),profiles):
        z=reference[:,1]*solution.case.length;radii=np.interp(z,profile[:,0],profile[:,1])
        factor=radii/np.max(profile[:,1])
        if np.any(factor<=0):raise ValueError('profile volume factor underflows; rescale the geometry or restrict its radius contrast')
        points=np.column_stack((reference[:,0]*radii,z));sampler=FieldSampler.from_solution(solution)
        values=np.column_stack([sampler.evaluate(points,i,outside='raise')['Hphi_A_per_m'] for i in range(len(solution.frequencies_hz))])
        samples.append(values*factor[:,None])
    result=track_sampled_mode_subspaces(*samples,measure,previous.frequencies_hz,current.frequencies_hz,previous_ids,
        comparison_description='Hphi_A_per_m times R(z)/Rmax pulled back by r=rho R(L zeta), z=L zeta; reference measure rho d_rho d_zeta; variable physical volume factor retained',**controls)
    result['physical_mapping']=dict(name=mapping,sample_order=sample_order,sample_count=count,
        field='Hphi_A_per_m',field_multiplier='R(z)/Rmax',reference_breakpoints_zeta=breaks.tolist(),
        reference_points_rho_zeta=reference.tolist(),reference_weights=measure.tolist(),
        previous_profile_zr_m=profiles[0].tolist(),current_profile_zr_m=profiles[1].tolist(),
        scope='positive continuous piecewise linear profiles and closed PEC ends; quadrature split at both profiles; no guarantee of continuous branch identity or FEM convergence')
    return result

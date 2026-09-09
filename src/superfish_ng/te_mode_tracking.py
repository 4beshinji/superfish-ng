# SPDX-License-Identifier: Apache-2.0
"""Electric-field correspondence for closed PEC m=0 TE cylinders."""
import numpy as np
from .te import is_te, TEFieldSampler


def track_te_cylindrical_modes(previous, current, previous_ids, *, mapping, sample_order, **controls):
    """Compare real Ephi on a shared normalized cylinder, with volume weights.

    Constant permittivity and the constant volume Jacobian cancel under
    column normalization. This is a pointwise pullback, not a path history.
    """
    from .mode_tracking import track_sampled_mode_subspaces
    if not all(is_te(s.case) for s in (previous,current)):
        raise ValueError('TE tracking requires two TE solutions; mixed TE/TM correspondence is unsupported')
    if any(s.reflection_source_case is not None for s in (previous,current)):
        raise ValueError('TE tracking of reflected partial spectra is pending; track the source half domains')
    if mapping != 'normalized_cylinder':
        raise ValueError('TE tracking currently requires normalized_cylinder mapping')
    if type(sample_order) is not int or not 2 <= sample_order <= 256:
        raise ValueError('sample_order must be an integer from 2 to 256 per reference coordinate')
    dimensions=[]
    for solution in (previous,current):
        case=solution.case
        if (case.geometry_order != 1 or case.geometry_type != 'profile' or not case.profile
                or case.z_min != 'pec' or case.z_max != 'pec'
                or any(radius != case.profile[0][1] for _,radius in case.profile)):
            raise ValueError('TE normalized_cylinder requires straight constant-radius profile geometry and closed PEC ends')
        dimensions.append((case.profile[0][1],case.length))
    nodes,weights=np.polynomial.legendre.leggauss(sample_order)
    nodes=(nodes+1)/2;weights=weights/2
    rho,zeta=np.meshgrid(nodes,nodes,indexing='ij')
    reference=np.column_stack((rho.ravel(),zeta.ravel()))
    measure=(weights[:,None]*weights[None,:]*rho).ravel()
    samples=[]
    for solution,(radius,length) in zip((previous,current),dimensions):
        sampler=TEFieldSampler(solution);points=reference*[radius,length]
        samples.append(np.column_stack([sampler.evaluate(points,i)['Ephi_V_per_m']
                                        for i in range(len(solution.frequencies_hz))]))
    result=track_sampled_mode_subspaces(*samples,measure,previous.frequencies_hz,current.frequencies_hz,previous_ids,
        comparison_description='TE Ephi_V_per_m pulled back by r=R*rho, z=L*zeta; reference measure rho d_rho d_zeta',**controls)
    result['physical_mapping']=dict(name=mapping,sample_order=sample_order,field='Ephi_V_per_m',physics='axisymmetric_m0_te',
        reference_points_rho_zeta=reference.tolist(),reference_weights=measure.tolist(),
        previous_radius_length_m=list(dimensions[0]),current_radius_length_m=list(dimensions[1]),
        scope='closed PEC TE cylinders only; real peak Ephi pointwise pullback; quadrature accuracy must be checked separately')
    return result

# SPDX-License-Identifier: Apache-2.0
"""Electric-field correspondence for matching m=0 TE cylinder sectors."""
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
    reflected = [s.reflection_source_case is not None for s in (previous,current)]
    if any(reflected) and not all(reflected):
        raise ValueError('TE sector tracking cannot mix ordinary and reflected spectra')
    sources = [s.reflection_source_case or s.case for s in (previous,current)]
    if not all(is_te(case) for case in sources):
        raise ValueError('TE tracking requires TE reflection source physics')
    ends = [(case.z_min,case.z_max) for case in sources]
    symmetry_count = sum(tag != 'pec' for tag in ends[0])
    if ends[0] != ends[1] or symmetry_count > 1 or (all(reflected) and symmetry_count != 1):
        raise ValueError('TE sector tracking requires matching ends and at most one symmetry plane; reflected fields require one source symmetry plane')
    if mapping != 'normalized_cylinder':
        raise ValueError('TE tracking currently requires normalized_cylinder mapping')
    if type(sample_order) is not int or not 2 <= sample_order <= 256:
        raise ValueError('sample_order must be an integer from 2 to 256 per reference coordinate')
    dimensions=[]
    for solution in (previous,current):
        case=solution.case
        if (case.geometry_order != 1 or case.geometry_type != 'profile' or not case.profile
                or any(radius != case.profile[0][1] for _,radius in case.profile)):
            raise ValueError('TE normalized_cylinder requires straight constant-radius profile geometry')
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
    if symmetry_count:
        result['physical_mapping'].update(
            boundary_conditions=list(ends[0]), reflected_partial_spectrum=all(reflected),
            mode_index_scope='source symmetry-sector order; not full-spectrum ranks',
            scope='matching TE cylinder symmetry sectors; real peak Ephi pointwise pullback; quadrature accuracy must be checked separately')
    return result

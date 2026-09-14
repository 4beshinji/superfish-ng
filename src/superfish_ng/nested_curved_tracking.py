# SPDX-License-Identifier: Apache-2.0
"""Mass-inner-product mode correspondence along native quadratic histories."""
from dataclasses import replace
import numpy as np
from scipy.sparse import eye, csr_matrix
from .curved_solution import CurvedSolution
from .curved_space import case_curved_space
from .curved_refinement import refine_curved_space
from .curved_marked_refinement import refine_marked_curved_space
from .curved_refinement_steps import CurvedRefinementStep
from .curved_saved import geometry_arrays
from .curved_reflection import reflect_curved_space, reflected_case
from .curved_fem import assemble_curved
from .mesh_input import mesh_from_dict, mesh_digest
from .mode_tracking import _real_array, _control, track_sampled_mode_subspaces
from .mass_tracking import mass_inner_product_features

MAX_FEATURE_ENTRIES = 8388608
MASS_QUADRATURE_ORDER = 8


def _history(case):
    return (CurvedRefinementStep('uniform'),)*case.curved_refinement_levels+case.curved_refinement_steps


def _same_space(expected, actual):
    a,b = geometry_arrays(expected),geometry_arrays(actual)
    return set(a)==set(b) and all(np.array_equal(a[k],b[k]) for k in a)


def _reconstruct(solution):
    if not isinstance(solution,CurvedSolution) or solution.case.geometry_order!=2 or solution.source_mesh_data is None:
        raise ValueError('nested_curved requires native curved solutions with source meshes')
    reflected = solution.reflection_source_case is not None
    source = solution.reflection_source_case if reflected else solution.case
    half = case_curved_space(source,mesh_from_dict(source,solution.source_mesh_data))
    reflection = reflect_curved_space(source,half) if reflected else None
    space = reflection.space if reflected else half
    if reflected and reflected_case(source,reflection)!=solution.case:
        raise ValueError('nested_curved reflection Case differs from its source')
    if not _same_space(space,solution.space):
        raise ValueError('nested_curved geometry differs from native reconstruction')
    values = _real_array(solution.u,'curved coefficients',2)
    if values.shape!=(len(space.geometry.points_rz_m),len(solution.frequencies_hz)):
        raise ValueError('nested_curved coefficient dimensions differ from the declared space')
    original = values[:len(half.geometry.points_rz_m)]
    if np.any(original[half.constrained_dofs]!=0):
        raise ValueError('nested_curved magnetic_symmetry coefficients violate the essential constraint')
    if reflected and not np.array_equal(reflection.apply(original),values):
        raise ValueError('nested_curved coefficients violate declared reflection parity')
    return source,half,space,reflection,values


def _nested_transfer(previous,current):
    old,coarse,old_space,old_reflection,a = _reconstruct(previous)
    new,fine,new_space,new_reflection,b = _reconstruct(current)
    if (old_reflection is None)!=(new_reflection is None):
        raise ValueError('nested_curved requires the same direct or reflected construction')
    stripped = lambda case: replace(case,curved_refinement_levels=0,curved_refinement_steps=()).to_dict()
    if stripped(old)!=stripped(new) or mesh_digest(previous.source_mesh_data)!=mesh_digest(current.source_mesh_data):
        raise ValueError('nested_curved requires identical source Case and chord mesh apart from refinement history')
    before,after = _history(old),_history(new)
    if len(after)<=len(before) or after[:len(before)]!=before:
        raise ValueError('nested_curved current history must strictly extend the previous history')
    entries=len(b)*(a.shape[1]+b.shape[1])
    if entries>MAX_FEATURE_ENTRIES:
        raise ValueError('nested_curved exceeds 8388608 coefficient feature entries')
    transfer=eye(len(coarse.geometry.points_rz_m),format='csr')
    space=coarse
    limit=new.contour_mesh.max_triangles if new.contour_mesh is not None else 250000
    for step in after[len(before):]:
        if step.kind=='uniform':
            if 4*len(space.geometry.cell_nodes)>limit:
                raise ValueError('nested_curved uniform history exceeds the Case triangle budget')
            refined=refine_curved_space(space)
        else:
            refined=refine_marked_curved_space(space,list(step.marked_cells),max_triangles=limit,
                                              minimum_corner_angle_deg=step.minimum_corner_angle_deg,split_pattern=step.split_pattern)
        transfer=refined.prolongation@transfer;space=refined.space
    if not _same_space(space,fine):
        raise ValueError('nested_curved final space differs from composed history')
    if old_reflection is not None:
        # Reflection retains all source nodes first. Extraction is a left inverse
        # only on the parity-constrained fields checked above, not arbitrary full fields.
        count=len(coarse.geometry.points_rz_m)
        extract=csr_matrix((np.ones(count),(np.arange(count),np.arange(count))),shape=(count,len(a)))
        transfer=new_reflection.coefficient_map@transfer@extract
    return transfer,new_space,a,b,dict(previous_steps=len(before),current_steps=len(after),
        appended_steps=[step.to_dict() for step in after[len(before):]],
        construction='reflected parity subspace' if old_reflection is not None else 'direct native space')


def track_nested_curved_modes(previous,current,previous_ids,*,mapping,**controls):
    if mapping!='nested_curved':
        raise ValueError('explicit mapping must be nested_curved')
    prepared=_nested_transfer(previous,current)
    return _track_prepared_nested_modes(previous,current,previous_ids,prepared,**controls)


def _track_prepared_nested_modes(previous,current,previous_ids,prepared,**controls):
    """Internal reuse of a transfer already verified by _nested_transfer.

    Never deserialize or accept this execution-local tuple from a caller's
    persistent document. Public tracking always reconstructs and verifies it.
    """
    transfer,space,a,b,ancestry=prepared
    def normalized(values):
        scale=np.max(abs(values),axis=0)
        return values/np.where(scale>0,scale,1.)
    coefficients=np.column_stack((transfer@normalized(a),normalized(b)))
    _,mass=assemble_curved(space,quadrature_order=MASS_QUADRATURE_ORDER)
    features,scale=mass_inner_product_features(coefficients,mass,label='nested_curved')
    gram=coefficients.T@(mass@coefficients)/scale
    denominator=max(float(np.linalg.norm(gram)),np.finfo(float).tiny)
    difference=float(np.linalg.norm(features.T@features-gram)/denominator)
    if not np.isfinite(difference) or difference>1e-10:
        raise ValueError('nested_curved mass embedding failed its inner-product check')
    numeric_margin=32*np.finfo(float).eps*max(coefficients.shape)
    declared_margin=_control(controls['minimum_assignment_margin'],'minimum_assignment_margin',zero=True)
    controls=dict(controls,minimum_assignment_margin=max(declared_margin,numeric_margin))
    report=track_sampled_mode_subspaces(features[:,:a.shape[1]],features[:,a.shape[1]:],np.ones(len(features)),
        previous.frequencies_hz,current.frequencies_hz,previous_ids,
        comparison_description='native quadratic refinement history; transferred u=Hphi/r in fine curved P2 mass inner product integral r^3 u v dr dz; QR/Cholesky coordinates, not physical point samples',**controls)
    report['physical_mapping']=dict(name='nested_curved',triangle_counts=[len(previous.space.geometry.cell_nodes),len(space.geometry.cell_nodes)],
        ancestry=ancestry,coefficient_feature_entries=coefficients.size,feature_rows=len(features),
        mass_quadrature_order=MASS_QUADRATURE_ORDER,mass_embedding_relative_difference=difference,
        numerical_assignment_margin_floor=numeric_margin,
        scope='polynomial mass integration up to rounding on explicitly nested quadratic maps; reflected inputs retain declared parity; no changed-domain, continuous-branch or physical-error certificate')
    return report

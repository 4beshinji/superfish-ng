# SPDX-License-Identifier: Apache-2.0
"""Mass-inner-product tracking on an explicitly verified affine refinement."""
import numpy as np
from .fem import assemble
from .high_order import quadratic_space,assemble_p2
from .marked_refinement import refine_marked_cells
from .mesh_input import mesh_to_dict
from .mode_tracking import _real_array,_control,track_sampled_mode_subspaces

MAX_FEATURE_ENTRIES=8388608


def _mass_features(coefficients,mass):
    """F.T F = X.T M X / scale using thin QR and a small SPD factorization.

    Do not factor the potentially rank-deficient column Gram matrix directly.
    Even dependent columns retain their dependence in the triangular factor R.
    """
    from .mass_tracking import mass_inner_product_features
    return mass_inner_product_features(coefficients,mass,label='nested affine')


def track_nested_affine_modes(previous,current,previous_ids,*,mapping,marked_cells,**controls):
    if mapping!='nested_affine':raise ValueError('explicit mapping must be nested_affine')
    case=getattr(previous,'case',None)
    if case is None or case!=getattr(current,'case',None) or case.geometry_order!=1:
        raise ValueError('nested_affine requires matching native cases and straight geometry')
    if previous.element_order!=case.element_order or current.element_order!=case.element_order:
        raise ValueError('nested_affine requires unchanged P1/P2 element order')
    # This comparison checks ancestry; quality policy belongs to the refinement
    # caller. Case constraints are still enforced by refine_marked_cells.
    refined=refine_marked_cells(case,previous.mesh,marked_cells,max_triangles=len(current.mesh.triangles),minimum_angle_deg=1e-12)
    if mesh_to_dict(refined.mesh)!=mesh_to_dict(current.mesh):raise ValueError('nested_affine current mesh differs from declared marked refinement')
    a=_real_array(previous.u,'previous coefficients',2);b=_real_array(current.u,'current coefficients',2)
    if (a.shape!=(refined.prolongation.shape[1],len(previous.frequencies_hz))
            or b.shape!=(refined.prolongation.shape[0],len(current.frequencies_hz))):raise ValueError('nested_affine coefficient dimensions differ from the declared spaces')
    entries=len(b)*(a.shape[1]+b.shape[1])
    if entries>MAX_FEATURE_ENTRIES:raise ValueError('nested_affine exceeds 8388608 coefficient feature entries')
    def normalized(x):
        scale=np.max(abs(x),axis=0);return x/np.where(scale>0,scale,1.)
    coefficients=np.column_stack((refined.prolongation@normalized(a),normalized(b)))
    space=quadratic_space(current.mesh) if case.element_order==2 else None
    _,mass=assemble_p2(space) if space else assemble(current.mesh)
    features,scale=_mass_features(coefficients,mass)
    gram=coefficients.T@(mass@coefficients)/scale
    denominator=max(float(np.linalg.norm(gram)),np.finfo(float).tiny)
    difference=float(np.linalg.norm(features.T@features-gram)/denominator)
    if not np.isfinite(difference) or difference>1e-10:raise ValueError('nested_affine mass embedding failed its inner-product check')
    numeric_margin=32*np.finfo(float).eps*max(coefficients.shape)
    declared_margin=_control(controls['minimum_assignment_margin'],'minimum_assignment_margin',zero=True)
    controls=dict(controls,minimum_assignment_margin=max(declared_margin,numeric_margin))
    report=track_sampled_mode_subspaces(features[:,:a.shape[1]],features[:,a.shape[1]:],np.ones(len(features)),
        previous.frequencies_hz,current.frequencies_hz,previous_ids,
        comparison_description='declared affine parent-child refinement; transferred u=Hphi/r in the fine P1/P2 mass inner product integral r^3 u v dr dz; QR/Cholesky coordinates, not physical point samples',**controls)
    report['physical_mapping']=dict(name=mapping,triangle_counts=[len(previous.mesh.triangles),len(current.mesh.triangles)],
        coefficient_feature_entries=entries,feature_rows=len(features),mass_embedding_relative_difference=difference,
        numerical_assignment_margin_floor=numeric_margin,
        scope='exact polynomial mass integration up to rounding on explicitly nested affine spaces; no changed-domain or continuous-branch certificate')
    return report

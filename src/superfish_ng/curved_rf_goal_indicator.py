# SPDX-License-Identifier: Apache-2.0
"""RF-weighted residual priorities from a native uniform confirmation solve."""
import math
import numpy as np
from .curved_rf_sensitivity import _omega
from .curved_rf_adjoint import r_over_q_adjoint
from .curved_rf_frequency_sensitivity import r_over_q_frequency_derivative
from .curved_fem import mapped_element_matrices
from .nested_curved_tracking import _nested_transfer,_track_prepared_nested_modes
from .curved_rf import quantities_curved
from .residual_indicator import mark_bulk


def curved_rf_goal_indicator(previous,current,*,mode=0,bulk_fraction=.5):
    """Return signed parent R/Q contributions and nonnegative marking scores.

    Requires exactly one uniform native extension and individually tracked modes.
    Both fields are actual eigenfields. The fine adjoint includes the angular
    frequency partial derivative; its parent interpolation is subtracted.
    Scores are priorities, never physical error bounds or stopping certificates.
    """
    mark_bulk([1.],bulk_fraction)  # Validate before reconstruction or factorization.
    _omega(previous,mode)
    if previous.reflection_source_case is not None or current.reflection_source_case is not None:
        raise ValueError('RF goal indicator requires direct native spaces, not reflected constructions')
    prepared=_nested_transfer(previous,current)
    p,space,a,b,ancestry=prepared
    if ancestry['appended_steps']!=[{'kind':'uniform'}]:
        raise ValueError('RF goal indicator requires exactly one uniform confirmation step')
    # _nested_transfer already applies and verifies this exact uniform step.
    # Its four-child order supplies parent ownership without rebuilding it.
    parent_cells=np.repeat(np.arange(len(previous.space.geometry.cell_nodes)),4)
    if previous.quadrature_order!=current.quadrature_order:
        raise ValueError('RF goal indicator requires the same assembly quadrature order')
    ids=[f'previous-{i}' for i in range(a.shape[1])]
    tracking=_track_prepared_nested_modes(previous,current,ids,prepared,minimum_overlap=.95,
        minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
    if tracking['status']!='PASS' or not tracking['individual_ids_complete'] or ids[mode] not in tracking['current_mode_ids']:
        raise ValueError('RF goal indicator requires verified individual mode tracking, not a cluster')
    fine_mode=tracking['current_mode_ids'].index(ids[mode])
    # The adjoint also checks eigenvalue consistency, separation and residuals.
    r_over_q_adjoint(previous,mode)
    adjoint=r_over_q_adjoint(current,fine_mode)
    frequency=r_over_q_frequency_derivative(current,fine_mode)
    u=b[:,fine_mode];mass=current.mass;stiffness=current.stiffness
    norm=float(u@(mass@u));coarse=p@a[:,mode]
    coarse_norm=float(coarse@(mass@coarse))
    coarse*=math.copysign(math.sqrt(norm/coarse_norm),float(u@(mass@coarse)))
    value=float(current.eigenvalues[fine_mode])
    qlambda=frequency.accelerator_derivative_ohm_per_rad_s*frequency.angular_frequency_rad_s/(2*value)
    total_adjoint=adjoint.accelerator_adjoint-qlambda*u/norm
    # Uniform restriction preserves all parent nodes first, so this is the
    # canonical nodal interpolant in the parent P2 space, not coordinate search.
    detail=total_adjoint-p@total_adjoint[:len(a)]
    eigenvalue=float(previous.eigenvalues[mode])
    residual=stiffness@coarse-eigenvalue*(mass@coarse)
    global_action=-float(detail@residual)
    removed_action=-float((total_adjoint-detail)@residual)
    children=[]
    for nodes,mapping in zip(space.geometry.cell_nodes,space.geometry.local_maps):
        k,m=mapped_element_matrices(mapping,quadrature_order=current.quadrature_order)
        children.append(-float(detail[nodes]@((k-eigenvalue*m)@coarse[nodes])))
    children=np.asarray(children)
    signed=np.bincount(parent_cells,weights=children,minlength=len(previous.space.geometry.cell_nodes))
    scores=abs(signed);total=float(math.fsum(signed));absolute=float(math.fsum(abs(children)))
    consistency=abs(total-global_action)/max(absolute,abs(global_action),np.finfo(float).tiny)
    if not np.isfinite(children).all() or not math.isfinite(consistency) or consistency>1e-10:
        raise ValueError('RF goal local/global residual action check failed')
    old=quantities_curved(previous,mode,include_surface_peaks=False)['r_over_q_accelerator_ohm']
    new=quantities_curved(current,fine_mode,include_surface_peaks=False)['r_over_q_accelerator_ohm']
    return dict(schema_version=1,previous_mode_index=mode,current_mode_index=fine_mode,
        parent_signed_accelerator_ohm=signed.tolist(),parent_signed_circuit_ohm=(signed/2).tolist(),
        parent_priority_ohm=scores.tolist(),estimated_accelerator_change_ohm=total,
        estimated_circuit_change_ohm=total/2,observed_accelerator_change_ohm=float(new-old),
        local_global_relative_difference=consistency,removed_parent_action_ohm=removed_action,
        tracking=tracking,physical_error_bound=None,bulk_fraction=float(bulk_fraction),
        marked_parent_cells=mark_bulk(scores,bulk_fraction),
        marking_measure="absolute signed parent RF contributions in ohms, not squared residuals",
        scope='fixed represented quadratic domain; one uniform confirmation; RF-weighted residual priorities, not error bounds or an adaptive stopping certificate')

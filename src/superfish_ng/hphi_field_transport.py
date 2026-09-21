# SPDX-License-Identifier: Apache-2.0
"""Norm-preserving comparison transport in the fixed cylindrical component frame."""
import numpy as np


def mapped_transport_factors(overlay, barycentric, *, regular=False):
    """Return physical E/H and scalar q/u factors at interior quadrature points.

    For y=F(x), D=det(dy/dx)>0, dV_y/dV_x=D*r_y/r_x.
    Keep the r,z,phi component labels fixed and multiply each physical component
    by sqrt(r_x/(D*r_y)). This is a unitary L2 comparison convention, not the
    covariant Maxwell field transform and not a candidate eigenfield.
    Scalar factors follow H=r*u or H=q/r, respectively.
    """
    old_radius = np.einsum('i,ti->t', barycentric, overlay.previous_vertices_rz_m[:, :, 0])
    new_radius = np.einsum('i,ti->t', barycentric, overlay.vertices_rz_m[:, :, 0])
    ratio = old_radius/new_radius
    determinant = overlay.determinants/overlay.previous_determinants
    physical = np.sqrt(ratio/determinant)
    scalar = physical*ratio if regular else physical/ratio
    if (np.any(old_radius <= 0) or np.any(new_radius <= 0)
            or not np.isfinite(physical).all() or not np.isfinite(scalar).all()
            or np.any(physical <= 0) or np.any(scalar <= 0)):
        raise ValueError('mapped Hphi comparison transport is unresolved in finite positive arithmetic')
    return physical, scalar

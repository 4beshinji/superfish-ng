# SPDX-License-Identifier: Apache-2.0
"""Finite-dimensional coordinates preserving a positive FEM mass inner product."""
import numpy as np


def mass_inner_product_features(coefficients,mass,*,label='mass tracking'):
    """Thin QR retains column dependence before a small SPD factorization."""
    q,r=np.linalg.qr(coefficients,mode='reduced')
    gram=q.T@(mass@q);scale=float(np.max(np.diag(gram)))
    if not np.isfinite(gram).all() or not scale>0:raise ValueError(f'{label} mass projection is not finite positive')
    gram=(gram/scale+gram.T/scale)/2
    try:lower=np.linalg.cholesky(gram)
    except np.linalg.LinAlgError as exc:raise ValueError(f'{label} mass projection lost positive definiteness') from exc
    return lower.T@r,scale

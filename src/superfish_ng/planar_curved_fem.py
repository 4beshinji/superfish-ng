# SPDX-License-Identifier: Apache-2.0
"""Cartesian curved-P2 area K/M: no radius weights or axis conditions."""
import numpy as np
from scipy.sparse import coo_matrix
from .fem import triangle_quadrature
from .planar_curved import PlanarCurvedCase, PlanarCurvedSpace, _bounded_integer
from .planar_curved_geometry import PlanarQuadraticTriangle, immutable_array


def mapped_planar_element_matrices(geometry, *, quadrature_order=8):
    if not isinstance(geometry, PlanarQuadraticTriangle):
        raise ValueError('planar mapped assembly requires a validated PlanarQuadraticTriangle')
    _bounded_integer(quadrature_order, 'quadrature_order', 4, 32)
    rule = list(triangle_quadrature(quadrature_order))
    mapped = geometry.evaluate([bary[1:] for bary, _ in rule])
    k, m = np.zeros((6, 6)), np.zeros((6, 6))
    for i, (_, weight) in enumerate(rule):
        measure = weight*mapped['determinant_m2'][i]
        basis = mapped['basis_values'][i]
        gradient = mapped['basis_gradients'][i]
        k += measure*(gradient@gradient.T)
        m += measure*np.outer(basis, basis)
    if not np.isfinite(k).all() or not np.isfinite(m).all():
        raise ValueError('planar mapped matrix arithmetic exceeds finite SI range')
    return k, m


def planar_curved_matrices(case):
    """Return original quadratic space, full area K/M, and PEC free indices."""
    if not isinstance(case, PlanarCurvedCase):
        raise ValueError('planar curved assembly requires an explicit PlanarCurvedCase')
    domain = case.domain
    free = np.arange(len(domain.points_xy_m))
    if case.polarization == 'tm':
        free = np.setdiff1d(free, np.unique(domain.boundary_nodes))
    positive_dimension = len(free)-(case.polarization == 'te')
    if case.modes > positive_dimension:
        raise ValueError('requested curved planar modes exceed positive FEM degrees of freedom; refine the quadratic domain or request fewer modes')
    local = [mapped_planar_element_matrices(element, quadrature_order=case.quadrature_order) for element in domain.elements]
    rows = np.repeat(domain.cell_nodes, 6, axis=1).ravel()
    columns = np.tile(domain.cell_nodes, (1, 6)).ravel()
    size = len(domain.points_xy_m)
    matrices = tuple(coo_matrix((np.array([pair[i] for pair in local]).ravel(), (rows, columns)), shape=(size, size)).tocsr() for i in (0, 1))
    if any(not np.isfinite(matrix.data).all() for matrix in matrices):
        raise ValueError('curved planar assembled matrices exceed finite SI range')
    space = PlanarCurvedSpace(domain, immutable_array(free, np.int64))
    return space, *matrices, space.free_dofs

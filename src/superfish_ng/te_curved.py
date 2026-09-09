# SPDX-License-Identifier: Apache-2.0
"""Mapped P2 geometry helpers for the explicit electric TE solution."""
import numpy as np
from .constants import MU0, TAU
from .config import integer


def mapped_fields(solution, cells, barycentric, mode):
    geometry = solution.space.geometry
    fields = {key: np.empty(len(cells)) for key in
              ('Ephi_V_per_m', 'Hr_quadrature_A_per_m', 'Hz_quadrature_A_per_m')}
    omega = TAU * solution.frequencies_hz[mode]
    for cell in np.unique(cells):
        selected = np.flatnonzero(cells == cell)
        bary = np.maximum(barycentric[selected], 0.)
        bary /= bary.sum(axis=1)[:, None]
        reference = bary[:, 1:].copy()
        reference[:, 1] = np.minimum(reference[:, 1], 1 - reference[:, 0])
        mapped = geometry.local_maps[cell].evaluate(reference)
        coefficients = solution.coefficients_v_per_m2[geometry.cell_nodes[cell], mode]
        value = mapped['basis_values'] @ coefficients
        gradient = np.einsum('qia,i->qa', mapped['basis_gradients'], coefficients)
        radius = mapped['points_rz_m'][:, 0]
        fields['Ephi_V_per_m'][selected] = radius * value
        fields['Hr_quadrature_A_per_m'][selected] = -radius * gradient[:, 1] / (omega * MU0)
        fields['Hz_quadrature_A_per_m'][selected] = (2 * value + radius * gradient[:, 0]) / (omega * MU0)
    return fields


def wall_integral(solution, mode, quadrature_order=None):
    """Integrate the side-cell tangential H on the actual mapped PEC wall."""
    integer(mode, 'TE wall mode', 0)
    if mode >= solution.case.modes:
        raise ValueError('TE wall mode is outside the saved mode range')
    order = solution.case.quadrature_order if quadrature_order is None else quadrature_order
    integer(order, 'TE wall quadrature order', 2)
    geometry = solution.space.geometry
    incidence = {}
    for cell, nodes in enumerate(geometry.cell_nodes):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            incidence.setdefault(tuple(sorted((int(nodes[a]), int(nodes[b])))), []).append((cell, a, b))
    selected = geometry.boundary_nodes[solution.space.boundary_tags == 'pec']
    cells, references, derivatives = [], [], []
    vertices = np.array(((0., 0.), (1., 0.), (0., 1.)))
    nodes, weights = np.polynomial.legendre.leggauss(order)
    fractions = (nodes + 1) / 2
    for edge in selected:
        sides = incidence.get(tuple(sorted(map(int, edge[:2]))), [])
        if len(sides) != 1:
            raise ValueError('TE mapped wall must have exactly one incident cell')
        cell, a, b = sides[0]
        cells.append(cell)
        references.append((1 - fractions[:, None]) * vertices[a] + fractions[:, None] * vertices[b])
        derivatives.append(vertices[b] - vertices[a])
    integral = 0.
    for cell, reference, derivative in zip(cells, references, derivatives):
        mapped = geometry.local_maps[cell].evaluate(reference)
        tangent = np.einsum('qab,b->qa', mapped['jacobian'], derivative)
        length = np.linalg.norm(tangent, axis=1)
        tangent /= length[:, None]
        bary = np.column_stack((1 - reference.sum(axis=1), reference))
        fields = mapped_fields(solution, np.full(order, cell, dtype=int), bary, mode)
        ht = fields['Hr_quadrature_A_per_m'] * tangent[:, 0] + fields['Hz_quadrature_A_per_m'] * tangent[:, 1]
        integral += float(np.sum(weights / 2 * TAU * mapped['points_rz_m'][:, 0] * length * ht**2))
    return integral


class MappedTELocator:
    def __init__(self, solution):
        from .curved_sampling import QuadraticLocator
        self.solution = solution
        self.locators = [QuadraticLocator(mapping) for mapping in solution.space.geometry.local_maps]
        self.lower = np.array([item.origin + item.scale * item.lower for item in self.locators])
        self.upper = np.array([item.origin + item.scale * item.upper for item in self.locators])

    def evaluate(self, points, mode, outside):
        fields = {key: np.full(len(points), np.nan) for key in
                  ('Ephi_V_per_m', 'Hr_quadrature_A_per_m', 'Hz_quadrature_A_per_m')}
        inside = np.zeros(len(points), dtype=bool)
        for index, point in enumerate(points):
            candidates = np.flatnonzero(np.all(point >= self.lower, axis=1) & np.all(point <= self.upper, axis=1))
            unresolved = []
            for cell in candidates:
                try:
                    reference = self.locators[cell].inverse(point)
                except ValueError as exc:
                    unresolved.append(str(exc))
                    continue
                if reference is None:
                    continue
                bary = np.array([[1-reference.sum(), *reference]])
                result = mapped_fields(self.solution, np.array([cell]), bary, mode)
                for key in fields:
                    fields[key][index] = result[key][0]
                inside[index] = True
                break
            if not inside[index]:
                if unresolved:
                    raise ValueError(f'TE curved probe {index} UNVERIFIED: ' + unresolved[0])
                if outside == 'raise':
                    raise ValueError(f'TE curved probe {index} lies outside the mapped mesh')
        axis = inside & (points[:, 0] == 0)
        fields['Ephi_V_per_m'][axis] = 0.
        fields['Hr_quadrature_A_per_m'][axis] = 0.
        return dict(fields, inside=inside)

# SPDX-License-Identifier: Apache-2.0
"""Display tessellation samples; never used to compute RF integrals."""
import numpy as np
from .sampling import FieldSampler


def display_fields(solution, mode=0):
    """Return points, triangles, nodal Hphi and cell-centre (Er,Ez,Hphi).

    P2 elements split into four straight display triangles. Exact P2 fields
    are sampled at their centres; these samples are not a new FEM solution.
    """
    order = getattr(solution, 'element_order', 1)
    if order == 1:
        from .rf import cell_fields
        mesh = solution.mesh
        return mesh.points, mesh.triangles, mesh.points[:, 0]*solution.u[:, mode], cell_fields(solution, mode)
    if order != 2:
        raise ValueError('unsupported display element order')
    sampler = FieldSampler.from_solution(solution)
    points = solution.space.dof_points
    dofs = solution.space.cell_dofs
    triangles = dofs[:, [[0, 3, 5], [3, 1, 4], [5, 4, 2], [3, 4, 5]]].reshape(-1, 3)
    fields = sampler.evaluate(points[triangles].mean(axis=1), mode)
    components = tuple(fields[key] for key in ('Er_quadrature_V_per_m', 'Ez_quadrature_V_per_m', 'Hphi_A_per_m'))
    return points, triangles, points[:, 0]*solution.u[:, mode], components

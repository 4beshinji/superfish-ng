# SPDX-License-Identifier: Apache-2.0
"""Explicit solver dispatch for rectangle, polygon and actual curved cases."""
from .planar_curved import PlanarCurvedCase


def solve_planar_case(case):
    if isinstance(case, PlanarCurvedCase):
        from .planar_curved_solver import solve_planar_curved
        return solve_planar_curved(case)
    from .planar import solve_planar
    return solve_planar(case)

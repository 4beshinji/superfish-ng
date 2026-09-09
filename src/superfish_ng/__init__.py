# SPDX-License-Identifier: Apache-2.0
"""Independent vacuum RF FEM solvers; see docs/PHYSICS.md for conventions."""
__version__ = "0.1.0"

from .config import Case
from .mesh import make_mesh
from .solver import solve
from .planar import PlanarCase, solve_planar
from .planar_polygon import PlanarPolygonCase, load_planar_case

__all__ = ["Case", "make_mesh", "solve", "PlanarCase", "PlanarPolygonCase", "load_planar_case", "solve_planar", "__version__"]

# SPDX-License-Identifier: Apache-2.0
"""Independent m=0 TM cavity solver; see docs/PHYSICS.md for conventions."""
__version__ = "0.1.0"

from .config import Case
from .mesh import make_mesh
from .solver import solve

__all__ = ["Case", "make_mesh", "solve", "__version__"]

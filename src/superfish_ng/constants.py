# SPDX-License-Identifier: Apache-2.0
"""Fixed SI constants for reproducibility, independent of SciPy CODATA updates.

mu0 uses the CODATA 2022 central value (not exact). eps0 is derived using
the exact SI speed of light; precision exceeds this discretization's accuracy.
"""
import math

C0 = 299_792_458.0
MU0 = 1.25663706127e-6
EPS0 = 1.0 / (MU0 * C0**2)
Z0 = MU0 * C0
TAU = 2 * math.pi

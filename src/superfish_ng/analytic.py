# SPDX-License-Identifier: Apache-2.0
"""Independent closed-form benchmarks, never used to produce FEM eigenvalues."""
import numpy as np
from scipy.special import jn_zeros, j1, jnp_zeros
from .constants import C0, EPS0, MU0, TAU
from .config import positive, integer


def tm0np_frequency(radius_m, length_m, n=1, p=0):
    positive(radius_m, "radius_m")
    positive(length_m, "length_m")
    integer(n, "n")
    integer(p, "p", 0)
    return float(C0/TAU*np.hypot(jn_zeros(0, n)[-1]/radius_m, p*np.pi/length_m))


def pillbox_spectrum(radius_m, length_m, count):
    integer(count, "count")
    modes = [(tm0np_frequency(radius_m, length_m, n, p), f"TM0{n}{p}", n, p)
             for n in range(1, count+1) for p in range(count)]
    return sorted(modes)[:count]


def pillbox_tm010(radius_m, length_m, beta=1., conductivity_s_per_m=5.8e7):
    positive(beta, "beta")
    if beta > 1:
        raise ValueError("beta must be <= 1")
    positive(conductivity_s_per_m, "conductivity_s_per_m")
    f = tm0np_frequency(radius_m, length_m)
    omega = TAU*f
    root = jn_zeros(0, 1)[0]
    ttf = abs(np.sinc(omega*length_m/(2*beta*C0)/np.pi))
    rs = np.sqrt(omega*MU0/(2*conductivity_s_per_m))
    g = omega*MU0*radius_m*length_m/(2*(radius_m+length_m))
    rq = 2*length_m*ttf**2/(omega*EPS0*np.pi*radius_m**2*j1(root)**2)
    hmax = j1(jnp_zeros(1, 1)[0])
    return {"frequency_hz": f, "transit_time_factor_abs": float(ttf),
            "surface_resistance_ohm": float(rs), "geometry_factor_ohm": float(g),
            "q0": float(g/rs), "r_over_q_accelerator_ohm": float(rq),
            "r_over_q_circuit_ohm": float(rq/2),
            "epk_over_eacc_estimate": float(1/ttf) if ttf > 1e-12 else None,
            "bpk_over_eacc_estimate_mt_per_mv_per_m": float(hmax/(C0*ttf)*1e9) if ttf > 1e-12 else None}

# SPDX-License-Identifier: Apache-2.0
"""Independent closed-form benchmarks, never used to produce FEM eigenvalues."""
import numpy as np
from scipy.special import jn_zeros, j1, jnp_zeros
from .constants import C0, EPS0, MU0, TAU
from .config import positive, integer, acceleration_parameters


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


def pillbox_tm_mode(radius_m, length_m, n=1, p=0, beta=1.,
                    conductivity_s_per_m=5.8e7, normalization_j=1., *,
                    active_length_m=None, voltage_interval_m=None, phase_origin_m=None):
    """Full-cavity TM0np reference: Hphi=H0 J1(chi*r/R) cos(p*pi*z/L).

    Axial mean cos² is 1 for p=0, 1/2 otherwise. Both end plates contribute
    to loss. Peak phasors, total stored energy, no FEM calibration.
    """
    f = tm0np_frequency(radius_m, length_m, n, p)
    positive(beta, 'beta')
    positive(conductivity_s_per_m, 'conductivity_s_per_m')
    positive(normalization_j, 'normalization_j')
    if beta > 1:
        raise ValueError('beta must be <= 1')
    omega = TAU*f
    chi = jn_zeros(0, n)[-1]
    alpha, kz = chi/radius_m, p*np.pi/length_m
    average = 1. if p == 0 else .5
    h0 = np.sqrt(2*normalization_j/(MU0*np.pi*radius_m**2*length_m*j1(chi)**2*average))
    e0 = h0*alpha/(omega*EPS0)
    kb = omega/(beta*C0)
    def exp_integral(k):
        x = k*length_m/2
        return length_m*np.exp(1j*x)*np.sinc(x/np.pi)
    voltage = e0*(exp_integral(kb+kz)+exp_integral(kb-kz))/2
    absolute = e0*length_m*(1. if p == 0 else 2/np.pi)
    overridden = any(v is not None for v in (active_length_m, voltage_interval_m, phase_origin_m))
    if overridden:
        active, (a, b), origin = acceleration_parameters(length_m, active_length_m, voltage_interval_m, phase_origin_m)
        def interval_integral(k):
            return (b-a)*np.exp(1j*k*(a+b)/2)*np.sinc(k*(b-a)/(2*np.pi))
        phase = kb*origin
        if not np.isfinite(phase):
            raise ValueError('phase_origin_m produces an unrepresentable phase')
        voltage = e0*(interval_integral(kb+kz)+interval_integral(kb-kz))/2*np.exp(-1j*phase)
        def absolute_cosine_primitive(t):
            periods = np.floor((t+np.pi/2)/np.pi)
            return 2*periods+np.sin(t-periods*np.pi)
        absolute = e0*(b-a) if p == 0 else e0*(absolute_cosine_primitive(kz*b)-absolute_cosine_primitive(kz*a))/kz
    rs = np.sqrt(omega*MU0/(2*conductivity_s_per_m))
    loss = np.pi*rs*h0**2*j1(chi)**2*(radius_m*length_m*average+radius_m**2)
    q0 = omega*normalization_j/loss
    rq = abs(voltage)**2/(omega*normalization_j)
    result = {'frequency_hz': float(f), 'stored_energy_j': float(normalization_j),
            'surface_resistance_ohm': float(rs), 'wall_loss_w': float(loss),
            'q0': float(q0), 'geometry_factor_ohm': float(q0*rs),
            'vacc_v': float(abs(voltage)), 'transit_time_factor_abs': float(abs(voltage)/absolute),
            'r_over_q_accelerator_ohm': float(rq), 'r_over_q_circuit_ohm': float(rq/2),
            'r_shunt_accelerator_ohm': float(rq*q0), 'r_shunt_circuit_ohm': float(rq*q0/2),
            'h0_a_per_m': float(h0), 'e0_v_per_m': float(e0),
            'radial_wave_number_per_m': float(alpha), 'axial_wave_number_per_m': float(kz)}
    if overridden:
        result.update(voltage_real_v=float(voltage.real), voltage_imag_v=float(voltage.imag),
                      active_length_m=active, eacc_v_per_m=float(abs(voltage)/active),
                      voltage_interval_start_m=a, voltage_interval_end_m=b, phase_origin_m=origin)
    return result

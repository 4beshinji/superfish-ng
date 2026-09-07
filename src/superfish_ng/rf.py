# SPDX-License-Identifier: Apache-2.0
"""Peak phasors, total time-averaged stored energy, and explicit R/Q conventions."""
import numpy as np
from .constants import C0, EPS0, MU0, TAU
from .mesh import element_geometry


def linear_voltage(z, field, wave_number):
    """Exact integral of a piecewise-linear real field times exp(+i*k*z).

    Taylor expansion avoids cancellation when k*dz is small. This removes an
    integration-resolution dependency for slow particles/high-order modes.
    """
    z, field = np.asarray(z), np.asarray(field)
    h = np.diff(z)/2
    t = wave_number*h
    sinc = np.sinc(t/np.pi)
    f = np.empty_like(t)
    small = np.abs(t) < 1e-3
    f[small] = t[small]/3 - t[small]**3/30 + t[small]**5/840
    f[~small] = (np.sin(t[~small])-t[~small]*np.cos(t[~small]))/t[~small]**2
    a, b = (field[:-1]+field[1:])/2, (field[1:]-field[:-1])/2
    voltage = np.sum(2*h*np.exp(1j*wave_number*(z[:-1]+h))*(a*sinc+1j*b*f))
    left, right = np.abs(field[:-1]), np.abs(field[1:])
    absolute = h*(left+right)
    crossing = field[:-1]*field[1:] < 0
    absolute[crossing] = h[crossing]*(left[crossing]**2+right[crossing]**2)/(left[crossing]+right[crossing])
    return complex(voltage), float(np.sum(absolute))


def cell_fields(solution, mode):
    """Cell-centre signed amplitudes (Er, Ez, Hphi); Ephasor=-i*Eamplitude."""
    if getattr(solution, 'element_order', 1) == 2:
        from .sampling import FieldSampler
        centers = solution.mesh.points[solution.mesh.triangles].mean(axis=1)
        fields = FieldSampler.from_solution(solution).evaluate(centers, mode)
        return tuple(fields[key] for key in ('Er_quadrature_V_per_m', 'Ez_quadrature_V_per_m', 'Hphi_A_per_m'))
    if getattr(solution, 'element_order', 1) != 1:
        raise ValueError('unsupported element order for cell fields')
    mesh = solution.mesh
    p, _, grad = element_geometry(mesh)
    u = solution.u[:, mode][mesh.triangles]
    du = np.einsum("ti,tij->tj", u, grad)
    uc, r = u.mean(axis=1), p[:, :, 0].mean(axis=1)
    omega = float(TAU*solution.frequencies_hz[mode])
    return -r*du[:, 1]/(omega*EPS0), (2*uc+r*du[:, 0])/(omega*EPS0), r*uc


def accelerating_voltage(case, z, field, wave_number):
    """Integrate the selected axial interval and apply a global phase origin."""
    _, (a, b), origin = case.acceleration_parameters
    if case.voltage_interval_m is not None:
        z, field = np.asarray(z), np.asarray(field)
        clipped = np.concatenate(([a], z[(z > a) & (z < b)], [b]))
        field = np.interp(clipped, z, field)
        z = clipped
    voltage, absolute = linear_voltage(z, field, wave_number)
    if origin != 0:
        phase = wave_number*origin
        if not np.isfinite(phase):
            raise ValueError('phase_origin_m produces an unrepresentable phase')
        voltage *= complex(np.exp(-1j*phase))
    return voltage, absolute


def quantities(case, solution, mode=0):
    order = getattr(solution, 'element_order', 1)
    if order not in (1, 2):
        raise ValueError('unsupported element order for RF integrals')
    mesh, u = solution.mesh, solution.u[:, mode]
    omega = float(TAU*solution.frequencies_hz[mode])
    h2_volume = TAU*float(u @ (solution.mass @ u))
    e2_volume = TAU*float(u @ (solution.stiffness @ u))/(omega*EPS0)**2
    magnetic, electric = MU0*h2_volume/4, EPS0*e2_volume/4
    energy = magnetic+electric
    if order == 2:
        from .quadratic_rf import surface_integrals_p2, accelerating_voltage_p2
        surface_h2, epk, hpk = surface_integrals_p2(solution, mode)
    else:
        pec = mesh.boundary_tags == "pec"
        edges, cells = mesh.boundary_edges[pec], mesh.boundary_cells[pec]
        ends, values = mesh.points[edges], u[edges]
        ds = np.linalg.norm(ends[:, 1]-ends[:, 0], axis=1)
        q, w = np.polynomial.legendre.leggauss(4)
        surface_h2 = 0.
        for t, weight in zip((q+1)/2, w/2):
            r = (1-t)*ends[:, 0, 0]+t*ends[:, 1, 0]
            h = r*((1-t)*values[:, 0]+t*values[:, 1])
            surface_h2 += float(np.sum(weight*ds*TAU*r*h*h))
    rs = float(np.sqrt(omega*MU0/(2*case.conductivity_s_per_m)))
    loss = rs*surface_h2/2
    if order == 2:
        voltage, absolute = accelerating_voltage_p2(case, solution, mode)
    else:
        z = mesh.points[mesh.axis_nodes, 1]
        ez_axis = 2*u[mesh.axis_nodes]/(omega*EPS0)
        voltage, absolute = accelerating_voltage(case, z, ez_axis, omega/(case.beta*C0))
    vacc = abs(voltage)
    # Near-zero accelerating voltage makes normalized peak ratios meaningless.
    accelerating = absolute > 0 and vacc > 1e-12*absolute
    active_length, interval, phase_origin = case.acceleration_parameters
    eacc = vacc/active_length
    if order == 1:
        _, _, grad = element_geometry(mesh)
        du = np.einsum("ti,tij->tj", u[mesh.triangles], grad)[cells]
        # E is affine within each element: its norm on an edge is maximal at an end.
        er = -ends[:, :, 0]*du[:, None, 1]/(omega*EPS0)
        ez = (2*values+ends[:, :, 0]*du[:, None, 0])/(omega*EPS0)
        epk = float(np.max(np.hypot(er, ez)))
        # H=r*u is quadratic on each straight edge; include stationary points.
        r0, dr = ends[:, 0, 0], ends[:, 1, 0]-ends[:, 0, 0]
        u0, delta_u = values[:, 0], values[:, 1]-values[:, 0]
        a, b = dr*delta_u, r0*delta_u+dr*u0
        t = np.zeros_like(a)
        np.divide(-b, 2*a, out=t, where=a != 0)
        t = np.clip(t, 0, 1)
        hpk = float(np.max(np.abs(np.concatenate((r0*u0, (r0+dr)*(u0+delta_u), (r0+t*dr)*(u0+t*delta_u))))))
    rq = vacc**2/(omega*energy)
    q0 = omega*energy/loss
    result = {
        "mode_index": mode+1, "frequency_hz": float(solution.frequencies_hz[mode]),
        "relative_eigen_residual": float(solution.residuals[mode]),
        "stored_energy_j": energy, "electric_energy_j": electric, "magnetic_energy_j": magnetic,
        "energy_balance_relative": abs(electric-magnetic)/energy,
        "surface_resistance_ohm": float(rs), "wall_loss_w": float(loss), "q0": q0,
        "geometry_factor_ohm": q0*rs,
        "voltage_real_v": voltage.real, "voltage_imag_v": voltage.imag,
        "vacc_v": vacc, "beta": case.beta, "active_length_m": active_length,
        "eacc_v_per_m": eacc, "transit_time_factor_abs": vacc/absolute if absolute else None,
        "r_over_q_accelerator_ohm": rq, "r_over_q_circuit_ohm": rq/2,
        "r_shunt_accelerator_ohm": rq*q0, "r_shunt_circuit_ohm": rq*q0/2,
        "epk_surface_estimate_v_per_m": epk, "bpk_surface_estimate_t": MU0*hpk,
        "epk_over_eacc_estimate": epk/eacc if accelerating else None,
        "bpk_over_eacc_estimate_mt_per_mv_per_m": MU0*hpk/eacc*1e9 if accelerating else None,
        "peak_status": f"P{order} one-sided surface estimate; corners may be singular; no error bound",
    }
    if case.has_acceleration_overrides:
        result.update(voltage_interval_start_m=interval[0], voltage_interval_end_m=interval[1], phase_origin_m=phase_origin)
    return result

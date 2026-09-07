# SPDX-License-Identifier: Apache-2.0
"""Mapped curved-wall loss and straight-axis voltage under the native RF convention."""
import math
import numpy as np
from .constants import C0,MU0,EPS0,TAU
from .curved_solution import CurvedSolution
from .quadratic_rf import quadratic_voltage


def _check(solution,mode):
    if not isinstance(solution,CurvedSolution):
        raise ValueError('curved RF requires a CurvedSolution')
    if type(mode) is not int or not 0<=mode<len(solution.frequencies_hz):
        raise ValueError('mode must be a valid zero-based integer')


def wall_h2_integral(solution,mode=0,*,quadrature_order=8):
    """Integral of peak |Hphi|² over PEC walls, with the quadratic edge arc length."""
    _check(solution,mode)
    if type(quadrature_order) is not int or quadrature_order<2:
        raise ValueError('wall quadrature_order must be an integer >= 2')
    geometry=solution.space.geometry
    nodes=geometry.boundary_nodes[solution.space.boundary_tags=='pec']
    points=geometry.points_rz_m[nodes]
    coefficients=solution.u[nodes,mode]
    q,w=np.polynomial.legendre.leggauss(quadrature_order)
    integral=0.
    for t,weight in zip((q+1)/2,w/2):
        shape=np.array(((1-t)*(1-2*t),t*(2*t-1),4*t*(1-t)))
        derivative=np.array((-3+4*t,-1+4*t,4-8*t))
        radius=points[:,:,0]@shape
        tangent=np.einsum('eic,i->ec',points-points[:,:1,:],derivative)
        h=radius*(coefficients@shape)
        integral+=float(np.sum(weight*TAU*radius*np.linalg.norm(tangent,axis=1)*h*h))
    return integral


def accelerating_voltage_curved(solution,mode=0):
    """Axis is geometrically straight; retain all P2 coefficients and R01 overrides."""
    _check(solution,mode)
    geometry=solution.space.geometry
    nodes=geometry.boundary_nodes[solution.space.boundary_tags=='axis']
    points=geometry.points_rz_m[nodes]
    if not np.all(points[:,:,0]==0):
        raise ValueError('curved RF axis must stay exactly at r=0')
    if not np.array_equal(points[:,2,1],points[:,:2,1].mean(axis=1)):
        raise ValueError('curved RF axis parameterization must be affine')
    omega=TAU*solution.frequencies_hz[mode]
    field=2*solution.u[nodes,mode]/(omega*EPS0)
    _,interval,origin=solution.case.acceleration_parameters
    return quadratic_voltage(points[:,:2,1],field,omega/(solution.case.beta*C0),
                             interval=interval,phase_origin=origin)


def quantities_curved(solution,mode=0,*,wall_quadrature_order=8):
    """RF integrals only: surface peaks are explicitly not evaluated here."""
    _check(solution,mode)
    case=solution.case
    omega=float(TAU*solution.frequencies_hz[mode])
    u=solution.u[:,mode]
    magnetic=MU0*TAU*float(u@(solution.mass@u))/4
    electric=TAU*float(u@(solution.stiffness@u))/(4*omega**2*EPS0)
    energy=magnetic+electric
    rs=math.sqrt(omega*MU0/(2*case.conductivity_s_per_m))
    surface=wall_h2_integral(solution,mode,quadrature_order=wall_quadrature_order)
    loss=rs*surface/2
    if not math.isfinite(loss) or loss<=0 or not math.isfinite(energy) or energy<=0:
        raise ValueError('curved RF requires positive finite energy and PEC wall loss')
    voltage,absolute=accelerating_voltage_curved(solution,mode)
    vacc=abs(voltage)
    active,interval,origin=case.acceleration_parameters
    rq=vacc**2/(omega*energy)
    q0=omega*energy/loss
    return dict(mode_index=mode+1,frequency_hz=float(solution.frequencies_hz[mode]),
                stored_energy_j=energy,electric_energy_j=electric,magnetic_energy_j=magnetic,
                energy_balance_relative=abs(electric-magnetic)/energy,
                surface_resistance_ohm=rs,wall_loss_w=loss,q0=q0,geometry_factor_ohm=q0*rs,
                voltage_real_v=voltage.real,voltage_imag_v=voltage.imag,vacc_v=vacc,
                beta=case.beta,active_length_m=active,eacc_v_per_m=vacc/active,
                voltage_interval_start_m=interval[0],voltage_interval_end_m=interval[1],
                phase_origin_m=origin,transit_time_factor_abs=vacc/absolute if absolute else None,
                r_over_q_accelerator_ohm=rq,r_over_q_circuit_ohm=rq/2,
                r_shunt_accelerator_ohm=rq*q0,r_shunt_circuit_ohm=rq*q0/2,
                wall_quadrature_order=wall_quadrature_order,
                peak_status='not evaluated; curved surface peak validation pending')

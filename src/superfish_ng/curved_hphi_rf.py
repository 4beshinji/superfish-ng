# SPDX-License-Identifier: Apache-2.0
"""Original curved Hphi volume/wall integrals and explicit straight-axis voltage."""
import numpy as np
from .constants import C0,EPS0,MU0,TAU
from .config import integer
from .fem import triangle_quadrature
from .quadratic_rf import quadratic_voltage
from .curved_hphi import CurvedHphiSolution


def _integrals(solution,mode,order):
    g=solution.space.geometry;base=g.base_mesh;rule=list(triangle_quadrature(order))
    cells=np.repeat(np.arange(len(g.cell_nodes)),len(rule));bary=np.tile([p for p,w in rule],(len(g.cell_nodes),1))
    points,values,grad,det=solution.mapped_points(cells,bary);fields=solution.fields_in_cells(cells,bary,mode)
    measure=TAU*points[:,0]*det*np.tile([w for p,w in rule],len(g.cell_nodes))
    electric=EPS0/4*float(measure@(fields['Er_quadrature_V_per_m']**2+fields['Ez_quadrature_V_per_m']**2))
    magnetic=MU0/4*float(measure@fields['Hphi_real_A_per_m']**2)
    t,w=np.polynomial.legendre.leggauss(order);t=(t+1)/2;w=w/2
    count=len(base.surface_area_m2_by_segment);walls=np.zeros(count);areas=np.zeros(count)
    phi=np.column_stack(((1-t)*(1-2*t),t*(2*t-1),4*t*(1-t)))
    derivative=np.column_stack((4*t-3,4*t-1,4-8*t))
    for edge in np.flatnonzero(g.boundary_tags=='pec'):
        cell=int(base.boundary_cells[edge]);i,j=base.boundary_local_vertices[edge]
        bary=np.zeros((order,3));bary[:,i]=1-t;bary[:,j]=t
        h=solution.fields_in_cells(np.full(order,cell,dtype=int),bary,mode)['Hphi_real_A_per_m']
        nodes=g.points_rz_m[g.boundary_nodes[edge]];r=(phi@nodes)[:,0]
        speed=np.linalg.norm(derivative@(nodes-nodes[0]),axis=1);measure=TAU*w*r*speed
        segment=base.boundary_segments[edge];walls[segment]+=measure@(h*h);areas[segment]+=measure.sum()
    return electric,magnetic,walls,areas


def curved_hphi_quantities(solution,mode=0):
    if type(solution) is not CurvedHphiSolution:raise ValueError('curved Hphi RF requires a CurvedHphiSolution')
    integer(mode,'curved Hphi RF mode',0)
    if mode>=solution.case.modes:raise ValueError('curved Hphi RF mode is out of range')
    case=solution.case;orders=[case.quadrature_order+4,case.quadrature_order+8]
    low=_integrals(solution,mode,orders[0]);high=_integrals(solution,mode,orders[1]);differences=[]
    for a,b in zip(low,high):
        a,b=np.asarray(a),np.asarray(b);denominator=np.maximum(abs(a),abs(b))
        differences.append(float(np.max(np.divide(abs(a-b),denominator,out=np.zeros_like(a),where=denominator>0))))
    if not np.isfinite(differences).all() or max(differences)>5e-10:
        raise ValueError('curved Hphi RF quadrature is unresolved; increase quadrature_order or refine the explicit geometry')
    electric,magnetic,walls,areas=high;energy=electric+magnetic
    frequency=float(solution.frequencies_hz[mode]);omega=TAU*frequency;wall=float(walls.sum())
    rs=float(np.sqrt(np.pi*frequency*MU0/case.conductivity_s_per_m));loss=rs*wall/2
    if (not np.isfinite([electric,magnetic,*walls,*areas,energy,loss]).all() or min(electric,magnetic,energy,wall,loss)<=0
        or abs(energy/case.normalization_j-1)>1e-8):
        raise ValueError('curved Hphi RF fails finite energy, normalization or positive total wall loss')
    components=[];offset=0
    base=case.geometry.base_mesh
    for contour in (base.outer_rz_m,*base.holes_rz_m):
        components.append(float(walls[offset:offset+len(contour)].sum()));offset+=len(contour)
    result=dict(frequency_hz=frequency,stored_energy_j=energy,electric_energy_j=electric,magnetic_energy_j=magnetic,
        wall_loss_w=loss,surface_resistance_ohm=rs,q0=omega*energy/loss,geometry_factor_ohm=2*omega*energy/wall,
        wall_h2_integral_a2_by_segment=walls.tolist(),wall_h2_integral_a2_by_component=components,
        volume_m3=case.geometry.volume_m3,surface_area_m2_by_segment=areas.tolist(),
        vacc_v=None,eacc_v_per_m=None,r_over_q_accelerator_ohm=None,r_over_q_circuit_ohm=None,
        accelerating_quantities_reason='no acceleration path is declared',
        integration_diagnostic=dict(orders=orders,electric_energy_relative_difference=differences[0],
            magnetic_energy_relative_difference=differences[1],maximum_wall_segment_relative_difference=differences[2],
            maximum_surface_area_segment_relative_difference=differences[3],relative_tolerance=5e-10,
            interpretation='finite integration comparison; no discretization or surface-peak accuracy bound'))
    if case.acceleration is not None:
        path=case.acceleration;edges=solution.space.boundary_dofs[case.geometry.boundary_tags=='axis']
        ends=solution.space.dof_points[edges[:,:2],1]
        values=-2*solution.coefficients[edges,mode]/(omega*EPS0)
        if case.element_order==1:values=np.column_stack((values,values.mean(axis=1)))
        voltage,absolute=quadratic_voltage(ends,values,omega/(path.beta*C0),interval=(path.z_start_m,path.z_end_m),phase_origin=path.phase_origin_m)
        voltage*=1j;rq=abs(voltage)**2/(omega*energy);eacc=abs(voltage)/(path.z_end_m-path.z_start_m)
        if not np.isfinite([voltage.real,voltage.imag,absolute,rq,eacc]).all():raise ValueError('curved Hphi acceleration exceeds finite SI arithmetic')
        result.update(vacc_v=dict(real=voltage.real,imag=voltage.imag),axis_absolute_voltage_v=absolute,
            eacc_v_per_m=eacc,r_over_q_accelerator_ohm=rq,r_over_q_circuit_ohm=rq/2,accelerating_quantities_reason=None)
    if not np.isfinite([result[k] for k in ('q0','geometry_factor_ohm','stored_energy_j','wall_loss_w')]).all():
        raise ValueError('curved Hphi RF exceeds finite SI arithmetic')
    return result

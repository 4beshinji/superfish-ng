# SPDX-License-Identifier: Apache-2.0
"""Cell-material energies, all PEC wall losses and declared vacuum-axis voltage."""
import numpy as np
from .constants import C0,EPS0,MU0,TAU
from .config import integer
from .fem import triangle_quadrature
from .quadratic_rf import quadratic_voltage
from .material_hphi import MaterialHphiSolution


def _material_integrals(solution,mode,order):
    partition=solution.case.partition;mesh=partition.mesh;space=solution.space
    cells=np.arange(len(mesh.triangles));vertices=mesh.points_rz_m[mesh.triangles]
    electric=np.zeros(len(partition.regions));magnetic=np.zeros_like(electric)
    for bary,weight in triangle_quadrature(order):
        fields=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)),mode)
        measure=TAU*(vertices[:,:,0]@bary)*weight*solution.determinants
        electric+=np.bincount(partition.cell_region_indices,weights=EPS0/4*partition.epsilon_r*measure*
            (fields['Er_quadrature_V_per_m']**2+fields['Ez_quadrature_V_per_m']**2),minlength=len(electric))
        magnetic+=np.bincount(partition.cell_region_indices,weights=MU0/4*partition.mu_r*measure*
            fields['Hphi_real_A_per_m']**2,minlength=len(magnetic))
    wall_indices=np.flatnonzero(space.mesh.boundary_tags=='pec')
    owners=mesh.boundary_cells[wall_indices];local=mesh.boundary_local_vertices[wall_indices]
    endpoints=mesh.points_rz_m[mesh.boundary_edges[wall_indices]];length=np.linalg.norm(endpoints[:,1]-endpoints[:,0],axis=1)
    wall_edges=np.zeros(len(wall_indices));areas=np.zeros_like(wall_edges);rows=np.arange(len(wall_indices))
    nodes,weights=np.polynomial.legendre.leggauss(order)
    for t,weight in zip((nodes+1)/2,weights/2):
        bary=np.zeros((len(owners),3));bary[rows,local[:,0]]=1-t;bary[rows,local[:,1]]=t
        h=solution.fields_in_cells(owners,bary,mode)['Hphi_real_A_per_m']
        radius=(1-t)*endpoints[:,0,0]+t*endpoints[:,1,0];measure=TAU*radius*weight*length
        wall_edges+=measure*h*h;areas+=measure
    count=len(mesh.surface_area_m2_by_segment)
    walls=np.bincount(mesh.boundary_segments[wall_indices],weights=wall_edges,minlength=count)
    surface=np.bincount(mesh.boundary_segments[wall_indices],weights=areas,minlength=count)
    region_walls=np.bincount(partition.cell_region_indices[owners],weights=wall_edges,minlength=len(electric))
    return electric,magnetic,walls,surface,region_walls


def material_hphi_quantities(solution,mode=0):
    if type(solution) is not MaterialHphiSolution:raise ValueError('material Hphi RF requires MaterialHphiSolution')
    integer(mode,'material Hphi RF mode',0)
    if mode>=solution.case.modes:raise ValueError('material Hphi RF mode is out of range')
    case=solution.case;partition=case.partition;mesh=partition.mesh;orders=[case.quadrature_order+4,case.quadrature_order+8]
    low=_material_integrals(solution,mode,orders[0]);high=_material_integrals(solution,mode,orders[1]);differences=[]
    for a,b in zip(low,high):
        denominator=np.maximum(abs(a),abs(b))
        differences.append(float(np.max(np.divide(abs(a-b),denominator,out=np.zeros_like(a),where=denominator>0))))
    if not np.isfinite(differences).all() or max(differences)>5e-10:
        raise ValueError('material Hphi RF quadrature is unresolved; refine the mesh or increase quadrature_order')
    electric_regions,magnetic_regions,walls,areas,region_walls=high
    electric=float(electric_regions.sum());magnetic=float(magnetic_regions.sum());energy=electric+magnetic
    frequency=float(solution.frequencies_hz[mode]);omega=TAU*frequency;wall=float(walls.sum())
    # The specified wall is nonmagnetic metal. Adjacent RF material mu_r is
    # already used in the eigensolve and energy, but is not the wall's mu_r.
    rs=float(np.sqrt(np.pi*frequency*MU0/case.conductivity_s_per_m));loss=rs*wall/2
    if (not np.isfinite([electric,magnetic,*walls,*areas,*region_walls,loss]).all() or min(electric,magnetic,wall,loss)<=0
        or max(abs(2*electric/case.normalization_j-1),abs(2*magnetic/case.normalization_j-1))>1e-8):
        raise ValueError('material Hphi RF fails finite energy, electric/magnetic balance or positive wall loss')
    components=[];offset=0
    for contour in (mesh.outer_rz_m,*mesh.holes_rz_m):
        components.append(float(walls[offset:offset+len(contour)].sum()));offset+=len(contour)
    regions=[dict(id=region.id,material=region.material,volume_m3=float(partition.region_volume_m3[i]),
        electric_energy_j=float(electric_regions[i]),magnetic_energy_j=float(magnetic_regions[i]),
        stored_energy_j=float(electric_regions[i]+magnetic_regions[i]),adjacent_wall_loss_w=float(rs*region_walls[i]/2))
        for i,region in enumerate(partition.regions)]
    result=dict(frequency_hz=frequency,stored_energy_j=energy,electric_energy_j=electric,magnetic_energy_j=magnetic,
        wall_loss_w=loss,volume_loss_w=0.,surface_resistance_ohm=rs,q0=omega*energy/loss,geometry_factor_ohm=2*omega*energy/wall,
        wall_h2_integral_a2_by_segment=walls.tolist(),wall_h2_integral_a2_by_component=components,
        volume_m3=mesh.volume_m3,surface_area_m2_by_segment=areas.tolist(),regions=regions,
        wall_model=dict(type='normal_skin_effect_perturbation',relative_permeability=1.,conductivity_s_per_m=case.conductivity_s_per_m),
        normalization=dict(stored_energy_j=case.normalization_j,volume_measure='2*pi*r*dr*dz',
            phasor='peak exp(+i*omega*t); field=real+i*quadrature; Hphi real; Er/Ez quadrature',
            energy='(epsilon0*epsilon_r*|E|^2+mu0*mu_r*|H|^2)/4',
            r_over_q_accelerator='|Vacc|^2/(omega*U)',r_over_q_circuit='|Vacc|^2/(2*omega*U)'),
        vacc_v=None,eacc_v_per_m=None,r_over_q_accelerator_ohm=None,r_over_q_circuit_ohm=None,
        accelerating_quantities_reason='no vacuum-axis acceleration path is declared',
        integration_diagnostic=dict(orders=orders,maximum_electric_region_relative_difference=differences[0],
            maximum_magnetic_region_relative_difference=differences[1],maximum_wall_segment_relative_difference=differences[2],
            maximum_surface_area_segment_relative_difference=differences[3],maximum_wall_region_relative_difference=differences[4],
            relative_tolerance=5e-10,interpretation='finite integration comparison; no discretization or surface-peak accuracy bound'))
    if case.acceleration is not None:
        path=case.acceleration;edges=solution.space.boundary_dofs[mesh.axis_edges]
        ends=solution.space.dof_points[edges[:,:2],1]
        values=-2*solution.coefficients[edges,mode]/(omega*EPS0*partition.epsilon_r[mesh.boundary_cells[mesh.axis_edges],None])
        if case.element_order==1:values=np.column_stack((values,values.mean(axis=1)))
        voltage,absolute=quadratic_voltage(ends,values,omega/(path.beta*C0),interval=(path.z_start_m,path.z_end_m),phase_origin=path.phase_origin_m)
        voltage*=1j;rq=abs(voltage)**2/(omega*energy);eacc=abs(voltage)/(path.z_end_m-path.z_start_m)
        if not np.isfinite([voltage.real,voltage.imag,absolute,rq,eacc]).all():raise ValueError('material Hphi acceleration exceeds finite SI arithmetic')
        result.update(vacc_v=dict(real=voltage.real,imag=voltage.imag),axis_absolute_voltage_v=absolute,
            eacc_v_per_m=eacc,r_over_q_accelerator_ohm=rq,r_over_q_circuit_ohm=rq/2,accelerating_quantities_reason=None)
    if not np.isfinite([result[k] for k in ('q0','geometry_factor_ohm','stored_energy_j','wall_loss_w')]).all():
        raise ValueError('material Hphi RF exceeds finite SI arithmetic')
    return result

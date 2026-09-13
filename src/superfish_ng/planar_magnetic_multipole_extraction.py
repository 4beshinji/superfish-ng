# SPDX-License-Identifier: Apache-2.0
"""Original linear planar FEM magnetic harmonics in a verified source-free disk."""
import hashlib,json
from fractions import Fraction
import numpy as np
from .constants import MU0
from .planar_bh import PlanarBHSolution,solve_planar_bh
from .planar_recoil import PlanarRecoilSolution,solve_planar_recoil
from .config import integer
from .planar_magnetostatic import PlanarMagnetostaticSolution,solve_planar_magnetostatic
from .planar_magnetic_multipoles import PlanarMagneticMultipoleFrame,PlanarMagneticMultipoleSeries


def _segment_distance(a,b):
    with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
        delta=b-a;squared=np.sum(delta*delta,axis=-1);fraction=np.clip(-np.sum(a*delta,axis=-1)/squared,0.,1.);nearest=a+fraction[...,None]*delta;distance=np.hypot(nearest[...,0],nearest[...,1])
    if np.any(squared<=0.) or not np.isfinite(distance).all():raise ValueError('multipole disk/edge distances are unresolved in finite SI geometry')
    return distance


def _linear_material_aperture(solution,cells):
    p=solution.case.partition;materials={m.id:m for m in p.materials};selected=[materials[p.regions[i].material] for i in np.unique(p.cell_region_indices[cells])]
    if type(solution) is PlanarBHSolution:
        slopes=[]
        for material in selected:
            ratios=[Fraction(h)/Fraction(b) for b,h in zip(material.b_t[1:],material.h_a_per_m[1:])]
            if any(value!=ratios[0] for value in ratios):raise ValueError('multipole disk B-H tables must be exactly linear H=nu B over every declared interval; a local tangent is insufficient')
            slopes.append(ratios[0])
        if any(value!=slopes[0] for value in slopes):raise ValueError('multipole disk intersects different linear B-H reluctivity values')
        with np.errstate(over='ignore',under='ignore',invalid='ignore'):permeability=np.divide(1.,np.float64(MU0)*float(slopes[0]))
        policy='B-H tables exactly linear over all declared points by rational comparison of input floats; one positive scalar reluctivity'
    else:
        for material in selected:
            if material.mu_r_principal[0]!=material.mu_r_principal[1] or any(v!=0. for v in material.remanent_b_local_t):raise ValueError('multipole disk recoil material must declare equal principal mu_r and exactly zero remanent B')
        permeability=selected[0].mu_r_principal[0]
        if any(material.mu_r_principal[0]!=permeability for material in selected):raise ValueError('multipole disk intersects different scalar recoil permeability values')
        policy='declared equal positive principal mu_r and exactly zero remanent B in every disk material'
    if not np.isfinite(permeability) or permeability<=0.:raise ValueError('multipole aperture permeability is unresolved in finite SI arithmetic')
    return float(permeability),dict(kind='isotropic_linear_nonremanent',checked_material_ids=[m.id for m in selected],policy=policy)


def _source_free_disk(solution,frame):
    mesh=solution.case.partition.mesh;p=solution.case.partition
    try:center_cells,_=solution._locator.locate(np.asarray([frame.center_xy_m]))
    except ValueError as exc:raise ValueError('multipole disk center is outside the magnetic domain') from exc
    with np.errstate(over='ignore',invalid='ignore',divide='ignore'):normalized=(mesh.points_xy_m-np.asarray(frame.center_xy_m))/frame.reference_radius_m
    if not np.isfinite(normalized).all():raise ValueError('multipole disk normalization exceeds finite SI geometry')
    edges=normalized[mesh.boundary_edges];distance=_segment_distance(edges[:,0],edges[:,1]);clearance=float(distance.min());guard=128*np.finfo(float).eps*max(1.,float(np.max(abs(normalized))))
    if clearance<=1.+guard:raise ValueError('closed multipole disk must be strictly inside the magnetic domain; reduce the radius or move the center')
    vertices=normalized[mesh.triangles];minimum=np.minimum.reduce([_segment_distance(vertices[:,i],vertices[:,j]) for i,j in ((0,1),(1,2),(2,0))]);intersects=minimum<=1.+guard;intersects[center_cells]=True;cells=np.flatnonzero(intersects)
    densities=np.array([solution.case.current_density_z_a_per_m2[v.id] for v in p.regions]);current=densities[p.cell_region_indices[cells]]
    if np.any(current!=0.):raise ValueError('multipole disk contains a declared current cell; circle samples alone do not establish a source-free aperture')
    if type(solution) is PlanarMagnetostaticSolution:
        permeability=p.mu_r[cells]
        if not np.all(permeability==permeability[0]):raise ValueError('multipole disk intersects different permeability values; homogeneous isotropic material is required')
        return dict(cell_indices=cells.tolist(),mu_r=float(permeability[0]),minimum_outer_boundary_distance_m=clearance*frame.reference_radius_m,
            policy='whole closed disk against original cells, not just the sampling circles; exact zero Jz and one positive scalar mu_r')
    permeability,model=_linear_material_aperture(solution,cells)
    return dict(cell_indices=cells.tolist(),mu_r=permeability,minimum_outer_boundary_distance_m=clearance*frame.reference_radius_m,
        policy='whole closed disk against original cells; exact zero Jz and a declared homogeneous isotropic linear nonremanent aperture; exterior material remains in the original FEM solve',linear_aperture_model=model)



def _trace(solution,frame,order,count,radius_fraction):
    angle=2*np.pi*np.arange(count)/count;global_angle=angle+frame.rotation_rad;radius=frame.reference_radius_m*radius_fraction
    points=np.asarray(frame.center_xy_m)+radius*np.column_stack((np.cos(global_angle),np.sin(global_angle)));probe=solution.probe_at(points)
    bx=np.asarray(probe['fields']['Bx_T']);by=np.asarray(probe['fields']['By_T']);co,si=np.cos(frame.rotation_rad),np.sin(frame.rotation_rad)
    local=(co*by-si*bx)+1j*(co*bx+si*by);spectrum=np.fft.fft(local)/count;coefficients=spectrum[:order]/radius_fraction**np.arange(order)
    if not np.isfinite(coefficients).all() or not np.isfinite(spectrum).all():raise ValueError('multipole Fourier coefficients exceed finite SI arithmetic')
    reconstructed=np.sum(coefficients[None,:]*(radius_fraction*np.exp(1j*angle[:,None]))**np.arange(order)[None,:],axis=1)
    rms=float(np.linalg.norm(local)/np.sqrt(count));remainder=float(np.linalg.norm(local-reconstructed)/np.sqrt(count));frequencies=np.fft.fftfreq(count)
    return coefficients,dict(sample_count=count,radius_m=radius,radius_fraction=radius_fraction,points_xy_m=points.tolist(),cell_indices=probe['cell_indices'],b_xy_t=np.column_stack((bx,by)).tolist(),
        normal_t=coefficients.real.tolist(),skew_t=coefficients.imag.tolist(),field_rms_t=rms,truncated_field_rms_error_t=remainder,
        truncated_field_relative_error=remainder/rms if rms else 0.,negative_harmonic_rms_t=float(np.linalg.norm(spectrum[frequencies<0.])),
        discarded_positive_harmonic_rms_t=float(np.linalg.norm(spectrum[(frequencies>=order/count)&(frequencies>0.)])),
        interpretation='original one-sided FEM B; Fourier negative/high-order content, angular aliasing, and truncated field remainder are diagnostics, not a continuum error bound')


def extract_planar_magnetic_multipoles(solution,frame,maximum_order=8,angular_samples=128):
    solvers={PlanarMagnetostaticSolution:solve_planar_magnetostatic,PlanarBHSolution:solve_planar_bh,PlanarRecoilSolution:solve_planar_recoil}
    if type(solution) not in solvers:raise ValueError('multipole extraction requires an explicit planar linear scalar, B-H or recoil FEM solution')
    extended=type(solution) is not PlanarMagnetostaticSolution
    if type(frame) is not PlanarMagneticMultipoleFrame:raise ValueError('explicit PlanarMagneticMultipoleFrame required')
    integer(maximum_order,'maximum multipole order');integer(angular_samples,'multipole angular_samples')
    if not 1<=maximum_order<=32 or not 4*maximum_order<=angular_samples<=8192:raise ValueError('multipole extraction requires order 1..32 and 4*order<=angular_samples<=8192; an additional 2N comparison is retained')
    # Recompute the actual FEM source. User-edited coefficients do not become
    # a verified multipole result merely by preserving an old residual value.
    case=solution.case.to_dict();fresh=solvers[type(solution)](solution.case)
    for name in ('az_relative_to_reference_wb_per_m','az_wb_per_m'):
        if not np.array_equal(getattr(solution,name),getattr(fresh,name)):raise ValueError('multipole source coefficients disagree with actual planar FEM replay')
    if solution.reference_az_wb_per_m!=fresh.reference_az_wb_per_m or solution.case.to_dict()!=case:raise ValueError('multipole source Case or Az reference changed during verification')
    disk=_source_free_disk(fresh,frame);traces=[];coefficients=[]
    for fraction,count in ((1.,angular_samples),(1.,2*angular_samples),(.75,angular_samples),(.75,2*angular_samples)):
        values,trace=_trace(fresh,frame,maximum_order,count,fraction);coefficients.append(values);traces.append(trace)
    def difference(a,b):
        norm=max(float(np.linalg.norm(a)),float(np.linalg.norm(b)));return float(np.linalg.norm(a-b)/norm) if norm else 0.
    source_hash=hashlib.sha256(json.dumps(case,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest();field_hash=hashlib.sha256(fresh.az_relative_to_reference_wb_per_m.tobytes()).hexdigest()
    provenance='Original verified '+(case['physics']+' planar FEM' if extended else 'linear planar FEM')+'; Case SHA256 '+source_hash+'; relative Az float64 SHA256 '+field_hash
    series=PlanarMagneticMultipoleSeries(frame,coefficients[0].real,coefficients[0].imag,provenance)
    result=dict(format='superfish_ng_planar_magnetic_multipole_extraction',schema_version=1,series=series.to_dict(),source_case_sha256=source_hash,source_relative_az_sha256=field_hash,
        element_order=fresh.case.element_order,source_free_disk=disk,maximum_order=maximum_order,angular_samples=angular_samples,traces=traces,
        angular_coefficient_relative_difference=difference(coefficients[0],coefficients[1]),inner_angular_coefficient_relative_difference=difference(coefficients[2],coefficients[3]),
        radial_coefficient_relative_difference=difference(coefficients[1],coefficients[3]),
        interpretation='primary N-sample spatial harmonics of the original FEM B in a declared homogeneous source-free disk; 2N and smaller-radius comparisons diagnose angular/field differences; no fitted correction, omitted-order bound, force, torque or longitudinal integration')
    if extended:
        result.update(schema_version=2,source_physics=case['physics'],interpretation='primary N-sample spatial harmonics of the original verified planar material FEM B; whole disk is declared homogeneous isotropic linear and nonremanent with Jz=0; nonlinear or anisotropic/remanent exterior material stays in the source solve; angular/radial diagnostics are not continuum error bounds; no force, torque or longitudinal integral')
    return result

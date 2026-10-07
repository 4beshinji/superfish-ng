# SPDX-License-Identifier: Apache-2.0
"""Original straight vacuum Hphi sequences with independent E/H identity and RF."""
from dataclasses import dataclass
import numpy as np
from .config import integer, keys
from .hphi_convergence import HphiConvergence, _relative_difference
from .hphi_tracking import HphiTrackingRequest, track_hphi_modes
from .hphi_field_overlap import _verified_solution, _declared_mesh
from .hphi_native import hphi_result
from .meridional_overlap import meridional_overlay
from .fem import triangle_quadrature
from .constants import TAU


@dataclass(frozen=True)
class VacuumHphiConvergence:
    convergence: HphiConvergence
    tracking_requests: tuple
    mode_id: str = 'mode-1'
    max_sample_points: int = 2000000

    def __post_init__(self):
        if type(self.convergence) is not HphiConvergence:
            raise ValueError('straight vacuum RF convergence requires HphiConvergence; material and curved types need dedicated adapters')
        convergence=HphiConvergence.from_dict(self.convergence.to_dict())
        if len(convergence.projects)!=3:
            raise ValueError('vacuum RF convergence requires exactly three explicit original Projects')
        integer(self.max_sample_points,'max_sample_points',1)
        if type(self.tracking_requests) not in (tuple,list) or len(self.tracking_requests)!=2:
            raise ValueError('vacuum RF convergence requires two adjacent E/H tracking declarations')
        if any(type(q) is not HphiTrackingRequest for q in self.tracking_requests):
            raise ValueError('expected HphiTrackingRequest for each adjacent pair')
        requests=tuple(HphiTrackingRequest.from_dict(q.to_dict()) for q in self.tracking_requests)
        initial=requests[0].previous_mode_ids
        if initial is None or type(self.mode_id) is not str or self.mode_id not in initial:
            raise ValueError('vacuum RF mode_id must name one initial individual tracked mode')
        if convergence.mode_ranks!=(initial.index(self.mode_id)+1,):
            raise ValueError('vacuum RF convergence mode_ranks must select the initial rank of mode_id only; later ranks follow actual E/H IDs')
        thresholds=convergence.thresholds
        for index,request in enumerate(requests):
            if request.geometry_mapping is not None:
                raise ValueError('fixed-domain vacuum RF convergence does not permit a geometry transport map')
            if (request.previous_mode_ids is None or set(request.previous_mode_ids)!=set(initial) or
                request.previous_mode_count!=len(initial) or request.current_mode_count!=len(initial)):
                raise ValueError('vacuum RF tracking must preserve the full initial individual ID set')
            if any(len(initial)>=p.case.modes for p in convergence.projects[index:index+2]):
                raise ValueError('vacuum RF convergence requires a computed upper guard at every original level')
            controls=request.controls
            if (controls.minimum_overlap<thresholds.minimum_overlap or
                controls.minimum_assignment_margin<thresholds.overlap_margin or
                controls.relative_cluster_gap<thresholds.spectral_gap_relative):
                raise ValueError('vacuum RF identity controls cannot weaken convergence overlap, margin or gap thresholds')
            if (controls.max_overlay_triangles>convergence.max_overlay_triangles or
                controls.max_candidate_tests>convergence.max_candidate_tests or
                controls.max_gram_modes>convergence.max_gram_modes):
                raise ValueError('vacuum RF tracking limits cannot exceed the declared convergence budgets')
        object.__setattr__(self,'convergence',convergence)
        object.__setattr__(self,'tracking_requests',requests)

    def to_dict(self):
        return dict(format='superfish_ng_vacuum_hphi_convergence',convergence_version=1,
            convergence=self.convergence.to_dict(),tracking_requests=[q.to_dict() for q in self.tracking_requests],
            mode_id=self.mode_id,max_sample_points=self.max_sample_points)

    @classmethod
    def from_dict(cls,data):
        names=['format','convergence_version','convergence','tracking_requests','mode_id','max_sample_points']
        keys(data,names,names,'vacuum RF convergence')
        if data['format']!='superfish_ng_vacuum_hphi_convergence' or type(data['convergence_version']) is not int or data['convergence_version']!=1:
            raise ValueError('expected vacuum Hphi convergence version 1')
        if type(data['tracking_requests']) is not list:
            raise ValueError('vacuum RF tracking_requests must be a JSON array')
        return cls(HphiConvergence.from_dict(data['convergence']),
            [HphiTrackingRequest.from_dict(q) for q in data['tracking_requests']],data['mode_id'],data['max_sample_points'])


def _field_changes(previous,current,declaration,old_mode,new_mode,phase,order,max_samples):
    controls=declaration.controls
    overlay=meridional_overlay(_declared_mesh(previous),_declared_mesh(current),
        max_candidate_tests=controls.max_candidate_tests,max_overlay_triangles=controls.max_overlay_triangles)
    if len(overlay.determinants)*order**2>max_samples:
        raise ValueError('vacuum RF direct field differences exceed max_sample_points')
    errors=np.zeros(2);norms=np.zeros(2)
    names=(('Er_quadrature_V_per_m','Ez_quadrature_V_per_m'),('Hphi_real_A_per_m',))
    for bary,weight in triangle_quadrature(order):
        a=previous.fields_in_cells(overlay.previous_cells,np.einsum('i,tij->tj',bary,overlay.previous_vertex_barycentric),old_mode)
        b=current.fields_in_cells(overlay.current_cells,np.einsum('i,tij->tj',bary,overlay.current_vertex_barycentric),new_mode)
        measure=TAU*(overlay.vertices_rz_m[:,:,0]@bary)*weight*overlay.determinants
        for i,components in enumerate(names):
            errors[i]+=sum(float(measure@(phase*a[name]-b[name])**2) for name in components)
            norms[i]+=sum(float(measure@b[name]**2) for name in components)
    if not np.isfinite([*errors,*norms]).all() or np.any(norms<=0):
        raise ValueError('vacuum RF direct field differences require finite positive norms')
    return np.sqrt(errors/norms)


def _wall_losses(solution,rf):
    mesh=_declared_mesh(solution)
    if 'wall_h2_integral_a2_by_segment' in rf:
        integrals=np.asarray(rf['wall_h2_integral_a2_by_segment'])
    else:
        surfaces=rf['wall_h2_integral_a2_by_surface']
        integrals=np.array([surfaces[k] for k in ('z_min_end_plate','outer_conductor','z_max_end_plate','inner_conductor')])
    if len(integrals)!=len(mesh.surface_area_m2_by_segment):
        raise ValueError('vacuum RF wall integrals do not cover every original PEC segment')
    losses=integrals*rf['surface_resistance_ohm']/2
    components=[];offset=0
    for contour in (mesh.outer_rz_m,*mesh.holes_rz_m):
        components.append(float(losses[offset:offset+len(contour)].sum()));offset+=len(contour)
    if not np.isclose(losses.sum(),rf['wall_loss_w'],rtol=1e-12,atol=0.):
        raise ValueError('vacuum RF ordered walls do not reproduce the complete wall loss')
    return losses,np.asarray(components)


def _rf_changes(a,b,left_walls,right_walls,phase):
    names=('stored_energy_j','electric_energy_j','magnetic_energy_j','wall_loss_w',
           'surface_resistance_ohm','q0','geometry_factor_ohm','r_over_q_accelerator_ohm','r_over_q_circuit_ohm')
    changes={}
    for name in names:
        x,y=a[name],b[name]
        if (x is None)!=(y is None):raise ValueError('vacuum RF quantity availability changes across a fixed domain')
        if x is not None:changes['rf/'+name]=_relative_difference(x,y)
    for family,left,right in zip(('wall_segment','wall_component'),left_walls,right_walls):
        if len(left)!=len(right):raise ValueError('vacuum RF ordered PEC wall components differ')
        for i,(x,y) in enumerate(zip(left,right)):changes[family+'/'+str(i+1)]=_relative_difference(x,y)
    va,vb=a['vacc_v'],b['vacc_v']
    if (va is None)!=(vb is None):raise ValueError('vacuum RF axis voltage availability changes')
    if va is not None:
        changes['axis_voltage_relative']=_relative_difference(phase*complex(va['real'],va['imag']),complex(vb['real'],vb['imag']))
    return changes


def compare_vacuum_hphi_convergence(request,solutions):
    """No same-rank assumption: use each original level's actual verified ID rank."""
    if type(request) is not VacuumHphiConvergence:raise ValueError('expected VacuumHphiConvergence')
    request=VacuumHphiConvergence.from_dict(request.to_dict())
    if type(solutions) not in (tuple,list) or len(solutions)!=3:
        raise ValueError('vacuum RF convergence requires every declared original FEM')
    verified=[]
    for project,solution in zip(request.convergence.projects,solutions):
        if not hasattr(solution,'case') or solution.case.to_dict()!=project.case.to_dict():
            raise ValueError('vacuum RF solution differs from its declared original level')
        verified.append(_verified_solution(solution))
    native=[hphi_result(s)['modes'] for s in verified]
    ids=list(request.tracking_requests[0].previous_mode_ids);ranks=[ids.index(request.mode_id)+1]
    rf=[native[0][ranks[0]-1]];walls=[_wall_losses(verified[0],rf[0])];pairs=[];stop=None
    for index,declaration in enumerate(request.tracking_requests):
        if list(declaration.previous_mode_ids)!=ids:
            raise ValueError('vacuum RF adjacent declaration replaces or reorders inherited IDs')
        try:tracking=track_hphi_modes(verified[index],verified[index+1],declaration)
        except ValueError as error:
            tracking=dict(status='UNVERIFIED',individual_ids_complete=False,current_mode_ids=None,verification_reasons=[str(error)])
        if tracking['status']!='PASS' or not tracking['individual_ids_complete']:
            pairs.append(dict(tracking=tracking,changes=None,field_difference_integration_orders=None))
            stop='individual E/H identity or finite upper guard is unverified';break
        current_ids=tracking['current_mode_ids'];old_mode=ids.index(request.mode_id);new_mode=current_ids.index(request.mode_id)
        match=next(m for m in tracking['matches'] if m['previous_ids']==[request.mode_id] and m['dimension']==1)
        phase=match['previous_phase_multiplier']
        if phase not in (-1,1):raise ValueError('vacuum RF individual match lacks one common E/H phase')
        order=tracking['physical_mapping']['integration']['integration_orders'][-1]
        try:
            low,high=(_field_changes(verified[index],verified[index+1],declaration,old_mode,new_mode,phase,n,request.max_sample_points) for n in (order,order+2))
            if np.max(abs(low-high))>1e-10:raise ValueError('vacuum RF direct field quadrature is unresolved')
            current=native[index+1][new_mode];current_walls=_wall_losses(verified[index+1],current)
            changes=_rf_changes(rf[-1],current,walls[-1],current_walls,phase)
            changes.update(frequency_relative=_relative_difference(verified[index].frequencies_hz[old_mode],verified[index+1].frequencies_hz[new_mode]),
                electric_field_relative=float(high[0]),magnetic_field_relative=float(high[1]))
        except ValueError as error:
            pairs.append(dict(tracking=tracking,changes=None,field_difference_integration_orders=[order,order+2],reason=str(error)))
            stop=str(error);break
        pairs.append(dict(tracking=tracking,changes=changes,field_difference_integration_orders=[order,order+2],previous_phase_multiplier=phase))
        rf.append(current);walls.append(current_walls);ranks.append(new_mode+1);ids=list(current_ids)
    checks={}
    if len(pairs)==2 and all(p['changes'] is not None for p in pairs):
        previous,last=[p['changes'] for p in pairs]
        if previous.keys()!=last.keys():raise ValueError('vacuum RF convergence required quantities differ')
        for name,value in last.items():
            thresholds=request.convergence.thresholds
            limit=(getattr(thresholds,name) if name in ('frequency_relative','electric_field_relative','magnetic_field_relative','axis_voltage_relative') else thresholds.rf_relative)
            old=previous[name];stable=value<=old+max(1e-12,old*1e-8)
            checks[name]=dict(passed=bool(stable and value<=limit),previous=old,last=value,threshold=limit,nonincreasing=bool(stable))
    passed=bool(checks) and all(c['passed'] for c in checks.values())
    return dict(format='superfish_ng_vacuum_hphi_convergence_result',result_version=1,request=request.to_dict(),
        status='PASS' if passed else 'UNVERIFIED',mode_id=request.mode_id,mode_ranks=ranks,
        individual_ids_complete=len(ranks)==3,comparisons=pairs,checks=checks,selected_rf=rf,
        wall_loss_w_by_segment=[w[0].tolist() for w in walls],wall_loss_w_by_component=[w[1].tolist() for w in walls],
        stop_reason=stop,field_measure='2*pi*r dr dz; original peak E/H; direct finer-norm differences with one common coefficient phase',
        interpretation='two consecutive differences on three original full-domain vacuum FEMs; finite sampled E/H identity and upper guards, not a continuum error bound',surface_peak_accuracy='not_checked')

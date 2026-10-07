# SPDX-License-Identifier: Apache-2.0
"""Three original material FEMs: finite E/H identity, direct fields and all RF."""
from dataclasses import dataclass, field
import numpy as np
from .config import keys
from .hphi_project import HphiProject
from .hphi_convergence import HphiConvergenceThresholds, _relative_difference
from .material_hphi import MaterialHphiCase
from .material_hphi_tracking import MaterialHphiTrackingRequest, track_material_hphi_modes
from .material_hphi_field_overlap import verified_material_hphi_solution
from .material_hphi_comparison import material_hphi_overlay
from .material_hphi_rf import material_hphi_quantities
from .fem import triangle_quadrature
from .constants import TAU, EPS0, MU0


@dataclass(frozen=True)
class MaterialHphiConvergence:
    projects: tuple
    tracking_requests: tuple
    mode_id: str = 'mode-1'
    thresholds: HphiConvergenceThresholds = field(default_factory=HphiConvergenceThresholds)

    def __post_init__(self):
        if type(self.projects) not in (list, tuple) or len(self.projects) != 3:
            raise ValueError('material RF convergence requires exactly three explicit HphiProjects')
        if any(type(p) is not HphiProject or type(p.case) is not MaterialHphiCase for p in self.projects):
            raise ValueError('material RF convergence requires dedicated material HphiProjects')
        projects = tuple(HphiProject.from_dict(p.to_dict()) for p in self.projects)
        if type(self.tracking_requests) not in (list, tuple) or len(self.tracking_requests) != 2:
            raise ValueError('material RF convergence requires two explicit original E/H tracking declarations')
        if any(type(q) is not MaterialHphiTrackingRequest for q in self.tracking_requests):
            raise ValueError('expected MaterialHphiTrackingRequest for each adjacent pair')
        requests = tuple(MaterialHphiTrackingRequest.from_dict(q.to_dict()) for q in self.tracking_requests)
        if type(self.thresholds) is not HphiConvergenceThresholds:
            raise ValueError('expected HphiConvergenceThresholds')
        thresholds = HphiConvergenceThresholds.from_dict(self.thresholds.to_dict())
        initial_ids = requests[0].previous_mode_ids
        if initial_ids is None or type(self.mode_id) is not str or self.mode_id not in initial_ids:
            raise ValueError('material RF mode_id must name one distinct initial tracked mode')
        reference = None; previous = None
        for project in projects:
            case = project.case; partition = case.partition; mesh = partition.mesh
            physical = case.to_dict()
            physical.pop('partition'); physical.pop('name')
            physical.update(outer=mesh.outer_rz_m.tolist(), holes=[h.tolist() for h in mesh.holes_rz_m],
                materials={m.id:(m.epsilon_r, m.mu_r) for m in partition.materials},
                regions={r.id:r.material for r in partition.regions})
            if reference is None: reference = physical
            elif reference != physical:
                raise ValueError('material RF convergence requires one fixed full domain, materials, region IDs, P1/P2, quadrature, normalization, wall sigma and axis path')
            vertices = mesh.points_rz_m[mesh.triangles]
            maximum = float(np.max(np.linalg.norm(vertices-np.roll(vertices,-1,axis=1),axis=2)))
            count = len(mesh.triangles)
            if previous is not None and not (count > previous[0] and maximum < previous[1]):
                raise ValueError('each material RF mesh must have more triangles and smaller maximum edge length')
            previous = count, maximum
        for index, request in enumerate(requests):
            a,b = projects[index].case, projects[index+1].case
            if (request.comparison.mapping != 'same_domain' or
                request.comparison.previous_partition.to_dict() != a.partition.to_dict() or
                request.comparison.current_partition.to_dict() != b.partition.to_dict()):
                raise ValueError('material RF tracking must compare the complete adjacent original partitions on the same domain')
            if any(old != new for name in ('material_pairs', 'region_pairs')
                   for old, new in getattr(request.comparison, name)):
                raise ValueError('material RF convergence requires identity correspondence for fixed material and region IDs')
            if (request.previous_mode_ids is None or set(request.previous_mode_ids) != set(initial_ids) or
                request.previous_mode_count != len(initial_ids) or request.current_mode_count != len(initial_ids)):
                raise ValueError('material RF tracking must preserve the full initial individual ID set')
            if request.previous_mode_count >= a.modes or request.current_mode_count >= b.modes:
                raise ValueError('material RF convergence requires a computed upper guard mode at every level')
            for side,case in [('previous',a),('current',b)]:
                if getattr(request,side+'_resolution').previous_partition.to_dict() != case.partition.to_dict():
                    raise ValueError('material RF finite spectral declaration differs from its original level partition')
            controls = request.controls
            if (controls.minimum_overlap < thresholds.minimum_overlap or
                controls.minimum_assignment_margin < thresholds.overlap_margin or
                controls.relative_cluster_gap < thresholds.spectral_gap_relative):
                raise ValueError('material RF identity controls must preserve the convergence overlap, margin and gap thresholds')
        object.__setattr__(self, 'projects', projects)
        object.__setattr__(self, 'tracking_requests', requests)
        object.__setattr__(self, 'thresholds', thresholds)

    def to_dict(self):
        return dict(format='superfish_ng_material_hphi_convergence', convergence_version=1,
            projects=[p.to_dict() for p in self.projects], tracking_requests=[q.to_dict() for q in self.tracking_requests],
            mode_id=self.mode_id, thresholds=self.thresholds.to_dict())

    @classmethod
    def from_dict(cls, data):
        names=['format','convergence_version','projects','tracking_requests','mode_id','thresholds']
        keys(data,names,names,'material RF convergence')
        if data['format']!='superfish_ng_material_hphi_convergence' or type(data['convergence_version']) is not int or data['convergence_version']!=1:
            raise ValueError('expected material Hphi convergence version 1')
        if type(data['projects']) is not list or type(data['tracking_requests']) is not list:
            raise ValueError('material RF projects and tracking_requests must be JSON arrays')
        return cls([HphiProject.from_dict(p) for p in data['projects']],
            [MaterialHphiTrackingRequest.from_dict(q) for q in data['tracking_requests']], data['mode_id'],
            HphiConvergenceThresholds.from_dict(data['thresholds']))


def _field_changes(previous, current, declaration, old_mode, new_mode, phase, order):
    controls = declaration.controls
    owned = material_hphi_overlay(declaration.comparison,
        max_candidate_tests=controls.max_candidate_tests, max_overlay_triangles=controls.max_overlay_triangles,
        max_interface_tests=declaration.max_interface_tests, max_interface_pieces=declaration.max_interface_pieces)
    overlay = owned.overlay
    if len(overlay.determinants)*order**2 > declaration.max_sample_points:
        raise ValueError('material RF direct field differences exceed max_sample_points')
    errors = np.zeros(2); norms = np.zeros(2)
    names = (('Er_quadrature_V_per_m','Ez_quadrature_V_per_m'),('Hphi_real_A_per_m',))
    a,b=previous.case.partition,current.case.partition
    densities=(EPS0*b.epsilon_r[overlay.current_cells], MU0*b.mu_r[overlay.current_cells])
    if (not np.array_equal(a.epsilon_r[overlay.previous_cells], b.epsilon_r[overlay.current_cells]) or
        not np.array_equal(a.mu_r[overlay.previous_cells], b.mu_r[overlay.current_cells])):
        raise ValueError('material RF direct differences require exactly fixed original material densities')
    for bary,weight in triangle_quadrature(order):
        left = previous.fields_in_cells(overlay.previous_cells, np.einsum('i,tij->tj',bary,overlay.previous_vertex_barycentric),old_mode)
        right = current.fields_in_cells(overlay.current_cells, np.einsum('i,tij->tj',bary,overlay.current_vertex_barycentric),new_mode)
        measure=TAU*(overlay.vertices_rz_m[:,:,0]@bary)*weight*overlay.determinants
        for i,(components,density) in enumerate(zip(names,densities)):
            errors[i]+=sum(float((measure*density)@(phase*left[name]-right[name])**2) for name in components)
            norms[i]+=sum(float((measure*density)@right[name]**2) for name in components)
    if not np.isfinite([*errors,*norms]).all() or np.any(norms<=0):
        raise ValueError('material RF direct field differences require positive finite energy norms')
    return np.sqrt(errors/norms)


def _rf_changes(left, right, phase):
    names=['stored_energy_j','electric_energy_j','magnetic_energy_j','wall_loss_w',
           'surface_resistance_ohm','q0','geometry_factor_ohm','r_over_q_accelerator_ohm','r_over_q_circuit_ohm']
    changes={}
    for name in names:
        a,b=left[name],right[name]
        if (a is None)!=(b is None): raise ValueError('material RF quantity availability differs between fixed-domain levels')
        if a is not None: changes['rf/'+name]=_relative_difference(a,b)
    for family in ['wall_h2_integral_a2_by_segment','wall_h2_integral_a2_by_component']:
        a,b=left[family],right[family]
        if len(a)!=len(b):raise ValueError('material RF ordered PEC wall declaration differs')
        for i,(x,y) in enumerate(zip(a,b)):
            changes[family+'/'+str(i+1)]=_relative_difference(x,y)
    a={r['id']:r for r in left['regions']};b={r['id']:r for r in right['regions']}
    if a.keys()!=b.keys():raise ValueError('material RF region IDs differ')
    for region in a:
        for name in ['electric_energy_j','magnetic_energy_j','stored_energy_j','adjacent_wall_loss_w']:
            changes['region/'+region+'/'+name]=_relative_difference(a[region][name],b[region][name])
    va,vb=left['vacc_v'],right['vacc_v']
    if (va is None)!=(vb is None): raise ValueError('material RF axis voltage availability differs')
    if va is not None:
        changes['axis_voltage_relative']=_relative_difference(phase*complex(va['real'],va['imag']),complex(vb['real'],vb['imag']))
    return changes


def compare_material_hphi_convergence(request, solutions):
    """Verify finite individual E/H correspondence before quantity convergence."""
    if type(request) is not MaterialHphiConvergence:raise ValueError('expected MaterialHphiConvergence')
    request=MaterialHphiConvergence.from_dict(request.to_dict())
    if type(solutions) not in (list,tuple) or len(solutions)!=3:
        raise ValueError('material RF convergence requires every declared original FEM')
    verified=[]
    for project,solution in zip(request.projects,solutions):
        if not hasattr(solution,'case') or solution.case.to_dict()!=project.case.to_dict():
            raise ValueError('material RF solution differs from its declared level Project')
        verified.append(verified_material_hphi_solution(solution))
    ids=list(request.tracking_requests[0].previous_mode_ids)
    ranks=[ids.index(request.mode_id)+1];comparisons=[];rf=[material_hphi_quantities(verified[0],ranks[0]-1)]
    stop=None
    for index,declaration in enumerate(request.tracking_requests):
        if list(declaration.previous_mode_ids)!=ids:
            raise ValueError('material RF adjacent tracking replaces or reorders inherited individual IDs')
        try:
            tracking=track_material_hphi_modes(verified[index],verified[index+1],declaration)
        except ValueError as error:
            tracking=dict(status='UNVERIFIED',individual_ids_complete=False,current_mode_ids=None,verification_reasons=[str(error)])
        if tracking['status']!='PASS' or not tracking['individual_ids_complete']:
            comparisons.append(dict(tracking=tracking,changes=None,field_difference_integration_orders=None))
            stop='individual E/H identity or finite spectral guard is unverified';break
        next_ids=tracking['current_mode_ids'];old_mode=ids.index(request.mode_id);new_mode=next_ids.index(request.mode_id)
        match=next(m for m in tracking['matches'] if m['previous_ids']==[request.mode_id] and m['dimension']==1)
        phase=match['previous_phase_multiplier']
        if phase not in (-1,1):raise ValueError('material RF individual correspondence lacks a common E/H coefficient phase')
        order=tracking['physical_mapping']['integration']['integration_orders'][-1]
        try:
            low,high=(_field_changes(verified[index],verified[index+1],declaration,old_mode,new_mode,phase,n) for n in (order,order+2))
            if np.max(abs(low-high))>1e-10:raise ValueError('material RF direct field difference quadrature is unresolved')
            current=material_hphi_quantities(verified[index+1],new_mode)
            changes=_rf_changes(rf[-1],current,phase)
            changes.update(frequency_relative=_relative_difference(verified[index].frequencies_hz[old_mode],verified[index+1].frequencies_hz[new_mode]),
                electric_field_relative=float(high[0]),magnetic_field_relative=float(high[1]))
        except ValueError as error:
            comparisons.append(dict(tracking=tracking,changes=None,field_difference_integration_orders=[order,order+2],reason=str(error)))
            stop=str(error);break
        comparisons.append(dict(tracking=tracking,changes=changes,field_difference_integration_orders=[order,order+2],previous_phase_multiplier=phase))
        rf.append(current);ranks.append(new_mode+1);ids=list(next_ids)
    checks={}
    if len(comparisons)==2 and all(p['changes'] is not None for p in comparisons):
        previous,last=[p['changes'] for p in comparisons]
        if previous.keys()!=last.keys():raise ValueError('material RF convergence required quantity sets differ')
        for name,value in last.items():
            limit=(getattr(request.thresholds,name) if name in ('frequency_relative','electric_field_relative','magnetic_field_relative','axis_voltage_relative') else request.thresholds.rf_relative)
            old=previous[name];stable=value<=old+max(1e-12,old*1e-8)
            checks[name]=dict(passed=bool(stable and value<=limit),previous=old,last=value,threshold=limit,nonincreasing=bool(stable))
    passed=bool(checks) and all(c['passed'] for c in checks.values())
    return dict(format='superfish_ng_material_hphi_convergence_result',result_version=1,request=request.to_dict(),
        status='PASS' if passed else 'UNVERIFIED',mode_id=request.mode_id,mode_ranks=ranks,
        individual_ids_complete=len(ranks)==3,comparisons=comparisons,checks=checks,selected_rf=rf,
        stop_reason=stop,interpretation='two consecutive differences on three original material FEMs; finite sampled E/H identity and spectral guards, not a continuum error bound',
        field_measure='2*pi*r dr dz; original peak E/H weighted by epsilon0*epsilon_r and mu0*mu_r; one common coefficient phase',
        surface_peak_accuracy='not_checked')

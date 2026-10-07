# SPDX-License-Identifier: Apache-2.0
"""RF acceptance on three original complete P2 domains with actual E/H IDs."""
from dataclasses import dataclass, replace
from types import SimpleNamespace
import numpy as np
from .config import keys
from .curved_hphi_convergence import CurvedHphiConvergence, _level_rf
from .curved_hphi_tracking import CurvedHphiTrackingRequest, track_curved_hphi_modes, _charts
from .curved_hphi_field_overlap import verified_curved_hphi_solution
from .curved_hphi_comparison import build_curved_hphi_comparison
from .hphi_convergence import _relative_difference
from .fem import triangle_quadrature
from .constants import TAU


@dataclass(frozen=True)
class CurvedHphiRFConvergence:
    convergence: CurvedHphiConvergence
    tracking_requests: tuple
    mode_id: str = 'mode-1'

    def __post_init__(self):
        if type(self.convergence) is not CurvedHphiConvergence:
            raise ValueError('curved RF convergence requires CurvedHphiConvergence with full P2 reference and native charts')
        convergence=CurvedHphiConvergence.from_dict(self.convergence.to_dict())
        if len(convergence.projects)!=3:
            raise ValueError('curved RF convergence requires exactly three explicit original Projects')
        if type(self.tracking_requests) not in (tuple,list) or len(self.tracking_requests)!=2:
            raise ValueError('curved RF convergence requires two adjacent original E/H tracking declarations')
        if any(type(q) is not CurvedHphiTrackingRequest for q in self.tracking_requests):
            raise ValueError('curved RF convergence requires CurvedHphiTrackingRequest declarations')
        requests=tuple(CurvedHphiTrackingRequest.from_dict(q.to_dict()) for q in self.tracking_requests)
        initial=requests[0].previous_mode_ids
        if initial is None or type(self.mode_id) is not str or self.mode_id not in initial:
            raise ValueError('curved RF mode_id must name one initial individual tracked mode')
        if convergence.mode_ranks!=(initial.index(self.mode_id)+1,):
            raise ValueError('curved RF mode_ranks must select the initial rank of mode_id only; later ranks follow actual E/H IDs')
        thresholds=convergence.thresholds;reference=convergence.reference_geometry.to_dict()
        for index,request in enumerate(requests):
            if (request.domain.mapping!='same_vacuum' or request.domain.previous.to_dict()!=reference or
                request.domain.current.to_dict()!=reference):
                raise ValueError('curved RF tracking must use the same complete fixed quadratic reference domain')
            if (request.previous_cells!=_charts(convergence.native_cells[index],convergence.reference_geometry) or
                request.current_cells!=_charts(convergence.native_cells[index+1],convergence.reference_geometry)):
                raise ValueError('curved RF tracking must retain each original native chart declaration')
            if (request.previous_mode_ids is None or set(request.previous_mode_ids)!=set(initial) or
                request.previous_mode_count!=len(initial) or request.current_mode_count!=len(initial)):
                raise ValueError('curved RF tracking must preserve the full initial individual ID set')
            if any(len(initial)>=p.case.modes for p in convergence.projects[index:index+2]):
                raise ValueError('curved RF convergence requires a computed upper guard at every original level')
            controls=request.controls
            if (controls.minimum_overlap<thresholds.minimum_overlap or
                controls.minimum_assignment_margin<thresholds.overlap_margin or
                controls.relative_cluster_gap<thresholds.spectral_gap_relative):
                raise ValueError('curved RF identity controls cannot weaken convergence overlap, margin or gap thresholds')
            if (controls.max_overlay_triangles>convergence.max_overlay_triangles or
                controls.max_candidate_tests>convergence.max_candidate_tests or
                controls.max_gram_modes>convergence.max_gram_modes or request.max_sample_points>convergence.max_sample_points):
                raise ValueError('curved RF tracking limits cannot exceed declared convergence budgets')
        object.__setattr__(self,'convergence',convergence);object.__setattr__(self,'tracking_requests',requests)

    def to_dict(self):
        return dict(format='superfish_ng_curved_hphi_rf_convergence',convergence_version=1,
            convergence=self.convergence.to_dict(),tracking_requests=[q.to_dict() for q in self.tracking_requests],mode_id=self.mode_id)

    @classmethod
    def from_dict(cls,data):
        names=['format','convergence_version','convergence','tracking_requests','mode_id']
        keys(data,names,names,'curved RF convergence')
        if data['format']!='superfish_ng_curved_hphi_rf_convergence' or type(data['convergence_version']) is not int or data['convergence_version']!=1:
            raise ValueError('expected curved Hphi RF convergence version 1')
        if type(data['tracking_requests']) is not list:raise ValueError('curved RF tracking_requests must be a JSON array')
        return cls(CurvedHphiConvergence.from_dict(data['convergence']),
            [CurvedHphiTrackingRequest.from_dict(q) for q in data['tracking_requests']],data['mode_id'])


def _field_changes(previous,current,overlay,old_mode,new_mode,phase,order,max_samples):
    rule=list(triangle_quadrature(order));q=np.array([p for p,w in rule]);w=np.array([w for p,w in rule])
    if len(rule)*len(overlay.triangles)>max_samples:raise ValueError('curved RF direct field differences exceed max_sample_points')
    errors=np.zeros(2);norms=np.zeros(2)
    for start in range(0,len(overlay.triangles),64):
        part=replace(overlay,triangles=overlay.triangles[start:start+64]);samples=[]
        for side,(solution,mode) in enumerate(((previous,old_mode),(current,new_mode))):
            rows=part.evaluate(side,q)
            cells=np.concatenate([np.full(len(q),row['native_cell'],dtype=int) for row in rows])
            bary=np.concatenate([row['native_barycentric'] for row in rows])
            samples.append(solution.fields_in_cells(cells,bary,mode))
        weights=np.concatenate([TAU*row['points_rz_m'][:,0]*row['determinant_m2']*w for row in rows])
        for family,names in enumerate((('Er_quadrature_V_per_m','Ez_quadrature_V_per_m'),('Hphi_real_A_per_m',))):
            errors[family]+=sum(weights@(phase*samples[0][name]-samples[1][name])**2 for name in names)
            norms[family]+=sum(weights@samples[1][name]**2 for name in names)
    if not np.isfinite([*errors,*norms]).all() or np.any(norms<=0):raise ValueError('curved RF direct field differences require finite positive norms')
    return np.sqrt(errors/norms)


def _selected_rf(convergence,solution,charts,rank):
    # The existing wall integrator needs only this already validated reference
    # and the actual selected rank. Do not revalidate a same-rank declaration.
    declaration=SimpleNamespace(reference_geometry=convergence.reference_geometry,mode_ranks=(rank,))
    return _level_rf(declaration,solution,charts)[rank]


def _rf_changes(a,b,left_walls,right_walls,phase):
    names=('stored_energy_j','electric_energy_j','magnetic_energy_j','wall_loss_w',
           'surface_resistance_ohm','q0','geometry_factor_ohm','r_over_q_accelerator_ohm','r_over_q_circuit_ohm')
    changes={}
    for name in names:
        x,y=a[name],b[name]
        if (x is None)!=(y is None):raise ValueError('curved RF availability changes across the fixed domain')
        if x is not None:changes['rf/'+name]=_relative_difference(x,y)
    for family,left,right in zip(('wall_segment','wall_component'),left_walls,right_walls):
        if len(left)!=len(right):raise ValueError('curved RF reference wall component counts differ')
        for i,(x,y) in enumerate(zip(left,right)):changes[family+'/'+str(i+1)]=_relative_difference(x,y)
    va,vb=a['vacc_v'],b['vacc_v']
    if (va is None)!=(vb is None):raise ValueError('curved RF axis voltage availability changes')
    if va is not None:
        changes['axis_voltage_relative']=_relative_difference(phase*complex(va['real'],va['imag']),complex(vb['real'],vb['imag']))
    return changes


def compare_curved_hphi_rf_convergence(request,solutions):
    """Retain original full P2 fields/walls; only actual individual IDs select RF."""
    if type(request) is not CurvedHphiRFConvergence:raise ValueError('expected CurvedHphiRFConvergence')
    request=CurvedHphiRFConvergence.from_dict(request.to_dict());convergence=request.convergence
    if type(solutions) not in (tuple,list) or len(solutions)!=3:raise ValueError('every original curved RF FEM level is required')
    verified=[]
    for project,solution in zip(convergence.projects,solutions):
        if not hasattr(solution,'case') or solution.case.to_dict()!=project.case.to_dict():
            raise ValueError('curved RF solution differs from its original level Case')
        verified.append(verified_curved_hphi_solution(solution))
    ids=list(request.tracking_requests[0].previous_mode_ids);ranks=[ids.index(request.mode_id)+1]
    rf0,w0,c0=_selected_rf(convergence,verified[0],convergence.native_cells[0],ranks[0])
    rf=[rf0];walls=[(w0,c0)];pairs=[];stop=None
    for index,declaration in enumerate(request.tracking_requests):
        if list(declaration.previous_mode_ids)!=ids:raise ValueError('curved RF adjacent declaration replaces or reorders inherited IDs')
        try:tracking=track_curved_hphi_modes(verified[index],verified[index+1],declaration)
        except ValueError as error:
            tracking=dict(status='UNVERIFIED',individual_ids_complete=False,current_mode_ids=None,verification_reasons=[str(error)])
        if tracking['status']!='PASS' or not tracking['individual_ids_complete']:
            pairs.append(dict(tracking=tracking,changes=None,field_difference_integration_orders=None))
            stop='individual E/H identity or finite upper guard is unverified';break
        current_ids=tracking['current_mode_ids'];old_mode=ids.index(request.mode_id);new_mode=current_ids.index(request.mode_id)
        match=next(m for m in tracking['matches'] if m['previous_ids']==[request.mode_id] and m['dimension']==1)
        phase=match['previous_phase_multiplier']
        if phase not in (-1,1):raise ValueError('curved RF individual match lacks a common E/H coefficient phase')
        order=tracking['physical_mapping']['integration']['integration_orders'][-1]
        try:
            overlay=build_curved_hphi_comparison(verified[index].case.geometry,verified[index+1].case.geometry,declaration.domain,
                previous_cells=declaration.previous_cells,current_cells=declaration.current_cells,
                max_pair_tests=declaration.controls.max_candidate_tests,max_triangles=declaration.controls.max_overlay_triangles)
            low,high=(_field_changes(verified[index],verified[index+1],overlay,old_mode,new_mode,phase,n,convergence.max_sample_points) for n in (order,order+2))
            if np.max(abs(low-high))>1e-10:raise ValueError('curved RF direct field quadrature is unresolved')
            current,w,c=_selected_rf(convergence,verified[index+1],convergence.native_cells[index+1],new_mode+1)
            current_walls=(w,c);changes=_rf_changes(rf[-1],current,walls[-1],current_walls,phase)
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
        if previous.keys()!=last.keys():raise ValueError('curved RF required quantities differ')
        for name,value in last.items():
            thresholds=convergence.thresholds
            limit=(getattr(thresholds,name) if name in ('frequency_relative','electric_field_relative','magnetic_field_relative','axis_voltage_relative') else thresholds.rf_relative)
            old=previous[name];stable=value<=old+max(1e-12,old*1e-8)
            checks[name]=dict(passed=bool(stable and value<=limit),previous=old,last=value,threshold=limit,nonincreasing=bool(stable))
    passed=bool(checks) and all(c['passed'] for c in checks.values())
    return dict(format='superfish_ng_curved_hphi_rf_convergence_result',result_version=1,request=request.to_dict(),
        status='PASS' if passed else 'UNVERIFIED',mode_id=request.mode_id,mode_ranks=ranks,individual_ids_complete=len(ranks)==3,
        comparisons=pairs,checks=checks,selected_rf=rf,wall_loss_w_by_segment=[w[0].tolist() for w in walls],
        wall_loss_w_by_component=[w[1].tolist() for w in walls],stop_reason=stop,
        field_measure='2*pi*r dr dz; original full quadratic maps and peak E/H; direct finer-norm differences with one common coefficient phase',
        wall_segment_basis='complete original quadratic reference boundary; native curved edge integrals aggregated by exact boundary charts',
        interpretation='two consecutive differences on three original complete fixed quadratic domains with sampled individual E/H identity and finite guards; not an analytic-boundary or continuum error bound',surface_peak_accuracy='not_checked')

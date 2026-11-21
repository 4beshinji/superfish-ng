# SPDX-License-Identifier: Apache-2.0
"""Explicit same-domain Hphi mesh sequences and finite-difference diagnostics."""
from dataclasses import dataclass,field
from pathlib import Path
from types import SimpleNamespace
import json
import numpy as np
from .config import integer,positive,keys
from .project import parse_json
from .hphi_project import HphiProject
from .curved_hphi import CurvedHphiCase
from .material_hphi import MaterialHphiCase
from .hphi_native import hphi_result
from .coaxial import CoaxialCase,_space
from .hphi_field_overlap import _declared_mesh,_verified_solution,hphi_field_grams
from .meridional_overlap import meridional_overlay
from .fem import triangle_quadrature
from .constants import TAU


@dataclass(frozen=True)
class HphiConvergenceThresholds:
    frequency_relative: float=1e-4
    electric_field_relative: float=.01
    magnetic_field_relative: float=.01
    rf_relative: float=.005
    axis_voltage_relative: float=.005
    spectral_gap_relative: float=.001
    minimum_overlap: float=.9
    overlap_margin: float=.1

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value=positive(getattr(self,name),name)
            if value>=1:raise ValueError(f'{name} must be less than 1')
            object.__setattr__(self,name,value)

    def to_dict(self):return {name:getattr(self,name) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls,data):
        names=list(cls.__dataclass_fields__);keys(data,names,names,'Hphi convergence thresholds')
        return cls(**data)


def _project_mesh(project):
    case=project.case
    if isinstance(case,MaterialHphiCase):
        raise ValueError("material Hphi convergence is unsupported; material partitions need a separate comparison contract")
    if isinstance(case,CurvedHphiCase):
        raise ValueError('curved Hphi requires CurvedHphiConvergence with complete quadratic reference geometry and native charts; straight convergence cannot consume curved geometry')
    return _declared_mesh(SimpleNamespace(case=case,space=_space(case))) if isinstance(case,CoaxialCase) else case.mesh


@dataclass(frozen=True)
class HphiConvergence:
    projects: tuple
    mode_ranks: tuple=(1,)
    max_triangles: int=250000
    max_candidate_tests: int=2000000
    max_overlay_triangles: int=250000
    max_gram_modes: int=256
    thresholds: HphiConvergenceThresholds=field(default_factory=HphiConvergenceThresholds)

    def __post_init__(self):
        for name in ('max_triangles','max_candidate_tests','max_overlay_triangles','max_gram_modes'):integer(getattr(self,name),name)
        if not isinstance(self.projects,(tuple,list)) or len(self.projects)<3 or any(not isinstance(p,HphiProject) for p in self.projects):
            raise ValueError('Hphi convergence requires at least three explicit HphiProjects')
        object.__setattr__(self,'projects',tuple(HphiProject.from_dict(p.to_dict()) for p in self.projects))
        if not isinstance(self.thresholds,HphiConvergenceThresholds):raise ValueError('expected HphiConvergenceThresholds')
        if not isinstance(self.mode_ranks,(tuple,list)) or not self.mode_ranks:raise ValueError('mode_ranks must be a nonempty list')
        for rank in self.mode_ranks:
            integer(rank,'mode rank')
            if rank>self.projects[0].case.modes:raise ValueError('mode rank exceeds the positive spectrum')
        if len(set(self.mode_ranks))!=len(self.mode_ranks):raise ValueError('mode_ranks must be unique')
        object.__setattr__(self,'mode_ranks',tuple(self.mode_ranks))
        previous=None;reference=None
        for project in self.projects:
            case=project.case
            if isinstance(case,MaterialHphiCase):
                raise ValueError("material Hphi convergence is unsupported; material partitions need a separate comparison contract")
            if isinstance(case,CurvedHphiCase):
                _project_mesh(project)
            if case.modes>self.max_gram_modes:raise ValueError('Hphi convergence exceeds max_gram_modes')
            count=2*case.nr*case.nz if isinstance(case,CoaxialCase) else len(case.mesh.triangles)
            if count>min(self.max_triangles,self.max_overlay_triangles):raise ValueError('Hphi convergence mesh exceeds triangle budget')
            mesh=_project_mesh(project);acceleration=getattr(case,'acceleration',None)
            physical=dict(outer=mesh.outer_rz_m.tolist(),holes=[h.tolist() for h in mesh.holes_rz_m],
                element_order=case.element_order,quadrature_order=getattr(case,'quadrature_order',None),modes=case.modes,energy=case.normalization_j,conductivity=case.conductivity_s_per_m,
                acceleration=None if acceleration is None else acceleration.to_dict())
            if reference is None:reference=physical
            elif physical!=reference:raise ValueError('Hphi convergence requires identical ordered contours, fixed P1/P2 and quadrature orders, spectrum size, normalization, conductivity and acceleration path')
            vertices=mesh.points_rz_m[mesh.triangles]
            maximum=float(np.max(np.linalg.norm(vertices-np.roll(vertices,-1,axis=1),axis=2)))
            if previous is not None and not (count>previous[0] and maximum<previous[1]):
                raise ValueError('each explicit Hphi mesh must have more triangles and a smaller maximum edge length')
            previous=count,maximum

    def to_dict(self):
        return dict(format='superfish_ng_hphi_convergence',convergence_version=1,
            projects=[p.to_dict() for p in self.projects],mode_ranks=list(self.mode_ranks),
            **{name:getattr(self,name) for name in ('max_triangles','max_candidate_tests','max_overlay_triangles','max_gram_modes')},thresholds=self.thresholds.to_dict())

    @classmethod
    def from_dict(cls,data):
        names=['format','convergence_version','projects','mode_ranks','max_triangles','max_candidate_tests','max_overlay_triangles','max_gram_modes','thresholds']
        keys(data,names,names,'Hphi convergence')
        if data['format']!='superfish_ng_hphi_convergence' or type(data['convergence_version']) is not int or data['convergence_version']!=1:
            raise ValueError('expected superfish_ng_hphi_convergence convergence_version 1')
        if not isinstance(data['projects'],list) or not isinstance(data['mode_ranks'],list):raise ValueError('Hphi convergence projects and mode_ranks must be JSON lists')
        return cls([HphiProject.from_dict(p) for p in data['projects']],data['mode_ranks'],
            **{name:data[name] for name in ('max_triangles','max_candidate_tests','max_overlay_triangles','max_gram_modes')},thresholds=HphiConvergenceThresholds.from_dict(data['thresholds']))

    @classmethod
    def load(cls,path):return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def save(self,path):
        with Path(path).open('x',encoding='utf-8') as stream:stream.write(json.dumps(self.to_dict(),indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def _relative_difference(a,b):
    scale=max(abs(a),abs(b))
    return float(abs(a-b)/scale) if scale else 0.


def _field_changes(coarse,fine,overlay,mode,phase,order):
    errors=np.zeros(2);norms=np.zeros(2)
    components=(('Er_quadrature_V_per_m','Ez_quadrature_V_per_m'),('Hphi_real_A_per_m',))
    for bary,weight in triangle_quadrature(order):
        a=coarse.fields_in_cells(overlay.previous_cells,np.einsum('i,tij->tj',bary,overlay.previous_vertex_barycentric),mode)
        b=fine.fields_in_cells(overlay.current_cells,np.einsum('i,tij->tj',bary,overlay.current_vertex_barycentric),mode)
        radius=np.einsum('i,ti->t',bary,overlay.vertices_rz_m[:,:,0]);weights=TAU*radius*weight*overlay.determinants
        for family,names in enumerate(components):
            errors[family]+=sum(float(weights@(phase*a[name]-b[name])**2) for name in names)
            norms[family]+=sum(float(weights@b[name]**2) for name in names)
    if not np.isfinite([*errors,*norms]).all() or np.any(norms<=0):raise ValueError('Hphi direct field differences require finite positive norms')
    return np.sqrt(errors/norms)


def _adjacent(request,coarse,fine):
    threshold=request.thresholds
    grams=hphi_field_grams(coarse,fine,max_candidate_tests=request.max_candidate_tests,max_overlay_triangles=request.max_overlay_triangles,max_gram_modes=request.max_gram_modes)
    overlay=meridional_overlay(_declared_mesh(coarse),_declared_mesh(fine),max_candidate_tests=request.max_candidate_tests,max_overlay_triangles=request.max_overlay_triangles)
    overlaps=[]
    for aa,ab,bb in (grams.electric,grams.magnetic):
        normalized=ab/np.sqrt(np.diag(aa)[:,None]*np.diag(bb)[None,:])
        if np.max(abs(normalized))>1+1e-10:raise ValueError('Hphi normalized overlap exceeds Cauchy-Schwarz bound')
        overlaps.append(normalized)
    qa,qb=(hphi_result(s)['modes'] for s in (coarse,fine));rows=[]
    rf_names=('stored_energy_j','electric_energy_j','magnetic_energy_j','wall_loss_w','surface_resistance_ohm','q0','geometry_factor_ohm','r_over_q_accelerator_ohm','r_over_q_circuit_ohm')
    for rank in request.mode_ranks:
        mode=rank-1;reasons=[]
        if rank==coarse.case.modes:reasons.append('upper spectral neighbor was not computed')
        gaps=[]
        for s in (coarse,fine):
            gaps.extend(abs(float(s.frequencies_hz[i]/s.frequencies_hz[mode]-1)) for i in (mode-1,mode+1) if 0<=i<s.case.modes)
        neighborhood=[i for i in (mode-1,mode,mode+1) if 0<=i<coarse.case.modes]
        drift=max(_relative_difference(coarse.frequencies_hz[i],fine.frequencies_hz[i]) for i in neighborhood)
        required_gap=max(threshold.spectral_gap_relative,2*drift)
        if not gaps or min(gaps)<=required_gap:reasons.append('spectral separation is unresolved or near-degenerate')
        margins=[]
        for name,overlap in zip(('electric','magnetic'),overlaps):
            absolute=abs(overlap);competitor=max(float(np.max(np.delete(absolute[mode],mode),initial=0.)),float(np.max(np.delete(absolute[:,mode],mode),initial=0.)))
            margin=float(absolute[mode,mode]-competitor);margins.append(margin)
            if absolute[mode,mode]<threshold.minimum_overlap or margin<threshold.overlap_margin:reasons.append(f'same-rank {name} overlap is not uniquely dominant')
        phase=1 if overlaps[1][mode,mode]>=0 else -1
        if phase*overlaps[0][mode,mode]<=0:reasons.append('electric and magnetic correspondence require different coefficient phases')
        order=grams.diagnostic['integration_orders'][-1]
        low=_field_changes(coarse,fine,overlay,mode,phase,order)
        high=_field_changes(coarse,fine,overlay,mode,phase,order+2)
        if np.max(abs(low-high))>1e-10:raise ValueError('Hphi direct field difference quadrature is unresolved; increase Case integration order or refine')
        rf={name:_relative_difference(qa[mode][name],qb[mode][name]) for name in rf_names if qa[mode][name] is not None}
        def walls(q):
            return q['wall_h2_integral_a2_by_segment'] if 'wall_h2_integral_a2_by_segment' in q else [q['wall_h2_integral_a2_by_surface'][key] for key in ('z_min_end_plate','outer_conductor','z_max_end_plate','inner_conductor')]
        wa,wb=(np.asarray(walls(q))*q['surface_resistance_ohm']/2 for q in (qa[mode],qb[mode]))
        if len(wa)!=len(wb):raise ValueError('Hphi wall segment declarations differ')
        segment=[_relative_difference(a,b) for a,b in zip(wa,wb)]
        va,vb=(q['vacc_v'] for q in (qa[mode],qb[mode]));voltage=None
        if va is not None:voltage=_relative_difference(phase*complex(va['real'],va['imag']),complex(vb['real'],vb['imag']))
        rows.append(dict(mode_rank=rank,correspondence='UNVERIFIED' if reasons else 'same_rank_overlap_verified',reasons=reasons,
            electric_overlap=float(overlaps[0][mode,mode]),magnetic_overlap=float(overlaps[1][mode,mode]),electric_overlap_margin=margins[0],magnetic_overlap_margin=margins[1],
            minimum_spectral_gap_relative=min(gaps) if gaps else None,neighborhood_frequency_drift_relative=drift,required_spectral_gap_relative=required_gap,
            coarse_phase_multiplier=phase,frequency_relative=_relative_difference(coarse.frequencies_hz[mode],fine.frequencies_hz[mode]),
            electric_field_relative=float(high[0]),magnetic_field_relative=float(high[1]),field_difference_integration_orders=[order,order+2],
            rf_relative=rf,wall_segment_relative=segment,axis_voltage_relative=voltage))
    return dict(electric_overlap_matrix=overlaps[0].tolist(),magnetic_overlap_matrix=overlaps[1].tolist(),integration=grams.diagnostic,modes=rows)


def compare_hphi_convergence(request,solutions):
    """Reverify all original FEMs and judge the last two differences independently.

    PASS is a finite sequence diagnostic. Near degeneracy, rank swaps and
    inadequate guard modes remain UNVERIFIED; no persistent ID is assigned.
    """
    if not isinstance(request,HphiConvergence):raise ValueError('expected HphiConvergence')
    request=HphiConvergence.from_dict(request.to_dict())
    if not isinstance(solutions,(tuple,list)) or len(solutions)!=len(request.projects):raise ValueError('Hphi convergence requires every declared FEM level')
    verified=[]
    for project,solution in zip(request.projects,solutions):
        if not hasattr(solution,'case') or solution.case.to_dict()!=project.case.to_dict():raise ValueError('Hphi solution does not match the requested level Case')
        verified.append(_verified_solution(solution))
    comparisons=[_adjacent(request,a,b) for a,b in zip(verified,verified[1:])];decisions=[]
    for index,rank in enumerate(request.mode_ranks):
        previous,last=(pair['modes'][index] for pair in comparisons[-2:])
        correspondence=all(row['correspondence']=='same_rank_overlap_verified' for row in (previous,last));checks={}
        def check(name,a,b,limit):
            stable=b<=a+max(1e-12,a*1e-8)
            checks[name]=dict(passed=bool(correspondence and stable and b<=limit),previous=a,last=b,threshold=limit,nonincreasing=bool(stable))
        for name in ('frequency_relative','electric_field_relative','magnetic_field_relative'):check(name,previous[name],last[name],getattr(request.thresholds,name))
        for name in last['rf_relative']:check('rf/'+name,previous['rf_relative'][name],last['rf_relative'][name],request.thresholds.rf_relative)
        for segment,(a,b) in enumerate(zip(previous['wall_segment_relative'],last['wall_segment_relative'])):check(f'wall_segment/{segment+1}',a,b,request.thresholds.rf_relative)
        if last['axis_voltage_relative'] is not None:check('axis_voltage_relative',previous['axis_voltage_relative'],last['axis_voltage_relative'],request.thresholds.axis_voltage_relative)
        decisions.append(dict(mode_rank=rank,status='PASS' if all(c['passed'] for c in checks.values()) else 'UNVERIFIED',correspondence_verified=correspondence,checks=checks))
    return dict(format='superfish_ng_hphi_convergence_result',result_version=1,request=request.to_dict(),
        status='PASS' if all(d['status']=='PASS' for d in decisions) else 'UNVERIFIED',comparisons=comparisons,decisions=decisions,
        interpretation='three-finest-level difference diagnostic; not a continuum discretization error bound',
        field_measure='2*pi*r dr dz; original peak E/H with one coefficient phase',
        relative_difference='abs(a-b)/max(abs(a),abs(b)); zero if both zero; field L2 uses the finer field norm',
        surface_peak_accuracy='not_checked',mode_tracking='not_performed')

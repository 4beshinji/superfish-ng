# SPDX-License-Identifier: Apache-2.0
"""Three-level diagnostics on one declared complete quadratic Hphi vacuum."""
from copy import deepcopy
from dataclasses import dataclass,field,replace
from pathlib import Path
import json
import numpy as np
from .config import integer,keys
from .project import parse_json
from .hphi_project import HphiProject
from .hphi_convergence import HphiConvergenceThresholds,_relative_difference
from .curved_hphi import CurvedHphiCase
from .curved_meridional_geometry import CurvedMeridionalGeometry
from .curved_hphi_comparison import CurvedHphiComparisonDomain,build_curved_hphi_comparison,UNIT,_fraction,CurvedHphiComparisonBudgetExceeded
from .curved_hphi_field_overlap import curved_hphi_field_grams,verified_curved_hphi_solution
from .curved_hphi_rf import curved_hphi_quantities
from .planar_tracking_overlap import _cross
from .constants import TAU
from .fem import triangle_quadrature

_LIMITS=('max_triangles','max_candidate_tests','max_overlay_triangles','max_gram_modes','max_sample_points')


@dataclass(frozen=True)
class CurvedHphiConvergence:
    projects: tuple
    reference_geometry: CurvedMeridionalGeometry
    native_cells: tuple
    mode_ranks: tuple=(1,)
    max_triangles: int=250000
    max_candidate_tests: int=2000000
    max_overlay_triangles: int=250000
    max_gram_modes: int=256
    max_sample_points: int=2000000
    comparison_quadrature_order: int=16
    thresholds: HphiConvergenceThresholds=field(default_factory=HphiConvergenceThresholds)

    def __post_init__(self):
        for name in _LIMITS:integer(getattr(self,name),name)
        integer(self.comparison_quadrature_order,'comparison_quadrature_order',2)
        if self.comparison_quadrature_order>36:raise ValueError('comparison_quadrature_order must not exceed 36')
        if not isinstance(self.projects,(tuple,list)) or len(self.projects)<3 or any(type(p) is not HphiProject for p in self.projects):
            raise ValueError('curved convergence requires at least three explicit HphiProjects')
        projects=tuple(HphiProject.from_dict(p.to_dict()) for p in self.projects)
        if any(type(p.case) is not CurvedHphiCase for p in projects):raise ValueError('curved convergence requires vacuum CurvedHphiCase projects')
        if type(self.reference_geometry) is not CurvedMeridionalGeometry:raise ValueError('complete reference quadratic geometry required')
        reference=CurvedMeridionalGeometry.from_dict(self.reference_geometry.to_dict())
        domain=CurvedHphiComparisonDomain(reference,reference,'same_vacuum')
        if not isinstance(self.native_cells,(tuple,list)) or len(self.native_cells)!=len(projects):
            raise ValueError('one explicit native chart list or null is required per level')
        native_cells=tuple(deepcopy(self.native_cells))
        if type(self.thresholds) is not HphiConvergenceThresholds:raise ValueError('expected HphiConvergenceThresholds')
        if not isinstance(self.mode_ranks,(tuple,list)) or not self.mode_ranks:raise ValueError('mode_ranks must be nonempty')
        for rank in self.mode_ranks:
            integer(rank,'mode rank')
            if rank>projects[0].case.modes:raise ValueError('mode rank exceeds the positive spectrum')
        if len(set(self.mode_ranks))!=len(self.mode_ranks):raise ValueError('mode_ranks must be unique')
        physical=None;previous=None
        for p,charts in zip(projects,native_cells):
            c=p.case;g=c.geometry
            if c.modes>self.max_gram_modes:raise ValueError('curved convergence exceeds max_gram_modes')
            count=len(g.cell_nodes)
            if count>self.max_triangles:raise CurvedHphiComparisonBudgetExceeded('curved convergence exceeds max_triangles')
            fixed=dict(element_order=c.element_order,quadrature_order=c.quadrature_order,modes=c.modes,
                normalization_j=c.normalization_j,conductivity_s_per_m=c.conductivity_s_per_m,
                acceleration=None if c.acceleration is None else c.acceleration.to_dict())
            if physical is not None and fixed!=physical:
                raise ValueError('curved convergence requires fixed FEM order, quadrature, spectrum, energy, conductivity and acceleration path')
            physical=fixed
            build_curved_hphi_comparison(reference,g,domain,current_cells=charts,
                max_pair_tests=self.max_candidate_tests,max_triangles=self.max_overlay_triangles)
            points=g.points_rz_m[g.cell_nodes]
            controls=np.concatenate((points[:,:3],2*points[:,3:]-(points[:,[0,1,2]]+points[:,[1,2,0]])/2),axis=1)
            maximum=float(np.max(np.linalg.norm(np.ptp(controls,axis=1),axis=1)))
            if previous is not None and not (count>previous[0] and maximum<previous[1]):
                raise ValueError('each curved level must have more cells and a smaller whole-P2 bounding-box diameter')
            previous=count,maximum
        object.__setattr__(self,'projects',projects);object.__setattr__(self,'reference_geometry',reference)
        object.__setattr__(self,'native_cells',native_cells);object.__setattr__(self,'mode_ranks',tuple(self.mode_ranks))

    def to_dict(self):
        return dict(format='superfish_ng_curved_hphi_convergence',convergence_version=1,
            projects=[p.to_dict() for p in self.projects],reference_geometry=self.reference_geometry.to_dict(),
            native_cells=deepcopy(list(self.native_cells)),mode_ranks=list(self.mode_ranks),
            **{name:getattr(self,name) for name in _LIMITS},comparison_quadrature_order=self.comparison_quadrature_order,
            thresholds=self.thresholds.to_dict())

    @classmethod
    def from_dict(cls,data):
        names=('format','convergence_version','projects','reference_geometry','native_cells','mode_ranks',*_LIMITS,'comparison_quadrature_order','thresholds')
        keys(data,names,names,'curved Hphi convergence')
        if (data['format']!='superfish_ng_curved_hphi_convergence' or type(data['convergence_version']) is not int or data['convergence_version']!=1):
            raise ValueError('expected curved Hphi convergence_version 1')
        if any(type(data[name]) is not list for name in ('projects','native_cells','mode_ranks')):
            raise ValueError('projects, native_cells and mode_ranks must be JSON lists')
        return cls(tuple(HphiProject.from_dict(p) for p in data['projects']),
            CurvedMeridionalGeometry.from_dict(data['reference_geometry']),data['native_cells'],data['mode_ranks'],
            **{name:data[name] for name in (*_LIMITS,'comparison_quadrature_order')},
            thresholds=HphiConvergenceThresholds.from_dict(data['thresholds']))

    @classmethod
    def load(cls,path):return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def save(self,path):
        with Path(path).open('x',encoding='utf-8') as stream:stream.write(json.dumps(self.to_dict(),indent=2,allow_nan=False)+'\n')


def _reference_segments(reference,native,declarations):
    """Boundary charts already verified by the complete H11 partition contract."""
    lookup={tuple(sorted(map(int,nodes[:2]))):int(segment)
        for nodes,segment in zip(reference.boundary_nodes,reference.base_mesh.boundary_segments)}
    result=[]
    for edge,cell in zip(native.boundary_nodes,native.base_mesh.boundary_cells):
        if declarations is None:owner=int(cell);vertices=UNIT
        else:
            raw=declarations[int(cell)];owner=raw['base_cell']
            vertices=tuple(tuple(_fraction(v) for v in p) for p in raw['reference_vertices'])
        corners=list(map(int,native.cell_nodes[cell,:3]));a,b=(vertices[corners.index(int(node))] for node in edge[:2])
        for i,j in ((0,1),(1,2),(2,0)):
            if _cross(UNIT[i],UNIT[j],a)==0 and _cross(UNIT[i],UNIT[j],b)==0:
                result.append(lookup[tuple(sorted(map(int,reference.cell_nodes[owner,[i,j]])))]);break
        else:raise ValueError('native boundary lacks its verified reference segment')
    return np.asarray(result,dtype=int)


def _reference_wall_integrals(solution,labels,count,mode,order):
    g=solution.case.geometry;base=g.base_mesh;t,w=np.polynomial.legendre.leggauss(order);t=(t+1)/2;w=w/2
    derivative=np.column_stack((4*t-3,4*t-1,4-8*t));phi=np.column_stack(((1-t)*(1-2*t),t*(2*t-1),4*t*(1-t)))
    result=np.zeros(count)
    for edge in np.flatnonzero(g.boundary_tags=='pec'):
        cell=int(base.boundary_cells[edge]);i,j=base.boundary_local_vertices[edge]
        bary=np.zeros((order,3));bary[:,i]=1-t;bary[:,j]=t
        h=solution.fields_in_cells(np.full(order,cell,dtype=int),bary,mode)['Hphi_real_A_per_m']
        nodes=g.points_rz_m[g.boundary_nodes[edge]];r=(phi@nodes)[:,0]
        measure=TAU*w*r*np.linalg.norm(derivative@(nodes-nodes[0]),axis=1)
        result[labels[edge]]+=measure@(h*h)
    return result


def _field_changes(coarse,fine,overlay,mode,phase,order,max_samples):
    rule=list(triangle_quadrature(order));q=np.array([p for p,w in rule]);w=np.array([w for p,w in rule])
    if len(rule)*len(overlay.triangles)>max_samples:raise CurvedHphiComparisonBudgetExceeded('curved field differences exceed max_sample_points')
    errors=np.zeros(2);norms=np.zeros(2)
    for start in range(0,len(overlay.triangles),64):
        part=replace(overlay,triangles=overlay.triangles[start:start+64]);samples=[]
        for side,solution in enumerate((coarse,fine)):
            rows=part.evaluate(side,q)
            cells=np.concatenate([np.full(len(q),row['native_cell'],dtype=int) for row in rows])
            bary=np.concatenate([row['native_barycentric'] for row in rows])
            samples.append(solution.fields_in_cells(cells,bary,mode))
        weights=np.concatenate([TAU*row['points_rz_m'][:,0]*row['determinant_m2']*w for row in rows])
        for family,names in enumerate((('Er_quadrature_V_per_m','Ez_quadrature_V_per_m'),('Hphi_real_A_per_m',))):
            errors[family]+=sum(weights@(phase*samples[0][name]-samples[1][name])**2 for name in names)
            norms[family]+=sum(weights@samples[1][name]**2 for name in names)
    if not np.isfinite([*errors,*norms]).all() or np.any(norms<=0):raise ValueError('curved field differences require finite positive norms')
    return np.sqrt(errors/norms)


def _level_rf(request,solution,charts):
    reference=request.reference_geometry;count=len(reference.base_mesh.surface_area_m2_by_segment)
    labels=_reference_segments(reference,solution.case.geometry,charts);result={}
    for rank in request.mode_ranks:
        mode=rank-1;q=curved_hphi_quantities(solution,mode)
        low,high=(_reference_wall_integrals(solution,labels,count,mode,n) for n in q['integration_diagnostic']['orders'])
        scale=np.maximum(abs(low),abs(high));diff=np.divide(abs(low-high),scale,out=np.zeros_like(scale),where=scale>0)
        if not np.isfinite(diff).all() or max(diff,default=0)>5e-10:raise ValueError('curved reference wall quadrature is unresolved')
        components=[];offset=0
        for contour in (reference.base_mesh.outer_rz_m,*reference.base_mesh.holes_rz_m):
            components.append(float(high[offset:offset+len(contour)].sum()));offset+=len(contour)
        original=np.asarray(q['wall_h2_integral_a2_by_component'])
        if np.any(abs(np.asarray(components)-original)>1e-10*np.maximum(abs(original),1e-300)):
            raise ValueError('reference wall partition does not reproduce every original component integral')
        result[rank]=(q,high*q['surface_resistance_ohm']/2,np.asarray(components)*q['surface_resistance_ohm']/2)
    return result


def _adjacent(request,coarse,fine,old_cells,new_cells,qa,qb):
    domain=CurvedHphiComparisonDomain(request.reference_geometry,request.reference_geometry,'same_vacuum')
    options=dict(previous_cells=old_cells,current_cells=new_cells,max_candidate_tests=request.max_candidate_tests,
        max_overlay_triangles=request.max_overlay_triangles,max_gram_modes=request.max_gram_modes,
        max_sample_points=request.max_sample_points,quadrature_order=request.comparison_quadrature_order)
    grams=curved_hphi_field_grams(coarse,fine,domain,**options)
    overlay=build_curved_hphi_comparison(coarse.case.geometry,fine.case.geometry,domain,previous_cells=old_cells,
        current_cells=new_cells,max_pair_tests=request.max_candidate_tests,max_triangles=request.max_overlay_triangles)
    overlaps=[]
    for aa,ab,bb in (grams.electric,grams.magnetic):
        overlap=ab/np.sqrt(np.diag(aa)[:,None]*np.diag(bb)[None,:])
        if np.max(abs(overlap))>1+1e-10:raise ValueError('curved Hphi overlap exceeds Cauchy-Schwarz bound')
        overlaps.append(overlap)
    threshold=request.thresholds;rows=[]
    names=('stored_energy_j','electric_energy_j','magnetic_energy_j','wall_loss_w','surface_resistance_ohm','q0','geometry_factor_ohm','r_over_q_accelerator_ohm','r_over_q_circuit_ohm')
    for rank in request.mode_ranks:
        mode=rank-1;reasons=[];gaps=[];margins=[]
        if rank==coarse.case.modes:reasons.append('upper spectral neighbor was not computed')
        for s in (coarse,fine):
            gaps.extend(abs(float(s.frequencies_hz[i]/s.frequencies_hz[mode]-1)) for i in (mode-1,mode+1) if 0<=i<s.case.modes)
        neighborhood=[i for i in (mode-1,mode,mode+1) if 0<=i<coarse.case.modes]
        drift=max(_relative_difference(coarse.frequencies_hz[i],fine.frequencies_hz[i]) for i in neighborhood)
        required=max(threshold.spectral_gap_relative,2*drift)
        if not gaps or min(gaps)<=required:reasons.append('spectral separation is unresolved or near-degenerate')
        for name,overlap in zip(('electric','magnetic'),overlaps):
            absolute=abs(overlap);competitor=max(float(np.max(np.delete(absolute[mode],mode),initial=0.)),float(np.max(np.delete(absolute[:,mode],mode),initial=0.)))
            margin=float(absolute[mode,mode]-competitor);margins.append(margin)
            if absolute[mode,mode]<threshold.minimum_overlap or margin<threshold.overlap_margin:
                reasons.append(f'same-rank {name} overlap is not uniquely dominant')
        phase=1 if overlaps[1][mode,mode]>=0 else -1
        if phase*overlaps[0][mode,mode]<=0:reasons.append('electric and magnetic correspondence require different coefficient phases')
        order=grams.diagnostic['integration_orders'][-1]
        low,high=(_field_changes(coarse,fine,overlay,mode,phase,n,request.max_sample_points) for n in (order,order+2))
        if np.max(abs(low-high))>1e-10:raise ValueError('curved direct field difference quadrature is unresolved')
        a,wa,ca=qa[rank];b,wb,cb=qb[rank]
        rf={name:_relative_difference(a[name],b[name]) for name in names if a[name] is not None}
        va,vb=a['vacc_v'],b['vacc_v'];voltage=None if va is None else _relative_difference(phase*complex(va['real'],va['imag']),complex(vb['real'],vb['imag']))
        rows.append(dict(mode_rank=rank,correspondence='UNVERIFIED' if reasons else 'same_rank_overlap_verified',reasons=reasons,
            electric_overlap=float(overlaps[0][mode,mode]),magnetic_overlap=float(overlaps[1][mode,mode]),
            electric_overlap_margin=margins[0],magnetic_overlap_margin=margins[1],minimum_spectral_gap_relative=min(gaps) if gaps else None,
            neighborhood_frequency_drift_relative=drift,required_spectral_gap_relative=required,coarse_phase_multiplier=phase,
            frequency_relative=_relative_difference(coarse.frequencies_hz[mode],fine.frequencies_hz[mode]),
            electric_field_relative=float(high[0]),magnetic_field_relative=float(high[1]),field_difference_integration_orders=[order,order+2],
            rf_relative=rf,wall_segment_relative=[_relative_difference(x,y) for x,y in zip(wa,wb)],
            wall_component_relative=[_relative_difference(x,y) for x,y in zip(ca,cb)],axis_voltage_relative=voltage))
    return dict(electric_overlap_matrix=overlaps[0].tolist(),magnetic_overlap_matrix=overlaps[1].tolist(),integration=grams.diagnostic,modes=rows)


def compare_curved_hphi_convergence(request,solutions):
    """Compare actual original fields; PASS is only a finite three-level diagnostic."""
    if type(request) is not CurvedHphiConvergence:raise ValueError('expected CurvedHphiConvergence')
    request=CurvedHphiConvergence.from_dict(request.to_dict())
    if not isinstance(solutions,(tuple,list)) or len(solutions)!=len(request.projects):raise ValueError('every declared curved FEM level is required')
    verified=[]
    for project,solution in zip(request.projects,solutions):
        if not hasattr(solution,'case') or solution.case.to_dict()!=project.case.to_dict():raise ValueError('curved solution differs from the requested level Case')
        verified.append(verified_curved_hphi_solution(solution))
    rf=[_level_rf(request,s,cells) for s,cells in zip(verified,request.native_cells)]
    comparisons=[_adjacent(request,a,b,old,new,qa,qb) for a,b,old,new,qa,qb in
        zip(verified,verified[1:],request.native_cells,request.native_cells[1:],rf,rf[1:])]
    decisions=[]
    for index,rank in enumerate(request.mode_ranks):
        previous,last=(pair['modes'][index] for pair in comparisons[-2:]);checks={}
        correspondence=all(row['correspondence']=='same_rank_overlap_verified' for row in (previous,last))
        def check(name,a,b,limit):
            stable=b<=a+max(1e-12,a*1e-8)
            checks[name]=dict(passed=bool(correspondence and stable and b<=limit),previous=a,last=b,threshold=limit,nonincreasing=bool(stable))
        for name in ('frequency_relative','electric_field_relative','magnetic_field_relative'):
            check(name,previous[name],last[name],getattr(request.thresholds,name))
        for name in last['rf_relative']:check('rf/'+name,previous['rf_relative'][name],last['rf_relative'][name],request.thresholds.rf_relative)
        for family in ('wall_segment','wall_component'):
            for i,(a,b) in enumerate(zip(previous[family+'_relative'],last[family+'_relative'])):
                check(f'{family}/{i+1}',a,b,request.thresholds.rf_relative)
        if last['axis_voltage_relative'] is not None:check('axis_voltage_relative',previous['axis_voltage_relative'],last['axis_voltage_relative'],request.thresholds.axis_voltage_relative)
        decisions.append(dict(mode_rank=rank,status='PASS' if all(c['passed'] for c in checks.values()) else 'UNVERIFIED',correspondence_verified=correspondence,checks=checks))
    return dict(format='superfish_ng_curved_hphi_convergence_result',result_version=1,request=request.to_dict(),
        status='PASS' if all(d['status']=='PASS' for d in decisions) else 'UNVERIFIED',comparisons=comparisons,decisions=decisions,
        interpretation='three-finest-level differences on one fixed quadratic domain; not an analytic-boundary or continuum discretization error bound',
        field_measure='2*pi*r dr dz; original peak E/H with one coefficient phase',
        relative_difference='abs(a-b)/max(abs(a),abs(b)); zero if both zero; direct field L2 uses finer norm',
        wall_segment_basis='complete declared reference geometry; original native edge integrals aggregated by exact boundary charts',
        surface_peak_accuracy='not_checked',mode_tracking='not_performed')

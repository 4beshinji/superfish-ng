# SPDX-License-Identifier: Apache-2.0
"""Conservative original curved E/H subspace tracking with finite-space guards."""
from dataclasses import dataclass,field
from pathlib import Path
import json
import numpy as np
from .config import integer,keys
from .project import parse_json
from .curved_meridional_geometry import CurvedMeridionalGeometry
from .curved_hphi_comparison import CurvedHphiComparisonDomain,_fraction
from .curved_hphi_field_overlap import verified_curved_hphi_solution,curved_hphi_field_grams
from .curved_hphi_spectral_resolution import curved_hphi_spectral_resolution
from .hphi_tracking import HphiTrackingControls,_frequency_groups,_previous_groups
from .mode_tracking import _identity_groups,track_sampled_mode_subspaces
from .planar_tracking_fields import electric_gram_features


def _charts(value,reference):
    if value is None:return None
    if type(value) not in (list,tuple):raise ValueError('native charts must be a list or null')
    result=[]
    for row in value:
        keys(row,('base_cell','reference_vertices'),('base_cell','reference_vertices'),'curved tracking native chart')
        owner=integer(row['base_cell'],'base_cell',minimum=0)
        if owner>=len(reference.cell_nodes):raise ValueError('native chart base_cell is outside reference geometry')
        vertices=row['reference_vertices']
        if type(vertices) is not list or len(vertices)!=3 or any(type(v) is not list or len(v)!=2 for v in vertices):
            raise ValueError('native chart requires three rational reference vertices')
        encoded=[]
        for vertex in vertices:
            xy=[_fraction(v) for v in vertex]
            if min(xy)<0 or sum(xy)>1:raise ValueError('native chart vertex lies outside its reference triangle')
            encoded.append([[v.numerator,v.denominator] for v in xy])
        result.append(dict(base_cell=owner,reference_vertices=encoded))
    return result


@dataclass(frozen=True)
class CurvedHphiTrackingRequest:
    domain: CurvedHphiComparisonDomain
    previous_comparison_geometry: CurvedMeridionalGeometry
    current_comparison_geometry: CurvedMeridionalGeometry
    previous_cells: object=None
    current_cells: object=None
    previous_comparison_cells: object=None
    current_comparison_cells: object=None
    previous_mode_count: int=2
    current_mode_count: int=2
    previous_mode_ids: object=('mode-1','mode-2')
    previous_identity_groups: object=None
    previous_comparison_order: int=2
    current_comparison_order: int=2
    controls: HphiTrackingControls=field(default_factory=HphiTrackingControls)
    max_sample_points: int=2000000

    def __post_init__(self):
        if type(self.domain) is not CurvedHphiComparisonDomain:raise ValueError('curved tracking requires a complete quadratic comparison domain')
        object.__setattr__(self,'domain',CurvedHphiComparisonDomain.from_dict(self.domain.to_dict()))
        for name in ('previous_mode_count','current_mode_count','previous_comparison_order','current_comparison_order','max_sample_points'):
            integer(getattr(self,name),name)
        if self.previous_comparison_order not in (1,2) or self.current_comparison_order not in (1,2):
            raise ValueError('curved comparison orders must be P1 or P2')
        for side,reference in (('previous',self.domain.previous),('current',self.domain.current)):
            name=side+'_comparison_geometry';geometry=getattr(self,name)
            if type(geometry) is not CurvedMeridionalGeometry:raise ValueError('curved tracking requires complete quadratic comparison geometries')
            object.__setattr__(self,name,CurvedMeridionalGeometry.from_dict(geometry.to_dict()))
            for suffix in ('_cells','_comparison_cells'):
                name=side+suffix;object.__setattr__(self,name,_charts(getattr(self,name),reference))
        if type(self.controls) is not HphiTrackingControls:raise ValueError('expected HphiTrackingControls')
        object.__setattr__(self,'controls',HphiTrackingControls.from_dict(self.controls.to_dict()))
        if self.previous_identity_groups is not None:
            if self.previous_mode_ids is not None:raise ValueError('supply individual IDs or identity groups, never both')
            object.__setattr__(self,'previous_identity_groups',_identity_groups(self.previous_identity_groups,self.previous_mode_count))
        else:
            ids=self.previous_mode_ids
            if (type(ids) not in (tuple,list) or len(ids)!=self.previous_mode_count
                    or any(type(v) is not str or not v.strip() for v in ids) or len(set(ids))!=len(ids)):
                raise ValueError('one distinct nonempty previous ID is required per tracked positive rank')
            object.__setattr__(self,'previous_mode_ids',tuple(ids))

    def to_dict(self):
        result=dict(format='superfish_ng_curved_hphi_tracking_request',tracking_version=1,
                    transport='unitary_fixed_cylindrical_components')
        for name in self.__dataclass_fields__:
            value=getattr(self,name)
            result[name]=value.to_dict() if hasattr(value,'to_dict') else value
        return json.loads(json.dumps(result,allow_nan=False))

    @classmethod
    def from_dict(cls,data):
        fields=list(cls.__dataclass_fields__);names=['format','tracking_version','transport',*fields]
        keys(data,names,names,'curved Hphi tracking request')
        if (data['format']!='superfish_ng_curved_hphi_tracking_request' or type(data['tracking_version']) is not int
                or data['tracking_version']!=1 or data['transport']!='unitary_fixed_cylindrical_components'):
            raise ValueError('expected curved Hphi tracking version 1 with unitary fixed cylindrical transport')
        values={name:data[name] for name in fields}
        values['domain']=CurvedHphiComparisonDomain.from_dict(values['domain'])
        for name in ('previous_comparison_geometry','current_comparison_geometry'):
            values[name]=CurvedMeridionalGeometry.from_dict(values[name])
        values['controls']=HphiTrackingControls.from_dict(values['controls'])
        return cls(**values)

    @classmethod
    def load(cls,path):return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def save(self,path):
        with Path(path).open('x',encoding='utf-8') as stream:
            stream.write(json.dumps(self.to_dict(),indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def track_curved_hphi_modes(previous,current,request):
    """Match original E and H; unresolved guards clear every individual ID."""
    if type(request) is not CurvedHphiTrackingRequest:raise ValueError('expected CurvedHphiTrackingRequest')
    request=CurvedHphiTrackingRequest.from_dict(request.to_dict());controls=request.controls
    if any(not hasattr(s,'case') or s.case.modes>controls.max_gram_modes for s in (previous,current)):
        raise ValueError('curved tracking requires dedicated FEM spectra within max_gram_modes')
    previous,current=map(verified_curved_hphi_solution,(previous,current));solutions=previous,current
    counts=request.previous_mode_count,request.current_mode_count
    if any(count>=solution.case.modes for count,solution in zip(counts,solutions)):
        raise ValueError('each tracked positive prefix requires at least one computed upper guard mode')
    grams=curved_hphi_field_grams(previous,current,request.domain,previous_cells=request.previous_cells,
        current_cells=request.current_cells,quadrature_order=controls.quadrature_order+4,
        max_candidate_tests=controls.max_candidate_tests,max_overlay_triangles=controls.max_overlay_triangles,
        max_gram_modes=controls.max_gram_modes,max_sample_points=request.max_sample_points)
    resolutions=[]
    for side,solution,reference in zip(('previous','current'),solutions,(request.domain.previous,request.domain.current)):
        domain=CurvedHphiComparisonDomain(reference,reference,'same_vacuum',restriction_policy=request.domain.restriction_policy)
        resolutions.append(curved_hphi_spectral_resolution(solution,getattr(request,side+'_comparison_geometry'),domain,
            comparison_order=getattr(request,side+'_comparison_order'),quadrature_order=controls.quadrature_order,
            original_cells=getattr(request,side+'_cells'),comparison_cells=getattr(request,side+'_comparison_cells'),
            maximum_relative_projection_error=controls.maximum_relative_projection_error,max_candidate_tests=controls.max_candidate_tests,
            max_overlay_triangles=controls.max_overlay_triangles,max_dofs=controls.max_dofs,max_sample_points=request.max_sample_points))
    groups=[_frequency_groups(s.frequencies_hz,r,controls.relative_cluster_gap) for s,r in zip(solutions,resolutions)]
    guard=[any(min(g)<=n<max(g) for g in partition) for n,partition in zip(counts,groups)]
    na,nb=counts;reports=[];numerical_margin=max(1e-10,32*np.finfo(float).eps*grams.diagnostic['geometry']['triangle_count']*25)
    for name,family in (('electric',grams.electric),('magnetic',grams.magnetic)):
        features=electric_gram_features(family[0][:na,:na],family[1][:na,:nb],family[2][:nb,:nb])
        reports.append(track_sampled_mode_subspaces(*features,np.ones(len(features[0])),previous.frequencies_hz[:na],current.frequencies_hz[:nb],None,
            comparison_description=f'original curved peak {name} in fixed cylindrical components with unitary L2 transport on the complete declared quadratic domain',
            minimum_overlap=controls.minimum_overlap,minimum_assignment_margin=max(controls.minimum_assignment_margin,numerical_margin),
            relative_cluster_gap=controls.relative_cluster_gap,minimum_relative_singular_value=controls.minimum_relative_singular_value,
            previous_identity_groups=_previous_groups(request,groups[0]),current_frequency_groups=[[i for i in g if i<=nb] for g in groups[1] if min(g)<=nb],
            cluster_transition_policy='retain_connected_subspace',minimum_cluster_link=controls.minimum_cluster_link))
    electric,magnetic=reports;reasons=[]
    if any(guard):reasons.append('finite spectral resolution group crosses the tracked band into its upper guard')
    for name,count,resolution in zip(('previous','current'),counts,resolutions):
        if any(row['status']!='PASS' for row in resolution['modes'][:count+1]):
            reasons.append(f'{name} tracked band or first upper guard has unresolved projection or inverse spectrum')
    if electric['status']!='PASS':reasons.append('electric subspace correspondence is incomplete or ambiguous')
    if magnetic['status']!='PASS':reasons.append('magnetic subspace correspondence is incomplete or ambiguous')
    def key(match):return tuple(match['previous_indices']),tuple(match['current_indices']),tuple(match['previous_ids'])
    magnetic_matches={key(m):m for m in magnetic['matches']}
    if set(map(key,electric['matches']))!=set(magnetic_matches):reasons.append('electric and magnetic subspace assignments differ')
    for match in electric['matches']:
        other=magnetic_matches.get(key(match));match['magnetic_principal_overlaps']=None if other is None else other['principal_overlaps']
        match['previous_phase_multiplier']=None
        if match['dimension']==1 and other is not None:
            i,j=match['previous_indices'][0]-1,match['current_indices'][0]-1
            phase=int(np.sign(grams.magnetic[1][i,j]))
            if phase*grams.electric[1][i,j]<=0:reasons.append('electric and magnetic modes require different coefficient phases')
            else:match['previous_phase_multiplier']=phase
    if reasons:electric.update(status='UNVERIFIED',individual_ids_complete=False,current_mode_ids=[None]*nb)
    for match in electric['matches']:match['status']=electric['status']
    electric.update(format='superfish_ng_curved_hphi_tracking_result',result_version=1,request=request.to_dict(),
        verification_reasons=reasons,guard_overlap=guard,spectral_resolution=resolutions,spectral_resolution_groups=groups,
        magnetic_overlap_matrix=magnetic['overlap_matrix'],magnetic_unresolved=magnetic['unresolved'],
        physical_mapping=dict(name=request.domain.mapping,domain=request.domain.to_dict(),previous_frequency_scale=1.,previous_case=previous.case.to_dict(),current_case=current.case.to_dict(),
            integration=grams.diagnostic,electric_grams=[m.tolist() for m in grams.electric],magnetic_grams=[m.tolist() for m in grams.magnetic],
            minimum_numerical_assignment_margin=numerical_margin),
        scope='numerical original curved E/H correspondence under an explicit quadratic domain map; finite comparison-space diagnostics only; no continuous-path mode identity, continuum error bound or surface-peak guarantee')
    return electric

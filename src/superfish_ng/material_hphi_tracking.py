# SPDX-License-Identifier: Apache-2.0
"""Conservative original material E/H subspace tracking with finite-space guards."""
from dataclasses import dataclass,field
from pathlib import Path
import json
import numpy as np
from .config import integer,keys
from .project import parse_json
from .material_hphi_comparison import MaterialHphiComparison
from .material_hphi_field_overlap import verified_material_hphi_solution,material_hphi_field_grams
from .material_hphi_spectral_resolution import material_hphi_spectral_resolution
from .hphi_tracking import HphiTrackingControls,_frequency_groups,_previous_groups
from .mode_tracking import _identity_groups,track_sampled_mode_subspaces
from .planar_tracking_fields import electric_gram_features


@dataclass(frozen=True)
class MaterialHphiTrackingRequest:
    comparison: MaterialHphiComparison
    previous_resolution: MaterialHphiComparison
    current_resolution: MaterialHphiComparison
    previous_mode_count: int=2
    current_mode_count: int=2
    previous_mode_ids: object=('mode-1','mode-2')
    previous_identity_groups: object=None
    previous_comparison_order: int=2
    current_comparison_order: int=2
    controls: HphiTrackingControls=field(default_factory=HphiTrackingControls)
    max_sample_points: int=2000000
    max_interface_tests: int=2000000
    max_interface_pieces: int=250000

    def __post_init__(self):
        for name in ('comparison','previous_resolution','current_resolution'):
            value=getattr(self,name)
            if type(value) is not MaterialHphiComparison:raise ValueError('material tracking requires complete material comparison declarations')
            object.__setattr__(self,name,MaterialHphiComparison.from_dict(value.to_dict()))
        for name in ('previous_mode_count','current_mode_count','previous_comparison_order','current_comparison_order',
                     'max_sample_points','max_interface_tests','max_interface_pieces'):
            integer(getattr(self,name),name)
            if getattr(self,name)<=0:raise ValueError(name+' must be positive')
        if self.previous_comparison_order not in (1,2) or self.current_comparison_order not in (1,2):
            raise ValueError('material comparison orders must be P1 or P2')
        if any(getattr(self,name).mapping!='same_domain' for name in ('previous_resolution','current_resolution')):
            raise ValueError('material spectral declarations require same_domain')
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
        result=dict(format='superfish_ng_material_hphi_tracking_request',tracking_version=1,
                    transport='unitary_fixed_cylindrical_components')
        for name in self.__dataclass_fields__:
            value=getattr(self,name)
            result[name]=value.to_dict() if hasattr(value,'to_dict') else value
        return json.loads(json.dumps(result,allow_nan=False))

    @classmethod
    def from_dict(cls,data):
        fields=list(cls.__dataclass_fields__);names=['format','tracking_version','transport',*fields]
        keys(data,names,names,'material Hphi tracking request')
        if (data['format']!='superfish_ng_material_hphi_tracking_request' or type(data['tracking_version']) is not int
                or data['tracking_version']!=1 or data['transport']!='unitary_fixed_cylindrical_components'):
            raise ValueError('expected material Hphi tracking version 1 with unitary fixed cylindrical transport')
        values={name:data[name] for name in fields}
        for name in ('comparison','previous_resolution','current_resolution'):
            values[name]=MaterialHphiComparison.from_dict(values[name])
        values['controls']=HphiTrackingControls.from_dict(values['controls'])
        return cls(**values)

    @classmethod
    def load(cls,path):return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def save(self,path):
        with Path(path).open('x',encoding='utf-8') as stream:
            stream.write(json.dumps(self.to_dict(),indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def track_material_hphi_modes(previous,current,request):
    """Match original E and H; unresolved guards clear every individual ID."""
    if type(request) is not MaterialHphiTrackingRequest:raise ValueError('expected MaterialHphiTrackingRequest')
    request=MaterialHphiTrackingRequest.from_dict(request.to_dict());controls=request.controls
    if any(not hasattr(s,'case') or s.case.modes>controls.max_gram_modes for s in (previous,current)):
        raise ValueError('material tracking requires dedicated FEM spectra within max_gram_modes')
    previous,current=map(verified_material_hphi_solution,(previous,current));solutions=previous,current
    counts=request.previous_mode_count,request.current_mode_count
    if any(count>=solution.case.modes for count,solution in zip(counts,solutions)):
        raise ValueError('each tracked positive prefix requires at least one computed upper guard mode')
    options=dict(max_candidate_tests=controls.max_candidate_tests,max_overlay_triangles=controls.max_overlay_triangles,
        max_interface_tests=request.max_interface_tests,max_interface_pieces=request.max_interface_pieces,
        max_sample_points=request.max_sample_points)
    for side,solution in zip(('previous','current'),solutions):
        if getattr(request,side+'_resolution').previous_partition.to_dict()!=solution.case.partition.to_dict():
            raise ValueError('material spectral declaration differs from original '+side+' partition')
    grams=material_hphi_field_grams(previous,current,request.comparison,quadrature_order=controls.quadrature_order+4,
        max_gram_modes=controls.max_gram_modes,**options)
    resolutions=[material_hphi_spectral_resolution(solution,getattr(request,side+'_resolution'),
        comparison_order=getattr(request,side+'_comparison_order'),quadrature_order=controls.quadrature_order,
        maximum_relative_projection_error=controls.maximum_relative_projection_error,
        max_dofs=controls.max_dofs,max_modes=controls.max_gram_modes,**options)
        for side,solution in zip(('previous','current'),solutions)]
    groups=[_frequency_groups(s.frequencies_hz,r,controls.relative_cluster_gap) for s,r in zip(solutions,resolutions)]
    guard=[any(min(g)<=n<max(g) for g in partition) for n,partition in zip(counts,groups)]
    na,nb=counts;reports=[];numerical_margin=max(1e-10,32*np.finfo(float).eps*grams.diagnostic['overlay_triangles']*25)
    for name,family in (('electric',grams.electric),('magnetic',grams.magnetic)):
        features=electric_gram_features(family[0][:na,:na],family[1][:na,:nb],family[2][:nb,:nb])
        reports.append(track_sampled_mode_subspaces(*features,np.ones(len(features[0])),previous.frequencies_hz[:na],current.frequencies_hz[:nb],None,
            comparison_description=f'original material peak {name} in fixed cylindrical components with unitary energy-L2 transport on all declared regions and interfaces',
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
    electric.update(format='superfish_ng_material_hphi_tracking_result',result_version=1,request=request.to_dict(),
        verification_reasons=reasons,guard_overlap=guard,spectral_resolution=resolutions,spectral_resolution_groups=groups,
        magnetic_overlap_matrix=magnetic['overlap_matrix'],magnetic_unresolved=magnetic['unresolved'],
        physical_mapping=dict(comparison=request.comparison.to_dict(),previous_frequency_scale=1.,previous_case=previous.case.to_dict(),current_case=current.case.to_dict(),
            integration=grams.diagnostic,electric_grams=[m.tolist() for m in grams.electric],magnetic_grams=[m.tolist() for m in grams.magnetic],
            minimum_numerical_assignment_margin=numerical_margin),
        scope='numerical original material E/H correspondence under an explicit fixed-material domain map; finite comparison-space diagnostics only; no continuous-path mode identity, continuum error bound or surface-peak guarantee')
    return electric

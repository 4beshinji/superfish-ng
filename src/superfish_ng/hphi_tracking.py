# SPDX-License-Identifier: Apache-2.0
"""Conservative E/H subspace correspondence on the same meridional vacuum."""
from dataclasses import dataclass,field
from pathlib import Path
import json
import numpy as np
from .config import integer,keys,positive
from .project import parse_json
from .axis_connected_mesh import AxisConnectedMesh
from .meridional_mesh import MeridionalMesh
from .hphi_field_overlap import _verified_solution,hphi_field_grams
from .hphi_spectral_resolution import hphi_spectral_resolution
from .hphi_geometry_mapping import HphiGeometryMapping
from .mode_tracking import _control,_identity_groups,track_sampled_mode_subspaces
from .planar_tracking_fields import electric_gram_features


@dataclass(frozen=True)
class HphiTrackingControls:
    minimum_overlap: float=.9
    minimum_assignment_margin: float=.1
    relative_cluster_gap: float=.001
    minimum_relative_singular_value: float=1e-8
    minimum_cluster_link: float=.7
    maximum_relative_projection_error: float=.01
    quadrature_order: int=12
    max_candidate_tests: int=2000000
    max_overlay_triangles: int=250000
    max_dofs: int=250000
    max_gram_modes: int=256

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value=getattr(self,name)
            if name.startswith('max_') or name=='quadrature_order':integer(value,name)
            else:object.__setattr__(self,name,_control(value,name,zero=name in ('minimum_assignment_margin','relative_cluster_gap'),one=name not in ('relative_cluster_gap','maximum_relative_projection_error')))
        if not 4<=self.quadrature_order<=32:raise ValueError('Hphi tracking quadrature_order must be from 4 to 32')

    def to_dict(self):return {name:getattr(self,name) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls,data):
        names=list(cls.__dataclass_fields__);keys(data,names,names,'Hphi tracking controls');return cls(**data)


def _mesh(data):
    if not isinstance(data,dict):raise ValueError('Hphi comparison mesh must be a complete mesh object')
    if data.get('format')=='superfish_ng_axis_connected_mesh':return AxisConnectedMesh.from_dict(data)
    return MeridionalMesh.from_dict(data)


@dataclass(frozen=True)
class HphiTrackingRequest:
    previous_comparison_mesh: object
    current_comparison_mesh: object
    previous_mode_count: int=2
    current_mode_count: int=2
    previous_mode_ids: object=('mode-1','mode-2')
    previous_identity_groups: object=None
    previous_comparison_order: int=2
    current_comparison_order: int=2
    controls: HphiTrackingControls=field(default_factory=HphiTrackingControls)

    def __post_init__(self):
        for name in ('previous_mode_count','current_mode_count','previous_comparison_order','current_comparison_order'):
            integer(getattr(self,name),name)
        if self.previous_comparison_order not in (1,2) or self.current_comparison_order not in (1,2):
            raise ValueError('comparison orders must be P1 or P2')
        for name in ('previous_comparison_mesh','current_comparison_mesh'):
            mesh=getattr(self,name)
            if type(mesh) not in (AxisConnectedMesh,MeridionalMesh):raise ValueError('Hphi tracking requires two explicit comparison meshes')
            object.__setattr__(self,name,_mesh(mesh.to_dict()))
        if not isinstance(self.controls,HphiTrackingControls):raise ValueError('expected HphiTrackingControls')
        if self.previous_identity_groups is not None:
            if self.previous_mode_ids is not None:raise ValueError('supply individual IDs or identity groups, never both')
            object.__setattr__(self,'previous_identity_groups',_identity_groups(self.previous_identity_groups,self.previous_mode_count))
        else:
            ids=self.previous_mode_ids
            if (not isinstance(ids,(tuple,list)) or len(ids)!=self.previous_mode_count
                    or any(type(i) is not str or not i.strip() for i in ids) or len(set(ids))!=len(ids)):
                raise ValueError('one distinct nonempty previous ID is required per tracked positive rank')
            object.__setattr__(self,'previous_mode_ids',tuple(ids))

    def to_dict(self):
        return dict(format='superfish_ng_hphi_tracking_request',tracking_version=1,mapping='same_vacuum',
            previous_comparison_mesh=self.previous_comparison_mesh.to_dict(),current_comparison_mesh=self.current_comparison_mesh.to_dict(),
            previous_mode_count=self.previous_mode_count,current_mode_count=self.current_mode_count,
            previous_mode_ids=None if self.previous_mode_ids is None else list(self.previous_mode_ids),
            previous_identity_groups=json.loads(json.dumps(self.previous_identity_groups)),
            previous_comparison_order=self.previous_comparison_order,current_comparison_order=self.current_comparison_order,controls=self.controls.to_dict())

    @classmethod
    def from_dict(cls,data):
        names=['format','tracking_version','mapping',*cls.__dataclass_fields__];keys(data,names,names,'Hphi tracking request')
        if data['format']!='superfish_ng_hphi_tracking_request' or type(data['tracking_version']) is not int or data['tracking_version']!=1 or data['mapping']!='same_vacuum':
            raise ValueError('expected Hphi tracking_version 1 with explicit same_vacuum mapping')
        if data['previous_mode_ids'] is not None and type(data['previous_mode_ids']) is not list:
            raise ValueError('previous_mode_ids must be a JSON list or null')
        return cls(**{name:(_mesh(data[name]) if name.endswith('_mesh') else HphiTrackingControls.from_dict(data[name]) if name=='controls' else data[name]) for name in cls.__dataclass_fields__})

    @classmethod
    def load(cls,path):return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def save(self,path):
        with Path(path).open('x',encoding='utf-8') as stream:stream.write(json.dumps(self.to_dict(),indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def _frequency_groups(frequencies,resolution,gap):
    groups=[];upper=None
    for i,(frequency,interval) in enumerate(zip(frequencies,resolution['nearby_comparison_frequency_intervals_hz'])):
        if i and (frequency-frequencies[i-1]<=gap*frequency or upper is None or interval[0]<=upper):
            groups[-1].append(i+1);upper=None if upper is None or interval[1] is None else max(upper,interval[1])
        else:groups.append([i+1]);upper=interval[1]
    return groups


def _previous_groups(request,resolution_groups):
    declared=request.previous_identity_groups
    if declared is None:declared=[dict(indices=[i+1],ids=[v]) for i,v in enumerate(request.previous_mode_ids)]
    groups=[(set(g['indices']),set(g['ids'])) for g in declared]
    for ranks in resolution_groups:
        relevant=set(ranks)&set(range(1,request.previous_mode_count+1))
        touching=[i for i,(indices,_) in enumerate(groups) if relevant&indices]
        if len(touching)>1:
            combined=(set().union(*(groups[i][0] for i in touching)),set().union(*(groups[i][1] for i in touching)))
            groups=[g for i,g in enumerate(groups) if i not in touching]+[combined]
    return [dict(indices=sorted(ranks),ids=sorted(ids)) for ranks,ids in sorted(groups,key=lambda g:min(g[0]))]


def track_hphi_modes(previous,current,request):
    """Match complete finite prefix bands conservatively in both E and H.

    Multidimensional matches carry ID sets only. A failed guard, projection,
    assignment or E/H consistency check clears every current individual ID.
    Saved frequencies and coefficients are never changed by tracking.
    """
    return _track_hphi_modes(previous,current,request)


def track_mapped_hphi_modes(previous,current,request,mapping):
    """Track with explicit unitary component comparison under a geometry map.

    The finite spectral diagnostics stay in each original physical domain.
    No nonuniform frequency scaling is inferred. The version-1 same-vacuum
    request supplies bands, IDs, controls and each original comparison mesh;
    the returned declaration replaces its mapping with the complete geometry.
    """
    if type(mapping) is not HphiGeometryMapping:
        raise ValueError('expected HphiGeometryMapping')
    return _track_hphi_modes(previous,current,request,geometry_mapping=mapping)


def _track_hphi_modes(previous,current,request,*,previous_scale=None,geometry_mapping=None):
    """Shared Hphi assessment; the tune caller explicitly supplies its scale.

    Spectral resolution is computed in each original SI domain. Only the
    previous frequencies passed to correspondence use the current length scale.
    The public version-1 reader and same-vacuum entry point remain unchanged.
    """
    if geometry_mapping is not None:
        if previous_scale is not None:
            raise ValueError('supply geometry_mapping or previous_scale, never both')
        if type(geometry_mapping) is not HphiGeometryMapping:
            raise ValueError('expected HphiGeometryMapping')
        geometry_mapping=HphiGeometryMapping.from_dict(geometry_mapping.to_dict())
    scaled = previous_scale is not None
    scale = positive(previous_scale, 'previous_scale') if scaled else 1.
    if not isinstance(request,HphiTrackingRequest):raise ValueError('expected HphiTrackingRequest')
    request=HphiTrackingRequest.from_dict(request.to_dict());controls=request.controls
    if any(not hasattr(s,'case') or s.case.modes>controls.max_gram_modes for s in (previous,current)):
        raise ValueError('Hphi tracking requires dedicated FEM spectra within max_gram_modes')
    previous,current=map(_verified_solution,(previous,current));solutions=previous,current
    counts=request.previous_mode_count,request.current_mode_count
    if any(count>=solution.case.modes for count,solution in zip(counts,solutions)):
        raise ValueError('each tracked positive prefix requires at least one computed upper guard mode')
    grams=hphi_field_grams(previous,current,max_candidate_tests=controls.max_candidate_tests,
        max_overlay_triangles=controls.max_overlay_triangles,max_gram_modes=controls.max_gram_modes,previous_scale=scale,geometry_mapping=geometry_mapping)
    resolutions=[hphi_spectral_resolution(solution,mesh,comparison_order=order,quadrature_order=controls.quadrature_order,
        maximum_relative_projection_error=controls.maximum_relative_projection_error,max_candidate_tests=controls.max_candidate_tests,
        max_overlay_triangles=controls.max_overlay_triangles,max_dofs=controls.max_dofs)
        for solution,mesh,order in zip(solutions,(request.previous_comparison_mesh,request.current_comparison_mesh),
            (request.previous_comparison_order,request.current_comparison_order))]
    groups=[_frequency_groups(s.frequencies_hz,r,controls.relative_cluster_gap) for s,r in zip(solutions,resolutions)]
    guard=[any(min(g)<=n<max(g) for g in partition) for n,partition in zip(counts,groups)]
    na,nb=counts;reports=[];numerical_margin=max(1e-10,32*np.finfo(float).eps*grams.diagnostic['overlay_triangles']*25)
    for name,family in (('electric',grams.electric),('magnetic',grams.magnetic)):
        features=electric_gram_features(family[0][:na,:na],family[1][:na,:nb],family[2][:nb,:nb])
        reports.append(track_sampled_mode_subspaces(*features,np.ones(len(features[0])),previous.frequencies_hz[:na]/scale,current.frequencies_hz[:nb],None,
            comparison_description=(f'original peak {name} in fixed cylindrical components with unitary L2 transport; current 2*pi*r dr dz' if geometry_mapping is not None
                                    else f'all original peak {name} components with declared uniform-scale pull-forward; current 2*pi*r dr dz' if scaled
                                    else f'all original peak {name} components on exactly the same vacuum; 2*pi*r dr dz'),
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
    electric.update(format='superfish_ng_hphi_tracking_result',result_version=1,request=request.to_dict(),
        verification_reasons=reasons,guard_overlap=guard,spectral_resolution=resolutions,spectral_resolution_groups=groups,
        magnetic_overlap_matrix=magnetic['overlap_matrix'],magnetic_unresolved=magnetic['unresolved'],
        physical_mapping=dict(name='same_vacuum',previous_case=previous.case.to_dict(),current_case=current.case.to_dict(),
            integration=grams.diagnostic,electric_grams=[m.tolist() for m in grams.electric],magnetic_grams=[m.tolist() for m in grams.magnetic],
            minimum_numerical_assignment_margin=numerical_margin),
        scope='numerical E/H subspace correspondence on exactly the same vacuum; finite comparison-space diagnostics only; no continuous-path mode identity, continuum error bound or surface-peak guarantee')
    if scaled:
        declaration=request.to_dict()
        declaration.pop('tracking_version')
        declaration.update(format='superfish_ng_hphi_tune_comparison',comparison_version=1,
                           mapping=dict(kind='uniform_scale',previous_scale=scale))
        electric.update(format='superfish_ng_hphi_tune_tracking_result',request=declaration,
            scope='explicit uniform-scale original E/H correspondence; original-domain finite spectral diagnostics; no continuous-path identity or continuum error bound')
        electric['physical_mapping']['name']='uniform_scale'
        electric['physical_mapping']['previous_frequency_scale']=1/scale
        electric['physical_mapping']['previous_original_frequencies_hz']=previous.frequencies_hz.tolist()
    if geometry_mapping is not None:
        declaration=request.to_dict()
        declaration.pop('tracking_version')
        declaration.update(format='superfish_ng_hphi_mapped_comparison',comparison_version=1,
            mapping=geometry_mapping.to_dict(),transport='unitary_fixed_cylindrical_components')
        electric.update(format='superfish_ng_hphi_mapped_tracking_result',request=declaration,
            scope='explicit nonuniform geometry comparison of original E/H; unitary fixed components; original-domain finite spectral diagnostics; no continuous-path identity or continuum error bound')
        electric['physical_mapping'].update(name='piecewise_affine',previous_frequency_scale=1.,
            previous_original_frequencies_hz=previous.frequencies_hz.tolist())
    return electric

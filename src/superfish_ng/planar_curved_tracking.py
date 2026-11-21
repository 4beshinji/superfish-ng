# SPDX-License-Identifier: Apache-2.0
"""Original curved xy E/H subspaces with fixed-boundary finite guards."""
from dataclasses import dataclass, field
from pathlib import Path
import json
import numpy as np
from .config import integer, keys
from .project import parse_json
from .mode_tracking import _control, _identity_groups, track_sampled_mode_subspaces
from .planar_tracking import _previous_groups
from .planar_tracking_fields import electric_gram_features
from .planar_tracking_resolution import resolution_frequency_groups
from .planar_curved_comparison import PlanarCurvedComparisonDomain, _fraction, _cross
from .planar_curved_field_overlap import verified_planar_curved_solution, planar_curved_field_grams
from .planar_curved_spectral_resolution import planar_curved_spectral_resolution


@dataclass(frozen=True)
class PlanarCurvedTrackingControls:
    minimum_overlap: float = .9
    minimum_assignment_margin: float = .1
    relative_cluster_gap: float = .001
    minimum_relative_singular_value: float = 1e-8
    minimum_cluster_link: float = .7
    quadrature_order: int = 16
    max_pair_tests_per_comparison: int = 2000000
    max_comparison_triangles: int = 250000
    max_refined_triangles_per_side: int = 250000
    max_dofs_per_side: int = 250000
    max_gram_modes: int = 256
    max_field_sample_points: int = 2000000
    max_enrichment_sample_points_per_side: int = 2000000

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if name.startswith('max_') or name == 'quadrature_order':
                integer(value, name, 4 if name == 'quadrature_order' else 1)
            else:
                object.__setattr__(self, name, _control(value, name,
                    zero=name in ('minimum_assignment_margin', 'relative_cluster_gap'),
                    one=name != 'relative_cluster_gap'))
        if self.quadrature_order > 28:
            raise ValueError('curved planar tracking quadrature_order must be 4 through 28; field verification uses order+4')

    def to_dict(self):return {name:getattr(self, name) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data):
        names = list(cls.__dataclass_fields__)
        keys(data, names, names, 'curved planar tracking controls')
        return cls(**data)


def _charts(value, reference):
    if value is None:return None
    if type(value) is not list:raise ValueError('curved planar native charts require a JSON list or null')
    result = []
    for row in value:
        keys(row, ['base_cell', 'reference_vertices'], ['base_cell', 'reference_vertices'], 'curved planar tracking chart')
        owner = integer(row['base_cell'], 'base_cell', 0)
        if owner >= len(reference.cell_nodes):raise ValueError('curved planar native chart base_cell is outside its reference domain')
        raw = row['reference_vertices']
        if type(raw) is not list or len(raw) != 3 or any(type(p) is not list or len(p) != 2 for p in raw):
            raise ValueError('native chart requires three rational reference vertices')
        points = tuple(tuple(_fraction(v) for v in p) for p in raw)
        if any(min(p) < 0 or sum(p) > 1 for p in points) or _cross(*points) <= 0:
            raise ValueError('native chart must be a positive triangle inside the closed reference triangle')
        result.append(dict(base_cell=owner, reference_vertices=[[[v.numerator,v.denominator] for v in p] for p in points]))
    return result


@dataclass(frozen=True)
class PlanarCurvedTrackingRequest:
    domain: PlanarCurvedComparisonDomain
    previous_mode_count: int = 2
    current_mode_count: int = 2
    previous_mode_ids: object = ('mode-1', 'mode-2')
    previous_identity_groups: object = None
    previous_cells: object = None
    current_cells: object = None
    controls: PlanarCurvedTrackingControls = field(default_factory=PlanarCurvedTrackingControls)

    def __post_init__(self):
        if type(self.domain) is not PlanarCurvedComparisonDomain:
            raise ValueError('curved planar tracking requires an explicit full quadratic comparison domain')
        object.__setattr__(self, 'domain', PlanarCurvedComparisonDomain.from_dict(self.domain.to_dict()))
        for name in ('previous_mode_count', 'current_mode_count'):integer(getattr(self, name), name)
        for name, reference in (('previous_cells', self.domain.previous), ('current_cells', self.domain.current)):
            object.__setattr__(self, name, _charts(getattr(self, name), reference))
        if type(self.controls) is not PlanarCurvedTrackingControls:raise ValueError('expected PlanarCurvedTrackingControls')
        object.__setattr__(self, 'controls', PlanarCurvedTrackingControls.from_dict(self.controls.to_dict()))
        if self.previous_identity_groups is not None:
            if self.previous_mode_ids is not None:raise ValueError('supply previous_mode_ids or previous_identity_groups, never both')
            object.__setattr__(self, 'previous_identity_groups', _identity_groups(self.previous_identity_groups, self.previous_mode_count))
        else:
            ids = self.previous_mode_ids
            if (type(ids) not in (tuple, list) or len(ids) != self.previous_mode_count
                    or any(type(v) is not str or not v.strip() for v in ids) or len(set(ids)) != len(ids)):
                raise ValueError('one distinct nonempty ID is required for each previous positive band rank')
            object.__setattr__(self, 'previous_mode_ids', tuple(ids))

    def to_dict(self):
        values = {name:getattr(self, name).to_dict() if hasattr(getattr(self, name), 'to_dict') else getattr(self, name)
                  for name in self.__dataclass_fields__}
        return json.loads(json.dumps(dict(format='superfish_ng_planar_curved_tracking_request', tracking_version=1,
            transport='unitary_fixed_cartesian_components', **values), allow_nan=False))

    @classmethod
    def from_dict(cls, data):
        names = ['format', 'tracking_version', 'transport', *cls.__dataclass_fields__]
        keys(data, names, names, 'curved planar tracking request')
        if (data['format'] != 'superfish_ng_planar_curved_tracking_request' or type(data['tracking_version']) is not int
                or data['tracking_version'] != 1 or data['transport'] != 'unitary_fixed_cartesian_components'):
            raise ValueError('expected curved planar tracking version 1 with fixed Cartesian unitary transport')
        values = {name:data[name] for name in cls.__dataclass_fields__}
        values['domain'] = PlanarCurvedComparisonDomain.from_dict(values['domain'])
        values['controls'] = PlanarCurvedTrackingControls.from_dict(values['controls'])
        return cls(**values)

    @classmethod
    def load(cls, path):return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def save(self, path):
        with Path(path).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(self.to_dict(), ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def track_planar_curved_modes(previous, current, request):
    """Match E and H independently; all individual IDs clear on guard failure."""
    if type(request) is not PlanarCurvedTrackingRequest:raise ValueError('expected PlanarCurvedTrackingRequest')
    request = PlanarCurvedTrackingRequest.from_dict(request.to_dict())
    controls = request.controls
    previous, current = map(verified_planar_curved_solution, (previous, current))
    counts = request.previous_mode_count, request.current_mode_count
    if any(count >= solution.case.modes for count, solution in zip(counts, (previous, current))):
        raise ValueError('each tracked positive prefix requires at least one computed upper guard mode')
    grams = planar_curved_field_grams(previous, current, request.domain, previous_cells=request.previous_cells,
        current_cells=request.current_cells, quadrature_order=controls.quadrature_order,
        max_pair_tests=controls.max_pair_tests_per_comparison, max_triangles=controls.max_comparison_triangles,
        max_gram_modes=controls.max_gram_modes, max_sample_points=controls.max_field_sample_points)
    resolutions = [planar_curved_spectral_resolution(s, quadrature_order=controls.quadrature_order,
        max_refined_triangles=controls.max_refined_triangles_per_side, max_dofs=controls.max_dofs_per_side,
        max_pair_tests=controls.max_pair_tests_per_comparison,
        max_sample_points=controls.max_enrichment_sample_points_per_side) for s in (previous, current)]
    groups = [resolution_frequency_groups(s.frequencies_hz, r, controls.relative_cluster_gap)
              for s, r in zip((previous, current), resolutions)]
    guards = [any(min(g) <= count < max(g) for g in partition) for count, partition in zip(counts, groups)]
    na, nb = counts
    floor = max(1e-10, 32*np.finfo(float).eps*grams.diagnostic['geometry']['triangle_count']*(controls.quadrature_order+4)**2)
    reports = []
    for name, family in (('electric', grams.electric), ('magnetic', grams.magnetic)):
        features = electric_gram_features(family[0][:na,:na], family[1][:na,:nb], family[2][:nb,:nb])
        reports.append(track_sampled_mode_subspaces(*features, np.ones(len(features[0])),
            previous.frequencies_hz[:na], current.frequencies_hz[:nb], None,
            comparison_description=f'original curved peak {name} in fixed Cartesian components with square-root actual native dx dy density',
            minimum_overlap=controls.minimum_overlap, minimum_assignment_margin=max(controls.minimum_assignment_margin, floor),
            relative_cluster_gap=controls.relative_cluster_gap, minimum_relative_singular_value=controls.minimum_relative_singular_value,
            previous_identity_groups=_previous_groups(request, groups[0]),
            current_frequency_groups=[[i for i in g if i <= nb] for g in groups[1] if min(g) <= nb],
            cluster_transition_policy='retain_connected_subspace', minimum_cluster_link=controls.minimum_cluster_link))
    electric, magnetic = reports
    reasons = []
    if any(guards):reasons.append('finite spectral resolution group crosses the tracked prefix into its upper guard')
    for side, count, resolution in zip(('previous', 'current'), counts, resolutions):
        if any(row['status'] != 'PASS' for row in resolution['modes'][:count+1]):
            reasons.append(f'{side} tracked prefix or first upper guard has unresolved inverse spectrum')
    for name, report in zip(('electric', 'magnetic'), reports):
        if report['status'] != 'PASS':reasons.append(f'{name} subspace correspondence is incomplete or ambiguous')
    def key(match):return tuple(match['previous_indices']), tuple(match['current_indices']), tuple(match['previous_ids'])
    matches = {key(match):match for match in magnetic['matches']}
    if set(map(key, electric['matches'])) != set(matches):reasons.append('electric and magnetic subspace assignments differ')
    for match in electric['matches']:
        other = matches.get(key(match))
        match['magnetic_principal_overlaps'] = None if other is None else other['principal_overlaps']
        match['previous_phase_multiplier'] = None
        if match['dimension'] == 1 and other is not None:
            i, j = match['previous_indices'][0]-1, match['current_indices'][0]-1
            phase = int(np.sign(grams.electric[1][i,j]))
            if phase*grams.magnetic[1][i,j] <= 0:reasons.append('electric and magnetic fields require different original coefficient phases')
            else:match['previous_phase_multiplier'] = phase
    if reasons:electric.update(status='UNVERIFIED', individual_ids_complete=False, current_mode_ids=[None]*nb)
    for match in electric['matches']:match['status'] = electric['status']
    electric.update(format='superfish_ng_planar_curved_tracking_result', result_version=1, request=request.to_dict(),
        verification_reasons=reasons, guard_overlap=guards, spectral_resolution=resolutions, spectral_resolution_groups=groups,
        magnetic_overlap_matrix=magnetic['overlap_matrix'], magnetic_unresolved=magnetic['unresolved'],
        physical_mapping=dict(name=request.domain.mapping, domain=request.domain.to_dict(), previous_case=previous.case.to_dict(),
            current_case=current.case.to_dict(), integration=grams.diagnostic,
            electric_grams=[m.tolist() for m in grams.electric], magnetic_grams=[m.tolist() for m in grams.magnetic],
            minimum_numerical_assignment_margin=floor),
        scope='original curved Cartesian E/H subspaces under an explicit quadratic correspondence; finite guards only; no continuous-path identity, continuum error bound or surface-peak guarantee')
    return electric

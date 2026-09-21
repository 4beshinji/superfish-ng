# SPDX-License-Identifier: Apache-2.0
"""Declared planar electric-field correspondence with guarded mode bands."""
from dataclasses import dataclass, field
import json
from pathlib import Path
import numpy as np
from .config import integer, keys
from .project import parse_json
from .mode_tracking import _control, _identity_groups, track_sampled_mode_subspaces
from .planar_tracking_fields import verified_rectangular_solutions, _electric_grams, electric_gram_features
from .planar_tracking_overlap import rectangle_tracking_overlay
from .planar_tracking_resolution import rectangle_spectral_resolution, polygon_spectral_resolution, resolution_frequency_groups
from .planar_tracking_polygon import PolygonScaleMapping, polygon_scale_overlay
from .planar_tracking_similarity import PolygonSimilarityMapping, polygon_similarity_overlay
from .planar_tracking_resolution import similarity_spectral_resolution
from .planar_tracking_remesh import PolygonRemeshMapping, polygon_remesh_overlay
from .planar_tracking_similarity_remesh import PolygonSimilarityRemeshMapping, polygon_similarity_remesh_overlay
from .planar_tracking_affine_remesh import PolygonAffineRemeshMapping, polygon_affine_remesh_overlay
from .planar_tracking_exact_mapping import PolygonExactAffineRemeshMapping, polygon_exact_affine_remesh_overlay
from .planar_affine_shape_mapping import PlanarAffineShapeMapping, affine_shape_overlay


@dataclass(frozen=True)
class PlanarTrackingControls:
    minimum_overlap: float = .9
    minimum_assignment_margin: float = .1
    relative_cluster_gap: float = .001
    minimum_relative_singular_value: float = 1e-8
    minimum_cluster_link: float = .7
    max_overlay_triangles: int = 250000
    max_refined_triangles: int = 250000

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if name.startswith('max_'):
                integer(value, name)
            else:
                object.__setattr__(self, name, _control(value, name,
                    zero=name in ('minimum_assignment_margin', 'relative_cluster_gap'),
                    one=name != 'relative_cluster_gap'))

    def to_dict(self):
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data):
        names = list(cls.__dataclass_fields__)
        keys(data, names, names, 'planar tracking controls')
        return cls(**data)


@dataclass(frozen=True)
class PlanarTrackingRequest:
    previous_mode_count: int = 2
    current_mode_count: int = 2
    previous_mode_ids: object = ('mode-1', 'mode-2')
    previous_identity_groups: object = None
    mapping: object = 'normalized_rectangle'
    controls: PlanarTrackingControls = field(default_factory=PlanarTrackingControls)

    def __post_init__(self):
        integer(self.previous_mode_count, 'previous_mode_count')
        integer(self.current_mode_count, 'current_mode_count')
        if not isinstance(self.mapping, (PolygonScaleMapping, PolygonSimilarityMapping, PolygonRemeshMapping, PolygonSimilarityRemeshMapping, PolygonAffineRemeshMapping, PolygonExactAffineRemeshMapping, PlanarAffineShapeMapping)) and self.mapping != 'normalized_rectangle':
            raise ValueError('planar tracking requires normalized_rectangle or a declared polygon mapping (scale, similarity, remesh, affine, exact affine, or polynomial affine shape)')
        if not isinstance(self.controls, PlanarTrackingControls):
            raise ValueError('expected PlanarTrackingControls')
        ids, groups = self.previous_mode_ids, self.previous_identity_groups
        if groups is not None:
            if ids is not None:
                raise ValueError('supply previous_mode_ids or previous_identity_groups, never both')
            object.__setattr__(self, 'previous_identity_groups', _identity_groups(groups, self.previous_mode_count))
        elif (not isinstance(ids, (list, tuple)) or len(ids) != self.previous_mode_count
              or any(type(v) is not str or not v.strip() for v in ids) or len(set(ids)) != len(ids)):
            raise ValueError('previous_mode_ids requires one distinct nonempty ID for each previous band rank')
        else:
            object.__setattr__(self, 'previous_mode_ids', tuple(ids))

    def to_dict(self):
        return dict(format='superfish_ng_planar_tracking_request', tracking_version=8 if isinstance(self.mapping, PlanarAffineShapeMapping) else 7 if isinstance(self.mapping, PolygonExactAffineRemeshMapping) else 6 if isinstance(self.mapping, PolygonAffineRemeshMapping) else 5 if isinstance(self.mapping, PolygonSimilarityRemeshMapping) else 4 if isinstance(self.mapping, PolygonRemeshMapping) else 3 if isinstance(self.mapping, PolygonSimilarityMapping) else 2 if isinstance(self.mapping, PolygonScaleMapping) else 1,
                    mapping=self.mapping.to_dict() if isinstance(self.mapping, (PolygonScaleMapping, PolygonSimilarityMapping, PolygonRemeshMapping, PolygonSimilarityRemeshMapping, PolygonAffineRemeshMapping, PolygonExactAffineRemeshMapping, PlanarAffineShapeMapping)) else self.mapping, previous_mode_count=self.previous_mode_count,
                    current_mode_count=self.current_mode_count,
                    previous_mode_ids=list(self.previous_mode_ids) if self.previous_mode_ids is not None else None,
                    previous_identity_groups=json.loads(json.dumps(self.previous_identity_groups)),
                    controls=self.controls.to_dict())

    @classmethod
    def from_dict(cls, data):
        names = ['format', 'tracking_version', 'mapping', 'previous_mode_count', 'current_mode_count',
                 'previous_mode_ids', 'previous_identity_groups', 'controls']
        keys(data, names, names, 'planar tracking request')
        if (data['format'] != 'superfish_ng_planar_tracking_request'
                or type(data['tracking_version']) is not int or data['tracking_version'] not in (1, 2, 3, 4, 5, 6, 7, 8)):
            raise ValueError('expected superfish_ng_planar_tracking_request tracking_version 1, 2, 3, 4, 5, 6, 7 or 8')
        mapping = (PlanarAffineShapeMapping.from_dict(data['mapping']) if data['tracking_version']==8
                   else PolygonExactAffineRemeshMapping.from_dict(data['mapping']) if data['tracking_version']==7
                   else PolygonAffineRemeshMapping.from_dict(data['mapping']) if data['tracking_version']==6
                   else PolygonSimilarityRemeshMapping.from_dict(data['mapping']) if data['tracking_version']==5
                   else PolygonRemeshMapping.from_dict(data['mapping']) if data['tracking_version']==4
                   else PolygonSimilarityMapping.from_dict(data['mapping']) if data['tracking_version']==3
                   else PolygonScaleMapping.from_dict(data['mapping']) if data['tracking_version']==2 else data['mapping'])
        if data['tracking_version'] == 1 and mapping != 'normalized_rectangle':
            raise ValueError('tracking_version 1 requires normalized_rectangle mapping')
        if data['previous_mode_ids'] is not None and type(data['previous_mode_ids']) is not list:
            raise ValueError('previous_mode_ids must be a JSON list or null')
        return cls(data['previous_mode_count'], data['current_mode_count'], data['previous_mode_ids'],
                   data['previous_identity_groups'], mapping, PlanarTrackingControls.from_dict(data['controls']))

    @classmethod
    def load(cls, path):
        return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def save(self, path):
        with Path(path).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(self.to_dict(), ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def _previous_groups(request, resolved_groups):
    count = request.previous_mode_count
    declared = request.previous_identity_groups
    if declared is None:
        declared = [dict(indices=[i+1], ids=[v]) for i, v in enumerate(request.previous_mode_ids)]
    parent = list(range(count))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for group in [g['indices'] for g in declared]+resolved_groups:
        ranks = [i-1 for i in group if i <= count]
        for i in ranks[1:]:
            parent[find(i)] = find(ranks[0])
    components = {}
    for i in range(count):
        components.setdefault(find(i), []).append(i+1)
    return [dict(indices=indices, ids=sorted(v for g in declared if set(g['indices']) <= set(indices) for v in g['ids']))
            for indices in sorted(components.values())]


def track_planar_modes(previous, current, request):
    """Compare finite FEM subspaces; a passed match is not a continuous-path proof."""
    if not isinstance(request, PlanarTrackingRequest):
        raise ValueError('expected PlanarTrackingRequest')
    request = PlanarTrackingRequest.from_dict(request.to_dict())
    remesh = isinstance(request.mapping, PolygonRemeshMapping)
    similarity = isinstance(request.mapping, PolygonSimilarityMapping)
    composed = isinstance(request.mapping, PolygonSimilarityRemeshMapping)
    affine = isinstance(request.mapping, PolygonAffineRemeshMapping)
    exact_affine = isinstance(request.mapping, PolygonExactAffineRemeshMapping)
    shape = isinstance(request.mapping, PlanarAffineShapeMapping)
    polygon = isinstance(request.mapping, (PolygonScaleMapping, PolygonSimilarityMapping, PolygonRemeshMapping,
                                           PolygonSimilarityRemeshMapping, PolygonAffineRemeshMapping, PolygonExactAffineRemeshMapping, PlanarAffineShapeMapping))
    if polygon:
        from .planar import PlanarSolution
        from .planar_polygon import PlanarPolygonCase
        from .planar_project import PlanarProject
        from .planar_convergence_compare import _verified_solution
        if any(not isinstance(s, PlanarSolution) or not isinstance(s.case, PlanarPolygonCase) for s in (previous, current)):
            raise ValueError('polygon tracking requires explicit polygon Case schema_version 2 on both sides')
        previous, current = [_verified_solution(s, PlanarProject(s.case)) for s in (previous, current)]
        if previous.case.polarization != current.case.polarization:
            raise ValueError('planar tracking cannot mix TE and TM polarizations')
    else:
        previous, current = verified_rectangular_solutions(previous, current)
    counts = (request.previous_mode_count, request.current_mode_count)
    if any(count >= solution.case.modes for count, solution in zip(counts, (previous, current))):
        raise ValueError('each tracked positive prefix band requires at least one computed upper guard mode')
    controls = request.controls
    if shape:
        overlay, shape_transport = affine_shape_overlay(previous.case.mesh, current.case.mesh, request.mapping,
                                                        max_overlay_triangles=controls.max_overlay_triangles)
    elif polygon:
        overlay = (polygon_exact_affine_remesh_overlay if exact_affine else polygon_affine_remesh_overlay if affine else polygon_similarity_remesh_overlay if composed else polygon_remesh_overlay if remesh else polygon_similarity_overlay if similarity else polygon_scale_overlay)(previous.case.mesh, current.case.mesh, request.mapping,
                                        max_overlay_triangles=controls.max_overlay_triangles)
    else:
        overlay = rectangle_tracking_overlay((previous.case.nx, previous.case.ny), (current.case.nx, current.case.ny),
                                             max_overlay_triangles=controls.max_overlay_triangles)
    rotation = (shape_transport if shape else request.mapping.current_to_previous_linear if affine or exact_affine
                else request.mapping.current_to_previous_rotation if similarity or composed else None)
    grams = _electric_grams(previous, current, overlay, 3, current_to_previous_rotation=rotation)
    higher = _electric_grams(previous, current, overlay, 5, current_to_previous_rotation=rotation)
    a_norm, b_norm = np.sqrt(np.diag(grams[0])), np.sqrt(np.diag(grams[2]))
    discrepancies = [float(np.max(abs(a-b)/left[:, None]/right[None, :]))
                     for a, b, left, right in zip(grams, higher,
                        (a_norm, a_norm, b_norm), (a_norm, b_norm, b_norm))]
    resolutions = [(similarity_spectral_resolution if similarity or remesh or composed or affine or exact_affine or shape else polygon_spectral_resolution if polygon else rectangle_spectral_resolution)(s, max_refined_triangles=controls.max_refined_triangles)
                   for s in (previous, current)]
    groups = [resolution_frequency_groups(s.frequencies_hz, r, controls.relative_cluster_gap)
              for s, r in zip((previous, current), resolutions)]
    edge_unresolved = [any(min(group) <= count < max(group) for group in partition)
                       for count, partition in zip(counts, groups)]
    na, nb = counts
    numerical_margin_floor = max(1e-10, 32*np.finfo(float).eps*len(overlay.previous_cells)*25)
    features = electric_gram_features(grams[0][:na, :na], grams[1][:na, :nb], grams[2][:nb, :nb])
    result = track_sampled_mode_subspaces(*features, np.ones(len(features[0])),
        previous.frequencies_hz[:na], current.frequencies_hz[:nb], None,
        comparison_description=('physical peak E on regenerated polynomial-affine trial meshes with a shared original dyadic reference partition; per-cell adjugate transport and previous physical xy area' if shape else 'all physical peak E components under a rationally evaluated affine map with independent boundary and interior subdivisions; current transverse vectors transported by the adjugate of the effective map; original element polynomials integrated on current physical xy area' if exact_affine else 'all physical peak E components under the declared invertible proper or orientation-reversing affine map with an independently meshed interior on the exact transformed boundary; current transverse vectors transported by the adjugate of the effective linear map; exact intersections of the two element unions' if affine else 'all physical peak E components under the declared proper similarity with an independently meshed interior on the exact transformed boundary; current vectors rotated into the previous frame; exact intersections of the two element unions' if composed else 'all physical peak E components under the declared proper similarity; current vectors in the previous frame; previous original physical xy area' if similarity else 'all physical peak E components composed with the declared origin polygon scale; verified nested original elements; previous physical xy area' if polygon else 'all physical peak E components pulled back by x=a*rho, y=b*eta; exact rectangle triangle intersections; reference area d_rho d_eta'),
        minimum_overlap=controls.minimum_overlap, minimum_assignment_margin=max(controls.minimum_assignment_margin, numerical_margin_floor),
        relative_cluster_gap=controls.relative_cluster_gap,
        minimum_relative_singular_value=controls.minimum_relative_singular_value,
        previous_identity_groups=_previous_groups(request, groups[0]),
        current_frequency_groups=[[i for i in group if i <= nb] for group in groups[1] if min(group) <= nb],
        cluster_transition_policy='retain_connected_subspace', minimum_cluster_link=controls.minimum_cluster_link)
    reasons = []
    if max(discrepancies) > 1e-10:
        reasons.append('electric Gram integration is not stable between orders 3 and 5')
    if any(edge_unresolved):
        reasons.append('spectral resolution group reaches beyond a tracked band into its guard mode')
    for match in result['matches']:
        match['previous_phase_multiplier'] = (int(np.sign(grams[1][match['previous_indices'][0]-1, match['current_indices'][0]-1]))
                                              if match['dimension'] == 1 else None)
    if reasons:
        result.update(status='UNVERIFIED', individual_ids_complete=False, current_mode_ids=[None]*nb)
    result.update(format='superfish_ng_planar_tracking_result', result_version=8 if shape else 7 if exact_affine else 6 if affine else 5 if composed else 4 if remesh else 3 if similarity else 2 if polygon else 1, request=request.to_dict(),
                  verification_reasons=reasons, spectral_resolution=resolutions,
                  spectral_resolution_groups=groups, guard_overlap=edge_unresolved,
                  physical_mapping=dict(name='polynomial_affine_xy_reference' if shape else 'polygon_exact_affine_remesh' if exact_affine else 'polygon_affine_remesh' if affine else 'polygon_similarity_remesh' if composed else 'polygon_same_domain' if remesh else 'polygon_similarity' if similarity else 'polygon_uniform_scale' if polygon else request.mapping, physics='cartesian_cutoff_rf', polarization=previous.case.polarization,
                      previous_case=previous.case.to_dict(), current_case=current.case.to_dict(),
                      overlay_triangles=len(overlay.previous_cells), integration_orders=[3, 5],
                      maximum_normalized_gram_discrepancy=max(discrepancies), integration_tolerance=1e-10,
                      minimum_numerical_assignment_margin=numerical_margin_floor,
                      electric_gram_previous=grams[0].tolist(), electric_gram_cross=grams[1].tolist(), electric_gram_current=grams[2].tolist()),
                  scope='numerical electric-field subspace correspondence on a declared rectangle map; finite-enrichment resolution diagnostic only; no continuum error bound, surface-peak guarantee or continuous-path mode identity')
    if polygon and not remesh and not composed and not affine and not exact_affine and not shape:
        result['physical_mapping'].update(declaration=request.mapping.to_dict(), reference_measure='previous physical xy area in m^2',
                                         coordinate_roundoff_relative_tolerance=16*np.finfo(float).eps,
                                         coordinate_roundoff_scale='minimum of coordinate magnitude and shortest incident mesh edge; exact alternate scale/refinement construction also accepted')
        result['scope']='numerical electric-field subspace correspondence on a declared polygon origin scale and nested mesh relation; finite-enrichment resolution diagnostic only; no continuum error bound, surface-peak guarantee or continuous-path mode identity'
    if similarity:
        result['physical_mapping'].update(current_to_previous_rotation=rotation.tolist(),
            coordinate_roundoff_scale='shortest incident mesh edge; exact matrix/component forward/inverse and refinement constructions also accepted')
        result['scope']='numerical electric-field subspace correspondence on a declared proper polygon similarity and nested mesh relation; area-scaled finite-enrichment diagnostic only; no continuum error bound, surface-peak guarantee or continuous-path mode identity'
    if remesh:
        result['physical_mapping'].update(declaration=request.mapping.to_dict(),
            reference_measure='previous physical xy area in m^2',
            partition_verification='exact binary64-coordinate intersections cover every original triangle on both sides')
        result['scope']='numerical electric-field subspace correspondence on the same polygon with independent meshes; area-scaled finite-enrichment diagnostic only; no continuum error bound, surface-peak guarantee or continuous-path mode identity'
    if composed:
        result['physical_mapping'].update(declaration=request.mapping.to_dict(),
            current_to_previous_rotation=rotation.tolist(),
            reference_measure='physical xy area of the exact common frame; both element unions share the exactly mapped boundary vertex cycle',
            partition_verification='exact binary64-coordinate intersections cover every original triangle on both sides; the mapped boundary cycle must match exactly',
            coordinate_roundoff_scale='exact matrix or explicit component evaluation of the declared similarity in either direction; no fitted map or widened tolerance; interior nodes and connectivity are independent')
        result['scope']='numerical electric-field subspace correspondence on a declared proper polygon similarity whose boundary is mapped exactly and whose interior is independently remeshed; area-scaled finite-enrichment diagnostic only; no continuum error bound, surface-peak guarantee or continuous-path mode identity'
    if affine:
        result['physical_mapping'].update(declaration=request.mapping.to_dict(),
            current_to_previous_linear=rotation.tolist(),
            reference_measure='physical xy area of the exact common frame; both element unions share the exactly mapped boundary vertex cycle',
            partition_verification='exact binary64-coordinate intersections cover every original triangle on both sides; the mapped boundary cycle must match exactly',
            coordinate_roundoff_scale='exact matrix or explicit component evaluation of the declared affine map in either direction; no fitted map or widened tolerance; interior nodes and connectivity are independent',
            signed_determinant=request.mapping.signed_determinant,
            orientation=('preserved' if request.mapping.orientation_preserving
                         else 'reversed; polygon order and triangle vertex order normalized to positive orientation'))
        result['scope']='numerical electric-field subspace correspondence on a declared invertible affine map whose boundary is mapped exactly and whose interior is independently remeshed; shear or orientation-reversing maps are declared correspondences without an exact eigenvalue law; area-scaled finite-enrichment diagnostic only; no continuum error bound, surface-peak guarantee or continuous-path mode identity'
    if exact_affine:
        result['physical_mapping'].update(declaration=request.mapping.to_dict(),
            current_to_previous_linear=rotation.tolist(),
            reference_measure='current physical xy area in m^2 in both declaration directions',
            partition_verification='rational affine intersections exactly cover every original triangle on both sides; boundary and interior subdivisions are independent',
            coordinate_evaluation='binary64 inputs interpreted as exact rationals; affine map and inverse evaluated before any quadrature conversion; rounded boundary or corner deviations rejected',
            declared_determinant_exact=str(request.mapping.exact_determinant),
            effective_determinant_exact=str(1/request.mapping.exact_determinant if request.mapping.inverse else request.mapping.exact_determinant),
            orientation=('preserved' if request.mapping.orientation_preserving
                         else 'reversed; original cell indices and barycentric column order retained'))
        result['scope']='numerical electric-field subspace correspondence on an exact rational affine map with independently subdivided boundaries and interiors; shear or orientation-reversing maps do not imply a general eigenvalue law; area-scaled finite-enrichment diagnostic only; no continuum error bound, surface-peak guarantee or continuous-path mode identity'
    if shape:
        result['physical_mapping'].update(declaration=request.mapping.to_dict(),
            reference_measure='previous physical xy area in m^2',
            current_to_previous_linear_by_triangle=rotation.tolist(),
            partition_verification='both original trial meshes regenerated exactly; common dyadic reference partition retains original cell indices and barycentric coordinates',
            coordinate_evaluation='rounded actual trial meshes retained; piecewise affine correspondence, no fitted global affine map')
        result['scope']='numerical electric-field subspace correspondence between polynomial-affine trials on a shared original reference partition; J/m normalization; finite-enrichment diagnostic only; no continuum-error or continuous-path certificate'
    return result

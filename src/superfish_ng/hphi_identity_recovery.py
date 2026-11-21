# SPDX-License-Identifier: Apache-2.0
"""Explicit sampled-field reidentification inside inherited Hphi identity sets.

The history owner must bind the declared anchor index to its native snapshot.
This numerical kernel recomputes both correspondences from the supplied fields;
it does not accept caller-authored correspondence results as evidence.
"""
from dataclasses import dataclass

from .config import integer, keys
from .hphi_geometry_mapping import HphiGeometryMapping
from .hphi_tracking import HphiTrackingRequest, track_hphi_modes, track_mapped_hphi_modes
from .mode_tracking import _identity_groups


@dataclass(frozen=True)
class HphiIdentityRecoveryRequest:
    anchor_snapshot_index: int
    comparison: HphiTrackingRequest
    mapping: object = None

    def __post_init__(self):
        integer(self.anchor_snapshot_index, 'anchor_snapshot_index', 0)
        if not isinstance(self.comparison, HphiTrackingRequest):
            raise ValueError('Hphi recovery requires an explicit anchor comparison request')
        comparison = HphiTrackingRequest.from_dict(self.comparison.to_dict())
        if comparison.geometry_mapping is not None:
            raise ValueError('declare recovery geometry only in the outer recovery mapping')
        if comparison.previous_mode_ids is None:
            raise ValueError('Hphi recovery anchor must declare resolved individual IDs, not an ID set')
        object.__setattr__(self, 'comparison', comparison)
        if self.mapping is not None:
            if type(self.mapping) is not HphiGeometryMapping:
                raise ValueError('Hphi recovery requires an explicit HphiGeometryMapping or same vacuum')
            object.__setattr__(self, 'mapping', HphiGeometryMapping.from_dict(self.mapping.to_dict()))

    def to_dict(self):
        return dict(format='superfish_ng_hphi_identity_recovery_request', recovery_version=1,
                    anchor_snapshot_index=self.anchor_snapshot_index,
                    comparison=self.comparison.to_dict(),
                    mapping='same_vacuum' if self.mapping is None else self.mapping.to_dict())

    @classmethod
    def from_dict(cls, data):
        names=('format','recovery_version','anchor_snapshot_index','comparison','mapping')
        keys(data, names, names, 'Hphi identity recovery request')
        if (data['format'] != 'superfish_ng_hphi_identity_recovery_request'
                or type(data['recovery_version']) is not int or data['recovery_version'] != 1):
            raise ValueError('expected Hphi identity recovery request recovery_version 1')
        mapping = data['mapping']
        if type(mapping) is str and mapping == 'same_vacuum':
            mapping = None
        elif type(mapping) is dict:
            mapping = HphiGeometryMapping.from_dict(mapping)
        else:
            raise ValueError('declare same_vacuum or a complete Hphi geometry mapping')
        return cls(data['anchor_snapshot_index'], HphiTrackingRequest.from_dict(data['comparison']), mapping)


def _compare(previous, current, request, mapping):
    if mapping is None:
        return track_hphi_modes(previous, current, request)
    return track_mapped_hphi_modes(previous, current, request, mapping)


def _anchor_comparison(anchor, current, request):
    return _compare(anchor, current, request.comparison, request.mapping)


def _assess(comparison, groups, count):
    groups = _identity_groups(groups, count)
    candidates = comparison['current_mode_ids']
    if len(candidates) != count:
        raise ValueError('anchor comparison differs from the inherited current band')
    checks = []
    preserved = [None]*count
    for group in groups:
        observed = [candidates[i-1] for i in group['indices']]
        observed = sorted(observed) if all(type(item) is str for item in observed) else None
        checks.append(dict(indices=group['indices'], expected_ids=group['ids'],
                           candidate_ids=observed, consistent=observed == group['ids']))
        if len(group['indices']) == 1:
            preserved[group['indices'][0]-1] = group['ids'][0]
    resolved = comparison['status'] == 'PASS' and comparison['individual_ids_complete']
    consistent = all(check['consistent'] for check in checks)
    passed = resolved and consistent
    return dict(status='PASS' if passed else 'UNVERIFIED',
                candidate_mode_ids=list(candidates),
                current_mode_ids=list(candidates) if passed else preserved,
                current_identity_groups=([dict(indices=[i+1],ids=[name]) for i,name in enumerate(candidates)]
                                         if passed else groups),
                individual_ids_complete=passed, group_checks=checks,
                reasons=([] if resolved else ['anchor E/H comparison does not resolve every individual ID'])+
                        ([] if consistent else ['candidate IDs do not equal each inherited identity set']))


def recover_hphi_modes(anchor, previous, current, inherited_request, request, *,
                       current_snapshot_index, inherited_mapping=None):
    """Recover only after verified subspace continuity, then check every ID set.

    Snapshot positions are zero-based. Geometry transport and finite spectral
    diagnostics remain those of the dedicated Hphi comparison. In particular,
    no frequency-rank label or continuum branch identity is inferred here.
    """
    if not isinstance(request, HphiIdentityRecoveryRequest):
        raise ValueError('expected HphiIdentityRecoveryRequest')
    request = HphiIdentityRecoveryRequest.from_dict(request.to_dict())
    integer(current_snapshot_index, 'current_snapshot_index')
    if request.anchor_snapshot_index >= current_snapshot_index:
        raise ValueError('Hphi recovery anchor must precede the current snapshot')
    if not isinstance(inherited_request, HphiTrackingRequest):
        raise ValueError('expected the inherited HphiTrackingRequest')
    if request.comparison.current_mode_count != inherited_request.current_mode_count:
        raise ValueError('anchor and inherited comparisons must cover the same current band')
    inherited = _compare(previous, current, inherited_request, inherited_mapping)
    event = dict(format='superfish_ng_hphi_identity_recovery', recovery_version=1,
                 request=request.to_dict(), current_snapshot_index=current_snapshot_index,
                 inherited=inherited, comparison=None, assessment=None, status='UNVERIFIED',
                 scope='declared earlier native-field reidentification inside inherited ID sets; '
                       'not a continuous-branch certificate through degeneracy')
    if inherited['status'] != 'PASS':
        event['stop_reason'] = 'inherited E/H subspace is UNVERIFIED; anchor recovery is forbidden'
        return event
    if inherited['individual_ids_complete']:
        raise ValueError('Hphi recovery requires an inherited unresolved individual ID set')
    groups = [dict(indices=match['current_indices'], ids=match['previous_ids'])
              for match in inherited['matches']]
    comparison = _anchor_comparison(anchor, current, request)
    assessment = _assess(comparison, groups, inherited_request.current_mode_count)
    event.update(comparison=comparison, assessment=assessment, status=assessment['status'],
                 stop_reason=None if assessment['status'] == 'PASS' else '; '.join(assessment['reasons']))
    return event

# SPDX-License-Identifier: Apache-2.0
"""Explicit earlier-field planar ID recovery within inherited identity sets.

The owner must bind anchor_snapshot_index to the actual resolved snapshot.
This kernel recomputes both physical comparisons; it never trusts a supplied
tracking result or infers identity from frequency rank.
"""
from dataclasses import dataclass
from .config import integer, keys
from .planar_tracking import PlanarTrackingRequest, track_planar_modes
from .mode_identity_recovery import assess_identity_recovery


@dataclass(frozen=True)
class PlanarIdentityRecoveryRequest:
    anchor_snapshot_index: int
    comparison: PlanarTrackingRequest

    def __post_init__(self):
        integer(self.anchor_snapshot_index, 'anchor_snapshot_index', 0)
        if type(self.comparison) is not PlanarTrackingRequest:
            raise ValueError('planar recovery requires a complete PlanarTrackingRequest')
        comparison = PlanarTrackingRequest.from_dict(self.comparison.to_dict())
        if comparison.previous_mode_ids is None:
            raise ValueError('planar recovery anchor must declare resolved individual IDs')
        object.__setattr__(self, 'comparison', comparison)

    def to_dict(self):
        return dict(format='superfish_ng_planar_identity_recovery_request', recovery_version=1,
                    anchor_snapshot_index=self.anchor_snapshot_index, comparison=self.comparison.to_dict())

    @classmethod
    def from_dict(cls, data):
        names = ('format', 'recovery_version', 'anchor_snapshot_index', 'comparison')
        keys(data, names, names, 'planar identity recovery')
        if (data['format'] != 'superfish_ng_planar_identity_recovery_request'
                or type(data['recovery_version']) is not int or data['recovery_version'] != 1):
            raise ValueError('expected planar identity recovery_version 1')
        return cls(data['anchor_snapshot_index'], PlanarTrackingRequest.from_dict(data['comparison']))


def recover_planar_modes(anchor, previous, current, inherited_request, request, *, current_snapshot_index):
    """Reidentify only after a verified unresolved subspace continuation.

    Frequencies by recovered ID are available only when every inherited set
    agrees. Raw comparison spectra remain separate evidence on failure.
    """
    if type(request) is not PlanarIdentityRecoveryRequest:
        raise ValueError('expected PlanarIdentityRecoveryRequest')
    request = PlanarIdentityRecoveryRequest.from_dict(request.to_dict())
    integer(current_snapshot_index, 'current_snapshot_index')
    if request.anchor_snapshot_index >= current_snapshot_index:
        raise ValueError('planar recovery anchor must precede the current snapshot')
    if type(inherited_request) is not PlanarTrackingRequest:
        raise ValueError('expected the inherited PlanarTrackingRequest')
    if inherited_request.current_mode_count != request.comparison.current_mode_count:
        raise ValueError('anchor and inherited comparisons must cover the same current band')
    inherited = track_planar_modes(previous, current, inherited_request)
    event = dict(format='superfish_ng_planar_identity_recovery', recovery_version=1,
                 request=request.to_dict(), current_snapshot_index=current_snapshot_index,
                 inherited=inherited, comparison=None, assessment=None, status='UNVERIFIED',
                 recovered_frequencies_hz=None,
                 scope='earlier original planar E-field reidentification inside inherited ID sets; '
                       'J/m normalization; no continuous-path identity through degeneracy')
    if inherited['status'] != 'PASS':
        event['stop_reason'] = 'inherited planar subspace is UNVERIFIED; anchor recovery is forbidden'
        return event
    if inherited['individual_ids_complete']:
        raise ValueError('planar recovery requires an inherited unresolved individual ID set')
    groups = [dict(indices=match['current_indices'], ids=match['previous_ids'])
              for match in inherited['matches']]
    comparison = track_planar_modes(anchor, current, request.comparison)
    assessment = assess_identity_recovery(comparison, groups)
    event.update(comparison=comparison, assessment=assessment, status=assessment['status'],
                 stop_reason=None if assessment['status'] == 'PASS' else '; '.join(assessment['reasons']))
    if assessment['status'] == 'PASS':
        event['recovered_frequencies_hz'] = dict(zip(assessment['current_mode_ids'], comparison['current_frequencies_hz']))
    return event

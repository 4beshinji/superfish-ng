# SPDX-License-Identifier: Apache-2.0
"""Earlier original Cartesian P2 E/H recovery inside inherited ID sets.

The history/tuning owner must bind anchor_snapshot_index to the actual earlier
resolved snapshot and its original ID labels. This kernel recomputes both
complete comparisons; no supplied tracking result or frequency label is used.
"""
from dataclasses import dataclass
from .config import integer, keys
from .mode_identity_recovery import assess_identity_recovery
from .planar_curved_tracking import PlanarCurvedTrackingRequest, track_planar_curved_modes


@dataclass(frozen=True)
class PlanarCurvedIdentityRecoveryRequest:
    anchor_snapshot_index: int
    comparison: PlanarCurvedTrackingRequest

    def __post_init__(self):
        integer(self.anchor_snapshot_index, 'anchor_snapshot_index', 0)
        if type(self.comparison) is not PlanarCurvedTrackingRequest:
            raise ValueError('curved planar recovery requires a complete PlanarCurvedTrackingRequest')
        comparison = PlanarCurvedTrackingRequest.from_dict(self.comparison.to_dict())
        if comparison.previous_mode_ids is None:
            raise ValueError('curved planar recovery anchor must declare resolved individual IDs')
        object.__setattr__(self, 'comparison', comparison)

    def to_dict(self):
        return dict(format='superfish_ng_planar_curved_identity_recovery_request', recovery_version=1,
                    anchor_snapshot_index=self.anchor_snapshot_index, comparison=self.comparison.to_dict())

    @classmethod
    def from_dict(cls, data):
        names = ['format', 'recovery_version', 'anchor_snapshot_index', 'comparison']
        keys(data, names, names, 'curved planar identity recovery request')
        if (data['format'] != 'superfish_ng_planar_curved_identity_recovery_request'
                or type(data['recovery_version']) is not int or data['recovery_version'] != 1):
            raise ValueError('expected curved planar identity recovery_version 1')
        return cls(data['anchor_snapshot_index'], PlanarCurvedTrackingRequest.from_dict(data['comparison']))


def recover_planar_curved_modes(anchor, previous, current, inherited_request, request, *, current_snapshot_index):
    """Reidentify only after verified subspace continuity; failure has null f.

    Both comparisons use actual original peak E/H, full declared quadratic
    correspondences and their own finite guards/budgets. Frequencies keyed by
    recovered ID exist only after the entire anchor assignment agrees with
    every inherited identity set. This is not continuous-path certification.
    """
    if type(request) is not PlanarCurvedIdentityRecoveryRequest:
        raise ValueError('expected PlanarCurvedIdentityRecoveryRequest')
    request = PlanarCurvedIdentityRecoveryRequest.from_dict(request.to_dict())
    integer(current_snapshot_index, 'current_snapshot_index')
    if request.anchor_snapshot_index >= current_snapshot_index:
        raise ValueError('curved planar recovery anchor must precede the current snapshot')
    if type(inherited_request) is not PlanarCurvedTrackingRequest:
        raise ValueError('expected the inherited PlanarCurvedTrackingRequest')
    inherited_request = PlanarCurvedTrackingRequest.from_dict(inherited_request.to_dict())
    if inherited_request.current_mode_count != request.comparison.current_mode_count:
        raise ValueError('anchor and inherited comparisons must cover the same current band')
    inherited = track_planar_curved_modes(previous, current, inherited_request)
    event = dict(format='superfish_ng_planar_curved_identity_recovery', recovery_version=1,
        request=request.to_dict(), current_snapshot_index=current_snapshot_index,
        inherited=inherited, comparison=None, assessment=None, status='UNVERIFIED',
        recovered_frequencies_hz=None,
        scope='declared earlier original curved Cartesian E/H reidentification within inherited ID sets; J/m normalization; no continuous-path identity through degeneracy')
    if inherited['status'] != 'PASS':
        event['stop_reason'] = 'inherited curved planar E/H subspace is UNVERIFIED; anchor recovery is forbidden'
        return event
    if inherited['individual_ids_complete']:
        raise ValueError('curved planar recovery requires an inherited unresolved individual ID set')
    groups = [dict(indices=match['current_indices'], ids=match['previous_ids']) for match in inherited['matches']]
    comparison = track_planar_curved_modes(anchor, current, request.comparison)
    assessment = assess_identity_recovery(comparison, groups)
    event.update(comparison=comparison, assessment=assessment, status=assessment['status'],
        stop_reason=None if assessment['status'] == 'PASS' else '; '.join(assessment['reasons']))
    if assessment['status'] == 'PASS':
        event['recovered_frequencies_hz'] = dict(zip(assessment['current_mode_ids'], comparison['current_frequencies_hz']))
    return event

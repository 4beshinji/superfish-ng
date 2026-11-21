# SPDX-License-Identifier: Apache-2.0
"""Original fixed-material E/H recovery inside inherited identity sets."""
from dataclasses import dataclass
from .config import integer,keys
from .material_hphi_tracking import MaterialHphiTrackingRequest,track_material_hphi_modes
from .hphi_identity_recovery import _assess


@dataclass(frozen=True)
class MaterialHphiIdentityRecoveryRequest:
    anchor_snapshot_index: int
    comparison: MaterialHphiTrackingRequest

    def __post_init__(self):
        integer(self.anchor_snapshot_index,'anchor_snapshot_index',0)
        if type(self.comparison) is not MaterialHphiTrackingRequest:
            raise ValueError('material recovery requires a complete fixed-material anchor comparison')
        comparison=MaterialHphiTrackingRequest.from_dict(self.comparison.to_dict())
        if comparison.previous_mode_ids is None:
            raise ValueError('material recovery anchor requires resolved individual IDs')
        object.__setattr__(self,'comparison',comparison)

    def to_dict(self):
        return dict(format='superfish_ng_material_hphi_identity_recovery_request',recovery_version=1,
                    anchor_snapshot_index=self.anchor_snapshot_index,comparison=self.comparison.to_dict())

    @classmethod
    def from_dict(cls,data):
        names=('format','recovery_version','anchor_snapshot_index','comparison')
        keys(data,names,names,'material Hphi identity recovery')
        if (data['format']!='superfish_ng_material_hphi_identity_recovery_request'
                or type(data['recovery_version']) is not int or data['recovery_version']!=1):
            raise ValueError('expected material Hphi recovery_version 1')
        return cls(data['anchor_snapshot_index'],MaterialHphiTrackingRequest.from_dict(data['comparison']))


def recover_material_hphi_modes(anchor, previous, current, inherited_request, request, *,
                       current_snapshot_index):
    """Recover only after verified subspace continuity, then check every ID set.

    Snapshot positions are zero-based. Geometry transport and finite spectral
    diagnostics remain those of the dedicated Hphi comparison. In particular,
    no frequency-rank label or continuum branch identity is inferred here.
    """
    if not isinstance(request, MaterialHphiIdentityRecoveryRequest):
        raise ValueError('expected MaterialHphiIdentityRecoveryRequest')
    request = MaterialHphiIdentityRecoveryRequest.from_dict(request.to_dict())
    integer(current_snapshot_index, 'current_snapshot_index')
    if request.anchor_snapshot_index >= current_snapshot_index:
        raise ValueError('Hphi recovery anchor must precede the current snapshot')
    if not isinstance(inherited_request, MaterialHphiTrackingRequest):
        raise ValueError('expected the inherited MaterialHphiTrackingRequest')
    if request.comparison.current_mode_count != inherited_request.current_mode_count:
        raise ValueError('anchor and inherited comparisons must cover the same current band')
    inherited = track_material_hphi_modes(previous, current, inherited_request)
    event = dict(format='superfish_ng_material_hphi_identity_recovery', recovery_version=1,
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
    comparison = track_material_hphi_modes(anchor, current, request.comparison)
    assessment = _assess(comparison, groups, inherited_request.current_mode_count)
    event.update(comparison=comparison, assessment=assessment, status=assessment['status'],
                 stop_reason=None if assessment['status'] == 'PASS' else '; '.join(assessment['reasons']))
    return event

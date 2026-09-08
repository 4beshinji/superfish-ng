# SPDX-License-Identifier: Apache-2.0
"""Ordered, strict instructions for restricting a fixed quadratic mesh."""
from dataclasses import dataclass
from .config import integer, keys, positive


@dataclass(frozen=True)
class CurvedRefinementStep:
    kind: str
    marked_cells: tuple[int, ...] = ()
    minimum_corner_angle_deg: float | None = None

    def __post_init__(self):
        if not isinstance(self.kind, str) or self.kind not in ('uniform', 'marked'):
            raise ValueError('curved refinement kind must be uniform or marked')
        if type(self.marked_cells) is not tuple:
            raise ValueError('marked_cells must be an immutable tuple')
        if self.kind == 'uniform':
            if self.marked_cells or self.minimum_corner_angle_deg is not None:
                raise ValueError('uniform refinement accepts only kind')
        else:
            if not self.marked_cells:
                raise ValueError('marked refinement requires nonempty marked_cells')
            for cell in self.marked_cells:
                integer(cell, 'marked_cells entry', minimum=0)
            if len(set(self.marked_cells)) != len(self.marked_cells):
                raise ValueError('marked_cells must be unique')
            if positive(self.minimum_corner_angle_deg, 'minimum_corner_angle_deg') >= 60:
                raise ValueError('minimum_corner_angle_deg must be below 60')

    @classmethod
    def from_dict(cls, data):
        keys(data, ('kind', 'marked_cells', 'minimum_corner_angle_deg'), ('kind',), 'curved refinement step')
        required = ('kind',) if data['kind'] == 'uniform' else ('kind', 'marked_cells', 'minimum_corner_angle_deg')
        keys(data, required, required, 'curved refinement step')
        if 'marked_cells' in data and not isinstance(data['marked_cells'], list):
            raise ValueError('marked_cells must be an array')
        return cls(data['kind'], tuple(data.get('marked_cells', ())), data.get('minimum_corner_angle_deg'))

    def to_dict(self):
        if self.kind == 'uniform':
            return dict(kind=self.kind)
        return dict(kind=self.kind, marked_cells=list(self.marked_cells),
                    minimum_corner_angle_deg=self.minimum_corner_angle_deg)


def steps_from_dict(data):
    if not isinstance(data, list) or not data:
        raise ValueError('curved_refinement_steps must be a nonempty array; omit it for no refinement')
    return tuple(CurvedRefinementStep.from_dict(step) for step in data)


def steps_to_dict(steps):
    return [step.to_dict() for step in steps]

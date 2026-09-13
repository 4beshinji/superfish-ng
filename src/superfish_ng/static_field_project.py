# SPDX-License-Identifier: Apache-2.0
"""Portable static-field input documents preserving each dedicated SI Case."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile

from .config import keys
from .project import parse_json
from .electrostatic import AxisymmetricElectrostaticCase
from .planar_electrostatic import PlanarElectrostaticCase
from .planar_magnetostatic import PlanarMagnetostaticCase
from .axis_magnetostatic import AxisMagnetostaticCase
from .off_axis_magnetostatic import OffAxisMagnetostaticCase
from .planar_recoil import PlanarRecoilCase
from .axis_recoil import AxisRecoilCase
from .off_axis_recoil import OffAxisRecoilCase
from .planar_bh import PlanarBHCase
from .axis_bh import AxisBHCase
from .off_axis_bh import OffAxisBHCase

_FAMILIES = (
    ('superfish_ng_axisymmetric_electrostatic_case', AxisymmetricElectrostaticCase, 'linear_electrostatic', 'axisymmetric', (1, 2)),
    ('superfish_ng_planar_electrostatic_case', PlanarElectrostaticCase, 'linear_electrostatic', 'cartesian_xy', (1, 2)),
    ('superfish_ng_planar_magnetostatic_case', PlanarMagnetostaticCase, 'linear_magnetostatic', 'cartesian_xy', (1, 2)),
    ('superfish_ng_axis_magnetostatic_case', AxisMagnetostaticCase, 'linear_magnetostatic', 'axis_connected_rz', (1, 2)),
    ('superfish_ng_off_axis_magnetostatic_case', OffAxisMagnetostaticCase, 'linear_magnetostatic', 'positive_radius_rz', (1, 2)),
    ('superfish_ng_planar_recoil_case', PlanarRecoilCase, 'linear_recoil_magnetostatic', 'cartesian_xy', (1, 2)),
    ('superfish_ng_axis_recoil_case', AxisRecoilCase, 'linear_recoil_magnetostatic', 'axis_connected_rz', (1, 2)),
    ('superfish_ng_off_axis_recoil_case', OffAxisRecoilCase, 'linear_recoil_magnetostatic', 'positive_radius_rz', (1, 2)),
    ('superfish_ng_planar_bh_case', PlanarBHCase, 'nonlinear_isotropic_magnetostatic', 'cartesian_xy', (1,)),
    ('superfish_ng_axis_bh_case', AxisBHCase, 'nonlinear_isotropic_magnetostatic', 'axis_connected_rz', (1,)),
    ('superfish_ng_off_axis_bh_case', OffAxisBHCase, 'nonlinear_isotropic_magnetostatic', 'positive_radius_rz', (1,)),
)
_CASE_TYPES = {name: case_type for name, case_type, *_ in _FAMILIES}


def static_case_families():
    """Return independent metadata copies; the dedicated parsers own restrictions."""
    return [dict(case_format=name, case_schema_versions=[1], physics=physics,
                 coordinates=coordinates, element_orders=list(orders))
            for name, _, physics, coordinates, orders in _FAMILIES]


def static_case_from_dict(data):
    if (not isinstance(data, dict) or type(data.get('format')) is not str
            or data['format'] not in _CASE_TYPES):
        raise ValueError('expected a supported dedicated static-field Case format; RF and unknown physics are not static Projects')
    return _CASE_TYPES[data['format']].from_dict(data)


@dataclass(frozen=True, eq=False)
class StaticFieldProject:
    case: object
    display_length_unit: str = 'mm'

    def __post_init__(self):
        if type(self.case) not in _CASE_TYPES.values():
            raise ValueError('StaticFieldProject requires a supported dedicated electrostatic, magnetic, recoil or B-H Case')
        if type(self.display_length_unit) is not str or self.display_length_unit not in ('m', 'mm'):
            raise ValueError('static Project display_length_unit must be m or mm; saved Case values remain SI')
        object.__setattr__(self, 'case', static_case_from_dict(self.case.to_dict()))

    @classmethod
    def from_dict(cls, data):
        if isinstance(data, dict) and type(data.get('format')) is str and data['format'] in _CASE_TYPES:
            return cls(static_case_from_dict(data))
        names = ['format', 'project_version', 'case', 'display_length_unit']
        keys(data, names, names, 'static field Project')
        if (data['format'] != 'superfish_ng_static_field_project'
                or type(data['project_version']) is not int or data['project_version'] != 1):
            raise ValueError('expected superfish_ng_static_field_project project_version 1')
        return cls(static_case_from_dict(data['case']), data['display_length_unit'])

    def to_dict(self):
        # Frozen dataclasses alone do not establish ownership of nested data.
        verified = type(self)(self.case, self.display_length_unit)
        return dict(format='superfish_ng_static_field_project', project_version=1,
                    case=verified.case.to_dict(), display_length_unit=verified.display_length_unit)

    def __eq__(self, other):
        if not isinstance(other, StaticFieldProject):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    __hash__ = None

    def dumps(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, allow_nan=False) + '\n'

    @classmethod
    def load(cls, path):
        return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def save(self, path):
        """Publish complete JSON without overwriting an existing destination."""
        raw, path = self.dumps(), Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.static-project-', dir=path.parent) as temporary:
            staged = Path(temporary) / 'project.json'
            with staged.open('x', encoding='utf-8') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            if self.dumps() != raw:
                raise ValueError('static Project changed during publication')
            os.link(staged, path)


def load_static_document(text):
    return StaticFieldProject.from_dict(parse_json(text))

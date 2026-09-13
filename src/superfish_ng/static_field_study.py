# SPDX-License-Identifier: Apache-2.0
"""Independent static parameter inputs; no implicit warm start or branch tracking."""
from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile

from .axis_magnetostatic_boundary import finite_signed
from .config import keys
from .project import parse_json
from .static_field_project import StaticFieldProject

PARAMETERS = ('uniform_scale', 'excitation_scale')
_BOUNDARY_EXCITATIONS = {
    'electrode_potential': 'potential_v',
    'outward_displacement': 'outward_displacement_c_per_m2',
    'fixed_az': 'az_wb_per_m',
    'fixed_aphi_over_r': 'aphi_over_r_t',
    'fixed_psi': 'psi_wb',
    'tangential_h': 'tangential_h_a_per_m',
    'axis_symmetry': None,
    'axis_regularity': None,
}
_SOURCE_FIELDS = ('charge_density_c_per_m3', 'current_density_z_a_per_m2',
                  'current_density_phi_a_per_m2')


def _geometry_scale(case, factor):
    partition = case['partition']
    geometry = partition['mesh'] if case['format'] == 'superfish_ng_axisymmetric_electrostatic_case' else partition['geometry']
    if 'polygon_xy_m' in geometry:
        names = ('polygon_xy_m', 'points_xy_m')
    else:
        names = ('outer_rz_m', 'points_rz_m')
        geometry['holes_rz_m'] = [[[coordinate * factor for coordinate in point] for point in hole] for hole in geometry['holes_rz_m']]
    for name in names:
        geometry[name] = [[coordinate * factor for coordinate in point] for point in geometry[name]]


def _excitation_scale(case, factor):
    sources = [name for name in _SOURCE_FIELDS if name in case]
    if len(sources) != 1:
        raise ValueError('static Study requires exactly one recognized volume source density field')
    source = sources[0]
    case[source] = {region: density * factor for region, density in case[source].items()}
    for boundary in case['boundaries']:
        if boundary['kind'] not in _BOUNDARY_EXCITATIONS:
            raise ValueError('static Study cannot scale unsupported boundary kind ' + str(boundary['kind']))
        name = _BOUNDARY_EXCITATIONS[boundary['kind']]
        if name is not None: boundary[name] *= factor
    for material in case['partition']['materials']:
        if material['type'] == 'linear_recoil_magnetic_material':
            material['remanent_b_local_t'] = [value * factor for value in material['remanent_b_local_t']]
        elif material['type'] not in ('linear_isotropic_dielectric', 'linear_isotropic_magnetic_material', 'isotropic_monotone_bh_curve'):
            raise ValueError('static Study has no excitation rule for material type ' + str(material['type']))


@dataclass(frozen=True, eq=False)
class StaticFieldStudy:
    project: StaticFieldProject
    parameter: str
    values: tuple

    def __post_init__(self):
        if type(self.project) is not StaticFieldProject:
            raise ValueError('static Study requires a dedicated StaticFieldProject')
        object.__setattr__(self, 'project', StaticFieldProject.from_dict(self.project.to_dict()))
        if type(self.parameter) is not str or self.parameter not in PARAMETERS:
            raise ValueError('static Study parameter must be uniform_scale or excitation_scale')
        if not isinstance(self.values, (list, tuple)) or len(self.values) < 2:
            raise ValueError('static Study requires at least two finite parameter values')
        values = tuple(finite_signed(value, 'static Study value') for value in self.values)
        if self.parameter == 'uniform_scale' and any(value <= 0 for value in values):
            raise ValueError('static Study uniform_scale values must be positive')
        object.__setattr__(self, 'values', values)
        # Validate every derived Case before allocating output or starting a solver.
        self.projects()

    def projects(self):
        result = []
        base = self.project.to_dict()
        for index, value in enumerate(self.values):
            raw = deepcopy(base)
            operation = _geometry_scale if self.parameter == 'uniform_scale' else _excitation_scale
            operation(raw['case'], value)
            try: result.append(StaticFieldProject.from_dict(raw))
            except (ValueError, OverflowError) as exc:
                raise ValueError(f'static Study point {index} ({self.parameter}={value}) is invalid: {exc}') from exc
        return tuple(result)

    def to_dict(self):
        verified = type(self)(self.project, self.parameter, self.values)
        return dict(format='superfish_ng_static_field_study', study_version=1, kind='sweep',
                    project=verified.project.to_dict(), parameter=verified.parameter, values=list(verified.values))

    @classmethod
    def from_dict(cls, data):
        names = ['format', 'study_version', 'kind', 'project', 'parameter', 'values']
        keys(data, names, names, 'static Study')
        if (data['format'] != 'superfish_ng_static_field_study'
                or type(data['study_version']) is not int or data['study_version'] != 1):
            raise ValueError('expected superfish_ng_static_field_study study_version 1')
        if data['kind'] != 'sweep':
            raise ValueError('static Study supports independent sweeps; branch tracking and mesh convergence require separate operations')
        if type(data['values']) is not list:
            raise ValueError('static Study values must be a JSON array')
        return cls(StaticFieldProject.from_dict(data['project']), data['parameter'], data['values'])

    def __eq__(self, other):
        if not isinstance(other, StaticFieldStudy): return NotImplemented
        return self.to_dict() == other.to_dict()

    __hash__ = None

    def dumps(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, allow_nan=False) + '\n'

    @classmethod
    def load(cls, path):
        return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def save(self, path):
        raw, path = self.dumps(), Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.static-study-', dir=path.parent) as temporary:
            staged = Path(temporary) / 'study.json'
            with staged.open('x', encoding='utf-8') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            if self.dumps() != raw: raise ValueError('static Study changed during publication')
            os.link(staged, path)


def load_static_study_document(text):
    return StaticFieldStudy.from_dict(parse_json(text))

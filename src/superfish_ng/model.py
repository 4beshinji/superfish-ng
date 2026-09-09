# SPDX-License-Identifier: Apache-2.0
"""Explicit supported physics; planned solvers never fall back to vacuum TM."""
from dataclasses import dataclass, replace
from .config import Case, integer, keys


@dataclass(frozen=True)
class Model:
    physics: str = 'rf_eigenmode'
    coordinates: str = 'axisymmetric'
    polarization: str = 'tm'
    azimuthal_index: int = 0
    material_id: str = 'vacuum'
    region_id: str = 'cavity'

    def __post_init__(self):
        for name, supported in [('physics', 'rf_eigenmode'),
                                ('coordinates', 'axisymmetric')]:
            if getattr(self, name) != supported:
                raise ValueError(f'model.{name}: only {supported!r} is implemented; see capabilities')
        if self.polarization not in ('tm','te'):
            raise ValueError('model.polarization: only tm and te are implemented; see capabilities')
        integer(self.azimuthal_index, 'model.azimuthal_index', 0)
        if self.azimuthal_index != 0:
            raise ValueError('model.azimuthal_index: only m=0 is implemented')
        for name in ('material_id', 'region_id'):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'model.{name} must be a nonempty string')

    @classmethod
    def from_dict(cls, data):
        required = ['physics', 'coordinates', 'polarization', 'azimuthal_index',
                    'materials', 'regions']
        keys(data, required, required, 'model')
        for name in ('materials', 'regions'):
            if not isinstance(data[name], list) or len(data[name]) != 1:
                raise ValueError(f'model.{name}: exactly one vacuum material/interior region is implemented')
        material, region = data['materials'][0], data['regions'][0]
        keys(material, ['id', 'type'], ['id', 'type'], 'model.materials[0]')
        keys(region, ['id', 'material', 'domain'], ['id', 'material', 'domain'], 'model.regions[0]')
        if material['type'] != 'vacuum':
            raise ValueError('model.materials[0].type: only vacuum is implemented; RF wall conductivity belongs in rf')
        if region['domain'] != 'interior':
            raise ValueError('model.regions[0].domain: only the complete geometry interior is implemented')
        if region['material'] != material['id']:
            raise ValueError('model.regions[0].material must reference the declared material id')
        return cls(**{k: data[k] for k in required[:4]},
                   material_id=material['id'], region_id=region['id'])

    def to_dict(self):
        return {'physics': self.physics, 'coordinates': self.coordinates,
                'polarization': self.polarization, 'azimuthal_index': self.azimuthal_index,
                'materials': [{'id': self.material_id, 'type': 'vacuum'}],
                'regions': [{'id': self.region_id, 'material': self.material_id, 'domain': 'interior'}]}


def upgrade_case(data):
    """Validate a case and explicitly migrate to v3 without mutating input data."""
    case = Case.from_dict(data)
    return replace(case, model=case.model or Model()).to_dict()


def capabilities():
    """Machine-readable capabilities of this implementation, not its roadmap."""
    return {'capabilities_version': 1, 'case_schema_versions': [1, 2, 3],
            'supported_models': [Model().to_dict(), Model(polarization='te').to_dict()],
            'model_limits': {'te': 'vacuum m=0, straight P1/P2 and curved P2, solve/TE native read/Project/JobManager/GUI; normalized-cylinder tracking; parameter sweeps and same-physics refinement diagnostics; other tracking pending'},
            'geometry_types': ['pillbox', 'profile', 'stepped_profile', 'arc_profile', 'contour'],
            'automatic_mesh_geometry_types': ['pillbox', 'profile', 'stepped_profile', 'arc_profile', 'contour'],
            'contour_mesh_requirement': 'explicit mesh.contour_mesh controls or validated external tagged mesh',
            'end_boundaries': ['pec', 'electric_symmetry', 'magnetic_symmetry'],
            'wall_boundary': 'pec', 'axis_condition': 'regular Hphi=r*u; finite u',
            'field_units': {'Er': 'V/m', 'Ez': 'V/m', 'Hphi': 'A/m'},
            'energy_unit': 'J', 'wall_loss_unit': 'W',
            'volume_measure': '2*pi*r*dr*dz', 'phasor': 'peak; exp(+i*omega*t)',
            'solution_space': 'P1/P2 scalar u=Hphi/r on affine triangles',
            'element_orders': [1, 2], 'default_element_order': 1,
            'rq_definitions': {'accelerator': '|Vacc|^2/(omega*U)',
                               'circuit': '|Vacc|^2/(2*omega*U)'}}

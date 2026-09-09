# SPDX-License-Identifier: Apache-2.0
"""Same-domain planar refinement requests; differences are not error bounds."""
from dataclasses import dataclass, field, replace
import json
from pathlib import Path
from .config import integer, positive, keys
from .project import parse_json
from .planar_project import PlanarProject
from .planar_polygon import PlanarPolygonCase
from .planar_mesh import PlanarMesh
from .planar_refinement import refine_planar_mesh


@dataclass(frozen=True)
class PlanarConvergenceThresholds:
    frequency_relative: float = 1e-4
    electric_field_relative: float = .01
    magnetic_field_relative: float = .01
    rf_relative: float = .005
    spectral_gap_relative: float = .001
    minimum_overlap: float = .9
    overlap_margin: float = .1

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = positive(getattr(self, name), name)
            if value >= 1:
                raise ValueError(f'{name} must be less than 1')
            object.__setattr__(self, name, value)

    def to_dict(self):
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data):
        names = list(cls.__dataclass_fields__)
        keys(data, names, names, 'planar convergence thresholds')
        return cls(**data)


@dataclass(frozen=True)
class PlanarConvergence:
    project: PlanarProject
    levels: int = 3
    mode_ranks: tuple = (1,)
    max_triangles: int = 250000
    thresholds: PlanarConvergenceThresholds = field(default_factory=PlanarConvergenceThresholds)

    def __post_init__(self):
        if not isinstance(self.project, PlanarProject):
            raise ValueError('planar convergence requires a PlanarProject')
        object.__setattr__(self, 'project', PlanarProject.from_dict(self.project.to_dict()))
        integer(self.levels, 'levels', 3)
        integer(self.max_triangles, 'max_triangles')
        if not isinstance(self.mode_ranks, (tuple, list)) or not self.mode_ranks:
            raise ValueError('mode_ranks must be a nonempty list of one-based ranks')
        for rank in self.mode_ranks:
            integer(rank, 'mode rank')
            if rank > self.project.case.modes:
                raise ValueError('mode rank exceeds the requested positive spectrum')
        if len(set(self.mode_ranks)) != len(self.mode_ranks):
            raise ValueError('mode_ranks must be unique')
        object.__setattr__(self, 'mode_ranks', tuple(self.mode_ranks))
        if not isinstance(self.thresholds, PlanarConvergenceThresholds):
            raise ValueError('expected PlanarConvergenceThresholds')
        self._check_budget()

    def _check_budget(self):
        case = self.project.case
        count = len(case.mesh.triangles) if isinstance(case, PlanarPolygonCase) else 2*case.nx*case.ny
        # Division bounds the loop without constructing enormous powers or meshes.
        if count > self.max_triangles:
            raise ValueError('initial planar mesh exceeds max_triangles')
        for _ in range(self.levels - 1):
            if count > self.max_triangles // 4:
                raise ValueError('requested planar refinement levels exceed max_triangles')
            count *= 4

    def projects(self):
        """Generate and validate every declared mesh before a worker solves any."""
        self._check_budget()
        original = PlanarProject.from_dict(self.project.to_dict())
        case = original.case
        if isinstance(case, PlanarPolygonCase):
            polygon_case = case
        else:
            from .planar import planar_matrices
            space, _, _, _ = planar_matrices(case)
            boundary = [[0., 0.], [case.width_m, 0.],
                        [case.width_m, case.height_m], [0., case.height_m]]
            mesh = PlanarMesh.create(boundary, space.points_xy_m, space.triangles)
            polygon_case = PlanarPolygonCase(
                mesh, case.polarization, case.element_order, case.modes,
                case.normalization_j_per_m, case.conductivity_s_per_m, case.name)
        result = [original]
        for _ in range(self.levels - 1):
            polygon_case = replace(polygon_case, mesh=refine_planar_mesh(
                polygon_case.mesh, max_triangles=self.max_triangles))
            result.append(PlanarProject(polygon_case, original.display_length_unit))
        return result

    def to_dict(self):
        return dict(format='superfish_ng_planar_convergence', convergence_version=1,
                    project=self.project.to_dict(), levels=self.levels,
                    mode_ranks=list(self.mode_ranks), max_triangles=self.max_triangles,
                    thresholds=self.thresholds.to_dict())

    @classmethod
    def from_dict(cls, data):
        names = ['format', 'convergence_version', 'project', 'levels', 'mode_ranks',
                 'max_triangles', 'thresholds']
        keys(data, names, names, 'planar convergence')
        if (data['format'] != 'superfish_ng_planar_convergence'
                or type(data['convergence_version']) is not int or data['convergence_version'] != 1):
            raise ValueError('expected superfish_ng_planar_convergence convergence_version 1')
        if not isinstance(data['mode_ranks'], list):
            raise ValueError('mode_ranks must be a JSON list')
        return cls(PlanarProject.from_dict(data['project']), data['levels'], data['mode_ranks'],
                   data['max_triangles'], PlanarConvergenceThresholds.from_dict(data['thresholds']))

    @classmethod
    def load(cls, path):
        return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def save(self, path):
        with Path(path).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(self.to_dict(), ensure_ascii=False, indent=2, allow_nan=False) + '\n')

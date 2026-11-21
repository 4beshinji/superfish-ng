# SPDX-License-Identifier: Apache-2.0
"""Strict single-domain Cartesian curved-P2 inputs, geometry and spaces.

Dedicated v3 API; legacy planar dispatch/CLI/native integration belongs to P08.
This module neither solves modes nor invents a straight mesh for curved data.
"""
from dataclasses import dataclass
from types import MappingProxyType
import numpy as np
from .config import keys, positive, integer
from .planar_curved_geometry import (PlanarQuadraticTriangle, strict_array,
    immutable_array, check_planar_edges, exact_boundary_area)

_LOCAL_EDGES = ((0, 1, 3), (1, 2, 4), (2, 0, 5))


def _bounded_integer(value, name, minimum, maximum):
    integer(value, name, minimum)
    if value > maximum:
        raise ValueError(f'{name} must be <= {maximum}')


@dataclass(frozen=True, eq=False)
class PlanarCurvedDomain:
    points_xy_m: object
    cell_nodes: object
    boundary_nodes: object
    max_geometry_boxes: int = 100000

    def __post_init__(self):
        _bounded_integer(self.max_geometry_boxes, 'max_geometry_boxes', 1, 100000000)
        points = strict_array(self.points_xy_m, 2, 'planar curved points_xy_m')
        cells = strict_array(self.cell_nodes, 6, 'planar curved cell_nodes', indices=True)
        boundary = strict_array(self.boundary_nodes, 3, 'planar curved boundary_nodes', indices=True)
        if len(boundary) < 3 or np.any(cells >= len(points)) or np.any(boundary >= len(points)):
            raise ValueError('planar curved boundary needs at least three edges; all indices must be in range')
        if len(np.unique(points, axis=0)) != len(points):
            raise ValueError('planar curved nodes have duplicate physical xy coordinates')
        if len(np.unique(cells)) != len(points):
            raise ValueError('planar curved points contain unused nodes')
        if len({tuple(sorted(map(int, cell[:3]))) for cell in cells}) != len(cells):
            raise ValueError('planar curved domain repeats a cell')
        incidence = {}
        for owner, cell in enumerate(cells):
            if len(set(map(int, cell))) != 6:
                raise ValueError('planar curved cell repeats a node')
            for local, (i, j, k) in enumerate(_LOCAL_EDGES):
                a, b, mid = map(int, (cell[i], cell[j], cell[k]))
                incidence.setdefault(tuple(sorted((a, b))), []).append((owner, a, b, mid, local))
        mids = set()
        vertices = set(map(int, cells[:, :3].ravel()))
        expected = {}
        neighbors = [set() for _ in cells]
        for pair, owners in incidence.items():
            if len(owners) > 2 or len({record[3] for record in owners}) != 1:
                raise ValueError(f'planar curved nonconforming shared edge {pair}')
            mid = owners[0][3]
            if mid in mids or mid in vertices:
                raise ValueError('each planar curved edge requires a unique midpoint separate from vertices')
            mids.add(mid)
            if len(owners) == 2:
                if owners[0][1:3] != owners[1][2:0:-1]:
                    raise ValueError('planar curved shared edge orientations must oppose')
                a, b = owners[0][0], owners[1][0]
                neighbors[a].add(b)
                neighbors[b].add(a)
            else:
                record = owners[0]
                expected[record[1:4]] = (record[0], record[4])
        if len(vertices)-len(incidence)+len(cells) != 1:
            raise ValueError('planar curved domain requires disk Euler characteristic; holes are unsupported')
        visited, pending = {0}, [0]
        while pending:
            for neighbor in neighbors[pending.pop()]-visited:
                visited.add(neighbor)
                pending.append(neighbor)
        if len(visited) != len(cells):
            raise ValueError('planar curved cells must be connected through shared edges')
        supplied = [tuple(map(int, edge)) for edge in boundary]
        if len(set(supplied)) != len(supplied) or set(supplied) != set(expected):
            raise ValueError('planar curved boundary must match every oriented one-sided cell edge including its midpoint')
        if len(set(map(int, boundary[:, 0]))) != len(boundary) or not np.array_equal(boundary[:, 1], np.roll(boundary[:, 0], -1)):
            raise ValueError('planar curved boundary must be one ordered closed CCW cycle')
        elements = tuple(PlanarQuadraticTriangle(points[cell]) for cell in cells)
        exact_area = sum(element.exact_area_m2 for element in elements)
        green_area = exact_boundary_area(points, boundary)
        if exact_area != green_area or green_area <= 0:
            raise ValueError('planar curved Green boundary area disagrees with cell area or CCW orientation')
        with np.errstate(over='ignore', invalid='ignore'):
            extent = np.ptp(points, axis=0)
        if not np.isfinite(extent).all() or np.max(extent) <= 0 or not np.isfinite(float(exact_area)):
            raise ValueError('planar curved domain exceeds finite SI geometry arithmetic')
        edge_report = check_planar_edges(points, incidence, self.max_geometry_boxes)
        owners = immutable_array([expected[edge][0] for edge in supplied], np.int64)
        local = immutable_array([expected[edge][1] for edge in supplied], np.int64)
        for name, value in [('points_xy_m', points), ('cell_nodes', cells), ('boundary_nodes', boundary),
                            ('boundary_cells', owners), ('boundary_local_edges', local), ('elements', elements)]:
            object.__setattr__(self, name, value)
        object.__setattr__(self, 'area_m2', float(exact_area))
        object.__setattr__(self, 'geometry_diagnostics', MappingProxyType(dict(edge_report,
            cells=len(cells), euler_characteristic=1, boundary_edges=len(boundary),
            area_m2=float(exact_area), green_area_m2=float(green_area), exact_green_area_agrees=True,
            minimum_jacobian_lower_bound_m2=min(element.determinant_lower_bound_m2 for element in elements))))

    @classmethod
    def from_dict(cls, data, *, max_geometry_boxes=100000):
        names = ['format', 'domain_version', 'points_xy_m', 'cell_nodes', 'boundary_nodes']
        keys(data, names, names, 'planar curved domain')
        if data['format'] != 'superfish_ng_planar_curved_domain' or type(data['domain_version']) is not int or data['domain_version'] != 1:
            raise ValueError('expected superfish_ng_planar_curved_domain domain_version 1')
        return cls(data['points_xy_m'], data['cell_nodes'], data['boundary_nodes'], max_geometry_boxes)

    def to_dict(self):
        return dict(format='superfish_ng_planar_curved_domain', domain_version=1,
            points_xy_m=self.points_xy_m.tolist(), cell_nodes=self.cell_nodes.tolist(), boundary_nodes=self.boundary_nodes.tolist())

    def __eq__(self, other):
        return isinstance(other, PlanarCurvedDomain) and self.to_dict() == other.to_dict()

    def boundary_evaluate(self, edge_index, parameters):
        if type(edge_index) is not int or not 0 <= edge_index < len(self.boundary_nodes):
            raise ValueError('planar curved boundary edge_index is out of range')
        try:
            raw = np.asarray(parameters, dtype=object)
        except (TypeError, ValueError) as exc:
            raise ValueError('planar curved boundary parameters require a nonempty vector') from exc
        if raw.ndim != 1 or not len(raw):
            raise ValueError('planar curved boundary parameters require a nonempty vector')
        t = strict_array([[value, 0] for value in raw], 2, 'boundary parameters')[:, 0]
        if np.any(t < 0) or np.any(t > 1):
            raise ValueError('planar curved boundary parameters must lie in [0,1]')
        p, q, mid = self.points_xy_m[self.boundary_nodes[edge_index]]
        values = p+(t*(2*t-1))[:, None]*(q-p)+(4*t*(1-t))[:, None]*(mid-p)
        derivative = (4*t-1)[:, None]*(q-p)+(4-8*t)[:, None]*(mid-p)
        speed = np.linalg.norm(derivative, axis=1)
        if not np.isfinite(values).all() or np.any(speed <= 0) or not np.isfinite(speed).all():
            raise ValueError('planar curved boundary arithmetic is unresolved')
        tangent = derivative/speed[:, None]
        normal = np.column_stack((tangent[:, 1], -tangent[:, 0]))
        return dict(points_xy_m=values, derivatives_xy_m=derivative, speed_m=speed,
                    tangent_xy=tangent, outward_normal_xy=normal)

    def boundary_length_m(self, *, quadrature_order=12):
        _bounded_integer(quadrature_order, 'wall_quadrature_order', 4, 32)
        nodes, weights = np.polynomial.legendre.leggauss(quadrature_order)
        return sum(float((weights/2) @ self.boundary_evaluate(i, (nodes+1)/2)['speed_m']) for i in range(len(self.boundary_nodes)))


@dataclass(frozen=True, eq=False)
class PlanarCurvedCase:
    domain: PlanarCurvedDomain
    polarization: str = 'te'
    modes: int = 4
    normalization_j_per_m: float = 1.
    conductivity_s_per_m: float = 5.8e7
    name: str = 'planar curved cutoff'
    quadrature_order: int = 8
    wall_quadrature_order: int = 12
    max_geometry_boxes: int = 100000

    def __post_init__(self):
        if not isinstance(self.domain, PlanarCurvedDomain):
            raise ValueError('planar curved case requires an explicit PlanarCurvedDomain')
        if self.polarization not in ('te', 'tm'):
            raise ValueError('planar curved polarization must be te or tm')
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError('planar curved name must be nonempty')
        integer(self.modes, 'modes')
        _bounded_integer(self.quadrature_order, 'quadrature_order', 4, 32)
        _bounded_integer(self.wall_quadrature_order, 'wall_quadrature_order', 4, 32)
        _bounded_integer(self.max_geometry_boxes, 'max_geometry_boxes', 1, 100000000)
        for name in ('normalization_j_per_m', 'conductivity_s_per_m'):
            object.__setattr__(self, name, positive(getattr(self, name), name))
        if self.domain.max_geometry_boxes != self.max_geometry_boxes:
            object.__setattr__(self, 'domain', PlanarCurvedDomain.from_dict(self.domain.to_dict(), max_geometry_boxes=self.max_geometry_boxes))

    @property
    def element_order(self):
        return 2

    @property
    def width_m(self):
        return float(np.ptp(self.domain.points_xy_m[:, 0]))

    @property
    def height_m(self):
        return float(np.ptp(self.domain.points_xy_m[:, 1]))

    def to_dict(self):
        return dict(format='superfish_ng_planar_case', schema_version=3, name=self.name,
            model=dict(physics='rf_eigenmode', coordinates='cartesian', polarization=self.polarization,
                propagation_constant_per_m=0, material='vacuum', boundary='pec'),
            geometry=dict(type='quadratic_mesh', domain=self.domain.to_dict()), mesh=dict(element_order=2),
            numerics=dict(quadrature_order=self.quadrature_order, wall_quadrature_order=self.wall_quadrature_order,
                max_geometry_boxes=self.max_geometry_boxes), modes=self.modes,
            rf=dict(stored_energy_j_per_m=self.normalization_j_per_m, conductivity_s_per_m=self.conductivity_s_per_m))

    @classmethod
    def from_dict(cls, data):
        names = ['format', 'schema_version', 'name', 'model', 'geometry', 'mesh', 'numerics', 'modes', 'rf']
        keys(data, names, names, 'planar curved case')
        if data['format'] != 'superfish_ng_planar_case' or type(data['schema_version']) is not int or data['schema_version'] != 3:
            raise ValueError('expected superfish_ng_planar_case schema_version 3')
        model = data['model']
        names = ['physics', 'coordinates', 'polarization', 'propagation_constant_per_m', 'material', 'boundary']
        keys(model, names, names, 'planar curved model')
        for key, expected in [('physics', 'rf_eigenmode'), ('coordinates', 'cartesian'), ('material', 'vacuum'), ('boundary', 'pec')]:
            if model[key] != expected:
                raise ValueError(f'planar curved model.{key}: only {expected} is implemented')
        beta = model['propagation_constant_per_m']
        if type(beta) not in (int, float) or beta != 0:
            raise ValueError('planar curved cutoff requires propagation_constant_per_m=0')
        geometry = data['geometry']
        keys(geometry, ['type', 'domain'], ['type', 'domain'], 'planar curved geometry')
        if geometry['type'] != 'quadratic_mesh':
            raise ValueError('planar curved v3 requires explicit quadratic_mesh; holes and implicit arcs are unsupported')
        mesh = data['mesh']
        keys(mesh, ['element_order'], ['element_order'], 'planar curved mesh')
        if type(mesh['element_order']) is not int or mesh['element_order'] != 2:
            raise ValueError('planar curved element_order must be 2')
        numerics = data['numerics']
        names = ['quadrature_order', 'wall_quadrature_order', 'max_geometry_boxes']
        keys(numerics, names, names, 'planar curved numerics')
        for key in names:
            _bounded_integer(numerics[key], key, 1 if key == 'max_geometry_boxes' else 4, 100000000 if key == 'max_geometry_boxes' else 32)
        rf = data['rf']
        names = ['stored_energy_j_per_m', 'conductivity_s_per_m']
        keys(rf, names, names, 'planar curved rf')
        domain = PlanarCurvedDomain.from_dict(geometry['domain'], max_geometry_boxes=numerics['max_geometry_boxes'])
        return cls(domain, model['polarization'], data['modes'], rf['stored_energy_j_per_m'],
                   rf['conductivity_s_per_m'], data['name'], **numerics)

    def __eq__(self, other):
        return isinstance(other, PlanarCurvedCase) and self.to_dict() == other.to_dict()


@dataclass(frozen=True, eq=False)
class PlanarCurvedSpace:
    domain: PlanarCurvedDomain
    free_dofs: np.ndarray

    @property
    def points_xy_m(self):
        return self.domain.points_xy_m

    @property
    def cell_nodes(self):
        return self.domain.cell_nodes

    @property
    def boundary_nodes(self):
        return self.domain.boundary_nodes

    @property
    def boundary_cells(self):
        return self.domain.boundary_cells

    @property
    def boundary_local_edges(self):
        return self.domain.boundary_local_edges

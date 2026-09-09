# SPDX-License-Identifier: Apache-2.0
"""Strict versioned JSON case input. All lengths in metres."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import Model


def positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite positive number")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return float(value)


def integer(value, name, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def acceleration_parameters(length, active_length=None, interval=None, phase_origin=None):
    def finite(value, name):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{name} must be a finite number')
        return float(value)
    active = length if active_length is None else positive(active_length, 'active_length_m')
    origin = 0. if phase_origin is None else finite(phase_origin, 'phase_origin_m')
    if interval is None:
        interval = (0., length)
    if not isinstance(interval, (tuple, list)) or len(interval) != 2:
        raise ValueError('voltage_interval_m must contain [start_m, end_m]')
    a, b = (finite(x, 'voltage_interval_m') for x in interval)
    if not 0 <= a < b <= length:
        raise ValueError('voltage_interval_m must satisfy 0 <= start < end <= cavity length')
    return active, (a, b), origin


def keys(data, allowed, required, label):
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be an object")
    unknown, missing = set(data) - set(allowed), set(required) - set(data)
    if unknown or missing:
        raise ValueError(f"{label}: unknown keys {sorted(unknown)}, missing keys {sorted(missing)}")


@dataclass(frozen=True)
class Case:
    profile: tuple[tuple[float, float], ...]  # (z, outer radius), connected to axis
    nr: int = 24
    nz: int = 32  # approximate axial count, each profile corner is preserved
    modes: int = 3
    beta: float = 1.0
    conductivity_s_per_m: float = 5.8e7
    normalization_j: float = 1.0
    name: str = "cavity"
    z_min: str = "pec"
    z_max: str = "pec"
    geometry_type: str = "profile"
    arcs: tuple[tuple[int, float, str], ...] = ()  # (end vertex index, radius m, direction in z,r)
    arc_chord_tolerance_m: float = 1e-5
    triangulation: str = "diagonal"

    boundary_max_edge_m: float | None = None
    corner_max_edge_m: float | None = None
    corner_radius_m: float | None = None
    model: 'Model | None' = None
    active_length_m: float | None = None
    voltage_interval_m: tuple[float, float] | None = None
    phase_origin_m: float | None = None
    element_order: int = 1
    geometry_order: int = 1
    curved_refinement_levels: int = 0
    quadrature_order: int = 8
    contour: object | None = None
    contour_mesh: object | None = None
    curved_contour: object | None = None
    curve_chord_tolerance_m: float | None = None
    curve_chord_max_segments: int = 20000
    curve_segments_per_curve: tuple | None = None
    curved_refinement_steps: tuple = ()

    def __post_init__(self):
        if self.curved_contour is not None:
            from .curved_contour import CurvedContour
            if not isinstance(self.curved_contour,CurvedContour) or self.profile:
                raise ValueError('curved_contour requires a validated CurvedContour and empty profile')
            if self.curve_segments_per_curve is not None and type(self.curve_segments_per_curve) is not tuple:
                raise ValueError('curve_segments_per_curve must be an immutable tuple')
            approximation = self.curved_contour.linearize(self.curve_chord_tolerance_m,max_segments=self.curve_chord_max_segments,segments_per_curve=self.curve_segments_per_curve)
            if self.contour is not None and self.contour != approximation.contour:
                raise ValueError('supplied contour differs from curved geometry chords; clear contour when changing chord tolerance or partition')
            object.__setattr__(self,'contour',approximation.contour)
        elif self.curve_chord_tolerance_m is not None or self.curve_chord_max_segments!=20000 or self.curve_segments_per_curve is not None:
            raise ValueError('curve chord controls require curved_contour')
        if self.contour_mesh is not None:
            from .mesh_controls import ContourMeshControls
            if not isinstance(self.contour_mesh,ContourMeshControls) or self.contour is None:
                raise ValueError('contour_mesh requires validated ContourMeshControls and contour geometry')
            self.contour_mesh.__post_init__()
        if type(self.element_order) is not int or self.element_order not in (1, 2):
            raise ValueError("element_order must be integer 1 or 2")
        if type(self.geometry_order) is not int or self.geometry_order not in (1,2):
            raise ValueError('geometry_order must be integer 1 or 2')
        if type(self.quadrature_order) is not int or self.quadrature_order<2:
            raise ValueError('quadrature_order must be integer >= 2')
        if self.geometry_order==2 and (self.curved_contour is None or self.element_order!=2):
            raise ValueError('geometry_order=2 requires curved_contour and element_order=2')
        if self.geometry_order==1 and self.quadrature_order!=8:
            raise ValueError('quadrature_order requires geometry_order=2')
        if type(self.curved_refinement_levels) is not int or self.curved_refinement_levels < 0:
            raise ValueError('curved_refinement_levels must be a nonnegative integer')
        if self.curved_refinement_levels and self.geometry_order != 2:
            raise ValueError('curved_refinement_levels requires geometry_order=2')
        from .curved_refinement_steps import CurvedRefinementStep
        if type(self.curved_refinement_steps) is not tuple:
            raise ValueError('curved_refinement_steps must be an immutable tuple')
        for step in self.curved_refinement_steps:
            if not isinstance(step, CurvedRefinementStep):
                raise ValueError('curved_refinement_steps requires validated CurvedRefinementStep instances')
            step.__post_init__()
        if self.curved_refinement_steps:
            if self.geometry_order != 2:
                raise ValueError('curved_refinement_steps requires geometry_order=2')
            if self.curved_refinement_levels:
                raise ValueError('curved_refinement_steps conflicts with curved_refinement_levels; use uniform steps in the ordered history')
        if self.model is not None:
            from .model import Model
            if not isinstance(self.model, Model):
                raise ValueError('model must be a validated Model instance or None for legacy input')
            self.model.__post_init__()
        if not isinstance(self.name, str):
            raise ValueError("name must be a string")
        if self.contour is not None:
            from .contour import Contour
            if not isinstance(self.contour, Contour) or self.profile:
                raise ValueError('contour Case requires a validated Contour and empty profile')
            if self.geometry_type not in ('profile', 'contour', 'curved_contour'):
                raise ValueError('contour cannot be combined with profile geometry metadata')
            object.__setattr__(self, 'geometry_type', 'curved_contour' if self.curved_contour is not None else 'contour')
            for side, z in [('z_min', 0.), ('z_max', self.length)]:
                points=self.contour.vertices_zr_m
                tags={tag for i,tag in enumerate(self.contour.edge_tags)
                      if points[i][0]==points[(i+1)%len(points)][0]==z and tag!='axis'}
                value='mixed' if len(tags)>1 else next(iter(tags), 'pec')
                if getattr(self,side) not in ('pec',value):
                    raise ValueError('contour tags disagree with Case end boundary')
                object.__setattr__(self,side,value)
        else:
            if len(self.profile) < 2:
                raise ValueError("profile requires at least two [z_m, radius_m] points")
            converted = []
            for point in self.profile:
                if not isinstance(point, (list, tuple)) or len(point) != 2:
                    raise ValueError("profile points must be [z_m, radius_m]")
                z, r = point
                if isinstance(z, bool) or not isinstance(z, (int, float)) or not math.isfinite(z):
                    raise ValueError("profile z must be finite")
                converted.append((float(z), positive(r, "profile radius")))
            object.__setattr__(self, "profile", tuple(converted))
            if self.geometry_type not in ("profile", "stepped_profile", "arc_profile"):
                raise ValueError("geometry_type must be profile, stepped_profile or arc_profile")
            if self.geometry_type == "profile":
                if self.profile[0][0] != 0 or any(b[0] <= a[0] for a, b in zip(self.profile, self.profile[1:])):
                    raise ValueError("profile must start at z=0 and have strictly increasing z")
            else:
                if (self.profile[0][0] != 0 or self.profile[-1][0] <= 0
                        or any(b[0] < a[0] or b == a for a, b in zip(self.profile, self.profile[1:]))
                        or self.profile[1][0] == 0 or self.profile[-2][0] == self.profile[-1][0]
                        or any(a[0] == b[0] == c[0] for a, b, c in zip(self.profile, self.profile[1:], self.profile[2:]))):
                    raise ValueError("stepped_profile requires nondecreasing z from zero, isolated nonzero vertical steps, and nonvertical first/last segments")
        for name in ('boundary_max_edge_m', 'corner_max_edge_m', 'corner_radius_m'):
            if getattr(self, name) is not None:
                positive(getattr(self, name), name)
        if (self.corner_max_edge_m is None) != (self.corner_radius_m is None):
            raise ValueError('corner_max_edge_m and corner_radius_m must be specified together')
        if self.corner_max_edge_m is not None and self.geometry_type == 'arc_profile':
            raise ValueError('corner refinement requires a polygon profile; arc tangent junctions are not sharp corners')
        integer(self.nr, "nr", 2)
        integer(self.nz, "nz", 2)
        if self.triangulation not in ('diagonal', 'crossed'):
            raise ValueError('triangulation must be diagonal or crossed')
        integer(self.modes, "modes")
        positive(self.beta, "beta")
        if self.beta > 1:
            raise ValueError("beta must be <= 1")
        positive(self.conductivity_s_per_m, "conductivity_s_per_m")
        positive(self.normalization_j, "normalization_j")
        _, interval, _ = self.acceleration_parameters
        if self.voltage_interval_m is not None:
            object.__setattr__(self, 'voltage_interval_m', interval)
        if (self.has_acceleration_overrides or self.element_order == 2 or self.contour is not None) and self.model is None:
            from .model import Model
            object.__setattr__(self, 'model', Model())
        positive(self.arc_chord_tolerance_m, "arc_chord_tolerance_m")
        if self.geometry_type != 'arc_profile' and (self.arcs or self.arc_chord_tolerance_m != 1e-5):
            raise ValueError('arc metadata requires arc_profile geometry')
        if self.geometry_type == 'arc_profile':
            converted_arcs = []
            for arc in self.arcs:
                if not isinstance(arc, (list, tuple)) or len(arc) != 3:
                    raise ValueError('arcs must contain [end_index, radius_m, direction]')
                index, radius, direction = arc
                integer(index, 'arc end_index')
                if index >= len(self.profile) or direction not in ('cw', 'ccw'):
                    raise ValueError('arc end_index out of range or unsupported direction')
                converted_arcs.append((index, positive(radius, 'arc radius'), direction))
            if not converted_arcs or len({a[0] for a in converted_arcs}) != len(converted_arcs):
                raise ValueError('arc_profile requires nonempty arcs with unique end indices')
            object.__setattr__(self, 'arcs', tuple(sorted(converted_arcs)))
            from .geometry import linearize_profile
            linearize_profile(self)  # validate radius, monotonicity and positive r before meshing
        for side in ("z_min", "z_max"):
            value = getattr(self, side)
            if self.contour is not None and value == "mixed":
                continue
            if not isinstance(value, str) or value not in ("pec", "electric_symmetry", "magnetic_symmetry"):
                raise ValueError(f"{side} must be pec, electric_symmetry or magnetic_symmetry")

    @property
    def length(self):
        return max(z for z,r in self.contour.vertices_zr_m) if self.contour is not None else self.profile[-1][0]

    @property
    def has_acceleration_overrides(self):
        return any(v is not None for v in (self.active_length_m, self.voltage_interval_m, self.phase_origin_m))

    @property
    def acceleration_parameters(self):
        return acceleration_parameters(self.length, self.active_length_m, self.voltage_interval_m, self.phase_origin_m)

    def reflected_acceleration_parameters(self, side):
        if "mixed" in (self.z_min, self.z_max):
            raise ValueError("reflection requires a complete symmetry end; mixed end tags cannot be mirrored")
        options = {}
        if self.active_length_m is not None:
            options['active_length_m'] = 2*self.active_length_m
        if self.voltage_interval_m is not None:
            a, b = self.voltage_interval_m
            if (side == 'z_min' and a != 0) or (side == 'z_max' and b != self.length):
                raise ValueError('reflection requires voltage_interval_m to touch the symmetry plane; disjoint intervals are unsupported')
            options['voltage_interval_m'] = (self.length-b, self.length+b) if side == 'z_min' else (a, 2*self.length-a)
        if self.phase_origin_m is not None:
            options['phase_origin_m'] = self.phase_origin_m + (self.length if side == 'z_min' else 0.)
        return options

    @classmethod
    def from_dict(cls, data):
        keys(data, ["schema_version", "name", "geometry", "mesh", "solver", "rf", "boundaries", "model"],
             ["schema_version", "geometry"], "case")
        if type(data["schema_version"]) is not int or data["schema_version"] not in (1, 2, 3):
            raise ValueError("only schema_version 1, 2 and 3 are supported")
        model = None
        if data['schema_version'] == 3:
            from .model import Model
            if 'model' not in data:
                raise ValueError('schema_version 3 requires an explicit model')
            model = Model.from_dict(data['model'])
        elif 'model' in data:
            raise ValueError('explicit model requires schema_version 3')
        if data["schema_version"] == 1 and "boundaries" in data:
            raise ValueError("explicit boundaries require schema_version 2")
        boundaries = data.get("boundaries", {})
        keys(boundaries, ["z_min", "z_max"], [], "boundaries")
        g = data["geometry"]
        if not isinstance(g, dict):
            raise ValueError("geometry must be an object")
        if g.get("type") == "pillbox":
            keys(g, ["type", "radius_m", "length_m"], ["type", "radius_m", "length_m"], "geometry")
            radius = positive(g["radius_m"], "radius_m")
            profile = ((0.0, radius), (positive(g["length_m"], "length_m"), radius))
        elif g.get("type") == 'contour':
            if data['schema_version'] != 3 or boundaries:
                raise ValueError('contour requires v3 and edge_tags instead of boundaries')
            keys(g, ['type','vertices_zr_m','edge_tags'], ['type','vertices_zr_m','edge_tags'], 'geometry')
            profile = ()
        elif g.get('type') == 'curved_contour':
            if data['schema_version']!=3 or boundaries:
                raise ValueError('curved_contour requires v3 and edge_tags instead of boundaries')
            keys(g,('type','curves','edge_tags','join_tolerance_m','minimum_gap_m','chord_tolerance_m','chord_max_segments','minimum_meridional_radius_m','segments_per_curve'),
                 ('type','curves','edge_tags','join_tolerance_m','chord_tolerance_m'),'geometry')
            profile = ()
        elif g.get("type") in ("profile", "stepped_profile", "arc_profile"):
            if g["type"] != "profile" and data["schema_version"] < 2:
                raise ValueError("stepped_profile and arc_profile require schema_version 2")
            arc_keys = ["arcs", "chord_tolerance_m"] if g["type"] == 'arc_profile' else []
            keys(g, ["type", "points_zr_m"]+arc_keys, ["type", "points_zr_m"]+arc_keys, "geometry")
            if not isinstance(g["points_zr_m"], list):
                raise ValueError("points_zr_m must be an array")
            profile = g["points_zr_m"]
        else:
            raise ValueError("geometry type must be pillbox, profile, stepped_profile or arc_profile")
        geometry_options = {}
        if g['type']=='curved_contour':
            from .curved_contour import CurvedContour
            if 'segments_per_curve' in g and type(g['segments_per_curve']) is not list:
                raise ValueError('geometry.segments_per_curve must be an array')
            geometry_options.update(curved_contour=CurvedContour.from_dict({k:v for k,v in g.items()
                                    if k not in ('type','chord_tolerance_m','chord_max_segments','segments_per_curve')}),
                                    curve_chord_tolerance_m=g['chord_tolerance_m'],
                                    curve_segments_per_curve=tuple(g['segments_per_curve']) if 'segments_per_curve' in g else None,
                                    curve_chord_max_segments=g.get('chord_max_segments',20000))
        if g['type'] == 'contour':
            from .contour import Contour
            geometry_options['contour'] = Contour(g['vertices_zr_m'], g['edge_tags'])
        if g['type'] == 'arc_profile':
            if not isinstance(g['arcs'], list):
                raise ValueError('geometry.arcs must be an array')
            for arc in g['arcs']:
                keys(arc, ['end_index', 'radius_m', 'direction'], ['end_index', 'radius_m', 'direction'], 'arc')
            geometry_options = {'arcs': tuple((a['end_index'], a['radius_m'], a['direction']) for a in g['arcs']),
                                'arc_chord_tolerance_m': g['chord_tolerance_m']}
        mesh, solver, rf = (data.get(k, {}) for k in ("mesh", "solver", "rf"))
        keys(mesh, ["nr", "nz", "triangulation", "boundary_max_edge_m", "corner_max_edge_m", "corner_radius_m", "contour_mesh", "geometry_order", "curved_refinement_levels", "curved_refinement_steps"], [], "mesh")
        if 'contour_mesh' in mesh:
            from .mesh_controls import ContourMeshControls
            if data['schema_version'] != 3:
                raise ValueError('mesh.contour_mesh requires schema_version 3')
            mesh = dict(mesh,contour_mesh=ContourMeshControls.from_dict(mesh['contour_mesh']))
        if any(k in mesh for k in ('boundary_max_edge_m', 'corner_max_edge_m', 'corner_radius_m')) and data['schema_version'] < 2:
            raise ValueError('physical mesh sizes require schema_version 2')
        for k in ('boundary_max_edge_m', 'corner_max_edge_m', 'corner_radius_m'):
            if k in mesh:
                positive(mesh[k], k)
        if 'triangulation' in mesh and data['schema_version'] < 2:
            raise ValueError('explicit triangulation requires schema_version 2')
        if "geometry_order" in mesh and data["schema_version"]!=3:
            raise ValueError('mesh.geometry_order requires schema_version 3')
        if 'curved_refinement_levels' in mesh and (data['schema_version'] != 3 or mesh.get('geometry_order') != 2):
            raise ValueError('mesh.curved_refinement_levels requires v3 geometry_order=2')
        if 'curved_refinement_steps' in mesh:
            from .curved_refinement_steps import steps_from_dict
            if data['schema_version'] != 3 or mesh.get('geometry_order') != 2:
                raise ValueError('mesh.curved_refinement_steps requires v3 geometry_order=2')
            mesh = dict(mesh, curved_refinement_steps=steps_from_dict(mesh['curved_refinement_steps']))
        keys(solver, ["modes", "element_order", "quadrature_order"], [], "solver")
        if "quadrature_order" in solver and (data["schema_version"]!=3 or mesh.get("geometry_order",1)!=2):
            raise ValueError('solver.quadrature_order requires v3 geometry_order=2')
        if "element_order" in solver and data["schema_version"] != 3:
            raise ValueError("solver.element_order requires schema_version 3")
        additions = ['active_length_m', 'voltage_interval_m', 'phase_origin_m']
        keys(rf, ["beta", "conductivity_s_per_m", "normalization_j"]+additions, [], "rf")
        for key in additions:
            if key in rf and (data['schema_version'] != 3 or rf[key] is None):
                raise ValueError(f'rf.{key} requires schema_version 3 and a non-null value')
        return cls(profile=profile, geometry_type="profile" if g["type"] == "pillbox" else g['type'],
                   name=data.get("name", "cavity"), model=model, **mesh, **solver, **rf, **boundaries, **geometry_options)

    @classmethod
    def load(cls, path):
        def reject_duplicate(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate JSON key: {key}")
                result[key] = value
            return result
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate))

    def to_dict(self):
        data = {"schema_version": 1, "name": self.name,
                "geometry": {"type": self.geometry_type, "points_zr_m": [list(p) for p in self.profile]},
                "mesh": {"nr": self.nr, "nz": self.nz}, "solver": {"modes": self.modes},
                "rf": {"beta": self.beta, "conductivity_s_per_m": self.conductivity_s_per_m,
                       "normalization_j": self.normalization_j}}
        if self.z_min != "pec" or self.z_max != "pec":
            data.update(schema_version=2, boundaries={"z_min": self.z_min, "z_max": self.z_max})
        if self.geometry_type in ("stepped_profile", "arc_profile"):
            data["schema_version"] = 2
        if self.geometry_type == 'arc_profile':
            data['geometry'].update(arcs=[{'end_index': i, 'radius_m': r, 'direction': d} for i, r, d in self.arcs],
                                    chord_tolerance_m=self.arc_chord_tolerance_m)
        if self.triangulation != 'diagonal':
            data['schema_version'] = 2
            data['mesh']['triangulation'] = self.triangulation
        for key in ('boundary_max_edge_m', 'corner_max_edge_m', 'corner_radius_m'):
            if getattr(self, key) is not None:
                data['schema_version'] = 2
                data['mesh'][key] = getattr(self, key)
        if self.geometry_order==2:
            data["mesh"]["geometry_order"]=2
            data["solver"]["quadrature_order"]=self.quadrature_order
        if self.curved_refinement_levels:
            data["mesh"]["curved_refinement_levels"] = self.curved_refinement_levels
        if self.curved_refinement_steps:
            from .curved_refinement_steps import steps_to_dict
            data['mesh']['curved_refinement_steps'] = steps_to_dict(self.curved_refinement_steps)
        if self.element_order != 1:
            data["solver"]["element_order"] = self.element_order
        if self.model is not None:
            data.update(schema_version=3, model=self.model.to_dict())
        for key in ('active_length_m', 'voltage_interval_m', 'phase_origin_m'):
            value = getattr(self, key)
            if value is not None:
                data['rf'][key] = list(value) if key == 'voltage_interval_m' else value
        if self.contour is not None:
            data['geometry'] = {'type':'contour', 'vertices_zr_m':[list(p) for p in self.contour.vertices_zr_m],
                                'edge_tags':list(self.contour.edge_tags)}
            data.pop('boundaries', None)
        if self.contour_mesh is not None:
            data['mesh']['contour_mesh'] = self.contour_mesh.to_dict()
        if self.curved_contour is not None:
            data['geometry'] = dict(type='curved_contour',**self.curved_contour.to_dict(),
                                    chord_tolerance_m=self.curve_chord_tolerance_m,
                                    chord_max_segments=self.curve_chord_max_segments)
            if self.curve_segments_per_curve is not None:data['geometry']['segments_per_curve']=list(self.curve_segments_per_curve)
        return data

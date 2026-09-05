# SPDX-License-Identifier: Apache-2.0
"""Strict versioned JSON case input. All lengths in metres."""
from dataclasses import dataclass
import json
import math
from pathlib import Path


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

    def __post_init__(self):
        if not isinstance(self.name, str):
            raise ValueError("name must be a string")
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
        if self.profile[0][0] != 0 or any(b[0] <= a[0] for a, b in zip(self.profile, self.profile[1:])):
            raise ValueError("profile must start at z=0 and have strictly increasing z")
        integer(self.nr, "nr", 2)
        integer(self.nz, "nz", 2)
        integer(self.modes, "modes")
        positive(self.beta, "beta")
        if self.beta > 1:
            raise ValueError("beta must be <= 1")
        positive(self.conductivity_s_per_m, "conductivity_s_per_m")
        positive(self.normalization_j, "normalization_j")

    @property
    def length(self):
        return self.profile[-1][0]

    @classmethod
    def from_dict(cls, data):
        keys(data, ["schema_version", "name", "geometry", "mesh", "solver", "rf"],
             ["schema_version", "geometry"], "case")
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise ValueError("only schema_version 1 is supported")
        g = data["geometry"]
        if not isinstance(g, dict):
            raise ValueError("geometry must be an object")
        if g.get("type") == "pillbox":
            keys(g, ["type", "radius_m", "length_m"], ["type", "radius_m", "length_m"], "geometry")
            radius = positive(g["radius_m"], "radius_m")
            profile = ((0.0, radius), (positive(g["length_m"], "length_m"), radius))
        elif g.get("type") == "profile":
            keys(g, ["type", "points_zr_m"], ["type", "points_zr_m"], "geometry")
            if not isinstance(g["points_zr_m"], list):
                raise ValueError("points_zr_m must be an array")
            profile = g["points_zr_m"]
        else:
            raise ValueError("geometry type must be pillbox or profile")
        mesh, solver, rf = (data.get(k, {}) for k in ("mesh", "solver", "rf"))
        keys(mesh, ["nr", "nz"], [], "mesh")
        keys(solver, ["modes"], [], "solver")
        keys(rf, ["beta", "conductivity_s_per_m", "normalization_j"], [], "rf")
        return cls(profile=profile, name=data.get("name", "cavity"), **mesh, **solver, **rf)

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
        return {"schema_version": 1, "name": self.name,
                "geometry": {"type": "profile", "points_zr_m": [list(p) for p in self.profile]},
                "mesh": {"nr": self.nr, "nz": self.nz}, "solver": {"modes": self.modes},
                "rf": {"beta": self.beta, "conductivity_s_per_m": self.conductivity_s_per_m,
                       "normalization_j": self.normalization_j}}

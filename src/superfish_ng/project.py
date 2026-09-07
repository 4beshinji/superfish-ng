# SPDX-License-Identifier: Apache-2.0
"""Portable editing document layered over the unchanged strict FEM Case."""

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

from .config import Case, integer, keys


def parse_json(text):
    """Read JSON while rejecting duplicate keys at every depth."""

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(text, object_pairs_hook=pairs)


def load_document(text):
    """Read a project or legacy Case with strict duplicate-key rejection."""
    return Project.from_dict(parse_json(text))


def assemble_geometry(sections):
    """Concatenate local z=0 profiles with explicit repetition counts.

    A radial mismatch at a join becomes an actual vertical PEC segment.
    Case validation rejects joins that create unsupported topology. Circular
    arc radii and directions survive translation; no fitted geometry is used.
    """
    if not isinstance(sections, list) or not sections:
        raise ValueError("sections must be a nonempty array")
    points, arcs, tolerances = [], [], []
    offset = 0.0
    for section in sections:
        keys(section, ["geometry", "count"], ["geometry", "count"], "section")
        count = integer(section["count"], "section.count")
        local = Case.from_dict({"schema_version": 2, "geometry": section["geometry"]})
        if local.arcs:
            tolerances.append(local.arc_chord_tolerance_m)
        if len(points) + len(local.profile) * count > 100000:
            raise ValueError(
                "assembly exceeds 100000 editing vertices; reduce repetitions"
            )
        for _ in range(count):
            translated = [[offset + z, r] for z, r in local.profile]
            shared = bool(points and points[-1] == translated[0])
            base = len(points) - int(shared)
            points.extend(translated[int(shared) :])
            arcs.extend(
                {"end_index": base + i, "radius_m": r, "direction": d}
                for i, r, d in local.arcs
            )
            offset += local.length
    geometry = {
        "type": "arc_profile" if arcs else "stepped_profile",
        "points_zr_m": points,
    }
    if arcs:
        geometry.update(arcs=arcs, chord_tolerance_m=min(tolerances))
    return Case.from_dict({"schema_version": 2, "geometry": geometry}).to_dict()[
        "geometry"
    ]


@dataclass(frozen=True)
class Project:
    case: Case
    sections: list | None = None
    reflect_full: bool = False
    display_length_unit: str = "mm"

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("document must be an object")
        if "project_version" not in data:
            return cls(Case.from_dict(data))
        keys(
            data,
            [
                "project_version",
                "case",
                "sections",
                "reflect_full",
                "display_length_unit",
            ],
            ["project_version", "case"],
            "project",
        )
        if type(data["project_version"]) is not int or data["project_version"] != 1:
            raise ValueError("only project_version 1 is supported")
        case = Case.from_dict(data["case"])
        sections = data.get("sections")
        if "sections" in data:
            expanded = assemble_geometry(sections)
            # Compare canonical physics, including geometry type and arc metadata.
            if expanded != case.to_dict()["geometry"]:
                raise ValueError(
                    "case geometry differs from expanded sections; regenerate the case"
                )
        reflect = data.get("reflect_full", False)
        if type(reflect) is not bool:
            raise ValueError("reflect_full must be a boolean")
        if reflect and not ((case.z_min == "pec") != (case.z_max == "pec")):
            raise ValueError("reflection requires one symmetry end and one PEC end")
        if reflect:
            case.reflected_acceleration_parameters('z_min' if case.z_min != 'pec' else 'z_max')
        unit = data.get("display_length_unit", "mm")
        if unit not in ("m", "mm"):
            raise ValueError("display_length_unit must be m or mm")
        return cls(case, deepcopy(sections), reflect, unit)

    @classmethod
    def from_sections(cls, template, sections, **options):
        """Expand geometry once, then enforce the same serialized contract."""
        raw = deepcopy(template.to_dict() if isinstance(template, Case) else template)
        raw["schema_version"] = max(raw["schema_version"], 2)
        raw["geometry"] = assemble_geometry(sections)
        return cls.from_dict(
            {"project_version": 1, "case": raw, "sections": sections, **options}
        )

    @classmethod
    def load(cls, path):
        return load_document(Path(path).read_text(encoding="utf-8"))

    def to_dict(self):
        data = {
            "project_version": 1,
            "case": self.case.to_dict(),
            "reflect_full": self.reflect_full,
            "display_length_unit": self.display_length_unit,
        }
        if self.sections is not None:
            data["sections"] = deepcopy(self.sections)
        return data

    def dumps(self):
        return (
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, allow_nan=False)
            + "\n"
        )

    def save(self, path):
        # Exclusive creation matches the existing no-overwrite output contract.
        with Path(path).open("x", encoding="utf-8") as stream:
            stream.write(self.dumps())

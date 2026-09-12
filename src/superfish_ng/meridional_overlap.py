# SPDX-License-Identifier: Apache-2.0
"""Exact common triangles for independently meshed, identical meridional vacuum."""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from .config import integer
from .axis_connected_mesh import AxisConnectedMesh
from .meridional_mesh import MeridionalMesh
from .planar_tracking_exact_affine import _RationalTriangulation, _corners
from .planar_tracking_overlap import _barycentric, _clip, _cross
from .planar_tracking_remesh import _candidate_pairs, _rational_points


@dataclass(frozen=True)
class MeridionalOverlay:
    previous_cells: np.ndarray
    current_cells: np.ndarray
    previous_vertex_barycentric: np.ndarray
    current_vertex_barycentric: np.ndarray
    vertices_rz_m: np.ndarray
    determinants: np.ndarray


def _domain(mesh):
    outer=tuple(_corners(_rational_points(mesh.outer_rz_m)))
    holes=tuple(sorted(tuple(_corners(_rational_points(hole))) for hole in mesh.holes_rz_m))
    return outer,holes


def meridional_overlay(previous,current,*,max_candidate_tests=2000000,max_overlay_triangles=250000):
    """Return common original-cell quadrature pieces measured in dr dz.

    Both meshes must describe exactly the same outer contour and PEC holes.
    Binary64 coordinates denote exact rational inputs; boundary subdivisions,
    hole order, numbering and internal triangulation are independent. All
    original-cell areas are covered exactly before converting the partition
    to floating arrays. No field, material, mode or physical measure is added.
    """
    integer(max_candidate_tests,'max_candidate_tests');integer(max_overlay_triangles,'max_overlay_triangles')
    if any(not isinstance(mesh,(MeridionalMesh,AxisConnectedMesh)) for mesh in (previous,current)):
        raise ValueError('meridional overlay requires validated MeridionalMesh or AxisConnectedMesh objects')
    if max(len(previous.triangles),len(current.triangles))>max_overlay_triangles:
        raise ValueError('input meshes exceed max_overlay_triangles')
    meshes=[type(mesh).from_dict(mesh.to_dict()) for mesh in (previous,current)]
    if _domain(meshes[0])!=_domain(meshes[1]):
        raise ValueError('meridional meshes must describe the same exact vacuum outer contour and all PEC holes')
    points=[_rational_points(mesh.points_rz_m) for mesh in meshes]
    rational=[_RationalTriangulation(np.asarray(p,dtype=object),mesh.triangles) for p,mesh in zip(points,meshes)]
    triangles=[[[p[int(index)] for index in cell] for cell in mesh.triangles] for p,mesh in zip(points,meshes)]
    covered=[[Fraction(0) for _ in ts] for ts in triangles];parts=[[],[],[],[],[],[]]
    for i,j in _candidate_pairs(*rational,max_candidate_tests):
        a,b=triangles[0][i],triangles[1][j];polygon=_clip(a,b)
        for k in range(1,len(polygon)-1):
            child=[polygon[0],polygon[k],polygon[k+1]];determinant=_cross(*child)
            if determinant<0:raise ValueError('meridional intersection has invalid orientation')
            if determinant==0:continue
            if len(parts[0])>=max_overlay_triangles:raise ValueError('meridional intersections exceed max_overlay_triangles')
            covered[0][i]+=determinant;covered[1][j]+=determinant
            values=(i,j,_barycentric(child,a),_barycentric(child,b),child,determinant)
            for part,value in zip(parts,values):part.append(value)
    for actual,ts in zip(covered,triangles):
        if actual!=[_cross(*tri) for tri in ts]:raise ValueError('meridional intersections do not exactly cover every original element')
    try:arrays=[np.asarray(part,dtype=np.int64 if i<2 else float) for i,part in enumerate(parts)]
    except (OverflowError,ValueError) as exc:raise ValueError('meridional partition is unresolved in floating arithmetic') from exc
    if any(not np.isfinite(array).all() for array in arrays) or np.any(arrays[-1]<=0):
        raise ValueError('meridional partition is unresolved in floating arithmetic')
    for array in arrays:array.setflags(write=False)
    return MeridionalOverlay(*arrays)

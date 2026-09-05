# SPDX-License-Identifier: Apache-2.0
"""Straight P1 triangles in (r,z); profile corners are mesh vertices."""
from dataclasses import dataclass
import numpy as np
from .config import Case


@dataclass
class Mesh:
    points: np.ndarray
    triangles: np.ndarray
    boundary_edges: np.ndarray
    boundary_tags: np.ndarray  # axis / pec / electric_symmetry / magnetic_symmetry
    boundary_cells: np.ndarray
    axis_nodes: np.ndarray


def make_mesh(case: Case) -> Mesh:
    zs = []
    for (za, _), (zb, _) in zip(case.profile, case.profile[1:]):
        count = max(1, int(np.ceil(case.nz * (zb - za) / case.length - 1e-12)))
        zs.extend(np.linspace(za, zb, count + 1)[:-1])
    zs.append(case.length)
    radius = np.interp(zs, *np.array(case.profile).T)
    stride = case.nr + 1
    points = np.array([(s*r, z) for z, r in zip(zs, radius)
                       for s in np.linspace(0, 1, stride)], dtype=float)
    triangles = []
    for j in range(len(zs)-1):
        for i in range(case.nr):
            a = j*stride+i
            b = a+stride
            triangles.extend(((a, a+1, b+1), (a, b+1, b)))
    triangles = np.array(triangles, dtype=np.int64)
    incidence = {}
    for cell, t in enumerate(triangles):
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            edge = tuple(sorted((a, b)))
            incidence.setdefault(edge, []).append(cell)
    boundary = [(e, c[0]) for e, c in incidence.items() if len(c) == 1]
    edges = np.array([e for e, _ in boundary], dtype=np.int64)
    tags = np.full(len(edges), "pec", dtype="U20")
    tags[np.all(points[edges, 0] == 0, axis=1)] = "axis"
    tags[np.all(points[edges, 1] == 0, axis=1)] = case.z_min
    tags[np.all(points[edges, 1] == case.length, axis=1)] = case.z_max
    result = Mesh(points, triangles, edges, tags,
                  np.array([c for _, c in boundary]), np.arange(0, len(points), stride))
    element_geometry(result)  # reject degenerate geometry before assembly
    return result


def element_geometry(mesh):
    p = mesh.points[mesh.triangles]
    jac = np.stack((p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=2)
    det = np.linalg.det(jac)
    if np.any(det <= 0) or not np.all(np.isfinite(det)):
        raise ValueError("mesh has nonpositive or nonfinite triangle Jacobian")
    grad = np.einsum("ij,tjk->tik", np.array([[-1., -1.], [1., 0.], [0., 1.]]), np.linalg.inv(jac))
    return p, det, grad

# SPDX-License-Identifier: Apache-2.0
"""Canonical regular Hphi=r*u forms on explicit axis-connected meshes with PEC holes."""
from dataclasses import dataclass
import numpy as np
from .axis_connected_mesh import AxisConnectedMesh
from .config import integer
from .mesh import Mesh
from .fem import assemble
from .high_order import quadratic_space,assemble_p2


@dataclass
class AxisConnectedSpace:
    mesh: Mesh
    dof_points: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray
    axis_dofs: np.ndarray


def axis_connected_matrices(declared,element_order=1):
    """Return a regular scalar space and canonical K/M; retain every axis DOF.

    This is a geometry/form API. It does not perform an eigenmode solve,
    certify discretization accuracy, or turn axis segments into PEC walls.
    The unchanged polynomial quadrature integrates P1/P2 straight forms exactly.
    """
    integer(element_order,'axis-connected element_order',1)
    if element_order not in (1,2):raise ValueError('axis-connected elements must be P1 or P2')
    if not isinstance(declared,AxisConnectedMesh):raise ValueError('explicit AxisConnectedMesh required')
    declared=AxisConnectedMesh.from_dict(declared.to_dict())
    mesh=Mesh(declared.points_rz_m,declared.triangles,declared.boundary_edges,declared.boundary_tags,declared.boundary_cells,declared.axis_nodes)
    if element_order==1:
        space=AxisConnectedSpace(mesh,mesh.points,mesh.triangles,mesh.boundary_edges,mesh.axis_nodes);k,m=assemble(mesh)
    else:
        quadratic=quadratic_space(mesh);space=AxisConnectedSpace(mesh,quadratic.dof_points,quadratic.cell_dofs,quadratic.boundary_dofs,quadratic.axis_dofs);k,m=assemble_p2(quadratic)
    if any(not np.isfinite(a.data).all() or np.any(a.diagonal()<=0) for a in (k,m)):
        raise ValueError('axis-connected K/M is outside finite positive SI arithmetic')
    return space,k,m

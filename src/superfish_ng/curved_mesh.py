# SPDX-License-Identifier: Apache-2.0
"""Shared curved geometry candidates with local maps and simple boundary checks."""
from dataclasses import dataclass
import numpy as np
from .conics import LineSegment
from .high_order import quadratic_space
from .mesh_input import mesh_from_dict,mesh_to_dict
from .quadratic_geometry import QuadraticTriangle,quadratic_minimum,_VANDERMONDE


@dataclass(frozen=True)
class CurvedGeometryCandidate:
    points_rz_m: np.ndarray
    cell_nodes: np.ndarray
    boundary_nodes: np.ndarray
    boundary_curve_indices: np.ndarray
    boundary_parameters: np.ndarray
    local_maps: tuple
    node_displacements_m: np.ndarray
    boundary_check: object


def curve_geometry_candidate(case, mesh):
    """Lift chord boundary vertices/midpoints while retaining shared connectivity.

    Reject local folds and invalid quadratic boundary cycles. Global curved
    space/assembly integration is pending; solve/saved APIs do not accept this type.
    """
    if case.curved_contour is None:
        raise ValueError('curved geometry requires native curved_contour')
    source = mesh_from_dict(case,mesh_to_dict(mesh))
    approximation = case.curved_contour.linearize(case.curve_chord_tolerance_m,
                                                  max_segments=case.curve_chord_max_segments,segments_per_curve=case.curve_segments_per_curve)
    space = quadratic_space(source)
    points = space.dof_points.copy()
    contour = np.asarray(approximation.contour.vertices_zr_m)[:,::-1]
    ends = np.roll(contour,-1,axis=0)
    delta = ends-contour
    lengths = np.linalg.norm(delta,axis=1)
    scale = float(np.max(np.ptp(contour,axis=0)))
    tolerance = 512*np.finfo(float).eps*scale
    assigned = {}
    owners,parameters = [],[]
    for edge,nodes,tag in zip(source.boundary_edges,space.boundary_dofs,source.boundary_tags):
        positions = source.points[edge]
        fractions = np.einsum('eij,ij->ei',positions[:,None,:]-contour,delta)/lengths**2
        projections = contour+fractions[:,:,None]*delta
        match = np.all((np.linalg.norm(positions[:,None,:]-projections,axis=2)<=tolerance)
                       & (fractions>=-tolerance/lengths)
                       & (fractions<=1+tolerance/lengths),axis=0)
        indices = np.flatnonzero(match)
        if len(indices)!=1:
            raise ValueError('boundary edge has no unique original chord segment')
        segment = int(indices[0])
        if tag!=approximation.contour.edge_tags[segment]:
            raise ValueError('boundary edge tag disagrees with original curve')
        fractions = fractions[:,segment].copy()
        fractions[abs(fractions)<=tolerance/lengths[segment]] = 0.
        fractions[abs(fractions-1)<=tolerance/lengths[segment]] = 1.
        low,high = approximation.segment_parameter_intervals[segment]
        pair = low+(high-low)*fractions
        owner = approximation.segment_curve_indices[segment]
        curve = case.curved_contour.curves[owner]
        owners.append(owner); parameters.append(pair)
        for node,parameter in zip(nodes,(*pair,float(pair.mean()))):
            # Straight boundaries and original joins keep their exact common
            # source coordinate; primitive endpoint adjustments remain explicit.
            if isinstance(curve,LineSegment) or parameter in (0.,1.):
                proposal = space.dof_points[node]
            else:
                proposal = curve.evaluate(float(parameter))['points_zr_m'][::-1]
            if node in assigned and np.linalg.norm(assigned[node]-proposal)>tolerance:
                raise ValueError('inconsistent shared curved geometry node')
            assigned.setdefault(int(node),proposal.copy())
            points[node] = assigned[int(node)]
    maps = []
    for index,nodes in enumerate(space.cell_dofs):
        try:
            geometry = QuadraticTriangle(points[nodes])
            radius = points[nodes,0]
            # Nonnegative quadratic Bernstein controls certify radius >= 0,
            # including exact axis edges. Fall back to the polynomial minimum.
            controls = np.r_[radius[:3],2*radius[3:]-.5*radius[[0,1,2]]-.5*radius[[1,2,0]]]
            if np.any(controls<0):
                minimum,_ = quadratic_minimum(np.linalg.solve(_VANDERMONDE,radius))
                if minimum<=512*np.finfo(float).eps*scale:
                    raise ValueError('mapped radius negative or UNVERIFIED')
            maps.append(geometry)
        except ValueError as exc:
            raise ValueError(f'curved geometry cell {index}: {exc}; reduce chord tolerance or regenerate the interior mesh before retrying') from exc
    arrays = [points,space.cell_dofs.copy(),space.boundary_dofs.copy(),
              np.asarray(owners,dtype=int),np.asarray(parameters),
              np.linalg.norm(points-space.dof_points,axis=1)]
    for array in arrays:
        array.setflags(write=False)
    from .quadratic_boundary import check_quadratic_boundary
    from types import MappingProxyType
    boundary = check_quadratic_boundary(points,space.boundary_dofs)
    return CurvedGeometryCandidate(*arrays[:5],tuple(maps),arrays[5],MappingProxyType(boundary))

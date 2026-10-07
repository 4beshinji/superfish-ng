# SPDX-License-Identifier: Apache-2.0
"""Original Hphi samples through checked, adjacent uniform P2 restrictions.

No field coefficients are prolonged, renormalized or fitted here. Every child
geometry polynomial is checked before parent reference addresses are used.
Unrelated connectivity, local refinements and reflected/TE fields are rejected.
"""
from dataclasses import replace
import math
import numpy as np

from .curved_solution import CurvedSolution
from .curved_refinement import _REFERENCE, _CHILDREN
from .fem import triangle_quadrature


def uniform_curved_pair_samples(previous, current, *, sample_order):
    """Return the original two-sided quadrature fields and half-sum measure.

    This in-memory diagnostic checks geometry; saved wrappers additionally
    validate the native eigenpairs and their complete original source files.
    """
    if type(sample_order) is not int or not 2 <= sample_order <= 32:
        raise ValueError('uniform P2 sampling order must be an integer from 2 to 32')
    pair=(previous,current)
    if any(not isinstance(s,CurvedSolution) or s.reflection_source_case is not None for s in pair):
        raise ValueError('uniform P2 sampling UNVERIFIED: only direct native TM fields are supported')
    if any(s.case.curved_refinement_steps or s.case.geometry_order != 2 for s in pair):
        raise ValueError('uniform P2 sampling UNVERIFIED: local history or non-P2 geometry')
    levels=[s.case.curved_refinement_levels for s in pair]
    if abs(levels[0]-levels[1]) != 1:
        raise ValueError('uniform P2 sampling UNVERIFIED: adjacent uniform levels are required')
    if (replace(previous.case,curved_refinement_levels=0).to_dict() !=
            replace(current.case,curved_refinement_levels=0).to_dict() or
            previous.source_mesh_data != current.source_mesh_data):
        raise ValueError('uniform P2 sampling UNVERIFIED: complete base Case/source mesh differs')
    for solution in pair:
        if (solution.u.shape != (len(solution.space.geometry.points_rz_m),len(solution.frequencies_hz)) or
                not np.isfinite(solution.u).all()):
            raise ValueError('uniform P2 sampling requires finite original nodal coefficients for every mode')
    from .curved_same_domain_tracking import compare_quadratic_boundaries
    compare_quadratic_boundaries(previous,current)
    coarse=pair[int(levels[1]<levels[0])];fine=pair[int(levels[1]>levels[0])]
    coarse_geometry=coarse.space.geometry;fine_geometry=fine.space.geometry
    if len(fine_geometry.cell_nodes) != 4*len(coarse_geometry.cell_nodes):
        raise ValueError('uniform P2 sampling UNVERIFIED: four deterministic children per parent are required')
    vertices=_REFERENCE[_CHILDREN];origins=vertices[:,0]
    matrices=np.stack((vertices[:,1]-origins,vertices[:,2]-origins),axis=2)
    inverse=np.linalg.inv(matrices)
    scale=float(np.max(np.ptp(coarse_geometry.points_rz_m,axis=0)))
    tolerance=512*np.finfo(float).eps*scale
    maximum=0.
    for parent,mapping in enumerate(coarse_geometry.local_maps):
        for child in range(4):
            coordinates=_REFERENCE@matrices[child].T+origins[child]
            expected=mapping.evaluate(coordinates)['points_rz_m']
            nodes=fine_geometry.cell_nodes[4*parent+child]
            actual=fine_geometry.points_rz_m[nodes]
            error=float(np.max(np.linalg.norm(actual-expected,axis=1)))
            maximum=max(maximum,error)
            if not math.isfinite(error) or error>tolerance:
                raise ValueError('uniform P2 sampling UNVERIFIED: child geometry polynomial differs from parent restriction')
    rule=list(triangle_quadrature(order=sample_order))
    q=np.array([b[1:] for b,w in rule]);reference=np.array([w for b,w in rule])
    coordinates=[(q-origins[c])@inverse[c].T for c in range(4)]
    owners=np.full(len(q),-1,dtype=int)
    for child,points in enumerate(coordinates):
        found=(points>=0).all(axis=1)&(points.sum(axis=1)<=1)&(owners<0)
        owners[found]=child
    if np.any(owners<0):
        raise ValueError('uniform P2 sampling UNVERIFIED: reference child partition does not cover all quadrature nodes')
    values=[[],[]];weights=[];volumes=[];physical_points=[]
    for side,solution in enumerate(pair):
        other=pair[1-side];geometry=solution.space.geometry;measure=[]
        for cell,mapping in enumerate(geometry.local_maps):
            data=mapping.evaluate(q);r=data['points_rz_m'][:,0]
            own=r[:,None]*(data['basis_values']@solution.u[geometry.cell_nodes[cell]])
            local_measure=r*data['determinant_m2']*reference
            if not np.isfinite(local_measure).all() or np.any(local_measure<=0):
                raise ValueError('uniform P2 sampling requires positive finite physical volume weights')
            if solution is coarse:
                sampled=np.empty((len(q),len(other.frequencies_hz)))
                for child in range(4):
                    mask=owners==child
                    if not mask.any():continue
                    index=4*cell+child
                    target=fine_geometry.local_maps[index].evaluate(coordinates[child][mask])
                    sampled[mask]=target['points_rz_m'][:,0,None]*(target['basis_values']@other.u[fine_geometry.cell_nodes[index]])
            else:
                parent=cell//4;child=cell%4
                target=coarse_geometry.local_maps[parent].evaluate(q@matrices[child].T+origins[child])
                sampled=target['points_rz_m'][:,0,None]*(target['basis_values']@other.u[coarse_geometry.cell_nodes[parent]])
            values[side].append(own);values[1-side].append(sampled)
            measure.append(local_measure);physical_points.append(data['points_rz_m'])
        measure=np.concatenate(measure);weights.append(measure/2)
        volumes.append(float(2*math.pi*np.sum(measure)))
    # Both value lists have the same source-side/cell/node order, including when
    # the caller supplies child first. No quadrature point or mode is omitted.
    return dict(values=tuple(np.concatenate(v) for v in values),weights=np.concatenate(weights),
        volumes_m3=volumes,points_rz_m=np.concatenate(physical_points),
        certificate=dict(child_polynomials_checked=len(fine_geometry.cell_nodes),
            maximum_node_difference_m=maximum,existing_refinement_tolerance_m=tolerance,
            source_mesh_supplied=previous.source_mesh_data is not None,
            coarse_uniform_level=min(levels),fine_uniform_level=max(levels),
            scope='all six nodes of every quadratic child vs deterministic parent restriction at the existing 512-epsilon geometric tolerance; roundoff agreement, not a Maxwell error bound'),
        field='Hphi_A_per_m',sample_order=sample_order,new_eigensolves=0)

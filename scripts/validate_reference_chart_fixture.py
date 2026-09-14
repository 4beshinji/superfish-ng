# SPDX-License-Identifier: Apache-2.0
"""Nonaffine chart fixture and separately integrated polynomial reference field."""
from copy import deepcopy
import numpy as np


def reference_chart_fixture(cases, documents, scale):
    """Flip one interior diagonal and split one axis boundary edge explicitly."""
    meshes = [deepcopy(m['source_mesh']) for m in documents]
    mesh = meshes[1]; edge = (1, 8)
    owners = [i for i, t in enumerate(mesh['triangles']) if set(edge) <= set(t)]
    if len(owners) != 2:
        raise ValueError('declared fixture diagonal no longer has two parents')
    a, b = [next(k for k in mesh['triangles'][i] if k not in edge) for i in owners]
    def oriented(t):
        p = np.asarray([mesh['points'][k] for k in t])
        det = np.linalg.det(np.column_stack((p[1]-p[0], p[2]-p[0])))
        if det == 0: raise ValueError('degenerate fixture triangle')
        return list(t if det > 0 else (t[0], t[2], t[1]))
    for i, t in zip(owners, [(a, b, edge[0]), (b, a, edge[1])]):
        mesh['triangles'][i] = oriented(t)
    charts = [[[x/scale for x in p] for p in meshes[0]['points']] for _ in range(2)]
    boundary = next(i for i, tag in enumerate(mesh['boundary_tags']) if tag == 'axis')
    u, v = mesh['boundary_edges'][boundary]
    parent = next(i for i, t in enumerate(mesh['triangles']) if {u, v} <= set(t))
    opposite = next(k for k in mesh['triangles'][parent] if k not in (u, v))
    midpoint = len(mesh['points'])
    mesh['points'].append([(mesh['points'][u][k]+mesh['points'][v][k])/2 for k in (0, 1)])
    charts[1].append([(charts[1][u][k]+charts[1][v][k])/2 for k in (0, 1)])
    mesh['triangles'][parent] = oriented((u, midpoint, opposite))
    mesh['triangles'].append(oriented((midpoint, v, opposite)))
    mesh['boundary_edges'][boundary] = [u, midpoint]
    mesh['boundary_edges'].append([midpoint, v]); mesh['boundary_tags'].append('axis')
    return [dict(schema_version=5, source_mesh=mesh, reference_vertices=chart,
                 boundary_pairing='declared_reference_polylines', max_pair_tests=100000)
            for mesh, chart in zip(meshes, charts)]


def independent_chart_overlap(cases, documents):
    """Integrate Hphi=r with independent P2 basis and dblquad on proven cells.

    Common-cell coverage is independently checked by the geometry invariants.
    This integration does not call the product physical-map evaluator.
    """
    from fractions import Fraction as F
    from scipy.integrate import dblquad
    from superfish_ng.project import Project
    from superfish_ng.curved_reference_partition import build_curved_reference_partition
    from superfish_ng.curved_space import case_curved_space
    from superfish_ng.mesh_input import mesh_from_dict
    projects = [Project(c, mesh_data=d['source_mesh']) for c, d in zip(cases, documents)]
    overlay = build_curved_reference_partition(*projects, reference_vertices=[d['reference_vertices'] for d in documents],
                                               max_pair_tests=100000, max_triangles=10000)
    spaces = [case_curved_space(p.case, mesh_from_dict(p.case, p.mesh_data)) for p in projects]
    totals = np.zeros(3)
    for row in overlay.report['triangles']:
        nodes = [s.geometry.points_rz_m[s.geometry.cell_nodes[row[name+'_cell']]]
                 for name, s in zip(('previous', 'current'), spaces)]
        coordinates = [np.array([[float(F(*v)) for v in p[1:]] for p in row[name+'_barycentric']])
                       for name in ('previous', 'current')]
        transforms = [np.column_stack((p[1]-p[0], p[2]-p[0])) for p in coordinates]
        def evaluate(side, x, y):
            x, y = coordinates[side][0]+transforms[side] @ np.array([x, y]); l = 1-x-y
            basis = np.array([l*(2*l-1), x*(2*x-1), y*(2*y-1), 4*l*x, 4*x*y, 4*y*l])
            dx = np.array([1-4*l, 4*x-1, 0, 4*(l-x), 4*y, -4*y])
            dy = np.array([1-4*l, 0, 4*y-1, -4*x, 4*x, 4*(l-y)])
            det = np.linalg.det(np.column_stack((dx @ nodes[side], dy @ nodes[side]))) * np.linalg.det(transforms[side])
            return (basis @ nodes[side])[0], det
        def integrand(x, y, kind):
            (r0, d0), (r1, d1) = [evaluate(side, x, y) for side in (0, 1)]
            return ((r0*r1)**1.5*np.sqrt(d0*d1), r0**3*d0, r1**3*d1)[kind]
        for kind in range(3):
            totals[kind] += dblquad(lambda y, x: integrand(x, y, kind), 0, 1, lambda x: 0, lambda x: 1-x,
                                   epsabs=1e-15, epsrel=1e-10)[0]
    return float(totals[0]/np.sqrt(totals[1]*totals[2]))

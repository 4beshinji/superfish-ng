# SPDX-License-Identifier: Apache-2.0
"""Explicit topological correspondence of saved straight or curved FEM meshes."""
import numpy as np
from .curved_solution import CurvedSolution
from .fem import triangle_quadrature
from .high_order import basis_p2
from .mode_tracking import track_sampled_mode_subspaces


def _geometry(solution):
    if isinstance(solution,CurvedSolution):
        g=solution.space.geometry
        return g.points_rz_m,g.cell_nodes[:,:3],g.boundary_nodes[:,:2],solution.space.boundary_tags
    m=solution.mesh
    return m.points,m.triangles,m.boundary_edges,m.boundary_tags


def _cell_samples(solution,cell,bary):
    if isinstance(solution,CurvedSolution):
        g=solution.space.geometry;data=g.local_maps[cell].evaluate(bary[:,1:])
        r=data['points_rz_m'][:,0];det=data['determinant_m2']
        u=data['basis_values']@solution.u[g.cell_nodes[cell]]
    else:
        vertices=solution.mesh.points[solution.mesh.triangles[cell]];r=(bary@vertices)[:,0]
        det=np.full(len(bary),np.linalg.det(np.column_stack((vertices[1]-vertices[0],vertices[2]-vertices[0]))))
        if solution.element_order==2:
            u=np.array([basis_p2(b,np.zeros((3,2)))[0] for b in bary])@solution.u[solution.space.cell_dofs[cell]]
        else:u=bary@solution.u[solution.mesh.triangles[cell]]
    if not np.isfinite(r).all() or not np.isfinite(det).all() or np.any(r<=0) or np.any(det<=0):
        raise ValueError('paired mesh samples require positive finite radius and physical Jacobian')
    return r[:,None]*u,r,det


def track_paired_mesh_modes(previous,current,previous_ids,*,mapping,sample_order,vertex_pairs,**controls):
    """Use a declared vertex bijection, never an inferred node-number match.

    Barycentric cell coordinates induce the map; edge midpoint correspondence
    in P2 geometry follows the declared endpoint pair, not physical proximity.
    """
    if mapping!='paired_mesh':raise ValueError('explicit mapping must be paired_mesh')
    if type(sample_order) is not int or not 2<=sample_order<=32:
        raise ValueError('paired_mesh sample_order must be an integer from 2 to 32 per triangle')
    geometries=[_geometry(s) for s in (previous,current)]
    for _,_,_,tags in geometries:
        if any(tag not in ('axis','pec') for tag in tags):raise ValueError('paired_mesh supports closed PEC and axis boundaries only')
    old,new=geometries;old_vertices=set(map(int,old[1].ravel()));new_vertices=set(map(int,new[1].ravel()))
    if (type(vertex_pairs) is not list or any(type(p) is not list or len(p)!=2 or any(type(i) is not int for i in p) for p in vertex_pairs)
            or len(vertex_pairs)!=len(old_vertices) or len(vertex_pairs)!=len(new_vertices)
            or {p[0] for p in vertex_pairs}!=old_vertices or {p[1] for p in vertex_pairs}!=new_vertices):
        raise ValueError('vertex_pairs must explicitly biject every old/new geometric vertex using zero-based integer indices')
    bijection=dict(vertex_pairs)
    old_edges={tuple(sorted(bijection[int(i)] for i in edge)):str(tag) for edge,tag in zip(old[2],old[3])}
    new_edges={tuple(sorted(map(int,edge))):str(tag) for edge,tag in zip(new[2],new[3])}
    if old_edges!=new_edges:raise ValueError('vertex correspondence must preserve axis/PEC boundary edges and tags')
    lookup={tuple(sorted(map(int,t))):i for i,t in enumerate(new[1])}
    pairings=[]
    for triangle in old[1]:
        mapped=[bijection[int(i)] for i in triangle];j=lookup.get(tuple(sorted(mapped)))
        if j is None:raise ValueError('vertex correspondence does not preserve triangle connectivity')
        pairings.append((j,[list(new[1][j]).index(i) for i in mapped]))
    if len(pairings)!=len(new[1]) or len({j for j,_ in pairings})!=len(new[1]):
        raise ValueError('paired_mesh requires a bijection of all triangles')
    count=len(pairings)*sample_order**2
    if count>262144:raise ValueError('paired_mesh exceeds 262144 samples; reduce sample_order or use a coarser comparison mesh')
    rule=list(triangle_quadrature(order=sample_order));bary=np.array([b for b,_ in rule]);weights=np.tile([w for _,w in rule],len(pairings))
    values=[[],[]];radii=[[],[]];determinants=[[],[]]
    for i,(j,permutation) in enumerate(pairings):
        current_bary=np.empty_like(bary);current_bary[:,permutation]=bary
        for k,(solution,cell,coordinates) in enumerate(((previous,i,bary),(current,j,current_bary))):
            h,r,det=_cell_samples(solution,cell,coordinates);values[k].append(h);radii[k].append(r);determinants[k].append(det)
    samples=[]
    for h,r,d in zip(values,radii,determinants):
        h=np.concatenate(h);r=np.concatenate(r);d=np.concatenate(d)
        factor=np.sqrt(r/np.max(r))*np.sqrt(d/np.max(d))
        if np.any(factor<=0):raise ValueError('paired mesh volume factor underflows; restrict mesh scale contrast')
        samples.append(h*factor[:,None])
    report=track_sampled_mode_subspaces(*samples,weights,previous.frequencies_hz,current.frequencies_hz,previous_ids,
        comparison_description='explicit vertex bijection and matched triangle barycentric coordinates; Hphi times normalized sqrt(r*detJ); common reference triangle measure',**controls)
    report['physical_mapping']=dict(name=mapping,sample_order=sample_order,sample_count=count,
        vertex_pairs=sorted(vertex_pairs),current_cells_for_previous=[int(j) for j,_ in pairings],
        current_local_positions_for_previous=[p for _,p in pairings],reference_barycentric=bary.tolist(),
        reference_triangle_weights=[float(w) for _,w in rule],field='Hphi_A_per_m',field_multiplier='sqrt(r/max(r))*sqrt(detJ/max(detJ)) independently per mesh',
        scope='declared topologically equivalent straight or quadratic meshes; native saved geometry and field; not inferred physical correspondence or continuous-path identity')
    return report

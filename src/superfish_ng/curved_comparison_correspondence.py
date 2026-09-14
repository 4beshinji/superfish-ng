# SPDX-License-Identifier: Apache-2.0
"""Infer a unique numbering map from curve fractions and triangle adjacency.

The inputs must already be validated native spaces. This identifies the same
oriented triangulation across two declared curve parameterizations; it does
not invent a one-to-one correspondence between different triangulations.
"""
from collections import deque
import numpy as np


def _edge_table(geometry):
    result={}
    for cell,nodes in enumerate(geometry.cell_nodes):
        for i,j,mid in ((0,1,3),(1,2,4),(2,0,5)):
            edge=tuple(sorted((int(nodes[i]),int(nodes[j]))))
            result.setdefault(edge,[]).append((cell,int(nodes[mid])))
    return result


def _boundary_partitions(case,space,tolerance):
    partitions=[[] for _ in case.curved_contour.curves];g=space.geometry
    for nodes,owner,parameters,tag in zip(g.boundary_nodes,g.boundary_curve_indices,g.boundary_parameters,space.boundary_tags):
        a,b,mid=map(int,nodes);lo,hi=map(float,parameters)
        if hi<lo:lo,hi=hi,lo;a,b=b,a
        if hi-lo<=tolerance:raise ValueError('automatic curved correspondence has unresolved boundary parameter intervals')
        partitions[int(owner)].append((lo,hi,a,b,mid,str(tag)))
    for entries in partitions:
        entries.sort()
        if (not entries or abs(entries[0][0])>tolerance or abs(entries[-1][1]-1)>tolerance
                or any(abs(a[1]-b[0])>tolerance for a,b in zip(entries,entries[1:]))):
            raise ValueError('automatic curved correspondence requires complete nonoverlapping curve partitions')
    return partitions


def infer_curved_comparison_correspondence(cases,spaces,*,boundary_pairing):
    """Return current node/cell IDs for every previous P2 node/cell.

    Curve index, increasing fraction order and tag anchor the whole boundary.
    The explicit same_curve_fractions policy additionally requires equal fractions;
    ordered_curve_vertices declares ordinal pairing even if fractions move. Once
    an oriented boundary edge is fixed, its incident triangle's third vertex
    is forced; connected dual adjacency propagates that choice everywhere.
    Conflicts, reversed cells or a missing bijection fail before field sampling.
    No nearest-coordinate search, eigenvector or frequency enters the map.
    """
    if boundary_pairing not in ('same_curve_fractions','ordered_curve_vertices'):
        raise ValueError('boundary_pairing must be same_curve_fractions or ordered_curve_vertices')
    first,second=[s.geometry for s in spaces]
    if (len(first.points_rz_m)!=len(second.points_rz_m) or len(first.cell_nodes)!=len(second.cell_nodes)):
        raise ValueError('automatic curved correspondence requires isomorphic final comparison triangulations; node/cell counts differ')
    curves=[c.curved_contour.curves for c in cases]
    if len(curves[0])!=len(curves[1]) or any(type(a) is not type(b) for a,b in zip(*curves)):
        raise ValueError('automatic curved correspondence requires the same ordered native curve kinds')
    tolerance=512*np.finfo(float).eps
    partitions=[_boundary_partitions(c,s,tolerance) for c,s in zip(cases,spaces)]
    tables=[_edge_table(g) for g in (first,second)]
    node_map=np.full(len(first.points_rz_m),-1,dtype=int);node_inverse=node_map.copy()
    cell_map=np.full(len(first.cell_nodes),-1,dtype=int);cell_inverse=cell_map.copy()
    canonical={}
    def bind(old,new):
        if node_map[old] not in (-1,new) or node_inverse[new] not in (-1,old):
            raise ValueError('automatic curved correspondence has conflicting boundary or interior node topology')
        node_map[old]=new;node_inverse[new]=old
        if old not in canonical:canonical[old]=len(canonical)
    pending=deque();maximum=0.;boundary_count=0
    for old,new in zip(*partitions):
        if len(old)!=len(new):raise ValueError('automatic curved correspondence requires matching final curve partitions')
        for a,b in zip(old,new):
            difference=max(abs(a[0]-b[0]),abs(a[1]-b[1]));maximum=max(maximum,difference)
            if (boundary_pairing=='same_curve_fractions' and difference>tolerance) or a[5]!=b[5]:
                raise ValueError('automatic curved correspondence requires matching curve fractions and boundary tags')
            for i in (2,3,4):bind(a[i],b[i])
            pair=[table[tuple(sorted(entry[2:4]))] for table,entry in zip(tables,(a,b))]
            if any(len(edge)!=1 for edge in pair):raise ValueError('automatic curved correspondence boundary must have one incident cell')
            pending.append((pair[0][0][0],pair[1][0][0]));boundary_count+=1
    while pending:
        old,new=pending.popleft()
        if cell_map[old]>=0:
            if cell_map[old]!=new:raise ValueError('automatic curved correspondence has conflicting cell topology')
            continue
        if cell_inverse[new]>=0:raise ValueError('automatic curved correspondence is not a cell bijection')
        a=first.cell_nodes[old];b=second.cell_nodes[new];known=[int(node_map[i]) for i in a[:3] if node_map[i]>=0]
        if len(known)<2 or not set(known).issubset(set(map(int,b[:3]))):
            raise ValueError('automatic curved correspondence has incompatible adjacent triangles')
        missing_old=[int(i) for i in a[:3] if node_map[i]<0];missing_new=[int(i) for i in b[:3] if i not in known]
        if len(missing_old)!=len(missing_new):raise ValueError('automatic curved correspondence has incompatible vertex incidence')
        for i,j in zip(missing_old,missing_new):bind(i,j)
        oriented=list(map(int,node_map[a[:3]]));corners=list(map(int,b[:3]))
        if not any(oriented==corners[i:]+corners[:i] for i in range(3)):
            raise ValueError('automatic curved correspondence would reverse triangle orientation')
        cell_map[old]=new;cell_inverse[new]=old
        # Canonical boundary-rooted visitation is independent of cell/vertex IDs
        # and cyclic local node rotations. It also fixes quadrature coordinates.
        start=min(range(3),key=lambda i:canonical[int(a[i])])
        for k in range(3):
            i=(start+k)%3;j=(i+1)%3;mid=3+i
            old_edge=tables[0][tuple(sorted((int(a[i]),int(a[j]))))]
            new_edge=tables[1][tuple(sorted((int(node_map[a[i]]),int(node_map[a[j]]))))]
            if len(old_edge)!=len(new_edge):raise ValueError('automatic curved correspondence has incompatible edge incidence')
            bind(int(a[mid]),new_edge[0][1])
            left=[cell for cell,_ in old_edge if cell!=old];right=[cell for cell,_ in new_edge if cell!=new]
            pending.extend(zip(left,right))
    if any(np.any(ids<0) for ids in (node_map,node_inverse,cell_map,cell_inverse)):
        raise ValueError('automatic curved correspondence does not cover all P2 nodes and cells')
    reference=[]
    for nodes in first.cell_nodes:
        start=min(range(3),key=lambda i:canonical[int(nodes[i])])
        ordered=[int(nodes[(start+i)%3]) for i in range(3)]+[int(nodes[3+(start+i)%3]) for i in range(3)]
        reference.append(ordered)
    reference.sort(key=lambda nodes:tuple(canonical[n] for n in nodes[:3]))
    return dict(method='ordered_curve_fractions_and_oriented_triangle_adjacency',
        boundary_pairing=boundary_pairing,previous_reference_cell_nodes=reference,
        current_node_for_previous=node_map.tolist(),current_cell_for_previous=cell_map.tolist(),
        boundary_edge_count=boundary_count,maximum_parameter_difference=maximum,
        parameter_roundoff_tolerance=tolerance,
        scope='unique combinatorial numbering map anchored by declared curve indices and fractions; not inferred physical mode identity or a map between nonisomorphic triangulations')

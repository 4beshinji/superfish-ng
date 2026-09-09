# SPDX-License-Identifier: Apache-2.0
"""Quadratic Bezier boundary checks using subdivision and convex-hull bounds."""
from dataclasses import dataclass
import numpy as np
from .box_candidates import _overlapping_box_candidates


@dataclass(frozen=True)
class QuadraticEdge:
    control_points: object

    def __post_init__(self):
        raw = np.asarray(self.control_points)
        if raw.dtype.kind not in 'iuf' or raw.shape!=(3,2) or not np.isfinite(raw).all():
            raise ValueError('quadratic edge requires three finite control points')
        points = raw.astype(float).copy()
        points.setflags(write=False)
        object.__setattr__(self,'control_points',points)

    @classmethod
    def from_nodes(cls,start,end,midpoint):
        start,end,midpoint = map(np.asarray,(start,end,midpoint))
        return cls(np.array((start,2*midpoint-(start+end)/2,end)))

    def split(self,t=.5):
        if type(t) not in (int,float) or not np.isfinite(t) or not 0<=t<=1:
            raise ValueError("split fraction must be finite and in [0,1]")
        p = self.control_points
        a,b = (1-t)*p[0]+t*p[1],(1-t)*p[1]+t*p[2]
        middle = (1-t)*a+t*b
        return QuadraticEdge((p[0],a,middle)),QuadraticEdge((middle,b,p[2]))

    def bounds(self,padding):
        return self.control_points.min(axis=0)-padding,self.control_points.max(axis=0)+padding

    def derivatives(self):
        return 2*np.diff(self.control_points,axis=0)

    def regular(self,padding):
        derivatives = self.derivatives()
        norms = np.linalg.norm(derivatives,axis=1)
        if np.any(norms<=padding):
            raise ValueError('quadratic boundary FAIL/UNVERIFIED: zero endpoint tangent')
        direction = (derivatives/norms[:,None]).sum(axis=0)
        if np.min(derivatives@direction)<=padding:
            raise ValueError('quadratic boundary FAIL/UNVERIFIED: cusp or unresolved reversal')


def separated_edges(first,second,*,padding,max_boxes=10000):
    """Certify disjoint convex boxes; never accept an exhausted search."""
    if type(max_boxes) is not int or max_boxes<1:
        raise ValueError('max_boxes must be a positive integer')
    if not np.isfinite(padding) or padding<=0:
        raise ValueError('padding must be finite and positive')
    pending = [(first,second)]
    checked = 0
    while pending:
        if checked>=max_boxes:
            raise ValueError('quadratic boundary UNVERIFIED: subdivision budget exhausted')
        a,b = pending.pop(); checked += 1
        alo,ahi = a.bounds(padding); blo,bhi = b.bounds(padding)
        if np.any(ahi<blo) or np.any(bhi<alo):
            continue
        samples_a = np.array((a.control_points[0],a.split()[0].control_points[-1],a.control_points[-1]))
        samples_b = np.array((b.control_points[0],b.split()[0].control_points[-1],b.control_points[-1]))
        if np.min(np.linalg.norm(samples_a[:,None]-samples_b,axis=2))<=padding:
            raise ValueError('quadratic boundary FAIL/UNVERIFIED: contact or gap below roundoff resolution')
        if max(np.max(ahi-alo),np.max(bhi-blo))<=4*padding:
            raise ValueError('quadratic boundary UNVERIFIED: unresolved intersection')
        if np.max(ahi-alo)>=np.max(bhi-blo):
            left,right = a.split()
            pending.extend(((left,b),(right,b)))
        else:
            left,right = b.split()
            pending.extend(((a,left),(a,right)))
    return checked


def adjacent_edges(first,second,*,padding,max_boxes=10000):
    if not np.array_equal(first.control_points[-1],second.control_points[0]):
        raise ValueError('quadratic boundary adjacent nodes must be identical')
    u,v = first.derivatives()[-1],second.derivatives()[0]
    norms = np.linalg.norm((u,v),axis=1)
    if np.any(norms<=padding):
        raise ValueError('quadratic boundary UNVERIFIED: zero join tangent')
    direction = u/norms[0]+v/norms[1]
    for depth in range(33):
        width = 2.**(-depth)
        before,tail = first.split(1-width)
        head,after = second.split(width)
        if min(np.min(tail.derivatives()@direction),np.min(head.derivatives()@direction))>padding:
            break
    else:
        raise ValueError('quadratic boundary UNVERIFIED: no monotone shared-endpoint neighborhood')
    if depth==0:
        return 0
    checked = separated_edges(before,second,padding=padding,max_boxes=max_boxes)
    if checked>=max_boxes:
        raise ValueError("quadratic boundary UNVERIFIED: adjacency subdivision budget exhausted")
    checked += separated_edges(tail,after,padding=padding,max_boxes=max_boxes-checked)
    return checked


def check_quadratic_boundary(points,boundary_nodes,*,max_boxes=10000):
    """Check one unordered closed edge cycle, preserving all supplied geometry.

    Node rows are (start,end,midpoint). The output certifies the boundary only;
    a global curved mesh still needs topology, conformity and local-map checks.
    """
    raw,nodes = np.asarray(points),np.asarray(boundary_nodes)
    if raw.dtype.kind not in 'iuf' or raw.ndim!=2 or raw.shape[1]!=2 or not np.isfinite(raw).all():
        raise ValueError('boundary geometry requires finite N by 2 points')
    if nodes.dtype.kind not in 'iu' or nodes.ndim!=2 or nodes.shape[1]!=3 or len(nodes)<3:
        raise ValueError('boundary nodes require at least three integer start/end/midpoint rows')
    if np.any(nodes<0) or np.any(nodes>=len(raw)):
        raise ValueError('boundary node index is out of range')
    if type(max_boxes) is not int or max_boxes<1:
        raise ValueError('max_boxes must be a positive integer')
    scale = float(np.max(np.ptp(raw[nodes.ravel()],axis=0)))
    if not np.isfinite(scale) or scale<=0:
        raise ValueError('boundary geometry scale is invalid')
    # Normalize before subdivision; no snapping or tolerance enlargement.
    p = (raw-raw[nodes[0,0]])/scale
    padding = 512*np.finfo(float).eps
    incidence = {}
    for i,(a,b,m) in enumerate(nodes):
        if len({int(a),int(b),int(m)})!=3:
            raise ValueError('boundary edge has repeated nodes')
        for node in (a,b):
            incidence.setdefault(int(node),[]).append(i)
    if any(len(edges)!=2 for edges in incidence.values()):
        raise ValueError('quadratic boundary must be a degree-two cycle')
    if len(set(map(int,nodes[:,2])))!=len(nodes) or set(nodes[:,2]) & set(incidence):
        raise ValueError('boundary midpoints must be distinct from each other and endpoints')
    ordered = []
    used = set()
    node = int(nodes[0,0]); start = node
    while True:
        choices = [i for i in incidence[node] if i not in used]
        if not choices:
            break
        i = choices[0]; used.add(i)
        a,b,m = nodes[i]
        end = int(b if a==node else a)
        edge = QuadraticEdge.from_nodes(p[node],p[end],p[m])
        edge.regular(padding)
        ordered.append(edge)
        node = end
    if node!=start or len(used)!=len(nodes):
        raise ValueError('quadratic boundary must be one closed cycle')
    bounds=np.asarray([edge.bounds(padding) for edge in ordered])
    # Each nonadjacent pair has one initial box test. Spatially discharged
    # pairs contribute that same logical count without entering subdivision.
    checked = len(ordered)*(len(ordered)-3)//2
    for i,candidates in _overlapping_box_candidates(bounds):
        a=ordered[i]
        # Shared endpoints are inclusive candidates; retain adjacency checks
        # explicitly as well, in the original first-failure order.
        adjacent={i+1} if i+1<len(ordered) else set()
        if i==0:adjacent.add(len(ordered)-1)
        for j in sorted(set(candidates)|adjacent):
            b = ordered[j]
            if j==i+1:
                checked += adjacent_edges(a,b,padding=padding,max_boxes=max_boxes)
            elif i==0 and j==len(ordered)-1:
                checked += adjacent_edges(b,a,padding=padding,max_boxes=max_boxes)
            else:
                checked += separated_edges(a,b,padding=padding,max_boxes=max_boxes)-1
    return dict(status='PASS',edges=len(ordered),boxes_checked=checked,
                roundoff_padding_m=padding*scale,scope='quadratic boundary cycle only')

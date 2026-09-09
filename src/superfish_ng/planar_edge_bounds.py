# SPDX-License-Identifier: Apache-2.0
"""Conservative edge AABB pairs for large explicit planar triangulations.

All closed-box overlaps, including zero-width boxes and endpoint contact,
are yielded once. The caller still applies exact segment predicates.
"""
import numpy as np

class EdgeBoundsNode:
    def __init__(self,indices,low,high):
        self.low=low[indices].min(axis=0);self.high=high[indices].max(axis=0)
        self.count=len(indices);self.indices=None;self.children=None
        if len(indices)<=8:self.indices=indices
        else:
            centers=low[indices]/2+high[indices]/2
            axis=int(np.argmax(np.ptp(centers,axis=0)))
            order=indices[np.argsort(centers[:,axis],kind='stable')];middle=len(order)//2
            self.children=(EdgeBoundsNode(order[:middle],low,high),EdgeBoundsNode(order[middle:],low,high))


def edge_pairs(low,high):
    if not len(low):return
    root=EdgeBoundsNode(np.arange(len(low)),low,high)
    stack=[(root,root)]
    while stack:
        a,b=stack.pop()
        if np.any(a.high<b.low) or np.any(b.high<a.low):continue
        if a is b and a.children:
            left,right=a.children;stack.extend(((left,left),(left,right),(right,right)));continue
        if a.indices is not None and b.indices is not None:
            for i in a.indices:
                for j in b.indices:
                    if a is b and i>=j:continue
                    if np.all(high[i]>=low[j]) and np.all(high[j]>=low[i]):yield (min(i,j),max(i,j))
        elif b.children is None or (a.children is not None and a.count>=b.count):
            stack.extend((child,b) for child in a.children)
        else:stack.extend((a,child) for child in b.children)

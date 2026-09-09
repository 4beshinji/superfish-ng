# SPDX-License-Identifier: Apache-2.0
"""Conservative spatial candidates for padded two-dimensional boxes."""
import numpy as np


def _overlapping_box_candidates(bounds):
    """Yield lexicographic candidates for finite padded (N, 2, 2) boxes.

    Tree bounds only discard strictly separated boxes. Inclusive contact and
    original edge order are retained for the subsequent geometric checks.
    """
    if not len(bounds):
        return
    # Median splits bound tree depth even for coincident box centers.
    centers=.5*bounds[:,0]+.5*bounds[:,1]
    def build(ids):
        low=bounds[ids,0].min(axis=0);high=bounds[ids,1].max(axis=0)
        if len(ids)<=16:return (low,high,int(ids.max()),ids,None,None)
        axis=int(np.argmax(np.ptp(centers[ids],axis=0)))
        ids=ids[np.argsort(centers[ids,axis],kind='stable')];mid=len(ids)//2
        return (low,high,int(ids.max()),None,build(ids[:mid]),build(ids[mid:]))
    root=build(np.arange(len(bounds)))
    for i,box in enumerate(bounds):
        stack=[root];found=[]
        while stack:
            low,high,maximum,ids,left,right=stack.pop()
            if maximum<=i or box[1,0]<low[0] or high[0]<box[0,0] or box[1,1]<low[1] or high[1]<box[0,1]:continue
            if ids is not None:
                ids=ids[ids>i]
                mask=np.all(box[1]>=bounds[ids,0],axis=1)&np.all(bounds[ids,1]>=box[0],axis=1)
                found.extend(ids[mask].tolist())
            else:stack.extend((right,left))
        # Preserve the old first-failure order and full diagnostic counts.
        yield i,sorted(found)

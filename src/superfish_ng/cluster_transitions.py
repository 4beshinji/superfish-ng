# SPDX-License-Identifier: Apache-2.0
"""Propose dimension-preserving one-to-many cluster unions from subspace links."""
import numpy as np


def transition_partition(old,new,identities,left,right,minimum_link,*,allow_repartition=False):
    links=np.zeros((len(old),len(new)));neighbors=[set() for _ in range(len(old)+len(new))]
    for i,u in enumerate(left):
        for j,v in enumerate(right):
            if u is None or v is None:continue
            # Fraction of the smaller space represented in the other space.
            value=float(np.sqrt(np.clip(np.sum((u.T@v)**2)/min(u.shape[1],v.shape[1]),0.,1.)))
            links[i,j]=value
            if value>=minimum_link:neighbors[i].add(len(old)+j);neighbors[len(old)+j].add(i)
    pending=set(range(len(neighbors)));components=[]
    while pending:
        root=min(pending);component={root};queue=[root];pending.remove(root)
        while queue:
            for other in sorted(neighbors[queue.pop()] & pending):
                pending.remove(other);component.add(other);queue.append(other)
        components.append((sorted(i for i in component if i<len(old)),sorted(i-len(old) for i in component if i>=len(old))))
    old_result=[];new_result=[];events=[]
    for a,b in components:
        previous=sorted(k for i in a for k in old[i]);current=sorted(k for j in b for k in new[j])
        one_to_many=(len(a)==1 and len(b)>1) or (len(a)>1 and len(b)==1)
        repartition=(allow_repartition and len(a)>1 and len(b)>1
            and any(len(old[i])>1 for i in a) and any(len(new[j])>1 for j in b))
        if (one_to_many or repartition) and len(previous)==len(current):
            ids=sorted(x for i in a for x in identities[i])
            old_result.append((previous,ids));new_result.append(current)
            events.append(dict(kind='REPARTITION' if repartition else ('MERGE' if len(a)>1 else 'SPLIT'),previous_indices=[k+1 for k in previous],
                current_indices=[k+1 for k in current],previous_ids=ids,
                previous_cluster_count=len(a),current_cluster_count=len(b),dimension=len(ids)))
        else:
            old_result.extend((old[i],identities[i]) for i in a);new_result.extend(new[j] for j in b)
    old_result.sort(key=lambda x:x[0][0]);new_result.sort(key=lambda x:x[0])
    return [x[0] for x in old_result],new_result,[x[1] for x in old_result],dict(
        initial_previous_clusters=[[k+1 for k in c] for c in old],initial_current_clusters=[[k+1 for k in c] for c in new],
        link_matrix=links.tolist(),minimum_cluster_link=minimum_link,events=events,
        scope=('links propose connected equal-dimension unions with multidimensional clusters on both sides, or one-to-many transitions; full worst-principal-overlap and assignment tests still required; individual IDs are not recovered' if allow_repartition else 'links propose only one-to-many or many-to-one equal-dimension unions; full worst-principal-overlap and assignment tests still required; individual IDs are not recovered after a split'))

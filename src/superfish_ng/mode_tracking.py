# SPDX-License-Identifier: Apache-2.0
"""Two-snapshot tracking of weighted sampled real mode subspaces.

Sampling locations, pullback and the physical meaning of weights must be shared
and declared by the caller. Frequency rank is never a persistent mode identity.
"""
import numpy as np
from scipy.optimize import linear_sum_assignment


def _real_array(value,name,ndim):
    raw=np.asarray(value)
    if raw.dtype.kind not in 'iuf' or raw.ndim!=ndim:
        raise ValueError(f'{name} requires a real numeric array of dimension {ndim}')
    array=np.asarray(raw,dtype=float)
    if not np.isfinite(array).all():raise ValueError(f'{name} must be finite')
    return array


def _control(value,name,*,zero=False,one=True):
    if type(value) not in (int,float) or not np.isfinite(value) or not (0<=value if zero else 0<value) or not (value<=1 if one else value<1):
        raise ValueError(f'{name} must be a finite number in its declared unit interval')
    return float(value)


def _clusters(frequencies,gap):
    groups=[]
    for i,value in enumerate(frequencies):
        if i==0 or value-frequencies[i-1]>gap*max(value,frequencies[i-1]):groups.append([i])
        else:groups[-1].append(i)
    return groups


def _basis(fields,weights,indices,rank_threshold):
    block=fields[:,indices]
    scale=np.max(np.abs(block),axis=0)
    if np.any(scale==0):return None
    # Two column rescalings protect normalization against arbitrary mode units
    # and very small weighted norms, without changing any column span.
    block=(block/scale)*(np.sqrt(weights)/np.sqrt(np.max(weights)))[:,None]
    scale=np.max(np.abs(block),axis=0)
    if np.any(scale==0):return None
    block=block/scale
    block=block/np.linalg.norm(block,axis=0)
    u,s,_=np.linalg.svd(block,full_matrices=False)
    if len(s)<len(indices) or s[-1]/s[0]<rank_threshold:return None
    return u[:,:len(indices)]


def _identity_groups(groups,count):
    from .config import keys
    if type(groups) is not list or not groups:raise ValueError('previous_identity_groups requires a nonempty partition')
    normalized=[];indices=[];identities=[]
    for group in groups:
        keys(group,('indices','ids'),('indices','ids'),'identity group')
        ranks=group['indices'];ids=group['ids']
        if (type(ranks) is not list or not ranks or any(type(i) is not int for i in ranks)
                or ranks!=sorted(set(ranks))
                or type(ids) is not list or len(ids)!=len(ranks)
                or any(type(x) is not str or not x.strip() for x in ids)):
            raise ValueError('identity group requires increasing distinct frequency indices and one nonempty ID per dimension')
        indices.extend(ranks);identities.extend(ids)
        normalized.append(dict(indices=list(ranks),ids=sorted(ids)))
    if sorted(indices)!=list(range(1,count+1)) or len(set(identities))!=len(identities):
        raise ValueError('identity groups must partition all frequency ranks with globally distinct IDs')
    return sorted(normalized,key=lambda x:x['indices'][0])


def track_sampled_mode_subspaces(previous_fields,current_fields,weights,previous_frequencies_hz,current_frequencies_hz,
                                 previous_ids,*,comparison_description,minimum_overlap,minimum_assignment_margin,
                                 relative_cluster_gap,minimum_relative_singular_value=1e-8,previous_identity_groups=None,
                                 cluster_transition_policy=None,minimum_cluster_link=None):
    """Match equal-dimensional frequency clusters by their worst principal overlap.

    PASS means all previous and current clusters have unambiguous matches.
    A multidimensional match identifies only a subspace, never its basis modes.
    Births/losses remain unresolved. Explicit retain_subspace policy can
    continue dimension-preserving one-to-many cluster transitions as ID sets.
    """
    a=_real_array(previous_fields,'previous_fields',2);b=_real_array(current_fields,'current_fields',2)
    w=_real_array(weights,'weights',1)
    f=_real_array(previous_frequencies_hz,'previous_frequencies_hz',1)
    g=_real_array(current_frequencies_hz,'current_frequencies_hz',1)
    if (not len(w) or not a.shape[1] or not b.shape[1] or a.shape[0]!=len(w) or b.shape[0]!=len(w)
            or a.shape[1]!=len(f) or b.shape[1]!=len(g) or np.any(w<=0)
            or np.any(f<=0) or np.any(g<=0) or np.any(np.diff(f)<0) or np.any(np.diff(g)<0)):
        raise ValueError('tracking requires common samples, positive weights and positive frequency-ranked columns')
    groups=None
    if previous_identity_groups is not None:
        if previous_ids is not None:raise ValueError('supply individual IDs or identity groups, never both')
        groups=_identity_groups(previous_identity_groups,len(f))
    elif (not isinstance(previous_ids,(list,tuple)) or len(previous_ids)!=len(f)
            or any(type(x) is not str or not x.strip() for x in previous_ids) or len(set(previous_ids))!=len(previous_ids)):
        raise ValueError('previous_ids must contain one distinct nonempty string per previous frequency rank')
    if type(comparison_description) is not str or not comparison_description.strip():
        raise ValueError('declare the shared sample mapping, field and weight measure in comparison_description')
    overlap=_control(minimum_overlap,'minimum_overlap')
    margin=_control(minimum_assignment_margin,'minimum_assignment_margin',zero=True)
    gap=_control(relative_cluster_gap,'relative_cluster_gap',zero=True,one=False)
    rank_threshold=_control(minimum_relative_singular_value,'minimum_relative_singular_value')
    if cluster_transition_policy is None:
        if minimum_cluster_link is not None:raise ValueError('minimum_cluster_link requires an explicit cluster_transition_policy')
    elif cluster_transition_policy not in ('retain_subspace','retain_connected_subspace'):raise ValueError('cluster_transition_policy must be retain_subspace or retain_connected_subspace')
    else:minimum_cluster_link=_control(minimum_cluster_link,'minimum_cluster_link')
    effective_margin=max(margin,32*np.finfo(float).eps*max(len(w),len(f),len(g)))
    old=_clusters(f,gap) if groups is None else [[k-1 for k in c['indices']] for c in groups];new=_clusters(g,gap)
    left=[_basis(a,w,c,rank_threshold) for c in old];right=[_basis(b,w,c,rank_threshold) for c in new]
    identities=[sorted(previous_ids[k] for k in c) for c in old] if groups is None else [c['ids'] for c in groups]
    transitions=None
    if cluster_transition_policy is not None:
        from .cluster_transitions import transition_partition
        old,new,identities,transitions=transition_partition(old,new,identities,left,right,minimum_cluster_link,
            allow_repartition=cluster_transition_policy=='retain_connected_subspace')
        left=[_basis(a,w,c,rank_threshold) for c in old];right=[_basis(b,w,c,rank_threshold) for c in new]
    scores=np.full((len(old),len(new)),np.nan)
    singular={}
    for i,u in enumerate(left):
        for j,v in enumerate(right):
            if u is None or v is None or u.shape[1]!=v.shape[1]:continue
            values=np.clip(np.linalg.svd(u.T@v,compute_uv=False),0.,1.)
            scores[i,j]=values[-1];singular[i,j]=values.tolist()
    cost=np.where(np.isfinite(scores),-scores,1e6)
    rows,columns=linear_sum_assignment(cost)
    matches=[];unresolved=[];matched_old=set();matched_new=set();current_ids=[None]*len(g)
    for i,j in zip(rows,columns):
        value=scores[i,j]
        if not np.isfinite(value):continue
        row_other=[scores[i,k] for k in range(len(new)) if k!=j and np.isfinite(scores[i,k])]
        col_other=[scores[k,j] for k in range(len(old)) if k!=i and np.isfinite(scores[k,j])]
        row_margin=float(value-max(row_other,default=0.));column_margin=float(value-max(col_other,default=0.))
        # Exact ties are ambiguous even if the caller requests zero margin.
        if value<overlap or row_margin<=0 or column_margin<=0 or row_margin<effective_margin or column_margin<effective_margin:
            unresolved.append(dict(previous_indices=[k+1 for k in old[i]],current_indices=[k+1 for k in new[j]],
                                   reason='overlap or assignment separation is insufficient',overlap=float(value),
                                   row_margin=row_margin,column_margin=column_margin));continue
        ids=identities[i];dimension=len(ids)
        match=dict(previous_ids=ids,previous_indices=[k+1 for k in old[i]],current_indices=[k+1 for k in new[j]],
                   dimension=dimension,kind='MODE' if dimension==1 else 'SUBSPACE',principal_overlaps=singular[i,j],
                   minimum_principal_overlap=float(value),row_margin=row_margin,column_margin=column_margin,
                   current_frequencies_hz=[float(g[k]) for k in new[j]])
        matches.append(match);matched_old.add(int(i));matched_new.add(int(j))
        if dimension==1:current_ids[new[j][0]]=ids[0]
    unmatched_old=[dict(indices=[k+1 for k in c],reason='rank-deficient samples' if left[i] is None else 'no accepted equal-dimensional match') for i,c in enumerate(old) if i not in matched_old]
    unmatched_new=[dict(indices=[k+1 for k in c],reason='rank-deficient samples' if right[j] is None else 'no accepted equal-dimensional match') for j,c in enumerate(new) if j not in matched_new]
    passed=not unmatched_old and not unmatched_new
    result=dict(status='PASS' if passed else 'UNVERIFIED',comparison_description=comparison_description,
                previous_frequencies_hz=f.tolist(),current_frequencies_hz=g.tolist(),previous_mode_ids=list(previous_ids) if groups is None else None,
                matches=matches,current_mode_ids=current_ids,individual_ids_complete=passed and all(x is not None for x in current_ids),
                unmatched_previous=unmatched_old,unmatched_current=unmatched_new,unresolved=unresolved,
                previous_clusters=[[k+1 for k in c] for c in old],current_clusters=[[k+1 for k in c] for c in new],
                overlap_matrix=[[float(x) if np.isfinite(x) else None for x in row] for row in scores],
                controls=dict(minimum_overlap=overlap,minimum_assignment_margin=margin,effective_assignment_margin=effective_margin,relative_cluster_gap=gap,
                              minimum_relative_singular_value=rank_threshold),
                scope='numerical weighted sample/subspace correspondence; mode_index remains frequency rank; no proof of continuous-path identity, mapping accuracy or FEM convergence')

    if groups is not None:result['previous_identity_groups']=groups
    if transitions is not None:
        for event in transitions['events']:
            event['status']='PASS' if any(m['previous_indices']==event['previous_indices'] and m['current_indices']==event['current_indices'] for m in matches) else 'UNVERIFIED'
        result['cluster_transitions']=transitions
        result['controls'].update(cluster_transition_policy=cluster_transition_policy,minimum_cluster_link=minimum_cluster_link)
    return result


def tracked_frequency_hz(report,mode_id):
    """Return a frequency only after a complete, individually resolved match."""
    if report['status']!='PASS':raise ValueError('mode tracking is UNVERIFIED; no frequency may be passed to tuning')
    for match in report['matches']:
        if mode_id in match['previous_ids']:
            if match['dimension']!=1:raise ValueError('only a subspace is identified; an individual frequency is ambiguous')
            return match['current_frequencies_hz'][0]
    raise ValueError('mode_id is not present in the tracking result')


def track_cylindrical_modes(previous,current,previous_ids,*,mapping,sample_order,**controls):
    """Pull physical Hphi back by r=R*rho, z=L*zeta for two closed PEC cylinders.

    The constant volume Jacobian cancels from each normalized inner product.
    Variable-radius or folded contours need a separately specified mapping.
    """
    from .sampling import FieldSampler
    if mapping!='normalized_cylinder':raise ValueError('explicit mapping must be normalized_cylinder')
    if type(sample_order) is not int or not 2<=sample_order<=256:
        raise ValueError('sample_order must be an integer from 2 to 256 per reference coordinate')
    dimensions=[]
    for solution in (previous,current):
        case=solution.case
        if (case.geometry_type!='profile' or not case.profile or case.z_min!='pec' or case.z_max!='pec'
                or any(radius!=case.profile[0][1] for _,radius in case.profile)):
            raise ValueError('normalized_cylinder mapping requires constant-radius profile geometry and closed PEC ends')
        dimensions.append((case.profile[0][1],case.length))
    nodes,weights=np.polynomial.legendre.leggauss(sample_order)
    nodes=(nodes+1)/2;weights=weights/2
    rho,zeta=np.meshgrid(nodes,nodes,indexing='ij')
    reference=np.column_stack((rho.ravel(),zeta.ravel()))
    measure=(weights[:,None]*weights[None,:]*rho).ravel()
    samples=[]
    for solution,(radius,length) in zip((previous,current),dimensions):
        points=reference*np.array([radius,length]);sampler=FieldSampler.from_solution(solution)
        samples.append(np.column_stack([sampler.evaluate(points,i,outside='raise')['Hphi_A_per_m']
                                        for i in range(len(solution.frequencies_hz))]))
    result=track_sampled_mode_subspaces(*samples,measure,previous.frequencies_hz,current.frequencies_hz,previous_ids,
                comparison_description='Hphi_A_per_m pulled back by r=R*rho, z=L*zeta; reference measure rho d_rho d_zeta',**controls)
    result['physical_mapping']=dict(name=mapping,sample_order=sample_order,field='Hphi_A_per_m',
        reference_points_rho_zeta=reference.tolist(),reference_weights=measure.tolist(),
        previous_radius_length_m=list(dimensions[0]),current_radius_length_m=list(dimensions[1]),
        scope='closed PEC cylinders only; normalized pointwise Hphi pullback; quadrature accuracy must be checked separately')
    return result

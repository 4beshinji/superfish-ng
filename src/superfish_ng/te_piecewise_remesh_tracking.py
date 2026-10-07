# SPDX-License-Identifier: Apache-2.0
"""Native Ephi correspondence on owned straight comparison domains."""
from types import SimpleNamespace
import numpy as np
from .te import is_te,validate_te_case
from .mesh_input import mesh_from_dict,mesh_digest
from .fem import triangle_quadrature
from .sampling import FieldSampler
from .same_domain_tracking import _same_boundary
from .mode_tracking import track_sampled_mode_subspaces


def _sector(solutions):
    if not all(hasattr(s,'case') and is_te(s.case) for s in solutions):
        raise ValueError('mixed TE/TM straight correspondence is unsupported')
    reflected=[getattr(s,'reflection_source_case',None) is not None for s in solutions]
    if reflected[0]!=reflected[1]:
        raise ValueError('TE straight comparison cannot mix direct and reflected fields')
    cases=[getattr(s,'reflection_source_case',None) or s.case for s in solutions]
    for case in cases:
        validate_te_case(case)
        if case.geometry_order!=1 or case.geometry_type not in ('profile','stepped_profile','contour'):
            raise ValueError('TE straight comparison requires native straight profile, stepped_profile or contour geometry')
    ends=[(c.z_min,c.z_max) for c in cases]
    count=sum(tag!='pec' for tag in ends[0])
    if (ends[0]!=ends[1] or any(tag not in ('pec','electric_symmetry','magnetic_symmetry') for tag in ends[0])
            or count>1 or (reflected[0] and count!=1)):
        raise ValueError('TE straight comparison requires matching source symmetry sectors and at most one symmetry end; reflected fields require one source plane')
    sector=None if count==0 else dict(source_end_conditions=dict(zip(('z_min','z_max'),ends[0])),
        reflected=reflected[0],mode_indices='source symmetry-sector frequency order; not full-spectrum ranks')
    return cases,reflected[0],sector


def _reflected_mesh(case,mesh):
    """Mirror the declared source half, retaining positive cell orientation."""
    plane=0. if case.z_min!='pec' else case.length
    shift=case.length if plane==0. else 0.
    on_plane=mesh.points[:,1]==plane
    original=mesh.points.copy();original[:,1]+=shift
    mirror=mesh.points.copy();mirror[:,1]=2*plane-mirror[:,1]+shift
    mapping=np.arange(len(original));mapping[~on_plane]=np.arange(len(original),len(original)+np.count_nonzero(~on_plane))
    tag=case.z_min if plane==0. else case.z_max;keep=mesh.boundary_tags!=tag
    return dict(schema_version=1,length_unit='m',coordinate_order='rz',index_base=0,
        points=np.vstack((original,mirror[~on_plane])).tolist(),
        triangles=np.vstack((mesh.triangles,mapping[mesh.triangles][:,[0,2,1]])).tolist(),
        boundary_edges=np.vstack((mesh.boundary_edges[keep],mapping[mesh.boundary_edges[keep]])).tolist(),
        boundary_tags=np.tile(mesh.boundary_tags[keep],2).tolist())


def track_te_piecewise_remesh_modes(previous,current,previous_ids,*,mapping,sample_order,comparison_meshes,**controls):
    """Compare real native Ephi with the full variable r detJ volume measure."""
    if mapping!='piecewise_remesh':raise ValueError('TE straight mapping must be piecewise_remesh')
    if type(sample_order) is not int or not 2<=sample_order<=32:
        raise ValueError('TE straight sample_order must be an integer from 2 to 32')
    solutions=(previous,current);cases,reflected,sector=_sector(solutions)
    from .piecewise_remesh_tracking import validate_comparison_meshes
    validate_comparison_meshes(comparison_meshes,allow_symmetry=True)
    if any(m['schema_version']!=1 for m in comparison_meshes):
        raise ValueError('TE straight comparison meshes require schema_version 1')
    copies=2 if reflected else 1;count=copies*len(comparison_meshes[0]['triangles'])*sample_order**2
    if count>262144:raise ValueError('TE straight piecewise_remesh exceeds 262144 samples; reduce sample_order or comparison mesh size')
    meshes=[];tolerances=[];evaluation_hashes=[]
    for solution,case,data in zip(solutions,cases,comparison_meshes):
        mesh=mesh_from_dict(case,data)
        evaluation=_reflected_mesh(case,mesh) if reflected else data
        if reflected:mesh=mesh_from_dict(solution.case,evaluation)
        tolerances.append(_same_boundary(SimpleNamespace(mesh=mesh),solution))
        meshes.append(mesh);evaluation_hashes.append(mesh_digest(evaluation))
    if any(not np.array_equal(getattr(meshes[0],name),getattr(meshes[1],name))
            for name in ('triangles','boundary_edges','boundary_tags')):
        raise ValueError('TE reflected comparison must retain the same source numbering and mirrored boundary roles')
    rule=list(triangle_quadrature(order=sample_order));bary=np.array([b for b,_ in rule])
    weights=np.tile([w for _,w in rule],len(meshes[0].triangles))
    samples=[];volumes=[];det_ranges=[]
    for solution,mesh in zip(solutions,meshes):
        v=mesh.points[mesh.triangles];points=np.einsum('qi,tij->tqj',bary,v).reshape(-1,2)
        determinants=np.linalg.det(np.stack((v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=-1))
        det=np.repeat(determinants,len(bary));r=points[:,0]
        with np.errstate(over='ignore',invalid='ignore',divide='ignore',under='ignore'):
            factor=np.sqrt(r/np.max(r))*np.sqrt(det/np.max(det));volume=float(2*np.pi*np.sum(r*det*weights))
        if not np.isfinite(factor).all() or np.any(factor<=0) or not np.isfinite(volume) or volume<=0:
            raise ValueError('TE straight physical volume factors must be positive and finite')
        sampler=FieldSampler.from_solution(solution)
        values=np.column_stack([sampler.evaluate(points,i,outside='raise')['Ephi_V_per_m'] for i in range(len(solution.frequencies_hz))])
        samples.append(values*factor[:,None]);volumes.append(volume)
        det_ranges.append([float(min(determinants)),float(max(determinants))])
    report=track_sampled_mode_subspaces(*samples,weights,previous.frequencies_hz,current.frequencies_hz,previous_ids,
        comparison_description='declared paired straight comparison cells; independent native Ephi times normalized sqrt(r*detJ); common reference triangle measure',**controls)
    report['physical_mapping']=dict(name=mapping,comparison_geometry_order=1,sample_order=sample_order,sample_count=count,
        comparison_triangle_count=len(meshes[0].triangles),solver_triangle_counts=[len(s.mesh.triangles) for s in solutions],
        comparison_mesh_sha256=[mesh_digest(m) for m in comparison_meshes],evaluation_comparison_mesh_sha256=evaluation_hashes,
        axisymmetric_volumes_m3=volumes,determinant_ranges_m2=det_ranges,boundary_roundoff_tolerances_m=tolerances,
        field='Ephi_V_per_m',physics='axisymmetric_m0_te',
        field_multiplier='sqrt(r/max(r))*sqrt(detJ/max(detJ)) independently per comparison mesh',
        scope='explicit straight piecewise affine coordinate correspondence with original native TE fields and matching source sectors; variable volume retained; quadrature convergence required; not a continuous branch identity or physical error bound')
    if sector is not None:report['physical_mapping']['symmetry_sector']=sector
    if reflected:report['physical_mapping']['reflection_mapping']=dict(declaration_domain='source half-domain',
        evaluation_domain='both lobes of native reflected fields',source_comparison_triangle_count=len(comparison_meshes[0]['triangles']),
        construction='source mesh and mirror with positive cell orientation; original half shifted for z_min symmetry')
    return report

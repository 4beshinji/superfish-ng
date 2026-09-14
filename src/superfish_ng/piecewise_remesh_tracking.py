# SPDX-License-Identifier: Apache-2.0
"""Explicit paired comparison meshes independent of the solved FEM meshes."""
from types import SimpleNamespace
import numpy as np
from .config import keys
from .curved_solution import CurvedSolution
from .fem import triangle_quadrature
from .mesh_input import mesh_from_dict,mesh_digest
from .mode_tracking import track_sampled_mode_subspaces
from .same_domain_tracking import _same_boundary
from .sampling import FieldSampler


def validate_comparison_meshes(value, *, allow_symmetry=False):
    if type(value) is not list or len(value)!=2:raise ValueError('comparison_meshes requires [previous_mesh,current_mesh]')
    if any(isinstance(mesh,dict) and mesh.get('schema_version') in (2,3,4,5) for mesh in value):
        from .curved_piecewise_remesh_tracking import validate_curved_comparison_meshes
        validate_curved_comparison_meshes(value)
        return
    allowed=('axis','pec','electric_symmetry','magnetic_symmetry') if allow_symmetry else ('axis','pec')
    names=('schema_version','length_unit','coordinate_order','index_base','points','triangles','boundary_edges','boundary_tags')
    for mesh in value:
        keys(mesh,names,names,'comparison mesh')
        if (type(mesh['schema_version']) is not int or mesh['schema_version']!=1 or mesh['length_unit']!='m'
                or mesh['coordinate_order']!='rz' or type(mesh['index_base']) is not int or mesh['index_base']!=0):
            raise ValueError('comparison meshes require schema_version=1, metres, rz coordinates and zero-based indices')
        for field,width in (('points',2),('triangles',3),('boundary_edges',2)):
            rows=mesh[field]
            if type(rows) is not list or not rows or any(type(row) is not list or len(row)!=width for row in rows):
                raise ValueError(f'comparison mesh {field} requires nonempty rows of length {width}')
            for row in rows:
                for number in row:
                    if field=='points':
                        if type(number) not in (int,float) or not np.isfinite(number):raise ValueError('comparison points must be finite numbers')
                    elif type(number) is not int or not 0<=number<len(mesh['points']):raise ValueError('comparison indices must refer to declared points')
        if (type(mesh['boundary_tags']) is not list or len(mesh['boundary_tags'])!=len(mesh['boundary_edges'])
                or any(tag not in allowed for tag in mesh['boundary_tags'])):
            raise ValueError('comparison meshes require closed PEC and axis tags for every boundary edge')
    if (len(value[0]['points'])!=len(value[1]['points']) or any(value[0][key]!=value[1][key] for key in ('triangles','boundary_edges','boundary_tags'))):
        raise ValueError('comparison meshes must explicitly share vertex numbering, oriented triangle connectivity and boundary tags')


def track_piecewise_remesh_modes(previous,current,previous_ids,*,mapping,sample_order,comparison_meshes,**controls):
    """Use matched comparison-cell barycentric coordinates, with variable volume.

    Each comparison mesh must independently cover its native physical domain.
    The comparison mesh defines the map, not the native field interpolation.
    """
    if mapping!='piecewise_remesh':raise ValueError('explicit mapping must be piecewise_remesh')
    if type(sample_order) is not int or not 2<=sample_order<=32:raise ValueError('piecewise_remesh sample_order must be an integer from 2 to 32')
    validate_comparison_meshes(comparison_meshes)
    if comparison_meshes[0]['schema_version'] in (2,3,4,5):
        from .curved_piecewise_remesh_tracking import track_curved_piecewise_remesh_modes
        return track_curved_piecewise_remesh_modes(previous,current,previous_ids,mapping=mapping,
            sample_order=sample_order,comparison_meshes=comparison_meshes,**controls)
    count=len(comparison_meshes[0]['triangles'])*sample_order**2
    if count>262144:raise ValueError('piecewise_remesh exceeds 262144 samples; reduce sample_order or comparison mesh size')
    solutions=(previous,current);meshes=[];tolerances=[]
    for solution,data in zip(solutions,comparison_meshes):
        if isinstance(solution,CurvedSolution):raise ValueError('piecewise_remesh currently requires straight geometric triangles')
        if not hasattr(solution,'case'):raise ValueError('piecewise_remesh requires native saved solutions with Case metadata')
        mesh=mesh_from_dict(solution.case,data)
        tolerances.append(_same_boundary(SimpleNamespace(mesh=mesh),solution));meshes.append(mesh)
    rule=list(triangle_quadrature(order=sample_order));bary=np.array([b for b,_ in rule]);quadrature=np.array([w for _,w in rule])
    samples=[];volumes=[];det_ranges=[]
    for solution,mesh in zip(solutions,meshes):
        v=mesh.points[mesh.triangles];points=np.einsum('qi,tij->tqj',bary,v).reshape(-1,2)
        determinants=np.linalg.det(np.stack((v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=-1))
        det=np.repeat(determinants,len(bary));r=points[:,0]
        factor=np.sqrt(r/np.max(r))*np.sqrt(det/np.max(det))
        if not np.isfinite(factor).all() or np.any(factor<=0):raise ValueError('comparison mesh physical volume factor must be positive and finite')
        sampler=FieldSampler.from_solution(solution)
        values=np.column_stack([sampler.evaluate(points,i,outside='raise')['Hphi_A_per_m'] for i in range(len(solution.frequencies_hz))])
        samples.append(values*factor[:,None])
        volumes.append(float(2*np.pi*np.sum(r*det*np.tile(quadrature,len(v)))))
        det_ranges.append([float(min(determinants)),float(max(determinants))])
    report=track_sampled_mode_subspaces(*samples,np.tile(quadrature,len(meshes[0].triangles)),previous.frequencies_hz,current.frequencies_hz,previous_ids,
        comparison_description='explicit paired comparison-cell barycentric coordinates; native Hphi sampled independently; normalized sqrt(r*detJ) per side retains variable physical volume',**controls)
    report['physical_mapping']=dict(name=mapping,sample_order=sample_order,sample_count=count,
        comparison_triangle_count=len(meshes[0].triangles),solver_triangle_counts=[len(s.mesh.triangles) for s in solutions],
        comparison_mesh_sha256=[mesh_digest(m) for m in comparison_meshes],axisymmetric_volumes_m3=volumes,
        determinant_ranges_m2=det_ranges,boundary_roundoff_tolerances_m=tolerances,field='Hphi_A_per_m',
        field_multiplier='sqrt(r/max(r))*sqrt(detJ/max(detJ)) independently per comparison mesh',
        scope='declared piecewise affine homeomorphism between polygonal domains using validated comparison meshes; independent native P1/P2 fields; sample-order convergence required; not inferred, curved, or continuous-branch correspondence or physical convergence acceptance')
    return report

# SPDX-License-Identifier: Apache-2.0
"""Declared nonlinear quadratic comparison maps for independent native fields."""
from dataclasses import replace
import numpy as np
from .config import keys,integer
from .curved_refinement_steps import steps_from_dict
from .curved_solution import CurvedSolution
from .curved_space import case_curved_space
from .curved_same_domain_tracking import compare_quadratic_space_boundaries
from .fem import triangle_quadrature
from .mesh_input import mesh_from_dict, mesh_digest
from .mode_tracking import track_sampled_mode_subspaces
from .sampling import FieldSampler

MAX_SAMPLES = 262144


def validate_curved_comparison_meshes(value):
    """Versions 2/3/4/5 declare a source chord mesh and its own refinement history.

    Each side uses its corresponding native Case's curve declarations. No Case
    override or solver coefficients enter this document. Version 3 explicitly
    selects boundary pairing before topology-based numbering inference. Version
    4 pairs initial triangulations and intersects independent final histories.
    Version 5 declares common vertex charts for independent initial connectivity.
    """
    if type(value) is not list or len(value)!=2:
        raise ValueError('curved comparison meshes require [previous,current]')
    for mesh in value:
        names=('schema_version','source_mesh','curved_refinement_levels','curved_refinement_steps')
        version=mesh.get('schema_version') if isinstance(mesh,dict) else None
        required=('schema_version','source_mesh')
        if version in (3,4,5):names+=('boundary_pairing',);required+=('boundary_pairing',)
        if version in (4,5):names+=('max_pair_tests',);required+=('max_pair_tests',)
        if version==5:names+=('reference_vertices',);required+=('reference_vertices',)
        keys(mesh,names,required,'curved comparison mesh')
        if type(version) is not int or version not in (2,3,4,5):
            raise ValueError('both curved comparison meshes require schema_version=2, 3, 4 or 5; mixed geometry is unsupported')
        if version in (3,4) and mesh['boundary_pairing'] not in ('same_curve_fractions','ordered_curve_vertices'):
            raise ValueError('boundary_pairing must be same_curve_fractions or ordered_curve_vertices')
        if version in (4,5):integer(mesh['max_pair_tests'],'max_pair_tests')
        if version==5 and mesh['boundary_pairing']!='declared_reference_polylines':
            raise ValueError('version 5 boundary_pairing must be declared_reference_polylines')
        if 'curved_refinement_levels' in mesh and 'curved_refinement_steps' in mesh:
            raise ValueError('curved comparison mesh must use levels or steps, not both')
        levels=mesh.get('curved_refinement_levels',0)
        if type(levels) is not int or levels<0:
            raise ValueError('curved comparison levels must be a nonnegative integer')
        if 'curved_refinement_steps' in mesh:steps_from_dict(mesh['curved_refinement_steps'])
        if not isinstance(mesh['source_mesh'],dict) or mesh['source_mesh'].get('schema_version')!=1:
            raise ValueError('curved comparison source_mesh requires a schema_version=1 chord mesh')
    from .piecewise_remesh_tracking import validate_comparison_meshes
    if value[0]['schema_version']!=value[1]['schema_version']:
        raise ValueError('curved comparison mesh versions must agree')
    if value[0]['schema_version']==2:
        validate_comparison_meshes([mesh['source_mesh'] for mesh in value],allow_symmetry=True)
    else:
        if value[0]['boundary_pairing']!=value[1]['boundary_pairing']:
            raise ValueError('both curved comparison meshes must declare the same boundary_pairing')
        for mesh in value:
            validate_comparison_meshes([mesh['source_mesh'],mesh['source_mesh']],allow_symmetry=True)
            if mesh['schema_version']==5:
                points=mesh['reference_vertices']
                if (type(points) is not list or len(points)!=len(mesh['source_mesh']['points'])
                        or any(type(p) is not list or len(p)!=2 for p in points)
                        or any(type(x) not in (int,float) or not np.isfinite(x) for p in points for x in p)):
                    raise ValueError('reference_vertices require one finite dimensionless pair per initial source vertex')
        if value[0]['schema_version'] in (4,5) and value[0]['max_pair_tests']!=value[1]['max_pair_tests']:
            raise ValueError('both curved comparison meshes must declare the same max_pair_tests')


def track_curved_piecewise_remesh_modes(previous,current,previous_ids,*,mapping,sample_order,comparison_meshes,**controls):
    """Pull Hphi and physical volume to matched reference quadratic cells.

    Reconstructed comparison spaces cover the respective native domains, have
    positive Jacobians and nonintersecting conforming edges, and share full P2
    connectivity or a common reference partition. FEM evaluation uses each
    original independent solved space.
    """
    if mapping!='piecewise_remesh':raise ValueError('explicit mapping must be piecewise_remesh')
    if type(sample_order) is not int or not 2<=sample_order<=32:
        raise ValueError('curved piecewise_remesh sample_order must be an integer from 2 to 32')
    validate_curved_comparison_meshes(comparison_meshes)
    solutions=(previous,current)
    from .te import TESolution,is_te
    if any(not isinstance(s,(CurvedSolution,TESolution)) or s.case.geometry_order!=2 or s.reflection_source_case is not None for s in solutions):
        raise ValueError('curved piecewise_remesh requires two direct native curved solutions; reflected construction is unsupported')
    te=[is_te(s.case) for s in solutions]
    if any(te) and not all(te):
        raise ValueError('mixed TE/TM curved correspondence is unsupported')
    sector=None;allowed=('axis','pec')
    if all(te):
        from .curved_same_domain_tracking import _te_symmetry_sector
        sector=_te_symmetry_sector(solutions)
        allowed+=('electric_symmetry','magnetic_symmetry')
    field='Ephi_V_per_m' if all(te) else 'Hphi_A_per_m'
    spaces=[];boundaries=[];projects=[]
    for solution,document in zip(solutions,comparison_meshes):
        if any(tag not in allowed for tag in solution.space.boundary_tags):
            raise ValueError('curved comparison requires closed PEC and axis boundaries')
        levels=document.get('curved_refinement_levels',0)
        steps=steps_from_dict(document['curved_refinement_steps']) if 'curved_refinement_steps' in document else ()
        limit=MAX_SAMPLES//sample_order**2
        if len(document['source_mesh']['triangles'])>limit:
            raise ValueError('curved comparison source mesh already exceeds the 262144 samples budget')
        budget=solution.case.contour_mesh
        case=replace(solution.case,curved_refinement_levels=levels,curved_refinement_steps=steps,
            contour_mesh=replace(budget,max_triangles=min(limit,budget.max_triangles)) if budget is not None else None)
        mesh=mesh_from_dict(case,document['source_mesh'])
        space=case_curved_space(case,mesh)
        boundaries.append(compare_quadratic_space_boundaries(case,space,solution.case,solution.space))
        spaces.append(space)
        if document['schema_version'] in (4,5):
            from .project import Project
            projects.append(Project(case,mesh_data=document['source_mesh']))
    first,second=spaces
    automatic=comparison_meshes[0]['schema_version']==3;correspondence=None;overlay=None
    if comparison_meshes[0]['schema_version']==5:
        from .curved_reference_partition import build_curved_reference_partition
        overlay=build_curved_reference_partition(*projects,reference_vertices=[m['reference_vertices'] for m in comparison_meshes],
            max_pair_tests=comparison_meshes[0]['max_pair_tests'],max_triangles=MAX_SAMPLES//sample_order**2)
    elif comparison_meshes[0]['schema_version']==4:
        from .curved_comparison_overlay import build_curved_comparison_overlay
        overlay=build_curved_comparison_overlay(*projects,boundary_pairing=comparison_meshes[0]['boundary_pairing'],
            max_pair_tests=comparison_meshes[0]['max_pair_tests'],max_triangles=MAX_SAMPLES//sample_order**2)
    elif automatic:
        from .curved_comparison_correspondence import infer_curved_comparison_correspondence
        correspondence=infer_curved_comparison_correspondence([s.case for s in solutions],spaces,
            boundary_pairing=comparison_meshes[0]['boundary_pairing'])
    elif any(not np.array_equal(getattr(first.geometry,key),getattr(second.geometry,key)) for key in ('cell_nodes','boundary_nodes')) or not np.array_equal(first.boundary_tags,second.boundary_tags):
        raise ValueError('curved comparison spaces must share full oriented P2 connectivity and boundary tags; check both declared histories')
    cells=len(overlay.report['triangles']) if overlay is not None else len(first.geometry.cell_nodes);count=cells*sample_order**2
    if count>MAX_SAMPLES:raise ValueError('curved piecewise_remesh exceeds 262144 samples; reduce sample_order or comparison mesh size')
    rule=list(triangle_quadrature(order=sample_order));q=np.array([b[1:] for b,_ in rule])
    weights=np.tile([w for _,w in rule],cells)
    samples=[];volumes=[];det_ranges=[]
    for side,(solution,space) in enumerate(zip(solutions,spaces)):
        if overlay is not None:data=overlay.evaluate(side,q)
        elif automatic:
            from .quadratic_geometry import QuadraticTriangle
            nodes=np.asarray(correspondence['previous_reference_cell_nodes'])
            if side:nodes=np.asarray(correspondence['current_node_for_previous'])[nodes]
            data=[QuadraticTriangle(space.geometry.points_rz_m[cell]).evaluate(q) for cell in nodes]
        else:data=[mapping_cell.evaluate(q) for mapping_cell in space.geometry.local_maps]
        points=np.concatenate([item['points_rz_m'] for item in data])
        det=np.concatenate([item['determinant_m2'] for item in data]);r=points[:,0]
        with np.errstate(over='ignore',invalid='ignore',divide='ignore',under='ignore'):
            factor=np.sqrt(r/np.max(r))*np.sqrt(det/np.max(det))
            volume=float(2*np.pi*np.sum(r*det*weights))
        if not np.isfinite(factor).all() or np.any(factor<=0) or not np.isfinite(volume) or volume<=0:
            raise ValueError('curved comparison physical volume weights must be finite and positive')
        sampler=FieldSampler.from_solution(solution)
        values=np.column_stack([sampler.evaluate(points,i,outside='raise')[field] for i in range(len(solution.frequencies_hz))])
        samples.append(values*factor[:,None]);volumes.append(volume)
        det_ranges.append([float(min(det)),float(max(det))])
    report=track_sampled_mode_subspaces(*samples,weights,previous.frequencies_hz,current.frequencies_hz,previous_ids,
        comparison_description=('declared paired native quadratic comparison cells; independently sampled '+('Ephi' if all(te) else 'Hphi')+' times normalized sqrt(r*detJ); common reference triangle measure'),**controls)
    report['physical_mapping']=dict(name=mapping,comparison_geometry_order=2,sample_order=sample_order,sample_count=count,
        comparison_triangle_count=cells,solver_triangle_counts=[len(s.space.geometry.cell_nodes) for s in solutions],
        comparison_mesh_sha256=[mesh_digest(m) for m in comparison_meshes],axisymmetric_volumes_m3=volumes,
        sampled_determinant_ranges_m2=det_ranges,boundary_coincidence=boundaries,
        comparison_edge_checks=[dict(s.edge_check) for s in spaces],field=field,
        field_multiplier='sqrt(r/max(r))*sqrt(detJ/max(detJ)) independently per comparison space',
        scope='explicit piecewise quadratic coordinate correspondence with matching native domain boundaries and independent curved FEM fields; variable volume retained; sample-order convergence required; not inferred physical correspondence, continuous branch identity or a physical error bound')
    if all(te):report['physical_mapping']['physics']='axisymmetric_m0_te'
    if sector is not None:report['physical_mapping']['symmetry_sector']=sector
    if automatic:report['physical_mapping']['numbering_correspondence']=correspondence
    if overlay is not None:report['physical_mapping']['common_reference_partition']=overlay.report
    return report

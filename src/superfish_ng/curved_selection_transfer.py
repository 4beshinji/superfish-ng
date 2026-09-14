# SPDX-License-Identifier: Apache-2.0
"""Transfer selected regions through exact reference-triangle intersections."""
from collections import defaultdict
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from .config import keys,integer
from .project import Project
from .mesh import make_mesh
from .mesh_input import mesh_from_dict
from .curved_space import curved_space
from .curved_refinement import refine_curved_space
from .curved_marked_refinement import refine_marked_curved_space
from .curved_comparison_correspondence import infer_curved_comparison_correspondence
from .planar_tracking_overlap import _clip,_cross

UNIT=((F(0),F(0)),(F(1),F(0)),(F(0),F(1)))


def _encode(value):
    return [value.numerator,value.denominator]


def _area(vertices):
    return sum((_cross(vertices[0],vertices[i],vertices[i+1]) for i in range(1,len(vertices)-1)),F(0))/2


def _compose(vertices,points):
    a,b,c=vertices
    return tuple(tuple(a[k]+F(float(x))*(b[k]-a[k])+F(float(y))*(c[k]-a[k]) for k in (0,1)) for x,y in points)


def _prepare(project):
    if not isinstance(project,Project):raise ValueError('curved selection transfer requires two Projects')
    project=Project.from_dict(project.to_dict());case=project.case
    from .te import is_te
    if case.curved_contour is None or case.geometry_order!=2 or is_te(case) or project.sections is not None or project.reflect_full:
        raise ValueError('curved selection transfer requires direct unassembled/unreflected native P2 TM Projects')
    mesh=make_mesh(case) if project.mesh_data is None else mesh_from_dict(case,project.mesh_data)
    limit=case.contour_mesh.max_triangles if case.contour_mesh is not None else 250000
    if len(mesh.triangles)>limit:raise ValueError('curved selection transfer base exceeds Case max_triangles')
    return project,curved_space(replace(case,curved_refinement_levels=0,curved_refinement_steps=()),mesh),limit


def _lineage(project,base,limit,initial):
    space=base;lineage=initial
    def steps():
        for _ in range(project.case.curved_refinement_levels):yield None
        yield from project.case.curved_refinement_steps
    for index,step in enumerate(steps(),1):
        try:
            if step is None or step.kind=='uniform':
                if 4*len(lineage)>limit:raise ValueError(f'uniform refinement exceeds max_triangles={limit}')
                refined=refine_curved_space(space)
            else:
                refined=refine_marked_curved_space(space,list(step.marked_cells),max_triangles=limit,
                    minimum_corner_angle_deg=step.minimum_corner_angle_deg,split_pattern=step.split_pattern)
        except ValueError as exc:raise ValueError(f'selection transfer history step {index}: {exc}') from exc
        lineage=[(lineage[int(parent)][0],_compose(lineage[int(parent)][1],vertices))
            for parent,vertices in zip(refined.parent_cells,refined.parent_reference_vertices)]
        space=refined.space
    totals=defaultdict(F)
    for owner,vertices in lineage:
        area=_area(vertices)
        if area<=0:raise ValueError('selection transfer has a nonpositive reference cell')
        totals[owner]+=area
    if set(totals)!=set(owner for owner,_ in initial) or any(value!=F(1,2) for value in totals.values()):
        raise ValueError('selection transfer history does not exactly cover each base reference triangle')
    return lineage


def _validate_request(request):
    fields=('schema_version','selected_cells','boundary_pairing','coverage_policy','max_pair_tests')
    keys(request,fields,fields,'curved selection transfer request')
    if type(request['schema_version']) is not int or request['schema_version']!=1:
        raise ValueError('curved selection transfer schema_version must be 1')
    if request['boundary_pairing'] not in ('same_curve_fractions','ordered_curve_vertices'):
        raise ValueError('boundary_pairing must be same_curve_fractions or ordered_curve_vertices')
    if request['coverage_policy'] not in ('intersects','contained'):
        raise ValueError('coverage_policy must be intersects or contained')
    integer(request['max_pair_tests'],'max_pair_tests')
    cells=request['selected_cells']
    if type(cells) is not list or not cells:raise ValueError('selected_cells must be a nonempty array of old final cell indices')
    for cell in cells:integer(cell,'selected_cells entry',minimum=0)
    if len(set(cells))!=len(cells):raise ValueError('selected_cells must be unique')


def transfer_curved_cell_selection(previous,current,request):
    """Return a replayable selection document for independent local histories.

    Base triangulations must correspond under the declared boundary policy.
    Final triangulations need not be nested or isomorphic. Native refinement
    parent maps are composed exactly, then rational clipping measures selected
    material regions in the common base reference coordinates. Intersects
    selects positive-area overlap; contained selects complete coverage. Edge/
    point contact has zero area and never selects a cell by itself.
    """
    _validate_request(request);request=deepcopy(request)
    prepared=[_prepare(p) for p in (previous,current)]
    projects=[p for p,_,_ in prepared];bases=[s for _,s,_ in prepared]
    correspondence=infer_curved_comparison_correspondence([p.case for p in projects],bases,
        boundary_pairing=request['boundary_pairing'])
    node_map=correspondence['current_node_for_previous'];cell_map=correspondence['current_cell_for_previous']
    previous_initial=[(i,UNIT) for i in range(len(cell_map))];current_initial=[None]*len(cell_map)
    for old,new in enumerate(cell_map):
        lookup={node_map[int(node)]:UNIT[i] for i,node in enumerate(bases[0].geometry.cell_nodes[old,:3])}
        current_initial[new]=(old,tuple(lookup[int(node)] for node in bases[1].geometry.cell_nodes[new,:3]))
    old,new=[_lineage(p,s,limit,initial) for (p,s,limit),initial in zip(prepared,(previous_initial,current_initial))]
    if max(request['selected_cells'])>=len(old):raise ValueError('selected_cells index exceeds the old final mesh')
    selected=defaultdict(list);targets=defaultdict(list)
    source_area=defaultdict(F)
    for cell in sorted(request['selected_cells']):
        owner,vertices=old[cell];selected[owner].append((cell,vertices));source_area[owner]+=_area(vertices)
    for cell,(owner,vertices) in enumerate(new):targets[owner].append((cell,vertices))
    candidates=sum(len(rows)*len(targets[owner]) for owner,rows in selected.items())
    if candidates>request['max_pair_tests']:
        raise ValueError(f'selection transfer requires {candidates} base-local pair tests, exceeding max_pair_tests={request["max_pair_tests"]}')
    overlaps=[];covered=defaultdict(F);intersection_area=defaultdict(F)
    def bounds(vertices):
        return tuple((min(p[k] for p in vertices),max(p[k] for p in vertices)) for k in (0,1))
    for owner,rows in selected.items():
        for source_cell,a in rows:
            box=bounds(a)
            for target_cell,b in targets[owner]:
                other=bounds(b)
                if any(max(x[0],y[0])>=min(x[1],y[1]) for x,y in zip(box,other)):continue
                polygon=_clip(a,b);area=_area(polygon)
                if area<0:raise ValueError('selection intersection has reversed orientation')
                if area==0:continue
                covered[target_cell]+=area;intersection_area[owner]+=area
                overlaps.append(dict(previous_cell=source_cell,current_cell=target_cell,base_cell=owner,
                    reference_vertices=[[ _encode(x),_encode(y)] for x,y in polygon],reference_area=_encode(area)))
    if any(intersection_area[owner]!=area for owner,area in source_area.items()):
        raise ValueError('selection intersections do not exactly cover the source selected region')
    cells=[];partial=[];coverage=[]
    for cell,area in sorted(covered.items()):
        fraction=area/_area(new[cell][1])
        if not 0<fraction<=1:raise ValueError('selection coverage exceeds a target reference cell')
        if fraction<1:partial.append(cell)
        if request['coverage_policy']=='intersects' or fraction==1:cells.append(cell)
        coverage.append(dict(current_cell=cell,covered_fraction=_encode(fraction),covered_reference_area=_encode(area)))
    return dict(schema_version=1,document_type='curved_selection_transfer',status='PASS',
        previous_project=projects[0].to_dict(),current_project=projects[1].to_dict(),request=request,
        base_correspondence=correspondence,
        selection=dict(selected_cells=cells,partially_covered_cells=partial,coverage=coverage,overlaps=overlaps,
            previous_final_cell_count=len(old),current_final_cell_count=len(new),base_local_pair_tests=candidates,
            source_reference_area=_encode(sum(source_area.values(),F(0))),
            intersection_reference_area=_encode(sum(intersection_area.values(),F(0))),
            base_area_checks=[dict(base_cell=owner,source_reference_area=_encode(area),intersection_reference_area=_encode(intersection_area[owner])) for owner,area in sorted(source_area.items())]),
        scope='exact rational selected-region coverage in corresponding base reference triangles; native P2 histories validated; reference fractions are not physical area/volume fractions or FEM error estimates; selected target cells are a cover or a contained subset, not necessarily the identical region')


def _same_json_values(actual,expected):
    """JSON may spell 0.0 as 0; derived integer IDs and booleans stay strict."""
    if type(expected) is dict:
        return type(actual) is dict and actual.keys()==expected.keys() and all(_same_json_values(actual[k],v) for k,v in expected.items())
    if type(expected) is list:
        return type(actual) is list and len(actual)==len(expected) and all(_same_json_values(a,b) for a,b in zip(actual,expected))
    if isinstance(expected,float):
        # NumPy float64 metadata also serializes as a JSON number. Browser
        # downloads may spell integral floating values without a decimal.
        return (isinstance(actual,float) or type(actual) is int) and actual==expected
    return type(actual) is type(expected) and actual==expected


def replay_curved_selection_transfer(document):
    fields=('schema_version','document_type','status','previous_project','current_project','request','base_correspondence','selection','scope')
    keys(document,fields,fields,'curved selection transfer document')
    if type(document['schema_version']) is not int or document['schema_version']!=1 or document['document_type']!='curved_selection_transfer':
        raise ValueError('curved selection transfer document requires schema_version=1 and its document_type')
    expected=transfer_curved_cell_selection(Project.from_dict(document['previous_project']),Project.from_dict(document['current_project']),document['request'])
    if not _same_json_values(document,expected):raise ValueError('curved selection transfer document differs from full reconstruction')
    return expected

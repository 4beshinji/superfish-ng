# SPDX-License-Identifier: Apache-2.0
"""Original-Project curved tuning trials with same-P2 final and comparison meshes."""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from scipy.sparse import eye
from .config import integer
from .hphi_project import HphiProject
from .curved_hphi import CurvedHphiCase
from .curved_hphi_shape_tuning import CurvedHphiShapeLaw
from .curved_hphi_refinement import refine_curved_hphi_geometry
from .curved_hphi_comparison import (CurvedHphiComparisonDomain,build_curved_hphi_comparison,
    CurvedHphiComparisonBudgetExceeded,_fraction,_vertices)
from .curved_hphi_tracking import CurvedHphiTrackingRequest
from .hphi_tracking import HphiTrackingControls


def _compose(parent,children):
    """Compose validated affine reference charts using exact rational arithmetic."""
    result=[]
    for child in children:
        source=parent[child['base_cell']]
        corners=[tuple(_fraction(x) for x in row) for row in source['reference_vertices']]
        points=[]
        for row in child['reference_vertices']:
            x,y=map(_fraction,row);weights=(1-x-y,x,y)
            points.append(tuple(sum((weights[j]*corners[j][i] for j in range(3)),F(0)) for i in range(2)))
        result.append(dict(base_cell=source['base_cell'],reference_vertices=_vertices(points)))
    return result


def _budget(geometry,order,levels,max_triangles,max_dofs,max_pair_tests):
    vertices=len(geometry.base_mesh.points_rz_m);edges=len(geometry.edge_vertices);cells=len(geometry.cell_nodes)
    root=cells
    for level in range(levels+1):
        if cells>max_triangles:raise CurvedHphiComparisonBudgetExceeded('curved tune trial exceeds max_triangles')
        if vertices+(edges if order==2 else 0)>max_dofs:
            raise CurvedHphiComparisonBudgetExceeded('curved tune trial exceeds max_dofs')
        children=4**level
        if root*(children*(children-1)//2+children)>max_pair_tests or (level<levels and 10*cells>max_pair_tests):
            raise CurvedHphiComparisonBudgetExceeded('curved tune root restriction exceeds max_pair_tests')
        vertices,edges,cells=vertices+edges,2*edges+3*cells,4*cells


@dataclass(frozen=True)
class CurvedHphiTuneTrial:
    project: HphiProject
    reference_geometry: object
    native_cells: list
    prolongation: object
    diagnostic: dict


def build_curved_hphi_tune_trial(project,law,value,*,phase='search',refinement_levels=1,
        max_triangles=250000,max_dofs=250000,max_pair_tests=2000000):
    """Generate one candidate from the root Project; preserve its quadratic domain.

    This prepares geometry and scalar transfer only. It neither accepts a
    target frequency nor substitutes transferred coefficients for a FEM solve.
    """
    if type(project) is not HphiProject or type(project.case) is not CurvedHphiCase:
        raise ValueError('curved tune trial requires an original CurvedHphiCase Project')
    if type(law) is not CurvedHphiShapeLaw:raise ValueError('curved tune trial requires an explicit CurvedHphiShapeLaw')
    if phase not in ('search','refinement'):raise ValueError('curved tune trial phase must be search or refinement')
    for name,number in (('refinement_levels',refinement_levels),('max_triangles',max_triangles),('max_dofs',max_dofs),('max_pair_tests',max_pair_tests)):
        integer(number,name)
    if refinement_levels>8:raise ValueError('curved tune refinement_levels must be from 1 to 8')
    levels=refinement_levels if phase=='refinement' else 0
    _budget(project.case.geometry,project.case.element_order,levels,max_triangles,max_dofs,max_pair_tests)
    shaped=law.apply(project,value);reference=shaped.project.case.geometry;geometry=reference
    cells=[dict(base_cell=i,reference_vertices=[[[0,1],[0,1]],[[1,1],[0,1]],[[0,1],[1,1]]])
           for i in range(len(reference.cell_nodes))]
    dofs=len(reference.points_rz_m) if project.case.element_order==2 else len(reference.base_mesh.points_rz_m)
    transfer=eye(dofs,format='csr');diagnostics=[]
    for _ in range(levels):
        refined=refine_curved_hphi_geometry(geometry,element_order=project.case.element_order,
            max_triangles=max_triangles,max_dofs=max_dofs,max_pair_tests=max_pair_tests)
        cells=_compose(cells,refined.native_cells);transfer=refined.prolongation@transfer
        geometry=refined.geometry;diagnostics.append(refined.diagnostic)
    domain=CurvedHphiComparisonDomain(reference,reference,'same_vacuum',restriction_policy='binary64_roundoff')
    coverage=build_curved_hphi_comparison(reference,geometry,domain,current_cells=cells,
        max_pair_tests=max_pair_tests,max_triangles=max_triangles)
    for array in (transfer.data,transfer.indices,transfer.indptr):array.setflags(write=False)
    return CurvedHphiTuneTrial(replace(shaped.project,case=replace(shaped.project.case,geometry=geometry)),
        reference,cells,transfer,dict(shape=shaped.diagnostic,phase=phase,refinement_levels=levels,
            refinements=diagnostics,root_geometry_comparison=coverage.report,
            scope='same full quadratic candidate with explicit rounded-native restrictions; no target or continuum acceptance'))


def curved_hphi_trial_comparison(previous,current,*,previous_mode_ids=None,previous_identity_groups=None,
        previous_mode_count=2,current_mode_count=2,controls=None,max_sample_points=2000000):
    """Prepare original-domain finer spaces for search or final-trial tracking."""
    if type(previous) is not CurvedHphiTuneTrial or type(current) is not CurvedHphiTuneTrial:
        raise ValueError('curved tune comparison requires two generated trial records')
    controls=HphiTrackingControls() if controls is None else controls
    if type(controls) is not HphiTrackingControls:raise ValueError('expected HphiTrackingControls')
    comparison=[];charts=[]
    for trial in (previous,current):
        refined=refine_curved_hphi_geometry(trial.project.case.geometry,element_order=2,
            max_triangles=controls.max_overlay_triangles,max_dofs=controls.max_dofs,max_pair_tests=controls.max_candidate_tests)
        cells=_compose(trial.native_cells,refined.native_cells)
        reference=trial.reference_geometry
        domain=CurvedHphiComparisonDomain(reference,reference,'same_vacuum',restriction_policy='binary64_roundoff')
        build_curved_hphi_comparison(reference,refined.geometry,domain,current_cells=cells,
            max_pair_tests=controls.max_candidate_tests,max_triangles=controls.max_overlay_triangles)
        comparison.append(refined.geometry);charts.append(cells)
    domain=CurvedHphiComparisonDomain(previous.reference_geometry,current.reference_geometry,
        'declared_quadratic',restriction_policy='binary64_roundoff')
    return CurvedHphiTrackingRequest(domain,*comparison,previous_cells=previous.native_cells,current_cells=current.native_cells,
        previous_comparison_cells=charts[0],current_comparison_cells=charts[1],previous_mode_count=previous_mode_count,
        current_mode_count=current_mode_count,previous_mode_ids=previous_mode_ids,previous_identity_groups=previous_identity_groups,
        controls=controls,max_sample_points=max_sample_points)

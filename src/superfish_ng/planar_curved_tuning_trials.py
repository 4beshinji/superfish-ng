# SPDX-License-Identifier: Apache-2.0
"""Regenerated curved xy search/final meshes with complete original charts."""
from dataclasses import dataclass, replace
from fractions import Fraction as F
from .config import integer
from .planar_project import PlanarProject
from .planar_curved_shape import PlanarCurvedAffineShapeLaw
from .planar_curved_refinement import refine_planar_curved_domain
from .planar_curved_comparison import (PlanarCurvedComparisonDomain,
    PlanarCurvedComparisonBudgetExceeded, build_planar_curved_comparison, UNIT, _vertices)


@dataclass(frozen=True)
class PlanarCurvedTrial:
    reference_project: PlanarProject
    project: PlanarProject
    _charts: tuple
    diagnostic: dict

    @property
    def native_cells(self):
        # A fresh JSON chart copy; no external mutation changes stored charts.
        return [dict(base_cell=owner,reference_vertices=_vertices(vertices)) for owner,vertices in self._charts]


def generate_planar_curved_trial(original, shape_law, value, *, refinement_levels=0,
        max_triangles=250000, max_dofs=250000, max_pair_tests=2000000):
    """Build from the original full Project, then restrict its quadratic maps.

    Complete final counts and the ORIGINAL-chart comparison cost are checked
    before partial refinement. Local restrictions are composed as rationals;
    accumulated binary64 differences are tested against that original map,
    never merely against the preceding refinement level. No eigensolve occurs.
    """
    integer(refinement_levels,'refinement_levels',0)
    if refinement_levels>8:raise ValueError('curved planar trials support at most eight uniform refinement levels')
    for name,budget in (('max_triangles',max_triangles),('max_dofs',max_dofs),('max_pair_tests',max_pair_tests)):
        integer(budget,name)
    if type(shape_law) is not PlanarCurvedAffineShapeLaw:
        raise ValueError('curved planar trial requires a complete PlanarCurvedAffineShapeLaw')
    shape_law=PlanarCurvedAffineShapeLaw.from_dict(shape_law.to_dict())
    reference=shape_law.project(original,value)
    base=reference.case.domain
    original_count=len(base.cell_nodes)
    count=original_count
    edges={tuple(sorted((int(cell[a]),int(cell[b])))) for cell in base.cell_nodes for a,b in ((0,1),(1,2),(2,0))}
    edge_count,dofs=len(edges),len(base.points_xy_m)
    for _ in range(refinement_levels):
        dofs+=2*edge_count+3*count
        edge_count=2*edge_count+3*count
        count*=4
    descendants=4**refinement_levels
    pairs=original_count*descendants*(descendants+1)//2
    for expected,limit,name in ((count,max_triangles,'max_triangles'),(dofs,max_dofs,'max_dofs'),(pairs,max_pair_tests,'max_pair_tests')):
        if expected>limit:
            raise PlanarCurvedComparisonBudgetExceeded(f'complete original-map curved trial exceeds {name}')
    charts=tuple((owner,UNIT) for owner in range(original_count))
    native=base
    for _ in range(refinement_levels):
        restriction=refine_planar_curved_domain(native,max_geometry_boxes=reference.case.max_geometry_boxes)
        composed=[]
        for parent,vertices in zip(restriction.parent_cells,restriction.parent_reference_vertices):
            owner,previous=charts[int(parent)]
            next_vertices=[]
            for point in vertices:
                x,y=(F(float(v)) for v in point)
                weights=1-x-y,x,y
                next_vertices.append(tuple(sum((w*v[axis] for w,v in zip(weights,previous)),F(0)) for axis in (0,1)))
            composed.append((owner,tuple(next_vertices)))
        charts=tuple(composed)
        native=restriction.domain
    if len(native.cell_nodes)!=count or len(native.points_xy_m)!=dofs:
        raise ValueError('UNVERIFIED: curved trial native counts differ from full uniform refinement')
    cells=[dict(base_cell=owner,reference_vertices=_vertices(vertices)) for owner,vertices in charts]
    domain=PlanarCurvedComparisonDomain(base,base,restriction_policy='binary64_roundoff',
                                      max_geometry_boxes_per_domain=reference.case.max_geometry_boxes)
    comparison=build_planar_curved_comparison(base,native,domain,current_cells=cells,
        max_pair_tests=max_pair_tests,max_triangles=max_triangles)
    if comparison.report['pair_tests']!=pairs:
        raise ValueError('UNVERIFIED: curved trial original-map comparison cost differs from full partition')
    project=replace(reference,case=replace(reference.case,domain=native))
    diagnostic=dict(original_project=PlanarProject.from_dict(original.to_dict()).to_dict(),shape_law=shape_law.to_dict(),
        value=value,parameter_unit='dimensionless',refinement_levels=refinement_levels,
        original_triangles=original_count,native_triangles=count,native_dofs=dofs,
        original_map_pair_tests=pairs,max_triangles=max_triangles,max_dofs=max_dofs,max_pair_tests=max_pair_tests,
        geometry=comparison.report,
        boundary_policy='restrictions of original full quadratic trial domain; no analytic reprojection',
        scope='original-Project trial geometry and complete rational charts only; no FEM frequency, identity or tuning acceptance')
    return PlanarCurvedTrial(reference,project,charts,diagnostic)


def planar_curved_trial_comparison(previous,current):
    """Declare both complete reference domains; source owner still verifies runs."""
    if type(previous) is not PlanarCurvedTrial or type(current) is not PlanarCurvedTrial:
        raise ValueError('curved trial comparison requires two generated PlanarCurvedTrial objects')
    if (previous.diagnostic['original_project']!=current.diagnostic['original_project']
            or previous.diagnostic['shape_law']!=current.diagnostic['shape_law']):
        raise ValueError('curved tuning trials must share the complete original Project and shape law')
    a,b=previous.reference_project.case,current.reference_project.case
    return PlanarCurvedComparisonDomain(a.domain,b.domain,'declared_quadratic','binary64_roundoff',
                                       max(a.max_geometry_boxes,b.max_geometry_boxes))

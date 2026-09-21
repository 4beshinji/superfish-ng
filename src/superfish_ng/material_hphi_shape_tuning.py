# SPDX-License-Identifier: Apache-2.0
"""Explicit fixed-material straight shape laws generated from an original Project."""
from dataclasses import dataclass,replace
from fractions import Fraction as F
import numpy as np
from .config import keys,positive
from .coaxial import _numeric_coordinates
from .axis_hphi import AxisAccelerationPath
from .hphi_project import HphiProject
from .material_hphi import MaterialHphiCase
from .rf_materials import RFMaterialPartition
from .hphi_shape_tuning import _boundary_cycles
from .hphi_geometry_mapping import HphiGeometryMapping
from .material_hphi_comparison import MaterialHphiComparison,material_hphi_overlay


@dataclass(frozen=True)
class MaterialHphiShapeResult:
    project: HphiProject
    comparison: MaterialHphiComparison
    diagnostic: dict


@dataclass(frozen=True)
class MaterialHphiShapeLaw:
    kind: str
    reference_value: float=1.
    displacements_rz_m: object=None
    acceleration_policy: str='transport_on_axis'

    def __post_init__(self):
        if self.kind not in ('uniform_scale','general_piecewise_affine'):
            raise ValueError('material shape requires uniform_scale or general_piecewise_affine')
        object.__setattr__(self,'reference_value',positive(self.reference_value,'material shape reference_value'))
        if self.acceleration_policy!='transport_on_axis':raise ValueError('material shape acceleration_policy must be transport_on_axis')
        if self.kind=='uniform_scale':
            if self.displacements_rz_m is not None:raise ValueError('uniform_scale requires null displacements_rz_m')
        else:
            points=_numeric_coordinates(self.displacements_rz_m,2,'material shape displacements_rz_m').copy()
            if not len(points):raise ValueError('material shape requires nonempty displacements')
            points.setflags(write=False);object.__setattr__(self,'displacements_rz_m',points)

    def to_dict(self):
        return dict(format='superfish_ng_material_hphi_shape_law',schema_version=1,kind=self.kind,
            reference_value=self.reference_value,displacements_rz_m=None if self.displacements_rz_m is None else self.displacements_rz_m.tolist(),
            acceleration_policy=self.acceleration_policy)

    @classmethod
    def from_dict(cls,data):
        names=('format','schema_version','kind','reference_value','displacements_rz_m','acceleration_policy')
        keys(data,names,names,'material Hphi shape law')
        if data['format']!='superfish_ng_material_hphi_shape_law' or type(data['schema_version']) is not int or data['schema_version']!=1:
            raise ValueError('expected material Hphi shape law schema_version 1')
        return cls(*(data[n] for n in names[2:]))

    def apply(self,project,value,*,max_candidate_tests=2000000,max_overlay_triangles=250000,
              max_interface_tests=2000000,max_interface_pieces=250000):
        """Generate a candidate from root coordinates, retaining material ownership.

        uniform_scale uses value/reference_value; displacements use
        x+(value-reference_value)*d. Rational arithmetic precedes one rounding
        to binary64. Every original boundary vertex becomes a control corner.
        This validates geometry and original interfaces, not a tuned frequency.
        """
        value=positive(value,'material shape value')
        if type(project) is not HphiProject or type(project.case) is not MaterialHphiCase:
            raise ValueError('material shape requires an original MaterialHphiCase Project')
        project=HphiProject.from_dict(project.to_dict());case=project.case;p=case.partition;mesh=p.mesh
        if self.kind=='general_piecewise_affine':
            if self.displacements_rz_m.shape!=mesh.points_rz_m.shape:
                raise ValueError('material shape requires one displacement per original mesh vertex')
            if case.axis_connected and np.any(self.displacements_rz_m[mesh.axis_nodes,0]!=0):
                raise ValueError('material shape cannot move any axis node radially')
            delta=F(value)-F(self.reference_value)
            exact=[[F(float(x))+delta*F(float(d)) for x,d in zip(point,shift)] for point,shift in zip(mesh.points_rz_m,self.displacements_rz_m)]
        else:
            scale=F(value)/F(self.reference_value)
            exact=[[scale*F(float(x)) for x in point] for point in mesh.points_rz_m]
        try:points=np.array([[float(x) for x in point] for point in exact])
        except OverflowError as error:raise ValueError('material shape exceeds finite SI coordinates') from error
        if not np.isfinite(points).all():raise ValueError('material shape exceeds finite SI coordinates')
        cycles=_boundary_cycles(mesh)
        def geometry(coords):return type(mesh)(coords[cycles[0]],[coords[c] for c in cycles[1:]],coords,mesh.triangles)
        mapping=HphiGeometryMapping(geometry(mesh.points_rz_m),geometry(points))
        current=RFMaterialPartition(mapping.current,p.materials,p.regions)
        comparison=MaterialHphiComparison(p,current,mapping,
            [dict(previous_id=m.id,current_id=m.id) for m in p.materials],
            [dict(previous_id=r.id,current_id=r.id) for r in p.regions])
        coverage=material_hphi_overlay(comparison,max_candidate_tests=max_candidate_tests,max_overlay_triangles=max_overlay_triangles,
            max_interface_tests=max_interface_tests,max_interface_pieces=max_interface_pieces)
        changes=dict(partition=current)
        if case.acceleration is not None:
            path=case.acceleration;z=mapping.transport_axis_coordinates([path.z_start_m,path.z_end_m,path.phase_origin_m])
            changes['acceleration']=AxisAccelerationPath(float(z[0]),float(z[1]),path.beta,float(z[2]))
        candidate=replace(project,case=replace(case,**changes))
        return MaterialHphiShapeResult(candidate,comparison,dict(shape_law=self.to_dict(),value=value,
            parameter_unit='dimensionless',overlay_triangles=len(coverage.overlay.determinants),interface_pieces=len(coverage.interfaces.previous_edges),
            original_boundary_segments=mesh.boundary_segments.tolist(),current_boundary_segments=current.mesh.boundary_segments.tolist(),
            boundary_policy='every original boundary vertex is an explicit control corner',
            scope='fixed-material original-Project geometry only; no field solve, frequency correction or tuning acceptance'))

# SPDX-License-Identifier: Apache-2.0
"""Explicit full-P2 shape laws derived independently from an original Project."""
from dataclasses import dataclass,replace
from fractions import Fraction as F
import numpy as np
from .config import keys,positive
from .coaxial import _numeric_coordinates
from .axis_hphi import AxisAccelerationPath
from .curved_hphi import CurvedHphiCase
from .hphi_project import HphiProject
from .curved_meridional_geometry import CurvedMeridionalGeometry
from .curved_hphi_comparison import CurvedHphiComparisonDomain,_upper_float
from .hphi_geometry_mapping import HphiGeometryMapping
from .hphi_shape_tuning import _boundary_cycles


@dataclass(frozen=True)
class CurvedHphiShapeResult:
    project: HphiProject
    domain: CurvedHphiComparisonDomain
    diagnostic: dict


@dataclass(frozen=True)
class CurvedHphiShapeLaw:
    reference_value: float
    displacements_rz_m: object
    acceleration_policy: str

    def __post_init__(self):
        object.__setattr__(self,'reference_value',positive(self.reference_value,'curved shape reference_value'))
        displacement=_numeric_coordinates(self.displacements_rz_m,2,'curved shape full-P2 displacements_rz_m').copy()
        if not len(displacement):raise ValueError('curved shape requires nonempty full-P2 displacement rows')
        displacement.setflags(write=False);object.__setattr__(self,'displacements_rz_m',displacement)
        if self.acceleration_policy!='transport_on_axis':
            raise ValueError('curved shape acceleration_policy must explicitly be transport_on_axis')

    def to_dict(self):
        return dict(format='superfish_ng_curved_hphi_shape_law',schema_version=1,kind='full_quadratic_displacement',
            reference_value=self.reference_value,displacements_rz_m=self.displacements_rz_m.tolist(),
            acceleration_policy=self.acceleration_policy)

    @classmethod
    def from_dict(cls,data):
        names=('format','schema_version','kind','reference_value','displacements_rz_m','acceleration_policy')
        keys(data,names,names,'curved Hphi shape law')
        if (data['format']!='superfish_ng_curved_hphi_shape_law' or type(data['schema_version']) is not int
                or data['schema_version']!=1 or data['kind']!='full_quadratic_displacement'):
            raise ValueError('expected curved Hphi full_quadratic_displacement shape law version 1')
        return cls(data['reference_value'],data['displacements_rz_m'],data['acceleration_policy'])

    def apply(self,project,value):
        """Return a new candidate; never accumulate deformation on a prior trial.

        All P2 coordinates follow x+(value-reference_value)*displacement,
        evaluated rationally then rounded once. Axis midpoint coordinates use
        the native straight-axis convention, with the difference explicitly
        bounded and reported; radial axis motion is never accepted.
        """
        value=positive(value,'curved shape value')
        if type(project) is not HphiProject or type(project.case) is not CurvedHphiCase:
            raise ValueError('curved shape requires an original vacuum CurvedHphiCase Project')
        project=HphiProject.from_dict(project.to_dict());case=project.case;g=case.geometry;base=g.base_mesh
        displacement=self.displacements_rz_m
        if displacement.shape!=g.points_rz_m.shape:
            raise ValueError('curved shape requires one displacement for every original P2 geometry node')
        axis=g.boundary_nodes[g.boundary_tags=='axis']
        if len(axis):
            if np.any(displacement[np.unique(axis),0]!=0):raise ValueError('curved shape cannot move any axis node radially')
            if not np.array_equal(displacement[axis[:,2]],displacement[axis[:,:2]].mean(axis=1)):
                raise ValueError('curved axis midpoint displacement must equal the endpoint mean')
        delta=F(float(value))-F(float(self.reference_value))
        nominal=[[F(float(x))+delta*F(float(d)) for x,d in zip(point,shift)]
                 for point,shift in zip(g.points_rz_m,displacement)]
        try:points=np.array([[float(v) for v in row] for row in nominal])
        except OverflowError as error:raise ValueError('curved shape coordinates exceed finite SI arithmetic') from error
        if not np.isfinite(points).all():raise ValueError('curved shape coordinates exceed finite SI arithmetic')
        axis_error=F(0)
        if len(axis):
            points[axis[:,2]]=points[axis[:,:2]].mean(axis=1)
            axis_error=max(abs(F(float(points[node,coordinate]))-nominal[node][coordinate])
                           for node in axis[:,2] for coordinate in (0,1))
            scale=max(abs(v) for row in nominal for v in row)
            if axis_error>8*F(2)**-52*scale:
                raise ValueError('curved shape axis midpoint canonicalization exceeds binary64 roundoff')
            for first,last,middle in axis:
                local_error=max(abs(F(float(points[middle,k]))-nominal[middle][k]) for k in (0,1))
                extent=max(abs(F(float(points[last,k]))-F(float(points[first,k]))) for k in (0,1))
                if local_error>512*F(2)**-52*extent:
                    raise ValueError('curved shape axis roundoff is unresolved relative to its edge size')
        cycles=_boundary_cycles(base);nv=len(base.points_rz_m)
        def geometry(coordinates):
            vertices=coordinates[:nv]
            mesh=type(base)(vertices[cycles[0]],[vertices[c] for c in cycles[1:]],vertices,base.triangles)
            return CurvedMeridionalGeometry(mesh,g.edge_vertices,coordinates[nv:])
        reference=geometry(g.points_rz_m);current=geometry(points)
        domain=CurvedHphiComparisonDomain(reference,current,'declared_quadratic')
        changes=dict(geometry=current)
        if case.acceleration is not None:
            path=case.acceleration
            coordinates=HphiGeometryMapping(reference.base_mesh,current.base_mesh).transport_axis_coordinates(
                [path.z_start_m,path.z_end_m,path.phase_origin_m])
            changes['acceleration']=AxisAccelerationPath(float(coordinates[0]),float(coordinates[1]),path.beta,float(coordinates[2]))
        diagnostic=dict(shape_law=self.to_dict(),value=value,parameter_unit='dimensionless',
            axis_midpoint_roundoff_upper_m=_upper_float(axis_error),
            original_boundary_segments=base.boundary_segments.tolist(),
            reference_boundary_segments=reference.base_mesh.boundary_segments.tolist(),
            boundary_components=len(base.holes_rz_m)+1,
            boundary_policy='retain every original boundary vertex as an explicit reference corner; all original P2 coordinates unchanged in reference',
            acceleration_policy=self.acceleration_policy,
            scope='original-Project geometry only; no FEM solve, frequency correction, tracking or tuning acceptance')
        return CurvedHphiShapeResult(replace(project,case=replace(case,**changes)),domain,diagnostic)

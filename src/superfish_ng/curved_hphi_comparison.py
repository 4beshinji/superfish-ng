# SPDX-License-Identifier: Apache-2.0
"""Complete P2 Hphi domains and exact declared native reference partitions.

No field projection, eigensolve or physical identity is inferred here. Binary64
geometry coefficients are treated as exact rationals when checking restrictions.
"""
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction as F
import numpy as np
from .axis_connected_mesh import AxisConnectedMesh
from .config import integer, keys
from .curved_meridional_geometry import CurvedMeridionalGeometry, _polynomial
from .hphi_geometry_mapping import HphiGeometryMapping
from .planar_tracking_overlap import _clip, _cross, _barycentric
from .quadratic_geometry import QuadraticTriangle

UNIT=((F(0),F(0)),(F(1),F(0)),(F(0),F(1)))


class CurvedHphiComparisonBudgetExceeded(ValueError):
    """A geometry comparison that was not verified within its declared budget."""
    status='UNVERIFIED'


def _encode(value):
    return [value.numerator,value.denominator]


def _upper_float(value):
    """Outward-round a nonnegative rational bound, including subnormal values."""
    rounded=float(value)
    return float(np.nextafter(rounded,np.inf)) if F(rounded)<value else rounded


def _vertices(vertices):
    return [[_encode(x),_encode(y)] for x,y in vertices]


def _area(polygon):
    return sum((_cross(polygon[0],polygon[i],polygon[i+1])/2
                for i in range(1,len(polygon)-1)),F(0))


@dataclass(frozen=True)
class CurvedHphiComparisonDomain:
    previous: CurvedMeridionalGeometry
    current: CurvedMeridionalGeometry
    mapping: str
    restriction_policy: str='exact'

    def __post_init__(self):
        if self.restriction_policy not in ('exact','binary64_roundoff'):
            raise ValueError('native restriction policy must be exact or binary64_roundoff')
        if self.mapping not in ('same_vacuum','declared_quadratic'):
            raise ValueError('curved Hphi mapping must be same_vacuum or declared_quadratic')
        domains=[]
        for geometry in (self.previous,self.current):
            if type(geometry) is not CurvedMeridionalGeometry:
                raise ValueError('curved Hphi comparison requires complete quadratic meridional geometry')
            domains.append(CurvedMeridionalGeometry.from_dict(geometry.to_dict()))
        a,b=domains
        # This checks every boundary component, oriented cell, axis node and
        # explicit numbering. The actual physical maps below remain quadratic.
        HphiGeometryMapping(a.base_mesh,b.base_mesh)
        if not np.array_equal(a.cell_nodes,b.cell_nodes) or not np.array_equal(a.boundary_tags,b.boundary_tags):
            raise ValueError('curved reference domains require explicit matching P2 topology and boundary roles')
        if self.mapping=='same_vacuum' and not np.array_equal(a.points_rz_m,b.points_rz_m):
            raise ValueError('same_vacuum requires identical complete quadratic reference coefficients, including midpoints')
        object.__setattr__(self,'previous',a);object.__setattr__(self,'current',b)

    def to_dict(self):
        data=dict(format='superfish_ng_curved_hphi_comparison_domain',schema_version=1,
                    mapping=self.mapping,previous=self.previous.to_dict(),current=self.current.to_dict())
        if self.restriction_policy!='exact':
            data.update(schema_version=2,native_restriction=self.restriction_policy)
        return data

    @classmethod
    def from_dict(cls,data):
        version=data.get('schema_version') if isinstance(data,dict) else None
        names=('format','schema_version','mapping','previous','current')+(('native_restriction',) if version==2 else ())
        keys(data,names,names,'curved Hphi comparison domain')
        if (data['format']!='superfish_ng_curved_hphi_comparison_domain'
                or type(version) is not int or version not in (1,2)):
            raise ValueError('expected curved Hphi comparison domain schema_version 1 or 2')
        if version==2 and data['native_restriction']!='binary64_roundoff':
            raise ValueError('domain version 2 requires explicit binary64_roundoff native restriction')
        return cls(*(CurvedMeridionalGeometry.from_dict(data[name]) for name in ('previous','current')),data['mapping'],
                   'exact' if version==1 else data['native_restriction'])

    def inverse(self):
        return type(self)(self.current,self.previous,self.mapping,self.restriction_policy)


def _fraction(raw):
    if (type(raw) is not list or len(raw)!=2 or any(type(n) is not int for n in raw)
            or raw[1]<=0):
        raise ValueError('reference coordinates require [integer numerator, positive integer denominator]')
    return F(*raw)


def _partition(reference,native,declarations,max_pair_tests,max_triangles,restriction_policy='exact'):
    if type(native) is not CurvedMeridionalGeometry:
        raise ValueError('native geometry must be CurvedMeridionalGeometry')
    native=CurvedMeridionalGeometry.from_dict(native.to_dict())
    if type(native.base_mesh) is not type(reference.base_mesh):
        raise ValueError('native and reference geometry must have the same axis/positive-radius formulation')
    if len(native.cell_nodes)>max_triangles:
        raise CurvedHphiComparisonBudgetExceeded('curved Hphi native partition exceeds max_triangles')
    if declarations is None:
        if len(native.cell_nodes)!=len(reference.cell_nodes):
            raise ValueError('different native partition requires one explicit chart per native cell')
        declarations=[dict(base_cell=i,reference_vertices=_vertices(UNIT)) for i in range(len(native.cell_nodes))]
    if type(declarations) is not list or len(declarations)!=len(native.cell_nodes):
        raise ValueError('one explicit reference chart per native cell is required')
    groups=defaultdict(list);charts=[];error_bounds=[]
    polynomials=[tuple(_polynomial(reference.points_rz_m[nodes,i]) for i in (0,1)) for nodes in reference.cell_nodes]
    for cell,(nodes,raw) in enumerate(zip(native.cell_nodes,declarations)):
        keys(raw,('base_cell','reference_vertices'),('base_cell','reference_vertices'),'curved Hphi native chart')
        owner=integer(raw['base_cell'],'base_cell',0)
        if owner>=len(reference.cell_nodes):raise ValueError('base_cell is outside the reference geometry')
        vertices=raw['reference_vertices']
        if type(vertices) is not list or len(vertices)!=3 or any(type(p) is not list or len(p)!=2 for p in vertices):
            raise ValueError('reference_vertices must contain three rational coordinate pairs')
        vertices=tuple(tuple(_fraction(v) for v in p) for p in vertices)
        if any(x<0 or y<0 or x+y>1 for x,y in vertices) or _cross(*vertices)<=0:
            raise ValueError('native chart requires a positive triangle inside its reference cell')
        samples=vertices+tuple(tuple((vertices[i][k]+vertices[j][k])/2 for k in (0,1)) for i,j in ((0,1),(1,2),(2,0)))
        errors=[];reference_points=reference.points_rz_m[reference.cell_nodes[owner]]
        coordinate_scale=[max(F(abs(float(v))) for v in reference_points[:,axis]) for axis in (0,1)]
        for point,node in zip(samples,nodes):
            error=[]
            for axis,p in enumerate(polynomials[owner]):
                expected=sum((v*point[0]**a*point[1]**b for (a,b),v in p.items()),F(0))
                difference=F(float(native.points_rz_m[node,axis]))-expected
                if restriction_policy=='exact' and difference:
                    raise ValueError(f'native cell {cell} is not the exact declared quadratic restriction (including midpoints)')
                if restriction_policy=='binary64_roundoff' and abs(difference)>8*F(1,2**52)*coordinate_scale[axis]:
                    raise ValueError(f'native cell {cell} differs from its quadratic restriction beyond binary64 roundoff')
                error.append(difference)
            errors.append(error)
        # Convex-hull bound of the vector-valued quadratic error polynomial.
        controls=errors[:3]+[[2*errors[3+k][axis]-(errors[i][axis]+errors[j][axis])/2 for axis in (0,1)]
                            for k,(i,j) in enumerate(((0,1),(1,2),(2,0))) ]
        bound=[max(abs(row[axis]) for row in controls) for axis in (0,1)]
        extent=max(max(F(float(v)) for v in native.points_rz_m[nodes,axis])-min(F(float(v)) for v in native.points_rz_m[nodes,axis]) for axis in (0,1))
        if max(bound)>512*F(1,2**52)*extent:
            raise ValueError('native quadratic restriction roundoff is unresolved relative to the cell size')
        error_bounds.append([_upper_float(v) for v in bound])
        charts.append((owner,vertices));groups[owner].append((cell,vertices))
    pairs=sum(len(rows)*(len(rows)-1)//2 for rows in groups.values())
    if pairs>max_pair_tests:
        raise CurvedHphiComparisonBudgetExceeded('curved Hphi native coverage exceeds max_pair_tests')
    for owner in range(len(reference.cell_nodes)):
        rows=groups[owner]
        if sum((_area(v) for _,v in rows),F(0))!=F(1,2):
            raise ValueError('native reference partition does not completely cover every base cell')
        for i,(_,a) in enumerate(rows):
            if any(_area(_clip(a,b))!=0 for _,b in rows[i+1:]):
                raise ValueError('native reference partition has overlapping positive areas')
    # Check component labels on all physical boundary restrictions, including
    # every hole and the regular axis. Native segmentation may be finer.
    boundary={tuple(sorted(map(int,row[:2]))):(int(component),str(tag))
              for row,component,tag in zip(reference.boundary_nodes,reference.base_mesh.boundary_components,reference.boundary_tags)}
    for edge,cell,component,tag in zip(native.boundary_nodes,native.base_mesh.boundary_cells,
                                      native.base_mesh.boundary_components,native.boundary_tags):
        owner,vertices=charts[int(cell)];corners=list(map(int,native.cell_nodes[cell,:3]))
        a,b=(vertices[corners.index(int(node))] for node in edge[:2])
        for i,j in ((0,1),(1,2),(2,0)):
            if _cross(UNIT[i],UNIT[j],a)==0 and _cross(UNIT[i],UNIT[j],b)==0:
                key=tuple(sorted(map(int,reference.cell_nodes[owner,[i,j]])))
                if boundary.get(key)==(int(component),str(tag)):break
        else:raise ValueError('native boundary does not preserve every declared reference component and axis role')
    return native,charts,groups,pairs,error_bounds


@dataclass(frozen=True)
class CurvedHphiComparison:
    domain: CurvedHphiComparisonDomain
    native_geometries: tuple
    triangles: tuple
    report: dict

    def evaluate(self,side,barycentric):
        """Common quadrature points, native cell coordinates and physical measure."""
        if type(side) is not int or side not in (0,1):raise ValueError('comparison side must be 0 or 1')
        q=np.asarray(barycentric)
        if (q.dtype.kind not in 'iuf' or q.ndim!=2 or q.shape[1]!=3 or not np.isfinite(q).all()
                or np.any(q<0) or np.any(q>1) or not np.allclose(q.sum(axis=1),1.,rtol=0,atol=8*np.finfo(float).eps)):
            raise ValueError('comparison sampling requires unit-sum nonnegative barycentric triples')
        reference=(self.domain.previous,self.domain.current)[side];result=[]
        for owner,vertices,old,new,parents in self.triangles:
            points=q@np.asarray(vertices,dtype=float)
            mapped=QuadraticTriangle(reference.points_rz_m[reference.cell_nodes[owner]]).evaluate(points)
            measure=mapped['determinant_m2']*float(_cross(*vertices))
            native_vertices=np.asarray(_barycentric(vertices,parents[side]))
            if not np.isfinite(measure).all() or np.any(measure<=0):
                raise ValueError('curved common partition is unresolved in floating SI arithmetic')
            result.append(dict(native_cell=(old,new)[side],native_barycentric=q@native_vertices,
                points_rz_m=mapped['points_rz_m'],determinant_m2=measure))
        return result


def build_curved_hphi_comparison(previous,current,domain,*,previous_cells=None,current_cells=None,
                                 max_pair_tests=2000000,max_triangles=250000):
    """Verify both complete native restrictions and intersect their exact charts."""
    integer(max_pair_tests,'max_pair_tests');integer(max_triangles,'max_triangles')
    if type(domain) is not CurvedHphiComparisonDomain:raise ValueError('explicit curved Hphi comparison domain required')
    domain=CurvedHphiComparisonDomain.from_dict(domain.to_dict())
    prepared=[_partition(ref,native,cells,max_pair_tests,max_triangles,domain.restriction_policy)
              for ref,native,cells in zip((domain.previous,domain.current),(previous,current),(previous_cells,current_cells))]
    groups=[p[2] for p in prepared]
    cross_pairs=sum(len(rows)*len(groups[1][owner]) for owner,rows in groups[0].items())
    total_pairs=cross_pairs+sum(p[3] for p in prepared)
    if total_pairs>max_pair_tests:
        raise CurvedHphiComparisonBudgetExceeded('curved Hphi common partition exceeds max_pair_tests')
    triangles=[];covered=[defaultdict(F),defaultdict(F)];areas=defaultdict(F)
    for owner in range(len(domain.previous.cell_nodes)):
        for old,a in groups[0][owner]:
            for new,b in groups[1][owner]:
                polygon=_clip(a,b)
                if _area(polygon)==0:continue
                polygon=[p for i,p in enumerate(polygon) if _cross(polygon[i-1],p,polygon[(i+1)%len(polygon)])!=0]
                start=min(range(len(polygon)),key=lambda i:polygon[i]);polygon=polygon[start:]+polygon[:start]
                for i in range(1,len(polygon)-1):
                    vertices=(polygon[0],polygon[i],polygon[i+1]);area=_area(vertices)
                    if area<=0:raise ValueError('curved Hphi common triangle has nonpositive orientation')
                    if len(triangles)>=max_triangles:
                        raise CurvedHphiComparisonBudgetExceeded('curved Hphi common intersections exceed max_triangles')
                    triangles.append((owner,vertices,old,new,(a,b)))
                    covered[0][old]+=area;covered[1][new]+=area;areas[owner]+=area
    for side,(_,charts,_,_,_) in enumerate(prepared):
        if any(covered[side][i]!=_area(vertices) for i,(_,vertices) in enumerate(charts)):
            raise ValueError('common partition does not exactly cover every native cell')
    if any(areas[i]!=F(1,2) for i in range(len(domain.previous.cell_nodes))):
        raise ValueError('common partition does not exactly cover every base cell')
    triangles.sort(key=lambda t:(t[0],t[1]))
    report=dict(status='GEOMETRY_VERIFIED',mapping=domain.mapping,triangle_count=len(triangles),
        pair_tests=total_pairs,boundary_components=domain.previous.validation['boundary_components'],
        axis_connected=isinstance(domain.previous.base_mesh,AxisConnectedMesh),
        base_reference_areas=[_encode(areas[i]) for i in range(len(domain.previous.cell_nodes))],
        native_cell_reference_coverage=[[_encode(covered[s][i]) for i in range(len(p[1]))] for s,p in enumerate(prepared)],
        area_m2=[g.area_m2 for g in (domain.previous,domain.current)],
        volume_m3=[g.volume_m3 for g in (domain.previous,domain.current)],
        native_restriction_policy=domain.restriction_policy,
        exact_native_restrictions=not any(value for p in prepared for row in p[4] for value in row),
        native_coordinate_error_bounds_m=[p[4] for p in prepared],
        maximum_native_coordinate_error_bound_m=max(value for p in prepared for row in p[4] for value in row),
        roundoff_coordinate_epsilon_factor=8 if domain.restriction_policy!='exact' else 0,
        maximum_roundoff_cell_extent_epsilon_factor=512,
        triangles=[dict(base_cell=o,reference_vertices=_vertices(v),previous_cell=a,current_cell=b) for o,v,a,b,_ in triangles],
        scope='complete declared quadratic reference domains and rational chart coverage; native coefficient equality or explicitly bounded binary64 roundoff; not field identity, quadrature accuracy or a discretization error bound')
    return CurvedHphiComparison(domain,tuple(p[0] for p in prepared),tuple(triangles),report)

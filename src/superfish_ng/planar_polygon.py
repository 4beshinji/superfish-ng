# SPDX-License-Identifier: Apache-2.0
"""Explicit single-polygon Cartesian cutoff case and point location."""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from .config import keys, positive, integer
from .planar_mesh import PlanarMesh, _orient


@dataclass(frozen=True, eq=False)
class PlanarPolygonCase:
    mesh: PlanarMesh
    polarization: str = 'te'
    element_order: int = 2
    modes: int = 4
    normalization_j_per_m: float = 1.
    conductivity_s_per_m: float = 5.8e7
    name: str = 'planar polygon cutoff'

    def __post_init__(self):
        if not isinstance(self.mesh,PlanarMesh):raise ValueError('polygon case requires an explicit PlanarMesh')
        object.__setattr__(self,'mesh',PlanarMesh.create(self.mesh.polygon_xy_m,self.mesh.points_xy_m,self.mesh.triangles))
        for name in ('normalization_j_per_m','conductivity_s_per_m'):
            object.__setattr__(self,name,positive(getattr(self,name),name))
        integer(self.element_order,'element_order');integer(self.modes,'modes')
        if self.element_order not in (1,2) or self.polarization not in ('te','tm'):
            raise ValueError('polygon cutoff requires P1/P2 and TE/TM')
        if not isinstance(self.name,str) or not self.name.strip():raise ValueError('planar name must be nonempty')

    @property
    def width_m(self):return float(np.ptp(self.mesh.points_xy_m[:,0]))

    @property
    def height_m(self):return float(np.ptp(self.mesh.points_xy_m[:,1]))

    def __eq__(self,other):return isinstance(other,PlanarPolygonCase) and self.to_dict()==other.to_dict()

    def to_dict(self):
        return dict(format='superfish_ng_planar_case',schema_version=2,name=self.name,
            model=dict(physics='rf_eigenmode',coordinates='cartesian',polarization=self.polarization,
                propagation_constant_per_m=0,material='vacuum',boundary='pec'),
            geometry=dict(type='polygon',vertices_xy_m=self.mesh.polygon_xy_m.tolist()),
            mesh=dict(points_xy_m=self.mesh.points_xy_m.tolist(),triangles=self.mesh.triangles.tolist(),element_order=self.element_order),
            modes=self.modes,rf=dict(stored_energy_j_per_m=self.normalization_j_per_m,conductivity_s_per_m=self.conductivity_s_per_m))

    @classmethod
    def from_dict(cls,data):
        required=['format','schema_version','name','model','geometry','mesh','rf','modes']
        keys(data,required,required,'planar polygon case')
        if data['format']!='superfish_ng_planar_case' or type(data['schema_version']) is not int or data['schema_version']!=2:
            raise ValueError('expected superfish_ng_planar_case schema_version 2 for polygon')
        model=data['model'];names=['physics','coordinates','polarization','propagation_constant_per_m','material','boundary']
        keys(model,names,names,'planar polygon model')
        for key,expected in [('physics','rf_eigenmode'),('coordinates','cartesian'),('material','vacuum'),('boundary','pec')]:
            if model[key]!=expected:raise ValueError(f'planar model.{key}: only {expected} is implemented')
        beta=model['propagation_constant_per_m']
        if type(beta) not in (int,float) or beta!=0:raise ValueError('planar cutoff requires propagation_constant_per_m=0')
        g=data['geometry'];keys(g,['type','vertices_xy_m'],['type','vertices_xy_m'],'polygon geometry')
        if g['type']!='polygon':raise ValueError('planar v2 requires a single simple PEC polygon')
        mesh=data['mesh'];names=['points_xy_m','triangles','element_order'];keys(mesh,names,names,'explicit polygon mesh')
        rf=data['rf'];names=['stored_energy_j_per_m','conductivity_s_per_m'];keys(rf,names,names,'polygon rf')
        geometry=PlanarMesh.create(g['vertices_xy_m'],mesh['points_xy_m'],mesh['triangles'])
        return cls(geometry,model['polarization'],mesh['element_order'],data['modes'],
            rf['stored_energy_j_per_m'],rf['conductivity_s_per_m'],data['name'])


def planar_case_from_dict(data):
    from .planar import PlanarCase
    if isinstance(data,dict) and type(data.get('schema_version')) is int and data['schema_version']==2:
        return PlanarPolygonCase.from_dict(data)
    return PlanarCase.from_dict(data)


def load_planar_case(path):
    from .project import parse_json
    return planar_case_from_dict(parse_json(Path(path).read_text(encoding='utf-8')))


class PolygonLocator:
    """Deterministic lowest-cell one-sided location on the actual xy triangles.

    No barycentric tolerance admits an exterior point through a thin cell.
    Exact binary64 orientation handles points on shared edges and vertices.
    """
    def __init__(self,space):
        self.vertices=space.points_xy_m[space.triangles]
        self.low=self.vertices.min(axis=1);self.high=self.vertices.max(axis=1)

    def locate(self,points):
        cells=[];bary=[]
        for point in points:
            candidates=np.flatnonzero(np.all(point>=self.low,axis=1)&np.all(point<=self.high,axis=1))
            for cell in candidates:
                vertices=self.vertices[cell]
                if any(_orient(vertices[i],vertices[(i+1)%3],point)<0 for i in range(3)):continue
                a,b,c=vertices.astype(np.longdouble);p=point.astype(np.longdouble)
                u,v=b-a,c-a;offset=p-a
                determinant=u[0]*v[1]-u[1]*v[0]
                second=(offset[0]*v[1]-offset[1]*v[0])/determinant
                third=(u[0]*offset[1]-u[1]*offset[0])/determinant
                values=np.asarray([1-second-third,second,third],dtype=float)
                if not np.isfinite(values).all() or np.min(values)<-1e-12:
                    raise ValueError('polygon point location is numerically unresolved')
                cells.append(cell);bary.append(values);break
            else:raise ValueError('planar probe point is outside the declared polygon mesh')
        return np.asarray(cells,dtype=np.int64),np.asarray(bary,dtype=float).reshape(-1,3)

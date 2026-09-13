# SPDX-License-Identifier: Apache-2.0
"""Strict axis cell ownership for isotropic monotone B-H materials."""
from dataclasses import dataclass,field
from numbers import Integral
import numpy as np
from .config import keys
from .bh_curve import MonotoneBHCurve,_real_array
from .axis_magnetic_materials import AxisMagneticPartition
from .magnetic_materials import LinearMagneticMaterial,MagneticRegion
from .axis_connected_mesh import AxisConnectedMesh


@dataclass(frozen=True,eq=False)
class AxisBHPartition:
    mesh: AxisConnectedMesh
    materials: tuple
    regions: tuple
    cell_region_indices: np.ndarray=field(init=False)
    cell_material_indices: np.ndarray=field(init=False)
    interface_edges: np.ndarray=field(init=False)
    interface_cells: np.ndarray=field(init=False)
    interface_region_indices: np.ndarray=field(init=False)
    interface_material_definition_changes: np.ndarray=field(init=False)
    boundary_region_indices: np.ndarray=field(init=False)
    region_area_m2: np.ndarray=field(init=False)
    region_volume_m3: np.ndarray=field(init=False)
    region_axis_contact: np.ndarray=field(init=False)

    def __post_init__(self):
        if type(self.mesh) is not AxisConnectedMesh:raise ValueError('axis B-H materials require a straight AxisConnectedMesh')
        for name,cls in (('materials',MonotoneBHCurve),('regions',MagneticRegion)):
            values=getattr(self,name)
            if not isinstance(values,(list,tuple)) or not values or any(type(v) is not cls for v in values):raise ValueError('axis B-H '+name+' requires explicit '+cls.__name__+' values')
            object.__setattr__(self,name,tuple(cls.from_dict(v.to_dict()) for v in values))
        # Unit coefficients provide neutral topology/coverage checks only.
        # Every physical H and tangent is evaluated from the declared B-H table.
        checked=AxisMagneticPartition(self.mesh,[LinearMagneticMaterial(m.id,1.) for m in self.materials],self.regions)
        object.__setattr__(self,'mesh',checked.mesh)
        for name in ('cell_region_indices','interface_edges','interface_cells','interface_region_indices','boundary_region_indices','region_area_m2','region_volume_m3'):object.__setattr__(self,name,getattr(checked,name))
        axis_cells=np.any(self.mesh.points_rz_m[self.mesh.triangles,0]==0.,axis=1)
        contacts=np.array([bool(np.any(axis_cells[list(v.cell_indices)])) for v in self.regions]);contacts.setflags(write=False);object.__setattr__(self,'region_axis_contact',contacts)
        indices={m.id:i for i,m in enumerate(self.materials)};by_region=np.array([indices[v.material] for v in self.regions],dtype=np.int64);owners=by_region[self.cell_region_indices]
        definitions=[(m.b_t,m.h_a_per_m) for m in self.materials]
        changes=np.array([definitions[owners[a]]!=definitions[owners[b]] for a,b in self.interface_cells],dtype=bool)
        for name,value in dict(cell_material_indices=owners,interface_material_definition_changes=changes).items():value.setflags(write=False);object.__setattr__(self,name,value)

    def evaluate_cells(self,cell_indices,b_t):
        try:raw=np.asarray(cell_indices,dtype=object)
        except (ValueError,TypeError) as exc:raise ValueError('B-H cell indices require a one-dimensional integer sequence') from exc
        if raw.ndim!=1 or not raw.size or any(not isinstance(v,Integral) or isinstance(v,(bool,np.bool_)) for v in raw):raise ValueError('B-H cell indices require explicit integers')
        if any(v<0 or v>=len(self.mesh.triangles) for v in raw):raise ValueError('B-H cell index is outside the mesh')
        cells=np.asarray(raw,dtype=np.int64);b=_real_array(b_t,'axis cell B [T]')
        if b.shape!=(len(cells),2):raise ValueError('axis cell B must have shape (number of cells, 2)')
        owners=self.cell_material_indices[cells];result={}
        for i,material in enumerate(self.materials):
            mask=owners==i
            if not np.any(mask):continue
            state=material.evaluate_vectors(b[mask])
            for name,value in state.items():
                if name not in result:result[name]=np.empty((len(cells),*value.shape[1:]),dtype=value.dtype)
                result[name][mask]=value
        for value in result.values():value.setflags(write=False)
        return result

    def to_dict(self):
        return dict(format='superfish_ng_axis_bh_partition',schema_version=1,coordinates='axisymmetric_rz',azimuthal_model='isotropic_h_parallel_b_zero_azimuthal_field',
            geometry=dict(type='explicit_straight_axis_connected',outer_rz_m=self.mesh.outer_rz_m.tolist(),holes_rz_m=[h.tolist() for h in self.mesh.holes_rz_m],points_rz_m=self.mesh.points_rz_m.tolist(),triangles=self.mesh.triangles.tolist()),
            materials=[m.to_dict() for m in self.materials],regions=[v.to_dict() for v in self.regions])

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','coordinates','azimuthal_model','geometry','materials','regions'];keys(data,names,names,'axis B-H partition')
        if data['format']!='superfish_ng_axis_bh_partition' or type(data['schema_version']) is not int or data['schema_version']!=1 or data['coordinates']!='axisymmetric_rz':raise ValueError('expected superfish_ng_axis_bh_partition version 1, axisymmetric_rz')
        if data['azimuthal_model']!='isotropic_h_parallel_b_zero_azimuthal_field':raise ValueError('axis B-H requires isotropic H parallel to B and zero azimuthal B/H')
        g=data['geometry'];names=['type','outer_rz_m','holes_rz_m','points_rz_m','triangles'];keys(g,names,names,'axis B-H geometry')
        if g['type']!='explicit_straight_axis_connected':raise ValueError('axis B-H geometry requires a straight axis-connected domain')
        if type(data['materials']) is not list or type(data['regions']) is not list:raise ValueError('B-H materials and regions require JSON lists')
        mesh=AxisConnectedMesh(**{name:g[name] for name in names[1:]})
        return cls(mesh,[MonotoneBHCurve.from_dict(v) for v in data['materials']],[MagneticRegion.from_dict(v) for v in data['regions']])

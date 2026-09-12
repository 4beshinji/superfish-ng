# SPDX-License-Identifier: Apache-2.0
"""Explicit positive magnetic materials on straight domains with strictly r>0."""
from dataclasses import dataclass,field
import numpy as np
from .config import keys
from .magnetic_materials import LinearMagneticMaterial,MagneticRegion
from .rf_materials import LinearRFMaterial,RFMaterialRegion,RFMaterialPartition
from .meridional_mesh import MeridionalMesh
from .constants import MU0


@dataclass(frozen=True,eq=False)
class OffAxisMagneticPartition:
    mesh: MeridionalMesh
    materials: tuple
    regions: tuple
    mu_r: np.ndarray=field(init=False)
    reluctivity_m_per_h: np.ndarray=field(init=False)
    cell_region_indices: np.ndarray=field(init=False)
    interface_edges: np.ndarray=field(init=False)
    interface_cells: np.ndarray=field(init=False)
    interface_region_indices: np.ndarray=field(init=False)
    interface_coefficient_jumps: np.ndarray=field(init=False)
    boundary_region_indices: np.ndarray=field(init=False)
    region_area_m2: np.ndarray=field(init=False)
    region_volume_m3: np.ndarray=field(init=False)

    def __post_init__(self):
        if type(self.mesh) is not MeridionalMesh:
            raise ValueError('off-axis magnetic materials require a straight MeridionalMesh; axis-connected and curved geometry require different spaces')
        for name,cls in (('materials',LinearMagneticMaterial),('regions',MagneticRegion)):
            values=getattr(self,name)
            if not isinstance(values,(list,tuple)) or not values or any(type(v) is not cls for v in values):
                raise ValueError('off-axis magnetic '+name+' requires explicit '+cls.__name__+' values')
            object.__setattr__(self,name,tuple(cls.from_dict(v.to_dict()) for v in values))
        # Only topology, ownership, SI measures and real mu are shared. No RF
        # operator, phasor, frequency or boundary condition enters these forms.
        try:
            checked=RFMaterialPartition(self.mesh,[LinearRFMaterial(m.id,1.,m.mu_r) for m in self.materials],
                [RFMaterialRegion(r.id,r.material,r.cell_indices) for r in self.regions])
        except ValueError as exc:raise ValueError(str(exc).replace('RF material','off-axis magnetic material')) from exc
        object.__setattr__(self,'mesh',checked.mesh)
        for name in ('mu_r','cell_region_indices','interface_edges','interface_cells','interface_region_indices',
                     'interface_coefficient_jumps','boundary_region_indices','region_area_m2','region_volume_m3'):
            object.__setattr__(self,name,getattr(checked,name))
        with np.errstate(over='ignore',under='ignore',divide='ignore',invalid='ignore'):reluctivity=(1./MU0)/self.mu_r
        if not np.isfinite(reluctivity).all() or np.any(reluctivity<=0):raise ValueError('magnetic reluctivity must remain finite and positive in SI')
        reluctivity.setflags(write=False);object.__setattr__(self,'reluctivity_m_per_h',reluctivity)

    def to_dict(self):
        return dict(format='superfish_ng_off_axis_magnetic_partition',schema_version=1,coordinates='axisymmetric_rz',
            geometry=dict(type='explicit_straight_off_axis',outer_rz_m=self.mesh.outer_rz_m.tolist(),
                holes_rz_m=[hole.tolist() for hole in self.mesh.holes_rz_m],points_rz_m=self.mesh.points_rz_m.tolist(),
                triangles=self.mesh.triangles.tolist()),
            materials=[m.to_dict() for m in self.materials],regions=[r.to_dict() for r in self.regions])

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','coordinates','geometry','materials','regions'];keys(data,names,names,'off-axis magnetic partition')
        if (data['format']!='superfish_ng_off_axis_magnetic_partition' or type(data['schema_version']) is not int
            or data['schema_version']!=1 or data['coordinates']!='axisymmetric_rz'):
            raise ValueError('expected superfish_ng_off_axis_magnetic_partition version 1, axisymmetric_rz coordinates')
        geometry=data['geometry'];names=['type','outer_rz_m','holes_rz_m','points_rz_m','triangles'];keys(geometry,names,names,'off-axis magnetic geometry')
        if geometry['type']!='explicit_straight_off_axis':
            raise ValueError('off-axis magnetic partition requires explicit straight off-axis geometry')
        if type(data['materials']) is not list or type(data['regions']) is not list:raise ValueError('off-axis magnetic materials and regions must be JSON lists')
        mesh=MeridionalMesh(**{name:geometry[name] for name in names[1:]})
        return cls(mesh,[LinearMagneticMaterial.from_dict(m) for m in data['materials']],
                   [MagneticRegion.from_dict(r) for r in data['regions']])

# SPDX-License-Identifier: Apache-2.0
"""Strict independent Cartesian parameter sweeps; mode ranks are not identities."""
from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
import json
from .config import keys, positive
from .planar_project import PlanarProject
from .project import parse_json

PARAMETERS = ('uniform_scale', '/case/geometry/width_m', '/case/geometry/height_m',
              '/case/rf/stored_energy_j_per_m', '/case/rf/conductivity_s_per_m')

@dataclass(frozen=True)
class PlanarStudy:
    project: PlanarProject
    parameter: str
    values: tuple

    def __post_init__(self):
        if not isinstance(self.project, PlanarProject):
            raise ValueError('planar study requires a dedicated PlanarProject')
        object.__setattr__(self, 'project', PlanarProject.from_dict(self.project.to_dict()))
        if self.parameter not in PARAMETERS:
            raise ValueError('planar sweep parameter must be uniform_scale, rectangle width/height, stored energy per metre or wall conductivity')
        if not isinstance(self.values, (list, tuple)) or len(self.values)<2:
            raise ValueError('planar sweep requires at least two finite positive values')
        object.__setattr__(self, 'values', tuple(positive(value, 'planar sweep value') for value in self.values))
        # Validate every derived Case and mesh before any solver or output allocation.
        self.projects()

    def to_dict(self):
        return dict(format='superfish_ng_planar_study',study_version=1,kind='sweep',
                    project=self.project.to_dict(),parameter=self.parameter,values=list(self.values))

    @classmethod
    def from_dict(cls, data):
        fields=['format','study_version','kind','project','parameter','values']
        keys(data,fields,fields,'planar study')
        if data['format']!='superfish_ng_planar_study' or type(data['study_version']) is not int or data['study_version']!=1:
            raise ValueError('expected superfish_ng_planar_study study_version 1')
        if data['kind']!='sweep':
            raise ValueError('only independent planar sweep is implemented; convergence and tracking require separate operations')
        if not isinstance(data['values'],list):raise ValueError('planar study values must be a JSON array')
        return cls(PlanarProject.from_dict(data['project']),data['parameter'],data['values'])

    @classmethod
    def load(cls, path):
        return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def save(self, path):
        with Path(path).open('x',encoding='utf-8') as stream:
            json.dump(self.to_dict(),stream,indent=2,ensure_ascii=False,allow_nan=False)
            stream.write('\n')

    def projects(self):
        projects=[]
        for value in self.values:
            raw=deepcopy(self.project.to_dict());case=raw['case']
            if self.parameter=='uniform_scale':
                if case['schema_version']==1:
                    case['geometry']['width_m']*=value;case['geometry']['height_m']*=value
                else:
                    for points in (case['geometry']['vertices_xy_m'],case['mesh']['points_xy_m']):
                        for point in points:
                            point[0]*=value;point[1]*=value
            elif self.parameter.startswith('/case/geometry/'):
                if case['schema_version']!=1:
                    raise ValueError('rectangle width/height sweeps cannot rewrite an explicit polygon mesh; use uniform_scale or a declared transformation')
                case['geometry'][self.parameter.rsplit('/',1)[-1]]=value
            else:
                case['rf'][self.parameter.rsplit('/',1)[-1]]=value
            projects.append(PlanarProject.from_dict(raw))
        return tuple(projects)

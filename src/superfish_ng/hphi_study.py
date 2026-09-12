# SPDX-License-Identifier: Apache-2.0
"""Strict independent Hphi parameter sweeps; mode ranks are not identities."""
from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
import json
from .config import keys, positive
from .hphi_project import HphiProject
from .project import parse_json

PARAMETERS = ('uniform_scale', '/case/geometry/inner_radius_m', '/case/geometry/outer_radius_m', '/case/geometry/length_m',
              '/case/rf/stored_energy_j', '/case/rf/conductivity_s_per_m')

@dataclass(frozen=True)
class HphiStudy:
    project: HphiProject
    parameter: str
    values: tuple

    def __post_init__(self):
        if not isinstance(self.project, HphiProject):
            raise ValueError('hphi study requires a dedicated HphiProject')
        object.__setattr__(self, 'project', HphiProject.from_dict(self.project.to_dict()))
        if self.parameter not in PARAMETERS:
            raise ValueError('hphi sweep parameter must be uniform_scale, closed coaxial inner/outer radius/length, total stored energy or wall conductivity')
        if not isinstance(self.values, (list, tuple)) or len(self.values)<2:
            raise ValueError('hphi sweep requires at least two finite positive values')
        object.__setattr__(self, 'values', tuple(positive(value, 'hphi sweep value') for value in self.values))
        # Validate every derived Case and mesh before any solver or output allocation.
        self.projects()

    def to_dict(self):
        return dict(format='superfish_ng_hphi_study',study_version=1,kind='sweep',
                    project=self.project.to_dict(),parameter=self.parameter,values=list(self.values))

    @classmethod
    def from_dict(cls, data):
        fields=['format','study_version','kind','project','parameter','values']
        keys(data,fields,fields,'hphi study')
        if data['format']!='superfish_ng_hphi_study' or type(data['study_version']) is not int or data['study_version']!=1:
            raise ValueError('expected superfish_ng_hphi_study study_version 1')
        if data['kind']!='sweep':
            raise ValueError('only independent hphi sweep is implemented; convergence and tracking require separate operations')
        if not isinstance(data['values'],list):raise ValueError('hphi study values must be a JSON array')
        return cls(HphiProject.from_dict(data['project']),data['parameter'],data['values'])

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
            cylinder=case['format']=='superfish_ng_coaxial_case'
            if self.parameter=='uniform_scale':
                if cylinder:
                    for key in ('inner_radius_m','outer_radius_m','length_m'):case['geometry'][key]*=value
                else:
                    mesh=case['mesh']
                    for points in (mesh['outer_rz_m'],*mesh['holes_rz_m'],mesh['points_rz_m']):
                        for point in points:
                            point[0]*=value;point[1]*=value
                    if case['format']=='superfish_ng_axis_hphi_case' and case['acceleration'] is not None:
                        for key in ('z_start_m','z_end_m','phase_origin_m'):case['acceleration'][key]*=value
            elif self.parameter.startswith('/case/geometry/'):
                if not cylinder:
                    raise ValueError('coaxial dimension sweeps cannot rewrite an explicit Hphi mesh; use uniform_scale or another explicitly supported parameter')
                case['geometry'][self.parameter.rsplit('/',1)[-1]]=value
            else:
                case['rf'][self.parameter.rsplit('/',1)[-1]]=value
            projects.append(HphiProject.from_dict(raw))
        return tuple(projects)

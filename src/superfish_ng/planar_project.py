# SPDX-License-Identifier: Apache-2.0
"""Portable editing document for explicit Cartesian cutoff cases."""
from dataclasses import dataclass
import json
from pathlib import Path
from .config import keys
from .project import parse_json
from .planar import PlanarCase
from .planar_polygon import PlanarPolygonCase, planar_case_from_dict


@dataclass(frozen=True)
class PlanarProject:
    case: PlanarCase | PlanarPolygonCase
    display_length_unit: str = 'mm'

    def __post_init__(self):
        if not isinstance(self.case,(PlanarCase,PlanarPolygonCase)):
            raise ValueError('PlanarProject requires a dedicated Cartesian cutoff case')
        object.__setattr__(self,'case',planar_case_from_dict(self.case.to_dict()))
        if self.display_length_unit not in ('m','mm'):
            raise ValueError('planar display_length_unit must be m or mm; saved physics is SI')

    @classmethod
    def from_dict(cls,data):
        names=['format','project_version','case','display_length_unit']
        keys(data,names,names,'planar project')
        if data['format']!='superfish_ng_planar_project' or type(data['project_version']) is not int or data['project_version']!=1:
            raise ValueError('expected superfish_ng_planar_project project_version 1')
        return cls(planar_case_from_dict(data['case']),data['display_length_unit'])

    @classmethod
    def load(cls,path):return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def to_dict(self):
        return dict(format='superfish_ng_planar_project',project_version=1,
            case=self.case.to_dict(),display_length_unit=self.display_length_unit)

    def dumps(self):return json.dumps(self.to_dict(),ensure_ascii=False,indent=2,allow_nan=False)+'\n'

    def save(self,path):
        with Path(path).open('x',encoding='utf-8') as stream:stream.write(self.dumps())

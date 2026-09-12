# SPDX-License-Identifier: Apache-2.0
"""Portable Project for explicit closed coaxial and meridional Hphi cases."""
from dataclasses import dataclass
import json
from pathlib import Path
from .config import keys
from .coaxial import CoaxialCase
from .hphi_mesh import HphiMeshCase
from .axis_hphi import AxisHphiCase
from .hphi_native import hphi_case_from_dict
from .project import parse_json


@dataclass(frozen=True,eq=False)
class HphiProject:
    case: CoaxialCase | HphiMeshCase | AxisHphiCase
    display_length_unit: str = 'mm'

    def __post_init__(self):
        if not isinstance(self.case,(CoaxialCase,HphiMeshCase,AxisHphiCase)):
            raise ValueError('HphiProject requires a dedicated coaxial, positive-radius mesh or regular-axis Hphi case')
        object.__setattr__(self,'case',hphi_case_from_dict(self.case.to_dict()))
        if self.display_length_unit not in ('m','mm'):
            raise ValueError('Hphi display_length_unit must be m or mm; saved physics is SI')

    def __eq__(self,other):
        if not isinstance(other,HphiProject): return NotImplemented
        return self.to_dict() == other.to_dict()

    __hash__ = None

    @classmethod
    def from_dict(cls,data):
        names=['format','project_version','case','display_length_unit'];keys(data,names,names,'Hphi Project')
        if data['format'] != 'superfish_ng_hphi_project' or type(data['project_version']) is not int or data['project_version'] != 1:
            raise ValueError('expected superfish_ng_hphi_project project_version 1')
        return cls(hphi_case_from_dict(data['case']),data['display_length_unit'])

    def to_dict(self):
        return dict(format='superfish_ng_hphi_project',project_version=1,case=self.case.to_dict(),display_length_unit=self.display_length_unit)

    @classmethod
    def load(cls,path): return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))

    def dumps(self): return json.dumps(self.to_dict(),ensure_ascii=False,indent=2,allow_nan=False)+'\n'

    def save(self,path):
        with Path(path).open('x',encoding='utf-8') as stream: stream.write(self.dumps())

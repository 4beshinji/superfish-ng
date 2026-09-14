# SPDX-License-Identifier: Apache-2.0
"""Immutable, versioned topological choices for a marked quadratic refinement."""
from dataclasses import dataclass
import hashlib
import json
import re
from .config import integer,keys


def curved_topology_digest(space):
    """Bind choices to numbered P2 connectivity and labelled boundary ownership.

    Coordinates and curve fractions are intentionally not part of this digest:
    a declared geometry transformation may move the same topological entities.
    This is not a certificate of physical correspondence between arbitrary meshes.
    """
    g=space.geometry
    document={key:getattr(g,key).tolist() for key in ('cell_nodes','boundary_nodes','boundary_curve_indices')}
    document['boundary_tags']=space.boundary_tags.tolist()
    return hashlib.sha256(json.dumps(document,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class CurvedSplitPattern:
    parent_topology_sha256: str
    marked_cells: tuple[int,...]
    split_edges: tuple[tuple[int,int],...]
    transition_diagonals: tuple[tuple[int,int],...]

    def __post_init__(self):
        if type(self.parent_topology_sha256) is not str or re.fullmatch('[0-9a-f]{64}',self.parent_topology_sha256) is None:
            raise ValueError('split pattern parent_topology_sha256 must contain 64 lowercase hex digits')
        if type(self.marked_cells) is not tuple or not self.marked_cells:
            raise ValueError('split pattern marked_cells must be a nonempty immutable tuple')
        for cell in self.marked_cells:integer(cell,'split pattern marked cell',minimum=0)
        if tuple(sorted(set(self.marked_cells)))!=self.marked_cells:
            raise ValueError('split pattern marked_cells must be sorted and unique')
        for name in ('split_edges','transition_diagonals'):
            rows=getattr(self,name)
            if type(rows) is not tuple or any(type(row) is not tuple or len(row)!=2 for row in rows):
                raise ValueError(f'split pattern {name} must contain immutable pairs')
            for a,b in rows:
                integer(a,f'split pattern {name} entry',minimum=0);integer(b,f'split pattern {name} entry',minimum=0)
                if (name=='split_edges' and a>=b) or (name=='transition_diagonals' and b not in (0,1)):
                    raise ValueError(f'invalid split pattern {name} pair')
            if tuple(sorted(set(rows)))!=rows or (name=='transition_diagonals' and len({a for a,_ in rows})!=len(rows)):
                raise ValueError(f'split pattern {name} must be sorted and unique')
        if not self.split_edges:raise ValueError('split pattern split_edges must be nonempty')

    @classmethod
    def from_dict(cls,data):
        names=('schema_version','parent_topology_sha256','marked_cells','split_edges','transition_diagonals')
        keys(data,names,names,'curved split pattern')
        if type(data['schema_version']) is not int or data['schema_version']!=1:
            raise ValueError('curved split pattern schema_version must be 1')
        for name in ('marked_cells','split_edges','transition_diagonals'):
            if type(data[name]) is not list:raise ValueError(f'split pattern {name} must be an array')
        for name in ('split_edges','transition_diagonals'):
            if any(type(row) is not list for row in data[name]):raise ValueError(f'split pattern {name} must contain arrays')
        return cls(data['parent_topology_sha256'],tuple(data['marked_cells']),tuple(map(tuple,data['split_edges'])),tuple(map(tuple,data['transition_diagonals'])))

    def to_dict(self):
        return dict(schema_version=1,parent_topology_sha256=self.parent_topology_sha256,marked_cells=list(self.marked_cells),
                    split_edges=list(map(list,self.split_edges)),transition_diagonals=list(map(list,self.transition_diagonals)))

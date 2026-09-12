# SPDX-License-Identifier: Apache-2.0
"""Explicit dispatch for explicit positive-radius and regular-axis Hphi native types."""
from pathlib import Path
from .coaxial import CoaxialCase, solve_coaxial
from .coaxial_saved import FILES, save_coaxial_run, read_coaxial_run, coaxial_result
from .hphi_mesh import HphiMeshCase, HphiMeshSolution, solve_hphi_mesh
from .hphi_mesh_saved import save_hphi_mesh_run, read_hphi_mesh_run, hphi_mesh_result
from .axis_hphi import AxisHphiCase, AxisHphiSolution, solve_axis_hphi
from .axis_hphi_saved import save_axis_hphi_run, read_axis_hphi_run, axis_hphi_result
from .curved_hphi import CurvedHphiCase, CurvedHphiSolution, solve_curved_hphi
from .curved_hphi_saved import save_curved_hphi_run, read_curved_hphi_run, curved_hphi_result
from .material_hphi import MaterialHphiCase, MaterialHphiSolution, solve_material_hphi
from .material_hphi_saved import save_material_hphi_run, read_material_hphi_run, material_hphi_result
from .project import parse_json


def hphi_case_from_dict(data):
    if isinstance(data,dict):
        if data.get('format') == 'superfish_ng_material_hphi_case': return MaterialHphiCase.from_dict(data)
        if data.get('format') == 'superfish_ng_curved_hphi_case': return CurvedHphiCase.from_dict(data)
        if data.get('format') == 'superfish_ng_coaxial_case': return CoaxialCase.from_dict(data)
        if data.get('format') == 'superfish_ng_axis_hphi_case': return AxisHphiCase.from_dict(data)
        if data.get('format') == 'superfish_ng_hphi_mesh_case': return HphiMeshCase.from_dict(data)
    raise ValueError('expected a dedicated coaxial, positive-radius mesh, regular-axis or explicit curved Hphi mesh case')


def solve_hphi(case):
    if isinstance(case,MaterialHphiCase): return solve_material_hphi(case)
    if isinstance(case,CurvedHphiCase): return solve_curved_hphi(case)
    if isinstance(case,AxisHphiCase): return solve_axis_hphi(case)
    if isinstance(case,HphiMeshCase): return solve_hphi_mesh(case)
    if isinstance(case,CoaxialCase): return solve_coaxial(case)
    raise ValueError('unsupported Hphi case type')


def save_hphi_run(case,solution,directory):
    if isinstance(case,MaterialHphiCase): return save_material_hphi_run(case,solution,directory)
    if isinstance(case,CurvedHphiCase): return save_curved_hphi_run(case,solution,directory)
    if isinstance(case,AxisHphiCase): return save_axis_hphi_run(case,solution,directory)
    if isinstance(case,HphiMeshCase): return save_hphi_mesh_run(case,solution,directory)
    if isinstance(case,CoaxialCase): return save_coaxial_run(case,solution,directory)
    raise ValueError('unsupported Hphi case type')


def read_hphi_run(directory):
    data = parse_json((Path(directory)/'manifest.json').read_text(encoding='utf-8'))
    if isinstance(data,dict):
        if data.get('format') == 'superfish_ng_material_hphi_manifest': return read_material_hphi_run(directory)
        if data.get('format') == 'superfish_ng_curved_hphi_manifest': return read_curved_hphi_run(directory)
        if data.get('format') == 'superfish_ng_coaxial_manifest': return read_coaxial_run(directory)
        if data.get('format') == 'superfish_ng_axis_hphi_manifest': return read_axis_hphi_run(directory)
        if data.get('format') == 'superfish_ng_hphi_mesh_manifest': return read_hphi_mesh_run(directory)
    raise ValueError('expected a dedicated coaxial, positive-radius mesh, regular-axis or explicit curved Hphi native manifest')


def hphi_result(solution):
    if isinstance(solution,MaterialHphiSolution): return material_hphi_result(solution)
    if isinstance(solution,CurvedHphiSolution): return curved_hphi_result(solution)
    if isinstance(solution,AxisHphiSolution): return axis_hphi_result(solution)
    return hphi_mesh_result(solution) if isinstance(solution,HphiMeshSolution) else coaxial_result(solution)

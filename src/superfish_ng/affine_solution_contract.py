# SPDX-License-Identifier: Apache-2.0
"""Bind straight TM fields to their solve domain, roles and normalization.

This runtime contract does not change saved schema 1. Historical files are
checked against their actual mesh and volume fields, independently of hashes.
"""
from dataclasses import dataclass, replace
import json

import numpy as np

from .constants import EPS0, MU0, TAU
from .mesh_input import mesh_digest, mesh_from_dict, mesh_to_dict


def _physical_case(case, order):
    # solve_p2 historically accepts a P1 Case; its explicit P2 field order wins.
    if order==2 and case.element_order==1:case=replace(case,element_order=2)
    data=case.to_dict();data.pop('name',None);data.pop('schema_version',None)
    # Legacy v1 and an explicit v3 default vacuum model describe the same solve.
    # Acceleration overrides promote the latter without changing its physics.
    from .model import Model
    data.setdefault('model',Model().to_dict())
    for name in ('beta','conductivity_s_per_m','active_length_m','voltage_interval_m','phase_origin_m'):
        data['rf'].pop(name,None)
    return data


def _mesh_sha(solution):
    data=mesh_to_dict(solution.mesh)
    data.update(axis_nodes=solution.mesh.axis_nodes.tolist(),boundary_cells=solution.mesh.boundary_cells.tolist())
    if solution.element_order==2:
        for name in ('dof_points','cell_dofs','boundary_dofs','axis_dofs'):
            data[name]=getattr(solution.space,name).tolist()
    return mesh_digest(data)


@dataclass(frozen=True)
class AffineSolveContract:
    physical_case_json: str
    mesh_sha256: str
    mesh_origin: str
    reflection_source_json: str | None
    input_mesh_sha256: str | None


def bind_affine_solution(case, solution, *, origin):
    source=getattr(solution,'source_case',None)
    solution.solve_contract=AffineSolveContract(
        json.dumps(_physical_case(case,solution.element_order),sort_keys=True,allow_nan=False),
        _mesh_sha(solution),origin,
        None if source is None else json.dumps(source,sort_keys=True,allow_nan=False),
        None if solution.mesh_input is None else mesh_digest(solution.mesh_input))


def verify_affine_energy(case, u, frequencies, stiffness, mass):
    """Check peak-phasor electric and magnetic energy separately, never fit U."""
    omega=TAU*np.asarray(frequencies)
    magnetic=MU0*np.pi*np.sum(u*(mass@u),axis=0)/2
    electric=np.pi*np.sum(u*(stiffness@u),axis=0)/(2*EPS0*omega**2)
    for name,values in (('magnetic',magnetic),('electric',electric)):
        if not np.isfinite(values).all() or np.any(abs(values/(case.normalization_j/2)-1)>1e-7):
            raise ValueError(f'affine solution {name} energy differs from the declared normalization_j')


def verify_affine_solution(case, solution):
    contract=getattr(solution,'solve_contract',None)
    if not isinstance(contract,AffineSolveContract):
        raise ValueError('straight TM solution lacks its solve contract; use solve/solve_p2 or the verified saved reader')
    if _physical_case(case,solution.element_order)!=json.loads(contract.physical_case_json):
        raise ValueError('RF/save case differs from the affine solve domain, boundary roles, order or normalization')
    if _mesh_sha(solution)!=contract.mesh_sha256:
        raise ValueError('affine solution mesh/field space changed after its solve contract was captured')
    input_sha=None if solution.mesh_input is None else mesh_digest(solution.mesh_input)
    if input_sha!=contract.input_mesh_sha256:
        raise ValueError('affine input mesh declaration differs from its solve contract')
    source=getattr(solution,'source_case',None)
    if source!=(None if contract.reflection_source_json is None else json.loads(contract.reflection_source_json)):
        raise ValueError('affine reflection source differs from its solve contract')
    verify_affine_energy(case,solution.u,solution.frequencies_hz,solution.stiffness,solution.mass)
    # Case validation alone is insufficient when its length came from another domain.
    _,(a,b),_=case.acceleration_parameters
    z=solution.mesh.points[solution.mesh.axis_nodes,1]
    if not z[0]<=a<b<=z[-1]:raise ValueError('voltage interval lies outside the actual affine axis domain')


def verify_affine_saved_domain(case, mesh, results):
    imported=mesh_from_dict(case,mesh_to_dict(mesh))
    for name in ('boundary_cells','axis_nodes'):
        if not np.array_equal(getattr(imported,name),getattr(mesh,name)):
            raise ValueError(f'saved affine {name} differs from its physical boundary roles')
    if 'reflection_source_case' in results:
        from .config import Case
        from .symmetry import reflected_case
        source=Case.from_dict(results['reflection_source_case'])
        expected=reflected_case(source)
        if _physical_case(case,case.element_order)!=_physical_case(expected,case.element_order):
            raise ValueError('saved reflected domain/normalization differs from its declared half-domain source')
        return 'reflection'
    if 'input_sha256' in results['mesh']:return 'external'
    from .mesh import make_mesh
    generated=make_mesh(case)
    for name in ('points','triangles','boundary_edges','boundary_tags','boundary_cells','axis_nodes'):
        if not np.array_equal(getattr(mesh,name),getattr(generated,name)):
            raise ValueError(f'saved generated affine {name} differs from the declared Case mesh')
    return 'generated'

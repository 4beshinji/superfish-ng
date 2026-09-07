# SPDX-License-Identifier: Apache-2.0
"""Portable curved fields; revalidate geometry and eigenpairs without a new solve."""
import csv
import hashlib
import json
import platform
import numpy as np
import scipy
from . import __version__
from .constants import C0, EPS0, MU0, TAU
from .curved_solution import CurvedSolution
from .curved_space import case_curved_space
from .curved_fem import assemble_curved
from .curved_rf import quantities_curved, surface_peak_contract
from .mesh_input import mesh_from_dict, mesh_digest
from .curved_corners import classify_curve_joins
from .curved_reflection import (reflect_curved_space, reflected_case, reflection_contract,
                                DIRECT_CONSTRUCTION, REFLECTED_CONSTRUCTION)


def geometry_arrays(space):
    geometry = space.geometry
    names = ['points_rz_m', 'cell_nodes', 'boundary_nodes', 'boundary_curve_indices', 'boundary_parameters']
    if hasattr(geometry, 'node_displacements_m'):
        names.append('node_displacements_m')
    return {**{name: getattr(geometry, name) for name in names},
            **{name: getattr(space, name) for name in
               ('boundary_tags', 'axis_dofs', 'constrained_dofs')}}


def field_space(solution):
    result = dict(element_order=2, geometry_order=2, basis='quadratic Lagrange u=Hphi/r',
                dofs=len(solution.u), quadrature_order=solution.quadrature_order)
    if solution.case.curved_refinement_levels:
        result["curved_refinement_levels"] = solution.case.curved_refinement_levels
    return result


def write_curved_run(case, solution, directory):
    from .io import write_vtk
    canonical = json.dumps(case.to_dict(), sort_keys=True, separators=(',', ':'), allow_nan=False)
    result = dict(schema_version=1, save_protocol_version=1, software_version=__version__,
                  case=case.to_dict(), case_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
                  environment=dict(python=platform.python_version(), numpy=np.__version__,
                                   scipy=scipy.__version__, platform=platform.platform()),
                  field_space=field_space(solution), surface_extrema=surface_peak_contract(),
                  surface_corner_diagnostics=classify_curve_joins(case.curved_contour),
                  field_construction=DIRECT_CONSTRUCTION,
                  mesh=dict(nodes=len(solution.u), triangles=len(solution.space.geometry.cell_nodes),
                            source='saved source chord mesh for curved reconstruction', input_file='mesh.json',
                            input_sha256=mesh_digest(solution.source_mesh_data)),
                  mass_orthogonality_error=solution.orthogonality_error,
                  geometry_approximation=dict(representation='quadratic interpolation of analytic primitives',
                                              geometry_order=2, chord_tolerance_m=case.curve_chord_tolerance_m,
                                              boundary_check=dict(solution.space.geometry.boundary_check),
                                              edge_check=dict(solution.space.edge_check)),
                  scope='vacuum; closed PEC or explicit symmetry subdomain; axis-connected m=0 TM',
                  conventions=dict(phasor='exp(+i omega t); H real, E=-i*exported_quadrature',
                                   energy='U=1/4 integral(eps|E|^2+mu|H|^2)dV',
                                   domain='energy and loss over input domain only; no automatic symmetry doubling',
                                   rq_accelerator='|Vacc|^2/(omega U)', rq_circuit='|Vacc|^2/(2 omega U)',
                                   voltage='Ez_quadrature axis integral over specified interval with exp(+i omega (z-phase_origin)/(beta c)); global -i omitted',
                                   vtk_coordinates='x=r, y=z, z=0; four straight display triangles per curved element; fields sampled at mapped reference subtriangle centres'),
                  modes=[quantities_curved(solution, i) for i in range(case.modes)])
    if case.curved_refinement_levels:
        result['geometry_approximation'].update(
            representation='restrictions of the initial quadratic geometry; no analytic curve reprojection',
            curved_refinement_levels=case.curved_refinement_levels,
            curve_parameters='ancestral intervals only; refined points lie on the initial quadratic boundary')
    if solution.reflection_source_case is not None:
        source = solution.reflection_source_case
        parent = case_curved_space(source, mesh_from_dict(source, solution.source_mesh_data))
        reflection = reflect_curved_space(source, parent)
        if reflected_case(source, reflection).to_dict() != case.to_dict():
            raise ValueError('reflected curved Case differs from source reconstruction')
        result['reflection'] = reflection_contract(source, reflection)
        result['field_construction'] = REFLECTED_CONSTRUCTION
        result['mesh']['source'] = 'saved half-domain source chord mesh for curved reflection reconstruction'
        result['geometry_approximation']['representation'] = 'reflection of the reconstructed half-domain quadratic geometry; no reprojection'
    for filename, document in (('case.json', case.to_dict()), ('results.json', result),
                               ('mesh.json', solution.source_mesh_data)):
        (directory/filename).write_text(json.dumps(document, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    np.savez_compressed(directory/'fields.npz', **geometry_arrays(solution.space),
                        u_a_per_m2=solution.u, frequencies_hz=solution.frequencies_hz)
    for i in range(case.modes):
        write_vtk(directory/f'mode_{i+1:03d}.vtk', solution, i)
        axis = solution.space.axis_dofs
        z = solution.space.geometry.points_rz_m[axis, 1]
        ez = 2*solution.u[axis, i]/(TAU*solution.frequencies_hz[i]*EPS0)
        np.savetxt(directory/f'axis_{i+1:03d}.csv', np.column_stack((z, ez)), delimiter=',',
                   header='z_m,Ez_quadrature_V_per_m', comments='')
    with (directory/'modes.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result['modes'][0]))
        writer.writeheader()
        writer.writerows(result['modes'])
    return result


def read_curved_run(directory, case, results):
    """Called after the common completion manifest and Case hash checks."""
    from .project import parse_json
    if not (directory/'save_protocol.json').is_file() or results.get('save_protocol_version') != 1:
        raise ValueError('curved fields require the save completion protocol')
    declaration = results.get('field_space')
    required = {'element_order', 'geometry_order', 'basis', 'dofs', 'quadrature_order'}
    if case.curved_refinement_levels:
        required.add('curved_refinement_levels')
        if (not isinstance(declaration, dict) or type(declaration.get('curved_refinement_levels')) is not int
                or declaration['curved_refinement_levels'] != case.curved_refinement_levels):
            raise ValueError('invalid saved curved refinement declaration')
    if (not isinstance(declaration, dict)
            or set(declaration) != required
            or any(type(declaration[key]) is not int for key in
                   ('element_order', 'geometry_order', 'dofs', 'quadrature_order'))
            or declaration['element_order'] != 2 or declaration['geometry_order'] != 2
            or declaration['quadrature_order'] != case.quadrature_order
            or declaration['dofs'] <= 0 or declaration['basis'] != 'quadratic Lagrange u=Hphi/r'):
        raise ValueError('invalid saved curved field space declaration')
    mesh_data = parse_json((directory/'mesh.json').read_text(encoding='utf-8'))
    if mesh_digest(mesh_data) != results['mesh'].get('input_sha256'):
        raise ValueError('saved curved source mesh hash differs')
    source = None
    reflection = None
    if 'reflection' in results:
        from .config import Case
        declaration = results['reflection']
        if not isinstance(declaration, dict) or not isinstance(declaration.get('source_case'), dict):
            raise ValueError('invalid saved curved reflection declaration')
        source = Case.from_dict(declaration['source_case'])
        if source.geometry_order != 2:
            raise ValueError('saved curved reflection requires quadratic source geometry')
        parent = case_curved_space(source, mesh_from_dict(source, mesh_data))
        reflection = reflect_curved_space(source, parent)
        if json.dumps(declaration, sort_keys=True, allow_nan=False) != json.dumps(reflection_contract(source, reflection), sort_keys=True, allow_nan=False):
            raise ValueError('invalid saved curved reflection declaration')
        if reflected_case(source, reflection).to_dict() != case.to_dict():
            raise ValueError('saved reflected curved Case differs from source reconstruction')
        space = reflection.space
    else:
        space = case_curved_space(case, mesh_from_dict(case, mesh_data))
    construction = REFLECTED_CONSTRUCTION if reflection is not None else DIRECT_CONSTRUCTION
    if results.get('field_construction') != construction:
        raise ValueError('invalid saved curved field construction')
    if (results['mesh'].get('nodes') != len(space.geometry.points_rz_m)
            or results['mesh'].get('triangles') != len(space.geometry.cell_nodes)):
        raise ValueError('saved curved mesh counts differ')
    expected = geometry_arrays(space)
    with np.load(directory/'fields.npz', allow_pickle=False) as data:
        if set(data.files) != set(expected) | {'u_a_per_m2', 'frequencies_hz'}:
            raise ValueError('invalid saved curved array set')
        for name, values in expected.items():
            actual = data[name]
            if actual.dtype.kind != values.dtype.kind or not np.array_equal(actual, values):
                raise ValueError(f'saved curved geometry {name} differs from reconstruction')
        u, frequencies = data['u_a_per_m2'], data['frequencies_hz']
    if (u.dtype.kind != 'f' or frequencies.dtype.kind != 'f'
            or u.shape != (len(space.geometry.points_rz_m), case.modes)
            or frequencies.shape != (case.modes,) or not np.isfinite(u).all()
            or not np.isfinite(frequencies).all() or np.any(frequencies <= 0)
            or np.any(np.diff(frequencies) < 0) or np.any(u[space.constrained_dofs] != 0)):
        raise ValueError('invalid saved curved coefficients, constraints or frequencies')
    if reflection is not None:
        half_u = u[:reflection.coefficient_map.shape[1]]
        if not np.array_equal(u, reflection.apply(half_u)):
            raise ValueError('saved curved coefficients violate reflection parity')
    k, m = assemble_curved(space, quadrature_order=case.quadrature_order)
    values = (TAU*frequencies/C0)**2
    gram = (MU0*np.pi/case.normalization_j)*(u.T@(m@u))
    error = float(np.max(abs(gram-np.eye(case.modes))))
    if error > 1e-7 or not np.isfinite(error):
        raise ValueError('saved curved normalization or orthogonality differs')
    free = np.setdiff1d(np.arange(len(u)), space.constrained_dofs)
    residuals = []
    for i, value in enumerate(values):
        ku, mu = (k@u[:, i])[free], (m@u[:, i])[free]
        residuals.append(np.linalg.norm(ku-value*mu)/(np.linalg.norm(ku)+value*np.linalg.norm(mu)))
    if not np.isfinite(residuals).all() or max(residuals) > 1e-7:
        raise ValueError('saved curved eigenpair residual exceeds 1e-7')
    peak_declaration = results.get('surface_extrema')
    if 'surface_extrema' in results:
        if not isinstance(peak_declaration, dict):
            raise ValueError('invalid saved curved surface extrema declaration')
        contract = surface_peak_contract(peak_declaration.get('version'))
        if json.dumps(peak_declaration, sort_keys=True, allow_nan=False) != json.dumps(contract, sort_keys=True, allow_nan=False):
            raise ValueError('invalid saved curved surface extrema declaration')
    if 'surface_corner_diagnostics' in results or (peak_declaration is not None and peak_declaration.get('version') == 2):
        if json.dumps(results.get('surface_corner_diagnostics'), sort_keys=True, allow_nan=False) != json.dumps(classify_curve_joins(case.curved_contour), sort_keys=True, allow_nan=False):
            raise ValueError('invalid saved analytic corner diagnostics')
    solution = CurvedSolution(case, space, k, m, values, frequencies, u,
                              np.asarray(residuals), error, case.quadrature_order, mesh_data, source)
    if results.get('field_space') != field_space(solution):
        raise ValueError('invalid saved curved field space declaration')
    if len(results.get('modes', [])) != case.modes:
        raise ValueError('invalid saved curved mode count')
    for i, saved in enumerate(results['modes']):
        expected_mode = quantities_curved(solution, i, include_surface_peaks=peak_declaration is not None)
        if set(saved) != set(expected_mode):
            raise ValueError('saved curved RF keys differ')
        for name, value in expected_mode.items():
            actual = saved[name]
            if isinstance(value, (int, float)):
                valid = (type(actual) in (int, float) and np.isfinite(actual)
                         and np.isclose(actual, value, rtol=1e-10, atol=1e-12))
            else:
                valid = actual == value
            if not valid:
                raise ValueError(f'saved curved RF {name} differs from coefficients')
    solution.results = results
    return solution

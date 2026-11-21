# SPDX-License-Identifier: Apache-2.0
"""Bounded independent geometry, Galerkin, native FEM and saved-field checks.

This verifies the fixed selection-charts-06 specification. Small native solves
are not an acceptance of continuous pillbox accuracy or physical peak accuracy.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests'), str(ROOT/'scripts')]
from superfish_ng import solve
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.curved_marked_refinement import refine_marked_curved_space
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.curved_selection_transfer import transfer_curved_cell_selection, replay_curved_selection_transfer
from superfish_ng.io import save_run
from superfish_ng.project import Project, parse_json
from superfish_ng.rf import quantities
from superfish_ng.saved import read_solution, export_radial_probe
from validate_curved_selection_transfer import moments, space
from validate_large_curved_mesh_selection import fingerprints, boundary_moments
from validate_reference_chart_fixture import reference_chart_fixture
from test_curved_piecewise_remesh_tracking import curved_comparison_fixture

EXAMPLES = ROOT/'examples/curved_selection_charts'
GEOMETRY_GATE = 3e-12
MATRIX_GATE = 1e-10
RITZ_GATE = 5e-11
SIMILARITY_GATE = 1e-10
SAVED_RF_GATE = 1e-12
FIELD_KEYS = ('Hphi_A_per_m', 'Er_quadrature_V_per_m', 'Ez_quadrature_V_per_m')


def relative(actual, expected):
    actual, expected = np.asarray(actual), np.asarray(expected)
    if not np.isfinite(actual).all() or not np.isfinite(expected).all():
        raise ValueError('nonfinite independent comparison')
    return float(np.max(np.abs(actual-expected)/np.maximum(np.abs(expected), 1e-300)))


def require(value, limit, label):
    if not np.isfinite(value) or value > limit:
        raise AssertionError(f'{label}: {value} exceeds unchanged gate {limit}')


def rectangle(scale, uniform=True):
    projects = [Project.load(EXAMPLES/name) for name in ('old-project.json', 'new-project.json')]
    steps = (Step('uniform'), Step('uniform')) if uniform else ()
    result = []
    for project in projects:
        mesh = deepcopy(project.mesh_data)
        mesh['points'] = (np.asarray(mesh['points'])*scale).tolist()
        # The independent rectangle contour preserves each original edge owner.
        curves = tuple(replace(curve, start_zr_m=tuple(float(x)*scale for x in curve.start_zr_m),
                               end_zr_m=tuple(float(x)*scale for x in curve.end_zr_m))
                       for curve in project.case.curved_contour.curves)
        case = replace(project.case, contour=None,
                       curved_contour=replace(project.case.curved_contour, curves=curves),
                       curved_refinement_levels=0, curved_refinement_steps=steps)
        result.append(replace(project, case=case, mesh_data=mesh))
    request = parse_json((EXAMPLES/'intersects.json').read_text())
    return result, request


def nonaffine(scale):
    cases, documents = curved_comparison_fixture(scale)
    maps = reference_chart_fixture(cases, documents, scale)
    projects = [Project(replace(case, curved_refinement_steps=(Step('uniform'), Step('marked', (side,), 1.))),
                        mesh_data=mapping['source_mesh'])
                for side, (case, mapping) in enumerate(zip(cases, maps))]
    assert [len(p.mesh_data['triangles']) for p in projects] == [26, 27]
    request = dict(schema_version=2, selected_cells=[0, 5, 6],
                   boundary_pairing='declared_reference_polylines', coverage_policy='intersects',
                   max_pair_tests=100000, max_triangles=10000,
                   reference_vertices=[mapping['reference_vertices'] for mapping in maps])
    return projects, request


def geometry(projects, request):
    before = [p.to_dict() for p in projects], deepcopy(request)
    cover = transfer_curved_cell_selection(*projects, request)
    inside = transfer_curved_cell_selection(*projects, dict(request, coverage_policy='contained'))
    assert replay_curved_selection_transfer(cover) == cover
    assert replay_curved_selection_transfer(inside) == inside
    assert before == ([p.to_dict() for p in projects], request)
    for prefix in ('previous', 'current'):
        assert cover['reference_partition'][prefix+'_areas'] == cover['reference_partition'][prefix+'_covered_areas']
    for row in cover['selection']['source_cell_area_checks']:
        assert Fraction(*row['source_reference_area']) == Fraction(*row['intersection_reference_area'])
    spaces = [space(p) for p in projects]
    def native(side, ids):
        g = spaces[side].geometry
        return sum((moments(g.points_rz_m[g.cell_nodes[i]]) for i in ids), np.zeros(3))
    source = native(0, request['selected_cells'])
    overlap = [np.zeros(3), np.zeros(3)]
    for row in cover['selection']['overlaps']:
        for side, prefix in enumerate(('previous', 'current')):
            g = spaces[side].geometry
            vertices = [[float(Fraction(*value)) for value in point[1:]] for point in row[prefix+'_barycentric']]
            overlap[side] += moments(g.points_rz_m[g.cell_nodes[row[prefix+'_cell']]], vertices)
    source_error = relative(overlap[0], source)
    require(source_error, GEOMETRY_GATE, 'old selected physical moments')
    covered = native(1, cover['selection']['selected_cells'])
    contained = native(1, inside['selection']['selected_cells'])
    assert np.all(contained <= overlap[1]*(1+GEOMETRY_GATE))
    assert np.all(overlap[1] <= covered*(1+GEOMETRY_GATE))
    whole = []
    for side, s in enumerate(spaces):
        values = native(side, range(len(s.geometry.cell_nodes)))
        green = boundary_moments(s)
        # Boundary edges retain the source contour orientation in (z,r), while
        # cell determinants use (r,z). Retain the signed Green results and
        # compare their positive physical measures, requiring one orientation.
        assert green['signed_area_m2']*green['signed_volume_m3'] > 0
        errors = [abs(values[0]/abs(green['signed_area_m2'])-1),
                  abs(values[1]/abs(green['signed_volume_m3'])-1)]
        require(max(errors), GEOMETRY_GATE, 'independent Green geometry')
        whole.append(dict(volume_moments=values.tolist(), boundary_green=green, relative_errors=errors))
    result = dict(status='PASS', source_native=source.tolist(), source_overlay=overlap[0].tolist(),
                  target_overlay=overlap[1].tolist(), target_cover=covered.tolist(), target_contained=contained.tolist(),
                  source_relative_difference=source_error, whole_domain=whole,
                  component_names=['area_m2', 'axisymmetric_volume_m3', 'Hphi_equals_r_mass_m5'],
                  rational_coverage='EXACT', physical_error_bound=None)
    return cover, inside, result


def field_scale(a, b):
    # Independent tensor Gauss-Duffy weights and physical P2 Jacobian. One sign
    # comes from the global H inner product and is shared by all E/H components.
    t, w = np.polynomial.legendre.leggauss(8)
    t, w = (t+1)/2, w/2
    s, v = np.meshgrid(t, t, indexing='ij')
    x, y = s.ravel(), ((1-s)*v).ravel()
    q = np.column_stack((x, y)); l = 1-x-y
    n = np.column_stack((l*(2*l-1), x*(2*x-1), y*(2*y-1), 4*l*x, 4*x*y, 4*y*l))
    dx = np.column_stack((1-4*l, 4*x-1, np.zeros_like(x), 4*(l-x), 4*y, -4*y))
    dy = np.column_stack((1-4*l, np.zeros_like(x), 4*y-1, -4*x, 4*x, 4*(l-y)))
    rule = (np.outer(w, w)*(1-s)).ravel()
    assert np.array_equal(a.space.geometry.cell_nodes, b.space.geometry.cell_nodes)
    norms = {key: 0. for key in FIELD_KEYS}; positive = norms.copy(); negative = norms.copy()
    product = 0.
    for cell, nodes in enumerate(a.space.geometry.cell_nodes):
        p = a.space.geometry.points_rz_m[nodes]
        dr, dz = dx@p, dy@p
        jac = dr[:, 0]*dz[:, 1]-dr[:, 1]*dz[:, 0]
        weights = rule*jac*2*np.pi*(n@p)[:, 0]
        assert np.all(weights > 0)
        old, new = a.fields_in_cell(cell, q), b.fields_in_cell(cell, q)
        for key in FIELD_KEYS:
            value, scaled = old[key], new[key]*2**1.5
            norms[key] += float(weights @ value**2)
            positive[key] += float(weights @ (value-scaled)**2)
            negative[key] += float(weights @ (value+scaled)**2)
        product += float(weights @ (old[FIELD_KEYS[0]]*new[FIELD_KEYS[0]]))
    sign = 1 if product > 0 else -1
    differences = positive if sign == 1 else negative
    errors = {key: float(np.sqrt(differences[key]/norms[key])) if norms[key] > 0
              else (0. if differences[key] == 0 else float('inf')) for key in FIELD_KEYS}
    require(max(errors.values()), SIMILARITY_GATE, 'global volume-weighted original E/H scale')
    return dict(status='PASS', single_sign=sign, field_relative_l2=errors,
                supplied_points=len(q)*len(a.space.geometry.cell_nodes), weights='independent P2 physical 3D volume')


def package_saved_projects(root):
    """Attach the actual original Project to verified native copies for GUI import.

    These are explicitly imported archives, never freshly executed jobs. Raw
    save_run output contains a Case and fields; its unmanaged GUI reader has
    no original Project document and reconstructs a default editing Project.
    """
    import shutil
    from superfish_ng.jobs import _prepare, _digest, _write_json, _state, read_job
    root = Path(root)
    result = []
    for scale in (1, 2):
        for name in ('previous', 'current', 'refined'):
            stage = f'scale-{scale}-{name}'
            source = root/stage
            project = Project.load(root/(stage+'-project.json'))
            native = read_solution(source)
            assert native.case.to_dict() == project.case.to_dict()
            assert native.source_mesh_data == project.mesh_data
            destination = root/'managed'/stage
            _prepare(project, destination)
            shutil.copytree(source, destination/'solution')
            files = {str(p.relative_to(destination)): _digest(p)
                     for p in destination.rglob('*') if p.is_file() and p.name != 'job.json'}
            _write_json(destination/'manifest.json', dict(manifest_version=1, files=files,
                        source_changed_during_run=False, origin='imported', source=str(source.resolve()),
                        archive_scope='verified native copy with its original Project; no new solve'))
            _state(destination, 'complete', origin='imported', numerical_validation='not_checked')
            read_job(destination)
            assert all((destination/'solution'/p.name).read_bytes() == p.read_bytes()
                       for p in source.iterdir() if p.is_file())
            result.append(str(destination))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reuse-native', type=Path, help='read a prior incomplete run; never redo already saved solves')
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic(); before = fingerprints()
    budget = 32*1024**3
    resource.setrlimit(resource.RLIMIT_AS, (budget, budget))
    report = dict(status='IN_PROGRESS', scope='fixed selection-chart geometry and discrete-field invariants',
                  new_fem_solves=0, reused_native_solves=0, rows=[], geometry=[], similarity=[], cli=[],
                  continuous_accuracy='UNVERIFIED', physical_peak_accuracy='UNVERIFIED', physical_error_bound=None)
    stage_names = ['previous', 'current', 'refined']
    available = [args.reuse_native/f'scale-{scale}-{name}' for scale in (1, 2) for name in stage_names] if args.reuse_native else []
    if args.reuse_native:
        prior_sources = json.loads((args.reuse_native/'sources-before.json').read_text())
        assert all(before.get(p) == h for p, h in prior_sources.items() if p.startswith('src/')), 'product sources differ from archived native run'
    plan = dict(card='ADD-N04-selection-charts-06', scales=[1, 2], stages=stage_names,
                planned_new_fem_solves=6-sum((p/'save_complete.json').is_file() for p in available),
                max_seconds=3600, max_address_space_bytes=budget,
                BLAS_threads=1, gates=dict(geometry=GEOMETRY_GATE, Galerkin=MATRIX_GATE,
                                          Ritz=RITZ_GATE, similarity=SIMILARITY_GATE, saved_RF=SAVED_RF_GATE))
    (out/'plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    (out/'sources-before.json').write_text(json.dumps(before, indent=2)+'\n')
    def checkpoint():
        report['seconds'] = time.monotonic()-started
        report['source_changed_during_run'] = fingerprints() != before
        (out/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
        if report['seconds'] > 3600:
            raise TimeoutError('declared 3600 second budget exceeded')
    def cli(command, name):
        done = subprocess.run([sys.executable, '-m', 'superfish_ng', *map(str, command)],
                              capture_output=True, text=True, timeout=max(1, 3600-(time.monotonic()-started)))
        (out/(name+'.log')).write_text(done.stdout+done.stderr)
        report['cli'].append(dict(command=list(map(str, command)), returncode=done.returncode))
        if done.returncode:
            raise AssertionError(done.stderr)
        return done.stdout
    solutions, transfers = [], []
    try:
        # The closed-form selected triangle checks the independent integral
        # helper against mathematics before using it on non-affine geometry.
        base, request = rectangle(1, uniform=False)
        doc, inside, values = geometry(base, request)
        expected = np.array([.1*.2/2, 2*np.pi*.1**2*.2/3, .1**4*.2/5])
        require(relative(values['source_native'], expected), GEOMETRY_GATE, 'closed-form rectangle selection')
        assert [row['covered_fraction'] for row in doc['selection']['coverage']] == [[2, 3], [1, 3], [1, 2]]
        report['closed_form'] = dict(status='PASS', expected=expected.tolist(), geometry=values)
        for scale in (1, 2):
            pair, request = nonaffine(scale)
            cover, inside, values = geometry(pair, request)
            report['geometry'].append(dict(scale=scale, family='nonaffine26/27', values=values, selection=cover['selection']))
            for name, document in (('transfer', cover), ('contained', inside)):
                (out/f'nonaffine-{scale}-{name}.json').write_text(json.dumps(document, indent=2)+'\n')
            checkpoint()
        for key in ('source_native', 'source_overlay', 'target_overlay', 'target_cover', 'target_contained'):
            a, b = [np.array(row['values'][key]) for row in report['geometry']]
            require(relative(b, a*np.array([4, 8, 32])), GEOMETRY_GATE, 'nonaffine moment scale '+key)
        assert report['geometry'][0]['selection'] == report['geometry'][1]['selection']
        for scale in (1, 2):
            pair, request = rectangle(scale)
            document, contained, values = geometry(pair, request)
            selected = document['selection']['selected_cells']; assert selected
            refined = replace(pair[1], case=replace(pair[1].case, curved_refinement_steps=(
                *pair[1].case.curved_refinement_steps, Step('marked', tuple(selected), 1.))))
            projects = [*pair, refined]; transfers.append(document)
            for name, data in (('transfer', document), ('contained', contained), ('request', request)):
                (out/f'scale-{scale}-{name}.json').write_text(json.dumps(data, indent=2)+'\n')
            stages, rf_rows = [], []
            for name, project in zip(plan['stages'], projects):
                project.save(out/f'scale-{scale}-{name}-project.json')
                destination = out/f'scale-{scale}-{name}'
                source = args.reuse_native/f'scale-{scale}-{name}' if args.reuse_native else None
                if source is not None and (source/'save_complete.json').is_file():
                    original = Project.load(args.reuse_native/f'scale-{scale}-{name}-project.json')
                    assert original.to_dict() == project.to_dict()
                    solution = read_solution(source); report['reused_native_solves'] += 1
                    # Preserve the archived native exactly for downstream imports.
                    import shutil
                    shutil.copytree(source, destination)
                    saved = json.loads((destination/'results.json').read_text())
                else:
                    report['new_fem_solves'] += 1
                    solution = solve(project.case, mesh_data=project.mesh_data)
                    saved = save_run(project.case, solution, destination)
                restored = read_solution(destination)
                # The native stores coefficients/frequencies. Eigenvalues are
                # derived again from saved f and are not a saved exact array.
                for attribute in ('u', 'frequencies_hz'):
                    np.testing.assert_array_equal(getattr(solution, attribute), getattr(restored, attribute))
                for attribute in ('points_rz_m', 'cell_nodes', 'boundary_nodes', 'boundary_curve_indices', 'boundary_parameters'):
                    np.testing.assert_array_equal(getattr(solution.space.geometry, attribute), getattr(restored.space.geometry, attribute))
                errors = {}
                for key, value in quantities(project.case, restored, mode=0).items():
                    actual = saved['modes'][0][key]
                    if isinstance(value, (float, int)):
                        error = abs(float(actual)-float(value))/max(abs(float(value)), 1e-300)
                        require(error, SAVED_RF_GATE, 'saved RF '+key); errors[key] = error
                    else:
                        assert actual == value
                stages.append(solution); rf_rows.append(saved['modes'][0])
                checkpoint()
                z = .073*scale
                export_radial_probe(destination, out/f'scale-{scale}-{name}-api-probe.csv', z)
                cli(['probe', destination, '--z-m', z, '--out', out/f'scale-{scale}-{name}-cli-probe.csv'], f'scale-{scale}-{name}-cli-probe')
                assert (out/f'scale-{scale}-{name}-api-probe.csv').read_bytes() == (out/f'scale-{scale}-{name}-cli-probe.csv').read_bytes()
                assert json.loads((out/f'scale-{scale}-{name}-api-probe.csv.json').read_text()) == json.loads((out/f'scale-{scale}-{name}-cli-probe.csv.json').read_text())
            parent, child = stages[1:]
            restriction = refine_marked_curved_space(parent.space, selected, minimum_corner_angle_deg=1.)
            for key in ('points_rz_m', 'cell_nodes'):
                np.testing.assert_array_equal(getattr(restriction.space.geometry, key), getattr(child.space.geometry, key))
            coarse = assemble_curved(parent.space, quadrature_order=12)
            fine = assemble_curved(child.space, quadrature_order=12)
            galerkin = {}
            for name, a, b in zip(('stiffness', 'mass'), coarse, fine):
                p = restriction.prolongation
                error = float(np.linalg.norm((p.T@b@p-a).data)/np.linalg.norm(a.data))
                require(error, MATRIX_GATE, 'independently assembled Galerkin '+name); galerkin[name] = error
            ritz = float(np.max(child.frequencies_hz/parent.frequencies_hz-1))
            require(max(0., ritz), RITZ_GATE, 'fixed-domain Ritz nonincrease')
            rows = dict(scale=scale, geometry=values, galerkin=galerkin, ritz_frequency_change=ritz,
                        rf=rf_rows, selected_cells=selected, source_cells=document['selection']['previous_final_cell_count'],
                        target_cells=document['selection']['current_final_cell_count'],
                        refined_cells=len(child.space.geometry.cell_nodes), stages_saved='ALL_ARRAYS_EXACT')
            report['rows'].append(rows); solutions.append(stages)
            checkpoint()
        assert transfers[0]['selection'] == transfers[1]['selection']
        for stage in range(3):
            a, b = solutions[0][stage], solutions[1][stage]
            errors = {}
            for key in ('frequency_hz', 'r_over_q_accelerator_ohm', 'r_over_q_circuit_ohm', 'geometry_factor_ohm', 'transit_time_factor_abs'):
                x, y = [row['rf'][stage][key] for row in report['rows']]
                error = abs(y*(2 if key == 'frequency_hz' else 1)/x-1)
                require(error, SIMILARITY_GATE, 'RF scale '+key); errors[key] = error
            report['similarity'].append(dict(stage=plan['stages'][stage], rf_relative_errors=errors, field=field_scale(a, b)))
        cli(['transfer-curved-selection', out/'scale-1-previous-project.json', out/'scale-1-current-project.json',
             '--request', out/'scale-1-request.json', '--out', out/'cli-transfer.json'], 'transfer-cli')
        replay = cli(['replay-curved-selection-transfer', out/'cli-transfer.json'], 'replay-cli')
        saved_transfer = json.loads((out/'cli-transfer.json').read_text())
        assert saved_transfer == transfers[0] == replay_curved_selection_transfer(saved_transfer)
        assert replay.startswith('REPLAYED SELECTION TRANSFER: ')
        report['managed_saved_archives'] = package_saved_projects(out)
        report['native_sha256'] = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for scale in (1, 2) for name in plan['stages']
                                   for p in (out/f'scale-{scale}-{name}').iterdir() if p.is_file()}
        assert fingerprints() == before, 'sources changed during execution'
        report['status'] = 'PASS'; checkpoint()
        print(json.dumps(dict(status='PASS', new_fem_solves=report['new_fem_solves'], seconds=report['seconds'])))
        return 0
    except BaseException as error:
        report['status'] = 'FAIL'; report['error'] = str(error)
        (out/'failure.txt').write_text(traceback.format_exc())
        checkpoint()
        raise


if __name__ == '__main__':
    sys.exit(main())

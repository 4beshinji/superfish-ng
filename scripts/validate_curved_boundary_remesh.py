# SPDX-License-Identifier: Apache-2.0
"""Fixed boundary-remesh-06 gates: independent geometry, six FEMs and saved fields.

No fitting or analytic substitution is used to produce eigenpairs. The Bessel
reference is evaluated only after each native FEM has been saved completely.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import resource
import shutil
import sys
import time
import traceback
from unittest.mock import patch

import numpy as np
from scipy.special import j0, j1

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from superfish_ng import solve
from superfish_ng.analytic import pillbox_tm_mode
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.curved_marked_refinement import refine_marked_curved_space
from superfish_ng.curved_refinement import refine_curved_space
from superfish_ng.curved_project_remesh import remesh_curved_project
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.curved_remesh_generation import build_curved_remesh_generation, replay_curved_remesh_generation
from superfish_ng.curved_space import case_curved_space
from superfish_ng.io import save_run
from superfish_ng.mesh_input import mesh_from_dict
from superfish_ng.project import Project, parse_json
from superfish_ng.rf import quantities
from superfish_ng.saved import read_solution
from validate_curved_selection_transfer import moments
from validate_large_curved_mesh_selection import fingerprints

GATES = dict(geometry=3e-12, matrix=1e-10, size=1e-12, frequency=3e-3,
             rf=1e-2, field=2e-2, similarity=1e-9, saved_rf=1e-12)
RF_KEYS = ('frequency_hz', 'r_over_q_accelerator_ohm', 'r_over_q_circuit_ohm',
           'geometry_factor_ohm', 'transit_time_factor_abs')
FIELD_KEYS = ('Hphi_A_per_m', 'Er_quadrature_V_per_m', 'Ez_quadrature_V_per_m')


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def relative(actual, expected):
    actual, expected = np.asarray(actual), np.asarray(expected)
    assert np.isfinite(actual).all() and np.isfinite(expected).all()
    return float(np.max(np.abs(actual-expected)/np.maximum(np.abs(expected), 1e-300)))


def require(value, gate, label):
    if not np.isfinite(value) or value > gate:
        raise AssertionError(f'{label}: {value} exceeds fixed gate {gate}')


def basis(q):
    """Independent P2 nodal polynomial and derivatives; no product mapping call."""
    x, y = np.asarray(q).T; l = 1-x-y
    n = np.column_stack((l*(2*l-1), x*(2*x-1), y*(2*y-1), 4*l*x, 4*x*y, 4*y*l))
    dx = np.column_stack((1-4*l, 4*x-1, np.zeros_like(x), 4*(l-x), 4*y, -4*y))
    dy = np.column_stack((1-4*l, np.zeros_like(x), 4*y-1, -4*x, 4*x, 4*(l-y)))
    return n, dx, dy


def volume_rule(nodes):
    t, w = np.polynomial.legendre.leggauss(8); t, w = (t+1)/2, w/2
    a, b = np.meshgrid(t, t, indexing='ij')
    q = np.column_stack((a.ravel(), ((1-a)*b).ravel()))
    n, dx, dy = basis(q); p = n@nodes; u, v = dx@nodes, dy@nodes
    jac = u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0]
    weight = (np.outer(w, w)*(1-a)).ravel()*jac*2*np.pi*p[:, 0]
    assert np.all(weight > 0)
    return q, p, weight


def green(space):
    """Eight-point boundary quadrature including independent integral r^4 dz/4."""
    t, w = np.polynomial.legendre.leggauss(8); t, w = (t+1)/2, w/2
    n = np.column_stack(((1-t)*(1-2*t), t*(2*t-1), 4*t*(1-t)))
    d = np.column_stack((4*t-3, 4*t-1, 4-8*t))
    nodes = space.geometry.points_rz_m[space.geometry.boundary_nodes]
    p = np.einsum('qi,eik->eqk', n, nodes); v = np.einsum('qi,eik->eqk', d, nodes)
    r, z = p[..., 0], p[..., 1]; dr, dz = v[..., 0], v[..., 1]
    result = np.array([np.sum((r*dz-z*dr)*w)/2, np.pi*np.sum(r*r*dz*w), np.sum(r**4*dz*w)/4])
    assert np.all(result > 0) or np.all(result < 0)
    return result


def native_space(project):
    return case_curved_space(project.case, mesh_from_dict(project.case, project.mesh_data))


def independent_boundary(old, new):
    """Union of primitive breakpoints, direct Lagrange-to-Bernstein conversion."""
    partitions = []
    for space in (old, new):
        g = space.geometry; curves = {}
        for ids, owner, ends, tag in zip(g.boundary_nodes, g.boundary_curve_indices, g.boundary_parameters, space.boundary_tags):
            lo, hi = map(float, ends); p = g.points_rz_m[ids].copy()
            if hi < lo:lo, hi, p = hi, lo, p[[1, 0, 2]]
            assert hi > lo
            curves.setdefault(int(owner), []).append((lo, hi, p, str(tag)))
        for entries in curves.values():
            entries.sort(key=lambda e:e[0]); assert entries[0][0] == 0 and entries[-1][1] == 1
            assert all(a[1] == b[0] for a, b in zip(entries, entries[1:]))
        partitions.append(curves)
    assert set(partitions[0]) == set(partitions[1])
    scale = max(float(np.max(np.abs(s.geometry.points_rz_m))) for s in (old, new))
    tolerance = 512*np.finfo(float).eps*scale; maximum = 0.; count = 0
    for owner in partitions[0]:
        sides = [p[owner] for p in partitions]
        breaks = sorted({x for entries in sides for lo, hi, _, _ in entries for x in (lo, hi)})
        for lo, hi in zip(breaks, breaks[1:]):
            coefficients, tags = [], []
            for entries in sides:
                matches = [e for e in entries if e[0] <= lo and hi <= e[1]]; assert len(matches) == 1
                a, b, nodes, tag = matches[0]; tags.append(tag)
                t = (np.array([lo, (lo+hi)/2, hi])-a)/(b-a)
                q = np.column_stack(((1-t)*(1-2*t), t*(2*t-1), 4*t*(1-t)))@nodes
                coefficients.append(np.array([q[0], 2*q[1]-(q[0]+q[2])/2, q[2]]))
            assert tags[0] == tags[1]
            maximum = max(maximum, float(np.max(np.linalg.norm(coefficients[1]-coefficients[0], axis=1))))
            count += 1
    require(maximum, tolerance, 'whole P2 Bernstein boundary')
    return dict(common_intervals=count, maximum_coefficient_distance_m=maximum, roundoff_tolerance_m=tolerance)


def boundary_refusals(source, target, document):
    """Both the independent checker and public boundary contract reject defects."""
    from superfish_ng.curved_same_domain_tracking import compare_quadratic_space_boundaries
    old, new = native_space(source), native_space(target); g = new.geometry
    choices = np.flatnonzero(g.boundary_curve_indices == 1)
    index = int(min(choices, key=lambda i:min(g.boundary_parameters[i])))
    lo, hi = g.boundary_parameters[index]; assert 0 <= lo < hi < 1
    rejected = []
    for label in ('gap', 'overlap', 'wrong tag', 'reversed nodes', 'moved midpoint'):
        bad = new
        if label in ('gap', 'overlap'):
            values = g.boundary_parameters.copy(); values[index, 1] += (hi-lo)*(-.25 if label=='gap' else .25)
            bad = replace(new, geometry=replace(g, boundary_parameters=values))
        elif label == 'wrong tag':
            tags = new.boundary_tags.copy(); tags[index] = 'axis'; bad = replace(new, boundary_tags=tags)
        elif label == 'reversed nodes':
            nodes = g.boundary_nodes.copy(); nodes[index, :2] = nodes[index, 1::-1]
            bad = replace(new, geometry=replace(g, boundary_nodes=nodes))
        else:
            points = g.points_rz_m.copy(); points[g.boundary_nodes[index, 2], 0] += .000001
            bad = replace(new, geometry=replace(g, points_rz_m=points))
        for checker in (lambda:independent_boundary(old, bad),
                        lambda:compare_quadratic_space_boundaries(source.case, old, target.case, bad)):
            try:checker()
            except (AssertionError, ValueError):pass
            else:raise AssertionError('accepted boundary '+label)
        rejected.append(label)
    settings = deepcopy(document['settings']); settings.pop('curved_refinement_levels', None)
    settings['curved_refinement_steps'] = source.case.to_dict()['mesh']['curved_refinement_steps']
    try:build_curved_remesh_generation(source, settings)
    except ValueError as error:assert 'topology' in str(error)
    else:raise AssertionError('accepted frozen history from old source topology')
    return rejected+['old frozen topology']


def quality(space):
    g = space.geometry; p = g.points_rz_m[g.cell_nodes[:, :3]]
    u, v = p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]
    areas = (u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0])/2
    assert np.all(areas > 0)
    edges = np.unique(np.sort(g.cell_nodes[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1), axis=0)
    lengths = np.linalg.norm(np.diff(g.points_rz_m[edges], axis=1)[:, 0], axis=1)
    chord = [np.arctan2(2*areas, np.sum((p[:, (i+1)%3]-p[:, i])*(p[:, (i+2)%3]-p[:, i]), axis=1)) for i in range(3)]
    ref = np.array([[0., 0.], [1., 0.], [0., 1.]])
    _, dx, dy = basis(ref); tangent_angles = []
    for ids in g.cell_nodes:
        nodes = g.points_rz_m[ids]; first, second = dx@nodes, dy@nodes
        for i in range(3):
            directions = ref[[(i+1)%3, (i+2)%3]]-ref[i]
            a, b = directions@np.array([first[i], second[i]])
            tangent_angles.append(np.arctan2(a[0]*b[1]-a[1]*b[0], a@b))
    return dict(max_edge_m=float(lengths.max()), max_area_m2=float(areas.max()),
                min_chord_angle_deg=float(np.rad2deg(np.min(chord))),
                min_p2_corner_angle_deg=float(np.rad2deg(min(tangent_angles))))


def scaled(project, factor):
    result = transform_curved_project(project, dict(radial_scale=factor, axial_scale=factor, axial_shear=0.), rf_coordinates='axial')
    case = result.case
    controls = replace(case.contour_mesh, max_edge_m=case.contour_mesh.max_edge_m*factor) if case.contour_mesh else None
    lengths = {key:None if getattr(case, key) is None else getattr(case, key)*factor
               for key in ('boundary_max_edge_m', 'corner_max_edge_m', 'corner_radius_m')}
    contour = replace(case.curved_contour, minimum_gap_m=case.curved_contour.minimum_gap_m*factor)
    return replace(result, case=replace(case, contour_mesh=controls, curved_contour=contour, **lengths))


def generation_check(source, settings, document):
    assert replay_curved_remesh_generation(document) == document
    target = remesh_curved_project(source, document['plan']); old, new = native_space(source), native_space(target)
    boundary = independent_boundary(old, new)
    totals = [sum((moments(s.geometry.points_rz_m[ids]) for ids in s.geometry.cell_nodes), np.zeros(3)) for s in (old, new)]
    require(relative(totals[1], totals[0]), GATES['geometry'], 'original whole-domain moments')
    integrals = green(new); require(relative(totals[1], np.abs(integrals)), GATES['geometry'], 'three Green integrals')
    parent = native_space(replace(target, case=replace(target.case, curved_refinement_levels=0, curved_refinement_steps=())))
    matrices = assemble_curved(parent, quadrature_order=12); prefixes = []; galerkin = []
    def prefix(s):
        counts = [len(s.geometry.cell_nodes), len(s.geometry.boundary_nodes)]
        assert counts[0] <= settings['max_triangles'] and counts[1] <= settings['max_boundary_edges']
        q = quality(s); assert q['min_p2_corner_angle_deg'] >= settings['minimum_corner_angle_deg']
        prefixes.append(dict(cells=counts[0], boundary_edges=counts[1], quality=q))
    prefix(parent)
    for step in target.case.curved_refinement_steps:
        child = refine_curved_space(parent) if step.kind == 'uniform' else refine_marked_curved_space(
            parent, list(step.marked_cells), minimum_corner_angle_deg=step.minimum_corner_angle_deg, split_pattern=step.split_pattern)
        fine = assemble_curved(child.space, quadrature_order=12); errors = {}
        for key, a, b in zip(('K', 'M'), matrices, fine):
            error = float(np.linalg.norm((child.prolongation.T@b@child.prolongation-a).data)/np.linalg.norm(a.data))
            require(error, GATES['matrix'], 'seed-child Galerkin '+key); errors[key] = error
        galerkin.append(errors); parent, matrices = child.space, fine; prefix(parent)
    np.testing.assert_array_equal(parent.geometry.points_rz_m, new.geometry.points_rz_m)
    one = np.ones(matrices[1].shape[0]); mass = float(one@matrices[1]@one)
    require(relative(mass, totals[1][2]), GATES['geometry'], 'Hphi=r assembled mass')
    q = prefixes[-1]['quality']; edge = min(settings['max_chord_edge_m'], source.case.contour_mesh.max_edge_m) if source.case.contour_mesh else settings['max_chord_edge_m']
    assert q['max_edge_m'] <= edge*(1+GATES['size']) and q['max_area_m2'] <= settings['max_chord_triangle_area_m2']*(1+GATES['size'])
    assert q['min_chord_angle_deg'] >= settings['minimum_corner_angle_deg']
    v = document['validation']; assert [p['cells'] for p in prefixes] == v['prefix_triangle_counts']
    assert [p['boundary_edges'] for p in prefixes] == v['prefix_boundary_edge_counts']
    return target, dict(boundary=boundary, moments=totals[1].tolist(), green_signed=integrals.tolist(),
                        assembled_known_field_mass=mass, prefixes=prefixes, galerkin=galerkin)


def field_error(native, reference):
    """Single global H sign; independent physical volume weights; E is a vector."""
    samples = []; inner = 0.
    for cell, ids in enumerate(native.space.geometry.cell_nodes):
        q, p, w = volume_rule(native.space.geometry.points_rz_m[ids])
        actual = native.fields_in_cell(cell, q); exact = reference(cell, q, p)
        inner += float(w@(actual[FIELD_KEYS[0]]*exact[FIELD_KEYS[0]])); samples.append((w, actual, exact))
    sign = 1 if inner >= 0 else -1; errors = {}
    for label, keys in (('H', FIELD_KEYS[:1]), ('E', FIELD_KEYS[1:])):
        numerator = sum(float(w@(sign*a[k]-b[k])**2) for w, a, b in samples for k in keys)
        denominator = sum(float(w@b[k]**2) for w, a, b in samples for k in keys)
        assert denominator > 0
        errors[label] = float(np.sqrt(numerator/denominator))
    return dict(relative_l2=errors, single_sign=sign, physical_volume_points=64*len(native.space.geometry.cell_nodes))


def exact_fields(reference, radius):
    kr = reference['radial_wave_number_per_m']*radius
    return dict(zip(FIELD_KEYS, (reference['h0_a_per_m']*j1(kr), np.zeros_like(kr), reference['e0_v_per_m']*j0(kr))))


def saved_check(project, native, destination):
    before = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir() if p.is_file()}
    with patch('superfish_ng.curved_solution.solve_curved', side_effect=AssertionError('reader must not solve')):
        restored = read_solution(destination)
    assert restored.case.to_dict() == project.case.to_dict() and restored.source_mesh_data == project.mesh_data
    def arrays(s):
        g = s.space.geometry
        result = {key:getattr(g, key) for key in ('points_rz_m', 'cell_nodes', 'boundary_nodes', 'boundary_curve_indices', 'boundary_parameters')}
        result.update({key:getattr(s.space, key) for key in ('boundary_tags', 'axis_dofs', 'constrained_dofs')})
        result.update(u_a_per_m2=s.u, frequencies_hz=s.frequencies_hz); return result
    with np.load(destination/'fields.npz') as data:
        a, b = arrays(native), arrays(restored); assert set(data.files) == set(a) == set(b)
        for key in data.files:
            np.testing.assert_array_equal(data[key], a[key]); np.testing.assert_array_equal(data[key], b[key])
    errors = {}
    for key, value in quantities(project.case, restored, mode=0).items():
        original = restored.results['modes'][0][key]
        if isinstance(value, (int, float)):
            error = relative(original, value); require(error, GATES['saved_rf'], 'saved RF '+key); errors[key] = error
        else:assert original == value
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == v for p, v in before.items())
    return restored, dict(npz_arrays=10, files_sha256=before, recomputed_rf_relative_errors=errors,
                          all_modes=restored.results['modes'], conventions=restored.results.get('conventions'))


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reuse-native', type=Path, help='Reuse completed native saves from an earlier incomplete run')
    args = parser.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic(); before = fingerprints(); write(out/'sources-before.json', before)
    budget = 32*1024**3; resource.setrlimit(resource.RLIMIT_AS, (budget, budget))
    report = dict(status='IN_PROGRESS', new_fem_solves=0, reused_fem_solves=0, geometry=[], rows=[],
                  similarity=[], rejections=[], gates=GATES, physical_peak_accuracy='UNVERIFIED', physical_error_bound=None)
    def checkpoint():
        report.update(seconds=time.monotonic()-started, source_changed_during_run=fingerprints()!=before)
        write(out/'report.json', report)
        if report['seconds'] > 3600:raise TimeoutError('fixed one-hour validation budget exceeded')
    try:
        if args.reuse_native:
            previous = parse_json((args.reuse_native/'sources-before.json').read_text())
            assert all(before.get(p) == h for p, h in previous.items() if p.startswith('src/'))
        projects = {}; documents = {}; natives = {}; requests = []
        for family in ('rectangle-coarse', 'rectangle-fine', 'nonaffine'):
            name = family.split('-')[0]; source = Project.load(ROOT/f'examples/curved_boundary_remesh/{name}-project.json')
            source = replace(source, case=replace(source.case, quadrature_order=12))
            settings = parse_json((ROOT/f'examples/curved_boundary_remesh/{name}-settings.json').read_text())
            if family == 'rectangle-fine':settings.update(max_chord_edge_m=.0225, max_chord_triangle_area_m2=.000125)
            for scale in (1, 2):
                p = source if scale == 1 else scaled(source, 2.)
                s = dict(settings, max_chord_edge_m=settings['max_chord_edge_m']*scale,
                         max_chord_triangle_area_m2=settings['max_chord_triangle_area_m2']*scale**2)
                requests.append((f'{family}-{scale}', family, scale, p, s))
        write(out/'plan.json', dict(card='ADD-N04-boundary-remesh-06', planned_native_count=6, quadrature_order=12,
                                   gates=GATES, max_seconds=3600, max_address_space_bytes=budget,
                                   cases=[dict(name=n, family=f, scale=a, source_project=p.to_dict(), settings=s) for n, f, a, p, s in requests]))
        for name, family, scale, source, settings in requests:
            document = build_curved_remesh_generation(source, settings)
            target, geometry = generation_check(source, settings, document)
            if family.startswith('rectangle'):
                radius, length = .1*scale, .2*scale
                require(relative(geometry['moments'], [radius*length, np.pi*radius**2*length, radius**4*length/4]), GATES['geometry'], 'closed cylinder integrals')
            source.save(out/(name+'-source-project.json')); target.save(out/(name+'-project.json'))
            write(out/(name+'-generation.json'), document); projects[name] = target; documents[name] = document
            report['geometry'].append(dict(name=name, **geometry)); checkpoint()
        report['boundary_refusals'] = boundary_refusals(source, target, document)
        for family in ('rectangle-coarse', 'rectangle-fine', 'nonaffine'):
            a, b = [documents[f'{family}-{s}']['plan'] for s in (1, 2)]
            assert a['source_mesh']['triangles'] == b['source_mesh']['triangles'] and a.get('curved_refinement_steps') == b.get('curved_refinement_steps')
            rows = [next(r for r in report['geometry'] if r['name']==f'{family}-{s}') for s in (1, 2)]
            require(relative(rows[1]['moments'], np.asarray(rows[0]['moments'])*[4, 8, 32]), GATES['geometry'], '4/8/32 similarity '+family)
        source = requests[-2][3]; settings = requests[-2][4]
        for label, bad, message in [('root budget', dict(settings, max_boundary_edges=9), 'max_boundary_edges'),
                                    ('size budget', dict(settings, max_boundary_edges=10), 'max_boundary_edges'),
                                    ('round exhaustion', dict(settings, max_rounds=1), 'max_rounds'),
                                    ('unknown setting', dict(settings, unknown=0), 'unknown')]:
            try:build_curved_remesh_generation(source, bad)
            except ValueError as error:assert message in str(error); report['rejections'].append(label)
            else:raise AssertionError('accepted '+label)
        raw = json.dumps(settings).replace('"schema_version": 2', '"schema_version": 2,"schema_version": 2')
        try:parse_json(raw)
        except ValueError as error:assert 'duplicate' in str(error); report['rejections'].append('raw duplicate')
        else:raise AssertionError('accepted duplicate')
        bad = deepcopy(documents['nonaffine-1']); bad['validation']['prefix_boundary_edge_counts'][-1] += 1
        try:replay_curved_remesh_generation(bad)
        except ValueError as error:assert 'full reconstruction' in str(error); report['rejections'].append('saved modification')
        else:raise AssertionError('accepted modified saved count')
        checkpoint()
        for name, family, scale, source, settings in requests:
            project = projects[name]; destination = out/name
            previous = args.reuse_native/name if args.reuse_native else None
            if previous is not None and (previous/'save_complete.json').exists():
                assert Project.load(args.reuse_native/(name+'-project.json')).to_dict() == project.to_dict()
                native = read_solution(previous); shutil.copytree(previous, destination); report['reused_fem_solves'] += 1
            else:
                report['new_fem_solves'] += 1; native = solve(project.case, mesh_data=project.mesh_data)
                save_run(project.case, native, destination)
            restored, saved = saved_check(project, native, destination); natives[name] = restored
            row = dict(name=name, saved=saved); report['rows'].append(row); checkpoint()
            if family.startswith('rectangle'):
                exact = pillbox_tm_mode(.1*scale, .2*scale, normalization_j=1.)
                errors = {k:relative(restored.results['modes'][0][k], exact[k]) for k in RF_KEYS}
                row['analytic'] = dict(reference=exact, rf_relative_errors=errors,
                    fields=field_error(restored, lambda cell, q, p:exact_fields(exact, p[:, 0])))
                checkpoint()
                for key, value in errors.items():require(value, GATES['frequency' if key=='frequency_hz' else 'rf'], 'Bessel '+key)
                require(max(row['analytic']['fields']['relative_l2'].values()), GATES['field'], 'Bessel vector E/H')
        a, b = natives['nonaffine-1'], natives['nonaffine-2']
        np.testing.assert_array_equal(a.space.geometry.cell_nodes, b.space.geometry.cell_nodes)
        rf = {k:relative(b.results['modes'][0][k]*(2 if k=='frequency_hz' else 1), a.results['modes'][0][k]) for k in RF_KEYS}
        fields = field_error(a, lambda cell, q, p:{k:v*2**1.5 for k, v in b.fields_in_cell(cell, q).items() if k in FIELD_KEYS})
        report['similarity'].append(dict(family='nonaffine', rf_relative_errors=rf, fields=fields))
        require(max(rf.values()), GATES['similarity'], 'nonaffine RF scale')
        require(max(fields['relative_l2'].values()), GATES['similarity'], 'nonaffine vector E/H scale')
        assert len(report['rows']) == 6 and report['new_fem_solves']+report['reused_fem_solves'] == 6
        assert fingerprints() == before; report['status'] = 'PASS'; checkpoint()
        print(json.dumps({k:report[k] for k in ('status', 'new_fem_solves', 'reused_fem_solves', 'seconds')}))
    except BaseException as error:
        report.update(status='FAIL', error=str(error)); write(out/'report.json', report)
        (out/'failure.txt').write_text(traceback.format_exc()); raise


if __name__ == '__main__':main()

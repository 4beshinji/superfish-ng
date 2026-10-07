# SPDX-License-Identifier: Apache-2.0
"""Independent region coverage and physical integrals across base charts."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import sys
import unittest
import numpy as np

from superfish_ng.project import Project, parse_json
from superfish_ng.curved_selection_transfer import transfer_curved_cell_selection
from superfish_ng.curved_reference_partition import build_curved_reference_partition
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh_input import mesh_from_dict
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from test_curved_reference_partition import rectangle_project, CHART

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples/curved_selection_charts'
# Validator modules also import their sibling helpers by module name.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


def fixture():
    projects = [Project.from_dict(parse_json((EXAMPLES / name).read_text()))
                for name in ('old-project.json', 'new-project.json')]
    request = parse_json((EXAMPLES / 'intersects.json').read_text())
    return projects, request


def space(project):
    return case_curved_space(project.case, mesh_from_dict(project.case, project.mesh_data))


def physical_moments(projects, document, contained):
    # Reuse the independently written P2 basis/derivatives and 8x8 Duffy rule,
    # not the product common-map evaluator or the selection area accumulator.
    from validate_curved_selection_transfer import moments
    spaces = [space(p) for p in projects]
    selected = document['request']['selected_cells']
    native = sum((moments(spaces[0].geometry.points_rz_m[spaces[0].geometry.cell_nodes[i]])
                  for i in selected), np.zeros(3))
    totals = [np.zeros(3), np.zeros(3)]
    for row in document['selection']['overlaps']:
        for side, prefix in enumerate(('previous', 'current')):
            nodes = spaces[side].geometry.points_rz_m[
                spaces[side].geometry.cell_nodes[row[prefix + '_cell']]]
            q = [[float(F(*v)) for v in p[1:]] for p in row[prefix + '_barycentric']]
            totals[side] += moments(nodes, q)
    cover = sum((moments(spaces[1].geometry.points_rz_m[spaces[1].geometry.cell_nodes[i]])
                 for i in document['selection']['selected_cells']), np.zeros(3))
    inside = sum((moments(spaces[1].geometry.points_rz_m[spaces[1].geometry.cell_nodes[i]])
                  for i in contained['selection']['selected_cells']), np.zeros(3))
    np.testing.assert_allclose(totals[0], native, rtol=3e-12, atol=0)
    if not np.all(cover >= totals[1] * (1 - 3e-12)):
        raise AssertionError('target cover does not contain mapped physical region')
    if not np.all(inside <= totals[1] * (1 + 3e-12)):
        raise AssertionError('contained target cells exceed mapped physical region')
    return native, totals[1]


def symmetry(project, side, tag):
    index = 3 if side == 'z_min' else 1
    tags = list(project.case.curved_contour.edge_tags)
    tags[index] = tag
    mesh = deepcopy(project.mesh_data)
    for i, edge in enumerate(mesh['boundary_edges']):
        z = [mesh['points'][node][1] for node in edge]
        plane = 0. if side == 'z_min' else project.case.length
        if z[0] == z[1] == plane:
            mesh['boundary_tags'][i] = tag
    case = replace(project.case, contour=None,
                   curved_contour=replace(project.case.curved_contour, edge_tags=tuple(tags)))
    return replace(project, case=case, mesh_data=mesh)


class CurvedSelectionChartsTests(unittest.TestCase):
    def test_closed_form_fractions_and_policy_source_coverage(self):
        projects, request = fixture()
        original = [p.to_dict() for p in projects], deepcopy(request)
        cover = transfer_curved_cell_selection(*projects, request)
        inside = transfer_curved_cell_selection(*projects, dict(request, coverage_policy='contained'))
        self.assertEqual(cover['schema_version'], 2)
        self.assertIsNone(cover['physical_error_bound'])
        self.assertEqual(cover['selection']['selected_cells'], [0, 1, 2])
        self.assertEqual(inside['selection']['selected_cells'], [])
        self.assertEqual(cover['selection']['partially_covered_cells'], [0, 1, 2])
        self.assertEqual([r['covered_fraction'] for r in cover['selection']['coverage']],
                         [[2, 3], [1, 3], [1, 2]])
        self.assertEqual([r['covered_reference_area'] for r in cover['selection']['coverage']],
                         [[1, 6], [1, 12], [1, 4]])
        for key in ('source_reference_area', 'intersection_reference_area'):
            self.assertEqual(cover['selection'][key], [1, 2])
        self.assertEqual(cover['selection']['source_cell_area_checks'], [dict(
            previous_cell=0, source_reference_area=[1, 2], intersection_reference_area=[1, 2])])
        for key in ('coverage', 'overlaps', 'source_cell_area_checks'):
            self.assertEqual(cover['selection'][key], inside['selection'][key])
        partition = cover['reference_partition']
        for prefix in ('previous', 'current'):
            self.assertEqual(partition[prefix + '_areas'], partition[prefix + '_covered_areas'])
        self.assertEqual(original, ([p.to_dict() for p in projects], request))

    def test_closed_form_physical_selected_integrals(self):
        projects, request = fixture()
        cover = transfer_curved_cell_selection(*projects, request)
        inside = transfer_curved_cell_selection(*projects, dict(request, coverage_policy='contained'))
        old, mapped = physical_moments(projects, cover, inside)
        expected = [.1*.2/2, 2*np.pi*.1**2*.2/3, .1**4*.2/5]
        np.testing.assert_allclose(old, expected, rtol=3e-12, atol=0)
        np.testing.assert_allclose(mapped, expected, rtol=3e-12, atol=0)

    def test_edge_contacts_and_full_selection_do_not_create_false_partial_area(self):
        projects = [rectangle_project(), rectangle_project()]
        _, request = fixture()
        request['reference_vertices'] = [CHART, CHART]
        one = transfer_curved_cell_selection(*projects, request)['selection']
        self.assertEqual(one['selected_cells'], [0])
        self.assertEqual(one['partially_covered_cells'], [])
        self.assertTrue(all(row['current_cell'] == 0 for row in one['overlaps']))
        projects, request = fixture()
        both = transfer_curved_cell_selection(*projects, dict(request, selected_cells=[1, 0],
                                             coverage_policy='contained'))['selection']
        self.assertEqual(both['selected_cells'], [0, 1, 2])
        self.assertEqual(both['partially_covered_cells'], [])
        self.assertEqual(both['source_reference_area'], [1, 1])

    def test_numbering_and_reverse_full_cover_preserve_chart_region(self):
        from test_curved_comparison_correspondence import renumber_source
        projects, request = fixture()
        changed = []
        orders = []
        charts = []
        for side, project in enumerate(projects):
            mesh, order = renumber_source(project.mesh_data, seed=102 + side)
            chart = {tuple(p): q for p, q in zip(project.mesh_data['points'], request['reference_vertices'][side])}
            charts.append([chart[tuple(p)] for p in mesh['points']])
            changed.append(replace(project, mesh_data=mesh))
            orders.append(order.tolist())
        actual = transfer_curved_cell_selection(*changed, dict(request,
            selected_cells=[orders[0].index(0)], reference_vertices=charts))['selection']
        expected = [F(2, 3), F(1, 3), F(1, 2)]
        self.assertEqual([F(*r['covered_fraction']) for r in actual['coverage']],
                         [expected[i] for i in orders[1]])
        reverse = transfer_curved_cell_selection(*projects[::-1], dict(request,
            selected_cells=[0, 1, 2], reference_vertices=request['reference_vertices'][::-1],
            coverage_policy='contained'))['selection']
        self.assertEqual(reverse['selected_cells'], [0, 1])
        self.assertEqual(reverse['source_reference_area'], [1, 1])

    def test_non_nested_frozen_histories_preserve_native_selection_area(self):
        from superfish_ng.frozen_curved_refinement import freeze_curved_refinement
        projects, request = fixture()
        projects = [replace(p, case=replace(p.case, curved_refinement_steps=(
            Step('uniform'), Step('marked', (side,), 1.)))) for side, p in enumerate(projects)]
        request['selected_cells'] = [0, len(space(projects[0]).geometry.cell_nodes) - 1]
        cover = transfer_curved_cell_selection(*projects, request)
        inside = transfer_curved_cell_selection(*projects, dict(request, coverage_policy='contained'))
        old, mapped = physical_moments(projects, cover, inside)
        self.assertLess(abs(float(F(*cover['selection']['source_reference_area'])) / (old[0]/.02) - 1), 3e-12)
        np.testing.assert_allclose(mapped, old, rtol=3e-12, atol=0)
        frozen = [freeze_curved_refinement(p) for p in projects]
        rebuilt = transfer_curved_cell_selection(*frozen, request)
        self.assertEqual(rebuilt['selection'], cover['selection'])
        self.assertEqual(rebuilt['reference_partition'], cover['reference_partition'])

    def test_nonaffine_maps_and_scale_preserve_three_independent_integrals(self):
        from validate_reference_chart_fixture import reference_chart_fixture
        from test_curved_piecewise_remesh_tracking import curved_comparison_fixture
        values = []
        selections = []
        for scale in (1., 2.):
            cases, documents = curved_comparison_fixture(scale)
            maps = reference_chart_fixture(cases, documents, scale)
            projects = [Project(replace(case, curved_refinement_steps=(
                Step('uniform'), Step('marked', (side,), 1.))), mesh_data=m['source_mesh'])
                for side, (case, m) in enumerate(zip(cases, maps))]
            request = dict(schema_version=2, selected_cells=[0, 5, 6],
                boundary_pairing='declared_reference_polylines', coverage_policy='intersects',
                max_pair_tests=100000, max_triangles=10000,
                reference_vertices=[m['reference_vertices'] for m in maps])
            cover = transfer_curved_cell_selection(*projects, request)
            inside = transfer_curved_cell_selection(*projects, dict(request, coverage_policy='contained'))
            values.append(physical_moments(projects, cover, inside))
            selections.append(cover['selection'])
            self.assertEqual([len(m['source_mesh']['triangles']) for m in maps], [26, 27])
        self.assertEqual(selections[0], selections[1])
        np.testing.assert_allclose(values[1], np.asarray(values[0]) * [4, 8, 32], rtol=3e-12, atol=0)

    def test_original_symmetry_tags_need_explicit_opt_in_and_match_sectors(self):
        projects, request = fixture()
        for side in ('z_min', 'z_max'):
            for tag in ('electric_symmetry', 'magnetic_symmetry'):
                pair = [symmetry(p, side, tag) for p in projects]
                with self.subTest(side=side, tag=tag):
                    actual = transfer_curved_cell_selection(*pair, request)
                    self.assertEqual(actual['selection']['selected_cells'], [0, 1, 2])
                    self.assertTrue(any(r['tag'] == tag for r in actual['reference_partition']['reference_boundary']))
                    with self.assertRaisesRegex(ValueError, 'closed PEC'):
                        build_curved_reference_partition(*pair, reference_vertices=request['reference_vertices'],
                            max_pair_tests=100000, max_triangles=1000)
        with self.assertRaisesRegex(ValueError, 'symmetry sector'):
            transfer_curved_cell_selection(symmetry(projects[0], 'z_min', 'magnetic_symmetry'), projects[1], request)
        for flag in (1, None, 'true'):
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, 'allow_tm_symmetry'):
                build_curved_reference_partition(*projects, reference_vertices=request['reference_vertices'],
                    max_pair_tests=100000, max_triangles=1000, allow_tm_symmetry=flag)

    def test_all_chart_and_native_budgets_reject_before_partial_result(self):
        projects, request = fixture()
        actual = transfer_curved_cell_selection(*projects, request)
        self.assertEqual(actual['selection']['total_pair_tests'], 41)
        self.assertEqual(actual['selection']['total_pair_tests'], actual['reference_partition']['total_pair_tests'])
        transfer_curved_cell_selection(*projects, dict(request, max_pair_tests=41))
        for budget in (1, 31, 40):
            with self.subTest(budget=budget), self.assertRaisesRegex(ValueError, 'max_pair_tests'):
                transfer_curved_cell_selection(*projects, dict(request, max_pair_tests=budget))
        for maximum in (1, 2, 3):
            with self.subTest(maximum=maximum), self.assertRaisesRegex(ValueError, 'max_triangles'):
                transfer_curved_cell_selection(*projects, dict(request, max_triangles=maximum))
        refined = replace(projects[1], case=replace(projects[1].case, curved_refinement_levels=1))
        with self.assertRaisesRegex(ValueError, 'max_triangles'):
            transfer_curved_cell_selection(projects[0], refined, dict(request, max_triangles=11))

    def test_geometric_refusals_and_input_immutability(self):
        projects, request = fixture()
        invalid = [dict(request, selected_cells=[2])]
        for mutation in ('missing_vertex', 'duplicate_vertex', 'inverted_chart', 'changed_boundary'):
            value = deepcopy(request)
            chart = value['reference_vertices'][1]
            if mutation == 'missing_vertex': chart.pop()
            elif mutation == 'duplicate_vertex': chart[4] = chart[0]
            elif mutation == 'inverted_chart': chart[0], chart[2] = chart[2], chart[0]
            else: chart[4] = [.125, .5]
            invalid.append(value)
        for value in invalid:
            before = [p.to_dict() for p in projects], deepcopy(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                transfer_curved_cell_selection(*projects, value)
            self.assertEqual(before, ([p.to_dict() for p in projects], value))
        for target in (replace(projects[1], mesh_data=None), replace(projects[1], reflect_full=True),
                       replace(projects[1], case=replace(projects[1].case, geometry_order=1, element_order=1))):
            with self.subTest(target=target), self.assertRaises(ValueError):
                transfer_curved_cell_selection(projects[0], target, request)
        raw = projects[1].case.to_dict()
        raw['model']['polarization'] = 'te'
        from superfish_ng import Case
        te = replace(projects[1], case=Case.from_dict(raw))
        with self.assertRaisesRegex(ValueError, 'TM'):
            transfer_curved_cell_selection(projects[0], te, request)


class CurvedSelectionChartsSavedTests(unittest.TestCase):
    def document(self):
        projects, request = fixture()
        return transfer_curved_cell_selection(*projects, request)

    def assert_bad_documents(self, document, mutations):
        from superfish_ng.curved_selection_transfer import replay_curved_selection_transfer
        for label, mutate in mutations:
            changed = deepcopy(document)
            mutate(changed)
            before = deepcopy(changed)
            with self.subTest(label=label), self.assertRaises(ValueError):
                replay_curved_selection_transfer(changed)
            self.assertEqual(changed, before)

    def test_full_document_round_trip_both_policies_and_browser_numbers(self):
        import json
        from superfish_ng.curved_selection_transfer import replay_curved_selection_transfer

        def browser(value):
            if type(value) is dict:
                return {k: browser(v) for k, v in value.items()}
            if type(value) is list:
                return [browser(v) for v in value]
            return int(value) if type(value) is float and value.is_integer() else value

        projects, request = fixture()
        for policy in ('intersects', 'contained'):
            document = transfer_curved_cell_selection(*projects, dict(request, coverage_policy=policy))
            for serialized in (json.loads(json.dumps(document)), browser(document)):
                before = deepcopy(serialized)
                replayed = replay_curved_selection_transfer(serialized)
                self.assertEqual(replayed, document)
                self.assertEqual(serialized, before)
                replayed['selection']['coverage'][0]['covered_fraction'][0] += 1
                self.assertEqual(serialized, before)

    def test_top_level_version_metadata_and_project_refusals(self):
        document = self.document()
        mutations = []
        for key in document:
            mutations.append(('missing '+key, lambda d, k=key: d.pop(k)))
        for key, value in (('extra', 1), ('schema_version', True), ('schema_version', 2.),
                           ('schema_version', 1), ('schema_version', 3),
                           ('document_type', 'other'), ('status', 'FAIL'),
                           ('scope', 'physical accuracy verified'), ('physical_error_bound', 0),
                           ('base_correspondence', {}), ('previous_project', None)):
            mutations.append((str((key, value)), lambda d, k=key, v=value: d.update({k: v})))
        mutations.extend([
            ('unknown project field', lambda d: d['previous_project'].update(extra=1)),
            ('source point count', lambda d: d['current_project']['mesh_data']['points'].pop()),
            ('reflection', lambda d: d['current_project'].update(reflect_full=True)),
            ('request version', lambda d: d['request'].update(schema_version=1)),
            ('source selection', lambda d: d['request'].update(selected_cells=[1])),
            ('chart boundary', lambda d: d['request']['reference_vertices'][1][4].__setitem__(0, .125)),
        ])
        self.assert_bad_documents(document, mutations)

    def test_all_selection_and_partition_evidence_is_reconstructed_with_strict_types(self):
        document = self.document()
        mutations = []
        for group in ('selection', 'reference_partition'):
            for key in document[group]:
                mutations.append(('missing '+group+'.'+key, lambda d, g=group, k=key: d[g].pop(k)))
            mutations.append(('extra '+group, lambda d, g=group: d[g].update(extra=1)))
        mutations.extend([
            ('integer cell as float', lambda d: d['selection']['selected_cells'].__setitem__(0, 0.)),
            ('integer cell as bool', lambda d: d['selection']['coverage'][0].update(current_cell=False)),
            ('fraction bool numerator', lambda d: d['selection']['coverage'][0]['covered_fraction'].__setitem__(0, True)),
            ('fraction float denominator', lambda d: d['selection']['coverage'][0]['covered_fraction'].__setitem__(1, 3.)),
            ('source area', lambda d: d['selection']['source_reference_area'].__setitem__(0, 2)),
            ('cell area check', lambda d: d['selection']['source_cell_area_checks'][0].update(previous_cell=True)),
            ('overlap parent', lambda d: d['selection']['overlaps'][0].update(previous_cell=1)),
            ('overlap barycentric', lambda d: d['selection']['overlaps'][0]['previous_barycentric'][0][0].__setitem__(0, 9)),
            ('partition triangle', lambda d: d['reference_partition']['triangles'][0].update(current_cell=True)),
            ('partition coverage', lambda d: d['reference_partition']['previous_covered_areas'][0].__setitem__(0, 2)),
            ('pair count', lambda d: d['selection'].update(total_pair_tests=41.)),
            ('empty contained forgery', lambda d: d['selection'].update(selected_cells=[])),
        ])
        self.assert_bad_documents(document, mutations)

    def test_saved_budgets_raw_duplicate_keys_and_nonfinite_requests_are_rejected(self):
        import json
        from superfish_ng.curved_selection_transfer import replay_curved_selection_transfer
        document = self.document()
        self.assert_bad_documents(document, [
            ('pair budget', lambda d: d['request'].update(max_pair_tests=40)),
            ('triangle budget', lambda d: d['request'].update(max_triangles=3)),
            ('boolean budget', lambda d: d['request'].update(max_triangles=True)),
            ('nonfinite chart', lambda d: d['request']['reference_vertices'][0][0].__setitem__(0, float('inf'))),
        ])
        for raw in (json.dumps(document).replace('"schema_version": 2', '"schema_version": 2, "schema_version": 2', 1),
                    json.dumps(document).replace('"max_pair_tests": 100000', '"max_pair_tests": 100000, "max_pair_tests": 100000', 1)):
            with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
                parse_json(raw)
        bad = deepcopy(document)
        bad['request']['reference_vertices'][0][0][0] = float('nan')
        with self.assertRaises(ValueError):
            replay_curved_selection_transfer(parse_json(json.dumps(bad)))

    def test_non_nested_frozen_and_original_symmetry_saved_reconstruction(self):
        from superfish_ng.curved_selection_transfer import replay_curved_selection_transfer
        from superfish_ng.frozen_curved_refinement import freeze_curved_refinement
        projects, request = fixture()
        projects = [replace(p, case=replace(p.case, curved_refinement_steps=(
            Step('uniform'), Step('marked', (side,), 1.)))) for side, p in enumerate(projects)]
        for tag in ('electric_symmetry', 'magnetic_symmetry'):
            inputs = [symmetry(p, 'z_min', tag) for p in projects]
            for frozen in (False, True):
                inputs = [freeze_curved_refinement(p) for p in inputs] if frozen else inputs
                document = transfer_curved_cell_selection(*inputs, request)
                self.assertEqual(replay_curved_selection_transfer(document), document)

    def test_cli_both_policies_exclusive_output_raw_refusals_and_portable_replay(self):
        from contextlib import redirect_stdout, redirect_stderr
        import io
        import json
        import tempfile
        from superfish_ng.cli import main
        projects, request = fixture()

        def run(args):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                return main(args)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, project in zip(('old', 'new'), projects):
                project.save(root / (name+'.json'))
            original = {p: p.read_bytes() for p in root.iterdir()}
            for policy in ('intersects', 'contained'):
                value = dict(request, coverage_policy=policy)
                request_path = root / 'request.json'
                request_path.write_text(json.dumps(value))
                output = root / (policy+'.json')
                args = ['transfer-curved-selection', str(root/'old.json'), str(root/'new.json'),
                        '--request', str(request_path), '--out', str(output)]
                self.assertEqual(run(args), 0)
                saved = output.read_bytes()
                self.assertEqual(parse_json(saved.decode()), transfer_curved_cell_selection(*projects, value))
                self.assertEqual(run(args), 2)
                self.assertEqual(output.read_bytes(), saved)
                self.assertEqual(run(['replay-curved-selection-transfer', str(output)]), 0)
                self.assertEqual(output.read_bytes(), saved)
            invalid_requests = [
                '{"schema_version":2,"schema_version":2}',
                json.dumps(dict(request, max_pair_tests=40)),
                json.dumps(dict(request, reference_vertices=[[[float('nan'), 0], [1, 0], [0, 1]]]*2)),
            ]
            for i, raw in enumerate(invalid_requests):
                request_path.write_text(raw)
                output = root / ('invalid-'+str(i)+'.json')
                args[-1] = str(output)
                self.assertEqual(run(args), 2)
                self.assertFalse(output.exists())
            bad = self.document()
            bad['selection']['coverage'][0]['covered_fraction'][0] = True
            bad_path = root/'bad.json'
            bad_path.write_text(json.dumps(bad))
            saved_bad = bad_path.read_bytes()
            self.assertEqual(run(['replay-curved-selection-transfer', str(bad_path)]), 2)
            self.assertEqual(bad_path.read_bytes(), saved_bad)
            self.assertEqual(original, {p: p.read_bytes() for p in original})
            moved = root/'moved'
            moved.mkdir()
            for policy in ('intersects', 'contained'):
                (root/(policy+'.json')).rename(moved/(policy+'.json'))
            for p in original:
                p.unlink()
            request_path.unlink()
            for p in moved.iterdir():
                before = p.read_bytes()
                self.assertEqual(run(['replay-curved-selection-transfer', str(p)]), 0)
                self.assertEqual(p.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()

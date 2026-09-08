# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import unittest
from superfish_ng.conics import EllipseArc, HyperbolaArc
from superfish_ng.certified_construction import certified_construction_candidates, connect_certified_arcs
from superfish_ng.tangent_construction import construct_tangent_case, save_construction, read_construction


def certified_request():
    data = json.loads((Path(__file__).resolve().parents[1]/'examples/construction/capsule_request.json').read_text())
    data['schema_version'] = 2
    data['controls'].pop('parameter_guard')
    data['controls'].update(max_contact_width_m=1e-12, endpoint_width=2.**-100, max_series_terms=96,
                            fraction_width=2.**-44, max_fraction_steps=64, normal_width=2.**-56)
    return data


class CertifiedConstructionTests(unittest.TestCase):
    def test_interval_selected_trim_and_position_bound(self):
        a = EllipseArc((0,0),(1,1),math.pi,-math.pi)
        b = replace(a,center_zr_m=(4,0))
        result = connect_certified_arcs(a,b,candidate_index=0,position_tolerance_m=1e-9,angle_tolerance_rad=1e-8)
        self.assertEqual(len(result['curves']),3)
        item = result['selected_candidate']
        self.assertEqual(item['connection_direction'],'FORWARD')
        self.assertTrue(all(x <= 1e-9 for x in item['trim_contact_error_bounds_m']))
        for chosen, fraction in zip(item['contact_fractions'],item['parameter_fractions']):
            self.assertLessEqual(fraction['interval'][0],chosen)
            self.assertGreaterEqual(fraction['interval'][1],chosen)
        self.assertEqual(result['curves'][0].center_zr_m,a.center_zr_m)
        self.assertEqual(result['curves'][2].semiaxes_m,b.semiaxes_m)

    def test_exact_end_start_preserved_and_empty_arc_rejected(self):
        a = HyperbolaArc((0,0),(1,1),-1.,0.)
        b = HyperbolaArc((0,4),(1,1),0.,1.)
        result = connect_certified_arcs(a,b,candidate_index=0,position_tolerance_m=1e-10,angle_tolerance_rad=1e-8)
        self.assertEqual(result['curves'][0],a)
        self.assertEqual(result['curves'][2],b)
        preview = certified_construction_candidates(replace(a,start_parameter=0.,end_parameter=1.),b,
                                                     position_tolerance_m=1e-10,angle_tolerance_rad=1e-8)
        self.assertEqual(preview['candidates'][0]['connection_direction'],'EMPTY_ARC')
        with self.assertRaises(ValueError):
            connect_certified_arcs(replace(a,start_parameter=0.,end_parameter=1.),b,candidate_index=0,
                                   position_tolerance_m=1e-10,angle_tolerance_rad=1e-8)

    def test_v2_case_replay_and_v1_still_has_unchanged_contract(self):
        request = certified_request()
        original = deepcopy(request)
        built = construct_tangent_case(request,candidate_index=0)
        self.assertEqual(request,original)
        self.assertEqual(built['schema_version'],2)
        self.assertEqual(built['status'],'CASE_VALIDATED')
        self.assertEqual(built['enumeration']['arc_filter_status'],'CERTIFIED_MEMBERSHIP_AND_FRACTIONS')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'construction.json'
            save_construction(request,path,candidate_index=0)
            self.assertEqual(read_construction(path),built)
        old = json.loads((Path(__file__).resolve().parents[1]/'examples/construction/capsule_request.json').read_text())
        legacy = construct_tangent_case(old,candidate_index=0)
        self.assertEqual(legacy['schema_version'],1)
        self.assertEqual(legacy['enumeration']['arc_filter_status'],'NUMERICALLY_ASSESSED')
        self.assertNotIn('trim_contact_error_bounds_m',legacy['enumeration']['candidates'][0])

    def test_too_small_position_tolerance_and_unknown_controls_fail(self):
        a = EllipseArc((0,0),(1,1),math.pi,-math.pi)
        b = replace(a,center_zr_m=(4,0))
        with self.assertRaises(ValueError):
            connect_certified_arcs(a,b,candidate_index=0,position_tolerance_m=1e-30,angle_tolerance_rad=1e-8)
        request = certified_request();request['controls']['parameter_guard']=1e-8
        with self.assertRaises(ValueError):construct_tangent_case(request)
        for invalid in (True,-1,100):
            with self.assertRaises(ValueError):
                connect_certified_arcs(a,b,candidate_index=invalid,position_tolerance_m=1e-9,angle_tolerance_rad=1e-8)

    def test_v2_fem_scaling_area_volume_and_gui_response(self):
        from superfish_ng.config import Case
        from superfish_ng.solver import solve
        from superfish_ng.rf import quantities
        from superfish_ng.gui import tangent_document
        request = certified_request()
        built = construct_tangent_case(request,candidate_index=0)
        gui = tangent_document(request,candidate_index=0)
        self.assertEqual(gui['construction'],built)
        self.assertEqual(tangent_document(gui['serialized'],replay=True)['construction'],built)
        case = Case.from_dict(built['case'])
        self.assertAlmostEqual(case.curved_contour.area_m2,.4*.1+math.pi*.1**2/2,places=12)
        self.assertAlmostEqual(case.curved_contour.volume_m3,math.pi*.1**2*.4+4*math.pi*.1**3/3,places=12)
        scaled = deepcopy(request)
        g = scaled['case_template']['geometry']
        for curve in g['curves']:
            for key in ('center_zr_m','semiaxes_m','start_zr_m','end_zr_m'):
                if key in curve:curve[key]=[2*x for x in curve[key]]
        for key in ('join_tolerance_m','minimum_gap_m','chord_tolerance_m'):g[key]*=2
        scaled['case_template']['mesh']['contour_mesh']['max_edge_m']*=2
        for key in ('position_tolerance_m','max_contact_width_m'):scaled['controls'][key]*=2
        large = Case.from_dict(construct_tangent_case(scaled,candidate_index=0)['case'])
        a,b=quantities(case,solve(case)),quantities(large,solve(large))
        self.assertAlmostEqual(b['frequency_hz']/a['frequency_hz'],.5,places=10)
        for key in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs'):
            self.assertAlmostEqual(b[key]/a[key],1.,places=9)

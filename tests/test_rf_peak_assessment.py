# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.rf_peak_assessment import assess_rf_peaks,save_rf_peaks,read_rf_peaks,replay_rf_peaks

class RFPeakAssessmentTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
    def save(self,case,name):
        run=self.root/name;save_run(case,solve(case),run);return run

    def test_affine_orders_energy_scaling_and_rank_are_separate_from_accuracy(self):
        for order in (1,2):
            case=Case(((0.,.1),(.2,.1)),nr=4,nz=5,modes=2,element_order=order)
            a=self.save(case,f'p{order}');b=self.save(replace(case,normalization_j=4.),f'p{order}-u4')
            first=assess_rf_peaks(a,mode=1);second=assess_rf_peaks(b,mode=1)
            self.assertEqual(first['mode_index'],1);self.assertEqual(first['status'],'DISCRETE_BOUNDS_ONLY')
            self.assertEqual(first['mesh_convergence'],'UNASSESSED');self.assertIsNone(first['physical_error_bound'])
            self.assertEqual(first['rf'],json.loads((a/'results.json').read_text())['modes'][1])
            for key in ('epk_v_per_m','hpk_a_per_m','bpk_t'):
                np.testing.assert_allclose(second['intervals'][key],np.array(first['intervals'][key])*2,rtol=2e-9)
            for key in ('epk_over_eacc','bpk_over_eacc_mt_per_mv_per_m'):
                np.testing.assert_allclose(second['intervals'][key],first['intervals'][key],rtol=2e-9)

    def test_curved_saved_replay_and_cli_do_not_solve_again(self):
        case=replace(Case.load('examples/curved_ellipse.json'),geometry_order=2)
        run=self.save(case,'curve');path=self.root/'peaks.json'
        with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('must not solve')):
            report=save_rf_peaks(run,path);self.assertEqual(read_rf_peaks(path),report)
        q=json.loads((run/'results.json').read_text())['modes'][0]
        self.assertEqual(report['intervals']['epk_v_per_m'],[q['epk_discrete_lower_bound_v_per_m'],q['epk_discrete_upper_bound_v_per_m']])
        self.assertFalse(report['geometry_approximation_assessed'])
        from superfish_ng.cli import main
        self.assertEqual(main(['assess-rf-peaks',str(run),'--out',str(self.root/'cli.json')]),0)
        self.assertEqual(main(['replay-rf-peaks',str(self.root/'cli.json')]),0)
        self.assertEqual(read_rf_peaks(self.root/'cli.json'),report)

    def test_reentrant_and_tampered_results_never_claim_physical_acceptance(self):
        case=Case(((0.,.1),(.1,.075),(.2,.1)),nr=4,nz=5,element_order=2)
        run=self.save(case,'neck');r=assess_rf_peaks(run)
        self.assertEqual(r['geometry_diagnostic']['status'],'SINGULAR_GEOMETRY');self.assertEqual(r['status'],'DISCRETE_BOUNDS_ONLY')
        for key in ('intervals','source','conventions','rf','geometry_diagnostic','physical_error_bound'):
            bad=deepcopy(r);bad[key]='altered'
            with self.assertRaisesRegex(ValueError,'replay'):replay_rf_peaks(bad)
        for mode in (True,-1,case.modes):
            with self.assertRaises(ValueError):assess_rf_peaks(run,mode=mode)
        (run/'case.json').write_text((run/'case.json').read_text()+' ')
        with self.assertRaises(ValueError):replay_rf_peaks(r)

    def test_gui_binds_serialized_document_to_completed_result_and_mode(self):
        from superfish_ng.jobs import JobManager
        from superfish_ng.gui_rf_peaks import rf_peak_response
        run=self.save(Case(((0.,.1),(.2,.1)),nr=4,nz=5,modes=2,element_order=2),'source')
        manager=JobManager(self.root/'jobs');self.addCleanup(manager.close)
        job=manager.import_result(run);data=dict(id=job,mode=2)
        response=rf_peak_response(manager,'assess-rf-peaks',data)
        self.assertEqual(json.loads(response['serialized']),response['document'])
        self.assertEqual(rf_peak_response(manager,'replay-rf-peaks',dict(data,document=response['serialized'])),response)
        with self.assertRaisesRegex(ValueError,'result and mode'):
            rf_peak_response(manager,'replay-rf-peaks',dict(id=job,mode=1,document=response['serialized']))
        bad=response['serialized'].replace('"schema_version": 1','"schema_version": 1, "schema_version": 1',1)
        with self.assertRaisesRegex(ValueError,'duplicate JSON key'):
            rf_peak_response(manager,'replay-rf-peaks',dict(data,document=bad))
        for invalid in (dict(data,mode=True),dict(data,extra=1)):
            with self.assertRaises(ValueError):rf_peak_response(manager,'assess-rf-peaks',invalid)

    def test_historical_curved_rf_without_peak_fields_can_be_assessed(self):
        import csv
        from superfish_ng.curved_rf import quantities_curved
        from superfish_ng.completion import digest
        case=replace(Case.load('examples/curved_ellipse.json'),geometry_order=2)
        solution=solve(case);run=self.root/'historical';result=save_run(case,solution,run)
        del result['surface_extrema'];del result['surface_corner_diagnostics']
        result['modes']=[quantities_curved(solution,i,include_surface_peaks=False) for i in range(case.modes)]
        (run/'results.json').write_text(json.dumps(result))
        with (run/'modes.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(result['modes'][0]));writer.writeheader();writer.writerows(result['modes'])
        marker=json.loads((run/'save_complete.json').read_text())
        for name in ('results.json','modes.csv'):marker['files'][name]=digest(run/name)
        (run/'save_complete.json').write_text(json.dumps(marker))
        report=assess_rf_peaks(run)
        self.assertNotIn('epk_over_eacc_estimate',report['rf'])
        self.assertIsNotNone(report['intervals']['epk_over_eacc'])
        self.assertEqual(report['rf'],result['modes'][0]);self.assertEqual(replay_rf_peaks(report),report)

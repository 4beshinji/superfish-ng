# SPDX-License-Identifier: Apache-2.0
"""TE plots/probes preserve field components, phasors and native identity."""
import json
import tempfile
import unittest
from pathlib import Path
from dataclasses import replace
import numpy as np
from superfish_ng import solve
from superfish_ng.io import save_run
from superfish_ng.constants import MU0
from superfish_ng.te import TEFieldSampler
from superfish_ng.te_display import display_te_fields
from superfish_ng.saved import export_radial_probe
from test_te import cavity, reference
from test_te_curved import sphere


class TEDisplayTests(unittest.TestCase):
    def test_display_and_probe_components_all_spaces(self):
        for case in (cavity(order=1,n=8,modes=1),cavity(n=8,modes=1),replace(sphere(1),modes=1)):
            with self.subTest(order=case.element_order,geometry=case.geometry_order), tempfile.TemporaryDirectory() as tmp:
                solution=solve(case);run=Path(tmp)/'run';save_run(case,solution,run)
                p,t,e,fields=display_te_fields(solution)
                np.testing.assert_array_equal(e,p[:,0]*solution.coefficients_v_per_m2[:,0])
                self.assertEqual(len(t),len(fields['Hz_quadrature_A_per_m']))
                if case.geometry_order==1:
                    independent=TEFieldSampler(solution).evaluate(p[t].mean(axis=1))
                    for key in ('Ephi_V_per_m','Hr_quadrature_A_per_m','Hz_quadrature_A_per_m'):
                        np.testing.assert_allclose(fields[key],independent[key],atol=1e-6,rtol=1e-10)
                z=float((p[:,1].min()+p[:,1].max())/2)
                out=Path(tmp)/'probe.csv';metadata=export_radial_probe(run,out,z)
                rows=np.loadtxt(out,delimiter=',',skiprows=1)
                sampled=TEFieldSampler(solution).evaluate(rows[:,:2],outside='nan')
                for col,key in enumerate(('Ephi_V_per_m','Hr_quadrature_A_per_m','Hz_quadrature_A_per_m'),2):
                    np.testing.assert_allclose(rows[:,col],sampled[key],rtol=1e-10,atol=1e-6)
                np.testing.assert_allclose(rows[:,5:7],MU0*rows[:,3:5])
                self.assertEqual(rows[0,2],0);self.assertEqual(rows[0,3],0)
                self.assertIn('+i',metadata['conventions']['magnetic_phasor'])
                self.assertIn('te_complete.json',metadata['native_source_sha256'])
                self.assertEqual(metadata,json.loads(out.with_suffix('.csv.json').read_text()))
                with self.assertRaises(FileExistsError):export_radial_probe(run,out,z)

    def test_cylinder_probe_matches_independent_bessel_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)/'run';save_run(cavity(n=16,modes=1),solve(cavity(n=16,modes=1)),run)
            out=Path(tmp)/'probe.csv';export_radial_probe(run,out,.073)
            rows=np.loadtxt(out,delimiter=',',skiprows=1);expected=reference()[2](rows[:,:2])
            for col,key in enumerate(('Ephi_V_per_m','Hr_quadrature_A_per_m','Hz_quadrature_A_per_m'),2):
                self.assertLess(np.max(abs(rows[:,col]-expected[key]))/np.max(abs(expected[key])),.01,key)

    def test_plot_dispatch_and_strict_mode(self):
        try:from superfish_ng.visualize import plot_mode
        except ImportError:self.skipTest('optional Matplotlib unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)/'run';save_run(cavity(n=6,modes=1),solve(cavity(n=6,modes=1)),run)
            for mode in (True,0,2):
                with self.assertRaises(ValueError):plot_mode(run,Path(tmp)/'bad.png',mode)
            out=Path(tmp)/'fields.png';result=plot_mode(run,out,show_mesh=True)
            self.assertTrue(out.read_bytes().startswith(b'\x89PNG'))
            self.assertIn('Ephi_V_per_m',result['radial_fields'])
            self.assertNotIn('Ez_quadrature_V_per_m',result['radial_fields'])

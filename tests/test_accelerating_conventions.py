# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from scipy.integrate import quad
from superfish_ng import Case, solve
from superfish_ng.constants import C0, TAU
from superfish_ng.rf import quantities


class AcceleratingConventionTests(unittest.TestCase):
    def test_phase_and_length_change_only_their_defined_quantities(self):
        case = Case(((0., .1), (.2, .1)), nr=8, nz=12, modes=1)
        sol = solve(case)
        base = quantities(case, sol)
        shifted = quantities(replace(case, phase_origin_m=-.027), sol)
        k = TAU*base['frequency_hz']/C0
        v = complex(base['voltage_real_v'],base['voltage_imag_v'])*np.exp(1j*k*.027)
        self.assertAlmostEqual(abs(complex(shifted['voltage_real_v'],shifted['voltage_imag_v'])-v)/abs(v),0,places=12)
        scaled = quantities(replace(case, active_length_m=.4), sol)
        for key in ['vacc_v','r_over_q_accelerator_ohm','q0','geometry_factor_ohm','stored_energy_j','transit_time_factor_abs']:
            self.assertAlmostEqual(shifted[key]/base[key],1,places=12)
            self.assertEqual(scaled[key],base[key])
        self.assertEqual(scaled['eacc_v_per_m'],base['eacc_v_per_m']/2)
        self.assertEqual(scaled['epk_over_eacc_estimate'],base['epk_over_eacc_estimate']*2)

    def test_clipped_signed_field_and_low_beta_against_independent_quadrature(self):
        from superfish_ng.rf import accelerating_voltage
        z=np.array([0.,.031,.072,.2]); field=np.array([1.,-2.,3.,1.])
        case=Case(((0.,.1),(.2,.1)),voltage_interval_m=(.017,.139),phase_origin_m=.041)
        for k in [0.,.01,13.,1200.]:
            v, absolute=accelerating_voltage(case,z,field,k)
            a,b=case.voltage_interval_m
            points=[p for p in z if a<p<b]
            real=quad(lambda x:np.interp(x,z,field)*np.cos(k*(x-.041)),a,b,points=points,epsabs=1e-12,limit=300)[0]
            imag=quad(lambda x:np.interp(x,z,field)*np.sin(k*(x-.041)),a,b,points=points,epsabs=1e-12,limit=300)[0]
            absolute_ref=quad(lambda x:abs(np.interp(x,z,field)),a,b,points=points,epsabs=1e-12,limit=300)[0]
            self.assertLess(abs(v-complex(real,imag))/absolute_ref,1e-10)
            self.assertAlmostEqual(absolute/absolute_ref,1,places=10)

    def test_strict_schema_and_saved_roundtrip(self):
        from superfish_ng.io import save_run
        from superfish_ng.saved import read_solution
        case=Case(((0.,.1),(.2,.1)),nr=5,nz=6,modes=1,active_length_m=.15,
                  voltage_interval_m=(.02,.17),phase_origin_m=-.1)
        self.assertEqual(case.to_dict()['schema_version'],3)
        self.assertEqual(Case.from_dict(case.to_dict()),case)
        for key,bad in [('active_length_m',0),('active_length_m',True),('phase_origin_m',float('nan')),
                        ('voltage_interval_m',(0,.21)),('voltage_interval_m',(.1,.1)),
                        ('voltage_interval_m',(True,.2))]:
            with self.subTest(key=key,bad=bad),self.assertRaises(ValueError):replace(case,**{key:bad})
        for key in ['active_length_m','voltage_interval_m','phase_origin_m']:
            data=case.to_dict(); data['rf'][key]=None
            with self.assertRaises(ValueError):Case.from_dict(data)
        data=case.to_dict();data.pop('model');data['schema_version']=2
        with self.assertRaises(ValueError):Case.from_dict(data)
        with tempfile.TemporaryDirectory() as tmp:
            save_run(case,solve(case),Path(tmp)/'run')
            saved=read_solution(Path(tmp)/'run')
            self.assertEqual(saved.case,case)
            self.assertEqual(saved.results['modes'][0]['phase_origin_m'],-.1)

    def test_reflection_maps_interval_and_origin_and_rejects_disjoint_windows(self):
        from superfish_ng.symmetry import reflect_solution
        for side in ['z_min','z_max']:
            interval=(0.,.08) if side=='z_min' else (.02,.1)
            case=Case(((0.,.1),(.1,.1)),nr=6,nz=8,modes=1,**{side:'electric_symmetry'},
                      active_length_m=.07,voltage_interval_m=interval,phase_origin_m=.03)
            full,sol=reflect_solution(case,solve(case))
            np.testing.assert_allclose(full.voltage_interval_m,(.02,.18),atol=1e-16)
            self.assertEqual(full.active_length_m,.14)
            self.assertAlmostEqual(full.phase_origin_m,.13 if side=='z_min' else .03)
            expected=replace(full,phase_origin_m=0.)
            self.assertAlmostEqual(quantities(full,sol)['vacc_v']/quantities(expected,sol)['vacc_v'],1,places=12)
            from superfish_ng.mesh_input import mesh_to_dict
            # Re-solve the full mesh independently: opposite diagonal choices
            # otherwise introduce discretization differences into this identity.
            independently_solved=quantities(full,solve(full,mesh_data=mesh_to_dict(sol.mesh)))
            reflected=quantities(full,sol)
            for key in ['frequency_hz','stored_energy_j','r_over_q_accelerator_ohm','geometry_factor_ohm']:
                self.assertAlmostEqual(reflected[key]/independently_solved[key],1,places=8)
            bad=replace(case,voltage_interval_m=(.02,.08))
            with self.assertRaisesRegex(ValueError,'interval'):
                reflect_solution(bad,solve(bad))

    def test_analytical_window_reference_against_independent_integration(self):
        from superfish_ng.analytic import pillbox_tm_mode
        a,b,origin=.017,.173,-.021
        for p in [0,1,3]:
            ref=pillbox_tm_mode(.1,.2,p=p,beta=.03,active_length_m=.18,
                                voltage_interval_m=(a,b),phase_origin_m=origin)
            k=TAU*ref['frequency_hz']/(.03*C0)
            kz=p*np.pi/.2
            field=lambda z:ref['e0_v_per_m']*np.cos(kz*z)
            parts=[quad(lambda z:field(z)*fn(k*(z-origin)),a,b,epsabs=1e-7,limit=500)[0]
                   for fn in [np.cos,np.sin]]
            voltage=complex(*parts)
            zeros=[(j+.5)*.2/p for j in range(p) if a<(j+.5)*.2/p<b] if p else []
            absolute=quad(lambda z:abs(field(z)),a,b,points=zeros,epsabs=1e-7,limit=500)[0]
            self.assertLess(abs(complex(ref['voltage_real_v'],ref['voltage_imag_v'])-voltage)/absolute,1e-10)
            self.assertAlmostEqual(ref['transit_time_factor_abs'],abs(voltage)/absolute,places=10)

    def test_saved_analytical_comparison_uses_selected_voltage_window(self):
        from superfish_ng.cli import main
        from superfish_ng.saved import compare_pillbox
        case=Case(((0.,.1),(.2,.1)),nr=32,nz=48,modes=2,active_length_m=.13,
                  voltage_interval_m=(.021,.173),phase_origin_m=.027)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run'
            source=Path(tmp)/'case.json';source.write_text(json.dumps(case.to_dict()))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['solve',str(source),'--out',str(path)]),0)
            report=compare_pillbox(path)
            self.assertTrue(all(m['status']=='PASS' for m in report['modes']))

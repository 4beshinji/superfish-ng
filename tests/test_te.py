# SPDX-License-Identifier: Apache-2.0
"""TE spectrum, field phasors, axis regularity, energy and PEC loss."""
import contextlib,io,json,tempfile,unittest
from dataclasses import replace
from pathlib import Path
import numpy as np
from scipy.special import jn_zeros,jv
from superfish_ng import Case,solve
from superfish_ng.constants import EPS0,MU0,C0,TAU
from superfish_ng.model import Model
from superfish_ng.te import TEFieldSampler,te_quantities
from superfish_ng.te_saved import read_te_run
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.cli import main
from superfish_ng.completion import digest


def cavity(scale=1,order=2,n=16,modes=3):
    return Case(((0.,.1*scale),(.2*scale,.1*scale)),nr=n,nz=3*n//2,element_order=order,modes=modes,model=Model(polarization='te'))


def reference(radius=.1,length=.2,energy=1.):
    chi=jn_zeros(1,1)[0];kr=chi/radius;kz=np.pi/length;omega=C0*np.hypot(kr,kz)
    amplitude=np.sqrt(4*energy/(EPS0*np.pi*length*radius**2*jv(0,chi)**2))
    geometry=omega*MU0*(kr**2+kz**2)*length*radius/(2*(kr**2*length+2*kz**2*radius))
    def fields(points):
        r,z=np.asarray(points).T
        return dict(Ephi_V_per_m=amplitude*jv(1,kr*r)*np.sin(kz*z),
            Hr_quadrature_A_per_m=-amplitude*kz/(omega*MU0)*jv(1,kr*r)*np.cos(kz*z),
            Hz_quadrature_A_per_m=amplitude*kr/(omega*MU0)*jv(0,kr*r)*np.sin(kz*z))
    return omega/TAU,geometry,fields


class TETests(unittest.TestCase):
    def test_bessel_spectrum_fields_axis_and_energy_are_independent_checks(self):
        c=cavity();s=solve(c);root=jn_zeros(1,1)[0]
        expected=C0/TAU*np.sqrt((root/.1)**2+(np.arange(1,4)*np.pi/.2)**2)
        self.assertLess(float(np.max(abs(s.frequencies_hz/expected-1))),1e-4)
        points=np.array([[r,z] for r in [0.,.02,.055,.087,.1] for z in [.035,.075,.125,.175]])
        exact=reference()[2](points);actual=TEFieldSampler(s).evaluate(points)
        for name,values in exact.items():self.assertLess(np.max(abs(actual[name]-values))/np.max(abs(values)),.01,name)
        np.testing.assert_array_equal(actual['Ephi_V_per_m'][points[:,0]==0],0)
        np.testing.assert_array_equal(actual['Hr_quadrature_A_per_m'][points[:,0]==0],0)
        self.assertGreater(np.max(abs(actual['Hz_quadrature_A_per_m'][points[:,0]==0])),0)
        q=te_quantities(s);self.assertAlmostEqual(q['stored_energy_j'],1.,places=10)
        self.assertAlmostEqual(q['electric_energy_j'],q['magnetic_energy_j'],places=10)
        self.assertLess(abs(q['geometry_factor_ohm']/reference()[1]-1),.005)
        self.assertIsNone(q['r_over_q_accelerator_ohm']);self.assertIsNone(q['r_over_q_circuit_ohm'])
        self.assertIsNone(q['vacc_v']);self.assertIn('NOT_APPLICABLE',q['accelerating_quantities_status'])

    def test_ritz_p1_p2_and_maxwell_scaling(self):
        for order in (1,2):
            a=solve(cavity(order=order,n=8,modes=1));b=solve(cavity(order=order,n=16,modes=1))
            f=reference()[0]
            self.assertGreater(a.frequencies_hz[0],b.frequencies_hz[0]);self.assertGreater(b.frequencies_hz[0],f)
        a=solve(cavity(modes=1));b=solve(cavity(scale=2,modes=1));qa,qb=te_quantities(a),te_quantities(b)
        self.assertLess(abs(qb['frequency_hz']*2/qa['frequency_hz']-1),1e-10)
        self.assertLess(abs(qb['geometry_factor_ohm']/qa['geometry_factor_ohm']-1),1e-10)
        self.assertLess(abs(qb['q0']/qa['q0']/np.sqrt(2)-1),1e-10)
        points=np.array([[.02,.06],[.06,.13]])
        fa,fb=TEFieldSampler(a).evaluate(points),TEFieldSampler(b).evaluate(2*points)
        for name in ('Ephi_V_per_m','Hr_quadrature_A_per_m','Hz_quadrature_A_per_m'):
            np.testing.assert_allclose(fb[name]*2**1.5,fa[name],rtol=1e-9)

    def test_symmetry_boundaries_have_te_parity_and_no_wall_loss(self):
        full=solve(cavity(modes=1));halfcase=replace(cavity(modes=1),profile=((0.,.1),(.1,.1)),z_max='magnetic_symmetry',normalization_j=.5)
        half=solve(halfcase)
        self.assertLess(abs(half.frequencies_hz[0]/full.frequencies_hz[0]-1),1e-4)
        qf,qh=te_quantities(full),te_quantities(half)
        self.assertLess(abs(qh['wall_loss_w']*2/qf['wall_loss_w']-1),.005)
        self.assertLess(abs(qh['geometry_factor_ohm']/qf['geometry_factor_ohm']-1),.005)
        electric=solve(replace(halfcase,z_max='electric_symmetry'))
        self.assertGreater(electric.frequencies_hz[0],half.frequencies_hz[0])

    def test_native_cli_and_refusal_of_tm_consumers_or_forged_fields(self):
        from superfish_ng.project import Project
        from superfish_ng.symmetry import reflect_solution
        for order in (1,2):
            c=cavity(n=6,modes=1,order=order)
            with self.assertRaisesRegex(ValueError,'TE reflected Project'):Project(c,reflect_full=True)
            with self.assertRaisesRegex(ValueError,'TE reflection'):reflect_solution(c,solve(c))
            with self.assertRaisesRegex(ValueError,'axial accelerating'):replace(c,active_length_m=.1)
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);casefile=root/'case.json';casefile.write_text(json.dumps(c.to_dict()))
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(['solve',str(casefile),'--out',str(root/'run')]),0)
                    self.assertEqual(main(['replay-te',str(root/'run')]),0)
                saved=read_te_run(root/'run');np.testing.assert_array_equal(saved.coefficients_v_per_m2,solve(c).coefficients_v_per_m2)
                with self.assertRaisesRegex(ValueError,'TE saved fields'):read_solution(root/'run')
                result=json.loads((root/'run/results.json').read_text());self.assertEqual(result['field_space']['coefficient_unit'],'V/m^2')
                self.assertIn('Ephi_V_per_m',(root/'run/mode_001.vtk').read_text())
                file=root/'run/fields.npz'
                with np.load(file) as data:v=data['coefficients_v_per_m2'];f=data['frequencies_hz']
                v*=1.01;np.savez_compressed(file,coefficients_v_per_m2=v,frequencies_hz=f)
                with self.assertRaisesRegex(ValueError,'bytes differ'):read_te_run(root/'run')
                marker=root/'run/te_complete.json';manifest=json.loads(marker.read_text());manifest['files']['fields.npz']=digest(file);marker.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError,'normalization'):read_te_run(root/'run')

    def test_native_metadata_must_preserve_te_meaning_even_with_new_hashes(self):
        from superfish_ng.curved_solution import solve_curved
        c=cavity(n=4,modes=1)
        with self.assertRaisesRegex(ValueError,'geometry_order=2 requires'):solve_curved(c)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run';save_run(c,solve(c),path)
            original=json.loads((path/'results.json').read_text());marker=json.loads((path/'te_complete.json').read_text())
            changes=[lambda r:r['conventions'].update(magnetic_phasor='-i times quadrature amplitude'),
                     lambda r:r['modes'][0].update(r_over_q_accelerator_ohm=0.),
                     lambda r:r['modes'][0].update(mode_index=True),
                     lambda r:r['field_space'].update(basis='Lagrange u=Hphi/r'),
                     lambda r:r.update(normalization_j=True),lambda r:r.update(extra=1)]
            for change in changes:
                with self.subTest(change=change):
                    r=json.loads(json.dumps(original));change(r);(path/'results.json').write_text(json.dumps(r))
                    marker['files']['results.json']=digest(path/'results.json');(path/'te_complete.json').write_text(json.dumps(marker))
                    with self.assertRaises(ValueError):read_te_run(path)

    def test_tm_native_reader_rejects_te_declaration_without_te_marker(self):
        import hashlib
        c=replace(cavity(n=4,modes=1),model=Model())
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run';save_run(c,solve(c),p)
            data=json.loads((p/'case.json').read_text());data['model']['polarization']='te';(p/'case.json').write_text(json.dumps(data))
            result=json.loads((p/'results.json').read_text());result['case']=data
            result['case_sha256']=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            (p/'results.json').write_text(json.dumps(result))
            marker=json.loads((p/'save_complete.json').read_text())
            for name in ('case.json','results.json'):marker['files'][name]=digest(p/name)
            (p/'save_complete.json').write_text(json.dumps(marker))
            with self.assertRaisesRegex(ValueError,'TE Case'):read_solution(p)

    def test_external_mesh_and_common_sampling_keep_te_units(self):
        from superfish_ng.mesh_input import mesh_to_dict
        from superfish_ng.sampling import FieldSampler
        from superfish_ng.rf import quantities
        for order in (1,2):
            c=cavity(n=6,modes=2,order=order);original=solve(c);data=mesh_to_dict(original.mesh)
            external=solve(c,mesh_data=data)
            np.testing.assert_array_equal(external.frequencies_hz,original.frequencies_hz)
            np.testing.assert_array_equal(external.coefficients_v_per_m2,original.coefficients_v_per_m2)
            self.assertEqual(quantities(c,external),te_quantities(original))
            fields=FieldSampler.from_solution(external).evaluate([[0.,.1],[.04,.07]])
            self.assertEqual(set(fields),{'Ephi_V_per_m','Hr_quadrature_A_per_m','Hz_quadrature_A_per_m','inside'})
            self.assertEqual(fields['Ephi_V_per_m'][0],0.)
            invalid=json.loads(json.dumps(data));invalid['boundary_tags'][0]='unknown'
            with self.assertRaises(ValueError):solve(c,mesh_data=invalid)

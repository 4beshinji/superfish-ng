# SPDX-License-Identifier: Apache-2.0
"""Independent cutoff invariants and strict Cartesian native/CLI contracts."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng import Case
from superfish_ng.constants import C0,EPS0,MU0,TAU
from superfish_ng.planar import PlanarCase,solve_planar,PlanarFieldSampler,planar_quantities
from superfish_ng.planar_saved import save_planar_run,read_planar_run


class PlanarRFTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases={pol:PlanarCase(.31,.2,polarization=pol,nx=16,ny=16,modes=4) for pol in ('te','tm')}
        cls.solutions={pol:solve_planar(c) for pol,c in cls.cases.items()}

    def test_strict_coordinate_material_unit_and_boundary_contract(self):
        case=self.cases['te'];data=case.to_dict();self.assertEqual(PlanarCase.from_dict(data),case)
        for section,key,value in [('model','coordinates','axisymmetric'),('model','material','dielectric'),
                ('model','boundary','pmc'),('model','propagation_constant_per_m',1),('model','propagation_constant_per_m',False),
                ('geometry','type','circle'),('rf','stored_energy_j',1),('mesh','nx',True),('mesh','element_order',3)]:
            other=json.loads(json.dumps(data));other[section][key]=value
            with self.assertRaises(ValueError):PlanarCase.from_dict(other)
        with self.assertRaises(ValueError):Case.from_dict(data)
        for kwargs in ({'width_m':0},{'height_m':float('nan')},{'normalization_j_per_m':False},{'polarization':'tem'}):
            with self.assertRaises(ValueError):replace(case,**kwargs)
        with self.assertRaises(ValueError):solve_planar(replace(case,nx=2,ny=2,element_order=1,modes=10))

    def test_distinct_boundary_spectra_and_te_constant_exclusion(self):
        for pol,solution in self.solutions.items():
            lo=1 if pol=='tm' else 0
            exact=sorted(C0/2*np.hypot(i/.31,j/.2) for i in range(lo,5) for j in range(lo,5) if i+j)[:4]
            np.testing.assert_allclose(solution.frequencies_hz,exact,rtol=2e-4)
            self.assertLess(max(solution.residuals),1e-8)
            if pol=='te':
                self.assertLess(np.max(abs(np.ones(len(solution.coefficients))@(solution.mass@solution.coefficients))),1e-9)
            else:np.testing.assert_array_equal(solution.coefficients[np.unique(solution.space.boundary_dofs)],0)
        self.assertLess(self.solutions['te'].frequencies_hz[0],self.solutions['tm'].frequencies_hz[0])

    def test_signed_maxwell_fields_and_all_complex_components(self):
        points=np.array([[.07,.04],[.14,.13],[.21,.17]])
        for pol,solution in self.solutions.items():
            fields=PlanarFieldSampler(solution).evaluate(points);x,y=points.T;omega=TAU*solution.frequencies_hz[0]
            if pol=='tm':
                a=np.sqrt(8/(EPS0*.31*.2));kx,ky=np.pi/.31,np.pi/.2
                expected=dict(Ez_real_V_per_m=a*np.sin(kx*x)*np.sin(ky*y),
                    Hx_quadrature_A_per_m=a*ky*np.sin(kx*x)*np.cos(ky*y)/(omega*MU0),
                    Hy_quadrature_A_per_m=-a*kx*np.cos(kx*x)*np.sin(ky*y)/(omega*MU0))
                primary='Ez_real_V_per_m'
            else:
                a=np.sqrt(4/(MU0*.31*.2));kx=np.pi/.31
                expected=dict(Hz_real_A_per_m=a*np.cos(kx*x),Ey_quadrature_V_per_m=-a*kx*np.sin(kx*x)/(omega*EPS0))
                primary='Hz_real_A_per_m'
            sign=np.sign(np.dot(fields[primary],expected[primary]))
            self.assertEqual(len(fields),12)
            for key,values in expected.items():
                np.testing.assert_allclose(sign*fields[key],values,rtol=.01,atol=.002*np.max(abs(values)))
            # Exact absent components; TE Ex is discretely small, not forced zero.
            for key in fields.keys()-expected.keys()-({'Ex_quadrature_V_per_m'} if pol=='te' else set()):
                np.testing.assert_array_equal(fields[key],0)
            with self.assertRaises(ValueError):PlanarFieldSampler(solution).evaluate([[.32,.1]])
            with self.assertRaises(ValueError):PlanarFieldSampler(solution).evaluate(points,-1)

    def test_per_length_energy_wall_integral_and_scaling(self):
        for pol,solution in self.solutions.items():
            q=planar_quantities(solution);f=q['frequency_hz'];omega=TAU*f;a,b=.31,.2
            if pol=='te':g=omega*MU0*a*b*.5/(2*b+a)
            else:
                kx,ky=np.pi/a,np.pi/b;g=omega*MU0*(kx*kx+ky*ky)*a*b/(4*(b*kx*kx+a*ky*ky))
            self.assertLess(abs(q['geometry_factor_ohm']/g-1),.02)
            self.assertAlmostEqual(q['electric_energy_j_per_m'],.5,places=9)
            self.assertAlmostEqual(q['magnetic_energy_j_per_m'],.5,places=9)
            self.assertNotIn('stored_energy_j',q);self.assertNotIn('wall_loss_w',q)
            self.assertIsNone(q['r_over_q_accelerator_ohm']);self.assertIsNone(q['r_over_q_circuit_ohm'])
            scaled=solve_planar(replace(solution.case,width_m=2*a,height_m=2*b));other=planar_quantities(scaled)
            self.assertLess(abs(other['frequency_hz']*2/f-1),1e-10)
            self.assertLess(abs(other['geometry_factor_ohm']/q['geometry_factor_ohm']-1),1e-10)
            self.assertLess(abs(other['q0']/q['q0']/np.sqrt(2)-1),1e-10)

    def test_native_physics_replay_rejects_rehashed_corruption(self):
        for pol,solution in self.solutions.items():
            with tempfile.TemporaryDirectory() as temporary:
                folder=Path(temporary)/'native';save_planar_run(solution.case,solution,folder)
                other=read_planar_run(folder);np.testing.assert_array_equal(other.coefficients,solution.coefficients)
                arrays={k:v.copy() for k,v in np.load(folder/'fields.npz').items()}
                arrays['coefficients']*=2;np.savez_compressed(folder/'fields.npz',**arrays)
                manifest=json.loads((folder/'manifest.json').read_text());manifest['files']['fields.npz']=hashlib.sha256((folder/'fields.npz').read_bytes()).hexdigest()
                (folder/'manifest.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError,'normalization'):read_planar_run(folder)

    def test_native_does_not_accept_a_valid_but_wrong_frequency_band(self):
        solution=solve_planar(replace(self.cases['te'],modes=5))
        altered=replace(solution,case=self.cases['te'],coefficients=solution.coefficients[:,1:],frequencies_hz=solution.frequencies_hz[1:])
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError,'lowest positive'):
                save_planar_run(altered.case,altered,Path(temporary)/'bad')

    def test_native_source_change_during_replay_is_rejected(self):
        from superfish_ng import planar_saved
        solution=self.solutions['te']
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/'native';save_planar_run(solution.case,solution,folder)
            original=planar_saved._restore
            def changed(*args,**kwargs):
                value=original(*args,**kwargs)
                with (folder/'case.json').open('a') as stream:stream.write('\n')
                return value
            with patch.object(planar_saved,'_restore',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):read_planar_run(folder)

    def test_probe_preserves_native_directory_and_rejects_non_numeric_points(self):
        solution=self.solutions['te']
        with tempfile.TemporaryDirectory() as temporary:
            p=Path(temporary);folder=p/'native';save_planar_run(solution.case,solution,folder)
            before={x.name:x.read_bytes() for x in folder.iterdir()}
            (p/'points.json').write_text('[[0.1,0.1]]')
            run=subprocess.run([sys.executable,'-m','superfish_ng','probe-planar',str(folder),'--points',str(p/'points.json'),'--out',str(folder/'probe.csv')],capture_output=True,text=True)
            self.assertNotEqual(run.returncode,0)
            self.assertEqual({x.name:x.read_bytes() for x in folder.iterdir()},before)
        for points in ({'x':.1,'y':.1},[[False,.1]],[['0.1',.1]]):
            with self.assertRaises(ValueError):PlanarFieldSampler(solution).evaluate(points)

    def test_corrupt_or_duplicate_archive_members_are_rejected_after_rehash(self):
        import io,zipfile
        solution=self.solutions['tm']
        archive=io.BytesIO()
        payload=io.BytesIO();np.save(payload,solution.coefficients,allow_pickle=False)
        with zipfile.ZipFile(archive,'w') as z:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                z.writestr('coefficients.npy',payload.getvalue());z.writestr('coefficients.npy',payload.getvalue())
            f=io.BytesIO();np.save(f,solution.frequencies_hz,allow_pickle=False);z.writestr('frequencies_hz.npy',f.getvalue())
        for invalid in (b'PK\x03\x04truncated',archive.getvalue()):
            with tempfile.TemporaryDirectory() as temporary:
                folder=Path(temporary)/'native';save_planar_run(solution.case,solution,folder)
                (folder/'fields.npz').write_bytes(invalid)
                manifest=json.loads((folder/'manifest.json').read_text());manifest['files']['fields.npz']=hashlib.sha256(invalid).hexdigest()
                (folder/'manifest.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):read_planar_run(folder)

    def test_cli_save_replay_and_si_probe(self):
        with tempfile.TemporaryDirectory() as temporary:
            p=Path(temporary);case=replace(self.cases['te'],nx=4,ny=4,modes=2)
            (p/'case.json').write_text(json.dumps(case.to_dict()));(p/'points.json').write_text('[[0.1,0.1],[0.2,0.1]]')
            for arguments in (['solve-planar',str(p/'case.json'),'--out',str(p/'native')],
                    ['replay-planar',str(p/'native')],['probe-planar',str(p/'native'),'--points',str(p/'points.json'),'--out',str(p/'probe.csv')]):
                run=subprocess.run([sys.executable,'-m','superfish_ng',*arguments],capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr)
            header=(p/'probe.csv').read_text().splitlines()[0]
            self.assertTrue(header.startswith('x_m,y_m,'));self.assertIn('Hz_real_A_per_m',header)
            with self.assertRaises(FileExistsError):save_planar_run(case,solve_planar(case),p/'native')


if __name__=='__main__':unittest.main()

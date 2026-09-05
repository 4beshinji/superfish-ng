# SPDX-License-Identifier: Apache-2.0
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case, make_mesh, solve
from superfish_ng.cli import main
from superfish_ng.io import save_run


class InterfaceTests(unittest.TestCase):
    def test_case_roundtrip(self):
        c = Case(((0., .1), (.2, .1)))
        self.assertEqual(Case.from_dict(c.to_dict()), c)

    def test_reject_invalid_geometry_and_numbers(self):
        for profile in [((0.,0.),(.2,.1)), ((0.,.1),(0.,.2)), ((.1,.1),(.2,.1)), ((0.,.1),(.2,float('nan')))]:
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                Case(profile)
        for key,value in [('nr',True),('nz',1),('modes',0),('beta',1.1),('beta',0),('normalization_j',float('inf')),('conductivity_s_per_m',-1)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                Case(((0.,.1),(.2,.1)), **{key:value})

    def test_unknown_physics_not_silently_ignored(self):
        d = Case(((0.,.1),(.2,.1))).to_dict()
        for key,value in [('epsilon_r',4),('boundary','PMC'),('backend','mfem')]:
            bad = dict(d, **{key:value})
            with self.assertRaises(ValueError):
                Case.from_dict(bad)
        d['solver']['polarization'] = 'TE'
        with self.assertRaises(ValueError):
            Case.from_dict(d)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'case.json'
            path.write_text('{"schema_version":1,"schema_version":2}')
            with self.assertRaises(ValueError):
                Case.load(path)

    def test_profile_corners_boundary_tags_and_positive_mesh(self):
        c = Case(((0.,.04),(.031,.09),(.13,.05)), nr=7,nz=9)
        m = make_mesh(c)
        self.assertTrue(np.any(m.points[:,1] == .031))
        self.assertTrue(np.all(m.points[m.axis_nodes,0] == 0))
        self.assertEqual(set(m.boundary_tags), {'axis','pec'})
        self.assertTrue(np.all(np.any(m.points[m.boundary_edges[m.boundary_tags=='pec'],0] > 0, axis=1)))

    def test_exports_have_units_and_finite_arrays(self):
        c = Case(((0.,.1),(.2,.1)),nr=6,nz=7,modes=2)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'run'
            r = save_run(c, solve(c), out)
            reread = json.loads((out/'results.json').read_text())
            self.assertEqual(reread['case_sha256'], r['case_sha256'])
            with np.load(out/'fields.npz', allow_pickle=False) as fields:
                self.assertEqual(fields['u_a_per_m2'].shape[1], 2)
                self.assertTrue(np.isfinite(fields['u_a_per_m2']).all())
            vtk = (out/'mode_001.vtk').read_text()
            self.assertIn('CELL_TYPES',vtk)
            self.assertIn('Er_quadrature_V_per_m',vtk)
            self.assertEqual(len(list(out.glob('mode_*.vtk'))),2)

    def test_cli_solve_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            case, out = Path(d)/'case.json', Path(d)/'out'
            case.write_text(json.dumps(Case(((0.,.1),(.2,.1)),nr=4,nz=5,modes=1).to_dict()))
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['solve',str(case),'--out',str(out)]),0)
                before = (out/'results.json').read_bytes()
                self.assertEqual(main(['solve',str(case),'--out',str(out)]),2)
                self.assertEqual((out/'results.json').read_bytes(),before)

    def test_convergence_gate_fails_for_coarse_mesh(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            path = Path(d)/'convergence.json'
            self.assertEqual(main(['converge','--levels','2','4','--out',str(path)]),1)
            self.assertFalse(json.loads(path.read_text())['passed'])

    def test_too_many_modes(self):
        with self.assertRaises(ValueError):
            solve(Case(((0.,.1),(.2,.1)),nr=2,nz=2,modes=9))


if __name__ == '__main__':
    unittest.main()

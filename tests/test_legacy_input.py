# SPDX-License-Identifier: Apache-2.0
"""Synthetic interface fixtures and independent geometry/physics invariants."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case, solve, make_mesh
from superfish_ng.cli import main
from superfish_ng.geometry import profile_area, arc_geometry
from superfish_ng.mesh import element_geometry
from superfish_ng.model import Model
from superfish_ng.rf import quantities

OPTIONS = dict(nr=12, nz=16, modes=1, conductivity_s_per_m=5.8e7, normalization_j=1.)
HEADER = ('$reg kprob=1, icylin=1, nbslo=0, nbsup=1, nbslf=1, nbsrt=1,\n'
          ' beta=1, kmethod=1, zctr=10, dx=.5, freq=1100, epsik=1d-10 $\n')
RECTANGLE = '$po x=0,y=0 $\n$po x=0,y=10 $\n$po x=20,y=10 $\n$po x=20,y=0 $\n$po x=0,y=0 $\n'
DECK = 'Synthetic test cylinder\n' + HEADER + RECTANGLE


class LegacyInputTests(unittest.TestCase):
    def parse(self, text=DECK, **changes):
        from superfish_ng.legacy_input import parse_af
        return parse_af(text, **dict(OPTIONS, **changes))

    def test_cylinder_dimensions_volume_and_identical_fem(self):
        imported, report = self.parse()
        direct = Case(((0., .1), (.2, .1)), name=imported.name, model=Model(), **OPTIONS)
        self.assertEqual(imported, direct)
        mesh = make_mesh(imported)
        vertices, det, _ = element_geometry(mesh)
        self.assertAlmostEqual(det.sum()/2, .1*.2, places=14)
        self.assertAlmostEqual(np.sum(det/2*vertices[:, :, 0].mean(axis=1))*2*np.pi,
                               np.pi*.1**2*.2, places=14)
        a, b = solve(imported), solve(direct)
        np.testing.assert_array_equal(a.u, b.u)
        self.assertEqual(quantities(imported, a), quantities(direct, b))
        self.assertEqual(report['ng_settings']['nr'], 12)
        self.assertEqual(report['legacy_controls_si']['frequency_initial_hz'], 1.1e9)
        self.assertTrue(report['diagnostics'])

    def test_units_comments_case_and_d_exponents(self):
        cm, _ = self.parse()
        mm = DECK.replace('zctr=10', 'zctr=100, conv=0.1').replace('dx=.5', 'dx=5')
        mm = mm.replace('x=20', 'x=200').replace('y=10', 'y=100')
        candidate, _ = self.parse(mm.upper().replace('$', '&'))
        self.assertEqual(cm.profile, candidate.profile)
        text = DECK.replace('$\n', '$end ! comment\n').replace('1d-10', '1D-10')
        self.assertEqual(self.parse(text)[0].profile, cm.profile)
        self.assertEqual(self.parse(DECK.replace('dx=.5,', 'dx=.5, ; ignored=7\n'))[0].profile, cm.profile)
        self.assertEqual(self.parse(DECK.replace('Synthetic test cylinder', 'R&D cavity costing $5'))[0].name,
                         'R&D cavity costing $5')

    def test_step_and_arc_area_are_independent_of_parser(self):
        points = [(0,0),(0,4),(5,4),(5,7),(20,7),(20,0),(0,0)]
        text = HEADER + ''.join(f'$po x={x},y={y} $\n' for x,y in points)
        case, _ = self.parse(text)
        self.assertEqual(case.geometry_type, 'stepped_profile')
        self.assertAlmostEqual(profile_area(case), .05*.04+.15*.07, places=14)
        # Quarter arcs with independently known centers: (2,5) for ccw,
        # (3,4) for cw, in cm. Arc area differs from its chord by a segment.
        for nt, sign, center in [(4, -1, [.02, .05]), (5, 1, [.03, .04])]:
            text = HEADER.replace('zctr=10', 'zctr=2') + (
                '$po x=0,y=0 $\n$po x=0,y=4 $\n$po x=2,y=4 $\n'
                f'$po x=3,y=5,nt={nt},radius=1 $\n'
                '$po x=4,y=5 $\n$po x=4,y=0 $\n$po x=0,y=0 $\n')
            case, _ = self.parse(text)
            self.assertEqual(case.arcs, ((2, .01, 'ccw' if nt == 4 else 'cw'),))
            actual_center, _, _ = arc_geometry(case.profile[1], case.profile[2], .01, case.arcs[0][2])
            np.testing.assert_allclose(actual_center, center, atol=1e-15)
            chord_area = .02*.04+.01*.045+.01*.05
            self.assertAlmostEqual(profile_area(case), chord_area+sign*.01**2*(np.pi/2-1)/2, places=14)

    def test_imported_cylinder_bessel_frequency_and_rf_convergence(self):
        from superfish_ng.analytic import pillbox_tm010
        exact = pillbox_tm010(.1, .2)
        limits = {'frequency_hz': 1e-4, 'r_over_q_accelerator_ohm': .005,
                  'geometry_factor_ohm': .005}
        errors = []
        for n in (16, 32):
            case, _ = self.parse(nr=n, nz=2*n)
            q = quantities(case, solve(case))
            errors.append({key: abs(q[key]/exact[key]-1) for key in limits})
        for key, limit in limits.items():
            with self.subTest(quantity=key):
                self.assertLess(errors[-1][key], limit)
                self.assertLess(errors[-1][key], errors[0][key])

    def test_errors_have_source_positions_and_reject_unsupported(self):
        from superfish_ng.legacy_input import AFInputError
        for old, new in [('kprob=1', 'kprob=0'), ('icylin=1', 'icylin=0'),
                         ('nbslo=0', 'nbslo=1'), ('beta=1', 'beta=.9'),
                         ('zctr=10', 'zctr=0'), ('dx=.5', 'dx=1+2'),
                         ('dx=.5', 'dx=1e999'), ('dx=.5', 'dx=nan'),
                         ('dx=.5', 'dx=.5,dx=.4'), ('dx=.5', 'dx=.5,unknown=1'),
                         ('kprob=1', 'kprob=1.0'), ('x=20,y=10', 'x=20,y=10,nt=2'),
                         ('x=20,y=10', 'x=20,y=10,radius=1'),
                         ('x=20,y=10', 'x=20,y=10,x0=1'),
                         ('dx=.5', 'dx=.5,mat=2'), ('dx=.5', 'dx=.5,xdri=0')]:
            with self.subTest(new=new), self.assertRaises(AFInputError) as caught:
                self.parse(DECK.replace(old, new))
            self.assertGreaterEqual(caught.exception.line, 1)
            self.assertGreaterEqual(caught.exception.column, 1)
        for text in [DECK+'$reg mat=1 $', DECK+'STOP', DECK+'$mt epsilon=4 $',
                     DECK.rsplit('$po', 1)[0], DECK.replace('x=20,y=0', 'x=21,y=0'),
                     DECK.replace('kprob=1,', ''), DECK[:-2], DECK+'arbitrary tail']:
            with self.subTest(text=text[-30:]), self.assertRaises(AFInputError):
                self.parse(text)
        with self.assertRaises(AFInputError) as caught:
            self.parse(DECK.replace('dx=.5', 'alien=1'))
        line = DECK.replace('dx=.5', 'alien=1').splitlines()[caught.exception.line-1]
        self.assertTrue(line[caught.exception.column-1:].startswith('alien'))

    def test_cli_source_hash_conversion_and_no_output_on_failure(self):
        from superfish_ng.saved import read_solution
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source, converted, run = folder/'input.af', folder/'converted', folder/'run'
            source.write_bytes(DECK.replace('\n', '\r\n').encode())
            original = source.read_bytes()
            args = ['import-af', str(source), '--out', str(converted), '--nr', '12', '--nz', '16',
                    '--modes', '1', '--conductivity-s-per-m', '58000000', '--normalization-j', '1']
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(args), 0)
                self.assertEqual(main(args), 2)
                self.assertEqual(main(['solve',str(converted/'case.json'),'--out',str(run)]), 0)
                source.write_text(DECK.replace('kprob=1', 'kprob=0'))
                args[args.index('--out')+1] = str(folder/'invalid')
                self.assertEqual(main(args), 2)
            self.assertFalse((folder/'invalid').exists())
            report = json.loads((converted/'conversion.json').read_text())
            self.assertEqual(report['source_sha256'], hashlib.sha256(original).hexdigest())
            self.assertEqual((converted/'source.af').read_bytes(), original)
            self.assertEqual(read_solution(run).case, Case.load(converted/'case.json'))

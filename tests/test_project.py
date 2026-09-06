# SPDX-License-Identifier: Apache-2.0
"""Shared editing contract: independent geometry and preservation checks."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from superfish_ng.config import Case
from superfish_ng.project import Project, assemble_geometry, load_document


class ProjectTests(unittest.TestCase):
    def test_repeated_polygon_area_and_end_lengths(self):
        # Three trapezoids of area 0.006 m², with rectangular end pieces.
        cell = {'type': 'profile', 'points_zr_m': [[0, .04], [.05, .08], [.1, .04]]}
        end = {'type': 'profile', 'points_zr_m': [[0, .04], [.02, .04]]}
        geometry = assemble_geometry([{'geometry': end, 'count': 1},
                                      {'geometry': cell, 'count': 3},
                                      {'geometry': end, 'count': 1}])
        case = Case.from_dict({'schema_version': 2, 'geometry': geometry})
        area = sum((b[0]-a[0])*(a[1]+b[1])/2 for a,b in zip(case.profile,case.profile[1:]))
        self.assertAlmostEqual(case.length, .34)
        self.assertAlmostEqual(area, .0196)
        self.assertEqual(case.profile[0], (0., .04))
        self.assertAlmostEqual(case.profile[-1][1], .04)

    def test_plain_case_roundtrip_preserves_canonical(self):
        for path in Path('examples').glob('*.json'):
            with self.subTest(path=path):
                project = load_document(path.read_text())
                self.assertEqual(project.case.to_dict(), Case.load(path).to_dict())
                self.assertEqual(load_document(project.dumps()).to_dict(), project.to_dict())

    def test_unknown_duplicate_and_mismatch_rejected(self):
        case = {'schema_version': 1, 'geometry': {'type': 'pillbox', 'radius_m': .06, 'length_m': .1}}
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            load_document('{"schema_version":1,"schema_version":2}')
        with self.assertRaises(ValueError):
            Project.from_dict({'project_version':1,'case':case,'material':'dielectric'})
        sections = [{'geometry':case['geometry'],'count':2}]
        with self.assertRaisesRegex(ValueError, 'geometry'):
            Project.from_dict({'project_version':1,'case':case,'sections':sections})
        with self.assertRaises(ValueError):
            assemble_geometry([{'geometry':case['geometry'],'count':True}])

    def test_arc_radius_and_indices_survive_assembly(self):
        geometry = {'type':'arc_profile','points_zr_m':[[0,.04],[.01,.05],[.02,.04]],
                    'arcs':[{'end_index':1,'radius_m':.01,'direction':'cw'},
                            {'end_index':2,'radius_m':.01,'direction':'cw'}],
                    'chord_tolerance_m':1e-5}
        repeated = assemble_geometry([{'geometry':geometry,'count':5}])
        self.assertEqual(len(repeated['arcs']),10)
        self.assertTrue(all(a['radius_m']==.01 for a in repeated['arcs']))
        self.assertEqual([a['end_index'] for a in repeated['arcs']],list(range(1,11)))
        Case.from_dict({'schema_version':2,'geometry':repeated})

    def test_save_refuses_overwrite_and_reflection_is_explicit(self):
        p = Project.from_dict({'schema_version':1,'geometry':{'type':'pillbox','radius_m':.06,'length_m':.1}})
        self.assertFalse(p.reflect_full)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'project.json'; p.save(path)
            self.assertEqual(Project.load(path).to_dict(),p.to_dict())
            with self.assertRaises(FileExistsError): p.save(path)
        raw=copy.deepcopy(p.to_dict());raw['reflect_full']=True
        with self.assertRaisesRegex(ValueError,'symmetry'): Project.from_dict(raw)

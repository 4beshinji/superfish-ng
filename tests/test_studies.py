# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study


def base():
    return Project.from_dict(
        {
            "schema_version": 1,
            "geometry": {"type": "pillbox", "radius_m": 0.06, "length_m": 0.08},
            "mesh": {"nr": 10, "nz": 12},
            "solver": {"modes": 2},
        }
    )


class StudyTests(unittest.TestCase):
    def test_curved_geometry_and_fem_refinement_are_separate(self):
        import math
        from superfish_ng import Case
        from superfish_ng.conics import LineSegment,EllipseArc
        from superfish_ng.curved_contour import CurvedContour
        from superfish_ng.mesh_controls import ContourMeshControls
        curved = CurvedContour((LineSegment((0,0),(.2,0)),EllipseArc((.1,0),(.1,.08),0,math.pi)),('axis','pec'),1e-14)
        case = Case((),curved_contour=curved,curve_chord_tolerance_m=.002,
                    contour_mesh=ContourMeshControls(.02),modes=1,element_order=2)
        project = Project.from_dict(case.to_dict())
        geometry = Study(project,'geometry_convergence','/case/geometry/chord_tolerance_m',[.002,.001,.0005])
        cases = [p.case for p in geometry.projects()]
        self.assertTrue(all(c.curved_contour==curved and c.contour_mesh==case.contour_mesh for c in cases))
        self.assertTrue(len(cases[0].contour.vertices_zr_m)<len(cases[-1].contour.vertices_zr_m))
        mesh = Study(project,'mesh_convergence','mesh_scale',[1,2])
        mesh_cases = [p.case for p in mesh.projects()]
        self.assertEqual(mesh_cases[0].contour,mesh_cases[1].contour)
        self.assertEqual([c.contour_mesh.max_edge_m for c in mesh_cases],[.02,.01])
        with tempfile.TemporaryDirectory() as tmp:
            report = execute_study(geometry,Path(tmp)/'geometry')
            self.assertEqual(len(report['comparisons']),2)
            moments = [p['geometry_approximation'] for p in report['points']]
            self.assertTrue(all(abs(m['analytic_volume_m3']/(4*math.pi*.1*.08**2/3)-1)<1e-12 for m in moments))
            errors = [abs(m['volume_difference_m3']) for m in moments]
            self.assertGreater(errors[0],errors[1])
            self.assertGreater(errors[1],errors[2])
            self.assertIn('element orders [2]',report['surface_field'])

    def test_contour_refinement_changes_physical_size_and_actual_mesh(self):
        from superfish_ng import Case
        from superfish_ng.contour import Contour
        from superfish_ng.mesh import make_mesh
        from superfish_ng.mesh_controls import ContourMeshControls
        case = Case((),contour=Contour(((0,0),(.2,0),(.2,.1),(0,.1)),('axis','pec','pec','pec')),
                    contour_mesh=ContourMeshControls(.05),modes=1)
        study = Study(Project.from_dict(case.to_dict()),'mesh_convergence','mesh_scale',[1,2])
        projects = study.projects()
        self.assertEqual([p.case.contour_mesh.max_edge_m for p in projects],[.05,.025])
        self.assertEqual(projects[0].case.contour,projects[1].case.contour)
        self.assertEqual(projects[0].case.contour_mesh.max_triangles,projects[1].case.contour_mesh.max_triangles)
        meshes = [make_mesh(p.case) for p in projects]
        self.assertGreater(len(meshes[1].triangles),len(meshes[0].triangles))

    def test_pillbox_length_sweep_obeys_independent_tm010_invariant(self):
        project = base().to_dict()
        project["case"]["mesh"] = {"nr": 64, "nz": 96}
        study = Study(
            Project.from_dict(project),
            "sweep",
            "/case/geometry/points_zr_m/1/0",
            [0.04, 0.08, 0.12],
        )
        with tempfile.TemporaryDirectory() as root:
            report = execute_study(study, Path(root) / "study")
            frequencies = [p["modes"][0]["frequency_hz"] for p in report["points"]]
            self.assertLess(max(frequencies) / min(frequencies) - 1, 1e-9)
            self.assertEqual(
                report["mode_tracking"], "not performed; independent spectra"
            )
            self.assertEqual(len(report["points"]), 3)

    def test_refinement_contract_and_serialization(self):
        s = Study(base(), "mesh_convergence", "mesh_scale", [1, 2])
        self.assertEqual(Study.from_dict(s.to_dict()).to_dict(), s.to_dict())
        self.assertEqual([p.case.nr for p in s.projects()], [10, 20])
        self.assertEqual([p.case.nz for p in s.projects()], [12, 24])
        with self.assertRaises(ValueError):
            Study(base(), "mesh_convergence", "/case/rf/beta", [0.8, 1])
        with self.assertRaises(ValueError):
            Study(base(), "mesh_convergence", "mesh_scale", [2, 1])
        with self.assertRaises(ValueError):
            Study(base(), "sweep", "/case/unsupported", [1, 2]).projects()

    def test_convergence_separates_field_frequency_and_rf(self):
        with tempfile.TemporaryDirectory() as root:
            r = execute_study(
                Study(base(), "mesh_convergence", "mesh_scale", [1, 2]),
                Path(root) / "study",
            )
            self.assertEqual(len(r["comparisons"]), 1)
            c = r["comparisons"][0]
            self.assertIn(c["status"], ["PASS", "FAIL", "UNVERIFIED"])
            self.assertEqual(
                c["pairing"], "same geometry; sampled magnetic-field overlap"
            )
            self.assertIn("frequency", c["modes"][0]["gates"])
            self.assertIn("axis_field", c["modes"][0]["gates"])
            self.assertIn("rf", c["modes"][0]["gates"])
            self.assertEqual(
                c["surface_field"], "not certified; P1 peak estimates retained"
            )

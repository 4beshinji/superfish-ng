# SPDX-License-Identifier: Apache-2.0
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scripts.hphi_mesh_reference import rectangular_holes,reference
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.hphi_native import solve_hphi,save_hphi_run
from superfish_ng.hphi_display import display_hphi_fields,export_hphi_probe,plot_hphi_mode,verified_hphi_view


class HphiDisplayTests(unittest.TestCase):
    def test_original_cells_and_all_phase_components(self):
        for order in (1,2):
            for holes in (0,2):
                case=(CoaxialCase(.025,.05,.18,nr=3,nz=6,element_order=order,modes=2) if not holes
                      else HphiMeshCase(MeridionalMesh(**rectangular_holes(2,holes)),element_order=order,modes=2))
                solution=solve_hphi(case);display=display_hphi_fields(solution,1)
                self.assertEqual(len(display['triangles']),len(solution.space.mesh.triangles)*(1 if order==1 else 4))
                self.assertEqual(len(display['fields']),18)
                parent=solution.space.mesh.points[solution.space.mesh.triangles[display['parent_cells']]]
                centres=np.einsum('tij,ti->tj',parent,display['barycentric'])
                np.testing.assert_allclose(display['points_rz_m'][display['triangles']].mean(axis=1),centres,rtol=1e-14,atol=1e-16)
                for key,value in solution.fields_in_cells(display['parent_cells'],display['barycentric'],1).items():
                    np.testing.assert_array_equal(display['fields'][key],value)

    def test_csv_preserves_source_si_phases_and_rejects_holes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=HphiMeshCase(MeridionalMesh(**rectangular_holes(2)),modes=2)
            solution=solve_hphi(case);run=root/'native';save_hphi_run(case,solution,run)
            before={p.name:p.read_bytes() for p in run.iterdir()};points=[[.025,0.],[.035,.09],[.1,.18]]
            out=root/'probe.csv';metadata=export_hphi_probe(run,out,points,2)
            with out.open() as stream:rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows[0]),20)
            self.assertIn('real + i*quadrature',metadata['conventions']['phasor'])
            self.assertIsNone(metadata['quantities']['r_over_q_accelerator_ohm'])
            for key,value in solution.fields_at(points,1).items():
                np.testing.assert_allclose([float(row[key]) for row in rows],value,rtol=1e-12,atol=0)
            self.assertEqual(metadata['data_sha256'],hashlib.sha256(out.read_bytes()).hexdigest())
            self.assertEqual(metadata,json.loads(out.with_suffix('.csv.json').read_text()))
            with self.assertRaises(ValueError):export_hphi_probe(run,root/'bad.csv',[[.06,.09]])
            with self.assertRaises(ValueError):export_hphi_probe(run,out,points)
            with self.assertRaises(ValueError):export_hphi_probe(run,run/'probe.csv',points)
            self.assertEqual(before,{p.name:p.read_bytes() for p in run.iterdir()})

    def test_plot_metadata_and_changed_source_rejected(self):
        try: import matplotlib
        except ImportError: self.skipTest('optional matplotlib unavailable')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=HphiMeshCase(MeridionalMesh(**rectangular_holes(1)),modes=2)
            run=root/'native';save_hphi_run(case,solve_hphi(case),run)
            for unit in ('m','mm'):
                out=root/f'{unit}.png';metadata=plot_hphi_mode(run,out,2,mesh=True,length_unit=unit)
                self.assertTrue(out.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertEqual(metadata['length_unit'],unit);self.assertEqual(metadata['display_samples'],64)
                self.assertEqual(metadata['components'],['Hphi_real_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'])
            import superfish_ng.hphi_display as module
            original=module.read_hphi_run
            def changed(path):
                solution=original(path)
                with (run/'case.json').open('a') as stream:stream.write(' ')
                return solution
            with patch.object(module,'read_hphi_run',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed while preparing'):verified_hphi_view(run,1)

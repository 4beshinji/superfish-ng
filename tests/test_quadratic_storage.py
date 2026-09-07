# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case
from superfish_ng.high_order import solve_p2
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.sampling import FieldSampler
from superfish_ng.completion import digest


class QuadraticStorageTests(unittest.TestCase):
    def test_roundtrip_full_coefficients_and_structural_corruption(self):
        case=Case(((0.,.1),(.2,.1)),nr=4,nz=6,modes=2)
        solution=solve_p2(case)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run'
            save_run(case,solution,root)
            with self.assertRaisesRegex(ValueError,'high-order reader'):
                read_solution(root)
            saved=read_solution(root,allow_quadratic=True)
            np.testing.assert_array_equal(saved.u,solution.u)
            for name in ['dof_points','cell_dofs','boundary_dofs','axis_dofs']:
                np.testing.assert_array_equal(getattr(saved.space,name),getattr(solution.space,name))
            probes=[[0.,.033],[.017,.081],[.082,.191]]
            for mode in range(2):
                a=FieldSampler.from_solution(solution).evaluate(probes,mode)
                b=FieldSampler.from_solution(saved).evaluate(probes,mode)
                for key in a:np.testing.assert_array_equal(a[key],b[key])
            # Rehash deliberately damaged bytes to exercise structure, not just manifest integrity.
            with np.load(root/'fields.npz') as data: original={k:data[k] for k in data.files}
            for key in ['cell_dofs','boundary_dofs','axis_dofs','dof_points']:
                arrays={k:v.copy() for k,v in original.items()}
                arrays[key].flat[0]+=1
                np.savez_compressed(root/'fields.npz',**arrays)
                manifest=json.loads((root/'save_complete.json').read_text())
                manifest['files']['fields.npz']=digest(root/'fields.npz')
                (root/'save_complete.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError,'quadratic'):
                    read_solution(root,allow_quadratic=True)

    def test_plot_uses_saved_quadratic_field_and_verifies_completion(self):
        try:
            from superfish_ng.visualize import plot_mode
        except ImportError:
            self.skipTest('optional Matplotlib unavailable')
        case=Case(((0.,.1),(.2,.1)),nr=4,nz=6,modes=1)
        solution=solve_p2(case)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run'
            save_run(case,solution,root)
            image=Path(tmp)/'plot.png'
            report=plot_mode(root,image,show_mesh=True)
            self.assertTrue(image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
            exact=FieldSampler.from_solution(solution).evaluate(report['radial_points_rz_m'])
            for key in exact:
                np.testing.assert_array_equal(report['radial_fields'][key],exact[key])
            (root/'save_complete.json').unlink()
            with self.assertRaisesRegex(ValueError,'incomplete'):
                plot_mode(root,Path(tmp)/'incomplete.png')

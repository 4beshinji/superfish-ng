# SPDX-License-Identifier: Apache-2.0
"""TE parity, geometry, normalization and explicit filtered-spectrum provenance."""
from dataclasses import replace
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.io import save_run
from superfish_ng.model import Model
from superfish_ng.te_saved import read_te_run
from superfish_ng.symmetry import reflect_solution
from superfish_ng.te import TEFieldSampler,te_quantities
from test_curved_reflection import half_case


class TEReflectionTests(unittest.TestCase):
    def verify_reflection(self,case,side,tag):
        half=solve(case);full,solution=reflect_solution(case,half)
        self.assertEqual(solution.reflection_source_case,case)
        self.assertEqual(full.normalization_j,2*case.normalization_j)
        self.assertLess(max(solution.residuals),1e-7)
        np.testing.assert_array_equal(solution.frequencies_hz,half.frequencies_hz)
        parity=1 if tag=='magnetic_symmetry' else -1
        points=np.array([[.015,.031],[.025,.052],[.035,.069]])
        reflected=points.copy();reflected[:,1]=(case.length if side=='z_min' else 2*case.length)-points[:,1]
        for mode in range(case.modes):
            a,b=te_quantities(half,mode),te_quantities(solution,mode)
            for key,factor in [('stored_energy_j',2),('wall_loss_w',2),('geometry_factor_ohm',1),('q0',1)]:
                np.testing.assert_allclose(b[key],factor*a[key],rtol=1e-10)
            ha=TEFieldSampler(half).evaluate(points,mode);fb=TEFieldSampler(solution).evaluate(reflected,mode)
            for key,sign in [('Ephi_V_per_m',parity),('Hr_quadrature_A_per_m',-parity),('Hz_quadrature_A_per_m',parity)]:
                self.assertLess(max(abs(fb[key]-sign*ha[key]))/max(abs(ha[key])),1e-10)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'native'
            result=save_run(full,solution,path)
            self.assertEqual(result['schema_version'],4)
            self.assertIn('NOT full-spectrum',result['reflection']['mode_indices'])
            restored=read_te_run(path)
            self.assertEqual(restored.reflection_source_case,case)
            np.testing.assert_array_equal(restored.coefficients_v_per_m2,solution.coefficients_v_per_m2)
            np.testing.assert_array_equal(restored.reflection_source_coefficients,half.coefficients_v_per_m2)
        with self.assertRaisesRegex(ValueError,'already filtered'):
            reflect_solution(full,solution)

    def test_straight_both_sides_and_symmetries(self):
        for order in (1,2):
            for side in ('z_min','z_max'):
                for tag in ('electric_symmetry','magnetic_symmetry'):
                    with self.subTest(order=order,side=side,tag=tag):
                        case=Case(((0.,.1),(.1,.1)),nr=10,nz=14,modes=2,
                                  element_order=order,normalization_j=.5,model=Model(polarization='te'),**{side:tag})
                        self.verify_reflection(case,side,tag)

    def test_curved_both_sides_and_symmetries(self):
        for side in ('z_min','z_max'):
            for tag in ('electric_symmetry','magnetic_symmetry'):
                with self.subTest(side=side,tag=tag):
                    case=replace(half_case(side,tag,level=1),model=Model(polarization='te'),normalization_j=.5)
                    self.verify_reflection(case,side,tag)

    def test_wrong_case_and_non_symmetry_domains_rejected(self):
        case=Case(((0.,.1),(.1,.1)),nr=8,nz=10,modes=1,model=Model(polarization='te'))
        solution=solve(case)
        with self.assertRaisesRegex(ValueError,'exactly one symmetry'):
            reflect_solution(case,solution)
        with self.assertRaisesRegex(ValueError,'matching solved'):
            reflect_solution(replace(case,name='different'),solution)

    def test_project_import_preserves_half_domain_and_rejects_forged_parity(self):
        import json
        from superfish_ng.project import Project
        from superfish_ng.jobs import execute_project,JobManager,read_job
        from superfish_ng.completion import digest
        case=Case(((0.,.1),(.1,.1)),nr=8,nz=10,modes=1,element_order=2,
                  z_max='magnetic_symmetry',model=Model(polarization='te'))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=root/'run';project=Project(case,reflect_full=True)
            execute_project(project,run)
            self.assertEqual(read_job(run)['status'],'complete')
            with closing(JobManager(root/'jobs')) as manager:
                identifier=manager.import_result(run/'solution')
                imported=Project.load(manager.directory(identifier)/'project.json')
                self.assertEqual(imported.case,case)
                self.assertTrue(imported.reflect_full)
                self.assertIsNotNone(imported.mesh_data)
            with closing(JobManager(root/'jobs')) as manager:
                self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
            path=run/'solution/results.json';marker=run/'solution/te_complete.json'
            data=json.loads(path.read_text());data['reflection']['parity']=-1;path.write_text(json.dumps(data))
            completion=json.loads(marker.read_text());completion['files']['results.json']=digest(path);marker.write_text(json.dumps(completion))
            with self.assertRaisesRegex(ValueError,'reflection metadata disagrees'):
                read_te_run(run/'solution')

    def test_replay_rejects_changed_full_coefficients_even_with_updated_hash(self):
        import json
        from superfish_ng.completion import digest
        from superfish_ng.studies import compare_refinement
        from superfish_ng.mode_tracking import track_cylindrical_modes
        case=Case(((0.,.1),(.1,.1)),nr=8,nz=10,modes=1,element_order=2,
                  z_max='magnetic_symmetry',model=Model(polarization='te'))
        full,solution=reflect_solution(case,solve(case))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'native';save_run(full,solution,root)
            with self.assertRaisesRegex(ValueError,'partial spectra'):
                compare_refinement(root,root)
            with self.assertRaisesRegex(ValueError,'partial spectra'):
                track_cylindrical_modes(solution,solution,['a'],mapping='normalized_cylinder',sample_order=12)
            path=root/'fields.npz'
            with np.load(path) as data:v=data['coefficients_v_per_m2'];f=data['frequencies_hz']
            v=-v;np.savez_compressed(path,coefficients_v_per_m2=v,frequencies_hz=f)
            marker=root/'te_complete.json';completion=json.loads(marker.read_text());completion['files']['fields.npz']=digest(path);marker.write_text(json.dumps(completion))
            with self.assertRaisesRegex(ValueError,'source reconstruction'):
                read_te_run(root)

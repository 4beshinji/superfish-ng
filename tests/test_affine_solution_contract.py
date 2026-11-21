# SPDX-License-Identifier: Apache-2.0
"""Case/domain and physical energy must agree independently of file hashes."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from superfish_ng import Case, solve
from superfish_ng.completion import digest
from superfish_ng.io import save_run
from superfish_ng.rf import quantities
from superfish_ng.saved import read_solution


class AffineSolutionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=[Case(((0.,.1),(.2,.1)),nr=8,nz=8,modes=1,element_order=order) for order in (1,2)]
        cls.solutions=[solve(case) for case in cls.cases]

    def substitutions(self,case):
        return [('radius',replace(case,profile=((0.,.2),(.2,.2)))),
                ('length',replace(case,profile=((0.,.1),(.4,.1)))),
                ('energy',replace(case,normalization_j=9.))]

    def test_wrong_domain_or_normalization_refused_before_rf_or_publication(self):
        for case,solution in zip(self.cases,self.solutions):
            self.assertEqual(solution.mesh.points[:,0].max(),.1)
            self.assertAlmostEqual(quantities(case,solution)['stored_energy_j'],1.,places=10)
            for name,bad in self.substitutions(case):
                with self.subTest(order=case.element_order,change=name,operation='RF'),self.assertRaises(ValueError):
                    quantities(bad,solution)
                with tempfile.TemporaryDirectory() as tmp:
                    path=Path(tmp)/'bad'
                    with self.subTest(order=case.element_order,change=name,operation='save'):
                        with self.assertRaises(ValueError):save_run(bad,solution,path)
                        self.assertFalse((path/'save_complete.json').exists())

    def test_rehashed_old_format_cannot_hide_wrong_case_domain_or_energy(self):
        for case,solution in zip(self.cases,self.solutions):
            for name,bad in self.substitutions(case):
                with tempfile.TemporaryDirectory() as tmp:
                    path=Path(tmp)/'run';save_run(case,solution,path)
                    document=json.loads((path/'results.json').read_text());document['case']=bad.to_dict()
                    encoded=json.dumps(bad.to_dict(),sort_keys=True,separators=(',',':'),allow_nan=False)
                    document['case_sha256']=hashlib.sha256(encoded.encode()).hexdigest()
                    (path/'case.json').write_text(json.dumps(bad.to_dict()))
                    (path/'results.json').write_text(json.dumps(document))
                    marker=json.loads((path/'save_complete.json').read_text())
                    marker['files']={file:digest(path/file) for file in marker['files']}
                    (path/'save_complete.json').write_text(json.dumps(marker))
                    with self.subTest(order=case.element_order,change=name),self.assertRaises(ValueError):read_solution(path)

    def test_postprocessing_changes_keep_the_original_physical_solution(self):
        for case,solution in zip(self.cases,self.solutions):
            changed=replace(case,beta=.7,conductivity_s_per_m=case.conductivity_s_per_m*4,
                            voltage_interval_m=(.013,.187),phase_origin_m=-.027,active_length_m=.4)
            old,new=quantities(case,solution),quantities(changed,solution)
            self.assertEqual(old['frequency_hz'],new['frequency_hz'])
            self.assertEqual(old['stored_energy_j'],new['stored_energy_j'])
            self.assertAlmostEqual(new['q0']/old['q0'],2.,places=10)
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'run';save_run(changed,solution,path)
                self.assertEqual(read_solution(path).case,changed)

    def test_changed_mesh_or_field_normalization_is_not_a_solved_eigenmode(self):
        for case,solution in zip(self.cases,self.solutions):
            original=solution.u.copy()
            try:
                solution.u*=3
                with self.subTest(order=case.element_order,change='field'),self.assertRaisesRegex(ValueError,'energy'):
                    quantities(case,solution)
                with tempfile.TemporaryDirectory() as tmp:
                    path=Path(tmp)/'bad'
                    with self.assertRaisesRegex(ValueError,'energy'):save_run(case,solution,path)
                    self.assertFalse(path.exists())
            finally:solution.u[:]=original
            tags=solution.mesh.boundary_tags.copy()
            try:
                solution.mesh.boundary_tags[0]='axis' if tags[0]=='pec' else 'pec'
                with self.subTest(order=case.element_order,change='roles'),self.assertRaisesRegex(ValueError,'mesh/field space'):
                    quantities(case,solution)
            finally:solution.mesh.boundary_tags[:]=tags

    def test_reflection_owns_immutable_source_and_rejects_rehashed_false_half_domain(self):
        from superfish_ng.symmetry import reflect_solution
        for case in self.cases:
            half=replace(case,z_max='electric_symmetry')
            full,solution=reflect_solution(half,solve(half))
            source=solution.source_case['rf']['normalization_j']
            try:
                solution.source_case['rf']['normalization_j']=9.
                with self.assertRaisesRegex(ValueError,'reflection source'):quantities(full,solution)
            finally:solution.source_case['rf']['normalization_j']=source
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'run';save_run(full,solution,path)
                self.assertAlmostEqual(read_solution(path).results['modes'][0]['stored_energy_j'],2.,places=10)
                document=json.loads((path/'results.json').read_text())
                document['reflection_source_case']['rf']['normalization_j']=9.
                (path/'results.json').write_text(json.dumps(document))
                marker=json.loads((path/'save_complete.json').read_text())
                marker['files']['results.json']=digest(path/'results.json')
                (path/'save_complete.json').write_text(json.dumps(marker))
                with self.assertRaisesRegex(ValueError,'half-domain source'):read_solution(path)

    def test_external_mesh_is_owned_and_its_restored_declaration_remains_bound(self):
        from superfish_ng.affine_saved import read_verified_affine_solution
        from superfish_ng.mesh import make_mesh
        from superfish_ng.mesh_input import mesh_to_dict
        for case in self.cases:
            data=mesh_to_dict(make_mesh(case));solution=solve(case,mesh_data=data)
            data['points'][0][0]+=1.
            quantities(case,solution)  # Caller mutation does not change the owned mesh.
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'run';save_run(case,solution,path)
                restored=read_verified_affine_solution(path)
                self.assertEqual(restored.mesh_input,solution.mesh_input)
                restored.mesh_input['points'][0][0]+=1.
                with self.assertRaisesRegex(ValueError,'input mesh declaration'):quantities(case,restored)


if __name__=='__main__':unittest.main()

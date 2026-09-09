# SPDX-License-Identifier: Apache-2.0
"""A symmetry-sector comparison must equal the original half-domain comparison."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng import Case,solve
from superfish_ng.model import Model
from superfish_ng.io import save_run
from superfish_ng.symmetry import reflect_solution
from superfish_ng.studies import Study,compare_refinement,execute_study
from superfish_ng.project import Project
from superfish_ng import te_convergence
from test_curved_reflection import half_case


class TEReflectedConvergenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name);cls.pairs=[]
        for curved in (False,True):
            for side in ('z_min','z_max'):
                for tag in ('magnetic_symmetry','electric_symmetry'):
                    paths=[]
                    for level in (0,1):
                        if curved:
                            case=replace(half_case(side,tag,level),model=Model(polarization='te'),normalization_j=.5)
                        else:
                            case=Case(((0.,.1),(.1,.1)),nr=8*2**level,nz=12*2**level,modes=1,
                                      element_order=2,normalization_j=.5,model=Model(polarization='te'),**{side:tag})
                        half=solve(case);full,reflected=reflect_solution(case,half)
                        hp=cls.root/f'{curved}-{side}-{tag}-{level}-half';fp=cls.root/f'{curved}-{side}-{tag}-{level}-full'
                        save_run(case,half,hp);save_run(full,reflected,fp);paths.append((hp,fp))
                    cls.pairs.append((curved,side,tag,paths))

    def test_all_diagnostics_equal_direct_half_comparison(self):
        for curved,side,tag,paths in self.pairs:
            with self.subTest(curved=curved,side=side,tag=tag):
                expected=compare_refinement(paths[0][0],paths[1][0])
                actual=compare_refinement(paths[0][1],paths[1][1])
                metadata=actual.pop('reflection_comparison')
                self.assertEqual(actual,expected)
                self.assertEqual(metadata['domain'],'reconstructed source half-domain')
                self.assertIn('not full-spectrum',metadata['mode_indices'])
                self.assertEqual([r['parity'] for r in metadata['source_reflections']],[1 if tag=='magnetic_symmetry' else -1]*2)

    def test_mixed_ordinary_reflected_and_different_sectors_rejected(self):
        a=self.pairs[0][3];b=self.pairs[1][3]
        with self.assertRaisesRegex(ValueError,'mix ordinary and reflected'):
            compare_refinement(a[0][0],a[1][1])
        with self.assertRaisesRegex(ValueError,'identical source physics and symmetry'):
            compare_refinement(a[0][1],b[1][1])
        with self.assertRaisesRegex(ValueError,'identical source physics and symmetry'):
            compare_refinement(a[0][1],self.pairs[2][3][1][1])

    def test_source_change_during_integrals_is_rejected(self):
        paths=self.pairs[0][3];target=paths[0][1]/'source_fields.npz';original=target.read_bytes()
        integrate=te_convergence._integrals
        def changed(*args):
            result=integrate(*args);target.write_bytes(original+b'changed after reading');return result
        try:
            with patch.object(te_convergence,'_integrals',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'source changed during comparison'):
                    compare_refinement(paths[0][1],paths[1][1])
        finally:target.write_bytes(original)

    def test_changed_source_normalization_is_not_refinement(self):
        case=replace(Case.load(self.pairs[0][3][0][0]/'case.json'),normalization_j=2.)
        full,solution=reflect_solution(case,solve(case));path=self.root/'changed-energy';save_run(full,solution,path)
        with self.assertRaisesRegex(ValueError,'identical source physics and symmetry'):
            compare_refinement(self.pairs[0][3][0][1],path)

    def test_reflected_study_preserves_full_results_and_half_comparison(self):
        from superfish_ng.jobs import read_job
        from superfish_ng.te_saved import read_te_run
        case=Case.load(self.pairs[0][3][0][0]/'case.json')
        path=self.root/'study';result=execute_study(Study(Project(case,reflect_full=True),'mesh_convergence','mesh_scale',[1,2]),path)
        self.assertEqual(read_job(path)['status'],'complete')
        comparison=result['comparisons'][0]
        self.assertEqual(comparison['reflection_comparison']['domain'],'reconstructed source half-domain')
        self.assertEqual(comparison,compare_refinement(path/result['points'][0]['directory']/'solution',path/result['points'][1]['directory']/'solution'))
        for point in result['points']:
            saved=read_te_run(path/point['directory']/'solution')
            self.assertEqual(saved.case.normalization_j,1.)
            self.assertEqual(saved.reflection_source_case.normalization_j,.5)
            self.assertIsNone(point['modes'][0]['r_over_q_accelerator_ohm'])

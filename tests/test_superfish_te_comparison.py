# SPDX-License-Identifier: Apache-2.0
"""Synthetic SI contract tests; no legacy software or output fixtures required."""
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('comparison_te_script',SCRIPTS/'compare_superfish_te.py')
comparison=importlib.util.module_from_spec(spec);spec.loader.exec_module(comparison)


class ComplementaryTEComparisonTests(unittest.TestCase):
    def table(self,z,r,hr=2.,hz=3.,ephi=5.):
        z,r=np.broadcast_arrays(z,r);a=np.zeros((z.size,6));a[:,0]=z;a[:,1]=r
        a[:,2]=hz*comparison.IMPEDANCE;a[:,3]=hr*comparison.IMPEDANCE
        a[:,4]=np.hypot(a[:,2],a[:,3]);a[:,5]=ephi/comparison.IMPEDANCE
        return a

    def test_explicit_polarization_and_common_phase_are_required(self):
        table=self.table(np.linspace(0,1,5),.2,hr=-2.,hz=3.)
        fields=comparison.complementary_fields(table,declaration=comparison.DECLARATION)
        np.testing.assert_allclose(fields['Ephi_V_per_m'],5.)
        np.testing.assert_allclose(fields['Hr_quadrature_A_per_m'],-2.)
        np.testing.assert_allclose(fields['Hz_quadrature_A_per_m'],3.)
        for bad in ('tm','te',None):
            with self.assertRaisesRegex(ValueError,'explicit'):
                comparison.complementary_fields(table,declaration=bad)
        corrupted=table.copy();corrupted[:,4]=0
        with self.assertRaisesRegex(ValueError,'magnitude'):
            comparison.complementary_fields(corrupted,declaration=comparison.DECLARATION)
        flipped=table.copy();flipped[:,2:4]*=-1
        self.assertGreater(max(comparison.field_errors([flipped],[fields]).values()),1.)

    def test_peak_wall_integral_counts_two_disks_and_cylinder(self):
        radius,length=.3,.8;r=np.linspace(0,radius,21);z=np.linspace(0,length,21)
        tables=[self.table(0,r),self.table(z,radius),self.table(length,r)]
        actual=comparison.wall_integral(tables,radius,length,declaration=comparison.DECLARATION)
        expected=2*np.pi*radius**2*2**2+2*np.pi*radius*length*3**2
        self.assertAlmostEqual(actual,expected,places=12)
        # Wrong component / missing wall / reversed integration must not pass.
        for bad in (tables[:2],[tables[1],tables[0],tables[2]],
                    [tables[0][::-1],tables[1],tables[2]]):
            with self.assertRaises(ValueError):
                comparison.wall_integral(bad,radius,length,declaration=comparison.DECLARATION)
        scaled=[t.copy() for t in tables]
        for t in scaled:t[:,2:]*=7
        self.assertAlmostEqual(comparison.wall_integral(scaled,radius,length,declaration=comparison.DECLARATION)/actual,49.,places=12)


if __name__=='__main__':unittest.main()

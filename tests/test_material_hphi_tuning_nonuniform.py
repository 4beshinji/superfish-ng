# SPDX-License-Identifier: Apache-2.0
"""Independent two-layer interface determinant for nonuniform material tuning."""
import unittest
import numpy as np
from scipy.optimize import brentq
from superfish_ng.constants import C0,TAU
from superfish_ng.material_hphi_shape_tuning import MaterialHphiShapeLaw
from superfish_ng.material_hphi_tuning import run_material_hphi_tune
from superfish_ng.hphi_project import HphiProject
from test_material_hphi_tuning import request


class MaterialHphiNonuniformTuningTests(unittest.TestCase):
    def test_two_layer_unequal_length_changes_match_independent_interface_root(self):
        q=request();p=HphiProject.from_dict(q['project']);points=p.case.partition.mesh.points_rz_m
        cut=.125;length=.1875;delta=np.column_stack((np.zeros(len(points)),points[:,1]/2+np.maximum(points[:,1]-cut,0)/2))
        q['shape_law']=MaterialHphiShapeLaw('general_piecewise_affine',1.,delta).to_dict()
        def reference(value):
            l1=cut*(1+(value-1)/2);l2=(length-cut)*value
            # Continuity of q and (1/epsilon)*dq/dz, with Neumann end walls.
            def determinant(k):return np.sin(k*l1)*np.cos(2*k*l2)+.5*np.cos(k*l1)*np.sin(2*k*l2)
            baseline=3*np.pi/(4*length)
            return C0/TAU*brentq(determinant,.5*baseline,1.5*baseline,xtol=1e-13)
        q['target_hz']=float(reference(1.1));run=run_material_hphi_tune(q)
        self.assertEqual(run.report['status'],'TUNED',run.report['decision'])
        self.assertEqual([t['value'] for t in run.report['trials']],[1.,1.2,1.1,1.1])
        for trial,project in zip(run.report['trials'],run.projects):
            self.assertLess(abs(trial['frequency_hz']/reference(trial['value'])-1),.001)
            if trial['value']>1:
                old=p.case.partition.region_volume_m3;new=project.case.partition.region_volume_m3
                self.assertNotAlmostEqual(new[0]/old[0],new[1]/old[1],places=5)
        self.assertTrue(run.report['decision']['mesh_difference_met'])
        self.assertTrue(run.report['decision']['refined_target_met'])


if __name__=='__main__':unittest.main()

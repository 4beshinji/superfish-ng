# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from copy import deepcopy
import tempfile,unittest
from pathlib import Path
import numpy as np
from superfish_ng.axis_hphi import AxisHphiCase,AxisAccelerationPath
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.hphi_native import solve_hphi
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_convergence import HphiConvergence,HphiConvergenceThresholds,compare_hphi_convergence
from test_meridional_overlap import fixture


def request(axis=True,order=2,holes=0,modes=3):
    projects=[]
    for n in (1,2,4):
        geometry=fixture(n,holes,axis,n==2)
        case=AxisHphiCase(geometry,element_order=order,modes=modes,acceleration=AxisAccelerationPath(0.,.09375,.8,.01)) if axis else HphiMeshCase(geometry,element_order=order,modes=modes,quadrature_order=12)
        projects.append(HphiProject(case))
    return HphiConvergence(projects)


class HphiConvergenceTests(unittest.TestCase):
    def test_strict_request_and_actual_refinement_required(self):
        q=request();self.assertEqual(HphiConvergence.from_dict(q.to_dict()).to_dict(),q.to_dict())
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'request.json';q.save(path);self.assertEqual(HphiConvergence.load(path).to_dict(),q.to_dict())
            with self.assertRaises(FileExistsError):q.save(path)
        bad=q.to_dict();bad['implicit_refinement']=True
        with self.assertRaises(ValueError):HphiConvergence.from_dict(bad)
        for projects in ([q.projects[0]]*3,list(q.projects[:2]),[q.projects[0],replace(q.projects[1],case=replace(q.projects[1].case,normalization_j=2.)),q.projects[2]]):
            with self.assertRaises(ValueError):HphiConvergence(projects)
        positive=request(False);changed=list(positive.projects);changed[1]=replace(changed[1],case=replace(changed[1].case,quadrature_order=16))
        with self.assertRaises(ValueError):HphiConvergence(changed)
        with self.assertRaises(ValueError):replace(q,max_triangles=1)
        with self.assertRaises(ValueError):replace(q,mode_ranks=(True,))

    def test_real_fields_and_all_rf_without_mode_ids(self):
        for axis in (False,True):
            q=request(axis);solutions=[solve_hphi(p.case) for p in q.projects];report=compare_hphi_convergence(q,solutions)
            self.assertEqual(report['mode_tracking'],'not_performed');self.assertEqual(len(report['comparisons']),2)
            last=report['comparisons'][-1]['modes'][0]
            self.assertEqual(last['correspondence'],'same_rank_overlap_verified')
            self.assertEqual(len(last['wall_segment_relative']),4)
            self.assertEqual(last['axis_voltage_relative'] is None,not axis)
            self.assertLess(last['electric_field_relative'],report['comparisons'][0]['modes'][0]['electric_field_relative'])
            if axis:self.assertEqual(last['wall_segment_relative'][-1],0.)
            bad=deepcopy(solutions);bad[0].coefficients[0,0]*=2
            with self.assertRaises(ValueError):compare_hphi_convergence(q,bad)

    def test_phase_reversal_and_guard_or_tolerance_unverified(self):
        q=request();solutions=[solve_hphi(p.case) for p in q.projects];original=compare_hphi_convergence(q,solutions)
        solutions[1].coefficients[:,0]*=-1;flipped=compare_hphi_convergence(q,solutions)
        for a,b in zip(original['comparisons'],flipped['comparisons']):
            a,b=a['modes'][0],b['modes'][0]
            for key in ('electric_field_relative','magnetic_field_relative','axis_voltage_relative'):self.assertAlmostEqual(a[key],b[key],delta=1e-12)
        strict=replace(q,thresholds=replace(q.thresholds,frequency_relative=1e-15));self.assertEqual(compare_hphi_convergence(strict,solutions)['status'],'UNVERIFIED')
        guard=replace(q,mode_ranks=(3,));report=compare_hphi_convergence(guard,solutions)
        self.assertEqual(report['status'],'UNVERIFIED');self.assertIn('upper spectral neighbor was not computed',report['comparisons'][-1]['modes'][0]['reasons'])


if __name__=='__main__':unittest.main()

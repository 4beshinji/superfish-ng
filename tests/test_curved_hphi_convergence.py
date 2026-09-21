# SPDX-License-Identifier: Apache-2.0
"""Fixed quadratic-domain three-level diagnostics, with original RF kept apart."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.curved_hphi import solve_curved_hphi
from superfish_ng.hphi_project import HphiProject
from superfish_ng.axis_hphi import AxisAccelerationPath
from test_curved_hphi_field_overlap import case
from test_curved_hphi_comparison import charts


def request(axis=False,holes=0,shear=1.,modes=3):
    from superfish_ng.curved_hphi_convergence import CurvedHphiConvergence
    cases=[replace(case(axis,n=n,holes=holes,shear=shear),modes=modes,
        acceleration=AxisAccelerationPath(.01,.17,.8,.02) if axis else None) for n in (1,2,4)]
    reference=cases[0].geometry
    return CurvedHphiConvergence(tuple(HphiProject(c) for c in cases),reference,
        [charts(reference,c.geometry,alpha=shear) for c in cases])


class CurvedHphiConvergenceTests(unittest.TestCase):
    def test_three_levels_separate_frequency_fields_rf_and_guard(self):
        q=request(True);solutions=[solve_curved_hphi(p.case) for p in q.projects]
        self.assertTrue(all(np.all(s.frequencies_hz>0) for s in solutions))
        from superfish_ng.curved_hphi_convergence import compare_curved_hphi_convergence
        report=compare_curved_hphi_convergence(q,solutions)
        self.assertEqual(len(report['comparisons']),2)
        self.assertEqual(report['mode_tracking'],'not_performed')
        rows=[p['modes'][0] for p in report['comparisons']]
        self.assertEqual(rows[-1]['correspondence'],'same_rank_overlap_verified')
        self.assertLess(rows[-1]['electric_field_relative'],rows[0]['electric_field_relative'])
        self.assertLess(rows[-1]['magnetic_field_relative'],rows[0]['magnetic_field_relative'])
        self.assertIsNotNone(rows[-1]['axis_voltage_relative'])
        checks=report['decisions'][0]['checks']
        for name in ('frequency_relative','electric_field_relative','magnetic_field_relative','rf/q0','rf/r_over_q_accelerator_ohm','rf/r_over_q_circuit_ohm','axis_voltage_relative'):
            self.assertIn(name,checks)
        self.assertEqual(len(rows[-1]['wall_segment_relative']),len(q.reference_geometry.base_mesh.surface_area_m2_by_segment))
        self.assertEqual(len(rows[-1]['wall_component_relative']),1)
        strict=replace(q,thresholds=replace(q.thresholds,frequency_relative=1e-15))
        self.assertEqual(compare_curved_hphi_convergence(strict,solutions)['status'],'UNVERIFIED')
        guard=replace(q,mode_ranks=(3,));r=compare_curved_hphi_convergence(guard,solutions)
        self.assertEqual(r['status'],'UNVERIFIED')
        self.assertIn('upper spectral neighbor was not computed',r['comparisons'][-1]['modes'][0]['reasons'])

    def test_saved_holes_phase_and_original_rf_are_preserved(self):
        from superfish_ng.curved_hphi_convergence import compare_curved_hphi_convergence
        from superfish_ng.curved_hphi_saved import save_curved_hphi_run,read_curved_hphi_run,_snapshot
        q=request(False,holes=1)
        with tempfile.TemporaryDirectory() as tmp:
            paths=[]
            for i,p in enumerate(q.projects):
                path=Path(tmp)/str(i);save_curved_hphi_run(p.case,solve_curved_hphi(p.case),path);paths.append(path)
            before=[_snapshot(p) for p in paths];solutions=[read_curved_hphi_run(p) for p in paths]
            original=compare_curved_hphi_convergence(q,solutions)
            solutions[1].coefficients[:,0]*=-1
            flipped=compare_curved_hphi_convergence(q,solutions)
            for old,new in zip(original['comparisons'],flipped['comparisons']):
                a,b=old['modes'][0],new['modes'][0]
                for key in ('electric_field_relative','magnetic_field_relative'):
                    self.assertAlmostEqual(a[key],b[key],delta=1e-12)
                self.assertEqual(len(b['wall_component_relative']),2)
                self.assertIsNone(b['axis_voltage_relative'])
                self.assertNotIn('r_over_q_accelerator_ohm',b['rf_relative'])
            self.assertEqual(before,[_snapshot(p) for p in paths])
            bad=list(solutions);bad[0]=replace(solutions[0],coefficients=solutions[0].coefficients*2)
            with self.assertRaises(ValueError):compare_curved_hphi_convergence(q,bad)

    def test_strict_fixed_geometry_request_and_real_refinement(self):
        from superfish_ng.curved_hphi_convergence import CurvedHphiConvergence
        q=request();self.assertEqual(CurvedHphiConvergence.from_dict(q.to_dict()).to_dict(),q.to_dict())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'request.json';q.save(path);self.assertEqual(CurvedHphiConvergence.load(path).to_dict(),q.to_dict())
            with self.assertRaises(FileExistsError):q.save(path)
        for key,value in (('convergence_version',True),('implicit_refinement',True),('max_sample_points',True),('mode_ranks',[True])):
            bad=q.to_dict();bad[key]=value
            with self.assertRaises(ValueError):CurvedHphiConvergence.from_dict(bad)
        for projects in ([q.projects[0]]*3,q.projects[:2],
                         [q.projects[0],replace(q.projects[1],case=replace(q.projects[1].case,normalization_j=2.)),q.projects[2]]):
            with self.assertRaises(ValueError):replace(q,projects=projects)
        with self.assertRaises(ValueError):replace(q,max_triangles=1)
        changed=list(q.projects);changed[1]=HphiProject(case(n=2,shear=.5,holes=0))
        with self.assertRaisesRegex(ValueError,'quadratic restriction'):replace(q,projects=changed)

    def test_analytic_tem_frequency_field_q_and_near_degenerate_stop(self):
        from superfish_ng.curved_hphi_convergence import compare_curved_hphi_convergence
        from superfish_ng.constants import C0,MU0,TAU
        from superfish_ng.curved_hphi_rf import curved_hphi_quantities
        from scripts.validate_coaxial import radial_roots
        q=coax_request(.125,levels=(4,8,16));solutions=[solve_curved_hphi(p.case) for p in q.projects]
        report=compare_curved_hphi_convergence(q,solutions)
        self.assertEqual(report['status'],'PASS',report['decisions'])
        s=solutions[-1];a,b,length=.0625,.125,.125
        frequency=C0/(2*length);self.assertAlmostEqual(s.frequencies_hz[0]/frequency,1.,delta=3e-4)
        exact=np.cos(np.pi*s.space.dof_points[:,1]/length);actual=s.coefficients[:,0]
        overlap=abs(actual@(s.mass@exact))/np.sqrt((actual@(s.mass@actual))*(exact@(s.mass@exact)))
        self.assertGreater(overlap,.999)
        rf=curved_hphi_quantities(s);rs=np.sqrt(np.pi*frequency*MU0/s.case.conductivity_s_per_m)
        expected_q=TAU*frequency*MU0*length*np.log(b/a)/(rs*(length*(1/a+1/b)+4*np.log(b/a)))
        self.assertAlmostEqual(rf['q0']/expected_q,1.,delta=.001)
        # An independently known TEM/radial crossing rounded to a declared
        # dyadic length remains closer than the existing 0.001 separation gate.
        critical=np.pi/radial_roots(a,b,1)[0];near=round(critical*65536)/65536
        q=coax_request(near);solutions=[solve_curved_hphi(p.case) for p in q.projects]
        self.assertLess(abs(C0/(2*near)/(C0/(2*critical))-1),.001)
        result=compare_curved_hphi_convergence(q,solutions)
        self.assertEqual(result['status'],'UNVERIFIED')
        self.assertIn('spectral separation is unresolved or near-degenerate',result['comparisons'][-1]['modes'][0]['reasons'])


def coax_request(length,levels=(2,4,8)):
    from fractions import Fraction as F
    from superfish_ng.meridional_mesh import MeridionalMesh
    from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
    from superfish_ng.curved_hphi import CurvedHphiCase
    from superfish_ng.curved_hphi_convergence import CurvedHphiConvergence
    def geometry(n):
        points=np.array([[.0625+.0625*i/n,length*j/n] for j in range(n+1) for i in range(n+1)])
        cells=[];declarations=[]
        for j in range(n):
            for i in range(n):
                a=j*(n+1)+i;b=a+1;d=a+n+1;c=d+1
                for cell in ((a,b,c),(a,c,d)):
                    cells.append(cell);xy=[(F(v%(n+1),n),F(v//(n+1),n)) for v in cell]
                    lower=all(y<=x for x,y in xy)
                    q=[(x-y,y) if lower else (x,y-x) for x,y in xy]
                    declarations.append(dict(base_cell=0 if lower else 1,reference_vertices=[[[v.numerator,v.denominator] for v in p] for p in q]))
        cells=np.array(cells);edges=np.unique(np.sort(cells[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
        base=MeridionalMesh([[.0625,0.],[.125,0.],[.125,length],[.0625,length]],[],points,cells)
        return CurvedMeridionalGeometry(base,edges,points[edges].mean(axis=1)),declarations
    reference,_=geometry(1);projects=[];declarations=[]
    for n in levels:
        g,cells=geometry(n);projects.append(HphiProject(CurvedHphiCase(g,modes=3)))
        declarations.append(cells)
    return CurvedHphiConvergence(projects,reference,declarations)


class CurvedHphiConvergencePhaseTests(unittest.TestCase):
    def test_p1_axis_common_phase_preserves_complex_voltage(self):
        from superfish_ng.curved_hphi_convergence import compare_curved_hphi_convergence
        q=request(True)
        q=replace(q,projects=[replace(p,case=replace(p.case,element_order=1)) for p in q.projects])
        solutions=[solve_curved_hphi(p.case) for p in q.projects]
        initial=compare_curved_hphi_convergence(q,solutions)
        solutions[1].coefficients[:,0]*=-1
        flipped=compare_curved_hphi_convergence(q,solutions)
        for a,b in zip(initial['comparisons'],flipped['comparisons']):
            old,new=a['modes'][0],b['modes'][0]
            self.assertEqual(new['coarse_phase_multiplier'],-old['coarse_phase_multiplier'])
            for name in ('electric_field_relative','magnetic_field_relative','axis_voltage_relative'):
                self.assertAlmostEqual(old[name],new[name],delta=1e-12)
            self.assertEqual(a['integration']['scalar_fields'],['u=Hphi/r','u=Hphi/r'])
            self.assertEqual(a['integration']['excluded_static_dimensions'],[0,0])

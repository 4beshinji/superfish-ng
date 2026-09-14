# SPDX-License-Identifier: Apache-2.0
"""TE electric pullbacks on declared quadratic comparison meshes."""
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
import numpy as np
from scipy.integrate import dblquad
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh_input import mesh_from_dict
from superfish_ng import solve
from superfish_ng.model import Model
from superfish_ng.io import save_run
from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking
from test_curved_piecewise_remesh_tracking import curved_comparison_fixture,CONTROLS

class TECurvedTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cases,cls.maps=curved_comparison_fixture()
        cls.cases=[replace(c,model=Model(polarization='te')) for c in cases]
        cls.solutions=[solve(replace(c,curved_refinement_levels=i),mesh_data=m['source_mesh']) for i,(c,m) in enumerate(zip(cls.cases,cls.maps))]
        cls.controls=dict(CONTROLS,comparison_meshes=cls.maps)

    def test_nonaffine_native_fields_and_saved_replay(self):
        report=track_piecewise_remesh_modes(*self.solutions,['TE'],**self.controls)
        self.assertEqual(report['status'],'PASS');self.assertEqual(report['physical_mapping']['field'],'Ephi_V_per_m')
        self.assertEqual(report['physical_mapping']['physics'],'axisymmetric_m0_te')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for i,s in enumerate(self.solutions):save_run(s.case,s,root/str(i))
            saved=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(root/'0'),current_run=str(root/'1'),previous_ids=['TE'],controls=self.controls))
            self.assertEqual(replay_mode_tracking(saved),saved)
            path=root/'0'/'axis_001.csv';path.write_text(path.read_text()+'\n')
            with self.assertRaises(ValueError):replay_mode_tracking(saved)

    def test_mixed_polarization_rejected(self):
        tm=solve(replace(self.cases[0],model=Model()),mesh_data=self.maps[0]['source_mesh'])
        with self.assertRaisesRegex(ValueError,'mixed TE/TM'):
            track_piecewise_remesh_modes(self.solutions[0],tm,['TE'],**self.controls)

    def test_variable_curved_volume_weight_against_independent_integrals(self):
        # Analytic test field v=1, Ephi=r. These adapters are not eigenmodes.
        solutions=[replace(s,coefficients_v_per_m2=np.ones_like(s.coefficients_v_per_m2)) for s in self.solutions]
        result=track_piecewise_remesh_modes(*solutions,['polynomial'],**self.controls)
        spaces=[case_curved_space(case,mesh_from_dict(case,m['source_mesh'])) for case,m in zip(self.cases,self.maps)]
        def evaluate(nodes,x,y):
            l=1-x-y
            basis=np.array([l*(2*l-1),x*(2*x-1),y*(2*y-1),4*l*x,4*x*y,4*y*l])
            dx=np.array([1-4*l,4*x-1,0,4*(l-x),4*y,-4*y])
            dy=np.array([1-4*l,0,4*y-1,-4*x,4*x,4*(l-y)])
            return (basis@nodes)[0],float(np.linalg.det(np.column_stack((dx@nodes,dy@nodes))))
        totals=np.zeros(3)
        for i in range(len(spaces[0].geometry.cell_nodes)):
            points=[s.geometry.points_rz_m[s.geometry.cell_nodes[i]] for s in spaces]
            def integrand(x,y,kind):
                (r0,d0),(r1,d1)=[evaluate(p,x,y) for p in points]
                return [(r0*r1)**1.5*np.sqrt(d0*d1),r0**3*d0,r1**3*d1][kind]
            for kind in range(3):totals[kind]+=dblquad(lambda y,x:integrand(x,y,kind),0,1,lambda x:0,lambda x:1-x,epsabs=1e-15,epsrel=1e-10)[0]
        expected=totals[0]/np.sqrt(totals[1]*totals[2])
        self.assertLess(expected,.999)
        self.assertAlmostEqual(result['matches'][0]['minimum_principal_overlap'],expected,places=8)


    def test_versions_three_four_five_and_maxwell_field_scaling(self):
        from superfish_ng.te import TEFieldSampler,te_quantities
        for version in [3,4]:
            maps=[dict(m,schema_version=version,boundary_pairing='ordered_curve_vertices',**({'max_pair_tests':100000} if version==4 else {})) for m in self.maps]
            report=track_piecewise_remesh_modes(*self.solutions,['TE'],**dict(self.controls,comparison_meshes=maps))
            self.assertEqual(report['status'],'PASS')
        cases,maps=curved_comparison_fixture(2.)
        scaled=[solve(replace(c,model=Model(polarization='te'),curved_refinement_levels=i),mesh_data=m['source_mesh']) for i,(c,m) in enumerate(zip(cases,maps))]
        for a,b in zip(self.solutions,scaled):
            qa=te_quantities(a);qb=te_quantities(b)
            for key,factor in [('frequency_hz',2),('geometry_factor_ohm',1),('stored_energy_j',1),('q0',1/np.sqrt(2))]:
                self.assertLess(abs(qa[key]/(factor*qb[key])-1),1e-10)
            points=np.array([[.02,.05],[.025,.1],[.02,.15]])
            fa=TEFieldSampler(a).evaluate(points);fb=TEFieldSampler(b).evaluate(2*points)
            for key in ['Ephi_V_per_m','Hr_quadrature_A_per_m','Hz_quadrature_A_per_m']:
                np.testing.assert_allclose(fa[key],2**1.5*fb[key],rtol=1e-10,atol=1e-10)
            self.assertIsNone(qa['r_over_q_accelerator_ohm'])
        report=track_piecewise_remesh_modes(*scaled,['TE'],**dict(self.controls,comparison_meshes=maps))
        original=track_piecewise_remesh_modes(*self.solutions,['TE'],**self.controls)
        np.testing.assert_allclose(report['overlap_matrix'],original['overlap_matrix'],rtol=1e-11,atol=1e-12)
        from test_curved_reference_partition import rectangle_project,CHART
        projects=[rectangle_project(levels=2),rectangle_project(True,levels=2)]
        solutions=[solve(replace(p.case,model=Model(polarization='te')),mesh_data=p.mesh_data) for p in projects]
        documents=[dict(schema_version=5,source_mesh=p.mesh_data,reference_vertices=CHART,boundary_pairing='declared_reference_polylines',max_pair_tests=10000) for p in projects]
        report=track_piecewise_remesh_modes(*solutions,['TE'],**dict(self.controls,comparison_meshes=documents))
        self.assertEqual(report['status'],'PASS');self.assertEqual(report['physical_mapping']['field'],'Ephi_V_per_m')

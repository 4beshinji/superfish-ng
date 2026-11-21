# SPDX-License-Identifier: Apache-2.0
"""Validate dedicated annular TM RF constraints, fields, walls and native replay."""
from pathlib import Path
import sys
REPOSITORY=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPOSITORY))
sys.path.insert(0,str(REPOSITORY/'src'))
import hashlib,json,unittest
import numpy as np
from scripts.validate_coaxial import exact_modes,reference,radial
from superfish_ng.coaxial import CoaxialCase,solve_coaxial
from superfish_ng.constants import EPS0,MU0,TAU
from superfish_ng.coaxial_saved import save_coaxial_run
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_convergence import HphiConvergence,_project_mesh
from superfish_ng.hphi_tuning import _refine_mesh
from superfish_ng.hphi_tracking import HphiTrackingRequest
from superfish_ng.vacuum_hphi_convergence import VacuumHphiConvergence
from superfish_ng.rf_optimization import save_vacuum_hphi_rf_design,read_vacuum_hphi_rf_design

ROOT=None


class AnnularTMRFTests(unittest.TestCase):
    def test_original_radial_tm_full_fields_all_pec_loss_three_levels_and_saved_replay(self):
        ROOT.mkdir(parents=True,exist_ok=False)
        projects=[HphiProject(CoaxialCase(.0625,.125,.015625,nr=8*2**i,nz=2*2**i,modes=3)) for i in range(3)]
        meshes=[_refine_mesh(_project_mesh(p)) for p in projects]
        pairs=[HphiTrackingRequest(meshes[i],meshes[i+1],previous_mode_count=1,current_mode_count=1,previous_mode_ids=('mode-1',)) for i in range(2)]
        declaration=VacuumHphiConvergence(HphiConvergence(projects),pairs)
        runs=[];solutions=[];hashes=[];errors=[];previous=None
        for i,p in enumerate(projects):
            solution=solve_coaxial(p.case);run=ROOT/str(i);save_coaxial_run(p.case,solution,run)
            runs.append(run);solutions.append(solution);hashes.append({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in run.iterdir()})
        item=exact_modes(projects[0].case)[0];self.assertEqual(item[1:3],(1,0))
        expected,wall_h2,field=reference(projects[0].case,item)
        criteria=dict(schema_version=1,objective=dict(quantity='wall_loss_w',direction='minimize'),constraints=[
            dict(quantity='frequency_hz',lower=float(.99*expected['frequency_hz']),upper=float(1.01*expected['frequency_hz'])),
            dict(quantity='wall_loss_w',lower=float(.99*expected['wall_loss_w']),upper=float(1.01*expected['wall_loss_w']))])
        report=save_vacuum_hphi_rf_design(runs,declaration,criteria,ROOT/'assessment.json')
        self.assertEqual(report['status'],'CRITERIA_MET',report['assessment'])
        self.assertEqual(report,read_vacuum_hphi_rf_design(ROOT/'assessment.json'))
        assessment=report['assessment'];self.assertTrue(assessment['individual_ids_complete']);self.assertEqual(assessment['mode_ranks'],[1,1,1])
        self.assertEqual(report['objective']['eligible_value'],max(rf['wall_loss_w'] for rf in assessment['selected_rf']))
        self.assertIsNone(report['physical_error_bound'])
        for solution,rf,segments in zip(solutions,assessment['selected_rf'],assessment['wall_loss_w_by_segment']):
            rz=solution.space.mesh.points[solution.space.mesh.triangles].mean(axis=1)
            h,e=field(*rz.T);actual=solution.fields_at(rz)
            sign=np.sign(h@actual['Hphi_real_A_per_m']);ae=np.column_stack((actual['Er_quadrature_V_per_m'],actual['Ez_quadrature_V_per_m']))
            error=np.array([abs(rf['frequency_hz']/expected['frequency_hz']-1),
                np.linalg.norm(sign*actual['Hphi_real_A_per_m']-h)/np.linalg.norm(h),np.linalg.norm(sign*ae-e)/np.linalg.norm(e),
                abs(rf['wall_loss_w']/expected['wall_loss_w']-1)])
            if previous is not None:self.assertTrue(np.all(error<previous),(error,previous))
            previous=error;errors.append(error.tolist())
            expected_walls=np.asarray(wall_h2)[[2,1,3,0]]*rf['surface_resistance_ohm']/2
            # This checks each ordered original endplate/conductor separately;
            # a total-wall sum alone cannot prove the PEC segment assignment.
            np.testing.assert_allclose(segments,expected_walls,rtol=.005,atol=0.)
            self.assertAlmostEqual(sum(segments),rf['wall_loss_w'],delta=1e-9)
            self.assertAlmostEqual(rf['q0'],TAU*rf['frequency_hz']/rf['wall_loss_w'],delta=1e-7)
            self.assertIsNone(rf['vacc_v']);self.assertIsNone(rf['r_over_q_accelerator_ohm']);self.assertIsNone(rf['r_over_q_circuit_ohm'])
        self.assertLess(previous[0],1e-4);self.assertLess(previous[1],.001);self.assertLess(previous[2],.01);self.assertLess(previous[3],.005)
        self.assertEqual(hashes,[{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in run.iterdir()} for run in runs])
        (ROOT/'independent-invariants.json').write_text(json.dumps(dict(FEM_calls=3,native_runs_preserved=True,reference=expected,analytic_family=dict(radial_index=item[1],axial_index=item[2]),
            errors_f_H_E_Pwall=errors,ordered_pec='z_min_end_plate,outer_conductor,z_max_end_plate,inner_conductor',native_sha256=hashes,three_level_status=report['status'],saved_replay_verified=True),indent=2)+'\n')
        print('independent annular TM f/H/E/Pwall errors:',json.dumps(errors),flush=True)


def main():
    import argparse
    global ROOT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path,help='new output directory; existing directories are refused')
    args=parser.parse_args()
    ROOT=args.out.resolve()
    unittest.main(argv=[sys.argv[0]],verbosity=2)


if __name__=='__main__':main()

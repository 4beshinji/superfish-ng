# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_native import solve_hphi
from superfish_ng.hphi_convergence import HphiConvergence, _project_mesh
from superfish_ng.hphi_tuning import _refine_mesh
from superfish_ng.hphi_tracking import HphiTrackingRequest
from superfish_ng.vacuum_hphi_convergence import VacuumHphiConvergence, compare_vacuum_hphi_convergence


class VacuumHphiRFIdentityTests(unittest.TestCase):
    def test_next_declaration_must_inherit_actual_individual_id_order(self):
        projects=[HphiProject(CoaxialCase(.03125,.046875,.1875,nr=2*2**i,nz=12*2**i,modes=3)) for i in range(3)]
        meshes=[_refine_mesh(_project_mesh(p)) for p in projects]
        pairs=[HphiTrackingRequest(meshes[i],meshes[i+1]) for i in range(2)]
        request=VacuumHphiConvergence(HphiConvergence(projects),pairs)
        solutions=[solve_hphi(p.case) for p in projects]
        original=compare_vacuum_hphi_convergence(request,solutions)
        self.assertEqual(original['status'],'PASS',original)
        self.assertEqual(original['comparisons'][0]['tracking']['current_mode_ids'],['mode-1','mode-2'])
        swapped=[pairs[0],replace(pairs[1],previous_mode_ids=('mode-2','mode-1'))]
        # This is the same ID set and valid metadata. The first actual E/H match
        # supplies the order; a declared swap cannot replace its observed IDs.
        invalid=replace(request,tracking_requests=swapped)
        with self.assertRaisesRegex(ValueError,'reorders inherited IDs'):
            compare_vacuum_hphi_convergence(invalid,solutions)

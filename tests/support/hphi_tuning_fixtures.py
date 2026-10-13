# SPDX-License-Identifier: Apache-2.0
"""Original fresh straight_worker_request inputs; no FEM solves or test cases."""
from superfish_ng.constants import C0
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_tracking import HphiTrackingControls


def straight_worker_request(*, modes=2, nr=2, nz=4):
    return dict(
        format="superfish_ng_hphi_tune",
        schema_version=1,
        project=HphiProject(
            CoaxialCase(0.01, 0.02, 0.04, nr=nr, nz=nz, modes=modes)
        ).to_dict(),
        parameter="uniform_scale",
        mapping=dict(kind="uniform_scale"),
        bounds=[1.0, 2.0],
        target_hz=C0 / (2 * 0.04 * 1.5),
        frequency_tolerance_hz=1.0e6,
        parameter_tolerance=1.0e-6,
        max_trials=20,
        initial_ids=["fundamental"],
        mode_id="fundamental",
        controls=HphiTrackingControls().to_dict(),
        refinement_levels=1,
        max_triangles=10000,
        max_dofs=10000,
        mesh_frequency_tolerance_hz=1.0e6,
    )


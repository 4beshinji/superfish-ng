# SPDX-License-Identifier: Apache-2.0
"""Original fresh curved_tune_request inputs; no FEM solves or test cases."""
from superfish_ng.hphi_project import HphiProject
from superfish_ng.curved_hphi_shape_tuning import CurvedHphiShapeLaw
from superfish_ng.hphi_tracking import HphiTrackingControls
from .curved_hphi_geometry import coax


def curved_tune_request():
    p=HphiProject(coax(.125,shear=1/64,n=2));g=p.case.geometry
    return dict(format='superfish_ng_curved_hphi_tune',schema_version=1,project=p.to_dict(),parameter='deformation',
        shape_law=CurvedHphiShapeLaw(1.,g.points_rz_m.tolist(),'transport_on_axis').to_dict(),bounds=[1.,1.125],
        target_hz=1.1e9,frequency_tolerance_hz=1e6,mesh_frequency_tolerance_hz=1e6,parameter_tolerance=1e-6,
        max_trials=8,initial_ids=['TEM'],mode_id='TEM',controls=HphiTrackingControls().to_dict(),
        refinement_levels=1,max_triangles=10000,max_dofs=10000,max_sample_points=2000000,identity_recovery=None)


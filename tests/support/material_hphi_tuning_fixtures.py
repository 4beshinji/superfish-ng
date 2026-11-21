# SPDX-License-Identifier: Apache-2.0
"""Original fresh material_tune_request inputs; no FEM solves or test cases."""
from scripts.material_hphi_reference import layered_partition, layered_reference
from superfish_ng.material_hphi import MaterialHphiCase
from superfish_ng.hphi_project import HphiProject
from superfish_ng.material_hphi_shape_tuning import MaterialHphiShapeLaw
from superfish_ng.hphi_tracking import HphiTrackingControls


def material_tune_request():
    p=HphiProject(MaterialHphiCase(layered_partition(1,12),modes=3))
    frequency=float(layered_reference(1)[0]['frequency_hz'])
    return dict(format='superfish_ng_material_hphi_tune',schema_version=1,project=p.to_dict(),
        parameter='deformation',shape_law=MaterialHphiShapeLaw('uniform_scale').to_dict(),bounds=[1.,1.2],target_hz=frequency/1.1,
        frequency_tolerance_hz=frequency*.001,mesh_frequency_tolerance_hz=frequency*.001,
        parameter_tolerance=1e-6,max_trials=8,initial_ids=['first','second'],mode_id='first',
        controls=HphiTrackingControls().to_dict(),refinement_levels=1,max_triangles=10000,max_dofs=10000,
        max_sample_points=2000000,max_interface_tests=2000000,max_interface_pieces=250000,identity_recovery=None)


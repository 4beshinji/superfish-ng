# SPDX-License-Identifier: Apache-2.0
"""Root-derived material candidates, nested final spaces and original-domain comparisons."""
from dataclasses import dataclass,replace
import numpy as np
from scipy.sparse import eye
from .config import integer
from .hphi_project import HphiProject
from .material_hphi import MaterialHphiCase
from .material_hphi_shape_tuning import MaterialHphiShapeLaw
from .material_hphi_refinement import refine_material_hphi_partition
from .material_hphi_comparison import MaterialHphiComparison,material_hphi_overlay
from .material_hphi_tracking import MaterialHphiTrackingRequest
from .hphi_tracking import HphiTrackingControls
from .hphi_geometry_mapping import HphiGeometryMapping


def _comparison(previous,current,mapping='same_domain'):
    return MaterialHphiComparison(previous,current,mapping,
        [dict(previous_id=m.id,current_id=m.id) for m in previous.materials],
        [dict(previous_id=r.id,current_id=r.id) for r in previous.regions])


def _budget(partition,order,levels,max_triangles,max_dofs,max_candidate_tests):
    for name,value in (('levels',levels),('max_triangles',max_triangles),('max_dofs',max_dofs),('max_candidate_tests',max_candidate_tests)):
        integer(value,name,minimum=0 if name=='levels' else 1)
    mesh=partition.mesh;vertices=len(mesh.points_rz_m);triangles=len(mesh.triangles)
    edges=len(np.unique(np.sort(mesh.triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0))
    for level in range(levels+1):
        if triangles>max_triangles:raise ValueError('material trial exceeds max_triangles')
        if vertices+(edges if order==2 else 0)>max_dofs:raise ValueError('material trial exceeds max_dofs')
        if triangles>max_candidate_tests:raise ValueError('material trial exceeds minimum max_candidate_tests')
        vertices,edges,triangles=vertices+edges,2*edges+3*triangles,4*triangles


@dataclass(frozen=True)
class MaterialHphiTuneTrial:
    project: HphiProject
    root_project: HphiProject
    reference_partition: object
    root_cells: np.ndarray
    prolongation: object
    diagnostic: dict


def build_material_hphi_tune_trial(project,law,value,*,phase='search',refinement_levels=1,
        max_triangles=250000,max_dofs=250000,max_candidate_tests=2000000,
        max_interface_tests=2000000,max_interface_pieces=250000):
    """Generate one candidate and optional final subdivision, without solving modes."""
    if type(project) is not HphiProject or type(project.case) is not MaterialHphiCase:
        raise ValueError('material tune trial requires an original MaterialHphiCase Project')
    if type(law) is not MaterialHphiShapeLaw:raise ValueError('material trial requires MaterialHphiShapeLaw')
    if phase not in ('search','refinement'):raise ValueError('material trial phase must be search or refinement')
    integer(refinement_levels,'refinement_levels')
    if not 1<=refinement_levels<=8:raise ValueError('refinement_levels must be from 1 to 8')
    for name,value_limit in (('max_interface_tests',max_interface_tests),('max_interface_pieces',max_interface_pieces)):
        integer(value_limit,name,minimum=1)
    levels=refinement_levels if phase=='refinement' else 0
    _budget(project.case.partition,project.case.element_order,levels,max_triangles,max_dofs,max_candidate_tests)
    options=dict(max_candidate_tests=max_candidate_tests,max_interface_tests=max_interface_tests,max_interface_pieces=max_interface_pieces)
    shaped=law.apply(project,value,max_overlay_triangles=max_triangles,**options)
    reference=shaped.project.case.partition;partition=reference;mesh=partition.mesh
    edges=np.unique(np.sort(mesh.triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
    dofs=len(mesh.points_rz_m)+(len(edges) if project.case.element_order==2 else 0)
    transfer=eye(dofs,format='csr');root_cells=np.arange(len(mesh.triangles));diagnostics=[]
    for _ in range(levels):
        refined=refine_material_hphi_partition(partition,element_order=project.case.element_order,
            quadrature_order=project.case.quadrature_order,max_triangles=max_triangles,max_dofs=max_dofs,**options)
        root_cells=root_cells[refined.parent_cells];transfer=refined.prolongation@transfer
        partition=refined.partition;diagnostics.append(refined.diagnostic)
    coverage=material_hphi_overlay(_comparison(reference,partition),max_overlay_triangles=max_triangles,**options)
    root_cells.setflags(write=False)
    for array in (transfer.data,transfer.indices,transfer.indptr):array.setflags(write=False)
    return MaterialHphiTuneTrial(replace(shaped.project,case=replace(shaped.project.case,partition=partition)),
        HphiProject.from_dict(project.to_dict()),reference,root_cells,transfer,
        dict(shape=shaped.diagnostic,phase=phase,refinement_levels=levels,refinements=diagnostics,
             root_overlay_triangles=len(coverage.overlay.determinants),
             scope='fixed-material candidate and scalar transfer only; no eigenfield, target or continuum acceptance'))


def material_hphi_trial_comparison(previous,current,*,previous_mode_ids=None,previous_identity_groups=None,
        previous_mode_count=2,current_mode_count=2,controls=None,max_sample_points=2000000,
        max_interface_tests=2000000,max_interface_pieces=250000):
    """Prepare one finer P2 space in each original material trial domain."""
    if type(previous) is not MaterialHphiTuneTrial or type(current) is not MaterialHphiTuneTrial:
        raise ValueError('material comparison requires two generated trial records')
    if previous.root_project.to_dict()!=current.root_project.to_dict():
        raise ValueError('material trial comparison requires the same original root Project')
    controls=HphiTrackingControls() if controls is None else controls
    if type(controls) is not HphiTrackingControls:raise ValueError('expected HphiTrackingControls')
    integer(max_sample_points,'max_sample_points',minimum=1)
    resolutions=[]
    for trial in (previous,current):
        partition=trial.project.case.partition
        _budget(partition,2,1,controls.max_overlay_triangles,controls.max_dofs,controls.max_candidate_tests)
        # Include the two extra orders used by direct scalar projection loss.
        if len(partition.mesh.triangles)*4*(controls.quadrature_order+10)**2>max_sample_points:
            raise ValueError('material trial comparison exceeds max_sample_points')
        fine=refine_material_hphi_partition(partition,element_order=2,quadrature_order=controls.quadrature_order,
            max_triangles=controls.max_overlay_triangles,max_dofs=controls.max_dofs,
            max_candidate_tests=controls.max_candidate_tests,max_interface_tests=max_interface_tests,max_interface_pieces=max_interface_pieces)
        resolutions.append(_comparison(partition,fine.partition))
    mapping=HphiGeometryMapping(previous.reference_partition.mesh,current.reference_partition.mesh)
    return MaterialHphiTrackingRequest(_comparison(previous.project.case.partition,current.project.case.partition,mapping),
        *resolutions,previous_mode_count=previous_mode_count,current_mode_count=current_mode_count,
        previous_mode_ids=previous_mode_ids,previous_identity_groups=previous_identity_groups,controls=controls,
        max_sample_points=max_sample_points,max_interface_tests=max_interface_tests,max_interface_pieces=max_interface_pieces)

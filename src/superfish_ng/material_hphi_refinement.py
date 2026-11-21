# SPDX-License-Identifier: Apache-2.0
"""Material-preserving straight subdivision and reference-cell nodal scalar transfer."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from .config import integer
from .rf_materials import RFMaterialPartition,RFMaterialRegion
from .material_hphi_fem import material_hphi_matrices
from .hphi_tuning import _refine_mesh
from .hphi_mass_projection import _basis
from .material_hphi_comparison import MaterialHphiComparison,material_hphi_overlay


@dataclass(frozen=True)
class MaterialHphiRefinement:
    partition: RFMaterialPartition
    parent_cells: np.ndarray
    prolongation: object
    diagnostic: dict


def refine_material_hphi_partition(partition,*,element_order=2,quadrature_order=12,
        max_triangles=250000,max_dofs=250000,max_candidate_tests=2000000,
        max_interface_tests=2000000,max_interface_pieces=250000):
    """Split each original cell into four with its original region ownership.

    Return the complete refined partition and P1/P2 reference-cell scalar nodal
    transfer. This prepares a nested space, not a new solved eigenfield;
    no frequency, normalization or RF result is transferred.
    """
    if type(partition) is not RFMaterialPartition:raise ValueError('material refinement requires RFMaterialPartition')
    for name,value in (('element_order',element_order),('quadrature_order',quadrature_order),('max_triangles',max_triangles),('max_dofs',max_dofs),('max_candidate_tests',max_candidate_tests),
                       ('max_interface_tests',max_interface_tests),('max_interface_pieces',max_interface_pieces)):
        integer(value,name)
        if value<=0:raise ValueError(name+' must be positive')
    if element_order not in (1,2) or not 4<=quadrature_order<=32:raise ValueError('material refinement requires P1/P2 and quadrature_order from 4 to 32')
    partition=RFMaterialPartition.from_dict(partition.to_dict());mesh=partition.mesh
    edges=np.unique(np.sort(mesh.triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
    triangles=4*len(mesh.triangles);vertices=len(mesh.points_rz_m)+len(edges)
    count=vertices+(2*len(edges)+3*len(mesh.triangles) if element_order==2 else 0)
    if triangles>max_triangles:raise ValueError('material refinement exceeds max_triangles')
    if count>max_dofs:raise ValueError('material refinement exceeds max_dofs')
    refined=_refine_mesh(mesh);parents=np.repeat(np.arange(len(mesh.triangles)),4)
    regions=[RFMaterialRegion(r.id,r.material,(4*np.asarray(r.cell_indices)[:,None]+np.arange(4)).ravel().tolist()) for r in partition.regions]
    fine=RFMaterialPartition(refined,partition.materials,regions)
    comparison=MaterialHphiComparison(partition,fine,'same_domain',
        [dict(previous_id=m.id,current_id=m.id) for m in partition.materials],
        [dict(previous_id=r.id,current_id=r.id) for r in partition.regions])
    coverage=material_hphi_overlay(comparison,max_candidate_tests=max_candidate_tests,max_overlay_triangles=max_triangles,
        max_interface_tests=max_interface_tests,max_interface_pieces=max_interface_pieces)
    original,_,_,_=material_hphi_matrices(partition,element_order,quadrature_order=quadrature_order)
    current,_,_,_=material_hphi_matrices(fine,element_order,quadrature_order=quadrature_order)
    reference=np.array([[1.,0.,0.],[0.,1.,0.],[0.,0.,1.],[.5,.5,0.],[0.,.5,.5],[.5,0.,.5]])
    split=np.array([[0,3,5],[3,1,4],[5,4,2],[3,4,5]])
    bary=reference[split]
    if element_order==2:bary=np.concatenate((bary,(bary[:,[0,1,2]]+bary[:,[1,2,0]])/2),axis=1)
    basis=[_basis(points,element_order) for points in bary];rows={}
    for cell,parent in enumerate(parents):
        for node,weights in zip(current.cell_dofs[cell],basis[cell%4]):
            values={int(dof):float(weight) for dof,weight in zip(original.cell_dofs[parent],weights) if weight!=0}
            if int(node) in rows and rows[int(node)]!=values:raise ValueError('material refinement has inconsistent shared nodal transfer')
            rows[int(node)]=values
    if len(rows)!=len(current.dof_points):raise ValueError('material refinement transfer does not cover every scalar DOF')
    rr=[];cc=[];data=[]
    for row,values in rows.items():
        for col,value in values.items():rr.append(row);cc.append(col);data.append(value)
    transfer=coo_matrix((data,(rr,cc)),shape=(len(current.dof_points),len(original.dof_points))).tocsr()
    parents.setflags(write=False)
    for array in (transfer.data,transfer.indices,transfer.indptr):array.setflags(write=False)
    return MaterialHphiRefinement(fine,parents,transfer,dict(element_order=element_order,
        original_triangles=len(mesh.triangles),refined_triangles=triangles,original_dofs=len(original.dof_points),refined_dofs=count,
        overlay_triangles=len(coverage.overlay.determinants),interface_pieces=len(coverage.interfaces.previous_edges),
        scope='nested material scalar space with original cell ownership; no solved mode, RF or continuum error estimate'))

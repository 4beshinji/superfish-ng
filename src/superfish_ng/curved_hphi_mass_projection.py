# SPDX-License-Identifier: Apache-2.0
"""Original curved q/u mass coupling and scalar L2 projection, never an eigensolve."""
from dataclasses import replace
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from .axis_connected_mesh import AxisConnectedMesh
from .config import integer
from .curved_meridional_geometry import CurvedMeridionalGeometry
from .curved_hphi_fem import curved_hphi_matrices
from .curved_hphi_comparison import build_curved_hphi_comparison,CurvedHphiComparisonBudgetExceeded
from .hphi_mass_projection import HphiMassCoupling,HphiProjection,_basis,_difference
from .fem import triangle_quadrature


def _sampling(overlay,order,max_samples):
    rule=list(triangle_quadrature(order));q=np.array([p for p,w in rule]);w=np.array([w for p,w in rule])
    if len(rule)*len(overlay.triangles)>max_samples:
        raise CurvedHphiComparisonBudgetExceeded('curved scalar comparison exceeds max_sample_points')
    return q,w


def _samples(part,q,w,orders,regular):
    bases=[];measures=[];cells=[]
    for side,order in enumerate(orders):
        rows=part.evaluate(side,q)
        bary=np.array([row['native_barycentric'] for row in rows]);shape=bary.shape
        bases.append(_basis(bary.reshape(-1,3),order).reshape(shape[0],shape[1],3 if order==1 else 6))
        radius=np.array([row['points_rz_m'][:,0] for row in rows]);det=np.array([row['determinant_m2'] for row in rows])
        measure=w[None,:]*det*(radius**3 if regular else 1/radius)
        if not np.isfinite(measure).all() or np.any(measure<=0):raise ValueError('curved scalar mass requires finite positive interior measure')
        measures.append(measure);cells.append(np.array([row['native_cell'] for row in rows],dtype=int))
    return bases,measures,cells


def _integrate(spaces,overlay,orders,order,regular,max_samples):
    q,w=_sampling(overlay,order,max_samples);pairs=((0,0),(0,1),(1,1));n=len(overlay.triangles)
    sizes=[space.cell_dofs.shape[1] for space in spaces]
    blocks=[np.empty((n,sizes[i],sizes[j])) for i,j in pairs];all_dofs=[np.empty((n,size),dtype=int) for size in sizes]
    for start in range(0,n,64):
        part=replace(overlay,triangles=overlay.triangles[start:start+64]);stop=start+len(part.triangles)
        values,measure,cells=_samples(part,q,w,orders,regular)
        for side in (0,1):all_dofs[side][start:stop]=spaces[side].cell_dofs[cells[side]]
        for block,(i,j) in zip(blocks,pairs):
            weights=measure[i] if i==j else np.sqrt(measure[i])*np.sqrt(measure[j])
            block[start:stop]=np.einsum('tq,tqi,tqj->tij',weights,values[i],values[j])
    result=[]
    for block,(i,j) in zip(blocks,pairs):
        rows=np.repeat(all_dofs[i],sizes[j],axis=1).ravel();columns=np.tile(all_dofs[j],(1,sizes[i])).ravel()
        matrix=coo_matrix((block.ravel(),(rows,columns)),shape=(len(spaces[i].dof_points),len(spaces[j].dof_points))).tocsr()
        if not np.isfinite(matrix.data).all():raise ValueError('curved scalar mass exceeds finite SI arithmetic')
        result.append(matrix)
    return result


def _coupling(previous,current,domain,previous_order,current_order,quadrature_order,previous_cells,current_cells,
              max_candidate_tests,max_overlay_triangles,max_dofs,max_sample_points):
    for name,value in (('previous_order',previous_order),('current_order',current_order),('quadrature_order',quadrature_order),
                       ('max_candidate_tests',max_candidate_tests),('max_overlay_triangles',max_overlay_triangles),
                       ('max_dofs',max_dofs),('max_sample_points',max_sample_points)):
        integer(value,name)
    if previous_order not in (1,2) or current_order not in (1,2) or not 4<=quadrature_order<=32:
        raise ValueError('curved scalar coupling requires P1/P2 and quadrature_order from 4 to 32')
    for geometry,order in zip((previous,current),(previous_order,current_order)):
        if type(geometry) is not CurvedMeridionalGeometry:raise ValueError('curved scalar coupling requires complete quadratic native geometry')
        count=len(geometry.points_rz_m) if order==2 else len(geometry.base_mesh.points_rz_m)
        if count>max_dofs:raise CurvedHphiComparisonBudgetExceeded('curved scalar coupling exceeds max_dofs')
    overlay=build_curved_hphi_comparison(previous,current,domain,previous_cells=previous_cells,current_cells=current_cells,
        max_pair_tests=max_candidate_tests,max_triangles=max_overlay_triangles)
    regular=isinstance(previous.base_mesh,AxisConnectedMesh);orders=(previous_order,current_order)
    integration_orders=[quadrature_order+4,quadrature_order+8]
    _sampling(overlay,integration_orders[-1],max_sample_points)
    assembled=[curved_hphi_matrices(g,o,quadrature_order=quadrature_order) for g,o in zip(overlay.native_geometries,orders)]
    spaces=tuple(a[0] for a in assembled);masses=tuple(a[2] for a in assembled)
    norms=[np.sqrt(m.diagonal()) for m in masses]
    if any(not np.isfinite(n).all() or np.any(n<=0) for n in norms):raise ValueError('curved scalar mass norms must be finite positive')
    low,high=(_integrate(spaces,overlay,orders,n,regular,max_sample_points) for n in integration_orders)
    differences=[_difference(a,b,norms[i],norms[j]) for a,b,(i,j) in zip(low,high,((0,0),(0,1),(1,1)))]
    reproduction=[_difference(a,b,n,n) for a,b,n in zip((high[0],high[2]),masses,norms)]
    if max(differences)>1e-10 or max(reproduction)>1e-8:
        raise ValueError('curved scalar mass quadrature is unresolved; increase order or refine the native partition')
    for matrix in (*masses,high[1]):
        for array in (matrix.data,matrix.indices,matrix.indptr):array.setflags(write=False)
    diagnostic=dict(unknown='u=Hphi/r' if regular else 'q=r*Hphi',measure='r^3 dr dz' if regular else 'dr dz/r',
        physical_relation='2*pi times scalar mass is the full 3D Hphi inner product',
        previous_order=previous_order,current_order=current_order,integration_orders=integration_orders,
        normalized_quadrature_differences=differences,integration_tolerance=1e-10,
        normalized_source_mass_differences=reproduction,source_mass_tolerance=1e-8,
        previous_dofs=len(norms[0]),current_dofs=len(norms[1]),geometry=overlay.report,
        transport='square-root scalar mass density derived from fixed cylindrical Hphi and its actual volume; not a Maxwell transform',
        scope='original curved scalar-space inner products; axis DOFs and q constant retained; no eigenmode, frequency or identity')
    return HphiMassCoupling(*spaces,masses[0],high[1],masses[1],diagnostic),overlay


def curved_hphi_mass_coupling(previous,current,domain,*,previous_order=2,current_order=2,quadrature_order=12,
        previous_cells=None,current_cells=None,max_candidate_tests=2000000,max_overlay_triangles=250000,
        max_dofs=250000,max_sample_points=2000000):
    """Full-space q/u coupling with declared quadratic correspondence and both measures."""
    return _coupling(previous,current,domain,previous_order,current_order,quadrature_order,previous_cells,current_cells,
        max_candidate_tests,max_overlay_triangles,max_dofs,max_sample_points)[0]


def _direct_errors(coupling,overlay,coefficients,projected,orders,order,regular,max_samples):
    q,w=_sampling(overlay,order,max_samples);error=np.zeros(coefficients.shape[1])
    batch=max(1,262144//(len(q)*coefficients.shape[1]))
    for start in range(0,len(overlay.triangles),batch):
        part=replace(overlay,triangles=overlay.triangles[start:start+batch])
        bases,measures,cells=_samples(part,q,w,orders,regular);fields=[]
        for side,(space,values) in enumerate(((coupling.previous_space,coefficients),(coupling.current_space,projected))):
            scalar=np.einsum('tqi,tim->tqm',bases[side],values[space.cell_dofs[cells[side]]])
            fields.append(np.sqrt(measures[side])[:,:,None]*scalar)
        error+=np.sum((fields[0]-fields[1])**2,axis=(0,1))
    return error


def project_curved_hphi_coefficients(previous,current,coefficients,domain,*,previous_order=2,current_order=2,
        quadrature_order=12,previous_cells=None,current_cells=None,max_candidate_tests=2000000,
        max_overlay_triangles=250000,max_dofs=250000,max_sample_points=2000000,max_columns=256):
    """Orthogonal scalar projection with directly integrated loss, never a new mode."""
    integer(max_columns,'max_columns')
    raw=np.asarray(coefficients)
    if raw.ndim!=2 or raw.dtype.kind not in 'iuf' or not 0<raw.shape[1]<=max_columns or not np.isfinite(raw).all():
        raise ValueError('curved projection requires a finite real coefficient matrix within max_columns')
    coefficients=np.array(raw,dtype=float,copy=True)
    coupling,overlay=_coupling(previous,current,domain,previous_order,current_order,quadrature_order,previous_cells,current_cells,
        max_candidate_tests,max_overlay_triangles,max_dofs,max_sample_points)
    if coefficients.shape[0]!=coupling.previous_mass.shape[0]:raise ValueError('curved coefficient rows differ from the original scalar space')
    mass=coupling.current_mass;rhs=coupling.cross_mass.T@coefficients;projected=splu(mass.tocsc()).solve(rhs)
    residual=np.linalg.norm(mass@projected-rhs,axis=0);norm=np.linalg.norm(rhs,axis=0)
    relative=np.divide(residual,norm,out=np.zeros_like(norm),where=norm>0)
    source=np.sum(coefficients*(coupling.previous_mass@coefficients),axis=0)
    target=np.sum(projected*(mass@projected),axis=0)
    if not np.isfinite(source).all() or np.any((source<=0)&np.any(coefficients!=0,axis=0)):
        raise ValueError('nonzero curved coefficients require finite positive mass norms; rescale input')
    order=coupling.diagnostic['integration_orders'][-1]
    errors=[_direct_errors(coupling,overlay,coefficients,projected,(previous_order,current_order),n,
        isinstance(previous.base_mesh,AxisConnectedMesh),max_sample_points) for n in (order,order+2)]
    losses=[np.sqrt(np.divide(e,source,out=np.zeros_like(e),where=source>0)) for e in errors]
    defect=np.divide(abs(source-target-errors[-1]),source,out=np.zeros_like(source),where=source>0)
    if (not all(np.isfinite(v).all() for v in (projected,relative,source,target,*errors,*losses,defect))
            or np.any(source<0) or np.max(relative)>1e-10 or np.max(defect)>1e-8
            or np.any(target>source*(1+1e-8)) or np.max(abs(losses[0]-losses[1]))>1e-10):
        raise ValueError('curved scalar projection or directly integrated loss is numerically unresolved')
    projected.setflags(write=False)
    return HphiProjection(projected,dict(coupling=coupling.diagnostic,relative_linear_residual=relative.tolist(),
        linear_residual_tolerance=1e-10,source_squared_mass_norm=source.tolist(),projected_squared_mass_norm=target.tolist(),
        direct_squared_mass_error=errors[-1].tolist(),relative_mass_error=losses[-1].tolist(),
        relative_pythagoras_defect=defect.tolist(),pythagoras_tolerance=1e-8,difference_integration_orders=[order,order+2],
        scope='orthogonal curved scalar projection only; not a new FEM eigenmode, frequency or continuum error bound'))

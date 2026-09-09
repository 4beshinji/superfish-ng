# SPDX-License-Identifier: Apache-2.0
"""Vacuum m=0 TE: Ephi=r*v with essential electric-wall constraints."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import diags
from scipy.sparse.linalg import eigsh,ArpackNoConvergence
from .constants import C0,EPS0,MU0,TAU
from .mesh import make_mesh,element_geometry
from .mesh_input import mesh_from_dict,mesh_to_dict
from .fem import assemble
from .high_order import quadratic_space,assemble_p2,basis_p2
from .config import integer


def is_te(case):
    return case.model is not None and case.model.polarization=='te'


def validate_te_case(case):
    if not is_te(case):raise ValueError('TE solve requires explicit model.polarization=te')
    if case.geometry_order!=1:
        raise ValueError('TE currently requires straight triangular geometry; curved TE integration is pending')
    if case.has_acceleration_overrides:
        raise ValueError('TE has no axial accelerating field; remove active_length/voltage_interval/phase_origin overrides')


@dataclass
class TESolution:
    case: object
    mesh: object
    space: object
    stiffness: object
    mass: object
    eigenvalues: np.ndarray
    frequencies_hz: np.ndarray
    coefficients_v_per_m2: np.ndarray
    residuals: np.ndarray
    orthogonality_error: float
    source_mesh_data: dict

    @property
    def element_order(self):return self.case.element_order

    def fields_in_cells(self,cells,barycentric,mode=0):
        integer(mode,'TE mode',0)
        if mode>=self.case.modes:raise ValueError('TE mode is outside the saved mode range')
        cells=np.asarray(cells);bary=np.asarray(barycentric,dtype=float)
        if cells.ndim!=1 or not np.issubdtype(cells.dtype,np.integer) or np.any(cells<0) or np.any(cells>=len(self.mesh.triangles)):
            raise ValueError('TE cells must be valid integer element indices')
        if bary.shape!=(len(cells),3) or not np.isfinite(bary).all() or np.any(bary < -1e-10) or not np.allclose(bary.sum(axis=1),1,rtol=0,atol=1e-10):
            raise ValueError('TE reference points must be valid barycentric triples')
        p,_,grad=element_geometry(self.mesh);grad=grad[cells]
        if self.space is None:
            values=bary;derivatives=grad;dofs=self.mesh.triangles[cells]
        else:
            values=np.column_stack([bary[:,i]*(2*bary[:,i]-1) for i in range(3)]+[4*bary[:,i]*bary[:,j] for i,j in [(0,1),(1,2),(2,0)]])
            derivatives=np.stack([(4*bary[:,i]-1)[:,None]*grad[:,i] for i in range(3)]+[4*(bary[:,i,None]*grad[:,j]+bary[:,j,None]*grad[:,i]) for i,j in [(0,1),(1,2),(2,0)]],axis=1)
            dofs=self.space.cell_dofs[cells]
        nodal=self.coefficients_v_per_m2[dofs,mode]
        v=np.sum(values*nodal,axis=1);dv=np.einsum('ni,nij->nj',nodal,derivatives)
        r=np.einsum('ni,ni->n',p[cells,:,0],bary);omega=TAU*self.frequencies_hz[mode]
        return dict(Ephi_V_per_m=r*v,Hr_quadrature_A_per_m=-r*dv[:,1]/(omega*MU0),
                    Hz_quadrature_A_per_m=(2*v+r*dv[:,0])/(omega*MU0))


def te_matrices(case,mesh):
    validate_te_case(case)
    space=quadratic_space(mesh) if case.element_order==2 else None
    k,m=assemble(mesh) if space is None else assemble_p2(space)
    boundary=mesh.boundary_edges if space is None else space.boundary_dofs
    constrained=np.unique(boundary[np.isin(mesh.boundary_tags,['pec','electric_symmetry'])])
    free=np.setdiff1d(np.arange(k.shape[0]),constrained)
    return space,k,m,free


def solve_te(case,*,mesh_data=None):
    validate_te_case(case)
    mesh=make_mesh(case) if mesh_data is None else mesh_from_dict(case,mesh_data)
    space,k,m,free=te_matrices(case,mesh)
    if case.modes>=len(free)-1:raise ValueError('TE modes must be smaller than free degree count minus one')
    kr,mr=k[free][:,free],m[free][:,free];d=1/np.sqrt(mr.diagonal());scale=diags(d)
    try:
        values,vectors=eigsh(scale@kr@scale,k=case.modes,M=scale@mr@scale,sigma=0.,which='LM',tol=1e-10,maxiter=10000,
                             v0=np.random.default_rng(20260905).normal(size=len(free)))
    except ArpackNoConvergence as exc:raise RuntimeError('TE eigensolver did not converge') from exc
    order=np.argsort(values);values=values[order]
    if np.any(values<=0) or not np.isfinite(values).all():raise RuntimeError('TE eigenvalues must be finite and positive')
    v=np.zeros((k.shape[0],case.modes));v[free]=d[:,None]*vectors[:,order]
    v/=np.sqrt(np.sum(v*(m@v),axis=0));orth=float(np.max(abs(v.T@(m@v)-np.eye(case.modes))))
    residual=[]
    for i,value in enumerate(values):
        kv,mv=(k@v[:,i])[free],(m@v[:,i])[free]
        residual.append(np.linalg.norm(kv-value*mv)/(np.linalg.norm(kv)+value*np.linalg.norm(mv)))
        if v[np.argmax(abs(v[:,i])),i]<0:v[:,i]*=-1
    if not np.isfinite(residual).all() or max(residual)>1e-7:raise RuntimeError('TE free-equation residual exceeds 1e-7')
    v*=np.sqrt(case.normalization_j/(EPS0*np.pi))
    return TESolution(case,mesh,space,k,m,values,C0*np.sqrt(values)/TAU,v,np.asarray(residual),orth,mesh_to_dict(mesh))


def te_quantities(solution,mode=0):
    integer(mode,'TE mode',0)
    if mode>=solution.case.modes:raise ValueError('TE mode is outside the saved mode range')
    case=solution.case;v=solution.coefficients_v_per_m2[:,mode];omega=TAU*solution.frequencies_hz[mode]
    electric=EPS0*TAU*float(v@(solution.mass@v))/4
    magnetic=MU0*TAU*float(v@(solution.stiffness@v))/(4*(omega*MU0)**2)
    energy=electric+magnetic
    mesh=solution.mesh;chosen=np.flatnonzero(mesh.boundary_tags=='pec');cells=mesh.boundary_cells[chosen]
    endpoints=mesh.points[mesh.boundary_edges[chosen]];t=endpoints[:,1]-endpoints[:,0];length=np.linalg.norm(t,axis=1);t/=length[:,None]
    p,_,grad=element_geometry(mesh);surface=0.
    nodes,weights=np.polynomial.legendre.leggauss(5)
    for node,weight in zip((nodes+1)/2,weights/2):
        points=(1-node)*endpoints[:,0]+node*endpoints[:,1]
        bary=np.einsum('nij,nj->ni',grad[cells],points-p[cells,0]);bary[:,0]+=1
        fields=solution.fields_in_cells(cells,bary,mode)
        tangent=fields['Hr_quadrature_A_per_m']*t[:,0]+fields['Hz_quadrature_A_per_m']*t[:,1]
        surface+=float(np.sum(weight*length*TAU*points[:,0]*tangent**2))
    resistance=np.sqrt(omega*MU0/(2*case.conductivity_s_per_m));loss=resistance*surface/2
    if not surface>0 or not np.isfinite(surface):raise ValueError('TE PEC wall loss requires positive finite tangential magnetic energy')
    return dict(mode_index=mode+1,frequency_hz=float(solution.frequencies_hz[mode]),stored_energy_j=energy,
        electric_energy_j=electric,magnetic_energy_j=magnetic,surface_resistance_ohm=float(resistance),wall_loss_w=float(loss),
        q0=float(omega*energy/loss),geometry_factor_ohm=float(2*omega*energy/surface),
        vacc_v=None,eacc_v_per_m=None,transit_time_factor_abs=None,r_over_q_accelerator_ohm=None,r_over_q_circuit_ohm=None,
        epk_over_eacc_estimate=None,bpk_over_eacc_estimate_mt_per_mv_per_m=None,
        accelerating_quantities_status='NOT_APPLICABLE: m=0 TE has identically zero axial electric field')


class TEFieldSampler:
    """Reuse geometric point location; evaluate only TE-labelled components."""
    def __init__(self,solution):
        from .sampling import FieldSampler
        self.solution=solution
        self.locator=FieldSampler(solution.mesh.points,solution.mesh.triangles,solution.coefficients_v_per_m2,
                                  solution.frequencies_hz,space=solution.space)

    def evaluate(self,points_rz_m,mode=0,outside='raise'):
        points=np.asarray(points_rz_m,dtype=float);integer(mode,'TE mode',0)
        if mode>=self.solution.case.modes:raise ValueError('TE mode is outside the saved mode range')
        if outside not in ('raise','nan'):raise ValueError('outside must be raise or nan')
        if points.ndim!=2 or points.shape[1]!=2 or not len(points) or not np.isfinite(points).all():
            raise ValueError('TE probe coordinates must be a nonempty finite N by 2 array in (r,z) metres')
        loc=self.locator;k=min(16,len(loc.triangles));candidates=np.asarray(loc.tree.query(points,k=k)[1]).reshape(len(points),k)
        weights=loc._weights(points[:,None,:],candidates);valid=np.all((weights>=-1e-10)&(weights<=1+1e-10),axis=-1)
        cells=candidates[np.arange(len(points)),np.argmax(valid,axis=1)];found=valid.any(axis=1)
        for i in np.flatnonzero(~found):
            boxes=np.flatnonzero(np.all((points[i]>=loc.lower-1e-14)&(points[i]<=loc.upper+1e-14),axis=1))
            w=loc._weights(points[i],boxes);good=np.flatnonzero(np.all((w>=-1e-10)&(w<=1+1e-10),axis=1))
            if len(good):cells[i],found[i]=boxes[good[0]],True
        if outside=='raise' and not found.all():raise ValueError('TE probe points lie outside the mesh')
        bary=loc._weights(points,cells);bary[~found]=[1.,0.,0.]
        fields=self.solution.fields_in_cells(cells,bary,mode)
        # The queried axis is exact even if inverse barycentric coordinates round off.
        axis=found & (points[:,0]==0)
        fields['Ephi_V_per_m'][axis]=0.
        fields['Hr_quadrature_A_per_m'][axis]=0.
        for values in fields.values():values[~found]=np.nan
        return dict(fields,inside=found)

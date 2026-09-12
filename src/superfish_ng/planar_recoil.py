# SPDX-License-Identifier: Apache-2.0
"""Planar tensor recoil magnetic solve with original affine H and named potentials."""
from dataclasses import dataclass,field
from types import SimpleNamespace,MappingProxyType
import numpy as np
from scipy.sparse.linalg import spsolve
from .config import keys,integer
from .recoil_materials import PlanarRecoilPartition
from .magnetostatic_boundary import MagnetostaticBoundary,finite_signed,magnetic_field_coordinates
from .coaxial import _numeric_coordinates
from .planar_recoil_fem import planar_recoil_forms
from .mesh import element_geometry
from .fem import triangle_quadrature
from .planar_polygon import PolygonLocator


def _validate_planar_boundaries(mesh,boundaries):
    if not isinstance(boundaries,(list,tuple)) or not boundaries or any(type(b) is not MagnetostaticBoundary for b in boundaries):
        raise ValueError('explicit MagnetostaticBoundary values are required for every planar boundary edge')
    boundaries=tuple(MagnetostaticBoundary.from_dict(b.to_dict()) for b in boundaries)
    if len({b.id for b in boundaries})!=len(boundaries):raise ValueError('planar magnetostatic boundary IDs must be unique')
    owners=np.full(len(mesh.boundary_edges),-1,dtype=np.int64);fixed_boundary_nodes={};fixed_boundaries=0
    for i,boundary in enumerate(boundaries):
        edges=np.asarray(boundary.edge_indices,dtype=np.int64)
        if np.any(edges>=len(owners)) or np.any(owners[edges]!=-1):raise ValueError('planar boundary edges must be in range and assigned exactly once')
        owners[edges]=i
        if boundary.kind=='fixed_az':
            fixed_boundaries+=1
            for node in np.unique(mesh.boundary_edges[edges]):
                if node in fixed_boundary_nodes:raise ValueError('fixed-Az boundaries share a node; merge connected fixed-Az edges under one boundary ID')
                fixed_boundary_nodes[node]=boundary.id
    if np.any(owners<0):raise ValueError('every planar magnetostatic boundary must be explicit; no implicit ground or external boundary')
    if not fixed_boundaries:raise ValueError('at least one fixed-Az planar boundary is required; pure Neumann/gauge is unsupported')
    owners.setflags(write=False)
    return boundaries,owners


@dataclass(frozen=True,eq=False)
class PlanarRecoilCase:
    partition: PlanarRecoilPartition
    current_density_z_a_per_m2: dict
    boundaries: tuple
    element_order: int = 2
    quadrature_order: int = 4
    name: str = 'magnetostatic'
    boundary_owner_indices: np.ndarray = field(init=False,repr=False)

    def __post_init__(self):
        if type(self.partition) is not PlanarRecoilPartition:raise ValueError('explicit planar magnetic partition required')
        partition=PlanarRecoilPartition.from_dict(self.partition.to_dict());object.__setattr__(self,'partition',partition)
        names=[r.id for r in partition.regions];data=dict(self.current_density_z_a_per_m2) if isinstance(self.current_density_z_a_per_m2,MappingProxyType) else self.current_density_z_a_per_m2
        keys(data,names,names,'magnetostatic current_density_z_a_per_m2 by region')
        current={name:finite_signed(data[name],'current density Jz for '+name+' [A/m^2]') for name in names}
        object.__setattr__(self,'current_density_z_a_per_m2',MappingProxyType(current))
        boundaries,owners=_validate_planar_boundaries(partition.mesh,self.boundaries)
        object.__setattr__(self,'boundaries',boundaries);object.__setattr__(self,'boundary_owner_indices',owners)
        integer(self.element_order,'magnetostatic element_order');integer(self.quadrature_order,'magnetostatic quadrature_order')
        if self.element_order not in (1,2) or not 4<=self.quadrature_order<=32:raise ValueError('magnetostatic Case requires P1/P2 and quadrature_order from 4 to 32')
        if type(self.name) is not str or not self.name.strip():raise ValueError('magnetostatic name must be nonempty')

    def to_dict(self):
        return dict(format='superfish_ng_planar_recoil_case',schema_version=1,physics='linear_recoil_magnetostatic',
            name=self.name,partition=self.partition.to_dict(),current_density_z_a_per_m2=dict(self.current_density_z_a_per_m2),
            boundaries=[b.to_dict() for b in self.boundaries],element_order=self.element_order,quadrature_order=self.quadrature_order)

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','physics','name','partition','current_density_z_a_per_m2','boundaries','element_order','quadrature_order']
        keys(data,names,names,'planar magnetostatic Case')
        if (data['format']!='superfish_ng_planar_recoil_case' or type(data['schema_version']) is not int
            or data['schema_version']!=1 or data['physics']!='linear_recoil_magnetostatic'):
            raise ValueError('expected superfish_ng_planar_recoil_case version 1, linear_recoil_magnetostatic physics')
        if type(data['boundaries']) is not list:raise ValueError('magnetostatic boundaries must be a JSON list')
        return cls(PlanarRecoilPartition.from_dict(data['partition']),data['current_density_z_a_per_m2'],
            tuple(MagnetostaticBoundary.from_dict(b) for b in data['boundaries']),data['element_order'],data['quadrature_order'],data['name'])


def _edge_quadrature(space,index):
    mesh=space.partition.mesh;edge=mesh.boundary_edges[index];owner=mesh.boundary_cells[index]
    a,b=mesh.points_xy_m[edge];delta=b-a;length=np.linalg.norm(delta)
    nodes,weights=np.polynomial.legendre.leggauss(4);t=(nodes+1)/2;weights=weights/2
    local=mesh.boundary_local_vertices[index];bary=np.zeros((len(t),3));bary[:,local[0]]=1-t;bary[:,local[1]]=t
    values=bary if space.element_order==1 else np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
    # The oriented polygon boundary keeps the magnetic domain on its left.
    outward=np.array([delta[1],-delta[0]])/length
    return owner,bary,values,length*weights,outward


@dataclass(eq=False)
class PlanarRecoilSolution:
    case: PlanarRecoilCase
    space: object
    stiffness: object
    current_load_a: np.ndarray
    remanent_load_a: np.ndarray
    boundary_load_a: np.ndarray
    az_wb_per_m: np.ndarray
    az_relative_to_reference_wb_per_m: np.ndarray
    reference_az_wb_per_m: float
    free_dofs: np.ndarray
    fixed_boundary_dofs: dict
    assembly_report: dict
    relative_residual: float

    def __post_init__(self):
        _,self._determinants,self._gradients=element_geometry(self.space.mesh)
        self._locator=PolygonLocator(SimpleNamespace(points_xy_m=self.space.mesh.points,triangles=self.space.mesh.triangles))

    def fields_in_cells(self,cell_indices,barycentric):
        cells,bary=magnetic_field_coordinates(cell_indices,barycentric,len(self.space.cell_dofs))
        gradient=self._gradients[cells]
        if self.case.element_order==1:values,derivatives=bary,gradient
        else:
            values=np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
            derivatives=np.concatenate(((4*bary-1)[:,:,None]*gradient,
                np.stack([4*(bary[:,i,None]*gradient[:,j]+bary[:,j,None]*gradient[:,i]) for i,j in ((0,1),(1,2),(2,0))],axis=1)),axis=1)
        coefficients=self.az_relative_to_reference_wb_per_m[self.space.cell_dofs[cells]]
        potential=self.reference_az_wb_per_m+np.einsum('qi,qi->q',values,coefficients);gradient=np.einsum('qia,qi->qa',derivatives,coefficients)
        magnetic=np.column_stack((gradient[:,1],-gradient[:,0]));intensity=np.einsum('qij,qj->qi',self.case.partition.reluctivity_tensor_m_per_h[cells],magnetic-self.case.partition.remanent_b_t[cells])
        fields=dict(Az_Wb_per_m=potential,Bx_T=magnetic[:,0],By_T=magnetic[:,1],Hx_A_per_m=intensity[:,0],Hy_A_per_m=intensity[:,1])
        if any(not np.isfinite(v).all() for v in fields.values()):raise ValueError('magnetostatic fields exceed finite SI arithmetic')
        return fields

    def probe_at(self,points_xy_m):
        points=_numeric_coordinates(points_xy_m,2,'magnetostatic probe coordinates')
        if points.dtype.kind not in 'fi' or points.ndim!=2 or points.shape[1]!=2 or not len(points) or not np.isfinite(points).all():
            raise ValueError('magnetostatic probes require finite [x_m,y_m] points')
        try:cells,bary=self._locator.locate(points)
        except ValueError as exc:raise ValueError('magnetostatic probe is outside the declared magnetic polygon') from exc
        p=self.case.partition;owners=p.cell_region_indices[cells]
        return dict(points_xy_m=points.tolist(),cell_indices=cells.tolist(),barycentric=bary.tolist(),
            region_ids=[p.regions[i].id for i in owners],material_ids=[p.regions[i].material for i in owners],mu_r_tensor=p.mu_r_tensor[cells].tolist(),remanent_b_t=p.remanent_b_t[cells].tolist(),orientation_rad=[p.regions[i].orientation_rad for i in owners],
            fields={k:v.tolist() for k,v in self.fields_in_cells(cells,bary).items()},
            convention='static Az[Wb/m], B=(dAz/dy,-dAz/dx)[T], H=nu(original cell)*(B-Brem)[A/m]',
            interface_policy='lowest original cell at exactly represented shared edges/vertices; rounded coordinates may lie in either cell; one-sided values, no averaging')


def solve_planar_recoil(case):
    if type(case) is not PlanarRecoilCase:raise ValueError('explicit PlanarRecoilCase required')
    case=PlanarRecoilCase.from_dict(case.to_dict())
    space,k,volume,remanent,report=planar_recoil_forms(case.partition,dict(case.current_density_z_a_per_m2),case.element_order,quadrature_order=case.quadrature_order)
    boundary_load=np.zeros(len(volume));potential=np.zeros(len(volume));fixed=np.zeros(len(volume),dtype=bool);fixed_boundaries={}
    reference=next(b.value for b in case.boundaries if b.kind=='fixed_az')
    for boundary in case.boundaries:
        if boundary.kind=='fixed_az':
            dofs=np.unique(space.boundary_dofs[list(boundary.edge_indices)]);fixed[dofs]=True;potential[dofs]=boundary.value-reference;fixed_boundaries[boundary.id]=dofs
        elif boundary.kind=='tangential_h':
            for edge in boundary.edge_indices:
                owner,_,values,measure,_=_edge_quadrature(space,edge)
                np.add.at(boundary_load,space.cell_dofs[owner],-boundary.value*(values.T@measure))
    free=np.flatnonzero(~fixed);total=volume+remanent+boundary_load
    if len(free):potential[free]=spsolve(k[free][:,free],total[free]-(k@potential)[free])
    force=k@potential;denominator=np.linalg.norm(force)+np.linalg.norm(total)
    residual=float(np.linalg.norm((force-total)[free])/denominator) if denominator else 0.
    if not np.isfinite(potential).all() or not np.isfinite(residual) or residual>1e-10:
        raise ValueError('magnetostatic linear solve failed finite free-DOF residual validation')
    absolute_potential=potential+reference
    if not np.isfinite(absolute_potential).all():raise ValueError('absolute magnetostatic potential exceeds finite SI arithmetic')
    for array in (potential,absolute_potential,volume,remanent,boundary_load,free,*fixed_boundaries.values()):array.setflags(write=False)
    solution=PlanarRecoilSolution(case,space,k,volume,remanent,boundary_load,absolute_potential,potential,reference,free,MappingProxyType(fixed_boundaries),report,residual)
    planar_recoil_quantities(solution)  # Check magnetic energy/current identities before returning.
    return solution


def planar_recoil_quantities(solution):
    """Report affine constitutive potentials with explicit reference states."""
    if type(solution) is not PlanarRecoilSolution:raise ValueError('PlanarRecoilSolution required')
    s=solution;case=s.case;p=case.partition;cells=np.arange(len(p.mesh.triangles))
    quadratic=np.zeros(len(cells));coupling=np.zeros(len(cells));shifted=np.zeros(len(cells))
    for bary,weight in triangle_quadrature(case.quadrature_order+4):
        fields=s.fields_in_cells(cells,np.tile(bary,(len(cells),1)));measure=weight*s._determinants
        b=np.column_stack((fields['Bx_T'],fields['By_T']));delta=b-p.remanent_b_t
        quadratic+=.5*np.einsum('ti,tij,tj->t',b,p.reluctivity_tensor_m_per_h,b)*measure
        coupling+=np.einsum('ti,ti->t',b,p.remanent_h_a_per_m)*measure
        shifted+=.5*np.einsum('ti,tij,tj->t',delta,p.reluctivity_tensor_m_per_h,delta)*measure
    reference=.25*s._determinants*np.einsum('ti,ti->t',p.remanent_b_t,p.remanent_h_a_per_m)
    u=float(quadratic.sum());coupled=float(coupling.sum());w0=u-coupled;ws=float(shifted.sum());constant=float(reference.sum())
    def regions(values):return {v.id:float(x) for v,x in zip(p.regions,np.bincount(p.cell_region_indices,weights=values,minlength=len(p.regions)))}
    reaction=s.stiffness@s.az_relative_to_reference_wb_per_m-s.current_load_a-s.remanent_load_a-s.boundary_load_a
    fixed_reaction={name:float(reaction[dofs].sum()) for name,dofs in s.fixed_boundary_dofs.items()}
    fixed_original=dict.fromkeys(fixed_reaction,0.);circulation={v.id:0. for v in case.boundaries};flux=dict.fromkeys(circulation,0.);specified=flux_scale=0.
    for index in range(len(p.mesh.boundary_edges)):
        owner,bary,_,measure,normal=_edge_quadrature(s.space,index);fields=s.fields_in_cells(np.full(len(bary),owner,dtype=int),bary);tangent=np.array([-normal[1],normal[0]])
        line=float(measure@(fields['Hx_A_per_m']*tangent[0]+fields['Hy_A_per_m']*tangent[1]));normal_flux=float(measure@(fields['Bx_T']*normal[0]+fields['By_T']*normal[1]))
        flux_scale+=float(measure@np.hypot(fields['Bx_T'],fields['By_T']));boundary=case.boundaries[case.boundary_owner_indices[index]]
        circulation[boundary.id]+=line;flux[boundary.id]+=normal_flux
        if boundary.kind=='fixed_az':fixed_original[boundary.id]-=line
        else:specified+=boundary.value*float(measure.sum())
    current=float(sum(case.current_density_z_a_per_m2[v.id]*area for v,area in zip(p.regions,p.region_area_m2)))
    balance=sum(fixed_reaction.values())+current-specified
    current_scale=sum(abs(v) for v in fixed_reaction.values())+sum(abs(case.current_density_z_a_per_m2[v.id]*area) for v,area in zip(p.regions,p.region_area_m2))+abs(specified)
    # A zero-H remanence equilibrium may leave only roundoff-sized reactions.
    # The nonzero remanent load provides the physical current scale then.
    current_scale=max(current_scale,float(np.linalg.norm(s.remanent_load_a,1)))
    current_error=float(abs(balance)/current_scale) if current_scale else float(abs(balance))
    source_work=float(s.az_wb_per_m@s.current_load_a);remanent_work=float(s.az_relative_to_reference_wb_per_m@s.remanent_load_a)
    boundary_work=float(s.az_wb_per_m@s.boundary_load_a);fixed_work=sum(v.value*fixed_reaction[v.id] for v in case.boundaries if v.kind=='fixed_az')
    scale=2*u+abs(source_work)+abs(remanent_work)+abs(boundary_work)+abs(fixed_work)
    work_error=float(abs(2*u-source_work-remanent_work-boundary_work-fixed_work)/scale) if scale else 0.
    potential_scale=u+abs(coupled)+ws+constant
    potential_error=float(abs(w0+constant-ws)/potential_scale) if potential_scale else 0.
    coupling_scale=abs(coupled)+abs(remanent_work)+u+constant
    coupling_error=float(abs(coupled-remanent_work)/coupling_scale) if coupling_scale else 0.
    divergence=float(abs(sum(flux.values()))/flux_scale) if flux_scale else float(abs(sum(flux.values())))
    if not np.isfinite([u,coupled,w0,ws,constant,current_error,work_error,potential_error,coupling_error,divergence]).all() or min(u,ws,constant)<0 or max(current_error,work_error,potential_error,coupling_error,divergence)>1e-9:
        raise ValueError('recoil current/work/constitutive identity or divergence-free flux is unresolved')
    return dict(b_quadratic_j_per_m=u,remanence_coupling_j_per_m=coupled,constitutive_potential_b0_j_per_m=w0,
        constitutive_potential_h0_j_per_m=ws,remanent_reference_constant_j_per_m=constant,b_dot_h_j_per_m=2*u-coupled,
        region_b_quadratic_j_per_m=regions(quadratic),region_remanence_coupling_j_per_m=regions(coupling),
        region_constitutive_potential_b0_j_per_m=regions(quadratic-coupling),region_constitutive_potential_h0_j_per_m=regions(shifted),
        total_source_current_a=current,specified_tangential_h_integral_a=specified,fixed_boundary_reaction_current_a=fixed_reaction,
        fixed_boundary_original_reaction_current_a=fixed_original,boundary_original_h_circulation_a=circulation,
        original_field_ampere_balance_a=sum(circulation.values())-current,
        boundary_original_normal_flux_wb_per_m=flux,total_boundary_normal_flux_wb_per_m=sum(flux.values()),divergence_free_flux_relative_error=divergence,
        discrete_current_balance_a=balance,discrete_current_relative_error=current_error,source_work_j_per_m=source_work,
        remanent_load_work_j_per_m=remanent_work,boundary_load_work_j_per_m=boundary_work,fixed_boundary_work_j_per_m=fixed_work,
        discrete_work_relative_error=work_error,constitutive_potential_relative_error=potential_error,remanent_coupling_relative_error=coupling_error,
        free_dof_relative_residual=s.relative_residual,reference_az_wb_per_m=s.reference_az_wb_per_m,
        constitutive_convention='B=mu0*mu_rec*H+Brem; original H=nu*(B-Brem); tensors and remanent vectors follow each region orientation',
        potential_convention='w0=.5*B.nu.B-B.nu.Brem references B=0 and can be negative; ws=.5*(B-Brem).nu.(B-Brem) references H=0 and is nonnegative; both gradients with respect to B are H',
        circulation_convention='domain on left of planar tangent; curl(H)_z=Jz; fixed-Az reaction is minus original Ht integral [A]',
        flux_convention='original B dot outward normal integrated along boundary [Wb/m]; outward normal to right of tangent',
        interpretation='finite declared external boundaries; potentials are for a fixed linear recoil model, not absolute magnet internal energy or irreversible demagnetization; no winding inductance or force is inferred; discrete identities do not bound original field error')



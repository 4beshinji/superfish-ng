# SPDX-License-Identifier: Apache-2.0
"""m=0 q=r Hphi FEM on connected positive-radius PEC meshes with holes."""
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from .config import keys, integer, positive
from .constants import C0, EPS0, MU0, TAU
from .coaxial import CoaxialSpace, CoaxialSolution, _assemble, _eigenpairs, _restore_coaxial, _numeric_coordinates
from .fem import triangle_quadrature
from .high_order import quadratic_space
from .mesh import Mesh, element_geometry
from .meridional_mesh import MeridionalMesh
from .planar_polygon import PolygonLocator


@dataclass(frozen=True, eq=False)
class HphiMeshCase:
    mesh: MeridionalMesh
    element_order: int = 2
    quadrature_order: int = 8
    modes: int = 6
    normalization_j: float = 1.
    conductivity_s_per_m: float = 5.8e7
    name: str = 'positive-radius vacuum Hphi resonator'

    def __post_init__(self):
        if not isinstance(self.mesh,MeridionalMesh):
            raise ValueError('HphiMeshCase requires a validated MeridionalMesh; automatic generation is unsupported')
        for name in ('element_order','quadrature_order','modes'): integer(getattr(self,name),name)
        if self.element_order not in (1,2) or not 4 <= self.quadrature_order <= 32:
            raise ValueError('Hphi mesh requires P1/P2 and quadrature_order between 4 and 32')
        for name in ('normalization_j','conductivity_s_per_m'):
            object.__setattr__(self,name,positive(getattr(self,name),name))
        if not isinstance(self.name,str) or not self.name.strip(): raise ValueError('Hphi mesh name must be nonempty')

    @property
    def length_m(self): return float(np.ptp(self.mesh.points_rz_m[:,1]))
    @property
    def inner_radius_m(self): return float(np.min(self.mesh.points_rz_m[:,0]))
    @property
    def outer_radius_m(self): return float(np.max(self.mesh.points_rz_m[:,0]))

    def to_dict(self):
        return dict(format='superfish_ng_hphi_mesh_case',schema_version=1,name=self.name,
            model=dict(physics='rf_eigenmode',coordinates='axisymmetric',azimuthal_index=0,
                       field_family='Hphi',material='vacuum',boundary='closed_pec'),
            mesh=self.mesh.to_dict(),fem=dict(element_order=self.element_order,quadrature_order=self.quadrature_order),
            modes=self.modes,rf=dict(stored_energy_j=self.normalization_j,conductivity_s_per_m=self.conductivity_s_per_m))

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','name','model','mesh','fem','modes','rf']; keys(data,names,names,'Hphi mesh case')
        if data['format'] != 'superfish_ng_hphi_mesh_case' or type(data['schema_version']) is not int or data['schema_version'] != 1:
            raise ValueError('expected superfish_ng_hphi_mesh_case schema_version 1')
        expected=dict(physics='rf_eigenmode',coordinates='axisymmetric',azimuthal_index=0,
                      field_family='Hphi',material='vacuum',boundary='closed_pec')
        keys(data['model'],list(expected),list(expected),'Hphi mesh model')
        for name,value in expected.items():
            if type(data['model'][name]) is not type(value) or data['model'][name] != value:
                raise ValueError(f'Hphi mesh model.{name}: only {value!r} is implemented')
        names=['element_order','quadrature_order']; keys(data['fem'],names,names,'Hphi mesh FEM')
        names=['stored_energy_j','conductivity_s_per_m']; keys(data['rf'],names,names,'Hphi mesh RF')
        return cls(MeridionalMesh.from_dict(data['mesh']),**data['fem'],modes=data['modes'],name=data['name'],
                   normalization_j=data['rf']['stored_energy_j'],conductivity_s_per_m=data['rf']['conductivity_s_per_m'])

    @classmethod
    def load(cls,path):
        from .project import parse_json
        return cls.from_dict(parse_json(Path(path).read_text(encoding='utf-8')))


def hphi_mesh_matrices(case):
    if not isinstance(case,HphiMeshCase): raise ValueError('explicit HphiMeshCase required')
    # Revalidate caller-owned arrays before any solve or native publication.
    declared = MeridionalMesh.from_dict(case.mesh.to_dict())
    mesh = Mesh(declared.points_rz_m,declared.triangles,declared.boundary_edges,
                np.full(len(declared.boundary_edges),'pec',dtype='U20'),declared.boundary_cells,np.array([],dtype=np.int64))
    _,det,grad = element_geometry(mesh)
    if case.element_order == 2:
        q = quadratic_space(mesh); points,dofs,boundary = q.dof_points,q.cell_dofs,q.boundary_dofs
    else: points,dofs,boundary = mesh.points,mesh.triangles,mesh.boundary_edges
    space = CoaxialSpace(mesh,points,dofs,boundary,declared.boundary_local_vertices,det,grad)
    k,m = _assemble(space,case.element_order,case.quadrature_order)
    high = _assemble(space,case.element_order,case.quadrature_order+4)
    delta = [float(np.linalg.norm((a-b).data)/np.linalg.norm(b.data)) for a,b in zip((k,m),high)]
    if not np.isfinite(delta).all() or max(delta) > 5e-10:
        raise ValueError('Hphi mesh 1/r quadrature is unresolved; refine the mesh or increase quadrature_order')
    return space,k,m,dict(orders=[case.quadrature_order,case.quadrature_order+4],
        stiffness_relative_difference=delta[0],mass_relative_difference=delta[1],
        interpretation='finite quadrature comparison; not a discretization error bound')


@dataclass
class HphiMeshSolution(CoaxialSolution):
    def fields_at(self,points_rz_m,mode=0):
        points = _numeric_coordinates(points_rz_m,2,'Hphi mesh [r_m,z_m] probes')
        locator = PolygonLocator(SimpleNamespace(points_xy_m=self.space.mesh.points,triangles=self.space.mesh.triangles))
        try: cells,bary = locator.locate(points)
        except ValueError as exc:
            raise ValueError('Hphi probe is outside resolved vacuum, including any inner conductor') from exc
        return self.fields_in_cells(cells,bary,mode)


def restore_hphi_mesh(case,space,k,m,diagnostic,coefficients,frequencies,*,verify_spectrum=True):
    verified = _restore_coaxial(case,space,k,m,diagnostic,coefficients,frequencies,verify_spectrum=verify_spectrum)
    return HphiMeshSolution(**vars(verified))


def solve_hphi_mesh(case):
    if not isinstance(case,HphiMeshCase): raise ValueError('explicit HphiMeshCase required')
    case = HphiMeshCase.from_dict(case.to_dict())
    space,k,m,diagnostic = hphi_mesh_matrices(case)
    values,vectors = _eigenpairs(case,k,m)
    vectors *= np.sqrt(case.normalization_j/(MU0*np.pi))
    for mode in range(case.modes):
        if vectors[np.argmax(abs(vectors[:,mode])),mode] < 0: vectors[:,mode] *= -1
    return restore_hphi_mesh(case,space,k,m,diagnostic,vectors,C0/TAU*np.sqrt(values),verify_spectrum=False)


def hphi_mesh_quantities(solution,mode=0):
    if not isinstance(solution,HphiMeshSolution): raise ValueError('Hphi mesh RF requires HphiMeshSolution')
    case = solution.case; integer(mode,'mode',0)
    if mode >= case.modes: raise ValueError('Hphi mesh mode index out of range')
    space = solution.space; declared = case.mesh
    cells = np.arange(len(space.mesh.triangles)); vertices = space.mesh.points[space.mesh.triangles]
    ue = 0.; um = 0.
    for bary,weight in triangle_quadrature(case.quadrature_order+4):
        fields = solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)),mode)
        measure = TAU*(vertices[:,:,0]@bary)*weight*space.determinants
        ue += EPS0/4*float(measure@(fields['Er_quadrature_V_per_m']**2+fields['Ez_quadrature_V_per_m']**2))
        um += MU0/4*float(measure@fields['Hphi_real_A_per_m']**2)
    endpoints = space.mesh.points[space.mesh.boundary_edges]
    length = np.linalg.norm(endpoints[:,1]-endpoints[:,0],axis=1)
    walls = np.zeros(len(declared.surface_area_m2_by_segment))
    nodes,weights = np.polynomial.legendre.leggauss(case.quadrature_order+4)
    for node,weight in zip((nodes+1)/2,weights/2):
        bary = np.zeros((len(endpoints),3)); rows = np.arange(len(endpoints))
        bary[rows,space.boundary_local_vertices[:,0]] = 1-node; bary[rows,space.boundary_local_vertices[:,1]] = node
        h = solution.fields_in_cells(space.mesh.boundary_cells,bary,mode)['Hphi_real_A_per_m']
        radius = np.einsum('ti,ti->t',bary,space.mesh.points[space.mesh.triangles[space.mesh.boundary_cells],0])
        walls += np.bincount(declared.boundary_segments,weights=TAU*weight*length*radius*h*h,minlength=len(walls))
    components = []; offset = 0
    for contour in (declared.outer_rz_m,*declared.holes_rz_m):
        components.append(float(walls[offset:offset+len(contour)].sum())); offset += len(contour)
    f = float(solution.frequencies_hz[mode]); omega = TAU*f; energy = ue+um
    rs = float(np.sqrt(np.pi*f*MU0/case.conductivity_s_per_m)); wall = float(walls.sum()); loss = rs*wall/2
    if not np.isfinite([ue,um,*walls,loss]).all() or min(ue,um,wall,loss) <= 0:
        raise ValueError('invalid Hphi mesh energy or total wall loss')
    return dict(frequency_hz=f,stored_energy_j=energy,electric_energy_j=ue,magnetic_energy_j=um,
        wall_loss_w=loss,surface_resistance_ohm=rs,q0=omega*energy/loss,geometry_factor_ohm=2*omega*energy/wall,
        wall_h2_integral_a2_by_segment=walls.tolist(),wall_h2_integral_a2_by_component=components,
        volume_m3=declared.volume_m3,surface_area_m2_by_segment=declared.surface_area_m2_by_segment.tolist(),
        r_over_q_accelerator_ohm=None,r_over_q_circuit_ohm=None,vacc_v=None,eacc_v_per_m=None,
        accelerating_quantities_reason='the z axis is outside this vacuum; no acceleration path is declared')

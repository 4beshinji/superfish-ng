# SPDX-License-Identifier: Apache-2.0
"""Physical electric and magnetic inner products on identical meridional vacuum."""
from dataclasses import dataclass
import numpy as np
from .axis_hphi import AxisHphiCase,AxisHphiSolution,axis_hphi_matrices,restore_axis_hphi
from .axis_hphi_saved import _mesh_arrays as _axis_arrays
from .coaxial import CoaxialCase,CoaxialSolution,coaxial_matrices,_restore_coaxial
from .coaxial_saved import _mesh_arrays as _coaxial_arrays
from .hphi_mesh import HphiMeshCase,HphiMeshSolution,hphi_mesh_matrices,restore_hphi_mesh
from .hphi_mesh_saved import _mesh_arrays as _mesh_arrays
from .curved_hphi import CurvedHphiCase,CurvedHphiSolution
from .material_hphi import MaterialHphiCase,MaterialHphiSolution
from .config import integer
from .constants import EPS0,TAU
from .fem import triangle_quadrature
from .meridional_mesh import MeridionalMesh
from .meridional_overlap import meridional_overlay


@dataclass(frozen=True)
class HphiFieldGrams:
    # Each tuple contains previous self, previous-current cross, current self.
    electric: tuple
    magnetic: tuple
    diagnostic: dict


def _reject_unsupported_comparison(solution):
    if isinstance(solution,MaterialHphiSolution) or isinstance(getattr(solution,"case",None),MaterialHphiCase):
        raise ValueError("material Hphi comparison/tracking is unsupported; material interfaces require a separate verified correspondence")
    if isinstance(solution,CurvedHphiSolution) or isinstance(getattr(solution,"case",None),CurvedHphiCase):
        raise ValueError("curved Hphi field comparison and tracking are not implemented; inspect the original fields independently")


def _verified_solution(solution):
    _reject_unsupported_comparison(solution)
    if type(solution) is AxisHphiSolution and type(solution.case) is AxisHphiCase:
        case=AxisHphiCase.from_dict(solution.case.to_dict())
        space,k,m=axis_hphi_matrices(case)
        expected,actual=_axis_arrays(case,space),_axis_arrays(solution.case,solution.space)
        restored=restore_axis_hphi(case,space,k,m,solution.coefficients,solution.frequencies_hz)
    elif type(solution) is HphiMeshSolution and type(solution.case) is HphiMeshCase:
        case=HphiMeshCase.from_dict(solution.case.to_dict())
        space,k,m,diagnostic=hphi_mesh_matrices(case)
        expected,actual=_mesh_arrays(case,space),_mesh_arrays(solution.case,solution.space)
        restored=restore_hphi_mesh(case,space,k,m,diagnostic,solution.coefficients,solution.frequencies_hz)
    elif type(solution) is CoaxialSolution and type(solution.case) is CoaxialCase:
        case=CoaxialCase.from_dict(solution.case.to_dict())
        space,k,m,diagnostic=coaxial_matrices(case)
        expected,actual=_coaxial_arrays(space),_coaxial_arrays(solution.space)
        restored=_restore_coaxial(case,space,k,m,diagnostic,solution.coefficients,solution.frequencies_hz,verify_spectrum=True)
    else:
        raise ValueError('Hphi field comparison requires dedicated coaxial, positive-radius mesh or regular-axis FEM solutions')
    if any(not np.array_equal(value,actual[name]) for name,value in expected.items()):
        raise ValueError('Hphi solution mesh or space differs from the declared original FEM')
    return restored


def _declared_mesh(solution):
    _reject_unsupported_comparison(solution)
    case=solution.case
    if isinstance(case,(HphiMeshCase,AxisHphiCase)):
        return case.mesh
    a,b,length=case.inner_radius_m,case.outer_radius_m,case.length_m
    return MeridionalMesh([[a,0.],[b,0.],[b,length],[a,length]],[],
                          solution.space.mesh.points,solution.space.mesh.triangles)


def _field_grams(previous,current,overlay,order):
    na,nb=previous.case.modes,current.case.modes
    grams=[[np.zeros((na,na)),np.zeros((na,nb)),np.zeros((nb,nb))] for _ in range(2)]
    components=(('Er_quadrature_V_per_m','Ez_quadrature_V_per_m'),('Hphi_real_A_per_m',))
    # Every omitted cylindrical component vanishes in the verified m=0 Hphi family.
    for bary,weight in triangle_quadrature(order):
        samples=[]
        for solution,cells,vertices in (
                (previous,overlay.previous_cells,overlay.previous_vertex_barycentric),
                (current,overlay.current_cells,overlay.current_vertex_barycentric)):
            parent_bary=np.einsum('i,tij->tj',bary,vertices)
            fields=[solution.fields_in_cells(cells,parent_bary,mode) for mode in range(solution.case.modes)]
            samples.append([[np.column_stack([f[key] for f in fields]) for key in family] for family in components])
        radius=np.einsum('i,ti->t',bary,overlay.vertices_rz_m[:,:,0])
        weights=(TAU*radius*weight*overlay.determinants)[:,None]
        for family,(aa,ab,bb) in enumerate(grams):
            for a,b in zip(samples[0][family],samples[1][family]):
                aa+=a.T@(weights*a);ab+=a.T@(weights*b);bb+=b.T@(weights*b)
    return grams


def _normalized_difference(first,second):
    left,right=np.sqrt(np.diag(second[0])),np.sqrt(np.diag(second[2]))
    if not all(np.isfinite(matrix).all() for matrix in (*first,*second)) or np.any(left<=0) or np.any(right<=0):
        raise ValueError('Hphi field integrals require finite positive self norms')
    return max(float(np.max(abs(a-b)/x[:,None]/y[None,:])) for a,b,x,y in
               zip(first,second,(left,left,right),(left,right,right)))


def _source_grams(solution):
    c=solution.coefficients;omega=TAU*solution.frequencies_hz
    electric=TAU/EPS0**2*(c.T@(solution.stiffness@c))/omega[:,None]/omega[None,:]
    magnetic=TAU*(c.T@(solution.mass@c))
    return electric,magnetic


def hphi_field_grams(previous,current,*,max_candidate_tests=2000000,
                     max_overlay_triangles=250000,max_gram_modes=256):
    """Integrate original peak E and H separately with full 3D measure 2*pi*r dr dz.

    Both solutions are fully reconstructed and their lowest positive spectra
    verified. All original elements must cover exactly the same vacuum outer
    contour and PEC holes. Normalization, frequency and coefficient signs are
    retained; no rank correspondence, discretization estimate or mode ID is
    inferred. E units are V^2*m, H units A^2*m. Comparing acceleration paths or
    wall conductivities is outside this volume-field operation.
    """
    for name,value in (('max_candidate_tests',max_candidate_tests),
                       ('max_overlay_triangles',max_overlay_triangles),('max_gram_modes',max_gram_modes)):
        integer(value,name)
    for solution in (previous,current):
        _reject_unsupported_comparison(solution)
        if not isinstance(solution,(CoaxialSolution,AxisHphiSolution)):
            raise ValueError('Hphi field comparison requires dedicated Hphi FEM solutions')
        if solution.case.modes>max_gram_modes:
            raise ValueError('Hphi field comparison exceeds max_gram_modes')
    previous,current=map(_verified_solution,(previous,current))
    overlay=meridional_overlay(_declared_mesh(previous),_declared_mesh(current),
        max_candidate_tests=max_candidate_tests,max_overlay_triangles=max_overlay_triangles)
    regular=all(isinstance(s,AxisHphiSolution) for s in (previous,current))
    order=5 if regular else max(getattr(s.case,'quadrature_order',0) for s in (previous,current))+4
    orders=[order,order+2 if regular else order+4]
    low,high=(_field_grams(previous,current,overlay,n) for n in orders)
    differences=[_normalized_difference(a,b) for a,b in zip(low,high)]
    if max(differences)>1e-10:
        raise ValueError('Hphi field quadrature is unresolved; refine the mesh or increase the Case quadrature_order')
    source=[_source_grams(s) for s in (previous,current)];reproduction=[];minimum_eigenvalues=[]
    for family,matrices in enumerate(high):
        for matrix,expected in ((matrices[0],source[0][family]),(matrices[2],source[1][family])):
            norm=np.sqrt(np.diag(expected))
            reproduction.append(float(np.max(abs(matrix-expected)/norm[:,None]/norm[None,:])))
        aa,ab,bb=matrices;joint=np.block([[aa,ab],[ab.T,bb]])
        norm=np.sqrt(np.diag(joint));normalized=joint/norm[:,None]/norm[None,:]
        values=np.linalg.eigvalsh((normalized+normalized.T)/2)
        if values[0]<-1e-10*max(1.,values[-1]):
            raise ValueError('Hphi joint physical Gram matrix is not positive semidefinite')
        minimum_eigenvalues.append(float(values[0]))
    if not np.isfinite(reproduction).all() or max(reproduction)>1e-8:
        raise ValueError('Hphi field partition fails to reproduce original FEM energy inner products')
    for matrices in high:
        for matrix in matrices:matrix.setflags(write=False)
    diagnostic=dict(measure='2*pi*r dr dz; full 3D vacuum excluding PEC holes',electric_units='V^2 m',magnetic_units='A^2 m',
        phasor='peak exp(+i omega t); Hphi real, Er/Ez quadrature; field = real + i*quadrature',
        integration_orders=orders,normalized_quadrature_differences=differences,integration_tolerance=1e-10,
        maximum_source_gram_difference=max(reproduction),source_gram_tolerance=1e-8,
        minimum_normalized_joint_gram_eigenvalues=minimum_eigenvalues,overlay_triangles=len(overlay.determinants),
        mode_tracking='not_performed',scope='original volume field inner products; no continuum error bound or mode identity')
    return HphiFieldGrams(tuple(high[0]),tuple(high[1]),diagnostic)

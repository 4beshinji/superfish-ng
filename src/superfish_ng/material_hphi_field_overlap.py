# SPDX-License-Identifier: Apache-2.0
"""Original one-sided material E/H energy inner products on verified interfaces."""
from dataclasses import dataclass
import numpy as np
from .config import integer
from .constants import EPS0,MU0,TAU
from .fem import triangle_quadrature
from .material_hphi import MaterialHphiCase,MaterialHphiSolution,restore_material_hphi
from .material_hphi_saved import _mesh_arrays
from .material_hphi_comparison import MaterialHphiComparison,material_hphi_overlay
from .hphi_mapped_overlap import HphiMappedOverlay

_SAMPLE_MODE_BATCH=65536


@dataclass(frozen=True)
class MaterialHphiFieldGrams:
    # Previous self, previous-current cross, current self, all in joules.
    electric: tuple
    magnetic: tuple
    diagnostic: dict


def verified_material_hphi_solution(solution):
    if type(solution) is not MaterialHphiSolution or type(solution.case) is not MaterialHphiCase:
        raise ValueError('material comparison requires original MaterialHphiSolution objects')
    restored=restore_material_hphi(solution.case,solution.coefficients,solution.frequencies_hz)
    expected,actual=_mesh_arrays(restored.space),_mesh_arrays(solution.space)
    if expected.keys()!=actual.keys() or any(not np.array_equal(v,actual[k]) for k,v in expected.items()):
        raise ValueError('material Hphi native space or partition differs from its original declared FEM')
    return restored


def _integrate_fields(previous,current,overlay,order):
    na,nb=previous.case.modes,current.case.modes
    grams=[[np.zeros((na,na)),np.zeros((na,nb)),np.zeros((nb,nb))] for _ in range(2)]
    components=(('Er_quadrature_V_per_m','Ez_quadrature_V_per_m'),('Hphi_real_A_per_m',))
    previous_vertices=(overlay.previous_vertices_rz_m if isinstance(overlay,HphiMappedOverlay) else overlay.vertices_rz_m)
    previous_det=(overlay.previous_determinants if isinstance(overlay,HphiMappedOverlay) else overlay.determinants)
    batch=max(1,_SAMPLE_MODE_BATCH//max(na,nb))
    for start in range(0,len(overlay.determinants),batch):
        selected=slice(start,start+batch)
        for bary,weight in triangle_quadrature(order):
            samples=[]
            for solution,cells,vertices,physical,det in (
                (previous,overlay.previous_cells,overlay.previous_vertex_barycentric,previous_vertices,previous_det),
                (current,overlay.current_cells,overlay.current_vertex_barycentric,overlay.vertices_rz_m,overlay.determinants)):
                cells=cells[selected];parent_bary=np.einsum('i,tij->tj',bary,vertices[selected])
                radius=physical[selected,:,0]@bary;measure=TAU*radius*det[selected]*weight
                if not np.isfinite(measure).all() or np.any(measure<=0):raise ValueError('material volume quadrature requires positive finite measure')
                fields=[solution.fields_in_cells(cells,parent_bary,i) for i in range(solution.case.modes)]
                p=solution.case.partition;densities=(EPS0*p.epsilon_r[cells],MU0*p.mu_r[cells])
                samples.append([[np.sqrt(measure*density)[:,None]*np.column_stack([f[name] for f in fields])
                                 for name in names] for names,density in zip(components,densities)])
            for matrices,left,right in zip(grams,*samples):
                for a,b in zip(left,right):
                    matrices[0]+=a.T@a;matrices[1]+=a.T@b;matrices[2]+=b.T@b
    return grams


def _difference(low,high):
    left,right=np.sqrt(np.diag(high[0])),np.sqrt(np.diag(high[2]))
    if any(not np.isfinite(m).all() for m in (*low,*high)) or np.any(left<=0) or np.any(right<=0):
        raise ValueError('material energy Grams require finite positive self norms')
    return max(float(np.max(abs(a-b)/x[:,None]/y[None,:])) for a,b,x,y in
               zip(low,high,(left,left,right),(left,right,right)))


def _source_energy_grams(solution):
    c=solution.coefficients;omega=TAU*solution.frequencies_hz
    return (TAU/EPS0*(c.T@(solution.stiffness@c))/omega[:,None]/omega[None,:],
            TAU*MU0*(c.T@(solution.mass@c)))


def material_hphi_field_grams(previous,current,comparison,*,quadrature_order=None,
        max_candidate_tests=2000000,max_overlay_triangles=250000,max_interface_tests=2000000,
        max_interface_pieces=250000,max_gram_modes=256,max_sample_points=2000000):
    """Energy-weight original E/H in fixed cylindrical components, separately.

    Cross Grams use the geometric mean of both original material/volume
    densities. Self Grams reproduce the original K/epsilon and mu*M energy.
    Each original lowest positive spectrum is reverified; all material
    interfaces and cell ownership must match the explicit declaration.
    This is a unitary energy-L2 comparison, not a Maxwell transformation,
    frequency correction, discretization bound or mode-ID assignment.
    """
    integer(max_gram_modes,'max_gram_modes');integer(max_sample_points,'max_sample_points')
    if type(comparison) is not MaterialHphiComparison:raise ValueError('material fields require explicit MaterialHphiComparison')
    for solution,partition in ((previous,comparison.previous_partition),(current,comparison.current_partition)):
        if type(solution) is not MaterialHphiSolution or type(solution.case) is not MaterialHphiCase:
            raise ValueError('material fields require original MaterialHphiSolution objects')
        if solution.case.modes>max_gram_modes:raise ValueError('material fields exceed max_gram_modes')
        if solution.case.partition.to_dict()!=partition.to_dict():raise ValueError('material comparison partition differs from the original solution')
    order=max(16,previous.case.quadrature_order+4,current.case.quadrature_order+4) if quadrature_order is None else integer(quadrature_order,'quadrature_order',4)
    if order>36:raise ValueError('material field quadrature_order must be at most 36')
    orders=[order,order+4]
    owned=material_hphi_overlay(comparison,max_candidate_tests=max_candidate_tests,max_overlay_triangles=max_overlay_triangles,
        max_interface_tests=max_interface_tests,max_interface_pieces=max_interface_pieces)
    overlay=owned.overlay
    if len(overlay.determinants)*orders[-1]**2>max_sample_points:raise ValueError('material fields exceed max_sample_points per side and integration order')
    previous,current=map(verified_material_hphi_solution,(previous,current))
    low,high=(_integrate_fields(previous,current,overlay,n) for n in orders)
    differences=[_difference(a,b) for a,b in zip(low,high)]
    if max(differences)>1e-10:raise ValueError('material field quadrature is unresolved; refine the mesh or increase quadrature_order')
    source=[_source_energy_grams(s) for s in (previous,current)];errors=[];eigenvalues=[]
    for family,matrices in enumerate(high):
        for gram,reference in ((matrices[0],source[0][family]),(matrices[2],source[1][family])):
            norm=np.sqrt(np.diag(reference));errors.append(float(np.max(abs(gram-reference)/norm[:,None]/norm[None,:])))
        a,c,b=matrices;joint=np.block([[a,c],[c.T,b]]);norm=np.sqrt(np.diag(joint))
        normalized=joint/norm[:,None]/norm[None,:];values=np.linalg.eigvalsh((normalized+normalized.T)/2)
        if values[0]<-1e-10*max(1.,values[-1]):raise ValueError('material joint energy Gram is not positive semidefinite')
        eigenvalues.append(float(values[0]))
    if not np.isfinite(errors).all() or max(errors)>1e-8:raise ValueError('material field partition does not reproduce original FEM energy Grams')
    for matrices in high:
        for matrix in matrices:matrix.setflags(write=False)
    diagnostic=dict(format='superfish_ng_material_hphi_field_grams',schema_version=1,
        measure='2*pi*r dr dz on each original side; epsilon0*epsilon_r for E, mu0*mu_r for H',
        electric_units='J',magnetic_units='J',self_diagonal='2 * total stored energy in joules',
        transport='fixed cylindrical components; geometric mean of original energy densities; unitary energy-L2 comparison',
        phasor='peak exp(+i omega t); Hphi real and Er/Ez quadrature',integration_orders=orders,
        normalized_quadrature_differences=differences,integration_tolerance=1e-10,
        maximum_source_gram_difference=max(errors),source_gram_tolerance=1e-8,
        minimum_normalized_joint_gram_eigenvalues=eigenvalues,overlay_triangles=len(overlay.determinants),
        interface_pieces=len(owned.interfaces.previous_edges),mode_tracking='not_performed',
        scope='original material volume fields; no continuum error bound or mode identity')
    return MaterialHphiFieldGrams(tuple(high[0]),tuple(high[1]),diagnostic)

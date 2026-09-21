# SPDX-License-Identifier: Apache-2.0
"""Separate physical E/H Grams on complete explicit quadratic Hphi domains."""
import numpy as np
from dataclasses import replace
from .config import integer
from .constants import TAU
from .curved_hphi import CurvedHphiCase,CurvedHphiSolution,restore_curved_hphi
from .curved_hphi_saved import _mesh_arrays
from .curved_hphi_comparison import build_curved_hphi_comparison,CurvedHphiComparisonBudgetExceeded
from .hphi_field_overlap import HphiFieldGrams,_normalized_difference,_source_grams
from .fem import triangle_quadrature

_SAMPLE_MODE_BATCH=262144


def verified_curved_hphi_solution(solution):
    """Rebuild the original lowest positive FEM spectrum and every native DOF."""
    if type(solution) is not CurvedHphiSolution or type(solution.case) is not CurvedHphiCase:
        raise ValueError('curved comparison requires original vacuum CurvedHphiSolution objects')
    restored=restore_curved_hphi(solution.case,solution.coefficients,solution.frequencies_hz)
    expected,actual=_mesh_arrays(restored.space),_mesh_arrays(solution.space)
    if actual.keys()!=expected.keys() or any(not np.array_equal(v,actual[k]) for k,v in expected.items()):
        raise ValueError('curved Hphi native geometry or space differs from the original declared FEM')
    return restored


def _samples(solution,rows):
    cells=np.concatenate([np.full(len(row['native_barycentric']),row['native_cell'],dtype=int) for row in rows])
    bary=np.concatenate([row['native_barycentric'] for row in rows])
    names=(('Er_quadrature_V_per_m','Ez_quadrature_V_per_m'),('Hphi_real_A_per_m',))
    result=[[np.empty((len(cells),solution.case.modes)) for name in family] for family in names]
    for mode in range(solution.case.modes):
        fields=solution.fields_in_cells(cells,bary,mode)
        for family,matrices in zip(names,result):
            for name,matrix in zip(family,matrices):matrix[:,mode]=fields[name]
    return result


def _integrate_fields(previous,current,overlay,order,max_sample_points):
    """Quadrature seam also accepts explicit test integrands, never public input."""
    rule=list(triangle_quadrature(order));q=np.array([p for p,w in rule]);w=np.array([w for p,w in rule])
    if len(rule)*len(overlay.triangles)>max_sample_points:
        raise CurvedHphiComparisonBudgetExceeded('curved Hphi field quadrature exceeds max_sample_points')
    na,nb=previous.case.modes,current.case.modes
    grams=[[np.zeros((na,na)),np.zeros((na,nb)),np.zeros((nb,nb))] for _ in range(2)]
    # Bound resident field storage independently of the total geometry budget.
    # One triangle is the smallest chunk; no quadrature point is omitted.
    batch=max(1,_SAMPLE_MODE_BATCH//(len(rule)*max(na,nb)))
    for start in range(0,len(overlay.triangles),batch):
        part=replace(overlay,triangles=overlay.triangles[start:start+batch]);samples=[]
        for side,solution in enumerate((previous,current)):
            rows=part.evaluate(side,q)
            measure=np.concatenate([TAU*row['points_rz_m'][:,0]*row['determinant_m2']*w for row in rows])
            if not np.isfinite(measure).all() or np.any(measure<=0):
                raise ValueError('curved Hphi volume quadrature requires finite positive interior measure')
            root=np.sqrt(measure)[:,None]
            samples.append([[root*values for values in family] for family in _samples(solution,rows)])
        for matrices,left,right in zip(grams,*samples):
            for a,b in zip(left,right):
                matrices[0]+=a.T@a;matrices[1]+=a.T@b;matrices[2]+=b.T@b
    return grams


def curved_hphi_field_grams(previous,current,domain,*,previous_cells=None,current_cells=None,
                            quadrature_order=None,max_candidate_tests=2000000,
                            max_overlay_triangles=250000,max_gram_modes=256,max_sample_points=2000000):
    """Integrate original peak E/H with each actual quadratic 3D volume.

    A common reference-point pair represents the declared correspondence.
    Cross products use sqrt(dV_previous*dV_current), equivalent to transporting
    fixed cylindrical components with the positive square root of volume density.
    This preserves source self Grams; it is not a Maxwell coordinate transform,
    a frequency scaling law, a discretization bound, or mode tracking.
    """
    for name,value in (('max_candidate_tests',max_candidate_tests),('max_overlay_triangles',max_overlay_triangles),
                       ('max_gram_modes',max_gram_modes),('max_sample_points',max_sample_points)):
        integer(value,name)
    if quadrature_order is not None:
        integer(quadrature_order,'quadrature_order',2)
        if quadrature_order>36:raise ValueError('curved Hphi comparison quadrature_order must not exceed 36')
    for solution in (previous,current):
        if type(solution) is not CurvedHphiSolution or type(solution.case) is not CurvedHphiCase:
            raise ValueError('curved comparison requires original vacuum CurvedHphiSolution objects')
        if solution.case.modes>max_gram_modes:raise ValueError('curved Hphi comparison exceeds max_gram_modes')
    previous,current=map(verified_curved_hphi_solution,(previous,current))
    overlay=build_curved_hphi_comparison(previous.case.geometry,current.case.geometry,domain,
        previous_cells=previous_cells,current_cells=current_cells,max_pair_tests=max_candidate_tests,
        max_triangles=max_overlay_triangles)
    order=max(16,previous.case.quadrature_order+4,current.case.quadrature_order+4) if quadrature_order is None else quadrature_order
    orders=[order,order+4]
    low,high=(_integrate_fields(previous,current,overlay,n,max_sample_points) for n in orders)
    differences=[_normalized_difference(a,b) for a,b in zip(low,high)]
    if max(differences)>1e-10:
        raise ValueError('curved Hphi field quadrature is UNVERIFIED; increase quadrature_order or refine the declared native partition')
    source=[_source_grams(s) for s in (previous,current)];reproduction=[];minimum=[]
    for family,matrices in enumerate(high):
        for matrix,expected in ((matrices[0],source[0][family]),(matrices[2],source[1][family])):
            norm=np.sqrt(np.diag(expected))
            reproduction.append(float(np.max(abs(matrix-expected)/norm[:,None]/norm[None,:])))
        aa,ab,bb=matrices;joint=np.block([[aa,ab],[ab.T,bb]])
        norm=np.sqrt(np.diag(joint));normalized=joint/norm[:,None]/norm[None,:]
        values=np.linalg.eigvalsh((normalized+normalized.T)/2)
        if values[0]<-1e-10*max(1.,values[-1]):
            raise ValueError('curved Hphi joint physical Gram is not positive semidefinite')
        minimum.append(float(values[0]))
    if not np.isfinite(reproduction).all() or max(reproduction)>1e-8:
        raise ValueError('curved Hphi comparison fails to reproduce original FEM energy Grams')
    for matrices in high:
        for matrix in matrices:matrix.setflags(write=False)
    diagnostic=dict(measure='2*pi*r dr dz on each full quadratic vacuum excluding all PEC holes',
        electric_units='V^2 m',magnetic_units='A^2 m',
        phasor='peak exp(+i omega t); Hphi real, Er/Ez quadrature; field = real + i*quadrature',
        integration_orders=orders,normalized_quadrature_differences=differences,integration_tolerance=1e-10,
        maximum_source_gram_difference=max(reproduction),source_gram_tolerance=1e-8,
        minimum_normalized_joint_gram_eigenvalues=minimum,geometry=overlay.report,
        scalar_fields=[s.space.scalar for s in (previous,current)],
        excluded_static_dimensions=[0 if s.case.axis_connected else 1 for s in (previous,current)],
        spectrum='each original lowest positive FEM spectrum reverified; static q circulation is excluded, regular-axis u retained',
        transport='fixed cylindrical components with square-root volume density; unitary L2 comparison, not a Maxwell transform',
        mode_tracking='not_performed',scope='original curved volume field inner products; no continuum error bound or mode identity')
    return HphiFieldGrams(tuple(high[0]),tuple(high[1]),diagnostic)

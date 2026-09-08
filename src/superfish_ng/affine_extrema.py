# SPDX-License-Identifier: Apache-2.0
"""Continuous enclosures of represented affine P1/P2 PEC fields."""
from fractions import Fraction
import numpy as np
from .constants import EPS0,TAU
from .mesh_input import mesh_from_dict,mesh_to_dict
from .high_order import quadratic_space
from .rational_bounds import add,multiply,polynomial,bound_rational_norm

_GRADIENTS=((-1,-1),(1,0),(0,1))


def _combine(functions,values):
    result=polynomial([0])
    for function,value in zip(functions,values):result=add(result,multiply(function,[Fraction(float(value))]))
    return result


def _subtract(a,b):return add(a,[-v for v in b])


class AffineSurfaceTrace:
    """Validated affine geometry and canonical coefficient numbering.

    A trace enclosure certifies the represented field only, so manufactured
    non-eigenfields are allowed. No eigensolve residual is used as a peak bound.
    """
    def __init__(self,case,solution):
        if case.geometry_order!=1 or case.element_order not in (1,2) or solution.element_order!=case.element_order:
            raise ValueError('affine surface traces require matching straight P1/P2 case and solution')
        self.mesh=mesh_from_dict(case,mesh_to_dict(solution.mesh))
        space=quadratic_space(self.mesh) if case.element_order==2 else None
        count=len(space.dof_points) if space else len(self.mesh.points)
        frequencies=np.asarray(solution.frequencies_hz);coefficients=np.asarray(solution.u)
        if frequencies.shape!=(case.modes,) or np.iscomplexobj(frequencies) or not np.isfinite(frequencies).all() or np.any(frequencies<=0):
            raise ValueError('surface frequencies must be positive finite real values for every mode')
        if coefficients.shape!=(count,case.modes) or np.iscomplexobj(coefficients) or not np.isfinite(coefficients).all():
            raise ValueError('surface coefficients must be finite real values in the matching FEM space')
        if space and (solution.space is None or any(not np.array_equal(getattr(space,k),getattr(solution.space,k)) for k in ('dof_points','cell_dofs','boundary_dofs'))):
            raise ValueError('surface coefficient numbering differs from the canonical P2 space')
        self.order=case.element_order;self.u=coefficients.copy();self.frequencies=frequencies.copy()
        self.dofs=space.cell_dofs if space else self.mesh.triangles

    def edge_polynomials(self,boundary_index,mode=0):
        """Exact binary vertex/coefficient traces along stored edge endpoints.

        The affine Jacobian is formed by exact subtraction of vertex values;
        rounded physical gradients or rounded P2 midpoint coordinates are not
        interpolated back into an alleged exact representation.
        """
        if type(boundary_index) is not int or not 0<=boundary_index<len(self.mesh.boundary_edges):
            raise ValueError('boundary_index must be an available zero-based integer')
        if type(mode) is not int or not 0<=mode<len(self.frequencies):raise ValueError('mode must be an available zero-based integer')
        cell=int(self.mesh.boundary_cells[boundary_index]);triangle=self.mesh.triangles[cell]
        edge=self.mesh.boundary_edges[boundary_index]
        a,b=[int(np.flatnonzero(triangle==v)[0]) for v in edge]
        bary=[polynomial([int(i==a),int(i==b)-int(i==a)]) for i in range(3)]
        basis=bary;derivatives=[[polynomial([v]) for v in g] for g in _GRADIENTS]
        if self.order==2:
            basis=[multiply(n,add(multiply([2],n),[-1])) for n in bary]
            derivatives=[[multiply(add(multiply([4],bary[i]),[-1]),[g]) for g in _GRADIENTS[i]] for i in range(3)]
            for i,j in ((0,1),(1,2),(2,0)):
                basis.append(multiply([4],multiply(bary[i],bary[j])))
                derivatives.append([multiply([4],add(multiply([_GRADIENTS[i][k]],bary[j]),multiply([_GRADIENTS[j][k]],bary[i]))) for k in range(2)])
        points=[[Fraction(float(v)) for v in point] for point in self.mesh.points[triangle]]
        rx,ry=points[1][0]-points[0][0],points[2][0]-points[0][0]
        zx,zy=points[1][1]-points[0][1],points[2][1]-points[0][1]
        det=rx*zy-ry*zx
        if det<=0:raise ValueError('surface triangle must have positive exact orientation')
        radius=_combine(bary,self.mesh.points[triangle,0]);coefficients=self.u[self.dofs[cell],mode]
        u=_combine(basis,coefficients);ux,uy=[_combine([g[k] for g in derivatives],coefficients) for k in range(2)]
        er=multiply(radius,_subtract(multiply(ux,[ry]),multiply(uy,[rx])))
        ez=add(multiply(u,[2*det]),multiply(radius,_subtract(multiply(ux,[zy]),multiply(uy,[zx]))))
        # Match the existing peak contract: the binary omega*epsilon factor is an explicit input constant.
        factor=float(TAU*self.frequencies[mode]*EPS0)
        if not np.isfinite(factor) or factor<=0:raise ValueError('surface frequency factor is outside the representable positive range')
        return dict(electric=(er,ez),denominator=polynomial([det*Fraction(factor)]),magnetic=multiply(radius,u))


def bound_affine_surface_peaks(case,solution,mode=0,*,relative_tolerance=1e-6,max_boxes_per_edge=10000):
    """Enclose maxima on all closed PEC edges; keep both one-sided corner traces."""
    trace=AffineSurfaceTrace(case,solution);indices=np.flatnonzero(trace.mesh.boundary_tags=='pec')
    if not len(indices):raise ValueError('surface extrema require PEC edges')
    reports={'electric_v_per_m':[],'magnetic_a_per_m':[]}
    for raw in indices:
        edge=int(raw);functions=trace.edge_polynomials(edge,mode)
        for name,numerator,denominator in (('electric_v_per_m',functions['electric'],functions['denominator']),('magnetic_a_per_m',[functions['magnetic']],[1])):
            bound=bound_rational_norm(numerator,denominator,relative_tolerance=relative_tolerance,max_boxes=max_boxes_per_edge)
            reports[name].append(dict(bound,boundary_index=edge))
    maxima={}
    for name,bounds in reports.items():
        best=max(bounds,key=lambda b:b['lower_bound']);edge=best['boundary_index'];t=best['parameter']
        ends=trace.mesh.points[trace.mesh.boundary_edges[edge]]
        maxima[name]=dict(lower_bound=best['lower_bound'],upper_bound=max(b['upper_bound'] for b in bounds),boundary_index=edge,
            parameter=t,parameter_fraction=best['parameter_fraction'],point_rz_m=((1-t)*ends[0]+t*ends[1]).tolist(),boxes=sum(b['boxes'] for b in bounds))
    return dict(status='PASS',element_order=trace.order,relative_tolerance=relative_tolerance,pec_edges=len(indices),
        scope='continuous extrema of exact represented affine discrete fields; not a physical peak or discretization error bound',
        corner_convention='all PEC edges closed; one-sided cell derivatives retained',physical_error_bound=None,**maxima)


def assess_saved_affine_peaks(run,*,mode=0,relative_tolerance=1e-6,max_boxes_per_edge=10000):
    """Revalidate native fields and retain their exact source identity."""
    from pathlib import Path
    from .affine_saved import read_verified_affine_solution
    from .saved_mode_tracking import _snapshot
    run=Path(run).resolve();source=_snapshot(run);solution=read_verified_affine_solution(run)
    peaks=bound_affine_surface_peaks(solution.case,solution,mode,relative_tolerance=relative_tolerance,max_boxes_per_edge=max_boxes_per_edge)
    if source!=_snapshot(run):raise ValueError('affine peak sources changed during evaluation')
    return dict(schema_version=1,document_type='affine_discrete_surface_peaks',run=str(run),mode_index=mode,
        relative_tolerance=relative_tolerance,max_boxes_per_edge=max_boxes_per_edge,source=source,peaks=peaks)


def save_affine_peaks(run,path,**options):
    import json
    from pathlib import Path
    result=assess_saved_affine_peaks(run,**options)
    with Path(path).open('x',encoding='utf-8') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


def replay_affine_peaks(document):
    from .config import keys
    from .saved_mode_tracking import _canonical
    fields=('schema_version','document_type','run','mode_index','relative_tolerance','max_boxes_per_edge','source','peaks')
    keys(document,fields,fields,'affine discrete surface peaks')
    result=assess_saved_affine_peaks(document['run'],mode=document['mode_index'],relative_tolerance=document['relative_tolerance'],max_boxes_per_edge=document['max_boxes_per_edge'])
    if _canonical(result)!=_canonical(document):raise ValueError('affine surface peak replay differs from saved data or sources')
    return result


def read_affine_peaks(path):
    from pathlib import Path
    from .project import parse_json
    return replay_affine_peaks(parse_json(Path(path).read_text(encoding='utf-8')))

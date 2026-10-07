# SPDX-License-Identifier: Apache-2.0
"""Reuse one identical native high-order assembly inside a serial N07 step.

The original assembler still computes every stored matrix. The entry expires
when this context ends; no eigensolve, reference, or other execution is reused.
Returned sparse matrices are independent copies of immutable cache storage.
"""
from contextlib import contextmanager
from functools import wraps
import hashlib
import inspect

import numpy as np
from scipy.sparse import isspmatrix_csr

from . import curved_adaptive_refinement, geometry_surface_numerics
from .curved_fem import assemble_curved
from .curved_mesh import CurvedGeometryCandidate
from .curved_refinement import RestrictedGeometry
from .curved_space import CurvedSpace
from .quadratic_geometry import QuadraticTriangle


def _fingerprint(space):
    """Bind every operand actually read by the original global assembler."""
    if type(space) is not CurvedSpace or type(space.geometry) not in (CurvedGeometryCandidate,RestrictedGeometry):
        raise ValueError('high-order reuse requires the original native CurvedSpace/geometry types')
    geometry=space.geometry
    if (type(geometry.local_maps) is not tuple or not geometry.local_maps or
            any(type(mapping) is not QuadraticTriangle for mapping in geometry.local_maps)):
        raise ValueError('high-order reuse requires original immutable QuadraticTriangle maps')
    arrays=(geometry.points_rz_m,geometry.cell_nodes,*(m.points_rz_m for m in geometry.local_maps))
    bound=hashlib.sha256()
    for array in arrays:
        if type(array) is not np.ndarray or array.flags.writeable:
            raise ValueError('high-order reuse requires original read-only native assembly operands')
        bound.update(str((array.dtype.str,array.shape)).encode('ascii'))
        bound.update(array.tobytes(order='C'))
    return bound.hexdigest()


def _matrix_bytes(matrices):
    return sum(a.nbytes for matrix in matrices for a in (matrix.data,matrix.indices,matrix.indptr))


@contextmanager
def reuse_high_order_assembly(recorder,space,order,*,maximum_cache_bytes=512*1024**2):
    """Share only the two original high-quadrature consumer aliases.

Same object, order and complete operand digest are required for a hit. Other
arguments go directly to their original callable. A changed native operand
invalidates the entry. Large entries simply remain uncached; this does not
change the N05 resource budget or physics/quality/accuracy gates.
    """
    recorder._require_owner()
    if type(order) is not int or order<2:
        raise ValueError('high-order reuse order must be an integer >= 2')
    if type(maximum_cache_bytes) is not int or maximum_cache_bytes<0:
        raise ValueError('maximum_cache_bytes must be a nonnegative integer')
    _fingerprint(space)
    stats=dict(order=order,original_assembly_calls=0,original_assemblies=0,cache_hits=0,invalidations=0,
               peak_cached_matrix_bytes=0,oversized_entries=0,maximum_cache_bytes=maximum_cache_bytes,
               scope='one serial higher-quadrature context; identical original native operand bytes; independent CSR copies; no solve/reference/cross-level or cross-worker reuse')
    modules=(curved_adaptive_refinement,geometry_surface_numerics)
    selected=[];cache=None;cache_digest=None;failure=None
    for module in modules:
        original=module.assemble_curved
        if inspect.unwrap(original) is not assemble_curved and inspect.unwrap(original) is not inspect.unwrap(assemble_curved):
            raise ValueError('high-order reuse alias does not bind the original native assembler')
        selected.append((module,original))

    def wrapper(original):
        @wraps(original)
        def reused(*args,**kwargs):
            nonlocal cache,cache_digest
            recorder._require_owner()
            if (len(args)!=1 or args[0] is not space or set(kwargs)!={'quadrature_order'} or
                    type(kwargs['quadrature_order']) is not int or kwargs['quadrature_order']!=order):
                return original(*args,**kwargs)
            with recorder.phase('high_order_assembly_lookup_and_copy'):
                current=_fingerprint(space)
                if cache is not None and current==cache_digest:
                    stats['cache_hits']+=1
                    return tuple(matrix.copy() for matrix in cache)
                if cache is not None:
                    stats['invalidations']+=1;cache=None;cache_digest=None
            stats['original_assembly_calls']+=1
            matrices=original(*args,**kwargs)
            stats['original_assemblies']+=1
            with recorder.phase('high_order_assembly_bind_and_store'):
                if _fingerprint(space)!=current:
                    raise ValueError('native assembly operands changed during high-order assembly')
                if type(matrices) is not tuple or len(matrices)!=2 or any(not isspmatrix_csr(m) for m in matrices):
                    raise ValueError('original high-order assembly did not return its native CSR pair')
                size=_matrix_bytes(matrices)
                if size>maximum_cache_bytes:
                    stats['oversized_entries']+=1
                else:
                    cache=tuple(matrix.copy() for matrix in matrices);cache_digest=current
                    for matrix in cache:
                        for array in (matrix.data,matrix.indices,matrix.indptr):array.setflags(write=False)
                    stats['peak_cached_matrix_bytes']=max(stats['peak_cached_matrix_bytes'],size)
            return matrices
        return reused

    installed=[]
    try:
        for module,original in selected:
            reused=wrapper(original);module.assemble_curved=reused
            installed.append((module,original,reused))
        yield stats
    except BaseException as error:
        failure=error;raise
    finally:
        recorder._require_owner();conflicts=[]
        for module,original,reused in reversed(installed):
            if module.assemble_curved is reused:module.assemble_curved=original
            else:conflicts.append(module.__name__+'.assemble_curved')
        cache=None
        if conflicts:
            message='high-order reuse binding changed outside its serial context: '+', '.join(conflicts)
            if failure is None:raise ValueError(message)
            if hasattr(failure,'add_note'):failure.add_note(message)

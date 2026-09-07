# SPDX-License-Identifier: Apache-2.0
"""Mapped P2 TM integration and global assembly on validated curved spaces."""
import numpy as np
from .fem import triangle_quadrature
from .quadratic_geometry import QuadraticTriangle,quadratic_minimum,_VANDERMONDE


def mapped_element_matrices(geometry, *, quadrature_order=8):
    """Assemble one curved element; rational stiffness needs convergence checks."""
    if not isinstance(geometry,QuadraticTriangle):
        raise ValueError('mapped assembly requires a validated QuadraticTriangle')
    if type(quadrature_order) is not int or quadrature_order<2:
        raise ValueError('quadrature_order must be an integer >= 2')
    radius = geometry.points_rz_m[:,0]
    controls = np.r_[radius[:3],2*radius[3:]-.5*radius[[0,1,2]]-.5*radius[[1,2,0]]]
    if np.any(controls<0):
        radius_coefficients = np.linalg.solve(_VANDERMONDE,radius)
        if quadratic_minimum(radius_coefficients)[0]<0:
            raise ValueError('mapped element crosses r=0; negative physical radius is unsupported')
    rule = list(triangle_quadrature(order=quadrature_order))
    mapped = geometry.evaluate([barycentric[1:] for barycentric,_ in rule])
    stiffness = np.zeros((6,6)); mass = np.zeros((6,6))
    for i,(_,weight) in enumerate(rule):
        n = mapped['basis_values'][i]
        derivative = mapped['basis_gradients'][i]
        radius = mapped['points_rz_m'][i,0]
        measure = weight*mapped['determinant_m2'][i]
        curl_z = 2*n+radius*derivative[:,0]
        curl_r = radius*derivative[:,1]
        stiffness += measure*radius*(np.outer(curl_z,curl_z)+np.outer(curl_r,curl_r))
        mass += measure*radius**3*np.outer(n,n)
    return stiffness,mass


def assemble_curved(space, *, quadrature_order=8):
    """Scatter mapped local matrices through the unique shared node indices."""
    from scipy.sparse import coo_matrix
    from .curved_space import CurvedSpace
    if not isinstance(space,CurvedSpace):
        raise ValueError('global curved assembly requires a validated CurvedSpace')
    geometry = space.geometry
    local = [mapped_element_matrices(mapping,quadrature_order=quadrature_order)
             for mapping in geometry.local_maps]
    rows = np.repeat(geometry.cell_nodes,6,axis=1).ravel()
    columns = np.tile(geometry.cell_nodes,(1,6)).ravel()
    size = len(geometry.points_rz_m)
    matrices = tuple(coo_matrix((np.array([pair[i] for pair in local]).ravel(),(rows,columns)),
                               shape=(size,size)).tocsr() for i in (0,1))
    if any(not np.isfinite(matrix.data).all() for matrix in matrices):
        raise ValueError('curved assembly exceeds floating-point range')
    return matrices

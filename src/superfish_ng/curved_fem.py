# SPDX-License-Identifier: Apache-2.0
"""Local mapped P2 TM integration, not yet a global curved-mesh solver."""
import numpy as np
from .fem import triangle_quadrature
from .quadratic_geometry import QuadraticTriangle,quadratic_minimum,_VANDERMONDE


def mapped_element_matrices(geometry, *, quadrature_order=8):
    """Assemble one curved element; rational stiffness needs convergence checks."""
    if not isinstance(geometry,QuadraticTriangle):
        raise ValueError('mapped assembly requires a validated QuadraticTriangle')
    if type(quadrature_order) is not int or quadrature_order<2:
        raise ValueError('quadrature_order must be an integer >= 2')
    radius_coefficients = np.linalg.solve(_VANDERMONDE,geometry.points_rz_m[:,0])
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

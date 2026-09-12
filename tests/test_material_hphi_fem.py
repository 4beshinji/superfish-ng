# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.linalg import eigvalsh
from superfish_ng.material_hphi_fem import material_hphi_matrices
from superfish_ng.axis_connected_fem import axis_connected_matrices
from superfish_ng.hphi_mesh import HphiMeshCase,hphi_mesh_matrices
from superfish_ng.rf_materials import RFMaterialPartition,RFMaterialRegion
from test_rf_materials import partition


class MaterialHphiFormTests(unittest.TestCase):
    def test_uniform_epsilon_mu_scaling_and_correct_static_kernel(self):
        for axis in (False,True):
            for order in (1,2):
                for eps,mu in ((1.,1.),(4.,9.),(.5,2.)):
                    p=partition(axis,1,uniform=(eps,mu));space,k,m,report=material_hphi_matrices(p,order)
                    old=axis_connected_matrices(p.mesh,order) if axis else hphi_mesh_matrices(HphiMeshCase(p.mesh,element_order=order,quadrature_order=12))
                    for actual,expected,factor in ((k,old[1],1/eps),(m,old[2],mu)):
                        self.assertLess(np.linalg.norm((actual-factor*expected).data)/np.linalg.norm(expected.data)/factor,1e-12)
                    values=eigvalsh(k.toarray(),m.toarray());reference=eigvalsh(old[1].toarray(),old[2].toarray())
                    start=0 if axis else 1
                    np.testing.assert_allclose(values[start:],reference[start:]/(eps*mu),rtol=1e-10,atol=0)
                    if axis:self.assertGreater(values[0],0.);self.assertGreater(len(space.axis_dofs),0)
                    else:self.assertLess(np.linalg.norm(k@np.ones(k.shape[0]))/np.linalg.norm(k.data),1e-12)

    def test_layered_exact_field_and_boundary_traction_patch(self):
        # Manufactured Hphi: q=f(z) or u=f(z), f'=epsilon_r. It is a driven
        # weak-form patch, not a PEC resonant mode. Tangential E is continuous
        # at the z interface and the original scalar trace is shared.
        nodes,weights=np.polynomial.legendre.leggauss(16);t=(nodes+1)/2;weights=weights/2;cut=1/16
        for axis in (False,True):
            for order in (1,2):
                for holes in (0,2):
                    p=partition(axis,holes);space,k,m,_=material_hphi_matrices(p,order)
                    def field(z):return 2*np.minimum(z,cut)+5*np.maximum(z-cut,0.)+1.
                    coefficients=field(space.dof_points[:,1]);force=np.zeros(k.shape[0]);mesh=p.mesh
                    for edge,owner,local in zip(mesh.boundary_edges,mesh.boundary_cells,mesh.boundary_local_vertices):
                        a,b=mesh.points_rz_m[edge];dr,dz=b-a;points=(1-t[:,None])*a+t[:,None]*b;r,z=points.T
                        bary=np.zeros((len(t),3));bary[:,local[0]]=1-t;bary[:,local[1]]=t
                        basis=bary if order==1 else np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
                        traction=(2*r*r*field(z)*dz/p.epsilon_r[owner]-r**3*dr) if axis else -dr/r
                        np.add.at(force,space.cell_dofs[owner],basis.T@(weights*traction))
                    self.assertLess(np.linalg.norm(k@coefficients-force)/np.linalg.norm(force),1e-11)
                    self.assertGreater(len(p.interface_cells),0)
                    for edge,cells in zip(p.interface_edges,p.interface_cells):
                        r,z=mesh.points_rz_m[edge].mean(axis=0);traces=[]
                        for cell in cells:
                            dofs=space.cell_dofs[cell];x,y=space.dof_points[dofs].T
                            matrix=np.column_stack((np.ones(len(x)),x,y))
                            if order==2:matrix=np.column_stack((matrix,x*x,x*y,y*y))
                            polynomial=np.linalg.solve(matrix,coefficients[dofs])
                            if order==1:polynomial=np.r_[polynomial,0.,0.,0.]
                            value=polynomial@np.array([1.,r,z,r*r,r*z,z*z])
                            dr=polynomial@np.array([0.,1.,0.,2*r,z,0.]);dz=polynomial@np.array([0.,0.,1.,0.,r,2*z])
                            # E multiplied by omega*epsilon0; D by omega.
                            traces.append([r*value,r*dz/p.epsilon_r[cell],-(2*value+r*dr)] if axis else
                                          [value/r,dz/(p.epsilon_r[cell]*r),-dr/r])
                        expected=[r*field(z),r,-2*field(z)] if axis else [field(z)/r,1/r,0.]
                        for trace in traces:np.testing.assert_allclose(trace,expected,rtol=1e-11,atol=1e-11)

    def test_region_order_does_not_change_physical_forms_and_controls_are_strict(self):
        p=partition(True,2);changed=RFMaterialPartition(p.mesh,p.materials[::-1],p.regions[::-1])
        a=material_hphi_matrices(p);b=material_hphi_matrices(changed)
        for left,right in zip(a[1:3],b[1:3]):np.testing.assert_array_equal(left.toarray(),right.toarray())
        for order,quadrature in ((True,12),(3,12),(2,True),(2,3),(2,33)):
            with self.assertRaises(ValueError):material_hphi_matrices(p,order,quadrature_order=quadrature)
        with self.assertRaises(ValueError):material_hphi_matrices(p.to_dict())

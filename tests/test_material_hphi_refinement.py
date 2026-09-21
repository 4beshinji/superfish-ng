# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.material_hphi_refinement import refine_material_hphi_partition
from superfish_ng.material_hphi_fem import material_hphi_matrices
from test_material_hphi_comparison import partition


class MaterialHphiRefinementTests(unittest.TestCase):
    def test_region_volume_interface_and_galerkin_invariants(self):
        for axis in (False,True):
            for order in (1,2):
                p=partition(1,2,axis);before=p.to_dict()
                r=refine_material_hphi_partition(p,element_order=order)
                fine=r.partition;transfer=r.prolongation
                self.assertEqual(len(fine.mesh.triangles),4*len(p.mesh.triangles))
                np.testing.assert_array_equal(fine.cell_region_indices,p.cell_region_indices[r.parent_cells])
                self.assertEqual(len(fine.interface_edges),2*len(p.interface_edges))
                for cells_old,cells_new in zip((v.cell_indices for v in p.regions),(v.cell_indices for v in fine.regions)):
                    def volume(part,cells):
                        vertices=part.mesh.points_rz_m[part.mesh.triangles[list(cells)]]
                        det=np.linalg.det(np.transpose(vertices[:,1:]-vertices[:,:1],(0,2,1)))
                        return np.sum(np.pi*vertices[:,:,0].mean(axis=1)*det)
                    self.assertAlmostEqual(volume(fine,cells_new)/volume(p,cells_old),1.,delta=1e-12)
                a,k,m,_=material_hphi_matrices(p,order);b,kf,mf,_=material_hphi_matrices(fine,order)
                for old,new in ((k,kf),(m,mf)):
                    delta=(transfer.T@new@transfer-old).toarray();scale=np.sqrt(abs(old.diagonal()))
                    self.assertLess(np.max(abs(delta)/scale[:,None]/scale[None,:]),1e-9)
                def polynomial(points):
                    x,y=points.T
                    return 1+2*x-3*y+(x*x+x*y+2*y*y if order==2 else 0)
                np.testing.assert_allclose(transfer@polynomial(a.dof_points),polynomial(b.dof_points),rtol=1e-12,atol=1e-12)
                np.testing.assert_allclose(transfer@np.ones(len(a.dof_points)),1.,rtol=1e-12)
                self.assertEqual(p.to_dict(),before);self.assertFalse(r.parent_cells.flags.writeable)
                self.assertFalse(transfer.data.flags.writeable)

    def test_invalid_controls_and_budget_preflight(self):
        p=partition()
        import superfish_ng.material_hphi_refinement as module
        with patch.object(module,'material_hphi_matrices',side_effect=AssertionError('budget must be preflighted')):
            for options in ({'element_order':3},{'element_order':True},{'max_triangles':1},{'max_dofs':1},{'max_triangles':False}):
                with self.assertRaises(ValueError):refine_material_hphi_partition(p,**options)
        with self.assertRaises(ValueError):refine_material_hphi_partition(p.mesh)


if __name__=='__main__':unittest.main()

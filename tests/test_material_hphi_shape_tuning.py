# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng.material_hphi_shape_tuning import MaterialHphiShapeLaw
from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi
from superfish_ng.hphi_project import HphiProject
from superfish_ng.rf_materials import RFMaterialPartition,LinearRFMaterial
from superfish_ng.axis_hphi import AxisAccelerationPath
from test_material_hphi_comparison import partition


class MaterialHphiShapeTests(unittest.TestCase):
    def test_uniform_root_geometry_materials_and_actual_frequency(self):
        for axis in (False,True):
            root=HphiProject(MaterialHphiCase(partition(1,1,axis),modes=2));before=root.to_dict()
            law=MaterialHphiShapeLaw('uniform_scale')
            reference=solve_material_hphi(root.case)
            for value in (2.,1.5,1.):
                shaped=law.apply(root,value);p=shaped.project.case.partition
                np.testing.assert_allclose(p.mesh.points_rz_m,value*root.case.partition.mesh.points_rz_m,rtol=1e-14)
                np.testing.assert_allclose(p.region_volume_m3,value**3*root.case.partition.region_volume_m3,rtol=1e-12)
                np.testing.assert_array_equal(p.epsilon_r,root.case.partition.epsilon_r);np.testing.assert_array_equal(p.mu_r,root.case.partition.mu_r)
                s=solve_material_hphi(shaped.project.case)
                np.testing.assert_allclose(s.frequencies_hz*value,reference.frequencies_hz,rtol=1e-9)
            self.assertEqual(root.to_dict(),before)

    def test_nonuniform_domain_and_all_axis_coordinates(self):
        p=partition(1,1,True);p=RFMaterialPartition(p.mesh,[LinearRFMaterial('a',1.,1.),p.materials[1]],p.regions)
        path=AxisAccelerationPath(.005,.025,.7,.07)
        root=HphiProject(MaterialHphiCase(p,modes=2,acceleration=path))
        displacement=np.column_stack((np.zeros(len(p.mesh.points_rz_m)),p.mesh.points_rz_m[:,1]))
        law=MaterialHphiShapeLaw('general_piecewise_affine',1.,displacement,'transport_on_axis')
        result=law.apply(root,1.5);q=result.project.case.partition
        np.testing.assert_allclose(q.region_volume_m3,1.5*p.region_volume_m3,rtol=1e-12)
        actual=result.project.case.acceleration
        np.testing.assert_allclose([actual.z_start_m,actual.z_end_m,actual.phase_origin_m],1.5*np.array([path.z_start_m,path.z_end_m,path.phase_origin_m]),rtol=1e-14)
        self.assertEqual(actual.beta,path.beta);self.assertEqual(len(q.mesh.holes_rz_m),1)
        np.testing.assert_array_equal(q.interface_cells,p.interface_cells)
        with self.assertRaisesRegex(ValueError,'vacuum'):
            replace(result.project.case,acceleration=AxisAccelerationPath(.005,.07,.7,.01))
        bad=replace(root,case=replace(root.case,acceleration=replace(path,phase_origin_m=-1.)))
        with self.assertRaisesRegex(ValueError,'extrapolation'):law.apply(bad,1.5)

    def test_piecewise_interface_bend_and_declared_budget(self):
        for axis in (False,True):
            root=HphiProject(MaterialHphiCase(partition(1,0,axis),modes=2));p=root.case.partition
            points=p.mesh.points_rz_m;shift=np.zeros_like(points)
            selected=(points[:,1]==1/32)&(points[:,0]==(1/32 if axis else 2/32))
            self.assertEqual(selected.sum(),1);shift[selected,1]=1/512
            law=MaterialHphiShapeLaw('general_piecewise_affine',1.,shift)
            shaped=law.apply(root,1.5);q=shaped.project.case.partition
            np.testing.assert_array_equal(q.mesh.points_rz_m,points+.5*shift)
            np.testing.assert_array_equal(q.cell_region_indices,p.cell_region_indices)
            np.testing.assert_array_equal(q.interface_cells,p.interface_cells)
            self.assertGreater(q.region_volume_m3[0],p.region_volume_m3[0])
            self.assertAlmostEqual(q.mesh.volume_m3/p.mesh.volume_m3,1.,delta=1e-12)
            self.assertGreater(shaped.diagnostic['interface_pieces'],0)
            with self.assertRaises(ValueError):law.apply(root,1.5,max_candidate_tests=1)

    def test_strict_shape_and_fold_axis_rejection(self):
        p=HphiProject(MaterialHphiCase(partition(1,0,True),modes=2))
        law=MaterialHphiShapeLaw('uniform_scale');raw=law.to_dict()
        self.assertEqual(MaterialHphiShapeLaw.from_dict(raw).to_dict(),raw)
        for name,value in (('schema_version',True),('kind','change_material'),('reference_value',True),('displacements_rz_m',[[0,0]]),('acceleration_policy','fixed'),('extra',0)):
            bad=dict(raw);bad[name]=value
            with self.assertRaises(ValueError):MaterialHphiShapeLaw.from_dict(bad)
        for value in (True,0.,float('nan')):
            with self.assertRaises(ValueError):law.apply(p,value)
        coords=p.case.partition.mesh.points_rz_m
        for shifts in (coords[:-1],np.ones_like(coords),-2*coords):
            with self.assertRaises(ValueError):MaterialHphiShapeLaw('general_piecewise_affine',1.,shifts).apply(p,2.)
        mutable=coords.copy();owned=MaterialHphiShapeLaw('general_piecewise_affine',1.,mutable)
        mutable[:]=99;np.testing.assert_array_equal(owned.displacements_rz_m,coords)


if __name__=='__main__':unittest.main()

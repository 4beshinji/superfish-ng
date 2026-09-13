# SPDX-License-Identifier: Apache-2.0
import unittest
from dataclasses import replace
import numpy as np
from scripts.planar_magnetic_multipole_reference import quadrupole
from scripts.validate_planar_magnetic_multipoles import relative
from superfish_ng.planar_magnetostatic import solve_planar_magnetostatic
from superfish_ng.planar_magnetic_multipoles import PlanarMagneticMultipoleFrame as Frame,PlanarMagneticMultipoleSeries as Series
from superfish_ng.planar_magnetic_multipole_extraction import extract_planar_magnetic_multipoles as extract
from superfish_ng.magnetic_materials import PlanarMagneticPartition,LinearMagneticMaterial,MagneticRegion


class PlanarMagneticMultipoleExtractionTests(unittest.TestCase):
    def test_exact_P2_quadrupole_uses_real_FEM_with_original_fields_and_frame(self):
        for angle in (0.,.3):
            case,frame,ref=quadrupole(n=4,rotation_rad=angle);s=solve_planar_magnetostatic(case);report=extract(s,frame,4,64);series=Series.from_dict(report['series']);expected=np.r_[ref['coefficients_t'],[0j,0j]]
            self.assertLess(relative(np.asarray(series.normal_t)+1j*np.asarray(series.skew_t),expected),1e-10)
            for trace in report['traces']:self.assertLess(relative(trace['b_xy_t'],ref['fields'](trace['points_xy_m'])),1e-10)
            self.assertLess(report['angular_coefficient_relative_difference'],1e-10);self.assertLess(report['radial_coefficient_relative_difference'],1e-10);self.assertEqual(report['source_free_disk']['mu_r'],2.)
            self.assertEqual(report['angular_samples'],64);self.assertEqual([v['sample_count'] for v in report['traces']],[64,128,64,128])

    def test_P1_mesh_error_and_angular_diagnostics_are_separate(self):
        errors=[]
        for n in (8,16,32):
            case,frame,ref=quadrupole(n=n,order=1);report=extract(solve_planar_magnetostatic(case),frame,4,512);series=Series.from_dict(report['series']);expected=np.r_[ref['coefficients_t'],[0j,0j]]
            coefficient=relative(np.asarray(series.normal_t)+1j*np.asarray(series.skew_t),expected);field=relative(report['traces'][1]['b_xy_t'],ref['fields'](report['traces'][1]['points_xy_m']));errors.append((coefficient,field))
            self.assertGreater(report['traces'][1]['negative_harmonic_rms_t'],1e-8);self.assertGreater(report['traces'][1]['truncated_field_relative_error'],1e-5)
        for previous,current in zip(errors,errors[1:]):self.assertTrue(all(a<b for a,b in zip(current,previous)),errors)
        self.assertLess(max(errors[-1]),.02)

    def test_whole_disk_rejects_hidden_current_or_permeability_between_circle_samples(self):
        case,frame,ref=quadrupole(n=32);mesh=case.partition.mesh;vertices=mesh.points_xy_m[mesh.triangles];center=np.array(frame.center_xy_m);cell=int(np.argmin(np.linalg.norm(vertices.mean(axis=1)-center,axis=1)))
        self.assertLess(np.max(np.linalg.norm(vertices[cell]-center,axis=1)),frame.reference_radius_m)
        outside=[i for i in range(len(mesh.triangles)) if i!=cell]
        for inner_mu,current,error in [(2.,1.,'current cell'),(3.,0.,'permeability')]:
            p=PlanarMagneticPartition(mesh,[LinearMagneticMaterial('outside',2.),LinearMagneticMaterial('inner',inner_mu)],[MagneticRegion('outside','outside',outside),MagneticRegion('inner','inner',[cell])]);changed=replace(case,partition=p,current_density_z_a_per_m2=dict(outside=0.,inner=current));s=solve_planar_magnetostatic(changed)
            angle=2*np.pi*np.arange(128)/128;circle=center+frame.reference_radius_m*np.column_stack((np.cos(angle),np.sin(angle)));self.assertNotIn(cell,s.probe_at(circle)['cell_indices'])
            with self.assertRaisesRegex(ValueError,error):extract(s,frame,4,64)

    def test_coordinate_scale_permeability_and_Az_reference_changes_preserve_coefficients(self):
        first=None
        for scale,mu,offset in ((.5,1.,0.),(2.,7.,.125)):
            case,frame,ref=quadrupole(n=4,scale=scale,mu_r=mu,offset=offset);report=extract(solve_planar_magnetostatic(case),frame,4,64);series=Series.from_dict(report['series']);values=np.r_[series.normal_t,series.skew_t]
            if first is None:first=values
            self.assertLess(relative(values,first),1e-10)

    def test_strict_domain_order_source_type_and_modified_coefficients_are_rejected(self):
        case,frame,ref=quadrupole(n=4);s=solve_planar_magnetostatic(case)
        for order,count in ((True,64),(0,64),(33,256),(4,True),(4,15),(4,8193)):
            with self.assertRaises(ValueError):extract(s,frame,order,count)
        with self.assertRaises(ValueError):extract(object(),frame,4,64)
        for bad in (Frame((100.,100.),.1,0.),Frame(frame.center_xy_m,ref['length_m'],0.)):
            with self.assertRaises(ValueError):extract(s,bad,4,64)
        s.az_relative_to_reference_wb_per_m=s.az_relative_to_reference_wb_per_m.copy();s.az_relative_to_reference_wb_per_m[s.free_dofs[0]]+=.001
        with self.assertRaisesRegex(ValueError,'FEM replay'):extract(s,frame,4,64)

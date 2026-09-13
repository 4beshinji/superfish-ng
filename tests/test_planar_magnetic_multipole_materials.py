# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.planar_magnetic_multipole_material_reference import linear_limit,exterior_material
from scripts.validate_planar_magnetic_multipoles import relative
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh
from superfish_ng.planar_recoil import PlanarRecoilCase,solve_planar_recoil
from superfish_ng.planar_magnetic_multipoles import PlanarMagneticMultipoleFrame as Frame
from superfish_ng.planar_magnetic_multipole_extraction import extract_planar_magnetic_multipoles as extract


def solve(case):return solve_planar_bh(case) if type(case) is PlanarBHCase else solve_planar_recoil(case)


def errors(result,ref):
    series=result['series'];coefficients=np.asarray(series['normal_t'])+1j*np.asarray(series['skew_t']);expected=np.r_[ref['coefficients_t'],np.zeros(len(coefficients)-2,dtype=complex)];return relative(coefficients,expected),max(relative(t['b_xy_t'],ref['fields'](t['points_xy_m'])) for t in result['traces'])


class PlanarMagneticMultipoleMaterialTests(unittest.TestCase):
    def test_linear_limit_dipoles_and_exact_recoil_quadrupole(self):
        for kind,field,order in (('bh','dipole',1),('recoil','dipole',1),('recoil','dipole',2),('recoil','quadrupole',2)):
            case,frame,ref=linear_limit(kind,field,n=4,order=order,rotation_rad=.3,offset=.125);solution=solve(case);report=extract(solution,frame,8,128);self.assertEqual(report['schema_version'],2);self.assertEqual(report['source_physics'],case.to_dict()['physics']);self.assertEqual(report['source_free_disk']['linear_aperture_model']['kind'],'isotropic_linear_nonremanent');self.assertLess(max(errors(report,ref)),1e-9);self.assertEqual(len(report['traces']),4)

    def test_exterior_nonlinear_anisotropic_remanent_material_and_frame_covariance(self):
        for kind in ('bh','recoil'):
            normalized=None
            for angle,scale,amplitude in ((0.,1.,1.),(.3,.5,-1.),(-.7,2.,1.)):
                case,frame,ref=exterior_material(kind,angle=angle,scale=scale,amplitude=amplitude);solution=solve(case);report=extract(solution,frame,8,128);self.assertLess(max(errors(report,ref)),1e-9);self.assertEqual(len(report['source_free_disk']['linear_aperture_model']['checked_material_ids']),1)
                values=np.r_[report['series']['normal_t'],report['series']['skew_t']]/amplitude
                if normalized is None:normalized=values
                else:self.assertLess(relative(values,normalized),1e-9)
                self.assertGreater(len(case.partition.materials),1)

    def test_bh_p1_quadrupole_mesh_and_original_field_errors_improve_separately(self):
        previous=None
        for n in (8,16,32):
            case,frame,ref=linear_limit('bh','quadrupole',n=n,order=1,rotation_rad=.3,offset=.125);report=extract(solve(case),frame,8,512);values=errors(report,ref)
            if previous is not None:self.assertTrue(all(a<b for a,b in zip(values,previous)))
            previous=values
        self.assertLess(max(values),.02)

    def test_nonlinear_almost_linear_anisotropic_remanent_and_current_apertures_reject(self):
        for kind,field,value in (('bh','nonlinear',None),('bh','almost_linear',None),('recoil','anisotropic',None),('recoil','remanent',None),('recoil','current',1.)):
            case,frame,_=linear_limit(kind,'dipole',n=4,order=1);data=case.to_dict();material=data['partition']['materials'][0]
            if field in ('nonlinear','almost_linear'):
                h=material['h_a_per_m'];h[-1]=h[-1]*1.1 if field=='nonlinear' else float(np.nextafter(h[-1],np.inf))
            elif field=='anisotropic':material['mu_r_principal'][1]*=2
            elif field=='remanent':material['remanent_b_local_t'][0]=.1
            else:data['current_density_z_a_per_m2'][next(iter(data['current_density_z_a_per_m2']))]=value
            changed=type(case).from_dict(data);solution=solve(changed)
            with self.assertRaises(ValueError):extract(solution,frame,8,128)

    def test_exterior_material_intersection_and_modified_source_coefficients_reject(self):
        for kind in ('bh','recoil'):
            case,frame,_=exterior_material(kind);solution=solve(case);center=frame.center_xy_m;crossing=Frame((center[0],center[1]+2*frame.reference_radius_m),frame.reference_radius_m,frame.rotation_rad)
            with self.assertRaises(ValueError):extract(solution,crossing,8,128)
            solution.az_relative_to_reference_wb_per_m=solution.az_relative_to_reference_wb_per_m*1.01
            with self.assertRaisesRegex(ValueError,'FEM replay'):extract(solution,frame,8,128)


if __name__=='__main__':unittest.main()

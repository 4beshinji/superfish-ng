# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi
from superfish_ng.material_hphi_tracking import MaterialHphiTrackingRequest,track_material_hphi_modes
from superfish_ng.rf_materials import RFMaterialPartition,LinearRFMaterial,RFMaterialRegion
from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping
from test_material_hphi_comparison import partition,request
from test_hphi_geometry_mapping import transformed


class MaterialHphiTrackingIntegrationTests(unittest.TestCase):
    def test_p1_p2_vacuum_limit_ids_and_spectral_intervals(self):
        from superfish_ng.axis_hphi import AxisHphiCase,solve_axis_hphi
        from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh
        from superfish_ng.hphi_tracking import HphiTrackingRequest,track_hphi_modes
        for axis in (False,True):
            for order in (1,2):
                meshes=[partition(n,0,axis).mesh for n in (2,4)]
                parts=[RFMaterialPartition(m,[LinearRFMaterial('vacuum',1.,1.)],
                    [RFMaterialRegion('all','vacuum',list(range(len(m.triangles))))]) for m in meshes]
                a=solve_material_hphi(MaterialHphiCase(parts[0],element_order=order,modes=3))
                old=(solve_axis_hphi(AxisHphiCase(meshes[0],element_order=order,modes=3)) if axis else
                     solve_hphi_mesh(HphiMeshCase(meshes[0],element_order=order,modes=3,quadrature_order=12)))
                q=MaterialHphiTrackingRequest(request(parts[0],parts[0]),request(*parts),request(*parts),
                    previous_comparison_order=order,current_comparison_order=order)
                result=track_material_hphi_modes(a,a,q)
                reference=track_hphi_modes(old,old,HphiTrackingRequest(meshes[1],meshes[1],previous_comparison_order=order,current_comparison_order=order))
                self.assertEqual(result['status'],'PASS',result['verification_reasons'])
                self.assertEqual(result['current_mode_ids'],reference['current_mode_ids'])
                self.assertEqual(result['guard_overlap'],reference['guard_overlap'])
                for x,y in zip(result['spectral_resolution'],reference['spectral_resolution']):
                    np.testing.assert_allclose(x['nearby_comparison_frequency_intervals_hz'],y['nearby_comparison_frequency_intervals_hz'],rtol=1e-8)

    def test_original_material_scale_amplitude_and_one_sided_interfaces(self):
        from scripts.material_hphi_reference import layered_partition
        from superfish_ng.constants import EPS0
        for order in (1,2):
            parts=[layered_partition(2,24,scale) for scale in (1.,2.)]
            left,right=[solve_material_hphi(MaterialHphiCase(p,modes=3,element_order=order)) for p in parts]
            p=parts[0]
            for mode in range(3):
                cells=np.arange(len(p.mesh.triangles));bary=np.tile([.2,.3,.5],(len(cells),1))
                a=left.fields_in_cells(cells,bary,mode);b=right.fields_in_cells(cells,bary,mode)
                sign=np.sign(a['Hphi_real_A_per_m']@b['Hphi_real_A_per_m'])
                for key in ('Hphi_real_A_per_m','Bphi_real_T','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'):
                    error=np.linalg.norm(sign*2**1.5*b[key]-a[key])
                    # Ez is analytically zero for the separated TEM mode.
                    norm=np.linalg.norm(a['Er_quadrature_V_per_m']) if key=='Ez_quadrature_V_per_m' else np.linalg.norm(a[key])
                    self.assertLess(error/norm,1e-8)
                for edge,owners in zip(p.interface_edges,p.interface_cells):
                    values=[]
                    for cell in owners:
                        tri=p.mesh.triangles[cell];local=np.zeros(3)
                        for node in edge:local[np.flatnonzero(tri==node)[0]]=.5
                        values.append(left.fields_in_cells([int(cell)],[local],mode))
                    self.assertAlmostEqual(values[0]['Hphi_real_A_per_m'][0],values[1]['Hphi_real_A_per_m'][0],delta=1e-8)
                    d=[EPS0*p.epsilon_r[cell]*v['Ez_quadrature_V_per_m'][0] for cell,v in zip(owners,values)]
                    self.assertLess(abs(d[0]-d[1]),1e-12)

    def test_independent_material_remesh_and_nonuniform_map_both_directions(self):
        for axis in (False,True):
            a=partition(2,1,axis);af=partition(4,1,axis)
            base=partition(2,1,axis,True);fine=partition(4,1,axis,True);control=partition(1,1,axis)
            def move(points):
                result=points.copy();knots=np.arange(4)/32 if axis else np.arange(1,5)/32
                result[:,0]+=np.interp(points[:,0],knots,[0,1/2048,1/2048,0]);return result
            left=solve_material_hphi(MaterialHphiCase(a,modes=3))
            for mapped in (False,True):
                b=RFMaterialPartition(transformed(base.mesh,move),base.materials,base.regions) if mapped else base
                bf=RFMaterialPartition(transformed(fine.mesh,move),fine.materials,fine.regions) if mapped else fine
                mapping=HphiGeometryMapping(control.mesh,transformed(control.mesh,move)) if mapped else 'same_domain'
                right=solve_material_hphi(MaterialHphiCase(b,modes=3))
                q=MaterialHphiTrackingRequest(request(a,b,mapping),request(a,af),request(b,bf))
                result=track_material_hphi_modes(left,right,q)
                reverse=MaterialHphiTrackingRequest(request(b,a,mapping.inverse() if mapped else mapping),request(b,bf),request(a,af))
                back=track_material_hphi_modes(right,left,reverse)
                for report in (result,back):
                    self.assertEqual(report['status'],'PASS',report['verification_reasons'])
                    self.assertEqual(report['current_mode_ids'],['mode-1','mode-2'])
                for name in ('electric_grams','magnetic_grams'):
                    np.testing.assert_allclose(result['physical_mapping'][name][1],np.asarray(back['physical_mapping'][name][1]).T,rtol=1e-8,atol=1e-8)


if __name__=='__main__':unittest.main()

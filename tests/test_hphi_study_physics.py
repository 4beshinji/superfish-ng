# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scripts.hphi_mesh_reference import rectangular_holes
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.hphi_native import solve_hphi,hphi_result
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_study import HphiStudy


class HphiStudyPhysicsTests(unittest.TestCase):
    def check_law(self,parameter,values,coordinate_factor,field_factor,factors):
        for order in (1,2):
            for holes in (0,2):
                case=(HphiMeshCase(MeridionalMesh(**rectangular_holes(2,holes)),element_order=order,modes=2) if holes else CoaxialCase(.025,.05,.18,nr=3,nz=8,element_order=order,modes=2))
                study=HphiStudy(HphiProject(case),parameter,values);first,second=[solve_hphi(p.case) for p in study.projects()]
                for a,b in zip(hphi_result(first)['modes'],hphi_result(second)['modes']):
                    for key,factor in factors.items():self.assertLess(abs(b[key]/(factor*a[key])-1),1e-9,(holes,order,key))
                    self.assertIsNone(a['r_over_q_accelerator_ohm']);self.assertIsNone(b['r_over_q_circuit_ohm'])
                points=first.space.mesh.points[first.space.mesh.triangles].mean(axis=1)
                a=first.fields_at(points,0);b=second.fields_at(points*coordinate_factor,0)
                sign=1 if a['Hphi_real_A_per_m']@b['Hphi_real_A_per_m']>=0 else -1
                for family in ('E','H'):
                    x=np.column_stack([v for k,v in a.items() if k.startswith(family)]);y=np.column_stack([v for k,v in b.items() if k.startswith(family)])
                    self.assertLess(np.linalg.norm(sign*y-field_factor*x)/np.linalg.norm(field_factor*x),1e-9)
    def test_uniform_scale_at_fixed_total_energy(self):
        self.check_law('uniform_scale',[1.,2.],2.,2**-1.5,dict(frequency_hz=.5,stored_energy_j=1.,geometry_factor_ohm=1.,q0=np.sqrt(2),wall_loss_w=2**-1.5,volume_m3=8.))
    def test_total_energy_scaling(self):
        self.check_law('/case/rf/stored_energy_j',[1.,4.],1.,2.,dict(frequency_hz=1.,stored_energy_j=4.,geometry_factor_ohm=1.,q0=1.,wall_loss_w=4.,volume_m3=1.))
    def test_wall_conductivity_scaling(self):
        self.check_law('/case/rf/conductivity_s_per_m',[5.8e7,4*5.8e7],1.,1.,dict(frequency_hz=1.,stored_energy_j=1.,geometry_factor_ohm=1.,q0=2.,wall_loss_w=.5,volume_m3=1.))

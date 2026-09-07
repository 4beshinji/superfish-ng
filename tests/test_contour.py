# SPDX-License-Identifier: Apache-2.0
import math
import unittest
from superfish_ng.contour import Contour


class ContourTests(unittest.TestCase):
    def test_reentrant_area_volume_orientation_and_scaling(self):
        points=((0.,0.),(3.,0.),(3.,2.),(1.,2.),(1.,1.),(2.,1.),(2.,.5),(0.,.5))
        tags=('axis',)+('pec',)*7
        original=Contour(points,tags)
        self.assertEqual(original.area_m2,4.)
        self.assertAlmostEqual(original.volume_m3,7.5*math.pi)
        for offset in range(len(points)):
            rotated=points[offset:]+points[:offset]
            rotated_tags=tags[offset:]+tags[:offset]
            self.assertEqual(Contour(rotated,rotated_tags),original)
            reversed_tags=tuple(rotated_tags[(i-1)%len(tags)] for i in range(len(tags)-1,-1,-1))
            self.assertEqual(Contour(rotated[::-1],reversed_tags),original)
        scaled=Contour(tuple((z*3,r*3) for z,r in points),tags)
        self.assertAlmostEqual(scaled.area_m2/original.area_m2,9)
        self.assertAlmostEqual(scaled.volume_m3/original.volume_m3,27)

    def test_triangle_cone_is_a_valid_single_boundary(self):
        cone=Contour(((0,0),(3,0),(0,2)),('axis','pec','pec'))
        self.assertAlmostEqual(cone.area_m2,3)
        self.assertAlmostEqual(cone.volume_m3,4*math.pi)

    def test_invalid_crossings_contacts_axis_and_tags(self):
        bad=[((0,0),(3,0),(1,2),(3,2),(0,1)),
             ((0,0),(3,0),(3,2),(1,0),(0,2)),
             ((0,0),(3,0),(3,2),(3,1),(0,1)),
             ((0,0),(3,0),(3,2),(0,2),(0,0)),
             ((0,0),(3,0),(3,-1),(0,1))]
        for points in bad:
            with self.subTest(points=points),self.assertRaises(ValueError):
                Contour(points,('axis',)+('pec',)*(len(points)-1))
        rectangle=((0,0),(3,0),(3,2),(0,2))
        for tags in [('pec',)*4,('axis','pec','magnetic_symmetry','pec')]:
            with self.assertRaises(ValueError):Contour(rectangle,tags)
        self.assertEqual(Contour(rectangle,('axis','electric_symmetry','pec','pec')).area_m2,6)

    def test_profile_conversion_preserves_independent_frustum_volume(self):
        from superfish_ng import Case
        from superfish_ng.geometry import profile_area
        cases=[Case(((0.,.1),(.2,.1))),Case(((0.,.1),(.2,.2))),
               Case(((0.,.1),(.1,.1),(.1,.2),(.2,.2)),geometry_type='stepped_profile')]
        for case in cases:
            contour=Contour.from_profile(case)
            volume=sum(math.pi*(zb-za)*(ra*ra+ra*rb+rb*rb)/3 for (za,ra),(zb,rb) in zip(case.profile,case.profile[1:]))
            self.assertAlmostEqual(contour.area_m2,profile_area(case),places=14)
            self.assertAlmostEqual(contour.volume_m3,volume,places=14)
            self.assertEqual(contour.edge_tags.count('axis'),1)

    def test_reentrant_reflection_both_ends_and_parities(self):
        points=((0.,0.),(3.,0.),(3.,2.),(1.,2.),(1.,1.),(2.,1.),(2.,.5),(0.,.5))
        for edge in [1,7]:
            for tag in ['electric_symmetry','magnetic_symmetry']:
                tags=['axis']+['pec']*7;tags[edge]=tag
                half=Contour(points,tuple(tags));full=half.reflected()
                self.assertAlmostEqual(full.area_m2,2*half.area_m2)
                self.assertAlmostEqual(full.volume_m3,2*half.volume_m3)
                self.assertEqual(set(full.edge_tags),{'axis','pec'})
                self.assertEqual(max(z for z,r in full.vertices_zr_m),6)
        with self.assertRaises(ValueError):Contour(points,('axis',)+('pec',)*7).reflected()
        tags=['axis']+['pec']*7;tags[1]=tags[7]='electric_symmetry'
        with self.assertRaises(ValueError):Contour(points,tuple(tags)).reflected()

    def test_case_v3_roundtrip_and_explicit_mesher_refusal(self):
        from superfish_ng import Case,solve
        from superfish_ng.geometry import profile_area
        contour=Contour(((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),(2,.5),(0,.5)),
                        ('axis',)+('pec',)*7)
        case=Case((),contour=contour,element_order=2)
        self.assertEqual(case.length,3)
        self.assertEqual(profile_area(case),4)
        data=case.to_dict()
        self.assertEqual(data['schema_version'],3)
        self.assertNotIn('points_zr_m',data['geometry'])
        self.assertEqual(Case.from_dict(data),case)
        with self.assertRaisesRegex(ValueError,'G02'):solve(case)
        data['geometry']['points_zr_m']=[]
        with self.assertRaisesRegex(ValueError,'unknown'):Case.from_dict(data)

    def test_external_reentrant_mesh_fem_save_and_invalid_boundary(self):
        import tempfile
        from pathlib import Path
        import numpy as np
        from superfish_ng import Case,solve
        from superfish_ng.io import save_run
        from superfish_ng.saved import read_solution
        # Three rectangular pieces on a half-unit lattice; cells selected by
        # the explicit rectangular decomposition, not a polygon mesher.
        cells=[]
        for iz in range(6):
            for ir in range(4):
                if ir==0 or iz>=4 or (iz>=2 and ir>=2):cells.append((iz,ir))
        points=[];lookup={};triangles=[]
        def node(z,r):
            key=(r/2,z/2)
            if key not in lookup:lookup[key]=len(points);points.append(list(key))
            return lookup[key]
        for z,r in cells:
            a,b,c,d=node(z,r),node(z,r+1),node(z+1,r+1),node(z+1,r)
            triangles.extend([[a,b,c],[a,c,d]])
        incidence={}
        for tri in triangles:
            for a,b in zip(tri,tri[1:]+tri[:1]):
                key=tuple(sorted((a,b)));incidence[key]=incidence.get(key,0)+1
        edges=[list(edge) for edge,count in incidence.items() if count==1]
        tags=['axis' if points[a][0]==points[b][0]==0 else 'pec' for a,b in edges]
        data=dict(schema_version=1,length_unit='m',coordinate_order='rz',index_base=0,
                  points=points,triangles=triangles,boundary_edges=edges,boundary_tags=tags)
        contour=Contour(((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),(2,.5),(0,.5)),('axis',)+('pec',)*7)
        case=Case((),contour=contour,element_order=2,modes=2)
        sol=solve(case,mesh_data=data)
        self.assertLess(max(sol.residuals),1e-7)
        with tempfile.TemporaryDirectory() as tmp:
            save_run(case,sol,Path(tmp)/'run')
            saved=read_solution(Path(tmp)/'run')
            self.assertEqual(saved.case,case)
            np.testing.assert_array_equal(saved.u,sol.u)
        import copy
        wrong=copy.deepcopy(data)
        for point in wrong['points']:
            if point==[2.,2.]:point[0]=2.1
        with self.assertRaisesRegex(ValueError,'boundary|segment|area'):
            solve(case,mesh_data=wrong)

# SPDX-License-Identifier: Apache-2.0
"""Whole-domain P2 correspondence, distinct native partitions and hole moments."""
from copy import deepcopy
from fractions import Fraction as F
import unittest
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.fem import triangle_quadrature


def geometry(axis=False,holes=1,n=1,scale=1.,shear=1.):
    data,exact=fixture(axis,holes,n=n,scale=scale,shear=shear)
    return CurvedMeridionalGeometry(**data),exact


def charts(reference,native,*,alpha=1.):
    # Independent inverse of the analytic test shear, not product point location.
    def unshear(points):
        p=points.copy();p[:,1]-=alpha*p[:,0]**2;return p
    parent=unshear(reference.base_mesh.points_rz_m)[reference.base_mesh.triangles]
    points=unshear(native.base_mesh.points_rz_m)
    result=[]
    for cell in native.base_mesh.triangles:
        p=points[cell]
        for owner,t in enumerate(parent):
            q=np.linalg.solve(np.column_stack((t[1]-t[0],t[2]-t[0])),(p-t[0]).T).T
            if np.all(q>=0) and np.all(q.sum(axis=1)<=1):break
        else:raise AssertionError('test native cell has no reference parent')
        result.append(dict(base_cell=owner,reference_vertices=[[[F(float(v)).numerator,F(float(v)).denominator] for v in row] for row in q]))
    return result


class CurvedHphiComparisonTests(unittest.TestCase):
    def test_independent_holes_area_volume_and_positive_map(self):
        a,ea=geometry(holes=2);b,eb=geometry(holes=2,scale=2.,shear=.5)
        self.assertAlmostEqual(a.volume_m3/ea['volume_m3'],1.,places=13)
        self.assertAlmostEqual(b.area_m2/eb['area_m2'],1.,places=13)
        from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain,build_curved_hphi_comparison
        domain=CurvedHphiComparisonDomain(a,b,'declared_quadratic')
        overlay=build_curved_hphi_comparison(a,b,domain)
        rule=list(triangle_quadrature(8));q=np.array([v for v,w in rule]);w=np.array([w for v,w in rule])
        for side,expected in enumerate((ea,eb)):
            data=overlay.evaluate(side,q)
            area=sum(w@row['determinant_m2'] for row in data)
            volume=sum(w@(2*np.pi*row['points_rz_m'][:,0]*row['determinant_m2']) for row in data)
            self.assertAlmostEqual(area/expected['area_m2'],1.,places=12)
            self.assertAlmostEqual(volume/expected['volume_m3'],1.,places=12)
            self.assertTrue(all(np.all(row['determinant_m2']>0) for row in data))
        self.assertEqual(overlay.report['boundary_components'],3)
        self.assertEqual(overlay.report['status'],'GEOMETRY_VERIFIED')
        self.assertEqual(domain.to_dict(),CurvedHphiComparisonDomain.from_dict(domain.to_dict()).to_dict())

    def test_axis_and_positive_radius_distinct_native_partitions(self):
        from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain,build_curved_hphi_comparison
        for axis in (False,True):
            a,exact=geometry(axis,holes=1);fine,_=geometry(axis,holes=1,n=2)
            c=charts(a,fine);domain=CurvedHphiComparisonDomain(a,a,'same_vacuum')
            forward=build_curved_hphi_comparison(a,fine,domain,current_cells=c)
            backward=build_curved_hphi_comparison(fine,a,domain,previous_cells=c)
            self.assertEqual(forward.report['base_reference_areas'],[[1,2]]*len(a.cell_nodes))
            self.assertEqual(forward.report['triangle_count'],len(fine.cell_nodes))
            q=np.array([[.2,.3,.5]])
            for overlay in (forward,backward):
                left,right=overlay.evaluate(0,q),overlay.evaluate(1,q)
                for old,new in zip(left,right):
                    np.testing.assert_allclose(old['points_rz_m'],new['points_rz_m'],rtol=0,atol=1e-15)
                    np.testing.assert_allclose(old['determinant_m2'],new['determinant_m2'],rtol=1e-13,atol=0)
                    self.assertAlmostEqual(new['native_barycentric'][0].sum(),1.,places=14)
            self.assertEqual(forward.report['axis_connected'],axis)

    def test_equal_vertices_do_not_establish_equal_quadratic_domain(self):
        from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain,build_curved_hphi_comparison
        a,_=geometry(holes=0);raw=a.to_dict()
        # A boundary midpoint moves, with identical vertices and connectivity.
        node=int(a.boundary_nodes[0,2])-len(a.base_mesh.points_rz_m)
        raw['edge_midpoints_rz_m'][node][1]+=1/8192
        b=CurvedMeridionalGeometry.from_dict(raw)
        np.testing.assert_array_equal(a.base_mesh.points_rz_m,b.base_mesh.points_rz_m)
        with self.assertRaisesRegex(ValueError,'same_vacuum'):
            CurvedHphiComparisonDomain(a,b,'same_vacuum')
        domain=CurvedHphiComparisonDomain(a,a,'same_vacuum')
        with self.assertRaisesRegex(ValueError,'quadratic restriction'):
            build_curved_hphi_comparison(a,b,domain)

    def test_invalid_partitions_and_budget_never_verify(self):
        from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain,build_curved_hphi_comparison,CurvedHphiComparisonBudgetExceeded
        a,_=geometry();fine,_=geometry(n=2);c=charts(a,fine)
        domain=CurvedHphiComparisonDomain(a,a,'same_vacuum')
        for control in ('max_pair_tests','max_triangles'):
            with self.assertRaises(CurvedHphiComparisonBudgetExceeded) as caught:
                build_curved_hphi_comparison(a,fine,domain,current_cells=c,**{control:1})
            self.assertEqual(caught.exception.status,'UNVERIFIED')
        for key,value in (('base_cell',True),('base_cell',999),('extra',0),('reference_vertices',[[[0,0],[0,1]]]*3)):
            bad=deepcopy(c);bad[0][key]=value
            with self.assertRaises(ValueError):build_curved_hphi_comparison(a,fine,domain,current_cells=bad)
        bad=deepcopy(c);bad[0]['reference_vertices'][0]=[[2,1],[0,1]]
        with self.assertRaises(ValueError):build_curved_hphi_comparison(a,fine,domain,current_cells=bad)
        for key,value in (('schema_version',True),('mapping','guess'),('extra',0)):
            bad=domain.to_dict();bad[key]=value
            with self.assertRaises(ValueError):CurvedHphiComparisonDomain.from_dict(bad)

    def test_non_nested_partitions_and_native_numbering(self):
        from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain,build_curved_hphi_comparison
        from superfish_ng.meridional_mesh import MeridionalMesh
        def triangle(inner=None):
            p=np.array([[1/16,0.],[3/16,0.],[1/16,1/8]]+([] if inner is None else [[1/16+inner[0]/8,inner[1]/8]]))
            cells=np.array([[0,1,2]] if inner is None else [[0,1,3],[1,2,3],[2,0,3]])
            edges=np.unique(np.sort(cells[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
            mids=p[edges].mean(axis=1);mids[:,1]+=mids[:,0]**2
            mapped=p.copy();mapped[:,1]+=mapped[:,0]**2
            return CurvedMeridionalGeometry(MeridionalMesh(mapped[:3],[],mapped,cells),edges,mids)
        base=triangle();a=triangle((.25,.25));b=triangle((.5,.25))
        domain=CurvedHphiComparisonDomain(base,base,'same_vacuum')
        ca,cb=charts(base,a),charts(base,b)
        direct=build_curved_hphi_comparison(a,b,domain,previous_cells=ca,current_cells=cb)
        reverse=build_curved_hphi_comparison(b,a,domain,previous_cells=cb,current_cells=ca)
        self.assertGreater(direct.report['triangle_count'],3)
        self.assertEqual(direct.report['base_reference_areas'],[[1,2]])
        rule=list(triangle_quadrature(8));q=np.array([v for v,w in rule]);w=np.array([w for v,w in rule])
        expected_area=(1/8)**2/2;expected_volume=2*np.pi*expected_area*(1/16+1/24)
        for overlay in (direct,reverse):
            for side in (0,1):
                values=overlay.evaluate(side,q)
                self.assertAlmostEqual(sum(w@v['determinant_m2'] for v in values)/expected_area,1.,places=13)
                self.assertAlmostEqual(sum(w@(2*np.pi*v['points_rz_m'][:,0]*v['determinant_m2']) for v in values)/expected_volume,1.,places=13)
        # Reverse cell order and rotate local corners without altering geometry.
        raw=b.to_dict();raw['base_mesh']['triangles']=[row[1:]+row[:1] for row in raw['base_mesh']['triangles'][::-1]]
        changed=CurvedMeridionalGeometry.from_dict(raw)
        cc=[dict(base_cell=row['base_cell'],reference_vertices=row['reference_vertices'][1:]+row['reference_vertices'][:1]) for row in cb[::-1]]
        renumbered=build_curved_hphi_comparison(a,changed,domain,previous_cells=ca,current_cells=cc)
        for side in (0,1):
            for old,new in zip(direct.evaluate(side,q),renumbered.evaluate(side,q)):
                np.testing.assert_array_equal(old['points_rz_m'],new['points_rz_m'])
                np.testing.assert_array_equal(old['determinant_m2'],new['determinant_m2'])

    def test_hole_component_integrals_and_explicit_map_reverse(self):
        from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain,build_curved_hphi_comparison
        for axis in (False,True):
            a,ea=geometry(axis,2);b,eb=geometry(axis,2,scale=2.,shear=.5)
            fine,_=geometry(axis,2,n=2,scale=2.,shear=.5)
            domain=CurvedHphiComparisonDomain(a,b,'declared_quadratic')
            overlay=build_curved_hphi_comparison(a,fine,domain,current_cells=charts(b,fine,alpha=.25))
            reverse=build_curved_hphi_comparison(fine,a,domain.inverse(),previous_cells=charts(b,fine,alpha=.25))
            rule=list(triangle_quadrature(8));q=np.array([v for v,w in rule]);w=np.array([w for v,w in rule])
            for side,expected in enumerate((ea,eb)):
                values=overlay.evaluate(side,q)
                self.assertAlmostEqual(sum(w@v['determinant_m2'] for v in values)/expected['area_m2'],1.,places=12)
                self.assertAlmostEqual(sum(w@(2*np.pi*v['points_rz_m'][:,0]*v['determinant_m2']) for v in values)/expected['volume_m3'],1.,places=12)
                for old,new in zip(values,reverse.evaluate(1-side,q)):
                    np.testing.assert_array_equal(old['points_rz_m'],new['points_rz_m'])
            # Independent boundary Gauss integral of each known sheared rectangle.
            x,w1=np.polynomial.legendre.leggauss(4);t=(x+1)/2;w1=w1/2
            for g in (a,b):
                areas=np.zeros(3);volumes=np.zeros(3)
                for nodes,component in zip(g.boundary_nodes,g.base_mesh.boundary_components):
                    p0,p1,pm=g.points_rz_m[nodes]
                    p=p0[None,:]*(1-3*t+2*t*t)[:,None]+p1[None,:]*(2*t*t-t)[:,None]+pm[None,:]*(4*t-4*t*t)[:,None]
                    dz=p0[1]*(-3+4*t)+p1[1]*(4*t-1)+pm[1]*(4-8*t)
                    areas[component]+=w1@(p[:,0]*dz);volumes[component]+=np.pi*(w1@(p[:,0]**2*dz))
                original,_=fixture(axis,2,scale=1. if g is a else 2.,shear=0.)
                for component,loop in enumerate([original['base_mesh'].outer_rz_m,*original['base_mesh'].holes_rz_m]):
                    r0,z0=loop.min(axis=0);r1,z1=loop.max(axis=0);sign=1 if component==0 else -1
                    self.assertAlmostEqual(areas[component]/(sign*(r1-r0)*(z1-z0)),1.,places=13)
                    self.assertAlmostEqual(volumes[component]/(sign*np.pi*(r1*r1-r0*r0)*(z1-z0)),1.,places=13)

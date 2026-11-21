# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import unittest
import numpy as np
from test_meridional_overlap import fixture
from test_hphi_geometry_mapping import transformed
from superfish_ng.rf_materials import RFMaterialPartition,RFMaterialRegion,LinearRFMaterial
from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping
from superfish_ng.material_hphi_comparison import MaterialHphiComparison,material_hphi_overlay


def partition(n=1,holes=0,axis=False,opposite=False):
    mesh=fixture(n,holes,axis,opposite);lower=mesh.points_rz_m[mesh.triangles][:,:,1].mean(axis=1)<1/32
    return RFMaterialPartition(mesh,[LinearRFMaterial('a',2.,3.),LinearRFMaterial('b',5.,7.)],
        [RFMaterialRegion('lower','a',np.flatnonzero(lower).tolist()),RFMaterialRegion('upper','b',np.flatnonzero(~lower).tolist())])


def request(a,b,mapping='same_domain'):
    return MaterialHphiComparison(a,b,mapping,[{'previous_id':m.id,'current_id':m.id} for m in a.materials],
        [{'previous_id':r.id,'current_id':r.id} for r in a.regions])


class MaterialHphiComparisonTests(unittest.TestCase):
    def test_exact_regions_interfaces_and_independent_measures(self):
        for axis in (False,True):
            for holes in (0,1,2):
                a,b=partition(1,holes,axis),partition(2,holes,axis,True);q=request(a,b)
                self.assertEqual(MaterialHphiComparison.from_dict(q.to_dict()).to_dict(),q.to_dict())
                result=material_hphi_overlay(q);o=result.overlay
                for region in range(2):
                    area=volume=0.
                    for sign,contour in [(1,a.mesh.outer_rz_m),*[(-1,h) for h in a.mesh.holes_rz_m]]:
                        r0,z0=contour.min(axis=0);r1,z1=contour.max(axis=0)
                        low,high=(z0,min(z1,1/32)) if region==0 else (max(z0,1/32),z1)
                        height=max(0.,high-low);area+=sign*(r1-r0)*height;volume+=sign*np.pi*(r1*r1-r0*r0)*height
                    mask=result.previous_region_indices==region
                    self.assertAlmostEqual(o.determinants[mask].sum()/2,area,delta=1e-15)
                    self.assertAlmostEqual(np.sum(o.determinants[mask]*np.pi*o.vertices_rz_m[mask,:,0].mean(axis=1)),volume,delta=1e-15)
                expected=np.ptp(a.mesh.outer_rz_m[:,0])-sum(np.ptp(h[:,0]) for h in a.mesh.holes_rz_m if h[:,1].min()<=1/32<=h[:,1].max())
                self.assertAlmostEqual(np.linalg.norm(np.diff(result.interfaces.current_vertices_rz_m,axis=1)[:,0],axis=1).sum(),expected,delta=1e-15)
                np.testing.assert_array_equal(a.cell_region_indices[result.interfaces.previous_cells],b.cell_region_indices[result.interfaces.current_cells])
                self.assertFalse(result.interfaces.previous_cells.flags.writeable)

    def test_nonuniform_map_and_inverse_keep_both_interface_sides(self):
        for axis,holes in ((False,0),(True,1)):
            a,base=partition(1,holes,axis),partition(2,holes,axis,opposite=True)
            def change(p):return np.column_stack((2*p[:,0],np.where(p[:,1]<=1/32,2*p[:,1],p[:,1]+1/32)))
            b=RFMaterialPartition(transformed(base.mesh,change),base.materials,base.regions)
            mapping=HphiGeometryMapping(a.mesh,transformed(a.mesh,change));q=request(a,b,mapping)
            forward=material_hphi_overlay(q);reverse=material_hphi_overlay(request(b,a,mapping.inverse()))
            self.assertAlmostEqual(forward.overlay.previous_determinants.sum(),reverse.overlay.determinants.sum(),delta=1e-15)
            v=forward.interfaces
            np.testing.assert_allclose(v.current_vertices_rz_m[:,:,0],2*v.previous_vertices_rz_m[:,:,0],rtol=0,atol=0)
            np.testing.assert_allclose(v.current_vertices_rz_m[:,:,1],1/16,rtol=0,atol=0)
            self.assertEqual(q.to_dict()['mapping'],mapping.to_dict())

            for region,factor in ((0,4.),(1,2.)):
                mask=forward.previous_region_indices==region;o=forward.overlay
                self.assertAlmostEqual(o.determinants[mask].sum()/2,factor*a.region_area_m2[region],delta=1e-15)
                volume=np.sum(np.pi*o.determinants[mask]*o.vertices_rz_m[mask,:,0].mean(axis=1))
                self.assertAlmostEqual(volume,2*factor*a.region_volume_m3[region],delta=1e-15)

    def test_renumbered_cells_nodes_and_renamed_material_regions(self):
        a=partition(1,1);base=partition(2,1,opposite=True);raw=base.mesh.to_dict()
        points=np.asarray(raw['points_rz_m']);triangles=np.asarray(raw['triangles'])
        raw['points_rz_m']=points[::-1].tolist();raw['triangles']=(len(points)-1-triangles[::-1]).tolist()
        mesh=type(base.mesh).from_dict(raw);count=len(triangles)
        b=RFMaterialPartition(mesh,[LinearRFMaterial('new-b',5.,7.),LinearRFMaterial('new-a',2.,3.)],
            [RFMaterialRegion('new-upper','new-b',sorted(count-1-i for i in base.regions[1].cell_indices)),
             RFMaterialRegion('new-lower','new-a',sorted(count-1-i for i in base.regions[0].cell_indices))])
        q=MaterialHphiComparison(a,b,'same_domain',
            [dict(previous_id=x,current_id='new-'+x) for x in ('b','a')],
            [dict(previous_id=x,current_id='new-'+x) for x in ('upper','lower')])
        result=material_hphi_overlay(q)
        np.testing.assert_array_equal(result.current_region_indices,1-result.previous_region_indices)
        pairs=result.interfaces
        np.testing.assert_array_equal(b.cell_region_indices[pairs.current_cells],1-a.cell_region_indices[pairs.previous_cells])
        self.assertEqual(q.to_dict()['current_partition'],b.to_dict())

    def test_bent_interface_split_by_independent_control_cells(self):
        from superfish_ng.hphi_mapped_overlap import _triangles,_barycentric,_compose
        from superfish_ng.planar_tracking_remesh import _rational_points
        base=partition(2);mesh=base.mesh;lower=mesh.points_rz_m[mesh.triangles][:,:,1].mean(axis=1)<3/64
        regions=[RFMaterialRegion('lower','a',np.flatnonzero(lower).tolist()),RFMaterialRegion('upper','b',np.flatnonzero(~lower).tolist())]
        a=RFMaterialPartition(mesh,base.materials,regions);control=partition(1).mesh
        raw=control.to_dict();points=np.asarray(raw['points_rz_m']);mask=(points[:,0]==1/16)&(points[:,1]==1/32)
        self.assertEqual(int(mask.sum()),1);points[mask,1]+=1/128;raw['points_rz_m']=points.tolist()
        mapping=HphiGeometryMapping(control,type(control).from_dict(raw))
        triangles=_triangles(control);new_triangles=_triangles(mapping.current)
        def moved(values):
            result=[]
            for point in _rational_points(values):
                for i,triangle in enumerate(triangles):
                    try:bary=_barycentric([point],triangle)
                    except ValueError:continue
                    result.append(_compose(bary,new_triangles[i])[0]);break
                else:raise AssertionError('uncovered fixture point')
            return np.asarray(result,dtype=float)
        b=RFMaterialPartition(transformed(mesh,moved),a.materials,a.regions)
        result=material_hphi_overlay(request(a,b,mapping))
        self.assertGreater(len(np.unique(result.interfaces.current_vertices_rz_m[:,:,1])),1)
        for side,p in [('previous',a),('current',b)]:
            vertices=getattr(result.interfaces,side+'_vertices_rz_m')
            lengths=np.linalg.norm(np.diff(vertices,axis=1)[:,0],axis=1)
            original=p.mesh.points_rz_m[p.interface_edges]
            self.assertAlmostEqual(lengths.sum(),np.linalg.norm(original[:,1]-original[:,0],axis=1).sum(),delta=1e-15)

    def test_one_ulp_interface_shift_and_equal_coefficient_regions(self):
        a=partition();raw=a.mesh.to_dict();points=np.asarray(raw['points_rz_m'])
        points[points[:,1]==1/32,1]=np.nextafter(1/32,np.inf);raw['points_rz_m']=points.tolist()
        shifted=RFMaterialPartition(type(a.mesh).from_dict(raw),a.materials,a.regions)
        with self.assertRaisesRegex(ValueError,'region'):material_hphi_overlay(request(a,shifted))
        materials=[LinearRFMaterial('a',2.,3.),LinearRFMaterial('b',2.,3.)]
        equal=RFMaterialPartition(a.mesh,materials,a.regions)
        result=material_hphi_overlay(request(equal,equal));self.assertGreater(len(result.interfaces.current_cells),0)
        changed=RFMaterialPartition(a.mesh,materials,[RFMaterialRegion('lower','a',a.regions[1].cell_indices),RFMaterialRegion('upper','b',a.regions[0].cell_indices)])
        with self.assertRaisesRegex(ValueError,'region'):material_hphi_overlay(request(equal,changed))
        with self.assertRaisesRegex(ValueError,'max_interface_pieces'):material_hphi_overlay(request(a,a),max_interface_pieces=1)

    def test_uniform_partition_has_no_invented_interface_and_preserves_input(self):
        mesh=fixture(1,0);a=RFMaterialPartition(mesh,[LinearRFMaterial('fixed',4.,9.)],
            [RFMaterialRegion('all','fixed',list(range(len(mesh.triangles))))])
        q=request(a,a);raw=q.to_dict();result=material_hphi_overlay(q)
        self.assertEqual(result.interfaces.previous_cells.shape,(0,2))
        self.assertEqual(result.interfaces.current_vertices_rz_m.shape,(0,2,2))
        self.assertEqual(q.to_dict(),raw)
        raw['previous_partition']['materials'][0]['epsilon_r']=100.
        self.assertEqual(result.comparison.previous_partition.materials[0].epsilon_r,4.)

    def test_mismatch_strict_ids_fixed_coefficients_and_budgets(self):
        a=partition();q=request(a,a);raw=q.to_dict()
        for change in (lambda d:d.update(extra=1),lambda d:d.update(schema_version=True),lambda d:d.update(material_pairs=tuple(d['material_pairs'])),
                       lambda d:d['material_pairs'].pop(),lambda d:d['region_pairs'][0].update(current_id='upper'),
                       lambda d:d['current_partition']['materials'][0].update(epsilon_r=2.0000000000000004)):
            bad=deepcopy(raw);change(bad)
            with self.assertRaises(ValueError):MaterialHphiComparison.from_dict(bad)
        b=RFMaterialPartition(a.mesh,a.materials,[RFMaterialRegion('lower','a',a.regions[1].cell_indices),RFMaterialRegion('upper','b',a.regions[0].cell_indices)])
        with self.assertRaisesRegex(ValueError,'region'):material_hphi_overlay(request(a,b))
        for options in ({'max_interface_tests':1},{'max_overlay_triangles':1},{'max_candidate_tests':1}):
            with self.assertRaises(ValueError):material_hphi_overlay(q,**options)


if __name__=='__main__':unittest.main()

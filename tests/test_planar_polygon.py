# SPDX-License-Identifier: Apache-2.0
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.planar import PlanarCase,solve_planar,planar_matrices,PlanarFieldSampler,planar_quantities
from superfish_ng.planar_mesh import PlanarMesh,_check_edges
from superfish_ng.planar_polygon import PlanarPolygonCase,planar_case_from_dict,PolygonLocator
from superfish_ng.planar_saved import save_planar_run,read_planar_run,planar_result
from superfish_ng.constants import C0


class PlanarPolygonTests(unittest.TestCase):
    def rectangle(self,order=2,pol='te'):
        base=PlanarCase(.31,.2,pol,nx=6,ny=5,element_order=order,modes=3)
        space=planar_matrices(base)[0]
        mesh=PlanarMesh.create([[0.,0.],[.31,0.],[.31,.2],[0.,.2]],space.points_xy_m,space.triangles)
        return PlanarPolygonCase(mesh,pol,order,3)

    def rehash(self,folder,name):
        path=folder/'manifest.json';data=json.loads(path.read_text());data['files'][name]=hashlib.sha256((folder/name).read_bytes()).hexdigest();path.write_text(json.dumps(data))

    def test_strict_v2_and_legacy_reader_separation(self):
        case=self.rectangle();data=case.to_dict()
        self.assertEqual(planar_case_from_dict(data),case)
        with self.assertRaises(ValueError):PlanarCase.from_dict(data)
        for key,value in [('coordinates','axisymmetric'),('material','dielectric'),('boundary','magnetic'),('propagation_constant_per_m',1),('propagation_constant_per_m',False),('polarization','tem')]:
            bad=copy.deepcopy(data);bad['model'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):planar_case_from_dict(bad)
        for key in ('nx','curves','regions'):
            bad=copy.deepcopy(data);bad['mesh'][key]=1
            with self.subTest(key=key),self.assertRaises(ValueError):planar_case_from_dict(bad)
        bad=copy.deepcopy(data);bad['schema_version']=True
        with self.assertRaises(ValueError):planar_case_from_dict(bad)

    def test_triangle_spectrum_and_boundary_conditions(self):
        # Coarse smoke check; the independent fine-grid f/field/G gates are
        # documented separately and are stricter than this frequency check.
        n=16;a=.2;coordinates=[(i,j) for i in range(n+1) for j in range(i+1)];lookup={v:k for k,v in enumerate(coordinates)}
        points=np.array(coordinates)*a/n;cells=[]
        for i in range(n):
            for j in range(i+1):
                cells.append([lookup[(i,j)],lookup[(i+1,j)],lookup[(i+1,j+1)]])
                if j<i:cells.append([lookup[(i,j)],lookup[(i+1,j+1)],lookup[(i,j+1)]])
        mesh=PlanarMesh.create(points[[lookup[(0,0)],lookup[(n,0)],lookup[(n,n)]]],points,cells)
        for pol,numbers in (('te',[1,2,4]),('tm',[5,10,13])):
            s=solve_planar(PlanarPolygonCase(mesh,pol,2,3))
            np.testing.assert_allclose(s.frequencies_hz,C0/(2*a)*np.sqrt(numbers),rtol=1e-3)
            if pol=='tm':np.testing.assert_array_equal(s.coefficients[np.unique(s.space.boundary_dofs)],0.)
            else:
                ones=np.ones(len(s.coefficients));np.testing.assert_allclose(ones@(s.mass@s.coefficients),0.,atol=1e-10)

    def test_rigid_transform_and_unit_length_normalization(self):
        angle=.31;r=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        for order in (1,2):
            for pol in ('te','tm'):
                case=self.rectangle(order,pol);a=solve_planar(case);mesh=case.mesh
                transformed=PlanarMesh.create(mesh.polygon_xy_m@r.T*2+[-.4,.8],mesh.points_xy_m@r.T*2+[-.4,.8],mesh.triangles)
                b=solve_planar(replace(case,mesh=transformed,normalization_j_per_m=3.))
                np.testing.assert_allclose(b.frequencies_hz*2,a.frequencies_hz,rtol=1e-12)
                for mode in range(3):
                    qa,qb=planar_quantities(a,mode),planar_quantities(b,mode)
                    self.assertAlmostEqual(qb['stored_energy_j_per_m'],3.,places=11)
                    self.assertAlmostEqual(qb['geometry_factor_ohm']/qa['geometry_factor_ohm'],1.,places=11)
                    self.assertAlmostEqual(qb['wall_loss_w_per_m']/qa['wall_loss_w_per_m'],3*2**(-1.5),places=11)

    def test_native_v1_and_v2_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            for case in (PlanarCase(.31,.2,nx=6,ny=5,modes=3),self.rectangle()):
                folder=Path(temporary)/str(case.to_dict()['schema_version']);s=solve_planar(case)
                result=save_planar_run(case,s,folder);before={p.name:p.read_bytes() for p in folder.iterdir()}
                self.assertEqual(result,planar_result(read_planar_run(folder)))
                self.assertEqual(before,{p.name:p.read_bytes() for p in folder.iterdir()})
                self.assertEqual(json.loads((folder/'manifest.json').read_text())['schema_version'],case.to_dict()['schema_version'])

    def test_rehashed_case_and_version_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            case=self.rectangle();s=solve_planar(case)
            for key in ('geometry','modes','manifest'):
                folder=Path(temporary)/key;save_planar_run(case,s,folder)
                if key=='manifest':
                    data=json.loads((folder/'manifest.json').read_text());data['schema_version']=1;(folder/'manifest.json').write_text(json.dumps(data))
                else:
                    data=case.to_dict()
                    if key=='geometry':data['geometry']['vertices_xy_m'][0][0]+=.01
                    else:data['modes']=2
                    (folder/'case.json').write_text(json.dumps(data));self.rehash(folder,'case.json')
                with self.subTest(key=key),self.assertRaises(ValueError):read_planar_run(folder)

    def test_source_changes_during_v2_replay(self):
        import superfish_ng.planar_saved as saved
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/'native';case=self.rectangle();save_planar_run(case,solve_planar(case),folder)
            original=saved._restore
            def changed(*args,**kwargs):
                result=original(*args,**kwargs)
                with (folder/'case.json').open('a') as stream:stream.write(' ')
                return result
            with patch.object(saved,'_restore',side_effect=changed),self.assertRaisesRegex(ValueError,'changed during'):read_planar_run(folder)

    def test_wrong_positive_band_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/'native';case=self.rectangle();s=solve_planar(case);save_planar_run(case,s,folder)
            extra=solve_planar(replace(case,modes=4))
            np.savez_compressed(folder/'fields.npz',coefficients=extra.coefficients[:,1:],frequencies_hz=extra.frequencies_hz[1:]);self.rehash(folder,'fields.npz')
            with self.assertRaisesRegex(ValueError,'lowest positive'):read_planar_run(folder)

    def test_exact_thin_cell_and_shared_edge_location(self):
        p=np.array([[0.,0.],[1.,0.],[.3,1e-12]])
        locator=PolygonLocator(SimpleNamespace(points_xy_m=p,triangles=np.array([[0,1,2]])))
        for bary in (np.array([.2,.3,.5]),np.array([1.,0.,0.]),np.array([0.,0.,1.])):
            cells,actual=locator.locate((bary@p)[None,:]);np.testing.assert_allclose(actual[0],bary,atol=1e-14)
        for point in ([.3,1.001e-12],[.3,-1e-20],[1.00001,0]):
            with self.subTest(point=point),self.assertRaises(ValueError):locator.locate(np.array([point]))
        p=np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.]])
        locator=PolygonLocator(SimpleNamespace(points_xy_m=p,triangles=np.array([[0,1,2],[0,2,3]])))
        cells,bary=locator.locate(np.array([[.5,.5],[0.,0.],[1.,1.]]));np.testing.assert_array_equal(cells,[0,0,0])

    def test_cli_all_components_and_native_protection(self):
        import csv
        from superfish_ng.cli import main
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=self.rectangle();casefile=root/'case.json';casefile.write_text(json.dumps(case.to_dict()));folder=root/'native'
            self.assertEqual(main(['solve-planar',str(casefile),'--out',str(folder)]),0)
            points=np.array([[.021,.034],[.112,.087]]);pointfile=root/'points.json';pointfile.write_text(json.dumps(points.tolist()));csvfile=root/'probe.csv'
            self.assertEqual(main(['probe-planar',str(folder),'--points',str(pointfile),'--out',str(csvfile)]),0)
            expected=PlanarFieldSampler(read_planar_run(folder)).evaluate(points)
            with csvfile.open() as stream:rows=list(csv.DictReader(stream))
            self.assertEqual(set(rows[0]),{'x_m','y_m',*expected})
            for key in expected:np.testing.assert_array_equal([float(row[key]) for row in rows],expected[key])
            before={p.name:p.read_bytes() for p in folder.iterdir()}
            self.assertNotEqual(main(['probe-planar',str(folder),'--points',str(pointfile),'--out',str(folder/'probe.csv')]),0)
            self.assertEqual(before,{p.name:p.read_bytes() for p in folder.iterdir()})

    def test_bvh_matches_exhaustive_closed_box_pairs(self):
        from superfish_ng.planar_edge_bounds import edge_pairs
        rng=np.random.default_rng(884)
        for count in (1,8,9,32,80):
            for kind in ('random','thin','same'):
                endpoints=rng.normal(size=(count,2,2))
                if kind=='thin':endpoints[:,:,1]*=1e-14
                if kind=='same':endpoints[:]=endpoints[0]
                low,high=endpoints.min(axis=1),endpoints.max(axis=1)
                expected={(i,j) for i in range(count) for j in range(i+1,count) if np.all(high[i]>=low[j]) and np.all(high[j]>=low[i])}
                actual=list(edge_pairs(low,high));self.assertEqual(len(actual),len(set(actual)));self.assertEqual(set(actual),expected)

    def test_large_edge_path_keeps_hidden_crossing_rejection(self):
        count=32768;x=np.arange(count,dtype=float)*2
        points=np.empty((2*count,2));points[::2]=np.column_stack((x,np.zeros(count)));points[1::2]=np.column_stack((x+1,np.zeros(count)))
        edges=np.arange(2*count).reshape(-1,2)
        _check_edges(points,edges,'separated edges')
        points=np.vstack((points,[[.5,-1.],[.5,1.]]));edges=np.vstack((edges,[[2*count,2*count+1]]))
        with self.assertRaisesRegex(ValueError,'intersect'):_check_edges(points,edges,'large hidden crossing')


if __name__=='__main__':unittest.main()

# SPDX-License-Identifier: Apache-2.0
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.constants import EPS0, MU0, TAU
from superfish_ng.planar import PlanarCase, solve_planar
from superfish_ng.planar_saved import save_planar_run
from superfish_ng.planar_display import display_planar_fields, export_planar_probe
from superfish_ng.planar_polygon import PlanarPolygonCase, load_planar_case
from superfish_ng.planar_mesh import PlanarMesh


class PlanarDisplayTests(unittest.TestCase):
    def test_original_parent_samples_and_all_components(self):
        for polygon in (False, True):
            for order in (1, 2):
                for pol in ('te', 'tm'):
                    for scale in (1., 2.):
                        with self.subTest(polygon=polygon, order=order, pol=pol, scale=scale):
                            if polygon:
                                mesh=load_planar_case('examples/planar/triangle_te.json').mesh
                                case=PlanarPolygonCase(PlanarMesh.create(mesh.polygon_xy_m*scale,mesh.points_xy_m*scale,mesh.triangles),pol,order,2)
                            else:case=PlanarCase(.31*scale,.2*scale,pol,nx=8,ny=6,element_order=order,modes=2)
                            s=solve_planar(case);d=display_planar_fields(s,1)
                            self.assertEqual(len(d['triangles']),len(s.space.triangles)*(4 if order==2 else 1))
                            centres=d['points_xy_m'][d['triangles']].mean(axis=1)
                            expected=np.einsum('ni,nij->nj',d['barycentric'],s.space.points_xy_m[s.space.triangles[d['parent_cells']]])
                            np.testing.assert_allclose(centres,expected,rtol=1e-14,atol=1e-16)
                            fields=s.fields_in_cells(d['parent_cells'],d['barycentric'],1)
                            for key,value in fields.items():np.testing.assert_array_equal(value,d['fields'][key])
                            self.assertEqual(len(d['fields']),18)
                            for axis in 'xyz':
                                for phase in ('real','quadrature'):
                                    np.testing.assert_array_equal(d['fields'][f'B{axis}_{phase}_T'],MU0*fields[f'H{axis}_{phase}_A_per_m'])
                            for mode in (-1,True,2):
                                with self.assertRaises(ValueError):display_planar_fields(s,mode)

    def test_independent_rectangle_signed_fields(self):
        for pol in ('te','tm'):
            for scale in (1.,2.):
                a,b=.31*scale,.2*scale
                s=solve_planar(PlanarCase(a,b,pol,nx=24,ny=20,element_order=2,modes=1))
                d=display_planar_fields(s);x,y=d['points_xy_m'][d['triangles']].mean(axis=1).T
                omega=TAU*s.frequencies_hz[0]
                if pol=='tm':
                    amplitude=np.sqrt(8/(EPS0*a*b))
                    scalar=amplitude*np.sin(np.pi*x/a)*np.sin(np.pi*y/b)
                    dx=amplitude*np.pi/a*np.cos(np.pi*x/a)*np.sin(np.pi*y/b)
                    dy=amplitude*np.pi/b*np.sin(np.pi*x/a)*np.cos(np.pi*y/b)
                    expected={'Ez_real_V_per_m':scalar,'Hx_quadrature_A_per_m':dy/(omega*MU0),'Hy_quadrature_A_per_m':-dx/(omega*MU0)}
                else:
                    amplitude=np.sqrt(4/(MU0*a*b));scalar=amplitude*np.cos(np.pi*x/a)
                    dx=-amplitude*np.pi/a*np.sin(np.pi*x/a)
                    expected={'Hz_real_A_per_m':scalar,'Ey_quadrature_V_per_m':dx/(omega*EPS0)}
                first=next(iter(expected));phase=1 if np.dot(expected[first],d['fields'][first])>0 else -1
                for key,value in expected.items():
                    self.assertLess(np.linalg.norm(phase*d['fields'][key]-value)/np.linalg.norm(value),.01)
                if pol=='te':
                    self.assertLess(np.linalg.norm(d['fields']['Ex_quadrature_V_per_m'])/np.linalg.norm(expected['Ey_quadrature_V_per_m']),.01)

    def test_probe_si_metadata_and_output_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);run=root/'native';case=PlanarCase(.31,.2,'tm',nx=6,ny=5,modes=1)
            s=solve_planar(case);save_planar_run(case,s,run)
            before={p.name:p.read_bytes() for p in run.iterdir()};points=[[.03,.07],[.21,.11]];out=root/'probe.csv'
            metadata=export_planar_probe(run,out,points)
            self.assertEqual(metadata,json.loads(out.with_suffix('.csv.json').read_text()))
            self.assertEqual(metadata['data_sha256'],hashlib.sha256(out.read_bytes()).hexdigest())
            self.assertEqual(metadata['native_sha256'],{k:hashlib.sha256(v).hexdigest() for k,v in before.items()})
            self.assertEqual(metadata['quantities']['r_over_q_accelerator_ohm'],None)
            with out.open() as stream:rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows[0]),14);self.assertEqual(float(rows[0]['x_m']),.03)
            for destination in (out,run/'probe.csv'):
                with self.assertRaises(ValueError):export_planar_probe(run,destination,points)
            for points in ([[.4,.1]],[[True,.1]],[[float('nan'),.1]]):
                with self.assertRaises(ValueError):export_planar_probe(run,root/'invalid.csv',points)
            for mode in (0,True,2):
                with self.assertRaises(ValueError):export_planar_probe(run,root/'invalid.csv',[[.03,.07]],mode)
            self.assertFalse((root/'invalid.csv').exists())
            self.assertEqual(before,{p.name:p.read_bytes() for p in run.iterdir()})

    def test_plot_dispatch_signed_components_and_metadata(self):
        try:import matplotlib
        except ImportError:self.skipTest('optional matplotlib unavailable')
        from superfish_ng.visualize import plot_mode
        from superfish_ng.planar_visualize import plot_planar_mode
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for pol in ('te','tm'):
                case=load_planar_case(f'examples/planar/triangle_{pol}.json');run=root/pol
                save_planar_run(case,solve_planar(case),run);before={p.name:p.read_bytes() for p in run.iterdir()}
                out=root/(pol+'.png');metadata=plot_mode(run,out,show_mesh=True)
                self.assertTrue(out.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertEqual(metadata,json.loads(out.with_suffix('.png.json').read_text()))
                self.assertEqual(metadata['numerical_validation'],'not_checked')
                self.assertEqual(metadata['components'][0],'Ez_real_V_per_m' if pol=='tm' else 'Bz_real_T')
                for kwargs in ({'probe_z_m':.1},{'mode':True},{'mode':9}):
                    with self.assertRaises(ValueError):plot_mode(run,root/'invalid.png',**kwargs)
                for kwargs in ({'length_unit':'cm'},{'show_mesh':1}):
                    with self.assertRaises(ValueError):plot_planar_mode(run,root/'invalid.png',**kwargs)
                self.assertEqual(before,{p.name:p.read_bytes() for p in run.iterdir()})

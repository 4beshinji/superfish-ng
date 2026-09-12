# SPDX-License-Identifier: Apache-2.0
"""Physical and topological invariants for positive-radius meshes with holes."""
import copy
from dataclasses import replace
import unittest
import numpy as np
from scripts.hphi_mesh_reference import rectangular_holes, reference
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.hphi_mesh import HphiMeshCase, hphi_mesh_matrices, solve_hphi_mesh, hphi_mesh_quantities
from superfish_ng.coaxial import CoaxialCase, coaxial_matrices, solve_coaxial


class HphiMeshTests(unittest.TestCase):
    def test_sloped_hole_and_concave_outer_geometry(self):
        data = rectangular_holes(2)
        def transform(points):
            p = np.asarray(points); x = np.round((p[:,0]-.025)/.0125); y = np.round(p[:,1]/.03)
            return np.column_stack((.125+x/64+y/128,.25+y/64))
        data['points_rz_m'] = transform(data['points_rz_m'])
        data['outer_rz_m'] = transform(data['outer_rz_m'])
        data['holes_rz_m'] = [transform(h) for h in data['holes_rz_m']]
        mesh = MeridionalMesh(**data)
        self.assertAlmostEqual(mesh.area_m2,(36-4)/64**2,places=15)
        self.assertAlmostEqual(mesh.volume_m3,2*np.pi*(36-4)/64**2*(.125+3/64+3/128),places=15)
        solution = solve_hphi_mesh(HphiMeshCase(mesh,modes=2))
        hole = mesh.holes_rz_m[0]
        with self.assertRaises(ValueError):solution.fields_at([hole.mean(axis=0)])
        # A dyadic point immediately inside the hole is never accepted by a barycentric tolerance.
        inside = (hole[0]+hole[1])/2+np.array([2**-45,0.])
        with self.assertRaises(ValueError):solution.fields_at([inside])
        p = np.array([[0,0],[1,0],[2,0],[0,1],[1,1],[2,1],[0,2],[1,2]],dtype=float)/32+[.125,0]
        triangles = [[0,1,4],[0,4,3],[1,2,5],[1,5,4],[3,4,7],[3,7,6]]
        concave = MeridionalMesh(p[[0,2,5,4,7,6]],[],p,triangles)
        self.assertAlmostEqual(concave.area_m2,3/32**2,places=15)
        cavity = solve_hphi_mesh(HphiMeshCase(concave,modes=2))
        with self.assertRaises(ValueError):cavity.fields_at([[.125+1.5/32,1.5/32]])
        cavity.fields_at([[.125+.5/32,1.5/32]])

    def test_nested_external_crossed_and_disconnected_domains_rejected(self):
        good = rectangular_holes(2)
        bad = []
        data = copy.deepcopy(good);data['holes_rz_m'][0] = (np.array(data['holes_rz_m'][0])+[.1,0]).tolist();bad.append(data)
        data = copy.deepcopy(good);h = np.array(data['holes_rz_m'][0]);data['holes_rz_m'].append((h.mean(axis=0)+(h-h.mean(axis=0))/2).tolist());bad.append(data)
        data = copy.deepcopy(good);data['outer_rz_m'] = np.array(data['outer_rz_m'])[[0,2,1,3]];bad.append(data)
        data = copy.deepcopy(good);data['points_rz_m'] = np.vstack((data['points_rz_m'],[[.03,.03],[.035,.03],[.03,.035]]))
        data['triangles'] = np.vstack((data['triangles'],np.arange(len(data['points_rz_m'])-3,len(data['points_rz_m']))));bad.append(data)
        for data in bad:
            with self.assertRaises(ValueError):MeridionalMesh(**data)

    def test_holes_volume_surface_and_topology(self):
        for holes in (0, 1, 2):
            data = rectangular_holes(2, holes)
            mesh = MeridionalMesh(**data)
            a, b, length = .025, .1, .18
            volume = np.pi*(b*b-a*a)*length
            area = (b-a)*length
            for polygon in data['holes_rz_m']:
                c, low = polygon[0]; d, high = polygon[2]
                volume -= np.pi*(d*d-c*c)*(high-low)
                area -= (d-c)*(high-low)
            self.assertAlmostEqual(mesh.volume_m3, volume, places=14)
            self.assertAlmostEqual(mesh.area_m2, area, places=14)
            self.assertEqual(mesh.euler_characteristic, 1-holes)
            self.assertEqual(set(mesh.boundary_components), set(range(holes+1)))
            self.assertEqual(MeridionalMesh.from_dict(mesh.to_dict()).to_dict(), mesh.to_dict())

    def test_strict_geometry_and_hole_rejection(self):
        good = rectangular_holes(2)
        bad = []
        for key in ('outer_rz_m', 'holes_rz_m'):
            data = copy.deepcopy(good)
            if key == 'outer_rz_m': data[key] = data[key][::-1]
            else: data[key][0] = data[key][0][::-1]
            bad.append(data)
        data = copy.deepcopy(good); data['holes_rz_m'] = []; bad.append(data)
        data = copy.deepcopy(good); data['holes_rz_m'].append(data['holes_rz_m'][0]); bad.append(data)
        data = copy.deepcopy(good); data['triangles'] = data['triangles'][1:]; bad.append(data)
        data = copy.deepcopy(good); data['triangles'] = np.vstack((data['triangles'], data['triangles'][0])); bad.append(data)
        data = copy.deepcopy(good); data['points_rz_m'][0,0] = 0; bad.append(data)
        data = copy.deepcopy(good); data['points_rz_m'] = data['points_rz_m'].tolist(); data['points_rz_m'][0][0] = True; bad.append(data)
        for data in bad:
            with self.assertRaises(ValueError): MeridionalMesh(**data)

    def test_weighted_polynomial_forms_and_single_static_nullspace(self):
        for holes in (1, 2):
            data = rectangular_holes(2, holes)
            for order in (1, 2):
                case = HphiMeshCase(MeridionalMesh(**data), element_order=order, modes=4)
                space, k, m, _ = hphi_mesh_matrices(case)
                r, z = space.dof_points.T
                functions = [(np.ones(len(r)), lambda r,z: (1+0*r,0*r,0*r)),
                             (r, lambda r,z: (r,1+0*r,0*r)), (z, lambda r,z: (z,0*r,1+0*r))]
                if order == 2: functions += [(r*z, lambda r,z: (r*z,z,r)), (z*z, lambda r,z: (z*z,0*r,2*z))]
                expected_m = np.zeros((len(functions),)*2); expected_k = expected_m.copy()
                x, w = np.polynomial.legendre.leggauss(64)
                for sign, polygon in [(1, data['outer_rz_m']), *[(-1, h) for h in data['holes_rz_m']]]:
                    p = np.array(polygon); low = p.min(axis=0); high = p.max(axis=0)
                    rr, zz = np.meshgrid(low[0]+(x+1)*(high[0]-low[0])/2, low[1]+(x+1)*(high[1]-low[1])/2)
                    weight = sign*np.outer(w,w)*np.prod(high-low)/4/rr
                    values = [f[1](rr,zz) for f in functions]
                    expected_m += [[np.sum(weight*a[0]*b[0]) for b in values] for a in values]
                    expected_k += [[np.sum(weight*(a[1]*b[1]+a[2]*b[2])) for b in values] for a in values]
                c = np.column_stack([f[0] for f in functions])
                np.testing.assert_allclose(c.T@(m@c), expected_m, rtol=1e-10, atol=1e-14)
                np.testing.assert_allclose(c.T@(k@c), expected_k, rtol=1e-10, atol=1e-11)
                self.assertLess(np.linalg.norm(k@np.ones(len(r)))/np.linalg.norm(k.data), 1e-13)
                from scipy.linalg import eigvalsh
                values = eigvalsh(k.toarray(), m.toarray())
                self.assertLess(abs(values[0]), 1e-7)
                self.assertGreater(values[1], 1.)

    def test_hole_mode_fields_losses_and_probe_domain(self):
        for holes in (1, 2):
            data = rectangular_holes(4, holes)
            case = HphiMeshCase(MeridionalMesh(**data), modes=9)
            solution = solve_hphi_mesh(case); exact, walls, fields = reference(data)
            mode = int(np.argmin(abs(solution.frequencies_hz/exact['frequency_hz']-1)))
            self.assertLess(mode, case.modes-1)  # Require a guard above the analytic mode.
            self.assertLess(abs(solution.frequencies_hz[mode]/exact['frequency_hz']-1), .001)
            centers = case.mesh.points_rz_m[case.mesh.triangles].mean(axis=1)
            actual = solution.fields_at(centers, mode); h,e = fields(centers)
            sign = np.sign(h@actual['Hphi_real_A_per_m'])
            for key, value in [('Hphi_real_A_per_m',h), ('Er_quadrature_V_per_m',e)]:
                self.assertLess(np.linalg.norm(sign*actual[key]-value)/np.linalg.norm(value), .03)
            rf = hphi_mesh_quantities(solution, mode)
            np.testing.assert_allclose(rf['wall_h2_integral_a2_by_segment'], walls, rtol=.01)
            for key in ('geometry_factor_ohm','q0','wall_loss_w'):
                self.assertLess(abs(rf[key]/exact[key]-1), .01)
            self.assertAlmostEqual(rf['stored_energy_j'],1.,places=8)
            self.assertIsNone(rf['r_over_q_accelerator_ohm'])
            for hole in data['holes_rz_m']:
                with self.assertRaisesRegex(ValueError,'outside|conductor'): solution.fields_at([np.mean(hole,axis=0)])
                solution.fields_at([hole[0]])
            with self.assertRaises(ValueError): solution.fields_at([[0.,.1]])
            with self.assertRaises(ValueError): solution.fields_at([[True,.1]])

    def test_rectangle_matches_coaxial_forms_and_spectrum(self):
        for order in (1,2):
            cylinder = CoaxialCase(.025,.1,.18,nr=6,nz=6,element_order=order,modes=3)
            old,k0,m0,_ = coaxial_matrices(cylinder)
            data = rectangular_holes(2,0)
            case = HphiMeshCase(MeridionalMesh(**data),element_order=order,modes=3)
            new,k,m,_ = hphi_mesh_matrices(case)
            np.testing.assert_array_equal(new.dof_points,old.dof_points)
            np.testing.assert_array_equal(new.cell_dofs,old.cell_dofs)
            np.testing.assert_array_equal(k.toarray(),k0.toarray())
            np.testing.assert_array_equal(m.toarray(),m0.toarray())
            np.testing.assert_allclose(solve_hphi_mesh(case).frequencies_hz,solve_coaxial(cylinder).frequencies_hz,rtol=1e-12)

    def test_explicit_physics_schema_and_translation(self):
        case = HphiMeshCase(MeridionalMesh(**rectangular_holes(2)),modes=2)
        document = case.to_dict()
        self.assertEqual(HphiMeshCase.from_dict(document).to_dict(),document)
        for key,value in [('azimuthal_index',1),('material','dielectric'),('boundary','open'),('field_family','Ephi')]:
            bad = copy.deepcopy(document);bad['model'][key] = value
            with self.assertRaises(ValueError): HphiMeshCase.from_dict(bad)
        with self.assertRaises(ValueError): HphiMeshCase.from_dict(dict(document,extra=0))
        shifted = HphiMeshCase(MeridionalMesh(**rectangular_holes(2,z_offset=.25)),modes=2)
        np.testing.assert_allclose(solve_hphi_mesh(case).frequencies_hz,solve_hphi_mesh(shifted).frequencies_hz,rtol=1e-11)

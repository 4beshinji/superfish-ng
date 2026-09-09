# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.project import Project
from superfish_ng.affine_conics import transform_curve
from superfish_ng.affine_remesh_tracking import track_affine_remesh_modes
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution


def partition_case():
    raw=Case.load('examples/curved_ellipse.json').to_dict();raw['mesh']['geometry_order']=2
    raw['mesh']['contour_mesh'].update(max_edge_m=.08,min_angle_deg=5.);raw['geometry']['chord_tolerance_m']=.008
    return Case.from_dict(raw)


class CurvePartitionTests(unittest.TestCase):
    def test_declared_default_partition_preserves_native_fem_and_saved_geometry(self):
        case=partition_case();old=solve(case)
        approximation=case.curved_contour.linearize(case.curve_chord_tolerance_m)
        counts=tuple(np.bincount(approximation.segment_curve_indices,minlength=len(case.curved_contour.curves)).tolist())
        declared=replace(case,curve_segments_per_curve=counts)
        self.assertEqual(Case.from_dict(declared.to_dict()),declared)
        new=solve(declared,mesh_data=old.source_mesh_data)
        np.testing.assert_array_equal(new.space.geometry.points_rz_m,old.space.geometry.points_rz_m)
        np.testing.assert_array_equal(new.frequencies_hz,old.frequencies_hz)
        with tempfile.TemporaryDirectory() as tmp:
            save_run(declared,new,Path(tmp)/'run');saved=read_solution(Path(tmp)/'run')
            self.assertEqual(saved.case.curve_segments_per_curve,counts)
            np.testing.assert_array_equal(saved.space.geometry.points_rz_m,new.space.geometry.points_rz_m)

    def test_fixed_counts_preserve_affine_boundary_when_automatic_counts_change(self):
        case=partition_case();old=solve(case);mapping=dict(radial_scale=2.,axial_scale=.5,axial_shear=0.)
        contour=replace(case.curved_contour,curves=tuple(transform_curve(c,mapping) for c in case.curved_contour.curves))
        target=replace(case,curved_contour=contour,contour=None,curve_chord_tolerance_m=.04)
        mesh=deepcopy(old.source_mesh_data);mesh['points']=(np.array(mesh['points'])*[2.,.5]).tolist()
        with self.assertRaises(ValueError):Project(target,mesh_data=mesh)
        fixed=replace(target,curve_segments_per_curve=(1,4),contour=None)
        new=solve(fixed,mesh_data=mesh)
        np.testing.assert_allclose(new.space.geometry.points_rz_m,old.space.geometry.points_rz_m*[2.,.5],rtol=0,atol=1e-15)
        report=track_affine_remesh_modes(old,new,['A'],mapping='affine_remesh',affine_map=mapping,sample_order=5,
            minimum_overlap=.8,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        self.assertEqual(report['status'],'PASS')

    def test_insufficient_counts_and_strict_inputs(self):
        case=partition_case()
        for counts in ([],[1],[True,4],[1,0],[1,1],[1,20001],None,'1,4'):
            raw=case.to_dict();raw['geometry']['segments_per_curve']=counts
            with self.subTest(counts=counts),self.assertRaises(ValueError):Case.from_dict(raw)
        with self.assertRaises(ValueError):replace(case,curve_segments_per_curve=[1,4])

    def test_reflection_preserves_counts_and_replay(self):
        from test_curved_reflection import half_case
        from superfish_ng.symmetry import reflect_solution
        for side in ('z_min','z_max'):
            for tag in ('electric_symmetry','magnetic_symmetry'):
                case=half_case(side,tag)
                approximation=case.curved_contour.linearize(case.curve_chord_tolerance_m)
                counts=tuple(np.bincount(approximation.segment_curve_indices,minlength=3).tolist())
                case=replace(case,curve_segments_per_curve=counts)
                full,solution=reflect_solution(case,solve(case))
                self.assertEqual(len(full.curve_segments_per_curve),len(full.curved_contour.curves))
                with tempfile.TemporaryDirectory() as tmp:
                    save_run(full,solution,Path(tmp)/'run');read_solution(Path(tmp)/'run')

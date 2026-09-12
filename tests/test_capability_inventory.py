# SPDX-License-Identifier: Apache-2.0
import contextlib,io,json,tempfile,unittest
from pathlib import Path
from scripts.validate_capability_inventory import cases,commands
from superfish_ng.model import capabilities,Model
from superfish_ng.cli import main
from superfish_ng.hphi_native import hphi_case_from_dict,solve_hphi,save_hphi_run,read_hphi_run,hphi_result
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_study import HphiStudy
from superfish_ng.hphi_tracking_history import HphiTrackingHistoryRequest
from superfish_ng.hphi_field_overlap import hphi_field_grams
from superfish_ng.curved_hphi import CurvedHphiCase
from superfish_ng.axis_hphi import AxisHphiCase
from superfish_ng.planar_tracking import PlanarTrackingRequest
from superfish_ng.planar_tracking_polygon import PolygonScaleMapping
from superfish_ng.planar_tracking_similarity import PolygonSimilarityMapping
from superfish_ng.planar_tracking_remesh import PolygonRemeshMapping
from superfish_ng.planar_tracking_similarity_remesh import PolygonSimilarityRemeshMapping
from superfish_ng.planar_tracking_affine_remesh import PolygonAffineRemeshMapping
from superfish_ng.planar_tracking_exact_mapping import PolygonExactAffineRemeshMapping


class CapabilityInventoryTests(unittest.TestCase):
    def test_advertised_hphi_formats_match_real_fem_native_and_operations(self):
        inventory=capabilities()['hphi_rf'];families={f['case_format']:f for f in inventory['case_families']}
        with tempfile.TemporaryDirectory() as temp:
            for order in (1,2):
                for index,case in enumerate(cases(order)):
                    raw=case.to_dict();row=families[raw['format']];axis=isinstance(case,AxisHphiCase) or isinstance(case,CurvedHphiCase) and case.axis_connected
                    self.assertIn(axis,row['axis_connected']);self.assertIn(order,row['element_orders']);self.assertIn(raw['schema_version'],row['case_schema_versions'])
                    self.assertEqual(hphi_case_from_dict(raw).to_dict(),raw)
                    solution=solve_hphi(case);run=Path(temp)/f'{order}-{index}';result=save_hphi_run(case,solution,run)
                    self.assertEqual(hphi_result(read_hphi_run(run)),result)
                    manifest=json.loads((run/'manifest.json').read_text());self.assertEqual(manifest['format'],row['native_manifest_format'])
                    self.assertIn(manifest['schema_version'],row['native_schema_versions']);self.assertEqual(result['format'],row['result_format'])
                    formulation=inventory['formulations']['axis_connected' if axis else 'positive_radius']
                    self.assertEqual(result['excluded_nullspace']['dimension'],formulation['excluded_static_modes'])
                    self.assertEqual(result['modes'][0]['vacc_v'] is not None,axis)
                    p=HphiProject(case);self.assertEqual(p.to_dict()['format'],inventory['project']['format'])
                    for parameter in inventory['study']['common_parameters']:
                        study=HphiStudy(p,parameter,[1,2]);self.assertEqual(study.to_dict()['format'],inventory['study']['format'])
                        self.assertEqual(study.to_dict()['kind'],inventory['study']['kind'])
                    if not row['same_domain_comparison']:
                        self.assertNotIn(raw['format'],inventory['comparison']['case_formats'])
                        with self.assertRaisesRegex(ValueError,'curved Hphi'):hphi_field_grams(solution,solution)
                    invalid=case.to_dict();invalid['model']['material']='dielectric'
                    with self.assertRaises(ValueError):hphi_case_from_dict(invalid)
        history=HphiTrackingHistoryRequest(1).to_dict();self.assertEqual(history['format'],inventory['comparison']['history']['format'])
        self.assertEqual(history['history_version'],inventory['comparison']['history']['version'])

    def test_all_advertised_planar_mapping_versions_are_strictly_readable(self):
        inventory=capabilities()['planar_cutoff'];identity=((1.,0.),(0.,1.))
        mappings=['normalized_rectangle',PolygonScaleMapping(1.),PolygonSimilarityMapping(1.,0.,(0.,0.)),PolygonRemeshMapping(),
            PolygonSimilarityRemeshMapping(1.,0.,(0.,0.)),PolygonAffineRemeshMapping(identity),PolygonExactAffineRemeshMapping(identity)]
        rows=inventory['tracking_mappings'];self.assertEqual(len(rows),len(mappings))
        for row,mapping in zip(rows,mappings):
            request=PlanarTrackingRequest(mapping=mapping);raw=request.to_dict()
            self.assertEqual(raw['tracking_version'],row['version']);self.assertIn(row['version'],inventory['tracking_versions'])
            self.assertEqual(raw['mapping'] if isinstance(raw['mapping'],str) else raw['mapping']['name'],row['name'])
            self.assertEqual(PlanarTrackingRequest.from_dict(raw).to_dict(),raw)
        raw['tracking_version']=8
        with self.assertRaises(ValueError):PlanarTrackingRequest.from_dict(raw)

    def test_cli_inventory_matches_api_and_commands_are_real(self):
        expected=capabilities();out=io.StringIO()
        with contextlib.redirect_stdout(out):self.assertEqual(main(['capabilities']),0)
        self.assertEqual(json.loads(out.getvalue()),expected)
        for command in sorted(set(commands(expected))):
            with self.subTest(command=command),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:main([command,'--help'])
                self.assertEqual(exc.exception.code,0)
        expected['hphi_rf']['case_families'].clear();self.assertEqual(len(capabilities()['hphi_rf']['case_families']),4)
        self.assertEqual(capabilities()['supported_models'],[Model().to_dict(),Model(polarization='te').to_dict()])

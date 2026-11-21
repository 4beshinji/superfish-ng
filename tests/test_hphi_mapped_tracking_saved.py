# SPDX-License-Identifier: Apache-2.0
"""Owned nonuniform Hphi pair requests for recovered-history ancestry."""
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
import numpy as np
from superfish_ng.coaxial import CoaxialCase, solve_coaxial
from superfish_ng.constants import C0
from superfish_ng.hphi_native import save_hphi_run
from superfish_ng.hphi_field_overlap import _declared_mesh
from superfish_ng.hphi_geometry_mapping import coaxial_dimension_mapping
from superfish_ng.hphi_tracking import HphiTrackingRequest, track_hphi_modes, track_mapped_hphi_modes
from superfish_ng.hphi_tuning import _refine_mesh
from superfish_ng.hphi_tracking_jobs import execute_hphi_tracking, read_hphi_tracking


class HphiMappedTrackingSavedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=solve_coaxial(CoaxialCase(.0625,.125,.5,nr=2,nz=8,modes=3,quadrature_order=12))
        cls.b=solve_coaxial(CoaxialCase(.078125,.15625,.75,nr=3,nz=8,modes=3,quadrature_order=12))
        for s in (cls.a,cls.b):
            np.testing.assert_allclose(s.frequencies_hz[:2],np.arange(1,3)*C0/(2*s.case.length_m),rtol=3e-4)
        cls.base=HphiTrackingRequest(_refine_mesh(_declared_mesh(cls.a)),_refine_mesh(_declared_mesh(cls.b)))
        cls.mapping=coaxial_dimension_mapping(cls.a.case,cls.b.case)
        cls.raw={**cls.base.to_dict(),'tracking_version':2,'mapping':cls.mapping.to_dict(),
                 'transport':'unitary_fixed_cylindrical_components'}

    def test_strict_versioned_mapping_request_and_single_source_of_transport(self):
        request=HphiTrackingRequest.from_dict(self.raw)
        self.assertEqual(request.to_dict(),self.raw)
        self.assertEqual(self.base.to_dict()['tracking_version'],1)
        self.assertNotIn('geometry_mapping',self.base.to_dict())
        for change in ({'tracking_version':True},{'transport':'covariant'},{'mapping':'same_vacuum'},
                       {'geometry_mapping':self.mapping.to_dict()}):
            with self.assertRaises(ValueError):HphiTrackingRequest.from_dict({**self.raw,**change})
        with self.assertRaises(ValueError):track_mapped_hphi_modes(self.a,self.b,request,self.mapping)
        from superfish_ng.hphi_identity_recovery import HphiIdentityRecoveryRequest
        with self.assertRaises(ValueError):HphiIdentityRecoveryRequest(0,request)
        declared=track_hphi_modes(self.a,self.b,request)
        explicit=track_mapped_hphi_modes(self.a,self.b,self.base,self.mapping)
        self.assertEqual(declared,explicit)
        self.assertEqual(declared['current_mode_ids'],['mode-1','mode-2'])

    def test_saved_cli_replay_owns_native_after_source_move(self):
        from superfish_ng.cli import main
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);request=HphiTrackingRequest.from_dict(self.raw)
            for name,solution in (('a',self.a),('b',self.b)):
                save_hphi_run(solution.case,solution,root/name)
            request.save(root/'request.json')
            with redirect_stdout(io.StringIO()):
                code=main(['execute-hphi-tracking',str(root/'a'),str(root/'b'),str(root/'request.json'),'--out',str(root/'pair')])
            self.assertEqual(code,0)
            result=read_hphi_tracking(root/'pair')
            self.assertEqual(result['status'],'PASS')
            for name,side in (('a','previous'),('b','current')):
                for file in ('case.json','fields.npz','mesh.npz','results.json','manifest.json'):
                    self.assertEqual((root/name/file).read_bytes(),(root/'pair'/side/'solution'/file).read_bytes())
                (root/name).rename(root/(name+'-moved'))
            with redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(main(['replay-hphi-tracking',str(root/'pair')]),0)
            self.assertEqual(json.loads(stream.getvalue()),result)
            path=root/'pair'/'tracking.json';original=path.read_bytes()
            changed=json.loads(original);changed['transport']='covariant';path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):read_hphi_tracking(root/'pair')
            path.write_bytes(original)
            self.assertEqual(read_hphi_tracking(root/'pair'),result)

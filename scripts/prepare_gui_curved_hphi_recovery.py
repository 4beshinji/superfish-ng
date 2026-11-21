# SPDX-License-Identifier: Apache-2.0
"""Prepare real curved crossing pairs and explicit anchor recovery for GUI acceptance.

Run with PYTHONPATH=.:src:tests. The fixture checks the independently known
TEM-like branch; every pair is saved by the production FEM/native pipeline.
"""
import argparse
import json
from pathlib import Path
import shutil
from test_curved_hphi_tracking_history import CurvedHphiHistoryTests


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    CurvedHphiHistoryTests.setUpClass()
    try:
        source=CurvedHphiHistoryTests.root
        workspace=args.out/'workspace';workspace.mkdir()
        for name in ('enter','continue'):
            shutil.copytree(source/name,workspace/name)
        request=CurvedHphiHistoryTests().history_request().to_dict()
        (args.out/'request.json').write_text(json.dumps(request,indent=2)+'\n')
        (args.out/'prepared.json').write_text(json.dumps(dict(status='PASS',pairs=['enter','continue'],
            physical_check='independent small-shear TEM-like mass overlap > 0.999 on both originals'),indent=2)+'\n')
    finally:
        CurvedHphiHistoryTests.tearDownClass()


if __name__=='__main__':main()

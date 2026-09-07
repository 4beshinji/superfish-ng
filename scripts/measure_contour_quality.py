#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measure bounded contour quality generation, including expected failures."""
import argparse
import json
import time
from pathlib import Path
from superfish_ng import Case
from superfish_ng.contour import Contour
from superfish_ng.contour_mesh import quality_contour_mesh, contour_mesh_quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    rows = []
    for width in (.5,.05,.01,1e-5):
        case = Case((),contour=Contour(((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),(2,width),(0,width)),
                                      ('axis',)+('pec',)*7))
        start = time.perf_counter()
        row = dict(width_m=width,max_edge_m=.25,min_angle_deg=10.,max_triangles=4000,max_rounds=8)
        try:
            mesh = quality_contour_mesh(case,.25,max_triangles=4000,max_rounds=8)
            row.update(status='PASS',quality=contour_mesh_quality(mesh))
        except ValueError as error:
            row.update(status='FAIL',error=str(error))
        row['seconds'] = time.perf_counter()-start
        rows.append(row)
        print(json.dumps(row),flush=True)
    (args.out/'quality.json').write_text(json.dumps(dict(scope='geometry only; no RF validation',cases=rows),indent=2)+'\n')


if __name__ == '__main__':
    main()

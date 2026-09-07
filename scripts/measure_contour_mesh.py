#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measure initial/refined contour geometry; this is not RF validation."""
import argparse
import json
import time
import tracemalloc
from pathlib import Path

from superfish_ng import Case
from superfish_ng.contour import Contour
from superfish_ng.contour_mesh import triangulate_contour, refine_contour, contour_mesh_quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    rows = []
    for width in (.5,.01,.00001):
        contour = Contour(((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),(2,width),(0,width)),
                          ('axis',)+('pec',)*7)
        case = Case((),contour=contour)
        for edge_size in (.25,.125):
            tracemalloc.start()
            start = time.perf_counter()
            initial = triangulate_contour(case)
            mesh = refine_contour(case,initial,edge_size)
            seconds = time.perf_counter()-start
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            rows.append(dict(channel_width_m=width, requested_max_edge_m=edge_size,
                             initial=contour_mesh_quality(initial), refined=contour_mesh_quality(mesh),
                             elapsed_seconds=seconds, python_traced_peak_bytes=peak))
    report = dict(scope='geometric measurements only; no RF accuracy or minimum-angle acceptance',
                  memory_scope='tracemalloc peak, not process RSS or all native allocations', measurements=rows)
    (args.out/'measurements.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()

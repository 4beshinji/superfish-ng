# SPDX-License-Identifier: Apache-2.0
"""Compare independently refined Wine/NG surface fields and boundary spacing."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from compare_superfish import NUMBER
from evaluate_surface_fields import probe_surface, write_json
from superfish_ng import Case
from superfish_ng.geometry import arc_geometry


def boundary_edges(path):
    """Read the numerical Region 1 boundary sequence printed by Automesh."""
    text = path.read_text(encoding='latin-1')
    block = text.split('Region 1 mesh points', 1)[1].split('Region 1 done', 1)[0]
    rows = re.findall(r'^\s*\d+\s+\d+\s+('+NUMBER+r')\s+('+NUMBER+r')\s*$', block, re.M)
    points = np.array([[float(z.replace('D', 'E'))/100, float(r.replace('D', 'E'))/100]
                       for z, r in rows])[:, ::-1]
    if len(points) < 4 or not np.isfinite(points).all() or not np.allclose(points[0], points[-1], atol=1e-10, rtol=0):
        raise ValueError('Automesh boundary must be a finite, closed coordinate sequence')
    edges = np.stack((points[:-1], points[1:]), axis=1)
    if np.any(np.linalg.norm(edges[:, 1]-edges[:, 0], axis=1) <= 0):
        raise ValueError('Automesh boundary contains a zero length edge')
    return edges


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wine-report', type=Path, required=True)
    parser.add_argument('--ng-report', type=Path, required=True)
    parser.add_argument('--ng-inset-report', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    sf = json.loads(args.wine_report.read_text())
    ng = json.loads(args.ng_report.read_text())
    inset_ng = json.loads(args.ng_inset_report.read_text())
    if sf['status'] != 'COMPUTED_NO_AUTOMATIC_ACCURACY_RANKING':
        parser.error('Wine run is incomplete')
    if sf['ng_report_sha256'] != hashlib.sha256(args.ng_report.read_bytes()).hexdigest():
        parser.error('NG report does not match the Wine comparison input')
    if sf['ng_inset_report_sha256'] != hashlib.sha256(args.ng_inset_report.read_bytes()).hexdigest():
        parser.error('NG inset report does not match the Wine comparison input')
    for name in ['sharp', 'rounded']:
        for row in sf[name]:
            folder = Path(row.get('source_directory', args.wine_report.parent/f'{name}-dx{row["dx_cm"]:g}'))
            for filename, expected in row['sha256'].items():
                if hashlib.sha256((folder/filename).read_bytes()).hexdigest() != expected:
                    parser.error(f'reference file changed: {folder/filename}')
    args.out.mkdir(parents=True, exist_ok=False)
    result = {'wine_report_sha256': hashlib.sha256(args.wine_report.read_bytes()).hexdigest(),
              'status': 'DIAGNOSTIC_COMPARISON_NOT_AN_ERROR_BOUND',
              'surface_mesh_note': 'Wine printed boundary edge lengths only; interior cell diameters unavailable.',
              'probe_note': 'Fixed wall distances; offsets 0.1 and 1 um inside vacuum. Maxima cover both offsets.',
              'sharp': [], 'ng_sharp_spacing': {}, 'fixed_distance': {}, 'rounded': []}
    for series in ['sharp_diagonal', 'sharp_crossed']:
        result['ng_sharp_spacing'][series] = []
        for row in ng['runs'][series]:
            with np.load(args.ng_report.parent/f'{series}-{row["nr"]}/surface.npz') as saved:
                ends, fields, h = (saved[k] for k in ['endpoints_rz_m', 'electric_er_ez_v_per_m', 'owner_cell_diameter_m'])
                left = probe_surface(ends, fields, h, [.045, .025])
                right = probe_surface(ends, fields, h, [.045, .155])
            result['ng_sharp_spacing'][series].append({'nr': row['nr'], 'left_neck': left, 'right_neck': right,
                'corner_peak_mirror_difference_percent': 100*abs(right['e_max_v_per_m']/left['e_max_v_per_m']-1)})
    for row in sf['sharp']:
        folder = Path(row.get('source_directory', args.wine_report.parent/f'sharp-dx{row["dx_cm"]:g}'))
        edges = boundary_edges(folder/'OUTAUT.TXT')
        h = np.linalg.norm(edges[:, 1]-edges[:, 0], axis=1)
        # Use only the geometric part of the one-sided surface query. Printed
        # Automesh coordinates have finite precision; horizontal neck exact.
        local = probe_surface(edges, np.zeros_like(edges), h, [.045, .025])
        result['sharp'].append({'dx_cm': row['dx_cm'], 'quantities': row['sf']['quantities'],
                                'neck_incident_boundary_edge_max_m': local['edge_h_max_m']})
    for distance in [.0005, .001, .002, .004, .008]:
        previous = [p for p in sf['sharp'][-2]['probes'] if p['distance_m'] == distance and p['corner_index'] in [1, 4]]
        finest = [p for p in sf['sharp'][-1]['probes'] if p['distance_m'] == distance and p['corner_index'] in [1, 4]]
        result['fixed_distance'][str(distance)] = {
            'wine_last_change_percent': max(100*abs(b['e_v_per_m']/a['e_v_per_m']-1) for a, b in zip(previous, finest)),
            'ng_vs_wine_max_difference_percent': {series: max(100*p['ng_comparisons'][series]['relative_difference'] for p in finest)
                                                for series in ['sharp_diagonal', 'sharp_crossed']}}
        item = result['fixed_distance'][str(distance)]
        item['ng_last_change_percent'] = {}
        for series in ['sharp_diagonal', 'sharp_crossed']:
            a, b = inset_ng['runs'][series][-2:]
            item['ng_last_change_percent'][series] = max(100*abs(q['e_v_per_m']/p['e_v_per_m']-1)
                for p, q in zip(a['probes'], b['probes']) if p['distance_m'] == distance and p['corner_index'] in [1, 4])
        near = [p for p in finest if p['inset_m'] == 1e-7]
        far = [p for p in finest if p['inset_m'] == 1e-6]
        item['wine_offset_change_percent'] = max(100*abs(b['e_v_per_m']/a['e_v_per_m']-1) for a, b in zip(near, far))
    qng = ng['runs']['rounded-chord-2.5e-07'][-1]['quantities']
    arc_case = Case.load(args.ng_report.parent/'fillets-2.5e-07.json')
    for row in sf['rounded']:
        q = row['sf']['quantities']
        folder = Path(row.get('source_directory', args.wine_report.parent/f'rounded-dx{row["dx_cm"]:g}'))
        points = boundary_edges(folder/'OUTAUT.TXT')[:, 0, ::-1]
        circles = []
        for index, radius, direction in arc_case.arcs:
            start, end = arc_case.profile[index-1:index+1]
            center, _, _ = arc_geometry(start, end, radius, direction)
            arc_points = points[(points[:, 0] >= start[0]-1e-9) & (points[:, 0] <= end[0]+1e-9) & (points[:, 1] > .01)]
            if len(arc_points) < 2:
                raise ValueError('Automesh arc boundary endpoints missing')
            error = float(np.max(np.abs(np.linalg.norm(arc_points-center, axis=1)-radius)))
            if error > 1e-9:
                raise ValueError('Automesh boundary does not follow the specified tangent circle')
            circles.append({'end_index': index, 'boundary_points': len(arc_points), 'maximum_radius_error_m': error})
        result['rounded'].append({'dx_cm': row['dx_cm'], 'quantities': q,
                                  'circle_checks': circles,
                                  'ng_vs_wine_percent': {key: 100*abs(qng[key]/q[key]-1)
                                                        for key in ['frequency_hz', 'r_over_q_accelerator_ohm', 'epk_over_eacc_estimate']}})
    write_json(args.out/'summary.json', result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), constrained_layout=True)
    for series in ['sharp_diagonal', 'sharp_crossed']:
        rows = ng['runs'][series]
        axes[0].plot([1000*r['left_neck']['edge_h_max_m'] for r in result['ng_sharp_spacing'][series][1:]],
                     [r['quantities']['epk_over_eacc_estimate'] for r in rows[1:]], 'o-', label='NG '+series.split('_')[1])
    axes[0].plot([1000*r['neck_incident_boundary_edge_max_m'] for r in result['sharp']],
                 [r['quantities']['epk_over_eacc_estimate'] for r in result['sharp']], 's-', label='Wine SFO')
    axes[0].set(xscale='log', xlabel='Max incident boundary edge at left neck [mm]', ylabel='Epk / Eacc', title='Sharp geometry: mesh-dependent peaks')
    axes[0].invert_xaxis()
    distances = [float(d)*1000 for d in result['fixed_distance']]
    axes[1].plot(distances, [r['wine_last_change_percent'] for r in result['fixed_distance'].values()], 's-', label='Wine last mesh change')
    for series in ['sharp_diagonal', 'sharp_crossed']:
        axes[1].plot(distances, [r['ng_vs_wine_max_difference_percent'][series] for r in result['fixed_distance'].values()],
                     'o-', label=series+' vs Wine')
    axes[1].set(xscale='log', yscale='log', xlabel='Fixed wall distance from neck corner [mm]', ylabel='Maximum over four points x two offsets [%]', title='Vacuum-side fields at U=1 J')
    axes[2].plot([r['dx_cm']*10 for r in result['rounded']], [r['quantities']['epk_over_eacc_estimate'] for r in result['rounded']], 's-', label='Wine, exact arc input')
    axes[2].axhline(qng['epk_over_eacc_estimate'], label='NG nr=192, chord 0.25 um', linestyle='--')
    axes[2].set(xscale='log', xlabel='Wine DX [mm] (not NG mesh size)', ylabel='Epk / Eacc', title='Tangent 3 mm fillet control')
    axes[2].invert_xaxis()
    from matplotlib.ticker import NullFormatter
    for axis, ticks in zip(axes, [[.25, .5, 1, 2, 4], [.5, 1, 2, 4, 8], [.25, .5, 1, 2]]):
        axis.set_xticks(ticks, [f'{value:g}' for value in ticks])
        axis.xaxis.set_minor_formatter(NullFormatter())
    for axis in axes:
        axis.grid(True, alpha=.3)
        axis.legend(fontsize=7)
    fig.savefig(args.out/'wine_ng_surface.png', dpi=180)
    fig.savefig(args.out/'wine_ng_surface.pdf')
    plt.close(fig)


if __name__ == '__main__':
    main()

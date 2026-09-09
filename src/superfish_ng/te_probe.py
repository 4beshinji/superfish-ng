# SPDX-License-Identifier: Apache-2.0
"""SI radial probes of verified TE fields, with native source identity."""
import json
from pathlib import Path
import numpy as np
from .completion import digest
from .constants import MU0
from .sampling import solution_radial_extent
from .te import TEFieldSampler, te_quantities
from .te_saved import read_te_run, _names, _conventions


def export_te_radial_probe(directory, out, z_m, mode=1):
    directory, out = Path(directory), Path(out)
    metadata_path = out.with_suffix(out.suffix+'.json')
    if out.exists() or metadata_path.exists():
        raise FileExistsError(f'probe output already exists: {out}')
    from .config import Case
    case = Case.load(directory/"case.json")
    names = _names(case) | {"te_complete.json"}
    sources = {name: digest(directory/name) for name in sorted(names)}
    saved = read_te_run(directory)
    if type(mode) is not int or not 1 <= mode <= saved.case.modes:
        raise ValueError('probe mode must be a valid one-based integer')
    if type(z_m) not in (int, float) or not np.isfinite(z_m):
        raise ValueError('probe z must be finite metres')
    radius = solution_radial_extent(saved, z_m)
    positions = np.column_stack((np.linspace(0, radius, 401), np.full(401, z_m)))
    fields = TEFieldSampler(saved).evaluate(positions, mode-1, outside='nan')
    hr, hz = fields['Hr_quadrature_A_per_m'], fields['Hz_quadrature_A_per_m']
    columns = np.column_stack((positions, fields['Ephi_V_per_m'], hr, hz,
                               MU0*hr, MU0*hz, fields['inside'].astype(int)))
    header = 'r_m,z_m,Ephi_V_per_m,Hr_quadrature_A_per_m,Hz_quadrature_A_per_m,Br_quadrature_T,Bz_quadrature_T,inside'
    metadata = dict(physics='axisymmetric_m0_te', mode_index=mode,
                    frequency_hz=float(saved.frequencies_hz[mode-1]), z_m=z_m,
                    samples=len(positions), native_source_sha256=sources,
                    stored_energy_j=te_quantities(saved, mode-1)['stored_energy_j'],
                    normalization_j=saved.case.normalization_j,
                    conventions=_conventions(saved.case.geometry_order==2),
                    outside_policy='NaN fields with inside=0 in radial gaps',
                    outside_samples=int(np.count_nonzero(~fields['inside'])))
    if any((directory/name).is_symlink() or digest(directory/name) != value for name,value in sources.items()):
        raise ValueError('TE probe source changed during sampling')
    with out.open('x', encoding='utf-8') as stream:
        np.savetxt(stream, columns, delimiter=',', header=header, comments='')
    with metadata_path.open('x', encoding='utf-8') as stream:
        json.dump(metadata, stream, indent=2, allow_nan=False)
    return metadata

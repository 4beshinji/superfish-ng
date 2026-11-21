#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Supplement an observed full physical bridge with all-mode wall/byte checks.

Load only bytes already bound to a successful geometry/K/M/spectrum/RF replay.
Do not create a solver state or invent algebraic diagnostics. Invoke the public
field methods on those verified raw arrays and the same validated native case.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.project import parse_json
from superfish_ng.planar_curved import PlanarCurvedCase, PlanarCurvedSpace
from superfish_ng.planar_curved_geometry import immutable_array
from superfish_ng.planar_curved_solver import PlanarCurvedSolution
from extend_planar_curved_shapes import artifact_hashes
from validate_planar_curved_source_bridge import sampled_original_fields


class _VerifiedRawFieldFrame:
    """Public field arithmetic over previously physically verified raw only."""
    scalar_at_reference = PlanarCurvedSolution.scalar_at_reference
    fields_at_reference = PlanarCurvedSolution.fields_at_reference
    all_fields_at_reference = PlanarCurvedSolution.all_fields_at_reference

    def __init__(self, case, coefficients, frequencies):
        self.case = case
        free = np.arange(len(case.domain.points_xy_m))
        if case.polarization == 'tm':
            free = np.setdiff1d(free, np.unique(case.domain.boundary_nodes))
        self.space = PlanarCurvedSpace(case.domain, immutable_array(free, np.int64))
        self.coefficients = immutable_array(coefficients, float)
        self.frequencies_hz = immutable_array(frequencies, float)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('from-bridge', 'saved-solution', 'archived-validators', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    before, started = _implementation_hashes(), time.monotonic()
    report = parse_json((args.from_bridge/'report.json').read_text())
    terminal = parse_json(args.from_bridge.with_name(args.from_bridge.name+'-observed-termination.json').read_text())
    if not report['passed'] or (terminal['terminal'], terminal['observed_exit_code']) != (True, 0) or Path(terminal['original_evidence']).resolve() != args.from_bridge.resolve():
        raise ValueError('an actually observed successful full physical bridge is mandatory')
    if before != parse_json((args.from_bridge/'implementation-before.json').read_text()) or before != parse_json((args.from_bridge/'implementation-after.json').read_text()):
        raise ValueError('supplemental fields require the identical physically verified 401-product kernel')
    bridge_hashes = artifact_hashes(args.from_bridge)
    if bridge_hashes != parse_json(args.from_bridge.with_name(args.from_bridge.name+'-accepted-artifact-hashes.json').read_text()):
        raise ValueError('complete physically accepted bridge artifacts changed')
    archives = parse_json(args.archived_validators.read_text())
    for name, digest in parse_json((args.from_bridge/'validator-hashes.json').read_text()).items():
        preserved = archives[name]
        if preserved['sha256'] != digest or hashlib.sha256(Path(preserved['preserved_file']).read_bytes()).hexdigest() != digest:
            raise ValueError('complete original physical bridge validator source must remain archived exactly')
    snapshots = parse_json((args.from_bridge/'original-artifact-hashes.json').read_text())
    matches = [h for name, h in snapshots.items() if Path(name).resolve() == args.saved_solution.resolve()]
    if len(matches) != 1 or artifact_hashes(args.saved_solution) != matches[0] or args.saved_solution.name != report['label']:
        raise ValueError('saved original field bytes must be bound to the accepted full physical replay')
    code = {str(q): hashlib.sha256(q.read_bytes()).hexdigest() for q in
        (Path(__file__), Path(__file__).with_name('validate_planar_curved_source_bridge.py'),
         Path(__file__).with_name('planar_curved_vector_reference.py'), Path(__file__).with_name('extend_planar_curved_shapes.py'))}
    args.out.mkdir(parents=True, exist_ok=False)
    write = lambda name, value: (args.out/(name+'.json')).write_text(json.dumps(value, indent=2)+'\n')
    write('implementation-before', before);write('validator-hashes', code)
    write('preserved-bridge-artifacts', bridge_hashes);write('preserved-original-field-artifacts', matches[0])
    try:
        print('loading original verified native geometry and arrays; no matrix/eigenpair/energy rerun', flush=True)
        case = PlanarCurvedCase.from_dict(parse_json((args.saved_solution/'case.json').read_text()))
        if case.polarization != report['polarization']:
            raise ValueError('original verified polarization differs')
        with np.load(args.saved_solution/'fem-fields.npz', allow_pickle=False) as raw:
            frame = _VerifiedRawFieldFrame(case, raw['coefficients'], raw['frequencies_hz'])
            array_hashes = {}
            for name, actual in [('coefficients', frame.coefficients), ('frequencies_hz', frame.frequencies_hz)]:
                if actual.dtype != raw[name].dtype or actual.tobytes() != raw[name].tobytes():
                    raise ValueError('verified original raw copy must preserve all bytes, including signed zero')
                array_hashes[name] = hashlib.sha256(actual.tobytes()).hexdigest()
        probes = sampled_original_fields(frame)
        after = _implementation_hashes()
        if after != before or artifact_hashes(args.from_bridge) != bridge_hashes or artifact_hashes(args.saved_solution) != matches[0] or any(hashlib.sha256(Path(q).read_bytes()).hexdigest() != h for q, h in code.items()):
            raise ValueError('fixed kernel/code or verified bridge/raw changed during supplemental check')
        result = dict(passed=True, shape=report['shape'], polarization=case.polarization, scale=report['scale'],
            label=report['label'], parent_full_physical_bridge=str(args.from_bridge),
            new_FEM_solves=0, repeated_physical_restores=0, repeated_matrices_or_spectrum=0,
            repeated_independent_energy_wall_integrals=0, original_array_byte_hashes=array_hashes,
            signed_original_field_probes=probes, product_files_fixed=len(after),
            elapsed_s=time.monotonic()-started, P07_complete=False,
            scope='supplemental all-positive-mode canonical PEC trace and signed-zero byte checks over already physically verified native raw')
        write('implementation-after', after);write('report', result);print(json.dumps(result, indent=2), flush=True)
    except Exception as exc:
        write('failed-evidence', dict(error=repr(exc), new_FEM_solves=0, elapsed_s=time.monotonic()-started));raise


if __name__ == '__main__':
    main()

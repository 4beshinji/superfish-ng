# SPDX-License-Identifier: Apache-2.0
"""Completion and byte-integrity checks for saved solution directories."""
import hashlib
import json
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def required_files(case, results):
    names = {'save_protocol.json', 'case.json', 'results.json', 'fields.npz', 'modes.csv'}
    names.update(f'{prefix}_{i:03d}.{suffix}' for i in range(1, case.modes+1)
                 for prefix, suffix in [('axis', 'csv'), ('mode', 'vtk')])
    if 'input_sha256' in results['mesh']:
        names.add('mesh.json')
    return names


def verify_completion(directory, case, results):
    directory = Path(directory)
    protocol, complete = directory/'save_protocol.json', directory/'save_complete.json'
    if not (protocol.exists() or complete.exists() or 'save_protocol_version' in results):
        return  # Historical format retains the caller's structural checks.
    if not protocol.is_file() or not complete.is_file():
        raise ValueError('incomplete saved result: missing save protocol or completion marker')
    if protocol.is_symlink() or complete.is_symlink():
        raise ValueError('invalid linked save protocol or completion marker')
    declaration = json.loads(protocol.read_text())
    manifest = json.loads(complete.read_text())
    if (not isinstance(declaration, dict) or set(declaration) != {'version'}
            or type(declaration['version']) is not int or declaration['version'] != 1
            or type(results.get('save_protocol_version')) is not int or results['save_protocol_version'] != 1
            or not isinstance(manifest, dict) or set(manifest) != {'completion_version', 'files'}
            or type(manifest['completion_version']) is not int or manifest['completion_version'] != 1):
        raise ValueError('unsupported or invalid save completion protocol')
    files = manifest['files']
    if not isinstance(files, dict) or set(files) != required_files(case, results):
        raise ValueError('save completion manifest does not contain exactly the required output files')
    for name, expected in files.items():
        path = directory/name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError(f'saved output bytes disagree with completion manifest: {name}')

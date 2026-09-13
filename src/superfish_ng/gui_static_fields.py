# SPDX-License-Identifier: Apache-2.0
"""Strict static Project editing and asynchronous original-FEM field display."""
import copy
from dataclasses import replace
from pathlib import Path
import threading

from .config import keys
from .static_field_project import load_static_document, StaticFieldProject, static_case_families
from .static_field_jobs import KIND, _bindings, _job_hashes, _report_bytes, _sha, read_static_field_job

ACTIONS = {
    'static-project-validate': ['document', 'display_length_unit'],
    'static-project-download': ['document', 'display_length_unit'],
    'static-project-solve': ['document', 'display_length_unit'],
    'static-field-jobs': [],
    'static-field-result': ['id'],
    'static-field-download': ['id', 'file'],
}
FIELD_UNITS = {
    'potential_V': 'V', 'Ex_V_per_m': 'V/m', 'Ey_V_per_m': 'V/m', 'Er_V_per_m': 'V/m', 'Ez_V_per_m': 'V/m',
    'Dx_C_per_m2': 'C/m²', 'Dy_C_per_m2': 'C/m²', 'Dr_C_per_m2': 'C/m²', 'Dz_C_per_m2': 'C/m²',
    'Az_Wb_per_m': 'Wb/m', 'Aphi_Wb_per_m': 'Wb/m', 'Aphi_over_r_T': 'T', 'psi_Wb': 'Wb',
    'Bx_T': 'T', 'By_T': 'T', 'Br_T': 'T', 'Bz_T': 'T',
    'Hx_A_per_m': 'A/m', 'Hy_A_per_m': 'A/m', 'Hr_A_per_m': 'A/m', 'Hz_A_per_m': 'A/m',
}


def _project(data):
    if type(data['document']) is not str:
        raise ValueError('static Project editor requires JSON text; duplicate keys must remain detectable')
    project = load_static_document(data['document'])
    unit = data['display_length_unit']
    if unit is not None:
        project = replace(project, display_length_unit=unit)
    return project


def static_field_view(directory):
    directory = Path(directory)
    result = read_static_field_job(directory)
    project = StaticFieldProject.from_dict(result['project'])
    family = next(row for row in static_case_families() if row['case_format'] == project.case.to_dict()['format'])
    planar = family['coordinates'] == 'cartesian_xy'
    plot = None
    if result['status'] == 'complete':
        name, _, saved = _bindings(project.case)
        solution = getattr(saved, 'read_' + name + '_run')(directory / 'solution')
        mesh = project.case.partition.mesh
        points = mesh.points_xy_m if planar else mesh.points_rz_m
        centers = points[mesh.triangles].mean(axis=1)
        probe = solution.probe_at(centers)
        if probe['cell_indices'] != list(range(len(mesh.triangles))):
            raise ValueError('static display samples must retain their original material cells')
        if set(probe['fields']) - FIELD_UNITS.keys():
            raise ValueError('static display encountered a field without an explicit SI unit')
        plot = dict(points_m=points.tolist(), triangles=mesh.triangles.tolist(),
                    boundary_edges=mesh.boundary_edges.tolist(), coordinate_labels=['x', 'y'] if planar else ['r', 'z'],
                    cell_center_probe=probe, field_units={n: FIELD_UNITS[n] for n in probe['fields']},
                    interpretation='Original one-sided FEM values at each material cell center. Each display triangle has one constant color; this is a display sample, not a smoothed field, contour solution or extremum bound.')
    return dict(project=result['project'], outcome=result['outcome'], solver_status=result['status'], family=family,
                measure='per_unit_length' if planar else 'full_axisymmetric_domain', plot=plot,
                not_applicable=['RF frequency', 'R/Q (circuit)', 'R/Q (accelerator)', 'RF mode index'])


class StaticFieldAccess:
    """Replay off the HTTP thread and reject changed files before every read."""
    def __init__(self, manager):
        self.manager = manager
        self.lock = threading.RLock()
        self.entries = {}
        self.closed = False

    def close(self):
        with self.lock:
            self.closed = True
            self.entries.clear()

    def _verify(self, identifier, directory, entry):
        try:
            view = static_field_view(directory)
            if _job_hashes(directory, entry['failed']) != entry['hashes']:
                raise ValueError('static job changed during original-field display verification')
            result = dict(status='ready', id=identifier, view=view,
                          files=sorted(n for n in entry['hashes'] if n not in ('job.json', 'manifest.json')))
        except Exception as exc:
            result = dict(status='failed', id=identifier, error=str(exc))
        with self.lock:
            if not self.closed and not self.manager.closed and self.entries.get(identifier) is entry:
                entry['result'] = result

    def result(self, identifier):
        if self.closed or self.manager.closed:
            raise ValueError('static field access is closed')
        state = self.manager.status(identifier)
        if state.get('kind') != KIND:
            raise ValueError('select a dedicated static Project job')
        if state['status'] != 'complete' and not (state['status'] == 'failed' and state.get('outcome_saved') is True):
            return dict(status=state['status'], id=identifier, state=state)
        directory = self.manager.directory(identifier)
        failed = state.get('solver_status') == 'nonlinear_failed'
        hashes = _job_hashes(directory, failed)
        with self.lock:
            entry = self.entries.get(identifier)
            if entry is not None:
                if entry['hashes'] != hashes:
                    raise ValueError('static job changed after display verification; select an unchanged saved run')
                return copy.deepcopy(entry['result'])
            entry = dict(hashes=hashes, failed=failed, result=dict(status='verifying', id=identifier))
            self.entries[identifier] = entry
            threading.Thread(target=self._verify, args=(identifier, directory, entry), daemon=True,
                             name='static-field-verification').start()
            return dict(status='verifying', id=identifier)

    def download(self, identifier, name):
        if type(name) is not str:
            raise ValueError('static download requires a listed file name')
        result = self.result(identifier)
        if result['status'] != 'ready':
            raise ValueError('wait for original static FEM verification before downloading')
        if name not in result['files']:
            raise ValueError('select a listed Project or original native file')
        with self.lock:
            entry = self.entries[identifier]
        directory = self.manager.directory(identifier)
        raw = _report_bytes(directory / name)
        if _sha(raw) != entry['hashes'][name] or _job_hashes(directory, entry['failed']) != entry['hashes']:
            raise ValueError('static job changed during download')
        return raw


def static_field_response(manager, access, action, data):
    if action not in ACTIONS:
        raise ValueError('unknown static Project operation')
    fields = ACTIONS[action]
    keys(data, fields, fields, 'GUI static Project')
    if action.startswith('static-project-'):
        project = _project(data)
        if action == 'static-project-validate':
            return project.to_dict(), 'application/json'
        if action == 'static-project-download':
            return project.dumps().encode('utf-8'), 'application/json'
        return dict(id=manager.start_static_field(project)), 'application/json'
    if action == 'static-field-jobs':
        return [state for state in manager.list() if state.get('kind') == KIND], 'application/json'
    if action == 'static-field-result':
        return access.result(data['id']), 'application/json'
    raw = access.download(data['id'], data['file'])
    return raw, 'application/json' if data['file'].endswith('.json') else 'application/octet-stream'

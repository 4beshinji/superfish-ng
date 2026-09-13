# SPDX-License-Identifier: Apache-2.0
"""Static Study editing and asynchronous complete-study/selected-point display."""
import copy
from dataclasses import replace
import hashlib
import threading

from .config import keys
from .project import parse_json
from .static_field_study import load_static_study_document
from .static_field_study_jobs import KIND, _snapshot, read_static_field_study
from .static_field_jobs import _report_bytes
from .gui_static_fields import FIELD_UNITS, static_field_view

ACTIONS = {
    'static-study-validate': ['document', 'display_length_unit'],
    'static-study-download-input': ['document', 'display_length_unit'],
    'static-study-solve': ['document', 'display_length_unit'],
    'static-study-jobs': [],
    'static-study-result': ['id'],
    'static-study-point': ['id', 'index'],
    'static-study-download': ['id', 'file'],
}


def _study(data):
    if type(data['document']) is not str:
        raise ValueError('static Study editor requires JSON text; duplicate keys must remain detectable')
    study = load_static_study_document(data['document'])
    if data['display_length_unit'] is not None:
        study = replace(study, project=replace(study.project, display_length_unit=data['display_length_unit']))
    return study


def _files(hashes):
    return sorted(name for name in hashes if name not in ('job.json', 'manifest.json')
                  and not (len(name.split('/')) == 2 and name.rsplit('/', 1)[-1] in ('job.json', 'manifest.json')))


class StaticFieldStudyAccess:
    """Every point belongs to a fully replayed and still unchanged parent Study."""
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
            summary = read_static_field_study(directory)
            if _snapshot(directory, entry['count']) != entry['hashes']:
                raise ValueError('static Study changed during complete display verification')
            result = dict(status='ready', id=identifier, summary=summary, files=_files(entry['hashes']))
        except Exception as exc:
            result = dict(status='failed', id=identifier, error=str(exc))
        with self.lock:
            if not self.closed and not self.manager.closed and self.entries.get(identifier) is entry:
                entry['result'] = result

    def result(self, identifier):
        if self.closed or self.manager.closed:
            raise ValueError('static Study access is closed')
        state = self.manager.status(identifier)
        if state.get('kind') != KIND:
            raise ValueError('select a dedicated static Study job')
        if state['status'] != 'complete':
            return dict(status=state['status'], id=identifier, state=state)
        directory = self.manager.directory(identifier)
        with self.lock:
            entry = self.entries.get(identifier)
            if entry is not None:
                if _snapshot(directory, entry['count']) != entry['hashes']:
                    raise ValueError('static Study changed after display verification; select an unchanged saved Study')
                return copy.deepcopy(entry['result'])
            document = parse_json(_report_bytes(directory / 'study.json').decode('utf-8'))
            if not isinstance(document, dict) or type(document.get('values')) is not list or len(document['values']) < 2:
                raise ValueError('static Study display requires the complete requested values')
            count = len(document['values']); hashes = _snapshot(directory, count)
            entry = dict(count=count, hashes=hashes, points={}, result=dict(status='verifying', id=identifier))
            self.entries[identifier] = entry
            threading.Thread(target=self._verify, args=(identifier, directory, entry), daemon=True,
                             name='static-study-verification').start()
            return dict(status='verifying', id=identifier)

    def _verify_point(self, identifier, directory, index, entry, point_entry):
        try:
            point = entry['result']['summary']['points'][index]
            view = static_field_view(directory / point['directory'])
            if _snapshot(directory, entry['count']) != entry['hashes']:
                raise ValueError('static Study changed during selected-point display verification')
            prefix = point['directory'] + '/'
            result = dict(status='ready', id=identifier, index=index, point=point, view=view,
                          files=[name for name in _files(entry['hashes']) if name.startswith(prefix)])
        except Exception as exc:
            result = dict(status='failed', id=identifier, index=index, error=str(exc))
        with self.lock:
            if not self.closed and not self.manager.closed and self.entries.get(identifier) is entry:
                point_entry['result'] = result

    def point(self, identifier, index):
        if type(index) is not int or index < 0:
            raise ValueError('static Study point index must be a nonnegative integer')
        result = self.result(identifier)
        if result['status'] != 'ready': return result
        with self.lock:
            entry = self.entries[identifier]
            if index >= entry['count']: raise ValueError('select an existing static Study point index')
            point_entry = entry['points'].get(index)
            if point_entry is not None: return copy.deepcopy(point_entry['result'])
            point_entry = dict(result=dict(status='verifying', id=identifier, index=index))
            entry['points'][index] = point_entry
            threading.Thread(target=self._verify_point,
                             args=(identifier, self.manager.directory(identifier), index, entry, point_entry),
                             daemon=True, name='static-study-point-verification').start()
            return copy.deepcopy(point_entry['result'])

    def download(self, identifier, name):
        if type(name) is not str: raise ValueError('static Study download requires a listed file name')
        result = self.result(identifier)
        if result['status'] != 'ready': raise ValueError('wait for complete static Study FEM verification before downloading')
        if name not in result['files']: raise ValueError('select a listed Study, point Project or original native file')
        with self.lock: entry = self.entries[identifier]
        directory = self.manager.directory(identifier); raw = _report_bytes(directory / name)
        if hashlib.sha256(raw).hexdigest() != entry['hashes'][name] or _snapshot(directory, entry['count']) != entry['hashes']:
            raise ValueError('static Study changed during download')
        return raw


def static_field_study_response(manager, access, action, data):
    if action not in ACTIONS: raise ValueError('unknown static Study operation')
    fields = ACTIONS[action]; keys(data, fields, fields, 'GUI static Study')
    if action in ('static-study-validate', 'static-study-download-input', 'static-study-solve'):
        study = _study(data)
        if action == 'static-study-validate': return study.to_dict(), 'application/json'
        if action == 'static-study-download-input': return study.dumps().encode('utf-8'), 'application/json'
        return dict(id=manager.start_static_field_study(study)), 'application/json'
    if action == 'static-study-jobs': return [state for state in manager.list() if state.get('kind') == KIND], 'application/json'
    if action == 'static-study-result': return access.result(data['id']), 'application/json'
    if action == 'static-study-point': return access.point(data['id'], data['index']), 'application/json'
    raw = access.download(data['id'], data['file'])
    return raw, 'application/json' if data['file'].endswith('.json') else 'application/octet-stream'

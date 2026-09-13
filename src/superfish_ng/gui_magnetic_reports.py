# SPDX-License-Identifier: Apache-2.0
"""Asynchronous verified magnetic report transport with explicit SI quantities."""
import copy
import threading

from .config import keys
from .project import parse_json
from .magnetic_report_jobs import (
    KIND, _report_bytes, _sha, magnetic_report_job_hashes,
    start_magnetic_report, verify_magnetic_report_job,
)

ACTIONS = {
    'magnetic-report-import': ['source', 'report'],
    'magnetic-report-jobs': [],
    'magnetic-report-result': ['id'],
    'magnetic-report-download': ['id', 'file'],
}


def magnetic_report_view(report, case):
    """Transport numbers without rounding, unit conversion, or success inference."""
    common = dict(report_format=report['format'], report_schema_version=report['schema_version'],
                  physics=case['physics'], source_case=case,
                  source_native_sha256=report['source_native_sha256'],
                  request=report['request'], interpretation=report['interpretation'])
    if 'extraction' in report:
        extraction = report['extraction']
        series = extraction['series']
        result = dict(common, kind='planar_multipole', title='平面磁気多極',
                      frame=series['frame'], convention=series['convention'],
                      coefficients=[dict(order=i+1, normal_t=n, skew_t=s)
                                    for i, (n, s) in enumerate(zip(series['normal_t'], series['skew_t']))],
                      diagnostics={key: extraction[key] for key in (
                          'element_order', 'maximum_order', 'angular_samples', 'source_free_disk',
                          'angular_coefficient_relative_difference',
                          'inner_angular_coefficient_relative_difference',
                          'radial_coefficient_relative_difference')},
                      traces=extraction['traces'], virtual_work_status='not_applicable')
    else:
        force = report['force']
        work = report['virtual_work']
        work_status = ('not_performed' if work is None else
                       'failed' if report.get('status') == 'virtual_work_failed' else 'complete')
        axial = report['format'] == 'superfish_ng_off_axis_magnetic_force_report'
        if axial:
            quantities = [dict(name='軸方向力 Fz', value=force['force_z_n'], unit='N')]
            origin = None
            diagnostic_keys = ('quadrature_orders', 'quadrature_relative_difference', 'quadrature_difference_n')
        else:
            quantities = [dict(name=name, value=value, unit=unit) for name, value, unit in (
                ('力 Fx', force['force_xy_n_per_m'][0], 'N/m'),
                ('力 Fy', force['force_xy_n_per_m'][1], 'N/m'),
                ('重み付き応力トルク τz', force['torque_z_nm_per_m'], 'N m/m'),
                ('節点回転の応力トルク τz', force['nodal_rotation_stress_torque_z_nm_per_m'], 'N m/m'))]
            origin = force['origin_xy_m']
            diagnostic_keys = ('quadrature_orders', 'diagnostic_quantity_order', 'quadrature_relative_differences',
                               'nodal_minus_weighted_torque_nm_per_m')
        result = dict(common, kind='axial_force' if axial else 'planar_force',
                      title='軸を含まない磁場の全周軸力' if axial else '平面磁気力・トルク',
                      quantities=quantities, origin_xy_m=origin, body_region_ids=force['body_region_ids'],
                      convention=force['conventions'],
                      diagnostics={key: force[key] for key in diagnostic_keys},
                      virtual_work_status=work_status,
                      work_potential_unit='J' if axial else 'J/m',
                      work_comparison=report['stress_virtual_work_comparison'],
                      virtual_work=work)
    return copy.deepcopy(result)


class MagneticReportAccess:
    """Full replay off the HTTP thread; every later read checks the exact file set."""
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
            report = verify_magnetic_report_job(directory)
            case = parse_json(_report_bytes(directory / 'source/case.json').decode('utf-8'))
            view = magnetic_report_view(report, case)
            if magnetic_report_job_hashes(directory) != entry['hashes']:
                raise ValueError('magnetic report job changed during display verification')
            result = dict(status='ready', id=identifier, view=view)
        except Exception as exc:
            result = dict(status='failed', id=identifier, error=str(exc))
        with self.lock:
            if not self.closed and not self.manager.closed and self.entries.get(identifier) is entry:
                entry['result'] = result

    def result(self, identifier):
        if self.closed or self.manager.closed:
            raise ValueError('magnetic report access is closed')
        state = self.manager.status(identifier)
        if state.get('kind') != KIND:
            raise ValueError('select a dedicated magnetic report job')
        if state['status'] != 'complete':
            return dict(status=state['status'], id=identifier, state=state)
        directory = self.manager.directory(identifier)
        hashes = magnetic_report_job_hashes(directory)
        with self.lock:
            entry = self.entries.get(identifier)
            if entry is not None:
                if entry['hashes'] != hashes:
                    raise ValueError('magnetic report job changed after display verification; import a stable verified source again')
                return copy.deepcopy(entry['result'])
            entry = dict(hashes=hashes, result=dict(status='verifying', id=identifier))
            self.entries[identifier] = entry
            threading.Thread(target=self._verify, args=(identifier, directory, entry), daemon=True,
                             name='magnetic-report-verification').start()
            return dict(status='verifying', id=identifier)

    def download(self, identifier, name):
        if type(name) is not str:
            raise ValueError('magnetic report download requires a file name')
        result = self.result(identifier)
        if result['status'] != 'ready':
            raise ValueError('wait for successful magnetic report verification before downloading')
        with self.lock:
            hashes = self.entries[identifier]['hashes']
        allowed = {n for n in hashes if n not in ('job.json', 'manifest.json')}
        if name not in allowed:
            raise ValueError('select a listed magnetic report or native source file')
        directory = self.manager.directory(identifier)
        raw = _report_bytes(directory / name)
        if _sha(raw) != hashes[name] or magnetic_report_job_hashes(directory) != hashes:
            raise ValueError('magnetic report job changed during download')
        return raw


def magnetic_report_response(manager, access, action, data):
    if action not in ACTIONS:
        raise ValueError('unknown magnetic report operation')
    fields = ACTIONS[action]
    keys(data, fields, fields, 'GUI magnetic report')
    if action == 'magnetic-report-import':
        if any(type(data[key]) is not str or not data[key] for key in ('source', 'report')):
            raise ValueError('enter explicit source native and report paths')
        return dict(id=start_magnetic_report(manager, data['source'], data['report'])), 'application/json'
    if action == 'magnetic-report-jobs':
        return [state for state in manager.list() if state.get('kind') == KIND], 'application/json'
    if action == 'magnetic-report-result':
        return access.result(data['id']), 'application/json'
    raw = access.download(data['id'], data['file'])
    return raw, 'application/json' if data['file'].endswith('.json') else 'application/octet-stream'

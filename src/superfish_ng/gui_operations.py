# SPDX-License-Identifier: Apache-2.0
"""Explicit GUI operation/key/handler registry, independent of HTTP transport."""
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from .config import keys
from .jobs import read_job
from .project import Project, load_document, parse_json


@dataclass(frozen=True)
class OperationContext:
    manager: object
    render_lock: object
    plot_cache: Path
    magnetic_access: object
    static_access: object
    static_study_access: object
    preview_document: object
    tangent_document: object


@dataclass(frozen=True)
class OperationResponse:
    data: object
    content_type: str = "application/json; charset=utf-8"


@dataclass(frozen=True)
class OperationSpec:
    allowed_keys: tuple
    handler: object


def _respond_static_study(context, action, data):
    from .gui_static_field_studies import static_field_study_response
    manager = context.manager
    static_study_access = context.static_study_access
    payload, media = static_field_study_response(manager, static_study_access, action, {k: v for k, v in data.items() if k != 'action'})
    return OperationResponse(payload, content_type=media)

def _respond_static(context, action, data):
    from .gui_static_fields import static_field_response
    manager = context.manager
    static_access = context.static_access
    payload, media = static_field_response(manager, static_access, action, {k: v for k, v in data.items() if k != 'action'})
    return OperationResponse(payload, content_type=media)

def _respond_magnetic(context, action, data):
    from .gui_magnetic_reports import magnetic_report_response
    manager = context.manager
    magnetic_access = context.magnetic_access
    payload, media = magnetic_report_response(manager, magnetic_access, action, {k: v for k, v in data.items() if k != 'action'})
    return OperationResponse(payload, content_type=media)

def _respond_hphi(context, action, data):
    from .gui_hphi import hphi_response
    manager = context.manager
    render_lock = context.render_lock
    plot_cache = context.plot_cache
    payload, media = hphi_response(manager, action, {k: v for k, v in data.items() if k != 'action'}, render_lock, plot_cache)
    return OperationResponse(payload, content_type=media)

def _respond_planar(context, action, data):
    from .gui_planar import planar_response
    manager = context.manager
    render_lock = context.render_lock
    plot_cache = context.plot_cache
    payload, media = planar_response(manager, action, {k: v for k, v in data.items() if k != 'action'}, render_lock, plot_cache)
    return OperationResponse(payload, content_type=media)

def _respond_rf_peak(context, action, data):
    manager = context.manager
    from .gui_rf_peaks import rf_peak_response
    return OperationResponse(rf_peak_response(manager, action, {k: v for k, v in data.items() if k != 'action'}))

def _respond_surface_convergence(context, action, data):
    from .gui_surface_convergence import surface_convergence_response
    return OperationResponse(surface_convergence_response(action, {k: v for k, v in data.items() if k != 'action'}))

def _respond_adaptive_refinement(context, action, data):
    manager = context.manager
    from .gui_adaptive_refinement import adaptive_refinement_response
    return OperationResponse(adaptive_refinement_response(manager, action, {k: v for k, v in data.items() if k != 'action'}))

def _respond_rf_optimization(context, action, data):
    manager = context.manager
    from .gui_rf_optimization import rf_optimization_response
    return OperationResponse(rf_optimization_response(manager, action, {k: v for k, v in data.items() if k != 'action'}))

def _respond_tuning(context, action, data):
    manager = context.manager
    from .gui_tuning import tuning_response
    return OperationResponse(tuning_response(manager, action, {k: v for k, v in data.items() if k != 'action'}))

def _respond_tracked_study(context, action, data):
    manager = context.manager
    from .gui_tracked_study import tracked_study_response
    return OperationResponse(tracked_study_response(manager, action, {k: v for k, v in data.items() if k != 'action'}))

def _respond_mode_tracking(context, action, data):
    manager = context.manager
    from .gui_mode_tracking import tracking_response
    return OperationResponse(tracking_response(manager, action, {k: v for k, v in data.items() if k != 'action'}))

def _respond_tangent(context, action, data):
    tangent_document = context.tangent_document
    return OperationResponse(tangent_document(data['document'], candidate_index=data.get('candidate_index'), replay=action == 'replay-tangent'))

def _respond_curved_deformation(context, action, data):
    from .gui_curved_deformation import deformation_response
    return OperationResponse(deformation_response({k: v for k, v in data.items() if k != 'action'}))

def _respond_project_workspace(context, action, data):
    manager = context.manager
    render_lock = context.render_lock
    plot_cache = context.plot_cache
    preview_document = context.preview_document
    if action == 'freeze-curved-refinement':
        from .frozen_curved_refinement import freeze_curved_refinement
        project = load_document(data['document']) if isinstance(data['document'], str) else Project.from_dict(data['document'])
        return OperationResponse(freeze_curved_refinement(project).to_dict())
    if action == 'curved-selection-mesh':
        from .gui_curved_mesh import curved_mesh_document
        project = load_document(data['document']) if isinstance(data['document'], str) else Project.from_dict(data['document'])
        return OperationResponse(curved_mesh_document(project))
    if action == 'normalize':
        project = load_document(data['document']) if isinstance(data['document'], str) else Project.from_dict(data['document'])
    elif action == 'replace-mesh':
        from .project_mesh_operations import replace_project_mesh
        project = replace_project_mesh(data['document'], data['mesh_document'])
    elif action == 'assemble':
        project = Project.from_sections(data['case'], data['sections'], reflect_full=data.get('reflect_full', False))
    elif action == 'transfer-curved-selection':
        from .curved_selection_transfer import transfer_curved_cell_selection
        fields = ('action', 'previous_document', 'current_document', 'request_document')
        keys(data, fields, fields, 'curved selection transfer request')
        return OperationResponse(transfer_curved_cell_selection(load_document(data['previous_document']), load_document(data['current_document']), parse_json(data['request_document'])))
    elif action == 'replay-curved-selection-transfer':
        from .curved_selection_transfer import replay_curved_selection_transfer
        keys(data, ('action', 'document'), ('action', 'document'), 'curved selection transfer replay')
        return OperationResponse(replay_curved_selection_transfer(parse_json(data['document'])))
    elif action == 'generate-curved-remesh-plan':
        from .curved_remesh_generation import generate_curved_remesh_plan, build_curved_remesh_generation
        keys(data, ('action', 'document', 'settings_document', 'format'), ('action', 'document', 'settings_document'), 'curved remesh generation request')
        form = data.get('format', 'plan')
        if type(form) is not str or form not in ('plan', 'document'):
            raise ValueError('curved remesh generation format must be plan or document')
        build = build_curved_remesh_generation if form == 'document' else generate_curved_remesh_plan
        return OperationResponse(build(load_document(data['document']), parse_json(data['settings_document'])))
    elif action == 'replay-curved-remesh-generation':
        from .curved_remesh_generation import replay_curved_remesh_generation
        keys(data, ('action', 'document'), ('action', 'document'), 'curved remesh generation replay')
        return OperationResponse(replay_curved_remesh_generation(parse_json(data['document'])))
    elif action == 'normalize-study':
        from .studies import Study
        study = Study.from_dict(parse_json(data['document']))
        study.projects()
        return OperationResponse(study.to_dict())
    elif action == 'start-study':
        from .studies import Study
        return OperationResponse({'id': manager.start_study(Study.from_dict(data['study']))})
    elif action == 'start':
        project = Project.from_dict(data['document'])
        return OperationResponse({'id': manager.start(project)})
    elif action == 'import':
        return OperationResponse({'id': manager.import_result(data['path'])})
    elif action == 'jobs':
        return OperationResponse(manager.list())
    elif action == 'cancel':
        return OperationResponse(manager.cancel(data['id']))
    else:
        directory = manager.directory(data['id'])
        if action == 'log':
            return OperationResponse({'text': (directory / 'log.txt').read_text(errors='replace')[-32000:]})
        state = read_job(directory)
        if state['status'] != 'complete':
            raise ValueError('run is not complete')
        if action == 'study-result':
            return OperationResponse(json.loads((directory / 'study-results.json').read_text()))
        if action == 'study-point':
            index = data['index']
            if type(index) is not int or index < 1:
                raise ValueError('point index must be a positive integer')
            return OperationResponse({'id': manager.import_result(directory / f'point-{index:03d}')})
        if action == 'pillbox-reference':
            from .saved import compare_pillbox
            return OperationResponse(compare_pillbox(directory / 'solution'))
        if action in ('probe', 'probe-metadata'):
            from .saved import export_radial_probe
            from .jobs import _digest, _implementation_hashes
            import hashlib
            spec = {'mode': data.get('mode', 1), 'z_m': data['probe_z_m'], 'fields': _digest(directory / 'solution/fields.npz'), 'implementation': _implementation_hashes()}
            tag = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:20]
            path = directory / f'probe-{tag}.csv'
            with render_lock:
                if not path.exists():
                    export_radial_probe(directory / 'solution', path, data['probe_z_m'], data.get('mode', 1))
                if action == 'probe-metadata':
                    return OperationResponse(path.with_suffix('.csv.json').read_bytes())
                return OperationResponse(path.read_bytes(), content_type='text/csv; charset=utf-8')
        if action == 'band':
            from .saved import analyze_band
            return OperationResponse(analyze_band(directory / 'solution', data['cell_centers_z_m']))
        if action == 'download':
            name = data['file']
            available = {p.name for p in (directory / 'solution').iterdir() if p.suffix in ('.json', '.csv', '.npz', '.vtk')}
            if name not in available:
                raise ValueError('unknown output file')
            return OperationResponse((directory / 'solution' / name).read_bytes(), content_type='application/octet-stream')
        if action == 'result':
            return OperationResponse({'project': Project.load(directory / 'project.json').to_dict(), 'result': json.loads((directory / 'solution/results.json').read_text()), 'state': state, 'files': [p.name for p in sorted((directory / 'solution').iterdir())]})
        mode = data.get('mode', 1)
        if type(mode) is not int or mode < 1:
            raise ValueError('mode must be a positive integer')
        if type(data.get('mesh', False)) is not bool:
            raise ValueError('mesh must be boolean')
        with render_lock:
            import hashlib
            from importlib.metadata import version
            from .jobs import _digest
            render_sources = {name: _digest(Path(__file__).with_name(name)) for name in ('visualize.py', 'display.py', 'sampling.py', 'rf.py', 'te_visualize.py', 'te_display.py', 'te.py', 'te_curved.py', 'te_saved.py')}
            cache_spec = {'view': data, 'sources': render_sources, 'matplotlib': version('matplotlib'), 'numpy': version('numpy'), 'scipy': version('scipy'), 'fields_sha256': _digest(directory / 'solution/fields.npz')}
            tag = hashlib.sha256(json.dumps(cache_spec, sort_keys=True).encode()).hexdigest()[:20]
            image = directory / f'plot-{tag}.png'
            if not image.exists():
                args = [sys.executable, '-m', 'superfish_ng', 'plot', str(directory / 'solution'), '--mode', str(mode), '--out', str(image)]
                if data.get('probe_z_m') is not None:
                    args += ['--probe-z-m', str(data['probe_z_m'])]
                if data.get('mesh'):
                    args += ['--mesh']
                import os
                done = subprocess.run(args, capture_output=True, text=True, timeout=120, env={**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'MPLCONFIGDIR': str(plot_cache)})
                if done.returncode:
                    raise ValueError(done.stderr.strip() or 'plot failed')
                from .jobs import _write_json
                from .te import is_te
                plot_project = Project.load(directory / 'project.json')
                _write_json(image.with_suffix('.json'), {**cache_spec, 'case_sha256': _digest(directory / 'solution/case.json') if is_te(plot_project.case) else json.loads((directory / 'solution/results.json').read_text())['case_sha256']})
            return OperationResponse(image.read_bytes(), content_type='image/png')
    return OperationResponse(preview_document(project))

# Exact operation names and fields; no name-to-physics inference.
_BASE_OPERATIONS = {
    'assess-rf-peaks': OperationSpec(('id', 'mode'), _respond_rf_peak),
    'replay-rf-peaks': OperationSpec(('id', 'mode', 'document'), _respond_rf_peak),
    'start-adaptive-refinement': OperationSpec(('request', 'max_new_levels'), _respond_adaptive_refinement),
    'resume-adaptive-refinement': OperationSpec(('document', 'max_new_levels'), _respond_adaptive_refinement),
    'adaptive-refinement-result': OperationSpec(('id',), _respond_adaptive_refinement),
    'replay-adaptive-refinement': OperationSpec(('document',), _respond_adaptive_refinement),
    'prepare-rf-optimization': OperationSpec(('request',), _respond_rf_optimization),
    'start-rf-optimization': OperationSpec(('request', 'max_new_trials'), _respond_rf_optimization),
    'resume-rf-optimization': OperationSpec(('document', 'max_new_trials'), _respond_rf_optimization),
    'rf-optimization-result': OperationSpec(('id',), _respond_rf_optimization),
    'replay-rf-optimization': OperationSpec(('document',), _respond_rf_optimization),
    'rf-optimization-checkpoints': OperationSpec(('id',), _respond_rf_optimization),
    'open-rf-optimization-checkpoint': OperationSpec(('id', 'index'), _respond_rf_optimization),
    'rf-optimization-field': OperationSpec(('document', 'trial', 'level'), _respond_rf_optimization),
    'start-tune': OperationSpec(('request', 'max_new_trials'), _respond_tuning),
    'tune-checkpoints': OperationSpec(('id',), _respond_tuning),
    'open-tune-checkpoint': OperationSpec(('id', 'index'), _respond_tuning),
    'resume-tune': OperationSpec(('document', 'max_new_trials'), _respond_tuning),
    'tune-result': OperationSpec(('id',), _respond_tuning),
    'replay-tune': OperationSpec(('document',), _respond_tuning),
    'start-adaptive-study': OperationSpec(('request', 'max_new_attempts'), _respond_tracked_study),
    'resume-adaptive-study': OperationSpec(('document', 'max_new_attempts'), _respond_tracked_study),
    'adaptive-study-result': OperationSpec(('id',), _respond_tracked_study),
    'replay-adaptive-study': OperationSpec(('document',), _respond_tracked_study),
    'start-tracked-study': OperationSpec(('request', 'max_new_points'), _respond_tracked_study),
    'resume-tracked-study': OperationSpec(('document', 'max_new_points'), _respond_tracked_study),
    'tracked-study-result': OperationSpec(('id',), _respond_tracked_study),
    'replay-tracked-study': OperationSpec(('document',), _respond_tracked_study),
    'track-study-modes': OperationSpec(('study_id', 'initial_ids', 'controls', 'step_controls'), _respond_mode_tracking),
    'compare-modes': OperationSpec(('previous_id', 'current_id', 'previous_ids', 'controls'), _respond_mode_tracking),
    'start-mode-history': OperationSpec(('document',), _respond_mode_tracking),
    'extend-mode-history': OperationSpec(('document', 'current_id', 'controls'), _respond_mode_tracking),
    'recover-mode-identities': OperationSpec(('document', 'request_document'), _respond_mode_tracking),
    'recover-study-mode-identities': OperationSpec(('document', 'request_document'), _respond_mode_tracking),
    'replay-mode-tracking': OperationSpec(('document',), _respond_mode_tracking),
    'assess-affine-surface-convergence': OperationSpec(('document', 'mode_id'), _respond_surface_convergence),
    'replay-affine-surface-convergence': OperationSpec(('document',), _respond_surface_convergence),
    'assess-surface-convergence': OperationSpec(('document', 'mode_id'), _respond_surface_convergence),
    'replay-surface-convergence': OperationSpec(('document',), _respond_surface_convergence),
    'normalize': OperationSpec(('document',), _respond_project_workspace),
    'replace-mesh': OperationSpec(('document', 'mesh_document'), _respond_project_workspace),
    'curved-selection-mesh': OperationSpec(('document',), _respond_project_workspace),
    'freeze-curved-refinement': OperationSpec(('document',), _respond_project_workspace),
    'generate-curved-remesh-plan': OperationSpec(('document', 'settings_document', 'format'), _respond_project_workspace),
    'replay-curved-remesh-generation': OperationSpec(('document',), _respond_project_workspace),
    'transfer-curved-selection': OperationSpec(('previous_document', 'current_document', 'request_document'), _respond_project_workspace),
    'replay-curved-selection-transfer': OperationSpec(('document',), _respond_project_workspace),
    'preview-curved-deformation': OperationSpec(('document', 'geometry_document', 'rf_coordinates', 'minimum_corner_angle_deg'), _respond_curved_deformation),
    'tangent': OperationSpec(('document', 'candidate_index'), _respond_tangent),
    'replay-tangent': OperationSpec(('document',), _respond_tangent),
    'assemble': OperationSpec(('case', 'sections', 'reflect_full'), _respond_project_workspace),
    'start': OperationSpec(('document',), _respond_project_workspace),
    'jobs': OperationSpec((), _respond_project_workspace),
    'cancel': OperationSpec(('id',), _respond_project_workspace),
    'result': OperationSpec(('id',), _respond_project_workspace),
    'plot': OperationSpec(('id', 'mode', 'probe_z_m', 'mesh'), _respond_project_workspace),
    'log': OperationSpec(('id',), _respond_project_workspace),
    'import': OperationSpec(('path',), _respond_project_workspace),
    'band': OperationSpec(('id', 'cell_centers_z_m'), _respond_project_workspace),
    'download': OperationSpec(('id', 'file'), _respond_project_workspace),
    'pillbox-reference': OperationSpec(('id',), _respond_project_workspace),
    'probe': OperationSpec(('id', 'mode', 'probe_z_m'), _respond_project_workspace),
    'probe-metadata': OperationSpec(('id', 'mode', 'probe_z_m'), _respond_project_workspace),
    'normalize-study': OperationSpec(('document',), _respond_project_workspace),
    'start-study': OperationSpec(('study',), _respond_project_workspace),
    'study-result': OperationSpec(('id',), _respond_project_workspace),
    'study-point': OperationSpec(('id', 'index'), _respond_project_workspace),
}


def operation_registry():
    registry = dict(_BASE_OPERATIONS)
    from .gui_planar import ACTIONS, planar_response
    registry.update({name: OperationSpec(tuple(fields), _respond_planar) for name, fields in ACTIONS.items()})
    from .gui_hphi import ACTIONS as HPHI_ACTIONS, hphi_response
    registry.update({name: OperationSpec(tuple(fields), _respond_hphi) for name, fields in HPHI_ACTIONS.items()})
    from .gui_magnetic_reports import ACTIONS as MAGNETIC_ACTIONS, magnetic_report_response
    registry.update({name: OperationSpec(tuple(fields), _respond_magnetic) for name, fields in MAGNETIC_ACTIONS.items()})
    from .gui_static_fields import ACTIONS as STATIC_ACTIONS, static_field_response
    registry.update({name: OperationSpec(tuple(fields), _respond_static) for name, fields in STATIC_ACTIONS.items()})
    from .gui_static_field_studies import ACTIONS as STATIC_STUDY_ACTIONS, static_field_study_response
    registry.update({name: OperationSpec(tuple(fields), _respond_static_study) for name, fields in STATIC_STUDY_ACTIONS.items()})
    return registry


def dispatch_operation(context, data):
    """Validate the old strict envelope before calling its declared operation."""
    action = data.get("action")
    registry = operation_registry()
    if action not in registry:
        raise ValueError("unknown operation")
    spec = registry[action]
    keys(data, ["action", *spec.allowed_keys], ["action"], "request")
    return spec.handler(context, action, data)

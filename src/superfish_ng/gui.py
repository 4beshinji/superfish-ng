# SPDX-License-Identifier: Apache-2.0
"""Single-user loopback UI; no remote service or web framework dependency."""

import hmac
from contextlib import ExitStack
import json
import mimetypes
from pathlib import Path
import secrets
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import webbrowser

from .config import keys
from .geometry import linearize_profile
from .jobs import JobManager, read_job
from .project import Project, load_document, parse_json
from .gui_http import (read_api_request, make_handler, _REQUEST_BYTES,
                       _CHECKPOINT_REQUEST_BYTES, _CHECKPOINT_ACTIONS,
                       _CURVED_PLANAR_CHECKPOINT_BYTES, _CURVED_PLANAR_CHECKPOINT_ACTIONS)
from .gui_operations import OperationContext, dispatch_operation


ASSETS = Path(__file__).with_name("web")



def preview_document(project):
    """Preserve a closed contour distinctly from an open radius profile."""
    contour = project.case.contour
    result = {"project": project.to_dict(), "outline_zr_m":
              [list(p) for p in (contour.vertices_zr_m if contour is not None else linearize_profile(project.case))]}
    if contour is not None:
        result.update(outline_closed=True, outline_edge_tags=list(contour.edge_tags),
                      area_m2=contour.area_m2, volume_m3=contour.volume_m3)
    if project.case.curved_contour is not None:
        curve = project.case.curved_contour
        result["geometry_approximation"] = {
            "tolerance_m": project.case.curve_chord_tolerance_m,
            "analytic_area_m2": curve.area_m2,
            "analytic_volume_m3": curve.volume_m3,
            "area_difference_m2": contour.area_m2 - curve.area_m2,
            "volume_difference_m3": contour.volume_m3 - curve.volume_m3,
        }
    return result


def tangent_document(document, *, candidate_index=None, replay=False):
    """Shared GUI response; never apply an unfinished template to a project."""
    from .tangent_construction import construct_tangent_case, replay_construction
    from .construction_diagnostics import _from_replayed_construction, replay_construction_diagnosis
    document = parse_json(document) if isinstance(document, str) else document
    if replay and isinstance(document,dict) and document.get('document_type')=='construction_offset_diagnosis':
        diagnosis=replay_construction_diagnosis(document)
        construction=diagnosis['construction']
    else:
        construction = (replay_construction(document) if replay else
                        construct_tangent_case(document, candidate_index=candidate_index))
        diagnosis=_from_replayed_construction(construction)
    preview = (preview_document(Project.from_dict(construction["case"]))
               if construction["case"] is not None else None)
    return {"construction": construction, "preview": preview,
            "offset_diagnosis": diagnosis,
            "diagnosis_serialized": json.dumps(diagnosis,indent=2,ensure_ascii=False,allow_nan=False)+"\n" if diagnosis is not None else None,
            "serialized": json.dumps(construction, indent=2, ensure_ascii=False, allow_nan=False)+"\n"}


def create_server(workspace, port=0):
    from importlib.util import find_spec

    if find_spec("matplotlib") is None:
        raise ValueError(
            "GUI plotting requires the plot extra: uv pip install -e '.[plot]'"
        )
    token = secrets.token_urlsafe(32)
    render_lock = threading.Lock()


    manager = JobManager(workspace)
    from .gui_magnetic_reports import MagneticReportAccess
    magnetic_access = MagneticReportAccess(manager)
    from .gui_static_fields import StaticFieldAccess
    static_access = StaticFieldAccess(manager)
    from .gui_static_field_studies import StaticFieldStudyAccess
    static_study_access = StaticFieldStudyAccess(manager)
    context = OperationContext(
        manager=manager, render_lock=render_lock, plot_cache=manager.root / ".plot-cache",
        magnetic_access=magnetic_access, static_access=static_access,
        static_study_access=static_study_access,
        preview_document=lambda project: preview_document(project),
        tangent_document=lambda *args, **kwargs: tangent_document(*args, **kwargs),
    )
    Handler = make_handler(token, ASSETS, lambda data: dispatch_operation(context, data),
                           lambda *args, **kwargs: read_api_request(*args, **kwargs))
    try:
        plot_cache = manager.root / ".plot-cache"
        plot_cache.mkdir(exist_ok=True)
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except BaseException:
        manager.close()
        raise
    server.manager = manager
    server.magnetic_access = magnetic_access
    server.static_access = static_access
    server.static_study_access = static_study_access
    server.launch_url = f"http://127.0.0.1:{server.server_port}/#{token}"
    return server


def serve(workspace, port=0, open_browser=True):
    server = create_server(workspace, port)
    with ExitStack() as cleanup:
        cleanup.callback(server.manager.close)
        cleanup.callback(server.magnetic_access.close)
        cleanup.callback(server.static_access.close)
        cleanup.callback(server.static_study_access.close)
        cleanup.callback(server.server_close)
        print(f"Superfish-NG GUI: {server.launch_url}", flush=True)
        print(f"Workspace: {server.manager.root}", flush=True)
        if open_browser:
            webbrowser.open(server.launch_url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

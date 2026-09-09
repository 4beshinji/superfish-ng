# SPDX-License-Identifier: Apache-2.0
"""Single-user loopback UI; no remote service or web framework dependency."""

import hmac
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
            "GUI plotting requires the plot extra: python -m pip install -e '.[plot]'"
        )
    manager = JobManager(workspace)
    token = secrets.token_urlsafe(32)
    render_lock = threading.Lock()
    plot_cache = manager.root / ".plot-cache"
    plot_cache.mkdir(exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(
            self, data, status=200, content_type="application/json; charset=utf-8"
        ):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def valid_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.valid_host():
                return self.reply({"error": "invalid host"}, 403)
            name = {
                "/": "index.html",
                "/app.js": "app.js",
                "/style.css": "style.css",
            }.get(self.path)
            if name is None:
                return self.reply({"error": "not found"}, 404)
            self.reply(
                (ASSETS / name).read_bytes(),
                content_type=mimetypes.guess_type(name)[0] + "; charset=utf-8",
            )

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if (
                not self.valid_host()
                or self.headers.get("Origin", origin) != origin
                or not hmac.compare_digest(self.headers.get("X-NG-Token", ""), token)
            ):
                return self.reply(
                    {"error": "local session required; reopen the launch URL"}, 403
                )
            if self.path != "/api":
                return self.reply({"error": "not found"}, 404)
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4 * 1024 * 1024:
                    raise ValueError("request must be between 1 byte and 4 MiB")
                data = parse_json(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("request must be an object")
                action = data.get("action")
                allowed = {
                    "assess-rf-peaks": ["id", "mode"],
                    "replay-rf-peaks": ["id", "mode", "document"],
                    "start-adaptive-refinement": ["request", "max_new_levels"],
                    "resume-adaptive-refinement": ["document", "max_new_levels"],
                    "adaptive-refinement-result": ["id"],
                    "replay-adaptive-refinement": ["document"],
                    "start-tune": ["request", "max_new_trials"],
                    "tune-checkpoints": ["id"],
                    "open-tune-checkpoint": ["id", "index"],
                    "resume-tune": ["document", "max_new_trials"],
                    "tune-result": ["id"],
                    "replay-tune": ["document"],
                    "start-adaptive-study": ["request", "max_new_attempts"],
                    "resume-adaptive-study": ["document", "max_new_attempts"],
                    "adaptive-study-result": ["id"],
                    "replay-adaptive-study": ["document"],
                    "start-tracked-study": ["request", "max_new_points"],
                    "resume-tracked-study": ["document", "max_new_points"],
                    "tracked-study-result": ["id"],
                    "replay-tracked-study": ["document"],
                    "track-study-modes": ["study_id", "initial_ids", "controls", "step_controls"],
                    "compare-modes": ["previous_id", "current_id", "previous_ids", "controls"],
                    "start-mode-history": ["document"],
                    "extend-mode-history": ["document", "current_id", "controls"],
                    "replay-mode-tracking": ["document"],
                    "assess-affine-surface-convergence": ["document", "mode_id"],
                    "replay-affine-surface-convergence": ["document"],
                    "assess-surface-convergence": ["document", "mode_id"],
                    "replay-surface-convergence": ["document"],
                    "normalize": ["document"],
                    "replace-mesh": ["document", "mesh_document"],
                    "curved-selection-mesh": ["document"],
                    "tangent": ["document", "candidate_index"],
                    "replay-tangent": ["document"],
                    "assemble": ["case", "sections", "reflect_full"],
                    "start": ["document"],
                    "jobs": [],
                    "cancel": ["id"],
                    "result": ["id"],
                    "plot": ["id", "mode", "probe_z_m", "mesh"],
                    "log": ["id"],
                    "import": ["path"],
                    "band": ["id", "cell_centers_z_m"],
                    "download": ["id", "file"],
                    "pillbox-reference": ["id"],
                    "probe": ["id", "mode", "probe_z_m"],
                    "probe-metadata": ["id", "mode", "probe_z_m"],
                    "normalize-study": ["document"],
                    "start-study": ["study"],
                    "study-result": ["id"],
                    "study-point": ["id", "index"],
                }
                if action not in allowed:
                    raise ValueError("unknown operation")
                keys(data, ["action", *allowed[action]], ["action"], "request")
                if action in ("assess-rf-peaks", "replay-rf-peaks"):
                    from .gui_rf_peaks import rf_peak_response
                    return self.reply(rf_peak_response(manager,action,{k:v for k,v in data.items() if k!="action"}))
                if action in ("assess-surface-convergence", "replay-surface-convergence", "assess-affine-surface-convergence", "replay-affine-surface-convergence"):
                    from .gui_surface_convergence import surface_convergence_response
                    return self.reply(surface_convergence_response(action,{k:v for k,v in data.items() if k!='action'}))
                if action in ("start-adaptive-refinement", "resume-adaptive-refinement", "adaptive-refinement-result", "replay-adaptive-refinement"):
                    from .gui_adaptive_refinement import adaptive_refinement_response
                    return self.reply(adaptive_refinement_response(manager,action,{k:v for k,v in data.items() if k!='action'}))
                if action in ("start-tune", "resume-tune", "tune-result", "replay-tune", "tune-checkpoints", "open-tune-checkpoint"):
                    from .gui_tuning import tuning_response
                    return self.reply(tuning_response(manager,action,{k:v for k,v in data.items() if k!='action'}))
                if action in ("start-tracked-study", "resume-tracked-study", "tracked-study-result", "replay-tracked-study", "start-adaptive-study", "resume-adaptive-study", "adaptive-study-result", "replay-adaptive-study"):
                    from .gui_tracked_study import tracked_study_response
                    return self.reply(tracked_study_response(manager,action,{k:v for k,v in data.items() if k!='action'}))
                if action in ("track-study-modes", "compare-modes", "start-mode-history", "extend-mode-history", "replay-mode-tracking"):
                    from .gui_mode_tracking import tracking_response
                    return self.reply(tracking_response(manager,action,{k:v for k,v in data.items() if k!='action'}))
                if action in ("tangent", "replay-tangent"):
                    return self.reply(tangent_document(data["document"],
                                                       candidate_index=data.get("candidate_index"),
                                                       replay=action == "replay-tangent"))
                if action == "curved-selection-mesh":
                    from .gui_curved_mesh import curved_mesh_document
                    project = (load_document(data["document"]) if isinstance(data["document"], str)
                               else Project.from_dict(data["document"]))
                    return self.reply(curved_mesh_document(project))
                if action == "normalize":
                    project = (
                        load_document(data["document"])
                        if isinstance(data["document"], str)
                        else Project.from_dict(data["document"])
                    )
                elif action == "replace-mesh":
                    from .project_mesh_operations import replace_project_mesh
                    project=replace_project_mesh(data['document'],data['mesh_document'])
                elif action == "assemble":
                    project = Project.from_sections(
                        data["case"],
                        data["sections"],
                        reflect_full=data.get("reflect_full", False),
                    )
                elif action == "normalize-study":
                    from .studies import Study

                    study = Study.from_dict(parse_json(data["document"]))
                    study.projects()
                    return self.reply(study.to_dict())
                elif action == "start-study":
                    from .studies import Study

                    return self.reply(
                        {"id": manager.start_study(Study.from_dict(data["study"]))}
                    )
                elif action == "start":
                    project = Project.from_dict(data["document"])
                    return self.reply({"id": manager.start(project)})
                elif action == "import":
                    return self.reply({"id": manager.import_result(data["path"])})
                elif action == "jobs":
                    return self.reply(manager.list())
                elif action == "cancel":
                    return self.reply(manager.cancel(data["id"]))
                else:
                    directory = manager.directory(data["id"])
                    if action == "log":
                        return self.reply(
                            {
                                "text": (directory / "log.txt").read_text(
                                    errors="replace"
                                )[-32000:]
                            }
                        )
                    state = read_job(directory)
                    if state["status"] != "complete":
                        raise ValueError("run is not complete")
                    if action == "study-result":
                        return self.reply(
                            json.loads((directory / "study-results.json").read_text())
                        )
                    if action == "study-point":
                        index = data["index"]
                        if type(index) is not int or index < 1:
                            raise ValueError("point index must be a positive integer")
                        return self.reply(
                            {
                                "id": manager.import_result(
                                    directory / f"point-{index:03d}"
                                )
                            }
                        )
                    if action == "pillbox-reference":
                        from .saved import compare_pillbox

                        return self.reply(compare_pillbox(directory / "solution"))
                    if action in ("probe", "probe-metadata"):
                        from .saved import export_radial_probe
                        from .jobs import _digest, _implementation_hashes
                        import hashlib

                        spec = {
                            "mode": data.get("mode", 1),
                            "z_m": data["probe_z_m"],
                            "fields": _digest(directory / "solution/fields.npz"),
                            "implementation": _implementation_hashes(),
                        }
                        tag = hashlib.sha256(
                            json.dumps(spec, sort_keys=True).encode()
                        ).hexdigest()[:20]
                        path = directory / f"probe-{tag}.csv"
                        with render_lock:
                            if not path.exists():
                                export_radial_probe(
                                    directory / "solution",
                                    path,
                                    data["probe_z_m"],
                                    data.get("mode", 1),
                                )
                            if action == "probe-metadata":
                                return self.reply(
                                    path.with_suffix(".csv.json").read_bytes()
                                )
                            return self.reply(
                                path.read_bytes(),
                                content_type="text/csv; charset=utf-8",
                            )
                    if action == "band":
                        from .saved import analyze_band

                        return self.reply(
                            analyze_band(
                                directory / "solution", data["cell_centers_z_m"]
                            )
                        )
                    if action == "download":
                        name = data["file"]
                        available = {
                            p.name
                            for p in (directory / "solution").iterdir()
                            if p.suffix in (".json", ".csv", ".npz", ".vtk")
                        }
                        if name not in available:
                            raise ValueError("unknown output file")
                        return self.reply(
                            (directory / "solution" / name).read_bytes(),
                            content_type="application/octet-stream",
                        )
                    if action == "result":
                        return self.reply(
                            {
                                "project": Project.load(
                                    directory / "project.json"
                                ).to_dict(),
                                "result": json.loads(
                                    (directory / "solution/results.json").read_text()
                                ),
                                "state": state,
                                "files": [
                                    p.name
                                    for p in sorted((directory / "solution").iterdir())
                                ],
                            }
                        )
                    mode = data.get("mode", 1)
                    if type(mode) is not int or mode < 1:
                        raise ValueError("mode must be a positive integer")
                    if type(data.get("mesh", False)) is not bool:
                        raise ValueError("mesh must be boolean")
                    # Serialize plotting processes to bound memory and avoid pyplot shared state.
                    with render_lock:
                        import hashlib
                        from importlib.metadata import version
                        from .jobs import _digest

                        render_sources = {
                            name: _digest(Path(__file__).with_name(name))
                            for name in ("visualize.py", "sampling.py", "rf.py")
                        }
                        cache_spec = {
                            "view": data,
                            "sources": render_sources,
                            "matplotlib": version("matplotlib"),
                            "numpy": version("numpy"),
                            "scipy": version("scipy"),
                            "fields_sha256": _digest(directory / "solution/fields.npz"),
                        }
                        tag = hashlib.sha256(
                            json.dumps(cache_spec, sort_keys=True).encode()
                        ).hexdigest()[:20]
                        image = directory / f"plot-{tag}.png"
                        if not image.exists():
                            args = [
                                sys.executable,
                                "-m",
                                "superfish_ng",
                                "plot",
                                str(directory / "solution"),
                                "--mode",
                                str(mode),
                                "--out",
                                str(image),
                            ]
                            if data.get("probe_z_m") is not None:
                                args += ["--probe-z-m", str(data["probe_z_m"])]
                            if data.get("mesh"):
                                args += ["--mesh"]
                            import os

                            done = subprocess.run(
                                args,
                                capture_output=True,
                                text=True,
                                timeout=120,
                                env={
                                    **os.environ,
                                    "OPENBLAS_NUM_THREADS": "1",
                                    "MPLCONFIGDIR": str(plot_cache),
                                },
                            )
                            if done.returncode:
                                raise ValueError(done.stderr.strip() or "plot failed")
                            from .jobs import _write_json

                            _write_json(
                                image.with_suffix(".json"),
                                {
                                    **cache_spec,
                                    "case_sha256": json.loads(
                                        (
                                            directory / "solution/results.json"
                                        ).read_text()
                                    )["case_sha256"],
                                },
                            )
                        return self.reply(image.read_bytes(), content_type="image/png")
                return self.reply(preview_document(project))
            except (
                ValueError,
                KeyError,
                TypeError,
                OSError,
                RuntimeError,
                subprocess.TimeoutExpired,
            ) as exc:
                self.reply({"error": str(exc)}, 400)

    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except Exception:
        manager.close()
        raise
    server.manager = manager
    server.launch_url = f"http://127.0.0.1:{server.server_port}/#{token}"
    return server


def serve(workspace, port=0, open_browser=True):
    server = create_server(workspace, port)
    print(f"Superfish-NG GUI: {server.launch_url}", flush=True)
    print(f"Workspace: {server.manager.root}", flush=True)
    if open_browser:
        webbrowser.open(server.launch_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.manager.close()

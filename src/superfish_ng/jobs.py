# SPDX-License-Identifier: Apache-2.0
"""Local jobs with exclusive destinations and verified completion manifests."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import traceback
import uuid

from .project import Project
from .solver import solve
from .io import save_run


def _write_json(path, data):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def _digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _state(directory, status, **extra):
    previous = (
        json.loads((directory / "job.json").read_text())
        if (directory / "job.json").is_file()
        else {}
    )
    data = {
        "status": status,
        "created_unix": previous.get("created_unix", time.time()),
        "updated_unix": time.time(),
        **extra,
    }
    _write_json(directory / "job.json", data)
    return data


def read_job(directory, verify=True):
    directory = Path(directory)
    state = json.loads((directory / "job.json").read_text(encoding="utf-8"))
    if state.get("status") == "complete" and verify:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        from .planar_jobs import is_planar_job,verify_planar_job
        if is_planar_job(directory,state,manifest):
            verify_planar_job(directory,state,manifest)
            return state
        files = manifest.get("files", {})
        required = (
            {"study.json", "study-results.json"}
            if manifest.get("kind") == "study"
            else {
                "project.json",
                "solution/case.json",
                "solution/results.json",
                "solution/fields.npz",
                "solution/modes.csv",
            }
        )
        if manifest.get("kind") in ("tracked_study", "adaptive_study") or state.get("kind") in ("tracked_study", "adaptive_study"):
            if manifest.get("kind") != state.get("kind"):
                raise ValueError("tracked Study job kind differs from completion manifest")
            prefix = "adaptive-study" if manifest["kind"] == "adaptive_study" else "tracked-study"
            required = {prefix + "-request.json", prefix + "-results.json"}
        if manifest.get("kind") == "rf_optimization" or state.get("kind") == "rf_optimization":
            if manifest.get("kind") != state.get("kind"):
                raise ValueError("RF optimization job kind differs from completion manifest")
            required = {"rf-optimization-request.json", "rf-optimization-results.json"}
        if manifest.get("kind") == "tune" or state.get("kind") == "tune":
            if manifest.get("kind") != state.get("kind"):
                raise ValueError("tune job kind differs from completion manifest")
            required = {"tune-request.json", "tune-results.json"}
        if manifest.get("kind") == "adaptive_refinement" or state.get("kind") == "adaptive_refinement":
            if manifest.get("kind") != state.get("kind"):
                raise ValueError("adaptive refinement job kind differs from completion manifest")
            required = {"adaptive-refinement-request.json", "adaptive-refinement-results.json"}
        if not required.issubset(files):
            raise ValueError("completion manifest missing required output")
        for name, digest in files.items():
            path = directory / name
            if (
                Path(name).is_absolute()
                or ".." in Path(name).parts
                or path.is_symlink()
            ):
                raise ValueError("invalid completion manifest path")
            if not path.is_file() or _digest(path) != digest:
                raise ValueError(f"output integrity failure or missing file: {name}")
        if manifest.get("kind") == "rf_optimization":
            from .rf_optimization_jobs import verify_rf_optimization_job
            verify_rf_optimization_job(directory, state, manifest)
        if manifest.get("kind") == "tune":
            from .tuning_jobs import verify_tune_job
            verify_tune_job(directory, state, manifest)
        if manifest.get("kind") == "adaptive_refinement":
            from .adaptive_refinement_jobs import verify_adaptive_refinement_job
            verify_adaptive_refinement_job(directory, state, manifest)
        if manifest.get("kind") in ("tracked_study", "adaptive_study"):
            from .tracked_study import read_tracked_study
            from .adaptive_study import read_adaptive_study
            from .saved_mode_tracking import _canonical
            adaptive = manifest["kind"] == "adaptive_study"
            reader = read_adaptive_study if adaptive else read_tracked_study
            result = reader(directory / (prefix + "-results.json"))
            request = json.loads((directory / (prefix + "-request.json")).read_text())
            if adaptive and (state.get("accepted_points") != len(result["accepted_point_indices"])
                    or state.get("completed_attempts") != len(result["attempts"])
                    or state.get("unreached_target_indices") != result["unreached_target_indices"]):
                raise ValueError("adaptive Study job summary differs from verified checkpoint")
            if (_canonical(request.get("request")) != _canonical(result["request"])
                    or state.get("tracking_status") != result["status"]
                    or state.get("can_resume") is not result["can_resume"]
                    or state.get("computed_points") != len(result["points" if adaptive else "point_runs"])
                    or state.get("numerical_validation") != "not_checked"):
                raise ValueError("tracked Study job summary differs from verified checkpoint")
        if manifest.get('kind') in (None,'solve'):
            from .te_jobs import verify_te_job_if_present
            verify_te_job_if_present(directory,manifest)
    return state


def _prepare(project, directory):
    # Serialize and revalidate also for callers using the dataclass constructor.
    project = Project.from_dict(project.to_dict())
    directory.mkdir(parents=True, exist_ok=False)
    project.save(directory / "project.json")
    _state(directory, "queued")


def _implementation_hashes():
    root = Path(__file__).parent
    return {
        p.relative_to(root).as_posix(): _digest(p)
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix in (".py", ".html", ".js", ".css")
    }


def _execute_prepared(directory):
    start = time.monotonic()
    implementation = _implementation_hashes()
    try:
        project_hash = _digest(directory / "project.json")
        project = Project.load(directory / "project.json")
        _state(directory, "running", stage="finite element solve")
        solution = (solve(project.case) if project.mesh_data is None else solve(project.case,mesh_data=project.mesh_data))
        case = project.case
        if project.reflect_full:
            from .symmetry import reflect_solution

            case, solution = reflect_solution(case, solution)
        _state(directory, "running", stage="saving fields and RF quantities")
        save_run(case, solution, directory / "solution")
        if _digest(directory / "project.json") != project_hash:
            raise RuntimeError("project input changed during run; retry with stable input")
        files = {"project.json": project_hash}
        files.update(
            {
                p.relative_to(directory).as_posix(): _digest(p)
                for p in sorted((directory / "solution").iterdir())
                if p.is_file()
            }
        )
        if implementation != _implementation_hashes():
            raise RuntimeError(
                "implementation changed during run; retry with stable source"
            )
        _write_json(
            directory / "manifest.json",
            {
                "manifest_version": 1,
                "files": files,
                "implementation_sha256": implementation,
                "source_changed_during_run": False,
            },
        )
        _state(
            directory,
            "complete",
            elapsed_seconds=time.monotonic() - start,
            numerical_validation="not_checked",
            stage="saved",
        )
        return read_job(directory)
    except Exception as exc:
        _state(
            directory,
            "failed",
            error=str(exc),
            elapsed_seconds=time.monotonic() - start,
        )
        raise


def execute_project(project, directory):
    """Synchronously solve a project into a new directory; never overwrite."""
    directory = Path(directory)
    _prepare(project, directory)
    return _execute_prepared(directory)


class JobManager:
    """One local application's jobs; subprocesses isolate solves from the UI.

    The application owns the workspace exclusively. An advisory file lock
    prevents a second manager from reclassifying live work after a restart.
    """

    def __init__(self, root):
        import fcntl

        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._workspace_lock = (self.root / ".manager.lock").open("a+")
        try:
            fcntl.flock(self._workspace_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._workspace_lock.close()
            raise ValueError(
                "workspace already has a running application; choose another workspace"
            )
        self.processes = {}
        self.lock = threading.RLock()
        self.closed = False
        for p in self.root.iterdir():
            if p.is_dir() and not p.is_symlink() and (p / "job.json").is_file():
                state = read_job(p, verify=False)
                if state.get("status") in ("queued", "running"):
                    _state(
                        p,
                        "interrupted",
                        kind=state.get("kind", "solve"),
                        error="application stopped before completion; start a new run",
                    )

    def directory(self, identifier):
        if (
            not isinstance(identifier, str)
            or not identifier
            or any(
                c
                not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
                for c in identifier
            )
        ):
            raise ValueError("invalid job identifier")
        path = self.root / identifier
        if path.is_symlink():
            raise ValueError("job directory must not be a symlink")
        return path

    def start(self, project):
        with self.lock:
            if self.closed:
                raise ValueError("job manager is closed")
            identifier = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:10]
            directory = self.directory(identifier)
            _prepare(project, directory)
            try:
                with (directory / "log.txt").open("x") as log:
                    proc = subprocess.Popen(
                        [sys.executable, "-m", "superfish_ng.jobs", str(directory)],
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        env={**os.environ, "OPENBLAS_NUM_THREADS": "1"},
                    )
                self.processes[identifier] = proc
            except Exception as exc:
                _state(directory, "failed", error=str(exc))
                raise
            return identifier

    def start_planar(self, project):
        """Execute a dedicated Cartesian cutoff Project in a local worker."""
        from .planar_jobs import start_planar
        return start_planar(self,project)

    def import_planar_result(self, source):
        """Import verified planar native bytes, preserving their explicit mesh."""
        from .planar_jobs import import_planar_result
        return import_planar_result(self,source)

    def start_adaptive_study(self, request, *, max_new_attempts=None, checkpoint=None):
        """Run adaptive tracked FEM sweeps in an isolated local worker."""
        from .adaptive_study_jobs import start_adaptive_study
        return start_adaptive_study(self, request, max_new_attempts=max_new_attempts, checkpoint=checkpoint)

    def start_rf_optimization(self, request, *, max_new_trials=None, checkpoint=None):
        """Run constrained RF optimization in an isolated local worker."""
        from .rf_optimization_jobs import start_rf_optimization
        return start_rf_optimization(self, request, max_new_trials=max_new_trials, checkpoint=checkpoint)

    def start_tune(self, request, *, max_new_trials=None, checkpoint=None):
        """Run tracked frequency tuning in an isolated local worker."""
        from .tuning_jobs import start_tune
        return start_tune(self, request, max_new_trials=max_new_trials, checkpoint=checkpoint)

    def start_adaptive_refinement(self, request, *, max_new_levels=None, checkpoint=None):
        """Run adaptive FEM refinement in an isolated local worker."""
        from .adaptive_refinement_jobs import start_adaptive_refinement
        return start_adaptive_refinement(self, request, max_new_levels=max_new_levels, checkpoint=checkpoint)

    def start_tracked_study(self, request, *, max_new_points=None, checkpoint=None):
        """Run sequential tracked FEM points in an isolated local worker."""
        from .tracked_study_jobs import start_tracked_study
        return start_tracked_study(self, request, max_new_points=max_new_points, checkpoint=checkpoint)

    def start_study(self, study):
        with self.lock:
            if self.closed:
                raise ValueError("job manager is closed")
            study.projects()  # Validate all input points before reserving output.
            identifier = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:10]
            directory = self.directory(identifier)
            directory.mkdir()
            study.save(directory / "study.json")
            _state(directory, "queued", kind="study")
            try:
                with (directory / "log.txt").open("x") as log:
                    process = subprocess.Popen(
                        [sys.executable, "-m", "superfish_ng.studies", str(directory)],
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        env={**os.environ, "OPENBLAS_NUM_THREADS": "1"},
                    )
                self.processes[identifier] = process
            except Exception as exc:
                _state(directory, "failed", kind="study", error=str(exc))
                raise
            return identifier

    def status(self, identifier, verify=False):
        with self.lock:
            directory = self.directory(identifier)
            state = read_job(directory, verify=verify)
            process = self.processes.get(identifier)
            if (
                process is not None
                and process.poll() is not None
                and state["status"] in ("queued", "running")
            ):
                state = _state(
                    directory,
                    "failed",
                    kind=state.get("kind", "solve"),
                    error=f"worker exited {process.returncode} before completion",
                )
            if state["status"] in ("queued", "running"):
                state["elapsed_seconds"] = max(
                    0, time.time() - state.get("created_unix", state["updated_unix"])
                )
            return {"id": identifier, **state}

    def cancel(self, identifier):
        with self.lock:
            cancel_started = time.monotonic()
            state = self.status(identifier)
            if state["status"] not in ("queued", "running"):
                return state
            process = self.processes.get(identifier)
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            # A complete save that won the race stays complete.
            if (
                read_job(self.directory(identifier), verify=False)["status"]
                != "complete"
            ):
                _state(
                    self.directory(identifier),
                    "cancelled",
                    kind=state.get("kind", "solve"),
                    error="cancelled by user; start a new run to retry",
                    elapsed_seconds=state["elapsed_seconds"] + time.monotonic() - cancel_started,
                )
            return self.status(identifier)

    def import_result(self, source):
        """Copy checked NG output into history; never label this a fresh solve."""
        import shutil
        from .saved import read_solution

        with self.lock:
            source = Path(source).resolve()
            managed = (source / "job.json").is_file()
            if managed:
                if read_job(source)["status"] != "complete":
                    raise ValueError("source job is not complete")
                project = Project.load(source / "project.json")
                solution_dir = source / "solution"
            else:
                solution_dir = source
            from .config import Case
            from .te import is_te
            if is_te(Case.load(solution_dir/'case.json')):
                from .te_jobs import import_te_result
                return import_te_result(self,source,solution_dir,project if managed else None)
            saved = read_solution(solution_dir)
            if not managed:
                reflected = saved.results.get("reflection_source_case")
                project = Project.from_dict(
                    {
                        "project_version": 1,
                        "case": reflected or saved.case.to_dict(),
                        "reflect_full": bool(reflected),
                    }
                )
            identifier = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:10]
            directory = self.directory(identifier)
            _prepare(project, directory)
            try:
                target = directory / "solution"
                target.mkdir()
                names = ["case.json", "results.json", "fields.npz", "modes.csv"]
                if 'input_sha256' in saved.results['mesh']:
                    names.append('mesh.json')
                if 'save_protocol_version' in saved.results:
                    names.append('save_protocol.json')
                names += [
                    f"{prefix}_{i:03d}.{suffix}"
                    for i in range(1, saved.case.modes + 1)
                    for prefix, suffix in [("axis", "csv"), ("mode", "vtk")]
                ]
                if 'save_protocol_version' in saved.results:
                    names.append('save_complete.json')
                for name in names:
                    path = solution_dir / name
                    if path.is_symlink() or not path.is_file():
                        raise ValueError(f"missing or linked saved output: {name}")
                    if name == 'save_complete.json':
                        temporary = target / '.import-completion.tmp'
                        shutil.copyfile(path, temporary)
                        os.link(temporary, target / name)
                        temporary.unlink()
                    else:
                        shutil.copyfile(path, target / name)
                read_solution(target)
                files = {"project.json": _digest(directory / "project.json")}
                files.update(
                    {
                        p.relative_to(directory).as_posix(): _digest(p)
                        for p in target.iterdir()
                    }
                )
                _write_json(
                    directory / "manifest.json",
                    {
                        "manifest_version": 1,
                        "files": files,
                        "imported_from": str(source),
                    },
                )
                (directory / "log.txt").write_text(
                    "Imported saved NG output; no new FEM solve.\n"
                )
                _state(
                    directory,
                    "complete",
                    stage="imported saved result",
                    origin="imported",
                    source_completion="verified manifest"
                    if managed
                    else ("verified direct-save completion" if 'save_protocol_version' in saved.results
                          else "legacy files checked; no original completion manifest"),
                    numerical_validation="not_checked",
                )
            except Exception as exc:
                _state(directory, "failed", error=str(exc))
                raise
            return identifier

    def list(self):
        with self.lock:
            states = [
                self.status(p.name)
                for p in self.root.iterdir()
                if p.is_dir() and not p.is_symlink() and (p / "job.json").is_file()
            ]
            return sorted(
                states,
                key=lambda state: (state.get("created_unix", 0), state["id"]),
                reverse=True,
            )

    def close(self):
        with self.lock:
            if self.closed:
                return
            for identifier, process in self.processes.items():
                self.cancel(identifier)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            self.closed = True
            self._workspace_lock.close()


if __name__ == "__main__":
    try:
        _execute_prepared(Path(sys.argv[1]))
    except Exception:
        traceback.print_exc()
        sys.exit(2)

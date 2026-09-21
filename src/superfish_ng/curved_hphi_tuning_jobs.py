# SPDX-License-Identifier: Apache-2.0
"""Isolated workers for owned full-quadratic curved Hphi tuning checkpoints.

The tuning decisions and native ownership live in :mod:`curved_hphi_tuning_saved`.
This module only adds the process boundary, submitted-input ownership, job
state, and completion-manifest verification needed by ``JobManager``.
"""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid

from .config import integer, keys
from .hphi_tuning_saved import _snapshot_trial, CHECKPOINT_KEYS
from .hphi_tuning import _json_types
from .curved_hphi_tuning_saved import SCOPE
from .curved_hphi_tuning import validate_curved_hphi_tune
from .curved_hphi_tuning_saved import (
    execute_curved_hphi_tune,
    read_curved_hphi_tune,
    replay_curved_hphi_tune,
)
from .jobs import _digest, _implementation_hashes, _state, _write_json
from .project import parse_json
from .saved_mode_tracking import _canonical


KIND = "curved_hphi_tune"
INPUT = "curved-hphi-tune-request.json"
RESULT = "curved-hphi-tune-results.json"
PHYSICS = "axisymmetric_hphi_rf"


def _load(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Hphi tune worker metadata must be regular files, not links")
    return parse_json(path.read_text(encoding="utf-8"))


def _checkpoint(value):
    """Normalize a submitted checkpoint path before the envelope is serialized."""
    if isinstance(value, (str, Path)):
        return read_curved_hphi_tune(value)
    return value


def _input(data):
    """Validate submission against its original sources before copying."""
    names = ("request", "max_new_trials", "checkpoint")
    keys(data, names, names, "Hphi tune job input")
    validate_curved_hphi_tune(data["request"])
    if data["max_new_trials"] is not None:
        integer(data["max_new_trials"], "max_new_trials")
    data["checkpoint"] = _checkpoint(data["checkpoint"])
    if data["checkpoint"] is not None:
        previous = replay_curved_hphi_tune(data["checkpoint"])
        if not previous["can_resume"]:
            raise ValueError("only a verified PAUSED Hphi tune can resume")
        if _canonical(previous["request"]) != _canonical(data["request"]):
            raise ValueError("Hphi tune resume request differs from checkpoint")
    return data


def _owned_input(data, execution):
    """Replay submitted ancestry using this job's copies, without source I/O.

    The original paths remain in the sealed input as provenance. Only a deep
    copy is rebound; all checkpoint fields, native hashes and decisions still
    undergo the ordinary replay checks. Use this only after trials are owned,
    never to preflight a new submission or to repair missing copies.
    """
    names = ("request", "max_new_trials", "checkpoint")
    keys(data, names, names, "Hphi tune job input")
    owned = deepcopy(data)
    previous = owned["checkpoint"]
    if previous is not None:
        _json_types(previous)
        keys(previous, CHECKPOINT_KEYS, CHECKPOINT_KEYS, 'curved Hphi submitted checkpoint')
        if (previous['format'] != 'superfish_ng_curved_hphi_tune_checkpoint'
                or type(previous['schema_version']) is not int or previous['schema_version'] != 1
                or previous['scope'] != SCOPE):
            raise ValueError('expected curved Hphi tune checkpoint schema_version 1')
        runs = previous["trial_runs"]
        if type(runs) is not list or any(type(run) is not str or not run.strip() for run in runs):
            raise ValueError("Hphi tune submitted trial paths must be a list of nonempty paths")
        paths = [Path(run) for run in runs]
        # Check the recorded path structure lexically: old directories may no
        # longer exist or may have been replaced since the verified copy.
        if (any(not path.is_absolute() or ".." in path.parts
                or path.name != f"trial-{index + 1:03d}"
                for index, path in enumerate(paths))
                or len({path.parent for path in paths}) > 1):
            raise ValueError("Hphi tune submitted trials require ordered absolute paths with one owner")
        execution = Path(execution).resolve()
        previous["trial_runs"] = [str(execution / path.name) for path in paths]
    return _input(owned)


def is_curved_hphi_tune(directory, state, manifest):
    return (
        KIND in (state.get("kind"), manifest.get("kind"))
        or (directory / INPUT).is_file()
        or (directory / RESULT).is_file()
    )


def _snapshot(directory):
    """Hash the owned worker files while rejecting links and undeclared roots."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Hphi tune job directory must be regular")
    result = {}
    for name in (INPUT, RESULT, "job.json", "manifest.json"):
        result[name] = _digest(directory / name)
        _load(directory / name)
    claim = directory / "worker.claim"
    if claim.is_symlink() or not claim.is_file():
        raise ValueError("Hphi tune worker claim must be a regular file")
    result["worker.claim"] = _digest(claim)
    execution = directory / "execution"
    if execution.is_symlink() or not execution.is_dir():
        raise ValueError("Hphi tune execution must be a regular directory")
    for path in execution.rglob("*"):
        if path.is_symlink():
            raise ValueError("Hphi tune execution files must not be linked")
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = _digest(path)
    return result


def _check_manifest_shape(manifest):
    names = (
        "manifest_version",
        "kind",
        "files",
        "implementation_sha256",
        "source_changed_during_run",
    )
    keys(manifest, names, names, "Hphi tune manifest")
    if type(manifest["manifest_version"]) is not int or manifest["manifest_version"] != 1:
        raise ValueError("Hphi tune manifest_version must be 1")
    implementation = manifest["implementation_sha256"]
    if (
        not isinstance(implementation, dict)
        or not implementation
        or any(
            type(key) is not str
            or type(value) is not str
            or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)
            for key, value in implementation.items()
        )
        or manifest["source_changed_during_run"] is not False
    ):
        raise ValueError("Hphi tune requires stable implementation provenance")


def _validate_checkpoint_files(directory, result, expected_files, start_index):
    """Validate every checkpoint that the worker published, including prefixes."""
    execution = Path(directory) / "execution"
    request_copy = execution / "request.json"
    if request_copy.is_symlink() or not request_copy.is_file():
        raise ValueError("Hphi tune completion requires its owned request copy")
    expected_files.add(request_copy.relative_to(directory).as_posix())
    checkpoint_paths = sorted(execution.glob("checkpoint-*.json"))
    if not checkpoint_paths:
        raise ValueError("Hphi tune completion requires at least one checkpoint")
    trial_count = len(result["trials"])
    checkpoint_numbers = []
    for path in checkpoint_paths:
        try:
            number = int(path.stem.rsplit("-", 1)[1])
        except (IndexError, ValueError) as exc:
            raise ValueError("Hphi tune checkpoint has an invalid ordered name") from exc
        if path.name != f"checkpoint-{number:03d}.json" or number < 0 or number > trial_count:
            raise ValueError("Hphi tune checkpoint number is outside the verified trial prefix")
        checkpoint_numbers.append(number)
        prefix = replay_curved_hphi_tune(_load(path), base_directory=execution)
        if len(prefix["trials"]) != number:
            raise ValueError("Hphi tune checkpoint prefix length differs from its name")
        expected = {key: value for key, value in result.items()}
        for key in ("trial_runs", "trial_sources_sha256", "trials"):
            expected[key] = expected[key][:number]
        expected["decision"] = prefix["decision"]
        expected["status"] = prefix["status"]
        expected["can_resume"] = prefix["can_resume"]
        if _canonical(prefix) != _canonical(expected):
            raise ValueError("Hphi tune saved checkpoint differs from its verified prefix")
    if checkpoint_numbers != list(range(start_index, trial_count + 1)):
        raise ValueError("curved Hphi tune requires every checkpoint from its submitted prefix through completion")
    # Every declared file is accounted for below; this also prevents a hidden
    # linked or unbound checkpoint from being ignored by the manifest.
    expected_files.update(
        path.relative_to(directory).as_posix() for path in checkpoint_paths
    )


def verify_curved_hphi_tune_job(directory, state, manifest):
    """Replay an Hphi worker and verify its state, ancestry, budget, and files."""
    directory = Path(directory).resolve()
    before = _snapshot(directory)
    if state.get("status") != "complete" or state.get("kind") != KIND or manifest.get("kind") != KIND:
        raise ValueError("Hphi tune state and manifest require complete kind=curved_hphi_tune")
    _check_manifest_shape(manifest)
    expected_files = {key: value for key, value in before.items() if key not in ("job.json", "manifest.json")}
    if manifest["files"] != expected_files:
        raise ValueError("Hphi tune manifest must bind all request, checkpoint, and native files exactly")

    data = _owned_input(_load(directory / INPUT), directory / "execution")
    result = read_curved_hphi_tune(directory / RESULT)
    if (
        _canonical(data["request"]) != _canonical(result["request"])
        or state.get("tuning_status") != result["status"]
        or state.get("can_resume") is not result["can_resume"]
        or type(state.get("computed_trials")) is not int
        or state["computed_trials"] != len(result["trials"])
        or state.get("numerical_validation") != "not_checked"
        or state.get("physics") != PHYSICS
        or state.get("scope") != result["scope"]
        or state.get("input_sha256") != {INPUT: before[INPUT]}
    ):
        raise ValueError("Hphi tune job summary differs from its verified checkpoint")

    previous = data["checkpoint"]
    offset = 0 if previous is None else len(previous["trial_runs"])
    if previous is not None:
        if (
            _canonical(result["trial_sources_sha256"][:offset])
            != _canonical(previous["trial_sources_sha256"])
            or _canonical(result["trials"][:offset]) != _canonical(previous["trials"])
        ):
            raise ValueError("Hphi tune resume ancestry differs from submitted checkpoint")
    count = len(result["trials"]) - offset
    limit = data["max_new_trials"]
    if (
        count < 1
        or (limit is not None and count > limit)
        or (result["can_resume"] and (limit is None or count != limit))
    ):
        raise ValueError("Hphi tune trial budget differs from the verified result")

    expected = {INPUT, RESULT, "worker.claim"}
    for index, run in enumerate(result["trial_runs"]):
        relative = f"execution/trial-{index + 1:03d}"
        if run != str(directory / relative):
            raise ValueError("Hphi tune trial is outside its owned execution directory")
        trial_hashes = _snapshot_trial(directory / relative)
        if trial_hashes != result["trial_sources_sha256"][index]:
            raise ValueError("Hphi tune trial native hash differs from its checkpoint")
        expected.update(relative + "/" + name for name in trial_hashes)
    _validate_checkpoint_files(directory, result, expected, offset)
    if set(expected_files) != expected:
        raise ValueError("Hphi tune execution contains missing or undeclared trial files")
    if (
        _load(directory / "job.json") != state
        or _load(directory / "manifest.json") != manifest
        or before != _snapshot(directory)
    ):
        raise ValueError("Hphi tune files changed during verification")
    return result


def start_curved_hphi_tune(manager, request, *, max_new_trials=None, checkpoint=None):
    """Submit a dedicated Hphi tuning worker after strict preflight."""
    with manager.lock:
        if manager.closed:
            raise ValueError("job manager is closed")
        data = _input(
            deepcopy(
                dict(
                    request=request,
                    max_new_trials=max_new_trials,
                    checkpoint=checkpoint,
                )
            )
        )
        identifier = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:10]
        directory = manager.directory(identifier)
        directory.mkdir()
        _write_json(directory / INPUT, data)
        submitted = {INPUT: _digest(directory / INPUT)}
        _state(directory, "queued", kind=KIND, input_sha256=submitted)
        try:
            with (directory / "log.txt").open("x") as log:
                process = subprocess.Popen(
                    [sys.executable, "-m", "superfish_ng.curved_hphi_tuning_jobs", str(directory)],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    env={**os.environ, "OPENBLAS_NUM_THREADS": "1"},
                )
            manager.processes[identifier] = process
        except Exception as exc:
            _state(directory, "failed", kind=KIND, error=str(exc))
            raise
        return identifier


def execute_prepared_curved_hphi_tune(directory):
    """Run one queued Hphi tune directory in a separate worker process."""
    directory = Path(directory)
    state = _load(directory / "job.json")
    if state.get("status") != "queued" or state.get("kind") != KIND:
        raise ValueError("Hphi tune worker requires a fresh queued curved_hphi_tune job")
    with (directory / "worker.claim").open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()) + "\n")
    started = time.monotonic()
    try:
        implementation = _implementation_hashes()
        submitted = {INPUT: _digest(directory / INPUT)}
        if state.get("input_sha256") != submitted:
            raise ValueError("queued Hphi tune input changed before execution")
        data = _input(_load(directory / INPUT))
        _state(directory, "running", kind=KIND, input_sha256=submitted,
               stage="Hphi FEM frequency tuning and final mesh refinement")
        result = execute_curved_hphi_tune(
            data["request"],
            directory / "execution",
            max_new_trials=data["max_new_trials"],
            checkpoint=data["checkpoint"],
        )
        if implementation != _implementation_hashes() or submitted != {INPUT: _digest(directory / INPUT)}:
            raise RuntimeError("implementation or Hphi tune input changed during run")
        portable = deepcopy(result)
        portable['trial_runs'] = [Path(run).name for run in result['trial_runs']]
        _write_json(directory / RESULT, portable)
        files = {
            name: _digest(directory / name)
            for name in (INPUT, RESULT, "worker.claim")
        }
        files.update(
            {
                path.relative_to(directory).as_posix(): _digest(path)
                for path in sorted((directory / "execution").rglob("*"))
                if path.is_file()
            }
        )
        _write_json(
            directory / "manifest.json",
            dict(
                manifest_version=1,
                kind=KIND,
                files=files,
                implementation_sha256=implementation,
                source_changed_during_run=False,
            ),
        )
        _state(
            directory,
            "complete",
            kind=KIND,
            physics=PHYSICS,
            scope=result["scope"],
            tuning_status=result["status"],
            can_resume=result["can_resume"],
            computed_trials=len(result["trials"]),
            numerical_validation="not_checked",
            input_sha256=submitted,
            elapsed_seconds=time.monotonic() - started,
        )
        return result
    except Exception as exc:
        _state(
            directory,
            "failed",
            kind=KIND,
            error=str(exc),
            elapsed_seconds=time.monotonic() - started,
        )
        raise


if __name__ == "__main__":
    try:
        execute_prepared_curved_hphi_tune(Path(sys.argv[1]))
    except Exception:
        traceback.print_exc()
        sys.exit(2)

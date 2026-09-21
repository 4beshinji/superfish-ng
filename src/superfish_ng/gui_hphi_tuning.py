# SPDX-License-Identifier: Apache-2.0
"""Hphi tuning GUI transport for owned checkpoints and native trials."""
import hashlib
import json
import re
from pathlib import Path

from .config import integer, keys
from .hphi_tuning import validate_hphi_tune
from .hphi_tuning_jobs import _owned_input
from .hphi_tuning_saved import _snapshot_trial, read_hphi_tune, replay_hphi_tune
from .jobs import read_job
from .project import parse_json
from .saved_mode_tracking import _canonical


def _checkpoint_directory(manager, identifier):
    """Return a stopped Hphi tune job and its owned execution directory."""
    directory = manager.directory(identifier)
    state = manager.status(identifier, verify=False)
    if state.get("kind") != "hphi_tune" or state.get("status") not in (
        "complete",
        "cancelled",
        "interrupted",
        "failed",
    ):
        raise ValueError("select a stopped Hphi tuning job before opening checkpoints")
    execution = directory / "execution"
    if execution.is_symlink() or not execution.is_dir():
        raise ValueError("Hphi tune execution directory must be a regular directory")
    return directory, execution


def _submitted_data(directory):
    request_path = directory / "hphi-tune-request.json"
    if request_path.is_symlink() or not request_path.is_file():
        raise ValueError("Hphi tune submitted request must be a regular file")
    submitted = request_path.read_bytes()
    data = _owned_input(parse_json(submitted.decode("utf-8")), directory / "execution")
    return request_path, submitted, data


def _saved_checkpoint(manager, identifier, index):
    """Replay one checkpoint and bind it to the selected worker job."""
    integer(index, "checkpoint index")
    directory, execution = _checkpoint_directory(manager, identifier)
    path = execution / f"checkpoint-{index:03d}.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("Hphi tune checkpoint must be a regular file")

    request_path, submitted, data = _submitted_data(directory)
    state = manager.status(identifier, verify=False)
    submitted_hash = hashlib.sha256(submitted).hexdigest()
    if state.get("input_sha256") is not None and state["input_sha256"] != {
        "hphi-tune-request.json": submitted_hash
    }:
        raise ValueError("Hphi tune submitted input changed before checkpoint verification")

    original = path.read_bytes()
    raw_checkpoint = parse_json(original.decode("utf-8"))
    raw_runs = raw_checkpoint.get("trial_runs")
    if isinstance(raw_runs, list):
        for trial_index, raw_run in enumerate(raw_runs):
            expected = str((execution / f"trial-{trial_index + 1:03d}").resolve())
            if isinstance(raw_run, str) and Path(raw_run).is_absolute():
                if str(Path(raw_run).resolve()) != expected:
                    raise ValueError("checkpoint trial belongs to another Hphi tune job")
    result = read_hphi_tune(path)
    if _canonical(data["request"]) != _canonical(result["request"]):
        raise ValueError("checkpoint request differs from selected Hphi tune job")
    previous = data["checkpoint"]
    offset = 0 if previous is None else len(previous["trial_runs"])
    if len(result["trial_runs"]) != index or index < offset:
        raise ValueError("checkpoint trial count differs from selected Hphi tune job")
    # Resume copies the inherited trials into this job. Their contents and
    # decisions must agree, while every path must name the new owned copy.
    if previous is not None and any(
        _canonical(result[key][:offset]) != _canonical(previous[key])
        for key in ("trial_sources_sha256", "trials")
    ):
        raise ValueError("checkpoint ancestry differs from selected Hphi tune job")
    for trial_index in range(index):
        expected = str((execution / f"trial-{trial_index + 1:03d}").resolve())
        if result["trial_runs"][trial_index] != expected:
            raise ValueError("checkpoint trial belongs to another Hphi tune job")
    if original != path.read_bytes() or submitted != request_path.read_bytes():
        raise ValueError("Hphi tune checkpoint or submitted request changed during verification")
    return result


def _checkpoint_indices(manager, identifier):
    _, execution = _checkpoint_directory(manager, identifier)
    indices = []
    for path in execution.glob("checkpoint-*.json"):
        match = re.fullmatch(r"checkpoint-([0-9]{3,})\.json", path.name)
        if (
            match
            and path.name == f"checkpoint-{int(match.group(1)):03d}.json"
            and not path.is_symlink()
            and path.is_file()
        ):
            indices.append(int(match.group(1)))
    return sorted(set(indices))


def hphi_tuning_response(manager, action, data):
    """Serve strict Hphi tuning actions used by the browser and API clients."""
    fields = {
        "hphi-normalize-tune": (("request",), ("request",)),
        "hphi-start-tune": (("request", "max_new_trials"), ("request",)),
        "hphi-resume-tune": (("document", "max_new_trials"), ("document",)),
        "hphi-replay-tune": (("document",), ("document",)),
        "hphi-tune-result": (("id",), ("id",)),
        "hphi-tune-checkpoints": (("id",), ("id",)),
        "hphi-open-tune-checkpoint": (("id", "index"), ("id", "index")),
        "hphi-tune-trial": (("document", "index"), ("document", "index")),
    }
    if action not in fields:
        raise ValueError("unknown Hphi tuning operation")
    allowed, required = fields[action]
    keys(data, allowed, required, "GUI Hphi tuning")

    if action in ("hphi-normalize-tune", "hphi-start-tune"):
        request = data["request"]
        if isinstance(request, str):
            request = parse_json(request)
        validate_hphi_tune(request)
        if action == "hphi-normalize-tune":
            return parse_json(_canonical(request))
        return {
            "id": manager.start_hphi_tune(
                request, max_new_trials=data.get("max_new_trials")
            )
        }

    if action == "hphi-tune-checkpoints":
        return {"id": data["id"], "indices": _checkpoint_indices(manager, data["id"]), "verified": False}

    if action == "hphi-open-tune-checkpoint":
        result = _saved_checkpoint(manager, data["id"], data["index"])
    elif action == "hphi-tune-result":
        directory = manager.directory(data["id"])
        state = read_job(directory)
        if state.get("status") != "complete" or state.get("kind") != "hphi_tune":
            raise ValueError(
                "select a completed Hphi tune job; partial checkpoints can be opened separately"
            )
        result = read_hphi_tune(directory / "hphi-tune-results.json")
    else:
        document = data["document"]
        if isinstance(document, str):
            document = parse_json(document)
        result = replay_hphi_tune(document)
        if action == "hphi-resume-tune":
            return {
                "id": manager.start_hphi_tune(
                    result["request"],
                    checkpoint=result,
                    max_new_trials=data.get("max_new_trials"),
                )
            }
        if action == "hphi-tune-trial":
            index = integer(data["index"], "trial index") - 1
            if index >= len(result["trials"]):
                raise ValueError("Hphi tune trial index is out of range")
            trial = result["trials"][index]
            target = result["request"]["mode_id"]
            ids = trial["current_mode_ids"]
            if target not in ids:
                raise ValueError(
                    "this Hphi tune trial has no individually confirmed target mode"
                )
            path = Path(result["trial_runs"][index])
            before = _snapshot_trial(path)
            if before != result["trial_sources_sha256"][index]:
                raise ValueError("Hphi tune trial changed before import")
            # Hphi's native import API takes an unmanaged ``solution``
            # directory.  The surrounding trial Project remains the source of
            # the exact geometry/identity checks above.
            identifier = manager.import_hphi_result(path / "solution")
            if before != _snapshot_trial(path):
                raise ValueError("Hphi tune trial changed during import")
            return {"id": identifier, "mode": ids.index(target) + 1}

    return {
        "document": result,
        "serialized": json.dumps(
            result, indent=2, ensure_ascii=False, allow_nan=False
        )
        + "\n",
    }

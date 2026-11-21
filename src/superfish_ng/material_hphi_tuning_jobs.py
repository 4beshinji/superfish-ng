# SPDX-License-Identifier: Apache-2.0
"""Isolated workers for owned fixed-material straight Hphi tuning checkpoints.

The tuning decisions and native ownership live in :mod:`material_hphi_tuning_saved`.
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

from . import owned_tuning_worker as _worker
from .config import integer, keys
from .hphi_tuning_saved import _snapshot_trial, CHECKPOINT_KEYS
from .hphi_tuning import _json_types
from .material_hphi_tuning_saved import SCOPE
from .material_hphi_tuning import validate_material_hphi_tune
from .material_hphi_tuning_saved import (
    execute_material_hphi_tune,
    read_material_hphi_tune,
    replay_material_hphi_tune,
)
from .jobs import _digest, _implementation_hashes, _state, _write_json
from .project import parse_json
from .saved_mode_tracking import _canonical


KIND = "material_hphi_tune"
INPUT = "material-hphi-tune-request.json"
RESULT = "material-hphi-tune-results.json"
PHYSICS = "axisymmetric_hphi_rf"


def _contract():
    return _worker.OwnedTuningContract(kind=KIND, input_file=INPUT, result_file=RESULT, physics=PHYSICS, worker_module='superfish_ng.material_hphi_tuning_jobs')




def _checkpoint_policy():
    return _worker.CheckpointPolicy(minimum_number=0, canonical_names=True, complete_prefix=True, missing_prefix_message='material Hphi tune requires every checkpoint from its submitted prefix through completion')


def _verify_checkpoint_files(directory, result, expected_files, offset):
    return _validate_checkpoint_files(directory, result, expected_files, offset)


def _result_document(result):
    portable = deepcopy(result)
    portable["trial_runs"] = [Path(run).name for run in result["trial_runs"]]
    return portable


def _load(path):
    return _worker.load_metadata(path)


def _checkpoint(value):
    """Normalize a submitted checkpoint path before the envelope is serialized."""
    if isinstance(value, (str, Path)):
        return read_material_hphi_tune(value)
    return value


def _input(data):
    """Validate submission against its original sources before copying."""
    names = ("request", "max_new_trials", "checkpoint")
    keys(data, names, names, "Hphi tune job input")
    validate_material_hphi_tune(data["request"])
    if data["max_new_trials"] is not None:
        integer(data["max_new_trials"], "max_new_trials")
    data["checkpoint"] = _checkpoint(data["checkpoint"])
    if data["checkpoint"] is not None:
        previous = replay_material_hphi_tune(data["checkpoint"])
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
        keys(previous, CHECKPOINT_KEYS, CHECKPOINT_KEYS, 'material Hphi submitted checkpoint')
        if (previous['format'] != 'superfish_ng_material_hphi_tune_checkpoint'
                or type(previous['schema_version']) is not int or previous['schema_version'] != 1
                or previous['scope'] != SCOPE):
            raise ValueError('expected material Hphi tune checkpoint schema_version 1')
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


def is_material_hphi_tune(directory, state, manifest):
    return _worker.is_owned_tuning_job(directory, state, manifest, _contract())


def _snapshot(directory):
    """Hash the owned worker files while rejecting links and undeclared roots."""
    return _worker.snapshot_owned_files(directory, _contract())


def _check_manifest_shape(manifest):
    return _worker.check_manifest_shape(manifest)


def _validate_checkpoint_files(directory, result, expected_files, start_index):
    """Validate every checkpoint that the worker published, including prefixes."""
    return _worker.validate_checkpoint_prefixes(directory, result, expected_files, start_index=start_index, replay_checkpoint=replay_material_hphi_tune, policy=_checkpoint_policy())


def verify_material_hphi_tune_job(directory, state, manifest):
    """Replay an Hphi worker and verify its state, ancestry, budget, and files."""
    return _worker.verify_tuning_worker(directory, state, manifest, contract=_contract(), validate_owned_submission=_owned_input, read_result=read_material_hphi_tune, snapshot_trial=_snapshot_trial, validate_checkpoints=_verify_checkpoint_files)


def start_material_hphi_tune(manager, request, *, max_new_trials=None, checkpoint=None):
    """Submit a dedicated Hphi tuning worker after strict preflight."""
    return _worker.start_tuning_worker(manager, request, max_new_trials=max_new_trials, checkpoint=checkpoint, contract=_contract(), validate_submission=_input, write_state=_state)


def execute_prepared_material_hphi_tune(directory):
    """Run one queued Hphi tune directory in a separate worker process."""
    return _worker.execute_tuning_worker(directory, contract=_contract(), validate_submission=_input, execute_trials=execute_material_hphi_tune, prepare_result_document=_result_document, write_state=_state, implementation_hashes=_implementation_hashes)


if __name__ == "__main__":
    try:
        execute_prepared_material_hphi_tune(Path(sys.argv[1]))
    except Exception:
        traceback.print_exc()
        sys.exit(2)

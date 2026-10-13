# SPDX-License-Identifier: Apache-2.0
"""Execution-local reuse of a completely replayed owned curved tune history.

Only worker completion verification uses this context. Public checkpoint reads,
new submissions and restarts always perform the original complete native replay.
Every prefix remains bound to exact owned bytes, request, parent/identity records
and the current implementation. No verified state survives the context.
"""
from copy import deepcopy
from pathlib import Path
from .config import keys
from .curved_hphi_tuning_saved import (
    SCOPE, _checkpoint, _request_copy, _stable, read_curved_hphi_tune,
)
from .hphi_tuning import _json_types
from .hphi_tuning_saved import CHECKPOINT_KEYS, _resolve_trial_runs
from .jobs import _implementation_hashes
from .saved_mode_tracking import _canonical


class _VerifiedCurvedTuningPrefixes:
    """Attest one fresh full replay, then check its owned checkpoint prefixes."""
    def __init__(self, directory, result_file):
        self.directory = Path(directory).resolve()
        self.result_path = self.directory / result_file
        self.execution = self.directory / 'execution'
        self._active = False
        self._result = None
        self._implementation = None

    def __enter__(self):
        if self._active:
            raise RuntimeError('curved prefix replay context is already active')
        self._implementation = _implementation_hashes()
        self._active = True
        return self

    def __exit__(self, error_type, error, traceback):
        try:
            if error_type is None and _implementation_hashes() != self._implementation:
                raise RuntimeError('implementation changed during verified curved prefix replay')
        finally:
            self._active = False
            self._result = None
            self._implementation = None

    def _require_active(self):
        if not self._active:
            raise RuntimeError('curved prefix reuse requires an active worker verification')

    def read_result(self, path):
        """Always read and physically replay the complete owned result afresh."""
        self._require_active()
        self._result = None
        if Path(path).resolve() != self.result_path:
            raise ValueError('curved prefix result must belong to this worker')
        result = read_curved_hphi_tune(path)
        self._result = deepcopy(result)
        return result

    def replay_prefix(self, document, *, base_directory):
        """Compare strict prefix metadata with the freshly verified native chain."""
        try:
            return self._replay_prefix(document, base_directory=base_directory)
        except BaseException:
            self._result = None
            raise

    def _replay_prefix(self, document, *, base_directory):
        self._require_active()
        if self._result is None:
            raise RuntimeError('curved prefix reuse requires a completed native replay')
        if Path(base_directory).resolve() != self.execution:
            raise ValueError('curved prefix must belong to this worker execution')
        document = deepcopy(document)
        _json_types(document)
        keys(document, CHECKPOINT_KEYS, CHECKPOINT_KEYS, 'curved Hphi tune checkpoint')
        if (document['format'] != 'superfish_ng_curved_hphi_tune_checkpoint'
                or type(document['schema_version']) is not int or document['schema_version'] != 1
                or document['scope'] != SCOPE):
            raise ValueError('expected curved Hphi tune checkpoint schema_version 1')
        if (type(document['can_resume']) is not bool or type(document['trials']) is not list
                or type(document['trial_sources_sha256']) is not list):
            raise ValueError('curved tune checkpoint requires boolean can_resume and list trials/sources')
        runs = _resolve_trial_runs(document['trial_runs'], self.execution)
        count = len(runs)
        verified = self._result
        if runs != verified['trial_runs'][:count]:
            raise ValueError('curved prefix trials differ from the fully replayed owner')
        _request_copy(self.execution, document['request'])
        expected = _checkpoint(verified['request'], verified['trial_runs'][:count],
                               verified['trial_sources_sha256'][:count], verified['trials'][:count])
        _stable(runs, expected['trial_sources_sha256'])
        document['trial_runs'] = runs
        if _canonical(document) != _canonical(expected):
            raise ValueError('curved tune checkpoint differs from owned native replay')
        _request_copy(self.execution, document['request'])
        _stable(runs, expected['trial_sources_sha256'])
        return expected

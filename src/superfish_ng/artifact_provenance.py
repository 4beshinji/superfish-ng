# SPDX-License-Identifier: Apache-2.0
"""File hashing and replaceable JSON state; caller owns file-set policy.

The JSON writer replaces mutable metadata. Completion/native publication keeps
its existing exclusive file and final-marker protocols in the calling modules.
"""
import hashlib
import json
import os
import uuid


def atomic_write_json(path, data):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

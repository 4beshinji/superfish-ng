# SPDX-License-Identifier: Apache-2.0
"""Exclusive complete journals; failed staging stays available as evidence."""
import json
import os
from pathlib import Path
import tempfile


def publish_rf_goal_json(path, value):
    """Publish with a no-replace hard link, keeping failed staged bytes separate.

    The temporary directory is beside the target, on the same filesystem.
    A failed or interrupted serialization never becomes a checkpoint filename.
    """
    path=Path(path)
    if path.exists() or path.is_symlink():raise FileExistsError(path)
    if any(p.is_symlink() for p in path.parents):raise ValueError('RF journal parent paths must not be symlinks')
    stage=Path(tempfile.mkdtemp(prefix='.'+path.name+'-',dir=path.parent))/'staged.json'
    with stage.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.link(stage,path)
    stage.unlink();stage.parent.rmdir()

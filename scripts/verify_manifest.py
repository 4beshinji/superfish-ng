# SPDX-License-Identifier: Apache-2.0
"""Verify the shipped manifest after extraction: python scripts/verify_manifest.py."""
import hashlib
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
manifest = root/'MANIFEST.sha256'
if not manifest.exists():
    raise SystemExit('MANIFEST.sha256 exists in packaged ZIPs; build/extract a ZIP first.')
failures = []
count = 0
for line in manifest.read_text().splitlines():
    digest,name = line.split('  ',1)
    path = (root/name).resolve()
    if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        failures.append(name)
    count += 1
if failures:
    print('Manifest FAILED: '+', '.join(failures),file=sys.stderr)
    raise SystemExit(1)
print(f'Manifest PASS: {count} files')

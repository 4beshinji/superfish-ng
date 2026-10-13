# SPDX-License-Identifier: Apache-2.0
"""Duplicate-aware JSON and stable canonical bytes, without domain imports.

Parsing retains the existing JSON decoder policy, including nonfinite constants.
Domain parsers decide accepted values; canonical output rejects nonfinite values.
"""
import json


def parse_json(text):
    """Read JSON while rejecting duplicate keys at every depth."""

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(text, object_pairs_hook=pairs)


def canonical_json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)

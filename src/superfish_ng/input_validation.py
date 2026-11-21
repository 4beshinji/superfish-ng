# SPDX-License-Identifier: Apache-2.0
"""Primitive value checks; independent of Case, projects and operations."""
import math


def positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite positive number")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return float(value)

def integer(value, name, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value

def keys(data, allowed, required, label):
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be an object")
    unknown, missing = set(data) - set(allowed), set(required) - set(data)
    if unknown or missing:
        raise ValueError(f"{label}: unknown keys {sorted(unknown)}, missing keys {sorted(missing)}")

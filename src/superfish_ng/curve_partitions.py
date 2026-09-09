# SPDX-License-Identifier: Apache-2.0
"""Preserve declared native chord counts through the existing reflection order."""


def reflected_segments_per_curve(case):
    counts=case.curve_segments_per_curve
    if counts is None:return None
    tags=case.curved_contour.edge_tags
    seam={i for i,tag in enumerate(tags) if tag.endswith('_symmetry')}
    starts=[i for i in range(len(tags)) if i not in seam and (i-1)%len(tags) in seam]
    if len(starts)!=1:raise ValueError('curve partitions require one connected reflection seam')
    remaining=[];i=starts[0]
    while i not in seam:
        remaining.append(counts[i]);i=(i+1)%len(tags)
    return tuple(remaining+remaining[::-1])

# SPDX-License-Identifier: Apache-2.0
"""Execution-local evidence must not survive source, request or ancestry changes."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng import rf_optimization as engine


class RFOptimizationPrefixReuseTests(unittest.TestCase):
    def test_cached_state_is_copied_and_source_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'trial';directory.mkdir()
            for i in range(3):
                run=directory/f'level-{i}';run.mkdir();(run/'evidence.json').write_text('{}')
            directories=[str(directory)];request={'unit':'test cache ownership only'}
            trials=[dict(index=0,assessment={'value':1})];sources=[engine._trial_sources(directory)]
            cache=engine._VerifiedPrefix();cache.store(request,directories,trials,sources)
            trials[0]['assessment']['value']=2;sources[0][0].clear()
            loaded,_=cache.load(request,directories);self.assertEqual(loaded[0]['assessment']['value'],1)
            loaded[0]['assessment']['value']=3
            self.assertEqual(cache.load(request,directories)[0][0]['assessment']['value'],1)
            with self.assertRaisesRegex(ValueError,'request changed'):cache.load({'unit':'changed'},directories)
            with self.assertRaisesRegex(ValueError,'ancestry changed'):cache.load(request,[])
            with patch.object(engine,'_implementation_hashes',return_value={}):
                with self.assertRaisesRegex(RuntimeError,'implementation changed'):cache.load(request,directories)
            path=directory/'level-0/evidence.json'
            for mutation in ('bytes','removed','added','linked'):
                with self.subTest(mutation=mutation):
                    extra=directory/'level-1/extra.json'
                    if mutation=='bytes':path.write_text('{} ')
                    if mutation=='removed':path.unlink()
                    if mutation=='added':extra.write_text('{}')
                    if mutation=='linked':
                        path.unlink();path.symlink_to(directory/'level-1/evidence.json')
                    try:
                        with self.assertRaises(ValueError):cache.load(request,directories)
                    finally:
                        if path.is_symlink():path.unlink()
                        path.write_text('{}')
                        if extra.exists():extra.unlink()
                    cache.load(request,directories)

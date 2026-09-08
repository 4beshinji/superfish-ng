# SPDX-License-Identifier: Apache-2.0
"""RF peak transport bound to the selected completed job and mode."""
import json
from .config import keys,integer
from .jobs import read_job
from .project import parse_json
from .rf_peak_assessment import assess_rf_peaks,replay_rf_peaks


def rf_peak_response(manager,action,data):
    fields={'assess-rf-peaks':('id','mode'),'replay-rf-peaks':('id','mode','document')}
    if action not in fields:raise ValueError('unknown RF peak operation')
    keys(data,fields[action],fields[action],'GUI RF peaks');integer(data['mode'],'mode')
    directory=manager.directory(data['id']);state=read_job(directory)
    if state['status']!='complete' or not (directory/'solution').is_dir():raise ValueError('select a completed native RF result')
    run=str((directory/'solution').resolve());mode=data['mode']-1
    if action=='assess-rf-peaks':result=assess_rf_peaks(run,mode=mode)
    else:
        document=data['document'];document=parse_json(document) if isinstance(document,str) else document
        if not isinstance(document,dict) or document.get('run')!=run or type(document.get('mode_index')) is not int or document['mode_index']!=mode:
            raise ValueError('select the saved RF peak result and mode before replaying this assessment')
        result=replay_rf_peaks(document)
    read_job(directory)
    return dict(document=result,serialized=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

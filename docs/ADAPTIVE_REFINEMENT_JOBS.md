# N04 適応細分のローカルワーカー

2026-09-08。既存のJobManagerへ`start_adaptive_refinement`を追加した。
[適応計算](ADAPTIVE_REFINEMENT.md)の版1/版2要求を別のローカルPythonプロセスで実行する。
数値計算・追跡・停止基準は同じAPIを使用し、JobManager側で結果を補正しない。

```python
import json
import time
from pathlib import Path
from superfish_ng.jobs import JobManager
from superfish_ng.adaptive_refinement import read_adaptive_refinement

manager = JobManager('out/adaptive-workspace-new')
def finished(identifier):
    while manager.status(identifier)['status'] in ('queued', 'running'):
        time.sleep(0.1)
    state = manager.status(identifier, verify=True)
    if state['status'] != 'complete':
        raise RuntimeError(state)
    return state

try:
    request = json.loads(Path('examples/adaptive_refinement/pillbox_confirmed.json').read_text())
    identifier = manager.start_adaptive_refinement(request, max_new_levels=1)
    state = finished(identifier)
    if state['can_resume']:
        checkpoint = read_adaptive_refinement(manager.directory(identifier) / 'adaptive-refinement-results.json')
        continued = manager.start_adaptive_refinement(request, checkpoint=checkpoint)
        print(finished(continued))
    # 実行中の取消しには manager.cancel(identifier) を使う。
finally:
    manager.close()
```

max_new_levelsを省略すると、適応計算の終端判定まで進める。
指定した水準数だけ処理してPAUSEDになった結果は、別ジョブへ再開できる。
要求の未知項目・不正予算・初期メッシュの品質/要素上限・変更された再開要求は、
ジョブの出力先を予約する前に拒否する。ジョブIDは管理器が生成し、既存出力は上書きしない。

## 実行状態と数値判定

JobManagerの状態はqueued/running/complete/failed/cancelled/interrupted。
`complete`はワーカーが要求された処理を正常に終え、保存・完了情報を公開したことを表す。
適応計算の判定は別の`refinement_status`で、PAUSED/TARGETS_MET/LEVEL_LIMIT/
REFINEMENT_LIMIT/UNVERIFIED等を保持する。上限停止を達成へ変換しない。

完了時の概要はcomputed_levels（先祖を含む総水準数）、can_resume、surface_statusも持つ。
`numerical_validation="not_checked"`、`physical_error_bound=null`を保存する。
TARGETS_METでも物理誤差上界や表面ピークの精度を認定したことにはならない。
独立検証スクリプトの例題合格は、そのジョブ概要を一般の精度認定へ書き換える処理ではない。

## 保存・再検証・取消し

各ジョブのファイルは次の構造を使う。

- adaptive-refinement-request.json: 要求、max_new_levels、再開元チェックポイント。
- execution/: 新しく計算したlevel-NNN/とcheckpoint-NNN.json。
- adaptive-refinement-results.json: 検証済みの最終チェックポイント。
- manifest.json: 要求/結果/新規実行ファイルのhashと実行実装hash。
- job.json / log.txt: ワーカー状態と出力。

新しい水準だけが新ジョブのexecution/へ作られる。先祖の保存先とhashは継承し、
元ジョブへ書き戻したり、古い水準を新しい計算として数えたりしない。
完了時は要求/実装が実行中に変わっていないことを確認してから結果・manifest・complete状態を公開する。

`manager.status(id, verify=True)`または`read_job(directory)`では、通常のファイル完全性検査に加え、
全native場・メッシュ/選択/追跡/判定を再構築する。要求との一致、概要の型/数値状態、
先祖の連続性、max_new_levelsに対する新規水準数、新しい保存先が当該execution/にあること、
必要な水準/チェックポイントがmanifestに含まれることを検査する。
通常の進捗ポーリングではverify=Falseを使い、全再構築が必要な確認時にverify=Trueを指定できる。

取消しは既存の管理器が所有するワーカープロセスに対して行う。
取消し/失敗後は、execution/checkpoint-NNN.jsonのうち読込検証を通ったものを選んで再開できる。
書込み途中のファイルを採用しない。完了と取消しが競合し、完了保存が先に確定した場合は既存管理器の規則でcompleteを保持する。
管理器を閉じて再生成した後も、完了結果をディスクから再検証できる。

## 検証と残件

7検査で実ワーカーの全域確認途中からの再開、取消し時点の生存確認とチェックポイント保持、
版1/2の入力、管理器再生成、数値上限/未確認とジョブ完了の分離、要求/先祖/概要/worker予算/
manifest欠落の拒否、ワーカー例外・実行中要求変更時の非公開を確認する。
数値本体の6検査等は既存のまま標準回帰で確認する。

`python scripts/validate_adaptive_refinement_jobs.py --out out/adaptive-jobs-validation-new`
は版1/版2×尺度1/2のP2円筒を、各2ジョブで部分実行→再開し、管理器再生成後も再検証する。
解析周波数/RQ/G、長さ/正規化相似則、新しい水準だけの計算を記録する。
ここでの例題の要求基準とは別に、解析差f1e-4・RQ/G各0.005で独立比較する。

GUIの開始・取消し・確認段階表示・再開操作への接続は次段階。
一般形状の精度/効率、RFに対応する効率的な選択、曲線局所細分・表面量停止も引き続き残る。

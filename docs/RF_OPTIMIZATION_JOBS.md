# RF探索のローカルジョブと停止後の保存再開

`JobManager.start_rf_optimization(request, max_new_trials=None, checkpoint=None)`は
既存の[RF探索](RF_OPTIMIZATION.md)を別のローカルPythonプロセスで実行する。
FEM・探索・追跡・制約の式は変更しない。ジョブの完了と数値条件の合格は別に表示する。

```python
from superfish_ng.jobs import JobManager
from superfish_ng.rf_optimization_checkpoints import (
    list_optimization_checkpoints, open_optimization_checkpoint,
)
manager = JobManager("out/new-managed-workspace")
identifier = manager.start_rf_optimization(request, max_new_trials=1)
# manager.status(identifier) が complete になるまで通常の状態確認を行う。
state = manager.status(identifier, verify=True)
checkpoint = open_optimization_checkpoint(manager, identifier, 1)
resumed = manager.start_rf_optimization(request, checkpoint=checkpoint)
# 作業終了時には manager.close()。中止は manager.cancel(identifier)。
```

状態のkindはrf_optimization。queued/running/complete/failed/cancelled/interruptedは
ジョブの実行状態で、optimization_statusはPAUSED/SEARCH_COMPLETE/FINAL_UNVERIFIED/
FINAL_CRITERIA_FAILED。computed_trialsとcomputed_fem_solvesは祖先を含む完了試行/解の数。
数値結果が条件未達でも、正常に終了し検証可能なジョブはcompleteになる。
`numerical_validation=not_checked`を保ち、管理層が独立物理検証を追加実施したと主張しない。

完了manifestにはrequest/results、各checkpoint、各試行のlevel-0/1/2の全native Job出力を含む。
読込時は入力・場・追跡・探索順序を再構築し、要約状態、祖先、指定された新規試行数、
新規出力の所属、manifestの必須ファイル集合を照合する。実行中の入力/実装変更は
failedとし、完了manifestを公開しない。

`list_optimization_checkpoints(manager, id)`は停止した当該種別のジョブだけを受理し、
正規のファイル名の番号を返す。これは検証済み結果の一覧ではなく、verified=Falseを返す。
`open_optimization_checkpoint(manager, id, index)`でnative場の再検証と元ジョブへの
所属確認を行う。シンボリックリンク、別ジョブのtrial、改変された入力/祖先/場を拒否する。
実行中のcheckpointを開いて、その直後の変更を暗黙に承認する経路は設けない。

1試行は3水準の解とその検証が完了してから保存する。中止された未完了試行は再開対象に
含めず、保存地点から新しいジョブへ分岐する。元ジョブの部分出力・log・elapsed_secondsを
残し、中止された計算費用をゼロとは扱わない。computed_fem_solvesは完了試行の解数で、
途中中止/失敗した呼出しや別分岐を合算した利用者全体の予算ではない。
GUIの入力・一覧・結果表示・時間合算への接続は後続工程。

## 次のGUI接続で検証すること（未実装）

既存のgui_tuning.pyとweb/app.jsの調整結果カードを参照し、専用のRF探索操作へ接続する。
2変数の範囲/step/tolerance、目的関数/単位、複数制約/尺度、予算を入力・復元・保存し、
数値未達とジョブ失敗を別表示する。長いnative再検証の間も中止/状態確認を塞がないよう、
startのpreflightとmanager.lockの保持範囲を確認する。

試行には3水準があるため、場の選択はtrial_directoriesの配下level-0/1/2を指定する。
既存tuneの単一trial_runsをそのまま使わない。保存済み個別IDの実rankを各水準で確認して
から既存のnative import/表示経路へ渡し、未確認のIDを便宜的にrank 0へ置換しない。
実ブラウザーでは入力保存/復元、完了/未達、中止後のcheckpoint選択・再開、管理器再起動、
場の出所と表示、CLI/Pythonと同じnative入力/結果、外部要求なしを確認する。

## GUI前に解消する待ち時間

`out/rf-optimization-job-preflight-20260909/timing.json`は既存の投入requestを一度ずつ
読み取り専用で計測したもの。新規requestの検査は0.00782秒、1試行checkpointを含む
再開requestは16.498秒だった。一般的な速度の保証ではなく、標準検証と並行した単一観測。
新規FEMやワーカーは実行していない。
現在start_rf_optimizationはこの検証をmanager.lock内で行うため、GUI接続前に検証を
ロック外へ移す。検証中にmanager.close/cancel/statusが応答することと、閉じた後には
ワーカーを作らない再チェックを検証する。この応答性の修正は今回には含まない。

## 受入証拠 — 2026-09-09

基準5229c33。既存tuning jobs7件5.571秒、新規3件216.357秒がPASS。
実FEMの中止/管理器再起動/停止checkpointからの再開、数値未達でも正常なジョブ完了、
別ジョブへの差替え・3水準manifest欠落・祖先変更・投入入力raceの拒否を確認した。
投入予算超過のcheckpoint拒否を追加し、個別1件0.043秒でPASS。

`out/rf-optimization-jobs-independent-20260909`は終了0。初期3解をPAUSEDで保存し、
管理器再起動後に最終確認へ再開、完了解数6でSEARCH_COMPLETE。再度の管理器再起動後も
検証がPASS。初期3水準のnative Projectとmodesは既存CLI出力に完全一致した。
最終球形の独立解析相対差はf2.472e-5、RQ2.525e-6、G1.077e-7、
E比2.314e-4、B比6.077e-6で、既存の独立許容差を満たす。

標準`out/validation-rf-optimization-jobs-20260909`は終了0、738件中736合格・2skip、
unittest1202.231秒。seed9モード19量f差0/RF差最大8.882e-16。
標準/独立/待ち時間観測/終了後426対象hashが一致。driverとログをoutへ保存。
全関連実行終了、ソース固定解除。新規GUI/ブラウザーの検証は行っていない。
D03と全体計画は未完了。親集計8受入・8進行中・16他未受入・1候補、計33は維持。

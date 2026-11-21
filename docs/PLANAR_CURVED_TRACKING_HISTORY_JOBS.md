# 平面曲線の独立履歴CLI-worker

2026-10-07、P09の有界操作leaf。
[独立履歴/過去anchor](PLANAR_CURVED_TRACKING_HISTORY.md)と
[所有比較ジョブ](PLANAR_CURVED_TRACKING_JOBS.md)を共通JobManager/CLIへ接続する。
受入条件は、両形式の全元byteと作成来歴の保持、native/ID連鎖と実過去anchorの完全再生、
元履歴を保った新job回復/延長、実running取消し・新job・管理器再起動・移動後再生である。
P09はIN_PROGRESS。調整CLI-worker/checkpoint/実取消し/再開、実GUI、P09全条件監査は残る。

## ジョブの契約

`planar_curved_tracking_history_jobs.execute_planar_curved_history(pairs,request,new_directory)`
は同期実行、`JobManager.start_planar_curved_history(pairs,request)` は子プロセス実行。
要求は専用 `PlanarCurvedTrackingHistoryRequest`。
入力は専用所有二点directoryまたは完了済み比較job directory。
比較jobを入力すると、投入した元operandと比較結果だけでなく元job/claim/manifest/envelopeも
全byteで所有する。補助logは除く。履歴の実stepにはそのjob内の所有二点を使う。
同じ元比較jobとそのexecutionを二重に指定することは拒否する。

投入前に各二点/比較jobの全物理を検証し、source snapshotを取得する。
投入時のコピー各step/全stepとqueued出版時に全元source hashと所有入力を確認する。
隣接native、tracked count、ID集合、過去anchorの実resolved状態とID、回復要求を
履歴workerで再計算する。不一致はfailedとして停止し、履歴の有効完了を出版しない。
真縮退や上位guardはUNVERIFIED、回復周波数はnullに保持する。

保存先の `planar-curved-history-input.json` はstrict専用 `input_version=1`。
要求と順序付きsource descriptorを持ち、`steps/step-0000/` 等に全元二点/jobをコピーする。
元pathは来歴だけで再生時に開かない。`execution/` に専用所有履歴を保存する。
外側 `job.json`、`worker.claim`、`manifest.json` が実workerの来歴。
manifest version 1 / kind `planar_curved_tracking_history` は全要求/投入step/実行履歴/claimを束縛する。
実行履歴の作成実装も外側workerの作成実装と一致しなければならない。

`read_planar_curved_history` と `read_job(verify=True)` は、保存hashだけでなく
所有履歴の全元E/H/有限guard/ID連鎖/過去anchorを再計算する。
元比較job入力の物理/作成来歴も検証し、実行stepの全snapshotを投入した二点へ束縛する。
要求/報告/step数/個別ID/延長可否と全入力/実装の安定性を照合する。
専用envelopeからも経路を検出し、kind降格や再hashした回復周波数で旧検証へ逃がさない。
余分entryやsymlinkを拒否し、完了後の入力変異もfailedへ戻す。

`tracking_status` は対応/回復のPASS/UNVERIFIEDで、離散精度の保証ではない。
`numerical_validation='not_checked'`、元SI/単位長peak +i/全12場/RF/両R/QのN/Aを保持する。
native帯の順位とIDを分け、連続枝・連続体誤差・表面peak収束を保証しない。

## 回復と延長

`recover_planar_curved_history(history,recovery,new_directory)` と
`JobManager.recover_planar_curved_history` は最後がsubspace PASS/個別未確定/未回復の履歴を受け取り、
実際の過去resolved snapshotへanchorを束縛した新ジョブを作る。
`extend_planar_curved_history(history,next_pair,new_directory,recovery=None)` と
`JobManager.extend_planar_curved_history` はPASSかつmax_steps未満の場合だけ延長する。
新stepで明示回復を行う場合は `recovery` を指定する。
元所有履歴と新完了履歴jobの両方を親として受け入れ、全親履歴を再生してから要求/入力を導出する。
親の全byteは変更せず、投入完了まで親snapshotの不変性を確認する。
新workerはコピーしたstepだけで再生し、元親/元sourceを移動しても処理/再生を継続できる。

## CLI

```sh
uv run --no-sync superfish-ng execute-planar-curved-history history.json --steps PAIR_OR_JOB_0 PAIR_OR_JOB_1 --out NEW_JOB
uv run --no-sync superfish-ng recover-planar-curved-history HISTORY recovery.json --out NEW_JOB
uv run --no-sync superfish-ng extend-planar-curved-history HISTORY NEXT_PAIR_OR_JOB --out NEW_JOB
uv run --no-sync superfish-ng extend-planar-curved-history HISTORY NEXT_PAIR_OR_JOB --recovery recovery.json --out NEW_JOB
uv run --no-sync superfish-ng replay-planar-curved-history HISTORY_JOB
```

全報告をJSON表示し、PASSは終了0、UNVERIFIEDは終了1。
max_steps到達/UNVERIFIEDの延長と不正な回復状態は新保存先作成前に拒否する。
取消し/中断jobを同じ所有先で再実行せず、新jobへ投入する。

## 検証記録

rawは新規 `out/p09-planar-curved-history-jobs-20261007/`。
最初のAPI不在は `api-baseline.log` のModuleNotFoundErrorで確認した。
保存不変量は元二点/jobの全ファイルと投入stepのbyte一致、
実行履歴の全元二点snapshotと投入した二点snapshotの一致である。
先行の実反射parity/rank交換付き楕円→円→楕円→後続を同じ元曲線TEで使い、
回復したeven-x/odd-xと真の円doubletでのnull周波数を分ける。
元native/科学kernel/物理gateを変更しない。

新 `test_planar_curved_tracking_history_jobs` は8種類。
初回、元比較job＋所有二点のbyte/移動再生/kind拒否は `initial-test.log` 1件30.142秒PASS。
安全3件は `safety-test.log` 80.759秒PASS、新job回復/延長・親不変/optional anchor/true doublet/guard CLI停止2件は
`derived-test.log` 142.987秒PASS、実workerと全CLI2件は `runtime-test.log` 199.504秒PASS。
関連は `related-test.log` の旧平面履歴CLI/実worker/kind拒否3、
先行曲線比較jobの元byte/移動/kind拒否1、共通seed完了manifest/上書き拒否1の計5種類、43.202秒PASS。
新8種類＋関連5の分割受入であり、一括suite成功/全P09受入とは表現しない。
37608/34617/53610/54618/71078は全実終端0。追加の83912も実終端0、生存数値handle/worker/製品source固定なし。

実worker試験はrunning状態とprocess.pollがNoneを両方観測して取消し、
同じ元履歴から新jobを完了し、回復worker→延長workerを実行する。
各process.waitの終了コードを回収し、管理器を再起動して全完了を検証する。
元native/二点/親ジョブを移動し、最終所有jobを移動してから全再生する。
claimや状態fileだけを生存の証拠としない。`runtime-evidence.json` に終了状態/IDを保存する。
取消しprocessは終了−15、新履歴/回復/延長の3 processは全終了0を回収した。
生存中の元native四解/元二点二件の移動を明示するため、このworker caseだけを強化して追加実行した。
process.pollがNoneである前後に元sourceを移動し、その後の履歴完了/回復/延長/再起動/移動再生を確認。
`source-move-worker-test.log` は1件115.147秒PASS、handle83912終了0。
`source-move-worker-acceptance/history-job-worker/runtime-evidence.json` に実生存中移動と全終了を保存した。
新8種類の重複実行1件として記録し、新しい9種類目には数えない。
初回test源を `initial-history-job-tests.py` に保全し、他の7新methodのAST完全不変も照合した。

CLI試験はexecute→recover→extend→所有先移動→replayを別実プロセスで行う。
true doublet回復はnull、guard execute/replayは終了1で未確認IDを保持する。
再hashした1.01倍の回復周波数は元native/全anchor replayとの不一致で拒否する。
コピー中の先のsource変異と完了再生後の入力変異もcompleteとして残さない。
変異byteは `safety-acceptance/history-job-mutation/mutated-first-report.json` に保全する。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v <selected cases>
```

新caseと先行曲線比較caseでは `SUPERFISH_CURVED_TUNING_TEST_ROOT` をlogごとの
`{initial,safety,derived,runtime,related}-acceptance` へ設定した。
関連ケース名は `test_planar_tracking_history_saved.PlanarHistorySavedTests` の
`test_cli_start_extend_and_full_replay` / `test_real_worker_manager_restart_reentry_and_cancellation` /
`test_rehashed_summary_and_kind_downgrade_rejected`、
`test_planar_curved_tracking_jobs.PlanarCurvedTrackingJobTests.test_exact_managed_creator_native_and_portable_replay_with_kind_downgrade_rejection` と
`test_jobs.JobTests.test_complete_manifest_detects_missing_output_and_overwrite`。

基準d0fe497から新worker一源と共通jobs/cliの専用入口だけを追加する。
元415製品中413はbyte不変、既存二源は入口追加だけで旧経路の削除/置換なし。
全123カード/依存/anchorは維持する。最終監査はbyte/来歴/台帳だけで、新FEM求解/物理再構築0。
追加前の14job/59snapshot監査は `history-jobs-acceptance-before-live-move.json` /
`final-audit-before-live-move.log` にそのまま保全した（handle14029終了0）。
最終 `history-jobs-acceptance.json` / `final-audit.log` も終了0/PASS、handle17875も実終端。
17完了履歴job/内包と投入を含む73元二点snapshot、元raw親履歴の全hash、
全416作成実装/元415との差分、全123カード/依存/文書anchor、全logと実worker終端を照合した。
全科学源は不変、既存jobs/cliの追加branchの直接利用先を選択した。
新外部資料/依存/legacy参照なし。full/seed validator/実GUIは本leafで未実行。
P09 milestoneで必要な広域検証を行う。円/楕円は合成例で測定構造ではない。

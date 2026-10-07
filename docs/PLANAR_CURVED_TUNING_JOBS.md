# 平面曲線の所有調整CLI-worker

2026-10-07、P09の有界操作leaf。
[元Cartesian P2実調整](PLANAR_CURVED_TUNING.md)と
[所有調整・完全再生](PLANAR_CURVED_TUNING_SAVED.md)を共通JobManager/CLIへ接続する。
受入条件は、元trial九ファイル/creator/claimの保持、要求へ束縛した停止checkpoint、
新job再開、実running取消し・管理器再起動・元source移動中のworker完了、
円の独立絶対周波数と最終細分の両gateである。P09はIN_PROGRESS。
実GUIとP09全条件監査、原互換条件と全123カードgoalは継続する。

## 投入と作成来歴

`planar_curved_tuning_jobs.execute_planar_curved_tune_job(request,new_directory,...)` は同期実行、
`JobManager.start_planar_curved_tune(request,...)` は子プロセス実行。
`max_new_trials` は新規trialだけの正整数予算。`checkpoint` は全物理検証済みの
所有PAUSED checkpointであり、旧trialを別ジョブへコピーしてから新trialを計算する。
要求の一致、strict schema/type、symlinkと再開可否は新保存先作成前に確認する。
ゼロtrial checkpointは明示した所有ファイルから再開する。

`planar-curved-tune-input.json` は専用input_version 1で、要求/予算/相対prefixを保持する。
再開時の `ancestry/` は元request、投入checkpointと順序付きtrialを所有する。
元native五ファイルにproject/job/manifest/worker.claimを加えた九ファイルは全byteでコピーし、
元creator/claimを新workerへ書き換えない。元pathは再生時に開かない。
`execution/` に所有調整のrequest/全checkpoint/元trial/新trialを保存する。

共通管理器は取消し/再起動時にjob状態を書き換える。
そこで `submission.json` に投入envelope/ancestryの不変hashを保存し、
`worker-start.json` に実開始時の投入hash、実装hashとexclusive claim hashを保持する。
停止後のcheckpointもこの要求/元prefixへ束縛する。
新trialのcreatorとclaimは実開始workerに一致し、コピーした旧trialは元来歴を保持する。
投入コピー完了/queue出版と実行完了で全元source/所有入力/実装の安定性を検査する。

## 完了と停止checkpoint

外側manifest version 1 / kind `planar_curved_tune` は投入、開始、claim、結果と全実行byteを束縛する。
`read_planar_curved_tune_job` と `read_job(verify=True)` は元nativeの全E/H、有限guard、
ID継承/過去anchor回復、二分判断と最終固定境界細分の両gateを再計算する。
投入prefix、実行prefix、全checkpointの論理的履歴と新trial数/予算も照合する。
最終結果の全trialを物理再生した後で各prefixを導出し、同じ帯を各prefixごとに重複再構築しない。
専用入力ファイルからもkindを検出し、旧検証への降格を拒否する。
不足/余分entry、リンク、再hashした周波数/判断/claim改変を拒否する。

`read_planar_curved_tune_job_checkpoint(job,index)` はcomplete/cancelled/interrupted/failedの
停止ジョブだけから、そのindexの所有prefixを全物理再生する。
queued/running中は拒否し、要求・投入prefix・新trial作成来歴の一致を検査する。
初回/途中FEM失敗は有効なゼロ/既存prefixとfailure記録を残し、完了manifestを出版しない。
取消し時に書込み中だったtrialを有効prefixへ混ぜず、検証できた保存地点から新jobへ再開する。

`planar-curved-tune-results.json` 内のtrial名は `execution/` を基準とする。
全ジョブを再生する場合はjob directoryを渡す。
単独checkpointを渡す場合は `execution/checkpoint-NNN.json` を使う。
結果JSONだけを別所有先のcheckpointとして読み替えない。

プロセスcompleteは調整目標達成と別である。tuning_statusはTUNED/PAUSED/UNVERIFIED等の判断を保持し、
`numerical_validation='not_checked'` のまま保存する。
元SI、単位長peak +i phasor、全12場/RF、二つの名前付きR/QのN/Aを保持する。
離散精度、連続枝のidentity、表面peak収束の保証を追加しない。

## CLI

```sh
uv run --no-sync superfish-ng tune-planar-curved request.json --out NEW_JOB --max-new-trials 1
uv run --no-sync superfish-ng resume-tune-planar-curved STOPPED_JOB --checkpoint-index 1 --out NEW_JOB --max-new-trials 1
uv run --no-sync superfish-ng resume-tune-planar-curved OWNER/checkpoint-001.json --out NEW_JOB
uv run --no-sync superfish-ng replay-tune-planar-curved COMPLETE_JOB
uv run --no-sync superfish-ng replay-tune-planar-curved STOPPED_JOB --checkpoint-index 1
uv run --no-sync superfish-ng replay-tune-planar-curved OWNER/checkpoint-001.json
```

全報告をJSON表示する。TUNED/PAUSEDは終了0、他の有効な停止判断は終了1、不正入力は終了2。
jobからの再開にはindexを明示し、ファイル入力にindexを指定することは拒否する。
旧取消し/失敗jobを同じ所有先で再実行せず、新jobへ投入する。

## 検証記録

rawは新規 `out/p09-planar-curved-tuning-jobs-20261007/`。
API不在は `api-baseline.log` のModuleNotFoundErrorでFEM前に確認した。
独立不変量は円TMのBessel絶対周波数、実FEMの一様拡大f逆尺度則と全元九ファイルのbyte保存。
円の検索256セル→最終1024セルを実行し、目標差と粗細差を別々に検査する。
数値核・物理gate・benchmarkは変更しない。新外部資料/依存/legacy参照なし。


新 `test_planar_curved_tuning_jobs` は8種類、関連は5種類の分割受入。

- `initial-test.log`：元byte/逆尺度・全job移動、1件/54.881秒、PASS/終了0。
- `safety-test.log`：strict/失敗prefix/再hash拒否、3件/78.696秒、PASS/終了0。
- `runtime-test.log`：CLIと初回worker検査、2件/87.722秒、CLI1成功/worker後片付けERROR、終了1。
- `worker-recheck-test.log`：管理器の所有順序修正後worker検査、1件/51.406秒、PASS/終了0。
- `doublet-test.log`：真の円TE doublet/CLI未確認、1件/30.014秒、PASS/終了0。
- `circle-test.log`：実円TM/最終細分/独立Bessel絶対f、1件/811.905秒、PASS/終了0。
- `related-test.log`：関連直接利用先、5件/111.620秒、4成功/相対root期待値FAIL、終了1。
- `related-path-test.log`：絶対rootで不足関連1件補完、1件/12.767秒、PASS/終了0。

初回worker検査は取消し・新worker完了後、移動した旧jobを登録中の旧管理器がcloseで参照してERRORになった。
旧管理器を閉じ、新管理器で所有コピーへ再開してから元jobを移動する順序へ試験だけを修正し、その1件を再検査した。
共通管理器の取消し/close動作を変更したとは主張しない。
関連所有prefix検査は保存rootを相対指定したため、元試験の絶対trial path期待と一致せずFAIL。
絶対rootへ指定を直して不足1件だけを補完し、科学的な期待値や許容値は変えていない。
元7methodの6は不変、worker methodだけを修正し、真doubletの第8methodを追加した。
元FAIL/ERROR rawと元試験sourceを `initial-tuning-job-tests.py` に保持する。

円TMは検索256セル/最終1024セルの4trialでTUNED。
独立Bessel目標4780938659.800418 Hz、最終実FEM4781070789.776281 Hz、
相対絶対差2.7636827256261043e-5。粗細差208643.6307630539 Hzは別gateでPASS。
元全nativeからE/H/guard/ID/全RFを再生し、TUNED checkpointからの継続は新保存先作成前に拒否した。
真円TE doubletは1trialで個別周波数null/UNVERIFIEDを保持し、completeのままCLI execute/replay終了1、resume終了2。

再現の入口（未使用の保存先を使う）：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache SUPERFISH_CURVED_TUNING_TEST_ROOT=out/p09-curved-tuning-jobs-new uv run --no-sync python -m unittest -v test_planar_curved_tuning_jobs
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache SUPERFISH_CURVED_TUNING_TEST_ROOT=/ABS/NEW_RELATED_ROOT uv run --no-sync python -m unittest -v test_planar_tuning_jobs.PlanarTuningJobTests.test_real_worker_resume_restart_and_original_native_ancestry test_planar_tuning_jobs.PlanarTuningJobTests.test_queued_mutation_and_failure_keep_checkpoint_without_completion test_planar_curved_tuning_saved.PlanarCurvedOwnedTuningTests.test_original_native_scale_and_portable_owner_survive_source_removal test_jobs.JobTests.test_complete_manifest_detects_missing_output_and_overwrite test_planar_curved_tracking_history_jobs.PlanarCurvedTrackingHistoryJobTests.test_cli_execute_recover_extend_and_moved_full_replay
```

この全module一括コマンドを今回実行したとは数えない。上記logの各method選択で受入した。

`tuning-jobs-acceptance.json` / `final-audit.log` はFEM/物理再構築0の最終byte監査。
9受入完了job/15trial snapshot/3copied prefix snapshot、全417作成実装、全投入/開始/manifest/旧九byte/新claimを照合。
負例の再hash jobと後片付けERROR caseは成功job集計から除外した。
元416製品の414はbyte不変、jobs/cliは追加行のみ、新worker1モジュール。
全123 TSV/依存/文書anchorとP09 IN_PROGRESSを維持する。
全数値handleと実workerを実終端まで観測し、元source移動の生存中/取消し−15/再開0を確認した。

共通入口への有界追加と直接消費先に検証を限定した。seed数値/科学kernelは不変。
full/seed validator・実GUI・Hosted CI・Wine/GPU・新外部参照は今回未実行。
先行受入を今回の再実行へ数えず、次に実GUIとP09全条件監査を行う。

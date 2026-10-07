# 平面曲線の所有比較CLI-worker

2026-10-07、P09の有界操作leaf。
[所有二点比較](PLANAR_CURVED_TRACKING_HISTORY.md)を共通JobManagerとCLIへ接続する。
受入条件は、元Case版3/全native/作成来歴を持つ所有入力による比較、
完了時の全元E/H/guard再生、kind改変拒否、実行中取消し・新job・管理器再起動・移動後再生である。
P09はIN_PROGRESS。独立履歴と調整のCLI-worker、調整checkpoint/取消し/再開、実GUIと全条件監査は残る。

## APIと保存契約

`planar_curved_tracking_jobs.execute_planar_curved_tracking(previous,current,request,new_directory)`
は同期実行、`JobManager.start_planar_curved_tracking(previous,current,request)` は子プロセス実行。
要求は専用 `PlanarCurvedTrackingRequest`。元native五ファイルか完了job八/九ファイルを受け入れ、
Case/Project/表示単位/元claim/creator/import来歴をそのままコピーする。
投入時には元解を物理検証し、上位guardの存在を確認して全byteを保存する。
E/H比較・有限guard/全比較予算検査はworkerで実行する。予算不足はworkerのfailedとして停止する。
元入力を投入後に移動しても、workerは所有入力だけを使う。

保存先の `planar-curved-tracking-input.json` はstrict `input_version=1` の専用envelopeで、
元要求と両sourceの情報/全hashを持つ。元pathは来歴だけで再生時に開かない。
`operands/previous/`、`operands/current/` に元全byte、`execution/` に専用所有二点結果を保存する。
`job.json`、`worker.claim`、`manifest.json` は外側workerの実行来歴。
子プロセス出力の `log.txt` は補助logで完了manifestの物理入力に含めない。
claimのPIDは作成来歴であり、処理生存の証明ではない。

準備時はコピー各側/全側とqueued出版時に元source/所有入力hashを確認する。
workerはfresh queued +専用kindと入力hashを確認し、exclusive claimで二重実行を拒否する。
元全nativeを復元して専用所有比較を実行し、全入力/実装hash不変で完了を保存する。
完了manifestはversion 1 / kind `planar_curved_tracking` で、全envelope/両operand/実行結果/claimを束縛する。
実行内の作成実装と外側workerの作成実装も一致しなければならない。

`read_planar_curved_tracking` と `read_job(verify=True)` は所有層の全元E/H/有限guardを再計算する。
投入要求、元byte、完了報告、要約、全入力/実装の安定性まで検査する。
専用envelopeの存在からも経路を検出し、両kindを旧平面kindへ書き換えても旧検証へ逃がさない。
余分entryやsymlink、再hashしたID報告も拒否する。
完了後の変異を検出した場合はfailedへ戻し、completeとして残さない。

ジョブの `tracking_status` は対応のPASS/UNVERIFIED、`individual_ids_complete` は個別IDの状態。
`numerical_validation='not_checked'` は離散誤差/精度の全検証を実施したという誤解を避ける。
周波数順位や係数/全12場/RF/peak +i規約、SI/単位長、両R/QのN/Aは元解を保持する。
連続枝・連続体誤差・表面peak収束の保証ではない。

## CLI

```sh
uv run --no-sync superfish-ng execute-planar-curved-tracking PREVIOUS CURRENT tracking.json --out NEW_DIRECTORY
uv run --no-sync superfish-ng replay-planar-curved-tracking DIRECTORY
```

いずれも全報告をJSON表示し、対応PASSは終了0、UNVERIFIEDは終了1。
未確認結果も元native/停止理由を所有保存し、個別IDはnullに保つ。
取消し/中断jobを同じ所有先で再実行しない。新ジョブに入力を投入する。

## 検証記録

新API不在は `out/p09-planar-curved-tracking-jobs-20261007/api-baseline.log` の
ModuleNotFoundErrorで確認した。
独立な保存不変量は、元sourceとqueued operand/実行operandの五/九ファイル完全byte一致。
先行核の[実反射parity/rank交換](PLANAR_CURVED_IDENTITY_RECOVERY.md)と同じ元曲線TEを使い、
odd-x/even-xからeven-x/odd-xへの実rank交換を、元係数/全場/RFを変えずに再生する。
科学kernelは元byte不変で、worker/CLIから解析式やlegacy求解へ差し替えない。

新 `test_planar_curved_tracking_jobs` の6種類を次の分割で受入した。

| log | 対象 | 結果 |
| --- | --- | --- |
| `initial-test.log` | 完了job九byte/元creator、native五byte、移動/全再生、kind降格拒否 | 1件8.741秒PASS |
| `safety-test.log` | queued要求変異/links/旧Case拒否、後のコピー中の元source変異・完了後変異、再hash報告拒否 | 3件13.829秒PASS |
| `runtime-test.log` | 実running取消し・新job・元source移動/管理器再起動/中断queued/所有先移動、実CLI PASS/guard停止/両再生 | 2件25.711秒PASS |

取消し前に実process.pollがNoneかつ状態runningを観測した。取消しprocessは終了−15、
新processはwaitで終了0を回収した。claimやjob状態だけで生存を推測しない。
`runtime-acceptance/job-worker/runtime-evidence.json` に両job ID/終了状態と管理器再起動を記録する。
元sourceを移動してから子プロセスが完了し、元pathの再読込を要求しないことも確認した。

関連は `test_jobs` 全7、旧 `test_planar_tracking_jobs` の
`test_cli_execution_and_replay` / `test_actual_worker_cancel_restart_and_source_import` と
P08 `test_planar_curved_operations.PlanarCurvedOperationsTests.test_actual_cli_solve_replay_and_original_si_probe`。
初回は最後のクラス名を `PlanarCurvedOperationTests` と誤記し、
`related-test.log` は9成功/1読込ERROR、10件4.554秒終了1。そのlogを全成功と数えない。
不足の正しい1件だけを `related-curved-cli-test.log` 1.800秒PASSで補完し、関連10種類を分割受入した。

全実行は既存locked環境で次のprefixを使い、raw rootはlogごとの未使用directoryを指定した。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v <selected cases>
```

新caseでは `SUPERFISH_CURVED_TUNING_TEST_ROOT` を
`out/p09-planar-curved-tracking-jobs-20261007/{initial,safety,runtime}-acceptance` に設定した。
新6種類と関連10種類の分割証拠であり、一括suite成功/全P09受入とは表現しない。
61167/39091/75840/95073/41610は全実終端。生存数値handle/worker/製品source固定なし。

基準be1e0c6から、新worker一源と共通 `jobs.py` / `cli.py` への専用入口だけを追加した。
投入時の最後のsource再確認を追加する前の初回worker源を `initial-worker-source.py` に保存し、
初回完了manifestの元hashと完全一致を確認した。その他の作成実装は最終415源へ束縛する。
最終byte/台帳監査は `jobs-acceptance.json` / `final-audit.log`。
監査は終了0/PASSで、新6/関連10種類の分割証拠と実process終了を照合した。
元414製品中412は全byte不変で、変更した二源も旧経路の削除/置換なし。
全123カード/依存/anchorは不変、5完了jobの全元入力/実行/native/claim/manifestを照合する。
新FEM求解/物理再構築を最終hash監査へ追加しない。

数値/shared FEM/依存を変更していないため、追加branchの直接利用先を選択した。
full/seed専用validator/実GUIは今回未実行。P09 milestoneの全条件監査では必要な広域検証を行う。
新外部資料/依存/legacy参照なし。円/楕円は合成例で測定構造ではない。

# P02-b — 回復付き平面所有履歴

2026-09-22、開始点 `93a7f5a`。P02-aの元場回復を所有履歴・CLI・workerへ接続し、P02-bを受入。
親P02/調整P02-c/GUI監査P02-dは未完。

## 所有と継承

PlanarTrackingHistoryRequestの版2は非空のidentity_recoveriesを持つ。
各項目はafter_step_indexと完全なPlanarIdentityRecoveryRequestで、位置は厳密増加・履歴内、
anchor_snapshot_indexは回復対象より前でなければならない。版1要求/結果は保持する。

全保存pairを元nativeから再生し、隣接snapshotの全native hashを一致させる。
初期snapshotの個別IDは元要求と有限スペクトル群を検査し、途中snapshotは
直前の検証済み結果（回復があれば採用後の状態）から取得する。
anchorのIDが実際の過去の解決済みsnapshotと一致しなければ拒否する。
回復核へ渡す3場は所有された各pairのprevious/currentから読み、パス文字列だけを信頼しない。

raw stepsは書き換えず、identity_recoveriesへ継承比較・anchor比較・集合判定・anchor全native hashを保存する。
次のリンクだけが回復後の個別ID/集合を継承する。元のnull ID集合を成功結果で上書きしない。
継承/回復が未確認なら延長不可。回復後の実順位を元順位に戻す処理は行わない。

既存の所有保存は全pairと各nativeのbytesを新しい出力へコピーする。
回復も新しい履歴を作り、元の未回復履歴を保持する。
移動後は所有コピーだけで再生し、旧source pathは来歴としてのみ扱う。
延長時には既存回復イベントを引き継ぎ、全祖先を再検証する。

## 操作

- API：`recover_planar_history(history, recovery, new_directory)`。
- CLI：`recover-planar-history HISTORY RECOVERY_JSON --out NEW_DIRECTORY`。既存execute/extend/replayにも版2を渡せる。
- worker：`JobManager.recover_planar_history(history, recovery)`。既存の専用履歴workerとkindを使い、回復を含む全入力/実装hashを固定する。

要求/再生は [planar_tracking_history.py](../src/superfish_ng/planar_tracking_history.py)、
所有保存は [planar_tracking_history_saved.py](../src/superfish_ng/planar_tracking_history_saved.py)。
元場の独立解析・縮退/guardの検査は[P02-a](PLANAR_IDENTITY_RECOVERY.md)を維持する。
新たな損失モデルや物理値を導入せず、xy面積・U′[J/m]のまま比較する。

## 検査記録

`out/p02-planar-recovery-20260922/history-tests.log`で、実CLI回復、worker回復/延長、
管理器再起動、所有移動/再生、回復前raw保持、元hash不変、真縮退停止・誤anchor拒否を検査する。
新3件88.678秒PASS、session 60848終了0。元のnull集合を残した実ID回復、回復後延長、移動後の全再生を確認した。

追加で、P01の版8比較要求を保存pairへ渡すと、旧入口がCase型不一致で拒否する欠落を実FEMで再現した。
`out/p02-planar-recovery-20260922/mapping8-missing/failure.json`に記録し、失敗出力が作られないことも確認した。
純APIのP01比較/tuneが通ることと、保存pairの入口対応を区別する。入口に版8の厳密再生成を接続し、独立した保存pair/移動再生の検査を追加してPASS。要求や幾何の拒否条件を緩和していない。


追加の `history-related.log` は新2＋既存7の9件71.269秒PASS、session 64747終了0。
新2件は版8の保存入口/移動後再生と、回復イベントの改変をmanifestへ再hashしても拒否する検査。
既存7件は履歴核5件、CLI1件、実worker/再起動/中止1件。子P02-bの計5新規検査は分割証拠として扱う。
最初の3件後の製品追加は版8保存入口の分岐のみで、回復履歴の核は無変更。
全プロセスは終端回収し、src固定を解除した。

共通実行prefixは `OPENBLAS_NUM_THREADS=1 PYTHONPATH=.:src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v`。
新規は [test_planar_recovered_history](../tests/test_planar_recovered_history.py)、
関連は `test_planar_tracking_history` と
`test_planar_tracking_history_saved.PlanarHistorySavedTests.test_cli_start_extend_and_full_replay` / `test_real_worker_manager_restart_reentry_and_cancellation`。

初期の源nativeを変更せず、全pairコピー/manifest、回復anchorの全native hash、raw継承比較と回復イベントを別々に検査した。
この変更は平面履歴と追加CLI/manager分岐に限定され、FEM核・seed TM・材料核は無変更。
全suite/seed validatorは実行していない。新しい外部参照・依存・物性値・旧版実行なし。
次はP02-cの調整要求/検索/最終細分/worker再開。P02-dの実GUIと親P02は未完。

# 曲線Hφ調整workerと所有完了検証

2026-09-22。H13-d継続。`JobManager.start_curved_hphi_tune`から別プロセスで専用調整を実行する。[独立追跡履歴](CURVED_HPHI_HISTORY.md)と[調整回復の所有操作/H13-d監査](CURVED_HPHI_TUNING_RECOVERY_SAVED.md)も後続段階で受入済み。GUI/親H13/全goalは未完了。

## 契約

専用kindは`curved_hphi_tune`。要求を`curved-hphi-tune-request.json`に封じ、`execution/`の要求copy、全Project/native、完了prefixと`curved-hphi-tune-results.json`を所有する。開始prefix（新規なら000、再開なら提出済み試行数）から最終までのcheckpoint全番号を要求する。worker claimは排他的に作成し、開始前後の要求/実装hashを照合する。完了manifestは全所有ファイルと実装来歴を結び付ける。要求不正時はジョブを割り当てない。

`read_job(..., verify=True)`は専用検証へdispatchし、元FEM/RFと全追跡決定を再計算する。提出済みcheckpointの元pathは来歴として不変に保ち、検証用copyだけを現在の所有nativeへ結び直す。提出時点のhash/要求/順序/全履歴を引き継ぐため、元出力が移動しても検証できる。最終結果のdisk参照は相対pathで、ジョブ全体の移動にも対応する。

中止・例外では完了manifestを作らず、完了済みcheckpointから新ジョブを作る。中止されたjobの部分trialを周波数評価に加えない。管理器を閉じて再生成した後も完了jobは所有履歴を検証する。計算プロセスのcompleteと物理的TUNEDを分離し、PAUSED/UNVERIFIED等は`tuning_status`に保持する。

## 検証と残作業

標準環境は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v ...`。証拠は`out/h13-curved-tune-worker-20260922/`。

- `before.log`：起動API未実装を再現、1件error、終了1。
- `after.log`：新workerの不正入力、完了後例外、実中止/新job再開、管理器再起動/元出力移動と提出履歴改変拒否の4件PASS、291.510秒、終了0。
- `move-regression.log`：全job移動とmanifest/再hash済み偽prefix拒否、旧直線worker2件、共通`test_jobs`7件、計10件PASS、76.650秒、終了0。
- `prefix-before.log`：初期checkpointを削除してmanifestも更新すると拒否できない不備を再現。1件FAIL、53.358秒、終了1。曲線実行が必ず公開する開始prefixから最終までの連続性を検査するよう修正。`prefix-after.log`で全job移動/再hash改変/欠落拒否と実中止/新job再開の2件PASS、153.526秒、終了0。修正範囲の新規/再開検証を再実行し、数値・旧dispatchが不変の先行証拠は再利用した。全handle終端。新5件＋関連9件の分割証拠を保持する。

科学数値は変更せず、[所有API/CLIの元係数・全RF・Maxwell尺度則](CURVED_HPHI_TUNING_SAVED.md)を維持する。共通jobsへの変更は専用起動/検証dispatch追加だけで、seed/FEM/full-suiteを実施したとは主張しない。曲線穴付きProject所有と実曲線ID回復のworker操作は[追加受入](CURVED_HPHI_TUNING_RECOVERY_SAVED.md)で確認した。

## 来歴

既存自作`hphi_tuning_jobs`のプロセス・所有manifest検査構造を曲線専用要求/保存APIに適用した。初期checkpoint000とportable結果を曲線契約に合わせる。旧直線版の保存形式・検証を変更しない。新外部資料・依存・legacy参照なし。

# P02-d — 平面回復のGUI接続（進行中）

2026-09-22、開始点 `7c84a4f`。調整フォームの版1固定を解消する第一段階。
P02-d/親P02は未完。調整・履歴の操作を接続し、APIと隔離フォームで部分検証。実ブラウザーでの回復/延長・中止再開・サーバー再起動後表示は残る。

## 調整フォーム

多項式アフィン変形と法則JSON、追加回復なし/固定試行/最新解決試行の選択、固定anchor番号、
回復比較controlsを追加した。版1/2/3の読込→編集→保存で有効な項目を保持する。
法則/controlsのJSON文字列をそのままstrict APIへ送るため、重複キーをクライアントで消さない。
形状法則と探索範囲の一致・単位・全区間非退化は既存サーバーvalidatorが検証する。

試行一覧の下に、元tracking IDと採用ID、初期診断、回復元/親/現試行、回復比較・判定、周波数nullを含む記録を表示する。
結果を開いた場合は元要求からフォームを復元し、再開には保存checkpointを使う。
回復結果で元native/RFを変更しない。調整/追跡数値核は今回無変更。

## 検査と未完範囲

`node --check src/superfish_ng/web/planar.js` PASS。
`node scripts/verify_planar_tune_form.mjs` は4種類の要求の完全一致を確認しPASS。
これは実製品のフォーム関数を隔離実行する検査で、DOM・実ブラウザー・物理受入ではない。
ログ `out/p02-planar-recovery-gui-20260922/form.log`。

共通Python prefix：`OPENBLAS_NUM_THREADS=1 PYTHONPATH=.:src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v`。
既存 `test_gui_planar_tuning` 4件30.620秒PASS（transport.log）。
追加の `PlanarTuningGuiTests.test_recovery_checkpoint_resume_and_actual_native_import` は別ログ recovery-transport.logで1件82.337秒PASS。両ツールhandleは終了0。
実worker・checkpoint/API再生・対象順位・取込NPZ全配列一致を確認する範囲であり、画面クリックの証拠とはしない。

次工程は調整と履歴の候補/採用ID表示を実ブラウザーで検査する。
その後に全P02条件を監査する。新依存/外部資料/旧版実行はない。全suite/seed validatorは実行しない。

## 履歴回復と版8の保持

開始点 `26705f5`。`planar-normalize-recovery` と `planar-recover-history` を追加し、
完全な回復要求をstrictに検証して既存所有履歴workerへ接続した。
GUIではanchor番号と追跡フォームから要求を構成でき、完全JSONの保存/読込もできる。
元の履歴は変更せず新履歴を作る。履歴条件の版2回復配列を読込/保存時にも保持する。
結果表示には元比較・候補・採用ID・回復周波数nullを含む全イベントを保持する。
既存の次段階引継ぎは回復後の `current_identity_groups` を利用する。

版8の追跡要求が `loadTracking` で矩形へ変わる不具合を独立した要求一致検査で再現した。
元Project・法則・両試行値・両細分段数を指定する写像入力欄を追加し、版8を保持する。
次段階では値/細分段数を指定し直す案内を表示する。数値核は無変更。

証拠は `out/p02-planar-history-gui-20260922/`：

- tests.log：`test_gui_planar_recovery.PlanarRecoveryGuiTests`、新2件65.106秒PASS。
  回復→延長→管理器再起動、元履歴全hash不変、取込nativeの全ファイルbytes一致。
  真の正方形縮退ではUNVERIFIED・回復周波数nullを維持。重複JSONキー/未知キー拒否。
- related.log：`test_planar_tracking_history_saved.PlanarHistorySavedTests.test_gui_history_extension_and_native_import`、1件22.043秒PASS。
- form-before.log：`node scripts/verify_planar_tracking_form.mjs .../form-requests.json`、修正前は版8が矩形へ変わり終了1。
- form-after.log：同じ2要求（既存矩形と実validatorで生成した版8）が完全一致し終了0。
  この隔離フォーム検査は実ブラウザーの代替ではない。

新2件と関連1件はPython/API変更後の検査。最後の版8修正はJS/HTMLだけで、Pythonや数値経路は変更していない。
全handleは終端回収済み。実HTTP/Chrome受入と全P02監査を次に行う。

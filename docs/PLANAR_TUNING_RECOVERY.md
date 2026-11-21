# P02-c — 平面調整の明示ID回復

2026-09-22、開始点 `97a29ed`。P02-cを受入。親P02のGUI操作・全条件監査はP02-dに残す。

## 要求と判定

`superfish_ng_planar_tune` schema_version 3は `identity_recovery` を必須とする。
`anchor_selection` は `fixed_trial` または `latest_resolved_trial`、両者とも完全な追跡 `controls` を保存する。
前者だけが非負整数の `anchor_trial_index` を要求する。
矩形寸法・多角形uniform_scaleと、P01の `deformation` / `shape_law` に対応する。
版1/2の要求・再生を保持し、過去checkpointの意味を変更しない。

新版は初期試行も元場の自己比較、有限スペクトル/上側guard、個別ID成立を検証する。
未確認なら周波数と目標差をnullにして停止する。これは版3の追加契約である。
後続は親との通常比較を先に保存し、集合として成立して個別IDだけが未解決の場合に回復を試す。
元形状・両試行値・細分段数から完全な比較を生成し、[回復核](PLANAR_IDENTITY_RECOVERY.md)で再計算する。
guard失敗を回復で迂回しない。真の縮退、未解決/未来anchor、回復失敗は周波数評価に使わない。

イベントはanchor・parent・currentの番号、phase、回復結果を保存する。
元trackingのnull IDを上書きせず、採用trial IDを別に保持する。
回復後も目標周波数gateと最終メッシュ差gateを別判定する。
実装：[planar_tuning.py](../src/superfish_ng/planar_tuning.py)、[planar_tuning_recovery.py](../src/superfish_ng/planar_tuning_recovery.py)。

## 保存・操作と証拠

checkpoint外側版1と内側版3要求を保存し、全native/Projectから完全再生する。
実CLI `tune-planar` と既存workerを通り、別出力へ再開する。
旧試行の絶対パス参照とhash照合という既存契約を維持するため、checkpoint単体を移動可能な所有アーカイブとは呼ばない。
履歴の所有コピーは[P02-b](PLANAR_RECOVERED_HISTORY.md)の別契約である。

| 条件 | 結果 |
| --- | --- |
| 実矩形TE順位交換、検索/最終細分 | 高さ0.2 m、幅0.18→0.214 m。独立c/(2w)相対差1e-4、元集合IDはnull、採用IDはx,y。回復と両gate PASS |
| 真縮退/参照不成立 | 初期/現試行が正方形、未到達anchorの各例でUNVERIFIED、周波数/目標差null、再開不可 |
| 多項式版3 | 最新anchor 0→1、最終細分は版8比較、完全再生PASS |
| CLI/worker/再起動 | CLI検索→別worker最終細分→管理器再起動で同じID。元全ファイルhash不変、改変拒否PASS |
| 実取消し/再開 | 初期検証後に生存workerを中止、checkpoint不変、別workerで回復検索、初期試行の重複生成なし |
| 旧形式 | 旧調整、P01形状対応、既存worker検査14件PASS |

元E場の独立正弦形状とRF不変はP02-a、固定U′とE/H尺度則は[P01](PLANAR_AFFINE_TUNING.md)の独立検査を併用する。
今回これらの数値核は変更していない。元native/RFを回復結果に合わせて書き換えない。
通常比較の集合gap 0.08と回復の既定controlsを要求に明記した試験であり、失敗後の許容値緩和ではない。

共通prefix：`OPENBLAS_NUM_THREADS=1 PYTHONPATH=.:src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v`。
ログ：`out/p02-planar-tuning-recovery-20260922/`。

- kernel.log：`test_planar_tuning_recovery`、3件65.166秒PASS。
- jobs.log：`test_planar_tuning_recovery_jobs`、2件52.097秒PASS。
- related.log：`test_planar_tuning test_planar_affine_shape_mapping test_planar_tuning_jobs`、14件72.061秒PASS。

全handle終了0。平面調整の新分岐と対応生成に影響を限定し、全suite/TM seed validatorは実行しない。
新しい外部資料・依存・物性値・旧版実行はない。GUI受入は後続カードで行う。

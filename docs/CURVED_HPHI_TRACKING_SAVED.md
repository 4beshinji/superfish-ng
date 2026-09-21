# 元曲線Hφ追跡pairの所有保存とworker

2026-09-22。H13-dの独立追跡履歴に必要なpair段階。`execute_curved_hphi_tracking`/`read_curved_hphi_tracking`と`JobManager.start_curved_hphi_tracking`を追加。順序付き履歴、過去anchor回復、CLI/GUI操作は後続で、H13-d/親H13/全goalは未完了。

## 保存契約

専用`CurvedHphiTrackingRequest`版1の全P2参照領域、元native/比較native chart、比較幾何、ID集合、予算を保存する。入力は元曲線native五ファイルまたは検証済みHphi job。前者は保存Caseの既定Projectを明示生成し、後者は元Project byteを保持する。両側を所有import jobとしてコピーし、native byteを全て保存する。

専用kindは`curved_hphi_tracking`。`tracking.json`/`sources.json`/`tracking-results.json`と両側の元Project/nativeをmanifestに結び付ける。source pathは来歴であり、公開再生は所有copyだけを読む。元入力を移動しても再生できる。元解/RFの再検証後に完全二次領域のE/H Gramと有限比較スペクトルから追跡を再計算し、再hashされた偽IDも拒否する。追跡のPASSは連続経路のID証明や連続誤差保証ではない。

コピー前に元曲線型、正モードguard数、比較次数/全P2直径、DOF予算、元領域制限と完全被覆、共通分割/サンプル予算を検査する。workerは排他的claimと入力/実装hashで実行を封じ、途中入力変更や再実行を拒否する。計算のcompleteと物理対応のPASS/UNVERIFIEDを分離する。中止後は新jobを作る。

## 検証

標準環境は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v ...`。証拠はignored `out/h13-curved-tracking-owned-20260922/`。

- `before.log`：専用保存モジュール未実装を再現、終了1。
- `after.log`：`test_curved_hphi_tracking_jobs`新3件PASS、71.810秒、終了0。合成二次shear同軸の全P2一様変形、所有Project/native byte保持、元入力移動後の再生/再import、再hash偽ID拒否、worker中止/管理器再起動/偽kind拒否、待機中入力変更/リンク/予算拒否。
- `regression.log`：直接利用先`test_hphi_tracking_jobs test_hphi_jobs`計11件PASS、101.747秒、終了0。
- `preflight.log`：サンプル予算と直線native型の拒否を同じ予備検査ケースへ追加し、1件PASS、11.997秒、終了0。全handle終端。先行成功後のsrc差分は未使用importと重複format文字列の除去だけで、数値/保存/worker処理は不変。

数値追跡核、solver、場係数、RF規約、許容値は変更しない。科学受入は[曲線追跡核](CURVED_HPHI_TRACKING.md)を保持し、本段階は元nativeの全byte不変と再生同一性を検査する。計画全体や全suite/seedを受入済みとはしない。

## 来歴

既存自作`hphi_tracking_jobs`のコピー/来歴/manifest/worker構造を専用曲線要求へ適用した。幾何予備検査は既存の完全二次比較・Bernstein直径を使用する。追加外部資料・依存・legacy参照なし。合成形状を実測構造とは扱わない。

# 曲線Hφ調整の所有保存・再生

2026-09-22。H13-dの第一段階。専用Python APIとCLIを追加。[worker接続の検証](CURVED_HPHI_TUNING_WORKER.md)は別段階で記録し、独立追跡履歴の所有保存は後続に残す。H13-d、親H13、全計画は未完了。

## 契約と受入対象

`execute_curved_hphi_tune`は未使用の出力を作り、request.jsonと各trialの元Projectおよびnative五ファイルを所有する。各候補の追跡、ID回復event、幾何診断と決定を専用版1 checkpointへ格納する。disk参照は所有直下の相対pathで、出力全体を移動できる。

`read_curved_hphi_tune`/`replay_curved_hphi_tune`は元Projectの全P2形状・加速座標を要求から再構築し、nativeの元場/RFを検証してE/H追跡、回復、探索決定を再計算する。checkpoint内の周波数、IDや状態を信頼しない。新しい調整候補のFEM solveは呼ばないが、比較空間によるスペクトル検証は行う。

再開は検証済みPAUSED checkpointだけを受け入れ、所有元ファイルを新しい出力へコピーする。初期checkpoint（新規なら000）と完了prefixを保ち、新trial失敗時はfailureを分離して不完全なtrialを評価として公開しない。既存出力の再使用、path逸脱、symlink、余分なnativeファイル、要求/結果の改変を拒否する。

実行中は検証済み元場と評価をメモリで保持し、各試行の前後に所有全ファイルhash、要求copy、実装hashを照合する。同じbyteから全prefixの数値比較を毎回繰り返さない。外部再生と再開入口では必ず全履歴を再構築する。既存直線版のpath/hash/copyとJSON書出しだけを共用し、旧要求formatは変更しない。

## 検証

標準環境は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v ...`。
証拠はignored `out/h13-curved-owned-tune-20260922/`。

- `before.log`：専用モジュール未実装によるsetUpClassエラー、0件。変更前の不足を再現。
- `after.log`：`test_curved_hphi_tuning_saved`初期3件PASS、62.112秒。完了ログ確認。元曲線nativeの係数/周波数と全RFの同一性、所有再開、元出力と所有全体の移動、偽周波数/bytes/strict schema/要求変更拒否。tool handle出力が切れたため、この実行のexit codeは未回収。
- `ownership-regression.log`：追加2件（失敗時prefix保全、path/symlink拒否）と旧保存2件・元曲線native4件、計8件PASS、200.791秒、handle終了0。対象は`test_curved_hphi_tuning_saved.CurvedHphiTuneSavedTests`の`test_failed_resume_preserves_verified_prefix`/`test_traversal_and_symbolic_links_rejected_before_native_read`、`test_hphi_tuning_saved.HphiTuneSavedTests`の`test_owned_layout_replay_and_resume`/`test_native_tampering_and_request_change_are_rejected`、`test_curved_hphi_saved`全4件。新5件・関連6件を分割して確認した。

fixtureは小さい合成二次shearの正半径同軸領域で、実測構造ではない。物理アルゴリズムは変更せず、保存前後の元係数/全RF不変をこの段階の独立した保存不変量とする。穴付き非一様調整や実曲線回復の物理受入は[H13-c](CURVED_HPHI_TUNING.md)の証拠を保持する。本段階だけでは回復eventの所有再開、独立追跡履歴、CLI/worker中止・管理器再起動、実GUIを受入済みとしない。全suite/seed検証は未実施。

## 来歴

既存自作の曲線元native検証、追跡/調整、直線版所有ファイル検査を接続した。追加外部資料・依存・legacy参照なし。solver、場係数、RF規約、物理許容差は変更しない。

## CLI接続（H13-d継続）

曲線専用の厳密要求formatを使う。既存`tune-hphi`の直線要求は変更しない。

```sh
uv run --no-sync python -m superfish_ng tune-curved-hphi request.json --out out/new-curved --max-new-trials 1
uv run --no-sync python -m superfish_ng replay-tune-curved-hphi out/new-curved/checkpoint-001.json
uv run --no-sync python -m superfish_ng resume-tune-curved-hphi out/new-curved/checkpoint-001.json --out out/new-resumed --max-new-trials 1
```

出力は毎回未使用のpathを指定する。`--max-new-trials`は今回の新試行数で、途中PAUSEDをエラーとは扱わない。TUNED/PAUSEDは終了0、UNVERIFIED/REFINEMENT_FAILED等の物理未達は1、不正要求/改変/終端結果の再開は2。未確認IDの周波数は評価値として使わない。

CLI証拠は`out/h13-curved-tune-cli-20260922/`。`before.log`はコマンド未登録を再現し終了1。`test_curved_hphi_tuning_cli`の不正要求・実solve/resume/portable replayと既存直線CLIケースの計3件は`after.log`でPASS（202.989秒、終了0）。曲線未確認停止の追加1件は`guard.log`でPASS（31.198秒、終了0）。新3件と既存1件の分割証拠で、全handle終端を確認した。実solveでは全P2一様拡大に対するMaxwell周波数逆比例を独立照合し、コピーの全RFも一致させる。APIの数値・保存処理には変更を加えない。このCLI検査はworker中止/管理器再起動やGUI検証を代替しない。

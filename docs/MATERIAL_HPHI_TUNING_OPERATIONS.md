# 材料Hphi調整のCLIとワーカー

H16-cの最新受入：[所有操作の条件別監査](MATERIAL_HPHI_OPERATION_ACCEPTANCE.md)。回復/最終細分を含む操作検証まで成功。H16-d GUIと親H16は未完了。以下の段階別記録は当時の範囲を示す。

2026-09-22、H16-c。材料専用保存形式をCLIと実プロセス境界へ接続する。回復を含む全工程の操作受入とH16-d GUIは別途監査する。

```
tune-material-hphi REQUEST --out NEW_DIRECTORY [--max-new-trials N]
resume-tune-material-hphi CHECKPOINT --out NEW_DIRECTORY [--max-new-trials N]
replay-tune-material-hphi CHECKPOINT
```

TUNED/PAUSEDは終了0、UNVERIFIEDなどの未達結果は終了1、不正要求/保存形式は終了2。再開可能な物理検証済みPAUSEDのみ新規出力へ再開する。再生は元材料nativeから判断を再計算し、新試行solveを呼ばない。

`JobManager.start_material_hphi_tune(request,max_new_trials=...,checkpoint=...)`は専用`material_hphi_tuning_jobs`プロセスを起動する。kindは`material_hphi_tune`、入力/結果は`material-hphi-tune-request.json`と`material-hphi-tune-results.json`、全試行とcheckpointはexecution以下に所有する。共有のJobManager中止・一覧・管理器再起動を利用する。

投入時は元checkpoint全祖先を検証し、再開先にprefixを所有コピーする。保存後の検証は、元投入文書を改変せず、作業用コピーのpathだけを所有試行へ結び直す。元フォルダーの移動後も要求、native hash、周波数、判断、回復状態を再計算して照合する。リンクや欠損を元ソースから補わない。全prefixをmanifestへ束ね、余分な試行や欠損checkpoint、再hashした偽判断も拒否する。

workerは単独claimとqueued入力hashを検査し、実行前後の入力/実装hashを照合する。完了した調整状態と材料物理のscopeを保存する。中止/実行失敗は以前の完成checkpointを保持し、未完成試行を完了manifestで公開しない。

## 検査記録と来歴

`test_material_hphi_tuning_cli`は実二層材料FEMのuniform_scale周波数比1/1.2、1試行保存から別出力への再開、元/所有出力移動後の再生、新試行solve禁止、guard未確認の終了値と再開拒否、専用形式を検査する。

`test_material_hphi_tuning_jobs`は実workerのpause/resume、中止から新規workerへの再開、管理器再起動、全worker移動、入力文書不変、元全native/prefix照合、hash/周波数/判断/path/要求の改変拒否、欠損/リンク、再hashされたprefix改変、注入失敗後のcheckpoint保持を検査する。

材料起動API未実装のAttributeErrorを先に確認した。実行ログは`out/h16-material-tuning-operations-20260922/`。`initial.log`は新8件307.737秒PASS、`related.log`は関連1件70.743秒PASS、いずれも終了0。全handleと実workerの終端を確認し、実行中は製品実装を固定した。全suite/seed validator/GUIは未実行。関連は既存Hphi調整CLIの実行/再開/再生・終了値。

既存自作曲線調整のプロセス/所有構造を専用材料保存とrunnerへ接続した。材料FEM coreとseed TMは変更せず、新外部資料・依存・legacy参照なし。回復有効ケースの全nativeと実最終細分を伴う操作監査は、この基本CLI/worker検査とは分ける。

実行コマンド（共通prefixは`OPENBLAS_NUM_THREADS=1 PYTHONPATH=.:src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python`）:

```
-m unittest -v test_material_hphi_tuning_cli test_material_hphi_tuning_jobs
-m unittest -v test_hphi_tuning_saved.HphiTuneSavedTests.test_cli_tune_resume_and_replay_names_and_exit_codes
```

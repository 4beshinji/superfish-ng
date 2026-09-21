2026-09-21：要求版2の[非一様直線Hφ調整](HPHI_SHAPE_TUNING.md)で同軸3寸法・明示頂点変位とAPI/所有保存/CLIを追加。以下の版1契約は維持する。新写像のworker/GUI操作受入はH09-d。

# Hφ周波数調整の専用契約

作業カード [H01](development-plan/02-hphi.md#h01)（親D02/P03/P04）の成果物。
H01で仕様を固定し、H03で`hphi_tuning.py`のstrict要求reader・試行生成を実装した。
H04で実FEM runnerと判断再構築を実装し、H05で所有保存・再生・再開CLIを接続した。
workerはH06、GUIはH07で接続済みである。
後続H02〜H16は本書の名称・状態・保存契約を実装し、本書を実装済み範囲に合わせて更新する。

## 目的と範囲

軸対称m=0 Hφ（閉同軸・正半径一般断面・軸接続・曲線・材料）について、
形状変数を二分探索して目標周波数へ調整する専用workflowを定義する。
既存の平面調整 [PLANAR_TUNING.md](PLANAR_TUNING.md) を構造の雛形とし、
共有するのは`tuning._decision`にある物理非依存の二分判定のみとする。
Hφの零モード処理・比較測度・加速量規約は既存の専用物理仕様を正本とし、平面要求を読み替えない。

段階（`scope`）は次の順に広げる。v1で公開するのは`vacuum_uniform_scale`のみ。

| scope | 形状 | 追加カード | 備考 |
|---|---|---|---|
| `vacuum_uniform_scale` | 真空（同軸/正半径/軸接続）の一様尺度 | H02〜H07 | 無次元`uniform_scale` |
| `coaxial_dimensions` | 同軸の内外半径/長さ | H08,H09 | m単位、非相似 |
| `general_piecewise_affine` | 軸/穴を保持する明示区分アフィン | H08,H09 | 自動対応は推測しない |
| `curved_meridional` | 曲線穴付き二次領域 | H11〜H13 | 採用候補の二次境界を最終細分で保つ |
| `fixed_material` | 固定実数正値εr/μrの幾何変形 | H14〜H16 | 材料値変更は別要求 |

## 版と識別子

- 要求: `format="superfish_ng_hphi_tune"`、`schema_version=1`。
- trial checkpoint: `format="superfish_ng_hphi_tune_checkpoint"`、`schema_version=1`。
- 失敗記録: `document_type="hphi_tune_failure"`。
- 使用する`HphiProject`は`superfish_ng_hphi_project`版1、nativeは各専用
  `*_saved`の`schema_version=1`（[hphi_native.py](../src/superfish_ng/hphi_native.py)）。

## 要求（v1）

計画の補足仕様（[02-hphi.md](development-plan/02-hphi.md)）の名称を確定する。

| 項目 | 契約 |
|---|---|
| `project` | 専用`HphiProject`（`CoaxialCase`/`HphiMeshCase`/`AxisHphiCase`。v1は真空に限定） |
| `parameter` | `uniform_scale`（無次元）。v1の唯一の値。`stored_energy_j`/`conductivity_s_per_m`は**受理しない** |
| `mapping` | `{"kind":"uniform_scale"}`。v1はこの一種のみ。`same_vacuum`は使わない（下記） |
| `bounds` / `parameter_tolerance` | 正の増加2値、同じ変数単位での二分停止幅 |
| `target_hz` / `frequency_tolerance_hz` | 目標周波数と正の許容差（Hz） |
| `initial_ids` / `mode_id` | 初期の正周波数prefix帯域の一意IDと対象ID。計算モード数より少なくし上側guardを保持。`mode_id ∈ initial_ids` |
| `controls` | `HphiTrackingControls`の全項目（overlap/margin/quadrature/candidate/overlay/dofs/gram上限） |
| `max_trials` | 探索試行上限。受理候補の最終細分は**別予算**で最大1回 |
| `refinement_levels` / `max_triangles` / `max_dofs` | 最終細分の段数（1〜8）・要素/自由度予算 |
| `mesh_frequency_tolerance_hz` | 同じ対象ID・同じ形状の探索/最終細分周波数差の正の上限 |

要求は全てJSONへ正規化して保存する。NumPy由来の型・bool数値・NaN/Infを拒否する。

## 検証（`validate_hphi_tune`）

FEM実行前に拒否する。

- 形式/版の不一致、重複キー、未知項目、boolを数値として渡した項目、NaN/Inf。
- `bounds`の非増加・逆転、非正値、`parameter_tolerance`が幅を超える。
- `initial_ids`が一意でない、上側guardがない、`mode_id`が帯域外。
- 未対応の`project`型（材料/曲線をv1へ混入）、未対応`parameter`/`mapping`、
  `stored_energy_j`/`conductivity_s_per_m`を周波数形状変数として指定。
- `refinement_levels`範囲外向け、または最終細分予算が`max_triangles`/`max_dofs`を超える。
  **出力予約の前に**最終細分予算を検査する。

## 試行生成（`trial_hphi_project(request, value, phase)`）

- 常に**元Project**から候補を生成し、探索途中のメッシュを累積変形しない。
- `phase`は`'search'`/`'refinement'`。二度生成した同一値は同一Project（決定的）。
- v1の`uniform_scale`は幾何・メッシュ・加速座標を正の尺度`s`で相似に写す。
  軸区間・位相原点も同じ尺度で変形する。境界/軸/穴のトポロジーを維持し、
  穴消失・反転・軸移動・境界未被覆を生成段階で拒否する。
- 最終細分は元の採用候補だけを親にし、最後に計算した形状を基準にしない。

## 実行（`run_hphi_tune(...)`）

実専用FEM→元場の比較→個別ID確認→（確認済みのみ）周波数評価→二分判断、の順で進む。
実装は`run_hphi_tune(request, *, max_new_trials=None)`（メモリー上の実行）、
`assess_hphi_tune(request, solutions)`（全元FEMからの判断再構築）。返値`HphiTuneRun`は
`report/projects/solutions`を持つ。初期試行もE/H自己比較とguard診断を通す。
探索試行の比較親は常に初期試行、最終細分の比較親は採用候補であり、二分ブラケットの親と混同しない。
所有保存は`execute_hphi_tune(request, directory, *, max_new_trials=None, checkpoint=None)`、
再生は`replay_hphi_tune(document)`、ファイル読込を含む検証は`read_hphi_tune(path)`で行う。
既存runner（[hphi_native.py](../src/superfish_ng/hphi_native.py)、
[hphi_jobs.py](../src/superfish_ng/hphi_jobs.py)）の専用FEM型をそのまま使う。

- 場比較は既存の`hphi_field_grams`/`hphi_mass_coupling`/`project_hphi_coefficients`を使い、
  零モード・正則化は各空間の既存契約に従う。
- 個別IDが全て確認できない試行は周波数を`null`とし、ブラケット更新に使わない。
- 失敗解・未確認解を成功として保存しない。要求精度未達を`TUNED`にしない。

## 状態遷移と停止理由

`tuning._decision`が返す共有理由に加え、Hφ固有の理由をrunnerが付す。
`can_resume`は`PAUSED`のときのみ真。

| status | 意味 | 周波数 | 再開 |
|---|---|---|---|
| `PAUSED` | 中止、または`max_new_trials`到達で保存 | 評価済みのみ | 可（checkpoint選択） |
| `TUNED` | 目標差と粗細差の**両ゲート**を満たす | あり | 不可（完了） |
| `UNBRACKETED` | 探索範囲内に符号変化なくブラケット不成立 | 確認済みのみ | 不可（範囲変更は新要求） |
| `UNVERIFIED` | 個別ID未確認・集合合流・guard不足 | null | 不可（改善は新要求） |
| `MESH_LIMIT` | 要素/自由度上限超過（Hφ固有） | 超過試行はnull | 不可（改善は新要求） |
| `REFINEMENT_FAILED` | 最終細分で目標/粗細ゲート未達 | あり | 不可（改善は新要求） |
| `ITERATION_LIMIT` | `max_trials`到達 | 評価済みのみ | 不可（改善は新要求） |
| `PARAMETER_LIMIT` | 二分点が`parameter_tolerance`未満 | あり | 不可 |

`MESH_LIMIT`は`max_triangles`/`max_dofs`/`max_overlay_triangles`のいずれか超過で発生し、
`tuning._decision`の共有語彙へ無断追加しない。H04で共有判定と分離した専用停止として実装した。候補探索の`max_candidate_tests`超過は比較未確認として`UNVERIFIED`で停止する。

## 予算とゲート

- 探索予算`max_trials`と最終細分予算（`refinement_levels`/`max_triangles`/`max_dofs`）は別に管理する。
- 目標ゲート`frequency_tolerance_hz`と粗細ゲート`mesh_frequency_tolerance_hz`を**別判定**する。
  両方を満たすときだけ`TUNED`。片方のみは`REFINEMENT_FAILED`または`UNVERIFIED`として区別する。
- 小残差を物理精度上界へ読み替えない。

## 保存

保存する一試行は次を保持する（[PLANAR_TUNING.md](PLANAR_TUNING.md)の試行dictに対応）。

`index`, `value`, `phase`, `parent_index`, `status`, `current_mode_ids`,
`frequency_hz`（未確認はnull）, `target_error_hz`, `tracking`（比較要求/結果・継承ID/群・
実順位・stopping reason）, 実Project/nativeの所有先とhash。

checkpointは要求・全試行nativeの所有先・`trial_sources_sha256`・`trials`・`decision`・
`status`・`can_resume`・`scope`を持つ。出力先は**新規作成のみ**、既存を上書きしない。

H05の保存runnerは`hphi_tuning_saved.py`の
`execute_hphi_tune`/`replay_hphi_tune`/`read_hphi_tune`である。出力は次の所有構成を持つ。

```text
request.json
checkpoint-NNN.json
trial-NNN/project.json
trial-NNN/solution/{case.json,mesh.npz,fields.npz,results.json,manifest.json}
```

`trial_runs`はこの出力先直下の順序付き`trial-NNN`を指し、各
`trial_sources_sha256`は`project.json`と5個のnativeファイルの相対パス別SHA-256である。
native readerが再計算する周波数、場、全RF量を保存し、再生時に各Project、native manifest、
ファイルhash、判断履歴を照合する。再開は過去のtrial一式を新規出力先へコピーしてから
新しい試行を追加するため、再開先は元出力のファイルに依存しない。

## replay / resume の許容・禁止変更

`replay_hphi_tune(...)`は所有した要求/全nativeから判断履歴を再構築し、保存時との一致を確認する。
`resume`は要求と一致する`PAUSED`のみ許可し、常に新規ディレクトリへ書く。

- 許可: `max_new_trials`の変更、checkpoint選択。
- 禁止: 目標/許容差/境界/変数/ID帯域/対応方針の変更。元外部パスの移動は所有nativeで許容する。
- 要求・係数・試行順序・親の改変、同名競合、不完全保存は拒否し、完了扱いしない。

## CLI と終了コード

H05で固定した。既存`tune`/`tune-planar`と同じ引数構成に合わせる。

```sh
python -m superfish_ng tune-hphi REQUEST.json --out out/hphi-tune-new --max-new-trials 2
python -m superfish_ng resume-tune-hphi out/hphi-tune-new/checkpoint-002.json --out out/hphi-tune-rest
python -m superfish_ng replay-tune-hphi out/hphi-tune-rest/checkpoint-004.json
```

終了0は`PAUSED`/`TUNED`。未確認・未達等は1。入力/例外は2（[cli.py](../src/superfish_ng/cli.py)の既存規約）。
例は合成同軸であり、実機構造ではない。

## worker と GUI

- workerは[H06](development-plan/02-hphi.md#h06)で`hphi_tuning_jobs.py`をJobManagerへ登録した。
  `planar_tuning_jobs.py`の契約（kind、入力/結果ファイル名、要求所有、checkpoint選択、
  別ジョブ再開、ロック解放、完了manifestの`numerical_validation`区別）をHφの所有保存へ適用する。
  workerの公開結果はjob直下、所有trial/checkpointは`execution/`直下に置き、実中止後も完了済み
  checkpointを再利用できる。完了manifestは要求・全native・全checkpointを束縛し、失敗時は公開しない。
- GUIは[H07](development-plan/02-hphi.md#h07)で`gui_hphi.py`/`gui_hphi_tuning.py`/
  `web/hphi.js`/`hphi.html`へ要求編集/読込、開始/中止、保存地点選択、再開、両周波数ゲート、
  対象IDと実順位、対象元場を追加した。倍率は無次元、周波数はHz、Project座標はSI保存で、
  Projectの表示単位とは分離している。停止ジョブのcheckpointは行番号を選択して完全replayし、
  対象試行の確認済みIDから元nativeを既存Hφ結果表示へ渡す。URLの`tune`で完了結果を再読込できる。
  API/worker回帰とChromium headlessの画面初期化は確認済み。sandboxのloopback bind制約により、
  実ブラウザーの開始→中止→別ジョブ再開→元場クリック列は未確認である。

## `same_vacuum`制限を越える前提

現行`HphiTrackingRequest`は`mapping='same_vacuum'`を保存・読込で強制し
（[hphi_tracking.py](../src/superfish_ng/hphi_tracking.py)）、
`hphi_field_overlap._reject_unsupported_comparison`は材料/曲線解を拒否する。
Hφ調整は**これらを拡張する前提**で設計する。

- 追跡（`track_hphi_modes`）の`same_vacuum`は既存版1として維持する。
- 調整は`mapping`オブジェクトで形状法則を宣言し、`same_vacuum`を流用しない。
- scope拡張（H08/H11/H14）で、各段の比較写像・全境界被覆・正Jacobian・
  体積/面積の独立積分を検査してから物理を有効化する。未確認の自動対応は推測しない。

## 独立不変量（H02/H04の正本）

全長を正数`s`倍し、全周の蓄積エネルギー`U`を固定したとき、対応点で

- `f → f/s`
- E/Hは`s^(-3/2)`倍
- 正半径の`q=rHφ`は`s^(-1/2)`倍、軸接続の`u=Hφ/r`は`s^(-5/2)`倍
- 加速軸が有効で座標/位相原点も同じ尺度で変形した場合、両R/Q・G・TTFは尺度不変
- 同じ非磁性壁導電率では`Q0 → s^(1/2)`倍

元q/u係数の一致だけで元E/Hの一致を代用しない。尺度変換の係数/座標を新しいFEM解やRF量として保存しない。
異方変形・同軸一寸法変更では上式を適用せず、H08以後の写像と独立参照を使う。
N/Aの量には尺度比較を行わない。

## 受入例（入力 → 期待状態）

1. **成功**：合成同軸の`uniform_scale`を`bounds=[1,2]`、`target_hz`=解析共振の半分、
   `mesh_frequency_tolerance_hz`を達成可能値に設定 → 探索→最終細分で`TUNED`、`can_resume=false`。
2. **ブラケット不成立**：`bounds`が目標を挟まない → `UNBRACKETED`、確認済み周波数のみ。再開不可、範囲変更は新要求。
3. **個別ID未確認**：実順位交差または縮退で上側guard不足 → `UNVERIFIED`、`frequency_hz=null`、
   失敗解をブラケットに使わない。再開不可、改善は新要求。
4. **要素上限**：`max_triangles`/`max_dofs`を最終細分が超える要求 → FEM前に`validate_hphi_tune`が拒否。
   実行中の超過は`MESH_LIMIT`で保存し、上限を完了に読み替えない。
5. **中止**：`max_new_trials`到達または実中止 → `PAUSED`、所有checkpoint、`can_resume=true`。
6. **最終細分失敗**：目標は満たすが粗細差が`mesh_frequency_tolerance_hz`超 → `REFINEMENT_FAILED`
   （`TUNED`と区別）。目標差未達も同様に達成扱いしない。

拒否例：`stored_energy_j`/`conductivity_s_per_m`を`parameter`へ指定、未知`mapping.kind`、
材料/曲線Projectをv1へ指定、NaN/bool数値、`bounds`逆転、`mode_id`が`initial_ids`外。

## 既存APIとの対応

| 新設候補 | 責務 | 既存の基礎 |
|---|---|---|
| `validate_hphi_tune(request)` | 専用形式/版・Project・変数/単位・範囲・目標/許容差・ID/guard・予算を検査 | `planar_tuning.validate_planar_tune`の構成 |
| `trial_hphi_project(request, value, phase)` | 元Projectから候補生成（search/refinement） | `HphiStudy.projects()`の相似変換 |
| `run_hphi_tune(...)` | 実FEM→比較→ID確認→周波数評価→二分判断 | `hphi_native.solve_hphi`、`hphi_field_overlap`、`tuning._decision` |
| `execute_hphi_tune(...)` | 全試行のProject/native所有保存とPAUSED再開 | `hphi_tuning_saved.py`、`hphi_native.save_hphi_run` |
| `replay_hphi_tune(...)` | 所有nativeから判断履歴を再構築 | `planar_tuning.replay_planar_tune` |
| `hphi_tuning_jobs.py` | 所有/別プロセス/中止/保存地点/再開の管理 | `planar_tuning_jobs.py`、`hphi_jobs.py` |

## 検査候補（H02以降）

計画の候補に従う。新規`tests/test_hphi_tuning.py`（H03〜H05）、
`tests/test_hphi_tuning_jobs.py`（H06）、`tests/test_gui_hphi_tuning.py`（H07）、
専用`scripts/validate_hphi_tuning.py`（API/CLI/native/二尺度と失敗例）。
H02は`test_hphi_tracking`等へ独立尺度検査を追加する。H05の専用検証は実FEMと
`scripts/validate_hphi_tuning.py`で行い、worker以降の検査は後続カードで行う。

## 2026-09-21 レビュー修正

H07：再開時にコピーしたtrialの絶対パスを投入元パスと比較していたため、GUIの
保存地点選択が失敗していた。継承prefixはnative/RFを含む全ファイルhashと判断履歴で
照合し、全trialパスは再開先ジョブへの所属を検査する。コピー直後のcheckpointも選択できる。
追加回帰では修正前に継承地点/追加地点の2エラーを再現した。

`UV_CACHE_DIR=/tmp/superfish-review-uv-cache OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests
uv run --no-sync python -m unittest test_gui_hphi_tuning -v`：2件PASS、74.370秒。
実workerで両地点の再生・元場取込・全native/RFのhashと判断履歴保持、別ジョブ差替えと
改変拒否を確認した。ブラウザーのクリック列は未実行。数値核の変更はなくseed/fullは未実行。
新規外部資料・依存・legacy資産は使用していない。

H06：投入時の元source検証と、保存後の所有コピーによる検証を分離した。
`_input`は投入/worker開始時に元sourceを検査する。`_owned_input`は保存済み投入記録の
深いコピーだけを`execution/trial-NNN`へ対応付け、通常の完全replayで要求・全native/RFのhash・
判断履歴を再検証する。元パスは記録として保持し、保存した投入ファイルは書き換えない。
完了worker検証とGUIの停止checkpoint検証がこの経路を共有する。コピーが欠落/改変した場合や
リンクへ差し替えられた場合は拒否し、元sourceで代用しない。

修正前の追加回帰は、元ジョブ移動後の管理器再作成で`Hphi tune trial must be a regular directory`
を再現した。修正後の実行コマンド：

```sh
UV_CACHE_DIR=/tmp/superfish-review-uv-cache OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests uv run --no-sync python -m unittest test_hphi_tuning_jobs test_gui_hphi_tuning -v
```

6件PASS、185.788秒、終了0。元出力移動後の管理器再作成・GUI結果表示・継承/追加checkpoint、
投入記録不変、hash/周波数/判断/パス/要求の改変、コピー改変/欠落/リンク差替え拒否を確認。
既存の実worker中止/再開、失敗時checkpoint保持とmanifest非公開、別ジョブ差替え拒否もPASS。
数値核・保存schemaは変更していないため、専用数値validator・seed/fullは未実行。
ブラウザーのクリック列は未実行。新規外部資料・依存・legacy資産は使用していない。

## 実装記録

- **H05**（`feat: Hφ調整の所有保存とCLI再開を実装する`）：
  `hphi_tuning_saved.py`を追加し、H04の各完了試行を独立した`Project`と専用nativeの
  所有ディレクトリへ保存した。再生はsolverを呼ばずにnativeのFEM/RF復元、試行Project、
  尺度付きE/H追跡、個別ID、親、二分判断、目標/粗細ゲートを再計算し、保存hashと一致しない
  要求・係数・順序・親・nativeを拒否する。PAUSED再開では履歴prefixを新規出力へコピーし、
  外部の元出力を移動しても再開先を再生できる。`tune-hphi`、`resume-tune-hphi`、
  `replay-tune-hphi`の終了コード（成功0、未達1、入力/例外2）をCLIへ追加した。
  `test_hphi_tuning_saved` 5件（実FEMを含む、終了0）、H05指定の既存回帰/H04依存15件
  （347.129秒、終了0）、専用validatorの9実FEM・全17チェック（終了0）で、CLIの実経路、
  native改変/要求改変拒否、未確認終端、元出力移動後の再生を確認した。rawは
  `out/hphi-tuning-h05-final-20260916-rerun3`に保存した。
  新規外部資料・依存・旧SUPERFISH比較はない。次はH06のworker中止・再起動である。

- **H06**（`feat: Hφ調整workerの中止と再起動を接続する`）：`hphi_tuning_jobs.py`を追加し、
  `JobManager.start_hphi_tune`、worker claim、入力hash、所有checkpoint、完了manifest、
  別JobManagerからの検証へ接続した。H05のstandalone配置に加え、worker結果をjob直下、
  所有trialを`execution/`へ置く配置をreaderが再生する。PAUSED checkpointを新規出力へ複製して
  再開し、実プロセス中止後の完了checkpointを再利用できる。API/workerの試行、native hash、
  判断、対象IDを照合し、失敗時はcompletion manifestを公開しない。
  `tests.test_hphi_tuning_jobs` 4件（実workerの中止/再開を含む、43.784秒、終了0）がPASS。
  新規外部資料・依存・旧SUPERFISH比較はない。次はH07のGUI接続である。

- **H07**（GUI接続）：`gui_hphi_tuning.py`を追加し、H06 workerの要求を既存Hφ画面へ接続した。
  要求の正規化/同一ファイル再読込、開始/中止後の保存地点列挙、選択時の所属・祖先・native完全
  replay、PAUSED保存地点からの別ジョブ再開、確認済み対象IDの実順位による元native取込を検査する。
  結果表は探索/最終細分、倍率、Hz、目標差、二つの周波数ゲート、未確認理由を表示し、取込後は
  既存のHφ RF量/N/A表示を使う。`test_gui_hphi_tuning` 2件を含むHφ GUI回帰8件（既存HTTP
  1 skip）が終了0、JS構文と画面初期化も終了0。実ブラウザーのクリック列はloopback bind制約で
  未確認として残す。新規外部資料・依存・legacy比較はない。次はH08である。

- **H02**（`feat: 真空Hφの一様尺度比較を追加する`）：`hphi_field_grams`へ明示キーワード
  `previous_scale`（既定1.0）を追加した。`previous_scale=1.0`は既存の同領域経路と全配列一致する。
  1.0以外では前Projectの領域と全PEC穴を尺度倍して現領域とoverlayし、前E/Hへ`previous_scale**(-3/2)`を
  適用して現領域の測度`2*pi*r dr dz`で積分する。周波数`f/scale`はここでは適用せず呼出側で評価する
  （H04）。出力diagnosticに`previous_scale`/`previous_field_scale`を追加。`test_hphi_field_overlap`7件
  （軸接続/正半径の二尺度実FEMで`f→f/2`と正規化overlap恒等、scale=1一致、トポロジー/尺度相違拒否、
  不正尺度拒否）と`test_hphi_study_physics`のRF尺度則（Q0∝√s等）を確認した。同領域の既存版は維持。

## 残件

- 同軸寸法（H08）、一般写像／曲線（H11〜H13）、材料（H14〜H16）の比較・回復。
- 対象版C00.Vと旧tuner照合（[D02_PHYSICS_ROUTING.md](D02_PHYSICS_ROUTING.md)）。


### H03 / H04共通の細分・比較空間の決定（2026-09-16）

真空v1の最終細分は、採用した尺度を元Projectへ適用した後、各段で同軸Caseの
`nr/nz`を2倍、明示メッシュの全辺を中点で二分し各三角形を4分割する。
輪郭/穴/軸・要素次数・RF設定を保持する。これは新NGの数値方式の決定であり、旧tunerの方式の主張ではない。
HphiStudyの相似変換とplanar_refinementの標準中点4分割を基礎とし、
Hφ専用メッシュ型で全境界を再検証する。新規外部資料・依存は使用しない。

H04のguard診断では、各実試行メッシュをさらに1段4分割したP2比較空間を用いる。
探索/最終FEMには要求の`max_triangles/max_dofs`、比較にはcontrolsの
`max_overlay_triangles/max_dofs`を適用し、メッシュ型の250000要素上限も守る。
自由度予算は拘束前の全係数数（P1はV、P2はV+E、零モードを含む）を数える。
各段のV'=V+E、E'=2E+3T、T'=4Tで、最終比較空間まで割当て前に検査する。
交差分割の実予算超過はH04のMESH_LIMITで扱う。

H03受入：同一値の独立生成/元要求不変、strict JSONの重複・未知項目・非有限値・
bool数値・NumPy型・未対応変数/物理・guard/範囲の拒否、細分割当て前の予算拒否を確認。
同軸/正半径穴付き/軸接続穴付きで面積s²・体積s³、独立三角形回転体積、
正Jacobian、全輪郭保持、軸辺倍増を確認した。

実行：`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v test_hphi_tuning test_hphi_study test_hphi_study_physics`
→ 新3/既存11の14件PASS、11.429秒、終了0。
既存Studyの実FEM/RF尺度則を再利用。seed TMへの影響なし、seed/full validateは未実行。
H03完了。H04の実FEM二分実行、H05の所有保存/CLIはまだ未受入。


### H04 実装方式と範囲（2026-09-16）

`hphi_native.solve_hphi`の実FEM、H02の元E/H積分、既存Hφの有限比較空間による
スペクトル診断・guard・E/H一致・個別ID確認を接続した。既存`track_hphi_modes`の
版1/same_vacuum公開契約は維持し、内部の評価部分を共有する。調整の比較結果は
`superfish_ng_hphi_tune_tracking_result`、比較要求は`superfish_ng_hphi_tune_comparison`版1で、
明示尺度・両比較空間・controlsを記録する。以前の周波数は対応判断内だけでf/sへ写し、
元周波数・場・RF量は変更しない。有限空間の診断は各元SI領域で計算する。

共有`tuning._decision`は変更していない。探索の比較親だけを初期試行へ固定し、
採用候補の最終細分には採用親を渡す。終端後の追加元FEMを拒否し、
未確認・予算超過試行は周波数/目標差をnullにしてブラケット更新を止める。
`max_new_trials`は完了試行間のPAUSEDを返す。永続再開・実プロセス中止はH05/H06で接続する。

**座標表現の制限と判断**：中間試行を順次比較した初回の1.5→1.25は、
尺度比の丸めにより厳密輪郭一致を満たさずUNVERIFIEDとなった。物理閾値は緩めず、
一様尺度で共通の初期形状から各候補を直接比較する方式へ変更した。
初期試行→候補でもbinary64座標の厳密相似が成立しない入力は引き続きUNVERIFIEDとなる。
任意の非二進尺度・非相似変形での対応成功を保証しない。明示一般写像のH08/H09での検討対象とする。
失敗理由を保存し、座標を丸め直して入力領域をすり替えない。

来歴：HphiStudy、H02、hphi_tracking、tuning._decisionの独立実装を再利用した。
新規外部資料・依存・旧tuner比較はない。対象版/実機資料の未確認を変更しない。


H04受入記録：

- `OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v test_hphi_tuning test_hphi_tracking test_hphi_field_overlap test_tuning`
  → 29件PASS、89.701秒、終了0。初回はテスト属性`run`がunittestのメソッドと衝突して停止し、修正した。
- 比較親を初期試行へ固定した後、同じrunnerで`test_hphi_tuning.HphiTuneExecutionTests`を再実行
  → 4件PASS、61.118秒、終了0。29件のうち変更に直接依存する4件の証拠を置換した分割検証である。
- `OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python scripts/validate_hphi_tuning.py --out out/hphi-tuning-h04-final-20260916`
  → 専用4実FEM、12判定PASS、終了0。元Project/nativeと判断・各拒否を保存した。
  合成同軸TEMの独立式f=c/(2L)に対し、探索誤差最大1.573e-5、最終細分1.009e-6。
  二尺度の周波数・U・体積・G・Q0・損失の相対差最大1.777e-14、元E/Hの尺度誤差最大4.758e-14。
  目標ゲートのみ失敗/粗細ゲートのみ失敗、UNBRACKETED、UNVERIFIEDの周波数null、
  探索上限/変数幅上限、FEM前の要素予算拒否を別判定した。
- 追加の6実FEMは`out/hphi-tuning-h04-anchor-20260916`。
  1→2→1.5→1.25→1.375→最終細分でTUNED、最終比較親は4。
  `request.json`の要求で`run_hphi_tune`を実行すれば再現できる。
  変更前の1.25でのUNVERIFIEDとテスト初回失敗は最終証拠の`logs/`に保持する。

H04は真空一様尺度のAPI受入。CLI/所有checkpoint/replay/resume/worker/GUI、
一般写像、対象版照合、RF/表面ピークの収束受入ではない。
初期試行からも厳密相似輪郭を作れない入力の未確認停止は上記制限として残す。
同じ導電率/全周Uを保持し、両R/QのN/Aを数値へ置換しない。
seed TM経路と共有二分判定は不変で、seed/full validateは未実行。
次はH05（所有保存・改変検出・CLI再開）。

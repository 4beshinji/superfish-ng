# Hφ周波数調整の専用契約

作業カード [H01](development-plan/02-hphi.md#h01)（親D02/P03/P04）の成果物。
H01で仕様を固定し、H03で`hphi_tuning.py`のstrict要求reader・試行生成を実装した。
実FEM runner・保存・CLI以降は各カードの実装記録を参照する。
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
実装名・引数は既存runner（[hphi_native.py](../src/superfish_ng/hphi_native.py)、
[hphi_jobs.py](../src/superfish_ng/hphi_jobs.py)）との整合をH04で確定する。

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
| `UNBRACKETED` | 探索範囲内に符号変化なくブラケット不成立 | 末端のみ | 可（範囲変更は新要求） |
| `UNVERIFIED` | 個別ID未確認・集合合流・guard不足 | null | 可 |
| `MESH_LIMIT` | 要素/自由度上限超過（Hφ固有） | 直近の確認済み以下 | 可 |
| `REFINEMENT_FAILED` | 最終細分で目標/粗細ゲート未達 | あり | 不可（改善は新要求） |
| `ITERATION_LIMIT` | `max_trials`到達 | 評価済みのみ | 可 |
| `PARAMETER_LIMIT` | 二分点が`parameter_tolerance`未満 | あり | 不可 |

`MESH_LIMIT`は`max_triangles`/`max_dofs`/`max_overlay_triangles`のいずれか超過で発生し、
`tuning._decision`の共有語彙へ無断追加しない。H04で共有判定と分離した専用停止として実装する。

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

## replay / resume の許容・禁止変更

`replay_hphi_tune(...)`は所有した要求/全nativeから判断履歴を再構築し、保存時との一致を確認する。
`resume`は要求と一致する`PAUSED`のみ許可し、常に新規ディレクトリへ書く。

- 許可: `max_new_trials`の変更、checkpoint選択。
- 禁止: 目標/許容差/境界/変数/ID帯域/対応方針の変更。元外部パスの移動は所有nativeで許容する。
- 要求・係数・試行順序・親の改変、同名競合、不完全保存は拒否し、完了扱いしない。

## CLI と終了コード

H05で固定する。既存`tune`/`tune-planar`と同じ引数構成に合わせる。

```sh
python -m superfish_ng tune-hphi REQUEST.json --out out/hphi-tune-new --max-new-trials 2
python -m superfish_ng resume-tune-hphi out/hphi-tune-new/checkpoint-002.json --out out/hphi-tune-rest
python -m superfish_ng replay-tune-hphi out/hphi-tune-rest/checkpoint-004.json
```

終了0は`PAUSED`/`TUNED`。未確認・未達等は1。入力/例外は2（[cli.py](../src/superfish_ng/cli.py)の既存規約）。
例は合成同軸であり、実機構造ではない。

## worker と GUI

- workerは[H06](development-plan/02-hphi.md#h06)で`hphi_tuning_jobs.py`をJobManagerへ登録する。
  `planar_tuning_jobs.py`の契約（kind、入力/結果ファイル名、要求所有、checkpoint選択、
  別ジョブ再開、ロック解放、完了manifestの`numerical_validation`区別）に合わせる。
- GUIは[H07](development-plan/02-hphi.md#h07)で`gui_hphi.py`/`web/hphi.js`/`hphi.html`へ
  要求編集/読込、開始/中止、保存地点選択、再開、両周波数ゲート、対象IDと実順位、対象元場を追加する。
  表示単位と保存SIを分ける。実ブラウザーで開始→中止→別ジョブ再開→元場表示を確認する。

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
2. **ブラケット不成立**：`bounds`が目標を挟まない → `UNBRACKETED`、末端周波数のみ、再開可。
3. **個別ID未確認**：実順位交差または縮退で上側guard不足 → `UNVERIFIED`、`frequency_hz=null`、
   失敗解をブラケットに使わない。再開可。
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
| `replay_hphi_tune(...)` | 所有nativeから判断履歴を再構築 | `planar_tuning.replay_planar_tune` |
| `hphi_tuning_jobs.py` | 所有/別プロセス/中止/保存地点/再開の管理 | `planar_tuning_jobs.py`、`hphi_jobs.py` |

## 検査候補（H02以降）

計画の候補に従う。新規`tests/test_hphi_tuning.py`（H03〜H05）、
`tests/test_hphi_tuning_jobs.py`（H06）、`tests/test_gui_hphi_tuning.py`（H07）、
専用`scripts/validate_hphi_tuning.py`（API/CLI/native/二尺度と失敗例）。
H02は`test_hphi_tracking`等へ独立尺度検査を追加する。本書は文書のみでFEMを実行しない。

## 実装記録

- **H02**（`feat: 真空Hφの一様尺度比較を追加する`）：`hphi_field_grams`へ明示キーワード
  `previous_scale`（既定1.0）を追加した。`previous_scale=1.0`は既存の同領域経路と全配列一致する。
  1.0以外では前Projectの領域と全PEC穴を尺度倍して現領域とoverlayし、前E/Hへ`previous_scale**(-3/2)`を
  適用して現領域の測度`2*pi*r dr dz`で積分する。周波数`f/scale`はここでは適用せず呼出側で評価する
  （H04）。出力diagnosticに`previous_scale`/`previous_field_scale`を追加。`test_hphi_field_overlap`7件
  （軸接続/正半径の二尺度実FEMで`f→f/2`と正規化overlap恒等、scale=1一致、トポロジー/尺度相違拒否、
  不正尺度拒否）と`test_hphi_study_physics`のRF尺度則（Q0∝√s等）を確認した。同領域の既存版は維持。

## 残件

- H02以降の実装、v1の物理/保存/CLI/worker/GUI接続。
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

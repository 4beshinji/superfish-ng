# 平面RFの形状・追跡・調整

[全体索引と実行規則](README.md)に従う。本章のIDは親課題IDではなく、作業カードID。

各カードは原則1コミット。既存ファイルは調査・変更候補であり、全てを書き換える指示ではない。新設ファイルは本文で指定する。

## P01

### 平面アフィン形状法則を調整要求へ追加する

- **親課題**：P02 / D02。**種別**：実装。初期状態：未着手。
- **先行条件**：[B01](01-baseline.md#b01)
- **コミット件名案**：`feat: 平面アフィン形状法則を調整要求へ追加する`
- **既存の入口・影響先**：`src/superfish_ng/planar_tuning.py`、`src/superfish_ng/planar_tracking_exact_affine.py`、`src/superfish_ng/planar_study.py`
- **実施内容**：既存多角形アフィン比較を変数の有限多項式法則へ接続する。元xy Projectから全試行を生成し、行列/変数/係数の単位と全区間の退化拒否方針を保存する。
- **受入条件**：矩形の既存寸法調整との一致、面積行列式、回転/せん断/尺度の場則、不正行列のFEM前拒否を確認する。固定U′の場を3D規格化へ変えない。
- **既存の検査候補**：`test_planar_tuning`、`test_planar_tracking_exact_affine`、`test_planar_study`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_planar_tuning test_planar_tracking_exact_affine test_planar_study
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

- **進捗（2026-09-22）**：[多項式アフィン形状法則](../PLANAR_AFFINE_SHAPE.md)の基盤と独立3件を分割検証。調整要求/比較/保存への接続は未完、P01はIN_PROGRESS。

## P02

### 平面の個別ID回復を履歴・調整へ追加する

- **親課題**：P02 / D02。**種別**：実装。初期状態：未着手。
- **先行条件**：[P01](03-planar.md#p01)
- **コミット件名案**：`feat: 平面の個別ID回復を履歴・調整へ追加する`
- **既存の入口・影響先**：`src/superfish_ng/planar_tracking_history.py`、`src/superfish_ng/planar_tracking_history_saved.py`、`src/superfish_ng/planar_tuning.py`
- **実施内容**：完全な比較群と過去の個別IDを使った回復要求を定義し、保存履歴・調整の再開とworker/GUIへ接続する。
- **受入条件**：正方形の縮退と矩形順位交換を独立対照とし、回復不能では周波数nullで停止。回復後の実順位/IDと後続継承をAPI/CLI/GUIで一致させる。
- **既存の検査候補**：`test_planar_tracking_history`、`test_planar_tracking_history_saved`、`test_planar_tuning`、`test_planar_tuning_jobs`、`test_gui_planar_tuning`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_planar_tracking_history test_planar_tracking_history_saved test_planar_tuning test_planar_tuning_jobs test_gui_planar_tuning
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## P03

### 平面非線形写像の契約と幾何検査を追加する

- **親課題**：P02。**種別**：実装。初期状態：未着手。
- **先行条件**：[P02](03-planar.md#p02)
- **コミット件名案**：`feat: 平面非線形写像の契約と幾何検査を追加する`
- **既存の入口・影響先**：`src/superfish_ng/planar_tracking_exact_mapping.py`、`src/superfish_ng/planar_tracking_overlap.py`、`src/superfish_ng/planar_polygon.py`
- **実施内容**：新設planar_piecewise_mapping.pyで明示比較分割を使う非アフィン変形を定義する。全外周・領域被覆・正Jacobian・xyベクトル変換を検査し、既存アフィン方式を保持する。
- **受入条件**：既知座標写像の面積/多項式積分、アフィン極限、欠落/重複/反転の反例が通る。面積一致だけで領域一致としない。
- **既存の検査候補**：`test_planar_tracking_exact_mapping`、`test_planar_tracking_overlap`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_planar_tracking_exact_mapping test_planar_tracking_overlap
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## P04

### 平面非線形比較と調整を接続する

- **親課題**：P02 / D02。**種別**：実装。初期状態：未着手。
- **先行条件**：[P03](03-planar.md#p03)
- **コミット件名案**：`feat: 平面非線形比較と調整を接続する`
- **既存の入口・影響先**：`src/superfish_ng/planar_tracking_fields.py`、`src/superfish_ng/planar_tracking.py`、`src/superfish_ng/planar_tuning.py`、`src/superfish_ng/gui_planar_tuning.py`
- **実施内容**：元TE/TM場をP03の各実点写像で比較し、形状法則・追跡履歴・再開・調整GUIへ接続する。
- **受入条件**：相似極限の解析一致と非アフィン合成形状の独立細分を確認する。全試行が実FEMで、未確認群を評価しない。旧平面調整版と新要求の保存再生が一致する。
- **既存の検査候補**：`test_planar_tracking_fields`、`test_planar_tuning`、`test_gui_planar_tuning`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_planar_tracking_fields test_planar_tuning test_gui_planar_tuning
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## P05

### 平面曲線P2の幾何・弱形式を設計する

- **親課題**：P02。**種別**：仕様。初期状態：未着手。
- **先行条件**：[P03](03-planar.md#p03)
- **コミット件名案**：`docs: 平面曲線P2の幾何・弱形式を設計する`
- **既存の入口・影響先**：`src/superfish_ng/planar_polygon.py`、`src/superfish_ng/curved_fem.py`、`docs/PLANAR_RF_PLAN.md`
- **実施内容**：新設docs/PLANAR_CURVED_RF.mdにxy二次境界/面積求積/TE Neumann零空間/TM Dirichlet/元場/壁損失/保存版を定める。軸対称のr重みを含まない独立組立とする。丸め・円形解析・幾何/FEM別細分の検証条件を先に固定する。
- **受入条件**：円形cutoffの解析f/場/G、二尺度、両偏波、滑らかな非円形、特異角対照の入力と個別ゲートがある。一般材料/伝搬定数/穴をこの仕様へ黙って追加しない。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## P06

### 平面曲線幾何とP2空間を実装する

- **親課題**：P02。**種別**：実装。初期状態：未着手。
- **先行条件**：[P05](03-planar.md#p05)
- **コミット件名案**：`feat: 平面曲線幾何とP2空間を実装する`
- **既存の入口・影響先**：`src/superfish_ng/curved_fem.py`、`src/superfish_ng/planar_polygon.py`
- **実施内容**：新設planar_curved.py/planar_curved_fem.pyにstrict二次xy領域と面積ベースのK/Mを追加する。局所基底/求積のみ共有し、半径正値や軸境界の前提を使わない。
- **受入条件**：面積/境界長の独立積分、線形場パッチ、直線極限K/M、全Jacobianと閉外周検査、TE定数核とTM正値を検証する。
- **既存の検査候補**：`test_planar_polygon`、`test_curved_fem`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_planar_polygon test_curved_fem
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## P07

### 平面曲線の実解と元場・RFを実装する

- **親課題**：P02。**種別**：実装。初期状態：未着手。
- **先行条件**：[P06](03-planar.md#p06)
- **コミット件名案**：`feat: 平面曲線の実解と元場・RFを実装する`
- **既存の入口・影響先**：`src/superfish_ng/planar.py`、`src/superfish_ng/planar_saved.py`
- **実施内容**：新設平面曲線solver/場評価を専用Caseへ接続し、U′、全phasor場、片側PEC壁積分を実写像で求める。
- **受入条件**：円形の両偏波f/場/Gを独立解析と三水準で照合する。幾何近似と固定二次領域のFEM差を分け、fだけ合格しても場/RF未達なら未受入。
- **既存の検査候補**：`test_planar_rf`、`test_planar_rf`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_planar_rf test_planar_rf
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## P08

### 平面曲線native・Project・GUIを接続する

- **親課題**：P02 / O02。**種別**：実装。初期状態：未着手。
- **先行条件**：[P07](03-planar.md#p07)
- **コミット件名案**：`feat: 平面曲線native・Project・GUIを接続する`
- **既存の入口・影響先**：`src/superfish_ng/planar_saved.py`、`src/superfish_ng/planar_project.py`、`src/superfish_ng/planar_jobs.py`、`src/superfish_ng/gui_planar.py`
- **実施内容**：曲線Case/nativeの版付き読込・再構築・CLI、Project/worker/表示/独立Studyへ追加する。二次壁表示と元場を保持する。
- **受入条件**：独立API/CLI/GUIの全配列/RF一致、改変拒否、実中止・再起動、旧矩形/多角形保存の再生を確認する。加速量は理由付きN/Aを保つ。
- **既存の検査候補**：`test_planar_rf`、`test_planar_jobs`、`test_gui_planar`、`test_planar_study`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_planar_rf test_planar_jobs test_gui_planar test_planar_study
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## P09

### 平面曲線の比較・調整を接続する

- **親課題**：P02 / D02。**種別**：実装。初期状態：未着手。
- **先行条件**：[P04](03-planar.md#p04)、[P08](03-planar.md#p08)
- **コミット件名案**：`feat: 平面曲線の比較・調整を接続する`
- **既存の入口・影響先**：`src/superfish_ng/planar_tracking.py`、`src/superfish_ng/planar_tuning.py`、`src/superfish_ng/gui_planar_tuning.py`
- **実施内容**：同一二次領域/宣言写像の元場比較、固定境界細分、個別ID回復と調整/再開を追加する。曲線境界の比較予算を明示する。
- **受入条件**：円の尺度調整と非円形合成例で両周波数ゲートを検査し、最終細分時の二次境界不変と全場保存を確認する。曖昧/予算不足は停止する。
- **既存の検査候補**：`test_planar_tuning`、`test_planar_tracking`、`test_gui_planar_tuning`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_planar_tuning test_planar_tracking test_gui_planar_tuning
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## P10

### P02の物理範囲と残要件を受入監査する

- **親課題**：P02。**種別**：監査。初期状態：未着手。
- **先行条件**：[P09](03-planar.md#p09)、[C07-planar](06-compatibility.md#c07-planar)
- **コミット件名案**：`docs: P02の物理範囲と残要件を受入監査する`
- **既存の入口・影響先**：`docs/PLANAR_RF_PLAN.md`、`docs/COMPATIBILITY_MATRIX.md`、`docs/IMPLEMENTATION_STATUS.md`
- **実施内容**：新設P02_ACCEPTANCE.mdで矩形/多角形/曲線、単位長、追跡/調整、対象版の偏波/操作を照合する。対象版が要求する未対応形状/材料はL05で子課題化する。
- **受入条件**：必須集合の各偏波・境界・入出力・数値・操作に証拠があり、未確認の伝搬/TEMを対応済みとしない。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

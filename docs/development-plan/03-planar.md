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

- **受入（2026-09-22）**：[平面アフィン調整・版8比較・保存再生](../PLANAR_AFFINE_TUNING.md)。条件別検査・関連29件と別元場/strict検査を分割PASS。P01 DONE、次はP02。

## P02

2026-09-22受入：[全子条件の監査](../PLANAR_IDENTITY_RECOVERY_ACCEPTANCE.md)。原カードP02をDONE。後続P03/P04と親互換課題は継続。

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

## P02-a

### 元平面場による明示ID回復核

- 親カードP02、先行P01。`planar_identity_recovery.py`にanchor位置と完全なPlanarTrackingRequestを持つstrict回復要求を追加する。
- 継承比較とanchor比較を元FEMから再計算し、全継承ID集合との一致を確認する。未確認では回復周波数null、候補・継承集合を別保存する。
- 独立対照：TE矩形のcos場/解析遮断周波数、正方形の真縮退、.18→.20→.22 mの順位交換、guard未確認と集合越境拒否。元場/周波数不変、要求往復。
- 受入は専用APIまで。所有履歴のanchor位置実体への束縛はP02-bで必須。

- 受入記録：[P02-aの明示ID回復核](../PLANAR_IDENTITY_RECOVERY.md)。実矩形/正方形、独立周波数/場、guard/集合拒否と後続継承を分割4件PASS。

## P02-b

### 回復付き平面所有履歴とCLI/worker

- 親カードP02、先行P02-a。`planar_tracking_history.py`と`planar_tracking_history_saved.py`に回復位置/完全要求/元anchor所有コピーを追加する。
- 各隣接nativeの全hashと回復後ID継承、明示anchorが過去の解決済みsnapshotであることを再検証する。従来履歴版を保持する。
- 受入：実矩形→正方形→矩形→延長、保存移動/再生、誤anchor/置換ID/改変拒否、CLI/workerで元全native不変。未確認回復後に延長しない。

- 受入記録：[回復付き所有履歴](../PLANAR_RECOVERED_HISTORY.md)。API/CLI/worker・移動再生・回復後継承・改変拒否、版8保存入口補完を新3＋新2/既存7の分割検査で確認。

## P02-c

2026-09-22受入：[調整回復・保存・実操作の条件別証拠](../PLANAR_TUNING_RECOVERY.md)。新5件と関連14件が分割PASS。親P02/GUIは未完。

### 平面調整の回復・最終細分・再開

- 親カードP02、先行P02-b。`planar_tuning.py`と`planar_tuning_jobs.py`に完全比較/過去anchor方針を持つ新版要求を接続し、版1/2を保持する。
- 検索と最終細分の両方で継承集合と個別回復を検証する。失敗は周波数nullで停止し、過去checkpointを保持する。
- 受入：実矩形順位交換、正方形未確認、回復後の実最終細分、別job再開、worker取消し/再起動。独立遮断周波数と元E場、両gateと全U′/RF不変。

## P02-d

2026-09-22受入：[実Chrome履歴15・調整14・新サーバー5項目](../PLANAR_RECOVERY_GUI.md)。API/CLIと同じ回復ID、元native/Project bytes一致を確認。

### 回復操作GUIとP02条件別監査

- 親カードP02、先行P02-c。`gui_planar_tuning.py`と平面履歴GUIへ回復要求・候補/採用ID・anchor・null周波数の区別を接続する。
- 実ブラウザーで履歴回復→延長、調整回復→最終細分、中止/再開、サーバー再起動後の元場表示を確認する。API/CLI/GUIで同じ順位/ID、元native/Project全bytesを照合する。
- 全P02条件と子a〜cの証拠を監査してから親P02をDONEにする。部分APIだけで親を閉じない。

## P03

2026-10-02受入：[明示区分写像・全領域検査](../PLANAR_PIECEWISE_MAPPING.md)。
新7件＋既存25件、計32件PASS。連続区分アフィンによる全域非アフィン変形を対象とし、
解析面積/多項式積分・curl変換・独立native被覆・不正分割拒否を確認。P03 DONE、次はP04。
滑らかな非線形/曲線写像と場比較/調整の接続は今回の受入に含めない。

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

2026-10-02受入：[元条件別監査](../PLANAR_PIECEWISE_ACCEPTANCE.md)。P04-a/b/c全子の元場/実調整/所有保存/GUIを確認。滑らかな曲線は後続P05〜P09、原互換親P02/D02は未完了。

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

## P04-a

2026-10-02受入：[新版9の元場比較・追跡・所有再生](../PLANAR_PIECEWISE_TRACKING.md)。
新7件と直接消費先、計57件を分割PASS。主選択54PASS/誤メソッド名1ERROR、正しいstrict1件と独立物理2件を別確認。
実worker中止/管理器再起動・元全native不変、391製品ファイル固定、全handle終端。次はP04-b、親P04は継続。

### 区分写像による元場比較と追跡・所有再生

- 親P04、先行P03。比較セルと両側の独立nativeセルを有理数で交差し、各元セルの厳密被覆と元場の重心座標を保持する。前側SI面積で元TE/TM場を積分し、セル別adjugateを使用する。
- 追跡新版9を追加し旧版1〜8を保持。元領域の有限スペクトル・guard・ID集合・未確認停止を維持する。所有pair/履歴/CLI-workerの既存再生に接続する。
- 独立対照：既知区分座標写像の多項式場/curl積分、アフィン極限、実TE/TMの相似f/元場/U′/RF、非アフィン合成形状の独立細分。正逆・位相・全元セル面積・1 ULP/予算拒否・guard未確認・保存移動/改変拒否を検査する。
- 対象：新`planar_piecewise_overlap.py`、`planar_tracking.py`、`planar_tracking_jobs.py`、関連場/履歴テスト。形状法則と調整はP04-b。

## P04-b

受入：2026-10-02、[子a/b/cの条件別監査](../PLANAR_PIECEWISE_TUNING_WORKER.md#p04-b監査と来歴)。形状/実調整/所有保存/workerの全条件を受入。GUIと親P04は子c（P04-c）で継続。

### 区分形状法則と実調整・保存再開

- 親P04、先行P04-a。元Projectの明示比較分割と頂点の有限多項式変位法則を保存し、全試行を元形状から生成する。閉区間の正Jacobianを検査し、非局所接触/丸め不正は各試行FEM前に拒否する。
- 新調整要求で法則と回復方針を保存し、検索/最終細分の全個別ID確認、目標gate/粗細gateの分離、失敗prefixと新出力への再開を保持する。既存版1〜3を保持する。
- 独立対照：相似極限の解析周波数/元場/RF、不均一変形の実独立細分と実調整、元Project/native不変、未確認周波数null、移動後完全再生、worker中止/管理器再起動。
- 対象：新形状法則/API、`planar_tuning.py`、`planar_tuning_jobs.py`と直接消費先。GUI受入はP04-c。

## P04-c

2026-10-02受入：子aの調整GUI/API全50配列、子bの追跡/履歴GUI/API全70配列、新サーバー・最終表示と資源回収を確認。[親監査](../PLANAR_PIECEWISE_ACCEPTANCE.md)。

後続の前提はP04-bの全子工程受入。2026-10-02に調整操作aと単独追跡/履歴・親監査bへ分割。元P04の全条件は維持する。

### 区分調整GUIと操作・P04全条件監査

- 親P04、先行P04-b。新版要求編集/読込、比較/回復宣言、実調整/最終細分、保存地点選択/別job再開/元場表示をGUIへ接続する。
- 実ブラウザーで成功と未確認停止、中止/再開、新サーバー保存再生を確認し、APIとの全native/Project/要求/判断/RF一致と旧アフィン操作を確認する。
- 元P04と子a/bの全条件を専用文書で監査してから親P04をDONEにする。部分的なAPI合格で親を閉じない。

## P04-c-a

2026-10-02受入：[実操作/独立API全元場照合](../PLANAR_PIECEWISE_TUNING_GUI.md)。Python6件、Chrome20項目の分割PASS、全50配列/Project/要求/判断/RF一致。395製品hash不変、全handle終端。単独追跡/履歴と親監査は子b。

### 区分調整GUIの実操作と独立API全元場照合

- 親P04-c、先行P04-b。要求4の法則・回復方針・SI Projectを保存/再読込し、実成功/最終細分と未確認null、中止/所有地点選択/別job再開を操作する。
- 新サーバーで保存結果/元場を復元し、独立API実調整との全native配列/Project/要求/判断/RF一致を確認する。旧アフィン操作、製品hash固定、検証資源回収も確認する。
- 証拠は[区分調整GUI](../PLANAR_PIECEWISE_TUNING_GUI.md)。単独追跡/履歴と親監査は子b。

## P04-c-b

2026-10-02受入：[版9/10比較・所有履歴GUI](../PLANAR_PIECEWISE_TRACKING_GUI.md)。全版フォーム、Python10、Chromeの分割9/7/5/3項目、独立API3pair/全70配列を確認。検証器の初回失敗と表示修正を区別。全handle終端、数値ソース不変。

### 新版比較・追跡履歴GUIとP04全条件監査

- 親P04-c、先行P04-c-a。追跡版9の明示区分写像と版10の元Project/多項式区分法則をGUIで保持・編集・保存し、厳密JSONをサーバーへ渡す。
- 実元場のpair/ID集合引継ぎと所有履歴をGUIで開き、次段要求/回復の写像を維持する。旧追跡版を保持する。独立APIとの保存要求・判断・元場/RF不変を確認する。
- P04-a、P04-b全子、P04-c-aと本操作を原P04条件ごとに監査してからP04-c/P04をDONEにする。曲線/滑らかな非線形の後続P05〜P09は本カードへ数えない。

## P04-b-a

受入：2026-10-02、[元区分形状と参照比較](../PLANAR_PIECEWISE_SHAPE.md)。区間内重根/全域交差の独立反例、実相似TE/TM場・RF、共通参照/strict要求を確認。初回29件28PASS/1FAILは検証順序を修正し、影響17件再確認PASS、非影響12件成功を保持。394製品hash不変、全handle終端。P04-bは継続。

### 元区分形状法則と検索・最終細分の比較要求

- 親P04-b、先行P04-a。元明示meshの各頂点にxy変位の有限多項式（昇冪・最大8次・m）を宣言する。元Projectと完全な元meshを束縛し、閉区間の全セルJacobianを厳密多項式で検査する。
- 変形時の全境界節点をpolygonへ保持し、境界接触/交差・丸め不正を試行FEM前に拒否する。前試行から累積生成しない。
- 新追跡版10で両試行の実丸めmeshと検索/最終細分を元参照から完全再生成・照合する。元場を共通参照分割で比較し、P04-aの厳密overlayと二進対照で一致する。
- 新調整要求版4でこの法則と明示回復方針をstrict検査し、旧版1〜3を保持する。
- 独立不変量：偶数重根/端点/負Jacobian拒否、微小正対照、既知非アフィン変形の面積、全域/全外周保持、実FEMの相似f/E/H/U′/RF、親子の各元セル面積とadjugate、1 ULP/予算拒否。
- 受入は形状/比較/要求基盤まで。可搬保存と実runnerはP04-b-b、所有worker操作はP04-b-c。

## P04-b-b

受入：2026-10-02、[実区分調整と所有保存](../PLANAR_PIECEWISE_TUNING_SAVED.md)。非アフィンTE/TM解析/独立mesh、相似RF、実回復/guard/null、全prefix所有コピー・移動後CLI再開/再生、失敗prefix・再hash改変拒否を確認。分割22件PASS（新8/旧14）。初回粗格子/工場丸め・CLI60秒期限の失敗を保持し、数値許容差は維持。395製品hash不変、全handle終端。新版worker接続と親監査は子c。

### 実区分調整と可搬な全試行所有保存・再開

- 親P04-b、先行P04-b-a。実非アフィンFEM調整と相似解析対照、初回guard/個別ID・回復/未確認null、検索/最終gate別判定を確認する。
- 全元Project/native/要求/判断を所有コピーし、相対path宣言から移動後に全試行を物理再生する。再開は新出力へ書き、元checkpointと全nativeを保持する。結果/法則/親/係数の再hash改変を拒否する。
- 独立対照：非一様伸長と独立細分、解析相似目標、true縮退/guard拒否、実最終細分、未確認/失敗prefix、CLI所有再生、元出力移動後の再開。

## P04-b-c

受入：2026-10-02、[所有workerと親P04-b監査](../PLANAR_PIECEWISE_TUNING_WORKER.md)。新5/旧直接消費先12の分割17種類PASS、395製品hash不変、全handle終端。元移動・実中止/保存地点・別job・管理器再生成・実最終回復/解析cutoff・未確認null・改変拒否を確認。初回のテスト後処理2ERRORと1件再確認を保持。次はP04-c。

### 区分調整workerの所有中止・再開とP04-b監査

- 親P04-b、先行P04-b-b。queued入力に全先行trialを所有し、元出力移動後も実workerの再開・管理器再起動で再生する。中止時の確認済みprefixを保持し別jobへ再開する。
- 受入：実中止/保存地点選択/元移動/新job最終細分・回復と未確認null、全native/Project/判断/RF一致、コピー改変拒否。旧worker互換も確認する。
- 元P04-bと子a/bの全条件を監査して親P04-bをDONEにする。GUIはP04-c。

## P05

2026-10-02受入：[平面曲線P2仕様と条件別gate](../PLANAR_CURVED_RF.md)。
円二尺度/両偏波の解析f/E/H/G、楕円/再入角、固定Domainと幾何近似の別細分、
strict版3と保存/後続操作契約を定め、独立解析16組とpatch/JSON/依存/395製品hashを監査。
文書受入であり、曲線製品FEM/保存/GUIは未実装。P05 DONE、次はP06。

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

2026-10-02受入：[専用xy曲線Domain/面積P2 FEMと独立不変量](../PLANAR_CURVED_FEM.md)。
全Jacobian/閉外周・全edge/strict版3/面積K,M、二尺度patch/楕円/直線矩形・L字、TE核/TM正値を確認。
新9/既存5の14件と追加拒否の限定検査、四ring円6形状の専用validatorをPASS。
元395製品不変、実solve/元場/RF/native/操作は後続。P06 DONE、次はP07。

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

2026-10-07最終受入：[全原条件と主source/元artifact監査](../PLANAR_CURVED_ACCEPTANCE.md)。
元円独立38783の全四caseも実終端0となり、五source bridge/三補足を受入、限定kernelを主sourceへ統合した。
元401源/15validatorを別保全、最終401は受入版と完全一致、元主源から四変更/397不変。
P07 DONE、次はP08。以下の日付付き段落は当時の状態。全123カードgoal/原互換親は継続する。

2026-10-02進行：[実solve/元12場/曲線壁RF・厳密点所属と同Domain細分](../PLANAR_CURVED_SOLVER.md)。
新10/旧物理2種類を分割確認。固定二次円二尺度・両偏波の元12解を保持し、TMだけ追加2細分で
解析f/E/H/Gの全対象群がPASS。その後の[最終二水準比較](../PLANAR_CURVED_CONVERGENCE.md)は新5unitを確認し、
未達TE/TMを追加4FEMして計18元解を保持。TE L2→L3/TM L3→L4で二尺度のf/E/H/全RF差PASS。
独立内部mesh/増次数/幾何近似系列/楕円・再入角は未確認。
P07はIN_PROGRESS、P08/native/GUIと原互換親は未完。

2026-10-07追記：[有限N16/32/64の八幾何系列と元FEMの条件別監査](../PLANAR_CURVED_GEOMETRY_SERIES.md)は受入。
円/楕円の両偏波・二尺度で、真幾何と固定FEM f/E/H/全RFを別判定する。
楕円と角TEの固定A/B二尺度も受入。角TM二尺度・元円独立A/B半径.02・source統合は継続中。
[strict閉参照](../PLANAR_CURVED_EXACT_REFERENCE.md)と[元場point grouping](../PLANAR_CURVED_FIELD_GROUPING.md)は分離branchで限定受入。
P07はIN_PROGRESS、P08/P09と全原要件・全goalは未完了。過去の日付付き段落は当時の記録である。

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

- **現状（2026-10-07）**：DONE。[版3専用native](../PLANAR_CURVED_NATIVE.md)の
  元配列/全RF再構築・改変拒否を実装、新7件＋旧版直接利用5件は1.684秒PASS。
  [共通Case/Project/CLI-worker/Study/表示](../PLANAR_CURVED_OPERATIONS.md)も新9件分割受入、関連48件PASS。
  [全条件受入](../PLANAR_CURVED_OPERATION_ACCEPTANCE.md)：実Chrome15＋旧13＋別server7、計35項目PASS。
  全元native/全RF/12場・中止/新job/別server再生、全hash/元FAIL保全、全handle終端/Chrome回収を確認。
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

- **追跡核leaf（2026-10-07）**：[元E/H/有限guardの専用二状態API](../PLANAR_CURVED_TRACKING.md)。新8＋旧14の分割22件PASS、実rank交換/反射parity・真doublet/全RF確認、元406製品不変。回復/実調整/所有再開/GUIを残しIN_PROGRESS。

- **有限guard leaf（2026-10-07）**：[固定二次境界の細分スペクトル](../PLANAR_CURVED_SPECTRAL_RESOLUTION.md)。新4＋関連6の10件PASS、元405製品不変。rank/identityの受入は後続。

- **元場leaf（2026-10-07）**：[E/H自己・交差Gram](../PLANAR_CURVED_FIELD_COMPARISON.md)。新8＋関連10の分割18件PASS、元404製品不変。元場内積だけでidentity/周波数gate/調整を受入済みとしない。

- **進行（2026-10-07）**：[元二次写像の比較分割](../PLANAR_CURVED_COMPARISON.md)。新7＋関連12の19件PASS、元403製品不変。幾何leafのみ受入、元E/H・個別ID/実調整/最終細分・所有再開/GUIを残しIN_PROGRESS。

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

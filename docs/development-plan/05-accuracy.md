# 幾何・表面場・適応細分の精度と費用

[全体索引と実行規則](README.md)に従う。本章のIDは親課題IDではなく、作業カードID。

各カードは原則1コミット。既存ファイルは調査・変更候補であり、全てを書き換える指示ではない。新設ファイルは本文で指定する。

## N01

### 幾何・表面場の受入ケースを固定する

2026-10-07 N01仕様 **DONE**：[幾何3×FEM3・元場/RF/ピーク/独立参照の五合成ケース](../N01_GEOMETRY_SURFACE_CASES.md)。球/楕円の旧成功と元五量閾値を保持し、長楕円体・接線連続丸め二ローブ・鋭い導体先端を固定。五Case/15幾何入力のstrict解析、独立面積/体積とsmooth/singularをmetadataだけで確認。初稿端点projection UNVERIFIEDを保全し別明示寸法を選択、製品/閾値は変更せず1190 Python源不変。独立非球形Maxwell/物理peak参照はnull/未確認のままA01固定隔離環境と許可済みblack-boxの経路/両側細分を指定。図を目視確認、新FEM/unit/seed/full/legacy0。原123は69 DONE/2 IN_PROGRESS/52 PLANNED、親G03/N03/原互換32要件/全goalは継続、次はN02。rawは out/n01-geometry-surface-cases-20261007/。

- **親課題**：G03 / N03。**種別**：仕様。初期状態：未着手。
- **先行条件**：[B01](01-baseline.md#b01)
- **コミット件名案**：`docs: 幾何・表面場の受入ケースを固定する`
- **既存の入口・影響先**：`docs/G03_CURRENT_AUDIT.md`、`docs/SURFACE_CONVERGENCE.md`、`docs/CURVED_RF_NONSPHERE_COMPARISON.md`
- **実施内容**：既存球/楕円の成功を保持し、滑らかな非球形と丸めた再入形状、鋭角対照を追加する検証入力を定める。幾何3水準×各FEM3水準、場対応、独立参照の要否と参照入手経路を決める。
- **受入条件**：f 1e-4、R/QとG 0.5%、ピーク比1%の既存目標を維持し、場は専用仕様のゲートを引用する。形状ごとの基準値・独立性・限界を固定し、鋭角に有限ピークを要求しない。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N02

### 幾何と表面場の独立比較器を拡充する

2026-10-07：**N02 DONE**。[入力・元場・3×3数値集約の原条件受入](../N02_GEOMETRY_SURFACE_MATRIX.md)。
新17個別unit、実三モード九点の正しいFAIL、元楕円九点全量/元ゲート完全一致PASSを確認。
独立物理参照は未確認、全goal/親G03/N03は継続。次はN03。

2026-10-07：場対応工程を限定受入。[新10/直接4unit・旧楕円9保存解/8区間の完全一致](../N02_GEOMETRY_SURFACE_FIELDS.md)。
3×3の五量/幾何/求積/peak集約・反例が残りN02はIN_PROGRESSを維持。

2026-10-07：N01はDONE。入力・来歴工程を限定受入しN02はIN_PROGRESS。
[14個別unit/実CLI入力計画と元条件の残件](../N02_GEOMETRY_SURFACE_PLAN.md)。
実保存場の比較/反例/楕円の新判定再生が残る。FEM/seed/fullは0。

- **親課題**：G03 / N03。**種別**：実装。初期状態：未着手。
- **先行条件**：[N01](05-accuracy.md#n01)
- **コミット件名案**：`feat: 幾何と表面場の独立比較器を拡充する`
- **既存の入口・影響先**：`scripts/validate_geometry_surface_convergence.py`、`scripts/validate_surface_convergence.py`、`scripts/validate_curved_geometry_convergence.py`
- **実施内容**：新しい合成ケースを入力指定で受け付け、幾何差/FEM差/求積差/元場対応/ピーク上下界を別報告する。存在する参照は来歴を検査して再利用し、欠けた参照はUNVERIFIEDとする。
- **受入条件**：故意のピーク未収束・場不一致・幾何未確認で適切に失敗する。元の楕円成功報告の判定と一致し、検証器が自分の出力を独立参照として使わない。
- **既存の検査候補**：`test_surface_convergence`、`test_affine_surface_convergence`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_surface_convergence test_affine_surface_convergence
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N03

### 非球形と丸め形状の物理精度を検証する

2026-10-07 N03五系列の元条件監査PASS、節目の全検証中：[全域の独立場/RF・両側二区間](../N03_PHYSICAL_SERIES.md)。楕円PASS、元長楕円体のFAILは保存し追加2/3/4＋最終FEM4独立比較PASS（全1017.615秒・終了0）。元45＋追加六native、五形状の実三ID/元場/量別gate・全参照byteと1199源を終端後に再hash、監査は新FEM/標本0。版4は検証済みtemp commit81bce60と全1200源byte一致で本体へ統合、commit a907036。新7＋直接3unitの証拠を再利用し、独立比較handle22395/64791を含む旧ジョブはすべて終端。主公開は版1/2/3/4、元FEM/RF核・閾値不変。全validate handle72074を新out/validation-n03-milestone-20261007で一度実行中（2485検査/499モジュール・8 process）。主src/tests/scripts/examplesを固定し、完了前にfull受入とは呼ばない。N03はIN_PROGRESS、原123は70 DONE/3 IN_PROGRESS/50 PLANNED、親G03/互換32要件/全goalは継続。rawは out/n03-native-surface-series-20261007/completed-physical-series-acceptance.json と appended-main-integration.json。

2026-10-07 N03後続 **IN_PROGRESS**：[版3全行列と独立球](../N03_CURVED_TRACKING_RESOURCES.md)。保存45点の再評価は1025.114秒・終了0・新FEM0・1199源不変。球/楕円/丸め形状は全条件PASS、鋭角はSINGULAR_GEOMETRYとnumerical PASSを別表示、長楕円体はR/Qの二変化未達をFAILで保持。同じ元メッシュ/P2幾何にFEM3/4を六点明示追加中。独立球の全領域対応/Gauss16・24/三個別ID/両側二変化/元場RFは44.191秒・終了0でPASS。解析領域外点、未分割fan体積、参照root誤記の検査側失敗を保全し、曲線partitionと単位的体積密度規約を明示した。非球形/鋭角の独立比較と追加長楕円体は続行中、実行中は1199源を固定。原123は70 DONE/3 IN_PROGRESS/50 PLANNED、原互換32要件/親G03/N03/全goalを維持。rawは out/n03-native-surface-series-20261007/matrix-and-sphere-checkpoint.json。

2026-10-07 N03 **IN_PROGRESS**：[元45点終端と曲線親子比較の明示資源](../N03_CURVED_TRACKING_RESOURCES.md)。SHA固定N01五形状の45/45 nativeは2995.296秒・終了0、元1197源/catalog不変。追跡予算停止を保存し、版3の宣言資源と全P2子写像検査で元場・全求積点/個別IDを評価する拡張を統合。新/直接13個別unitを分割受入、球312000点の元比較は全三ID/元場PASS・3.479秒・新FEM0。既定逆写像/262144上限・科学核/RF/閾値は不変。独立MIT固定源79を隔離uv環境へ復元、参照15＋追加10求解は終端、球粗二水準のG等FAILは保持。rawは out/n03-native-surface-series-20261007/。全行列・元場/RF/ピーク二区間・両側独立精度の受入は後続、物理上界null。原123は70 DONE/3 IN_PROGRESS（H17/C07-planar/N03）/50 PLANNED、親G03/N03/互換32要件/全goalを維持。

- **親課題**：G03 / N03。**種別**：検証。初期状態：未着手。
- **先行条件**：[N02](05-accuracy.md#n02)
- **コミット件名案**：`test: 非球形と丸め形状の物理精度を検証する`
- **既存の入口・影響先**：`scripts/validate_geometry_surface_convergence.py`、`docs/G03_CURRENT_AUDIT.md`、`docs/SURFACE_FIELD_DIAGNOSTICS.md`
- **実施内容**：N01の各系列を専用validatorで実行する。必要な独立現代ソルバー/許可済みブラックボックス比較は別環境と別成果物にし、両側細分を記録する。製品修正が必要なら最小の失敗不変量を再現する修正コミットを挟む。
- **受入条件**：各滑らかな例で連続2区間のf/場/RF/ピークと幾何不変量を満たす。失敗例と費用を保持し、未達を閾値緩和で解消しない。独立参照なしなら物理参照の行を未確認に残す。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N04

### N03とG03の受入範囲を確定する

- **親課題**：N03 / G03。**種別**：監査。初期状態：未着手。
- **先行条件**：[N03](05-accuracy.md#n03)、[C03](06-compatibility.md#c03)
- **コミット件名案**：`docs: N03とG03の受入範囲を確定する`
- **既存の入口・影響先**：`docs/G03_CURRENT_AUDIT.md`、`docs/SURFACE_CONVERGENCE.md`、`docs/IMPLEMENTATION_STATUS.md`
- **実施内容**：G03の構築10/診断13までの既存証拠、旧NT=2/3変換、N03の幾何/FEM/独立参照を要件表へ対応付ける。新設N03_ACCEPTANCE.mdに一般保証でないことと適用範囲を記録する。
- **受入条件**：旧入力、滑らかな表面量、特異/未確認表示の必須行に証拠がある。離散ピーク上下界を連続問題の誤差上界とは呼ばない。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N05

### 適応細分の精度対費用の比較条件を固定する

2026-10-07 N05仕様 **DONE**：[三対照の同一初期領域・量別精度・固定費用比較](../N05_ADAPTIVE_EFFICIENCY_PLAN.md)。円筒/球とN01丸め二ローブ幾何2を選び、元Case/source/P2・両側同じ初期求解/全壁/個別ID、元五量・独立元場と二回全域確認を固定。各方式2回・順序交替の計12実行、8水準/250000要素/3600秒/32GiB・BLAS1、段階/全体時間・RSSと共有参照費用の計測境界を実行前に指定。旧球の適応非優位を保持し、精度達成と効率改善を別条件にする。文書だけの受入、新unit/FEM/seed/full0、主1200源不変。N06/N07/N08/N04と全goalは後続。原123は71 DONE/3 IN_PROGRESS（H17/C07-planar/N03）/49 PLANNED。別実行のN03全validate handle72074は継続し、src/tests/scripts/examplesを固定中。

- **親課題**：N04。**種別**：仕様。初期状態：未着手。
- **先行条件**：[N01](05-accuracy.md#n01)
- **コミット件名案**：`docs: 適応細分の精度対費用の比較条件を固定する`
- **既存の入口・影響先**：`docs/ADAPTIVE_REFINEMENT.md`、`docs/CURVED_ADAPTIVE_REFINEMENT.md`、`tests/test_adaptive_refinement_cost.py`
- **実施内容**：円筒/球の既存対照に加え、局所細分が必要な滑らかな形状を選ぶ。同じ初期領域/次数/量/精度目標で、一様と適応のDOF・壁時計・メモリ・全域確認費用を比較する。
- **受入条件**：以前の球で適応優位がなかった事実を残す。精度達成と効率改善を別条件にし、比較回数・測定環境・予算を実行前に固定する。普遍的優位を完了条件にしない。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N06

### 適応と一様細分の比較を実行する

- **親課題**：N04。**種別**：実装。初期状態：未着手。
- **先行条件**：[N05](05-accuracy.md#n05)
- **コミット件名案**：`feat: 適応と一様細分の比較を実行する`
- **既存の入口・影響先**：`scripts/validate.py`、`src/superfish_ng/curved_residual_indicator.py`、`src/superfish_ng/curved_rf_adjoint.py`
- **実施内容**：新設scripts/validate_adaptive_efficiency.pyで固定ケースの一様/適応を同じ条件で比較する。選択/追跡/求積/保存/全域確認の時間を測り、ボトルネックを特定する。
- **受入条件**：両経路の独立物理精度と費用を報告する。誤差対DOF曲線と誤差対時間を分け、前処理を片側だけ除かない。未達/予算超過も出力する。
- **既存の検査候補**：`test_adaptive_refinement_cost`、`test_curved_adaptive_refinement`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_adaptive_refinement_cost test_curved_adaptive_refinement
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N07

### 測定された適応処理の不足を修正する

- **親課題**：N04。**種別**：条件付き実装。初期状態：未着手。
- **先行条件**：[N06](05-accuracy.md#n06)
- **コミット件名案**：`fix: 測定された適応処理の不足を修正する`
- **既存の入口・影響先**：`src/superfish_ng/curved_residual_indicator.py`、`src/superfish_ng/curved_rf_adjoint.py`、`src/superfish_ng/curved_marked_refinement.py`
- **実施内容**：N06の失敗または律速がある場合に限り、指標・選択・再構築共有の一箇所を選び修正する。新しい計算法なら独立不変量を先に追加する。複数原因はN07-原因名の別コミットに分ける。
- **受入条件**：同じケース/精度目標で前後比較し、場/RFと親子質量保存を維持する。改善が不要/得られない場合は採用なしの判断を記録し、数値目標を緩めない。
- **既存の検査候補**：`test_curved_marked_refinement`、`test_curved_refinement`、`test_curved_adaptive_refinement`、`test_adaptive_refinement_cost`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_curved_marked_refinement test_curved_refinement test_curved_adaptive_refinement test_adaptive_refinement_cost
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N08

### 適応の一般ケース・保存・N04受入を確認する

- **親課題**：N04 / O02。**種別**：実装。初期状態：未着手。
- **先行条件**：[N07](05-accuracy.md#n07)
- **コミット件名案**：`feat: 適応の一般ケース・保存・N04受入を確認する`
- **既存の入口・影響先**：`docs/CURVED_ADAPTIVE_REFINEMENT.md`、`docs/ADAPTIVE_REFINEMENT.md`、`src/superfish_ng/gui_adaptive_refinement.py`
- **実施内容**：変更した選択/停止が保存再開とGUIにも一致することを確認し、N04_ACCEPTANCE.mdを作る。既存固定履歴・選択移送・大規模表示の証拠は再利用する。
- **受入条件**：対象物理量の精度/費用/全域確認、上限未達表示、実中止再開を記録する。効率の改善範囲と悪化範囲を明示し、要件未達なら親を閉じない。
- **既存の検査候補**：`test_gui_adaptive_refinement`、`test_adaptive_refinement_jobs`、`test_curved_adaptive_refinement`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_gui_adaptive_refinement test_adaptive_refinement_jobs test_curved_adaptive_refinement
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

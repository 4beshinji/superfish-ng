# TM/TE調整とRF制約付き探索

[全体索引と実行規則](README.md)に従う。本章のIDは親課題IDではなく、作業カードID。

各カードは原則1コミット。既存ファイルは調査・変更候補であり、全てを書き換える指示ではない。新設ファイルは本文で指定する。

## D01

2026-10-07 D01仕様 **DONE**：[非曲線TM/TEの形状・区分写像・対称/最終細分](../NONCURVED_TUNING_SCOPE.md)。profile/階段/単一一般輪郭の六正常/拒否要求と元追跡先を固定。現行profile正常2、未対応4、不正6、将来六領域の両bounds/面積・体積尺度と不正拒否、未実装版9拒否、TE異セクター事前拒否をmetadataだけで確認。136式は既存SI parserに適合し、初稿leaf拒否/runner引数順ERRORを保全して修正。製品/テスト/script1179源不変、新FEM/unit/seed/full/legacy0。現在の区分TM追跡と不足するTM調整/TE直線区分追跡を分離し、既存曲線TEを再実装へ戻さない。原123台帳はD01状態だけ変更、65 DONE/2 IN_PROGRESS/56 PLANNED。D02/D03実装・親D02/P01/全goal/原互換32要件は継続、次はD02。

### 非曲線TM/TE調整の形状対応を確定する

- **親課題**：D02 / P01。**種別**：仕様。初期状態：未着手。
- **先行条件**：[B01](01-baseline.md#b01)
- **コミット件名案**：`docs: 非曲線TM/TE調整の形状対応を確定する`
- **既存の入口・影響先**：`src/superfish_ng/tuning.py`、`src/superfish_ng/te_tuning.py`、`docs/D02_PHYSICS_ROUTING.md`
- **実施内容**：profile、階段、一般輪郭について既存要求の対応/拒否を表にする。階段角の移動、対称面、軸区間を保つ区分アフィン写像と変数単位、最終細分を仕様化する。曲線TEで受入済みの機能は作り直さない。
- **受入条件**：各形状に最小正常/拒否要求があり、既存追跡入口まで辿れる。不足箇所がTMかTEか明記され、対称セクター間の比較は拒否される。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D02

2026-10-07 D02原カード **DONE**：[直線TM調整の条件別監査](../STRAIGHT_TM_TUNING_ACCEPTANCE.md)。D01法則からの試行/追跡/独立細分/保存再開、独立円筒f/H/E/壁loss/両R/Q、実段差の元境界/体積/個別ID、無効中間形状の求解前停止、API/CLI/実Chromeの元要求/最終場/両R/Q一致を原6条件群で照合。52個別unit＋実Chrome7項目を源/元logへ再結合し、監査内の新FEM/unit/full/seed/legacy0。一般折返し輪郭は正しい未達停止/完全再生を受入し、追加二系列の差71.166/31.378 kHzをTUNEDへ変更しない。初稿監査の「折返し輪郭成功」は原カードを超える追加条件だったため、原文との照合記録を残し、原条件へ戻した。全1275源固定・全handle/server/browser終端、slot 0。原123はD02だけDONEへ変更、66 DONE/2 IN_PROGRESS（H17/C07-planar）/55 PLANNED。親D02/P01/全goal/原互換32要件は継続、次はD03（TE階段/一般輪郭）。rawは out/d02-whole-acceptance-20261007/acceptance.json。

2026-10-07 D02操作限定受入：[版9直線TMのGUI/入口一致](../STRAIGHT_TM_TUNING.md#guiと入口一致)。実Chromeで版9法則がlinearへ誤復元される不具合を終了1で再現し、専用法則入力・元Project/追跡条件復元・raw法則のstrict parser渡しを修正。既存checkpointから追加検索/細分へ再開し、完全要求再構築、重複キー求解前拒否、保存/改竄拒否、二周波数gate、追跡順位の最終場表示の7項目PASS（終了0/外部通信0）。独立API/CLIの元要求・decision・元最終H/E・9 RF量/両R/QはGUIと相対差0、表示importの元6科学ファイルもbyte一致。比較runnerのファイル名誤りを終了1で保全し、原nativeを読み直すだけで終了0に修正（追加求解0）。全1275源固定、Python科学核/52個別検査の源不変。全browser/server終端、slot 0、新full/seed/legacy0。D02全条件/一般輪郭成功系列は後続、全123/原互換32要件/全goal継続。rawは out/d02-straight-gui-20261007/leaf-audit.json。

2026-10-07 D02コア限定受入：[直線TM形状法則](../STRAIGHT_TM_TUNING.md)。版9の元全境界owner/SI式/まとめた座標更新・実区分比較を通常tune、最終細分、保存再開、版6回復wrapperへ接続した。新metadata6＋実物理6＋直接消費40の52個別検査を分割受入。独立円筒Bessel f/H/E/全壁loss/両R/Q、実段差の元場尺度則・完全再生、無効中間形状の求解前拒否、曖昧ID停止を確認。粗段差83.248 kHzは失敗を保持し、角局所細分の別系列は元10 kHz条件内6.240 kHzでTUNED。一般折返し輪郭は元1 Hz細分条件未達を保持。検査側ERRORと粗系列FAILの元logを保全し、成功済みケースは繰り返さず不足分を補った。1182源の固定、旧製品変更2ファイルの4関数に限定、科学核/RF定義/許容差不変。全handle実終端、新full/seed/legacy0。D02はIN_PROGRESS（実GUI/API/CLI一致と全条件監査が残る）、全123は65 DONE/3 IN_PROGRESS/55 PLANNED、原互換32要件/全goal継続。rawは out/d02-straight-tuning-20261007/bounded-audit-pre-docs.json。

### TMの階段・一般輪郭調整を接続する

- **親課題**：D02。**種別**：実装。初期状態：未着手。
- **先行条件**：[D01](04-design.md#d01)
- **コミット件名案**：`feat: TMの階段・一般輪郭調整を接続する`
- **既存の入口・影響先**：`src/superfish_ng/tuning.py`、`src/superfish_ng/tuning_jobs.py`、`src/superfish_ng/gui_tuning.py`
- **実施内容**：D01の明示写像をTM試行Project生成、追跡、最終細分と再開へ接続する。既存対応で満たす経路は新コードを作らず受入検証を追加する。
- **受入条件**：円筒極限の解析関係、段差付き実FEMの元境界/体積/ID、無効形状停止を確認する。API/CLI/GUIで元要求・最終場・両R/Qを一致させる。
- **既存の検査候補**：`test_tuning`、`test_coupled_tuning`、`test_tuning_jobs`、`test_gui_tuning`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_tuning test_coupled_tuning test_tuning_jobs test_gui_tuning
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D03

2026-10-07 D03原カード **DONE**：[直線TE調整の原条件監査](../STRAIGHT_TE_TUNING_ACCEPTANCE.md)。元版9法則をTE Eφ/対称半領域/鏡映・固定RF/N/Aへ接続し、独立Bessel f/Eφ/Hr/Hz/全PEC壁loss、実段差/独立細分/両端二偶奇、未確認/無効形状停止・所有保存再開を照合。追跡39＋調整35の74個別unitを源/元logに結合し、実Chromeは分割9項目PASS。API/CLI/GUIの元要求/decision/最終Eφ/Hr/Hzと7 RF量は相対差0、両R/Q N/A、表示importの元6科学ファイルbyte一致。磁気対称段差は通常/鏡映とも元10 kHz条件内8.974 kHz、閉PEC/電気対称25.043 kHzと粗折返し輪郭1.348 MHzの未達は保持。混在端がsampleへ進む反例を先に再現して拒否を追加。検査のcontour boundaries、独立peak振幅係数、RF表の行/列selector ERROR/FAILを保全し、不足分を修正して再検査した。1279源固定・全handle/server/browser終端、slot 0、新full/seed/legacy0。D03だけDONEへ変更、原123は67 DONE/2 IN_PROGRESS/54 PLANNED。親P01/D02/全goal/原互換32要件は継続。次は依存成立のD06、D04はH18/P10/C07-TEを待つ。rawは out/d03-whole-acceptance-20261007/acceptance.json。

2026-10-07 D03第一実装：[直線TEの元Eφ/回転体積・鏡映追跡](../STRAIGHT_TE_TRACKING.md)。独立非一様体積積分で現行Hφ読取KeyErrorを先に再現し、schema1の元Eφ専用比較を接続。元セクター/通常・鏡映混在/全境界をsample前に拒否し、元半meshを全鏡映領域へ導出する。新10＋直接消費29の39個別検査を分割受入、実段差/折返し/保存完全再生・両端/二偶奇/P1/P2・真の二ローブsample・G/QとEφ/Hr/Hz尺度則（最大4.637e-15）/両R/Q N/Aを確認。低overlapのmatches空配列を参照した検査ERRORを保全し、元overlap_matrixの検査へ修正。1184 Python源固定、旧製品変更2ファイル/3関数、科学核/RF閾値不変。新full/seed/legacy0・全handle終端。D03だけIN_PROGRESS、全123は66 DONE/3 IN_PROGRESS/54 PLANNED。版9TE調整/独立細分/操作接続とD03全監査、全goal/原互換32要件は未完。rawは out/d03-te-straight-tracking-20261007/acceptance.json。

### TEの階段・一般輪郭調整を接続する

- **親課題**：P01 / D02。**種別**：実装。初期状態：未着手。
- **先行条件**：[D01](04-design.md#d01)
- **コミット件名案**：`feat: TEの階段・一般輪郭調整を接続する`
- **既存の入口・影響先**：`src/superfish_ng/te_tuning.py`、`src/superfish_ng/gui_tuning.py`
- **実施内容**：D01の写像をEφ追跡とTE境界へ接続し、直接PEC/対称半領域/鏡映を区別する。元セクター順位と個別ID、固定RFと加速量N/Aを保持する。
- **受入条件**：円筒TE解析周波数/場、段差形状の独立細分と対称偶奇、未確認停止/保存再開を検査する。TMの境界条件を流用しない。
- **既存の検査候補**：`test_te_profile_tuning`、`test_te_tuning`、`test_gui_tuning`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_te_profile_tuning test_te_tuning test_gui_tuning
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D04

### P01とD02の原要件を最終照合する

- **親課題**：P01 / D02。**種別**：監査。初期状態：未着手。
- **先行条件**：[D02](04-design.md#d02)、[D03](04-design.md#d03)、[H18](02-hphi.md#h18)、[P10](03-planar.md#p10)、[C07-TE](06-compatibility.md#c07-te)
- **コミット件名案**：`docs: P01とD02の原要件を最終照合する`
- **既存の入口・影響先**：`docs/D02_PHYSICS_ROUTING.md`、`docs/COMPATIBILITY_PLAN.md`、`docs/IMPLEMENTATION_STATUS.md`
- **実施内容**：P01_ACCEPTANCE.md/D02_ACCEPTANCE.mdを新設する。各物理の全必須形状/変数/ID/二つの周波数ゲート/保存/操作と、C07の旧TE比較を対応させる。静的源問題を周波数tuneへ混ぜない。
- **受入条件**：実装済み一覧だけでなく独立解析と実再開の証拠が各必須行にある。追加カードが残る物理は受入にせず、対応済みの行は保持する。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D05

2026-10-07 **DONE**。[目的量/制約仕様](../RF_OPTIMIZATION_SCOPE.md)の全原条件を読取監査で受入。現行六量/追加能力/N/A・全体未収束predicate・独立三水準・L02/L03分離を照合。製品420源不変、既存full関連結果を再利用し新数値実行0。rawは `out/d05-rf-optimization-scope-20261007/acceptance.json`。次はD09、親D03/全goalは継続。

### D03の目的量と制約の残要件を固定する

- **親課題**：D03。**種別**：仕様。初期状態：未着手。
- **先行条件**：[B01](01-baseline.md#b01)
- **コミット件名案**：`docs: D03の目的量と制約の残要件を固定する`
- **既存の入口・影響先**：`docs/RF_OPTIMIZATION.md`、`docs/RF_OPTIMIZATION_GEOMETRY.md`、`src/superfish_ng/rf_optimization.py`
- **実施内容**：既存要求版1〜3に対し、一般形状・追加物理の必要量を列挙する。量の名称/単位/最大最小/無効時状態/数値収束条件、初期/最終の独立三水準を定める。存在しないR/Qを目的に選べないよう能力表を作る。
- **受入条件**：各物理の目的/制約の定義とN/Aが一意。未収束の制約を満足扱いする経路がない。静的磁石設計・熱はL02/L03へ分離する。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D06

### 一般TM形状のRF探索候補を生成する

2026-10-07 D06 **DONE**：[元直線TM候補の実座標探索/三水準個別ID/所有保存再開](../STRAIGHT_RF_CANDIDATE_SEARCH.md)。3形状で両変数6候補/18 FEM、独立Bessel f/H/E/全壁loss/両R/Q、実順位交換ID、invalid候補FEM0・曖昧2モード即停止・予算/祖先保全を確認。先行33＋新8の41個別unitを分割受入。曲線版1〜3の10元試行/30 native水準を完全再生（新FEM0）。検査側mass/contour条件・端点1 ulp ERRORを保全し不足分だけ再検査。全RF assessment null、例の18 FEM成果物もFINAL_UNVERIFIEDを保持。旧数値AST/許容差不変、1190源の検査修正以外固定・全handle終端、新full/seed/legacy0。原123は68 DONE/2 IN_PROGRESS/53 PLANNED、親D03/原互換32要件/全goalは継続。次はN01（N02/N03→D07の依存準備）。rawは out/d06-straight-native-search-20261007/acceptance.json。

2026-10-07 D06第一工程：[直線TMの多変数候補台帳](../STRAIGHT_RF_CANDIDATES.md)。元Project/全境界owner/SI式から3形状を独立生成し、変数/候補順・分割再開の実形状一致、invalid候補と上限・null assessment/IDを保存。新6＋直接25＋単変数物理2の33個別unitを分割受入、実段差2 FEMのH/E尺度差最大4.498e-14。TE selector誤記loader ERRORは元logを保全し正しい1件だけ追加。旧RF全関数AST/5入口源byte不変、1188 Python snapshot以後不変、全handle終端、新full/seed/legacy0。既存RF入口の能力規約は維持。D06はIN_PROGRESS、探索器/実候補ID・所有solve checkpointと全条件監査が残る。原123は67 DONE/3 IN_PROGRESS/53 PLANNED、全goal/原互換32要件を維持。rawは out/d06-straight-candidates-20261007/acceptance.json。

- **親課題**：D03。**種別**：実装。初期状態：未着手。
- **先行条件**：[D02](04-design.md#d02)、[D05](04-design.md#d05)
- **コミット件名案**：`feat: 一般TM形状のRF探索候補を生成する`
- **既存の入口・影響先**：`src/superfish_ng/rf_optimization_geometry.py`、`src/superfish_ng/rf_optimization_search.py`
- **実施内容**：確認済みの非曲線/曲線形状法則を多変数探索の候補生成へ接続する。元Project・固定履歴から生成し、失敗候補と予算使用を記録する。
- **受入条件**：変数/順序/再開によらず同じ候補は同じ実形状となる。無効形状・未確認IDは有利な目的値を返さない。既存曲線版1〜3の再生を保つ。
- **既存の検査候補**：`test_rf_optimization_geometry`、`test_rf_optimization_history`、`test_rf_optimization`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_rf_optimization_geometry test_rf_optimization_history test_rf_optimization
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D07

### RF制約の収束と独立最終評価を拡張する

- **親課題**：D03 / N03。**種別**：実装。初期状態：未着手。
- **先行条件**：[D06](04-design.md#d06)、[N03](05-accuracy.md#n03)
- **コミット件名案**：`feat: RF制約の収束と独立最終評価を拡張する`
- **既存の入口・影響先**：`src/superfish_ng/rf_optimization.py`、`src/superfish_ng/rf_optimization_checkpoints.py`、`src/superfish_ng/surface_convergence.py`
- **実施内容**：探索中の推定/細分評価と最終の独立系列を分離し、各制約の区間/失敗/未確認を保存する。初期と最終を同じ規約で比較し、固定幾何と幾何誤差の判定を混ぜない。
- **受入条件**：制約境界をまたぐ上下界、粗細で順位/採否が変わる例、計算上限の例を検査する。目的改善だけでは成功にならず、全必須制約と独立最終検証が必要。
- **既存の検査候補**：`test_rf_optimization`、`test_surface_convergence`、`test_rf_optimization_jobs`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_rf_optimization test_surface_convergence test_rf_optimization_jobs
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D08

### TEと平面RFの制約評価を追加する

- **親課題**：D03。**種別**：実装。初期状態：未着手。
- **先行条件**：[D05](04-design.md#d05)、[D03](04-design.md#d03)、[P09](03-planar.md#p09)
- **コミット件名案**：`feat: TEと平面RFの制約評価を追加する`
- **既存の入口・影響先**：`src/superfish_ng/rf_optimization.py`、`src/superfish_ng/te_tuning.py`、`src/superfish_ng/planar_tuning.py`
- **実施内容**：物理別の量取得アダプタを追加し、D05で定義されたエネルギー/損失/場量だけ評価する。TE加速量N/A、平面J/m・W/mを保持し、評価不能は理由付き状態にする。
- **受入条件**：独立円筒TE/矩形解析と二尺度で単位/規格化が一致する。存在しない量を要求すると求解前に拒否し、旧TM RF評価が不変。
- **既存の検査候補**：`test_rf_optimization`、`test_te_tuning`、`test_planar_tuning`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_rf_optimization test_te_tuning test_planar_tuning
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D09

2026-10-07 D09全原条件 **DONE**：[Hφ RF評価の条件別監査](../HPHI_RF_DESIGN_ACCEPTANCE.md)。単一/材料/直線真空/曲線P2の四受入receipt、独立同軸TEM/TM・一様/二層・全PEC壁・有効/不正軸経路、実個別E/H・有限guard・量別二変化/全包絡採用・保存完全再生を照合。過去76個別test IDの源/元log hashを再結合した読取監査で、新FEM/unit/seed/full/legacy0。粗曲線の数値未達はUNVERIFIEDを維持、peak/連続誤差は保証しない。過去真空receiptのコマンド表記5件（二重method suffix）は元記録を保全して訂正版を別保存。原123台帳はD09状態だけ変更、64 DONE/2 IN_PROGRESS/57 PLANNED。H17追加損失判断・D10-hphi探索運用・親D03/原互換32要件/全goalは未完。次は依存が揃ったD01の非曲線TM/TE形状対応仕様。

2026-10-07 **IN_PROGRESS**。[五nativeの全RF量取得/strict能力・保存再生](../HPHI_RF_DESIGN.md)を第一実装。新6件9.674秒＋直接利用18件51.316秒は終了0。独立同軸TEM/尺度・一様/二層材料のf/場/壁lossを確認。単一場の制約/採用は全UNVERIFIED/null。元三水準・個別ID/guard・量別収束/全体採用の接続は続行し、D09全受入へ数えない。rawは `out/d09-hphi-rf-observation-20261007/acceptance.json`。

[材料三水準/有限個別ID・RF制約](../MATERIAL_HPHI_RF_CONVERGENCE.md)を限定受入。新1件103.018秒＋新5件1168.208秒＋直接消費15件61.074秒、数値終端後のregion対応拒否1件7.140秒（FEM0）は実終了0。正常数値源/旧テストはarchive AST同一、拒否Ifのみ追加。台帳/全原条件は維持、真空/曲線三水準とD09全条件監査は続く。全handle終端、D09 IN_PROGRESS。

[直線真空三水準/実個別ID・全壁RF制約](../VACUUM_HPHI_RF_CONVERGENCE.md)も限定受入。新8＋直接消費17の全25件を分割PASS/実終了0。独立TEM/Besselと粗い一般穴の数値未達、二ID順序継承・保存移動/型偽装拒否を確認。元422製品ファイル中420不変、旧定義/核/許容差・全123台帳不変。曲線側と全条件監査は後続、D09 IN_PROGRESS。

2026-10-07 D09曲線三水準の限定受入：[完全P2参照・元chart/実個別E/H/全PEC壁RF](../CURVED_HPHI_RF_CONVERGENCE.md)。新8＋直接消費8＋独立同軸TM追加1の17件は分割PASS・全実終了0。解析TEMとTMのf/H/E/壁loss誤差減少、真正曲線穴の全領域/壁・尺度則と粗系列UNVERIFIED、strict能力・guard/予算/phase・保存移動/型偽装/元変異拒否を確認。等価な有理chart表記のFEM0反例を修正し、元数値AST/正常chartを保持。初期1177/修正後1178源の固定と元423製品源中421不変を監査。最後の保存完全再生1件1925.090秒も終了0。原同軸TM三nativeを保存後、NumPy scalar拒否のrunner ERRORを保全し、float入力で元場を再利用した1件49.705秒を受入。専用validatorは成功数値core/元creatorとsource結合し、CLI help/既存出力拒否を別確認、全数値CLIの重複求解は実施しない。rawは out/d09-curved-rf-convergence-20261007/acceptance.json。D09全条件監査は後続、全123台帳・原互換32要件・全goalを維持。科学核/旧RF定義/許容差不変、新full/seed/legacy0、全handle終端。

### HφのRF制約評価を追加する

- **親課題**：D03。**種別**：実装。初期状態：未着手。
- **先行条件**：[D05](04-design.md#d05)、[H16](02-hphi.md#h16)
- **コミット件名案**：`feat: HφのRF制約評価を追加する`
- **既存の入口・影響先**：`src/superfish_ng/rf_optimization.py`、`src/superfish_ng/hphi_native.py`、`src/superfish_ng/material_hphi_rf.py`
- **実施内容**：真空/内導体/確認済み材料の全周量・軸加速量の有無と全PEC壁量を専用評価へ接続する。材料損失はH17の受入済みモデルだけ使用する。
- **受入条件**：同軸/一様材料/二層の独立f・場・壁損失と保存再生が一致する。軸無し/非真空加速区間、未実装のピークや損失量は拒否/N/Aを保つ。
- **既存の検査候補**：`test_rf_optimization`、`test_material_hphi`、`test_hphi_convergence`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_rf_optimization test_material_hphi test_hphi_convergence
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D10-TE

### 追加RFの探索実行と保存再開を接続する：軸対称TE

- **親課題**：D03 / O02。**種別**：実装。初期状態：未着手。
- **先行条件**：[D07](04-design.md#d07)、[D08](04-design.md#d08)
- **コミット件名案**：`feat: 追加RFの探索実行と保存再開を接続する：軸対称TE`
- **既存の入口・影響先**：`src/superfish_ng/rf_optimization_search.py`、`src/superfish_ng/rf_optimization_jobs.py`、`src/superfish_ng/rf_optimization_checkpoints.py`
- **実施内容**：このコミットの対象は軸対称TEのみ。物理別候補/追跡/評価アダプタを探索器へ接続する。TE、平面、Hφは別々の小コミットD10-TE/D10-planar/D10-hphiとし、各コミットで専用native・試行履歴・中止再開を完結する。
- **受入条件**：各物理で初期/最終実FEM・制約不達・予算停止・再開一致を確認する。物理ごとの必須量を全て検証し、一つの物理の成功を他へ流用しない。
- **既存の検査候補**：`test_rf_optimization_jobs`、`test_rf_optimization_start_concurrency`、`test_rf_optimization_prefix_reuse`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_rf_optimization_jobs test_rf_optimization_start_concurrency test_rf_optimization_prefix_reuse
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D10-planar

### 追加RFの探索実行と保存再開を接続する：平面RF

- **親課題**：D03 / O02。**種別**：実装。初期状態：未着手。
- **先行条件**：[D07](04-design.md#d07)、[D08](04-design.md#d08)
- **コミット件名案**：`feat: 追加RFの探索実行と保存再開を接続する：平面RF`
- **既存の入口・影響先**：`src/superfish_ng/rf_optimization_search.py`、`src/superfish_ng/rf_optimization_jobs.py`、`src/superfish_ng/rf_optimization_checkpoints.py`
- **実施内容**：このコミットの対象は平面RFのみ。物理別候補/追跡/評価アダプタを探索器へ接続する。TE、平面、Hφは別々の小コミットD10-TE/D10-planar/D10-hphiとし、各コミットで専用native・試行履歴・中止再開を完結する。
- **受入条件**：各物理で初期/最終実FEM・制約不達・予算停止・再開一致を確認する。物理ごとの必須量を全て検証し、一つの物理の成功を他へ流用しない。
- **既存の検査候補**：`test_rf_optimization_jobs`、`test_rf_optimization_start_concurrency`、`test_rf_optimization_prefix_reuse`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_rf_optimization_jobs test_rf_optimization_start_concurrency test_rf_optimization_prefix_reuse
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D10-hphi

### 追加RFの探索実行と保存再開を接続する：Hφ

- **親課題**：D03 / O02。**種別**：実装。初期状態：未着手。
- **先行条件**：[D07](04-design.md#d07)、[D09](04-design.md#d09)
- **コミット件名案**：`feat: 追加RFの探索実行と保存再開を接続する：Hφ`
- **既存の入口・影響先**：`src/superfish_ng/rf_optimization_search.py`、`src/superfish_ng/rf_optimization_jobs.py`、`src/superfish_ng/rf_optimization_checkpoints.py`
- **実施内容**：このコミットの対象はHφのみ。物理別候補/追跡/評価アダプタを探索器へ接続する。TE、平面、Hφは別々の小コミットD10-TE/D10-planar/D10-hphiとし、各コミットで専用native・試行履歴・中止再開を完結する。
- **受入条件**：各物理で初期/最終実FEM・制約不達・予算停止・再開一致を確認する。物理ごとの必須量を全て検証し、一つの物理の成功を他へ流用しない。
- **既存の検査候補**：`test_rf_optimization_jobs`、`test_rf_optimization_start_concurrency`、`test_rf_optimization_prefix_reuse`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_rf_optimization_jobs test_rf_optimization_start_concurrency test_rf_optimization_prefix_reuse
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D10

### 追加RFの探索実行と保存再開を接続する（統合照合）

- **親課題**：D03 / O02。**種別**：監査。初期状態：未着手。
- **先行条件**：[D10-TE](04-design.md#d10-te)、[D10-planar](04-design.md#d10-planar)、[D10-hphi](04-design.md#d10-hphi)
- **コミット件名案**：`docs: 追加RFの探索実行と保存再開を接続する（統合照合）`
- **既存の入口・影響先**：`src/superfish_ng/rf_optimization_search.py`、`src/superfish_ng/rf_optimization_jobs.py`、`src/superfish_ng/rf_optimization_checkpoints.py`
- **実施内容**：各分割コミットの受入証拠を照合して親の残要件を更新する。コードの追加は各分割カードで実施する。
- **受入条件**：各物理で初期/最終実FEM・制約不達・予算停止・再開一致を確認する。物理ごとの必須量を全て検証し、一つの物理の成功を他へ流用しない。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D11-TE

### 追加RF探索のGUIとD03受入を仕上げる：TEのGUI

- **親課題**：D03 / O02。**種別**：実装。初期状態：未着手。
- **先行条件**：[D10-TE](04-design.md#d10-te)
- **コミット件名案**：`feat: 追加RF探索のGUIとD03受入を仕上げる：TEのGUI`
- **既存の入口・影響先**：`src/superfish_ng/gui_rf_optimization.py`、`docs/RF_OPTIMIZATION.md`、`docs/IMPLEMENTATION_STATUS.md`
- **実施内容**：このコミットの対象はTEのGUIのみ。物理別目的/制約の選択、未確認/実失敗理由、最終元場と独立細分結果を表示する。GUI接続は物理別コミット、最後にD03_ACCEPTANCE.mdの照合を文書コミットに分ける。
- **受入条件**：各物理の実ブラウザーで中止/再開/再起動とAPI一致を確認する。大域最適を主張せず、必須量/親D03の残行がなければ受入にする。
- **既存の検査候補**：`test_gui_rf_optimization`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_gui_rf_optimization
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D11-planar

### 追加RF探索のGUIとD03受入を仕上げる：平面のGUI

- **親課題**：D03 / O02。**種別**：実装。初期状態：未着手。
- **先行条件**：[D10-planar](04-design.md#d10-planar)
- **コミット件名案**：`feat: 追加RF探索のGUIとD03受入を仕上げる：平面のGUI`
- **既存の入口・影響先**：`src/superfish_ng/gui_rf_optimization.py`、`docs/RF_OPTIMIZATION.md`、`docs/IMPLEMENTATION_STATUS.md`
- **実施内容**：このコミットの対象は平面のGUIのみ。物理別目的/制約の選択、未確認/実失敗理由、最終元場と独立細分結果を表示する。GUI接続は物理別コミット、最後にD03_ACCEPTANCE.mdの照合を文書コミットに分ける。
- **受入条件**：各物理の実ブラウザーで中止/再開/再起動とAPI一致を確認する。大域最適を主張せず、必須量/親D03の残行がなければ受入にする。
- **既存の検査候補**：`test_gui_rf_optimization`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_gui_rf_optimization
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D11-hphi

### 追加RF探索のGUIとD03受入を仕上げる：HφのGUI

- **親課題**：D03 / O02。**種別**：実装。初期状態：未着手。
- **先行条件**：[D10-hphi](04-design.md#d10-hphi)
- **コミット件名案**：`feat: 追加RF探索のGUIとD03受入を仕上げる：HφのGUI`
- **既存の入口・影響先**：`src/superfish_ng/gui_rf_optimization.py`、`docs/RF_OPTIMIZATION.md`、`docs/IMPLEMENTATION_STATUS.md`
- **実施内容**：このコミットの対象はHφのGUIのみ。物理別目的/制約の選択、未確認/実失敗理由、最終元場と独立細分結果を表示する。GUI接続は物理別コミット、最後にD03_ACCEPTANCE.mdの照合を文書コミットに分ける。
- **受入条件**：各物理の実ブラウザーで中止/再開/再起動とAPI一致を確認する。大域最適を主張せず、必須量/親D03の残行がなければ受入にする。
- **既存の検査候補**：`test_gui_rf_optimization`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_gui_rf_optimization
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## D11

### 追加RF探索のGUIとD03受入を仕上げる（統合照合）

- **親課題**：D03 / O02。**種別**：監査。初期状態：未着手。
- **先行条件**：[D11-TE](04-design.md#d11-te)、[D11-planar](04-design.md#d11-planar)、[D11-hphi](04-design.md#d11-hphi)
- **コミット件名案**：`docs: 追加RF探索のGUIとD03受入を仕上げる（統合照合）`
- **既存の入口・影響先**：`src/superfish_ng/gui_rf_optimization.py`、`docs/RF_OPTIMIZATION.md`、`docs/IMPLEMENTATION_STATUS.md`
- **実施内容**：各分割コミットの受入証拠を照合して親の残要件を更新する。コードの追加は各分割カードで実施する。
- **受入条件**：各物理の実ブラウザーで中止/再開/再起動とAPI一致を確認する。大域最適を主張せず、必須量/親D03の残行がなければ受入にする。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

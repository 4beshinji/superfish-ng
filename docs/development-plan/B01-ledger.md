# B01: 残要件と証拠の対応台帳

作業カード [B01](01-baseline.md#b01)。親課題C00。種別：監査。

- 基準commit: `e21426e`（計画 `6484e30` の次。B01自体は文書のみで製品コードを変更しない）。
- 目的：K01〜K32の各受入軸（F/I/O/N/W）と親課題33件を、**最新の専用受入文書**へ対応付け、
  受入範囲・行全体で残る理由・担当親ID・本計画カード・証拠の現存/欠落を行単位で固定する。
- 制約：旧ソース/バイナリ内部は読まない。履歴の古い「未接続」「次は」から新しい要件を捏造しない。
  受入済み10親（C01、C02初期AF部分集合、O01、R01、N01/N02、G01/G02、A01、D01）を
  再実装対象へ戻さない。C02の追加部分集合（NT=2/3等）は §4 で別管理する。
- 出典：[COMPATIBILITY_BASELINE.md](../COMPATIBILITY_BASELINE.md)（全32行の適用軸・証拠記号）、
  [COMPATIBILITY_MATRIX.md](../COMPATIBILITY_MATRIX.md)（NG現状と限定受入文書）、
  [COMPATIBILITY_PLAN.md](../COMPATIBILITY_PLAN.md)（親課題集計）、
  [tasks.tsv](tasks.tsv)（親ID→カードの依存）。日付のない行はすべて本計画作成時点の証拠。

## 1. K01〜K32 対応台帳

表の意味。
- **適用軸**：COMPATIBILITY_BASELINE で宣言済みの受入軸。未知・参照不在は UNVERIFIED であり N/A にしない。
- **限定受入（最新文書）**：既存の「限定PASS」がどの専用文書・実行記録にあるか。**行全体の互換受入ではない**
  （COMPATIBILITY_BASELINE §受入軸と対象の決め方：全行の軸別互換受入は依然 UNVERIFIED）。
- **行全体で残る/未確認**：COMPATIBILITY_MATRIX の「互換として残るもの」と一致。
- **担当親／本計画カード**：親課題集計の担当親と tasks.tsv の parent_ids から展開。
- **証拠**：現存＝上記文書がrepoに存在する（限定受入）。欠落＝対象版/実機/抽出テキスト等が未取得。

| K | 適用軸 | 限定受入（最新文書） | 行全体で残る/未確認 | 担当親 | 本計画カード | 証拠 |
|---|---|---|---|---|---|---|
| K01 | F/I/O/N/W | [LEGACY_INPUT.md](../LEGACY_INPUT.md)、[MODEL_CONTRACT.md](../MODEL_CONTRACT.md)：単一真空・全PEC AF、直線/短円弧、周波数/RF照合 | 限定外の旧指定/既定値、G03の追加曲線 | C02,G03 | C01,C02,C03,N01〜N04 | 現存（限定） |
| K02 | F/I/O/N/W | [CURVED_ELEMENTS.md](../CURVED_ELEMENTS.md)、[OFFSET_DEGENERACIES.md](../OFFSET_DEGENERACIES.md)、[MERIDIONAL_RADIUS.md](../MERIDIONAL_RADIUS.md)：native楕円/双曲線・接続/共通接線・固定弧・曲線P2・描画/鏡映GUI | 一般の弧端/退化分類、曲線ピークの物理収束・全要件照合、旧曲線パラメータ/対象版実行 | C00,G03 | B01〜B04,L05,C01〜C03,N01〜N04 | 現存（限定）。旧曲線パラメータは欠落 |
| K03 | F/I/O/N/W | [GENERAL_CONTOUR.md](../GENERAL_CONTOUR.md)、[GENERAL_MESH.md](../GENERAL_MESH.md)：軸接続単一外周・品質付き生成 | 旧版全仕様はC00未確認、曲線はG03 | G01,G02（受入済）→残はC00,G03 | B01〜B04,C01〜C03,N01〜N04 | 現存（限定） |
| K04 | F/I/O/N/W | [COAXIAL_RF.md](../COAXIAL_RF.md)、[HPHI_MESH_RF.md](../HPHI_MESH_RF.md)、[AXIS_HPHI_RF.md](../AXIS_HPHI_RF.md)、[HPHI_JOBS.md](../HPHI_JOBS.md)、[GUI_HPHI.md](../GUI_HPHI.md)、[HPHI_STUDY.md](../HPHI_STUDY.md)、[AXIS_HPHI_WORKSPACE.md](../AXIS_HPHI_WORKSPACE.md)：閉同軸/一般正半径/軸接続穴付きのm=0 Hφ族・零空間処理・全壁RF・native/CLI/GUI | 曲線内導体、収束/追跡・旧版照合は未完 | P03 | H01〜H13,H18,C07-hphi | 現存（限定） |
| K05 | F/I/O/N/W | [GENERAL_MESH.md](../GENERAL_MESH.md)、[EXTERNAL_MESH_WORKFLOW.md](../EXTERNAL_MESH_WORKFLOW.md)：品質条件付き輪郭生成/JSON読込・GUI取込/固定Study | 外部形式変換・生成対象の拡張。旧と同じ節点配置は要求しない | G02,O02 | C01〜C03,H05〜H07,H13,H16,P08,D10,D11,N08,S07 | 現存（限定） |
| K06 | F/I/O/N/W | [HIGH_ORDER_FIELDS.md](../HIGH_ORDER_FIELDS.md)、[MARKED_REFINEMENT.md](../MARKED_REFINEMENT.md)、[RESIDUAL_INDICATOR.md](../RESIDUAL_INDICATOR.md)、[ADAPTIVE_REFINEMENT.md](../ADAPTIVE_REFINEMENT.md)、[ADAPTIVE_SURFACE_STOPPING.md](../ADAPTIVE_SURFACE_STOPPING.md)：P2場/RF、局所細分、残差指標、版1〜3停止、保存再開、GUI | 一般形状/効率・誤差上界は未完。旧アルゴリズム再現要件ではない | N01,N02,N04 | N01〜N08,D07 | 現存（限定） |
| K07 | F/I/O/N/W | [SUPERFISH_COMPARISON.md](../SUPERFISH_COMPARISON.md)、[MILESTONE_ACCEPTANCE.md](../MILESTONE_ACCEPTANCE.md)、[ACCELERATING_CONVENTIONS.md](../ACCELERATING_CONVENTIONS.md)：TM基本/高次モード、演習17照合、加速量規約 | 形状/周波数範囲・探索条件の網羅、対応モードの判定 | C04,D01（受入済）→残はC04 | C07-TM,C07,C08 | 現存（限定）。範囲網羅は欠落 |
| K08 | F/I/O/N/W | [MODEL_CONTRACT.md](../MODEL_CONTRACT.md)、[TE_REFLECTION_PLAN.md](../TE_REFLECTION_PLAN.md)：全PEC・平坦z端・鏡映 | 旧タグ写像、任意境界への拡張要否。旧半領域直接照合はしない | C02,G01（受入済）→残はC00/G03（C01〜C03） | C01〜C03,N01〜N04 | 現存（限定） |
| K09 | F/I/O/N/W | [AXISYMMETRIC_TE.md](../AXISYMMETRIC_TE.md)、[CURVED_TE_PLAN.md](../CURVED_TE_PLAN.md)、[TE_JOBS.md](../TE_JOBS.md)、[GUI_TE.md](../GUI_TE.md)、[TE_TRACKING_PLAN.md](../TE_TRACKING_PLAN.md)、[TE_STUDY_PLAN.md](../TE_STUDY_PLAN.md)、[TE_CONVERGENCE_STUDY_PLAN.md](../TE_CONVERGENCE_STUDY_PLAN.md)、[TE_REFLECTION_PLAN.md](../TE_REFLECTION_PLAN.md)：直線/曲線P2の固有値・Eφ/Hr/Hz・RF・native/CLI/Project/GUI/追跡/掃引 | 一般形状の追跡・受入。一般AF入力変換は未対応 | P01 | D01,D03,D04,C07-TE | 現存（限定）。一般AF変換は欠落 |
| K10 | F/I/O/N/W | [PLANAR_RF.md](../PLANAR_RF.md)、[PLANAR_POLYGON_RF.md](../PLANAR_POLYGON_RF.md)、[PLANAR_POLYGON_MESH.md](../PLANAR_POLYGON_MESH.md)、[PLANAR_JOBS.md](../PLANAR_JOBS.md)、[GUI_PLANAR.md](../GUI_PLANAR.md)、[PLANAR_STUDY.md](../PLANAR_STUDY.md)、[PLANAR_CONVERGENCE.md](../PLANAR_CONVERGENCE.md)、[PLANAR_TRACKING.md](../PLANAR_TRACKING.md)、[PLANAR_POLYGON_TRACKING.md](../PLANAR_POLYGON_TRACKING.md)、[PLANAR_TRACKING_HISTORY.md](../PLANAR_TRACKING_HISTORY.md)、[PLANAR_SIMILARITY_TRACKING.md](../PLANAR_SIMILARITY_TRACKING.md)、[PLANAR_REMESH_TRACKING.md](../PLANAR_REMESH_TRACKING.md)、[PLANAR_SIMILARITY_REMESH_TRACKING.md](../PLANAR_SIMILARITY_REMESH_TRACKING.md)、[PLANAR_AFFINE_REMESH_TRACKING.md](../PLANAR_AFFINE_REMESH_TRACKING.md)、[PLANAR_EXACT_AFFINE_TRACKING.md](../PLANAR_EXACT_AFFINE_TRACKING.md)：両尺度/両次数のf/場/G・追跡版1〜7・細分診断 | 曲線・材料・一般の丸めた境界・非線形変形追跡、旧版Cartesian実行は未完 | P02 | P01〜P10,C07-planar | 現存（限定）。旧版Cartesian実行は欠落 |
| K11 | F/I/O/N/W | K04と同一文書群：閉同軸TEM/TM・矩形穴の独立解析・二尺度/両次数/実細分・軸接続穴付きの別契約 | 円筒TEM/TMと矩形穴以外（曲線）・収束/追跡・旧版照合は未完 | P03 | H01〜H13,H18,C07-hphi | 現存（限定） |
| K12 | F/I/O/N/W | [MATERIAL_HPHI_FORMS.md](../MATERIAL_HPHI_FORMS.md)、[MATERIAL_HPHI_RF.md](../MATERIAL_HPHI_RF.md)、[MATERIAL_HPHI_NATIVE.md](../MATERIAL_HPHI_NATIVE.md)、[MATERIAL_HPHI_WORKSPACE.md](../MATERIAL_HPHI_WORKSPACE.md)：領域/界面・K/M基盤・専用固有解/場/RF・native/CLI/Project/GUI/Study | 材料比較/追跡・損失モデル・対象版での材料入力/実行検証は未完 | P04 | H10,H14〜H18,C07-material | 現存（限定） |
| K13 | F/I/O/N/W | [ACCELERATING_CONVENTIONS.md](../ACCELERATING_CONVENTIONS.md)、[SAVE_COMPLETION.md](../SAVE_COMPLETION.md)、[SUPERFISH_COMPARISON.md](../SUPERFISH_COMPARISON.md)：f/U/壁損失/Q0/G/RQ/シャント、二つのRQ規約・単位/正規化 | 単位/正規化/二つのRQ規約の入出力写像の全ケース照合 | R01（受入済）,C03,C04 | C04〜C08 | 現存（限定） |
| K14 | F/I/O/N/W | [ACCELERATING_CONVENTIONS.md](../ACCELERATING_CONVENTIONS.md)、[MODEL_CONTRACT.md](../MODEL_CONTRACT.md)：加速長/電圧区間/位相原点、任意区間積分、鏡映/GUI | 旧の任意位相指定の入出力写像・比較。現AF読込は限定 | R01（受入済）,C02,C03 | C01〜C03,C04〜C08 | 現存（限定） |
| K15 | F/I/O/N/W | [RF_DISCRETE_PEAKS.md](../RF_DISCRETE_PEAKS.md)、[AFFINE_SURFACE_EXTREMA.md](../AFFINE_SURFACE_EXTREMA.md)、[AFFINE_SURFACE_CONVERGENCE.md](../AFFINE_SURFACE_CONVERGENCE.md)、[SURFACE_CONVERGENCE.md](../SURFACE_CONVERGENCE.md)：上下界評価・P1/P2片側場・連続離散ピーク囲い込み・角診断・追跡済み表面収束 | 固定丸め半径での収束、境界評価位置/規約の一致 | N03 | N01〜N04 | 現存（限定） |
| K16 | F/I/O/N/W | [INDEPENDENT_COMPARISON.md](../INDEPENDENT_COMPARISON.md)、[GUI_HPHI.md](../GUI_HPHI.md)：軸/半径プローブ等の限定SIプローブ | 任意線/円弧/格子と必要出力の定義。旧補間アルゴリズムは再現しない | C03,O02 | C04〜C08,H05〜H07,H13,H16,P08,D10,D11,N08,S07 | 現存（限定） |
| K17 | F/I/O/N/W | [MODE_TRACKING.md](../MODE_TRACKING.md)、[MODE_IDENTITY_RECOVERY.md](../MODE_IDENTITY_RECOVERY.md)、[TUNING_IDENTITY_RECOVERY.md](../TUNING_IDENTITY_RECOVERY.md)：重み付き部分空間追跡・明示写像/メッシュ対応・保存/再検証CLI・個別ID回復 | 曲線領域・対応推定、製品接続 | D01（受入済）→残はD02/D03 | D01〜D04,D05〜D11 | 現存（限定） |
| K18 | F/I/O/N/W | [TUNING.md](../TUNING.md)、[RF_OPTIMIZATION.md](../RF_OPTIMIZATION.md)、[RF_OPTIMIZATION_JOBS.md](../RF_OPTIMIZATION_JOBS.md)、[RF_DESIGN_CRITERIA.md](../RF_DESIGN_CRITERIA.md)、[GUI_RF_OPTIMIZATION.md](../GUI_RF_OPTIMIZATION.md)：追跡付き1変数tune・RF制約評価・2変数探索・保存再開/GUI | 非アフィン曲線/任意関数連動・一般制約付き探索・旧tuner照合 | D02,D03 | D01〜D11,H01〜H18 | 現存（限定）。旧tuner照合は欠落 |
| K19 | F/I/O/N/W | [LEGACY_INPUT.md](../LEGACY_INPUT.md)、[MODEL_CONTRACT.md](../MODEL_CONTRACT.md)：位置付きstrict読込、明示NG設定、原入力/hash・変換診断 | 初期部分集合外の文法/既定値/領域、一般探索とモード対応 | C00,C02 | B01〜B04,L05,C01〜C03 | 現存（限定）。R25抽出テキストは欠落 |
| K20 | F/I/O/N/W | [SUPERFISH_COMPARISON.md](../SUPERFISH_COMPARISON.md)、[MILESTONE_ACCEPTANCE.md](../MILESTONE_ACCEPTANCE.md)：比較スクリプトの限定読取 | 製品用の読込/出力・終了コード・必要な列と精度 | C03,C04 | C04〜C08 | 現存（限定：比較のみ）。製品出力は欠落 |
| K21 | F/I/O/W（NはN/A：単独で数値ソルバーを追加しない） | なし（未実装） | 仕様確認。まずテキスト移行経路。バイト互換はv0で約束しない | C00,C03 | B01〜B04,L05,C04〜C06 | 欠落（バイナリ解ファイル仕様） |
| K22 | F/I/O/N/W | [O02_ACCEPTANCE.md](../O02_ACCEPTANCE.md)、[GUI_ACCEPTANCE.md](../GUI_ACCEPTANCE.md)：NG GUI・専用範囲の原要件照合 | 同じ実務を完結することの確認。画面/操作キーの完全複製は対象外 | O02,V02 | H05〜H07,H13,H16,P08,D10,D11,N08,S07,V01〜V05 | 現存（限定） |
| K23 | F/I/O/N/W | [SAVE_COMPLETION.md](../SAVE_COMPLETION.md)、[EXTERNAL_MESH_WORKFLOW.md](../EXTERNAL_MESH_WORKFLOW.md)、[STATIC_FIELD_PROJECT.md](../STATIC_FIELD_PROJECT.md)、[STATIC_FIELD_JOBS.md](../STATIC_FIELD_JOBS.md)、[STATIC_FIELD_GUI.md](../STATIC_FIELD_GUI.md)、[STATIC_FIELD_STUDY_INPUT.md](../STATIC_FIELD_STUDY_INPUT.md)、[STATIC_FIELD_STUDY_JOBS.md](../STATIC_FIELD_STUDY_JOBS.md)、[STATIC_FIELD_STUDY_GUI.md](../STATIC_FIELD_STUDY_GUI.md)、[LOCAL_DISTRIBUTION_20260909.md](../LOCAL_DISTRIBUTION_20260909.md) | 高次/追加物理との一貫性、他環境/配布再受入 | O01（受入済）,O02,V02 | H05〜H07,H13,H16,P08,D10,D11,N08,S07,V01〜V05 | 現存（限定）。他OS配布は欠落 |
| K24 | F/I/O/N/W | [ELECTROSTATIC_FORMS.md](../ELECTROSTATIC_FORMS.md)、[ELECTROSTATIC_SOLVE.md](../ELECTROSTATIC_SOLVE.md)、[ELECTROSTATIC_NATIVE.md](../ELECTROSTATIC_NATIVE.md)、[PLANAR_ELECTROSTATIC_FORMS.md](../PLANAR_ELECTROSTATIC_FORMS.md)、[PLANAR_ELECTROSTATIC_SOLVE.md](../PLANAR_ELECTROSTATIC_SOLVE.md)、[PLANAR_ELECTROSTATIC_NATIVE.md](../PLANAR_ELECTROSTATIC_NATIVE.md)、[ELECTROSTATIC_BOUNDARY_STUDY.md](../ELECTROSTATIC_BOUNDARY_STUDY.md)、[S01_ACCEPTANCE.md](../S01_ACCEPTANCE.md)、静的Project/Job/Study群 | C00の対象版照合・純Neumann等は未完 | S01 | S01,S06,C07-static | 現存（限定）。対象版照合は欠落 |
| K25 | F/I/O/N/W | [PLANAR_MAGNETOSTATIC_SOLVE.md](../PLANAR_MAGNETOSTATIC_SOLVE.md)、[PLANAR_MAGNETOSTATIC_NATIVE.md](../PLANAR_MAGNETOSTATIC_NATIVE.md)、[AXIS_MAGNETOSTATIC_FORMS.md](../AXIS_MAGNETOSTATIC_FORMS.md)、[AXIS_MAGNETOSTATIC_SOLVE.md](../AXIS_MAGNETOSTATIC_SOLVE.md)、[AXIS_MAGNETOSTATIC_NATIVE.md](../AXIS_MAGNETOSTATIC_NATIVE.md)、[MAGNETOSTATIC_BOUNDARY_STUDY.md](../MAGNETOSTATIC_BOUNDARY_STUDY.md)、[OFF_AXIS_MAGNETOSTATIC_FORMS.md](../OFF_AXIS_MAGNETOSTATIC_FORMS.md)、[OFF_AXIS_MAGNETOSTATIC_SOLVE.md](../OFF_AXIS_MAGNETOSTATIC_SOLVE.md)、[OFF_AXIS_MAGNETOSTATIC_NATIVE.md](../OFF_AXIS_MAGNETOSTATIC_NATIVE.md)、[S02_ACCEPTANCE.md](../S02_ACCEPTANCE.md) | C00.Vの対象版照合は未完 | S02 | S02,S06,C07-static | 現存（限定）。対象版照合は欠落 |
| K26 | F/I/O/N/W | [S04_ACCEPTANCE.md](../S04_ACCEPTANCE.md)、[AXIS_BH_*.md](../AXIS_BH_FORMS.md)、[PLANAR_BH_*.md](../PLANAR_BH_FORMS.md)、[OFF_AXIS_BH_*.md](../OFF_AXIS_BH_FORMS.md)：単調表/来歴・P1の解/失敗保存/CLI・元場/解析/BVP | C00.Vの対象版/材料モデルは未確認 | S04 | S04,S06,C07-static | 現存（限定）。対象版/材料モデルは欠落 |
| K27 | F/I/O/N/W | [S03_ACCEPTANCE.md](../S03_ACCEPTANCE.md)、[AXIS_RECOIL_*.md](../AXIS_RECOIL_FORMS.md)、[PLANAR_RECOIL_*.md](../PLANAR_RECOIL_FORMS.md)、[OFF_AXIS_RECOIL_NATIVE.md](../OFF_AXIS_RECOIL_NATIVE.md)：反跳FEM/保存・再構築・CLI | C00.Vの対象版/材料モデル確認は未完 | S03 | S03,S06,C07-static | 現存（限定）。対象版/材料モデルは欠落 |
| K28 | F/I/O/N/W | [S05_ACCEPTANCE.md](../S05_ACCEPTANCE.md)、[S05_GUI_HANDOFF.md](../S05_GUI_HANDOFF.md)：S02ベース平面線形/B-H/反跳と正半径線形軸力・native/CLI/GUI量受渡し | C00.V対象版と未対応範囲の必須性は未確認 | S05 | S05,S06,L02〜L04,C07-static | 現存（限定）。対象版/軸対称力範囲は欠落 |
| K29 | F/I/O/N/W | なし（未実装） | ツール一覧と実際の近似モデル/用途を確定。3D RFQと同一視しない | L01 | L01,L04 | 欠落（対象版ツール一覧） |
| K30 | F/I/O/N/W | なし（未実装） | 対象配布物での有無と必要操作を確認して採否・個別仕様 | L02 | L02,L03,L04 | 欠落（対象版機能の有無） |
| K31 | F/I/O/N/W | なし（未実装） | 公開可能な寸法/境界/参照不確かさ。旧との一致だけで実測一致としない | V01 | L06,L07 | 欠落（実機資料） |
| K32 | 別計画で確定 | なし | X01。本計画の互換必須集合外。未実装をPASSにしない | X01 | （本計画にカードなし。L05で必要時展開） | 対象外 |

### 1.1 受入軸（F/I/O/N/W）の状態

`限` = 上表の文書に限定受入の証拠がある（行全体は UNVERIFIED）。
`未` = UNVERIFIED（証拠なし・未確認）。`N/A` = 適用しない（理由付き）。

| K | F | I | O | N | W | 備考 |
|---|---|---|---|---|---|---|
| K01 | 限 | 限 | 限 | 限 | 限 | C02初期AF部分集合のみ |
| K02 | 限 | 限 | 限 | 限 | 限 | 曲線幾何/FEMの限定範囲 |
| K03 | 限 | 限 | 限 | 限 | 限 | 軸接続単一外周 |
| K04 | 限 | 限 | 限 | 限 | 限 | 直線の連結真空・m=0 Hφ族 |
| K05 | 限 | 限 | 限 | 限 | 限 | 品質条件・外部mesh単体 |
| K06 | 限 | 限 | 限 | 限 | 限 | P2/適応版1〜3 |
| K07 | 限 | 限 | 限 | 限 | 限 | 対象ケース照合の範囲 |
| K08 | 限 | 限 | 限 | 限 | 限 | 平坦z端・鏡映のみ |
| K09 | 限 | 限 | 限 | 限 | 限 | 直線/曲線P2、一般形状追跡は未 |
| K10 | 限 | 限 | 限 | 限 | 限 | 両尺度/両次数・追跡版1〜7 |
| K11 | 限 | 限 | 限 | 限 | 限 | TEM/TM・矩形穴 |
| K12 | 限 | 限 | 限 | 限 | 限 | 線形実数材料 |
| K13 | 限 | 限 | 限 | 限 | 限 | 二つのRQ規約の限定比較 |
| K14 | 限 | 限 | 限 | 限 | 限 | 加速量規約の限定比較 |
| K15 | 限 | 限 | 限 | 限 | 限 | 固定丸めの限定評価 |
| K16 | 限 | 限 | 限 | 限 | 限 | 軸/半径プローブ等 |
| K17 | 限 | 限 | 限 | 限 | 限 | 明示写像/メッシュ対応 |
| K18 | 限 | 限 | 限 | 限 | 限 | 1変数tune・2変数RF探索 |
| K19 | 限 | 限 | 限 | 限 | 限 | C02初期部分集合 |
| K20 | 未 | 未 | 限 | 限 | 限 | 比較スクリプトの読取のみ |
| K21 | 未 | 未 | 未 | N/A | 未 | N/A理由：単独で数値ソルバーを追加しない |
| K22 | 限 | 限 | 限 | 限 | 限 | O02専用範囲 |
| K23 | 限 | 限 | 限 | 限 | 限 | ローカル保存/配布 |
| K24 | 限 | 限 | 限 | 限 | 限 | 電荷/電位/誘電率 |
| K25 | 限 | 限 | 限 | 限 | 限 | 電流/透磁率 |
| K26 | 限 | 限 | 限 | 限 | 限 | 単調BH表・P1 |
| K27 | 限 | 限 | 限 | 限 | 限 | 反跳材料 |
| K28 | 限 | 限 | 限 | 限 | 限 | 多極/力/トルクの限定範囲 |
| K29 | 未 | 未 | 未 | 未 | 未 | 未実装 |
| K30 | 未 | 未 | 未 | 未 | 未 | 未実装 |
| K31 | 未 | 未 | 未 | 未 | 未 | 未実装 |
| K32 | N/A | N/A | N/A | N/A | N/A | N/A理由：X01として本計画の互換必須集合外 |

`限` の内容は §1 の各行に列挙した文書に限定する。`限` を行全体の互換受入や互換率へ読み替えない。

## 2. 親課題33件と担当カード

22未受入親すべてに担当カードがある（下表）。受入済み10親は再実装対象にしない。
件数は互換率・工数比ではない。親の完了出口は、その時点の追加必須カードが全て受入済みであることを要求する。

| 親 | 状態 | 現在の受入範囲（代表文書） | 本計画カード | 完了出口／残件 |
|---|---|---|---|---|
| C00 | 進行 | [COMPATIBILITY_BASELINE.md](../COMPATIBILITY_BASELINE.md)（K行と限定TM辞書） | B01〜B04,L05 | 対象版C00.V・必須集合・K行の全軸確定。B04で更新手順を集約 |
| C01 | 受入済 | [MODEL_CONTRACT.md](../MODEL_CONTRACT.md) | なし（維持） | v3共通契約。再実装しない |
| C02 | 受入済（初期AF部分集合） | [LEGACY_INPUT.md](../LEGACY_INPUT.md) | C01,C02,C03（追加部分集合、§4） | 初期部分集合は維持。追加NT=2/3等はC01〜C03 |
| C03 | 他未受入 | 個別プローブのみ（[INDEPENDENT_COMPARISON.md](../INDEPENDENT_COMPARISON.md)） | C04,C05,C06 | 旧テキスト出力/プローブの契約・実装・受渡し |
| C04 | 他未受入 | 個別比較のみ（比較スクリプト） | C07-TM,C07-TE,C07-planar,C07-hphi,C07-material,C07-static,C07,C08 | 全必須機能の物理別ブラックボックス回帰 |
| G01 | 受入済 | 軸接続単一輪郭 | なし（維持） | 再実装しない |
| G02 | 受入済 | 自動メッシュ（品質付き） | なし（維持） | 再実装しない |
| G03 | 進行 | [G03_ACCEPTANCE.md](../G03_ACCEPTANCE.md)、[G03_CURRENT_AUDIT.md](../G03_CURRENT_AUDIT.md)、[CURVED_ELEMENTS.md](../CURVED_ELEMENTS.md)、[OFFSET_DEGENERACIES.md](../OFFSET_DEGENERACIES.md) | C01,C02,C03,N01〜N04 | 異なる支持曲線の一般重解/全弧端・物理ピーク収束・旧曲線入力 |
| N01 | 受入済 | [QUADRATIC_ELEMENTS.md](../QUADRATIC_ELEMENTS.md) | なし（維持） | P2固有値コア。再実装しない |
| N02 | 受入済 | 直線P2 | なし（維持） | 再実装しない |
| N03 | 進行 | [RF_DISCRETE_PEAKS.md](../RF_DISCRETE_PEAKS.md)、[AFFINE_SURFACE_EXTREMA.md](../AFFINE_SURFACE_EXTREMA.md)、[SURFACE_CONVERGENCE.md](../SURFACE_CONVERGENCE.md) | N01〜N04 | 一般例/幾何差/独立物理の検証 |
| N04 | 進行 | [ADAPTIVE_REFINEMENT.md](../ADAPTIVE_REFINEMENT.md)、[ADAPTIVE_SURFACE_STOPPING.md](../ADAPTIVE_SURFACE_STOPPING.md)、曲線適応群 | N05〜N08 | 適応対一様の一般ケース精度対費用・保存/GUI |
| D01 | 受入済 | [D01_ACCEPTANCE.md](../D01_ACCEPTANCE.md) | なし（維持） | 元要件・一般写像・個別ID回復・全利用先 |
| D02 | 進行 | [TUNING.md](../TUNING.md)、[CURVED_HARMONIC_TUNING.md](../CURVED_HARMONIC_TUNING.md)、[GUI_PLANAR_TUNING.md](../GUI_PLANAR_TUNING.md)、[D02_PHYSICS_ROUTING.md](../D02_PHYSICS_ROUTING.md) | H01〜H18,P01〜P04,D01〜D04 | Hφ/平面一般形状・回復・TM/TE残要件 |
| D03 | 進行 | [RF_OPTIMIZATION.md](../RF_OPTIMIZATION.md)、[RF_OPTIMIZATION_GEOMETRY.md](../RF_OPTIMIZATION_GEOMETRY.md)、[RF_DESIGN_CRITERIA.md](../RF_DESIGN_CRITERIA.md) | D05〜D11 | 一般形状/追加物理/最終制約検証 |
| P01 | 進行 | [AXISYMMETRIC_TE.md](../AXISYMMETRIC_TE.md)、[CURVED_TE_PLAN.md](../CURVED_TE_PLAN.md)、[TE_JOBS.md](../TE_JOBS.md) | D01,D03,D04,C07-TE | 直線形状/親要件照合 |
| P02 | 進行 | [PLANAR_RF.md](../PLANAR_RF.md)、[PLANAR_POLYGON_RF.md](../PLANAR_POLYGON_RF.md)、追跡版1〜7群 | P01〜P10 | 一般変形/曲線/回復 |
| P03 | 進行 | [COAXIAL_RF.md](../COAXIAL_RF.md)、[HPHI_MESH_RF.md](../HPHI_MESH_RF.md)、[AXIS_HPHI_RF.md](../AXIS_HPHI_RF.md)、[AXIS_HPHI_WORKSPACE.md](../AXIS_HPHI_WORKSPACE.md) | H01〜H13,H18,C07-hphi | 形状比較/曲線追跡等 |
| P04 | 進行 | [MATERIAL_HPHI_FORMS.md](../MATERIAL_HPHI_FORMS.md)、[MATERIAL_HPHI_RF.md](../MATERIAL_HPHI_RF.md)、[MATERIAL_HPHI_WORKSPACE.md](../MATERIAL_HPHI_WORKSPACE.md) | H10,H14〜H18,C07-material | 比較/追跡/損失要否 |
| O01 | 受入済 | [SAVE_COMPLETION.md](../SAVE_COMPLETION.md) | なし（維持） | ローカル保存完了契約 |
| O02 | 進行 | [O02_ACCEPTANCE.md](../O02_ACCEPTANCE.md)、[GUI_ACCEPTANCE.md](../GUI_ACCEPTANCE.md)、静的Project/Job/Study群 | H05〜H07,H13,H16,P08,D10,D11,N08,S07 | 追加経路のProject/GUI接続 |
| R01 | 受入済 | [ACCELERATING_CONVENTIONS.md](../ACCELERATING_CONVENTIONS.md) | なし（維持） | native加速量規約 |
| S01 | 進行 | [S01_ACCEPTANCE.md](../S01_ACCEPTANCE.md)、[ELECTROSTATIC_*.md](../ELECTROSTATIC_FORMS.md)、静的Project/Job/Study群 | S01,S06,C07-static | C00.V対象版の境界/電極照合 |
| S02 | 進行 | [S02_ACCEPTANCE.md](../S02_ACCEPTANCE.md)、[PLANAR/AXIS/OFF_AXIS_MAGNETOSTATIC_*.md](../PLANAR_MAGNETOSTATIC_SOLVE.md) | S02,S06,C07-static | 対象版のポテンシャル/電流仕様照合 |
| S03 | 進行 | [S03_ACCEPTANCE.md](../S03_ACCEPTANCE.md)、[AXIS/PLANAR/OFF_AXIS_RECOIL_*.md](../AXIS_RECOIL_FORMS.md) | S03,S06,C07-static | 対象版の材料モデル照合 |
| S04 | 進行 | [S04_ACCEPTANCE.md](../S04_ACCEPTANCE.md)、[AXIS/PLANAR/OFF_AXIS_BH_*.md](../AXIS_BH_FORMS.md) | S04,S06,C07-static | 対象版のB-Hモデル/失敗仕様照合 |
| S05 | 進行 | [S05_ACCEPTANCE.md](../S05_ACCEPTANCE.md)、[S05_GUI_HANDOFF.md](../S05_GUI_HANDOFF.md) | S05,S06,C07-static | 対象版の多極/力/トルク規約照合 |
| L01 | 他未受入 | なし | L01,L04 | 専用tuner/RFQ/utilityのツール別確定 |
| L02 | 他未受入 | なし | L02,L03,L04 | 磁石最適化・熱機能の存在と必須性 |
| V01 | 他未受入 | なし | L06,L07 | 実機資料・不確かさ・来歴付き照合 |
| V02 | 他未受入 | [LOCAL_DISTRIBUTION_20260909.md](../LOCAL_DISTRIBUTION_20260909.md)（ローカル配布の限定確認） | V01〜V05 | 全必須機能/対象環境/実業務の統合受入 |
| A01 | 受入済 | [A01_BACKEND_COMPARISON.md](../A01_BACKEND_COMPARISON.md) | なし（維持） | 候補比較とADR-018 |
| X01 | 範囲外 | なし | なし（必要時にL05で展開） | 本v0の実装予定に組み込まない |

集計：受入済10、進行16、他未受入6、範囲外1。進行＋他未受入＝22親すべてに担当カードがある。

## 3. C02追加部分集合の別管理

初期AF部分集合（受入済み）と追加部分集合を混同しない。

| 区分 | 内容 | 管理場所 |
|---|---|---|
| 初期部分集合（受入維持） | 単一REG・軸接続真空・閉PEC・z非減少壁・直線/短円弧。位置付きstrict読込、明示NG設定、原入力/hash・変換診断 | [LEGACY_INPUT.md](../LEGACY_INPUT.md)。取り消さない |
| 追加部分集合（未受入） | NT=2楕円/NT=3双曲線のstrict読込と変換記録、全必須機能の旧計算等価 | C01（仕様）、C02（実装）、C03（検証） |
| 境界 | 追加分の受入は初期部分集合の受入を変更しない | 本節とC01〜C03カード |

## 4. 証拠の現存/欠落

現存（repo、限定受入の根拠）：
- 受入文書群（§1の各リンク）、[compatibility_reference_inventory.json](../compatibility_reference_inventory.json)、
  [c00_conic_input_reference_audit.json](../c00_conic_input_reference_audit.json)、
  [SUPERFISH_COMPARISON.md](../SUPERFISH_COMPARISON.md)、[MILESTONE_ACCEPTANCE.md](../MILESTONE_ACCEPTANCE.md)、
  [SURFACE_FIELD_DIAGNOSTICS.md](../SURFACE_FIELD_DIAGNOSTICS.md)。

欠落（対象版/実機/文書で、C00.V・B02/B03・L系/S系の前提）：
- 対象版C00.Vの機能集合・各ツール表示版・付属文書改訂日（K29/K30含む）。
- R25抽出テキストの現在の欠落（COMPATIBILITY_BASELINE 2026-09-14追補）。
- 旧曲線パラメータ実行検証、一般AF入力変換、旧版Cartesian実行、旧tuner照合。
- 実機参照（K31、L06/L07）、他OS配布再受入（K23/V02）。

欠落は UNVERIFIED のまま保持し、N/A へ読み替えない。`out/` のrawは配布物へ入れない。

## 5. 履歴の扱い

[BACKLOG.md](../BACKLOG.md)、[IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md)、
[COMPATIBILITY_MATRIX.md](../COMPATIBILITY_MATRIX.md)、[COMPATIBILITY_PLAN.md](../COMPATIBILITY_PLAN.md)
の日付付き経過記録は削除しない。各文書の冒頭に本台帳への案内を付し、現行表として本台帳を参照する。
古い「未接続」「次は」は履歴であり、そこから新しい必須要件を生成しない。

## 6. 検証と未確認

- 種別：文書/監査。FEM/unittest/GUIは実行しない（変更が文書のみのため）。
- 確認方法：全32行と33親の対応、22未受入親の担当カード有無、C02追加分の別管理、
  受入済み10親が再実装対象でないこと、リンク先文書の実在を差分で確認。
- 未確認：§4の欠落項目。対象版/実機/抽出テキストは未取得で、推測実装しない。
- 次：B04（更新手順の集約）とL05（新規必須仕様のカード展開）。実装区切りはH01。

# 単位付き式による周波数調整 — 要求版7

2026-09-15 JST、開始HEAD `7d3455e`。D02/P2-02の非多項式関数連動を、
profile座標とnative曲線寸法の実形状生成・実FEM・保存再開へ接続した。
GUIの入力・保存復元コードも追加したが、実ブラウザー検証と曲線の専用RF/場検証は未完了。
**D02親と全計画の完了を意味しない。**

## 入力

要求版1〜5の共通項目（project、parameter、bounds、目標・停止条件、ID、controls、
refinement_scale等）を保持し、`schema_version: 7`、`parameter_unit: "m" | "1"`、
`geometry_kind: "profile" | "curved_harmonic"`、`bindings`を明示する。
bindingsは重複対象のない非空配列で、各要素のキーはpathとexpressionのみ。

```json
{
  "path": "/case/geometry/points_zr_m/0/1",
  "expression": {
    "op": "mul",
    "args": [
      {"constant": 0.1, "unit": "m"},
      {"op": "exp", "args": [{"variable": "x"}]}
    ]
  }
}
```

この例はparameter=x、parameter_unit=1の場合の半径 `0.1 exp(x) m`。
profileの全半径を連動する場合は各頂点に同じ式を指定する。
構文・演算・次元・有限実数・予算は[SCALAR_EXPRESSIONS.md](SCALAR_EXPRESSIONS.md)に従う。
長さはSI m、角度radと曲線パラメータは無次元1として検査する。
少なくとも一つの式が変数を参照し、両端の実形状が浮動小数表現上異なることを要求する。
変数参照だけで真の非定数性を証明したとは扱わない。

profileのpathは既存の `/case/geometry/points_zr_m/頂点/0または1` のみ。
曲線は `/case/geometry/curves/番号/数値項目`、対象数値項目は版5と同じ。
曲線数・種類・タグ・境界分割・離散branch・solver設定は式で変更できない。

曲線の場合だけrf_coordinates（fixed/axis_fraction）とminimum_corner_angle_degを必須にする。
refinement_scaleは2の累乗。controlsはcomparison_meshesを含まないpiecewise_remesh。
各試行の実Projectから、元の固定細分履歴を持つ比較メッシュを導出する。
profileは既存のnormalized_cylinder/normalized_profileと明示メッシュ拒否を維持する。
TE、未対応物理、未固定のmarked選択、無効な形状・写像は既存規約どおり拒否する。

## 計算・保存

毎回元Projectの数値項目へ全式を反映してから、結合された形状を検査する。
曲線は既存の調和変位を使い、正Jacobian・全境界・要素品質・固定履歴を検査する。
多項式近似や解析周波数によるFEMの代用はしない。
個別ID確認、二分探索、目標差と最終細分差の別ゲートを維持する。

版7は共通execute_tune/replay_tune、CLI、JobManager、GUI APIへ接続する。
checkpoint版1に式の元要求を保存する。外側回復要求版6は内部版7も許可し、
回復付きの場合は既存checkpoint版2を使う。旧版1〜5の入力形式を変更しない。
式の途中定義域エラーはFEM前に停止し、failure記録と直前までのcheckpointを保持する。
再生・再開では元要求と各実Projectを再構築するため式の改変を検出する。
非滑らかな式や条件分岐も許すが、区間全体の連続性・単調性・一意根は保証しない。

## 今回の証拠と残件

`out/expression-tuning-20260915/` に実行ログを保存。
新5件の初回は15.627秒PASS。版7未実装時のbaselineエラーも保持した。
指数半径の直接座標・単位変更、非アフィン曲線の独立Green面積/体積尺度則、
全親接続と細分比較分割、入力拒否、実FEMの解析log半径目標、再生改変拒否、
内点のゼロ除算時のFEM未実行と元ファイル全byte保持を検査した。

CLI1解とGUI API経由の実worker1解の要求・試行情報が完全一致し、両者PAUSED。
重複JSONキーはジョブ作成前に拒否した。transport.jsonに記録。
保存した12場配列と全モードRF量もCLI/worker間で完全一致、元16ファイルのSHAを保持。
native-fidelity.jsonに記録し、この照合ではFEMを追加実行していない。
検証コードの初回JobManager context manager誤用はtransport.logに残し、
明示closeへ修正して保存CLI解を再利用した（CLIの再計算なし）。

関連8モジュール50件232.352秒PASS、回復要求の追加1件0.355秒PASS（計51件、分割実行）。
CLI/worker各1実FEM、保存12配列・全RF一致、元16ファイル保持。node --check終了0。
全検証handle終端、live processなし。実ブラウザー/曲線専用RF/版7実回復は未検証。
対象はtest_scalar_expressions/test_expression_tuning/test_coupled_tuning/test_polynomial_tuning/
test_tuning/test_gui_tuning/test_tuning_jobs/test_curved_harmonic_tuningと、
TuningIdentityRecoveryTests.test_strict_wrapper_policy_and_unavailable_anchor。
詳細はacceptance.jsonを参照。
この段階で実ブラウザー、曲線版7の実FEM/RF/場尺度則、版7の実回復事例を
検証済みとはしない。次にそれらとGUIの入力/保存/再開/既存版互換を検証する。
全suite・seed・Hosted CI・新Wine比較は今回未実行。solver核に変更なし。
境界分割変更と他物理の調整、D03の一般制約付き探索は別の明示残件として保持する。

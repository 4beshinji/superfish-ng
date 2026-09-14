# 単位付き式による周波数調整 — 要求版7

2026-09-15 JST、開始HEAD `7d3455e`。D02/P2-02の非多項式関数連動を、
profile座標とnative曲線寸法の実形状生成・実FEM・保存再開へ接続した。
GUIの入力・保存復元、実ブラウザー、曲線RF/場尺度則、版7の実ID回復を追加検証済み。
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
実装コミット0706c70時点では実ブラウザー、曲線のRF/場尺度則、実回復が未検証だった。
以下の追加検証でこの残件を解消した。
全suite・seed・Hosted CI・新Wine比較は今回未実行。solver核に変更なし。
境界分割変更と他物理の調整、D03の一般制約付き探索は別の明示残件として保持する。

## 版7の実経路追加検証（開始HEAD 0706c70）

製品コードを変更せず、既存Chrome検証器にprofile/曲線の式入力分岐を追加した。
フォームの厳密な元要求一致、単位/形状方式の表示、式内重複キーの実行前拒否、
2試行での一時停止、式の保存復元、完全一致のダウンロード、改変保存の拒否、
再開と最終細分の別ゲート、対象IDのnative場表示を実際のworkerで確認する。
旧版1の同じ保存・再開経路も別ブラウザーで確認する。

数値側は、非多項式の軸長 `0.08 exp(x) m` を外側回復要求版6に組み込み、
主比較で個別IDが未確定になる試行から明示anchorでIDを回復する実ケースを実行した。
成功15試行（14回の回復）、別の回復失敗2試行、計17実FEM。
保存再開で元sourceを保持、失敗はUNVERIFIED・周波数nullで停止した。
TM011のBessel分散式との相対差は最大2.854e-5未満、最終細分1.797e-6未満。
既存の解析許容値（粗1e-4、細1e-5）を満たす。例示の観測値を許容値にはしていない。

曲線側は先行1実FEMから操作検証用の目標を指定し、元寸法と全寸法2倍を別に調整する。
この目標は精度基準ではない。精度とは別に、Green境界積分による面積・回転体積と、
Maxwellの周波数/RF/全場の尺度則を保存した実FEMから照合する。
局所座標の同じ点でHphi/Er/Ezをすべて比較し、U=1 Jの場倍率2^(-3/2)を検査する。
周波数は1/2、両R/Q・geometry factor・transit time factorは不変。
曲線変形による面積倍率は1+expm1(x)/8、回転体積倍率はその二乗。

詳細な結果は同out配下のbrowser-*/report.json、expression-recovery.json、
curve-scale-comparison.json、およびacceptance.jsonに保持する。
検証中に新たな製品変更がなかったため、前回の関連51unitを重複実行していない。

追加検証はすべてPASS。Chrome profile9/曲線9/旧版7項目、外部HTTP0、製品332ファイルSHA保持。
GUI37実FEM＋曲線pilot1＋倍寸法3＋回復17＝58実FEM。全9ジョブ完了後、専用GUIをSIGINTで停止し終了0を回収。
取り込み3解の全保存配列/全RF量が元解と完全一致し、元29ファイルを保持した。
曲線RF尺度差最大4.652e-14未満、全場尺度差最大2.857e-14未満。全6元曲線解は変更なし。
正本索引はoutのacceptance.json、共有要約はbenchmarks/tuning/expression-tuning-20260915.json。
D02の次の実装課題は試行ごとの境界分割変更と、物理別の調整接続。D03一般制約付き探索は別親で保持する。

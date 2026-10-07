# N03：固定五系列の条件別受入

2026-10-08 JST、N03カードはDONE。先行N02はDONE。
これはN01の固定合成入力に対する経験的受入。N04/親G03・原互換32要件/全goalは継続する。

| 系列 | native | 独立現代参照 | 受入FEM水準 |
| --- | --- | --- | --- |
| N01-ellipse-archive | PASS | PASS | [0, 1, 2] |
| N01-prolate-new | PASS | PASS | [2, 3, 4] |
| N01-rounded-two-lobe | PASS | PASS | [0, 1, 2] |
| N01-sharp-two-lobe | SINGULAR_GEOMETRY | SINGULAR_GEOMETRY | [0, 1, 2] |
| N01-sphere-control | PASS | PASS | [0, 1, 2] |

各滑らかな例の固定P2幾何三水準で、元Hφに基づく三個別IDを追跡し、連続FEM二区間を確認した。
最細FEMで幾何二区間と面積/回転体積・全曲線・同一二次境界・Ritz/求積を別判定した。
f1e-4、両R/Q・G0.005、離散peak比上下界0.01を維持した。
独立参照三h水準の連続二区間、最終nativeとの全域E/H0.005・物理軸Ez0.01、
f/RF/peakと単一符号を確認し、振幅fit・領域縮小・標本削除をしなかった。
鋭角は有限ピークを受入量に含めず、非ピークPASSとSINGULAR_GEOMETRYを保持する。

元native45点と追加長楕円体六点、実参照25求解は過去の固定源実行証拠を使用した。
追加2/3/4の成功を、元0/1/2のR/Q失敗へ書き戻さない。
粗い参照球/領域lookup等の失敗と費用も保持する。
[五系列の条件/費用/公開参照API](N03_PHYSICAL_SERIES.md)と
[元ID来歴を保持した明示追加水準](N03_APPENDED_FEM_WINDOW.md)に詳細を記録した。

## 節目全検証と独立したseed回帰

localhost可の環境で全scripts/validate.pyを一度完走した。
2485検査/499モジュール、4772.019秒・終了0/PASS、0FAIL/0ERROR/3skip。
全1405対象ファイルは開始/終端/監査時に一致した。
skip理由は下記の元記録を保持し、対応物理を実行済みに数えない。

```json
[
  {
    "id": "test_independent_comparison.ReferencePhysicsTests.test_pillbox_frequency_rf_and_bessel_field",
    "reason": "optional NGSolve reference environment"
  },
  {
    "id": "test_independent_comparison.ReferencePhysicsTests.test_reference_rejects_unsupported_physics",
    "reason": "optional NGSolve reference environment"
  },
  {
    "id": "test_planar_curved_tuning_saved.PlanarCurvedOwnedTuningTests.test_actual_accepted_circle_and_recovered_ellipse_import_move_and_replay",
    "reason": "dedicated accepted circle/TE native evidence root required"
  }
]
```

元benchmarks/validationのseed9モード/周波数・RF207量を相対1e-10で別照合し、
最大相対差はf=0、RF=8.88178e-16だった。
元Case/mesh/両閉PEC端・1 J・全旧規約は一致。既知のscope/domain注記だけを厳密に確認した。
一つの固有ベクトル符号反転は複素電圧の両成分へ共通適用し、許容差を変更しない。
初回sandboxのHTTP socket禁止での失敗/終了130・244/499モジュール・1919.016秒は
別の部分実行として保全し、full受入に数えなかった。

## 監査・来歴・適用限界

raw `out/n03-native-surface-series-20261007/n03-card-acceptance.json` は五系列の条件、
物理検査元1199源（変更前三源だけ明示archive解決）、全523bound入力、
節目全検証の終端とseed別照合を結び付ける。監査は新FEM/新場標本0。
全検証は新N06基盤追加前の1405対象ファイルに対する証拠であり、後続追加源のfull受入ではない。
現代MIT cavsim2d/NGSolveの固定参照は製品依存/solve時通信に追加しない。
legacy source/binaryを参照/同梱せず、合成入力を実機測定と呼ばない。

元場の有限Gauss診断、native離散peak上下界、参照solverのpeak推定による経験的確認である。
連続PDE一般誤差上界/厳密な連続最大値の証明とは呼ばず、
physical_error_boundとphysical_peak_error_boundはnullを維持する。
旧NT=2/3などと親G03の全必須行の対応はC03/N04の後続監査で確認する。
数値文言・件数・hashだけのために新しいunit/FEM/fullを再実行しない。

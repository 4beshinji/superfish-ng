# 平面線形磁静場の材料・電流・Az弱形式

2026-09-13 JST。[計画](PLANAR_MAGNETOSTATIC_FORMS_PLAN.md)の固定710sourceを主716sourceへ統合し、弱形式API範囲で限定受入。
候補は `/tmp/superfish-planar-magnetostatic-forms-final-20260913`。

`LinearMagneticMaterial` と `PlanarMagneticPartition` は正値実数mu_r・全領域/セル割当・界面・領域面積・reluctivity=1/(mu0 mu_r)を保持する。
直線の単純多角形を対象とし、境界条件や厚さを仮定しない中立Cartesian JSONを使う。未割当/重複、epsilon/RF、非線形BH・異方性・永久磁石・曲線/穴は拒否する。

`planar_magnetostatic_forms` はAz[Wb/m]、B=(∂yAz,−∂xAz)[T]、H=B/(mu0 mu_r)[A/m]に対し、
K=∫(mu0 mu_r)^−1 gradNi·gradNj dxdy [m/H] と f=∫Jz Ni dxdy [A]を全DOFで組み立てる。
Jzは領域ごとの符号付きA/m²。定数Azのgauge核、総電流と符号相殺を保持する。境界条件/解法/場は後続工程。

先にmu倍率の逆比例則を確認した。静電のepsilon係数をmuへ読み替える試行では倍率7に対しKが7倍となり、必要な1/7則を満たさない。
これは電気の演算子自体の欠陥ではなく、磁気へ流用できない構成則の違いである。記録は `out/planar-magnetostatic-forms-development-20260913/before-invariant.json`。
新しい磁気弱形式は独立にreluctivityで組み立て、静電行列やソルバーを呼ばない。

追加5unitがPASS。独立検証は矩形/凹形、P1/P2、材料3パターン、尺度0.5/2、剛体変換3通りの72例。
独立18×18 Gauss/Vandermonde K/f、216多項式、72定数核全スペクトル、72mu倍率、72電流反転、72一様Bエネルギー、領域順序/JSON往復を検査した。
元の多角形/所有範囲検証と基底の独立積分方式だけを再利用し、磁気の係数・SI量・解析不変量を明示している。

独立記録は `out/planar-magnetostatic-forms-independent-final-20260913/report.json`、1.582秒でPASS。
最大相対差はK 3.150e-15、f 2.206e-15、尺度/剛体変換3.736e-15、多項式6.884e-15、総電流4.552e-15、mu逆比例2.852e-16、一様Bエネルギー9.548e-15。
標準1166件は `out/validation-planar-magnetostatic-forms-final-candidate-20260913` へ終了0。本体5unit/独立72例もPASS。

固定境界付き磁静場の解法、元B/H・磁束/エネルギー、軸対称、保存/CLI/GUI、外部境界は未接続。
新規依存・外部資料・旧版実行なし。S02と全計画は未完。

静電の実行例を専用フォルダへ移した修正を継承した。旧固定候補の全標準は失敗が既知となった時点で自身のunittest子だけを停止し終了241（合格とは扱わない）。元ログは保持する。磁気の製品/テストは変更せず、新規5+旧RF移行2unitと独立72例を再検証してPASS。修正固定候補で全標準を新規に実行してPASS。

標準2268.792秒、1163合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主5unitは0.378秒、主独立72例は1.582秒でPASS。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。

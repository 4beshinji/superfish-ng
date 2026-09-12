# 平面静電の誘電体分割・体積電荷・弱形式

2026-09-13 JST。[計画](PLANAR_ELECTROSTATIC_FORMS_PLAN.md)に従う固定候補692sourceを主698sourceへ統合し、行列/荷重API範囲で限定受入。
候補は `/tmp/superfish-planar-electrostatic-forms-20260913`。主ツリー統合・再検証済み。

`PlanarDielectricPartition` は既存の単純多角形メッシュ検査を幾何だけに使い、
全セルのepsilon_r・材料/領域・界面・領域面積を保持する。境界の電気的条件は宣言しない。
既存RFのPlanarMesh保存形式にはPEC宣言があるため、静電側の幾何JSONは
`explicit_straight_simple_polygon` と頂点/セルだけの中立な形式にした。
曲線、穴、異方性、非線形、mu_r、phasor、暗黙の厚さ・未割当材料を拒否する。

`planar_electrostatic_forms` は全領域の符号付きrho[C/m³]から、
K=epsilon0∫epsilon_r grad(Ni)·grad(Nj) dxdy [F/m] と
f=∫rho Ni dxdy [C/m] をP1/P2で組み立てる。
xyに垂直な方向に一様な場の単位長さ当たりの量であり、回転体の2πrを掛けない。
全DOFと定数電位核を保持し、x=0に軸の意味を与えない。
電荷和と領域面積の照合は符号相殺も扱う。積分次数/+4の差は離散化誤差の上界ではない。

追加5unitは0.327秒でPASS。最初のテスト用凹形メッシュが解析上の水平材料界面を横切っていたため、
領域面積と多項式形式の照合が失敗した。テスト入力だけを界面適合グリッドへ修正し、製品行列と許容差は不変。
その前の配列添字の誤りも含め、初回ログ・入力・修正理由は
`out/planar-electrostatic-forms-development-20260913/fixture-correction.json` と関連ログに保持した。

独立記録は `out/planar-electrostatic-forms-independent-20260913/report.json`。
矩形/凹形、P1/P2、材料3パターン、尺度0.5/2、剛体変換3通りの72例で、独立18×18 Gauss/Vandermonde K/f、
定数核の全スペクトル72、領域順序変更72、JSON往復72、多項式積分216を照合した。
Kの最大相対差3.1591e-15、荷重2.2052e-15、尺度/剛体変換5.5455e-15、多項式6.5503e-15、総電荷4.5519e-15。
独立照合は0.917秒でPASS。標準1147件は `out/validation-planar-electrostatic-forms-candidate-20260913` へ終了0。本体5unitと独立72例もPASS。

平面の境界/gauge、Poisson解、E/D、J/mのエネルギー、F/mの容量、保存/CLI/GUIは後続工程。
新規依存・外部資料・旧版実行なし。S01と全計画は未完。

標準2229.919秒、1144合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主5unitは0.334秒、主独立照合は0.933秒。候補692sourceと不変egg-info 6件を加えた主698sourceを照合。既存しきい値・ベンチマークは不変。統合証拠は標準出力内seed_regression.json。

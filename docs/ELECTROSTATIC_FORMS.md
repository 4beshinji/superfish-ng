# 軸対称静電の誘電体分割・体積電荷・弱形式

2026-09-13 JST。固定候補 `/tmp/superfish-electrostatic-forms-20260913` の679sourceを主685sourceへ統合し、本書の行列/荷重API範囲で限定受入。
[受入条件](ELECTROSTATIC_FORMS_PLAN.md)に従い、境界条件を適用する前の静電行列と荷重を実装した。

`LinearDielectric` は正値実数のepsilon_rだけを持つ。`DielectricRegion` と
`AxisymmetricDielectricPartition` は、正半径または軸接続の直線三角形をすべて一度ずつ明示材料へ割り当てる。
独立したJSON形式は `superfish_ng_axisymmetric_dielectric_partition` 版1、座標はaxisymmetric_rz。
未割当、重複、未知材料、未使用材料、mu_r、phasor、損失、異方性、非線形、曲線・平面入力は拒否する。
幾何・領域検査には既存の自作材料分割の内部処理を使うが、RF行列やRFの物理規約は使わない。

`axisymmetric_electrostatic_forms(partition, charge_density_c_per_m3, element_order, quadrature_order=4)` は
全領域の符号付きrhoを必要とし、P1/P2の空間、CSR剛性K、荷重f、積分診断を返す。
Phi[V]に対しK=2π epsilon0 ∫epsilon_r r grad(Ni)·grad(Nj) dr dz [F]、
f=2π∫rho r Ni dr dz [C]。全軸DOFと定数電位の核を保持する。
外形メッシュの既存境界タグから電極条件を推測せず、境界条件・gaugeを適用しない。

rhoの正負・0・総電荷の相殺を受理し、bool・非有限値・巨大整数のオーバーフローや領域の欠落を拒否する。
積分次数と+4の差、荷重和と領域体積電荷の一致を診断する。これは離散化誤差の上界ではない。
静電位の解法、元E/D、電極電荷、静電エネルギー・容量、保存/CLI/GUIはまだ対象外である。

実装前の反例は `out/electrostatic-forms-development-20260913/before-invariant.json`。
静電APIがなく、既存RFの軸接続u行列に定数係数を入れた相対残差は0.074203だった。
静電の定数Phiは電場0であり、このRF行列を転用できない。

追加5unitは1.340秒でPASS。最初のパターン探索は既存GUI2件も含め7件PASSだったため、最後は対象2モジュールの5件を明示した。
独立記録は `out/electrostatic-forms-independent-final-20260913/report.json`。
軸あり/なし、穴0/1/2、P1/P2、材料3パターン、空間尺度0.5/2の72例で、
独立18×18 Gauss/Vandermonde K・f、定数核の全スペクトル72、材料/領域の順序変更72、JSON往復72を照合した。
矩形から穴を引く解析積分により、216件の多項式エネルギー形式・電荷仕事を別に検証した。
最大相対差はK 2.9615e-15、荷重2.7065e-15、尺度則6.3009e-16、多項式3.8414e-14、総電荷6.6613e-16。
許容差を緩めず、RFのベンチマークも変更していない。

標準1132件は `out/validation-electrostatic-forms-candidate-20260913` へ終了0。主5unitと独立72例もPASS。
新規外部資料・依存・物性表・旧版実行なし。S01と全計画は未完。

標準は2215.336秒、1129合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主5unit 1.368秒、主独立照合 3.067秒。候補679sourceと不変egg-info 6件を加えた主685sourceを照合。統合証拠は標準出力のseed_regression.json。

# 固定材料の元Project形状則

2026-09-22。H16-aの形状則を実装。細分基盤は[材料細分](MATERIAL_HPHI_REFINEMENT.md)。試行生成・比較空間・調整runnerへの接続は残る。

`MaterialHphiShapeLaw`版1は`uniform_scale`または`general_piecewise_affine`、正の`reference_value`、明示変位（uniformではnull）、`acceleration_policy=transport_on_axis`を持つ。`apply(project,value)`は専用材料Caseの元Projectを複製し、毎回元座標から候補を生成する。前試行への変形累積を行わない。

uniformは`value/reference_value`を全座標に掛ける。区分アフィンは全元頂点に対して`x+(value-reference_value)*displacement`。有理数演算後、一度binary64へ丸める。材料係数・ID・領域セル所有は固定し、元全境界頂点を明示した制御角点にして、穴・外壁・界面の区分変形を保持する。

候補両側の正Jacobianと完全な材料比較overlayで元領域/全界面を検証する。軸頂点の半径方向変位、fold、不完全変位、非有限座標、不正な要求、予算不足を拒否する。返り値は新Project、元から候補への完全な`MaterialHphiComparison`、境界対応/規模診断。元場、RF、周波数を移送・補正した結果ではなく、新候補は実FEM solveを必要とする。

加速区間の両端と位相原点を全て同じ軸写像で移す。betaを保持し、軸外への外挿を認めない。生成後の`MaterialHphiCase`構築で、区間内の全軸辺にepsilon_r=mu_r=1を再要求する。非真空の区間へ広げた加速指定を許さず、N/Aを0へ置換しない。

## 検査と来歴

`out/h16-material-shape-20260922/before.log`で未実装APIのred。`initial.log`は新3件、3.564秒PASS。

- 正半径/穴付き軸の区分材料を元Projectから2、1.5、1倍の順に生成。元入力不変、領域体積s³、epsilon/mu不変、実FEMのf/sを検査。
- 全加速座標とbeta、非真空区間拒否、軸外位相原点の外挿拒否を検査。
- 厳密版/キー/形状種、変位所有、不完全頂点、軸移動とfoldを拒否。
- 追加検査で内部界面頂点だけを移し、領域体積変化と全体体積保持、同じ片側セル所有、全界面overlayと予算拒否を確認。

追加1件＋関連8件の記録は`piecewise-related.log`、8.265秒PASS。新4件は分割実行証拠。関連は`test_material_hphi_comparison`7件と`test_material_hphi.MaterialHphiTests.test_strict_physics_and_only_explicit_vacuum_axis_path`。全handle終了0。

既存自作直線写像・全境界cycle・材料比較を再利用した専用形状則。新規外部資料・依存・legacy参照なし。元FEM組立/seed TMの変更はなく、形状の独立体積/尺度則と直接利用先に検査を限定した。H16-a/親H16の完了、全suite、調整やGUI受入を主張しない。

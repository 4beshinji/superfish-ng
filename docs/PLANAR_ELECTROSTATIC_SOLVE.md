# 平面静電Poisson解・元E/D・電荷/容量

2026-09-13 JST。[計画](PLANAR_ELECTROSTATIC_SOLVE_PLAN.md)に従う固定697sourceを主703sourceへ統合し、専用API範囲で限定受入。
候補は `/tmp/superfish-planar-electrostatic-solve-refined-20260913`。

`PlanarElectrostaticCase` は単純多角形の直線適合P1/P2メッシュ、全セルの正値実数epsilon_r、全領域の符号付きrho[C/m³]、全境界の固定電位[V]または外向きDn[C/m²]を要求する。
接続した導体辺は同じ電極IDへまとめる。固定電極を少なくとも一つ要求し、平面でaxis_symmetryは拒否する。負のxy座標も有効で、厚さや回転軸を仮定しない。

`solve_planar_electrostatic` はK[F/m]と体積荷重・Neumann荷重-∫Dn Ni ds [C/m]から、固定電極を消去した実Poisson系を解く。
最初の電極を基準に相対係数を求め、絶対電位を別に保持する。定数電位の場0をそのまま保つ。
元セルのPhi、Ex/Ey、Dx/Dyを元係数から求め、界面プローブは最小の元セル番号側と明記する。平均化しない。

`planar_electrostatic_quantities` は静電エネルギー∫epsilon E²/2 dxdy [J/m]、領域エネルギー、総体積電荷、指定Neumann電束を計算する。
電極電荷[C/m]は離散反力と元Dの表面積分を分け、全電荷・離散エネルギー恒等式も保存する。
容量[F/m]のQ/ΔV、2U/ΔV²、元場Q/ΔVは別の値として返し、電極2つ・電荷0・他の境界Dn=0・電位差非0のときだけ評価する。
小さな離散残差や反力の保存則は元場・表面電荷の精度を保証しない。

追加6unitと共通入力2unit、既存軸solve/native10unitの計18件が26.169秒でPASS。
Pythonの数値とboolが混在するとNumPy変換で0/1へ通る問題を軸・平面双方で先に再現した。
座標と重心座標は変換前の数値検査、元セル番号は真偽値・整数範囲の検査を共有し、型付き数値配列の正常入力を保つ。
変更前の入力と結果は `out/planar-electrostatic-solve-development-20260913/static-input-before.json` に保持した。

独立解析は二層平行板32、凹形を含むPhi=A x²/A y²の製造解32、一様rho・全周0電位の矩形24の計88例。
二層は法線Dの連続性・領域エネルギー・電極電荷・容量を照合し、回転/平行移動、定数電位シフト、符号反転、epsilon倍率、平面容量の尺度不変を検査する。
矩形は分離変数のFourier級数でPhi/E/Dを、積分済みn^-5級数でエネルギーを独立に求める。
原三角形の独立4×4 Gauss/Duffy求積で場誤差を測る。解析尺度則だけで参照場を再利用し、FEM係数への補正は行わない。
Phi/E/D/U/元場電荷を別々に細分判定し、固定rhoでPhi∝s²・E∝s・U∝s⁴を照合する。

初回の512/1024項の打切り差はn64のE/Dで1.06304e-7となり、基準1e-7を超えた。
参照項数を2048/4096へ増やし、製品コード・FEM細分・すべての許容差を維持した。
初回入力・途中結果・検証スクリプト・変更理由は `out/planar-electrostatic-solve-development-20260913/fourier-reference-refinement-decision.json` と初回出力に保持した。
級数の標本打切り差は厳密誤差上界ではない。解析条件と数値しきい値は計画書を参照する。

最終独立照合は `out/planar-electrostatic-solve-independent-refined-20260913`、標準1155件は `out/validation-planar-electrostatic-solve-candidate-20260913` へ終了0。
既存の軸native24例・元240ファイル・プローブの不変も独立検証に含める。候補は固定後に編集しない。

曲線/穴、純Neumann/gauge、浮遊電極、非線形、保存/CLI/GUI、外部境界の遠方化診断は別工程。
有限に宣言した外部境界の解であり、厳密な開放境界解を主張しない。新規依存・外部資料・旧版実行なし。S01と全計画は未完。

P2のn64で元E/D差5.20161035e-4が基準5e-4を超えた。n16/n32を保持し、最細をn80へ増やして全88例を再検証する。旧固定候補は変更していない。未達のログ/結果と変更前後の全source hashは `out/planar-electrostatic-solve-development-20260913/p2-field-refinement-decision.json` に保持する。

独立88例は1030.401秒でPASS。二層/製造解の最大相対差2.453593e-14、電位シフト/剛体変換9.992007e-16、尺度則6.930012e-13。
最細P1のPhi/E/D/U/元場電荷の最大相対差は 2.202422e-04, 1.482747e-02, 1.482747e-02, 2.198538e-04, 1.556396e-02。
最細P2のPhi/E/D/U/元場電荷の最大相対差は 3.122313e-06, 3.407226e-04, 3.407226e-04, 1.161561e-07, 2.371238e-04。
2048/4096項のPhi/E/D打切り差最大は 9.296917e-13, 3.530901e-09, 3.530901e-09。
標準2268.227秒、1152合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主18unitは26.659秒でPASS。
固定候補の697sourceと主703source（不変egg-info 6件）の完全一致を照合した。独立88例と既存軸24nativeの証拠は候補source hashへ結び付け、本体で同じ全例を再実行したとは扱わない。標準実行の固定候補との差は独立検証スクリプトのP2最細n64→80だけで、製品・テスト・例・他スクリプトは完全一致。標準1155件を再実行したとは扱わない。既存ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。

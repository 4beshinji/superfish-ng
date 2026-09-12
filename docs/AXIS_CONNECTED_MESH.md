# 軸区間とPEC穴を持つ明示メッシュ・正則場の行列基盤

[軸接続穴付き領域の計画](AXIS_CONNECTED_HOLES_PLAN.md)の最初の工程。
隔離候補 `/tmp/superfish-axis-holes-20260912` の幾何と行列を主ツリーへ統合し、以下の範囲で限定受入。
製品Case・固有値solve・全壁RF・native・CLIはこの工程の受入に含めない。

## 幾何の契約

`AxisConnectedMesh` は `superfish_ng_axis_connected_mesh` schema 1。
座標は `r,z in metres`、境界は `axis_and_pec` を明示する。
一つの反時計回り外周と0個以上の時計回りPEC穴、元節点と正三角形を保存する。
外周は非負半径にあり、一本の非ゼロの連続軸区間を持つ。穴は全て正半径で、軸・外周・他の穴へ接触しない。
全セル/頂点の接続、manifold、Euler=1−穴数、交差/重複/T字の拒否、全元境界の厳密被覆を検査する。
binary64入力を元の有理数として扱う既存の幾何述語を使い、許容差による境界吸着はしない。

軸辺の面積は0で、物理PEC壁と区別する。軸以外の元線分は正の回転面積を持つ。
面積・体積は穴を除き、PEC穴の表面積は正に加える。軸節点をz順に保持し、軸区間のSI端点を明示する。
既存の全r>0専用MeridionalMeshや、CartesianのPlanarMeshの入力は変更しない。

## 行列の契約

`axis_connected_matrices(mesh, element_order)` は正則なu=Hφ/rのP1/P2空間とK/Mを返す。
既存canonical TMの非負curlエネルギー式と、直線P1/P2の厳密な多項式積分を再利用する。
軸自由度を残し、軸上u=0を課さない。PECは自然境界条件で、q一定の循環零空間を除く正半径形式は使わない。
このAPIは固有値solve・材料モデル・対称面・RF・加速経路を暗黙に設定しない。

## 受入条件と現時点の証拠

1. 一つの連続軸、軸接触穴・負半径・未知版/境界指定の拒否、全位相/被覆契約を検証する。
2. 穴なし/一穴/二穴とP1/P2で、u=1,r,zの独立した矩形差モーメントがK/Mと一致する。
3. 軸自由度を保持し、有限離散行列に非ゼロ循環nullspaceがないことを確認する。
4. 穴なし矩形の最小固有値がBessel解析値の上側にあるというRitz不変量を確認する。
5. 標準回帰、既存f/RF、固定候補と統合主ツリーのソース同一性を確認する。

追加4unitは0.240秒で合格。初回は未実装moduleの失敗を保持した。
最初の実行は誤った作業ディレクトリで0件だったため受入に使わず、候補で再実行した。
最初の組立検査ではfixtureとしてimportしたTestCaseも重複収集された。module参照へ変更し、最終件数を4件として確認した。
粗い穴なしFEMの1%確認は行列基盤のRitz診断で、穴付きFEMの最終周波数精度を受け入れる閾値ではない。

別の解析診断では、一穴/二穴のBessel場と軸Vaccの恒等式を確認した。
周波数最近傍だけを選ぶと、残差約1e-15・周波数差約0.18%でも別の場になる反例を得た。
全真空の磁場質量内積で対象を選ぶ18試作FEMでは、P1 n=64、P2 n=16まで細分してf/E/H/Vaccが固定ゲート内となった。
対象順位は一穴17・二穴26で、順位を一般の追跡IDとはしない。
これらは未受入の固有場診断で、全壁RF・保存・製品solveの完了証拠にはしない。

証拠はout/axis-hole-reference-20260912、out/axis-hole-spectrum-prototype-20260912、
out/axis-hole-field-matched-prototype-20260912。新しい外部資料・依存・旧版参照はない。

## 最終受入記録

標準1030件（1027合格・3skip）は1853.617秒、ResourceWarningなしでPASS。
任意NGSolve参照と、sandboxのローカルHTTP待受のskipを区別する。HTTP機能は変更していない。
固定候補593sourceと統合主599source（不変egg-info 6件）を照合し、主4unitも0.234秒で合格。
seed9モード19量は周波数差0、最大相対差8.882e-16。許容差・ベンチマークは変更していない。
証拠はout/validation-axis-connected-mesh-candidate-20260912/seed_regression.json、out/axis-connected-mesh-development-20260912。
製品RF候補の受入状況は[AXIS_HPHI_RF.md](AXIS_HPHI_RF.md)へ分離する。

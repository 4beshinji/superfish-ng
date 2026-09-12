# 線形RF材料の領域・界面・Hφ行列基盤

2026-09-13 JST。[計画](MATERIAL_HPHI_FORMS_PLAN.md)の固定候補664sourceを主670sourceへ統合し、本書の行列API範囲で限定受入。
対象は直線三角形に適合した、正値・実数・等方・線形・非分散・無損失の区分一定誘電率と透磁率。
この段階は材料領域とK/MのAPIに限る。材料固有解、場/RF、native、CLI、GUIは後続。
既存canonical Modelと専用真空Caseは材料指定を引き続き拒否する。

`RFMaterialPartition`は材料・領域ID、全セルの一度だけの被覆、係数、界面両側の元セルを保持する。
領域別の断面積と全3D体積、境界の領域所有を返す。領域名が異なるだけの界面と係数の不連続を区別する。
未割当セルを真空に補完せず、複素/分散/非線形/異方性/体積損失、曲線界面、未知キーを拒否する。
独立したJSON形式は`superfish_ng_rf_material_partition`版1。

`material_hphi_matrices`は正半径でq=rHφ、軸接続でu=Hφ/rのP1/P2を組み立てる。
共通2πを省き、qではK=∫∇q·∇v/(εr r)、M=∫μr qv/r。
uではK=∫r[(2u+r∂r u)(2v+r∂r v)+r²∂z u∂z v]/εr、M=∫μr r³uv。
係数を元セルごとに適用し、材料係数や界面微分を平均化しない。
qの定数静的核は行列に保持し、uは全軸DOFを保持する。正スペクトル抽出はこのAPIに含まない。
積分次数と4次増の差は数値積分の診断であり、離散化誤差上界ではない。

実装前に真空Caseが材料指定を拒否することを記録し、追加APIで一様材料のK/εr、μr Mを検証した。
追加5unitと関連15unitがPASS。層状の製造解は境界牽引を与える弱形式の検証であり、PEC共振モードではない。
その両側の元多項式を独立Vandermonde評価し、Hφ・接線E・法線Dの界面条件を個別に確認した。

独立72ケースは正半径/軸、穴0/1/2、P1/P2、材料3系列、空間尺度0.5/2を含む。
別の18×18Gauss/Vandermonde組立との差は最大4.969e-15、空間尺度則は7.289e-16。
材料/領域の列挙順72置換、JSON72往復、12全スペクトルの一様材料則を確認し、固有値尺度差は最大1.951e-13。
これは有限行列の検証であり、材料共振器の物理精度受入ではない。

標準1112件は`out/validation-material-hphi-forms-candidate-20260913`へ終了0。
主ツリー統合と主5unit・独立72ケースもPASS。
証拠は`out/material-hphi-forms-development-20260913`、`out/material-hphi-forms-independent-20260913`。
数式は既存自作Hφ弱形式とMaxwell方程式から導出した。新規外部資料・依存・旧版実行なし。

標準は2188.436秒、1109合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。
主独立照合は4.419秒。候補664sourceと不変egg-info 6件を加えた主670sourceが一致した。
旧seedの周波数/RFしきい値とベンチマークは不変。受入証拠は標準出力内seed_regression.json。

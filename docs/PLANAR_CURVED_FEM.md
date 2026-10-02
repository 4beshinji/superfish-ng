# 平面曲線xy領域と面積P2 FEM — P06

2026-10-02、基準 `bf0d6ec`。[P06原条件](development-plan/03-planar.md#p06)を受入。
[P05契約](PLANAR_CURVED_RF.md)の専用Cartesian経路を実装した。
固有モードの元場/RF、native/Project/CLI/worker/GUI、比較/調整はP07〜P09で未受入。

## 実装と独立不変量

`planar_curved.py` の `PlanarCurvedDomain` は全xy節点、六節点cell、順序付きCCW外周三節点edgeを保持する。
負座標とxy平行移動を許す。cell/共有mid/向き/未使用・重複node/edge接続を検査し、
cell隣接連結、disk Euler、単一の閉外周と全一側cell辺の一致を確認する。
入力には派生面積やownerを受け付けず、geometryから再構築する。
配列はimmutable bytesをbaseとし、write flagを戻して入力を変更することも拒否する。

`planar_curved_geometry.py` の `PlanarQuadraticTriangle` は入力binary64からFractionで二次写像を作る。
detJ二次多項式の頂点、三辺停留点、正定値Hessianの内部停留点で厳密最小を確認する。
符号不正/零点と丸め余裕以下を拒否し、正の求積点だけで受け入れない。
浮動小数演算用の下限には `512 eps max(1,Σ|det係数/scale²|) scale²` を差し引く。
さらに `8 eps max|xy|/scale > 1e−8`、scale²のoverflow/normal最小未満では局所分解能をUNVERIFIEDとして拒否する。
これは数値入力の解像度の条件であり、連続問題の物理誤差gateではない。

全unique二次edgeはBezier controlsの囲い・保守的boxと細分で接触/交差を調べる。
共有端点の周囲は射影の単調区間を確認し、それ以外の部分も比較する。
`max_geometry_boxes` はbroad phaseの候補比較、共有端点区間、細分boxを通じた**総予算**。
不足時は使った件数/上限/edge pairを含むactionable errorで止まり、PASS/直線fallbackにしない。
独立した厳密Green境界面積とcell面積を一致させるが、それだけで全域被覆と判定しない。

`boundary_evaluate` は実二次edgeのxy/微分/ds/単位tangent/外向きnormalを返し、
cell owner/local edgeも元domainの順序で保持する。境界長は実dsのGauss積分であり弦長ではない。
参照点は閉三角形、境界パラメータは[0,1]だけ。bool/非有限値/未知key/型/版をstrict拒否する。

`planar_curved_fem.py` の `mapped_planar_element_matrices` / `planar_curved_matrices` は
`∫∇Ni·∇Nj dA` と `∫NiNj dA` を組み、元六節点を共有DOFとしてscatterする。
TEは全DOF自由、TMは外周vertex/mid全DOFを拘束する。要求正モード数の不足はFEM自由度不足として拒否。
Case版3は専用 `PlanarCurvedCase.from_dict` / `to_dict` で往復し、面積/壁次数と幾何予算を明示する。
P08まで既存の一般平面dispatcher/CLI/nativeには版3を接続しない。

共有した実行数学は既存自作の局所 `basis_p2` と参照 `triangle_quadrature` のみ。
既存軸対称geometry/assemblerへxyをr/zとして渡さず、r/r³重み・軸DOFを使用しない。
新3製品ファイルを追加し、元395製品ファイルのhashは全て不変。新依存/外部コード/旧資産の参照なし。

着手時の独立対照はNeumann定数kernelと面積mass。
既存軸対称assemblerを別物理の平面へ流用すると、合成patchで `1ᵀK1=2.7200e−5`、
`1ᵀM1=9.474667e−9` となり、必要な0と面積1.866667e−4 m²に一致しないことを先に記録した。
これは既存軸対称式のbugではなく、専用Cartesian組立が必要な独立不変量である。
製品は実FEM行列を組み、解析参照を係数や固有値へ注入しない。

## 条件別証拠

| 原条件 | 検査と結果 |
| --- | --- |
| 独立面積/実境界長 | 二尺度の曲線patch解析area/一次moment/arc長、厳密Green、回転・移動した楕円16/32/64の別quad/閉形式areaと照合。相対gate1e−12 PASS |
| 線形物理場patch | q=1,x,yの実点/勾配、x/yのK Gram=area I、mass面積/一次moment。負xy移動と二尺度、1e−12 PASS |
| 直線極限K/M | 矩形/3π/2再入角L字、二尺度/両偏波。既存Cartesian P2の全K/M・元DOF・freeと一致、行列相対norm1e−12 PASS |
| 全Jacobian | 正の全vertexを持つ内部零点、三辺の停留零点、内部負最小−δ²/4を拒否。極薄cell/座標分解能/underflow/overflowも拒否 |
| 閉外周/全域 | 非conforming mid、共有辺同向き、順序/片側owner不一致、余分/重複node/cell、非連結/穴を拒否。正の全局所JacobianとGreen一致を持つ二周星形fanの全域交差も拒否 |
| TE定数核/TM正値 | 矩形/L字の独立dense一般固有値、四ring円二尺度16/32/64の独立sparse一般固有値でTE核1個とTM正値/外周拘束を確認。代数診断を物理誤差と混同しない |
| strict/予算/規約 | 専用Case/Domain往復、未知key/物理/材料/βz/穴/非P2/非有限/bool/次数・予算不足/重複JSON拒否。真空/βz=0/単位長RFの宣言を維持 |
| 数値求積/尺度 | 回転・移動楕円K不変/M4倍、次数8/12一致。円K/M尺度差最大3.432e−16/2.493e−16、実周長12/16差0 |

新 `test_planar_curved` 9件、旧 `test_curved_fem` 3件、直接平面consumerの
`test_triangle_spectrum_and_boundary_conditions` / `test_strict_v2_and_legacy_reader_separation` 2件、
計14件は2.317秒PASS/session56921終了0。
共有mid/同向辺の追加拒否fixtureは同unitを0.024秒/session95476終了0で確認。
内部負値/全三辺停留零点を追加したJacobian unitも個別確認した。未変更の14件全体は再実行しない。

初回/session28014は新9件中8PASS/1FAIL、0.783秒/終了1。
重複cell用fixtureがnode未使用を先に起こし、期待したerror文字列と異なった。
全nodeを使用する重複cell fixtureへ修正し、失敗logを残して最終14件を検査した。
初回後の実装レビューでedge controls/boundaryパラメータの型・有限値と数値scale範囲も厳格化したため、
最終の新moduleを全選択で確認した。許容差は緩和していない。

専用 `validate_planar_curved_fem.py` は四ringの合成円、a=0.01/0.02 m、N=16/32/64、
112/224/448cell・241/481/961nodeで16.202秒PASS/session15905終了0。
独立行列スペクトル12系はTE核/TM正値の判定に限定し、P07の共振f/元E/H/RF受入ではない。
mass面積差最大3.331e−16、定数kernel相対norm最大2.612e−16、P2円の閉形式面積差最大2.221e−16。
総box数5079/14269/49615を記録し、各Caseの10万予算内。
N=64の真円に対する面積/実周長/境界距離(aで規格化)は
1.934790e−7/9.669375e−8/1.813658e−7、三系列で減少し幾何gate1e−4以内。
ここから固有場/Gや点peakの精度を推論しない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved test_curved_fem test_planar_polygon.PlanarPolygonTests.test_triangle_spectrum_and_boundary_conditions test_planar_polygon.PlanarPolygonTests.test_strict_v2_and_legacy_reader_separation
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved.PlanarCurvedGeometryTests.test_shared_midpoint_orientation_disconnected_and_hole_rejected
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved.PlanarCurvedGeometryTests.test_whole_jacobian_rejects_internal_zero_despite_positive_samples
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_planar_curved_fem.py --out out/p06-planar-curved-fem-20261002/circle-forms
git diff --check
```

rawは `out/p06-planar-curved-fem-20261002/`。専用検証器は既存出力への書込みを拒否するため、
再検証する場合は未使用の--outを指定する。検証中398製品hash不変と元395不変を確認。
全handle終端、src固定解除。共有core/seed TMには差分がなく、seed/full validate/hosted CIは未実行。
文書/全123カード依存・リンク監査を記録し、P06 DONE。次はP07の実solve/元場/壁RFと
円二尺度・両偏波のf/全E,H/G個別gate、固定Domain/楕円/再入角の専用収束検証。

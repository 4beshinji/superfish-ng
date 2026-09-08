# 選択した曲線要素の適合細分

2026-09-08、直前基準9af9cf6。N04の曲線局所細分基盤。
`curved_marked_refinement.refine_marked_curved_space` は既存のCurvedSpaceを受け取り、
選択した二次曲線三角形と必要な隣接要素を細分する。場はP2。
既存の全域細分 `refine_curved_space` とCaseの全域細分回数による再構築は変更しない。

```python
from dataclasses import replace
from superfish_ng import Case
from superfish_ng.mesh import make_mesh
from superfish_ng.curved_space import curved_space
from superfish_ng.curved_marked_refinement import refine_marked_curved_space

case = replace(Case.load('examples/curved_ellipse.json'), geometry_order=2)
parent = curved_space(case, make_mesh(case))
refined = refine_marked_curved_space(
    parent, [0], max_triangles=case.contour_mesh.max_triangles,
    minimum_corner_angle_deg=5.0,
)
# coarse_coefficientsはparentの節点順のP2係数
# restricted_coefficients = refined.prolongation @ coarse_coefficients
```

## 選択・幾何・係数移送

marked_cellsは親空間の0始まり要素番号の非空リスト。重複・範囲外・boolを拒否する。
指定要素の3辺を分割する。分割辺に接する要素の最長の端点間弦も分割する操作を閉じるまで反復し、
1/2/3辺分割の参照三角形テンプレートで共有辺を適合させる。
2辺分割の四辺形部分は既存の曲線節点間の距離で対角線を選ぶ。
未変更要素も結果に含まれるため、parent_cellsで親を特定する。

子節点は親の二次写像をdyadic参照座標で評価して作る。
共有節点の識別には節点番号を用い、物理座標の丸め一致では結合しない。
新しい節点を解析曲線へ再投影しない。境界の曲線番号・パラメータ区間は祖先情報として保持する。
幾何と場の制限は浮動小数点精度内で同じ関数を表す。解析曲線との近似誤差は減らさない。

返り値のspaceはCurvedSpace、prolongationはSciPy CSR係数移送行列。
parent_cells、parent_reference_vertices、requested_cells、split_edges、qualityを持つ。
親入力を変更せず、返却する幾何・タグ・対応の配列は書込不可にする。
全要素を選んだ場合は、既存の全域細分と節点・親子対応・係数移送が一致する。

## 品質・対象の限界

元と子の二次写像の正Jacobian・非負半径、全共有辺と閉じた境界の交差/適合性を検証する。
軸節点は正確にr=0を保ち、磁気対称面の拘束係数は移送後も0を保つ。
境界タグ、拘束集合、曲線番号の非負整数、境界パラメータの有限性と[0,1]範囲も検査する。

max_triangles（既定250000）は全体の要素数上限。最終要素数を計算してから節点を追加し、超過は拒否。
minimum_corner_angle_deg（既定5度）は子の各頂点で写像の接線から測る角度の下限。
これは要素内全域の条件数の保証ではない。曲線空間だけを受け取るAPIなので、Caseの要素数制限は
呼び出し側で明示する。品質未達時に閾値を自動変更したり、全域細分へ置き換えたりしない。

このAPIは空間の細分と係数移送であり、新たな固有値計算・誤差推定・モード追跡・停止判断は行わない。
移送された旧場は細分後の固有対ではない。物理誤差上界やRF精度合格を返さない。
Caseの局所細分履歴、native保存再構築、CLI/JobManager/GUI、曲線の適応停止への接続は次段階。
現在のCaseのcurved_refinement_levelsを局所細分の代用にして保存してはいけない。

## 検証

着手前623件中621合格・2 skip（378.443秒）。追加5検査PASS（6.647秒）。
選択要素4分割と未変更要素、参照領域の面積分割、全共有辺の適合、幾何/場/勾配の一致を確認。
GalerkinのK/M一致は相対1e-10、全要素選択時の旧全域細分は配列・移送行列が完全一致。
解析曲線へ再投影していないこと、反復局所細分で軸・磁気対称拘束を保持すること、
不正入力・予算・品質・親の拘束/祖先情報の拒否も確認した。

独立検証は `scripts/validate_curved_marked_refinement.py --out NEW`。
円筒・楕円・双曲線×尺度1/2の実曲線空間に対し、別の密行列固有値解法で局所細分前後を計算する。
GalerkinのK/M一致、移送した旧場のRF/ピーク端点の保存、新しい固有値のRitz単調性、
円筒の解析f/RQ/G/ピーク比、Maxwell相似則を別々に検査する。
移送場と新しい固有対を区別して保存する。NPZは研究用の証拠でありnative save_run形式ではない。
楕円/双曲線の一般的な物理精度、効率改善、幾何誤差の収束を受け入れる検査ではない。

最終独立検証 out/curved-local-residual-metadata-20260908 はPASS。
尺度1/2とも円筒64→72、楕円360→369、双曲線216→224要素。
Galerkin K/Mの最大相対差3.552e-16、移送した旧場のRF最大相対差2.443e-15、ピーク端点差0。
別の密行列FEM固有値解法による先頭2固有値はRitz単調性を満たし、最大残差3.486e-13。
移送した旧場の細分後残差は最大7.392e-3であり、新しい固有対として扱っていない。
円筒の最大解析差はf=8.658e-7、RQ=2.150e-4、G=7.497e-7、Epk/Eacc=2.953e-4、Bpk/Eacc=2.261e-4。
Maxwell相似則最大相対差3.656e-12。一般物理精度・誤差対DOF/時間の改善受入ではない。
最終検証中のソース変更なし、最終ソースhash一致。

新たに解いた基本モードの局所細分前後の最大相対差も別記録した。

| 形状 | f | R/Q acc | G |
|---|---:|---:|---:|
| 円筒 | 2.045e-10 | 3.710e-5 | 6.324e-10 |
| 楕円 | 3.523e-9 | 8.063e-6 | 3.692e-8 |
| 双曲線 | 5.932e-7 | 4.237e-6 | 1.095e-6 |

この差は一般形状の離散化誤差上界ではない。移送場の不変量と、新しい固有対の変化を分離して確認する。

最終標準検証 out/validation-curved-local-20260908 は628件中626合格・2 skip（380.127秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立検証の記録hashは最終ソースに一致する。
この基盤APIの追加ではGUI変更/実ブラウザー検査、新規Wine比較、Hosted CIは実行していない。

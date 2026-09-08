# 選択要素の適合細分とP1/P2場の移送

N04の局所細分基盤API。直線三角形の任意の要素を指定して細分し、共有辺・境界タグ・
元の領域を保持する。旧P1/P2空間から新空間への疎な係数移送行列と、親要素の対応を返す。
後続で[残差指標と割合による選択](RESIDUAL_INDICATOR.md)を追加した。追跡付きf/RQ/G停止は[適応計算](ADAPTIVE_REFINEMENT.md)へ接続した。

```python
from superfish_ng import Case, solve
from superfish_ng.marked_refinement import refine_marked_cells
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.io import save_run

case = Case.load("examples/pillbox.json")
previous = solve(case)
refined = refine_marked_cells(case, previous.mesh, [0, 1],
                             max_triangles=250000, minimum_angle_deg=5.)
# 旧uと同じ関数を新空間で表す係数。電場の比較には旧周波数も保持する。
same_u = refined.prolongation @ previous.u
current = solve(case, mesh_data=mesh_to_dict(refined.mesh))
save_run(case, current, "out/refined-new")
```

## 細分と品質の契約

`marked_cells` は、入力メッシュの0始まりの要素番号を並べた、空でない重複なしの整数リスト。
指定要素の3辺を二分し、4子要素を作る。共有辺の中点は一つだけ作り、辺を分割する相手側も
適合するように細分する。短辺を分割するときは、その要素の最長辺も分割対象へ追加し、
必要な隣接要素へ伝播する。1辺/2辺/3辺の分割に2/3/4子要素を用い、2辺の場合は短い対角線を選ぶ。
選択していない要素も適合性のため細分されることがある。全要素を選ぶと4分割の一様細分になる。

既存の共有辺分割・タグ継承処理を利用し、出力を通常の厳密なメッシュ読込検査で再検証する。
辺上に新点を置くため、表現した多角形境界は変わらない。弦近似の解析曲線誤差は減らない。
PEC/axis/平坦対称面のタグを継承する。二次曲線幾何 `geometry_order=2` は明示的に拒否する。
場の次数は `case.element_order` のP1/P2に従う。

`max_triangles` は正の整数、`minimum_angle_deg` は0より大きく60より小さい有限値。
Caseに輪郭メッシュの上限・最小角がある場合、より厳しい条件を使う。
予測要素数で上限を検査し、生成後の測定最小角が条件未満なら拒否する。
品質条件を満たせない場合は出力を受理せず、入力メッシュを変更しない。
最小角は浮動小数点による幾何測定であり、RF誤差の保証ではない。

## 返却する対応

- `mesh`: 通常のMesh。`mesh_to_dict`を介して通常solve/保存へ渡せる。
- `prolongation`: 新自由度数×旧自由度数のCSR行列。対象は `u=Hphi/r` の係数。
- `parent_cells`: 各子要素の旧要素番号。
- `parent_barycentric_vertices`: 子要素の3頂点を旧親要素の重心座標で表した配列。
- `requested_cells`, `split_edges`: 元の選択要素と実際に分割した旧辺。
- `quality`: 実測最小角・要素数・形状品質と、適用した最小角/要素上限。

移送係数は親の二進分数の重心座標から計算し、共有自由度の行が一致することを確認する。
旧uと勾配を同じ関数として制限するため、剛性・質量について `P.T @ A_new @ P = A_old`
というGalerkinの関係を満たす（実計算は丸め誤差を含む）。
磁気対称面で0だった自由度は、移送後も0に保つ。軸の半径0と自由度も保持する。
移送だけでは新しい固有モードを得ないため、上例では通常FEMを改めて解いている。

## 検証と残件

独立検査は、局所性、境界/面積/体積、任意係数場と勾配、剛性/質量の保存、対称面拘束、
入力不変・品質/予算/選択拒否を含む。
`scripts/validate_marked_refinement.py` は円筒と合成折返し輪郭のP1/P2で、局所/一様の2段階細分を
実FEM再計算する。同じ演算子の入れ子空間に対する変分単調性、円筒の独立Bessel固有周波数、
長さ2倍のf/RQ/G相似則を確認し、DOF・時間・各RF量も記録する。
この局所選択は座標で明示した領域であり、誤差指標に基づく適応選択ではない。
少ないDOFが一様細分より小さい誤差を意味するとは扱わない。

指標/対象選択は[後続API](RESIDUAL_INDICATOR.md)を参照。追跡付きf/RQ/G停止とCLIは[適応計算](ADAPTIVE_REFINEMENT.md)へ接続。物理RF受入、曲線幾何の局所細分、GUI操作は残件。
N04全体の受入とはしない。既存の物理辺長による細分や曲線の固定幾何一様細分は変更していない。

受入証拠は `out/n04-marked-refinement-initial-20260908/validation.json`。
円筒/折返しのP1/P2について初回からPASSし、Galerkin相対差最大1.746e-15、
体積差6.662e-16、f/RQ/G相似則差1.830e-13以内。標準571件中569合格・2 skipと
既存周波数/RF回帰も最終ソースで確認した。一般の適応誤差推定を受入した記録ではない。

# 曲線Hφの完全比較領域（H11、受入済み）

H13-aで、旧版1の厳密契約を維持しつつ、[明示版2のbinary64丸め検証](CURVED_HPHI_REFINEMENT.md)を追加した。以下の係数厳密一致は版1の契約。版2も参照領域同士の完全一致と有理数chartの全被覆を要求し、native係数の丸めだけを測定・制限して報告する。

`curved_hphi_comparison`は、全境界成分を持つ明示二次参照領域と、それぞれのnative要素をその参照領域へ結ぶ有理数の三角形分割を検証する。軸接続/正半径と全PEC穴を保持する。場比較やモードID、FEM精度の判定は次のH12以降の責務である。

## 入力と幾何契約

`CurvedHphiComparisonDomain(previous, current, mapping)`は完全な`CurvedMeridionalGeometry`を二つ要求する。参照領域の要素・頂点・全境界成分/役割・軸節点は明示した同じ番号で対応する。最近傍検索や周波数から対応を推測しない。

- `same_vacuum`では、全P2座標を厳密一致させる。頂点一致だけでは足りず、辺中点と内部二次係数も一致しなければ拒否する。
- `declared_quadratic`では、対応する参照三角形上でそれぞれの二次写像を使う。両側で全領域の正Jacobian、境界交差、半径、外周/穴/軸の検証を再実行する。直線の写像へ置き換えない。

`to_dict/from_dict`は`superfish_ng_curved_hphi_comparison_domain, schema_version=1`を使用し、未知キー・不正version・推測mappingを拒否する。`inverse()`は明示対応の前後を交換する。

`build_curved_hphi_comparison(previous_native, current_native, domain, ...)`に、各native要素順の`previous_cells/current_cells`を渡す。各行は`base_cell`（0始まり）と`reference_vertices`（3頂点×2座標）を持ち、座標は`[整数分子, 正整数分母]`で表す。省略時は同じ番号の全参照要素をそのまま使う。異なる要素数なら宣言は必須。

各native要素の3頂点・3中点を、宣言した参照写像の有理数評価と厳密一致させる。binary64入力座標はそのまま厳密な有理数として扱う。丸め誤差を許容して別の二次領域を同一視する機能ではない。宣言と完全一致しない再投影/再生成形状は拒否し、元のnative座標を書き換えない。

各参照三角形について、全native子三角形が内側にあり、正の向きで、正面積の重複を持たず、面積総和が厳密に1/2であることを検証する。さらに全native境界辺の参照上の位置と境界成分番号/軸役割を照合する。独立した非nested分割を許すが、参照要素をまたぐnative要素への対応は推測しない。

## 共通分割とサンプリング

有理数の三角形交差を用い、両側の全native要素と全参照要素の完全被覆を再検証する。共通三角形順を参照座標で固定し、native番号変更や前後交換に依存させない。

`evaluate(side, barycentric)`は各共通三角形について、元native要素番号、native重心座標、実(r,z)、二次Jacobian×共通参照行列式を返す。これは元場を評価するための位置/測度であり、新しいFEM係数や解析解ではない。軸上の正則条件とPECを取り違えず、積分点の半径重みは利用側が明示する。

比較に使う全pair数（両側の自己重複検査を含む）と共通三角形数を制限する。予算を超えれば`CurvedHphiComparisonBudgetExceeded`（`status=UNVERIFIED`）で停止し、部分的な比較を確認済みreportとして返さない。成功reportの`GEOMETRY_VERIFIED`は幾何だけの判定で、場対応/求積精度/離散化誤差のPASSではない。

## 独立検査と証拠

既存の合成写像`(r,z) -> (r,z+alpha*r²)`を使用する。行列式は1、半径は不変なので、元矩形から全域/各穴の面積と回転体積を独立に求められる。二尺度・異なるshear、軸接続/正半径、2つの穴、別native細分を検査する。各境界のGauss積分`∮r dz`と`π∮r² dz`も、各元矩形の符号付き解析値に照合する。

単一三角形内の異なる内部頂点による二つの非nested分割を追加し、交差の完全被覆、独立三角形面積/回転体積、前後交換、native要素順/局所頂点順変更での同一サンプリングを確認する。同じ頂点で境界中点のみ変わった反例は、same-vacuum宣言とnative制限照合の両方で拒否する。

`out/h11-comparison-20260921/before.log`では、独立穴モーメントを確認した後に未実装APIのimportで失敗（0.160秒、終了1）。既存物理の誤答を直したという意味ではない。新4件は7.081秒、追加2件は5.159秒でPASS。`after.log/additional.log`は分割証拠であり、全suiteではない。既存幾何/Hφ形式/曲線共通分割の回帰は進行中。

新外部資料・依存・legacy参照はない。既存の有理数clip、完全二次幾何検証、独立合成shearを再利用する。seed TM、既存solver、RF規約、許容差を変更しない。Hosted CI/GUI/FEM調整の受入を主張しない。

既存`test_curved_meridional_geometry test_hphi_geometry_mapping test_curved_hphi_fem test_curved_comparison_overlay`の20件は11.443秒PASS、終了0（`regression.log`）。新6件の両handleも終了0。実行方法は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v <modules/cases>`。新モジュールは`test_curved_hphi_comparison`。新しい比較領域はまだsolver/保存runnerへ接続していないため、全suite/seed検証は実施していない。

| H11の受入条件 | 確認結果 |
|---|---|
| 全境界成分を持つ同領域/宣言写像 | 軸接続/正半径・2穴、same_vacuum/declared_quadratic、正逆でPASS |
| 二次写像の全被覆・正Jacobian | 全native/参照要素の厳密被覆、全二次幾何の再検証、非nested交差と番号変更でPASS |
| 穴面積/体積の独立積分 | 各成分のGauss境界積分と元矩形解析値、共通分割の体積積分でPASS |
| 同頂点・異中点の反例拒否 | 同領域宣言とnative制限照合の両方で拒否 |
| 比較予算超過は未確認 | pair/triangle予算の双方でUNVERIFIED例外、部分成功reportなし |

H11を受入。次はH12で、この共通分割上に元E/H場の比較と細分差診断を接続する。全goalは未完了。

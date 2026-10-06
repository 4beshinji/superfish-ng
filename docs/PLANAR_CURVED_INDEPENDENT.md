# 平面曲線の独立内部meshと増求積次数 — P07

2026-10-07、基準 `c802aa2`。P07追加検証であり、全カードの受入ではない。
[P05 gate](PLANAR_CURVED_RF.md#検査入力と固定した個別gate)と
[前回の最終二水準](PLANAR_CURVED_CONVERGENCE.md)を維持する。
製品のFEM・物理許容値・schema・依存・canonical TMは変更しない。

## 元領域と比較

`scripts/planar_curved_mesh_reference.py` は検証専用。完全初期Domainから細分を再生成し、
元cellの参照chartを合成する。Aはuniform四分割、Bは最初のopposite-edge二分割と
共有辺closure、その後uniform四分割。元P2境界は再投影しない。
最後の実native写像と初期写像の制限との差を有理数で測定し、二次Bernstein制御値から
外向き座標上限を保存する。局所幅に対する最終上限が512 epsを超えたらUNVERIFIEDで停止。
逐次丸め上限だけで最終領域一致を主張しない。

元parentごとに有理数clipし、各側の全cellのexact被覆を検査する。
全overlay三角形の上限と各異なるchart layoutのBVH候補検査上限を明示する。
同じdyadic layoutの幾何partitionだけを再利用し、場値や固有解は再利用しない。
measureは初期元P2領域の実面積、勾配は各側の実native J逆で評価する。
座標丸め上限を連続問題の物理誤差上界として扱わない。

円の完全解析群でscalar crossから単一直交回転を決め、同じ回転を元E/Hへ適用する。
二passの直接vector差を積分し、独立位相/振幅合わせを行わない。
元順位の周波数・全正RF・理由付き加速量nullを別比較する。guard群も保存し、
TE先頭5/TM先頭3を判定する。永続ID/連続枝/連続誤差上界を保証しない。
f≤1e−4、E/H≤1%、全RF≤0.5%をA対BとB最終二水準で別々に要求する。
粗い未達を残し、最大追加水準を明示した実細分だけを行う。

## 独立不変量と求積

新6unit/既存5unitは28.116秒PASS。二尺度patchの既知面積/一次moment、両偏波の
physical linear scalarに由来する12成分、既知二重群回転、逆比較、geometry/予算/不正群拒否を確認。
周波数3%差がTEのE/TMのHへ残り、振幅差も消えない。製造場を固有場の解析解としない。
独立面積/壁積分の追加1unitは1.475秒PASS。分割12種類の成功証拠を保持する。

求積系列は初期N16円の半径0.01/0.02 m、TE7/TM6正モードを実solveする。
area8/12/16、wall12/16/20の三組12元解を保存し、最後二組のf/全RF差≤1e−8を判定。
K/M norm差と全群E/H差も保存する。粗い初期meshのf精度を受入に使わない。
最後の4解は同じCase/次数で物理再構築し、元係数不変を確認する。
別order20の面積求積で元E/Hを積分し、実壁では全Hから法線成分を除く。
製品RFのTE scalar/TM tangent内積とは別式で壁H二乗積分を照合する。
areaとwallは元RFとの相対差≤1e−8を別に要求する。

求積session76545は42.155秒PASS/終了0、401製品hash不変。
初回session47601は検証器の`jacobian_m`誤参照で終了1、新FEM1保存済み。
実key `jacobian`への修正と上記1unitを追加し、失敗出力/logを保持する。
証拠は `out/p07-planar-curved-independent-20261007/quadrature-final/`。

## 実行と残る受入

独立meshは実行中。元Aの全artifact hash/401製品hashを前監査と照合し、
TE L3/TM L4二尺度の保存係数を物理再構築する。元A出力は変更しない。
新BのCase/全係数・周波数/chart/全解析場・RF/初期未達を新出力に保存する。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_mesh_reference test_planar_curved_convergence_reference
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_mesh_reference.PlanarCurvedMeshReferenceTests.test_independent_area_energy_and_normal_subtracted_wall
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_planar_curved_independent.py --quadrature-only --out out/p07-planar-curved-independent-20261007/quadrature-final
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_planar_curved_independent.py --mesh-only --from-evidence out/p07-planar-curved-convergence-20261002/circle-last-two-final --source-audit out/p07-planar-curved-convergence-20261002/progress-audit.json --out out/p07-planar-curved-independent-20261007/mesh
```

パスは今回の証拠であり、再実行では未使用出力を指定する。
N16/32/64幾何と十分細かい各FEM、楕円・再入角の二尺度対照は残る。
native/CLI/Project/worker/GUIはP08、一般曲線比較/調整はP09の別受入。
seed/full validate/hosted CIは未実行。既存自作P2/Gauss/細分と有理数clip/BVHを再利用し、
新外部資料・依存・legacy資産参照はない。

## 後続の入力と評価候補

`planar_curved_shape_reference.py` は4ringの二次円を回転・平行移動・異率拡大し、楕円N16/32/64の二尺度幾何を生成する。真周長は別のadaptive 1D積分、距離はaffine作用素normからの保守的上限。L字は角近傍のgraded直線P2 meshで、面積3a²/周長8aを確認する。局所r^(2/3)調和の壁二乗/面積勾配積分を独立 improper 積分で確認し、有限peak/全域固有値を主張しない。新4unitは4.734秒PASS/終了0、これらの入力のFEM受入は未実施。

`planar_curved_vector_reference.py` は実native座標/係数/周波数をそのまま使う検証専用のvector化候補。新3unitは0.018秒PASS、両偏波の元API全12成分、既知physical linear scalarの符号、strict参照点/番号を確認。150回×400点の単一translated patch実測は元API1.126864秒/候補0.106693秒（10.56倍）、vector norm差1.889e−16。実行中のmesh検証器には接続せず、現在のhash固定を維持する。将来の採用には比較器を通した実元場/全RF一致も別確認する。

求積最後二組の最大f差1.077e−14、全RF差2.309e−14、K norm差1.022e−15、M norm差1.261e−15。独立面積/壁積分と元RF差は最大2.198e−14。環境はuvの既存`.venv`、Python3.12.3/NumPy2.5.2/SciPy1.18.1、BLAS1thread。新依存導入なし。

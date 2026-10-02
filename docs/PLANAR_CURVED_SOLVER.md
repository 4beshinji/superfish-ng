# 平面曲線の実解・元場・側壁RF — P07進行記録

2026-10-02、基準 `fa4f82e`。[原P07](development-plan/03-planar.md#p07)はIN_PROGRESS。
実解核と円二尺度/両偏波の解析対照を実装・検査した。
[P05契約](PLANAR_CURVED_RF.md)の幾何近似系列、独立内部mesh、最終FEM差、増次数、楕円/再入角の
全gateが残るため、これをP07全体・P08保存/GUI・全goalの完了とはしない。

## 実装と独立物理

`planar_curved_solver.py` の `solve_planar_curved` は専用面積K/Mを実際に解く。
共有するのは既存Cartesianの `_eigenpairs` / `_restore` による一般固有値・代数検査だけ。
TE定数核を確認して除外し、TM外周を拘束、全正モードをM直交・U′規格化する。
代数残差1e−7/直交1e−8/TE定数混入1e−8/lowest spectrum再生1e−9を維持。
周波数順位を永続IDにせず、縮退群は完全群として扱う。解析式は検証器のみに置く。

`PlanarCurvedSolution` は元Domain/全係数/周波数/代数診断を保持し、主要場配列はimmutable。
`scalar_at_reference` / `fields_at_reference` は実二次写像とJ逆からscalar/勾配/全12phasor成分を評価する。
`all_fields_at_reference` は同じ実幾何を全正モードへ一度に使う配列API。
`fields_in_cells` は既存consumer用barycentric adapterで、閉参照三角形を保つ。
全場はpeak exp(+iωt)、TM real Ez / quadrature Hx,Hy、TE real Hz / quadrature Ex,Ey。
元geometryを描画用三角形/解析曲線へ置換しない。

`planar_curved_location.py` の `PlanarCurvedLocator` は二次edgeの有理数多項式で
binary64実点の接触と水平ray windingを判定し、検証済みcell上で逆写像を求める。
Bernstein controlsの外向きbox、y停留点での単調区間、二次多項式の消去によるexact signを使う。
Newton残差許容で外点を中へ広げない。共通edgeは最小cell番号を所有者にする。
逆写像未確認ではerrorとし、明示cell/ref probeを案内する。

`planar_curved_quantities` はU′e/U′mと、所有cellの片側場・実二次edgeのtangent/dsを積分する。
Rs、P′、Q0、G、全J/m/W/m/phasor/面積/実周長/求積次数を返す。
二つのR/Q、Vacc/Eaccは理由付きnull。伝搬電力や有限長端板を追加しない。
専用 `restore_planar_curved_solution` はCaseからgeometry/K/M/拘束を再構築して元全場を物理検証する。
これはP07の配列APIであり、五ファイルnative reader/Project/CLI/worker/GUIはP08で未接続。

着手時の独立wall対照：N=16・a=.01 mの二次円で、|Ht|²=1の実側壁積分は
0.06283031523337912 m、弦の和は0.06242890304516105 mで0.638883%違う。
弦長を曲線RFへ流用しないことを先に確認。旧平面dispatcherも新Caseをstrict拒否していた。
初回の実円TM01はf差1.58506e−4、G差6.5358%で未達。補正式/許容差変更で合わせていない。

## 同じ元二次写像を保つ細分

`planar_curved_refinement.py` は親の六節点からFractionで座標を評価し、
uniform参照4分割と、頂点→対辺mid bisectionの共有edge closureを生成する。
後者は各cellでmarked辺の数に応じて2/3/4分割し、T接続を作らない。
共通edgeの節点は有理barycentric keyで一意に共有し、円/楕円へ再投影しない。
出力は完全元Domain、親cell/参照頂点、scalar prolongation、丸め差の座標別上限を保持する。

binary64へ丸めた子節点との差をFractionで求め、差のBernstein controls最大値を外向き表示する。
全域上限/局所幅が512 epsを超える場合はUNVERIFIEDで止まる。
「同一Domain」はこの宣言した制限と丸め証拠の意味であり、係数の数学的完全一致と混同しない。
M転送相対norm1e−12、K転送1e−10、定数/線形場、親参照全被覆と独立内部接続をunitで確認した。
独立bisection meshの実固有場/最終RF比較は後続の受入条件。

## 実行した検査と失敗記録

新solver7件/細分3件はsession19390、10件2.343秒PASS/終了0。
旧直線平面の符号付きMaxwell/全成分、単位長energy/wall/尺度の2件は初回成功を保持し、
計12種類を分割確認。独立場energy order12とadaptive quad壁積分、
相似・回転・移動・U′/σ則、全配列再生/不正band・周波数/規格化/TE核/TM壁改変拒否を含む。
厳密点所属は曲線patchの弦内/実Domain外、実中点のnextafter外点も拒否した。

初回/session18384は9件中8PASS/1FAIL、1.036秒/終了1。
直線TEのほぼ零のEx成分−510.7074 V/mの差2.1442e−7 V/mを、単独成分の相対値で判定した。
同じ係数による旧新の場評価を先に照合し、独立solve同士は同じscalar符号による全E/H vector normへ分離。
場norm gate1e−10と同係数場の元許容値を保持し、ほぼ零の一成分を全場誤差としない。
限定再検査/session4352は1件1.007秒PASS/終了0。
全モード一括場API追加による製品変更後は新10件を再確認し、旧2件は不変ソースの成功を再利用した。
初回logと限定再検査を保持し、unit成功を曲線の物理収束へ水増ししない。

専用 `validate_planar_curved_rf.py` はBessel正根・独立解析規格化・全E/H・Gと、
同じ元P2 Domainの三水準以上を比較する。scalar crossの単一直交変換をE/Hの両方へ適用し、
場ごとに別の位相/振幅を合わせない。guard完全群を保存し、f/E/H/G gateを別々に記録。
実Ωhのfield積分は組立order8とは別のorder10で確認する。

最初の円a=.01/.02 m、両偏波L0/1/2、12新FEMはsession81249、68.327秒/終了1。
TEの対象TE11二重/TE21二重/TE01単一はL2で全gate PASS。
TM01単一/TM11二重はL2でf/E/HがPASS、G最大1.13743%で0.5%未達。
全12元解・失敗log・401製品hash不変を保持し、TM二尺度だけ新出力でL3へ延長した。
`--extend-from` は製品hash完全一致と元Case/全係数のlowest正帯再生を確認して、新所有コピーへ延長する。
通ったTEや既存12解は再solveしない。

延長/session65520は111.818秒/終了0、追加2FEM、保持14元解。
全4最終caseの対象群がP05の解析gateを満たした。最大相対誤差は次のとおり。

| 偏波/最終水準 | f | E L2 | H L2 | G |
| --- | ---: | ---: | ---: | ---: |
| TE L2、1792cell/3649DOF、両半径 | 2.826541e−5 | 2.687484e−3 | 1.086306e−4 | 8.136235e−6 |
| TM L3、7168cell/14465DOF、両半径 | 2.482936e−5 | 5.676298e−5 | 5.839893e−4 | 2.957906e−3 |
| 固定gate | ≤1e−4 | ≤1e−2 | ≤1e−2 | ≤5e−3 |

独立field energy差最大1.081e−13、代数残差最大1.013e−12。
これらの代数値を離散化誤差と呼ばず、上表の別物理対照を使用する。
制限座標の相対丸め上限最大4.520e−15、総box数はTE L2=231445/TM L3=1720265。
Caseで予算1e7を明示した。raw Case/係数/親chart/判断を元の出力へ残す。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_solver test_planar_rf.PlanarRFTests.test_signed_maxwell_fields_and_all_complex_components test_planar_rf.PlanarRFTests.test_per_length_energy_wall_integral_and_scaling
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_solver test_planar_curved_refinement
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_solver.PlanarCurvedSolverTests.test_straight_limit_actual_solution_fields_RF_and_native_restore
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_planar_curved_rf.py --out out/p07-planar-curved-rf-20261002/circle-fixed
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_planar_curved_rf.py --extend-from out/p07-planar-curved-rf-20261002/circle-fixed --out out/p07-planar-curved-rf-20261002/circle-extended
git diff --check
```

上の出力は現存証拠なので、将来の新規実行は未使用--outへ書く。
raw `fem-fields.npz` とCase/checksは検証器内部の出力であり、P08のnative受入済み形式ではない。
延長後に検証器のindent/未使用importだけを整え、ASTを確認。FEM/製品は再実行/変更しない。
全handle終端、401製品固定解除、元398製品不変。seed TM/全validate/hosted CIは未実行。
追加外部資料/依存/legacy参照なし。円の正根/場/Gの参照はP05のR39/R40と独立導出を継続利用する。

## P07を閉じる前に残る条件

| 条件 | 現在の証拠 |
| --- | --- |
| 実solver/元12場/片側実壁RF、strict/再構築 | unitと円解析の上記範囲で確認 |
| 円二尺度/両偏波、固定Domain三水準以上の解析f/E/H/G | 上記TE L2/TM L3の完全対象群 PASS。細分不足のFAILも保持 |
| 真形状へのN=16/32/64幾何近似と十分細かい各FEM | P06は幾何だけ。曲線RFの新系列は未確認 |
| 固定Domain最終二水準のE/H/全RF、独立A/B固有場 | 制限/転送unitのみ。実固有場の別比較gateは未確認 |
| 最後二求積次数のf/全RF≤1e−8 | unit内の独立積分は確認。三次数の全正帯RFは未確認 |
| 滑らかな楕円と再入角、二尺度・全f/E/H/RF差 | 基礎unit/幾何・尺度は確認。専用収束gateは未確認 |
| P08/P09 | native/Project/CLI-worker/Study/GUIと比較/調整は未接続 |

次は保持した円解の最終FEM差/増次数/独立mesh対照と、楕円・角の専用系列を検証する。
全残条件の証拠を監査してからP07をDONEにする。

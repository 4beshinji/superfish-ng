# P07：真形状の幾何系列と固定DomainのFEM差

2026-10-07、P07 IN_PROGRESS。[P05契約](PLANAR_CURVED_RF.md)の一部を検査する。
この記録は全P07・P08操作・全123カードの完走受入ではない。

## 判定と実装

`validate_planar_curved_geometry_series.py` は円/合成楕円のN16/32/64を個別に生成し、
各元P2 Domainのuniform細分をL0から別々の実FEMで解く。
真面積・周長・保守的境界距離上限は1e−4、各Domainの最終二水準はf 1e−4、
E/H各1%、全RF各0.5%。円はさらにBessel解析f/E/H/Gと完全guard群を検査する。
楕円に未提供の解析固有値を仮定しない。独立面積/全vector壁積分と全元chartも検査する。

円解析参照 `planar_curved_circle_reference.py` は既存P05のBessel零点/原点極限/
peak-phasor規格化を再利用し、各セル二回積分で単一scalar群回転と元E/H差を評価する。
全Domainの標本配列を一度に保持する旧参照に対し、セル単位の配列だけを保持する。
製品FEM、場配列、周波数、RF式、許容値は変更しない。
uniform比較は既存 `compare_pair` に明示的vector化adapterを渡す。
元Domain・保存係数・周波数・規格化を保持し、一般A/B比較とは別に確認した。

## 分割unit検査

Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1、uvの既存環境で実行。
共通prefixは `OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python`。

| unittest module | 件数 / 時間 / 終了 | 独立対照 |
| --- | --- | --- |
| `test_planar_curved_circle_reference` | 4 / 6.853秒 / 0 | 原点・二尺度・両偏波の既存解析全成分、規格化、旧全標本比較、完全群回転、guard拒否 |
| `test_planar_curved_geometry_series_reference` | 3 / 2.511秒 / 0 | 円の三N/二尺度真幾何、完全guard、実patchの元場/全RF比較 |
| `test_planar_curved_shape_extension` | 4 / 1.721秒 / 0 | 実保存解の物理再構築、全chart/RF/bytes不変、再hashした偽固有値とchart改変拒否 |
| `test_planar_curved_shape_recovery` | 4 / 0.515秒 / 0 | 終端観測必須、timeout/成功/別出力拒否、連続かつ順序付きprefix、全元artifact/製品/検証器hash |

新15件は上記四回の分割結果。後続mixed経路の新3件は1.115秒/終了0で別確認した。先行検査を再実行して数を増やさない。
raw/logは `out/p07-planar-curved-geometry-20261007/`。
製品401ファイル・seed/shared core/依存不変の検証専用追加なので、全validate/seed/GUIは実行していない。

## 終端を確認した八例の幾何/FEM受入

各ケースL0/L1/L2の新3実FEM、L1→L2で全ゲートPASS、製品401hash不変。
円は解析絶対gate、楕円は完全band gateもPASS。
下表の値は対象の最初3完全群についての相対差最大で、E/H/RFを別判定する。

| 元形状・偏波・尺度・N | 秒 / 終了 | f差 | E差 | H差 | 全RF差 |
| --- | --- | --- | --- | --- | --- |
| circle TE s1 N32 | 155.690 / 0 | 2.1121e−5 | 0.006515 | 0.0004438 | 8.742e−5 |
| circle TE s1 N64 | 431.778 / 0 | 1.6084e−5 | 0.005687 | 0.0004142 | 7.284e−5 |
| circle TE s2 N32 | 198.150 / 0 | 2.1121e−5 | 0.006515 | 0.0004438 | 8.742e−5 |
| circle TE s2 N64 | 273.594 / 0 | 1.6084e−5 | 0.005687 | 0.0004142 | 7.284e−5 |
| ellipse TE s1 N32 | 125.726 / 0 | 1.8103e−5 | 0.006024 | 0.0002712 | 6.218e−5 |
| ellipse TE s1 N64 | 353.458 / 0 | 1.2282e−5 | 0.004962 | 0.0002309 | 4.160e−5 |
| ellipse TE s2 N32 | 157.514 / 0 | 1.8103e−5 | 0.006024 | 0.0002712 | 6.218e−5 |
| ellipse TE s2 N64 | 226.226 / 0 | 1.2282e−5 | 0.004962 | 0.0002309 | 4.160e−5 |

真幾何の相対面積/周長/距離上限はN32で3.0931e−6 / 1.5436e−6 / 2.8984e−6、
N64で1.9348e−7 / 9.6694e−8 / 1.8137e−7。楕円は独立周長求積と保守的アフィン距離上限を用いる。
当初六例126ファイルのsnapshotを保持し、追加二例を含む八例168ファイルは
`accepted-eight-artifact-hashes.json`。八例計24新FEM。
N16の先行受入は再solveせず物理再構築/全hash付きで系列へ統合する予定。
TMはこの八例の受入に含めない。

`checkpoint-audit-final.json` は八例168artifact、製品401、各受入検証器のhash、
文書のローカルリンクを読取監査した。15生存handleの製品/使用検証器hashも現行と一致する。
これは新しいFEM solveやunit再実行ではなく、上記の成功証拠と実行中ソース固定の監査である。

## TEの三N・二尺度系列の監査（2026-10-07）

終端handle25430は13.845秒PASS/終了0。
`out/p07-planar-curved-geometry-20261007/te-geometry-series-audit-rf-schema/` に
円/楕円×二尺度の四系列、各N16/32/64を集約した。
N16の元円物理再構築監査/数値raw全hashと、元楕円TE二尺度の完了report/全8検証器/製品hashを確認し、
新N32/64は既存八例168artifact snapshot/10検証器/製品hashに照合した。
11証拠Directory/239ファイルの完全snapshotを保持し、原thresholdで数値判定を再監査した。
全対象/guardの完全群、f/E/H/全RF別差、独立energy/壁、peak U′=1 J/mとaccelerating nullを確認した。
元初期Domainの真幾何を別計算し、細かい元RFの面積と1e−12以内で一致することも確認した。

四系列ともN16の固定FEMはL2→L3、N32/N64はL1→L2で受入済み。
真形状の面積/周長/距離上限は各系列でN16>N32>N64、最終≤1e−4。
N16の誤差は4.9318e−5 / 2.4477e−5 / 4.6152e−5、N64の値は上表と同じ。
この有限FEM証拠集約で新FEM0/unit再実行0、新しい元場の物理再構築0。
既成功した元場比較をhash/source付きで利用したもので、連続誤差上界やTM/全P07受入ではない。

初回監査handle50608は楕円scaleのkeyword-only引数を位置指定して終了1。
次のhandle10976は一般比較のfine側保存名 `second_RF` とuniform比較の `fine_RF` の違いで終了1。
両失敗driver/log/終端auditを保持し、入力/保存schemaの参照だけを修正した。
原FEM/物理許容値/製品401は不変。修正後は一つの明確なfine側schemaだけを認め、数値RFを独立に監査する。

## 非円形の未達を保持した追加細分と復旧

`extend_planar_curved_shapes.py` は終端した失敗reportだけを入力とし、元rawを変更せず、
完全製品/元8検証器hash・元Domain/chart・実固有対/RFを再確認する。
既存FEMを繰り返さず、必要な追加A/B L5だけを解く。
実装/物理許容値/元二次境界を固定する。

先行 `out/p07-planar-curved-independent-20261007/` の終端失敗：

| ケース | 終了 / 秒 | 保存実FEM | 未達 |
| --- | --- | --- | --- |
| ellipse TM s1 | 1 / 2173.778 | 6、A L4受入/B L4未達 | B L3→L4全RF最大0.684177%、規定0.5% |
| corner TE s1 | 1 / 1047.787 | 6、A L3受入/B L4未達 | 第三完全群f差1.163565e−4、E差1.401941% |
| corner TE s2 | 1 / 1114.458 | 6、A L3受入/B L4未達 | 同じf/E gate、独立滑らか二重群周波数はPASS |
| corner TM s1 | 1 / 845.450 | 4、A L4未達 | 全RF最大0.703815%、f/E/HはPASS |
| corner TM s2 | 1 / 863.615 | 4、A L4未達 | 全RF最大0.703815%、f/E/HはPASS |

角TM s1の追加handle15560も終了1。L5 Domain生成で `max_geometry_boxes=100000000`
を使い切り、FEM実行前に明示的UNVERIFIEDとなった。物理未達やFEM成功とは数えない。
失敗log/failed-evidenceは `corner-tm-s1-L5/` と同名logに保持する。
角TE s1追加handle53536は継続観測中。

楕円TM s2はhandle92077に対する `write_stdin` が終了143を返した。
原因は未確定。終端audit `ellipse-tm-s2-termination.json` を別の新出力に保存し、
元A L1〜L4/B L3の五保存解・元製品/8検証器hashを保持する。
`recover_planar_curved_shapes.py` は全prefixを物理的に再構築してA/B判断をやり直し、
存在しない次のBだけを実solveする。timeoutを理由に処理を再起動しない。
部分出力が存在する未記録trialも拒否する。復旧handle70467の出力は `ellipse-tm-s2-recovery/`。

## 再入角TMの混合細分（検証中）

一様L5の幾何予算切れを実測したため、`extend_planar_curved_mixed_refinement.py` を別追加。
元A L1〜L4の完全失敗prefixと、完了新FEM0の予算切れ証拠だけを受け付ける。
元A L4を二分して `A-uniform4-bisection` を生成し、一般共通parent比較器でA L4との差を評価する。
uniform専用比較器を混合細分へ流用しない。元二次境界/予算上限1e8/全物理gateを保持する。
Aが通った場合だけ、別初期二分割Bのuniform3/4を実solveし、Bの二水準差とA/B差を別判定する。
両native Domainが同じ場合は独立mesh受入を拒否する。

新 `test_planar_curved_mixed_refinement` 3件は1.115秒PASS/終了0。
異なる順序の細分meshで既知線形scalarから元E/H・全RFの不変量を確認し、
不完全prefix/異なる物理/既に新FEMがある失敗の再実行を拒否する。
製品401ファイル不変、独立解析場は比較器対照だけで、実FEM固有値を置換しない。
尺度1/2の実検証handle50414/27391、出力 `corner-tm-s1-mixed/` / `corner-tm-s2-mixed/`。
これはまだ物理受入ではない。失敗時も許容値を維持してrawを保持する。

## 実行入口と残件

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_planar_curved_geometry_series.py --shape circle --polarization te --scale 1 --angular-segments 32 --out out/<new-unused-name>
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/extend_planar_curved_shapes.py --from-evidence out/<terminal-failed-shape> --out out/<new-unused-name>
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/extend_planar_curved_mixed_refinement.py --from-evidence out/<failed-corner-TM-A4> --budget-failure out/<zero-FEM-geometry-budget-failure> --out out/<new-unused-name>
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/recover_planar_curved_shapes.py --from-evidence out/<terminal-interrupted-prefix> --terminal-audit out/<observed-terminal-audit.json> --shape ellipse --polarization tm --scale 2 --out out/<new-unused-name>
```

独立円A/Bと非円形の残gate、N16/32/64の全尺度/偏波を確認してからP07条件別監査を行う。
増求積・独立共変性の既成功は再利用し、今回の部分受入を全P07へ拡張しない。
P08 native/CLI/Project/worker/GUI、P09比較/調整と原計画の他カードは継続する。
新外部資料/依存/legacy参照なし。R39/R40と既存独立数学を検証参照に使用し、製品固有値を置換しない。

## 幾何予算切れに対する分離作業ツリー（未統合）

mainの15検証handleが401製品を固定しているため、branch `p07-geometry-bvh` / commit `a1def65` を
`/tmp/superfish-ng-p07-geometry-bvh` に作成した。Cartesian全辺検査の候補探索だけを閉AABB二分木へ変更。
全閉箱/全辺対の被覆、接触/未解像gap、同じ総予算を保ち、全detJ/Green/元写像やFEM/RF式は不変。
独立に分離する三乗間隔水平1024辺の旧実装は32768予算で終了1、新探索は同予算以内PASS。
新4＋直接利用先19、計23unitは5.964秒PASS。旧/新の2048辺比較は2096128/7423回、2.337/0.121秒。
これは探索だけの実測で、FEM全体の速度比ではない。

条件/失敗/実測の全記録は同branch `docs/PLANAR_CURVED_EDGE_SEARCH.md`。
実検査handle27869、main側の新出力 `out/p07-planar-geometry-bvh-20261007/`。
元corner TM A L4の全場/周波数/全RFを物理再構築して確認し、同じ1e8予算で全98304cellのL5 Domainを検査中。
変更した分離製品はgeometry一ファイルだけ、mainの全401製品は不変。
現在mainへ未統合であり、L5のf/E/H/RF受入を先取りしない。最後の利用handle終端までmainのsource固定を維持する。

## 楕円TM B系列の最終一様細分の丸め未達と追加二分（2026-10-07）

尺度1の追加handle49794は1739.032秒/終了1を観測した。
元A L3/A L4/B L4の物理再構築とA再受入後、B一様L5の最終元親chartで
`cumulative original-map roundoff exceeds local resolution` が生じた。
規定上限512ε/局所extentを維持してUNVERIFIEDとし、追加新FEMは0、progressは空。
元失敗出力を変更せず、別の `ellipse-tm-s1-L5-termination.json` に終端観測を保存した。

`scripts/extend_planar_curved_ellipse_bisection.py` は、この終端観測・累積丸め失敗・新FEM0と
完全元A L1〜L4/B L3〜L4の失敗prefix・製品401/元8検証器/失敗側9検証器hashを必須とする。
元A L3/A L4/B L4を物理再構築し、accepted Aの実f/E/H/RF差を再確認した後、
B L4を二分した `B-bisection-uniform3-bisection` を新実FEMで解く。
元P2 boundaryを再投影せず、同じ512ε上限と1e8検査予算、原f/E/H/全RF許容差を維持する。
一般共通parent比較でB二水準差と独立A/B差を別判定し、同一native meshは独立受入を拒否する。
これは一様L5の成功を装う代替ラベルではなく、明示的に異なる細分履歴である。

新 `test_planar_curved_ellipse_bisection` 2件は3.101秒PASS/終了0（handle61068）。
完了prefix/終端/全artifactの読取不変と、timeout/成功/別case/完了FEMの繰返し/不完全hash拒否を確認する。
比較積分/元場不変量の既成功 `test_planar_curved_mixed_refinement` を unchanged integration の証拠として利用する。
新driverは実検証handle72293、出力 `ellipse-tm-s1-extra-bisection/` と同名log。
製品401と使用10検証器を終端まで固定する。現時点では検証中、楕円TMやP07を受入とはしない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_ellipse_bisection
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/extend_planar_curved_ellipse_bisection.py --from-evidence out/<completed-failed-ellipse-TM> --uniform-failure out/<terminal-zero-FEM-uniform-map-failure> --terminal-audit out/<observed-terminal.json> --out out/<new-unused-name>
```

分離BVH実検査27869は、元corner TM A L4の24576cell/37120edgeを物理再構築し、
全係数/周波数のbitwise一致と全RF/metadataの完全一致を確認した。
独立面積energy/全vector壁積分の差最大6.968e−12もPASS。
geometryは1848997 box検査/予算1e8、全detJ/GreenもPASS。
これはA4のRF収束未達を改善する数値補正ではなく、元の値を保存する証拠である。
新L5 Domain検査へ進行したが、f/E/H/RFや全P07受入は未達のまま。
新外部資料・依存・legacy参照なし、shared radial/seed形式を変更しない。

## 分離geometry変更の実L5受入と次の物理検証（2026-10-07）

実検査27869は終了0/PASS。L5の98304cell/197633node/147968edgeで全geometry検査を確認。
総box検査7452020回/同じ1e8予算、全Green/正detJと面積3e−4 m²/周長0.08 mはPASS。
最終元親map丸め上限1.875377e−14、規定512εを維持する。
生成全体456.170秒。旧L5は予算切れで未完了なので、両L5の全体速度比は算出しない。
元A4全係数/周波数/全RF一致と合わせて幾何探索のbounded四条件を確認した。
branch `p07-geometry-bvh` の実装はmainへ未統合、main401製品も不変。

新実FEM検査34914を開始、driver `out/p07-planar-geometry-bvh-20261007/solve-corner-A5.py`、
出力同親 `corner-tm-s1-uniform-A5/`、logは `solve-corner-A5.log`。
完了geometry全artifactと元A4全artifact、400旧製品不変/geometry一ファイル変更を照合し、
前回FEM前に失敗したuniform A5だけを新実solveする。
元A4の物理再構築/実uniform親制限/元f/E/H/全RF/完全band/独立積分を別検査する。
この検査中はbranchの401製品・使用検証器を固定する。
実FEMの終端は未確認、独立B/尺度2/P07全体をこのgeometry成功から受入とはしない。

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

新15件は上記四回の分割結果。先行検査を再実行して数を増やさない。
raw/logは `out/p07-planar-curved-geometry-20261007/`。
製品401ファイル・seed/shared core/依存不変の検証専用追加なので、全validate/seed/GUIは実行していない。

## 終端を確認した幾何/FEM受入

各ケースL0/L1/L2の新3実FEM、L1→L2で全ゲートPASS、製品401hash不変。
円は解析絶対gate、楕円は完全band gateもPASS。
下表の値は対象の最初3完全群についての相対差最大で、E/H/RFを別判定する。

| 元形状・偏波・尺度・N | 秒 / 終了 | f差 | E差 | H差 | 全RF差 |
| --- | --- | --- | --- | --- | --- |
| circle TE s1 N32 | 155.690 / 0 | 2.1121e−5 | 0.006515 | 0.0004438 | 8.742e−5 |
| circle TE s1 N64 | 431.778 / 0 | 1.6084e−5 | 0.005687 | 0.0004142 | 7.284e−5 |
| circle TE s2 N32 | 198.150 / 0 | 2.1121e−5 | 0.006515 | 0.0004438 | 8.742e−5 |
| ellipse TE s1 N32 | 125.726 / 0 | 1.8103e−5 | 0.006024 | 0.0002712 | 6.218e−5 |
| ellipse TE s1 N64 | 353.458 / 0 | 1.2282e−5 | 0.004962 | 0.0002309 | 4.160e−5 |
| ellipse TE s2 N32 | 157.514 / 0 | 1.8103e−5 | 0.006024 | 0.0002712 | 6.218e−5 |

真幾何の相対面積/周長/距離上限はN32で3.0931e−6 / 1.5436e−6 / 2.8984e−6、
N64で1.9348e−7 / 9.6694e−8 / 1.8137e−7。楕円は独立周長求積と保守的アフィン距離上限を用いる。
各21ファイル、計126の完全snapshotは `accepted-six-artifact-hashes.json`。
N16の先行受入は再solveせず物理再構築/全hash付きで系列へ統合する予定。
未終端N64尺度2/TMをこの六例の受入に含めない。

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

## 実行入口と残件

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_planar_curved_geometry_series.py --shape circle --polarization te --scale 1 --angular-segments 32 --out out/<new-unused-name>
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/extend_planar_curved_shapes.py --from-evidence out/<terminal-failed-shape> --out out/<new-unused-name>
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/recover_planar_curved_shapes.py --from-evidence out/<terminal-interrupted-prefix> --terminal-audit out/<observed-terminal-audit.json> --shape ellipse --polarization tm --scale 2 --out out/<new-unused-name>
```

独立円A/Bと非円形の残gate、N16/32/64の全尺度/偏波を確認してからP07条件別監査を行う。
増求積・独立共変性の既成功は再利用し、今回の部分受入を全P07へ拡張しない。
P08 native/CLI/Project/worker/GUI、P09比較/調整と原計画の他カードは継続する。
新外部資料/依存/legacy参照なし。R39/R40と既存独立数学を検証参照に使用し、製品固有値を置換しない。

# P07：元場APIの点所有cell grouping

2026-10-07、分離branch `p07-reference-basis-cache`。mainは元円独立検証38783の終端まで源を固定する。
この修正はstrict閉所属と参照basis再利用を実装済みの別checkoutに追加し、mainへ未統合。

## 問題・受入条件

`scalar_at_reference` / `all_fields_at_reference` は各ownerについて全点vectorをmask走査していた。
保存済み円TM半径.01のB5は81920cell、order8で5242880点、元実装は各modeで429496729600要素を走査する。
これはtimeoutからの推測ではなく、実case/保存rawと実コードの走査構造を照合した数量である。
384点/128ownerの反例では49920要素を走査し、線形上限3072の独立testにFAIL、0.211秒/終了1。
原log `out/p07-planar-exact-reference-20261007/field-grouping-baseline.log` を保持する。

受入条件は、所有cellのgroupingを一度だけ行う、各owner内の元point順序と元演算shape/orderを保存する、
全scalar/勾配/座標と全12場の値・返却順序をbitwise保存する、strict参照拒否と元Maxwell符号を保つ、の四点。
元場・係数・行列・RFをcacheせず、各実写像/J/場を元係数から計算する。

## 実装・分割unit検証

solver一ファイルに `_cell_point_groups` を追加。ownerが非減少なら連続sliceを線形走査で得る。
任意順序ならstable argsortでまとめ、各owner内の元point index順序を保存して元位置へ代入する。
二つの元APIで同じgroupingを利用する。所属/mode/finite SI検査と物理演算は維持する。

新3件と直接利用する旧solver7/strict4、計14件1.464秒PASS/95559終了0。
順序付き・random・逆順の両偏波で、旧mask実装の元P2演算に対し全成分/scalar/勾配/座標がbitwise一致。
製造線形scalarの勾配[1,2]とpeak +iωt Maxwell符号を独立検査する。
製造場はAPI不変量の検査であり、実固有対や離散化収束の証拠とはしない。
既存実固有場/energy・実壁/復旧/scale/strict拒否もPASS。全14件を文書更新のため再実行しない。
影響はCartesian曲線の点batch評価であり、radial seed/共有形式は未変更。full/seed validate/GUI/hosted CIは未実行。

## 実保存B5の物理再構築・測定

元円独立検証38783は生存し、半径.01 TEのB4とTMのB5が全gateにPASSした。
半径.02 TEのB3を生成済みで、元source/全401製品/旧5validatorの固定を維持して継続する。
進行更新は保存 `mesh-progress.json` と `mesh.log` から確認した。timeoutによる再起動・打切りはない。

別driver `scripts/measure_planar_curved_field_grouping.py` をhandle42739で開始。
出力 `out/p07-planar-exact-reference-20261007/field-grouping-physical-replay/` と同名log。
完了済み半径.01 TM B5の全元chart/native/K/M/lowest bandを物理再構築し、新FEM0。
全係数/周波数bitwise、全RF metadata完全一致とstrict閉壁parameterの浮動丸め≤1e−12、
独立energy/実壁≤1e−8を必須とする。元strict実装からsolver一変更/旧400製品不変を明示する。
旧Python solverの全source hashを照合し、実係数1024owner/65536点の元scalar/全mode APIを
順序付き/random入力で測定して全返却配列bitwise一致を検証する。測定速度を全FEM速度と呼ばない。
branch全401製品/使用8codeと保存済みB5全artifactを実終端まで固定する。実測は以下の終端追記で受入した。倍率の適用範囲を限定する。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=/tmp/superfish-ng-p07-reference-basis-cache/src:/tmp/superfish-ng-p07-reference-basis-cache/tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest test_planar_curved_field_grouping test_planar_curved_solver test_planar_curved_exact_reference
```

新外部資料・依存・legacy参照はない。既存自作P2元演算を比較referenceとして再利用する。
P07 IN_PROGRESS、全123カードgoal ACTIVE。元円全尺度/全N64/角TM、統合、P08/P09を継続する。


## 実保存B5の終端・測定範囲（2026-10-07）

42739は502.301秒PASS/終了0、新FEM0。元円TM半径.01 B5の81920cell・全元chart/native/K/M/最低帯を再構築した。
全係数/周波数bitwise、全RF metadata完全一致、閉壁parameter丸めによるRF差最大2.221e−16、
独立energy/壁最大8.276e−13を確認した。前後401branch製品/使用8code/元完了B5全artifact不変。
各1024owner/65536点の元scalar/全mode APIで、順序付き/randomとも全返却配列bitwise一致。
実測旧/新は順序付きscalar 0.2070/0.1910秒（1.084倍）、全mode 0.2410/0.2021秒（1.192倍）。
random scalar 1.0987/1.7597秒（0.624倍）、全mode 1.1443/1.0942秒（1.046倍）。
この単回・並行実行下のrandom scalar測定は低速化を示しており、全入力の速度改善や全FEMの倍率を主張しない。
受入は全点反復走査の除去、owner内演算と出力のbitwise保存、独立物理gateに限定する。
順序付きは線形、任意順序はstable sortでgroupingする。全81920owner/5242880点のAPI実測はしていない。
全6artifact snapshotと観測終端auditを保持。cache branch単独のsource固定を解除する。
mainの38783とboundaryの37232/67404の生存源は変更しない。source統合/P07全条件は未受入。

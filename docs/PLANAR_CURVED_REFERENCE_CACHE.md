# P07：参照P2基底の同一計算再利用と残るstrict条件

2026-10-07、分離branch `p07-reference-basis-cache`、worktree `/tmp/superfish-ng-p07-reference-basis-cache`。
main/BVH/boundaryの生存中ソースを変更せず、別checkoutで検証する。mainへ未統合、全P07未受入。

## boundedな変更と受入条件

各curve cellの面積/元場評価は、同じ参照Gauss点のP2基底を毎回計算していた。
検証専用vector adapterの先行単patch実測では元APIの基底評価を含む経路が重く、
大型P07/P08の物理再構築とP09の実FEM反復でも同じ参照表を全cellで繰り返す。

変更は `PlanarQuadraticTriangle.evaluate` の参照基底表だけ。
入力strict検査を従来どおり行ってから、binary64参照配列の完全bytesをkeyとして最大32表を保存する。
一表は4096点以下、大きい入力は再利用しない。float64値/勾配とkeyは総約21 MiB以下に制限される。
計算式・順序は既存自作 `basis_p2` のまま。保存表はbytes-backed immutable、公開値arrayは毎回copyする。
実座標、各実J/J逆、元場、K/M、係数、固有値、RFは保存表へ入れず、従来の演算順序で実計算する。

受入条件は同一参照表の重複計算を省く、異なる参照/実geometryを混同しない、外部array改変で後続を汚染しない、
容量を制限する、全mapped配列とK/Mのbitwise一致、元保存解の物理再構築/係数と全RF一致、の六点。
速度向上を精度の根拠にせず、物理gate/予算/solverを変更しない。

## 分割検証

変更前の独立一件は同じ64点を二geometryで128回計算し、期待する64回に対してFAIL、0.025秒/終了1。
`before.log` を保持した。
変更後の選択25件は5.830秒、24PASS/1FAIL（handle35737/終了1）。
新3件と直接利用する既存curve9・refinement3・boundary3・solver7の構成。
唯一の失敗は下記の既存1 ULP参照所属問題であり、cache導入前のmainでも同じ受理を実証した。
cacheの既存拒否動作検査を、元実装が明確に拒否する二ULP外点へ限定し、その一件だけ再確認：
handle68737、0.003秒PASS/終了0。分割25種類成功を保持し、他24件を繰り返さない。

新検査は実geometry二尺度/平行移動のJ/勾配法則、全配列を従来式とbitwise照合、
参照partition unity、返却array改変、別参照bytes、32表上限、4097点の非再利用、従来strict拒否を確認する。
既存curve/K/M/元場/PEC/RF/物理restoreの独立検査も24初回成功に含まれる。

ログはmainのignored `out/p07-planar-reference-basis-cache-20261007/`。
read-only main自作Pythonの元geometryを別module名でロードして比較し、legacy参照はない。

## 実測と元保存解の検査

`out/p07-planar-reference-basis-cache-20261007/measure.py` / handle78576。
area order8/12/16の参照64/144/256点を各200回評価し、二尺度・平行移動patchで全mapped配列/K/Mのbitwise一致を確認した。

| area order | 従来秒 / 再利用秒 | 一回実測比 |
| --- | --- | --- |
| 8 | 0.535507 / 0.032030 | 16.719 |
| 12 | 0.925001 / 0.065709 | 14.077 |
| 16 | 1.456274 / 0.100397 | 14.505 |

実J/J逆計算を含む単要素評価の一回実測で、FEM全体や他環境の速度比ではない。
保存済み実ellipse TM尺度1 A4を元chart/native/K/M/lowest spectrumから物理再構築し、288.568秒PASS/終了0を確認した。
全元係数/周波数bitwise、全RF/metadata完全一致、独立energy/壁積分を別に必須とする。
旧399製品不変・geometry/refinement二変更を明示する。新FEM0、既存解を再solveしない。
前後branch401/使用11コードhashは不変。全元係数/周波数bitwiseと全RF/metadata完全一致を確認した。
独立energy/壁差最大1.037e−13、元親map丸め7.928222e−14。新FEM0。
出力 `results/` / `measure.log` と別terminal audit・全7artifact snapshotを保持する。
このbounded性能/物理保存条件を受入し、branch単独のsource固定を解除する。他checkoutの生存源固定は維持する。
P07全受入と下記strict所属不備の解消は別条件。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=/tmp/superfish-ng-p07-reference-basis-cache/src:/tmp/superfish-ng-p07-reference-basis-cache/tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_reference_cache test_planar_curved test_planar_curved_refinement test_planar_curved_boundary_refinement test_planar_curved_solver
OPENBLAS_NUM_THREADS=1 PYTHONPATH=/tmp/superfish-ng-p07-reference-basis-cache/src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -u out/p07-planar-reference-basis-cache-20261007/measure.py
```

## P07完了前に是正するstrict参照所属

既存mainへ入力 `x=0.5, y=nextafter(0.5,1)` を渡すと、float和は1.0だが正確な有理和は
9007199254740993/9007199254740992で1より大きい。`evaluate` はこれを受理し、負のbarycentric基底も返した。
証拠 `original-rounded-reference.log`、新FEM0。cache前のAPIにもある不備であり、今回の性能変更で修正したとはしない。

[P05閉参照三角形契約](PLANAR_CURVED_RF.md#元場規格化pec壁rf)は未充足のまま。
次のbounded修正は、丸めで和が1になる外点を厳密に拒否し、元場の共通入力検査とlocatorも整合させること。
内部の壁参照 `(1−t,t)` には二進丸めによる同種の組があるので、独立の閉境界不変量を用い、
所有edge上の表現可能な参照点/壁点/法線/求積を一致させる必要がある。
許容差で外点を広げず、正確な境界接触と任意に近い外点を区別する。
正しい境界表現の丸め変更を従来全RFのbitwise一致と混同せず、全metadata保持と元物理gateを別検証する。
この不備を未確認リストから消さず、P07の完了判断前に実装・独立反例・場/RFを検査する。

## 来歴と検証範囲

自作P2表/Cartesian mapperのみを再利用。新外部資料・依存・legacy参照なし。
canonical TM/軸対称の共通基底やr形式は変更せず、参照表の再利用はCartesian曲線module内に限定する。
seed/full validate/GUI/hosted CIは未実行。現行の全123カードscopeとP08/P09の残要件を保持する。


後続の[厳密閉参照判定](PLANAR_CURVED_EXACT_REFERENCE.md)は別source変更。
一ULP外点の拒否/壁所有点の整合を分割28種類で確認し、保存TE/TMの実物理再構築74571を検証中。
30e604cの全RF bitwise保存証拠と、閉壁parameterの浮動丸め差/全metadata保持を分けて記録する。
mainは未統合であり、全P07受入は先取りしない。

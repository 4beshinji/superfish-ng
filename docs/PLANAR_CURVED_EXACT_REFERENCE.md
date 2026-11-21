# P07：丸めを越えて厳密に閉参照三角形を判定する

2026-10-07、分離branch `p07-reference-basis-cache` の `30e604c` 後続。
main/BVH/boundaryの生存中sourceを変更しない。main未統合、全P07未受入。
[参照表再利用の終端受入](PLANAR_CURVED_REFERENCE_CACHE.md)とは別の科学的修正。

## 独立反例と受入条件

x=0.5,y=nextafter(0.5,1)はfloat和1.0、正確な有理和9007199254740993/9007199254740992>1。
元APIはこれを受理し負のbarycentric基底を返した。x=1,y=最小正subnormalも同じ誤判定となる。
新反例test一件は変更前0.015秒FAIL/終了1。`out/p07-planar-exact-reference-20261007/before.log`を保持する。

受入条件は、正確なbinary64閉所属でこれらの外点を拒否する、真の接触/内点を受理する、
元12場/validator adapter/locatorを同じ閉所属へ整合する、
壁の所有参照/実点/法線が同じ表現可能parameterを使う、TMの壁Ezが厳密に零となる、
元K/M/保存係数/周波数と物理RF/metadataを保持する、の六点。
外点を許容差で拡張しない。科学的なf/E/H/RF/積分gateは変更しない。

## 変更

`_closed_reference_mask` は非負かつ座標≤1とfloat和≤1を確認し、
和がちょうど1に丸められた組だけをFractionの正確な和で再判定する。
和<1の内点や通常の面積Gauss ruleはvectorized経路のまま。
geometry評価、元場の共通入力、検証用全vector評価、locatorのNewton候補に接続する。
厳密外点がcache内にあっても、再利用前の所属検査で拒否する。

壁Gauss parameterを `t=1−(1−t)` として、tと1−tの有理和が厳密に1となる表現を選ぶ。
parameter移動はε/2以内。所有cell/ref、実壁点・tangent/法線・dsに同じparameterを使用する。
加速量null/理由、U′/単位、peak規約、area/wall orderと全物理式を保持する。
独立order20全vector壁積分も閉参照のparameterを使い、積分式は従来の法線除去式を保持する。

修正された四製品はgeometry/location/refinement/solver。refinementは先行boundary変更であり、
今回のstrict変更はgeometry/location/solver。main旧397製品は不変。
検証用vector/independent helperの変更は別source manifestに記録する。

## 分割検証

初回選択27件は2.947秒、25PASS/2ERROR、handle82996/終了1。
新strict3、旧curve9/solver7/vector5/cache3の構成。
二ERRORは従来の独立quad壁probeとcache実測gridが、丸めで厳密外点となる `(1−t,t)` を作っていたため。
その二つのtest入力を表現可能な閉辺へ整合し、数値許容値は変更しない。
該当二件だけ0.217秒PASS/終了0を再確認。初回他25件を繰り返さない。
さらに独立の実TM PEC壁zero一件は0.101秒PASS/終了0。
分割28種類の成功であり、一回の全suite成功とはしない。

新四件は丸め和1外点/最小subnormal外点の全元API拒否、真接触/内点、
64組の角/一ULP隣点を正確な有理oracleと照合、全三辺の正確なcomplement/実壁点一致、
実TE/TMの元場/energy/全vector壁積分、実TMの全壁Gauss点でEz=0を確認する。
旧直接消費先の行列/Green/全Jacobian/実元場/物理restore/全12成分/全RF/逆写像/容量検査も成功。
新FEM/依存/legacy参照による既知解への補正は行っていない。

## 保存済み両偏波の物理再構築

実handle74571、driver mainのignored `out/p07-planar-exact-reference-20261007/replay.py`。
円TE半径0.01の保存L3と楕円TM尺度1の保存A4を、全native/J/K/M/lowest spectrumから再構築する。
元全係数/周波数bitwiseと全RF metadataの完全一致を必須とする。
正しい閉辺parameter化によるRF数値の浮動丸め差は≤1e−12とし、元積分gate1e−8より厳しく確認する。
これを従来RF値のbitwise一致とは呼ばない。全値・最大差・規約・独立energy/壁を別保存する。
これは保存解の物理再検証であり、新FEM0、元解/Caseを再solveしない。

出力同親 `physical-replay/`、log `replay.log`。74571は230.797秒PASS/終了0、新FEM0。
元係数/周波数bitwise、全metadata完全一致。TE RF数値差0、TM最大2.221e−16、独立積分最大1.037e−13。
前後401製品/使用7code/全元artifact不変。全7artifact snapshotと別terminal auditを保持する。
このbounded strict条件を受入し、branch単独source固定を解除する。他checkoutの生存源固定は維持する。
mainへ統合後のP07全条件監査/P08/P09は別に残る。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=/tmp/superfish-ng-p07-reference-basis-cache/src:/tmp/superfish-ng-p07-reference-basis-cache/tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_exact_reference test_planar_curved test_planar_curved_solver test_planar_curved_vector_reference test_planar_curved_reference_cache
OPENBLAS_NUM_THREADS=1 PYTHONPATH=/tmp/superfish-ng-p07-reference-basis-cache/src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -u out/p07-planar-exact-reference-20261007/replay.py
```

## 来歴

既存自作Fraction幾何とbinary64参照演算を使用する。新外部資料/依存/legacy参照なし。
Cartesian曲線専用の所属/壁入力に限定し、shared高次基底/軸対称r形式/canonical TMは変更しない。
seed/full validate/GUI/hosted CIは未実行。全goal ACTIVE、P07は未完了。

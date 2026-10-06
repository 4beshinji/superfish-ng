# 平面曲線の楕円・再入角の固定領域検査 — P07進行記録

2026-10-07、`029be4c`の後続。P07/親P02の全受入ではない。
[P05の非円形gate](PLANAR_CURVED_RF.md#検査入力と固定した個別gate)を維持する。
専用 `scripts/validate_planar_curved_shapes.py` は1形状/1偏波/1尺度を未使用出力へ保存する。

## 入力と判定

楕円はa=0.02,b=0.012 mと2倍、中心(−0.03,0.01) m、回転π/7。
初期4ring円の全二次節点をaffine変換し、境界二次写像をnativeとして保持する。
円の一変数倍率を楕円固有値へ使わない。面積と真周長は独立公式/1D積分、
真形状への距離は円の二次辺のradial defectをaffine作用素normで移す保守的上限。
同一初期Domainの参照細分とN16/32/64の別初期幾何は異なる系列である。
本driverの各実行は指定N一つの固定領域FEM差に限定する。

L字はa=0.01/0.02 m、外周(−a,−a),(a,−a),(a,0),(0,0),(0,a),(−a,a)。
面積3a²/周長8a、3π/2再入角を保持する。初期96三角形を座標の三乗で角へgradedし、
その元P2写像を細分する。局所q~r^(2/3)の壁二乗/面積勾配が可積分であることは
[独立不変量](PLANAR_CURVED_INDEPENDENT.md#後続の入力と評価候補)で確認する。
有限corner peakや全L字の解析絶対f/Gを主張しない。

両形状で6正モードを保存する。楕円とL字TMはsimple group、L字TEは
`cos(πx/a),cos(πy/a)`の完全Neumann二重群を含む[1,1,2,1,1]を宣言する。
この二つの関数は全外周/内側直線で法線微分零、平均零、波数π/a。
その既知周波数は二重群を切らないための独立不変量であり、FEMを置換しない。
群境界の相対gap>1e−3、二重群のf差≤1e−4を確認し、未確認なら受入にしない。
数値順位を個別IDとして保存しない。

A uniform系列の最終二水準、B bisection→uniform系列の最終二水準、A対Bを別判定。
最初の3完全群を対象とする（L字TEは4モード）、残りはguardとして全結果を保持する。
f≤1e−4、元E/H各≤1%、全RF≤0.5%。各元場の独立area/wall積分も≤1e−8。
粗い未達を保存し、最大Lを明示して実細分する。1caseの成功を二尺度/両偏波へ拡張しない。

## 検証専用評価器

`vectorized_validation_view` は全元Case/係数/周波数/K/M/free DOFの同じobjectを持ち、
全モード場評価だけをvector化する。元RFは製品routineのままで全係数/周波数を保持する。
製品src/API/schemaは変更しない。円の既に実行中の比較器は元APIを継続使用する。
後続非円形driverがこのadapterを明示採用し、使用版hashを固定する。

追加adapter1unitは0.008秒PASS、全元array object/全12成分/全RF一致を確認。
全参照partition経由の追加1unitは0.373秒PASS、元APIと候補の直接E/H差・全判断・RF一致、
独立area/wall積分一致を確認。時間はunit logの実測値を正本とする。
先行vector3unitと合わせた分割5種類の成功証拠を保持する。
群guard拒否の追加1unitも0.000秒PASS（unittest表示）。先行shape4unitと合わせ分割5種類。

## 実行状態

楕円TE尺度1/session25516、L字TE尺度1/session68744が実行中。
出力は `out/p07-planar-curved-independent-20261007/ellipse-te-s1/` と `corner-te-s1/`。
同親の同名 `.log` を観測する。401製品と使用8検証器のhash固定、終了まで変更しない。
追加6実行：ellipse TM s1=12945 / TE s2=25128 / TM s2=92077、
corner TM s1=35844 / TE s2=27629 / TM s2=70344。同じ入力/固定gateで全8caseを検査中。
各出力とlogは同親の同じ命名規約。その他尺度/偏波も終端までは未受入。
幾何系列の各十分細かいFEM、尺度・回転の全vector不変量は残る。
P07 IN_PROGRESS、全goal ACTIVE。数値許容値・依存・参照制限は維持する。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_vector_reference.PlanarCurvedVectorReferenceTests.test_adapter_keeps_original_arrays_and_full_RF_and_API
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_vector_reference.PlanarCurvedVectorReferenceTests.test_adapter_preserves_whole_partition_comparison_and_independent_RF_integrals
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_shape_reference.PlanarCurvedShapeReferenceTests.test_complete_neumann_pair_and_group_guards_fail_closed
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_planar_curved_shapes.py --shape ellipse --polarization te --scale 1 --out out/p07-planar-curved-independent-20261007/ellipse-te-s1
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_planar_curved_shapes.py --shape corner --polarization te --scale 1 --out out/p07-planar-curved-independent-20261007/corner-te-s1
```

新外部資料・依存・legacy参照なし。独立pair/面積/可積分性は既存のMaxwell/弱形式から導出。
seed/full validate/hosted CIは未実行。native/操作はP08、追跡/調整はP09の別受入。

## 独立FEMの尺度・回転・平行移動

`validate_planar_curved_covariance.py` は円/楕円/graded L字の粗い初期Domainを使い、
一様2倍・回転π/9・平行移動(−0.07,0.02) mを全元native節点へ適用する。
各側を実FEMで独立に解き、元周波数/係数を法則で生成しない。計12FEMのCase/全係数を保存する。
全cell/境界の完全変換を確認し、参照点で各側の元場を評価する。
一つのscalar群回転だけを決め、Cartesian vectorは宣言した座標回転を逆に戻す。
元E/Hの相対L2、f→f/s、G不変、Q→sqrt(s)Qのほか全energy、壁H積分、Rs、P′、
面積・周長の尺度則を個別に≤1e−8で検査する。加速量null/規約も保持する。
これは粗い離散形式の共変性であり、絶対物理精度やmesh収束の代用ではない。

新3unitは0.083秒PASS/終了0。独立に解いた曲線patchの全場/全RF尺度則と、
frequency/amplitude差を整合で消さないこと、不正群/非proper回転/不完全geometryを拒否することを確認。
専用session71524、出力 `out/p07-planar-curved-independent-20261007/covariance/`、
logは同親 `covariance.log`、使用7検証器と401製品をhash固定して実行中。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_covariance_reference
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_planar_curved_covariance.py --out out/p07-planar-curved-independent-20261007/covariance
```

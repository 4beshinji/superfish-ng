# 平面曲線の元E/H内積

2026-10-07、P09の元場比較leaf。先行は[完全参照比較分割](PLANAR_CURVED_COMPARISON.md)。
P09はIN_PROGRESS。個別mode ID・guard・固定境界調整/最終細分・所有再開・GUIは未受入。

`planar_curved_field_overlap.py` の `planar_curved_field_grams` は、完全な宣言比較Domain/参照chartと
二つの実 `PlanarCurvedSolution` を取り、EとHそれぞれの旧自己/交差/新自己Gramを返す。
元の12 real/+i quadrature成分を各nativeの実写像で評価し、実nativeのdx dyを使う。
内積はpeak phasorの共役ベクトル積の実部で、E単位はV²、HはA²。軸対称のr重みを入れない。
交差は固定Cartesian成分とsqrt(dA_old*dA_new)の密度対応で、各自己energyを保つL2比較。
Maxwell座標変換/周波数則/射影/離散化誤差/個別identityの主張はしない。偏波の混在は拒否する。
元の符号・振幅・規格化は保持し、交差Gramへabsを掛けない。

両側の実Domain/元六配列/float64係数と周波数を再構築し、最低正帯・TM PEC・TE定数核除去・正規化を
再検証する。元K/Mとfree DOF/固有値も厳密に照合する。導出residual/orthogonalityは元solverの
1e-7/1e-8 gateを保持し、新たに再計算した値で検証する。strided入力をimmutable保存へコピーすると
BLAS累積の末尾bitが変わり得るため、導出診断値にbyte一致は要求しない。
元係数/周波数のdtype/shape/全byteには一致を要求する。返すGramはbytesを基底とするimmutable配列。

自己内積の独立対照は元FEM行列から得る。S=cᵀMc、Dij=(cᵀKc)ij/(ωiωj)として、
TMは E=S、H=D/μ₀²、TEは E=D/ε₀²、H=S。従って総time-averaged energyは
(ε₀ diag E + μ₀ diag H)/4、単位J/m。場の再積分と元行列の双方を一致させる。
E/Hを別判定し、求積二水準の規格化差は1e-10、元energy Gram再現は1e-8、joint Gram PSDは1e-10。
これらは連続問題に対する誤差許容値ではない。

比較次数はlow=4〜28、high=low+4（最大32）。標準lowは
min(28,max(16,両Case面積次数+4))。全二次数×両側×全比較三角形の総点数を
`max_sample_points`（標準2,000,000）で一度に制限し、次数/側ごとにリセットしない。
元モード数の予算 `max_gram_modes` は256。幾何予算は先行比較分割に従う。
積分のresident sampleは262,144 point-modeを目安に三角形単位でbatch化する。
予算不足/求積未解決/energy不一致はUNVERIFIEDで停止し、部分Gramを受入しない。

## 独立検査と初回反例

最初に実TE/TM楕円の元K/M energy対照を作成し、API不在の
ModuleNotFoundErrorを `field-baseline.log` に保存した。元数値回帰の失敗ではない。
新7＋関連10の初回17件5.318秒は16 PASS/1 FAIL。
strided一列から復元した正しい解のorthogonalityが2.220446049250313e-16→0となり、
導出診断値の完全一致要求が有効入力を誤拒否した。上記の再計算方針へ製品を修正し、
有効strided再生の係数全byte不変も検査した。元物理gate・場/energy tolerancesは変更していない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
uv run --no-sync python -m unittest -v \
test_planar_curved_field_overlap test_planar_curved_comparison test_planar_tracking_fields
```

修正後17件5.552秒PASS（終了0、`field-selected-tests-corrected.log`）。
新7件はTE/TM自己energy/全RF不変、尺度×2/U′×3.7/負符号の解析内積、
非nested二次patchの全real/quadrature定数場と独立面積、独立セル番号、実固定二次外周細分、
累積予算、再hash様の元配列/K/M/帯改変・偏波拒否を確認した。
manufactured場はprivate求積seam限定で、公APIは同じtest objectを拒否する。
合成楕円/patchは測定構造ではない。

追加1件 `test_small_algebraic_residual_cannot_accept_unresolved_energy_integral` も別実行PASS。
粗いTE面積次数4の代数残差約8.3e-15でも、高次数の場積分と元K/Mが不一致なら拒否する。
元Case次数16でも比較4→8が未解決なら拒否する。小さいresidualを場積分精度と読み替えない。
新8＋関連10、計18件を分割受入。元FAIL/成功/追加logを全保存した。

rawは `out/p09-planar-curved-comparison-20261007/`。
`field-acceptance.json` は実装/test/logのhash、基準91b0a35の元404製品不変を確認した。
新製品はこの専用比較1モジュールだけ。曲線/seedの物理kernelは無変更。
今回は専用leaf unit内の実FEMを実行し、full/seed/GUI/新大型validatorは実行していない。
既存自作のquadrature/元場API/strict native/幾何比較を再利用し、xy専用内積を独立実装。
新外部資料/依存/legacy参照なし。次はこれらの元場内積と別スペクトルguardによる追跡核。

# 平面曲線比較の参照分割

2026-10-07、P09の最初の有界変更。P09はIN_PROGRESS。
追跡・個別ID回復・円/非円形の実調整・二つの周波数gate・所有保存/再開・GUIは未受入。

`planar_curved_comparison.py` の `PlanarCurvedComparisonDomain` は、元の完全な二次xy Domain二つ、
`same_domain` または `declared_quadratic`、制限写像の丸め方針とDomainごとの幾何予算を保存するstrict版1。
同一領域は全midを含む座標一致が必要。宣言写像は同じ完全なP2 topology/PEC外周を要求する。
各nativeセルに元セル番号と正向きの有理参照三角形を明示する。任意の独立再meshを自動推定するAPIではない。

`build_planar_curved_comparison` は、元の六節点二次多項式への制限、全元セルの厳密な非重複被覆、
全PEC外周の有理区間被覆、両nativeセルの全被覆を検証する。非nested分割の交差はFractionで計算する。
`exact` は一座標の差も拒否する。明示した `binary64_roundoff` は二次誤差のBernstein上界を
外向きに丸めて保存し、各nativeセルの局所extentに対する512ε上限を検査する。真円への投影はしない。

`evaluate` は実native写像のxy点/面積と元参照写像のxy点/面積を別々に返す。
丸めを含むnativeの自己energyを元参照の面積で代用しない。入力は閉参照三角形内に限定する。
境界演算の丸めが未解決ならUNVERIFIEDで停止し、外側点を許す距離toleranceはない。

予算は `max_pair_tests`（標準2,000,000）、`max_triangles`（250,000）、
`max_geometry_boxes_per_domain`（100,000、上限100,000,000）。pairは両側の自己重複検査と
全交差候補を通して一つの累積予算で数える。現実装は元セル内の全組合せを調べるため、
大きな細分では予算停止し得る。元セルごとの予算リセットや部分受入はない。
幾何報告のGEOMETRY_VERIFIEDは、場の求積精度・identity・連続問題誤差の保証ではない。

## 独立対照と検査

最初に既知写像 F=(tx+sx*l*x, ty+sy*l*(y+d*x*(1-x-y))) の非nested三分割で
面積/一次moment/正逆対応の検査を作成。API未実装によるModuleNotFoundErrorを
`out/p09-planar-curved-comparison-20261007/baseline.log` に保存した。
既存数値回帰が失敗したという意味ではない。
独立式 A=l²(1/2-d/6)、Mx=tx*A+l³(1/6-d/12)、My=l³(1/6-d²/60) と照合する。
非一様尺度の面積×6、座標変換、節点/セル番号変更、全midが異なる反例、
実楕円の二次細分/丸め、欠落被覆、strict入力、全元セルで累積する予算を分けて確認した。
合成patch/楕円は測定構造ではない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
uv run --no-sync python -m unittest -v \
test_planar_curved_comparison test_planar_tracking_overlap test_planar_tracking_exact_affine
```

新7＋既存12、計19件2.151秒PASS（終了0）。`geometry-selected-tests.log` に全結果を保存。
`geometry-acceptance.json` は実装/検査/元FAIL/成功logのhashと基準604e52dの全403製品不変を照合した。
追加は専用比較1モジュール。曲線FEM/元場/RF、共通P2、seedは無変更。
今回の幾何leafにfull/seed/GUI/新専用FEM validatorは不要で実行していない。
旧関連検査に含まれる直線FEM evidenceを曲線場/実調整の受入とは扱わない。

既存自作の座標中立Fraction三角形交差、二次係数、制限評価のみ再利用した。
xy面積/PEC契約は専用に実装し、r重みや軸対称物理を使わない。
新外部資料/依存/legacy参照なし。次は元E/Hの自己Gram・交差Gramと独立energy対照。

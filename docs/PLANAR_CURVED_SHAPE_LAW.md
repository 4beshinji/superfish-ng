# 平面曲線の元全節点アフィン形状法則

2026-10-07、P09の形状生成leaf。P09はIN_PROGRESS。実調整/所有再開/GUIは未受入。
`planar_curved_shape.py` の `PlanarCurvedAffineShapeLaw` は、既存自作の有限多項式
`PlanarAffineShapeLaw` を完全な曲線xy Projectへ適用する専用strict版1。
パラメータ/行列係数はdimensionless、translation係数はm、係数はascending powers（最大9項）。
binary64宣言を厳密Fractionとして扱い、closed intervalでdetの全root（接線/端点を含む）を排除し、
正detを要求する。向き反転は別の二次chart契約が必要で、このlawは明示拒否する。
一般的な二次領域同士の[宣言比較](PLANAR_CURVED_COMPARISON.md)の範囲を狭める仕様ではない。
今回のlawはproper affine族だけで、任意の非アフィン曲線変位lawは実装しない。

`project(original,value)` は必ず元Projectから全六節点座標を有理式で生成し、各座標を一度だけfloatに丸める。
全cell_nodes/全boundary_nodesを保持し、真円/楕円への投影・直線化・直前試行への累積変形をしない。
偏波/元mode数/面積・壁求積次数/幾何予算/U′/conductivity/name/表示単位を保持する。
元Projectは変更しない。全mapped DomainのJacobian/外周/edge検証をFEM前に行い、
厳密なdet正則でも浮動座標が潰れる場合は拒否する。区間の数学的正則性を丸め分解能の保証と読み替えない。
`comparison(original,old,new)` は両値を元から再生成し、完全な二次declared correspondenceを返す。
後続細分の明示binary64 roundoff方針を保存するが、固有場/周波数法則を生成しない。

## 独立対照と限定検査

最初に二次patchの全節点・非一様面積・元からの再生成を検査し、API不在の
ModuleNotFoundErrorを `shape-baseline.log` に保存した。元数値回帰の失敗ではない。
独立式 F_t=(x+t*y/4+1/8,(1+t/2)*y-1/4)、det=1+t/2 を使い、
全mid/接続/PEC外周・元入力不変・JSON往復を確認する。
実円のTE完全doublet/TM基本modeを二尺度solveし、f×1/2、固定U′=2.3 J/m、
元mass内積の全scalar subspace一致、G不変/Q×sqrt(2)を照合する。
真doubletのbasisは任意なのでper-rank phase labelを要求せず全subspaceを比較する。
閉区間のeven root/端点退化・負det・strict版/単位/型・範囲外・丸め潰れを別拒否する。
2**53+1を含む整数boundも厳密に保持し、float(lower)で区間外へ丸めない。
合成円/patchは測定構造ではない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
uv run --no-sync python -m unittest -v test_planar_curved_shape test_planar_affine_shape \
test_planar_curved_operations.PlanarCurvedOperationsTests.test_project_and_dispatch_preserve_actual_case_and_solution
```

新4＋既存law3＋Project直接消費1、8件1.249秒PASS（終了0）。rawは
`out/p09-planar-curved-comparison-20261007/shape-selected-tests.log`。
`shape-acceptance.json` は実装/test/FAIL/成功log hashと基準76a795cの元408製品不変を照合した。
新製品は専用形状1モジュール。共有law/物理kernelは不変。
unit内の実TE/TM/旧直線FEMを実行し、full/seed/GUI/新大型validatorは実行していない。
自作の座標中立な有理多項式/全区間det root検査を再利用し、元xy P2座標/Projectを専用に扱う。
新外部資料/依存/legacy参照なし。次は全固定境界細分の試行生成/参照chartと実調整/所有保存/再開。
P09の円・非円形両周波数gate/全元場保存/worker/GUIは後続の必須範囲。

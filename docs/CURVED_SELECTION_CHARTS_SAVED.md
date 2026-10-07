# 曲線選択移送版2：完全再生とCLI

2026-10-08 JST、ADD-N04-selection-charts-04 **DONE**。開始commit `a7fc46f`。
[03の計算API](CURVED_SELECTION_CHARTS_CORE.md)へ保存文書の版別完全再計算を追加した。
全131は80 DONE/2 IN_PROGRESS/49 PLANNED、原123は76/2/45。
親N04・原32要件・全goalは継続。次は05のraw chart/図上選択/履歴GUI、06の専用独立受入。

## 保存と操作

版2のtop-level十項目をstrictに検査してから、両Projectと元requestから全参照分割を再構築し、
全親被覆・選択・予算・scope・physical_error_bound=nullを含む全文書を照合する。
旧版1の九項目/保存契約と再生経路は維持した。
版混用、欠落/未知項目、Project/参照座標/元選択の変更、全派生値の不一致を拒否する。
全有理数の分子/分母、要素ID、真偽値は元の厳密型を保持する。
Projectの浮動小数値の0.0→0表記は従来の同値JSON規約で受理する。
再生は新しい全文書を返し、入力を変更しない。自己完結した再計算であり外部真正性証明ではない。

CLIは既存二commandを利用し、版1/版2と要求chart/予算が分かるhelpへ更新した。
元CLI実行branchはbyte不変。transferは検証後に出力を排他作成し、既存ファイルを上書きしない。
replayは文書だけから再構築する。元入力ファイルを移動/削除しても保存文書を再生できる。

```bash
superfish-ng transfer-curved-selection \
  examples/curved_selection_charts/old-project.json \
  examples/curved_selection_charts/new-project.json \
  --request examples/curved_selection_charts/intersects.json \
  --out out/charts-transfer-new.json
superfish-ng replay-curved-selection-transfer out/charts-transfer-new.json
```

幾何被覆PASSはFEM精度や物理誤差上界のPASSではない。
GUI版2と新移送先markedの実FEM/RF検査は05/06の後続条件である。

## 受入と源束縛

新`CurvedSelectionChartsSavedTests`の6件は、両policy/全文書/浮動小数表記/返却値の独立性、
全top-level/selection/reference_partition項目の欠落と未知項目、Projectと元要求変更、
親番号/重心座標/被覆率/面積/組数とbool/float型の改竄、保存予算/重複キー/非有限座標、
non-nested/frozenと元電気/磁気対称、CLI排他出力/失敗時未作成/元byte保全/移動再生を確認した。

| 実行 | 結果 |
|---|---|
| 実装前反例 | 新round-trip一検査が旧版1保存readerの未知/欠落キーでERROR。0.088秒・終了1、元logを保全 |
| 新6＋直接旧8＋strict JSON1 | 15個別PASS、7.502秒・handle63580終了0。solver.solve/_solve/solve_curved/solve_teを例外guardして呼出し0 |
| 実CLI起動 | `uv run --no-sync python`から同じPythonの`-m superfish_ng`を四回起動。intersects/containedのtransfer/replay全終了0、保存全文書がAPIと一致 |
| 源/差分監査 | handle61362終了0。旧selectionは新saved helperとreplay dispatch以外の全AST一致。CLIは三help文字列以外byte一致、旧幾何9件と全helperもAST一致 |

全1440対象/1227 Python源は検査開始/終端/現行で一致。開始sourceとの変更はselection/CLI/new testの三つ、
他1437源byte一致。計算helper/参照分割/元科学核は03受入時と不変なので、独立三積分と尺度則、
旧TM/TE場比較の03証拠を再利用し数値検査を重複実行しない。
新FEM/seed/full/GUI/専用validator/legacy0。局所保存検査をfull受入として報告しない。
新外部資料/依存なし。既存自作JSON値比較と元native履歴の再構築を利用した。

rawは`out/n04-selection-charts-saved-20261008/`。元ERROR、開始三源archive、実runner/log/result、
四CLI log/Project/request/transfer、`audit-saved.py`/`acceptance.json`と全source SHAを保持する。
unitと監査のrunnerは`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python …`。

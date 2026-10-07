# 選択移送の明示参照座標：版2のstrict入力検査

現行追補：[04完全再生/CLI](CURVED_SELECTION_CHARTS_SAVED.md)をDONE。版2保存readerも接続済み。
以下の未接続/版1のみの記述は当該工程受入時点の履歴。次は05のGUI。

現行追補：[03計算工程](CURVED_SELECTION_CHARTS_CORE.md)をDONE。公開版2APIは接続済み。
以下の未接続/拒否の記述は02受入時点の履歴。次は04の完全再生/CLI。

2026-10-08 JST、ADD-N04-selection-charts-02 **DONE**。先行仕様commit `78d5c10`。
[固定仕様](CURVED_SELECTION_CHARTS_SPEC.md)の版2七フィールドを、
`curved_selection_transfer._validate_chart_request` で検査する。
公開版2の計算・保存・GUIは未接続で、次は03の全参照被覆と二policyの実装。
全131カードは78 DONE/2 IN_PROGRESS/51 PLANNED、原123は76/2/45。
親N04、原互換32要件、全goalは継続する。

## 実装と受入条件

未知/欠落項目、bool/floatの版/番号/予算、空/重複/負の選択、非文字列/未知方針、
二chart以外、list以外/三頂点未満、二座標以外、bool/文字列/非有限座標を拒否する。
巨大なPython整数は数学的に有限で、floatへcastしてOverflowErrorを起こさない。
入力は変更しない。raw JSONの重複キーは元 `project.parse_json` の全深さ拒否を使う。

頂点数とsource_meshの一致、選択番号上限、向き・自己交差・タグ・全被覆・幾何予算は03で確認する。
今回のinvalid-reference-boundary例は型検査を通り、全参照境界の実検査で拒否する必要がある。
型検査の成功を幾何PASSと呼ばない。
元 `_validate_request` / public transfer / saved replayは変更しておらず、公開版2は現在も拒否する。

| 検査 | 実結果 |
|---|---|
| 先行反例 | 新helper未実装で例の一testがImportError、1 test/4 errors、終了1。元logを保全 |
| 新 test_curved_selection_charts_input | 7個別PASS。正常/拒否例、未知/欠落/版混用、番号、両予算、chart構造/有限/巨大int、raw重複/NaN、旧入力/不変性 |
| 直接消費 test_curved_selection_transfer | 8個別PASS。元対応分割の二policy/非nested/独立番号/対称/保存CLI/型改竄の契約を維持 |
| 選択した実行 | 上記15件、1.761秒、handle53654終了0・OK。fullではない |
| 源/原動作監査 | 元1438対象の変更はselection module一つだけ、新test一つで1439対象/1226 Python源。元1437他源byte一致。新helperを除くmodule AST全体は元archiveと完全一致 |
| 公開能力/監査 | 公開版2は元unknown-key拒否を維持、監査solve guard呼出し0、終了0。幾何版2の実装証拠へ昇格しない |

新FEM/seed/full/GUI/legacy0。既存selection unitはnative幾何を再構築するが固有値を解かない。
入力だけの追加なのでFEM/独立精度validatorを重複実行せず、旧公開動作のAST一致と直接8検査を確認した。
仕様工程で受入済みの独立矩形面積/体積/Hφ=r質量と全有理被覆は同sourceの既存幾何証拠を再利用する。
新外部資料・依存・旧資産参照なし。数学/物理核、元RF定義、選択/停止/保存の閾値は変更していない。

## 再現と証拠

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_curved_selection_charts_input test_curved_selection_transfer
```

rawは `out/n04-selection-charts-input-20261008/`。
`input-red.log`、`input-selected.log`、`audit-input.py` / `audit.log` / `acceptance.json`、
元module archive・受入後module/test archive、1438/1439 source snapshotを保存した。
成功した15件を監査や文書更新のために再実行していない。
次はADD-N04-selection-charts-03。元Case/全P2履歴・対称タグ/源・有理交差の仕様を保持する。

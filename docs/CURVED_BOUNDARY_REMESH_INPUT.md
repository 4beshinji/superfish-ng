# 境界再メッシュ生成版2のstrict入力検査

2026-10-13 JST、ADD-N04-boundary-remesh-02 **DONE**。先行仕様commit `de2afc4`。
[固定仕様](CURVED_BOUNDARY_REMESH_SPEC.md)の九共通項目と一履歴指定を、
`curved_remesh_generation.validate_generation_settings`へ実装した。
全136カードは84 DONE/2 IN_PROGRESS/50 PLANNED、原123は76/2/45。
次は03の実生成。親N04と全goalは継続する。

公開生成器の版1経路は変更していない。新helperは版1/2のstrict検査後に独立なdeepcopyを返す。
版2は`restrict_native_p2`だけを許し、未知/欠落/版混用、bool/floatの整数欄、
非有限/非正のサイズ、0〜60度の開区間外、履歴の欠落/両指定、不正marked選択・patternを拒否する。
元history readerで巨大な角度整数がfloatへ変換できない場合も、専用入口でValueErrorへ変換する。
予算の正整数と一様段数の0以上整数は区別する。任意の小さい上限をmetadataに追加しない。

JSONの全深さの重複キーは元`project.parse_json`が拒否する。
同parserはNaN等をPython値として読むため、数値欄の有限性は新helperと既存history readerで拒否する。
仕様01のparser単体が非有限を拒否するように読めた記述を、この実装上の責務分担へ訂正した。
新しいJSON parserや共通数値readerの変更はない。

元境界区間数と予算、全prefixのサイズ/品質、固定patternと新seedの所有関係は
03の幾何検査に属する。型が正しい二つの拒否例もmetadataは受理し、幾何生成時には拒否が必要。
入力helper成功をメッシュ生成成功へ昇格しない。
公開`generate_curved_remesh_plan`、CLI、GUIはまだ版2を拒否する。

| 検査 | 結果 |
|---|---|
| 先行再現 | 新helper未実装の一test/四例がImportError、終了1。`red.log`を保全 |
| 新入力unit | 9個別PASS。四例/全項目/版/型/有限/両history/frozen deep copy/raw重複/旧契約/公開未接続拒否 |
| 直接消費の旧生成unit | 9個別PASS。独立内部/番号、全境界/Green/既知場質量/尺度、粗化/予算/品質、固定履歴、CLI排他/重複、TE受理を保持 |
| 一回の選択実行 | 計18件、16.186秒、handle71855終了0・OK。意図したCLI拒否のstderrを含む。fullではない |
| 源の監査 | 元1451対象のうちgeneration module一つだけ変更。他1450源byte一致。新helperを除くmodule全ASTは元archiveと一致。新test追加後1452対象 |
| 物理/能力 | 新FEM/seed/full/GUI/legacy0。新公開拒否testはmesherとsolveの呼出し0を確認。元物理核/RF定義/閾値は不変 |

仕様01の矩形/非アフィン全P2制限・独立三積分・粗化/再投影拒否の証拠を再利用する。
入力だけの変更なので専用FEMを重複実行しない。成功した18件も文書/台帳監査のためには再実行しない。
新外部資料・依存・legacy資産参照なし。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync python -m unittest -v test_curved_boundary_remesh_input test_curved_remesh_generation
```

rawは`out/n04-boundary-remesh-input-20261013/`。
開始snapshot、元module、red/selected log、受入後module/testと`acceptance.json`を保持する。
03で版2の実生成を接続する際、今回の「公開未実装拒否」testは接続済みの無求解検査へ更新する。
数学的に別の境界を作る再投影へ切り替えず、元Caseと全P2区間の保持を確認する。

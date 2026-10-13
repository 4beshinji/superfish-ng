# RF-01：validatorのソース前後監査

2026-10-13 JST、[RF-01](REFACTORING_PLAN.md#rf-01) **DONE**。
`scripts/validate.py`は数値/テストを始める前と終端で対象一覧を取り直し、
各ファイルのSHAを比較する。内容変更だけでなく追加・削除も受入不可とする。
元の数値ゲート、CLI引数、テスト/seedの範囲、子プロセスの終了コードとlogを維持する。

対象は従来と同じ`src/tests/scripts/examples`内のファイルで、`__pycache__`は除く。
初回一覧は`source-before.json`へ先に保存し、終端の`source-audit.json`へ
before/after、変更/追加/削除の相対パス、UNCHANGED/CHANGEDを保存する。
同じ情報を`validation.json.source_audit`にも記録し、従来の`source_sha256`は終端一覧として保持する。
終端で読取に失敗した場合はUNAVAILABLE、終端hashと差分をnullにして受入不可とする。
一時的に変更して元へ戻す行為を検知する常時監視ではなく、前後の内容/一覧監査である。

全数値ゲートが通っても監査に差分があれば`passed=false`・非ゼロ終了となる。
子コマンド失敗では元の終了コードを保持し、その後の数値計算は実行しない。
数値処理の例外でも元例外を再送出し、失敗reportと終端監査を残す。
report書込にも失敗した場合は、元例外を置換せず可能なら注記を追加する。
`--skip-tests`はseed-numerics/NOT_RUNと省略項目を維持し、full受入にはしない。
過去の終端hashだけの記録を、新しい前後監査済みの証拠へ変換しない。

## 検証と来歴

rawは`out/rf01-validator-provenance-20261013/`。
製品ツリーを計算中に変更せず、一時fixtureの実Python子プロセスで変更/追加/削除を行った。
数値部分はcontroller専用stubであり、このfixtureのfull/seed表示は物理検証の証拠ではない。
改修前は三つの差分があってもPASS/終了0となり、初回hashや差分が残らないことを再現した。
最初のfixtureではmesh attributeが不足していたため、そのERRORを保存し、
fixtureだけを補って元不具合を再現した。失敗した子/数値例外には終端reportがなかった。

新5＋直接2の7個別unit、0.471秒でPASS。
無変更、実子による内容変更/追加/削除、終了7の子失敗/log保持、
元RuntimeError objectの維持と終端監査、skip-testsを確認した。
直接consumerは並列runnerの失敗/エラー/import/予期しない成功と、異常終了/他module回収。
成功/失敗の報告範囲を確認し、並列runner自体は変更していない。

検証後のCLIエラー文言は元の文字列へ戻しただけで、数値・監査bodyは変えていない。
元/最終CLI登録と、全seed数値bodyのAST一致を記録する。
既存1487対象のうちvalidate以外1486源はbyte不変、新testで最終1488。
新FEM/seed/full/GUI/外部取得/依存/legacyは0。
RF-11のソース前後監査済みseed証拠はその時のvalidator/sourceとして保持する。
新validatorでの実full不変hash記録は、次の共有層の広範統合/節目に一度確認する。
`acceptance.json`へsource・全test/logを束縛し、`commit.json`へコミットを結合する。

計画11枚のうちRF-11/RF-01の2枚を完了。残9枚、配布/統合・既存機能受入と全goalは継続中。
次はRF-09の現行仕様と履歴の整理、その後RF-02→RF-03。

## 2026-10-14 実fullの失敗終端監査

RF-03の初回full（`out/validation-rf03-integration-20261014/`）で、新validatorの実前後監査を確認した。
1492 sourceのbefore/afterは一致し、statusはUNCHANGED、changed/added/deletedはすべて空。
子runnerは2689 test/528 moduleを収集し、8 moduleで2 FAIL/18 ERROR、参照環境/専用native rootによる3 SKIPを記録した。
validatorは元の子終了コード1を返し、passed=false/tests=FAILの終端reportを残した。convergenceとseed求解へ進まなかった。
SKIPはoptional NGSolve参照の2件と、専用の受入済みcircle/TE native rootを要する1件で、追加の機能受入へ数えない。
rawの終端receiptは`out/rf03-lower-helpers-20261013/full-initial-terminal.json`。
これは実ソース監査と失敗伝播の証拠であり、full数値受入ではない。

`test_validation_workflow`の旧「子失敗ならreportなし」という期待値は、RF-01の失敗report保持要件と矛盾していた。
元終了7・seed未実行の検査を保ち、passed=false、full/seedの実scope、FAIL/NOT_RUN、子終了コードとUNCHANGED監査を確認する期待値へ更新した。
隔離した同じ自作sourceで当該4 unitはPASS。製品validatorは変更していない。
58個別の統合追補検査へ束縛した5 sourceを終端後に主ツリーへbyte一致で反映し、成功fullの再検証を次工程に置く。
旧7 unitの受入とstubのfull/seed表示を、新しい実fullの数値成功へ読み替えない。

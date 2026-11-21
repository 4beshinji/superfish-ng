# CLIの構文登録と実行の境界（RF-06）

2026-10-14 **RF-06 DONE**。RF-04/05/08の受入後に検証済みCLIと新コマンドmoduleを主ツリーへ反映した。

最初の対象は`tune-curved-hphi`/`resume-tune-curved-hphi`/`replay-tune-curved-hphi`。
`cli_curved_hphi_tuning.py`が明示した三コマンドの`register_arguments`と`execute`を持つ。
mainは元の順序で登録を呼び、構文解析・操作選択・既存の例外/終了コード変換を担当する。
残る170コマンドは元の処理を維持した。動的なmodule探索は行わず、CLI公開入口
`superfish_ng.cli:main`とpackage entry pointは変えない。

新executeのbodyは元handlerとAST完全一致、mainの他操作/例外境界も対象の呼出分離以外
不変。全173コマンドの引数/action/type/default/必須条件/choices/optionと、順序・整形済み
helpを旧parserと機械比較して完全一致した。既存事前inventoryのCLI source SHAも一致する。

直接`test_interface`、`test_curved_hphi_tuning_cli`、capability inventoryの指定caseを
13個別unit/35.770秒、終了0/PASSで確認した。実run/resume/portable replay、元全RFと
Maxwell相似則、未確認の周波数欠落、終了0/1/2、別物理拒否は旧期待値/許容差を保つ。

旧新mainを同じ入力で13比較し、stdout/stderr/終了コードが一致した。capabilitiesのJSON、
欠落入力/重複JSONキー、旧nativeの完全再生、実既存出力のFileExists拒否を確認し、
TUNED/PAUSED/未確認/各非成功statusの表示と0/1変換も制御した。後者の制御比較を
実FEM成功と呼ばない。元所有artifactの全byteは前後不変、比較scriptの新FEM求解はゼロ。

rawは`out/rf06-cli-20261014/`、rootは`/tmp/superfish-rf06-cli-20261014`。
`cli-compatibility.json`が全parser/AST/実出力比較を束縛する。監査初稿のPath default
直列化不足も保全し、既存inventoryの表現に合わせた。製品CLIや許容差を変更していない。
数値核/schema、stdoutの既存形式、上書き方針、新依存は変更しない。
追加full/seedは行わず、11枚の最終統合で全体fullを行う。

主ツリー反映時に候補の全byteと他1499 sourceの不変を確認した。
`acceptance.json`が13個別unit/全173構文比較/13出力比較と反映前後source・raw SHAを結合する。

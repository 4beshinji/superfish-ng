# RF版5対照：随伴C-call計測と部分保存・資源停止

2026-10-13 JST、`ADD-N04-rf-goal-04` **IN_PROGRESS**。
随伴のfactorizationに続く実SuperLU.solveの費用を観測し、元の数学ソースはbyte単位で維持した。
JSON保存途中の実SIGINT/時間上限/RSS上限でも、完全checkpointと部分ファイルを区別して保持する。
[再開API](CURVED_RF_GOAL_EFFICIENCY_RESUME.md)は、追加nativeが保存済みでもcheckpointが未公開なら、
最後に完全公開されたprefixから続ける。04全体、固定36実行05、GUI/監査06は未完。

## 随伴のC線形solveの観測

`curved_rf_goal_efficiency_observation.observe_adjoint_linear_solves`は、元の随伴関数を呼ぶ
二つの実aliasを一時的に包み、その関数内だけでPythonのC-call profilerを有効にする。
元Python callerのcodeとSuperLU型/solve名を照合し、C-callの開始/戻り/例外を
`adjoint_linear_solve`として既存PhaseRecorderへ記録する。
FEM固有求解や別callerのSuperLU.solveを随伴費用へ混ぜない。
参照準備・全場sampling・保存時はprofilerを有効にしない。
元引数、SuperLU instance、結果、例外objectを変更せず、両aliasとprofilerを復元する。
既存profiler、二重観測、外部による置換を拒否し、外部の置換を上書きしない。

C例外イベントではPython側の例外object/型が取得できないため、費用欄の型は
`C_EXCEPTION_TYPE_UNAVAILABLE`と明示する。元の実例外はそのままcallerへ伝播する。
観測区間にはcallback等の負荷も含む。観測負荷を引いた純粋なC solver時間とは呼ばない。

元の66個の関数bindingは維持し、新記録だけ`observation_schema_version=2`と
明示`observed_c_calls`を持つ。readerはこの宣言を完全照合し、完了した区間では
各factorizationと後続C solveの数・順序・親phase一致も確認する。
版1の元記録も読むが、そこで未計測だったC solveを0回/0秒と推定しない。
途中失敗のC例外費用は失敗記録へ残し、成功した比較の性能値へ混ぜない。

## 完全checkpointだけを公開する保存

`curved_rf_goal_efficiency_io.publish_rf_goal_json`はtargetと同じdirectory内の専用stagingへ
有限JSONを書き、flush/fsync後にno-replace hard linkで公開する。
既存targetは置換しない。正常時だけ自身のstagingを回収する。
失敗/中断時はstagingの部分byteを残し、checkpoint/resultという完成名で公開しない。
電源断まで含むfilesystem全体の耐久性を保証するものではない。

workerのfailureには`active_stage`、正しいevent_index、全試行/完了数、
全保存native path、最後の完全checkpointのpath/SHAとそのlevel_runsを別々に残す。
次nativeとsampleが完成していても、未公開のcheckpointを自動的に採用prefixへ昇格しない。
再開は元failure/実終端processを束縛し、最後の完全checkpointのpath/SHAを照合する。
失敗記録の保存にも失敗した場合は、元例外へ注記して元例外objectを再送出する。
最終resultの公開失敗もこのfailure処理に入る。

## 実検証

rawは`out/n04-rf-goal-cost-failures-20261013/`。
最初のsource変更案は随伴の元SHA検査でFEM前に拒否された。失敗したprocessと初稿を保全し、
数学ソースを元byteへ戻して、上記の外側からの観測を採用した。
全記録を上書きせず、成功した実workerは`runtime/`、最終の限定profiler検証は`scoped/`へ分けた。

球の2個目のcheckpointをJSON書込中に停止させた。nativeは各2回完了し、
元checkpoint-001と全native/sampleを保持、checkpoint-002/resultは未公開、部分JSONはstagingだけに残った。
SIGINT後は元の最初のprefixから1回追加して再開し、全保存再検証も通過した。

| 実ケース | 終端 | 終了code | process wall秒 | 最大RSS byte |
| --- | --- | ---: | ---: | ---: |
| checkpoint書込中SIGINT | PROCESS_FAILED | -2 | 31.031394 | 98136064 |
| 上記prefixから再開/再検証 | PROCESS_EXITED | 0 | 56.198729 | 102342656 |
| 45秒wall上限で書込中停止 | WALL_LIMIT | -15 | 45.064768 | 98086912 |
| 192 MiB上限で書込中停止 | MEMORY_LIMIT | -15 | 31.180262 | 338415616 |

この四processは観測初稿のworker全区間profilerで計測されたため、その元ソースを
`observation-global-tested.py`へ保持している。これらを最終版の性能計測とはしない。
実測後はprofilerを随伴関数内へ限定し、通常時にprofilerが無効であること、alias復元、
元引数/結果/例外、C-callだけの計測を追加unitで確認した。

最終版では、保存長球の80→320棄却→元親から113局所の公開branch全体を、新FEM0で再構築した。
元の完全checkpointと全数値/選択が一致。factorization2回と対応するC solve2回を確認した。
C区間は約5.317e-5/4.505e-5秒、検証processは5.817297秒/最大RSS97161216 byte・終了0。
短い計測値を普遍的な速度・誤差の保証にしない。

実workerの新7nativeについて、元球の同一水準との73個の全native配列・全RFが完全一致した。
Ue/Uhの0.5 Jからの相対差は最大1.333e-15。
unit内の5個の小さいFEM求解はこの7個と別計上する。
独立な全固有空間展開と行列摂動への随伴応答、元gauge、両定義の関係を確認した。
初稿の小関数切出しはASTで元式へ厳密に戻せることを確認し、当該独立検証を再利用した。

重複を除く新8＋直接11の19個別unitを分割PASS。
`observation-tests.log`、`failure-tests.log`の成功6件、`failure-fixture-after.log`、
`c-profile-tests.log`、`c-profile-scoped-tests.log`に証拠を保存した。
先行の未実装/部分JSON公開FAIL、新版観測からC区間を省けたFAIL、Mockの観測属性による
fixture ERROR、最初の参照SHA停止、実prolate probeのMock guard ERRORは保全した。
fixtureは実関数の制御例外へ直し、成功済みのFEMや資源停止を再実行していない。

原1481源のうちworker/reader/resume以外1478はbyte不変、IO/観測/testの新3源で1484。
四つの旧観測版1の全prefix metadataも再確認した。全handleは終端。
`acceptance.json`へ元/最終source・raw SHA・各process・19個別testと残件を束縛し、
`commit.json`へコミットを記録する。外部取得/依存/legacy、seed/full/GUI/固定36実行は0。

## 残る受入

全process/failure manifest、最終result書込を含む外側費用境界、専用CLIが残る。
幾何/追跡予算の非成功停止では、失敗phaseと保存readerの整合、
再開直後に追加eventなしで停止する場合の表現を、
[予算停止の後続検証](CURVED_RF_GOAL_EFFICIENCY_BUDGET.md)で限定受入した。
固定予算での全36実行は後続05であり、異常系注入をその受入へ数えない。
SIGTERM/強制killの一般的な再開は未受入であり、今回の資源停止から自動再開したとは記さない。
全141は91 DONE/3 IN_PROGRESS/47 PLANNED、原123は76/2/45を維持する。

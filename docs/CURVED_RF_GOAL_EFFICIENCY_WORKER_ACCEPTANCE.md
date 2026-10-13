# ADD-N04-rf-goal-04：worker・費用・保存・再開の条件別受入

2026-10-14 JST、**DONE**。固定36実行05とGUI/原条件監査06はPLANNED。
親N04、原互換32要件、全実装計画は未完。

このカードの出口は、固定版5分岐と独立比較の実worker、全event費用、完全保存再生、
失敗/中止・再開、専用CLIの接続である。36行の精度/方式比較、GUIは別カードで監査する。

| 原条件 | 根拠と受入範囲 |
| --- | --- |
| 元固定行/要求・未知/型/予算拒否 | [02の18 unit](CURVED_RF_GOAL_EFFICIENCY_INPUT.md)、worker入力/最終要求再照合。旧N05計画・六要求・全36行は不変 |
| 九量/両次数・採用祖先と非採用probe | [指標の17 unit](CURVED_RF_GOAL_EFFICIENCY_WORKER.md)。元全E/H・物理軸・単一符号・両R/Q・peak両端、三採用祖先/二一様辺、未確認IDを保持 |
| fresh workerと元公開branch一致 | [元12新FEM](CURVED_RF_GOAL_EFFICIENCY_EXECUTION.md)、今回の六ケース初回実行。公開成功と独立精度を区別し、長球の棄却probe/元親localを保持 |
| 全native/mode/RF/全域場・完全再生 | [元12 event/全24 sample・6再hash拒否](CURVED_RF_GOAL_EFFICIENCY_REPLAY.md)。今回も同じ原12 eventを現行数値処理で完全再生、新固有求解0 |
| 実中止/別再開・比較用追加一様確認 | [SIGINT/二段階再開・4 event無中断一致](CURVED_RF_GOAL_EFFICIENCY_RESUME.md)、[TERM/KILLの五再開](CURVED_RF_GOAL_EFFICIENCY_TERMINATION.md)。新checkpoint前の元prefix、以後の最新prefixを区別 |
| factorization/C solve・nested時間 | [実C-callと19 unit](CURVED_RF_GOAL_EFFICIENCY_FAILURES.md)。元数値bodyを維持し、alias/profilerを復元。phase和/包含/排他/UNKNOWNと観測負荷の意味を保持 |
| 部分公開・実wall/RSS停止 | [SIGINT部分書込/45秒wall/192 MiBの実停止](CURVED_RF_GOAL_EFFICIENCY_FAILURES.md)。元完成checkpoint/部分stagingを別保存し、未公開nativeを昇格しない |
| 幾何/追跡予算停止・追加eventなし再開 | [19 unit/3新FEM・四停止再検証](CURVED_RF_GOAL_EFFICIENCY_BUDGET.md)。失敗phase/理由/元秒と終端を保持。幾何4T guardは実行、追跡は制御例外注入の範囲 |
| 専用CLI/全process bundle・最終書込費用 | [起動/再開/再生CLI](CURVED_RF_GOAL_EFFICIENCY_CLI.md)。stdout/stderr、全ローカル完成/部分byte、環境/前後source、実process終端を束縛。結果書込を外側wallへ含め、二重加算しない |
| 一般killのfailure欠落・再開中再kill | [実TERM/KILLと境界検証](CURVED_RF_GOAL_EFFICIENCY_TERMINATION.md)。同じinvocation hash/専用出力・最後の完全journalを照合し、誤行/古いprefix/source差分/非signal終了を拒否 |
| 新旧参照のsource移設/追加archive | [元必須入力とreader由来context](CURVED_RF_GOAL_EFFICIENCY_TERMINATION.md)。全必須SHA・全場を確認し、原journalを変更しない。archiveを実行せず、保存schemaを維持 |

最新rawは `out/n04-rf-goal-termination-20261014/acceptance.json`。
新9を含む52個別unitを分割PASSし、実process新20 FEM、元との187配列/全RF一致、
六ケースの独立尺度則、元12 event/24 sampleの完全再生を確認した。
unit内1小FEMは別scope、原過程のunit/FEMも新実行へ加算しない。

元成功証拠は、変更しない数値bodyのAST、原source同一byte、原input/全配列/全RFへ結合した。
今回のsource変更はbundle移設、signalの所有/履歴検査、必須参照のpath照合と返却context、
不正SHA型の明示拒否である。FEM/場/RF/幾何/指標/停止の式、許容値、mode順とID意味は不変。
元の失敗・棄却・未達・UNKNOWN、表面/固定P2領域の限定保証を保持する。
表中の旧日時の未完記述はその時点の記録で、現行出口は本表とCURRENT/TSVとする。

未実行の05/06、seed/full/Hosted CI/実機・新legacy比較を受入へ足さない。
20の開発求解と六PAUSED初回は固定36計測行の成功や性能優位ではない。
親N04の完了は05/06と原四群の最終照合を待つ。次は **ADD-N04-rf-goal-05**。

# RF版5対照：中断prefixからの再開と追加一様確認

2026-10-13 JST、`ADD-N04-rf-goal-04` **IN_PROGRESS**。
[全保存再検証](CURVED_RF_GOAL_EFFICIENCY_REPLAY.md)を再開前に必須とし、
元の保存prefixを保持した別出力先へ続けるAPIを追加した。
公開RF成功後の比較専用一様確認も、元checkpointを凍結して実行する。
固定36実行の無中断計測とは別の開発検証である。
[C-call計測/部分保存/実wall・RSS停止](CURVED_RF_GOAL_EFFICIENCY_FAILURES.md)も後続で限定受入した。
[予算停止の保存整合と追加求解ゼロの再開](CURVED_RF_GOAL_EFFICIENCY_BUDGET.md)も後続で限定受入した。
04の全process/failure manifest・専用CLI・一般kill再開と、05/06・親N04は未完。

## 入口と不変条件

`curved_rf_goal_efficiency_resume.resume_curved_rf_goal_efficiency_worker(path, directory, *,
expected_sha256, bindings=None, implementation_aliases=None, implementation_archives=None, interruption_files=None,
max_new_events=None, submission_origin=None)`を使う。
元journalのSHA、元の全native/参照/全場/親連鎖/停止判断を検証してから新FEMへ進む。
元比較判定がPAUSEDで、元event予算に余りがある場合だけ受け付ける。
新outputは存在しないdirectoryに限定し、既存出力を上書きしない。
`max_new_events`は今回だけの追加数であり、元max_levelsを拡大しない。

新規実行と再開は同じ`_execute_worker_events`の数値ループを使う。
元全event、棄却event、全mode、全場sample、誤差、採用親、元費用をprefixとしてコピーし、
初期Case/source、要求、規格化、求積、物理閾値を変更しない。
公開PAUSEDなら元公開engineで全prefixから次計画を再構築する。
一様対照または公開TARGETS_METの場合は最後の採用場の元P2一様制限を作る。
公開成功checkpointを再開/書換えせず、追加eventは`benchmark_confirmation`として別に保存する。

保存schema2は元schema1の全科学記録に`resume_origin`を加える。
originは原journalのpath/SHA、event_count、元実装alias、中断fileのpath/SHAを持つ。
readerはoriginを再帰的に完全再検証し、五つのprefix配列を原文書と厳密照合する。
各originは現在より短いprefixでなければならず、無限の親連鎖や同一長の自己参照を受理しない。
元完成状態の変更、元event/元費用の書換え、親要求/独立参照の変更を拒否する。
再開後も元束縛fileを最終再hashし、読取中の原データ変更を検出する。

`implementation_archives`は元SHA256から同一byte archiveの絶対pathへの写像である。
同じファイル名でも区間ごとに実装版が異なるため、SHA別に指定して親連鎖へ引き継ぐ。
各archiveを全byte検証し、実行しない。任意に作った別実装を元実装として受け入れない。
再開originへもこの写像を保存する。従来のschema1とarchive項目なしのschema2を読み続けられる。

## 中断と費用の扱い

完成した開発PAUSED結果からは、その元費用記録を保持して続けられる。
途中checkpointからは、元directoryの`failure.json`と実測supervisorの終端`process.json`を
`interruption_files`にSHA付きで渡す。現在の再開対象は実KeyboardInterruptである。
元の成功prefix、試行/完了数、部分費用、非ゼロ終了のPROCESS_FAILEDを必須にする。
強制killによる部分保存や資源停止一般の再開を、この受入へ含めない。

費用は各呼出しの別区間で測る。原prefix秒数を加算し直したり、新時計で置換したりしない。
新しいrecorder wallは元prefixの完全再検証、参照検査、再開計画、追加native、保存を含む。
readerは原区間を原文書で、新区間を追加eventだけで検証し、時計の再始動を単調性違反としない。
保存履歴のnative_solves_attempted/completedは成功prefixと当該呼出しの追加試行に対応する。
過去の中断試行は原failure側に別途残し、全実測の集計時に落とさない。
後処理の保存再検証費用と、新FEM worker自体の費用も分けて記録する。

## 開発検証の証拠

rawは`out/n04-rf-goal-resume-20261013/`。
独立不変量は元全蓄積エネルギー1 JでのUe=Uh=0.5 J、両R/Qの2倍関係、
球の独立解析場/RFの元ゲート、同一入力の無中断/再開における全係数・全sample・全RF一致である。
小さい代数残差だけを離散化精度の受入へ使わない。

実SIGINTは2回目のnative.solve内部へ送り、1回完了/2回試行で中断した。
元checkpoint-001から1event追加してPAUSED、さらに同じ保存readerを通して2event追加した。
3個の公開eventの後に比較専用の4個目が入り、実祖先1→2→3で独立精度と二一様辺が通った。
元の初回独立達成1、確認達成3を別々に保存する。
元球三方式の3event保存結果からも各1event追加し、公開checkpointの凍結と一様対照を確認する。
無中断freshも同じ4eventを実行して比較する。

長球は元320要素の棄却probeまでを公開engineで再構築し、次solveに渡すCase/sourceを
元80要素から作った保存済み113要素のrf_localと照合する。
この計画検査はsolve直前に制御例外で止め、新しい固有値問題は実行しない。
新規の長球中断系列や独立物理検証とは区別する。

最終数値・source/全束縛監査・個別test一覧は同directoryの`acceptance.json`に保存する。
未実装ImportError、中断traceback、部分費用、制御例外を成功ログで上書きしない。
新しい文献・外部取得・依存・legacy利用はない。seed/full/GUI/固定36実行は本工程で行わない。

## 実測結果と検査範囲

新nativeは11回完了、これとは別にSIGINTで中断した1回の試行を保持した。
下表のprocess wallは開発probeのworkerと、その後の完全保存再検証を含む。
worker自身の観測wallも別欄に保存する。固定36実行の性能値へ流用しない。

| 実行 | 追加完了native | process wall秒 | worker wall秒 | 最大RSS byte |
| --- | ---: | ---: | ---: | ---: |
| 実SIGINT | 1（別に中断1） | 7.069172 | 元failureに部分費用 | 97144832 |
| checkpointから1event再開 | 1 | 35.744567 | 17.549395 | 102207488 |
| 再開結果からさらに2event | 2 | 112.392840 | 58.675168 | 123047936 |
| 元rf_goalの追加確認 | 1 | 104.419724 | 50.173456 | 122998784 |
| 元uniformの追加確認 | 1 | 91.542313 | 41.613139 | 122228736 |
| 元uniform_when_rf_passesの追加確認 | 1 | 105.026257 | 50.488928 | 122974208 |
| 無中断fresh | 4 | 82.066456 | 45.590741 | 122691584 |

SIGINTは終了-2、他六processは終了0。最初の再開はPAUSED、そのほかの完了結果は
独立初回達成1/確認達成3のTARGETS_MET。元公開RFは3eventのまま保持した。
再開系列と三継続系列を無中断freshへ照合し、164個のnative配列と64個のsample配列、
全RF・全独立誤差・採用祖先判定が完全一致した。Ue/Uhの0.5 Jからの相対差は最大3.442e-15。
全1,680束縛fileを再hashし、原データを維持した。

`input-tests.log`の8件と`origin-tests.log`の2件がPASS。
後の非object拒否/版別archiveの1新testと直接消費先を`archive-guards-after.log`の3件で確認する。
重複を除く新4＋直接7の11個別unitである。先行のImportErrorと非object/未実装archiveのERRORも保全。
全native成功後の変更は原本・型・archiveの検査/伝播だけで、数値ループ/場指標/費用算術は不変。
この変更についてだけ、実archiveを指定した元1eventと再開2eventを新FEM0で完全再検証する。
最終sourceと元native成功時のsourceの対応は`final-source-binding.json`に保存する。

原1479源のうちworker/reader以外1477はbyte不変、resume/testを加えて1481源。
全141は91 DONE/3 IN_PROGRESS/47 PLANNED、原123は76/2/45のまま。
04の残件には資源停止・部分書込の範囲も残す。中断/継続の限定受入を04全体の完了とはしない。

# N06：新プロセスの費用・資源停止

2026-10-07、N06の外側実行器だけを限定受入する。N06はIN_PROGRESS。
先行は[N05の固定比較条件](N05_ADAPTIVE_EFFICIENCY_PLAN.md)。
主N03の全検証中は1405対象ファイルを固定し、実装/検査は別ツリーで行った。
FEM・既存保存形式・数値合格条件は変更しない。12回の比較計算は未実施。

`adaptive_efficiency_process.run_measured_process` はargvからshellを介さず
Linuxの新プロセスを起動し、新しい出力ディレクトリに要求、stdout/stderr、終端記録を残す。
既存出力は起動前に拒否する。既定は3600秒、32 GiB、50 ms間隔、TERM猶予0.5秒。
予算/argv/作業ディレクトリ/実行環境の不正は出力の予約前に拒否する。

壁時計にはプロセス起動/import・ログ出力・停止/回収が含まれる。
段階のinclusive/exclusive秒や別の参照準備秒とは別の計測であり、二重加算しない。
Linux `/proc` のworker VmHWMを標本化し、超過を検出したら専用process groupへTERM、
猶予後にKILLし、元workerをwait4で回収する。壁時計超過も同じ停止経路を使用する。
RSS標本間の一時超過は終端wait4の実high-water値で再判定する。
標本化した停止であり、常時32 GiB以下を保証するhard capとは呼ばない。
単一workerとそのthreadのRSSを対象にする。子孫の同時RSS合計は計測しない。
benchmark worker自身が全処理を終えてから退出する必要があり、退出後にgroupが
残った場合は停止してPROCESS_TREE_UNVERIFIEDとする。

退出コード0は数値合格ではない。終端RSSで超過がわかればMEMORY_LIMIT、
RSS欠測はUNKNOWN/nullおよびMEMORY_UNVERIFIEDを維持する。
時間超過時にworkerのTERM handlerが正常退出してもWALL_LIMITを維持する。
元worker失敗・起動失敗・KeyboardInterruptの退出/例外型、費用、ログを残す。
監督側の元例外はworker回収と終端記録の後に再送出する。
将来の専用validatorはこれらの非成功を物理精度達成へ集計しない。

## 検査と適用範囲

未実装moduleのImportErrorをbaselineとして保存した。
初稿8unitは0.587秒/PASS。その後、欠測メモリの非成功条件とgroup/起動失敗の
反例を追加し、共有終了経路の最終10個別unitを1.037秒・終了0で確認した。
反復分を別の個別件数へ加えない。

実Python子プロセスのstdout/stderr/退出7、独立のgetrusage高水位との一致方向、
既存出力のbyte不変、SIGTERMを無視するworkerの強制停止/回収、
実128 MiB allocationの96 MiB超過停止、live欠測時のwait4超過、
全メモリ欠測のnull/非成功、元中断の再送出、workerと実子孫へのgroup停止と
worker自身による子孫回収、起動失敗/不正予算の保全を確認した。
PIDは各検査後にwait不能かつ/procから消失している。FEMの物理検査ではない。

`uv run --no-sync python -m unittest -v test_adaptive_efficiency_process` を
tempの明示PYTHONPATHで実行した。元1200 Python源はmainと全byte一致を維持する。
計測器の既存7unitを再実行せず、その元証拠と実参照consumerを再利用した。
rawは `out/n06-cost-recording-20261007/process-runner-*.log` と
`process-runner-acceptance.json`。新FEM/seed/full/GUI/12benchmarkは0。

Linux以外は実行前に非対応として拒否する。主公開経路への統合、共通初期入力、
全段階の計測接続、量別参照精度・二回全域確認、二反復/三ケースの実比較は後続。
この限定受入でN06カードや全goalを閉じない。

# N06：重複を避ける段階費用の記録器

2026-10-08 JST：N03全validate/別seed207量の終端監査後、費用記録器・process停止器・
固定入力計画・call観測の四moduleと四test、丸め二入力をtemp commit371b800と
同byteで主ツリーへ統合した。元1405対象源は全byte不変、新1415対象/1208 Python源。
新八Python源は四module/28個別unitの別証拠を使用し、同byteの統合で再実行しない。
N03の2485/499 fullは追加前1405源に限る。統合だけの新FEM/seed/full/12benchmarkは0。
N06はIN_PROGRESS、実uniform/adaptive worker・全物理精度/費用比較は後続。
rawは `out/n06-cost-recording-20261007/main-foundation-integration.json`。
以下の「主統合待ち」は日付付き履歴として読む。

2026-10-07。N06はIN_PROGRESS、[N05の固定比較仕様](N05_ADAPTIVE_EFFICIENCY_PLAN.md)を先行とする。
最初の範囲は費用記録器だけ。物理ケース実行・独立精度/費用比較・N06全受入は後続。
N03全validate handle64569の主1405対象ファイルを固定したまま、
別ツリー `/tmp/superfish-ng-n06-cost-recording-20261007` で実装/検査した。
主公開APIにはまだ統合していない。

新 `adaptive_efficiency_timing.PhaseRecorder` はserialなstageのinclusive/exclusive秒を保存する。
直接の子stageの費用を親のinclusiveから引き、root stageだけを全体の記録秒へ加える。
clockの保存二進値をFractionで差分/配分し、重複加算や負の時間を認めない。
全clock区間からrootの区間を引いた未配賦秒も別欄に残す。
並行スレッドを誤って子stageにしないため、元thread以外の操作は記録前に拒否する。
記録範囲のCOMPLETEは数値合格や効率改善を意味しない。

元solver失敗やKeyboardInterruptは型/観測秒を保存して元例外を再送出する。
時計が非有限/逆行/欠測ならTIMING_UNVERIFIED、該当秒はnull。
時計の失敗で元のsolver例外を隠さない。開いたstageや未finishを成功にしない。
finish後は同じ記録をコピーして返し、後続stage/外部改変を拒否する。
Linuxのprocess-lifetime peak RSSをbytesで保存し、未知platform・不正/欠測readerは
UNKNOWN/nullを保持する。メモリの欠測を0へ換算しない。

この記録器の時計はそのlifetimeだけを覆う。
新プロセス開始/importを含む全体時間、別参照の準備費用、実壁時計/メモリ上限の中止は
N06の外側runnerで同じ境界に接続する必要がある。stage観測だけで予算執行済みと呼ばない。
solver/追跡/RF/選択核の数値・保存形式を変更していない。

## 検査と来歴

新7個別unitは最終源で0.002秒・終了0/PASS。
独立に18秒の時計区間を設定し、root=12秒、子=3/5秒、親exclusive=4秒、
未配賦=6秒、exclusive合計＋未配賦=18秒を確認した。
これは時計配分の数学的検査であり、FEMの実測秒ではない。
実例外/中断、開いたstage、元例外＋時計逆行、非有限時計、未知RSS、
完成後コピー/禁止、foreign threadの無配賦を確認した。

baselineは未実装moduleのImportErrorを保全した。
初稿の新6unit PASS後、serial thread条件を明示して所有反例を追加し、
共有入口の変更に対する最終7unitを実行した。重複分を別の個別検査数へ加算しない。
コマンドはmainのuv環境とtempの明示PYTHONPATHで
`python -m unittest -v test_adaptive_efficiency_timing`。
rawは `out/n06-cost-recording-20261007/`。元1200 Python源は全byte一致を保持し、
tempの新二源を含む1202源を固定した。主全validateの1405対象源も不変。
新FEM/seed/full/GUI/効率benchmarkは0。N03の全validateは別実行中である。

主数値ジョブ終端後に同一byteで統合し、専用validatorの入力/共通初期領域・
物理参照・選択/全域確認・全stage計測/予算・保存へ接続する。
12実行の実精度/費用と失敗保全が揃うまでN06を閉じない。

外側の[新プロセス費用・時間/RSS超過の停止器](N06_PROCESS_SUPERVISOR.md)も
別ツリーで限定受入した。計測器の元二源は変更せず、主統合は全検証終端後に行う。
[共通初期入力・交替12行の実行前計画](N06_FIXED_EXECUTION_PLAN.md)も同じ別ツリーで
限定受入した。入力の段階であり、数値実行/精度/効率の受入へ数えない。
[serial呼出しの観測接続](N06_CALL_OBSERVATION.md)は元の引数/結果/例外を保持して
別ツリーで限定受入した。実workerの全stage接続は後続である。

## 独立丸め参照の共有準備

受入済みN03丸め参照のGauss16/24（全22528/50688体積点＋物理軸）を、
全三h水準/全五モードを保持した二つのNPZへ詰め替えた。
元N03のコンパクト報告/元全field報告の一致、1199源（変更前三源はarchiveへ明示解決）、
全bound入力/現代参照byte、元fieldsの名前/順序/単位を確認した。
元参照読み手と完全AST一致の関数で、実保存NG fieldsを96空間点/480場vectorで再評価し、
元診断値と全成分の**完全一致**を確認した。NPZはallow_pickle=Falseで全配列を
再読込して元値と完全一致。標本削除・係数/規格化/閾値変更はない。

これは新固有値求解0・新全grid場標本0の共有参照準備で、12native benchmarkには数えない。
旧の有限Gauss診断の適用範囲/元reference選択IDをそのまま保持し、
新しい連続誤差やpeak認証を作らない。N06の実native経路への接続は未実施。
計測器の実consumerとしてrecorder-lifetimeは4.562449秒、process peak RSSは1340436480 bytes。
この秒には既に済んだimport/過去参照求解を含めず、外側/共有費用として別に計測/記録する。
Matplotlib importは書込不能の既定cacheから一時/tmpへfallbackした旨の元logを保持した。
主1405源とtemp計測器は前後不変、元7unitの後のsource変更/反復はない。
rawは `rounded-reference-grid/manifest.json`、二NPZ、`reference-grid-export-acceptance.json`。

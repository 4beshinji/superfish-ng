# N06：重複を避ける段階費用の記録器

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

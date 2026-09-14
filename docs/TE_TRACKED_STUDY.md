# TE逐次・適応Studyのnative読取

2026-09-15 JST。TEアフィンStudyの後続として、保存検証を実行中の逐次/適応Studyへ接続する。
受入条件は、実TE計算の停止・再開、EφによるID継承、完了済み点の非再計算、
変更された保存場の拒否、適応追跡不成立時の停止、および独立Maxwell尺度則の保持。

最初のTE点は計算できても、`tracked_study._point_sources` がTM専用`read_solution`を呼ぶため
チェックポイントを保存できなかった。修正前の実計算で再現した（baseline.log、1件3.637秒、ERROR）。
Project偏波に応じて正式な`read_te_run`へ分岐する。絶対パス/非symlink制限、Job完了、
宣言Project一致、読取前後の全ファイルhash照合はそのまま保持する。TMの読取処理も保持する。
適応Studyは同じ検証関数を利用するため、この接続を共有する。FEM・追跡積分・閾値は変更しない。

## 検証

生記録は `out/te-tracked-study-20260915/`。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=tests:src .venv/bin/python -m unittest \
 test_te_tracked_study test_tracked_study test_adaptive_study \
 test_tracked_study_jobs test_adaptive_study_jobs
```

新2件を含む24件、76.496秒PASS。TE逐次の1点停止/残り1点だけの再計算/保存再生/場改変拒否、
半径だけを変形するTE適応追跡の不成立と最大深さ停止、既存TM実行/workerの直接利用先を確認。
独立検査は、倍寸でfが1/2、固定エネルギーの係数が2^(-5/2)、Gが不変、両R/QがN/Aであること。
全suite/seedは再実行していない。今回の変更範囲は保存読取の偏波分岐であり、共通FEMは不変。

CLIでも逐次実行を1点で停止して別ディレクトリへ再開し、COMPLETEを確認した。
2組のnative保存配列と全RF値は、既存の独立TE Studyの同一点と完全一致した。
全要素重心のEφ/Hr/Hzについて倍寸時2^(-3/2)則の最大相対差8.990e-15。
この尺度検査は離散化誤差・ピーク精度や連続物理分枝の保証ではない。

適応CLIでは半径だけを変形し、minimum_overlap=0.999、max_depth=6、max_attempts=32を固定。
粗い区間がBISECTとなった1回目で停止し、別ディレクトリに再開した。
10点・17試行（BISECT 8、ACCEPT 9）で元の終点へ到達してCOMPLETE、終了0。
最初の2点を再利用して中点8点を追加した。逐次2点と合わせ専用12実FEMである。
初回不成立や途中のBISECTを捨てず、閾値・元要求・個別IDを保持する。
この17試行は全てサンプル間の対応であり、連続分枝や数値収束を認証しない。
全17試行を保存解から再構築する最終検証もPASS、終了0。
初回2点の完全なレコード一致、再開先にそれらの再計算がないこと、全比較のEφ指定と
閾値0.999、最終ID、読取前後165ファイルのhash一致を確認した（acceptance.json）。
追加FEMなしの保存再生にも数分を要した。全履歴の再構築コストは今後の改善対象として残る。
全実行handleは終端を回収済み。

## 残件と出典

実GUIでの逐次/適応TE計算、その他のTE形状/対称セクター/個別ID回復への実経路照合は後続。
既存TM GUI/workerの成功をTE GUIの検証実績として数えない。
TE版8・曲線対称/鏡映・未接続物理とD03も保持し、親D02と全計画goalは継続する。
親33=10受入/16進行/6他未受入/1範囲外。
既存TE native保存契約と公開Maxwell尺度則を再利用し、新規資料・依存・旧ソルバー参照はない。

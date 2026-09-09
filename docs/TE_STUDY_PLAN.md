# TE Studyの接続計画と一時コピー検証

2026-09-09。主ツリーの円筒TE追跡を検証している間の後続工程。
以下は一時コピーの候補であり、主ツリーのTE Study対応を意味しない。

## 接続する契約

最初に独立パラメータ掃引を接続する。全点のProjectを先に検証し、各点は通常TE FEMとnative保存を使う。
掃引の計算完了は収束合格やモード追跡合格ではない。独立スペクトルのnumerical_statusはUNVERIFIED。
追跡は完了した全点の入力・nativeを再検証した別操作とし、円筒以外のTE写像は拒否する。
軸加速量とR/Qはnull/N/A理由を保持し、表示時に0へ変換しない。

収束Studyは別工程。現在のcompare_refinementはTM専用であり、全TE拒否を取り除くだけでは対応にならない。
TEの場比較・RF量・縮退/順位の意味・同一物理条件・幾何誤差と離散化誤差の区別を確定してから接続する。
曲線/外部meshの掃引には元meshの変換規約が必要。既存の未対応変換を黙認しない。

## 一時コピーで判明した接続箇所

- studies.py: TE全拒否、execute_studyのTM reader、case hash、TE表面ピーク未評価の表示。
- study_mode_tracking.py: 点ごとのTM readerをTE native完全再検証へ分岐し、要約/Case/Projectとの一致を照合。
- web/app.js: Study表のNumber(null)による誤ったR/Q=0表示をN/A理由へ変更。
- web/index.html: パラメータ掃引の対応と収束Studyの未対応を分ける説明。

コピーは `/tmp/superfish-te-study-candidate-20260909`。
最新4ファイルの差分は `out/te-study-gui-candidate-20260909/candidate.patch`。
適用前に主ツリーの最新差分と照合すること。主ツリーの追跡検証対象452ファイルは変更していない。

## 現在の証拠

| 候補検証 | 結果 | 証拠 |
|---|---|---|
| 2点掃引/6モードと追跡 | PASS、最大周波数解析相対差5.598e-6、R/Q N/A、独立スペクトルUNVERIFIED、別途追跡PASS | te-study-tracking-candidate-20260909、82377終了0 |
| 実worker中止・小さい2点掃引・管理器再起動 | PASS、保存追跡/replay一致 | te-study-worker-candidate-20260909、44311終了0 |
| GUI実計算・全R/Q N/A・点の保存場取込 | Chrome2項目PASS、配信した一時コピーhash前後一致、外部要求0、画面目視 | browser-te-study-candidate-20260909、69859終了0 |
| strict入力・保存要約改変 | PASS、未対応収束/後続の不正値を拒否、N/Aを0へ改変しouter hash更新後もnative要約照合で拒否、復元後PASS | te-study-integrity-candidate-20260909、75271終了0 |

out名はいずれも無視対象のローカル証拠を指す。中止した実行は完成FEM数に数えない。
初回NumPy scalar入力のstrict拒否と、次の試行の追跡TM reader拒否も失敗log/driverを保持している。
候補GUIサーバー38921/PID940536はSIGINT終了0、候補の全実行は終了済み。

## 主ツリーで必要な受入

1. 円筒TE追跡の最終標準・回帰・コミットを先に確定する。
2. 候補を主ツリーへ適用し、API/CLI/worker/GUIのTE掃引を、改変・中止・再起動・N/A理由と合わせて再検証する。
3. P1/P2・両尺度、RF規格化掃引などで独立不変量を確認し、各点・各順位を勝手に個別IDへ読み替えない。
4. 旧TM Study/追跡書式と結果、標準周波数/RF、検証前後sourceを確認する。
5. README/対応表/計画/実装状況・物理モデル・来歴を限定対応へ更新し、ローカルコミットする。

新規物理式・外部資料・依存はない。候補の合格を製品受入や全Study対応の代わりにしない。

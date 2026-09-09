# TE独立掃引の仕様・受入と後続計画

2026-09-09。主ツリーの円筒TE追跡を検証している間の後続工程。
独立掃引を主ツリーへ接続し、限定受入を完了。収束Studyは後続工程。以下の一時コピー検証は予備証拠として区別する。

標準48904・最終比較22868はともに終了0。775件中773合格・2skip（unittest1179.803秒、command1180.149秒）。TM seed9モード19量の周波数差0、RF/エネルギー最大相対差8.882e-16、旧TE保存7件差0。標準・独立・GUI・固定時・終了後455対象hashを照合し一致。out/validation-te-study-20260909に全ログ・比較driver・source-fixed.json・seed_regression.jsonを保持。

最終独立18FEM、GUI2項目、CLI/GUI全保存一致、実worker中止/完了/再起動、旧TM Study3件/追跡完全一致を確認。全関連実行は終了しソース固定を解除。

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

## 主ツリーの受入手順（独立掃引について完了）

1. 円筒TE追跡の最終標準・回帰・コミットを先に確定する。
2. 候補を主ツリーへ適用し、API/CLI/worker/GUIのTE掃引を、改変・中止・再起動・N/A理由と合わせて再検証する。
3. P1/P2・両尺度、RF規格化掃引などで独立不変量を確認し、各点・各順位を勝手に個別IDへ読み替えない。
4. 旧TM Study/追跡書式と結果、標準周波数/RF、検証前後sourceを確認する。
5. README/対応表/計画/実装状況・物理モデル・来歴を限定対応へ更新し、ローカルコミットする。

新規物理式・外部資料・依存はない。候補の合格を製品受入や全Study対応の代わりにしない。

## 主ツリー接続中（基準324dc20）

studies/study_mode_trackingのTE分岐、GUIのN/A理由表示、対応範囲説明を適用。
追加4unitは0.8秒程度でPASS。初回の保存係数属性名のテスト誤りを修正し、失敗ログもout/te-study-development-20260909に保持。既存TE Job8件もPASS。
実worker中止・2点完了・管理器再起動・Study追跡/replayはout/te-study-worker-product-20260909でPASS（18173終了0）。
独立検証初回はP1 nr64/nz96の高位モード周波数相対差最大0.00109154が条件0.0008を超えてFAIL。条件を維持しP1のみnr96/nz144へ細分した。初回driver/logをout/te-study-independent-20260909に保持。
再実行62766はout/te-study-independent-refined-20260909、log /tmp/te-study-independent-refined-20260909.log。独立検証中はソース変更を保留。最終GUI・標準・回帰・文書確定・コミットは未完了。

最終統合進捗: 細分後62766は16FEM/P1P2/両尺度/規格化でPASS。最終ID順序検査を追加し4976で再検証中、標準48904も実行中、455source固定。Chrome12749終了0（fresh-final out）でN/A/点取込PASS・目視、GUI独立12518で管理器再起動2件・CLI/GUI全保存結果一致・追跡replayPASS。初回最終Chromeは既存Job選択でtimeoutし、新workspaceで再検証した。全GUIサーバーは停止済み。詳細なhandleと残作業は最新引継ぎを参照。

最終独立4976は終了0。16FEM・解析ID順序・両尺度・規格化・CLI追跡/replay4組がPASS、455source一致。標準48904は引き続き実行中。

[後続のTE収束Study設計](TE_CONVERGENCE_STUDY_PLAN.md)に、TM専用比較の不適合箇所とTEの場/RF/幾何別の受入条件を整理した。設計段階であり収束Studyの実装完了ではない。

追加曲線TE掃引6889終了0、out/te-study-curved-independent-20260909/verify.py/command.log/report.json。球形P2の2FEMで規格化振幅・損失比例/f,G,Q不変・N/A維持・未対応円筒追跡拒否PASS、455source一致。最終比較driverへ証拠照合を追加。README/対応表/計画/実装状況と物理/来歴に掃引の接続・標準待機状態を追記済み。後続docs/TE_CONVERGENCE_STUDY_PLAN.mdは設計のみ。標準48904は引き続きpollする。

旧TM保存Studyの追加照合84108終了0。out/te-study-development-20260909/verify_old_studies.py/old_studies.log/old_studies.jsonに保持。固定曲線3水準と明示元mesh P1/P2の計3Studyで全細分比較が保存時と完全一致、旧曲線Study追跡文書のfull replayも完全一致。最終比較driverにこの証拠も要求する。

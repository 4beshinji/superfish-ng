# N08：公開適応・保存・GUIの受入と親N04の残件

2026-10-08 JST、N08 **DONE**。実測した三形状の六adaptive系列を、変更していない公開
エンジンから再構築し、30水準の選択・追跡・RF・表面量・求積と公開保存readerの全出力を照合した。
現行GUIは直線19/曲線11の計30操作を確認した。親N04は **IN_PROGRESS**。
原123カードは76 DONE/2 IN_PROGRESS（H17/C07-planar）/45 PLANNED。
既存残件を実行可能な仕様工程にした追加3カードはPLANNEDで、台帳全126は76/2/48。
原互換32要件・全goalは継続する。次は[初期接続が異なる選択移送の仕様](N04_REMAINING_CARDS.md#add-n04-selection-charts-01)。

## 原カードの条件別判定

| 条件 | 確認した結果 | 限界・親の扱い |
|---|---|---|
| 対象量の精度、費用、全域確認 | N05の元三形状/量別閾値、N06固定12実行、N07の全場・900量別誤差・546 native/100 NPZ前後一致を再利用。束縛1747入力とN07元795出力を終端後に再hash | 有限参照格子・固定P2領域の経験的確認。誤差上界null |
| 選択・停止と保存の一致 | 公開 `_assemble` と `read_adaptive_refinement` が六系列/30水準を再構築。元public行の全量・選択・実ID・追跡・表面・曲線求積は専用worker行と完全一致。readerの全文書も完全一致 | workerの余分な参照/費用metadataを公開保存へコピーしていない |
| 元要求による再開・実中止 | 現行ブラウザーで生存中ジョブを中止し、部分checkpointを読込み、元要求の新ジョブで追加水準へ再開。祖先native保持・再起動はbyte不変の元unit証拠にも結合 | cancelledと数値未達とJob completeを別状態で確認 |
| 上限・未達を成功と区別 | LEVEL_LIMIT、UNVERIFIED、QUADRATURE_UNVERIFIED、未解決IDの場/再開無効、改変拒否を実GUIで確認 | 誤差上界や未評価の表面peakを成功へ変更していない |
| 旧履歴・選択移送・大規模表示 | 元N03全1405源の現行byte一致、下記66個別unitと歴史文書の適用範囲を照合 | 現行30操作は大規模250000描画の再試験ではない。非対応初期分割への選択移送と境界分割変更の生成は残る |
| 改善・悪化、親N04採否 | 円筒/丸めは一様、今回の球は適応が有利。旧球の非優位・円筒費用/RSS微増も保持 | N08の監査を受入。親N04は残件3仕様カードの後続独立受入まで閉じない |

## 公開保存の実再構築

開始commit `7f2e435`、全1432対象源/1225 Python源を実行中・終端後に固定した。
N07で受入済みの元nativeを読み、公開schema3（円筒）/4（球・丸め）自身のcheckpointを
排他的に新outへ作成した。元Case/source/P2、U=1 J、beta=1、sigma=5.8e7 S/m、
両R/Q、実個別ID、元f/RF/表面/求積の閾値・品質/上限を変更していない。
六系列すべてTARGETS_MET、各5水準、can_resume=false、physical_error_bound=null。
再構築した品質も公開engineの出力で、専用workerにない品質記録を捏造して比較していない。

| 系列（二反復） | 元公開再構築 [s] | 元公開reader/replay [s] |
|---|---|---|
| 円筒 | 1.310 / 1.319 | 1.320 / 1.322 |
| 球 | 16.400 / 16.563 | 16.444 / 16.574 |
| 丸め二ローブ | 341.642 / 359.524 | 342.856 / 420.663 |

全工程1536.589秒、handle95971終了0。solver.solve/_solve/eigshと両適応moduleのsolveを
例外guardし、全呼出し0、新固有値求解0。保存場からの行列/RF/追跡再評価は実行した。
独立参照の新全場NPZ生成は0。元nativeの全hashは再構築前後一致した。
この時間は新しい公開保存再生の費用で、N07の専用診断高速化の測定へ混ぜない。

## 現行GUIの実操作と失敗の保全

過去のブラウザー実行から公開GUI源に差があったため、専用localhostサーバーと
使い捨てChromeで追加確認した。既存 `verify_gui_curved_adaptive.mjs` は変更なし。
直線検証器のignoredコピーでは、既定schema3に対し、元検査が対象とするschema2を明示した。
最初の直線実行は11操作成功後、説明文の厳密比較で終了1。
元期待 `表面ピーク: 未評価。物理誤差上界: なし` に対し、現行は状態を含む
`表面ピーク: 未評価 (UNASSESSED)。物理誤差上界: なし` だった。
製品や数値閾値を変えず、既に完成したジョブを使う続行検証器で、実保存状態UNASSESSEDと
元三RFゲート・両区間・誤差上界なしを検査した。残り8操作が終了0で通った。
最初の失敗report自体をPASSにしていない。完了済み4+1水準の求解を繰り返していない。

直線11+8操作には、厳密raw入力・重複キー事前拒否、PAUSED→元要求でTARGETS_MET、
全checkpointの保存/再読込、追跡第二modeの場表示、未解決ID/上限表示、実中止再開、
旧版1の局所指標表示を含む。操作fixtureのRF閾値は元0.01/0.1/0.1のまま。
この第二modeのGUI確認をN05の物理精度の証拠には使わない。
物理精度はN06/N07の元fundamental/独立参照と今回の公開保存再構築で別に確認する。

曲線11操作には、元schema4の五量/求積・corner定義、元品質/求積を復元した再開、
二uniform区間のTARGETS_MET、保存/改変拒否/場表示、実QUADRATURE_UNVERIFIED、
今回作成した円筒schema3保存を開いた後の曲線求積表クリアと直線表復元を含む。
元球fixtureのf=1e-4、両R/Q/G=0.005を維持した。
直線/曲線の確認画面を目視し、ゲート/履歴表と未評価表示を確認した。

すべて外部HTTP要求0。成功側のbrowser source snapshotは実行中不変で現行と一致。
最初の失敗reportには終端source snapshotがないため、その前snapshot、続行の前後snapshotと
全1432源の実行前後固定を結合し、この欠測も記録した。
12 GUIジョブは11 complete/1 cancelled（10適応/2場取込）。未完了ジョブ0。
中止ジョブは実経過1.610秒、元完成checkpointから別ジョブへ再開した。
GUIは実求解を伴う。中止時に試行中だった求解を含む正確な新求解総数は計測しておらず、
公開保存監査の「新FEM0」をGUI全体へ拡大しない。

handle78654終了1、54095/74377終了0。全ジョブ終端後、所有UIDと完全argvを照合して
専用server PID3781822のみSIGINTし、handle40798終了0を回収。browser slotは0。

## 既存unitの再利用範囲と来歴

N03全validateは2485検査/499モジュール、終了0、3 skip、全1405対象源の証拠である。
その**全1405ファイル**が現行とbyte一致する。現在の追加27源を含む1432対象のfullを
実行済みとは呼ばない。元logのmethod block末尾okとmodule OKを結合し、以下を再利用した。

| モジュール | 元PASS個別数 |
|---|---:|
| test_adaptive_refinement | 7 |
| test_adaptive_refinement_jobs | 7 |
| test_gui_adaptive_refinement | 5 |
| test_curved_adaptive_refinement | 5 |
| test_gui_curved_mesh_selection | 4 |
| test_curved_selection_transfer | 8 |
| test_curved_comparison_overlay | 7 |
| test_curved_reference_partition | 6 |
| test_frozen_curved_refinement | 8 |
| test_curved_remesh_generation | 9 |

計66個別検査で、新unit実行0。実worker生存確認→中止→元checkpoint保全→追加一水準だけ再開、
再起動interrupted、祖先費用、上限未達、全native saved replay、独立Green/質量/参照被覆を含む。
監査初稿がCLI拒否のstderrを単体FAILと誤読した件は、元method block全体を照合して訂正した。
終端監査の相対native/出力パスのroot誤記も初回2ログを保存し、数値再実行なく訂正した。

rawは `out/n08-public-acceptance-20261008/`。
`rebuild-public-paths.py` / `public-paths-audit.json` / `public-paths.log`、六checkpoint/audit、
`audit-existing-evidence.py` / `existing-evidence-audit.json`、元失敗を含む三browser report/driver/画像、
全job/native、`gui-server-stop.json` とsource snapshotを保持する。
`audit-terminal.py` はhandle5001終了0で全1432源・1747入力・795出力を再hashし、
`acceptance.json`へ389 rawファイルの束縛・実handle終了状態を保存した。
この監査の新FEM/unit/seed/full/legacy0。新外部資料・依存・旧資産参照なし。
元数学・物理核・公開選択/停止/保存・製品GUI源を変更していない。

[親N04四群の現行照合](N04_ACCEPTANCE.md)は歴史記録を全保持した。
共通比較分割版5の成立を選択移送版1の一般化へ読み替えず、残る二機能とRF版5固有の対照を
[仕様カード](N04_REMAINING_CARDS.md)に接続する。D07は依存N03/N06が成立済みで引き続きready。

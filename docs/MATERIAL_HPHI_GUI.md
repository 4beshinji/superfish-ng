# 材料Hphi調整・追跡GUI

2026-09-22、H16-d進行中。まず材料調整要求/保存地点/元場のGUI経路を接続した。材料追跡・履歴・回復、実中止/サーバー再起動、親H16の統合監査は残る。

要求またはcheckpointの専用formatと、選択ジョブのkindにより材料専用GUI処理へ振り分ける。完全な材料Project、shape_law、材料/領域/全界面、各予算、回復規則をJSONのまま保持し、専用パーサーで検査する。元の要求や所有checkpointを旧形式へ変換しない。

実ワーカーの開始、停止後のcheckpoint一覧、個別保存地点の全物理再生、別ジョブへの再開、確認済み対象IDの元場取り込みを既存Hphi画面へ接続した。再開prefixは元投入文書と照合し、元データ移動後も所有コピーで検証する。試行の元Project（表示単位を含む）と全native/RFを保持したまま取り込む。

画面の調整ジョブ一覧に材料kindを追加し、要求プレビューは材料partitionの元メッシュを使う。目標/粗細gateと実行状態、未確認のID/周波数、両R/QのN/Aは既存の区別を保つ。

## 検査

新`test_gui_material_hphi_tuning`は厳密正規化、実workerの1試行保存→再開、元Project/全native取込、元フォルダー移動・管理器再起動、所有checkpoint再生を検査する。直接利用先は旧`test_gui_hphi_tuning`。`before.log`で材料要求が旧パーサーに誤配送されるValueErrorを再現した。実装後の検査は`out/h16-material-tuning-gui-20260922/after.log`。

`verify_gui_material_hphi_tuning.mjs`は実Chromeで要求入力、PAUSED計算、同じ保存ファイルの二度読込、別worker再開、対象順位と元Project表示単位、全native RF一致、元場描画を検査する。実装hash、元ファイルhash、外部要求も監査する。`browser.log`と`browser/report.json`に記録する。新GUI2件＋旧GUI2件は107.967秒PASS/終了0。Chrome実クリック5項目PASS/終了0、検査中の全385実装hashと元12ファイルは不変、外部要求0。ブラウザーとローカルサーバー、全テストworkerの終端を確認した。JSとブラウザー検証器の`node --check`もPASS。

ブラウザー検査後、画面説明の真空限定表現を固定材料の対応範囲へ更新した。HTMLの説明1段落だけの変更であり、追加のFEM/ブラウザー操作は実行していない。`post-browser-copy-edit.json`で検査時との実装hash差分がhphi.htmlだけであることを確認した。検査時hashを現在hashと偽って報告しない。

新規外部資料・依存・legacy参照なし。既存自作GUI輸送とブラウザー検証器を材料専用所有保存へ接続した。数値核/許容値は変更せず、独立物理はH16-a〜c受入へ分離する。全suite/seed validatorや、未実施の追跡/回復/中止GUI受入を主張しない。

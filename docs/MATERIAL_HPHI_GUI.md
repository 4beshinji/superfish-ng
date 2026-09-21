# 材料Hphi調整・追跡GUI

2026-09-22、H16-d進行中。材料調整と追跡/所有履歴の基本GUI、明示履歴回復と延長まで接続・検証した。調整の回復/最終細分表示、実中止/サーバー再起動、軸加速RFの実ブラウザー監査と親H16の統合受入は残る。

要求またはcheckpointの専用formatと、選択ジョブのkindにより材料専用GUI処理へ振り分ける。完全な材料Project、shape_law、材料/領域/全界面、各予算、回復規則をJSONのまま保持し、専用パーサーで検査する。元の要求や所有checkpointを旧形式へ変換しない。

実ワーカーの開始、停止後のcheckpoint一覧、個別保存地点の全物理再生、別ジョブへの再開、確認済み対象IDの元場取り込みを既存Hphi画面へ接続した。再開prefixは元投入文書と照合し、元データ移動後も所有コピーで検証する。試行の元Project（表示単位を含む）と全native/RFを保持したまま取り込む。

画面の調整ジョブ一覧に材料kindを追加し、要求プレビューは材料partitionの元メッシュを使う。目標/粗細gateと実行状態、未確認のID/周波数、両R/QのN/Aは既存の区別を保つ。

## 検査

新`test_gui_material_hphi_tuning`は厳密正規化、実workerの1試行保存→再開、元Project/全native取込、元フォルダー移動・管理器再起動、所有checkpoint再生を検査する。直接利用先は旧`test_gui_hphi_tuning`。`before.log`で材料要求が旧パーサーに誤配送されるValueErrorを再現した。実装後の検査は`out/h16-material-tuning-gui-20260922/after.log`。

`verify_gui_material_hphi_tuning.mjs`は実Chromeで要求入力、PAUSED計算、同じ保存ファイルの二度読込、別worker再開、対象順位と元Project表示単位、全native RF一致、元場描画を検査する。実装hash、元ファイルhash、外部要求も監査する。`browser.log`と`browser/report.json`に記録する。新GUI2件＋旧GUI2件は107.967秒PASS/終了0。Chrome実クリック5項目PASS/終了0、検査中の全385実装hashと元12ファイルは不変、外部要求0。ブラウザーとローカルサーバー、全テストworkerの終端を確認した。JSとブラウザー検証器の`node --check`もPASS。

ブラウザー検査後、画面説明の真空限定表現を固定材料の対応範囲へ更新した。HTMLの説明1段落だけの変更であり、追加のFEM/ブラウザー操作は実行していない。`post-browser-copy-edit.json`で検査時との実装hash差分がhphi.htmlだけであることを確認した。検査時hashを現在hashと偽って報告しない。

新規外部資料・依存・legacy参照なし。既存自作GUI輸送とブラウザー検証器を材料専用所有保存へ接続した。数値核/許容値は変更せず、独立物理はH16-a〜c受入へ分離する。全suite/seed validatorや、未実施の追跡/回復/中止GUI受入を主張しない。


## 材料追跡・所有履歴のGUI接続

材料専用の追跡/履歴formatまたは所有job kindから、専用パーサー、worker、全祖先再生を選択する。履歴への入力pairは要求と同じ種類の完了jobに限定する。GUI共通の明示形式判定helper名も、その役割に合わせた名称へ変更した。

画面の保存場選択に材料nativeを追加し、真空/材料の区別を表示する。追跡・履歴のジョブ一覧と結果表示も材料kindを受け付ける。比較空間のプレビューは各resolution宣言のcurrent_partitionから取る。JSON要求の全材料/領域対応、界面/点予算、写像は編集・保存・復元で保持する。

新`test_gui_material_hphi_tracking`は材料pairの開始/再生、元Project/native取込、元ソース移動後の所有場による再比較、所有履歴作成と段階ごとの元場取込、誤要求/side拒否を検査する。`out/h16-material-tracking-gui-20260922/before.log`で旧要求パーサーへの誤配送を再現した。直接利用先は旧`test_gui_hphi_tracking`と、既存履歴要求/GUI延長・元場取込の2件。

`verify_gui_material_hphi_tracking.mjs`は実Chromeで材料保存場選択、全要求保持、実pair worker、E/Hと有限区間、材料履歴worker、元Project/native/RF取込と場描画を検査する。rawは`out/h16-material-tracking-gui-20260922/`。新材料2件＋旧追跡GUI2件は123.631秒PASS/終了0。実Chrome4項目PASS/終了0、全385実装hashと元12ファイル不変、外部要求0。ブラウザーとローカルサーバー終端。既存履歴要求/延長の関連2件も141.020秒PASS/終了0。ここまでの全handle終端。この基本検査と、後節の明示回復を含む材料履歴の実延長検査は別の証拠である。中止/新サーバー再起動と親H16の統合監査は残る。

新外部資料・依存・legacy参照なし。材料FEM/追跡核・数値許容値は変更していない。保存/GUI経路を検査し、全suite/seedは今回実行しない。


`prepare_gui_material_hphi_recovery.py`は非真空一様材料の順位交換pairを実FEM/native経路で準備し、両元場が独立TEM形状との材料質量内積0.999を超えることを確認する。`out/h16-material-history-recovery-gui-20260922/prepared/prepared.json`はPASS、準備process終了0。

`verify_gui_material_hphi_recovered_history.mjs`で、画面から完全な過去anchor回復履歴を作成し、個別IDを次のpairへ引き継いで新規履歴へ延長する。元要求の保存/再読込、版1への切替で回復指定を消すこと、版2再読込で完全復元することも検査する。`browser/report.json`は実Chrome5項目PASS/終了0。二つの履歴workerが完了し、回復IDを継承して延長した全結果と保存要求が一致した。所有履歴49ファイル・全385実装hashは不変、外部要求0。ブラウザー、ローカルサーバー、全workerの終端を確認した。製品コードは検査中固定した。


追跡GUIの実行コマンドは共通prefix `OPENBLAS_NUM_THREADS=1 PYTHONPATH=.:src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python` に続けて次を指定した。

```
-m unittest -v test_gui_material_hphi_tracking test_gui_hphi_tracking
-m unittest -v test_gui_hphi_history_request test_hphi_tracking_history_saved.HphiHistorySavedTests.test_gui_ordered_history_extension_and_each_original_side
scripts/prepare_gui_material_hphi_recovery.py --out out/h16-material-history-recovery-gui-20260922/prepared
```

各Chrome検証器の`node --check`も成功。実クリックはローカル専用サーバーのlaunch URLを渡し、`--out`に未使用のbrowserディレクトリ、`--request`に各rawディレクトリの要求JSONを指定した。回復履歴検証器には`--workspace`として準備済み所有pairのworkspaceも指定した。

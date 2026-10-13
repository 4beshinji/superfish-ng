# HTTP輸送と曲線変形画面の境界（RF-07）

2026-10-14 **RF-07 DONE**。RF-04/06後の自作sourceを隔離し、HTTP、操作表、曲線変形の一workflowを順に抽出した。検証済み七ファイルだけを主ツリーへbyte一致で反映した。

## 現行の責務

- [gui_http.py](../src/superfish_ng/gui_http.py)はHost/Origin/token認証、厳密要求読取、4/64/128 MiBの条件別制限、応答ヘッダー、許可資産、HTTPエラー変換を持つ。Case・Project・JobManager・専用物理をimportしない。
- [gui_operations.py](../src/superfish_ng/gui_operations.py)は172操作の名前・許可キー・handlerを明示して結ぶ。五専用providerと九操作群、残るProject/workspace処理は元bodyを保ち、`self.reply`だけを型付き応答へ置換した。要求formatや物理型を類似名で統合しない。元のprovider重ね順も保持する。
- [gui.py](../src/superfish_ng/gui.py)は管理器/アクセス/ロック/plot-cacheの生成、明示contextの接続、サーバーの起動/終了と従来のpreview/tangent APIを持つ。旧要求readerと制限定数は下位moduleの公開aliasを保つ。
- [curved-deformation-workflow.js](../src/superfish_ng/web/curved-deformation-workflow.js)は要求生成、元P2境界のDOM描画、候補/編集世代/Undoの状態を分ける。要求はraw目標JSONとSI値を厳密server readerへ渡す。appは現在のAPI/editorを呼ぶadapterを注入し、通常編集/Project置換から状態解除を通知する。

`prepared`/`undo`は状態参照用getterであり、既存ブラウザー検証は旧global名だけをこの参照へ置換した。検証条件、操作、物理許容差は変更していない。曲線変形以外の画面やJobManager、保存地点/中止再開の業務bodyは抽出前と同じ。workerやcheckpoint形式は変更していない。

新JSをHTMLのapp前へ追加し、HTTP許可表も16→17資産へ更新した。既存`web/*.js`のpackage-data指定でwheelへ含まれる。ビルドツール/Web依存の追加なし。

## 受入証拠

raw索引は`out/rf07-http-workflow-20261014/acceptance.json`。着手HEADは`f53e3e3`。

| 選択した検証 | 結果と範囲 |
| --- | --- |
| `test_gui_request_size`、曲線変形3件、F02のHφ実HTTP、平面曲線実HTTP | 実テスト7件PASS、7.975秒。最後に誤指定した存在しないmethodのloader ERRORが一件あり、集約終了1を保持 |
| 正しい平面曲線large checkpoint action-bound method | 1件、0.492秒、終了0/PASS。65 MiB、128 MiB hintとaction対応、既存64 MiB制限を確認 |
| `test_job_startup_cleanup`、`test_gui_curved_mesh_selection`、`test_gui_tangent` | 12件、10.917秒、終了0/PASS。実起動/資源解放、native番号/P2境界、元CLI Case/再生を確認 |
| HTTP/全操作互換監査 | reader/認証/応答/制限/GET body AST、172操作の順序/許可キー/handler、176拒否結果が一致。元数学bodyを保持 |
| 曲線変形実Chrome | 21＋追加6項目PASS。保存/適用/Undo、非同期/イベントなし/値復元時の拒否、両RF方針、重複JSON、実負Jacobian、CLI/GUI実FEMとRF一致 |
| 既存固定履歴実Chrome | 9項目PASS。固定/解除、図上置換/Undo、実worker/native保持、古い非同期応答拒否 |
| `validate_gui_curved_deformation.py` | 1.544秒PASS、新FEM0。146要素の元native境界、独立Green面積/体積比、全P2係数/周波数完全一致、保存場から全RF量再評価、エネルギーと両R/Qを確認。27 native file不変 |
| 最終wheel展開/実HTTP | 最終sourceからbuildし展開後のmoduleをimport。17資産の元byteと実GET、172 strict操作拒否、認証/要求13条件、未許可path5条件を確認。旧新のstatus/body/全安定header完全一致。Date/Serverは比較対象外 |

異なる個別unitは20件の分割証拠であり、終了1の実行を単独PASSに書き換えない。Chrome36項目は外部HTTP0、各実行中の製品source不変、追加画像を目視確認。単独CLI 1 FEM、通常/既存履歴browser各1 FEMの計3新FEMを生成した（unit内の求解は別）。同じ合成形状の独立参照であり、実測構造の評価ではない。

## ソースとの結合と失敗記録

第一稿のasset辞書抽出位置とprovider import scopeを監査で修正し、第一稿sourceを保全した。最初のCLI参照準備で`run`/`solve`を誤指定し終了2、正しい`run-project`のnativeを使用した。固定履歴fixtureの相対path誤りと、sandbox内Chrome起動失敗（チェック/FEM0、仮URLも訂正）を保持し、実URL/実bind許可下の9項目で受入した。

通常/追加Chrome後の製品変更はgui facadeの同値な重複定数四宣言削除のみ。旧宣言と下位定数のAST一致、公開alias/全関数保持を証明し、JS/操作/reader byteは不変。raw監査のtarget-list取扱いERRORも保全して補修した。最終sourceで固定履歴Chrome、HTTP/操作AST監査とwheel実HTTPを確認したため、無変更のFEMを再計算して件数を増やさない。

元1,501 source中、変更した既存四ファイル以外の1,497は不変。新三資産/moduleで1,504 source。wheelビルドが生成した隔離egg metadataは主ツリーへコピーしない。全科学核/専用物理/参照/許容差、schema、公開CLIを保持。新外部資料/依存/旧SUPERFISH資産参照なし。

HTTP/操作/JS資産を一群で撤回でき、旧入力/保存結果の変換を要しない。新full/seed/Hosted CIは実行していない。RF-10と全11カードの最終証拠監査/固定source fullが残り、全goalと元の未受入カードは継続する。

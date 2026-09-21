# 曲線HφのGUI操作

H13-e進行中。曲線追跡・履歴・明示回復の実GUI操作と親H13の全条件監査を含む受入範囲を維持する。

## 調整GUIの第一段階

既存の専用調整画面で、曲線要求/保存地点のformatとworker kindを厳密に判別し、曲線専用の検証・実行・再生へ接続する。元Projectの全二次形状、shape law、比較予算、回復宣言をそのまま保存する。初期checkpoint 000を含む停止workerの保存地点を選択できる。完了結果はmanifestと全保存地点を物理再生し、途中の保存地点は投入要求・所有prefix・元nativeに結び付ける。再開は新しい所有workerへコピーする。

元場表示は対象IDの確認済み実順位を使う。試行が所有する元Projectをnative取込へ渡し、表示単位を保持する。明示ProjectのCaseが保存解と一致しない場合、または管理対象jobに別Projectを上書きしようとした場合は拒否する。元解・RFを再計算した代替表示に置き換えない。

## 対象検査（2026-09-22）

出力：`out/h13-curved-tune-gui-20260922/`。

- `test_gui_curved_hphi_tuning`：追加2件PASS、91.368秒、終了0。実曲線worker、checkpoint 000/001、別job再開、管理器終了後の元job移動と再起動、移動後checkpoint 002再生、元Project/native全バイト一致を検査。
- `test_hphi_project_import`追加1件と`test_hphi_jobs`既存8件は初回結合実行で全9件PASS。明示Project保持、Case変更/管理対象上書き/型不正の拒否、既存CLI・中止・改変拒否の互換性を確認。
- `test_gui_hphi_tuning`旧GUI2件PASS、96.719秒、終了0。
- `node --check src/superfish_ng/web/hphi.js` PASS。

最初の曲線要求正規化は旧パーサーがshape_law等を拒否し、明示Project取込は未実装の引数で失敗した。実装後の結合実行では新GUIテストが管理器を閉じる前に元jobを移動して終了処理を壊したため、管理器終了→移動→再起動の順に修正し、新GUI2件だけを再検査した（`after.log`と`gui-recheck.log`）。製品の数値核・許容値は変更していない。

実ブラウザー用`verify_gui_curved_hphi_tuning.mjs`を追加。Chromeの実クリック5項目PASS、終了0（`browser-2/report.json`）。曲線要求の全保持、開始/PAUSED表示、同一保存ファイル2回読込、新job再開、対象実順位と元Project表示単位、全native結果/RF一致、元場描画を確認。全368実装hashと元12ファイルは不変、外部要求0。検証用サーバーも終了0。初回ブラウザー検証は検証器内でID取得用関数にCSS selectorを渡したため停止し、その要素指定を修正して未使用workspaceで再検証した（`browser/report.json`も保持）。実中止、サーバー再起動後の表示、追跡/履歴/回復GUIと親H13監査はまだ未完了。

新規外部資料・依存・legacy参照はない。GUI輸送の所有検証と表示単位保持の変更であり、FEM/seed TM変更はないため全suite/seed validatorは実行していない。独立物理の根拠はH13-a〜dの曲線比較・調整受入に分離する。

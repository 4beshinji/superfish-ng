# 曲線HφのGUI操作

H13-e受入済み（2026-09-22）。[親H13の条件別監査](CURVED_HPHI_ACCEPTANCE.md)。以下は段階別の実装/失敗/修正/再検査記録であり、途中の未完記述は当時の状態。原受入範囲を変更していない。

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

## 曲線追跡・履歴のGUI接続

追跡要求のformat、履歴要求のformat、保存jobのkindに応じて、曲線専用パーサー・worker・所有再生へ振り分ける。曲線要求の全比較形状/元セルchart/予算はフォームで落とさず保持する。履歴は同じ種類の完了pairだけを受け付け、所有prefixから延長する。各段階の要求と元の前後Project/nativeを表示・取込できる。直線要求/履歴との混用は専用検証で拒否する。

画面の保存場選択とjob一覧に曲線追跡/履歴を追加した。材料場はこの真空追跡の候補には含めない。比較形状の三角形数は元二次geometryのbase_meshから表示する。完全な二次幾何は要求JSONに保持する。

対象検査は`test_gui_curved_hphi_tracking`新2件、直接利用先`test_gui_hphi_tracking`、`test_gui_hphi_history_request`と`test_hphi_tracking_history_saved.HphiHistorySavedTests.test_gui_ordered_history_extension_and_each_original_side`。曲線要求を旧パーサーが拒否する失敗を先に確認した（`out/h13-curved-tracking-gui-20260922/before.log`）。新曲線2件＋既存直線2件は191.725秒PASS、終了0（`after.log`）。Chrome実クリック4項目もPASS、終了0（`browser/report.json`）。全368実装hashと履歴が所有する12元ファイルは不変、外部要求0、検証用サーバー終了0。既存履歴フォーム/延長の2件も321.939秒PASS、終了0（`history-compatibility.log`）。全handle終端。

実ブラウザー検証器は`scripts/verify_gui_curved_hphi_tracking.mjs`。曲線保存場2件の選択、完全要求の保持、実pair workerの開始、E/H・有限比較スペクトル表示、曲線履歴worker、履歴の元Project/native/RF取込・描画を検査する。回復eventと実中止/再起動の操作受入は別途残る。

## 中止・再起動・明示回復の操作受入（進行中）

`verify_gui_curved_hphi_tune_cancel.mjs`は実workerのcheckpoint 001公開後にChromeの中止ボタンをクリックする。保存地点選択、同一ファイル2回再読込、別jobへの1試行再開、対象実順位の元場/RF描画を検査する。同軸状曲線の5項目は`out/h13-curved-cancel-gui-20260922/browser/report.json`でPASS/終了0。`native-audit.json`では取込先の元Projectとnative計6ファイルのbyte一致、現行368実装hash一致を確認した。穴付き曲線の同操作は`out/h13-curved-hole-cancel-gui-20260922/`で検証中。両者の数値的TUNED達成をこのPAUSED再開検査で主張しない。

`verify_gui_curved_hphi_tune_recovery.mjs`はH13-dの実曲線回復調整4試行を別workspaceへコピーし、サーバー配信→正常終了→新サーバー/新Chromeの順で開く。検索/最終細分の比較親とanchor、回復前のID集合と回復後の個別ID、完全要求保存、同一checkpoint再生、回復対象元場/RFを検査する。`out/h13-curved-recovery-gui-20260922/`で進行中。最初のサーバーのHTTP 200と正常終了は確認済みで、全ブラウザー検査完了までは受入としない。

`prepare_gui_curved_hphi_recovery.py`は既存の実曲線順位交換fixtureから二つの所有pairを準備し、独立な小shear TEM状の場との質量内積が両側で0.999を超えることを検査する。`out/h13-curved-history-recovery-gui-20260922/prepared.json`はPASS、準備process終了0。`verify_gui_curved_hphi_recovered_history.mjs`でGUIから明示anchor回復履歴を作り、成功IDを次のpairへ引き継いで延長、完全要求の保存/旧版切替/再読込を検査中。初回構文検査で検証器内の引用符不整合を検出し、修正後の`node --check`はPASS。

製品srcはこの操作検査中は固定。新規外部資料・依存・legacy参照なし。全handleの終端、穴付き中止/再開、両回復GUIの完了を確認してからH13-e/親H13の最終監査へ進む。

### 操作検査で発見したHTTP転送上限の不備

実Chromeの`#error`を読み取り、回復調整checkpoint（10,256,036 byte）と穴付き再開checkpoint（4,549,873 byte）の送信が既存4 MiB上限で拒否されることを確認した。前者は再読込、後者は試行2元場取込で失敗し、両ブラウザー検証を成功扱いせず停止（終了143）。各`transport-failure.json`に原因を保持した。両検証用サーバーは終了0。数値結果自体の破損/失敗ではない。

修正前テスト`test_gui_request_size`を追加し、新しいサイズ別読取関数が未実装の失敗を確認（`out/h13-gui-checkpoint-size-20260922/before.log`）。修正方針はcheckpoint replay/resume/trial importの3操作だけ64 MiB、それ以外4 MiB、絶対上限超過を本文読取前に拒否し、厳密JSONと各操作の完全検証を維持する。製品への適用は、現行src固定で走る回復履歴ブラウザーの終端後に行う。検証器のwaitにも画面エラーの即時検出を追加し、エラーを長時間の計算待ちと誤認しないようにした。

回復履歴の実Chromeは5項目PASS、終了0（browser37766）。明示anchor回復のGUI投入→別job延長→ID継承→完全要求保存/旧版切替/再読込を確認。全履歴ファイル/実装は検査中不変、外部要求0、server19380終了0。以後のHTTP修正による差分はgui.pyだけで、`post-http-fix-audit.json`に全所有ファイル不変を記録した。数値/履歴の成功証拠をHTTP修正後の全実装hash一致と読み替えない。

HTTP修正を適用し、`test_gui_request_size`2件0.170秒PASS、実HTTP認証/厳密操作1件0.623秒PASS（skipなし）、全handle終了0。修正後の大きい実保存地点再検査は回復調整browser-2と穴付きbrowser-2で進行中。以前の中止/再開と現在の読込/元場検査を分割証拠として保持する。

穴付き曲線のHTTP修正後再検査はbrowser-2の2項目PASS/終了0。以前の実中止・保存地点選択・2回読込・別job再開の証拠を保持し、その保存された2試行を新サーバー/新Chromeで再生して、失敗していた元場取込を完了した。`out/h13-curved-hole-cancel-gui-20260922/native-audit.json`で穴1個、元Project/native6ファイルbyte一致、現行368実装hash一致を確認。server60664も終了0。初回一続きの検証が全成功したとはせず、HTTP不具合の失敗と修正後の分割補完を明記する。

## H13-e最終照合（2026-09-22）

回復調整browser-2は4項目PASS/終了0。10 MB超checkpointを新サーバー/Chromeで読み込み、検索/最終細分の未確定ID集合と回復済みID、比較親/anchor、完全要求保存、同一checkpoint2回再生、対象実順位の元場/全RF/描画を確認した。`out/h13-curved-recovery-gui-20260922/final-audit.json`で現行368実装hash一致、元24ファイル不変、取込先Project/native6ファイルbyte一致を確認。server41749も終了0。全操作検査handle/検証用サーバーは終端。

穴付き実中止/再開は初回の所有prefix生成と、HTTP修正後の元場再検査を組み合わせた分割証拠である。`native-audit.json`で取消jobの第1試行と再開先第1試行6ファイル、再開試行2と取込先6ファイルをそれぞれbyte照合。穴/全二次境界/係数/元RFを維持した。PAUSEDからの再開操作をTUNED達成と混同せず、穴付き非一様調整のTUNEDはH13-cの独立証拠に分離する。

HTTP上限修正は認証後の本文読取だけを変更した。新しい転送2件と実HTTP契約1件、実際の大きい保存地点2ケースで影響を限定して検証し、既存物理・所有保存・履歴の成功証拠を再利用した。全suite/seed validator/Hosted CIを実施したという主張はしない。新規外部資料・依存・legacy参照なし。

# O02: 静的StudyのGUI入力・実行・各条件表示

統合記録の件数訂正：標準ログは1429件（1426合格・3skip）、4868.421秒で合格。統合用スクリプトがブラウザー最終群の20件で集計変数を上書きしたため、seed記録のstandard_tests/standard_passedだけを元ログから訂正した。元記録はout/static-field-study-gui-development-20260913/seed-regression-before-count-correction.json、訂正理由とSHAは同standard-count-correction.jsonに保持する。実装・標準結果・数値量・source SHAは変更せず、統合やテストを再実行していない。

2026-09-13 JST。固定895sourceを主901sourceへ統合し、専用静的Study GUIの範囲を限定受入。[受入計画](STATIC_FIELD_STUDY_GUI_PLAN.md)。

専用の/static-study.htmlと7種類の静的Study HTTP操作を追加する。入力はJSON文字列のまま既存StaticFieldStudy parserへ渡し、重複キー・未対応形式・不正な全派生Caseを出力予約前に拒否する。表示長さm/mmだけを変更でき、基底Projectの全SI値・材料/境界・B-H初期値/反復条件とパラメータの順序を保持する。JavaScriptの再編集でも負のゼロは-0.0で保持する。求解は既存の独立Study実workerへ接続する。

StaticFieldStudyAccessは最初の表示とサーバー再起動後に全Studyの元FEMを非同期で再検証する。所有Study、全点Project/nativeと親/各点のmanifest・Job状態をSHAへ拘束し、どの条件が変更されても現在の表示/取得を拒否する。HTTPスレッドで求解せず、全体検証の後に選択された条件の元FEMセル中心場を非同期で作り、同じ条件の表示は再利用する。選択されていない条件も全体検証の対象で、表示用の場の取得だけを選択時まで延期する。

全条件の実行完了と求解成功/非線形失敗の数を分け、全点の入力順と値を選択肢へ示す。成功点には元の専用静的Project画面と同じ全量・材料セル中心の片側標本・SI単位を表示する。元三角形ごとの一定色、明示した零中心の対称色範囲と標本最小/最大を使う。平面の単位長量と軸対称全周量、RF周波数・二つのR/Q・RFモード番号のN/Aを保つ。失敗点には元Caseと全停止履歴を示し、場や零の量を作らない。入力順を解枝追跡・収束系列と呼ばない。

Study入力・全Study結果と、各条件Project/元nativeをそのまま取得する。成功点はProjectとnative 5ファイル、実失敗点はProjectとnative 3ファイルで、nativeのmanifestも含む。取得の前後に全StudyのSHAを確認する。RF履歴から専用Study画面へ誘導し、実行中の中止を保つ。条件/Studyの切替時は旧表示を消し、遅れて返った旧選択の応答で新しい表示を置き換えない。

受入には全11形式・対応次数・両パラメータ、全点の元Case/量/場/単位と実失敗履歴、全元バイトの独立比較と初回/実サーバー再起動後の実Chrome操作を要求する。中止・強制終了、別条件の改変、無効な入力からの復帰、既存RF/単体静的Project/磁気報告も検査する。候補の専用6件・capability 3件・変更した既存CLI/capability 2件の計11unitは751.181秒、ResourceWarningなしで合格。画面/ブラウザーscript追加後のJavaScript構文検査も合格。4 Study/11点（成功8/実非線形失敗3）の実Chrome試作検証は初回20項目・実サーバー再起動後14項目が合格し、両方で元68ファイル取得が一致。初回は編集Study 4取得も別に確認した。重複JSON、別条件の改変/正常結果への復帰、実worker中止/強制終了と既存RFを検証し、2画像を目視した。試作サーバー/Chromeは両方終了済み。全78 Study/192条件の独立GUI比較・全件の初回/実サーバー再起動ブラウザー・標準回帰は未実施で、実行結果を受入時に追記する。

候補はworker独立検証中の889sourceを別ディレクトリへ複製して作成した。親workerを変更せず、GUI受入前にworkerの最終固定sourceとの差を照合する。新規数値モデル・依存・外部資料・旧版コード/実行の再利用はない。対象版、O02親と全計画は未完。

2026-09-13 継続：全件の独立GUI比較を開始。比較基準は受入済み入力66 Study/165条件と元9失敗Case/18条件、新たに元FEMで確認する3混合Study/9条件の、同じ78 Study/192条件である。Study workerの比較完了には依存させず、元nativeから期待するStudy全結果と元場を直接構築する。参照bundleにはStudy実行のJob/完了manifestを作らず、元nativeと明示のreference-provenanceを保存する。全38形式/次数/パラメータ組合せを実際の記録から検査する。

最初の独立GUI条件を通過した895sourceを検証用候補として固定し、標準1429件も並行実行中。実ブラウザーの全件期待値も同じ元nativeから別に評価し、独立GUI比較の全Case/量/元場と同一条件であることを監査する。全件初回/実サーバー再起動、既存静的42件/磁気20件、目視、全source/バイト一致は受入前の必須条件のままで、まだ受入ではない。

全件の独立GUI比較は1896.439秒でPASS、実ハンドル99583の終了0を確認した。全11形式・38形式/次数/パラメータ組合せ、78 Study/192条件（成功171/実非線形失敗21）で、実worker 78、初回/再起動後各78の全Study再検証・各192の点場表示・各1266取得が一致した。元1941/所有3537ファイルが不変で、全895sourceが固定候補と一致する。証拠はout/static-field-study-gui-independent-trial-20260913/report.jsonとdev/independent-completion.json。別に直接元nativeから作った実Chrome期待値との全78 Study/192条件・全Case/量/元場の照合もdev/browser-reference-audit.jsonでPASS。全件ブラウザー、標準1429件、親worker受入と主統合/専用検証は残る。

全件の初回実Chromeはout/static-field-study-gui-browser-20260913/report.jsonで94項目PASS、実ハンドル85430の終了0を確認。78 Study/192条件・元1266取得と編集Study 78取得、全Case/量/元場/単位/実失敗、中止/強制終了・別条件改変拒否/復帰・RF履歴誘導と既存RF実FEMが一致した。配信source不変・外部HTTP要求0。元の細かいメッシュと全失敗/混合Studyの3画像を追加目視し、初回の計4画像をdev/visual-review-in-progress.jsonへ記録。既存静的42例の初回ブラウザーを同じサーバーで開始し、その後の磁気20例・実再起動と標準/主受入は残る。

同じ初回サーバーで既存静的42例/234取得・56チェック、磁気報告20例/140取得・28チェックもPASS、端末42499/89529の終了0を確認。3報告の全配信sourceが固定候補と一致することをdev/all-initial-browser-completion.jsonに記録した。初回サーバー6993/PID1853591を正常終了0とし、2026-09-13 12:12 UTCに同じworkspaceを別PID2014893で再起動、全Study復元の実Chromeを開始した。再起動後の全3ブラウザー・最終目視・標準/主受入は未完。

実サーバー再起動後の全Study Chrome56778は終了0、out/static-field-study-gui-browser-restarted-20260913/report.jsonで88項目PASS。初回と同じ78ジョブ/192条件・成功171/実失敗21、各元1266取得と既存RF保存結果が一致し、配信source不変・外部要求0。再起動後の成功・平面混合失敗・正半径混合失敗の3画像を追加目視し、初回と合わせて7画像をdev/visual-review-in-progress.jsonへ記録した。既存静的42例の再起動後ブラウザーを開始し、その後の磁気20例・サーバー終了と最終目視記録・標準/主受入は残る。

再起動後の既存静的44276は50チェック/42例/234取得、磁気22395は26チェック/20例/140取得がPASS、両端末終了0。初回と同じジョブと既存RF結果を復元した。再起動サーバー53891/PID2014893も正常終了0とし、両実サーバーの停止記録を確認。全6ブラウザーは342チェック・元3280取得（初回の編集Study78/Project42は別）、固定895sourceと一致。dev/all-browser-completion.jsonに全記録を保持し、Study初回4/再起動3・既存静的/磁気各1の計9画像をdev/visual-review.jsonへ目視済みとして記録した。標準1429件、親worker受入と主統合/専用検証は残る。

最終独立比較は1896.439秒でPASS。受入済み入力段階66 Study/165条件、既存9失敗Caseの18条件と新たに元FEMで確認した3混合Study/9条件から、GUI/Study実行を用いず全参照を組み立てた。全Case/量・履歴、元セル中心場/材料/単位と各1266取得、元1941/新3537ファイル不変。最終証拠はout/static-field-study-gui-independent-trial-20260913/report.json。試作4件を全78件へ読み替えず、別の全件記録を得た。

標準は4868.421秒、1426合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは638.480秒でPASS。固定895sourceと主901source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。統合証拠はout/validation-static-field-study-gui-candidate-20260913/seed_regression.json。

実Chrome記録 out/static-field-study-gui-browser-20260913/report.json は94チェックPASS。

実Chrome記録 out/static-field-study-gui-browser-restarted-20260913/report.json は88チェックPASS。

実Chrome記録 out/static-field-study-gui-static-browser-20260913/report.json は56チェックPASS。

実Chrome記録 out/static-field-study-gui-static-browser-restarted-20260913/report.json は50チェックPASS。

実Chrome記録 out/static-field-study-gui-magnetic-browser-20260913/report.json は28チェックPASS。

実Chrome記録 out/static-field-study-gui-magnetic-browser-restarted-20260913/report.json は26チェックPASS。

実サーバー/Chromeを停止し、新しいサーバー/Chromeから同じworkspaceの全78 Study/192点、単体静的42件と磁気報告20件を再検証した。元取得はStudy各1266（初回編集Study 78は別）、単体静的各234、磁気各140。初回の入力編集/表示単位/負のゼロ、全場とSI量/履歴、条件切替、実中止/強制終了・別条件改変拒否と正常復帰、既存RFの実FEM/全native量を確認。目視記録はout/static-field-study-gui-development-20260913/visual-review.json。次は[O02原要件照合](O02_ACCEPTANCE_PLAN.md)。

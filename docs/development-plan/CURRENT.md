# 現行の作業入口

更新：2026-10-07、P07独立A/B内部mesh・増求積次数の検証を継続。
原90カードと追加子カードを含む全123カードの計画は継続中。P04の完了は全goalの完了ではない。
このページを現行入口とし、各文書の日付付き追記は履歴として読む。

## 横断レビューと計画（2026-09-22）

ユーザー依頼のREVIEW-01として、`a191b4e`基準の[既存実装レビュー](../IMPLEMENTATION_REVIEW_2026-09-22.md)と
[リファクタリング計画](../REFACTORING_PLAN.md)を作成した。所見10件とRF-01〜RF-10の依存・受入・検証・撤回方法を記録。
依存不在のGUIテストエラーを限定再現したが、製品・テスト・検証器は未変更、修正カードは全てPLANNED。
次にリファクタリングを実施する場合の推奨はRF-01（検証来歴）→RF-02（環境/任意依存）。
既存115開発カードの状態は維持する。以下は既存機能開発の次着手であり、今回の文書作成の継続作業ではない。

## 次の着手

**[P07：平面曲線の実解と元場・RFを実装する](03-planar.md#p07)**。IN_PROGRESS、先行P06はDONE。
[P07進行記録](../PLANAR_CURVED_SOLVER.md)で専用実solve/元12場/実側壁RF、strict点所属と元Domain細分を実装。
新10/旧物理2種類を分割確認。二尺度・両偏波の固定二次円の元12解を保持し、
TMだけL3へ追加2FEMで解析f/E/H/G全対象群を確認した。続く[最終二水準比較](../PLANAR_CURVED_CONVERGENCE.md)で
TEのE差/TMのRF差未達を保持し、追加4FEMでTE L2→L3/TM L3→L4の二尺度f/E/H/全RF差を確認。
保持元解は計18、401製品不変、許容値不変。[独立A/B内部mesh・増求積次数](../PLANAR_CURVED_INDEPENDENT.md)を検証中。続いてN16/32/64幾何と各FEM、
滑らかな楕円/再入角の二尺度・固定FEM差を[P05 gate](../PLANAR_CURVED_RF.md)で別々に検証する。
円の解析PASSだけでP07を閉じない。[P06受入](../PLANAR_CURVED_FEM.md)は継続利用、元398製品は不変。
既存dispatcher/CLI/native/Project/worker/GUIはP08、曲線比較/調整はP09で未接続。
既存P04全子とP05/P06はDONE、原互換親P02/D02とH17/H18、P07〜P09は未完了。

P03の新7/既存25件、計32件は1.871秒PASS（終了0）。
範囲・初回テスト入力エラー・解析不変量・コマンドは上記専用文書に記録。
全validate/seed/GUIの再実行はしていない。実行handle94126は終了0、生存処理の引継ぎなし。

H17は[損失範囲整理](../MATERIAL_HPHI_LOSS_SCOPE.md)まで実施しIN_PROGRESS。
2026-09-22のユーザー選択は「対象版の資料で必要性を確認してから決める」。
追加損失の採否は資料確認まで未確定。H17に依存しないP07を進める。

## 受入証拠と依存待ち

| 状態 | 根拠と限界 |
| --- | --- |
| H13 / H15 / H16カード受入済み | [曲線Hφ](../CURVED_HPHI_ACCEPTANCE.md)、[材料追跡](../MATERIAL_HPHI_ACCEPTANCE.md)、[材料調整と操作](../MATERIAL_HPHI_TUNING_ACCEPTANCE.md)。これらは親P03/P04の全旧互換受入ではない |
| B02 / B03整理済み | [B02](B02-reference-audit.md)、[B03](B03-required-scope.md)。C00.Vと未確認仕様の採否は未確定。TM旧集約JSONの欠落、TE集約hash一致を区別する |
| H18依存待ち | H13/H16はDONE。H17、C07-hphi、C07-materialが残る。H16の成功だけで親P03/P04を閉じない |
| 外部資料の不足 | R25改訂/対象版入力、K29/30ツール仕様、K31実機資料。調査カードの完了を、その資料に依存する実装・検証の完了としない |

全カードの着手可能性はTSVの`depends_on`を現在の状態で照合する。
この表は全残件の省略可能リストではなく、直近の引継ぎに必要な抜粋である。
原要件の全件対応は[計画](README.md)、[B01台帳](B01-ledger.md)と最新の専用受入文書を参照する。

## 実行中処理とソース固定

2026-10-07 P07：専用比較器 `scripts/planar_curved_mesh_reference.py` と
`scripts/validate_planar_curved_independent.py` を追加。元Domainから全chartを再生成し、
有理数の共通参照分割で元E/Hを直接比較する。新6/既存5unitは28.116秒PASS。
独立壁積分の最初の実行は検証器のJacobian key誤参照で終了1（新FEM1、保持済み）。
keyだけ修正し独立面積/全vector壁検査を1unit追加、session9777へ実行中。
求積系列の修正後session76545、出力 `out/p07-planar-curved-independent-20261007/quadrature-final/`、
logは同親の `quadrature-final.log`。二尺度・両偏波のarea8/12/16、wall12/16/20を別々に解く。
製品401ファイルと検証器5本をhash固定。終了まで製品/使用検証器を変更しない。
追加1unit/session9777は1.475秒PASS/終了0。求積/session76545は42.155秒PASS/終了0、
12元解と最後4解の物理再構築を保存、401製品hash不変。
独立mesh/session38783が実行中。出力は同親 `mesh/`、logは `mesh.log`。
元Aは前回最終二水準の全hash/物理再構築で確認し、Bの初期未達と実細分を別保存する。
TE半径0.01のB L2→L3はTE01 E差1.027957%で未達、A L3対B L3/解析対照はPASS。
許容差を維持しB L4を追加中。楕円/角入力の新4unitは4.734秒PASS、
vector化候補の新3unitは0.018秒PASS/単一patch10.56倍実測、使用validatorへ未接続。
後続の明示adapterは全array/元RF/全参照比較の追加2unitをPASS、群guard拒否1unitもPASS。
円meshの使用検証器には接続せず、別の[楕円・再入角driver](../PLANAR_CURVED_SHAPES.md)へ接続した。
楕円TE尺度1/session25516と角TE尺度1/session68744が実行中。
出力は同親 `ellipse-te-s1/` と `corner-te-s1/`、logは同名 `.log`。
全8非円形を並行検査：ellipse TE s1=25516 / TM s1=12945 / TE s2=25128 / TM s2=92077、
corner TE s1=68744 / TM s1=35844 / TE s2=27629 / TM s2=70344。
各出力は同親 `<shape>-<polarization>-s<scale>/`、logは同名 `.log`。
これらは401製品と使用8検証器をhash固定。円38783を含む全9handle終端まで変更しない。
非円形TE尺度1のA L2→L3は楕円/角ともPASS、Bの初期未達を保持して細分中。
独立FEM尺度・回転・平行移動の新3unitは0.083秒PASS。専用session71524を開始、
出力同親 `covariance/` / `covariance.log`、401製品と使用7検証器をhash固定。
全10handleの終端を観測し、各受入と原P07受入を分ける。
終端：楕円TE尺度1/25516は351.293秒PASS（5実FEM、A L3/B L3の全gate、401製品不変）。
共変性71524は11.919秒PASS（円/楕円/角両偏波12実FEM、全場/RF尺度則最大5.346e−13）。
楕円TE尺度2/25128も450.860秒PASS/終了0（A L3/B L3、5実FEM、401製品不変）。
現在は円mesh38783と非円形の残6handleが継続中：corner TE68744/27629、
ellipse TM12945/92077、corner TM35844/70344。終了した25516/25128/71524を再起動しない。
[仕様・分割検査・失敗履歴](../PLANAR_CURVED_INDEPENDENT.md)。
sessionを `write_stdin` で観測し、timeoutを理由に再起動しない。P07/全goalは未完了。

P07最終二水準：全handle終端、401製品/比較器固定解除。
新5unit/session79738は1.828秒PASS/終了0。初回/session8261はnp.bool_ JSON保存で終了1、新FEM0。
保存型だけboolへ修正し、JSON往復追加の限定1unitは0.521秒PASS/終了0。失敗log/出力を保持。
専用/session72321は1086.911秒PASS/終了0。元14解raw全hash不変、最終8解を物理再構築。
TE01 L1→L2のE差1.031212%/TM L2→L3のP′差0.851679%の未達を保持し、元境界を保った追加4FEM。
TE L2→L3/TM L3→L4の二尺度f/E/H/全RF差PASS、計18元解保持、追加fineの解析対照もPASS。
最大P′差0.221120%、親chart座標上限9.039e−15、独立場energy差2.513e−13、401製品不変。
証拠 `out/p07-planar-curved-convergence-20261002/`、[限定受入と残gate](../PLANAR_CURVED_CONVERGENCE.md)。
次は同初期Domain独立A/B内部meshの全場/全RF、増次数/幾何系列/楕円・角も残る。
P07 IN_PROGRESS/全goal ACTIVE、生存handleなし。

P07初回解析対照（履歴）：全handle終端、401製品hash固定解除。旧398全ファイル不変、新3製品ファイルのみ。
新solver7/同Domain細分3 unit/session19390は10件2.343秒PASS/終了0。旧直線物理2件は初回成功を保持、計12種類。
初回/session18384は8PASS/1FAIL、1.036秒/終了1。ほぼ零TE Exの単独相対値比較を、同係数場と全E/H normへ分離。
限定/session4352は1件1.007秒PASS/終了0。その後の全モードAPI追加で新10件を確認した。失敗log保持。
円三水準/session81249は12FEM、68.327秒/終了1。TE全target L2 PASS、TMはf/E/H PASS/G最大1.13743%で未達。
401hash不変と元12解を保持し、circle-extended/session65520でTM二尺度だけL3へ延長。
追加2FEM、保持14解、111.818秒PASS/終了0。TE L2とTM L3で解析f/E/H/G全対象群PASS、TM G最大0.295791%。
各実行内の401hash不変、独立field energy差最大1.081e−13、元398不変。
延長後の検証器indent/import整理はASTのみ、新FEM/製品変更なし。全handle終端、src固定解除。
証拠 `out/p07-planar-curved-rf-20261002/`、[限定成功と残る全gate](../PLANAR_CURVED_SOLVER.md)。
次は上記P07残条件の独立検証、P07 IN_PROGRESS/全goal ACTIVE。生存handleなし。

P06：全handle終端、398製品hash固定解除。先行unit/session56921は新9/既存5、14件2.317秒PASS/終了0。
shared拒否追加/session95476は1件0.024秒PASS/終了0、全Jacobian拒否追加/session31040は1件0.006秒PASS/終了0。
専用geometry/form validator/session15905は四ring円6Domain/12行列スペクトル、16.202秒PASS/終了0。
mass面積差最大3.331e−16、定数核相対norm最大2.612e−16、N64の面積/周長/距離は1e−4幾何gate以内。
実行前後398製品hash不変、元395製品も不変。新3製品ファイルのみ、shared core/seedに差分なし、seed/full validate未実行。
初回/session28014は8PASS/1FAIL、0.783秒/終了1、重複cell fixtureの未使用node先行拒否を修正し失敗log保持。
証拠 `out/p06-planar-curved-fem-20261002/`、[条件別受入と来歴](../PLANAR_CURVED_FEM.md)。
次はP07、全goal ACTIVE。生存handleなし。

P05：解析reference/session96355終了0、新FEM0。Bessel norm/エネルギー/壁G最大6.662e−16、
等分配8.882e−16、符号curl3.995e−10、二尺度則PASS。
仕様auditは全123カード/依存/節ID/JSON例/入口links20件/二尺度patch・Green積分を確認、2.647秒/終了0。
初回の小見出し未認識は監査器のみ修正し、失敗logを保持。数式照合を再実行しない。
395製品hashは前後不変、文書だけでunittest/seed/全validateは未実行、生存handleなし。
証拠 `out/p05-planar-curved-spec-20261002/`、[仕様受入と後続の責任](../PLANAR_CURVED_RF.md)。
次はP06、全goal ACTIVE。

P04-c-b：全handle終端、395製品hash固定解除。Python/session7780は10件160.560秒PASS/終了0。
独立API/session95901は3pair PASS/終了0、全照合/session12034は3pair全判断/所有履歴、70配列・全RF/最終Project一致/終了0。
browser2/session58021は9項目PASS後の回復宣言誤りで終了1、保存済みpair/履歴を継続したbrowser4/session19976は7項目PASS/終了0。
新サーバー復元/session67927は5項目PASS/終了0、最終CSS限定/session73174は3項目PASS/終了0。
表示修正後の差分はweb HTML/JS/CSSのみ、数値ソース不変。全reportは外部要求0、各実行内の製品hash不変。
server12853はSIGINT終端130、server86426はSIGINT正常終了0。所有browser slotは空。生存handleなし。
証拠 `out/p04cb-planar-tracking-gui-20261002/`、[失敗・分割操作・表示と最終受入](../PLANAR_PIECEWISE_TRACKING_GUI.md)。
修正前form/session51699の宣言喪失、prepare/session6542のfixture順位0、browser初回23379/3回目79214の検証器入力不備を保持。
原P04/全子監査を受入し次はP05。全goalと原互換親P02/D02は継続。

P04-c-a：製品 `c81782d`、395ファイルを固定した実操作。
新版browser4/session1506は11項目PASS/終了0、旧アフィンbrowser/session53127は5項目PASS/終了0。
新サーバーbrowser/session25370は復元4項目PASS/終了0。全reportで外部要求0、製品hash不変。
独立API session83901はTUNED4試行、61.034秒/終了0（api-success/）。
全native照合session33079は終了0、4試行+取込の50配列、Project/要求/全判断/RF一致。
解析TE10相対差1.0703275159507086e-6。全製品hash不変を確認しsrc固定解除。初回audit/session42718はGUI runtime exportへowned-disk readerを誤用して終了1。
監査器だけをruntime replayへ修正し、同じ既存結果を照合してPASS。新FEMは実行しない。
server90303/76968はともにSIGINT正常終了0、全ブラウザー回収済み、所有slotディレクトリなし。
新版/旧版/復元の場画像を目視し、単位J/mとRF N/A、対象順位、全三場を確認した。
最初のsandbox内loopback bindはEPERM/終了2であり、昇格したローカルサーバーを使用。
browser初回99585は起動待ちReferenceError、browser2/7873は旧error誤判定、
browser3/84849は応答前の次入力による正しいstale拒否で終了1、各回収済み。
検証器だけを応答counterで同期しbrowser4成功。各失敗report/logを保持する。
証拠 `out/p04c-planar-browser-20261002/`、[操作/全元場照合](../PLANAR_PIECEWISE_TUNING_GUI.md)。
新GUI1/旧GUI5のPython操作はsession93859、160.930秒PASS/終了0。
修正前地点選択はsession11909、6.316秒ERROR/終了1。証拠 `out/p04c-planar-gui-20261002/`。
上記P04-c-bで単独追跡/履歴と親P04監査も受入。

2026-10-02：P04-b-cのsession19594は603.667秒、17件中16PASS/同じ中止テスト2ERROR、終了1。
移動済み中止jobの旧pathをテストprocess辞書から除く修正後、session11536は1件40.054秒PASS、終了0。
分割17種類（新5/旧直接利用12）PASS、395製品hash不変。全handle/worker終端、src固定解除。
元移動・実中止/再開・管理器再作成・最終回復・未確認null・改変拒否を確認し、親P04-bを監査受入。
証拠 `out/p04bc-planar-worker-20261002/`、[条件別監査](../PLANAR_PIECEWISE_TUNING_WORKER.md)。

2026-10-02：P04-b-bは初回session30100終了1（新7件、2PASS/3FAIL/2ERROR、85.712秒）。
格子改善後session99948終了1（選択21件、20PASS/CLI期限1ERROR、846.030秒）。
旧版1〜3の14件全PASS。CLI300秒期限の再確認session65480は256.734秒PASS（終了0）。
独立TMはsession12993終了1（8/16gridでiteration limit）後、12/24gridのsession11671が
192.929秒PASS（終了0）。分割22件成功、全数値許容差を保持。395製品hash不変、
全handle終端、src固定解除。証拠 `out/p04bb-planar-owned-20261002/` と[専用記録](../PLANAR_PIECEWISE_TUNING_SAVED.md)。

2026-10-02：P04-b-aは初回session36755終了1（28PASS/1FAIL、146.388秒）。
再生成/幾何検査の順序修正後、session64698の影響17件は45.567秒PASS（終了0）、
非影響の初回12件成功を保持する。各実行の394製品hash不変、全handle終端、src固定解除。
証拠 `out/p04ba-planar-shape-20261002/` と[専用文書](../PLANAR_PIECEWISE_SHAPE.md)。

2026-10-02：P04-aのsession39306は終了1（54PASS/誤メソッド名1収集ERROR）。
正しいstrict1件と独立元場/RF2件は別実行で終了0。分割57件PASS、391製品ファイル不変、
全worker/handle終端、src固定解除。証拠 `out/p04a-planar-piecewise-20261002/`、詳細は専用文書。

履歴Chrome session 91632と調整/新サーバーsession 87997は終了0。
全Chrome/サーバー/managerをclose済み。製品src固定解除、生存handleの引継ぎなし。
証拠は `out/p02-planar-history-browser-20260922/` と `out/p02-planar-tune-browser-20260922/`。
各reportの389製品hashを現行ファイルと照合し不変。
sandbox内のプロセス一覧はホスト全体の不存在証明に使わない。

長時間処理を開始したら、この節にツールsession/cell ID、PID（取得できた場合）、
ジョブ/出力パス、開始時実装hash、次の観測方法、ソース固定範囲を記録する。
引継ぎでは同じhandleを観測し、観測timeoutだけで再実行しない。
古い履歴のPID/「生存中」を現在の生存証拠にせず、終端結果または現存handleで確認する。

## 更新手順

1. 開始時に`git status --short`とTSVを確認し、次カードの条件・専用文書・実装を読む。
2. 作業中はこのページの次着手/処理状態を更新する。BACKLOG・CODEX_HANDOFF・計画READMEの先頭案内は固定し、同じ進捗段落を三重追記しない。
3. 受入時は専用文書へ条件別の結果、実行コマンド/終了状態、失敗/未確認、証拠パスを記録する。TSVは満たしたカードだけ更新し、部分受入と親受入を分ける。
4. このページを次カード・残る依存・生存処理に合わせて更新し、整合したローカルコミットを作る。履歴の大量削除/一括再編はしない。
5. 原計画の全条件と追加必須カードを監査して初めてgoal完了を判断する。履歴の「全goal ACTIVE」「次は」は新しい開始命令ではない。

B04確認：3入口から本ページ、着手条件・実装・検査・受入証拠へのリンク、
全111カードと依存、差分を確認しPASS（リンク節IDを含む、git diff --checkもPASS）。文書のみで数値計算・unittestは実行しない。

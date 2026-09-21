H13-d受入（2026-09-22）：[調整回復の所有操作と条件別監査](CURVED_HPHI_TUNING_RECOVERY_SAVED.md)。追加2件1448.786秒PASS/終了0、両accepted.json、367実装hashと所有30/12ファイル一致を確認。回復調整4試行TUNEDと穴付き1試行PAUSEDを区別し、元場/全RF/移動後再生/再起動/改変拒否を受入。全handle終端。次はH13-eの実GUI/API一致・親監査。H14仕様はa6b7a7eで独立受入済み。親H13/全goalは未完了。

H14仕様はH08 DONEを確認して独立に受入・コミット（a6b7a7e）。[材料界面比較契約](MATERIAL_HPHI_TRACKING.md)。H15/H16は未着手。H13-d受入検査のsrc固定中に文書のみ進め、FEMを再実行していない。

H13-d曲線履歴・回復を接続（2026-09-22）：[所有曲線履歴とanchor回復](CURVED_HPHI_HISTORY.md)。隣接native/ID集合継承、所有過去anchor照合、worker延長・元pair移動・管理器再起動・未確認停止の新3件＋関連5件PASS、全handle終了0。履歴/追跡CLI新2件＋旧互換1件もPASS、全handle終了0。次は曲線調整回復の所有操作受入とH13-d監査、続いてH13-e GUI。全goalは継続。

H13-d独立曲線追跡の所有pairを接続（2026-09-22）。[所有保存・worker契約](CURVED_HPHI_TRACKING_SAVED.md)。全Project/nativeコピーと元E/H再計算、移動後再生、worker中止/再起動、改変・予算拒否の新3＋関連11件PASS。サンプル予算/直線native拒否の追加検査1件もPASS、全handle終了0。順序付き履歴・過去anchor回復・CLI/GUIは残る。全goalは継続。

H13-d worker接続済み（2026-09-22）：[曲線調整worker](CURVED_HPHI_TUNING_WORKER.md)を追加。起動/所有完了検証、実中止・新job再開、管理器再起動、全出力移動/改変拒否の新5＋関連9件を分割検証。初期prefix削除の不備を再現・修正し、影響2件PASS。全handle終了。独立追跡履歴・回復の所有操作・GUIは残る。全goalは継続。

H13-d CLI接続済み（2026-09-22）：`tune-curved-hphi`/`resume-tune-curved-hphi`/`replay-tune-curved-hphi`を追加。[所有保存とCLI契約](CURVED_HPHI_TUNING_SAVED.md)。実FEM尺度則、全RF保持、移動後再生、未確認停止、旧直線CLI互換の新3＋既存1件PASS。全handle終了0。独立追跡履歴・worker・GUIは未完了。

H13-d進行中（2026-09-22）：[曲線調整の所有保存・再生](CURVED_HPHI_TUNING_SAVED.md)を実装。専用Python APIで全元Project/nativeを所有し、物理再生と新出力への再開、移動後再生を接続。新5件と関連6件PASS（分割証拠）。追加8件200.791秒、handle終了0。独立追跡履歴・CLI/worker・中止/管理器再起動・GUIは残る。H13-d/親H13/全goalは未完了。

H13-c完了（2026-09-22）：[曲線調整・ID回復の条件別監査](CURVED_HPHI_TUNING.md)。元全P2形状/加速座標/同領域最終細分を接続し、実曲線anchor回復と未確認停止、穴付き非一様調整の目標/粗細差を確認。新8件は分割証拠で成功、関連5件PASS、全handle終端。n=5穴付き受入は1623.573秒、終了0。許容値は維持し、粗い例・大変形・不適切な直線式目標の未達も記録。次はH13-dの所有保存/履歴/CLI-worker。親H13/全goalは未完了。

H13-c検証中（2026-09-22）：[曲線調整runnerと明示ID回復](CURVED_HPHI_TUNING.md)を追加。初回guard、ID未確認時の周波数null、目標/粗細差の別判定、真の縮退停止、実曲線anchor回復を確認。粗い穴付き例のmesh未達と大きい非一様変形のoverlap不足は拒否を維持。細かい穴付きn=5/10%変形の成功受入試験を`out/h13-curved-tuning-20260921/nonuniform-budgeted.log`へ実行中。まだH13-cを完了/コミットしていない。結果の終端を確認し、条件別監査後にH13-dへ進む。

H13-c進行中（2026-09-21）：[元候補と同P2最終/比較細分](CURVED_HPHI_TUNE_TRIALS.md)を接続。参照chartを有理数で合成し、元領域までの全被覆/丸めと累積scalar質量保存、加速座標保持、構築前予算拒否を確認。次は曲線調整runnerの目標/粗細差別判定と明示anchor ID回復。H13-c/親H13/全goalは未完了。

H13-c進行中（2026-09-21）：[元Projectの全P2形状変数](CURVED_HPHI_SHAPE.md)を実装。全穴/二次中点を保持し、端点/位相原点を明示移送、軸中点丸めを局所寸法でも検査。新4件＋関連9件PASS、終了0。次はこの形状則と同P2細分を曲線調整探索・追跡・明示ID回復に接続する。H13-c/親H13/全goalは未完了。

H13-b完了（2026-09-21）：[曲線E/H追跡と条件別監査](CURVED_HPHI_TRACKING.md)。scalar射影・各元領域の有限スペクトル・E/H部分空間を接続し、実曲線順位交換、解析縮退ID集合、guard停止、位相、native番号/chartを確認。新7件（分割実行）＋関連8件PASS、全handle終端0。次はH13-cの曲線形状調整・加速座標・同P2最終細分・明示ID回復。親H13/全goalは未完了。

H13-b進行中（2026-09-21）：[曲線有限比較スペクトル](CURVED_HPHI_SPECTRA.md)を追加。明示same-vacuumのより細かいP1/P2空間で、元scalar場の射影とshifted-inverse残差を診断する。新3件＋追加直線極限1件＋関連8件PASS、全検査handle終了0。q静的零空間を保持し、順位/連続誤差/IDは主張しない。次はE/H部分空間追跡とguard接続。H13-b/親H13/全goalは未完了。

H13-b進行中（2026-09-21）：[曲線q/u質量射影](CURVED_HPHI_PROJECTION.md)を追加。独立モーメント・細分保存・粗視化損失・二尺度/非一様shear・P1/P2直線極限の新5件PASS。有限比較スペクトルとE/H部分空間追跡は未実装で、H13-b/親H13/全goalは未完了。次は比較空間での有限スペクトル診断。

H13-a完了（2026-09-21）：[同二次領域細分と明示丸め検証](CURVED_HPHI_REFINEMENT.md)。全穴/軸・P1/P2・定数場・M/K転送、再細分の元領域被覆を確認。旧版1は厳密、版2は測定した座標丸め上限と局所分解能を検証。新6＋関連21＋三水準利用先2件PASS、全handle終了0。次はH13-bの質量射影・有限スペクトル・部分空間追跡。親H13/全goalは継続。

H13-a進行中（2026-09-21）：[曲線Hφ細分と明示丸め検証](CURVED_HPHI_REFINEMENT.md)を追加。元二次境界を再投影せず4分割し、全穴/軸とP1/P2のM/K転送を確認。旧domain版1は厳密一致を維持し、版2だけ丸め上限を明示。新6件の最終検査、関連21件PASS。三水準の直接利用先2件は実行中。H13はa〜eに分割し、元の調整/保存/操作受入条件を維持。

H12-bと親H12を完了（2026-09-21）。[固定二次領域の三水準診断・条件別監査](CURVED_HPHI_CONVERGENCE.md)。f/直接E/H/全境界RF/軸電圧を別判定し、guard不足・近縮退を未確認に保持。新5件の分割証拠＋関連19件PASS、全handle終端。粗い解析TEMの未達とテストdeepcopy失敗も記録。次はH13の曲線履歴・調整と保存/操作接続。全goalは継続。

H12-a完了（2026-09-21）。[曲線Hφの元E/H場比較](CURVED_HPHI_FIELDS.md)を受入。完全二次共通分割・元native正スペクトル/q/u再検証、独立既知場/二尺度/直線極限/保存不変を確認。格納batch変更後の新6件＋関連20件PASS、全handle終了0。次はH12-bのguard/順位と三水準f・場・RF診断。親H12/全goalは未完了。

H11完了（2026-09-21）。[曲線Hφの比較領域](CURVED_HPHI_COMPARISON.md)を受入。全二次参照領域と厳密native制限、非nested共通分割、全穴/軸役割を検証。新6件（4+2分割）＋既存20件PASS、全handle終了0。次はH12の元E/H比較と細分診断。全goalは継続。

H11進行中（2026-09-21）。[曲線Hφ比較領域](CURVED_HPHI_COMPARISON.md)を追加。完全P2参照領域、全native制限、非nested共通分割、全穴/軸役割を検証。新6件は4+2分割でPASS、既存回帰は実行中。場比較はH12、親の受入範囲は拡張しない。

H10-cと親H10を完了（2026-09-21）。[調整回復・条件別監査](HPHI_TUNING_IDENTITY_RECOVERY.md)。検索/最終細分の比較親と過去anchorを分離し、成功個別IDだけを評価へ使用。新7unit＋既存25unitとChrome4項目PASS、全350実装/24所有ファイル不変、全handle/サーバー終了0。次はH11の曲線Hφ比較領域。全goalは継続。

H10-c進行中（2026-09-21）：[調整回復版3](HPHI_TUNING_IDENTITY_RECOVERY.md)を追加。独立物理と停止条件の新6件は3+2+1分割で終了0。所有CLI/worker検査と既存回帰は実行中（out/h10-tune-recovery-20260921）。src固定を維持し、終了後に実ブラウザー受入・親H10監査を行う。H10-c/親H10/全goalは未完了。

H10-b完了（2026-09-21）：[所有回復履歴](HPHI_RECOVERED_HISTORY.md)を受入。写像pair要求版2、履歴版2の過去owned anchor/ID順検証、成功回復だけの後続継承、CLI/worker所有再生・延長を接続。新6unit＋既存25unitの分割証拠、Chrome4項目PASS、全handle/サーバー終端。数値後の差はGUI3pathだけで、349実装と48所有ファイルを最終照合。次はH10-c（検索試行/最終細分の調整回復）。親H10/全goalは未完了。

H10-b進行中（2026-09-21）：[所有回復履歴](HPHI_RECOVERED_HISTORY.md)を実装。写像pair要求版2の新2件と調整利用先2件はPASS。新履歴3件・専用回帰は実行中（out/h10-history-20260921）。実行中はsrcを変更しない。GUI履歴フォームが回復eventを落とすredを再現済みで、数値handle終了後に修正・操作検証が必要。H10-b/親H10は未完了、作業差分はまだ未コミット。

H10-a完了（2026-09-21）：[明示個別ID回復核](HPHI_IDENTITY_RECOVERY.md)を追加。独立同軸TEM/Bessel根の順位交換・解析q場・縮退部分空間、継承/anchor guard、集合外/集合境界、元場不変を確認。新8件の分割証拠＋既存履歴1件PASS、全handle終了。核は履歴の過去snapshotとの結び付けをまだ証明しない。次はH10-bの所有回復eventと成功IDのみの後続継承。親H10/全goalは未完了。

H09完了（2026-09-21）：[worker/GUI受入と条件別監査](HPHI_SHAPE_TUNING_GUI.md)。両形状の実中止/所有再開・管理器再起動、元サーバー正常終了後の新サーバー/新ブラウザー復元、全native/RF byte一致、現行src hash一致がPASS。全handle終端。検証器失敗と補完再生は分割証拠として保持。次はH10。

H09-d進行中（2026-09-21）：[worker/GUI操作受入](HPHI_SHAPE_TUNING_GUI.md)。版2の単位・対応範囲の画面説明を補修し、両形状の実中止/所有再開/管理器再起動validatorとChromeクリック検証器を追加。同軸workerと同軸保存結果の新ブラウザー表示はPASS。穴付きの両検証は進行中で、サーバー再起動後ブラウザー復元・H09統合監査は残る。出力を確認せず再実行しない。

2026-09-21 JST：H09-cの[要求版2・非一様直線Hφ調整](HPHI_SHAPE_TUNING.md)を接続。同軸3寸法/明示頂点変位、実二分、所有保存・CLI再開を確認。新7件の分割証拠と旧版18件（551.668秒）、穴付き変形の専用4実FEM validatorがPASS。元出力移動後の再生・全native/RF保持・改変拒否を確認し全プロセス終了0。次はH09-dの新写像worker/GUI操作受入。

2026-09-21 JST：H09-bの[非一様直線Hφ比較・射影・追跡](HPHI_MAPPED_TRACKING.md)を接続。TEM/Bessel縮退、E/H別内積、q/u射影、正逆・guard・元RF保持を確認。新10件は分割証拠、既存31件（459.244秒）＋収束3件PASS、全プロセス終了0。H09親は継続し、次はH09-cのstrict形状要求・実調整・所有保存/CLI再開。

2026-09-21 JST：H09-aの[明示写像と独立FEM分割の交差](HPHI_MAPPED_OVERLAP.md)を実装。全親被覆を有理数で検査し、非一様穴移動・正逆積分・別分割/番号置換を確認。既存8件と修正後新規4件の分割証拠PASS。試験参照式の初回失敗は保持。追加外部資料/依存/legacy参照なし。H09は進行中、次はH09-bの場移送・質量射影・追跡。

2026-09-21 JST：H08の[直線Hφ幾何対応](HPHI_GEOMETRY_MAPPING.md)を実装。明示区分アフィンと同軸寸法の全境界/穴/軸・正Jacobianを検証し、独立面積/回転体積・H02一様尺度一致を確認した。新4/既存22unit、計26件PASS（22.178秒、終了0）。追加資料/依存/legacy参照なし。場比較・調整への接続は次のH09。

2026-09-16 JST：H05のHφ調整所有保存・再生・新規出力への再開・CLIを受入。専用5件、H05指定の既存回帰/H04依存15件、専用validator 9実FEM・全17チェックがPASS。要求・全Project/native/RF・hash・判断履歴を保存し、solverなし再生、最終細分直前・未確認終端の再生、要求/係数/順序/親の改変拒否、元出力移動後の再生を確認した。詳細は[HPHI_TUNING.md](HPHI_TUNING.md)。次はH06のworker中止/再起動。H01〜H05完了、90カード中6完了。
2026-09-16 JST：H07のHφ調整GUIを接続。専用transport、実worker開始/中止後checkpointのreplay・別ジョブ再開、対象ID/実順位/元native場取込、二つの周波数ゲートとSI表示を追加した。`test_gui_hphi test_gui_hphi_tracking test_gui_hphi_tuning` 8件中7件PASS・既存HTTP 1件skip、終了0。JS構文とChromium headless画面初期化はPASS、loopback bind制約のため実クリック列は未確認。次はH08の同軸寸法/直線一般写像。

2026-09-16 JST：H03のstrict要求・独立試行生成を完了。細分と比較予算の決定・新3/既存11件PASSは[HPHI_TUNING.md](HPHI_TUNING.md)。次はH04、保存/CLIはH05。

2026-09-16 JST：今回の依頼は未完の全課題について作業者へ渡せる詳細計画の作成。[全体索引と開始指示](development-plan/README.md)、[90カードの一覧](development-plan/tasks.tsv)を追加した。計画の初手はB01の要件/証拠照合、最初の実装区切りはH01〜H07のHφ調整。今回FEM/製品変更はなく、以下の実装履歴と親33=10/16/6/1は維持する。

2026-09-15 JST：[平面RF調整GUI](GUI_PLANAR_TUNING.md)を接続。
新4/関連11unit、Chrome主実行10項目＋保存再生で補完3項目を確認。実中止/保存地点選択/別ジョブ再開、対象IDの実順位を表示。
8保存完了FEM＋中止未保存1試行、取込2件。API/GUI等の8組80配列/全RF一致、比較119/GUI全133ファイル保持（重複あり）。
全handle終端。Hphi系調整・一般形状/回復・D03等は残り、親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[平面RF調整の専用worker](PLANAR_TUNING_WORKERS.md)を接続。
新5種類の分割検証と関連32unit PASS。実中止/保存再開/管理器再作成、各checkpointの履歴prefixと元場保持を確認。
専用4実FEM＋診断1実FEM。APIとの4組40配列/全RF一致、72 nativeファイル保持。状態照合追加後は既存2ジョブを再検証。
全handle終端。平面調整GUI・Hphi系調整/D03等は残り、親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[平面RFの周波数調整](PLANAR_TUNING.md)を専用API/CLIへ接続。
新4/関連24unit PASS。専用12実FEMで二分探索・保存再開・解析周波数・独立尺度則を検証。
4組40配列/全RF一致、108保存ファイル保持。零近傍の成分検査失敗は保持し、質量ノルム/ベクトル場の検査で補完。
[物理別接続表](D02_PHYSICS_ROUTING.md)を更新。平面worker/GUI・Hphi調整・D03等は残り、親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[TEの境界を保つ置換計画自動生成](TE_REMESH_GENERATION.md)を限定受入。
新4/関連17unit、8対称条件の独立体積、実円弧6半領域FEMの尺度則・保存再生、GUI23項目PASS。
2組16配列/全RF一致、52 nativeファイル保持。336製品SHA不変、外部要求0。全対象プロセス終端。
入口のTE一律拒否を既存検査へ接続し、計算本体・物理閾値は保持。D02元要件照合・他物理/D03等と全goalは継続、親33=10/16/6/1。

2026-09-15 JST：[TEアフィン調整版4](TE_AFFINE_TUNING.md)のGUI/CLI・場/RF追加検証を限定受入。

2026-09-15 JST：[TE分割切替のGUIと実円弧検証](TE_PARTITION_GUI_AND_CAP.md)を限定受入。
調整版8 GUI12/実円弧Study版4 GUI8項目PASS。円弧調整は比較予算300000で停止し、別要求700000で保存再開・再生後TUNED。
新15半領域FEM（初回停止の3場を含む）、13組104配列/全RF一致、289 nativeファイル保持。物理閾値・製品コードの変更なし。
全handle終端。TE計画自動生成・他物理/D03等は残り、親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[TE対称形状のメッシュ交換・分割切替](TE_SYMMETRY_PARTITION_WORKFLOWS.md)をStudy版4・調整版8へ接続。
新5unitの分割検証と関連27unit 932.594秒PASS。8対称条件の独立体積・局所細分履歴、専用10半領域FEMで円筒解析周波数/CLI保存再開を確認。
独立/逐次/適応の4組32配列と全RF一致、117 nativeファイル保持。調整は元分割の最終細分へ戻り両1 MHzゲートを満たす。
全handle終端。実円弧分割・専用GUI・TE計画自動生成・他物理/D03は残り、親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[実円弧TE逐次・適応StudyのCLI・GUI](TE_CAP_STUDY_WORKFLOWS.md)を限定受入。
CLI保存再開と未確認停止、適応GUI10項目PASS。逐次GUIは初回6項目成功後の読込タイムアウトを保持し、別ブラウザー再生1項目で補完。
新16半領域FEM、既存API3解との16組128配列/全RF一致、247 nativeファイル保持。336製品SHA不変、全5GUIジョブ・専用プロセス終端。
変更は検証器と記録のみ。分割切替TE対称条件・他物理/D03は残り、親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[実曲線TE調整のCLI・GUI](TE_CAP_TUNING_WORKFLOWS.md)を限定受入。
多項式版14/指数式版11のGUI検査、両版CLIの最終細分再開がPASS。新8半領域FEM、API比較元6解を再利用。
8組64配列・全RF一致、182 nativeファイル保持、両1 MHzゲートと元セクター順位を確認。製品コード変更なし。
全4GUIジョブ・全handle終端。逐次/適応の実曲線GUI/CLI、分割切替対称条件・他物理/D03は残る。親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[曲線境界の座標別丸め余裕](CURVE_COORDINATE_BOUNDS.md)を修正・限定受入。
新3unit、独立Decimal390座標、実曲線の体積増分・Study/調整/保存再生を確認。専用12半領域FEM、GUI/API24配列・全RF一致。
full validatorは361モジュール1826件PASS（3 skip）、HTTPの1件を別実行で補完。残る2 skipは任意NGSolve。
9モード207量の比較で周波数差0、RF相対差最大8.88179e-16。full後の変更はUI説明2か所のみで、表示4項目と実画像を確認。
全handle終端。実曲線の調整/逐次/適応の専用GUI・CLI、分割切替対称条件・他物理/D03等は残る。親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[TE対称形状の非アフィンStudy・調整](TE_SYMMETRY_HARMONIC_WORKFLOWS.md)をStudy版3・調整版5/7へ接続。
新3unit 125.895秒と拒否1件0.366秒、関連14件914.249秒PASS。独立円錐台体積、多項式/指数式の実調整・細分・保存再開を検査。
専用折線壁9半領域FEMで独立/逐次/適応Studyを確認し、6組48配列と全RF一致、117ファイル保持。CLI履歴再生PASS。
実曲線workflow追加検証・専用GUI・分割切替対称条件・他物理/D03等は残る。親33=10/16/6/1、全計画goal ACTIVE。

次はHphiの周波数/ID/単位に対応する調整要求を実装する。
平面調整GUIはGUI_PLANAR_TUNING.mdの範囲で接続済み。13項目は10＋3の分割検証であり、一括PASSではない。
out/planar-tuning-gui-20260915に全記録。全worker/browser/serverは終了、再開すべき計算はない。
同一ファイル再読込を修正、投入データ照合の追加後は既存完了/中止checkpointを再検証した。
workerはPLANAR_TUNING_WORKERS.mdの範囲で接続済み。out/planar-tuning-worker-20260915に全証拠。
新規5種類の分割検証と関連32件、専用2ジョブの保存再開/2回の管理器再作成、API完全一致を確認。
全handle終端、実行中のジョブはない。初回probeはclaim集合診断用で成功件数へ加えない。
D02_PHYSICS_ROUTING.mdに現在の物理別接続と未完事項を整理した。
平面調整API/CLIはPLANAR_TUNING.mdとout/planar-tuning-20260915に記録。全handle終端、再開すべき計算はない。
TE向け置換計画自動生成は接続・限定受入済み。out/te-remesh-generation-20260915に全証拠を保存。
専用API/GUI/native照合は終了、GUIサーバーPID2812309も停止済み。再開すべき計算はない。
分割切替のGUI・円弧追加記録はout/te-cap-partition-20260915とout/te-partition-gui-20260915/tune。
初回300000組は最終比較で予算超過し、700000組の別要求はTUNED・再生PASS。全handle終了済み、再開すべき計算はない。
旧円弧候補の鏡映拒否は座標別丸めの変更で解消。元のjoin tolerance 1e-14 mを保持した実入力と失敗ログをoutに残した。
専用GUIサーバーPID2707565はSIGINT終了0、全5ジョブ終了。逐次初回検証はタイムアウト、補完再生と適応は終了0。
CLI補助は期待したUNVERIFIEDの終了値1で終端、native照合は終了0。全対象プロセスは終了しており、再開すべき計算はない。
操作要求1 MHzと独立体積/Maxwell不変量の検査を混同しない。詳細と集約結果はCURVE_COORDINATE_BOUNDSを参照。

2026-09-15 JST：[TE対称曲線Projectの非アフィン変形](TE_SYMMETRY_DEFORMATION.md)をAPI/CLIへ接続。
元/変形後の対称セクターと固定履歴を保持し、鏡映指定では各段階の全領域幾何も検査する。
新3件5.578秒/関連19件467.930秒PASS。新2半領域固有値計算＋既存鏡映1解を用い、実場・Green体積・尺度則を確認。
30ファイル保持、CLI Project全項目一致。非アフィン対称tune/Study・専用GUI・他物理/D03等は残る。
親33=10/16/6/1、全計画goal ACTIVE。

2026-09-15 JST：[TE鏡映場の非アフィン曲線比較](TE_REFLECTED_PIECEWISE_TRACKING.md)を版2/3/4/5へ接続。
元半領域の写像を全領域へ延長し、実際の両側Eφ・全体積・対称セクター順位と両側分の予算を保持。
新3件28.810秒/関連34件65.809秒PASS。既存4半領域解の鏡映、8保存比較/再生とCLI版5がPASS。
新規固有値計算0、元36/鏡映40ファイル保持。非アフィン対称Project/tune/Study・GUI・他物理/D03等は残る。
親33=10/16/6/1、全計画goal ACTIVE。

2026-09-15 JST：[TE半領域の非アフィン曲線比較](TE_SYMMETRY_PIECEWISE_TRACKING.md)を版2/3/4/5へ接続。
同一対称セクターの実Eφ・変動体積重み・保存再生を保持し、異セクター/鏡映/直線比較の誤受理を拒否。
新4件は分割成功、関連30件49.780秒PASS。楕円弧4実FEM・8保存比較/再生・CLI版5がPASS、48ファイル保持。
独立積分とMaxwell場/RF尺度を確認。鏡映の全領域写像、非アフィン対称tune/Study、他物理/D03等は残る。
親33=10/16/6/1、全計画goal ACTIVE。

2026-09-15 JST：[TE対称アフィンの調整・逐次/適応Study GUI/CLI](TE_SYMMETRY_AFFINE_WORKFLOWS.md)を限定検証。
Chrome調整12/逐次8/適応10項目、従来保存再生1項目、GUI関連11unitがPASS。
曲線タグの対称順位注意書き漏れを修正。当初調整12項目中の表示検査1件は不十分で、実描画の失敗再現/修正後1件で補強。
専用17実FEM（GUI10/CLI6/目標pilot1）、6組nativeの48配列/全RF一致、156ファイル保持。
磁気対称z_maxの鏡映例で停止再開・目標/細分ゲート・未到達目標保持を確認。非アフィン対称接続・他物理/D03等は残る。
親33=10/16/6/1、全計画goal ACTIVE。

2026-09-15 JST：[TE対称曲線のアフィン調整・Study](TE_SYMMETRY_AFFINE_WORKFLOWS.md)をAPI/nativeへ接続。
対称面を保つ式全体のゼロせん断を要求し、元セクター順位・保存再開・Eφ/Maxwell尺度を検証。
新4件は分割成功、関連20件と非アフィン2件PASS。専用5成功＋2診断FEM、65ファイル保持。
1 Hz目標の停止と別の1 MHz要求のTUNEDを分離。追加GUI Study12/新旧画面各3項目PASS、2FEM・16配列/全RF一致・57ファイル保持。
調整/逐次/適応の実GUI・CLI専用検証と非アフィン対称接続等は残る。
親33=10/16/6/1、全計画goal ACTIVE。

2026-09-15 JST：[TE曲線の対称領域・鏡映比較](TE_CURVED_SYMMETRY_TRACKING.md)の基盤を限定検証。
同一二次領域/せん断なしアフィンのEφ追跡、元対称セクターの順位、native再生を接続。
新3件18.547秒、関連27件39.086秒と14件6.134秒がPASS。専用半領域8 FEMと全領域dense4計算、104ファイル保持。
曲線対称/鏡映のtune・Study・非アフィン比較への接続は残る。親33=10/16/6/1、全計画goal ACTIVE。

2026-09-15 JST：[TE調整版8のGUI/CLI・個別ID回復](TE_PARTITION_TUNING.md)を追加検証。
Chrome12項目・関連14unitがPASS。専用9実FEM、5組nativeの30配列/全RF一致、99ファイル保持。
2モードの宣言集合から実EφでIDを回復し、回復失敗時の周波数未評価・停止も保存再生で確認。
全3GUIジョブ・全handle終端。曲線対称/鏡映・他物理/D03等は残り、親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[TE分割切替調整版8](TE_PARTITION_TUNING.md)を直接閉PEC・固定RFでAPI接続。
新3unitは分割証拠で成功、関連26件44.420秒PASS。粗いG/周波数差と比較予算の失敗も保持。
曲線26/27初期分割の原寸/倍寸調整と保存再生が合格。専用成功7＋診断8実FEM、場/RF尺度差最大3.23420e-14。
54ファイル保持、全handle終端。実GUI・ID回復・曲線対称/鏡映・他物理/D03は残り、親33=10/16/6/1、全goal ACTIVE。

TE版8のGUI/CLI・API回復とUI説明更新は完了。次はD02の残るTE曲線対称/鏡映を、
元のTE境界条件・保存形式・調整の要求と照合する。未対応の幾何を単に受理させず、
全領域との周波数/場/RFおよび対称セクターの順位を独立に検証して接続する。

2026-09-15 JST：[TE逐次/適応Studyの実GUI](TE_TRACKED_STUDY.md)を限定検証。
Chrome逐次8/適応11項目、完了再生は新ブラウザー各1項目で補強。GUI関連6unitもPASS。
専用7実FEM、7組nativeの42配列/全RF一致、144ファイル保持。全6ジョブ・全handle終端。
他TE形状/対称セクター/回復例、TE版8・曲線対称/鏡映・他物理/D03は残る。親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[TE逐次・適応Studyのnative読取](TE_TRACKED_STUDY.md)を接続。
新2件を含む24unitが76.496秒でPASS。逐次CLIは停止/再開後COMPLETE、既存独立掃引との2組全配列/RF一致。
適応CLIは初回BISECTから再開し、10点/17試行で元終点まで到達。専用計12実FEM。
実GUI・その他のTE形状/セクター/回復例、TE版8・曲線対称/鏡映・他物理/D03は残る。
親33=10/16/6/1、全goal ACTIVE。最終保存再生もPASS、165ファイル保持、全handle終端。次はTE逐次/適応Studyの実GUIと他TE形状/回復例を検証する。

2026-09-15 JST：[TEアフィンStudy](TE_AFFINE_STUDY.md)を直接閉PEC・固定RFで限定受入。
新規を含む23unit、GUI実経路12項目、説明修正後の定義/画面3項目がPASS。専用4実FEM。
2組nativeの12配列/全RF一致、57ファイル保持、Maxwell場/RF尺度差最大8.990e-15。
完了StudyのEφ追跡は接続済み。逐次/適応の実計算は未接続、版8・曲線対称/鏡映・他物理/D03も残る。
親33=10/16/6/1、全計画goal ACTIVE。以下の未完表記は各段階の履歴。

アフィン係数の重複JSONキーを元テキストのままサーバーへ渡し、FEM前に拒否する修正も実施。
Chrome TE12/TM10項目、GUI関連5件PASS。専用比較21実FEM＋解像度/目標pilot3実FEM。
7組native全配列/RF一致、元108ファイル保持。TE affine Study・版8・曲線対称/鏡映・他物理/D03等は残り、全goal ACTIVE。

開始HEADf4d8c37。数値核は前回から固定。app.jsのaffine formだけJSON.parseで重複を消していたため、
元JSONをrequest末尾へ付けて厳密server parserへ渡す（harmonicと同方式）。valid requestは完全一致。
web/index.htmlのアフィン未対応文言を更新。共通Chrome verifierに版4フォーム/重複拒否/係数RF復元を追加。
先行検証では空欄JSON.parseとフォーム反映前の読み取りがあり、waitを修正。失敗ログ全保持、先行4runはFEM0。
前回level3比較約500sを受けlevel2/3の2TE pilotを測定、1.1倍時δ22630.804Hzが元5e4Hz以内なのでlevel2を採用。
TM目標pilot1FEM。原寸/倍寸/4倍エネルギー各4trial=12FEM、CLI再開1、GUI TE4/TM4、比較21＋pilot3=24実FEM。
Maxwell全RF差4.441e-15、全セル重心Ephi/Hr/Hz差6.261e-14、全係数1.347e-14、エネルギー等分2.221e-15。
Chrome TE12/TM10項目、製品336SHA固定、外部通信0。両result.png目視、TE粗細22630.804/TM14962.132Hz。
7組native全配列/RF完全一致、元108ファイル保持。GUI関連5件19.657sPASS、node構文check0。
全6GUI Job complete。baseline PID2346994 SIGINT/session1385終了0、本検証PID2349993/session10637終了0。
最終browser/native/CLI/physical/fidelity全終了0、全handle終端。full/seed/hosted CI再実行なし。
正本TE_AFFINE_TUNING.md、out/te-affine-tuning-acceptance-20260915/acceptance.json、共有benchmark同名。
次：TE affine Studyのfixed契約を既存生成/実Study/保存へ接続（旧guardは残っている）。
その後TE版8分割、曲線対称/鏡映、実個別ID回復、他物理/D03。親33=10/16/6/1、goal ACTIVE。
Wine拒否は別残件、回避しない。

2026-09-15 JST：[TEアフィン曲線調整版4](TE_AFFINE_TUNING.md)を固定RF契約でAPI接続。
Eφのアフィン/同一曲線領域比較、native保存再開、Maxwell周波数則とせん断体積比を検証。
新2件は分割で成功、関連35件134.814秒PASS。実GUI・追加場/RF尺度・TE affine Studyは後続。
版8・曲線対称/鏡映・実ID回復例・他物理/D03を保持し、全計画goal ACTIVE。

開始HEADc65d58e。curved_project_transformはTEのfixed/direct closed P2のみ、RF加速座標を新設しない。
curved_same_domain_trackingはTE専用係数vでEphi=r*vを評価、TE/TM混在とTEreflection拒否。
affine_remesh_trackingはTE curvedを同helperへdispatch、Ephi_new/aと一定体積比a²cを明記。
saved_mode_trackingはTE affine_remesh/curved_same_domainを許可（非曲線TE affineはbackendで明示拒否）。
te_tuningは版4 fixedを許可。TE affine Studyの旧guardは未変更、次課題。
新test_te_affine_tuning.py：実一様尺度tune pause2/restart/最終粗細/N/A、合成coneせん断Ephi=rと体積比、同領域native再生。
初期25.244sはcoarse refinement失敗＋楕円shearがz範囲外。許容差5e4Hz維持、TE初期levels1→3。
合成coneの最初の入力にはcurve_chord_tolerance_m欠落があり、.001を明示して当該1件1.917sPASS。
levels3調整の501.345s実行はtunePASS、旧入力のcone1errorだけ。新2件は分割成功（単一全件PASSではない）。
関連35件134.814sPASS。全handle終端、GUI起動なし。製品sourceを実検証中固定。
次：TE affine版4の実GUI/CLI/場・RF尺度/保存一致を追加し、GUI旧未対応文言を更新する。
高細分の対称両メッシュ積分は重い（新tune約500s）。検証済み証拠を再利用し、数だけ更新する再実行はしない。
その後affine Study、版8分割、曲線対称/鏡映、実ID回復、他物理/D03へ。親33=10/16/6/1、goal継続。
正本TE_AFFINE_TUNING.md、out/te-affine-tuning-20260915。full/seed/hosted CIなし。Wine拒否は別残件、回避しない。

2026-09-15 JST：[曲線TE調整版5/7](TE_CURVED_TUNING.md)の実GUI・場/RF追加検証がPASS。
直接閉PEC・固定RFメタデータ・凍結履歴の範囲を限定受入。Chrome多項式14/exp式11項目、専用21実FEM。
原寸/倍寸/4倍エネルギー、全係数・全要素の場・RF/PEC積分尺度を分離検査。8組native全配列/RF一致、元108ファイル保持。
版4/8・曲線対称/鏡映・実ID回復例・他物理/D03は残る。親33=10/16/6/1、全goal ACTIVE。

開始HEAD1f37be1。製品変更はweb/index.htmlのTE対応範囲説明のみ。前回API実装と関連34件を再実行していない。
多項式要求はout/te-curved-tuning-20260915/gui-request.json、目標は同形状の保存Study周波数。
新exp要求は0.5+exp(x)-1の実曲線寸法、bounds[-.1,.1]でx=0が同じ目標形状。多項式への近似ではない。
原寸/倍寸/4倍エネルギー各4trial=12実FEM、全てpause2/restart/TUNED。CLI再開1FEM、GUI各4FEM、計21。
verify-physical.pyは保存12解を再読し、全係数・全セル重心Ephi/Hr/Hz・全RF量・PEC接線H二乗積分の尺度を分離。
最大RF尺度差3.109e-15、全セル場5.643e-14、係数4.323e-14、電磁エネルギー等分1.777e-15。
Chrome14/11項目PASS、製品336SHA固定、外部通信0。両result.png目視済み、最終粗細419679.131Hz/許容1e6Hz。
8組native全配列/RF完全一致、元108ファイル保持。両ブラウザー終了0、CLI/native/physical/fidelity終了0。
全6GUI Job complete、PID2308114 SIGINT/session86729終了0。全handle終端、live serverなし。
正本TE_CURVED_TUNING.md、out/te-curved-tuning-acceptance-20260915/acceptance.json、共有benchmark同名。
次：曲線TEの版4 affine追跡/変形のRF契約、版8分割、対称曲線/鏡映、実個別ID回復を順次接続する。
一般他物理/D03と全33親を保持。full suite/seed/hosted CIの新規実行なし。Wine拒否は別残件、回避しない。

2026-09-15 JST：[曲線TE調整の固定RF契約](TE_CURVED_TUNING.md)を多項式版5・式版7へ接続。
TEでは加速区間を追加せず、形状変形・凍結履歴・Eφ比較・最終細分・保存再開を保持。
新3件の分割検証と関連34件482.550秒がPASS。独立Green積分、専用TE Study2実FEMも確認。
実GUIと追加場/RF尺度検証は未実施。版4/8・曲線対称/鏡映等を保持し、全goal ACTIVE。

開始HEADf7c9e9e。curved_harmonic_deformation/studyはTEのfixedのみ許可し、TMの従来RF処理を保持。
TEはraw rfへactive_length/voltage_interval/phase_originを新設しない。
te_tuning guardは版5と7(curved_harmonic)を直接閉PEC/軸P2＋piecewise_remeshで許可。
版4/8、対称曲線/鏡映は引き続き拒否。shared Studyの生成も同fixed契約なので専用2点実行して検証した。
新tests/test_te_curved_tuning.pyは実多項式調整、式/Study/不正RF拒否、独立Green面積体積則の3件。
初期2件153.667sは多項式PASS、式の変数X=xに要求shape_changeが不一致で1error。
試験入力をparameter=xへ訂正し当該1件34.140sPASS、Green1件3.982sPASS。
関連deformation/harmonicStudy/harmonicTune/expression/TEtune/TEJob未接続拒否34件482.550sPASS。
関連session84331は終了0、全handle終端。専用Study2実FEMのread_job completeと両R/Q N/A確認。
GUI未起動。out/te-curved-tuning-20260915/gui-request.jsonは同Studyのx=.5保存周波数を目標に準備済み。
次：実GUI＋原寸/倍寸/エネルギーの場/RF尺度検証、native一致を追加しTE_CURVED_TUNING受入を固める。
GUIの旧TE曲線未対応文言もその実検証時に更新する。今はAPI接続の検証までで限定受入完了とはしない。
その後版4 affineと版8分割、曲線対称/鏡映、実ID回復例、他物理/D03へ進む。親33=10/16/6/1。
全suite/seed/hosted CI再実行なし。正本TE_CURVED_TUNING.md、out/te-curved-tuning-20260915。
Wine拒否は別残件、回避しない。全計画goal ACTIVE。

2026-09-15 JST：[曲線TEの宣言比較写像](TE_CURVED_TRACKING.md)をpiecewise_remesh版2/3/4/5へ接続。
実Eφと可変体積重みを保持し、非アフィン変形・独立積分・Maxwell尺度・native再生を検証。
型検査順と共通参照分割のTE入口を修正、最後の関連22件がPASS。旧TM保存互換も照合。
閉PECの直接曲線P2が対象。曲線TE tune、曲線対称/鏡映、他物理/D03は残り、全goal ACTIVE。

開始HEAD5df18b8。curved_piecewise_remesh_trackingがCurvedSolution/TESolutionの型を先に確認し、
TE/TM混在拒否、TEはEphi_V_per_mをsampling、TEのみphysicsメタデータ追加。TM文書は不変。
saved_mode_trackingはTEのpiecewise_remeshを比較版2..5だけ許可（直線比較版1は拒否）。
版4/5の幾何prepareはcurved_selection_transfer._prepareのallow_te=Trueを明示。
公開の領域選択転送は既定Falseを保持。幾何/被覆/境界/履歴の検査自体を緩和しない。
新4test：実非アフィン/保存・混在拒否・Ephi=r独立P2/dblquad・版3/4/5/尺度。
初期新3件PASS6.883s、関連33件44.634sは2error（非曲線のcase属性参照、版3の境界パラメータ不一致）。
型検査順と宣言ordered_curve_verticesへ訂正、12件41.246sで版4がTM限定prepareにより1error。
幾何prepareを上記限定接続して当該＋overlay/reference/selection transfer22件10.780sPASS。
独立にcorrespondence/overlay/partition_tuning18件41.317sPASS。失敗は全て後続で解消、分割証拠。
旧TM partition checkpointを修正前後に再生照合（新FEM0）。full suite/seed/GUIは未実行。
次：曲線TE tuneに版4/5/7/8を接続し、実形状変形・最終細分・native/GUIを検証する。
対称曲線/鏡映は別残件。非円筒個別ID回復例も残る。親33=10/16/6/1、D02と全goal継続。
正本TE_CURVED_TRACKING.md、out/te-curved-tracking-20260915。Wine拒否を回避しない。

2026-09-15 JST：[TE一般profile調整](TE_PROFILE_TUNING.md)をnormalized_profileへ接続。
非円筒の連動寸法・局所半径式、閉PEC/半領域/鏡映、保存再開と最終粗細判定を検証。
新2件51.729秒＋関連48件94.247秒PASS。専用尺度8FEM、Chrome11項目/4FEMがPASS。
5組native全配列/RF一致、元81ファイル保持。曲線TE・他物理調整とD03は残り、全goal ACTIVE。

開始HEAD ee65a15。te_tuning guardはnormalized_profileを許可、円筒写像だけ一定半径を要求。
要求版1/2/3/7、同端条件一対称面/鏡映、TE専用readerを保持。曲線/階段は拒否。
新tests/test_te_profile_tuning.py：連動全座標尺度と局所半径exp式、pause2/restart/最終細分。
初期nr12/nz18は粗細59.671kHzで目標10kHzを満たさず正しくREFINEMENT_FAILED。
nr32/nz48に増し、許容差を保って新2件PASS。GUI鏡映式は粗細3664.3188Hzで4試行TUNED。
関連48件PASS。専用原寸/倍寸各4実FEM、場/RF尺度差最大3.934e-14。GUI11項目、製品336SHA固定。
5組native全配列/RF一致、元81ファイル保持。全3GUI Job complete、PID2275569 SIGINT/session19940終了0。
全handle終端。検証driver初回constantをvalueと誤記してFEM前KeyError、訂正後PASS（ログ保持）。
専用成功比較12FEMのほか粗い診断4FEMと目標pilot2FEMあり。unit内部FEMは別。
次は曲線TE追跡の必要な実写像/重みを既存曲線比較へ照合して接続する。
非円筒の実個別ID回復専用例も残る（円筒の回復証拠を一般形状へ拡大解釈しない）。
full suite/seed/hosted CIなし。親33=10/16/6/1、D02/D03/全goal継続。
正本TE_PROFILE_TUNING.md、out/te-profile-tuning-20260915。Wine拒否は別残件、回避しない。

2026-09-15 JST：[TE一般profile追跡](TE_PROFILE_TRACKING.md)の体積重み付きEφ写像を追加。
閉PEC・同端条件の一対称面・鏡映に対応。解析積分、P1/P2左右両対称条件、保存再生、実FEM尺度則を検証。
関連40件は39成功＋失敗入力修正後1成功の分割証拠。専用4実FEMもPASS。
一般profileのtune接続と曲線TEは残る。D02と全計画goalは継続中。

開始HEAD103958e。te_profile_tracking.pyを追加、profile_mode_trackingはTEのみ専用dispatch。
saved_mode_trackingのTE native readerはnormalized_profileも許可。TE tuneの円筒guardはまだ維持。
独立Eφ=rの解析overlap (7/3)/sqrt(31/5) で可変体積因子を検査。
新4テスト、既存profile/TE円筒/TEsector/saved/history/TEtuneの40件28.674秒で1失敗。
旧TE拒否テストの代替paired_meshにvertex_pairsがなく別エラー。same_domainへ訂正し当該1件PASS。
専用4実FEMの最大場尺度差1.644e-14、RF尺度差8.549e-15。全handle終端、GUI起動なし。
次：TE tuneにnormalized_profileを接続し、非円筒の実形状調整/再開/回復/最終細分とGUIを検証。
曲線TE追跡と他物理調整は保持。正本TE_PROFILE_TRACKING.md、out/te-profile-tracking-20260915。

2026-09-15 JST：[TE円筒チューニング](TE_TUNING.md)を同端条件の直線円筒へ接続し、限定受入。
EφによるID、半領域・鏡映の元セクター順位、加速量N/A、保存再開・回復・最終粗細ゲートを保持。
関連53unit（52＋1の分割実行）、専用44実FEM、Chrome閉PEC9/鏡映11/旧TM9項目がPASS。
8組native全配列/RF一致、元114ファイル保持。一般TE形状・他物理調整とD03は残る。
親33=10受入/16進行/6他未受入/1範囲外、D02と全計画goalは継続中。

開始HEAD c92ba87。te_tuning.pyでTE専用native readerと全Job検証を追加。shared tracked Studyは変更なし。
要求1/2/3/7 profile、normalized_cylinder、直線一定半径P1/P2、同じ一対称面まで。外側回復6も接続。
候補生成後も円筒条件を検査し、内部で非円筒になる式は実FEM前に拒否。旧TM checkpoint再生は完全一致。
52unit113.689秒＋P1拒否1unit1.549秒PASS。専用12解析/尺度、6回復、CLI1、GUI4/4/17＝44実FEM。
周波数最大相対誤差1.619e-6、G .003716、場 .002055、尺度4.487e-14。鏡映全領域p2場 .001507未満。
Chrome製品335SHA固定、全9Job complete、PID2245893 SIGINT/session21213終了0。P1最終ログOK、handle消滅確認。
full suite/seed/hosted CI再実行なし。実FEM核は変更なし。詳細TE_TUNING.md、out/te-tuning-20260915。
次はD02の一般TE形状・曲線追跡と他物理調整を元要件へ照合する。ガード削除だけで対応扱いにしない。
D03一般制約付き探索も保持。Wine永続prefix作成済み、solver復元は自動承認拒否の別残件、回避しない。

<!-- partition-tuning-current-begin -->
2026-09-15 JST：[曲線分割切替tune版8](PARTITION_TUNING.md)を実装・宣言分割方式で受入。
初期接続/PEC境界分割/履歴の異なる候補を実値から選び、式変形・実FEM・比較版5・保存再開/ID回復へ接続。
関連36unit、専用39実FEM、Chrome新10/旧9項目がPASS。8組のnative全配列/RF一致、元124ファイル保持。
親D02の他物理調整とD03一般制約付き探索は残り、親33=10/16/6/1、全計画goal ACTIVE。

開始HEAD547e62b。要求8は曲線式7＋mesh_schedule、外側回復6は内部8を許可。
全候補事前検査、実値で候補選択→候補自身の弦数/履歴へ式変形。比較は実Project全履歴＋その候補chartの版5。
新3unit初回1失敗は矩形境界の向きとGreen期待符号の違い。期待符号訂正後36件80.402秒PASS、許容差変更なし。
専用曲線はPEC初期26/27候補でx=.05切替、.075目標の5試行、最終108要素。倍寸法も5＋pilot1＝11実FEM。
最大RF尺度差2.265e-14/全場1.297e-14未満。回復5実FEM/4回復で参照26/現在27を確認。CLI追加1、GUI新5/旧17。
Chrome新10/旧9、製品334SHA一致、8組native全配列/RF一致、元124ファイル保持。全6job完了、GUI PID2220488 SIGINT/session99016終了0。
全handle終端、live processなし。物理/solver核変更なし。full suite/seed再実行なし。
次：D02他物理調整の明示残件を、現在対応する物理・場追跡・元親要件へ照合し、未接続部分を実装する。
D03一般制約付き探索も保持。D02親は進行中。Wine復元の拒否は別残件で例外返答なし、回避しない。
正本PARTITION_TUNING.md、out/partition-tuning-20260915/acceptance.json、共有benchmark同名。
<!-- partition-tuning-current-end -->

<!-- curved-partition-schedule-current-begin -->
2026-09-15 JST：D02の[曲線分割候補](CURVED_PARTITION_SCHEDULE.md)の検証基盤を追加。
区間ごとの初期接続/境界分割/明示履歴と共通参照座標を検証する。tune/保存/GUIへの接続は次の課題。
矩形の解析面積/体積、曲線PEC分割でのP2領域差、従来の同一境界拒否を検査した。
親33=10/16/6/1、全計画goal ACTIVE。

開始HEADf8b0638。curved_partition_schedule.pyにbuild_partition_schedule/partition_index/partition_comparison_mesh。
参照版5の明示chartを採用。自動物理メッシュの境界から共通chartを推定する方式は未実装。
候補はsource_mesh/任意segments_per_curve/reference_vertices/全新履歴/角度下限を指定。
元Caseの物理/解析曲線/RFを保持、新markedは候補上で凍結、全段階の幾何/品質と共通参照被覆を検査。
schedule版1のbreakpoints等号は右側、値依存のみ。最大32候補。各比較にmax_pair_tests適用。
次：tune新要求版へ接続し、候補選択→式変形→実FEM→比較版5→保存/再開/ID回復を実装する。
前回の式版7と外側回復6を保持。最終細分/参照元それぞれの実値から候補を選ぶ。
初期接続と境界分割を変更できる明示方式を、全自動メッシャーと呼ばない。D02受入は未完了。
証拠out/curved-partition-schedule-20260915、API不在baseline終了1、新4件0.909秒PASS。
Wine拒否の例外返答なし、別経路回避しない。親33/全goalは継続。

関連12件5.020秒PASS（新4、既存参照分割6、既存再メッシュ拒否/履歴2）。
既存参照分割テストにはnative場の検査を含む。新tune経路の専用FEM/GUI/全suiteは未実行。
全handle終端、live processなし。詳細はout/curved-partition-schedule-20260915/acceptance.json。
<!-- curved-partition-schedule-current-end -->

<!-- expression-tuning-acceptance-current-begin -->
2026-09-15 JST：[単位付き式によるtune版7](EXPRESSION_TUNING.md)の追加実経路検証がPASS。
Chrome profile9/曲線9/旧版7項目、曲線Maxwell RF/場尺度則、指数軸長の実ID回復・再開/拒否を確認。
追加58実FEM、全9GUIジョブ終端、取り込み3場の全配列/RF一致、元29ファイル保持。
親D02の境界分割変更・他物理は残り、親33=10/16/6/1、全計画goal ACTIVE。

開始HEAD0706c70。製品変更なし、verify_gui_curved_harmonic_tuning.mjsに版7フォーム分岐を追加。
profile/曲線は元要求完全一致、duplicate式キー拒否、保存復元/再開/改変拒否/最終場をChrome検証。
曲線3解の2倍尺度比較は周波数/RF/全場・独立Green形状則PASS。pilot目標を精度基準にしない。
指数軸長の外側6/内側7回復は成功15/失敗2実FEM、14回復、粗Bessel誤差2.854e-5/細1.797e-6未満。
全handle終端。GUI PID2184772 SIGINT、session41794終了0、live processなし。
前回51unitを再実行せず利用。新版ブラウザー各9/旧版7、画像目視、取り込み3解のnative一致。
次：D02境界分割変更の元要件を実装へ接続。現在の式版7は曲線分割/元履歴を固定する。
独立比較版5の参照chartを用いた試行別再メッシュ・追跡・保存再開を設計し、適用範囲を縮めない。
他物理の調整とD03一般制約付き探索も残る。全計画goalは継続、Wine拒否は別残件で例外返答なし。
証拠EXPRESSION_TUNING.mdとout/expression-tuning-20260915/acceptance.json、共有benchmark同名。
<!-- expression-tuning-acceptance-current-end -->

<!-- expression-tuning-current-begin -->
2026-09-15 JST：D02の[単位付き式によるtune版7](EXPRESSION_TUNING.md)をprofile/曲線の実形状生成へ接続。
実FEM円筒調整・保存再開・途中定義域エラー保持、非アフィン曲線の独立面積/体積則を検証。
GUIコードも追加したが、実ブラウザーと曲線の専用RF/場検証は残る。親33=10/16/6/1、全計画goal ACTIVE。

開始HEAD7d3455e。要求版7 geometry_kind=profile/curved_harmonic、bindings=[{path,expression}]。
曲線pathも/case/geometryから。m/1の次元を対象葉から決定し、元形状へ全式を反映して調和変位。
外側回復版6は内部7を許可、比較は曲線版5と同じ実親/固定履歴。GUI新2選択肢と式JSON復元。
次：新GUI実ブラウザー、曲線実FEM/RF/場尺度則、版7の実回復・再開を検証。
関連8モジュール50件232.352秒PASS、回復要求の追加1件0.355秒PASS（計51件、分割実行）。
CLI/worker各1実FEM、保存12配列・全RF一致、元16ファイル保持。node --check終了0。
全検証handle終端、live processなし。実ブラウザー/曲線専用RF/版7実回復は未検証。
今回の詳細と証拠はEXPRESSION_TUNING.mdおよびout/expression-tuning-20260915/acceptance.json。
Wine本体復元は以前の自動承認拒否のまま、例外許可の返答なし。回避しない。
<!-- expression-tuning-current-end -->

<!-- scalar-expression-current-begin -->
2026-09-15 JST：D02の[非多項式スカラー式](SCALAR_EXPRESSIONS.md)の評価基盤を追加。
単位検査、数学関数、遅延条件分岐、有限実数の定義域、構文/深さ/ノード予算を検査し、新8件0.124秒PASS。
まだtune/Project/CLI/GUIには未接続。[D02監査](D02_CURRENT_AUDIT.md)の関数連動・境界分割変更等は保持する。
開始HEAD7061866。scalar_expressions.pyは定数{constant,unit}/変数{variable}/演算{op,args}の厳密木。
変数値・単位マップ、結果単位m/1を指定。中間の長さ次元指数はFraction、定義域はmathの有限実数。
四則/累乗/平方根/指数対数/三角双曲線/abs/min/max/atan2/hypot/floor/ceilと比較付きifを提供。
次：式によるprofile/曲線寸法の生成をtuneへ接続。全試行は実FEM、個別ID、目標差/細分差、保存再開・失敗保持を守る。
入力版の設計は未実施。既存tune版1〜5と外側回復版6は保持し、式版を明示する。既存多項式近似への置換はしない。
D02には境界分割変更/他物理の明示残件もある。D03制約付き探索と混同しない。
証拠out/scalar-expressions-20260915、API不在baseline終了1、最終8unit0.124秒終了0。既存製品利用先・FEMは無変更。
全suite/数値/GUIなし、live handleなし。親33=10/16/6/1、全計画goal ACTIVE。
以下はD01親受入までの履歴。
<!-- scalar-expression-current-end -->

<!-- d01-parent-current-begin -->
2026-09-15 JST：[D01の元要件と明示後続要件](D01_ACCEPTANCE.md)を監査し、親D01.S/I/Vを受入済みに更新した。
個別ID回復の全利用先接続と、異なる初期比較接続・境界分割への対応を含む21実行報告、検査内容、現在のソースを照合。
親33=10受入/16進行/6他未受入/1範囲外。D02/D03と全計画goalは継続中。以下の旧段階の未完表記は履歴である。
監査対象HEADf25da6e。原e6271c2のD01.S/I/VとBACKLOGの後続約束を照合し、前回残件2件の実装・検証を確認。
D01_ACCEPTANCE.mdとbenchmarks/tracking/d01-parent-acceptance-20260915.jsonが正本。
21数値/ブラウザー報告を読み取りSHAを記録。out/d01-parent-acceptance-20260915/evidence-inventory.json。
直前全検証後のmode_tracking/回復/Study/tune核は同一。製品差は比較版5分岐/新参照分割/GUIで、その42検査と専用FEM/GUIが別証拠。
全検証の移行テスト初回FAILと修正後分割PASS、NGSolve任意2skipは保持。単一の全validate.py成功とは扱わない。
今回は監査・文書だけ、新FEM/テスト/ブラウザーなし。全計画完了ではない。live handleなし。
次：D02原S/I/VとBACKLOGの任意関数連動・境界分割変更等の明示後続要件を照合し、必要な残件を実装する。
未対応物理や旧版互換性は他親課題のまま。Wine本体/SFCODESの復元は自動承認レビュー拒否で例外許可待ち、別経路回避禁止。
以下はD01個別機能の実装・検証履歴。
<!-- d01-parent-current-end -->

<!-- curved-reference-partition-current-begin -->
2026-09-15 JST：[明示参照座標による曲線比較版5](CURVED_REFERENCE_PARTITION.md)を実装・限定受入。
旧新の初期接続と境界分割が異なる場合に、各実P2写像と全親被覆を確認して保存場を比較する。
新6/既存36unitの分割42件、非アフィン4実FEM/独立重み積分/尺度則/CLI、Chrome新版11・旧版10項目がPASS。
元24ファイルとGUI取り込み4場の全配列/RF一致を確認。全handle終端回収。親33=9/17/6/1、D01親監査と全計画goalは継続する。
開始HEAD3b30e3b。要求版5はreference_vertices/declared_reference_polylines/max_pair_testsを各比較メッシュに明示。
初期chart辺と曲線別参照折線/タグを検査し、独立初期接続/追加境界点/全固定履歴を共通有理数分割へ写す。
各側の実P2局所写像を別々の親内座標から評価し、Jacobianを合成。旧版1〜4の契約は維持。
41unit37.673秒＋追加strict1unit0.081秒の分割42件PASS。初期redと予算拒否ログを保持した。
専用39.115秒4FEM：内部対角線変更＋軸境界分割、26/27比較・26/108実FEM、29共通三角形。
独立Hphi=r積分0.9954271360619864/観測0.9954271360619866、最大RF尺度差2.754e-14/場差2.708e-13未満。
Chrome新版11/旧版10、説明文修正後の最終新版11項目PASS。全外部HTTP0、画像目視。取り込み6jobすべてcomplete。
元24ファイルのSHA保持、GUI4場の全配列/RF完全一致、照合新FEM0。1080source後の差は説明HTML＋追加strictテストのみ。
全検証handle終端。GUI PID2136146 SIGINT、session59636終了0回収。live handleなし。
正本CURVED_REFERENCE_PARTITION.md、out/curved-reference-partition-20260915/acceptance.json、共有benchmark同名。
次：D01の元S/I/V・BACKLOG明示約束を現在の写像/回復/保存証拠へ照合し、親受入可否を判断する。
本版の境界対応は宣言であり自動推定ではない。親にない連続枝証明を追加せず、明示要件を撤回しない。
Wineは専用永続環境のみ受入済み。本体/SFCODES復元は自動承認レビューのコピー拒否で例外許可待ち、別経路回避禁止。
以下は基盤commitまでの履歴。
<!-- curved-reference-partition-current-end -->

<!-- reference-partition-current-begin -->
2026-09-15 JST：D01の[異なる初期接続の共通参照分割](REFERENCE_PARTITION.md)を計算基盤として追加。
全親面積の厳密被覆・独立二次積分・境界分割変更・二つの親内座標・番号/方向・不正入力/予算を新5件で検査。
既存交差分割4件と合わせ9件0.200秒PASS。曲線P2写像/実FEM/保存/GUIへの接続は未実装、親33=9/17/6/1を維持する。
開始HEAD95da156。元D01の一般写像を縮小せず、異なる初期比較接続と境界分割変更を継続する。
reference_partition.pyは明示した参照三角形をFractionで交差分割。正面積自己重複拒否、旧新各親の全面積を厳密に照合。
結果は正規化した共通三角形と旧新それぞれの親番号/重心座標。物理境界の対応・写像連続性はまだこの基盤では検証しない。
次：曲線比較入力に各初期頂点の参照座標宣言を接続し、二つの実P2写像と履歴を評価する。境界順/タグ・被覆/正Jacobianを検査。
その後、独立Green/体積重み・実FEM・次数/尺度則・保存CLI/GUIを検証する。既存版2〜4を保持し、新版を明示する。
証拠out/reference-partition-20260915、baselineのAPI不在red/geometry4件/最終selected9件を保存。新FEM0、live handleなし。
以下はtune回復までの完了記録。
<!-- reference-partition-current-end -->

<!-- tuning-identity-recovery-current-begin -->
2026-09-15 JST最終検証：[tune個別ID回復](TUNING_IDENTITY_RECOVERY.md)の曲線保存再生20解/10条件がPASS（追加FEM0）。
全339モジュール1742件の実行は1858.249秒で移行テスト3subtest ERROR、3skipを記録して終了1。
Study例をCaseとして読むテストを修正し、当該8件が0.383秒PASS。HTTP制限のskip1件も許可環境で0.563秒PASS。
最終証拠は1740件成功・任意NGSolve参照2件skipの分割実行。単一の全validate.py成功とは呼ばない。
標準数値は別の--skip-testsでPASS、既存9モード23量のf差0/最大相対差8.882e-16未満。曲線検証後のソース差は移行テスト1ファイルだけ。
受入索引out/tuning-identity-recovery-20260914/acceptance.json。全handle終端回収。親33=9/17/6/1、全計画goal ACTIVE。
開始HEAD991560a。要求版6は既存tune版1〜5と明示回復方針を組み合わせ、チェックポイント版2に全根拠を保存。
専用55FEM/worker19FEM、CLI追加1FEM、GUI新21/旧16項目と72完了FEMがPASS。native全17点は直接/worker/GUIで完全一致。
新9unit・関連51unit・TE直接利用先1unitの限定検証も保持。曲線再生2859.966秒PASS、325元/1075source不変。
milestoneの初回修正は重複キー関数のimport先を誤り1ERROR、project.parse_jsonへ修正後8PASS。初期ログは保持。
現在live handleなし、ソース凍結解除。tune回復の実装・検証・文書を一つの変更にまとめた。次は一般比較写像の残件へ進む。
D01監査準備はout/.../next-parent-audit.md。異なる実FEM接続は対応済みだが、比較用初期接続が異なる場合は未対応。
明示された一般写像/境界分割変更の残件を保持。入力契約と独立不変量案は未実装であり親受入の根拠ではない。
Wine永続環境は作成/単体検証済み。本体/SFCODESは自動承認レビューのinstallerコピー拒否で例外許可待ち、別経路回避禁止。
以下は前回以前の履歴。本ブロックを現在の状態として優先する。
<!-- tuning-identity-recovery-current-end -->

2026-09-14 最新：D01の逐次Study個別ID回復を要求版2・CLI/JobManager/GUIへ実装・限定受入。
開始HEAD2ed8c72。正本[TRACKED_STUDY_IDENTITY_RECOVERY.md](TRACKED_STUDY_IDENTITY_RECOVERY.md)、索引out/tracked-study-identity-recovery-20260914/acceptance.json。
新study_identity_recovery.recovery_requestsで完了Study/逐次Studyの回復指定検査を共有。元点/回復点の実際のProjectから写像を導出。
回復前2点で停止→1点追加で回復/停止→残り3点で再合流/回復済みanchor利用を接続。旧要求/チェックポイント版1は維持。
新7unit48.608秒+既存8モジュール44unit97.141秒=51件の二実行がPASS。変更前の版2不在redを保持した。
専用は基準/寸法2倍/U4各6点と失敗停止2点、20FEM53.017秒PASS。再開前ファイル不変・次点未計算・CLI再生・Bessel/Maxwellを確認。
追加worker8FEM26.550秒PASS。JobManager再作成後の再開とUNVERIFIED停止、直接実行との全6点の全配列・RF完全一致。
共有検査の完了Studyは既存18保存解を74.532秒で再検証PASS、新FEM0。専用数値と新版browser等は一部並行、単独性能と扱わない。
尺度則最大RF5.063e-14/場3.106e-14、解析周波数最大5.614e-6。全1067ソース系が実行中不変/最終一致。
Chrome新16/旧逐次11/旧適応10項目PASS、外部HTTP0、326製品SHA一致。元JSON文字列の重複拒否・回復状態列・改変拒否・編集無視の再開を確認。
GUIで完了した新FEMは計18解。新版6点は直接実行と全配列/RF完全一致、180ファイル不変、追加FEM0。
最初の追加native照合は配列/RF一致後のSHA lambdaがstrをPathと扱って失敗。検証器だけ修正し終端PASS、製品は無変更。
全16GUIジョブ13完了/3中止、専用GUI PID1931726をSIGINT終了、session58306終了0回収。全validator/worker/browser/unit終端回収、live handleなし。
全suite/seed/Hosted CI/新Wine比較は今回未実行。親33=9/17/6/1、全計画goal ACTIVE。
次は適応Studyへの回復指定とチェックポイントの接続、その後tune。適応では二分点が挿入されるため、元目標番号と履歴snapshot番号を混同しない設計が必要。
明記した一般写像残件は保持し、元要件にない連続枝証明を必須へ追加しない。
Wine専用永続領域/home/sin/.local/share/superfish-referenceは作成・単体検証済み。
旧installerコピーは自動承認レビューによる拒否で明示例外許可待ち。別経路で回避せず、SUPERFISH本体/SFCODESは未復元。
以下は完了Studyと以前の記録。

2026-09-14 最新：D01/P2-01の適応Study個別ID回復を実装・限定検証済み。開始HEAD2992794。
正本[ADAPTIVE_STUDY_IDENTITY_RECOVERY.md](ADAPTIVE_STUDY_IDENTITY_RECOVERY.md)、索引out/adaptive-study-identity-recovery-20260914/acceptance.json。
要求版2のtarget_index/anchor_target_indexは元目標番号。中点が増えた採用履歴へ実行時に結び付け、チェックポイント版3のattemptへ全回復根拠を保存する。
回復失敗は直前採用履歴を保持し、現在点を採用せずSTOP/identity_recovery_unverified。次点計算/二分/再開はしない。隣接PASSと回復失敗は別保存。
新8件41.647秒・関連46件83.750秒PASS。変更前red、最初の2不変条件22.074秒も保持。
pilot3FEMの実重なりから固定閾値0.9999999988を選び、元anchorより前の二分を実現した。許容差緩和なし。
専用25FEM37.820秒・worker11FEM17.482秒PASS。元目標1→snapshot2、回復済み元目標3→snapshot4で2回回復。
前半は解析縮退、後半は明示gap=.2による近接集合であり、2回の物理縮退とは書かない。
Bessel最大差2.742e-5未満、Maxwell最大RF差5.219e-14/場差1.872e-14。q12/18と逆向きは保存解を再利用。
worker再作成後の全7native配列/RFと、Chrome新版7点の同量は直接実行と完全一致。GUI比較の新FEM0、210元ファイル不変。
Chrome新版15/旧適応10項目PASS、外部HTTP0、画像目視済み。GUI完了解16FEM、全12ジョブ10complete/2cancelled。
1070ソース系と327製品SHAは最終一致・実行中不変。数値/GUIの一部は並行、時間を単独性能としない。
全新検証handle終端回収。関連regression45191の最終出力はコンテキスト切替時に保持されず、再照会はunknown。ログは46件OK。
専用GUI PID1977513へ完全argv照合後SIGINT、session71946終了0回収。現在live handleなし。
全suite/seed/Hosted CI/新Wine比較は未実行。親33=9/17/6/1、全計画goal ACTIVE。
次はtuneへの回復指定・チェックポイント接続を1限定課題として設計し、その後D01一般写像残件と元親要件を監査する。
元D01にない連続枝証明等を必須に追加せず、明記した一般写像要件は保持する。
Wineは/home/sin/.local/share/superfish-referenceに専用永続環境作成・単体検証済み。
旧installerコピーは自動承認レビューの2回拒否で明示例外許可待ち。別経路で回避しない。SUPERFISH本体/SFCODESは未復元。
以下は逐次Study回復までの記録。

2026-09-14 最新：D01の完了済みStudy個別ID回復を要求版2・API/CLI/GUIへ実装・限定受入。
開始HEAD b14b62e（単独履歴回復のcommit）。正本[STUDY_IDENTITY_RECOVERY.md](STUDY_IDENTITY_RECOVERY.md)、索引out/study-identity-recovery-20260914/acceptance.json。
identity_recoveriesの各point_index/anchor_snapshot_index/controlsを全入力検査し、指定した実際の2点から写像を導出する。
回復成功後はIDを後続点へ渡し、失敗後は元集合と元比較を保存して未追跡点を残す。旧要求版1・Study独立スペクトル・nativeは保持。
GUIの既存Study読込→末尾回復→版2保存/再生に接続。複数点の事前指定はCLI/API、逐次/適応workerやtuneは未接続。
unit最終54件=50件19.852秒+曲線Study直接利用先3件237.351秒+追加表面収束拒否1件7.055秒の分割証拠。
新テスト8件。初回NumPy float fixture拒否、修正後の版2不在red、表面収束の拒否順を誤認した初回失敗を保持した。
専用は基準/長さ2倍/U4の各6点、18FEM。初回は解析零のErを自身のノルムで割る検証器の判定で停止した。
問題のEr相対差2.428e-9、電場全体に対する差1.010e-14。Eベクトルのノルムへ修正し、同じ18解を19.333秒PASS、追加FEM0。
解析周波数最大5.614e-6、尺度則RF最大5.063e-14/場最大3.106e-14。次数12/18、2回復/回復済みanchor/失敗停止/旧文書保持/CLIを確認。
Chrome新版8/単独履歴17項目PASS、外部HTTP0、新FEM0、画面目視済み。325製品SHAと282元Study/nativeファイルは不変。
数値1064ソース系以後の差はStudyブラウザー検証器と追加表面収束テストのみ。製品は変えていない。
全検証終端回収。取込3ジョブcomplete、専用GUI PID1903279をSIGINT終了、session81929終了0回収。live handleなし。
全suite/seed/Hosted CI/新Wine比較は今回未実行。親33=9/17/6/1、全計画goal ACTIVE。
次はtrackedStudy/適応Study/tuneへの回復方針とチェックポイントの接続。元D01にない連続枝証明を必須に追加せず、明記した一般写像残件は保持する。
Wine専用永続領域/home/sin/.local/share/superfish-referenceは作成・単体検証済み。
旧installerコピーは自動承認レビューによる拒否で明示例外許可待ち。別経路で回避しない。SUPERFISH本体/SFCODESは未復元。
以下は単独履歴回復と以前の記録。

2026-09-14 最新：D01/P2-01の単独履歴で分裂後の個別モードID回復を実装・限定検証済み。
開始HEAD9e1c13c。正本[MODE_IDENTITY_RECOVERY.md](MODE_IDENTITY_RECOVERY.md)、索引out/mode-identity-recovery-20260914/acceptance.json。
以前の全個別ID確認済みnative場と現集合を比較し、全個別対応/集合内一致だけを回復。元stepsと場は保持、版3イベントへ根拠を保存する。
回復後の継続・再合流後の複数回復・回復済みanchor・失敗UNVERIFIED保存/停止・厳密再生/改変拒否をAPI/CLI/単独履歴GUIへ接続した。
関連65unitは5.842秒PASS。独立座標固有空間の置換/集合境界違反はAPI不在のredを先に確認。
専用は初回9FEM保存後、検証器がnative読込結果にmassを要求して失敗。保存済みRFの利用へ修正し、同じ9解を再検証して4.188秒PASS、追加FEM0。
Bessel解析最大差5.614e-6、Maxwell最大RF差3.220e-14/場差1.848e-14。次数12/18、尺度1/2、U1/4で回復・継続・縮退拒否を確認。
Chrome17項目PASS、外部HTTP0。初回13項目後の同名ダウンロード検証器失敗は元履歴別保管で補修した。製品は変えていない。
最終レビューで旧履歴版1の不要な回復ボタンを再現・補修。旧履歴2項目と全17項目を最終製品で確認した。
数値1062ソース系からの差はブラウザー検証器とapp.jsのボタン条件。325製品SHAと108native保存ファイルは最終一致。
全実行終端回収。最後の3GUIジョブcomplete、専用GUI PID1882122をSIGINTで停止しsession39270終了0を回収。live handleなし。
全suite/seed/Hosted CI/新Wine比較は今回未実行。親33=9/17/6/1、全計画goal ACTIVE。
次はStudy/逐次Study/適応Study/tuneへ回復方針・イベントの保存/再生を接続する限定課題を設計する。現在は自動回復未接続。
元D01にない連続枝証明等を必須へ追加しない。一般写像の明記残件は撤回しない。旧mode_index・RF規約・停止契約を維持する。
Wineは/home/sin/.local/share/superfish-referenceに専用永続環境作成・単体検証済み。
旧installerコピーは自動承認レビューの拒否で明示例外許可待ち。別経路で回避しない。SUPERFISH本体/SFCODESは未復元。
以下は回復実装前のD01監査および過去履歴。

2026-09-14 最新: D03版3をdb8cd8fでコミット済み、worktree cleanからD01元要件監査へ進んだ。
[D01_CURRENT_AUDIT.md](D01_CURRENT_AUDIT.md)、out/d01-original-acceptance-20260914/audit.jsonが最新監査。
56選択検査（50件4.089秒+6件0.308秒）と6新FEM（円筒交差2・合流分裂3・多対多1）はPASS。1059ソース系は不変。
多対多retain_connected_subspaceは既実装。初期の未完了表記だけを見て再実装しない。
BACKLOG1052/1093付近は分裂後個別枝回復の完遂を明示しており、現在の要求/API/履歴に回復経路がない。
親D01/D02/D03の受入を完了へ変えず、個別枝回復の数学/保存/曖昧時拒否を次の限定課題として設計する。
過去の個別ID確認済みnative場と現在の集合の対応を使う案を記録したが、まだ実装/受入していない。
今ターンの全検証は終端、live handleなし。全計画goal ACTIVE、親33=9/17/6/1。
Wineの旧installerコピーは自動承認レビューによる拒否で明示例外許可待ち。別経路で回避しない。
以下はD03までの記録。

<!-- current-rf-geometry-begin -->
2026-09-14 最新状態: D03/P2-02の単位付き多変数曲線寸法RF探索版3の実装・限定検証を完了。
開始HEAD6e746d2、途中のWine永続化文書commit1de6f71。親33=9受入/17進行/6他未受入/1範囲外、全計画goal ACTIVE。
正本は[RF_OPTIMIZATION_GEOMETRY.md](RF_OPTIMIZATION_GEOMETRY.md)。索引はout/rf-optimization-geometry-20260914/acceptance.json。
新geometry_termsは既存曲線leafを多変数多項式で同時変更し、調和変位/元固定履歴/実3水準・最終別3水準/個別ID/厳密保存再開へ接続。
関連29unitは937.813秒で28合格/1ERROR。軸原点契約に反したfixtureだけを軸長変化へ直し、別1件0.818秒PASS。
専用数値終了後にその合格済みfixtureをrepoへ反映。他の試験ASTは同一。module docstringのTwo-variable表記だけも修正した。
最終36FEMは6206.019秒PASS、handle68843終了0を回収済み。1059ソース系は実行中不変、後続差はfixture/docstringのみ。
基準/無次元半径/寸法2倍の各4試行がCRITERIA_MET、両変数探索・全native再生/改変比較履歴拒否・固定履歴・Green/MaxwellのRF/場を確認。
探索146/584/2336、最終584/2336/9344要素。基準目的の上側包絡1614723199.2864945→1599730640.1691456Hz、TRIAL_LIMIT。
尺度則最大RF/区間1.530e-13、内部H/Er/Ez1.132e-13。benchmarks/optimization/curved-geometry-20260914.jsonに保存。
初回粗い12FEMは初期/探索候補NOT_CONVERGED・不採用、最終だけCRITERIA_MET。検証器のeligible値ありの仮定がTypeErrorとなった。
許容差/法則/範囲を変えず、入力例の元固定履歴をmarked→uniform→markedへ増した。初期失敗と全原入力はindependent/に保持。
Chrome新版24/旧版13/追加入力11項目PASS。324製品SHA一致・外部HTTP0、元場/表面評価/改変拒否/中止再開/3変数混合項/編集競合を確認。
新版browserは固定1段の粗いsnapshotで、最終入力例の固定3段と区別する。新旧各完了系列6FEM。追加入力の新FEM/workerは0。
CLI粗系列との既存6水準は10native配列と全RF mode数値が完全一致。Case hashは各原JSONを個別照合。新FEMなし。
全8GUIjobの終端確認・専用GUI停止済み。現在この課題のlive sessionは0。全suite/seed/Hosted CI/新Wine比較は未実行。
次はD01/D02とN03の元.S/.I/.V・依存を最新証拠へ照合し、D03親の受入を判断する。
任意関数/新物理/一般性能保証など元行にない拡張を、無条件に親の必須へ追加しない。次工程メモはout内next-parent-audit.md。
Wineは専用永続領域で単体動作PASSだが、旧installerコピーは自動承認レビューが2回拒否。許可待ちを回避せず、本計画の独立作業を進める。
以下は過去履歴。
<!-- current-rf-geometry-end -->
今回はD02/P2-02の非アフィン曲線寸法tune版5を実装・検証したprogress。全計画は未完、goal ACTIVE。親33=9受入/17進行/6他未受入/1範囲外は不変。
[CURVED_HARMONIC_TUNING.md](CURVED_HARMONIC_TUNING.md)が入力/数学/受入/制約/初期失敗の正本。
元Studyのgeometry_coefficientsをtune版5へ接続。native曲線P2・真空closed PEC/axis TM・非組立/非鏡映・全marked固定を要求する。
毎試行を元Projectから調和変位で構成し、rf_coordinatesはfixed/axis_fraction。controlsはpiecewise_remesh、comparison_meshesは入力禁止。
実試行の元弦メッシュと元Projectの全固定履歴から比較メッシュ版2を導出する。最終細分後も比較側の履歴は元のものを使う。
採用親の同じ二次領域へlog2(refinement_scale)回のuniform制限を追加し、場はそれぞれの実FEM空間から評価する。採用親が端点0のケースも検証済み。
FEM/求積/規約/探索判断/二つの周波数許容ゲートは不変。版1〜4の契約、外側checkpoint版1、strict完全再生を保持する。
GUIに曲線寸法の法則ひな形/入力/復元を追加。元法則文字列と調整要求文字列を厳密サーバーパースし、重複キーを開始前に拒否。既存辞書APIも維持する。
入力準備中の形状/調整設定変更を検出。保存再開は元checkpointの条件を使い、現在のフォーム編集を採用しない。
新独立2unitは版5/API不在でred（baseline.log、終了1）、実装後15.796秒PASS。最終35unit309.382秒とtuning_jobs7件7.212秒、合計42がPASS。
対象はtest_curved_harmonic_tuning6件、curved_tuning/tuning/coupled_tuning/polynomial_tuning/gui_tuning/tuning_jobs。独立幾何、厳密入力、採用端点親、保存/改変拒否、旧版/実workerを確認。
専用validate_curved_harmonic_tuning.pyは18新FEM758.895141秒PASS。基準/m表現/寸法2倍は各4試行、146/146/146/584要素、0→1→0.5→0.5（mは1/10）。
独立Green面積1+x/8/体積(1+x/8)^2、最終領域不変、両RQ/G/TTF/fのMaxwell/単位差最大2.221e-14、各要素2点H/Er/Ez最大2.774e-14。最小重なり.997724。
別円筒4試行はTM011順位3→2、解析f最大差2.176e-5/最終1.322e-6。無効内部形状は端点2FEM後、半径負の中間値でfailure-003のみ保存し、先行checkpoint完全再生を確認。
examples/tuning/curved_harmonic.jsonは合成半楕円対と固定marked→uniform→marked、26元要素。目標1525146908.755006Hzはx=.5の予備1FEMで選び、独立精度参照としない。
専用18FEMに予備1FEMは含めない。数値はbenchmarks/tuning/curved-harmonic-20260914.json。数値中1055ソース系SHA不変、以後の変更はブラウザー検証器だけ。
Chrome最終新版12/旧版7項目、4/17新FEM、外部HTTP0、323製品SHA一致、フォーム/結果を目視。
初回browser-newは3項目後に検証器が前の入力生成完了を待たずFAIL。埋込Projectのsemiaxes数まで数えていたため、期待法則辞書との一致待機へ検証器だけ修正。
修正後browser-correctedは全経路を再実行。実行中の製品は無変更。一時/tmp検証器で確認後、数値完了後に同一バイトをrepoへ反映した。
CLI/GUI全4試行の保存固有値/係数/二次幾何/接続は完全一致、Case/元弦mesh/RF数値も一致。32保存ファイル不変、.028秒、新FEMなし。
初回results.json全一致はCaseのJSON int/float表記に由来するcase_sha256差で失敗。各側の原JSONでhashを個別確認してから残りを全比較し、製品replayを緩和していない。
証拠索引out/curved-harmonic-tuning-20260914/acceptance.json。全handle終端: baseline同期1、geometry83267=0、selected24580=0、target17689=0、jobs61685=0、数値56991=0。
Chrome初回28336=1、修正37116=0、旧版66525=0。GUI13530/PID1626635は全worker completeを確認し、完全argv再照合後SIGINT、終了0。
全suite/seed/Hosted CI/新Wine比較は今回未実行。影響は調整器/直接利用先へ限定し、並行時間を単独性能としない。新規外部資料/依存/旧資産/skill/subagentなし。
次はD02一般関数/他物理の調整、D03一般形状変数の非アフィン探索、D01/N04/G03/C00.V等の残件へ進む。今回の接続受入を親D02全体へ拡張しない。
.git書込はrequire_escalated。以下は過去履歴。

2026-09-14 JST 最新継続状態。開始HEADb60e8c1、当初clean。前goalターンはA01比較とADR受入/commitでprogress。
今回はD03/P2-02の固定局所細分履歴をRF探索へ接続し、仕様/実装/検証を完了したprogress。親D03全体と全計画goalは未完、ACTIVE。
[RF_OPTIMIZATION_HISTORY.md](RF_OPTIMIZATION_HISTORY.md)が入力・数学・検証・失敗の正本。親33=9受入/17進行/6他未受入/1範囲外は不変。
要求版2は全markedにsplit_patternと明示元メッシュを要求し、freeze-curved-refinementを先に行う。暗黙固定なし。一様だけの履歴も受理。
元Projectから各形状へ変形し、Studyのadditional_uniform_refinementsで元履歴の後ろへ探索0/1/2・最終1/2/3回を追加。版1の履歴拒否は維持する。
表面評価版2は最初の履歴の末尾uniformを除く固定接頭部分と、その後の増加するuniform回数を保存/再検証する。途中挿入・marked変更・Case/源メッシュ変更・逆順を拒否。
refinement_levelは固定接頭部分の後のuniform数。元Projectの末尾uniformも含む。旧版1の文書/行とRF設計/探索checkpoint外側の版1は維持。
製品変更はrf_optimization.py/surface_convergence.py/web/app.js/index.htmlのみ。FEM/求積/規約/五量許容差/探索アルゴリズム/総予算は不変。
GUIは固定履歴時に要求版2を作り、読み込んだ版も保持。元履歴の後の全域細分を結果に表示し、表面評価版2の段数・元場を表示する。
baseline-red.logは新2件で要求版拒否とCaseの履歴/前置段数競合を再現、終了1。追加5件の初回は4合格/1失敗2.761秒。
失敗はmesh_dataを除いたProject版2が探索器の前にProjectパーサーで拒否する検証入力。Project版1へ直して探索器の明示元メッシュ必須を検査、製品は緩和なし。
selected-tests.logは8モジュール29件614.814秒PASS。新5件、既存の表面/設計/実FEM探索/GUI transport/JobManager中止再開/所有と予算/改変拒否を含む。
専用validate_rf_optimization_history.pyのindependent/validation.jsonは24実FEM897.259692秒PASS。両尺度の各4試行、探索43/172/688要素・最終172/688/2752。
値は[1,1]→[1.01,1]→[1.01,1.01]→同値最終、両尺度SEARCH_COMPLETE/TRIAL_LIMIT。CLI途中保存/再開/replay、全native場/判断/固定接頭部分と偽造拒否を確認。
球形解析最大差f2.472e-5/RQ2.231e-6/G1.076e-7/E比1.782e-4/B比3.700e-6、元許容内。各二次境界の独立Green面積/体積と細分不変を確認。
長さ2倍・U1→4JのRF五量尺度差最大7.039e-14、全要素2点H/Er/Ezの1/√2則最大9.762e-14、面積4/体積8倍差0。
1050src/tests/scripts/examples SHAは専用検証中不変。その後の変更はverify_gui_rf_optimization.mjsの検証器補修だけ。製品322SHAは専用/全3browser/最終が一致。
Chrome browser-v1は13項目PASS。browser-v2は12項目成功後、検証器が派生表面診断9箇所のfloat0.0/1.0をJSでint0/1へ再符号化し、完全再生に拒否され終了1。
数値/製品を変えず、サーバーserialized文字列をPythonで抽出するよう検証器を補修。--checkpointで既存完了文書を開く限定確認を追加。
browser-v2-replayは14項目PASS、後半の新FEMなし。初回12には実worker中止・所有checkpoint再生/編集に影響されない再開、後半14には表面版2・元場2水準・固定分割保持を含む。
新版は分割証拠で初回FAILを保持。各browser外部HTTP0、フォーム/結果画像を目視。各worker完了解6は中止別分岐の部分計算を含む総呼出し数ではない。
主要数値はbenchmarks/optimization/frozen-history-20260914.json、再現入力はexamples/optimization/frozen_history_rf.json。全証拠索引out/rf-optimization-history-20260914/acceptance.json。
全handle終端: 初回追加5件90390=1、最終unit50912=0、専用60417=0、Chrome初回75352=1、旧版99685=0、補修後12493=0。
専用GUI91603/PID1560264は完全argvを再確認してSIGINT、終了0。workerはcomplete/cancelled、GUIserver/検証processは残さない。
全suite/seed/Hosted CI/新Wine比較は未実行。直接利用箇所へ影響を限定、過去full失敗をfull PASSへ変えない。新規外部資料/依存/旧資産/skill/subagentなし。
次はD03一般形状変数/非アフィン探索、D02/D01/N04/G03/C00.V等の残件へ進む。今回の接続受入を親D03全体や他物理の完了へ拡張しない。
gitメタデータはrequire_escalated。以下は過去履歴。

2026-09-14 JST 最新継続状態。開始HEADfe1c8a8、当初clean。前goalターンは共通履歴再構築共有の実装/検証/commitでprogress。
今回は未着手だったA01/P0-04のcavsim2d役割比較を実行し、ADR-018と原要件照合まで受入したprogress。全計画は未完、goal ACTIVE。
[A01_BACKEND_COMPARISON.md](A01_BACKEND_COMPARISON.md)が仕様/出典/失敗/数値と受入照合の正本。親33は9受入/17進行/6他未受入/1範囲外へ更新した。
COMPATIBILITY_PLANの現在の親集計、BACKLOGのP0-04、IMPLEMENTATION_STATUSも更新。過去8/17/7/1は当時の履歴として保持。
判断は自作NGを製品として維持し、cavsim2dを限定した独立参照候補にすること。公開API全般や旧互換の受入ではない。
cavsim2d0.1.0の固定commit48741ff46ca44463281a5ab5945328615881b502。README/MIT LICENSE/pyprojectと現代的NGSolve Pythonの入出力/規約を参照した。
78選択Python/metadataを取得後、必須importの現代的ABCI wrapper1個を加え全79。全SHAとLICENSEを保持、ABCI/TopDrawer実行形式・旧SUPERFISH/POISSON実装の取得/実行なし。
比較専用/tmp/superfish-a01-reference-20260914にNGSolve/Netgen6.2.2606、Gmsh4.15.2、NumPy2.5.2/SciPy1.18.1等を導入。core importのIPython必須化を再現し公式jupyter extraを補った。
通常製品env/pyproject/FEM/求積/許容差不変。全依存版/ライセンスは専用文書とbenchmark JSON。約1.1 GiBの隔離環境は配布しない。
公開PillboxでR100/L80/Ri20mm、beampipe none、bc11/ee指定でもPMC長.04mが残ることを実FEM/保存meshで確認。閉PEC照合には使わず失敗として保持。
最終比較器scripts/compare_cavsim2d.pyはCavityを派生し公開Profileで4辺PEC/AXIを明示。SIの両端半径/長さとa01-profile.json/専用kindを保存し、未使用Pillbox deckを残さない。
この比較用モデルを標準Study.load対応とは主張しない。候補のFEM/求積/RF実装は無変更、NGmesh/行列/場を参照へ渡さない。
候補の実保存空間HCurl×H1のDOFを数える。表示値はHCurl部分のみ。requested1でもpadding3モードを解くことを報告し、NG1モードと演算量が同一とはしない。
円筒R.1/L.08m、円錐台R.08→.1/L.12m、NG P2 nr12/24/48 nz2nr、候補h20/10/5mm p2、全真空PEC・beta1。元タグ/辺長/面積/体積を双方で独立照合。
候補保存場のUe/Uh/報告UとTE比を検査し、U1Jへ一括正規化して内部12点E/Hを単一符号で照合する。zはL/2だけ平行移動。
R/Qは|V|²/(omega U)の値からaccelerator定義へ対応、circuitは半値。外部呼称の違いを式なしで読み替えない。
最終out/a01-backend-20260914/final-corrected/comparison.jsonは36実FEM/10.435824秒PASS、1047ソース系と候補79SHA不変。import実パス/SHAも別確認PASS。
最終両側差最大、円筒f2.283e-8/RQ1.021e-6/G2.750e-4/E1.848e-5/H2.671e-4、円錐台f2.567e-8/RQ2.050e-6/G5.178e-4/E2.141e-5/H2.190e-4。
双方最終細分も元許容f1e-4/RQ/G.005、円筒解析五量とピーク比.01に合格。Ue/Uh最大1.33e-10、報告U差2.69e-10、TE比7.85e-27。
最細NG18721DOF、候補円筒9049/円錐台12733。時間中央値NG.64128/.63853秒、候補.42343/.66198秒。3回交互順、import/独立reload除外、各native出力込み。一般性能保証としない。
benchmark主要数値/全3回/全環境版/候補SHAと2図はbenchmarks/cavsim2d/。両図を目視し、時間軸のラベル重なりだけを元測定値から再描画で修正した。生出力601件のSHA索引out/a01-backend-20260914/acceptance.json。
新unit4件.026秒PASS、既存判定5件は初回10件実行でPASS（当時物理2skip）、別参照環境の物理2件.113秒PASS。最終11件の分割証拠。
初回比較器はHphiの1-tupleで失敗、次は直線Caseへの曲線求積指定、次はFieldSampler生成APIで失敗。修正後measuredは1回12solve数値PASS。
その後、入力記録も正しくするため専用Cavityへ変更。最初は基底がn_cellsを保持せず失敗、明示属性で修正し最終36solveがPASS。初期失敗を保持、候補数値コードは補修していない。
全handle終端: metadata20146/venv91830/source51112/deps46670/extra88424/import99339/public80074/Hprobe26077/measured22955/final68940/plot7902/import-provenance64557/plot-correction18245=終了0。
比較失敗18768/82959/93500/21802=終了1。その他unit/選択installは同期終了0。GUIserver/workerなし。subagent/skillなし。
全suite/seed/ブラウザー/Hosted CI/新Wine比較は今回未実行。比較器/参照環境追加であり製品共有core変更ではない。過去full失敗をfull PASSへ読み替えない。
次はC00.V/G03/N04/D01等の未完了親課題へ戻る。A01の完了を他物理や利用者業務V02の完了へ拡張しない。旧7.17/Wine所在質問は未回答だがgoalのblockerではない。
gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEADe445a05、当初clean。前goalターンは共通比較分割版4の実装/検証/commitでprogress。
今回はN04残件2の共通履歴再構築共有を実装/検証したprogress。全計画未完、goal ACTIVE。
[NESTED_RECONSTRUCTION_REUSE.md](NESTED_RECONSTRUCTION_REUSE.md)が契約/数値/検証と制約の詳細。
製品変更はnested_curved_tracking.pyのみ。旧/新Case・元メッシュ一致と真の履歴延長を確認し、旧履歴を元弦メッシュから一度だけ構築する。
追加uniform/marked/frozen操作を一度ずつ実行し、新空間と移送を同時に導出する。両解の全幾何配列・係数寸法/有限性・本質拘束・反射Case/偶奇を従来同様照合。
両側のmesh_from_dictを保持する。初期切出しではJSON同hashのtuple行が通ることを新unitで再現し、新側の厳密解析を戻した。
source meshから公開呼出しごとに全履歴を再構築する。持続cache/保存値の信頼は追加しない。複数違反時の最初の理由は事前照合で変わり得る。
求積/FEM/随伴/RF局所作用/規約/閾値/表面区間/モード割当と保存schemaは不変。
開始時のcProfileはout/quadrature-reuse-20260914/。RF2.713秒中nested2.003秒。仮称出力先であり求積を変更したのではない。
初回対象12unit8.447秒PASS、その後同hash型違反の追加1件0.421秒FAIL。補修後nested9件7.377秒PASS。
最終consumer32件121.162秒PASS。RF指標/適応4・5/対称性/prefix/表面方針/保存/固定pattern、実FEM・CLI・JobManager・再開/改変拒否を含む。
最終41unitは9+32の分割証拠。全対象/コマンドはacceptance.jsonと専用文書。
新validate_nested_reconstruction_reuse.pyはe445a05の自作nestedモジュールだけを別名で読み、同じ読込済みnative場/ライブラリ/RFで旧新を各3回交互測定する。
旧ソースSHA d2cf14caa0a7e2b497d50432f1b5d22381284ff2f4acd1e06ea5d7c2061cd2e5はgit内容一致。旧SUPERFISH資産ではない。
最終paired-final/validation.jsonは45.855秒PASS、3形状の全転送/幾何/係数/履歴/追跡/RF報告完全一致。両対称の鏡映も完全一致。
回転楕円体391→1501DOFのRF中央値1.80848→1.17957秒、電気半球89→329は.36355→.24247、磁気半球120→451は.51465→.34165。
RF速度比1.5332/1.4994/1.5064、再構築約2倍。独立次数12質量形式差最大1.5531e-15、定数転送差0。単独交互測定であり一般速度保証ではない。
最初のpaired/は厳密解析補修前の比較として保持。solve直後のλ丸め差とnative読込後の比較を混同しない。
既存validate_nested_curved_tracking.pyもnative-tracking/でPASS、18既存native場/12組、円筒/楕円/双曲線両尺度のIDと質量/解析五量/実CLI/replayを再確認。
質量差最大1.2878e-15、RF尺度差最大1.0326e-13。専用検証の新FEMなし。consumer32unitと並行した時間を単独性能としない。
最終両検証の1045ソース系hash一致、実行中不変、native全入力不変。今回は全件validate/seed/実ブラウザー/Hosted CI/新Wine比較を実施していない。
FEM/求積/物理定数/seed TMは不変で、曲線親子追跡と直接利用箇所へ影響を限定。過去full失敗+対象補修+別seedをfull PASSとしない。
全handle終端: profile30153/初回focused77490/初回paired41970/補修86926/最終paired80950/consumer36273/native15666はいずれも終了0。型違反redは同期終了1。
索引out/nested-reconstruction-reuse-20260914/acceptance.json。GUIサーバー/workerは起動していない（unit内JobManagerは終了）。subagent/skill/新外部資料/依存/旧資産参照なし。
親33=8受入/17進行/7他未受入/1範囲外、goal ACTIVEを保持。今回の計算共有でN04一般精度/効率を完了へ変更しない。
次はN04残件2の適応全工程の費用/一般収束・精度対照、または残件4の対応しない初期接続間の移送/共通分割・境界変更再メッシュ、C00.V/G03/V02等へ進む。
旧7.17仕様/Wine所在のasync質問は未回答だが全体のblocking条件ではない。gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD54e8139、当初clean。前goalターンは異なる局所履歴への選択領域移送を実装/検証/commitしたprogress。
今回はN04残件4/D01の共通比較分割を版4の保存追跡/CLI/GUIへ追加したprogress。全計画は未完、goal ACTIVE。
[CURVED_COMPARISON_OVERLAY.md](CURVED_COMPARISON_OVERLAY.md)が入力/数学/検証/制約の最新記録。
comparison_meshesの両側schema_version=4はsource_mesh/boundary_pairing/max_pair_tests必須、levels/stepsは片方か省略0段。版/境界方針/組数上限は両側一致。
直接閉PEC/軸接続native曲線TM二解。初期P2分割は境界方針からの向き付き全単射が必要、最終分割は非同型/非nestedでよい。TE/対称半領域/反射/直線混在は旧追跡範囲どおり拒否。
新curved_comparison_overlay.build_curved_comparison_overlay(previous,current,*,boundary_pairing,max_pair_tests,max_triangles)が初期参照座標で全最終要素を交差させる。
既存selection_transferの_prepare/_lineageとFraction、planar_tracking_overlapのclip/crossを再利用。初期節点順/参照座標で正規化し、共線頂点除去/最小頂点fan/正規順で旧新入替えや独立番号に依存しない求積点を作る。
各旧新の最終要素と各初期要素を交差三角形が厳密被覆することを確認。初期別の全旧数×全新数を先にmax_pair_testsで制約し、Case品質/予算・262144標本を履歴/交差生成時にも守る。
初期P2写像を各共通参照三角形へ制限し、物理detJへ共通参照detを掛ける。元二次境界を再投影しない。元FEMのHphiと可変体積内積・RF/規格化/周波数順位契約は保持。
physical_mapping.common_reference_partitionに初期対応/全有理三角形/旧新親番号/各要素被覆/予算を保存し、通常CLI・履歴開始/逆方向/継続/全replayへ接続する。
base_cellはbase_correspondence.previous_reference_cell_nodesの正規順添字。前のsource_mesh要素番号ではない。previous/current_cellは各最終比較空間の番号。
新生成物は共通積分分割であり新FEM解/適合空間ではない。宣言比較履歴と実FEM履歴が違う場合、実FEM全内部境界の包含は保証せず次数確認を残す。
GUIは既存JSON欄で版4を受理し、111/112→119共通三角形・初期境界方針・厳密被覆を表示。失敗は前の結果/履歴を保持。従来版1/2/3の契約は不変。
新test_curved_comparison_overlayは7件の分割証拠。初回被覆/逆方向2件API不在red、実装後2件0.140秒PASS。追跡/厳密予算/保存3件1.468秒PASS、独立番号/固定pattern2件0.318秒PASS。
既存9モジュール56件61.240秒PASS。全実在を先に確認、selected-regressions.json/.logにコマンドと結果。直線/曲線/同領域/アフィン/番号/選択移送/保存/履歴/GUI応答を含む。
専用validate_curved_piecewise_remesh_tracking.py --common-partitionは4新FEM127.848秒PASS。初期26→比較111/112→共通119、501組、次数8で7616標本。実FEMは別26/104セル。
独立P2基底/偏微分のSciPy二重積分でHphi=r内積0.9954490990489955、実装0.9954490990489957。Green体積一致/体積比1.125²。
実場内積は次数4/8で0.9963240036177756/0.9963240033839375、逆向き差は両方0。保存全再構築/CLI完全一致。
尺度2のf/両RQ/G/TTF相対差最大3.364e-14、Hphi/Er/Ez差最大1.566e-13。一般精度/連続枝/表面ピーク収束へ読み替えない。
実Chrome版4/旧版3は各10項目PASS、外部HTTP0、各322製品SHA実行中不変、画像目視。両native取込を使い、ブラウザー中の新FEMなし。
初回browser34333は5項目後、逆方向履歴の15秒waitで終了1。診断は直前の非表示エラー文字列も出していた。保存pair直接逆再生34326は28.241秒PASS/終了0。
版4の検証器waitだけ60秒へ変更し、busy/hidden診断を追加。browser-v4-final40531とbrowser-v3 98183は終了0、専用server27745もSIGINTで終了0。
GUI/独立の全tracking報告は宣言SHA以外完全一致、各保存文書は自身の要求でreplayする。元nativeの全u/f/P2座標/接続も完全一致、36保存ファイル不変、source-fidelity.json 0.498秒PASS、新FEMなし。
数値時1044sourceからブラウザー完了までは追加2unitと検証器wait/診断の2パスだけ変更。最終レビューで共通標本評価から未使用の初期要素基底/Jacobianを除いた。
この最後の製品差はcurved_comparison_overlay.pyだけ。物理点/共通detの計算式は不変。尺度1/2×次数4/8の全保存比較を18.724秒で再構築し全報告完全一致、eigsh禁止、新FEMなし。
最終ソースはreviewed-source-sha256.jsonの1044ファイル。数値/両browser時のSHAが最終に全一致したとはしない。sampling-result-replay.jsonに最後の補完証拠を保持。
tracking81040/numerical93754/regression24363/sampling-replay35426は終了0。全handle/サーバー/workerは終端。
証拠索引out/curved-comparison-overlay-20260914/acceptance.json。全件validate/seed/Hosted CI/新Wine比較/実測は未実行。過去full失敗+対象補修+別seedをfull PASSとしない。
FEM/物理定数/許容差不変、新規外部資料/依存/旧資産参照なし。subagent/skillなし。親33=8受入/17進行/7他未受入/1範囲外、goal ACTIVE。
次は対応しない初期接続間の領域移送/共通分割、境界分割を変える一般再メッシュ、またはN04一般精度/効率とC00.V/G03/V02残件へ進む。今回の共通分割は対応した初期分割からの別履歴への限定受入。
旧7.17仕様/Wine所在のasync質問は未回答だが全体のblocking条件ではない。gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEADc87fab0、当初clean。前goalターンは同型曲線比較メッシュの番号自動対応を実装/検証/commitしたprogress。
今回はN04残件4の異なる曲線細分履歴への選択領域移送をAPI/CLI/GUIへ追加したprogress。全計画は未完、goal ACTIVE。
[CURVED_SELECTION_TRANSFER.md](CURVED_SELECTION_TRANSFER.md)が入力/数学/検証/制約の最新記録。
新curved_selection_transfer.transfer_curved_cell_selection(previous,current,request)は元/先Projectを変更せず完全な領域移送文書を返す。
直接native P2 TM・未組立/未反射限定。原領域の電気/磁気対称境界は試験済み。TE/鏡映後全空洞は拒否。
初期分割は既存番号対応で全P2全単射が必要。最終分割は独立の局所履歴、同型/nestedでなくてもよい。
要求版1はselected_cells/boundary_pairing/coverage_policy/max_pair_tests全必須。旧番号は旧全履歴後。境界方針は同分率/曲線節点順の明示二択。
親参照写像をFractionで合成し、既存planar_tracking_overlapの有理数clipで選択旧セルと新セルの交差を計算する。
各初期三角形を子が厳密被覆すること、全交差面積が旧選択面積と一致することを確認。pair予算は初期セル内の全組数、Case予算/品質は履歴で保持。
intersectsは正面積で重なる覆い、containedは完全包含のみ（空も有効）。部分被覆番号を別報告し、参照面積を物理面積/体積や誤差推定と呼ばない。
両Project/要求/初期対応/全有理交差多角形/被覆率/面積照合を文書へ保持、replayで全再構築する。status PASSは幾何選択契約のみ。
CLI transfer-curved-selection old new --request FILE --out FILE とreplay-curved-selection-transfer FILE。厳密reader/全検査後の排他保存。
GUIは対象段階の図へ移送し、既存の追加/途中挿入/再選択で反映する。全履歴/対象/条件/手動選択の途中変更を拒否し、失敗時は直前記録を保持。
保存記録replayは旧Projectと元選択/条件を復元し、現在の対象段階へ再計算する。移送先Project/全後続履歴の自動置換ではない。
新8unitは分割証拠。初回独立2件API不在red、実装後0.084秒PASS。初回6件0.523秒は5PASS/fixture履歴方式混在1ERROR、当該修正1件0.332秒PASS。
追加原対称領域と厳密TE/予算の2件0.348秒PASS。ブラウザーで実replay不具合を再現し、JSONの0/0.0同値とNumPy float64 metadataを値比較へ修正した。
整数ID/有理数分子分母/真偽値は厳密。追加replayのred/途中補修失敗を保持、最終関連2件0.317秒PASS。既存数値4+ブラウザー2記録の再構築もPASS、新FEMなし。
既存初回43件43.847秒は41PASS/不存在test_curved_refinement_historyの1ERROR/HTTP権限1skip。実curved_refinement_steps/planar_tracking_overlap8件3.847秒と許可HTTP1件0.564秒で補完。
最終既存50件の分割合格であり単一全件PASSではない。全対象/コマンドは専用文書とacceptance.json。
専用validate_curved_selection_transfer.pyは4新FEM6.299秒PASS。非アフィン独立番号の初期26セル、旧111→新112セル、旧[0,2,6]→覆い[81,82]/包含[81]、部分82。
新marked後126セル。独立P2基底/偏微分とGauss-Duffyで面積/回転体積/Hphi=rの幾何質量を照合、相対差最大1.555e-15。
尺度2は面積4/体積8/質量32、選択文書完全一致。f/両RQ/G/TTF尺度差最大1.022e-14、Hphi/Er/Ez差最大1.651e-13、固定領域Ritz非増加。
実Chrome新18/旧履歴20項目PASS、各1 FEM、外部HTTP0、各321製品SHAが最終一致。SVG/Canvas/旧履歴3画像目視済み。
初回browser31324は8項目後selectorエスケープ失敗。browser-final15319/verified75491/corrected9616は12項目後replay失敗、FEM前で終了1。
長寿命サーバーの旧モジュールを維持していたため、修正後は元server60348をSIGINT終了0、新server42203でbrowser-reloaded47621を実行して終了0。
旧browser48649も終了0。新server42203もSIGINT終了0。旧選択9538は終了1、補充5809/数値93995/独立probe68268は終了0。
新validate_curved_selection_transfer_browser.pyの59690は18.602秒PASS/終了0、新FEMなし。小規模と6656セル中96選択を全再構築し、独立物理三積分も一致。
GUI/独立FEMの全u/f/二次座標/接続が完全一致、RF11量とU/RQ定義もPASS。1042sourceと23保存artifact不変。
数値時1041sourceからの差は新native検証器/ブラウザーselector/replay修正/追加unitの4パス。幾何移送/FEMは不変、保存修正は別途検証した。
全検証handle/サーバー/workerは終端。索引out/curved-selection-transfer-20260914/acceptance.json。全件validate/seed/Hosted CI/新Wine比較/実測は未実行。
FEM/物理定数/許容差不変、新規外部資料/依存/旧資産参照なし。subagent/skillなし。過去full失敗+対象補修+別seedをfull PASSとしない。
親33=8受入/17進行/7他未受入/1範囲外、goal ACTIVE。次は対応しない初期接続の領域移送、同型でない分割の共通比較メッシュ、境界分割を変える一般再メッシュ、またはN04一般精度/効率とC00.V/G03/V02残件へ進む。
今回の移送は対応した初期分割からの異なる局所履歴への限定受入。連続物理枝回復や一般TE/反射追跡は別に未受入。
旧7.17仕様/Wine所在のasync質問は未回答だが全体のblocking条件ではない。gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD55fed30、当初clean。前goalターンは固定二次境界の内部メッシュ自動生成を実装/検証/commitしたprogress。
今回はN04残件4/D01の独立番号比較を、曲線比較宣言版3のAPI/保存/CLI/GUIへ追加したprogress。全計画は未完、goal ACTIVE。
[CURVED_COMPARISON_CORRESPONDENCE.md](CURVED_COMPARISON_CORRESPONDENCE.md)が入力/数学/検証/制約の最新記録。
新curved_comparison_correspondence.infer_curved_comparison_correspondence(cases,spaces,boundary_pairing=...)は検査済み二次比較空間の全節点/要素対応を返す。
境界のcurve index/増加分率順/タグから、境界辺に接する三角形の第三頂点と隣接セルへ一意な対応を伝播する。座標近傍/固有値/場係数は使わない。
全P2節点/要素の全単射・巡回向き・辺中点と全域到達を検査し、不整合を部分対応として返さない。
比較宣言schema_version=3はsource_meshとboundary_pairing必須、levels/stepsは片方か省略0段。両側は版/方針一致が必要。
same_curve_fractionsは同じ曲線分率を512epsで照合。ordered_curve_verticesは曲線内の節点順を明示対応とし、分率値の移動を許す。
曲線数/種類/順序・境界タグ/各曲線辺数、最終の向き付き三角形隣接関係が対応することを要求。同数でも内部対角線が異なれば拒否。
各側の旧marked番号/patternは各側の元メッシュ/段階で先に再構築する。自動番号対応を旧選択領域の別分割への移送とは扱わない。
source/要素行/局所巡回/境界行と向きが異なっても、境界からの正規順序で求積セル/参照頂点を固定し、非対称求積則の標本も番号に依存させない。
従来の全二次境界/正Jacobian/全辺検査・Hphi可変体積内積・標本/要素予算を保持。版1直線/版2曲線の明示番号契約と外側保存版は不変。
physical_mapping.numbering_correspondenceに旧ID添字の新node/cell配列、共通参照6節点、方針/分率差/丸め幅を保存し、replayで再構築/改変拒否。
GUI既存比較JSONで版3を受理し、方針と対応要素数を表示。CLI track-modes/逆向き履歴/保存再生へ既存経路で接続する。
初回独立2件はAPI不在red。初期幾何2件は二段細分1PASS/非アフィンの軸分率不一致1ERROR。
分率一致と節点順を明示区別する契約を実装し、前者での拒否を保持。幾何2件0.759秒PASS。
新8件16.409秒は7PASS/境界負例1FAIL。番号変更後の0番は有効な内部節点だったため、負例で境界節点を明示して当該1件0.332秒PASS。
最終新8件は分割合格。製品の幾何/許容差は変更していない。局所→一様履歴、異なる対角線、厳密入力、実FEM内積/保存/表改変も含む。
専用validate_curved_piecewise_remesh_tracking.py --automatic-numberingは4新FEM35.946秒PASS、1037ソース系不変。
旧26/新104の実FEM、独立番号の比較26要素。両尺度で番号変更前後の内積差0、独立Hphi=r二重積分0.9954490990489955対実装0.9954490990489956。
f/両RQ/G/TTF尺度差最大3.364e-14、Hphi/Er/Ez差1.566e-13。Green体積・次数4/8・逆向き・完全保存/CLI一致もPASS。
重なり次数4/8は0.9963257474285827/0.9963243587214313。版2と参照求積順が異なるので有限次数での旧値完全一致を要求しない。
実Chrome新版3の10/旧版2の8項目PASS、外部HTTP0、320製品SHA不変、両画像目視。ブラウザーは保存済みnativeを使い新FEMなし。
同じ分率方針は実保存固有場の局所→一様/独立番号の132比較要素で自己内積1.0、6.463秒PASS。元native9ファイルと入力不変、新FEMなし。
一時ブラウザーrunnerのURL形式、追加native runnerのimport/ディレクトリー誤指定は製品実行前の失敗として保持し、正しい入口で補修した。
既存9モジュール56件701.015秒PASS。曲線/直線/同一領域/アフィン比較・保存/履歴/HTTP GUI・曲線Study版3/4を含む。全一覧/コマンドと結果はacceptance.json/selected-regressions.log。
feature58066は終了1、補修負例は終了0。数値86571/既存28580/browser56781・66913/追加native27474は終了0、GUI server27750もSIGINTで終了0。
全handle/サーバー/workerは終端。数値1037ソース系と両browser320製品SHAが最終実装に一致し、証拠索引out/curved-comparison-correspondence-20260914/acceptance.jsonはPASS。
全件validate/seed/Hosted CI/新Wine比較/実測は未実行。過去full失敗+補修+別seedをfull PASSとしない。
FEM/物理定数/既存許容差は不変。新規外部資料/依存/旧資産参照なし。subagent/skillなし。
親33=8受入/17進行/7他未受入/1範囲外、goal ACTIVE。次は同型でない分割の共通比較メッシュ生成、境界分割を変える一般再メッシュ、旧marked領域の異なる分割への移送、またはN04一般精度/効率とC00.V/G03/V02残件へ進む。
同型比較メッシュの番号自動対応は今回実装済み。連続物理枝回復・TE/反射/半領域の契約は別に未受入。
旧7.17仕様/Wine所在のasync質問は未回答だが全体のblocking条件ではない。gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 継続履歴。開始HEADf73ff2d、当初clean。前goalターンは供給初期メッシュの条件別Study版4を実装/検証/commitしたprogress。
今回はN04残件4の固定二次境界の内部メッシュ自動生成をAPI/CLI/Study GUIへ追加したprogress。全計画は未完、goal ACTIVE。
[CURVED_REMESH_GENERATION.md](CURVED_REMESH_GENERATION.md)が入力/数学/検証/制約の最新記録。
新curved_remesh_generation.generate_curved_remesh_plan(project,settings)は既存の完全置換plan版1を返す。Study版4/保存形式は不変。
直接native P2・未組立/未反射・閉PEC/axis m=0 TM限定。元内部節点/要素/番号を破棄し、元境界だけを原点/向きで正規化する。
既存ear clipping、内部辺分割、重心挿入、角度改善flip/平滑化で再生成。境界節点/辺/タグは固定し、全二次境界を既存置換APIで照合する。
settings版1はmax_chord_edge_m/max_chord_triangle_area_m2/minimum_corner_angle_deg/max_triangles/max_roundsと片方の新履歴を必須にする。
弦辺長/面積は新初期メッシュ、角度/予算は新履歴へも適用。元Caseの厳しいサイズ/品質条件を保持し、旧メッシュが新予算を超える粗化は許す。
新marked番号だけを解釈し固定patternを計画へ保存する。旧番号/patternを暗黙継承しない。生成の失敗反復は返さない。
CLI generate-curved-remesh-plan PROJECT --settings FILE --out PLANは全検査後に排他的保存。合成設定例examples/curved_remesh_generation/settings.json。
GUIは版4の区間欄で生成条件を入力し、成功した完全planを切替値以降へ入れる。元Project保持、重複JSON/不適合サイズ/生成中の入力変更を拒否。
境界と内部番号を独立変更して同じ生成結果、独立Green面積/体積とu=Hphi/r=1の質量∫r³、2倍尺度の質量32倍を確認。
新9unitは分割証拠。初回2件API不在red、実装後2件4.350秒PASS。初回7件10.470秒は6PASS/相似入力1ERROR。
相似入力で元Case辺長も2倍へ修正。次の2件3.892秒は相似PASS/凹形状のGreen符号前提FAIL、凹形状補修1件0.605秒PASS。
予算と追加粗化2件2.681秒PASS。旧76初期/304最終から新30要素を予算50で生成し、新履歴超過の拒否も確認。単一9件実行ではない。
選択既存は49件474.822秒のうち48PASS/存在しないtest_guiの1ERROR。実在するtest_gui_hphi/test_job_startup_cleanupの10件6.090秒PASSで補完。
最終既存58件は分割合格証拠。合格済み48件は再実行していない。選択コマンド/失敗理由を保持する。
専用初回numericalは形状4+円筒1の5新FEM後、固定25mm境界/10度/面積2.5e-5m²という不可能条件を生成器が拒否して終了1。
独立必要条件A>=L²tanα/4=2.7551e-5m²をarea-feasibility.jsonに記録。検証器の円筒元Case辺長指定だけ.025→.015へ変更した。
新境界の最大辺13.75mmでは下限8.3342e-6m²。元25mm境界に成功したとは扱わず、製品/許容差は不変。
専用numerical-finalは6新FEM88.290秒PASS。元/変形を尺度1/2で独立再生成/求解し、Green面積比1.125/体積比1.125²を確認。
f/RF尺度差最大8.216e-15、Hphi/Er/Ez差最大1.488e-14、追跡重なり約0.9977237325131574、完全保存replay一致。
元26初期/146最終と生成36初期/144最終を使用。別円筒の初期160/456→最終640/1824、f誤差6.600e-9/2.739e-9。
円筒の両RQ誤差3.095e-6/1.084e-6、G5.803e-9/3.257e-9、TTF1.760e-8/4.281e-8。既存条件f<.003/RF<.01維持、全量単調収束とは呼ばない。
同検証器--workers-onlyは3新FEM304.515秒PASS。実BISECT/PAUSED後JobManager閉鎖/再生成、実0.5追加resume、STOP/UNVERIFIED、再生成/全replay一致。
worker初期数26/36/26、元点再利用、比較メッシュは元26由来の異なる実点座標。異常crash試験ではない。
worker/最終数値は各実行中1035ソース系不変。間の差は専用検証器の円筒元Case辺長1箇所だけ。製品は不変。
実Chrome新22/既存版3の13項目PASS、各2新FEM、外部HTTP0、両319製品SHAは最終一致、画像目視済み。
GUI/CLI生成計画完全一致。GUI/独立最終Studyのnative全f/u/二次座標/接続完全一致、57保存ファイル不変、1.163秒PASS、新FEMなし。
geometry79087/予算38980/worker1202/browser79845・23831/最終数値61373/native35474/追加GUI1341は終了0。
初回新7件56294/途中幾何90592/初回数値99832/初回既存14239は終了1を回収し上記の原因と補修を保持。GUI server68099もSIGINTで終了0。
全検証終端、実行中handle/サーバー/workerなし。証拠索引out/curved-remesh-generation-20260914/acceptance.json。
全件validate/seed/Hosted CI/新Wine比較/実測は未実行。過去full失敗+対象補修+別seedをfull PASSへ読み替えない。
FEM/変形数学/比較・物理許容差は無変更。新規外部資料/依存/旧資産参照なし。subagent/skillなし。
親33=8受入/17進行/7他未受入/1範囲外、goal ACTIVE。限定した自動生成をN04全体の受入や任意条件での生成保証にしない。
次はN04残件4の独立メッシュの自動番号対応または境界分割を変える一般再メッシュ、あるいはN04一般精度/効率とG03/C00.V/V02残件を限定して進める。
固定境界の自動生成とStudy接続は今回までで実装済み。TE/反射/半領域や曲線種類/個数の離散変更、一般物理枝回復は未受入。
旧7.17仕様/Wine所在のasync質問は未回答だが全体のblocking条件ではない。gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 継続履歴。開始HEADae5141e、当初clean。前goalターンは初期メッシュ置換API/CLIを実装/検証/commitしたprogress。
今回はN04残件4の条件別初期メッシュをStudy版4・追跡/逐次/適応再開・GUIへ接続したprogress。全計画は未完、goal ACTIVE。
[CURVED_REMESH_STUDY.md](CURVED_REMESH_STUDY.md)が入力/数学/検証/残件の最新記録。
Study study_version=4/kind=curved_remesh_sweep。版3の曲線法則/単位/RF/角度にmesh_schedule版1を必須追加。版1/2/3への混在は拒否。
mesh_schedule={schema_version:1,breakpoints:[...厳密昇順有限値],plans:[original又はreplace+完全plan]}。計画数=境界数+1、置換1個以上。
bisect_rightで境界値は右区間、逆順/再訪/適応二分でも実値で選ぶ。空境界は全値に一つの置換計画。単位はStudy parameter_unitのm/1。
curved_remesh_study.projects_at_valuesで全計画を元形状上でpreflightし、新marked履歴を既存remesh/freezeで固定する。未使用計画も無効なら拒否。
各実FEM点は選んだbaseを元geometry lawから独立変形。比較Projectは常に元Study.projectを実値へ変形し、元接続/固定履歴を保持。
各実点の実FEMと比較Projectの全二次境界を既存Bernstein係数比較で検査する。元形状上の一致だけで先の一致を仮定しない。
study_shape_tracking.pair_controlsは版4に限り供給済み実FEM Projectsを比較メッシュに使わず、元Projectから実比較点を導出する。
全点事前検査、通常の独立スペクトル/comparisons=[]/UNVERIFIED、既存piecewise_remesh閾値/手動comparison_meshes拒否と保存replayを保持。
適応の最大深さ/試行数/最小幅、拒否履歴、元点再利用、PAUSED/UNVERIFIEDは維持。外側要求/checkpoint版は不変。
GUIの新操作は共通寸法法則欄+区間計画JSON。完全planのfile読込で切替値未満original/以後replaceを作る。複数区間はJSONで明示。
raw法則/区間/planテキストをstrict readerへ送り重複キー拒否。非同期読込/normalization中の変更をsignatureで拒否。版3/旧版1のGUIも確認。
新portable合成例examples/curved_remesh_study.json。元26初期/146最終、置換28初期/188最終要素。測定構造を表さない。
新8unit413.395秒PASS、初回独立2件は版4不在red、最初の幾何2件18.157秒PASS。
既存16モジュール78件510.514秒PASS。選択回帰はselected-regressions-final.json/.log。初回一時runnerはPythonリンクresolveでsystem Pythonを呼びimport16ERROR/FEM未実行。
仮想環境パスを保持するrunnerへ修正し同じ選択を実行。製品の依存やソルバーは変えていない。
専用validate_curved_harmonic_study.py --remesh-study：6新FEM137.626秒PASS。独立Green面積比1.125/体積比1.125²、m換算/2倍Maxwell。
f/RF相対差最大1.266e-14、場形最大3.362e-14。三Study追跡0.9977229774915644、完全replay一致。
同検証器--workers-only --remesh-study：3新FEM353.704秒PASS。JobManager閉じ直し/再生成後resume、実0.5追加、再度全replay。
元/終端/二分点の初期数26/28/26。二比較メッシュは元26由来で終端/二分点座標が別。異常crash試験ではない。
validate_curved_harmonic_study_crossing.py --remesh-study：2新FEM112.694秒PASS。円筒長55→77mm、初期96→別生成384、最終105→1536。
解析TM010/TM020/TM011→TM010/TM011/TM020の順位交差と追跡ID一致。最大f誤差6.937e-5/3.171e-7、既存.003条件維持。
専用三実行で同一1031source不変。並行実行の秒数は単独性能測定ではない。
実Chrome新18/既存版3の13項目PASS、各2新FEM。外部HTTP0、両318製品SHAが現行一致。画像目視済み。
GUI/CLI同一入力・f/RF一致。追加native全f/u/二次座標/接続完全一致、57保存ファイル不変、1.393秒PASS、新FEMなし。
red16261終了1、幾何65894/新8unit81436/数値49468/worker88611/交差46832/既存78件36104/browser88647・93732/native96252は終了0。
GUI server65984もSIGINTで終了0。全検証終端、実行中handle/サーバー/workerなし。
証拠索引out/curved-remesh-study-20260914/acceptance.json。全件validate/seed/Hosted CI/新Wine比較/実測は未実行。過去full失敗+対象補修+別seedをfull PASSへ読み替えない。
FEM/変形数学/物理許容差は無変更。新規外部資料/依存/旧資産参照なし。subagent/skillなし。親33=8受入/17進行/7他未受入/1範囲外、goal ACTIVE。
次はN04残件4の自動mesh生成/番号対応か、N04全体の一般精度/効率とG03/C00.V/V02残件を独立受入条件へ限定して進める。
今回の供給メッシュStudyを自動生成/一般物理枝回復・全区間形状保証へ読み替えない。TE/反射/半領域や曲線種類/個数の離散変更は未受入。
旧7.17仕様/Wine所在のasync質問は未回答だが全体のblocking条件ではない。gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEADf6ee460、当初clean。前goalターンは単独Project形状変形GUIの実装/検証/commitでprogress。
今回はN04の初期メッシュ変更Studyに必要な、同じ二次領域での初期メッシュ置換と明示新履歴をAPI/CLIへ追加したprogress。
全計画は未完、goal ACTIVE。[CURVED_PROJECT_REMESH.md](CURVED_PROJECT_REMESH.md)が入力/数学/検証/残件の最新記録。
新curved_project_remesh.remesh_curved_project(project,plan)。plan版1はsource_meshとminimum_corner_angle_deg必須、curved_refinement_levels/stepsの片方も必須。
直接native曲線P2、未組立/未反射、閉PEC/axis TM。元のCase/Project・RF・正規化・幾何・予算を保持し、新メッシュと全履歴だけ置換。
旧marked番号を暗黙継承しない。新marked番号は新しい段階直前のメッシュへ解釈し、既存freezeで全split_patternを固定して返す。
旧接続SHAに拘束されたpattern、履歴なし/両方/空steps/不正quality・予算は拒否。全新prefixで正Jacobian/辺/品質と元全二次境界の一致を検査。
同じ解析曲線でも、弦の途中へ新しい節点を置いて再投影すると二次領域が変わる。既存compare_quadratic_space_boundariesの全区間Bezier係数一致で拒否する。
巨大一様段数を配列へ展開せずgeneratorで段階を検査し、元max_trianglesで拒否する。
CLI remesh-curved-project --plan ... --out ... は検査後に排他的保存。元/plan/既存出力を保持。新Study版や専用GUIはまだ追加していない。
portable合成例examples/curved_project_remesh/source-project.jsonとremesh-plan.json。元26初期/146最終、置換28初期/188最終要素。
変更前の独立幾何/質量2件はAPI不在red。実装後の2件は1PASS/1ERROR（keyword-only積分次数のテスト呼出し誤記）。テストだけ補修。
新6unit7.994秒、非アフィン変形受渡し1件2.975秒、専用後の独立内部点移動/節点・要素番号付替え1件1.467秒PASS。
最終新8件は6+1+1であり単一8件実行ではない。
既存harmonic_deformation/frozen_refinement/project_mesh/curved_same_domain/curved_piecewiseの34unit75.672秒PASS、external_mesh_study4unit0.478秒PASS。
旧APIのmarked履歴付き無宣言メッシュ置換拒否も維持。FEM/既存境界比較/変形数学・許容差は無変更。
専用validate_curved_project_remesh.pyは53.996秒PASS、8新FEM。元/置換×尺度1/2と元/置換の非アフィン変形6 FEM、別生成円筒2 FEM。
独立Green面積/体積と既知Hphi=rの質量は不変。Maxwell f/RF差最大4.441e-15、Hphi/Er/Ez尺度差最大2.919e-14。
同一領域追跡0.9999999408013291、元→変形後の独立置換FEM追跡0.9977230877971308でPASS、両完全保存replay/native一致。
後者は元Projectから変形した比較メッシュを用い、別接続FEMの実場を標本化した。
円筒は初期96/384→最終384/1536要素、TM010 f相対誤差2.103e-8/1.320e-9、両RQ8.555e-6/6.233e-7、G2.330e-8/1.566e-9、TTF3.303e-9/2.006e-10。
専用実行中1028ソース系不変、以後差分は独立番号付替え1テストだけ。製品は以後不変。索引out/curved-project-remesh-20260914/acceptance.json。
geometry93903終了1、feature57606/deformation28487/reg97834/native12620/numbering26578終了0。external4も終了0。全検証終端、サーバー/worker/実行中handleなし。
新API/CLIと直接消費先へ限定、全件validate/seed/browser/Hosted CI/新Wine比較/実測は未実行。過去full FAIL+対象補修+別seedを今回full PASSへ読み替えない。
新規外部資料/依存/旧資産参照なし。subagent/skillなし。親33=8受入/17進行/7他未受入/1範囲外、goal ACTIVE。
次はこの置換planをStudyの条件別メッシュ規則へ接続する。元の形状法則Projectは比較用に保持し、各点の実FEMは明示した別メッシュ/新固定履歴から作る。
同じ元/先解析曲線でも二次境界が変わる場合は既存piecewise比較を通せない点を維持。単なる自動make_mesh+旧番号流用は不正。
条件別の計画を二分点でも決定できる明示規則、実比較点の対応メッシュ、全点preflight・保存replay/再開・GUIが残る。離散mesh切替時も物理枝は追跡が必要。
未決定の設計案として、元形状上の置換planを値区間へ明示し、各点で独立変形し、元Projectから変形した比較用メッシュと全二次境界を照合する方法がある。まだ実装/受入済みではない。
自動mesh生成/番号対応、Study離散曲線変更、TE/反射/半領域契約、D01一般枝回復、N04一般精度/効率、C00.V/G03/V02ほかは未完。
旧7.17仕様/Wine所在のasync質問は未回答だが全体のblocking条件ではない。gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD91e177e、当初clean。前goalターンは曲線法則Studyの実装/検証/commitでprogress。
今回はN04残件4の単独Project形状変形GUIを実装・検証したprogress。全計画は未完、goal ACTIVE。
[GUI_CURVED_DEFORMATION.md](GUI_CURVED_DEFORMATION.md)が入力/状態/数学/検証/残件の最新記録。
新gui_curved_deformation.deformation_responseとpreview-curved-deformation API。document/geometry_document/rf_coordinates/minimum_corner_angle_degを必須にする。
既存deform_curved_projectをそのまま使用。元/先の全履歴後のnative境界を始/終/中点で返し、固有値求解/ファイル作成なし。
GUIは元形状ひな形/目標JSON読込、SIテキスト、RF方針/品質、同縮尺二次境界、節点/要素数と実RF座標、別保存/適用/Undo。
目標JSON文字列をstrict readerへ渡し重複キー拒否。候補へ元入力・文字列/条件・編集世代を拘束し、準備中/準備後の変更を拒否する。
Undoは適用直後のProject一致を確認し、以後のProject編集/別読込で解除。入力イベントを伴わない値変更も操作時に照合する。
元/先Bezier制御点は2m−(a+b)/2。全native境界を表示し、内部要素の選択は適用後の既存図上操作へ渡す。
元の単独変形API/数学/FEM/保存形式/品質閾値は無変更。閉PEC/axisの直接曲線P2 TM、全marked固定を維持。
初回の独立境界テストは新GUI API不在red。新3unit5.506秒PASS。
selected-testsは実31件PASS+誤指定test_project_mesh_operationsのimport1件ERRORで56.693秒/終了1。新3+既存28を含む。
正しいtest_project_meshとtest_projectは9件1.046秒、例題往復1件にStudy例を単独Caseとみなす古い前提の2subtest ERROR。
tests/test_project.pyだけを補修。Study専用パーサーで往復/元Project一致、単独Caseパーサーでの拒否を保持し、当該1件0.204秒PASS。
最終異なる40unit（新3/既存37）は分割合格証拠。一括40/full PASSにはしない。
実Chrome初回browserは10項目+実worker1 FEMまで進み、CLI参照をcli-run/result.jsonと誤指定して停止。
正しいcli-run/solution/results.jsonでbrowser-final21項目PASS。保存/適用/Undo/非同期変更/実worker1 FEMとCLI RF一致を含む。
既存verify_gui_frozen_curved_refinement.mjs無変更でbrowser-frozen-regression9項目/実worker1 FEMがPASS。
後続製品修正はapp.jsのプレビュー失敗時status3行とstyle.cssの図中文字サイズ1行だけ。
browser-additional6項目PASS、新FEMなし。RF両方針/明示座標、品質拒否/失敗表示、有効凹形状の実反転、変更して同値に戻した要求拒否、文字/幅を確認。
全browser外部HTTP0、最終画像目視。各実行中316製品SHA不変。最終追加browserが現行316製品と完全一致。
CLIの同じ変形Projectも1 FEM計算。成功browser2+CLI1と、初回browser1の計4 FEMを別々に保持する。
専用validate_gui_curved_deformation.py初回は検証器R/Qの係数2の向きの誤記でFAIL。PHYSICSのV²/(omega U)とV²/(2 omega U)へ補修。
native-validation-finalは1.489秒PASS、新FEMなし。GUI/CLIのf配列/全P2係数完全一致、146要素境界/全RF元場再評価、独立Green比/エネルギー/両RQが成立。
検証中1023ソース系/27native不変。GUI元実行20260914-135125-2732e3ca0e、CLI cli-run。全ファイル/結果の索引はout/gui-curved-deformation-20260914/acceptance.json。
GUI PID1219797は完全argv照合後SIGINT、session14612終了0。feature62718/CLI変形85970/追加fixture18299/browser-final60755/旧browser17545/追加89493/専用最終15164は終了0。
初回browser77166/selected86502/project32380/専用初回61873は終了1を回収して補修。全検証終端、実行中handleなし。
GUIと直接消費先だけへ限定。全件/seed/Hosted CI/新Wine比較/実測は未実行。過去full FAIL+対象補修+別seedを単一full PASSとしない。
新規外部資料/依存/旧資産参照なし。subagent/skillなし。親33=8受入/17進行/7他未受入/1範囲外を維持。
次はN04の初期メッシュ変更を伴うStudyと実比較メッシュの明示対応、または一般精度/効率の原受入条件へ進む。
単独形状変形GUIは今回接続済み。Study曲線法則/二分/保存再開も前段で完了。これらを残件として繰り返さない。
独立メッシュの自動番号対応、Studyの離散曲線変更、TE/反射/半領域変形、D01一般物理枝回復、C00.V/G03/V02ほかは継続。
旧7.17仕様/Wine所在のasync質問は未回答だが全体のblocking条件ではない。gitメタデータはrequire_escalated。
以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD78b61f1、当初clean。前goalターンは調和変位API/CLIの実装/検証/commitでprogress。
本段階はN04残件4の曲線法則Studyを実装・検証したprogress。全計画未完、goal ACTIVE。
[CURVED_HARMONIC_STUDY.md](CURVED_HARMONIC_STUDY.md)が入力/数学/操作/受入/残件の最新仕様。
Study版3はcurved_harmonic_sweep専用。parameter_unit=m/1、geometry_coefficients、rf_coordinates=fixed/axis_fraction、minimum_corner_angle_degを必須にする。
既存曲線の連続な数値葉だけを多項式で同時指定する。パスは/curves/index/...、枝/種類/個数/タグ/予算/物理・求解設定への法則を拒否。
新curved_harmonic_studyが有限係数/Horner/入力を検査し、各点を既存deform_curved_projectで元から独立作成。旧Study版1/アフィン版2は保持。
通常Studyはcomparisons空/UNVERIFIED/独立スペクトル。全指定点の品質/幾何/予算を出力作成前に検査する。
新study_shape_trackingで、版3はpiecewise_remesh controlsから実比較点の元メッシュ/全固定履歴を導出。手動comparison_meshes混在は拒否。
旧版1/2のcontrolsは旧affine helperへ同じ引数で渡す。逐次/適応では検査・求解済みProjectを比較にも使用し、二分点へ元終点メッシュを流用しない。
保存要求は導出メッシュなし、実比較/履歴には両メッシュを保持。元法則/条件/Project・native場・祖先出所で完全replayする。
GUIは曲線の数値法則/単位/RF/品質と定数項ひな形を追加。文字列のJSONをstrict readerへ渡し重複パスを拒否。
定義保存/読込、全点検査、非同期変更拒否、完了追跡と逐次/適応要求準備へ接続。単独Project変形のGUIプレビュー/適用/Undoはまだ残る。
初回独立幾何/実比較点2件は新版/API不在red。幾何2件15.646秒、新7unit239.756秒、追加二次法則/m換算/Green1件6.998秒PASS。最終新8件は7+1で確認。
既存14モジュール65unit278.056秒PASS。全一覧/コマンドはselected-regressions.json。旧Study/アフィン/調和変形/履歴/元メッシュ/追跡・逐次/適応のJob・GUIを含む。
専用validate_curved_harmonic_study.pyは111.592秒PASS。無次元/m/2倍尺度の各2条件、6新FEM。独立Green面積比1.125/体積比1.125²、RF/f差最大2.221e-14、元場差2.013e-14。
同--workers-onlyは223.940秒PASS、3新FEM。実BISECT後PAUSED、JobManager閉鎖/再生成・元二点再利用・0.5追加STOP/UNVERIFIED、完了後も再生成/全保存再検証一致。異常終了復旧試験ではない。
追加validate_curved_harmonic_study_crossing.pyは53.647秒PASS、2新FEM。円筒R=.1 L=.055→.077mの三Besselモード、最大f相対誤差7.352e-5。
TM020/TM011の順位交差を曲線法則/調和変位/比較メッシュ経路で追跡し、実IDと解析順序・保存replayが一致。
実Chrome新14項目/既存アフィン11項目PASS。各2FEMのStudy worker・CLI一致/追跡再生を含む。外部HTTP0、新GUI画像目視済み。
数値/worker実行中1018ファイル不変。以後は円筒検証器追加と二次法則1テストだけ変更。円筒1019ファイルも実行中不変、以後その1テストのみ。製品315は全browser/最終一致。
索引out/curved-harmonic-study-20260914/acceptance.json。feature-tests、quadratic-law、selected-regressions、native-validation、workers、crossing、browser/browser-affine-regression。
GUI PID1189653は完全argv照合後SIGINT、session12696終了0。feature37468/reg1658/native98683/worker23195/browser66115/旧browser93186/crossing43658/追加64963は全て終了0。
全検証終了、実行中handleなし。新規外部資料/依存/旧資産参照なし。subagent/skillなし。
Studyと直接消費先へ限定。今回は全件/seed/Hosted CI/新Wine比較/実測を再実行しない。前段全件FAIL+対象補修+別seedを今回単一full PASSとしない。
親33=8受入/17進行/7他未受入/1範囲外、goal ACTIVEを維持。
次は単独Projectの非アフィン変形GUI（目標形状の準備/プレビュー/適用/Undo）か、初期メッシュ変更に伴う明示対応へ進む。
Study曲線法則/区間二分/保存再開は今回接続済み。離散的な曲線種類/個数の変更、TE/反射/半領域の変形契約、自動番号対応と一般物理枝回復は残る。
N04一般精度/効率、C00.V/G03/V02ほか全計画の未完了も保持。旧7.17仕様/Wine所在のasync質問は未回答だが全体のblocking条件ではない。
gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD49869a6、当初clean。前goalターンは曲線アフィンStudyの実装/検証/commitでprogress。
本段階はN04残件4の非アフィン形状変更に向けた調和変位API/CLIを実装・検証したprogress。全計画未完、goal ACTIVE。
[CURVED_HARMONIC_DEFORMATION.md](CURVED_HARMONIC_DEFORMATION.md)が契約/数学/入力/検証/残件の最新仕様。
新curved_harmonic_deformation.deform_curved_project(project,target_geometry,rf_coordinates=...,minimum_corner_angle_deg=...)。
元の曲線番号/増加分率と弦分割数を保持し、元弦メッシュの平面P1 ∫|grad d|²で内部変位を求める。元座標のグラフ平均や電磁場求解ではない。
境界分率を先の弦へ写し、P2曲線を初期メッシュで構築後、固定履歴を同じ参照分割で制限する。全体の物理写像はF1∘F0^-1。
対象は未組立/直接native P2の閉PEC・軸TM。TE/反射/半領域は明示拒否。全marked段階を先にfreeze-curved-refinementする必要がある。
元/先の曲線数・順序・タグを保持。先の同じ整数segments_per_curveを補完または照合し、先の弦誤差/隙間/曲率等の通常Case検査を通す。
rf_coordinates=fixed/axis_fractionを必須とし、後者は全軸長の比で有効長/電圧区間/明示位相原点を変換。暗黙原点は暗黙のまま。
全初期一様水準/全履歴prefixで番号・境界分率、正Jacobian/全辺、指定角度floorと元markedの品質/要素予算を検査する。
CLI deform-curved-projectは元Projectとtarget geometry JSONから、新規Projectを排他的作成。元/既存出力を保持し、不正移動は作成前に拒否。
携帯合成例examples/curved_harmonic_deformation/source-project.jsonとtarget-geometry.json。新Study版や専用GUIはまだ追加していない。
変更前アフィン再現/非アフィン幾何2件はAPI不在red。最初の幾何2件4.826秒PASS、新7件35.058秒で6合格/1不合格。
不合格は細長い凸形状なら反転するという検証入力の前提。実際には有効で製品は正しい。有効な凹輪郭で実負Jacobianとなる負例へ修正し、CLI1件2.540秒PASS。
追加弦内境界節点/初期一様細分と標準importの幾何不変量2件3.992秒PASS。最終新8件は分割合格であり一括再実行ではない。
既存frozen_curved_refinement/curved_project_transform/curve_partitions/curved_piecewise_remesh_tracking/mesh_inputの5モジュール33件44.101秒PASS。
専用validate_curved_harmonic_deformation.pyは47.856秒PASS。元/先と2倍尺度の4新FEM、元26→履歴146要素。
独立Green面積比1.125/体積比1.125²、Maxwell f/両RQ/G/TTF差最大2.110e-14、場形差1.679e-14、質量2^5差6.528e-16。
保存場の非アフィン重なりは両尺度0.9977243304212868/0.997724330421287、完全保存replay一致。凹形状CLIは負Jacobianで終了2、出力なし。
analytic-geometry.jsonは保存Green符号の絶対値を独立解析半楕円積分と比較。面積不足1.55314e-4、体積不足2.32210e-4は幾何近似誤差として保持。
専用実行中1,012src/tests/scripts/examplesファイル不変、最終SHA一致。新規外部資料/依存/旧資産参照なし。subagent/skillなし。
影響先を新Project作成API/CLIと直接消費先へ限定し、既存FEM/Study/GUI無変更。全件/seed/browser/Hosted CI/新Wine比較/実測は未実行。
証拠索引out/curved-harmonic-deformation-20260914/acceptance.json。初回red/feature-testsの失敗、folded-fixed/additional-tests、selected-regressions、native-validation、analytic-geometry。
selected session95801、専用94291は終了0。他のfeature/負例/追加検証handleも全て終端確認済み。サーバーを起動しておらず、実行中handleなし。
親33=8受入/17進行/7他未受入/1範囲外は保持。全計画未完でgoal ACTIVE。
次はこの非アフィン変形を一般形状Studyの明示法則・区間二分・保存再開へ接続し、既存piecewise_remesh版2で実比較点の対応を構成する。
専用GUIの目標形状準備/プレビュー/Undoも残る。初期再メッシュ/自動番号対応、N04一般精度/効率、D01個別枝回復とC00.V/G03/V02ほかも未完。
旧7.17付属仕様/Wine所在のasync質問は未回答だが、全体を止める条件ではない。gitメタデータはrequire_escalated。
以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD8249df7、当初clean。前goalターンは曲線局所分割の固定を実装/検証/commitしたprogress。
本段階はN04残件4の宣言アフィン形状Studyを実装・検証したprogress。全計画未完、goal ACTIVE。
[CURVED_AFFINE_STUDY.md](CURVED_AFFINE_STUDY.md)が入力/数学/操作/受入範囲/残件の最新仕様。
Study版2はcurved_affine_sweep専用。parameter_unit=m/1、有限多項式三法則、rf_coordinates=fixed/axialを厳密必須とする。
既存tune.trial_mapとtransform_curved_projectを使い、元Projectから各条件を独立変形。旧版1の各kind/保存フィールドは維持。
native曲線P2/未組立TMを対象とし、TEは専用座標契約が必要と拒否する。全点の品質/範囲/要素予算を出力作成前に検査。
固定元メッシュ/分割の親子関係を保持。未固定履歴の接続不一致拒否、RF座標の従来条件を維持する。
通常Studyはcomparisons空/UNVERIFIED/独立スペクトル。曲線アフィン変形を固定領域の収束比較と呼ばない。
完了Study追跡・逐次/適応実行・全保存replayへ接続。新Studyのcontrolsはaffine_remeshで手動affine_mapを禁じ、実際の前後値から相対写像を導出する。
区間二分も元区間の閾値を継承しつつ、実比較点の写像を使う。外側要求/保存版・上限・失敗/祖先出所の契約を維持。
GUIに三法則/変数単位/RF方針を追加。定義往復、全点事前検査、非同期変更拒否、追跡要求生成・保存再生へ接続。
変更前の独立座標/Maxwell尺度則2件は新版拒否のred。関連14モジュール62unitは340.117秒PASS。
巨大整数の追加負例でOverflowErrorを再現し、有限性検査でValueErrorへ補修。厳密入力と旧版Studyの2件を0.297秒で再検査PASS。
専用validate_curved_affine_study.pyは111.541秒PASS、合成半楕円4/円筒2/適応3の9新FEM。
独立Green面積ac/体積a²c、質量a⁴c差4.660e-16、Maxwell f/両RQ/G/TTF差3.176e-14、場形差1.353e-13。
SIのm/無次元のCaseとuは完全一致。円筒TM020/TM011の解析順位交差を保存追跡し、最大f誤差7.352e-5。
適応1→1.5はBISECT、1→1.25はSTOP/UNVERIFIEDで実写像1.25。全3点と拒否比較を保持しreplay一致。
初回楕円せん断のz範囲外拒否は固有値計算前。別の有効な合成円錐2条件で非零せん断の幾何/質量を検査、追加FEMとは数えない。
専用--workers-onlyは174.721秒PASS、新5 FEM。逐次PAUSED→COMPLETE、適応BISECT後PAUSED→STOP/UNVERIFIED。
JobManagerを同じ検証プロセス内で閉じて再生成し、元点を再利用して実workerで再開、完了後も再生成/全保存検証。異常終了復旧試験ではない。
Chrome最終10項目と、係数欄CSS補修後の表示3項目がPASS。初回7項目後の空要求JSON読込は検証器待機不足で、待機を補修した。
外部HTTP0。最終画像目視済み。browser最終は通常Study2 FEM/完了追跡と再生を含み、表示専用実行は新FEMなし。
数値検証中1,007ファイル不変。その後の差分はCSSと二つの検証器だけ。最後のworker1,007ファイルと表示browser製品SHAは最終ソースと一致。
証拠索引out/curved-affine-study-20260914/acceptance.json。selected-tests/overflow-red/overflow-fixed、native-final、workers、browser-final/browser-layout。
Studyと直接消費先へ影響を限定し、今回は全件/seed/Hosted CI/新Wine比較/実測を再実行しない。前段の全件FAIL+対象補修+別seedを単一full PASSとはしない。
GUI PID1112537/1119852は完全argv照合後SIGINT、session85454/38575終了0。selected20308/native91494/browser18126/layout1390/workers1845も終了0。
全検証終了、実行中handleなし。新規外部資料/依存/旧資産参照なし。subagent/skillなし。
親33=8受入/17進行/7他未受入/1範囲外は維持。N04一般形状/初期再メッシュの掃引、自動番号対応、TE座標契約、一般精度/効率は残る。
次はN04残件4の非アフィン宣言変形・履歴対応か一般精度/効率を、既存の物理/保存契約と独立不変量でさらに限定して進める。
D01自動対応推定/個別枝回復、C00.V/G03/V02ほか全計画の残件も保持する。
C00旧7.17付属仕様/Wine所在はasync質問済み・未回答。他の開発を継続でき、全体を止める条件ではない。
gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD cb94270、当初clean。前goalターンは曲線比較メッシュ追跡の実装/commitでprogress。
本段階はN04の局所分割選択の固定/保存と宣言アフィン形状変更を実装・検証したprogress。全計画未完、goal ACTIVE。
[FROZEN_CURVED_REFINEMENT.md](FROZEN_CURVED_REFINEMENT.md)に受入条件/入力/数学/操作/回帰/残件を記録。
freeze_curved_refinement(Project)は元の番号付き弦メッシュと全marked段階の実分割辺/遷移対角線を保存する。
新CurvedSplitPatternは入れ子版1、parent_topology_sha256/marked_cells/split_edges/transition_diagonalsを厳密受理。
Case版3の任意split_patternで、未指定の旧JSONは不変。座標を除いたSHAは番号付き接続/境界所属への拘束で、任意メッシュの物理対応証明ではない。
refine_marked_curved_space、native再構築、nested追跡、適応の履歴適用へ接続。品質/予算/正Jacobian/全辺・境界検査は保持。
固定前のmarked→uniform→markedはdiag(2,.5)変形で接続不一致拒否。固定後は108要素の全接続と参照制限/変形の可換性が成立する。
既存transform_curved_project自体は変更せず、未固定の拒否をテストに残した。
CLI freeze-curved-refinementは新規Projectへ保存、GUIは固定状態/番号保護/解除/後続再指定/保存再読込とUndoへ接続。
新GUI応答中の入力変更を拒否し、図上再選択は固定を明示解除する。
関連21unit14.777秒と追加2unit2.139秒PASS。最終新モジュールは8件。
専用validate_frozen_curved_refinement.pyは75.988秒PASS、四形状I/A/2I/2Aとtune四試行の新規8 FEM。
独立質量a^4*c差最大4.660e-16、Green面積ac/回転体積a²c、f/両RQ/G/TTF尺度差最大3.176e-14、場差4.103e-12。
元50kHzの目標/メッシュ差条件で実TUNED、x=1.1、最終差7498.935Hz。全固定prefixと完全保存replayが一致。
新Chrome9項目/旧途中挿入20項目PASS、各実worker/native保存を含む。外部HTTP0、固定行画像を目視。
専用/seedの1,002ソース系SHAは一致し、両browserの製品311ファイルも最終一致。
共有保存契約のため全scripts/validate.pyを一度起動。全320モジュール1,602unitは888.194秒、1,598合格/2skip/2不合格で終了1。
不合格はtest_coincident_circle_arcsの新診断版8期待（現行13）とtest_construction_diagnosticsの対応版一覧9止まり（現行10を含む）。
製品無変更で2テストのみ補修。旧版1の完全保存/CLI再生と未対応構築拒否を維持し、両モジュール12件1.198秒PASS。
初回全件FAILは保持し、修正後の単一full PASSにはしない。全件は再実行せず、補修対象の結果で補う。
seed別実行--skip-testsはPASS、benchmarks/validationの9モード19量のf差0、RF/エネルギー最大8.882e-16。
以後のsrc/tests/scripts/examples差分は前記2テストのみとdiagnostic-test-repair.jsonに記録。以後製品変更なし。
証拠索引out/frozen-curved-refinement-20260914/acceptance.json。full試行はout/validation-frozen-curved-refinement-20260914、seedは同frozen-curved-refinement-seed-20260914。
専用GUI PID1056389の完全argv照合後SIGINT、session3977終了0。full54011終了1、補修23187終了0。全検証終了、実行中handleなし。
新規外部資料/依存/旧資産参照なし。Hosted CI・新Wine比較・実測は未実行。subagent/skillなし。
親33=8受入/17進行/7他未受入/1範囲外は保持。N04は宣言アフィン変形/tuneへ進んだが、一般Studyの履歴付き形状/初期メッシュ掃引・自動番号対応・一般精度/効率は残る。
次はStudyへの宣言アフィン変換接続を限定する。studies.pyは現状Study版1、明示mesh/履歴付きsweepを先頭で拒否し、fixed_geometry_convergenceだけ受理する。
元Projectから各値を独立変換し、既存tuneのRF方針/相対写像と整合する形が候補。形状変更を固定領域収束として扱わず、番号対応を暗黙推定しない。
D01自動対応推定/個別枝回復、C00.V/G03/V02ほか全計画の残件も保持。
C00の旧7.17付属仕様/Wine所在はasync質問済み・未回答。取得不要の開発を継続でき、全体のblocking条件はない。
gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。
2026-09-14 JST 最新継続状態。開始HEADa26f3cc、clean。前goalターンの履歴途中図上挿入は実装/検証/commitでprogress。

本段階はD01の曲線比較メッシュによる非線形対応を実装/検証したprogress。全計画は未完、goal ACTIVE。
[CURVED_PIECEWISE_REMESH_TRACKING.md](CURVED_PIECEWISE_REMESH_TRACKING.md)が受入条件/数学/入力/検証/残件の最新仕様。
既存paired_meshはnative接続一致を要求するため、piecewise_remeshの独立比較メッシュを曲線へ拡張した。
新curved_piecewise_remesh_tracking.pyは比較宣言schema_version2、source_meshの完全版1弦メッシュと独立levels/stepsを受理する。
各native Caseの曲線/元メッシュから有効な比較空間を構築し、二次全接続/境界タグと実FEM境界の全区間係数を照合。
可変r detJを含むHφ特徴を元独立保存場で評価。対応はF1∘F0^-1で、物理座標で二次多項式とは限らない。
直接構築した閉PEC/axisの曲線TMを受理。反射構築・半領域・混在・未知schema/fields・反転要素・接続不一致・予算超過を拒否。
旧直線比較宣言版1、外側tracking版1/2、FEM/Case/物理定数/求積/許容差を保持。
既存曲線境界照合をcase/spaceで呼べる関数へ抽出。旧same-domain/affine呼出しは同じアルゴリズムを使用する。
初回新テストは版2入力拒否でred。関連20件は19合格/負例Caseの古いcontour残し1error（30.864秒）。
その検証入力をcontour=Noneで修正し、生成設定省略ケースも含む2件が3.014秒PASS。順序付き比較/中点改変拒否2件も11.563秒PASS。
最終対象は新8+従来直線5/同一曲線6/アフィン4=23テスト。分割実行の証拠を保持し全23を一括実行したとはしない。
独立u=1/Hφ=r adapterの別P2基底・二重積分が次数8の重なりと小数8桁で一致。adapterは固有モードではない。
新validate_curved_piecewise_remesh_tracking.pyは28.933秒PASS、合成2半楕円接続の旧/新2尺度4実FEMと保存/CLI/逆向き履歴。
旧26/新104/比較26要素、次数4/8重なり0.9963266026323123/0.9963244749453846。体積比1.125²と独立Greenに相対1e-12以内。
連続解析体積との差約2.3221e-4を幾何誤差として保持。2倍尺度のf/両RQ/G/TTF差最大3.37e-14、H/Er/Ez全セル3点差最大1.57e-13。
専用検証中997ソース系ファイル不変。以後は追加2テストとブラウザー検証器だけ変更、製品ソースは不変。
GUI最終browser-visualは8項目PASS、外部HTTP0。native保存読込/数値報告/逆向き拒否と交換/履歴保護/保存再読込/改変拒否を確認。
初回browserは0.0→0のJSON表記による宣言hash差で停止。数値報告からhashだけを別扱いし、各宣言の再検証は保持した。
browser-finalは8項目PASSだが最終画像が再読込待ち中だった。入力欄復元も待つよう検証器を直しbrowser-visualの最終画面を目視。
証拠索引out/curved-piecewise-remesh-20260914/acceptance.json、native-validation/report.json、browser-visual/report.json。
GUIは保存済み4FEMを読むだけ。全unit/seed/全validate/Hosted CI/GUIサーバー再起動は未実行。新規依存/外部資料/旧資産参照なし。
専用GUI PID1009602の完全argvを照合しSIGINT、session30859終了0。全検証終了、実行中handleなし。subagent/skillなし。
親33=8受入/17進行/7他未受入/1範囲外を保持。D01の明示曲線比較写像は追加したが、自動対応推定/個別枝回復/一般物理精度は未完。
N04の形状変更後の細分番号移送/履歴付き形状掃引、C00.V/G03/V02ほか全計画の残件も保持。
次はN04の分割選択自体の保存/移送による形状掃引、またはD01の対応推定/個別枝回復を既存契約から限定する。
C00の旧7.17付属仕様/Wine所在はasync質問済み・未回答。取得不要の開発を継続でき、全体のblocking条件はない。
gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD16d0cd9、clean。前goalターンは大規模図上選択の実装/commitでprogress。
本段階はN04残件4の履歴途中への図上挿入・既存marked段階の再選択を実装/検証したprogress。全計画は未完、goal ACTIVE。
[GUI_CURVED_HISTORY_INSERTION.md](GUI_CURVED_HISTORY_INSERTION.md)に受入条件・操作/保存範囲・独立検証・再現入力を記録した。
選択欠落と39→56要素で同じID20のP2参照重心が約18 mm変わる例を先に保存。旧番号を暗黙再利用しない。
web/app.jsの内部collect(prefix)で前半だけの有効Projectを既存APIへ渡す。Case/FEM/許容差・API/保存スキーマは無変更。
段階指定（1始まり）、先頭/途中/末尾へのmarked挿入、行ボタンからの図上置換をSVG/Canvas共通で追加。
後続uniformとmarkedの種類/角度/順序を保持し、marked番号を空欄化、旧文字列を参照表示。未修復は保存/計算を拒否する。
有効な前半だけで次の未指定行を図上再選択できる。直前の図上操作前の全履歴への単段undo、入力変更時のundo拒否を提供。
選択署名は全生履歴/行ID/前半Project/反映先を含み、応答/準備/反映時に確認する。元メッシュと元領域を保持。
一様段数方式の途中挿入にも対応。全段数の最低4^n要素が予算を超える場合は先に拒否し、通常のnative品質/予算検査を維持。
関連test_gui_curved_mesh_selectionは4unit10.838秒PASS。新Chromeはbrowser-first20項目PASS、修復・保存再読込・実FEMを含む。
初回画像で細分方法のselect幅不足を確認しCSS列幅だけを修正。browser-append6項目/実FEMと画像で最終CSSを確認。
既存大規模browser-large-append21項目PASS、26,624要素の全操作/準備中入力変更/非同期破棄を確認。
新scripts/validate_curved_history_insertion.pyは6表示応答の全native配列、232/26,664要素の最終履歴と独立Green境界積分を確認。
31.223秒PASS、面積/回転体積は元固定二次境界に相対1e-12以内。保存場をeigsh禁止で再読込しRF9量をGUIと照合。
232要素の保存f=1614628212.5625715 Hz、U≈1 J、E/H各≈0.5 J、accelerator R/Q≈160.8151379 Ω、circuit≈80.4075690 Ω。
初回ブラウザー以後の製品差分はCSSのみと専用検証が記録。993ソース系/ブラウザー文書/保存場は専用検証中不変。
全ブラウザー外部HTTP0。新規外部資料・依存・旧資産参照なし。subagent/skillなし。
証拠索引はout/curved-history-insertion-20260914/acceptance.json。各browser*/report.json、native-verification/report.jsonを参照。
実FEMは小規模2ジョブ。大規模eigsolve、全unit/seed/全validate/Hosted CI/サーバー再起動は実行していない。
専用GUI PID978350の完全argvを照合してSIGINT、session60972終了0。全検証プロセス終了、実行中handleなし。
親33=8受入/17進行/7他未受入/1範囲外は不変。N04残件4の途中挿入は完了、履歴付き形状/初期メッシュ掃引と番号対応は未完。
次は残るN04の形状変更後の対応、またはD01の曲線変形の一般写像を、既存仕様と独立不変量から限定する。
一般適応効率/物理精度、C00.V/G03/V02ほか全計画の残件は維持する。
C00の旧7.17付属仕様/実行環境の所在はasync質問済み・未回答。資料探索の同じ失敗を繰り返さず、取得不要の開発を継続できる。
全体のblocking条件なし。gitメタデータはrequire_escalated。以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEADb6d624c、clean。前goalターンはC00版別参照の記録/commitでprogress。
本段階はN04の大規模曲線メッシュ図上選択を実装・検証したprogress。全計画は未完、goal ACTIVE。
[LARGE_CURVED_MESH_SELECTION.md](LARGE_CURVED_MESH_SELECTION.md)に受入条件・実装・数値/操作/費用・残件を記録した。
元の5,000上限拒否を26,624要素の合成Caseで再現してから、gui_curved_mesh.pyの既定を250,000へ拡張。
Case自身の小さい予算を守り、native節点/要素番号/二次曲線を変更しない。FEM/保存契約/許容差は無変更。
新web/curved-mesh-canvas.jsは5000超のPath2D曲線/制御点凸包索引、画面範囲の描画と背景再利用を提供。
従来SVGを保持し、クリック/ドラッグ/矢印/ホイール/拡大ボタン/番号移動/Enter/Spaceを接続。
入力署名を要求前/応答後/準備後/追加時に確認。準備中の操作を無効にし、Project変更/追加/再表示で旧描画とイベントを破棄。
既存CSPを保持。初回画像でinline styleが適用されず既定300x150となる問題を発見し配布CSSへ移した。最終は344x360表示。
関連test_gui_curved_mesh_selectionは4unit10.725秒PASS。大規模の全配列・4^n要素数・元予算/Case・明示メッシュを確認。
最終製品の実Chromeはbrowser-final17（250,000上限測定）、browser-pointer-fixed21、小規模一様/局所履歴各6がPASS。
中間browser-races19/初回browser-first15は保持。pointer初回は検証式の負数埋込でSyntaxError、検証器だけ括弧修正後に21件PASS。
全最終ブラウザーの308製品ファイルは現在と完全一致、外部HTTP0。小規模2例は元worker/FEMの保存Caseで選択番号を確認。
大規模は26,624要素/53,569節点。HTTPから準備終了18.758秒、ブラウザー準備216.4ms/描画40.8ms、5クリックCDP往復3.77〜3.90ms。
独立合成格子250,000要素/501,501節点は準備2178.6ms/描画250.7ms、解析24点の判定合計0.2ms。大規模eigsolveではない。
新scripts/validate_large_curved_mesh_selection.pyが表示全配列/Caseと実計算用空間を照合し、選択履歴を再構築。
番号0/1999/2000/13312/26623、26,624→26,676要素と元履歴が一致。独立二次境界Green面積/体積は元26要素とも相対1e-12以内。
63.546秒PASS、専用検証中991ソース系ファイルとブラウザー3文書不変。以後は検証mjsへ追加ポインター検査のみ、製品308は不変。
証拠はout/large-curved-mesh-selection-20260914/acceptance.json、各browser*/report.json、native-verification/report.json。
2枚の新表示と従来画像の表示確認範囲は専用文書。新依存/外部資料/旧資産参照なし。subagent/skillなし。
全unit/seed/全validate/Hosted CI/サーバー再起動は実施していない。今回のFEM実行は従来SVGの小規模2例だけ。
全ブラウザー/専用検証は終了。専用GUI PID936153と完全argvを照合してSIGINT、session70647終了0。実行中handleなし。
親33=8受入/17進行/7他未受入/1範囲外を保持。N04大規模図上選択は完了、履歴途中への図上挿入/形状変更後番号対応/一般適応効率は未完。
次はN04残件4の履歴途中への図上挿入、またはD01の未対応な曲線写像を、独立不変量と直接の利用先から限定する。
C00の旧7.17付属仕様/実行環境の所在はasync質問済み・未回答。前段の同じ資料探索を繰り返さず、取得不要の開発を継続できる。
C00.V/G03/V02ほか全計画の残件は保持。現段階に全体のblocking条件はない。gitメタデータはrequire_escalated。
以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD398817a、cleanからC00/K02・C02の旧曲線仕様を調査したprogress。
[C00_CONIC_INPUT_RESEARCH.md](C00_CONIC_INPUT_RESEARCH.md)に版付き原本、矛盾、独立数学対応と次の受入条件を保存。
現存の元台帳7入力/設定/数値出力は全bytes/SHA/版表示一致。7.17 release 1-13-2006を保持。
旧/tmp/superfish-wine-runtime/input-spec/SFCODES.txtは欠損。/home/sin/code/superfishと記録されたWine環境もない。
PATHにwine/wine64なし。/home/sin/code,/tmp,/home/sin/.wine,/home/sin/Downloadsの該当ファイル名探索で付属仕様/実行ファイルは見つからない。
旧ソルバーのソース・実行ファイル内容を取得/参照/実行していない。ユーザーへ保存先パスをasyncで質問済み、回答はまだない。
DOE OSTIの公式1987年マニュアルをout/c00-conic-input-spec-20260914/osti.pdfへ取得。
SHA6ba0f0374057bd3f2bdcb55a62247d0f820187b7039dafd51820087e97234851、9489185bytes、210pages。
入力仕様は印刷2-9〜2-12、PDF1始まり39〜42。PDFはテキストなしで、画像を表示して確認した。
この版のNT2は円のみ、NT3は第1象限、X0/Y0/THETA不使用。本文2XY=R²に対し表NT欄2XY=Rの矛盾あり。
相対許容差は画像で10^-3。旧ネットOCRから10^-5と推定しない。対象7.17の楕円/既定値へは流用しない。
CERN公式2010school/Indico時間割には目当てのSuperfish Exerciseリンクが見つからず、転載抜粋は仕様根拠にしていない。
USPAS403/UNTの直接PDFは非PDF/推測旧CERNパス404、OSTI取得成功。追加ネット探索は同じ失敗の一律反復を避ける。
自前の数学導出はnative矩形双曲線の半軸(R,R)、branch1、rotationπ/4、u=log(Y/X)/2と明示四分円。
自作36弧612点/負例2件はPASS、最大誤差1.1102230246251565e-15、988ソース系ファイル不変。
out/c00-conic-input-spec-20260914/{reference-audit,neutral-geometry-report,source-snapshot}.json、同check-neutral-geometry.pyが根拠。
機械可読な追補はdocs/c00_conic_input_reference_audit.json。元inventoryは過去記録のまま保持した。
製品/FEM/parser/CLI/保存/許容差は無変更。NT2/3は引き続き拒否。unit/seed/全validate/GUI/Hosted CIを今回実行していない。
C00の該当旧入力照合は付属仕様/実行環境の所在待ちだが、全計画のblockerとしない。
次は保存先回答があればその公式仕様のPO表だけを照合し、なければBACKLOG/COMPATIBILITY_PLANの取得不要な未完項目へ進む。
同じ資料不足を繰り返すだけのターンにしない。G03の一般物理表面精度、C00.V/V02ほか親33残件は継続。
親33=8受入/17進行/7他未受入/1範囲外、goal ACTIVE。完了/blockedにしない。
全ネット取得/検証プロセスは終了。subagent/skill/新依存なし。gitメタデータはrequire_escalated。
以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD d8855b0、clean。前goalターンは構築10受入commitというprogress。
本段階は[G03現行要件照合](G03_CURRENT_AUDIT.md)と欠けていた楕円の幾何/FEM別表面細分証拠を追加したprogress。
G03の番号付き5要件、最小子午面半径、全フィレット/退化、旧NT=2/3、物理ピークを実装/テスト内容/記録と照合。
旧G03_ACCEPTANCE.mdの表は履歴と明示し、現在の専用受入と未完項目をG03_CURRENT_AUDIT.mdへ整理。
既存out/validation-g03-native-geometry-separated-20260908は幾何3水準×FEM2水準のf/場/RF/モーメントPASSだが物理ピーク未確認。
楕円の保存上下界は存在した。各2FEMでは2区間条件を満たせないため、元6nativeを再検証し各系列を第3FEMへ延長。
新scripts/validate_geometry_surface_convergence.pyは3新solveと元6結果を分け、全9結果/固定幾何6区間/幾何2区間を検証。
独立二次補間位置上界max(a,b)h^3/(72sqrt(3))と140桁節点差×5/4、楕円解析面積/体積、固定領域不変、Ritzと高次積分を別々に確認。
577.959秒PASS、終了0、元アーカイブと988ソース系ファイル不変。初回失敗なし。全検証プロセス終了済み。
追加要素5760/18576/53808、位置上界6.07011e-6→7.58764e-7→9.94340e-8 m。五量の全比較は元の目標内。
楕円はSMOOTH_WITHIN_TOLERANCE、既存双曲線はUNVERIFIED_GEOMETRY。双曲線を滑らかなピーク合格へ読み替えない。
証拠はout/g03-separated-surface-independent-20260914/report.json、archive-provenance.json、out/g03-separated-surface-20260914/acceptance.json。
これは合成楕円1例の経験的な幾何/FEM別細分。独立な非球形Maxwell参照や一般物理誤差上界ではない。計算スペクトルは保存例の1モード。
製品/FEM/保存/GUI/許容差/benchmarksは無変更。unit/seed/全validate/Hosted CI/Chromeは本段階で再実行していない。
次はC00/K02・C02の対象版旧曲線NT=2/3仕様の確認とnative変換。既存legacy_input.py/LEGACY_INPUT.mdはNT=2/3,X0/Y0,極座標を拒否。
既存inventoryの/tmp/superfish-wine-runtime/input-spec/SFCODES.txtは現在存在しない（過去SHA8203169713608903bcf5d4ac600efd2b98f221af9ab8856213ea306eab675627）。
PROVENANCE.mdは付属公式SFCODES.DOCの入力仕様をR25と記録している。許可済みの公式文書または公開仕様を探し、欠けた文書から既定値を推定しない。
対象実行版は保存記録でAutomesh/Fish/SFO/SF7 7.17 release 1-13-2006。インストーラー名7.20や文書改訂日と混同しない。
旧solverコード/バイナリ内部は参照禁止。既存exeのblack-box実行・入力/設定/数値出力は2026-09-05の許可範囲。生結果はignored out。
C00.V/旧入力/物理精度/V02と全計画は未完、親33=8/17/7/1。goal ACTIVE、現段階blockingなし。手元の確認材料を広げて続行可能。
worktreeは/home/sin/code/agent/reserch/superfish-ng。subagent/追加skill/外部資料/依存なし。gitメタデータはrequire_escalated。
以下の過去履歴よりこの先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD c21c54f、cleanからG03一般非円フィレット構築を実装。
前goalターンは等距離/反対枝の診断13受入commitというprogress。本段階も実装・受入証拠を伴うprogress。
[非円円錐曲線同士の全元点対からのフィレット構築](NONCIRCULAR_CONIC_FILLET.md)を限定受入。
noncircular_conic_fillet.pyが同一支持の共有端点/全反射対、反対枝、一般有限射影の全相手元点を展開する。
元点対を中心数で潰さず、同じ第一元点の分率囲みを共有して第二分率、別元点なら第一分率で順序を証明。
有向元接線の内積符号と距離符号から厳密零長を判定。元/相手カスプでも元曲線は正則。
構築版10を厳密parser/dispatch・付属診断13・GUIへ接続し、旧構築1〜9/保存診断1〜13を保持。
構築10+診断12以下は拒否。無限対/所属・順序不足はUNVERIFIED、列挙PASSと個々の出力/Caseの可否は別。
共通_fillets_from_search/既存分類/FEMは変更していない。
初回9unit9.408秒、関連57unit42.890秒+旧版3/4追加2unitがPASS。
独立32条件61参照元点対と解析面積/体積・実FEM尺度則が146.511秒PASS、987ファイル不変。
初回は逆順反転で厳密共有端点を保持すると誤って仮定し1対対2対で停止。EllipseArc開始角の二進π正規化で実際に端点は弧外だった。
製品を変えず、参照で真のπと実保存範囲の所属を確認して専用全検査を再実行した。
合成例は最初の軸[-L/2,L/2]が正しくCase拒否され、[0,L]への平行移動後に正式fixture化した。
独立A=15.1289918351868313、V=167.1595705414297741、実Caseとの差は0/2.22e-16。
FEM各7519幾何節点、同接続/2倍座標、f比0.4999999999999984、両R/Q/G/TTF比は1との差<2e-14。
場係数相関1.0000000000000002。これは相似不変量であり離散化誤差/物理ピーク収束ではない。
Chrome初回56/実再起動54、9入力・計42取得・全21組の保存バイト一致・3画像目視PASS。
旧構築8/9と新10、同一中心4足/零長/カスプ/無限対/出力精度不足、beta不正と改変拒否を確認。
製品307ファイル不変、外部HTTP0。全Chrome/GUI/検証プロセス終了確認。GUIは専用PID+argvを照合してSIGINT exit0。
準備のfixture名/実行Python名の誤りも製品と分けてログへ保持。
証拠はout/noncircular-conic-fillet-20260914/acceptance.json、独立-fixed/ブラウザーinitial/restarted報告。
構築9fixtureは53925 bytes、SHA ad2b9fe40c302939192954ed55e6bc5fd8f4e900089549847985db02191f642d、開始HEADで全文再現済み。
次はG03_ACCEPTANCE.md/CONIC_GEOMETRY.md/COMPATIBILITY_PLAN.mdの最新要件照合から一件を限定する。
一般フィレットの構築10まで接続したが、物理ピーク収束、旧曲線指定対応・対象版入力/数値照合、G03全体/C00.V/V02は残る。
親33=8受入/17進行/7他未受入/1範囲外、全計画goalはACTIVE。完了/blockedにしない。
新幾何専用FEMを実行した。seed/全validate/Hosted CIは実行していない。現時点にblocking条件なし。
現在worktreeは/home/sin/code/agent/reserch/superfish-ng。旧資産は触らず、subagent/追加skillなし。
gitメタデータ更新はrequire_escalated。以下の過去履歴より先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD1692c5c、cleanから一般非円フィレット構築を調べ、必要な恒等零残件を先に解決した。
前goalターンは一般有限射影の相手実点回復・診断12受入/commitというprogress。本段階も実装・受入証拠を伴うprogress。
[同じ円錐曲線の等距離オフセットと反対枝](EQUAL_DISTANCE_CONIC_BRANCHES.md)を限定受入。
新equal_distance_conic_branches.pyが同じ凸な枝の反対法線側の離隔、反対双曲線枝の0/1/2中心を分類する。
重根の三次行列束は異なる2元点なら階数1。反対枝はlambda=-1/(n*a²)だけで、両枝の外向き距離が必要。
q=y²=b²(d²-n*a²)/(n*a²*(a²+b²))、元点(±sqrt(1+q),同符号sqrt(q))、中心(0,(a²+b²)/b*同符号sqrt(q))。
回転と元表現へ厳密に戻し、有限弧/符号/1ULP/尺度を検査。q=0正則接触、q>0横断、外向きなのでカスプなし。
診断13、旧12を専用関数へ固定。旧保存診断1〜12/構築1〜9を保持。新規フィレット構築はまだ接続していない。
関連112unit55.486秒+主軸交換/半回転の追加1不変量PASS、初回6unit0.016秒PASS。
独立576条件94元点対/凸な最近点不等式1080件が2.404秒PASS。初回は576条件保存後に検証器のHyperbolaArc位置引数誤りで停止。
検証器だけを修正し専用全検証を再実行した。専用後の変更は追加テスト1件のみで、製品と検証器は不変。
Chrome初回51/実再起動49チェック、計42取得、9入力、4画像目視PASS。元Case、保存バイト、全構築/診断、改変拒否を確認。
両GUIサーバーはPID+argv照合後SIGINTでexit0。Chromeもexit0、検証/サーバーの実行中プロセスなし。
証拠はout/equal-distance-conic-branches-20260914/acceptance.json、independent-fixed報告、browser initial/restarted報告。
fixture12は88,730 bytes、SHA4d71a33e63253e19ebc3de2ce9b0745eb936c8539fbc80e48cd49413f11efe86、変更前1692c5cで全再現済み。
次は一般非円の全元点対からのフィレット構築（想定構築10）。source-fractionと順序、全保持端点、零長/出力誤差/Caseを確定する。
構築の参考はcircle_conic_fillet.py、circular_fillet.py、共通conic_fillet._fillets_from_search(retain_whole_at_endpoint=True)。
一般有限射影はconic_offset_intersectionsのsource_local_box/target_local_boxとsource_candidate_indexを使える。
同じ元候補に相手2点なら第一fractionを共有し、第二fractionで辞書式順序。別元候補は第一fractionが別である。
同じ支持/同じ補正距離はreparameterized_conic_offsetsで全共有端点とself_contacts/included_parameter_pairsを利用できる。
自己接触中心はcoordinate_factor*sqrt(coordinate_square)を指定axisへ置き第一回転と中心で戻す。対を中心数で潰さない。
同じ物理点の共有端点は厳密零長として残す。新しい反対枝のrowsはsource_contacts_coincide=Falseを含む。
一般有限交点で両distancesが同じなら、tangent_parallelと元方向の接線内積の正符号により元接点一致を証明できる（カスプでも元接線は正則）。
_source_candidate_indexが異なる根の第一fraction順序はinterval分離で確定し、不足ならUNVERIFIED。数値近似のsortだけで順序を保証しない。
構築10を加える場合はtangent_constructionの厳密版別parser/dispatch、construction_diagnostics対応版、web/app.jsのfillet版一覧を更新する。
Case/FEMへ新形状を通すので次段階には解析面積/体積と実FEM尺度則も必要。診断変更だけの本段階ではseed/FEM/全validate/Hosted CI未実行。
物理ピーク収束・G03全体/C00.V/V02は未完。親33=8受入/17進行/7他未受入/1範囲外、全計画goalはACTIVE。
現在worktreeは/home/sin/code/agent/reserch/superfish-ng。旧資産は触らず、subagent/追加skillは要求がなく未使用。
gitメタデータ更新はrequire_escalated。以下の過去履歴より先頭を優先する。

2026-09-14 JST 最新継続状態。開始HEAD1cc75c1、旧診断11 fixture保存から一般両非零オフセットの相手回復へ進んだ。
前goalターンは全元候補射影の受入・commitというprogress。本段階も実装・受入証拠を作成したprogress。
[両非零の円錐曲線オフセット交点](GENERAL_CONIC_OFFSET_INTERSECTIONS.md)を限定受入。
conic_offset_intersections.pyが重根から階数2の単一実点/階数1の0〜2実点を回復する。
root_radical_arithmetic.pyが元根号と追加有理平方根の従属関係も厳密判定。射影はprivate handlerで孤立根を再利用。
診断12へ接続し、旧11を専用関数に固定。旧診断1〜11/構築1〜9を保持。新フィレット構築はまだ接続していない。
118テスト57.639秒+追加2不変量0.589秒PASS（初回内部16テスト16.424秒もPASS）。
独立初回7条件は数値合格後、並行した3テスト編集をファイル不変性ガードが検出してexit1。
数値実装はその間不変。実行器に入力SHA/変更パス保存を追加し編集終了後に一度再検証、137.664秒PASS。
最終独立7条件36候補/87法線足/18元点対。全unittest/seed/FEM/Hosted CIは今回未実行、許容差/benchmark不変。
Chrome初回53/再起動51チェック、計38取得、8入力、5画像目視がPASS。元Case、全診断・構築、保存バイト、改変拒否を確認。
作業用両GUIサーバーはPID+argv照合後SIGINTでexit0。実ブラウザーもexit0。実行中の検証・サーバーなし。
証拠はout/conic-offset-target-recovery-20260914/acceptance.json、専用frozen report、browser initial/restarted report。
開始前fixture11は88,730 bytes、SHA c83656d570c532208b7a3c9910dc999b907eabfaedd570d73b1055327c09f44f。
次は一般非円の全元点対からのフィレット構築か、恒等零射影（同一支持/逆符号等距離）の残分類。
構築には相手元点の原パラメータ/順序と端点保持/零長/誤差境界を新しく確定し、旧保存構築の版を維持すること。
恒等零は有限根なし/離隔と扱わない。一般回転の有限根例は約118秒なのでSturmを元/相手や根ごとに再構築しないこと。
物理ピーク収束・G03全体/C00.V/V02は残る。親33=8受入/17進行/7他未受入/1範囲外、全計画goalはACTIVE。
以前からの現在worktreeは /home/sin/code/agent/reserch/superfish-ng。旧資産は触らず、ユーザー所有出力は上書きしない。
subagent/追加skillの要求はなく未使用。gitメタデータの更新はrequire_escalatedを使用する。
以下は過去段階の履歴であり、この先頭状態を優先する。

2026-09-14 JST 最新継続状態。開始HEADcbfd162、cleanからG03の一般両非零オフセットへ進んだ。
前goalターンは同一支持の別主軸表現の等距離オフセット診断11を受入・commitしたprogress。
[両非零オフセットの全元候補射影](GENERAL_CONIC_OFFSET_PROJECTION.md)を専用範囲で受入。
新規conic_offset_projection.pyは相手円錐曲線/指定半径円の三次行列式の重根という必要条件を、
元曲線の有理チャート＋正平方根へ代入して次数56以下の多項式にする。正のH/S共通因子だけを余り零で除く。
project_conic_offset_candidatesで全元根・元平方根符号・有限元弧・元カスプを囲み、未完の全箱と理由を保存。
projection_completeは元候補だけ。target_incidence_certifiedは常にfalse。相手実元点・符号・有限弧・全元点対は未接続。
対称楕円対の8候補は既知4対角交点を含み、残る4つは相手の内向きオフセットの外にあることも独立区間式で確認した。
公開診断11、保存診断1〜11/構築1〜9、Case/mesh/solver/場/RF/GUIの旧経路へ新候補を自動接続していない。
新primitive_polynomial_roots.pyは正倍率を保持する整数疑似余り、整数端点評価、Sturm/GCD列の再利用。
既存polynomial_roots/RootSystemは不変。RootSystem/AlgebraicRootの代数符号/根号判定を新経路で再利用する。
旧有理Sturmは最初の次数56例で171.83秒経過して未完。専用ログ/PID/コマンドを照合してSIGTERMし終了143。
最初の別sandboxからはPIDが見えず、昇格した同じ専用ログ照合で実プロセスを停止した。現在は生存プロセスなし。
初期整数試作0.420686秒/8根、回転.3/.7例51.849796秒の後、列の重複計算を除いた。
最終整数版の同じ最初の例は0.330499秒/8根/91箱、[-1,1]要求幅1/4096。全入力の速度保証ではない。
初回新10unitは9合格/予算不足のテスト前提1失敗、2.183秒。有理根では小予算でも完了するため、無理数の根の例へ修正。
製品はこの修正で不変。関連35unit13.067秒が一括PASS。旧root/sign/一方距離0/直線交点の利用側も含む。
独立validator128.253841秒で336行列式点/6条件32元候補がPASS。最大正規化行列式差1.148e-133以下。
参照は元点＋有向単位法線、3×3行列の4点行列式補間と5×5 Sylvester行列式、140桁二分。消去係数やSturmは参照に使わない。
2048/4096元パラメータ標本が一致。参照の標本完全性は数値証拠であり認証証明ではない。
6条件は対称楕円8候補、移動楕円6、二進回転楕円6、楕円/双曲線8、双曲線/楕円4、双曲線/双曲線0。
二進回転の両チャート/元所属/独立参照は113.287427秒。今後の相手回復と実用時間は別の受入条件が必要。
記録はout/general-conic-offset-projection-20260914/acceptance.json、同independent系。既知の開始4不変量、初回ログ、時間測定/意図的停止も保存。
新外部資料/依存/旧版資産・実行/subagentなし。公開経路を変えていないため新CLI/ブラウザーなし。
全suite/seed/Hosted CIは実行せず、許容差/benchmarks不変。実行中検証・未解決承認拒否・質問待ちはない。
次は射影根に対応する相手の実元点を回復し、元平方根/距離符号と有限相手弧、全元点対・中心重複を認証して一般交点へ接続する。
その後の新フィレット構築、物理ピーク収束・G03全体/C00.V/V02も未完。親33=8受入/17進行/7他未受入/1範囲外、goalはACTIVE。
以下の履歴よりこの最新状態を優先する。

2026-09-14 JST 最新継続状態。開始HEAD9da1f92、cleanからG03の次の残件を実装した。
前goalターンは一方距離0の非円円錐曲線交差診断10を実装・受入・commitしたprogress。
[主軸表現が異なる同一円錐曲線のオフセット](REPARAMETERIZED_CONIC_OFFSETS.md)を限定受入。
同じ非円楕円/同じ物理枝の双曲線について、主軸変換の有理等号と向き補正距離の等号、
π係数を保持する有限重なり/共有端点、両元座標系の全反射元点対と中心重複を診断11へ接続した。
以前の公開分類器を_classify_offset_degeneracies_v10として保存し、保存診断1〜10/構築1〜9の規則を保持。
構築/Case/mesh/solver/場/RFは不変。異なる支持・距離の両非零一般交点、新フィレット構築の代用ではない。
初回6unitは5合格/テスト前提1失敗、0.554秒。.3と.3+πの二進係数が実際には反対だったため、
不一致の.7に修正し、.3の厳密一致/非単位ノルムも追加。製品はこのテスト修正で不変。
関連103unit57.033秒が一括PASS。既存構築5のFEM尺度unitを含むが新幾何のFEM精度検査ではない。
独立140桁法線成分二分/両元点＋法線の1,984条件が8.755431秒PASS。435反射元点対、608無限対条件。
両主軸順、零/正負距離、一般二進回転、枝番号、尺度2^-40/1/2^40、反転/交換、有限分率制限を含む。
参照の数値計算を認証付き完全性証明とはしない。製品の閉形式/変換/所属判定を参照へ使っていない。
実CLIは例の1中心を版11/全域完了で出力して終了0。
構築付属診断GUIの実Chromeは初回46/実サーバー再起動44チェック、各7入力17取得がPASS。
新しい楕円有限/重なり、双曲線有限、精度不足を構築5の付属診断で表示して未確認構築の適用不可を維持。
旧保存診断10、新構築9の診断11、生要求候補選択/Case適用/native出力/改変拒否/編集失効/beta拒否を確認。
全17保存ファイルがバイト一致、再起動後の有限2例/精度不足の3画面を目視した。両GUIプロセスは正常終了で停止済み。
自前保存診断10を開始HEADで全文再現してfixture化。元バイト88730/SHAとパスは上記文書。
追加API照合では、開始時に記録した未確認診断を同じ再現済み構築へ付け、旧10未確認/新11有限と版番号だけの変更拒否を確認。
製品301ファイルは独立validator/両ブラウザーを通して不変。記録はout/reparameterized-conic-offsets-20260914/acceptance.json、同independent/browser系。
新外部資料/依存/旧版資産・実行/subagentなし。全suite/seed/Hosted CIは実行せず、許容差/benchmarks不変。
実行中検証・未解決承認拒否・質問待ちはない。検証後は文書だけを更新した。
次は異なる支持・向き補正距離の両非零オフセットや双曲線の異なる物理枝の一般交差と新フィレット構築。
物理ピーク収束・G03全体/C00.V/V02も未完。親33=8受入/17進行/7他未受入/1範囲外を維持、goalはACTIVE。
以下の記録よりこの最新状態を優先する。

2026-09-14 JST 最新継続状態。開始HEAD8e5ffb8、cleanからG03の次の段階を実装した。
前goalターンは円同士の全元点対からのフィレット構築9を実装・受入・commitしたprogress。
[元の非円円錐曲線と法線オフセットの全交点](CONIC_IMPLICIT_OFFSET.md)を限定受入。
一方の距離が0の楕円/双曲線対を、二次形式代入の次数4/16以下の全根、元平方根符号、有限両弧/枝で分類する。
通常接触/カスプ、同じ中心へ来る別source元点を分け、新規診断10へ接続した。
以前の公開分類器を_classify_offset_degeneracies_v9として保存し、保存診断1〜9と構築1〜9の規則を保持。
構築/Case/mesh/solver/場/RFは不変。新機能は診断API/CLIで、独立診断を構築GUIへ適用する機能は追加していない。
両距離非零の一般処理や、新フィレット候補構築の代用ではない。
初回新7unitは6合格/偽解存在の期待1失敗、1.333秒。内側targetでは反対向きの外側オフセット根が存在しなかった。
別の外側targetに既知の反対向き接点(9/4,0)を与え、要求側の離隔と偽解除外を確認する入力へ修正した。
製品はこのテスト修正で不変。新規診断版の既存期待は9から10へ更新し、旧保存版の期待は保持した。
関連97unit56.631秒が一括PASS。既存構築5のFEM尺度unitを含み、新しい幾何のFEM精度検査とはしない。
140桁元関数/勾配の独立80条件200元点対が96.727825秒PASS。196中心、横断172/通常接触24/カスプ4。
20系列×4変種で尺度2^-40/1/2^40、反転/交換、楕円/双曲線両枝、端点/同一中心/有限制限、一般回転/平行移動を確認。
参照は1024/2048分割の勾配零点候補をNewtonで照合し、解析曲率カスプと単調区間二分を使用する。標本参照自体の完全性は認証証明ではない。
実CLIは例の4交点を版10/全域完了で出力し終了0。
既存構築GUIの実Chromeは初回49/実サーバー再起動47チェック、各7入力19取得がPASS。
新診断10/旧保存診断9、生要求からの構築、Case適用/native出力、未確認適用不可/改変拒否/編集失効/beta拒否を確認。
全19保存ファイルがバイト一致、再起動後3画面を目視。新しい独立診断をGUI操作した証拠ではない。
製品source300ファイルは独立validator/両ブラウザーを通して不変。両GUIは正常終了で停止済み。
記録はout/conic-implicit-offset-20260914/acceptance.json、同independent/browser-{initial,restarted}系。
自前保存診断9の最終受入済みブラウザー出力を開始HEADで全文再現してfixture化。元パス/SHA、導出とコマンドは上記文書。
新外部資料/依存/旧版資産・実行/subagentなし。全suite/seed/Hosted CIは実行せず、許容差/benchmarks不変。
実行中検証・未解決承認拒否・質問待ちはない。
次は両非零オフセットの一般処理と新候補構築、または異なる表現の同一非円支持曲線の未確認を解消する。
物理ピーク収束・G03全体・C00.V対象版/必須集合・V02利用者業務と全計画は未完。
親33=8受入/17進行/7他未受入/1範囲外。goalはACTIVE、blockedではなくprogress。
以下は過去の段階の記録であり、この最新状態が優先する。

2026-09-14 JST 最新継続状態。開始HEADa354d29、cleanからG03の次課題を実装した。
前goalターンは円/非円フィレット構築8を実装・受入・commitしたprogress。
[円同士の全元点対からのフィレット構築](CIRCULAR_FILLET.md)を限定受入。
構築版9で全有限元点対/順序、通常接触/負支持半径、同一支持円の孤立共有端点を候補へ接続した。
同一支持円の正長共有範囲と潰れ円の入射は無限元点対として選択不可。厳密零長と空保持範囲も選択不可。
一般二進回転のノルム差を保持し、出力誤差/G1とCase検査は別。旧構築1〜8/診断1〜9の規則を保持する。
既存の分類器/共有trim/FEM/場/RFと物理規約は変更していない。
初回新9unitは8合格/同一支持のテスト仮定1失敗、2.564秒。二進回転.3/.7のノルム差を見落としていた。
同一支持入力を±.3へ修正し、.3/.7は異なる同心支持円として離隔する検査を残した。
関連62unit37.834秒は61合格/既存の新規診断版期待1失敗。開始HEADにも残っていた版8期待を現行9へ修正。
最初の編集はインデント誤りでロード失敗、修正後の該当1unitが1.486秒でPASS。
62件の最終状態が全てPASSであり、一括成功実行ではない。これらのテスト修正で製品は不変。
160桁の独立Euclid幾何/周期区間と元曲線を用いた336条件264元点対と、新Case実FEMの一括validatorが25.241157秒PASS。
28系列×尺度3×両弧反転2×順序交換2。288有限条件/48無限条件、候補198FORWARD/48ZERO_LENGTH/18UNVERIFIED（全て空保持）。
合成7プリミティブの解析面積/体積、P2の2354節点で2倍尺度/場形相関約1、f比0.5、両R/Q/G/TTF不変を確認。
実Chrome初回94/実サーバー再起動92チェック、各19入力43取得がPASS。全43保存ファイルがバイト一致。
旧構築5/6/7/8と新9の5Case適用/native出力、零長/未確認選択不可、改変拒否/編集失効/beta拒否を検査。
再起動後4画面を目視した。製品source299ファイルは独立validator/両ブラウザーを通して不変。
両GUIは正常終了で停止済み。実行中の検証・未解決承認拒否・質問待ちはない。
記録はout/circular-fillet-20260914/acceptance.json、同independent/browser-{initial,restarted}系。
旧構築8fixtureは最終受入済みの自前ブラウザー出力を開始HEADで全文再現して採用した。
元パス/SHA、導出、コマンドと途中失敗は上記文書。新外部資料/依存/旧版資産・実行/subagentなし。
既存構築1/2/5のFEM尺度unitを含む。全suite/seed/Hosted CIは実行せず、許容差/benchmarks不変。
次は非円弧同士の一般交点を限定する。物理ピーク収束・G03全体・C00.V対象版/必須集合・V02利用者業務と全計画は未完。
親33=8受入/17進行/7他未受入/1範囲外。goalはACTIVE、blockedではなくprogress。
以下は過去の段階の記録であり、この最新状態が優先する。

2026-09-14 JST 最新継続状態。開始HEAD2c90c5c、cleanからG03の次課題を実装した。
前goalターンは円/非円オフセット全交点の診断9を実装・受入・commitしたprogress。
[円・非円円錐曲線の全元点対からのフィレット構築](CIRCLE_CONIC_FILLET.md)を限定受入。
構築版8で認証付き元分率順序、全体を残す端点、同一中心の別元点、厳密零長/カスプを候補へ接続した。
潰れ円の無限元点対は診断証拠だけを保存して候補選択不可。出力誤差/G1と選択後のCase検査は別。
旧構築1〜7/診断1〜9の規則、共有trim、FEM/場/RFと物理規約は不変。
関連62unit49.421秒、後から追加した負支持半径の独立零長1unit3.465秒がPASS。63件の一括実行ではない。
初回8件は7合格/テスト側の未対応CLI引数1エラー。既存export-constructed-caseへ分けて修正した。
追加零長テストの初回は既知2接点だけを全根とした参照が誤り。独立因数分解で別4交点も含む6候補を確認し、
厳密零長2個と反転/順序交換の全4条件を検査した。これらの参照修正で製品コードは変更していない。
140桁元関数の独立44条件100元点対と新構築Caseの実FEMをまとめたvalidatorが61.535295秒でPASS。
候補状態は91FORWARD/5UNVERIFIED（全て空保持範囲）/4ZERO_LENGTH。
合成7プリミティブの解析面積/体積、P2の1934節点で2倍尺度/場形相関約1、f比0.5、両R/Q/G/TTF不変を確認。
実Chrome初回78/実サーバー再起動76チェック、各14入力32取得がPASS。対応する全32ファイルがバイト一致。
旧5/6/7と新8の4Case適用/native出力、候補不可/改変拒否/編集失効/beta拒否を検査。再起動後3画面を目視した。
製品source298ファイルは独立validatorと両ブラウザー実行を通して不変。両GUIは正常終了で停止済み。
記録はout/circle-conic-fillet-20260914/acceptance.json、同independent/browser-{initial,restarted}系。
旧構築7fixtureは最終受入済みブラウザー出力を開始HEADで全文再現して採用した。
開発途中の別出力は全文再現に失敗し不採用。元パス/SHA、導出、コマンドと途中失敗は上記文書。
既存構築1/5/6のFEM尺度unitを含む。全suite/seed/Hosted CIは実行せず、許容差/benchmarks不変。
新外部資料/依存/旧版実行/subagentなし。実行中検証・未解決承認拒否・質問待ちはない。
次は円同士の全根からのフィレット構築（従来版5のKrawczyk探索が残る）、または非円弧同士の一般交点を限定する。
G03全体・物理ピーク収束・C00.V対象版/必須集合・V02利用者業務と全計画は未完。
親33=8受入/17進行/7他未受入/1範囲外。goalはACTIVE、blockedではなくprogress。
以下は過去の段階の記録であり、この最新状態が優先する。

2026-09-14 JST 最新継続状態。開始HEAD758ec12、cleanからG03の次課題を実装した。
前goalターンは全元点対からの直線/円錐曲線フィレット構築7を実装・受入・commitしたprogress。
[円と非円円錐曲線オフセットの全交点](CIRCLE_CONIC_CROSSINGS.md)を限定受入。
円距離式から次数12/24以下の全根を分離し、元の正平方根符号、有限両弧、接触/カスプ/潰れ円を検査。
同一中心の元点対を証拠へ残して中心数と区別する。診断9を追加し、旧診断1〜8/構築1〜7を保持。
元の構築/Case適用可否/FEMは不変。新しい根から円/非円フィレットを構築する接続はまだない。
関連87unitそれぞれの最終状態がPASS。初回73件123.378秒は68合格/旧版・旧範囲期待5失敗、
修正対象6+追加14の20件4.834秒は19合格/旧範囲期待1失敗、該当1件0.008秒で最終PASS。
87件の一括再実行ではない。離隔した潰れ円のmetadata誤りも失敗を再現して修正した。
独立元関数50条件155.833秒PASS、その後のmetadata修正では影響する潰れ円3条件0.027105秒PASS。
最後に一般二進回転と負の円支持半径を組み合わせた1条件4.075243秒もPASS。重複を除く53条件。根/中心計算の式は変えておらず、一般回転の重い検証は繰り返していない。
初回の円/非円の一般二進回転smokeは1条件96.146秒。根分割予算は係数演算時間の保証ではない。
実Chrome初回/実サーバー再起動は各10入力55チェック22取得。全22保存ファイルのバイト一致、
2選択済みCaseの適用/native出力、改変拒否/編集失効と未確認構築の適用不可がPASS。再起動後3画面を目視。
初回後にmetadataを修正したが10入力の保存バイトは不変。再起動後sourceは最終版と一致。
記録はout/circle-conic-crossings-20260914/acceptance.json、同independent[-collapse]/browser-{initial,restarted}系。
旧版8fixtureの来歴、導出、検査コマンドと途中失敗は上記文書。CLIの新規合成4交点例もPASS。
既存構築1/5/6のFEM尺度unitを含む。全suite/seed/Hosted CIは実行せず、許容差/benchmarks不変。
両GUIは正常終了で停止済み、実行中の検証はない。新外部資料/依存/旧版実行/subagentなし。
次は円/非円フィレット候補への接続、または非円弧同士の一般交点を限定する。
G03全体・物理ピーク収束・C00.V対象版/必須集合・V02利用者業務と全計画は未完。
親33=8受入/17進行/7他未受入/1範囲外。goalはACTIVE、blockedではなくprogress。
以下は過去の段階の記録であり、この最新状態が優先する。

2026-09-14 JST 最新継続状態。開始HEAD a1640d0、cleanからG03の次課題を実装した。
[全根列挙からの直線・円錐曲線フィレット構築](ALGEBRAIC_CONIC_FILLET.md)を限定受入。
構築版7で円/非円楕円/双曲線と直線の全元点対を候補に接続した。中心が同じでも元点対は分け、
分率の辞書式順序を証明する。全体を残す有限端点は許可、空範囲/厳密零長/予算不足は選択不可。
候補の出力誤差/G1と閉輪郭/Case検査は別。旧構築1〜6、診断1〜8の規則を保持する。
共有trimを切出す前に自前構築5/6全文書をfixture化し、変更後の再計算一致を検査した。
関連70unit39.042秒PASS、後から追加した円24条件の1unit4.073秒PASS。71件の一括再実行ではない。
独立非円36条件を全完了後、別FEM driverの属性参照で失敗。参照側の同一中心順序も初回で修正した。
製品コードはこれらの参照修正で変更せず、FEMだけ再実行して4.083486秒PASS。全体一括成功報告とはしない。
合成端点構築Caseの独立面積/体積、P2の1354節点の2倍尺度/場形相関1、f比0.5、両R/Q/G/TTF不変を確認。
実Chrome初回72/実再起動66チェック、各27取得、全27ファイルのバイト一致がPASS。
旧5/6と新7の選択・Case検査・適用・native Case書出し、改変拒否/編集失効を検査。3画面を目視した。
記録はout/algebraic-conic-fillet-20260914/acceptance.json、同browser-{initial,restarted}/fem系。
全suite/seed/Hosted CIは実行せず、既存直接FEM消費先と新尺度検証で影響を限定。許容差/benchmarks不変。
両GUIは正常終了で停止済み、実行中の検証はない。新外部資料/依存/旧版実行/subagentなし。
次は曲線同士の一般交点/重解を限定するか、G03の現要件を照合する。
G03全体・物理ピーク収束・C00.V対象版/必須集合・V02利用者業務と全計画は未完。
親33=8受入/17進行/7他未受入/1範囲外。goalはACTIVE、blockedではなくprogress。
以下は過去の段階の記録であり、この最新状態が優先する。

2026-09-14 JST 最新継続状態。開始HEAD3926e6b、cleanからG03の次課題を実装した。
前goalターンは直線と非円楕円/双曲線の接触証拠・全域射影境界を実装/受入/commitしたprogress。
[直線と非円円錐曲線オフセットの全交点](LINE_NONCIRCULAR_CROSSINGS.md)を限定受入。
有理チャートの次数8/16以下の多項式を全根分離し、元の平方根符号で偽解を除外、
有限所属・通常接触/カスプ・同一中心を分類する。予算不足は元接触証拠と未完了探索を残す。
新規診断版8、旧保存版1〜7を保持。元構築・Case適用可否・FEM/物理規約は不変。
関連83項目が合格。初回82unit33.507秒=81合格/新テスト入力のdocument_type誤り1件。
入力だけ修正して該当1unit0.007秒PASS、追加の公開予算保持1unit0.227秒PASS。83件の一括再実行ではない。
独立の元三角/双曲線式と投影単調分割102条件89.455秒、追加13条件24.018秒がPASS。
実Chrome初回/実サーバー再起動各16入力70チェック32取得、全保存32ファイルのバイト一致がPASS。
新版3画像を目視、カスプ詳細はCDPで検査。両GUIは終了0で停止済み、実行中の検証ハンドルはない。
記録はout/line-noncircular-crossings-20260914と同independent[-additional]/browser-{initial,restarted}系。
再現コマンド・数学・予算・履歴は上記文書、集約は同20260914/acceptance.json。
先行タスクの自前版7診断4件を公開分類器変更前にfixture化。旧版7専用接触テスト/validatorは保持した_v7を明示呼出する。
FEMを含む既存conic_fillet消費先は合格。全suite/seed/Hosted CIは再実行せず、許容差とbenchmarksは不変。
新外部資料・依存・旧版資産/実行・subagentなし。未解決の承認拒否・質問待ちはない。
次はG03の新フィレット候補構築への接続、または曲線同士の一般交点を限定する。
既存conic_fillet/構築版5/6は従来Krawczyk探索を保持しており、新診断の根からの候補構築はまだ追加していない。
C00.V対象版/必須集合、V02利用者業務、物理ピーク収束等も残る。全計画goalはactive、予算なし。
親33=8受入/17進行/7他未受入/1範囲外。

2026-09-14 JST 直前の継続状態。開始HEADbcdbc97、cleanからG03の次課題を実装した。
前goalターンは一般二進回転/直線長の円オフセット診断を実装/受入/commitしたprogress。
[直線と非円楕円・双曲線オフセットの接触](LINE_NONCIRCULAR_OFFSET_CONTACTS.md)を限定受入。
平行元接線の全接点を根号代数で検査し、正則な全域射影境界から有限0/1点を確定する。
非正則時はTANGENCY_WITNESSESとして通常/カスプ接触・同一中心の統合を保存し、他の交点を排除しない。
新規診断版7、旧保存版1〜6は元規則を保持。元構築・Case適用可否・FEM/物理規約は不変。
関連65unit25.979秒、独立1,944条件0.867秒がPASS。初回7unitもPASS。
実Chrome初回/実サーバー再起動は各16入力59チェック32取得がPASS、保存32ファイル全バイト一致。
新版3画像を目視。両GUIサーバーは終了0で停止済み、実行中の検証ハンドルはない。
記録はout/line-noncircular-offset-contacts-20260914と同independent/browser-{initial,restarted}系。
詳細なパス・数学・再現コマンドは上記文書、集約は同20260914/acceptance.json。
旧版6 fixtureは公開分類器の変更前に自前構築診断4件を保存。旧版の既知接触未確認を記録してから実装した。
新外部資料・依存・旧版資産/実行・subagentなし。全suite/seed/Hosted CIは再実行していない。
関連conic_filletテストの既存FEM尺度検査は合格。許容差とbenchmarksは不変。
次はG03の一般非円交点、元接線が平行でないカスプ、曲線同士、新フィレット候補構築を限定する。
C00.V対象版/必須集合、V02利用者業務、物理ピーク収束等も残る。全計画goalはactive、予算なし。
親33=8受入/17進行/7他未受入/1範囲外。未解決の承認拒否や質問待ちはない。

2026-09-14 JST 直前の継続状態。開始HEAD94b879c、cleanからG03の次課題を実装した。
前goalターンは有理支持の有限交点の実装/受入/commitを完了したprogress。
[一般二進回転/直線長を保持する円オフセット](ALGEBRAIC_CIRCULAR_OFFSETS.md)を限定受入。
根号代数は最大3段階、従属根号も再帰的符号で判定。円・直線の接触/横断/離隔・
同心円/潰れ/平行線と有限所属を追加した。新規診断版6、旧保存版1〜5は元規則を維持。
元構築・Case適用可否・FEM/物理規約は変更しない。関連58unit25.348秒、独立1,944条件9.362秒がPASS。
実Chrome初回/実サーバー再起動各8入力31チェック16取得がPASS。全保存バイト一致、新版3画像目視済み。
両GUIサーバーは終了0で停止済み。実行中の検証ハンドルはない。
記録はout/algebraic-circular-offsets-20260914と同independent/browser-{initial,restarted}系。
詳細なパスと再現コマンドは上記文書。初回51unitの旧期待値9失敗をログに保持して明示更新した。
旧版5 fixtureは公開分類器の変更前の自前構築2件。新外部資料・依存・旧版資産/実行・subagentなし。
全suite/seed/Hosted CIは再実行していない。許容差とbenchmarksは不変。
次はG03の非円楕円/双曲線の一般弧端/重解と新候補構築を限定する。
C00.V対象版/必須集合、V02利用者業務、物理ピーク収束等も残る。全計画goalはactive、予算なし。
親33=8受入/17進行/7他未受入/1範囲外。未解決の承認拒否や質問待ちはない。

2026-09-14 JST 開発再開。ユーザーが既存計画の完走を`/goal`に指定し、予算なしのactive goalを作成した。
作業checkoutは引き続き`/home/sin/code/agent/reserch/superfish-ng`。開始HEADはdbd5327、作業ツリーはcleanだった。
[有理支持の異なる円・直線の有限交点診断](FINITE_CIRCULAR_CROSSINGS.md)を限定受入。
新規normal/construction診断版5、旧構築診断1〜4は元規則を維持。元構築・Case・FEMは変更しない。
関連49unitは24.084秒、独立4,896条件は13.633秒でPASS。実Chromeの初回/実サーバー再起動各6入力・
24チェック12取得がPASS、保存全バイト一致、新版2画像目視済み。両GUIサーバーは終了0で停止済み。
記録はout/finite-circular-crossings-20260914、独立とブラウザーのパス/再現コマンドは上記文書。
初回の旧期待値7失敗とsandbox socket拒否のログを保持。旧版再検証を残して期待値を更新し、
ローカルサーバー/Chromeのsandbox外実行は自動承認され検証完了。未解決の承認要求はない。
今回の検証範囲は関連テストと専用幾何診断。全suite/seed/旧版比較/Hosted CIは再実行していない。
次はG03の無理数の回転ノルムを持つ異なる支持円、または非円楕円/双曲線の一般弧端/重解を限定する。
C00.V対象版/必須集合、V02利用者業務、物理ピーク収束等も残り、全計画は未完。
親33=8受入/17進行/7他未受入/1範囲外を維持する。subagent/新依存/新外部資料の利用なし。

2026-09-14 JST 検証運用の更新。現在の手順は[TESTING.md](TESTING.md)とAGENTS.md。
ユーザー要求により、着手時・各小変更での全件再実行を廃止し、対象テスト＋影響先を選ぶ。
seed数値だけ必要ならvalidate.py --skip-tests、全件は節目・広範な共通変更・影響不明時に一度実行する。
文書更新や同一コードの統合で同じ合格検証を繰り返さない。以下の件数・時間は各時点の履歴であり、新たな必須検証ではない。
棚卸しと手順変更は完了。実行器の対象4件・実seed CLI/報告生成が合格し、seedの全モード辞書は既存受入出力と一致した。
記録はTESTING.md末尾。今回の全unittest/Hosted CIは未実行であり、手順変更の確認のために追加で回す必要はない。

2026-09-14 JST 最新受入状態。以下の旧ハンドル/順次統合指示は本記録で置き換える。

2026-09-13 UTC：[有限オフセット診断の区切り](G03_FINITE_OFFSETS_CHECKPOINT.md)を主ツリーへ統合・限定受入。
同一支持円の全候補周期・任意二進回転と、同じ非円楕円/同枝双曲線の反射自己接点を分類する。新規診断版4と旧保存版1/2/3を別の規則で再検証し、元構築・Case・適用可否を保持する。
独立20496条件、実Chromeの初回/実サーバー再起動で46入力・計292チェック/182取得と保存バイト一致、9画像の目視がPASS。数値907sourceを保持した最終909sourceを主915sourceへ統合。標準1456件（1453合格・任意NGSolve参照2件/HTTP sandbox 1件の計3skip）が718.595秒でPASS。主統合後の専用41unitも6.443秒でPASS。既存seed9モード19量の最大相対差は周波数0、全量8.882e-16。許容差・ベンチマークは不変。
G03全体・対象版C00.V・利用者業務V02・全計画は未完。親33=8受入/17進行/7他未受入/1範囲外を維持する。

ユーザーの「完了後、ここまでを一区切りとしてcommit」と、待ち時間中の並列化要求に対応した区切り。G03の3実装と検証並列化、JSON fixture配布設定を一つの区切りとして記録する。主915source、PHYSICS v28。親HEADは324d3be、最終コミットはgit logを確認。全計画を完走済みとは扱わない。

最終固定候補は/tmp/superfish-parallel-validation-import-path-20260914、909source。数値907sourceからの変更はscripts/run_tests.py、scripts/validate.py、tests/test_parallel_test_runner.pyのみ。集約out/parallel-validation-development-20260914に最終SHA/差分復元コピー、逐次対並列18件の実測、主41unitとintegrate-final.py/finalize-final.pyを保存。両helperは実行済みで再実行禁止。G03の元17変更と独立/ブラウザー証拠はout/g03-finite-offsets-checkpoint-development-20260913。旧helper/途中freeze/失敗benchmarkは保存し、旧順次統合を実行しない。

標準out/validation-parallel-checkpoint-20260914の全299モジュール1456件は16プロセスで完走。test-run/report.jsonが件数/skip/各実行時間の正本で、結合tests.logの最初のRan行を全件数と誤読しない。既定8、--test-workers 1は元の逐次discover。旧逐次標準は最終全合格後に停止済みでPASSと扱わない。全Chrome/GUIサーバーも停止済み。

残件は異なる支持曲線の一般重解/全弧端、新フィレット構築、C00.V、V02利用者業務、物理ピーク収束等。親33=8受入/17進行/7他未受入/1範囲外。Wine実行環境は存在するので同じパス探索/質問を繰り返さない。旧版コード/バイナリ検査、subagent、新依存、hosted CI実行主張なし。

2026-09-14 JST 00:29 並列化要求を含む最新状態。以下の旧統合指示は置き換え済み。

ユーザーが待ち時間中の並列化を依頼。最終候補は/tmp/superfish-parallel-validation-import-path-20260914、909source固定。G03数値907sourceとの差はscripts/run_tests.py、scripts/validate.py、tests/test_parallel_test_runner.pyの3ファイルのみ。主はまだ901source/HEAD324d3beで未統合。最後にG03の3実装・並列化・MANIFEST.inのJSON fixture追加を一つのコミットにする。

実行中：全1456件・299モジュールの16プロセス標準はハンドル71476（2026-09-13 15:23 UTC開始）、out/validation-parallel-checkpoint-20260914、ログout/parallel-validation-development-20260914/standard-parallel.log。15:27UTCに289/299 PASS、失敗なし。最終固定sourceを変更しない。旧逐次1450件はハンドル55955、実PID46395/46412でまだ動作中だが、並列全件合格後に停止し、その停止記録を残す。途中逐次の時間から全suite短縮率を算出しない。

並列ランナーは既定最大8、--test-workersで変更、1なら元python -m unittest discover。全一覧と各workerの一覧/件数を照合し、進捗・時間・skip/エラー/失敗・異常終了を保存。モジュール/クラスfixtureを同じプロセスへ保持し、BLAS等各1スレッド、POSIXの中断で子孫も終了する。6unit初回PASS後、実FEM benchmarkでcwdのsys.path欠落によりscripts.* import失敗を検出。旧909source候補/ログ/3changesはfirst-trialとして保持。別候補でcwdを復元し、cwd補助moduleの回帰を含め6unit0.979秒PASS。

同じB-H保存/再読込18テストの元逐次は123.557秒、修正後3プロセス83.882秒（1.473倍）、全ID/件数/結果一致。benchmark-comparison.json。両測定時に旧逐次標準は動作していた。最終909sourceのsdistもネットワークなしsystem setuptools68.1.2で作り、修正前3fixture欠落/修正後3件元バイトと全909source一致、展開先41unitがPASS。out/parallel-checkpoint-source-distribution-20260914。

主受入手順：全並列標準PASS/全909source/1456=1453+3既知skipを確認→旧逐次を正確なPID/argv/cwd確認で停止、original-serial-termination.json（stopped=true）をparallel devへ→同dev/integrate-final.py（未実行、主915へ20source変更）→主41unit（test_same_conic_offset_intersections/test_general_coincident_circle_arcs/test_coincident_circle_arcs/test_offset_degeneracies/test_construction_diagnostics/test_parallel_test_runner）を同dev/main-unit.log→同dev/finalize-final.py（未実行）→文書/全diff/源SHA/コミットを確認。両helperは実行前に最終レビュー。旧combined integrate.py/finalize.pyおよび先行2候補のhelperは置換済みで実行しない。

独立20496条件/実Chrome292チェック182取得/9画像と907sourceの証拠はout/g03-finite-offsets-checkpoint-development-20260913に保持。最終909sourceの変更が検証用3ファイルだけであることをintegratorが照合する。新しいfinal-frozen-source-sha256.json/final-frozen-changes3と旧17変更から候補を復元できる。freezer/builders/record-browser/check-final-source-distributionは実行済み・再実行禁止。全GUIサーバー停止済み。親33=8/17/7/1、全計画未完。subagent/新依存/旧版再探索なし。

2026-09-13 UTC 15:03 この区切りの最新状態。以下の旧候補ハンドル・順次統合指示は廃止し、この記録を優先する。

ユーザーは「完了後、ここまでを一区切りとしてcommit」と指示。3つのG03拡張を最終907sourceでまとめて検証・主913sourceへ統合し、一つのローカルコミットにする。それまで新課題を開始しない。主HEADは324d3be、主901source、まだ追加ソース未統合。
最終候補/tmp/superfish-same-conic-offset-self-intersections-20260913は固定907source。集約out/g03-finite-offsets-checkpoint-development-20260913に17変更の復元用コピー、全SHA、helperと独立/ブラウザー証拠を保存済み。freezer/builders/record-browser.pyは実行済みで再実行禁止。
標準はハンドル55955、14:46:59 UTC開始、out/validation-g03-finite-offsets-checkpoint-20260913、集約standard.log。1450件（期待1447合格/3既知skip）を実行中。15時UTCに実プロセス46395/46412の生存・CPU進行を確認。空ログはcapture buffering。候補を変更/重複実行しない。
同じ907sourceで独立2688+4608+7056+6144=20496条件と専用35unitがPASS。実Chrome初回/実サーバー再起動各46入力・146チェック・91取得がPASS。全182保存バイトと46入力/実旧保存32ファイルのSHA一致、9画像目視済み。両サーバー50577/54803は正常停止済み。
集約のintegrate.pyとfinalize.pyは作成済み・未実行。標準PASS後、integrate.py→主test_same_conic_offset_intersections/test_general_coincident_circle_arcs/test_coincident_circle_arcs/test_offset_degeneracies/test_construction_diagnosticsの35unitを集約main-unit.logへ→finalize.py→全差分確認/コミット。元seed9モード19量のf/RF差は実数を確認し、許容差/benchmarksは不変。
一時ディレクトリ消失で先行候補の未完走標準を復元したが、最終ソースで全件検証する方針へ統合したため、先行再開2走は意図的に停止した。各devにtemporary-restoration/interrupted-standard-run/resumed-standard-supersededを保持。旧個別integrator/finalizerは置換済みで実行しない。
配布設定MANIFEST.inに*.json fixtureを追加。out/g03-finite-offsets-source-distribution-20260913のsystem setuptools 68.1.2によるネットワークなしsdist確認は、修正前3fixture欠落・修正後3件の元バイトと全907source一致・展開先35unitがPASS。集約check-source-distribution.pyは実行済みで再実行禁止。integrator/finalizerの受入条件にも加えた。
全計画は未完、親33=8受入/17進行/7他未受入/1範囲外。目標ツールの現状はpaused（達成済みではない）。同じWine探索/質問、旧版コード/バイナリ検査、新依存、subagentなし。既存Wine実行環境がある事実を保持する。

2026-09-13 UTC 14:18:34 最新継続状態。主HEADは808ca27・901source・PHYSICS v28。以下の古い実行中/未実装記録より優先する。

先行2候補は固定したまま標準検証中：相対四分の一回転/tmp/superfish-coincident-circle-arcs-20260913は899source、実ハンドル52289（13:07:11 UTC開始、期待1436=1433+3skip）。任意回転/tmp/superfish-general-coincident-circle-arcs-20260913は903source、実ハンドル57815（13:46:38開始、期待1443=1440+3skip）。両方14:16:41 UTCに生存確認。各out/validation-...-candidate-20260913とdev/standard.log。空ログはbufferingで、固定sourceを変更/重複起動しない。独立2688と4608/7056、各候補の実ブラウザー初回/実再起動・目視は既にPASS。両integrator/finalizerは未実行。親1436PASS→主905/21unit/finalizer/commit→後続1443PASS→主909/28unit/finalizer/commitの順。具体的なhelper絶対パスは直下の14時前の記録に保持する。mainの追加source統合はまだない。

G03の次の限定課題を開始：docs/SAME_CONIC_OFFSET_SELF_INTERSECTIONS_PLAN.md。開発候補/tmp/superfish-same-conic-offset-self-intersections-20260913、dev=out/same-conic-offset-self-intersections-development-20260913。先行一般円903sourceから複製し、現在906source/10変更（新module/test/版3fixtureの3追加、offset診断/構築診断/GUI JS/既存test4変更）。開発中で未固定・主未統合・未受入。circle候補を変更していない。新規独立driver未作成、追加後は907source/主統合913を見込むが実数を確認すること。

数学範囲は同じ中心・半軸・二進回転（双曲線は同じ枝）と向き補正距離が同じ二有限弧。非円楕円の等距離法線二接点θ=α±βの消去は(a²−b²)sinα cosα sin²β=0、異なる接点はどちらかの主軸の反射対。双曲線同枝では(a²+b²)sinhα coshα sinh²β=0でu,-uの反射対。具体的なq=sin²θ/sinh²uと距離符号・端等号、中心座標、二進回転ノルムL²の有理式は計画書を参照。周期を含む同じパラメータ対と有限自己接点を別に列挙し、全所属/除外/共有端点との重複が証明できた場合だけ全域分類する。別支持曲線・反対の双曲線枝は未確認を維持。FEM/構築/Case適用可否は不変。

変更前の解析7例はinitial-invariant.jsonで未完を確認。直接の新実装は全7例の有限中心数1/2/1/0/1/2/0が一致。最初の6例目で共有端点照合が未対応coshを既存APIへ要求したため、sinhの区間とsqrt(1+sinh²)へ修正した。first-implementation-invariant-failure.json、修正前moduleとdirect-invariants-after-hyperbola-endpoint-fix.jsonを保持。新規一般診断/構築診断は版4、旧版3は_classify_offset_degeneracies_v3へ保存し、旧1/2も元規則を維持。FINITE_CENTERSは有限中心数を表示。既存証拠もmergeして保持。

版3の自前構築診断7件を変更前に生成したtests/fixtures/offset_diagnosis_v3_same_conics.json（67087bytes）はdev/previous-version-three.jsonと同一。来歴/SHAはprevious-version-three-provenance.json。初回fixture helperは誤ったcontrols.turnをstrict parserが拒否、未出力。正しいturn_directionと宣言pair_startの別helperで生成した。両helper/失敗JSONを保存し再実行しない。

専用35unit=新7+先行28は5.789秒でPASS、ResourceWarningなし（focused-indentation-fixed-unit.log、実ハンドル37193終了0）。新7は解析/交換/逆向き/2回転/3尺度/双曲線両枝、楕円両軸順、1 ULPで共有端点に自己交差が追加される境界、中心で重複する共有端点、零距離/真2pi周期/部分区間、Decimal平方根、低予算/不一致支持/strict、旧1/2/3保存再検証/CLIバイト/GUI応答/新版4を含む。parent-first-unit.logの4失敗は新規版と全域完全性への旧期待値で、明示更新した。first-focused-unit.logは版番号更新行の字下げ誤りでimport失敗、修正後35PASS。既存数値許容差/物理は変更なし。

次は独立driverを作成する。実装のq公式を期待値に再利用せず、元normal変位の各対称軸成分を高精度で零点探索し、有限パラメータ所属と全中心数を照合する案。楕円はt=sinθ∈[0,1]で単調な速度から各法線成分を二分、角度は別のNewton三角参照。双曲線はt=sinh u≥0の速度と元normal成分を二分し、u=log(t+sqrt(1+t²))が参照。両楕円軸順/双曲線両枝、距離符号と閾値、元二進回転/尺度/部分区間/交換/逆向き、共有端点重複を含める。想定数6144等は未実行で証拠ではない。独立合格後にfinal unit→固定→標準1450（期待1447+3）/実Chrome初回・実再起動→目視→親受入後の統合へ進む。self候補のfreezer/integrator/finalizer/browser driverは未作成。現時点で標準を起動しない。

開発10変更はdev/development-changes/、3helperはdev/helpers/、SHAと状態はdev/checkpoint.jsonへ保存。一般円の統合helper等8本はgeneral dev/helpers/に別途保持。唯一の実行中ハンドルは52289/57815。全GUIサーバーとChromeは停止済み。全計画goal ACTIVE・予算なし、親33=8受入/17進行/7他未受入/1範囲外、C00.VとV02は未確認。新規外部資料/旧版資産/依存/subagent/hosted CIなし。Wine実行環境は存在するので同じ探索/質問を繰り返さない。承認拒否や質問待ちなし。

2026-09-13 UTC 13:58:01 最新継続状態。以下の古い実行中/未受入記録より優先する。

主は04adb61・901source・PHYSICS v28。O02専用原要件照合と静的Study worker/GUIは受入済み。全計画goal ACTIVE・予算なし、親33=8受入/17進行/7他未受入/1範囲外、C00.V対象版/必須集合とV02利用者評価は未確認。主sourceの追加統合はまだない。

G03の先行候補 /tmp/superfish-coincident-circle-arcs-20260913 は899source固定。独立2688条件、21unit、実Chrome初回/実再起動各27チェック/15取得、7旧新診断/既存構築計8入力と目視5枚PASS。主未統合・未受入。標準1436件は実ハンドル52289、13:07:11 UTC開始、out/validation-coincident-circle-arcs-candidate-20260913、dev/standard.logで継続中。空ログはcapture buffering。終了PASS後、未実行 /tmp/integrate-coincident-circle-arcs-20260913.py → 主21unit（test_coincident_circle_arcs test_offset_degeneracies test_construction_diagnostics）をdev/main-unit.log → 未実行 /tmp/finalize-coincident-circle-arcs-docs-20260913.py → 差分確認/コミット。期待主905source。parent finalizerの次課題文だけは一般回転の検証中候補へ更新済みで未実行。

後続は docs/GENERAL_COINCIDENT_CIRCLE_ARCS_PLAN.md とGENERAL_COINCIDENT_CIRCLE_ARCS.md。/tmp/superfish-general-coincident-circle-arcs-20260913 は903source固定済み、devはout/general-coincident-circle-arcs-development-20260913。先行899から4新規/4修正の8変更。元二進回転の非有理ノルムを含む支持半径一致を有理代数の符号と平方恒等式で証明し、一般相対角をatan加法/交代級数とπ区間で囲む。全候補周期を分類。元構築/Case/FEMは不変。新規診断版3、旧構築診断版1/2は従来規則を保持する。版2 fixtureは変更前の自前構築診断8件で、旧SUPERFISH資産ではない。

一般候補は開始時8例の未完と旧版2保存8件を保持。最初の全28unitで低予算時に既知共有端点を失う回帰を検出し、full-first-unit.logとoffset-degeneracies-before-witness-fix.pyを保存。証拠保持修正後28件2.830秒、固定直前のfinal-focused-unit.logも28PASS。独立 out/general-coincident-circle-arcs-independent-first-trial-20260913/report.json は有限弧4608/支持半径7056条件、4.690秒・全903source不変でPASS。120桁Decimal平方根/AGM pi/三角Newton相対角と固定17周期が参照。新規外部資料/依存/旧版資産なし。

一般候補標準1443件は実ハンドル57815、13:46:38 UTC開始、out/validation-general-coincident-circle-arcs-candidate-20260913、dev/standard.logで実行中。親/後続ともcwd各候補、主.venv絶対Python、OPENBLAS_NUM_THREADS=1 PYTHONPATH=src。期待skipは任意NGSolve2/HTTP sandbox1。固定候補を変更せず、重複実行しない。

一般候補の実Chromeは out/general-coincident-circle-arcs-browser-initial-20260913 と同browser-restarted-20260913、各75チェック/24入力/47取得でPASS。版2旧8/版3新8、先行版1/2と構築8件。元全JSON/元バイト、実サーバー再起動後の同じ初回取得ファイル、改変拒否/復帰/編集無効化/適用可否。dev/browser-completion.json は150チェック/94取得・元24入力不変・source903一致。初回PID3570612/session63572と再起動PID3612616/session12254は両方正常停止。Chrome81100/13435も終了0、旧28unit84202/最終6956/独立36525は終了0。目視7画像（旧版の証拠・新版の全域分類・既存構築適用を分離）はvisual-review.json。ブラウザー参照初回builder48554は既存status名をBUILTと誤記して失敗、FAILED JSONと部分入力/元helperを保持。CASE_VALIDATEDへ直した別helper87415はPASS、固定候補は不変。実使用参照はout/general-coincident-circle-arcs-browser-reference-status-fixed-20260913/cases.json。driverは同dev/verify-browser.mjsでsource固定対象外、SHAを両報告に保持。

一般候補の受入手順は親主受入後、標準1443/独立/実ブラウザー/目視の合格を条件に未実行 /tmp/integrate-general-coincident-circle-arcs-20260913.py → 主28unit（test_general_coincident_circle_arcs test_coincident_circle_arcs test_offset_degeneracies test_construction_diagnostics）をdev/main-unit.log → 未実行 /tmp/finalize-general-coincident-circle-arcs-docs-20260913.py → 差分確認/ローカルコミット。期待主909source。freezer、修正後browser builder、browser/visual recorderは実行済みで再実行禁止。失敗builderも再実行せず保存する。

次のG03一般楕円/双曲線オフセットの自己交差は読取調査中で未実装。円候補の検証や受入範囲を広げて扱わない。旧版Wineの同じ走査/パス質問を繰り返さず、既存Wine実行ファイルがある事実を保持。subagentなし・hosted CI実行主張なし・承認拒否/質問待ちなし。以下の古いハンドルは再利用しない。

2026-09-13 UTC 13:18 最新継続状態。以下の古い実行中/未受入記録より優先する。

主ツリーは901source・PHYSICS v28。静的Study worker/CLIはef3fa68で限定受入、標準1423件（1420合格/3skip、4254.005秒）と主6unit448.593秒PASS。GUIは30a2c5bで限定受入、標準1429件（1426合格/3skip、4868.421秒）と主6unit638.480秒PASS。両者の統合/finalizerは実行済みで再実行禁止。旧seed9モード19量はf差0・最大相対差8.882e-16。GUI integratorのloop変数衝突で20/17と誤記された集計は元1429/1426へ訂正し、元記録とstandard-count-correction.jsonをGUI devに保持した。FEM/結果/sourceは不変。

O02の専用範囲の原要件照合を完了。out/o02-acceptance-audit-final-20260913/report.jsonはPASS、主901sourceと関係182ファイル不変。過去33工程66標準/seed、46ブラウザー586チェック、保存復元23報告、追加RF5仕様/4ブラウザー60チェック、静的Studyの全6ブラウザー342チェック等へ対応する。過去検証の再実行ではない。対象版/必須集合C00.VとV02利用者業務評価は未確認、親33=8受入/17進行/7他未受入/1範囲外、全計画goal ACTIVE・予算なし。O02 audit/docs finalizerも実行済み・再実行禁止。

次はG03の同一支持円上の有限オフセット弧。docs/COINCIDENT_CIRCLE_ARCS_PLAN.mdとCOINCIDENT_CIRCLE_ARCS.md。候補/tmp/superfish-coincident-circle-arcs-20260913は899sourceで固定済み、主未統合・未受入。coincident_circle_arcsの有理数π/全候補周期、既存offset診断への接続、診断出力版2と旧構築診断版1の従来規則再検証。元構築/FEM/Case適用可否は不変。相対回転は厳密な四分の一回転だけ。一般回転・楕円/双曲線の重解/全弧端・退化候補構築等は残る。

開発証拠はout/coincident-circle-arcs-development-20260913。解析4例の初期未完、旧保存3例が単純拡張で拒否される回帰、独立参照の同位相端点相殺とブラウザーUNVERIFIED期待文の初回失敗を保持。修正後21unit（新7/既存14）1.125秒PASS。独立out/coincident-circle-arcs-independent-exact-endpoints-trial-20260913/report.jsonは120桁Decimal AGM/固定17周期で2688条件PASS、0.898秒、全899source一致。新規外部資料/依存/旧版資産の参照なし。fixtures/offset_diagnosis_v1.jsonは自前実装の旧保存物でSUPERFISH資産ではない。

実Chromeはout/coincident-circle-arcs-browser-initial-status-fixed-20260913と同browser-restarted-20260913が各27チェック/8件/15取得PASS、旧3/新3/既存構築済み2の全JSONと元バイト、実再起動後の同じ保存ファイル、改変拒否/復帰/編集無効化と適用可否を確認。browser-completion.jsonは54チェック/30取得、PID2531560と2682665は両方正常停止済み。目視5画像はvisual-review.json。旧入力の最初のoverview画像は診断文が画面下にあり、旧版の判定文は自動UI検査で確認したと区別。browser driverは同dev/verify-browser.mjs、固定候補外に保持しSHAを両報告へ記録。初回失敗11224、修正後73986、再起動19429とサーバー65049/96209は終了済み。再利用しない。

現在の実行中は標準1件だけ：実ハンドル52289、13:07:11 UTC開始、cwd候補、主.venv絶対Python、OPENBLAS_NUM_THREADS=1 PYTHONPATH=src。scripts/validate.py --out /main/out/validation-coincident-circle-arcs-candidate-20260913、ログdev/standard.log。期待1436件=1433合格/3skip（任意NGSolve2/HTTP sandbox1）。空ログはcapture buffering。固定候補を変更せず、重複実行しない。

標準終了PASS後の未実行手順：/tmp/integrate-coincident-circle-arcs-20260913.py（8変更を主905sourceへ統合）→主OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest test_coincident_circle_arcs test_offset_degeneracies test_construction_diagnostics -vをdev/main-unit.logへ（21件）→/tmp/finalize-coincident-circle-arcs-docs-20260913.py→差分/文書確認→ローカルコミット。両helperは未実行。freezerは実行済みで再実行禁止。両helperはstd1436/source899・独立・ブラウザー・目視・main901親とseed9モード19量、主21unitを要求する。unit_countはbrowser件数と別変数にした。

最新checkpointは同dev/checkpoint.json。frozen-changes/に変更8ファイル、helpers/に7helperを退避済み。clone.jsonとfrozen-candidate-source-sha256.jsonで親/候補を復元できる。旧静的Study標準77530、主GUI3944、旧主worker83492と全旧ブラウザー/サーバーは終了済み。git/ローカルHTTP/Chromeの必要なescalationは承認済み、拒否や質問待ちなし。既存Wine実行環境はあるので全体欠落と誤記せず、同じ探索/パス質問を繰り返さない。subagentなし・新規依存なし・hosted CI実行の主張なし。

2026-09-13：[O02原要件の照合](O02_ACCEPTANCE.md)を専用範囲で完了。
外部mesh/曲線高次・TM/TE・平面/Hφ・静的11形式と磁気後処理のProject/Study/GUI、同一入力/結果、保存復元、失敗/中止/描画/N/Aを受入証拠と主901sourceへ対応付けた。静的Study worker/CLIとGUIの標準1423/1429件・主各6unit、GUI全6ブラウザー342チェックもPASS。過去の記録は読取監査であり再実行とはしない。
対象版/必須集合C00.VとV02の利用者業務評価は未確認。親O02と全計画は未完、親33=8受入/17進行/7他未受入/1範囲外。次はG03の同じ支持円上の有限弧の分類。
O02最終監査と文書finalizerは実行済み、再実行禁止。out/o02-acceptance-audit-final-20260913/report.json。主901source、PHYSICS v28。静的Studyの両統合/finalizerも実行済み。以下の古い未完ハンドルを再利用しない。G03は/tmp/superfish-coincident-circle-arcs-20260913の開発候補で、主未統合・未受入。開始時4例、保存版1の回帰3例を保持。版2/旧版再検証の修正後21unitはPASS、独立Decimal比較の初回は参照側の端点精度判定で停止しており未完。標準/実ブラウザーは未実行。

2026-09-13：[静的StudyのGUI入力・実行・各条件表示](STATIC_FIELD_STUDY_GUI.md)を主ツリーへ統合・限定受入。
全11形式/次数・両パラメータの全Studyを元FEMで非同期再検証し、選択点の元場・全量/材料/実失敗履歴と元バイト取得を接続。実行完了と全点成否・入力順を区別する。元nativeを独立参照とする78 Study/192条件（成功171/実失敗21）と38組合せ、初回/再起動各1266取得が一致。元1941/新3537ファイル不変。実Chrome全78 Study/192点・各1266取得と中止/強制終了/別条件改変拒否・旧RF、既存静的42件/磁気20件の初回/実再起動も合格。
標準1429件（1426合格・3skip）、候補11unitと主6unitがPASS。固定895sourceを主901sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。O02原要件照合、対象版と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
static-field-study-gui統合/finalizer実行済み・再実行禁止。主901source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[静的Studyの実worker・各条件保存・CLI](STATIC_FIELD_STUDY_JOBS.md)を主ツリーへ統合・限定受入。
全11形式の全条件を既存専用FEMで独立に実行し、元Projectと成功/実失敗nativeを保存・再検証する。全条件実行完了と全点成功を分け、元初期値/条件・材料と失敗履歴を保持。独立78 Study/192条件（成功171/実非線形失敗21）のAPI/実worker/CLI各78と再起動78、156 CLIが一致。元1941/新6345ファイル不変。
標準1423件（1420合格・3skip）、候補10 focused unit・既存23件と主6unitがPASS。固定889sourceを主895sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。静的Study GUI、対象版、O02と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
static-field-study-jobs統合/finalizer実行済み・再実行禁止。主895source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13 UTC 11:47:28 並行検証の最新状態。以下の古いチェックポイントより、この冒頭を優先する。

2026-09-13 UTC 12:17:04 最新継続状態。以下の古い記録より、この冒頭を優先する。

主sourceは892、PHYSICS v28、受入済み静的Study入力e43aab7・標準1417件（1414合格/3skip、3778.058秒）。静的Project GUI335efd4も受入済み。現在はStudy worker/GUIの固定候補を検証中で主統合なし。元Case/メッシュ/FEM/数値許容差は変えていない。

worker候補 /tmp/superfish-static-field-study-jobs-20260913 は固定889source。独立86019は終了0、3238.294秒で78 Study/192条件（成功171/実失敗21）、API/実worker/CLI各78・再起動78・156 CLI、元1941/所有6345ファイル不変でPASS。out/static-field-study-jobs-independent-process-wait-trial-20260913/report.jsonとdev/independent-completion.json。旧15秒process.waitで24件後に失敗した初回は保持し、全体900秒期限内で終了を待つ検証器修正だけを最終候補に含める。root CLI stdout/stderrは即時照合済みだが所有6345には含めない。
worker標準1423件は実ハンドル20092、out/validation-static-field-study-jobs-candidate-20260913、ログdev/standard.logで継続中。空ログはbufferingで失敗とは限らない。固定候補を編集しない。終了PASS後 /tmp/integrate-static-field-study-jobs-20260913.py →主test_static_field_study_jobs 6件をdev/main-unit.log→ /tmp/finalize-static-field-study-jobs-docs-20260913.py →ローカルコミット。両helper未実行、期待主895source。

GUI候補 /tmp/superfish-static-field-study-gui-20260913 は固定895source。独立99583は終了0、1896.439秒で全11形式/38形式・次数・パラメータ、78 Study/192条件（成功171/実失敗21）、実worker78、初回/再生成access各78全Study再検証・各192点表示・各1266取得がPASS。元1941/所有3537不変。out/static-field-study-gui-independent-trial-20260913/report.json。元nativeから別に作った実Chrome期待値との全Case/量/元場一致はdev/browser-reference-audit.jsonでPASS、helperは実行済み。標準1429件は実ハンドル77530、out/validation-static-field-study-gui-candidate-20260913、ログdev/standard.logで継続中。

初回実Chromeは全3経路が終了0/PASS: Study85430=94チェック/78例192点/1266元取得+78編集Study、静的42499=56チェック/42例/234元取得+42編集Project、磁気89529=28チェック/20例/140取得。out/static-field-study-gui-browser-20260913、同static-browser、同magnetic-browser。全配信sourceが固定候補と一致・外部要求0。dev/all-initial-browser-completion.json。初回6993/PID1853591はCtrlC正常終了0、initial-process-stopped.jsonも確認済み。
実サーバーを同じout/static-field-study-gui-browser-server-20260913/workspaceへ別PID2014893で再起動済み。実ハンドル53891、launch-url-restarted.txt（0600）。再起動Study Chromeは実ハンドル56778、out/static-field-study-gui-browser-restarted-20260913、ログdev/browser-restarted.logで実行中。初回reportを--restoreへ渡した全78例192点。終わるまで固定候補を変えない。
再起動Study終了PASS後、同じサーバーで順に node scripts/verify_static_field_gui.mjs（cases=out/static-field-gui-independent-color-trial-20260913/cases.json、--restore初回static-browser/report.json、--out out/static-field-study-gui-static-browser-restarted-20260913）、次にverify_magnetic_report_gui.mjs（cases=out/magnetic-report-gui-independent-navigation-trial-20260913/cases.json、--restore初回magnetic-browser/report.json、--out out/static-field-study-gui-magnetic-browser-restarted-20260913）を実行する。共通--url-fileは上記再起動ファイル、--workspaceは同workspace。ログは各dev/static-browser-restarted.log、magnetic-browser-restarted.log。両方まだ未開始。同じworkspaceのRF最新行を使う検証のため並行実行しない。全3復元PASS後に53891を正常停止し、restarted-process-stopped.jsonを確認する。
目視は初回case0、24、66point1、76point2の計4画像をdev/visual-review-in-progress.jsonへ記録済み。元の細かいメッシュ・全失敗/混合の表示、SI/N/Aと場非表示を確認。再起動後の画像を見てdev/visual-review.json status=reviewed・全895sourceを作るまでは最終目視未完。試作4Studyだけで全件を受け入れていない。
GUI標準/全6ブラウザー/独立/参照監査/目視/両サーバー停止と親worker受入後、/tmp/integrate-static-field-study-gui-20260913.py →主test_gui_static_field_studies 6件をdev/main-unit.log→ /tmp/finalize-static-field-study-gui-docs-20260913.py →ローカルコミット。両helper未実行、期待主901source。新11unit751.181秒は固定前にPASS、最終標準も必要。

O02はdocs/O02_ACCEPTANCE.mdに原要件/経路の照合草稿を作成。既存33実装工程の標準/seed66報告、28工程のブラウザー46報告586チェック、保存/復元23報告を読取照合し、報告のPASSと受入時sourceに不一致なし。out/o02-acceptance-audit-in-progress-20260913にSHA/全対応を保存。この33工程は親33項目の受入数ではない。今回の監査で過去テストを再実行していない。静的Study主受入と最終要件対応が残り、O02/全計画は未完。

最新チェックポイント/12 helper退避はout/static-study-restarted-checkpoint-20260913-121704。clone/builders/freezers/export/参照監査/完了記録/本checkpointは実行済みで再実行禁止。主/候補sourceは完全一致を確認済み。goal ACTIVE・全計画完走・予算なし、今回も進展あり。親33=8受入/17進行/7他未受入/1範囲外、対象C00.V未確認。旧版再走査/再質問・旧ソース/バイナリ検査・subagent・新規依存・hosted CIなし。既存Wine実行ファイルはある。標準3skipは任意NGSolve2/HTTP環境1。主.venv絶対Python・cwd候補・OPENBLAS_NUM_THREADS=1 PYTHONPATH=src（unitはsrc:tests）。gitとローカルHTTP/Chromeの必要なescalationは承認済み、拒否/保留なし。


主HEADはe864134（e43aab7で静的Study入力、335efd4で静的Project GUIを受入済み）、主892source、PHYSICS v28、最新標準1417=1414合格/3skip、主入力7unit219.970秒PASS。元seed9モード19量はf差0・最大相対差8.882e-16。主ソースの追加統合はこの段階ではまだない。

worker候補 /tmp/superfish-static-field-study-jobs-20260913 を889sourceで固定済み。freezerは実行済み・再実行禁止。修正後の独立比較と標準回帰を同じ固定ソースで並行実行する方式へ変更した。固定を受入とはせず、integratorは独立全78 Study/192条件/156 CLIと標準1423件の全合格/source一致を引き続き必須とする。標準は11:20:49 UTC前に開始、ハンドル20092、out/validation-static-field-study-jobs-candidate-20260913、ログdev/standard.log。独立は既存ハンドル86019、out/static-field-study-jobs-independent-process-wait-trial-20260913、ログdev/independent-process-wait.log。最新DONE 77 mixed-off_axis_bh points 3 failures 1。元の15秒待機失敗を保持し、900秒全体期限の修正で大きい元メッシュを通過。固定ソースは変更しない。worker integrator/finalizerは未実行で、標準/独立合格後に主895へ統合、主test_static_field_study_jobs 6件をdev/main-unit.log、finalizer、ローカルコミット。

GUI候補 /tmp/superfish-static-field-study-gui-20260913 も895sourceで固定済み、freezer実行済み・再実行禁止。親固定889sourceとの差17ファイル。GUI独立の参照方式だけを元native直接方式へ変更し、同じ66入力Study/165点、9実失敗Study/18点、3混合Study/9点を保った。新旧物理・メッシュ・許容差は不変。期待する全結果/場を、GUIやStudy実行を使わず元nativeから組み立て、全38形式/次数/パラメータ組合せと各1266取得を検証する。参照bundle original-native-references はJob/完了manifestを捏造せず、元nativeとreference-provenanceを持つ検証用データ。
GUI独立はハンドル99583、11:23:10 UTC前に開始、out/static-field-study-gui-independent-trial-20260913、ログdev/independent-first.log。コマンドは候補cwdで scripts/validate_static_field_study_gui.py --input-reference /main/out/static-field-study-input-independent-final-trial-20260913 --reference-root /main/out --out /main/out/static-field-study-gui-independent-trial-20260913。ここで/mainは実workspace絶対パス。最新DONE 68 failure-2-planar-bh 2 point views。標準1429件は11:28:22 UTC前に開始、ハンドル77530、out/validation-static-field-study-gui-candidate-20260913、ログdev/standard.log。どちらも固定895sourceを変更/再実行しない。

元nativeを直接評価したブラウザー用参照78 Study/192点（実失敗21）は150.026秒で生成済み。out/static-field-study-gui-browser-reference-20260913/reference-report.json はREFERENCE_READYで、GUI受入PASSではない。cases.jsonと各viewsを実ブラウザーへ渡す。独立GUI完了後 /tmp/audit-static-study-browser-references-20260913.py を一度実行し、独立GUI全78件/192点と同一の順序付きCase/全結果/元場であることを比較してdev/browser-reference-audit.jsonを作る（未実行）。GUI integratorはこの監査も必須にした。
実Chrome全件の初回はハンドル85430、11:33:06 UTC前に開始。出力out/static-field-study-gui-browser-20260913、ログdev/browser-first.log、最新DONE 24 12-excitation_scale。同じ候補内 scripts/verify_static_field_study_gui.mjs を --url-file /main/out/static-field-study-gui-browser-server-20260913/launch-url.txt --cases /main/out/static-field-study-gui-browser-reference-20260913/cases.json --workspace /main/out/static-field-study-gui-browser-server-20260913/workspace --out /main/out/static-field-study-gui-browser-20260913 で実行中。
公式検証サーバーはハンドル6993（初回PIDはinitial-process.json）、同browser-serverディレクトリのserver.py、候補cwd/PYTHONPATH=srcで実行中。まだ停止しない。初回Study Chrome完了後に既存 scripts/verify_static_field_gui.mjs の42件と scripts/verify_magnetic_report_gui.mjs の20件を同じserver/workspaceへ順に実行する（RF履歴の新規Job順序が競合するため各Chrome driverを同じworkspaceで並列実行しない）。静的参照は out/static-field-gui-independent-color-trial-20260913/cases.json、磁気参照は out/magnetic-report-gui-independent-navigation-trial-20260913/cases.json（20件PASS・旧磁気browserと同じ全nameと元source/report存在を確認済み）。
既存画面の出力名は out/static-field-study-gui-static-browser-20260913 と out/static-field-study-gui-magnetic-browser-20260913 を使う。初回3種類合格後にサーバー6993へCtrl-Cして実終了を確認する。finallyがinitial-process-stopped.jsonを保存する。次に同ディレクトリserver-restarted.pyを新しい実プロセスで開始し、launch-url-restarted.txtを使って、同じ3 driverを初回report.jsonの--restore付きで順に実行する。出力は各名前に-browser-restarted相当、具体的には static-field-study-gui-browser-restarted-20260913、static-field-study-gui-static-browser-restarted-20260913、static-field-study-gui-magnetic-browser-restarted-20260913。再起動サーバーも終了後restarted-process-stopped.jsonを確認する。両PID/実終了・全件画像の目視をGUI integratorが要求する。
GUI全件画像は初回case-0-point-0.pngのみ目視済み（負の励起-2、Dzの青色/単位、3条件/成否とN/A）。dev/visual-review-in-progress.jsonを保持。大きいメッシュ/実失敗・再起動画像の目視後に、status=reviewedと全frozen source hashを持つdev/visual-review.jsonを別に作る。旧4 Studyの試作Chrome初回20/再起動14項目、各68取得と目視2枚は既に完了・全試作サーバー/Chrome終了済みだが、これで全78件を受入としない。

GUIのfreezerは実行済み、integratorとfinalizerは作成済み・未実行。標準/独立/全ブラウザー/目視/参照監査・親worker受入後、/tmp/integrate-static-field-study-gui-20260913.py →主test_gui_static_field_studies 6件をdev/main-unit.log→ /tmp/finalize-static-field-study-gui-docs-20260913.py →ローカルコミット（期待主901source）。全helperの退避はout/static-study-parallel-checkpoint-20260913-114728。既存のclone/page builders/asset準備/参考資料export/前チェックポイントは実行済みで再実行禁止。固定候補のtar/source SHAは各devに保存済み。
全計画goalはACTIVE・予算なし。前turnも今turnも進展あり、blocked/completeではない。親33=8受入/17進行/7他未受入/1範囲外。C00.V対象版は未確認。GUI受入後はO02_ACCEPTANCE_PLAN.mdの元要件照合。旧版再走査/再質問・旧ソース/バイナリ検査・subagent・新規依存・hosted CIなし。ソース/原出力を上書きせず、実行完了は必ず実ハンドルと出力で確認する。

2026-09-13 UTC 11:18:16 最新継続状態。以下の古い記録より、この冒頭を優先する。

主受入HEADはe43aab7、892source、PHYSICS v28、標準1417件（1414合格・3skip）3778.058秒。静的GUI335efd4と静的Study入力を主ツリーへ統合・限定受入済み。Study入力の主7unit、f差0/旧seed9モード19量の最大相対差8.882e-16、元の固定886sourceとの一致はseed_regression.jsonを参照。GUIとStudy入力のintegrator/finalizerは実行済み、再実行禁止。

静的Study worker候補 /tmp/superfish-static-field-study-jobs-20260913 は889source、まだ固定/標準/主統合なし。新6unit+cap3+変更した旧CLI1の10 focusedと既存23件が合格。初回10呼出のcontext manager誤用/旧CLI名誤指定による2エラー・ResourceWarningは保持し、contextlib.closingの修正1件21.661秒と既存24件19.252秒で確認済み。独立初回は24 Study完了後、大きい元1024三角形Caseで保存後FEM再検証が15秒を超え、検証側のprocess.waitで失敗。元900秒の全体期限内で終了まで待つ修正だけを加え、別出力で再実行中。元メッシュ/FEM/許容差を変えていない。
worker独立の実ハンドルは86019、ログout/static-field-study-jobs-development-20260913/independent-process-wait.log、出力out/static-field-study-jobs-independent-process-wait-trial-20260913。最新完了行はDONE 24 12-excitation_scale points 3 failures 0。78 Study/192条件（成功171/実非線形失敗21）、API/実worker/CLI各78・再起動78・156 CLIの全Case/native照合。完了までsourceを変更しない。大きいCaseは多重の元FEM照合に時間がかかるため、空ログを失敗と推定せず実ハンドルを確認する。
worker独立PASS後に /tmp/freeze-static-field-study-jobs-20260913.py を一度実行し、固定889sourceの標準1423件を out/validation-static-field-study-jobs-candidate-20260913、ログdev/standard.logで実行する。標準PASS後 /tmp/integrate-static-field-study-jobs-20260913.py →主test_static_field_study_jobs 6件をdev/main-unit.log→ /tmp/finalize-static-field-study-jobs-docs-20260913.py →明示ファイルをローカルコミット。期待主895source。これら3helperは未実行。freezer/integrator/finalizerは修正後process-wait-trialを参照する。

静的Study GUI候補 /tmp/superfish-static-field-study-gui-20260913 は編集可能895source、workerとの差17ファイル。全Study非同期元FEM再検証、選択点の元セル中心場、全Study/点Project/native取得、全点成否と順序、別条件改変拒否、静的Study専用画面/入力/実workerとRF履歴誘導を実装。6 GUI+3cap+2旧CLI/capabilityの11unitは751.181秒PASS、ResourceWarningなし。unit終了後にJS/独立validator/Chrome driverを追加し、JS構文とPython compileはPASS。親workerのprocess.wait修正もGUI候補とbase-source-sha256へ同期済み。
GUIの実Chrome試作は4 Study/11点（成功8/実失敗3）、初回20/実サーバー再起動後14チェックPASS、各68元ファイルと初回編集Study4取得。strict JSON負のゼロ、全場/単位/量・実失敗、中止/強制終了・別条件改変拒否/正常復帰と旧RF実FEM/nativeを確認。out/static-field-study-gui-prototype-browser-20260913 と同prototype-browser-restartedのreport.json。2画像目視はdev/prototype-visual-review.json。両サーバー/Chromeは終了済み。試作だけで全78例の受入とはしない。
GUI候補には scripts/validate_static_field_study_gui.py と scripts/verify_static_field_study_gui.mjs がある。worker独立PASSを参照して全78 Study/192点、全38形式/次数/パラメータ組合せ・各1266取得と初回/再起動を確認する。独立GUIは未開始、out/static-field-study-gui-independent-trial-20260913 を予定。全Chrome/既存静的42・磁気20の初回/実再起動・目視と固定/標準1429件/主統合は未実施。最新895sourceはdev/after-coverage-source-sha256.json。試作後の変更は独立validatorに38組合せの実測coverage assertionを足したのみ、実装sourceは試作初回/再起動のhashと一致。GUI freezer/finalizerは未作成、integratorのみ /tmp/integrate-static-field-study-gui-20260913.py を未実行で準備（期待17変更、主901source）。
GUIのclone、最終asset helper、page/browser buildersは実行済みで再実行禁止。worker/GUIの編集中sourceとhelper退避はout/static-study-checkpoint-20260913-111816。これは受入/freezeではない。全件受入後はdocs/O02_ACCEPTANCE_PLAN.mdの元要件照合へ進む。対象C00.V未確認、親/全計画は未完。goal ACTIVE・予算なし、実装進展ありでblocked/completeにしない。

作業rootはこのworkspace。旧AGENTS rootへ移動しない。候補には主の絶対.venv/bin/python、cwd候補、OPENBLAS_NUM_THREADS=1 PYTHONPATH=src（unitはsrc:tests）を使う。標準3skipは任意NGSolve参照2/HTTP環境1。Wine実行ファイルは既存、SUPERFISH prefixは未特定だがWine全体がないとは言わない。旧版コード/バイナリ検査、Wine再走査/再質問、subagent、新規依存、hosted CIなし。git add/commitのみ必要なescalation、ローカルHTTP/Chromeの検証も承認済みで拒否なし。上書きせず全失敗ログを保持。

2026-09-13：[静的Studyの入力・尺度変換](STATIC_FIELD_STUDY_INPUT.md)を主ツリーへ統合・限定受入。
全11形式の基底Projectとuniform_scale/excitation_scale、全派生Caseの厳密検査、初期値/条件/材料来歴と入力順、非上書き保存・normalize-static-studyを接続する。独立33参照Caseの66 Study/165条件・元FEM330回の対比較と66 CLI、励起比例/二次積分72点と幾何尺度4点が合格。全165条件が求解成功で、実非線形失敗はこの比較では未検証。元297/新1914ファイルが不変。
標準1417件（1414合格・3skip）、候補10unitと主7unitがPASS。固定886sourceを主892sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。静的Studyの実行/worker/GUI、対象版、O02と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
static-field-study-input統合/finalizer実行済み・再実行禁止。主892source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[静的ProjectのGUI入力・実求解・元場表示](STATIC_FIELD_GUI.md)を主ツリーへ統合・限定受入。
既存11形式の厳密Case/Project編集・m/mm表示と実worker、成功/保存済みB-H失敗、非同期の元FEM再検証を接続する。元セル中心場とSI全量/材料/履歴を保持し、零中心の明示配色と元バイト保存、中止/強制終了/改変拒否を検証。独立42例、初回/再起動各234取得が一致し、元360/新318ファイル不変。実Chrome初回/実サーバー再起動でも42例・各234取得と既存RF操作を確認し、既存磁気報告20件・各140取得も初回/再起動で合格。
標準1410件（1407合格・3skip）、候補11unitと主6unitがPASS。固定883sourceを主889sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。静的Study、対象版、O02と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
static-field-gui統合/finalizer実行済み・再実行禁止。主889source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13 UTC 10:11:14 最新継続状態。以下の古い詳細より、この冒頭を優先する。

主実装の受入コミットは2c75de5、主883source、PHYSICS v28（後続の文書コミットはgit logで確認）。静的Project worker/API/CLIを限定受入しコミット済み。標準1404件（1401合格・3skip）3452.844秒、主6unit 90.673秒。独立42成功/実失敗例・API/実worker/CLI・再起動、87 CLI、元192/新954ファイル不変。旧seed9モード19量はf差0、最大相対差8.882e-16。static-field-jobs integrator/finalizerは実行済み、再実行しない。

静的GUI候補 /tmp/superfish-static-field-gui-20260913 は固定883source・主未統合。独立color-trial 42例189.259秒、33成功/9実失敗、42実worker・初回/再起動各42 replay/234取得、元360/新318ファイル不変。実Chromeは初回42例56チェック、実サーバー再起動42例50チェック、各234元ファイル取得（初回編集Project 42取得は別）。既存磁気報告も初回20件28チェック/再起動20件26チェック、各140取得とRF実求解/native一致。静的中止・強制終了・改変拒否/正常結果へ復帰・厳密JSON負のゼロ・全場/単位、目視済み。全Chrome/サーバーは終了済み。初回2つの失敗は保持し、最終記録に混同しない。
GUI標準1410件はハンドル55111、out/validation-static-field-gui-candidate-20260913、ログout/static-field-gui-development-20260913/standard.logで進行中。固定sourceを変更/再実行しない。/tmp/integrate-static-field-gui-20260913.py と /tmp/finalize-static-field-gui-docs-20260913.py は未実行。標準PASS後に前者、主test_gui_static_fields 6件を同dev/main-unit.log、後者、明示ファイルをローカルコミット。期待主889source。GUI freezerは実行済み。

静的Study入力候補 /tmp/superfish-static-field-study-input-20260913 は固定886source・主未統合。StaticFieldStudyの厳密uniform_scale/excitation_scale、初期値/条件保持、非上書き保存/normalize-static-studyとcapability、7新unit・独立scriptを実装。元基底の重複検査を削減し各条件は独立deepcopyと専用parser検査を保持（1024要素3条件8.001→6.476秒、全Case同一）。最終10unit 231.638秒PASS。初回の未実装/import失敗、9unitの幾何尺度1失敗と修正ログを保持。理論上零の横成分の丸め差を自身で割る検証を、共通の解析ベクトル場尺度へ修正し許容値/FEM不変。解析24組の最大相対差5.968e-14/解析との差7.398e-14、穴/非零源1unitと修正幾何1unitもPASS。極端1e308尺度の拒否で既存幾何parserのRuntimeWarningが出るが、ResourceWarningではなく入力は拒否される。
初回独立は33 DONE/165対native後、物理名electrostaticの誤選択による幾何0件で最終coverage assertion失敗。out/static-field-study-input-independent-trial-20260913/attempt-summary.jsonに記録し未受入。正しいlinear_electrostaticと幾何4件必須へ修正した最終独立は 537.463秒PASS、33 Case/66 Study/165条件/330直接FEM対比較・66 CLI、励起不変量72/幾何4条件。元297/新1914ファイル不変、実非線形失敗0点（零なら実失敗を試したとは主張しない）。最終報告はout/static-field-study-input-independent-final-trial-20260913/report.json。
Study入力標準1417件はハンドル91690、out/validation-static-field-study-input-candidate-20260913、ログout/static-field-study-input-development-20260913/standard.logで進行中。/tmp/integrate-static-field-study-input-20260913.py と /tmp/finalize-static-field-study-input-docs-20260913.py は未実行。先にGUIを主889へ受入し、この標準PASS後に統合、主test_static_field_study 7件を同dev/main-unit.log、文書finalizer、コミット。期待主892source。Study入力のclone/apply-geometry-test/freezerは実行済み・再実行禁止。

次はdocs/STATIC_FIELD_STUDY_JOBS_PLAN.mdの実worker/各条件保存・CLI、その後静的Study GUI。Study全体はdocs/STATIC_FIELD_STUDY_PLAN.md、入力限定範囲を全体完了としない。worker候補/実装はまだない。全計画goalはactive・予算なし。親33=8受入/17進行/7他未受入/1範囲外で未完。C00.V対象版未確認。進展があるのでblocked/completeへ変更しない。

作業rootは/home/sin/code/agent/reserch/superfish-ng（AGENTSの/home/sin/code/superfishは旧マシンの記述）。候補は主の絶対.venv/bin/pythonとcwd候補、OPENBLAS_NUM_THREADS=1 PYTHONPATH=src（unitはsrc:tests）で実行。旧版再探索・Wine実行やパス再質問をしていない。Wine実行ファイルは既存、SUPERFISH prefixは未特定で、Wine自体が無いとは言わない。新規依存・旧版コード/バイナリ検査・subagentなし。git add/commitのみ必要時require_escalated、拒否なし。生出力はignored out/、既存出力を上書きしない。保存スナップショット out/static-continuation-checkpoint-20260913-101114.json。

2026-09-13：[静的Projectの実worker・保存・CLI](STATIC_FIELD_JOBS.md)を主ツリーへ統合・限定受入。
既存11種類の専用FEMを同じProjectから求解し、成功native 5ファイルと実非線形失敗3ファイルを保存・再現する。JobManagerの別プロセス・再起動・中止とCLI 0/1/2、全SI Case/結果/失敗履歴を保持する。独立42例（成功33/実失敗9）のAPI/実worker/CLI各42件と再起動42件、87 CLI、元192/新954所有ファイルが一致・不変。
標準1404件（1401合格・3skip）、追加6unit・capability 3unitと主6unitがPASS。固定877sourceを主883sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。静的GUI/Study、O02と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
static-field-jobs統合/finalizer実行済み・再実行禁止。主883source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[静的Projectの入力・保存・CLI](STATIC_FIELD_PROJECT.md)を主ツリーへ統合・限定受入。
既存11種類の専用Caseを保持し、m/mm表示選択をSI値・材料・境界・B-H初期値/反復条件へ作用させない。厳密JSON往復と非上書きのnormalize-static-projectを追加した。独立33元Caseの66 Projectを実FEMで再求解し、264 Project/330 nativeの全バイトが一致、元165ファイル不変。
標準1398件（1395合格・3skip）、追加6unit・capability 3unitと主6unitがPASS。固定874sourceを主880sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。静的worker/GUI/Study、O02と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
static-field-project統合/finalizer実行済み・再実行禁止。主880source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13 17:49 JST（08:49 UTC）— この節を以下の過去記録より優先。

計画完走のgoalはACTIVE。全計画は未完、親33=8受入/17進行/7他未受入/1範囲外。現主ソース877、PHYSICS v28。今回89772d6で軸方向磁気力native、d9044e7で磁気報告GUI、8accb49でS05原要件照合をコミット済み。S05は13受入工程を原要件へ照合したが、C00.V対象版/必須範囲の確認待ちで親は未受入。旧ベンチマーク9モード19量はf差0/最大相対差8.882e-16、許容差不変。

磁気報告GUIは固定871sourceを主877sourceへ統合済み。標準1392件（1389合格・3skip）3326.087秒と主12unit 86.631秒がPASS。独立20実worker/20初回/20再起動と140ダウンロード、Chrome初回28/再起動26項目・各20報告/140ダウンロードを確認。GUI統合/finalizer、軸力native統合/finalizer、S05照合finalizerは実行済み、再実行禁止。ローカルGUIサーバー/Chromeは稼働していない。

進行中の固定候補は順に統合する。標準PASSと前段主ツリーの受入が条件。元候補には編集を加えず、既存出力も上書きしない。

- 静的Project: /tmp/superfish-static-field-project-20260913、固定874source→主880source予定。標準1398件の実ハンドル95869（08:14 UTC開始）。独立out/static-field-project-independent-mesh-trial-20260913/report.jsonは33元Case/66 Project、66実再求解・134 CLI、元165/新594ファイルが125.550秒でPASS。unit 9件38.536秒PASS。初回独立の静電partition.meshキー取り違えは検証側だけ修正し失敗記録を保持。統合待ちhelper /tmp/integrate-static-field-project-20260913.py、主test_static_field_project 6件をout/static-field-project-development-20260913/main-unit.logへ実行後、/tmp/finalize-static-field-project-docs-20260913.py。どちらも未実行。
- 静的worker: /tmp/superfish-static-field-jobs-20260913、固定877source→主883source予定。標準1404件の実ハンドル86870（08:36 UTC開始）。独立out/static-field-jobs-independent-corrected-trial-20260913/report.jsonは33成功/9実非線形失敗のAPI/実worker/CLI各42件、再起動42件、87 CLI、元192/新954ファイルが335.915秒でPASS。初回unitは8合格/1検証用一時保存先名の重複エラー、正確に修正した1件1.656秒PASS、計9 unique。既存RF/磁気Job 13件37.643秒PASS。初回独立42件335.192秒も保持し、修正後の全sourceへ結び付けるため別出力へ最終比較を実施した。統合待ちhelper /tmp/integrate-static-field-jobs-20260913.py、主test_static_field_jobs 6件をout/static-field-jobs-development-20260913/main-unit.logへ実行後、/tmp/finalize-static-field-jobs-docs-20260913.py。どちらも未実行。

編集可能な次工程は/tmp/superfish-static-field-gui-20260913。固定worker877sourceから作成し、現881source（4新規+10既存変更）。gui_static_fields.py、static.html/js、test_gui_static_fields.pyを追加し、gui/model/capability/4既存画面ナビ/RF履歴と既存Project/workerのGUI capability期待値2件を更新した。入力はJSON文字列をサーバーの厳密parserへ渡し、m/mmは表示だけ。実worker、非同期の元FEM再検証、毎回SHA、セル中心の片側元場の一定色三角形表示、全Case/量/材料・実失敗履歴と元バイト取得を接続。失敗にはplot=null。RF周波数/二つのR/Q/モード番号はN/A。

静的GUIのunit 11件（新6+cap3+既存capability期待値が変わる入力/worker各1）は82.959秒PASS、Node構文検査もPASS。試作viewは受入済み42元Job（33成功/9実失敗）を確認し、out/static-field-gui-development-20260913/prototype-view.logに保持。これは独立GUI受入/実ブラウザー検証ではない。まだ独立validatorとChrome driverは未作成、ブラウザー・標準回帰・freeze・主統合も未実施。次は全11形式/次数、元場/全量/単位・Project往復、実worker/再起動、各6成功/4失敗ファイルの元バイトダウンロードと改変拒否を独立に照合し、実Chrome初回/再起動と表示目視を実施する。既存磁気報告/RF操作も確認する。新script 2件を追加すれば固定883source/主889source/標準1410件の見込みだが実数を照合する。失敗時は候補を固定せず原因を修正し、実結果を保持する。

最新の完全fingerprint/実ハンドル/準備済みhelper一覧はout/static-integration-checkpoint-20260913-084804.json。/tmp/checkpoint-static-integration-20260913.pyは現主877・静的GUI881を前提に新しい時刻名で監査を保存できる。Project/workerのfreezerと/tmp/prepare-static-field-gui-20260913.pyは実行済み、再実行禁止。静的GUIの独立検証・browser・受入helperはまだ存在しない。

候補内では絶対パスの主.venv/bin/pythonを使い、cwdを候補、PYTHONPATH=src（unitはsrc:tests）、OPENBLAS_NUM_THREADS=1とする。editable installの主ソースを誤って読み込まない。標準ログは完了時まで空でも正常。標準の3skipは任意NGSolve参照2/HTTP環境1で固定。主source fingerprintを統合helperが検証する。不変egg-info 6件を削除しない。全源/数値出力の同一性を確認後に文書・次計画を選択してローカルコミットする。新規依存・サブエージェント・hosted CIの実施主張なし。

Wine実行ファイルの存在は確認済み。SUPERFISH prefixは未特定だが環境全体が存在しないとは扱わない。今回Wine/旧版実行やパスの再走査・再質問はしていない。ユーザー所有の旧版コード/バイナリは読まない。実作業rootはこのworkspaceであり、古いAGENTSの/home/sin/code/superfishへ移動しない。

2026-09-13：[S05原要件の受入照合](S05_ACCEPTANCE.md)を完了。
S02に基づく平面多極・力/トルク・実変位FEM仮想仕事、正半径の線形軸力、元native/CLIと磁気報告GUIの専用範囲を照合した。全周量/単位長量、未実施/零/実求解失敗、元場/材料/履歴を区別する。標準1392件と主12unit、実Chrome初回/再起動の受入証拠がある。
対象版と未対応な軸力範囲の必須性はC00.V未確認。親S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
S05原要件照合finalizer実行済み・再実行禁止。主877sourceはGUI受入時と不変。次はO02静的Project。

2026-09-13：[検証済み磁気後処理量のGUI受渡し](S05_GUI_HANDOFF.md)を主ツリーへ統合・限定受入。
専用磁気報告の所有コピーと実FEM replay worker、非同期の初回/再起動検証、毎回のSHA照合、元Case/材料/規約と全量表示・元バイト保存を接続する。平面多極/二つのトルクと全周軸力のSI、仮想仕事の未実施/完了/実求解失敗を区別し、詳細JSONの負のゼロも保持する。独立20実workerと20初回/20再起動replay、140ダウンロード、元120ファイルと所有180ファイル不変。Chromeでも20報告の初回/再起動表示と各140ダウンロード、改変拒否、既存RFの実FEM/全量保存を確認。
標準1392件（1389合格・3skip）、追加Job 6unit・GUI 6unit・capability 3unitと主12unitがPASS。固定871sourceを主877sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
原要件/対象版確認と未対応な軸接続/B-H/反跳の軸対称力、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
magnetic-report-gui統合/finalizer実行済み・再実行禁止。主877source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸を含まない磁気力報告の保存・CLI](OFF_AXIS_MAGNETIC_FORCE_NATIVE.md)を主ツリーへ統合・限定受入。
正半径の線形P1/P2の元native 5ファイルSHAへ拘束した軸方向力Fz[N]と、明示nullまたは実変位FEMのポテンシャル[J]/全Caseを保存・再計算する。求積/+4診断、基準ψ、対象と重みを保持し、平面N/mや断面回転へ読み替えない。独立20例（仮想仕事10/応力のみ10）、62CLI、60報告の全JSON/バイトが一致。元native 100/新報告60/要求20と参照50ファイル不変。
標準1380件（1377合格・3skip）、追加保存6unit・capability 3unitと主6unitがPASS。固定863sourceを主869sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
GUI受渡し・軸接続/B-H/反跳の軸対称力、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
off-axis-magnetic-force-native統合/finalizer実行済み・再実行禁止。主869source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13 07:52 UTC 進行チェックポイント：主0a1bead、866source、PHYSICS v28。材料仮想仕事28d5c90、材料力保存/CLI 7b10e7e、軸非接続の軸方向力0a1beadを検証・コミット済み。各integrator/finalizerは実行済みで再実行禁止。

未統合の固定候補は2件。`/tmp/superfish-off-axis-magnetic-force-native-20260913` は863source、独立20例/62CLIと追加9unit合格、標準1380件を実ハンドル96351で実行中。`/tmp/superfish-magnetic-report-gui-20260913` は871source、独立20実worker/20初回/20再起動replay、最終Chrome初回28項目/再起動26項目・各20報告と140ダウンロードが合格、標準1392件を実ハンドル46500で実行中。固定候補を編集しない。GUIの最終独立出力は `out/magnetic-report-gui-independent-navigation-trial-20260913`、ブラウザーは `out/magnetic-report-gui-browser-navigation-20260913` と `out/magnetic-report-gui-browser-restarted-20260913`。全失敗ログと修正判断をdevelopmentへ保持し、古い途中出力を最終証拠へ置換していない。二つのローカル検証サーバーは正常に停止済み。

それぞれの標準PASS後、直前の主統合を確認して `/tmp/integrate-off-axis-magnetic-force-native-20260913.py` →主6unit→ `/tmp/finalize-off-axis-magnetic-force-native-docs-20260913.py`、次に `/tmp/integrate-magnetic-report-gui-20260913.py` →主12unit（test_magnetic_report_jobs、test_gui_magnetic_reports）→ `/tmp/finalize-magnetic-report-gui-docs-20260913.py` の順。これら4helperは未実行。主unitログは各 `out/<slug>-development-20260913/main-unit.log`。文書finalizerの独立参照先は実際のtrial/navigation-trialへ補正済み。統合後は差分を確認し、その工程と次計画だけをローカルコミットする。

機械可読状態は `out/magnetic-report-checkpoint-20260913-075140.json`。次のS05原要件照合は `docs/S05_ACCEPTANCE_PLAN.md` と `docs/S05_ACCEPTANCE.md` の未受入草稿、読取監査は `out/s05-acceptance-audit-in-progress-20260913/accepted-stages.json`。親33=8受入/17進行/7他未受入/1範囲外、S05/全計画は未完、目標はACTIVE。新規依存・subagent・Wine/旧版実行なし。Wine本体は存在し、SUPERFISH用prefixは未特定。パス質問や同じ探索を繰り返さず、進行中の検証と残要件を進める。

2026-09-13：[軸を含まない軸対称磁場の軸方向力](OFF_AXIS_MAGNETIC_FORCE.md)を主ツリーへ統合・限定受入。
元r>0の線形P1/P2 FEMから、真空P1重みと全周2πrのMaxwell応力でFz[N]を求める。同じ節点z移動の別Caseを実FEM再求解し、全周停留ポテンシャル[J]の差分と照合する。独立50例（解析42/線形磁性体8）、30条件120変位FEM、メッシュ/重み/求積/基準ψの別系列がPASS。130ファイル不変。低次P2求積の拒否を実細分で解消し、元5e-12条件と力/仕事許容差を維持した。
標準1374件（1371合格・3skip）、追加6unitと主6unitがPASS。固定860sourceを主866sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸方向力保存/CLI・GUI受渡し・軸接続とB-H/反跳の軸対称力、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
off-axis-magnetic-force統合/finalizer実行済み・再実行禁止。主866source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[B-H・反跳材料の力・仮想仕事報告保存・CLI](PLANAR_MAGNETIC_FORCE_MATERIAL_NATIVE.md)を主ツリーへ統合・限定受入。
材料の成功nativeを元FEMで再検証し、応力とnull/完了/実非線形失敗の仮想仕事をversion 2で保存・再計算する。元Case/材料方向/ポテンシャル/全履歴を保持し、CLIは完了0・保存された実求解失敗1・不正2を返す。独立20例（完了12/実変位先失敗8）、70CLI、60報告と元100nativeファイルがPASS・不変。旧線形24報告と72ファイルも不変。
標準1368件（1365合格・3skip）、追加6unit・旧保存6unit・capability 3unit、主6unitがPASS。固定856sourceを主862sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
GUI受渡し・軸対称の力/トルク、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
planar-magnetic-force-material-native統合/finalizer実行済み・再実行禁止。主862source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[B-H・反跳材料の平面仮想仕事](PLANAR_MAGNETIC_VIRTUAL_WORK_MATERIALS.md)を主ツリーへ統合・限定受入。
専用material_planar_magnetic_virtual_workでB-H P1/反跳P1/P2の実変位FEMを再求解し、真の構成ポテンシャルから力/トルクを差分する。反跳主軸/残留Bは対象と共回転し、非線形失敗の全履歴を保持して失敗した対の微分をnullにする。独立50条件と4原点変更（完了54系列で648変位FEM、失敗例の途中成功分は別記）、12実非線形失敗がPASS。材料62応力、旧56線形応力・40仮想仕事・24native報告が一致し元461ファイル不変。
標準1362件（1359合格・3skip）、追加6unitと主6unitがPASS。固定854sourceを主860sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
材料保存/CLI・GUI受渡し・軸対称の力/トルク、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
planar-magnetic-virtual-work-materials統合/finalizer実行済み・再実行禁止。主860source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[B-H・反跳材料解からの平面Maxwell応力](PLANAR_MAGNETIC_FORCE_MATERIALS.md)を主ツリーへ統合・限定受入。
B-H P1/反跳P1/P2の元実FEMを再検証し、宣言された真空の重み遷移だけでMaxwell応力を積分する。全B-H表・反跳主値/残留Bで真空を厳密判定し、非線形/異方性/残留磁化の対象を元解に保持する。独立62例、8メッシュ系列と6重み、解析Lorentz力/磁気モーメントトルク/材料対称性がPASS。旧56応力・40仮想仕事・24native報告が一致し元275ファイル不変。
標準1356件（1353合格・3skip）、追加6unitと主6unitがPASS。固定851sourceを主857sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
材料仮想仕事と保存/CLI・GUI受渡し・軸対称の力/トルク、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
planar-magnetic-force-materials統合/finalizer実行済み・再実行禁止。主857source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[平面磁場の力・トルク報告保存・CLI](PLANAR_MAGNETIC_FORCE_NATIVE.md)を主ツリーへ統合・限定受入。
線形P1/P2の元native 5ファイルSHAに固定した力/二つのトルクと、明示nullまたは実変位FEM仮想仕事の完全JSONを保存・再計算する。API/CLIは元Case/場と規約、差分/求積診断を保持する。独立8例（仮想仕事4/応力のみ4）、26CLI、24報告と元native 40ファイルがPASS・不変。API/CLIのJSON/バイトが一致し、改変/上書き/リンク/中断を拒否。
標準1350件（1347合格・3skip）、追加6unitとcapability 3unit、主6unitがPASS。固定848sourceを主854sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
GUI受渡し・B-H/反跳/軸対称の力/トルク、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
planar-magnetic-force-native統合/finalizer実行済み・再実行禁止。主854source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

継続中の候補（主ツリーへは未統合）：B-H/反跳の平面Maxwell応力は固定851source・独立62例PASS、標準1356件をout/validation-planar-magnetic-force-materials-candidate-20260913へ実行中。材料仮想仕事は固定854source・独立50成功条件+4原点変更/12実失敗PASS、標準1362件をout/validation-planar-magnetic-virtual-work-materials-candidate-20260913へ実行中。元主ソースは854件で不変。候補は/tmp/superfish-<各slug>-20260913。両段階のintegrator/finalizerは/tmpに準備済みだが未実行で、各標準PASSと直前主のfocused PASSを待って順に実行する。固定候補を編集しない。最新のout/magnetic-force-work-checkpoint-*.jsonも確認する。

材料仮想仕事の新入口は別専用material_planar_magnetic_virtual_work。既存の線形用APIの型契約とversion 1、材料応力version 2は不変。後続は材料力報告native/CLI、軸対称の軸力、GUI量受渡し。OFF_AXIS_MAGNETIC_FORCE_PLAN.mdとS05_GUI_HANDOFF_PLAN.mdは未受入の設計草案。軸方向力の先行試作out/off-axis-magnetic-force-design-probe-20260913は製品API受入に数えない。

2026-09-13：[平面磁場のMaxwell応力と仮想仕事](PLANAR_MAGNETIC_FORCE.md)を主ツリーへ統合・限定受入。
元P1/P2のBと真空P1重みから力[N/m]、重み付きトルクと節点回転の応力トルク[N m/m]を別々に積分する。同じ節点移動・固定境界/電流の実FEM停留ポテンシャル差分を独立に照合する。独立56例（解析32/細分16/線形材料8）、8細分系列、40条件480変位FEMと3重みがPASS。211ファイル不変。P1の二つの回転場の違いを修正で消さず明示した。
標準1344件（1341合格・3skip）、追加6unitと主6unitがPASS。固定845sourceを主851sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
保存/CLI・GUI受渡し・B-H/反跳/軸対称の力/トルク、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
planar-magnetic-force統合/finalizer実行済み・再実行禁止。主851source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[B-H/反跳モデルの多極報告保存・CLI](PLANAR_MAGNETIC_MULTIPOLE_MATERIAL_NATIVE.md)を主ツリーへ統合・限定受入。
成功したB-H/反跳nativeを厳密manifestで選び、元材料/係数/反復履歴と円板条件・全4系列を再検証する。材料報告は版2、従来線形報告は版1、request版1と2コマンドを保持する。独立24例、72報告/98 CLI、新216出力/48参照と旧192ファイルが不変。従来72報告と24 CLI再検証も一致。
標準1338件（1335合格・3skip）、追加6unitと主6unitがPASS。固定841sourceを主847sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
GUI受渡し・力/トルク、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
planar-magnetic-multipole-material-native統合/finalizer実行済み・再実行禁止。主847source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[反跳/B-Hモデルの線形無源領域での多極抽出](PLANAR_MAGNETIC_MULTIPOLE_MATERIALS.md)を主ツリーへ統合・限定受入。
B-H P1/反跳P1/P2を元FEMで再求解し、円板全体の厳密な線形・等方・非残留・Jz=0を確認する。円板外の非線形/異方性/永久磁石は元の解に保持する。旧線形版1を保持し、新しい物理は抽出版2とする。独立72例（厳密48/細分24）と8系列、旧版1の72抽出/72保存報告が一致。旧336ファイルと新144ファイルが不変。
標準1332件（1329合格・3skip）、追加5unitと主16unitがPASS。固定839sourceを主845sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
材料報告の保存/CLI・GUI受渡し・力/トルク、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
planar-magnetic-multipole-materials統合/finalizer実行済み・再実行禁止。主845source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[多極抽出結果の保存・元native照合・CLI](PLANAR_MAGNETIC_MULTIPOLE_NATIVE.md)を主ツリーへ統合・限定受入。
元5ファイルのSHA256、厳密request、FEM再求解による元場・全4系列/係数/診断を報告へ保存し、明示出典と再計算で照合する。上書き/出典差/改変/途中変更を拒否する。独立24例、72報告/74 CLI、全216出力と48参照ファイルが不変。API/CLIの全JSONとバイトが一致。
標準1327件（1324合格・3skip）、追加6unitと主6unitがPASS。固定836sourceを主842sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
GUI受渡し・対象材料の拡張・力/トルク、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
planar-magnetic-multipole-native統合/finalizer実行済み・再実行禁止。主842source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[元の平面FEM磁場からの多極抽出](PLANAR_MAGNETIC_MULTIPOLE_EXTRACTION.md)を主ツリーへ統合・限定受入。
線形スカラーP1/P2の元Caseを実FEMで再求解して係数を照合し、円板全体の電流ゼロ/一様mu_r/領域内部を確認する。Rと.75RのN/2N、元片側B・全4系列と角度/半径/負次数/打切り診断を保持する。独立72例（厳密48/細分24）、P1の8細分系列と別の角度系列がPASS。元場と係数の誤差を分離し、144入力/結果ファイルを保持した。
標準1321件（1318合格・3skip）、追加5unitと主5unitがPASS。固定833sourceを主839sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
保存/CLI・GUI受渡し・対象材料の拡張・力/トルク、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
planar-magnetic-multipole-extraction統合/finalizer実行済み・再実行禁止。主839source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[平面磁場の有限多極表現と座標変換](PLANAR_MAGNETIC_MULTIPOLES.md)を主ツリーへ統合・限定受入。
原点[m]・半径[m]・局所軸角[rad]とnormal/skew[T]を明示した最大32次の有限多項式を評価/座標変換する。これはFEM求解/無源領域の証明ではない。独立84条件のDecimal場/168 Fourier係数/逆変換/合成・div/curlがPASS。有限SIの単位四極場で先に失敗した複素除算を修正した。
標準1316件（1313合格・3skip）、追加5unitと主5unitがPASS。固定829sourceを主835sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
元FEM抽出・保存/CLI・GUI受渡し・対象材料・力/トルク、S05と全計画は未完。親33=8受入/17進行/7他未受入/1範囲外。
planar-magnetic-multipoles統合/finalizer実行済み・再実行禁止。主835source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[S04原要件の受入照合](S04_ACCEPTANCE.md)を完了。
平面・軸接続・軸非接続P1のB-H入力/来歴、反復/失敗保存、元場/積分、線形極限/合成飽和と独立1次元BVPの専用API範囲を検証済み。C00.Vの対象版/材料モデルは未確認で、親S04と全計画は未完。親33=8受入/16進行/8他未受入/1範囲外。
S04照合finalizer実行済み・再実行禁止。主832sourceのまま。次はS05の有限多極表現。以下よりこの冒頭を優先。

2026-09-13：[軸非接続P1非線形磁場の保存・失敗再現・CLI](OFF_AXIS_BH_NATIVE.md)を主ツリーへ統合・限定受入。
元相対/絶対psiと基準・B-H表/来歴・g/接線・求積差/高次数残差と全反復履歴を同じ非線形FEMで再検証する。成功5ファイルと版2失敗3ファイル、元6場の片側probeを保持する。独立成功24例/失敗8例、64保存と99 CLI、288 native/98参照ファイル不変、API/CLIのファイルとprobe全JSONが一致。
標準1311件（1308合格・3skip）、追加6unitと主6unitがPASS。固定826sourceを主832sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
対象版モデルと原要件の受入照合、S04と全計画は未完。親33=8受入/16進行/8他未受入/1範囲外。
軸非接続BH native統合/finalizer実行済み・再実行禁止。主832source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸非接続P1の境界付き非線形磁静場](OFF_AXIS_BH_SOLVE.md)を主ツリーへ統合・限定受入。
正半径psi=r*Aphi、固定psi/Htと基準、実接線Newtonと版2の明示相対psi失敗履歴、元6場と全J U/U*・A周回/反力/Wb磁束を分離する。q/q+4差と高次数の自由残差も保持する。独立96条件（成功88/期待失敗8）、16細分系列と独立1次元BVP 8比較がPASS。旧平面/軸接続128 nativeの576ファイルと履歴も不変。
標準1305件（1302合格・3skip）、追加6unitと主18unitがPASS。固定823sourceを主829sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸非接続の保存/CLI・対象版モデル、S04と全計画は未完。親33=8受入/16進行/8他未受入/1範囲外。
軸非接続BH solve統合/finalizer実行済み・再実行禁止。主829source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸非接続P1の非線形B-H弱形式](OFF_AXIS_BH_FORMS.md)を主ツリーへ統合・限定受入。
正半径psi=r*Aphiの元H/接線からg/Kと電流荷重を組み立て、全JのU/U*、元B·Hと相対psi·g、定数psi核を検査する。独立96例384形式/192変分、96零場と12対数積分・線形極限・尺度/基準変更がPASS。表折点の求積差を別に記録した。
標準1299件（1296合格・3skip）、追加5unitと主5unitがPASS。固定819sourceを主825sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸非接続境界付き反復/失敗保存・対象版モデル、S04と全計画は未完。親33=8受入/16進行/8他未受入/1範囲外。
軸非接続BH forms統合/finalizer実行済み・再実行禁止。主825source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸接続P1非線形磁場の保存・失敗再現・CLI](AXIS_BH_NATIVE.md)を主ツリーへ統合・限定受入。
元a/全軸DOF・B-H表/来歴・g/接線・求積差/高次数残差と全反復履歴を同じ非線形FEMで再検証する。成功5ファイルと版2失敗3ファイル、元6場の片側probeを保持する。独立成功24例/失敗8例、64保存と99 CLI、288 native/98参照ファイル不変、API/CLIのファイルとprobe全JSONが一致。
標準1294件（1291合格・3skip）、追加6unitと主6unitがPASS。固定814sourceを主820sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸非接続非線形・対象版モデル、S04と全計画は未完。親33=8受入/16進行/8他未受入/1範囲外。
軸BH native統合/finalizer実行済み・再実行禁止。主820source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸接続P1の境界付き非線形磁静場](AXIS_BH_SOLVE.md)を主ツリーへ統合・限定受入。
正則a=Aphi/r、固定a/Ht/軸境界、実接線Newtonと版2失敗履歴、元6場と全J U/U*・A周回/A m²反力/Wb磁束を分離する。q/q+4差と高次数の自由残差も保持する。独立96条件（成功88/期待失敗8）、16細分系列と独立1次元BVP 8比較がPASS。版2変更前後の88物理記録は完全一致し、旧平面64 nativeも不変。
標準1288件（1285合格・3skip）、追加6unitと主18unitがPASS。固定811sourceを主817sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸接続の保存/CLI・軸非接続非線形・対象版モデル、S04と全計画は未完。親33=8受入/16進行/8他未受入/1範囲外。
軸BH solve統合/finalizer実行済み・再実行禁止。主817source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸接続P1の非線形B-H弱形式](AXIS_BH_FORMS.md)を主ツリーへ統合・限定受入。
正則a=Aphi/rの元H/接線からg/Kと電流荷重を組み立て、全JのU/U*、元B·Hとa·g、一定a試験を検査する。独立96例384形式/192変分、非零一定a・線形極限・尺度/移動則がPASS。表折点の求積差を別に記録した。
標準1282件（1279合格・3skip）、追加5unitと主5unitがPASS。固定807sourceを主813sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸対称境界付き反復/失敗保存・対象版モデル、S04と全計画は未完。親33=8受入/16進行/8他未受入/1範囲外。
軸BH forms統合/finalizer実行済み・再実行禁止。主813source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[平面P1非線形磁場の保存・失敗再現・CLI](PLANAR_BH_NATIVE.md)を主ツリーへ統合・限定受入。
B-H表/来歴・元場/接線・内部g/電流/境界荷重と全反復履歴を同じ非線形FEMで再検証する。成功5ファイルと失敗3ファイルを分離し、CLIは成功0/非線形失敗1/入力・保存エラー2。独立成功24例/失敗8例、64保存と99 CLI、288 native/98参照ファイル不変、API/CLIのファイルとprobe全JSONが一致。
標準1277件（1274合格・3skip）、追加6unitと主6unitがPASS。固定802sourceを主808sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸対称非線形・対象版モデル、S04と全計画は未完。親33=8受入/16進行/8他未受入/1範囲外。
平面BH native統合/finalizer実行済み・再実行禁止。主808source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[平面P1の境界付き非線形磁静場](PLANAR_BH_SOLVE.md)を主ツリーへ統合・限定受入。
固定Az/Ht・全Jzと実接線Newton、採用/棄却/失敗履歴、元Az/B/HとU/U*、元H周回/反力・B磁束を保持する。仕事はU+U*で、K@Azを内部gへ代用しない。独立96条件（成功88/期待失敗8）、線形極限と一様/二層解析場、8/16/32細分の場/各量・凸エネルギー差、独立1次元BVP 8比較がPASS。
標準1271件（1268合格・3skip）、追加6unitと主6unitがPASS。固定799sourceを主805sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
保存/CLI・軸対称非線形・対象版モデル、S04と全計画は未完。親33=8受入/16進行/8他未受入/1範囲外。
平面BH solve統合/finalizer実行済み・再実行禁止。主805source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[平面P1の非線形B-H弱形式](PLANAR_BH_FORMS.md)を主ツリーへ統合・限定受入。
明示材料の元Hと接線からg/Kと電流荷重を組み立て、U/U*、元B·HとAz·gを独立に検査する。独立72例288形式/144変分、定数核・線形極限・回転/尺度則がPASS。
標準1265件（1262合格・3skip）、追加5unitと主5unitがPASS。固定794sourceを主800sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
境界付き反復/失敗保存・軸対称・独立ソルバー比較・対象版モデル、S04と全計画は未完。親33=8受入/16進行/8他未受入/1範囲外。
平面BH forms統合/finalizer実行済み・再実行禁止。主800source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[単調な等方B-H表の構成則](BH_CURVE.md)を主ツリーへ統合・限定受入。
SI/原点/厳密増加/来歴・区分線形H(B)・外挿拒否を明示し、元H・接線・エネルギー/余エネルギーと逆関数を評価する。独立27曲線459スカラー/1296ベクトル/3240微分列/54零場がPASS。
標準1260件（1257合格・3skip）、追加5unitと主5unitがPASS。固定789sourceを主795sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
S04を進行中へ移す。非線形FEM/反復/失敗保存・独立ソルバー比較・対象版モデル、S04と全計画は未完。親33=8受入/16進行/8他未受入/1範囲外。
BH curve統合/finalizer実行済み・再実行禁止。主795source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸非接続の反跳材料の保存・再構築・CLI](OFF_AXIS_RECOIL_NATIVE.md)を主ツリーへ統合・限定受入。
材料テンソル/残留B/向き・phiモデル、psi基準と相対/絶対係数、三荷重を保存し、同じ実FEMで元6場とJの構成ポテンシャルを再検証する。独立24例48native/80CLIがPASS。API/CLIの5ファイルと全プローブJSONが一致し、元240native/98参照ファイルは不変。
標準1255件（1252合格・3skip）、主4unitがPASS。固定786sourceを主792sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
C00.Vの対象版/材料モデル確認、S03と全計画は未完。親33=8受入/15進行/9他未受入/1範囲外。
軸非接続反跳材料native統合/finalizer実行済み・再実行禁止。主792source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸非接続の反跳材料の境界付きFEM・元6場](OFF_AXIS_RECOIL_SOLVE.md)を主ツリーへ統合・限定受入。
固定psi/Htの実FEM、元H=nu(B−Brem)、三荷重、Jの基準付き構成ポテンシャル、Wb磁束とA周回/反力を接続した。独立96例がPASS。平面と軸非接続のゼロBで仕事が相殺する検査を修正し、平面独立96例と過去48native/240ファイルの一致・不変性も確認した。
標準1251件（1248合格・3skip）、主14unitがPASS。固定783sourceを主789sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸非接続の保存/CLI・対象版モデル確認、S03と全計画は未完。親33=8受入/15進行/9他未受入/1範囲外。
軸非接続反跳材料solve統合/finalizer実行済み・再実行禁止。主789source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸非接続の反跳材料と縮約磁束弱形式](OFF_AXIS_RECOIL_FORMS.md)を主ツリーへ統合・限定受入。
全r>0の明示tensor/残留B/向きから、psi=r*Aphi[Wb]のK[1/H]と電流/残留荷重[A]を分離する。定数psi核・残留荷重総和0、P2一様B=Bremの零HとJの基準付き構成ポテンシャルを確認した。
標準1243件（1240合格・3skip）、追加5unitと主5unit、独立72例216多項式・零H12条件がPASS。固定778sourceを主784sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸非接続の境界付き解/保存・仕事相殺検査の修正・対象版モデル確認、S03と全計画は未完。親33=8受入/15進行/9他未受入/1範囲外。
軸非接続反跳材料forms統合/finalizer実行済み・再実行禁止。主784source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸接続の反跳材料の保存・再構築・CLI](AXIS_RECOIL_NATIVE.md)を主ツリーへ統合・限定受入。
材料テンソル/残留B/向き・軸接触/phiモデル、a=Aphi/rと三荷重を保存し、同じ実FEMで元6場・全構成ポテンシャルを再検証する。独立24例48native/80CLIがPASSし、API/CLIの5ファイルと全プローブJSONが一致。元240native/98参照ファイルは不変。
標準1238件（1235合格・3skip）、追加4unitと主4unitがPASS。固定773sourceを主779sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸非接続・対象版モデル確認、S03と全計画は未完。親33=8受入/15進行/9他未受入/1範囲外。
軸反跳材料nativeの統合/finalizer実行済み・再実行禁止。主779source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸接続の反跳材料の境界付きFEM・元6場](AXIS_RECOIL_SOLVE.md)を主ツリーへ統合・限定受入。
固定a/Ht/軸の正則性の実FEM、元H=nu(B−Brem)、三荷重、J単位の基準付き構成ポテンシャルと元Wb磁束/A周回/A m²反力を接続した。独立96例がPASS。
標準1234件（1231合格・3skip）、追加6unitと主6unitがPASS。固定770sourceを主776sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸の保存/CLI・軸非接続・対象版モデル確認、S03と全計画は未完。親33=8受入/15進行/9他未受入/1範囲外。
軸反跳材料solveの統合/finalizer実行済み・再実行禁止。主776source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸接続の反跳材料と全3次元弱形式](AXIS_RECOIL_FORMS.md)を主ツリーへ統合・限定受入。
軸の材料正則性と3次元拡張を明示し、a=Aphi/r[T]のtensor Kと電流/残留荷重を分離する。全軸DOFを保ち、一様B=Bremの零H平衡とJ単位の基準付き構成ポテンシャルを確認した。
標準1228件（1225合格・3skip）、追加5unitと主5unit、独立72例216多項式・零H24条件がPASS。固定766sourceを主772sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸の境界付き解/保存・軸非接続・対象版モデル確認、S03と全計画は未完。親33=8受入/15進行/9他未受入/1範囲外。
軸反跳材料forms統合/finalizer実行済み・再実行禁止。主772source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[平面の線形反跳材料の保存・再構築・CLI](PLANAR_RECOIL_NATIVE.md)を主ツリーへ統合・限定受入。
材料テンソル/残留B/向き、基準と相対/絶対Azを保存し、同じ実FEMで元5場・三荷重・全構成ポテンシャルを再検証する。独立24例48native/80CLIがPASSし、API/CLIの5ファイルと全プローブJSONが一致。元240native/98参照ファイルは不変。
標準1223件（1220合格・3skip）、追加4unitと主4unitがPASS。固定761sourceを主767sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸対称・対象版モデル確認、S03と全計画は未完。親33=8受入/15進行/9他未受入/1範囲外。
反跳材料nativeの統合/finalizer実行済み・再実行禁止。主767source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[平面の線形反跳材料の境界付きFEM・元場](PLANAR_RECOIL_SOLVE.md)を主ツリーへ統合・限定受入。
固定Az/Htの実FEM、元H=nu(B−Brem)、分離した三荷重、J/mの基準付き構成ポテンシャルと元磁束/周回/反力を接続した。独立96例がPASS。
標準1219件（1216合格・3skip）、追加6unitと主6unitがPASS。固定758sourceを主764sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
保存/CLI・軸対称・対象版モデル確認、S03と全計画は未完。親33=8受入/15進行/9他未受入/1範囲外。
反跳材料solveの統合/finalizer実行済み・再実行禁止。主764source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[平面の反跳透磁率テンソル・残留磁束弱形式](PLANAR_RECOIL_FORMS.md)を主ツリーへ統合・限定受入。
主軸mu_rと残留B、領域の向きを明示し、tensor K・Jz荷重・残留荷重を分離する。B=0とH=0を零点とする構成ポテンシャルを区別し、定数Az核を保持する。
標準1213件（1210合格・3skip）、追加5unitと主5unit、独立72例216多項式・零H24条件がPASS。固定754sourceを主760sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
S03を進行中へ移し、親33=8受入/15進行/9他未受入/1範囲外。境界付き解・保存・軸対称・対象版のモデル確認、S03と全計画は未完。
反跳材料forms統合/finalizer実行済み・再実行禁止。主760source。次は平面の境界付き反跳FEM。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸非接続の磁静保存・再構築・CLI](OFF_AXIS_MAGNETOSTATIC_NATIVE.md)を主ツリーへ統合・限定受入。
基準と相対/絶対psi、全mu_r/Jphi/境界/穴を保存し、同じ実FEM再求解で元6場とJ/Wb/Aの全量を照合する。独立24例48native/80CLIがPASSし、API/CLIの5ファイル・全プローブJSONが一致、元240native/90参照ファイルは不変。
標準1208件（1205合格・3skip）、追加4unitと主4unitがPASS。固定749sourceを主755sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
C00の対象版/旧版仕様確認等は未完。親33=8受入/14進行/10他未受入/1範囲外、S02と全計画は未完。
軸非接続磁静nativeの統合/finalizer実行済み・再実行禁止。主755source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸非接続の境界付き磁静FEM・元6場/J/Wb](OFF_AXIS_MAGNETOSTATIC_SOLVE.md)を主ツリーへ統合・限定受入。
固定psi/Htから相対psiを実FEMで解き、元6場、Jエネルギー/Wb磁束/A電流と反力を保持する。独立88例（P2一様B32、環状電流24、二層24、零場8）がPASS。保存/CLIは後続工程。
標準1204件（1201合格・3skip）、追加6unitと主6unitがPASS。固定746sourceを主752sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
C00の対象版/旧版仕様確認等は未完。親33=8受入/14進行/10他未受入/1範囲外、S02と全計画は未完。
軸非接続磁静solveの統合/finalizer実行済み・再実行禁止。主752source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸非接続の縮約磁束psi弱形式](OFF_AXIS_MAGNETOSTATIC_FORMS.md)を主ツリーへ統合・限定受入。
r>0のpsi=r*Aphi[Wb]、1/r重みのK[1/H]、Jphi荷重[A]を接続し、定数psiの零場を保持する。独立72例・216多項式、P2一様B36例がPASS。境界付き解・保存は後続工程。
標準1198件（1195合格・3skip）、追加5unitと主5unitがPASS。固定741sourceを主747sourceへ統合。旧seed9モード19量はf差0、最大相対差8.882e-16。
C00の対象版/旧版仕様確認等は未完。親33=8受入/14進行/10他未受入/1範囲外、S02と全計画は未完。
軸非接続磁静formsの統合/finalizer実行済み・再実行禁止。主747source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[固定電流での境界距離と細分の分離](MAGNETOSTATIC_BOUNDARY_STUDY.md)を主ツリーへ統合・限定受入。
平面Jzスラブ/軸Jphi電流核の144例、48細分系列・32境界変化を独立照合した。平面の場不変とAz基準変化、軸の物理的戻りH∝b^-2をFEM差と分離した。
追加2unit/既存RF例移行2unit・主4unit、例2つの6CLI/4nativeがPASS。API/CLIの5ファイル・全プローブJSONが一致、元20native不変。固定736sourceを主742sourceへ統合し、製品ソース変更なし。
対応する全標準1191件と旧周波数/RF証拠を継承し、新規unitを別に実行した。新たな全1193件の標準実行とは区別する。S02の原要件と残件は[S02受入照合](S02_ACCEPTANCE.md)を参照。
軸非接続とC00の旧版仕様確認等は未完。親33=8受入/14進行/10他未受入/1範囲外、S02と全計画は未完。
磁静境界study統合/finalizer実行済み・再実行禁止。主742source。次は軸非接続の磁静ポテンシャル/参照空間。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸接続磁静の専用保存・再構築・CLI](AXIS_MAGNETOSTATIC_NATIVE.md)を主ツリーへ統合・限定受入。
mu_r/reluctivity・Jphi・全境界/軸DOFと元a[T]を保持し、再求解で元6場とJエネルギー・Wb磁束・A電流・A m²反力を検証する専用native/CLIを接続した。
標準1191件（1188合格・3skip）、追加4unit/旧能力表3unit、独立24例48native/80CLIと主4unitがPASS。API/CLIの5ファイル・全プローブJSONが一致、元240native/90参照ファイルは不変。固定731sourceと主737sourceは一致。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸非接続・外部境界診断・磁静Project/GUI/Study等は未完。親33=8受入/14進行/10他未受入/1範囲外、S02と全計画は未完。
軸磁静native統合/finalizer実行済み・再実行禁止。主737source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸接続磁静の実FEM・元Aphi/B/H・全3D磁束/エネルギー](AXIS_MAGNETOSTATIC_SOLVE.md)を主ツリーへ統合・限定受入。
明示mu_r/Jphi・軸/固定Aphi/r/Htから正則aを実FEMで解き、元6場、Jエネルギー、Wb磁束を接続した。Ampere電流[A]と固定a反力[A m²]を区別する。
標準1187件（1184合格・3skip）、追加6unit・独立88例と主6unitがPASS。固定728sourceと主734sourceは一致。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸保存/CLI・軸非接続・外部境界診断等は未完。親33=8受入/14進行/10他未受入/1範囲外、S02と全計画は未完。
軸磁静solve統合/finalizer実行済み・再実行禁止。主734source。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[軸に接続した磁静場の正則弱形式](AXIS_MAGNETOSTATIC_FORMS.md)を主ツリーへ統合・限定受入。
正値mu_r/Jphi、a=Aphi/r[T]と全軸DOF、元Br/Bzのエネルギー形式K[m⁴/H]・源仕事荷重[A m²]を追加した。定数aは一様軸方向Bで、gauge核と扱わない。
標準1181件（1178合格・3skip）、追加5unit、独立72例216多項式と主5unit/同独立照合がPASS。固定723sourceと主729sourceは一致。旧seed9モード19量はf差0、最大相対差8.882e-16。
軸対称の境界付き解・場/磁束出力・保存/CLI・軸非接続と外部境界診断等は未完。親33=8受入/14進行/10他未受入/1範囲外、S02と全計画は未完。
軸磁静forms統合/finalizer実行済み・再実行禁止。主729source。次は軸接続磁静の境界付き解法。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[平面磁静場の専用保存・再構築・CLI](PLANAR_MAGNETOSTATIC_NATIVE.md)を主ツリーへ統合・限定受入。
mu_r/reluctivity・Jz・固定Az/Ht・相対/絶対Azを保持し、再求解と元Az/B/H・エネルギー・電流/磁束・規約の全照合を接続した。
標準1176件（1173合格・3skip）、追加4unit/旧能力表3unit、独立24例48native/80CLIと主4unitがPASS。API/CLIの5ファイル・全プローブJSONが一致し、元240native/90参照ファイルは不変。固定718sourceと主724sourceは一致。
旧seed9モード19量はf差0、最大相対差8.882e-16。軸対称・外部境界診断・磁静Project/GUI/Study等は未完。親33=8受入/14進行/10他未受入/1範囲外、S02と全計画は未完。
磁静native統合/finalizer実行済み・再実行禁止。主724source。次は軸対称磁静の正則弱形式。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[平面線形磁静場の実FEM・元B/H・磁束/エネルギー](PLANAR_MAGNETOSTATIC_SOLVE.md)を主ツリーへ統合・限定受入。
明示mu_r/Jzと全境界の固定Az/Ht、実FEMの相対Az、元Az/B/H、J/mエネルギー、反力/元H周回積分[A]・元B磁束[Wb/m]を接続した。
標準1172件（1169合格・3skip）、追加6unit、独立88例と主6unitがPASS。固定715sourceと主721sourceは一致。旧seed9モード19量はf差0、最大相対差8.882e-16。
離散反力保存と元HのAmpere診断を区別する。平面保存/CLI・軸対称・外部境界診断等は未完。親33=8受入/14進行/10他未受入/1範囲外、S02と全計画は未完。
磁静solve統合/finalizer実行済み・再実行禁止。主721source。次は平面磁静の保存/CLI。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13：[平面磁静の材料・Jz・Az弱形式](PLANAR_MAGNETOSTATIC_FORMS.md)を主ツリーへ統合・限定受入。
正値実数mu_r・全領域電流から、reluctivityによるK[m/H]と荷重[A]を組み立て、全DOFと定数Azのgauge核を保持する。
標準1166件（1163合格・3skip）、追加5unit/旧RF移行2unit、独立72例216多項式・72mu逆比例/一様Bエネルギー、主5unit/同独立照合がPASS。固定710sourceと主716sourceが一致。
旧seed9モード19量はf差0、最大相対差8.882e-16。境界付き磁静解・元B/H/磁束・保存/CLIは後続工程。
S02を進行中へ移し、親33=8受入/14進行/10他未受入/1範囲外。S02と全計画は未完。
磁静forms統合/finalizer実行済み・再実行禁止。主716source。次は平面磁静の境界付き解法。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

最新：境界studyは最終144例/4unit PASS、主711sourceと4unitもPASS。初回integratorは新examples/electrostaticディレクトリ未作成で3検証ファイルだけコピーして停止。resume-electrostatic-boundary-study-integration-20260913.pyで全partial hashを照合し、例2ファイルだけ追加して復旧済み。元integrator/resume/finalizerはすべて再実行禁止。主711source、次は磁静forms-final710の標準58978（1166件）。磁静formsは5新+2RF移行unit/独立72例216多項式PASS、本体未統合、integrator/finalizer未作成。全GUI停止、全計画未完、親33=8/13/11/1。

2026-09-13：[静電の境界距離とメッシュ細分の分離検証](ELECTROSTATIC_BOUNDARY_STUDY.md)を主ツリーへ統合・限定受入。
固定電荷の平面帯/同軸領域144例で、48固定境界細分系列と32境界移動を解析照合した。共通場が不変でも絶対電位が距離/対数で増えることを明記し、厳密開放境界の収束とは扱わない。
追加2unit/旧RF移行2unit・主4unit、入力例2つの6CLI/4nativeがPASS。API/CLIの5ファイルと全プローブJSONが一致、元20native不変。製品ソース変更なし、固定705sourceを主711sourceへ統合した。
既存標準1159件と周波数/RFの証拠を継承し、追加2unitを別に実行した。新たな全標準実行とは区別する。S01の原要件と残件を[S01受入照合](S01_ACCEPTANCE.md)に集約。
C00の旧版仕様確認と静電GUI等は未完。親33=8受入/13進行/11他未受入/1範囲外、全計画未完。
境界study統合/finalizer実行済み・再実行禁止。主711source。次の限定課題/実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

最新：平面native主4unit PASS、統合/finalizer実行済み・再実行禁止。主706source。次は準備済み境界study-final705 integrator→主4unit（新2+旧RF移行2）→finalizer、全144例は再実行しない。境界の独立144例と固定最終705sourceは完全一致。残る実ハンドルは磁静forms標準58978だけ。磁静forms統合/finalizer未作成。全GUI停止、全計画未完、親33=8/13/11/1。

2026-09-13：[平面静電の専用保存・再構築・CLI](PLANAR_ELECTROSTATIC_NATIVE.md)を主ツリーへ統合・限定受入。
中立Cartesian幾何・全材料/rho/境界・基準電位と元係数を保存し、実Poisson再構築/再求解で元Phi/E/D・C/m電荷・J/mエネルギー・F/m容量を全再生する。
標準1159件（1156合格・3skip）、追加4unit/旧能力表3unit、独立24例48native/80CLIと主4unitがPASS。API/CLIの5ファイル・プローブJSONが一致し、元240nativeは不変。固定700sourceと主706sourceは一致。
旧seed9モード19量はf差0、最大相対差8.882e-16。静電Project/GUI/Study・外部境界診断等、S01と全計画は未完。親33=8受入/13進行/11他未受入/1範囲外。
平面native統合/finalizer実行済み・再実行禁止。主706source。次の限定課題と実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

最新：平面native独立88424/標準6986は終了0（24例48native/80CLI、193.876秒、240native/90参照不変、標準1159件）。native integrator実行済み、主706source。本体4unitの実ハンドルを確認しfinalizerへ。境界study-final705の独立7049は144例PASS/163.620秒、4unit PASSで最終固定済み。境界integrator/finalizerを新examples/electrostatic/配置と独立全source一致・主4unitへ更新済み未実行。磁静forms-final710は7unit/72例PASS、標準58978だけが実行中。元50194は終了241で保持。磁静forms統合/finalizerは未作成。全GUI停止、全計画未完、親33=8/13/11/1。

最新：平面solveは主18unit PASS、統合/finalizer実行済み・再実行禁止。主703source、標準55579終了0（1155=1152+3skip、2268.227秒）、独立71566終了0（88例1030.401秒、既存軸24native/240ファイル/プローブ不変）。native独立88424/標準6986は実行中、統合/finalizer未実行。境界例のroot配置で旧RF移行2検査が4errorsになることを確認。専用examples/electrostatic/へ移した-final候補705で追加2+旧移行2unit PASS、独立7049（144例）実行中。境界統合/finalizerの旧版はまだ新配置へ要更新。磁静formsも-final710へ継承し5新+2移行unit/独立72例PASSで固定、標準58978実行中（1166件）。旧標準50194は失敗が既知のため自分のunittest子だけSIGTERMで停止し終了241、partial log保持。磁静forms統合/finalizer未作成。全GUI停止、全計画未完、親33=8/13/11/1。

2026-09-13：[平面静電Poisson解・元E/D・電荷/容量](PLANAR_ELECTROSTATIC_SOLVE.md)を主ツリーへ統合・限定受入。
全境界の固定電位/Dn、単位長さの実FEMと元Phi/Ex/Ey/Dx/Dy、J/mエネルギー、反力/元場電荷とF/m容量を接続した。
標準1155件（1152合格・3skip）、追加8unitと既存10unit、独立88例、既存軸24native/240ファイル/プローブ不変、主18unitがPASS。固定697sourceと主703sourceは一致。
軸/平面の混在bool入力漏れを修正。Fourier参照の打切り差の未達は、許容差不変で2048/4096項へ増やして解消した。
旧seed9モード19量はf差0、最大相対差8.882e-16。平面保存/CLI・静電GUI・外部境界診断等、S01と全計画は未完。親33=8受入/13進行/11他未受入/1範囲外。
平面solve統合/finalizer実行済み・再実行禁止。主703source。次は平面専用native/CLI。実ハンドルの最新状態を確認する。以下よりこの冒頭を優先。

最新19:30 UTC前後：主2545745/698source。平面solve独立71566（-refined697、P2最細n80）、元標準55579、native元標準6986は実行中。native-refined700の独立24例80CLIは71566 PASS待ち。2組integrator/finalizerは準備済み未実行、標準との差は別の独立検証スクリプト1件だけとして監査する。境界study88105は144例PASS/163.018秒、2unit PASS、705source固定（独立時との差も同じ別検証スクリプト1件）。境界integrator/finalizerも準備済み未実行、本体は2unitだけ。平面磁静forms候補710sourceは5unit/72例216多項式・72mu逆比例/一様B PASS、固定して標準50194を開始（1166件）。どの固定候補も編集禁止。磁静forms統合/finalizerは未作成。S01原要件照合は docs/S01_ACCEPTANCE.md、C00未確定で親受入数は維持。全GUI停止、全計画未完、親33=8/13/11/1。

最新：主2545745/698source。平面solveの独立93588はP2n64元E/D差0.000520161>0.0005で終了1。許容差不変で最細n80へ増やした別固定候補 /tmp/superfish-planar-electrostatic-solve-refined-20260913（697source）で独立71566を開始。元標準55579とnative標準6986は元候補のまま継続。nativeも別固定-refined候補700へ検証スクリプト1件だけ更新、独立24例80CLIは新88例PASS待ち。2組integrator/finalizerはこの一差分を監査するよう更新済み・未実行。境界遠方化の別候補 /tmp/superfish-electrostatic-boundary-study-20260913 は2unit PASS、独立144例88105実行中、未固定。ソルバー変更なし、新3検証ファイル+2実行例だけ。全GUI停止、全計画未完、親33=8/13/11/1。

最新：平面formsは主5unit/72例216多項式PASS、標準73191終了0（1147=1144合格+3skip、2229.919秒）。統合/finalizer実行済み・再実行禁止、主698source。平面solve固定697は独立93588（88例と既存軸24native）/標準55579（1155件）、native固定700は標準6986（1159件）。独立参照のFourier初回512/1024項の未達を保存し、しきい値不変で2048/4096項へ増やした。nativeは4unit/旧能力表3unit/3CLI smoke PASS、独立24例80CLIはsolve独立PASS待ちで未実行。両候補src/tests/scripts/examplesを変更しない。solve/native統合ヘルパーは準備済み未実行、doc finalizerはまだ未作成。全GUI停止、全計画未完、親33=8/13/11/1。

2026-09-13：[平面静電の誘電体・電荷・弱形式](PLANAR_ELECTROSTATIC_FORMS.md)を主ツリーへ統合・限定受入。
単純多角形の全セルへepsilon_r/rhoを明示し、軸や厚さを仮定しないK[F/m]・荷重[C/m]と定数電位核を保持する。
標準1147件（1144合格・3skip）、追加5unit、独立72例/216多項式と主5unit/同照合がPASS。平行移動/回転、Kの尺度不変、荷重の面積尺度則を確認した。
旧seed9モード19量はf差0、最大相対差8.882e-16。平面の境界/Poisson解・元場/容量・保存操作は別工程。
S01と全計画は未完。親33=8受入/13進行/11他未受入/1範囲外。
平面forms統合/finalizer実行済み、再実行しない。主698source。次は平面Poisson解の限定課題。実ハンドルの最新状態を確認する。以下よりこの冒頭を優先。

最新：軸対称静電native標準51514終了0（1142=1139合格+3skip、2255.990秒）、主4unit/24例79CLIはPASS（独立99.195秒）。統合/finalizer実行済み・再実行禁止、主693source。残る標準は平面forms73191だけ。平面solve候補は関連18unit PASSで未固定。混在boolの入力漏れを再現し、electrostatic_boundary.py共通入力検査と軸/平面の2ソルバーへ修正した。軸の既存2src変更を含むので、次の独立検証で既存24軸native/全240ファイル/プローブを再生して数値不変を確認する。全計画未完、親33=8/13/11/1。

2026-09-13：[軸対称静電の専用保存・再構築・CLI](ELECTROSTATIC_NATIVE.md)を主ツリーへ統合・限定受入。
誘電体/電荷/全境界・基準電位・元係数を保存し、同じPoisson問題の再構築/再求解と元Phi/E/D・電荷/エネルギー/容量を全再生する。
標準1142件（1139合格・3skip）、追加4unit/旧能力表3unit、独立24例48native/79CLIと主4unit/同照合がPASS。API/CLIの5ファイル・プローブJSONが一致、元240native不変。
capabilitiesへ静電の専用入口・SI単位・境界/容量の制約を追加。旧seed9モード19量はf差0、最大相対差8.882e-16。
静電Project/GUI/Study・平面・純Neumann等、S01と全計画は未完。親33=8受入/13進行/11他未受入/1範囲外。
静電native統合/finalizerは実行済み、再実行しない。主693source。全計画は未完。次の限定課題はBACKLOGの最新記載を確認する。以下よりこの冒頭を優先。

最新：軸対称静電solve標準1962は終了0（1138=1135合格+3skip、2261.456秒）。主6unit PASSで統合/finalizer実行済み、主690source。残る標準はnative51514と平面forms73191。両統合/finalizerは準備済み未実行。native本体は4unit+24例79CLI、平面forms本体は5unit+72例。平面solveは新planar_electrostatic.pyとscripts/planar_electrostatic_reference.pyを実装しsmoke PASS、6例の矩形Poisson細分の予備調査が完了（本体未統合・未受入）。次はこの平面solveの正式unit/独立検証。全計画未完、親33=8/13/11/1。

2026-09-13：[軸対称静電Poisson解・元E/D・電荷/容量](ELECTROSTATIC_SOLVE.md)を主ツリーへ統合・限定受入。
全境界を固定電位/外向きDn/対称軸へ明示し、基準電極からの電位差を実FEMで解く。元場・領域エネルギー、離散反力と元Dによる電極電荷を別々に評価する。
標準1138件（1135合格・3skip）、追加6unit、二層32/製造解48/同軸24の独立104例と主6unitがPASS。固定684sourceと主690sourceの一致を確認した。
同電位の場0を基準電位差で保ち、同軸P1/P2の電位誤差未達はしきい値を変えず16/32/64の細分で解消した。
旧seed9モード19量はf差0、最大相対差8.882e-16。静電保存/CLI/GUI・平面・純Neumann等、S01と全計画は未完。親33=8受入/13進行/11他未受入/1範囲外。
静電solve統合/finalizerは実行済み、再実行しない。主690source。次は専用静電native/CLI。実ハンドルの最新状態を確認する。以下よりこの冒頭を優先。

最新：主HEAD 9202a9e、685source。標準の実ハンドルは軸対称solve1962（1138件）、native51514（1142件）、平面forms73191（1147件）。前二者の独立照合は104例/24例79CLIともPASS。平面formsは5unit/72例216多項式PASSで固定692source、主未統合。平面solve候補 /tmp/superfish-planar-electrostatic-solve-20260913 を作成したが実装未着手、計画のみ。軸対称solve/native統合+finalizerは準備済み未実行。平面forms統合/finalizerは未作成。親33=8/13/11/1、全計画未完。

2026-09-13 JST最新：主HEAD 9202a9e、静電formsまで685source受入済み。solve最終42541は104例PASS（872.013秒、固定684一致）、native独立14077は24例48native/79CLI PASS（99.970秒、固定687一致）。残る標準はsolve1962とnative51514。両統合/finalizerは準備済み未実行、主期待690/693。solve本体は6unitと全ソース一致で確認し、104例を本体で再実行したとは扱わない。native本体は4unitと独立24例79CLI。平面静電forms候補 /tmp/superfish-planar-electrostatic-forms-20260913 は固定native687を基に実装中。新2srcのみ、smoke PASS、テスト/独立検証はこれから。全計画未完、親33=8/13/11/1。

最新：静電forms主5unit/72独立例は終了0、統合/finalizer実行済み（再実行禁止）、主685source。残る実ハンドルはsolve独立42541/標準1962、native標準51514。solve/native統合とdoc finalizerは両方準備済み未実行。native独立24例79CLIはsolve最終104例PASS待ち。親33=8受入/13進行/11他未受入/1範囲外、全計画未完。

2026-09-13：[軸対称静電の誘電体・電荷・弱形式](ELECTROSTATIC_FORMS.md)を主ツリーへ統合・限定受入。
正値実数epsilon_r・全材料割当・符号付き領域rhoから全3DのK[F]と荷重[C]を組み立て、定数電位核と全軸DOFを保持する。
標準1132件（1129合格・3skip）、追加5unit、独立72例/216多項式と主5unit/同照合がPASS。総電荷・尺度則・領域順序変更も照合した。
旧seed9モード19量はf差0、最大相対差8.882e-16。静電の境界/解法・場/容量・保存操作は別工程。
S01を進行中へ移し、親33=8受入/13進行/11他未受入/1範囲外。S01と全計画は未完。
静電forms統合/finalizerは実行済み。主685source、再実行しない。次はELECTROSTATIC_SOLVE_PLAN.mdの限定課題。実ハンドルは最新状態を確認する。以下よりこの冒頭を優先。

2026-09-13 JST最新：主HEAD e615881、680source。静電forms標準39531、solve独立42541/標準1962、native標準51514が実行中。native固定687sourceは4unit+旧能力表3unit+3CLI PASS、独立24例79CLIはsolve最終104例のPASS待ちで未開始。3固定候補679/684/687を変更しない。forms統合/finalizer準備済み未実行、solve/native統合スクリプトだけ準備済み未実行（各doc finalizer未作成）。主での期待sourceは順に685/690/693。全GUIサーバー停止済み。全計画未完、親33=8/12/12/1。

最新：主HEAD e615881、材料workspaceまで680source受入済み。静電forms固定679の標準39531、静電solve固定684の最終独立42541/標準1962が実行中。後者P1/P2とも電位の未達を記録し、しきい値不変で16/32/64へ細分した。固定候補のソース変更禁止。静電native候補は固定solveを基に作成し実装中、未受入。forms統合/finalizerの2スクリプトは準備済み・未実行。全GUIサーバー停止済み。親33=8/12/12/1、全計画未完。

最新：材料workspace主5unit/12例24StudyFEM/14保存ジョブ6CLIは終了0、統合とfinalizer実行済み。主680source。静電弱形式標準39531だけが実行中。静電solve別候補は6unit PASS、独立解析照合の初回37569は終了1で理由を調査する。全GUIサーバー停止済み。全計画は未完。

2026-09-13：[材料HφのProject・表示・独立掃引](MATERIAL_HPHI_WORKSPACE.md)を主ツリーへ統合・限定受入。
全材料分割を保持する所有worker/GUIへ接続し、元セルのB=mu0 mu_r H、片側の材料情報付き25列CSV、領域エネルギー/壁損失、尺度/U/壁導電率の独立Studyを扱う。
標準1127件（1124合格・3skip）、追加5unit、独立12例24StudyFEM/24取込/12再起動、Chrome41項目と主5unit/同独立照合/14保存ジョブ6CLIがPASS。
元300nativeとGUI65nativeは不変。PNG/CSVはCLI/GUI/復元で一致し、旧同軸PNG/CSVは変更前とbyte一致。旧seed9モード19量はf差0、最大相対差8.882e-16。
材料比較/追跡・損失/分散・旧版照合、P04/O02と全計画は未完。親33=8受入/12進行/12他未受入/1範囲外。
材料workspace標準93382は終了0。統合/finalizerは実行済み、再実行しない。主680source。
実GUI/HTTPサーバーは停止済み。原本2ディレクトリはbrowser-server/moved-originalsへ移動済み、所有コピー14ジョブ/保存物65ファイルを検証済み。
全計画は未完。次の限定課題はBACKLOGの最新記載を確認する。以下よりこの冒頭を優先。

2026-09-13 JST最新：主HEAD 5b1229c、材料nativeまで678source受入済み。材料workspace標準93382が実行中。静電弱形式候補679sourceは追加5unit/独立72例・216多項式PASSで固定し、標準1132件を39531で開始した。どちらの固定候補もsrc/tests/scripts/examplesを変更しない。静電はまだ本体未統合・未受入。全GUIサーバー停止済み。全計画は未完。

2026-09-13：[材料Hφの専用保存・再生・CLI](MATERIAL_HPHI_NATIVE.md)を主ツリーへ統合・限定受入。
材料/界面/元メッシュ・最低正スペクトル・領域RFを全再構築するnative版1とsolve/replay/probe-material-hphiを追加した。プローブは片側の材料情報とB=mu0 mu_r Hを保持する。
標準1122件（1119合格・3skip）、追加4unit/旧能力表3unit、独立24例48native/78CLIと主4unit/同照合がPASS。API/CLIの全5ファイルとプローブJSONが一致、元240native/25参照ファイルは不変。
旧seed9モード19量はf差0、最大相対差8.882e-16。材料Project/GUI/Study・損失/旧版照合、P04と全計画は未完。親33=8受入/12進行/12他未受入/1範囲外。
材料native標準4327は終了0。統合/finalizerは実行済み、再実行しない。主678source。
次は材料Project/表示/独立Studyを、全材料・片側B/領域情報と尺度則を保持して接続する。実ハンドルの最新状態を確認する。
全計画は未完。以下よりこの冒頭を優先。

最新状態：材料RFの主6unit/32独立FEMは終了0、finalizer実行済み。材料native標準4327も終了0で、次に統合する。材料workspace標準93382だけが実行中。全GUIサーバー停止済み。静電弱形式は独立候補で実装中、未受入。

2026-09-13：[材料重み付きHφ固有解・元場・RF](MATERIAL_HPHI_RF.md)を主ツリーへ統合・限定受入。
直線適合メッシュの正値実数・等方・無損失材料を専用Caseへ接続し、実FEM・セルごとのE/H/B・領域エネルギー・非磁性壁損失・明示真空軸電圧を評価する。
標準1118件（1115合格・3skip）、追加6unit、独立24材料例72モード/二層8例24モード、主6unit/同独立照合がPASS。
粗いP1のfとP2のEの未達を記録し、許容差不変で細分した。最細P2の最大f差2.087e-7、E L2差4.735e-4、壁損失差1.627e-6。
旧seed9モード19量はf差0、最大相対差8.882e-16。材料native/CLI/GUI・損失/旧版照合、P04と全計画は未完。親33=8受入/12進行/12他未受入/1範囲外。
材料RF標準82717は終了0。統合/finalizerは実行済み、再実行しない。主675source。
次は専用材料native/CLI候補の標準を確認し、本体で4unitと24例78CLIを照合する。実ハンドルの最新状態を確認する。
全計画は未完。以下よりこの冒頭を優先。

2026-09-13 JST 02:13時点：材料workspaceの復元Chrome68810は8項目PASS、server61697停止済み。保存物95321もPASS：14jobs=13complete+1cancel、元65native不変、原本2移動、6CLI、Chrome合計41操作。旧同軸PNG/CSVは変更前byte一致。GUI/ブラウザーは全て停止。
材料3候補の標準82717/4327/93382だけが実行中。RF(1118)→native(1122)→workspace(1127)の順に実結果を確認して統合する。3組の/tmp/integrate-material-hphi-*と/tmp/finalize-material-hphi-*-docs-20260913.pyはすべて準備済み・未実行。
workspaceの主照合は5unit、scripts/validate_material_hphi_workspace.pyで新out/material-hphi-workspace-main-20260913、/tmp/verify-material-hphi-workspace-browser-artifacts-20260913.py --source主 --out新out/material-hphi-workspace-main-browser-artifacts-20260913（期待14jobs/6CLI）。主sourceは順に675/678/680になる。std中の候補src変更禁止。
全計画は未完。以下よりこの最新冒頭を優先。

2026-09-13 JST 02:07時点。主HEAD 11c2234、材料領域/行列まで670source受入済み。全計画は未完、親33=8受入/12進行/12他未受入/1範囲外。
固定候補の標準回帰3本：材料RF82717（669source/期待1118、16:39〜UTC）、材料native4327（672source/期待1122、16:48〜UTC）、材料workspace93382（674source/期待1127、17:03〜UTC）。src/tests/scripts/examplesを変更しない。
RFは6unit/独立32FEM96モード、nativeは4unit/独立24例48native78CLI、workspaceは5unit/独立12例24StudyFEM・24取込12再起動・元300nativeがPASS。材料B表示の誤差82.68%を先に再現し、修正後0。材料RF粗いP1/P2の未達を残し、許容差不変で48/96へ細分した。
RFとnativeの/tmp/integrate-*および/tmp/finalize-*-docs-20260913.pyは準備済み・未実行。主RF6unit+独立32例、主native4unit+24例78CLIを統合後に実行してから各finalizer。
材料workspace実Chrome新20/旧同軸8/旧TMTE平面5チェックPASS。旧server73379は停止済み。restart準備43754は実行済み（再実行不可）：既存13jobs、所有取込2、保存native65ファイル、元2ディレクトリを移動。次の復元Chromeと再起動serverの実ハンドルを確認する。
/tmp/verify-material-hphi-workspace-browser-artifacts-20260913.pyは準備済み、復元ブラウザー終了後にserver停止して--source候補 --out新規で実行する。旧曲線と件数を混同しない。復元後は14jobs見込み、実測で確定する。workspaceの統合/finalizerはまだ未作成。
以下よりこの最新冒頭を優先する。

2026-09-13 JST 01:48時点：材料行列基盤は標準1112件・主5unit/独立72ケースすべてPASS、主670source。統合/finalizerは実行済み。P04を進行中へ移し、親33=8受入/12進行/12他未受入/1範囲外。
材料RF候補669sourceの標準82717は継続（期待1118件）。最終6unitと独立32FEM/96モードはPASS。P1/P2の粗い失敗を残し、しきい値不変で48/96分割へ増やした。/tmp/integrate-material-hphi-rf-20260913.pyは準備済み未実行。
材料native候補/tmp/superfish-material-hphi-native-20260913は専用native/CLI/能力情報を実装。4unit・独立24例48native/78CLIがPASS（71623終了0、56.785秒）。native240ファイルと元参照25ファイル不変。候補固定/標準と主統合はまだ未完。
実GUI/HTTPサーバーはすべて停止済み。全計画は未完。以下よりこの最新冒頭を優先。

2026-09-13：[線形RF材料の領域・界面・Hφ行列基盤](MATERIAL_HPHI_FORMS.md)を主ツリーへ統合・限定受入。
正値・実数・等方・区分一定epsilon_r/mu_rを全直線セルへ明示割当し、q/uの材料重み付きK/Mを組み立てる。
標準1112件（1109合格・3skip）、独立72ケース・材料尺度則12全スペクトル、主5unit/72ケースがPASS。
旧seed9モード19量はf差0、最大相対差8.882e-16。材料固有解・場/RF・保存/CLI/GUIと全計画は未完。
P04を進行中へ移し、親33課題は8受入/12進行/12他未受入/1範囲外。材料ソルバーの利用可能性は宣言しない。
材料行列基盤の標準76192は終了0、主670source。統合/文書finalizerは実行済みで再実行しない。
次は材料重み付き固有解・場・RFを、独立した層状共振器の解析対照を先に確定して実装する。
以下よりこの冒頭を優先する。全計画は未完。

2026-09-13 JST 01:36時点：能力表は標準1107件・主3unit/5例59CLIすべてPASS、主665source。統合/文書finalizerは実行済み。主検証ハンドルなし。
材料行列の標準76192は継続、期待1112件。材料RF候補は追加5unit PASS。独立検証57592は粗いP1第3モードのf差1.072%でFAIL（基準1%）、元ログを保存。数値しきい値を保ちP1の分割を48/96へ増やして再検証する。製品コードの失敗ではなく離散化精度の未達として扱う。
全計画は未完。以下よりこの最新冒頭を優先。

2026-09-13：[実装済み能力表の整合](CAPABILITY_INVENTORY.md)を主ツリーへ統合・限定受入。
capabilitiesへHφ4形式の入力/保存・q/u/軸・CLI/Project/GUI/Studyと直線だけの比較を追加し、平面追跡版1〜7の写像/境界条件を列挙した。
標準1107件（1104合格・3skip）、関連11unit、5Hφ例/38コマンド/59CLI/75nativeと主3unit/同照合がPASS。旧seed9モード19量はf差0、最大相対差8.882e-16。
能力表の補完で物理や入力受理を拡張していない。親33課題の8受入/11進行/13他未受入/1範囲外と全計画未完を維持する。
能力表標準10066は終了0・2221.826秒、主3unit/5例59CLIも終了0。主665source。
/tmp/integrate-capability-inventory-20260913.pyと/tmp/finalize-capability-inventory-docs-20260913.pyは実行済み。再実行しない。
次のP04材料領域/K・M候補は/tmp/superfish-material-hphi-forms-20260913。別受入で、最新の実ハンドルを確認する。全計画は未完。以下よりこの冒頭を優先する。

2026-09-13 JST 01:26時点：曲線workspaceは標準1104件・主5unit/独立12ケース/17保存ジョブ6CLIすべてPASS、主662source。統合/文書finalizerは実行済み。コード変更中の主検証なし。
残る標準：能力表10066（候補659source、期待1107）、材料行列76192（候補664source、期待1112）。実GUI/HTTPサーバーはすべて停止済み。
能力表と材料行列の統合/finalizeスクリプトを/tmpへ準備済み、未実行。各標準完了後に順序どおり統合し主検証する。
次の材料RF候補/tmp/superfish-material-hphi-rf-20260913を材料行列候補から分離し実装中。Case/固有解/元E/H/Bを追加、RFと検証は未完。MATERIAL_HPHI_RF_PLAN.mdが受入条件。主には未統合。
全計画は未完。以下よりこの最新冒頭を優先。

2026-09-13：[明示曲線HφのProject・表示・独立掃引](CURVED_HPHI_WORKSPACE.md)を主ツリーへ統合・限定受入。
二次の全幾何を保持するProject/worker、曲線パッチで穴を除く元場表示、全18成分CSV、全中点/軸経路を変換する独立Studyを接続した。
標準1104件（1101合格・3skip）、独立12ケース/24Study FEM/24取込/12再起動、Chrome新18/復元8/旧13、主5unit/同独立照合/17保存ジョブ6CLIがPASS。
元300nativeとGUI元80nativeは不変。曲線PNG/CSVはCLI/GUI/復元後で一致し、旧同軸PNG/CSVは変更前とbyte一致。旧seed9モード19量はf差0、最大相対差8.882e-16。
曲線比較/追跡・一般写像・材料/静的場・旧版照合等と全計画は未完。親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
曲線workspace標準93189は終了0・2210.902秒、主5unit/12ケース/17保存ジョブ6CLIも終了0。主662source。
/tmp/integrate-curved-hphi-workspace-20260913.pyと/tmp/finalize-curved-hphi-workspace-docs-20260913.pyは実行済み。再実行しない。
次の能力表候補/tmp/superfish-capability-inventory-20260913は別受入。最新の実ハンドルを確認する。全計画は未完。以下よりこの冒頭を優先する。

2026-09-13 JST（2026-09-12 15:48 UTC）：主HEAD eca0ea2、主659source。曲線workspace候補656sourceは最終標準93189が実稼働（out/validation-curved-hphi-workspace-final-20260913）。先行27730は任意Matplotlib欠如のテストskip追加のため意図的停止143、合格に数えない。製品/validatorソースは初回固定と同じ。
workspaceの追加5unit/関連32unit、独立12ケース319.164秒、Chrome新18/復元8/旧Hφ8/旧TMTE平面5、artifact17ジョブ/元80native/6CLI11.905秒はPASS。全サーバー・ブラウザーは停止済み。ROOT=out/curved-hphi-workspace-browser-server-20260913には2元結果をmoved-originalsへ移した検証状態を保持。
次のC01能力表修正は/tmp/superfish-capability-inventory-20260913の別候補で実装中。元656sourceをコピー済み。能力表にHφ4形式・平面追跡7が欠落する失敗を確認し、専用metadataを作業中。まだテスト/標準/受入なし。全計画は未完。以下よりこの冒頭を優先。

2026-09-13 JST（2026-09-12 15:33 UTC）：曲線nativeを主659sourceへ統合し、標準1099件・主4unit/24ケース74CLIとも終了0。RFは039ac25へローカルコミット済み。
次のProject/表示/Studyは/tmp/superfish-curved-hphi-workspace-20260913の別候補。追加5unit 36.670秒、関連32unit 56.855秒（HTTP環境1skip）がPASS。独立38044とGUIサーバー38399が実稼働、ROOT=out/curved-hphi-workspace-browser-server-20260913。未受入。以下よりこの冒頭を優先する。

2026-09-12：[明示曲線Hφのnative・CLI](CURVED_HPHI_NATIVE.md)を主ツリーへ統合・限定受入。
二次幾何・元係数・最低正帯域・全RFとq/u/phasor/R/Q規約を5ファイルへ保持し、完全再生と専用solve/replay/probeを接続した。
標準1099件（1096合格・3skip）、関連30unit、独立24ケース/48保存/74CLIと主4unit/同保存CLI照合がPASS。元240native不変、API/CLIのnative5はbyte一致、全プローブJSON一致。追加の半径非線形24ケース/48RF/12CLIもPASS。
旧seed9モード19量はf差0、最大相対差8.882e-16。Project/GUI・一般写像・旧版照合等と全計画は未完。親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
曲線native標準94675は終了0・2262.072秒。主4unit7.719秒、主24ケース/48保存/74CLIも終了0。主659source。
/tmp/integrate-curved-hphi-native-20260912.pyと/tmp/finalize-curved-hphi-native-docs-20260912.pyは実行済み。再実行しない。
曲線幾何/K/M、RF、nativeの3固定候補は全て受入済み。次のProject/GUI・Study/追跡は別工程。全計画は未完。以下よりこの冒頭を優先する。

2026-09-12：[明示曲線Hφの固有解・場・RF](CURVED_HPHI_RF.md)を主ツリーへ統合・限定受入。
正半径qの静的循環と軸接続uを分け、元物理微分・逆写像プローブ、全曲線壁損失、明示軸の複素Vaccと両R/Qを専用APIへ接続した。
標準1095件（1092合格・3skip）、関連26unit、独立48 FEM/144 RFと主4unit/同独立検証がPASS。半径非線形写像の追加24ケース/48RF/12CLIもPASS。旧seed9モード19量はf差0、最大相対差8.882e-16。
native/CLI・Project/GUI・一般の形状写像・旧版照合等と全計画は未完。親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
曲線RF標準38419は終了0・2230.517秒。主4unit5.300秒、主48 FEM/144 RFも終了0。主656source。
/tmp/integrate-curved-hphi-rf-20260912.pyと/tmp/finalize-curved-hphi-rf-docs-20260912.pyは実行済み。再実行しない。
次のnative/CLI候補/tmp/superfish-curved-hphi-native-20260912は別の受入。実ハンドル94675等の最新状態を確認してから統合する。全計画は未完。以下よりこの冒頭を優先する。

2026-09-12 15:04 UTC 続報：主652sourceへ幾何/K/Mを統合し限定受入。標準36849は1091件（1088合格・3skip）2251.925秒で終了0。主22unit1279は3.374秒、主72幾何47330は8.791秒、主72形式62184は18.460秒で終了0。対応するintegrate/finalize helperは実行済み、再実行しない。
現在liveは曲線RF標準38419（候補650source、期待1095件、14:39 UTC開始）と曲線native標準94675（候補653source、期待1099件、14:53 UTC開始）。候補を変更しない。未終了を合格に数えない。
native候補/tmp/superfish-curved-hphi-native-20260912は追加4unit7.502秒、関連30unit20.729秒、独立24ケース/48保存/74CLI（72成功・2想定拒否）77.974秒がPASS。240nativeと97参照ファイル不変、API/CLI native5はbyte一致、プローブ全JSON一致。GUI/Projectは未接続。
半径も二次となる追加検証98863は24ケース/48RF/12CLI、40native不変で14.345秒・終了0。解析形式差2.177e-14、f7.128e-14、RF7.223e-15、場1.161e-15。全3候補の固定基盤sourceとの対応をreportへ保存。実行helperはout/curved-hphi-native-development-20260912/operation-helpersへhash付き保管。
RFとnativeのintegrate helperは準備済み・未実行。RF/nativeのfinalize helperは未準備。本体統合後は各主4unitと主独立検証、文書/来歴/物理仕様、ローカルコミットを行う。全計画は未完。以下よりこの冒頭を優先する。

2026-09-12：[穴付き二次幾何](CURVED_MERIDIONAL_GEOMETRY.md)と[Hφ K/M](CURVED_HPHI_FORMS.md)を主ツリーへ統合・限定受入。
全境界成分/辺/セルを検証し、厳密な半径・Jacobian最小と面積/体積照合を接続した。qの静的核と軸接続uの正値を分け、全軸DOFを保持する。
標準1091件（1088合格・3skip）、関連22unit、独立72幾何/72形式と主ツリーの同照合がPASS。旧seed9モード19量はf差0、最大相対差8.882e-16。
二次多項式が幾何の正本。曲線の固有解/RF・保存/GUI・一般写像・旧版照合等と全計画は未完。親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
幾何/K/M標準36849は終了0・2251.925秒。主22unit3.374秒、主72幾何/72形式も終了0。主652source。
/tmp/integrate-curved-meridional-geometry-20260912.pyと/tmp/finalize-curved-meridional-geometry-docs-20260912.pyは実行済み。再実行しない。
次の曲線Hφ固有解/RFは/tmp/superfish-curved-hphi-rf-20260912の別候補で継続。候補の実行状態は後続の冒頭記録/実ハンドルを確認する。幾何とK/Mの受入に含めない。
全計画は未完。以下よりこの冒頭を優先する。

2026-09-12 14:42 UTC 続報：主6313da8・645source。受入済み追跡履歴の全検証は終了。
標準は幾何/K/M36849（候補646source、期待1091件、14:20 UTC開始）と曲線Hφ固有解/RF38419（候補650source、期待1095件、14:39 UTC開始）の2本が継続中。両候補を変更しない。未終了を合格に数えない。
RF候補/tmp/superfish-curved-hphi-rf-20260912は初回4unitで軸上Hφの微小非零を検出。軸を直線区間から直接逆変換する修正後4unit5.221秒、関連26unit11.146秒、独立48 FEM/144 RF/48 Case往復24.190秒がPASS。元96ファイル不変。f差7.861e-14、RF差1.022e-14、E/H差1.157e-15/3.275e-16。初回ログ5.096秒を保持する。
幾何/K/Mのintegrateとfinalize helperは/tmpへ準備済み、どちらも未実行。標準の実終了後に統合し、主関連22unitと主72幾何/72形式を新しいoutで再確認する。RFのintegrate/finalizeはまだ未準備。主ツリーへ未受入コードを混ぜない。
現在の独立・unitハンドルは全て終了済み。原則標準2本だけがlive。次のnative/CLIは調査段階。全計画は未完。以下よりこの冒頭を優先する。

2026-09-12 14:23 UTC 続報：主6313da8・645source。Hφ追跡履歴は統合・限定受入済み。標準1082件/主9unit377.836秒/主artifact139.450秒は終了0。履歴のintegrate/finalizeは実行済み。
曲線幾何とHφ K/Mの候補/tmp/superfish-curved-meridional-geometry-20260912は646source固定。追加9/関連22unit3.306秒、独立幾何72/JSON往復8.742秒、独立K/M72形式18.089秒がPASS。行列差最大4.132e-15、解析エネルギー差1.704e-13、相似差3.755e-16。初回K/M unitは旧参照だけ積分次数8で1件FAIL。同次数12へ揃えて再検証し、実装/しきい値は不変。初回ログを保持。
現時点で標準36849だけが継続中。期待1091件、未終了を合格に数えない。候補646sourceを変更しない。out/curved-meridional-geometry-development-20260912/frozen-candidate-source.tar.gzは内部バックアップ。
/tmp/integrate-curved-meridional-geometry-20260912.pyは準備済み・未実行。標準合格と2独立reportのsource一致を確認して主652sourceへ統合する。主関連22unitと必要な独立照合、文書/受入/来歴更新、ローカルコミットが残る。
幾何は二次多項式の正本。K/Mはq=rHφの定数静的核とu=Hφ/rの正値を区別し、全軸DOFを保持する。固有解/RF・native/Project/GUI・一般写像は未受入。全計画は未完。以下よりこの冒頭を優先する。

2026-09-12：[Hφ追跡の所有履歴](HPHI_TRACKING_HISTORY.md)を主ツリーへ統合・限定受入。
保存場・帯域・個別ID/ID集合の連続性を全再生し、所有コピーへの延長、CLI・worker・取消/再起動・GUIの各段階の元場取込まで接続した。
標準1082件（1079合格・3skip）、独立8チェーン/21履歴worker/39再起動/5CLI、Chrome新16/復元8/旧19、主9unit/28保存ジョブ/5CLIがPASS。元286native・6履歴は不変、PNG/CSVはbyte一致。
旧seed9モード19量はf差0、最大相対差8.882e-16。形状写像・曲線内導体・旧版照合等と全計画は未完。親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
履歴標準96229は終了0・2211.843秒、主9unit/28保存ジョブ/5CLIも終了0。主645source。
/tmp/integrate-hphi-tracking-history-20260912.py、/tmp/finalize-hphi-tracking-history-docs-20260912.py、/tmp/prepare-hphi-history-gui-restart-20260912.pyは実行済み。再実行しない。
全worker・ブラウザー・サーバーは停止済み。未終了検証なし。履歴ROOT=out/hphi-tracking-history-browser-server-20260912は元追跡/親履歴の2保存先をmoved-original-sourcesへ移動した検証状態を保持する。
固定候補の追加9unit421.101秒、独立1111.930秒、artifact142.123秒。主9unit377.836秒、主artifact139.450秒。初回unitの編集中hash検知と独立検証器の終了順序失敗を保持する。
次のP03曲線内導体は[幾何計画](CURVED_MERIDIONAL_GEOMETRY_PLAN.md)を作成し、別候補/tmp/superfish-curved-meridional-geometry-20260912で実装中、未受入。現候補643source、追加5unit0.807秒、関連18unit1.308秒、独立72幾何/JSON往復11.524秒がPASS（面積/体積相対差最大1.111e-15、座標patch最大2.532e-14）。標準回帰と本体統合はまだ。候補に大域閉路/Euler、厳密半径/Jacobian最小と全要素/境界の厳密モーメント照合を実装した。旧円板既定の契約と出力キーを保った。幾何正本は二次多項式で、円/楕円の厳密表現や曲線Hφ solveではない。
Wine本体/usr/lib/wine/wine64は存在する（wine-9.0）。既知の/tmp/superfish-wine-runtime、/home/sin/.wine-superfish、/home/sin/code/superfishはホスト読取確認でも見つからなかった。ユーザーの環境が存在しないと断定しない。追加探索の権限不足等はout/wine-runtime-additional-location-scan-20260912へ保持。旧版比較は今回未実行、コード/バイナリ内容は未参照。
以下よりこの冒頭を優先する。

2026-09-12 14:00 UTC 続報：主f8486a0・640source。追跡API/保存/CLI/GUIは限定受入済み。
履歴候補/tmp/superfish-hphi-tracking-history-20260912は639source固定。9unit67890は421.101秒、独立再実行74139は1111.930秒で終了0。独立8チェーン/21履歴・11追跡・2Project worker/39再起動/5CLIがPASS。初回の検証器終了順序の失敗を保持、製品/testsは不変。
履歴Chrome新16/復元8/旧追跡14/旧TM・TE・平面5は全PASS。全ブラウザー/サーバーは終了。artifact92787も終了済みでreport PASS（142.123秒）、28保存ジョブ・286元native・6元履歴・5CLIを照合した。
標準96229だけが継続中。期待1082件、未終了を合格に数えない。候補を変更しない。
/tmp/integrate-hphi-tracking-history-20260912.pyは未実行、標準終了後に証拠を検査して645sourceへ統合する。/tmp/verify-hphi-history-main-artifacts-20260912.pyは未実行、統合後の9unitと別出力の主artifact確認に使う。
履歴の実行済み8helperをout/hphi-tracking-history-development-20260912/operation-helpersへ保存した。再起動前準備helperは実行済み、再実行しない。全計画は未完。以下よりこの冒頭を優先する。

2026-09-12：[Hφ部分空間対応のGUI](GUI_HPHI_TRACKING.md)を主ツリーへ統合・限定受入。
個別ID/縮退ID集合、E/H対応とguard等の理由、所有した元場の取込・再比較、要求/結果・URL復元を接続した。
標準1073件（1070合格・3skip）、独立6GUI/18再起動/6CLI、Chrome新14/復元8/旧40、主2unit/33保存ジョブ/5CLIがPASS。元226native不変、PNG/CSVはbyte一致。
旧seed9モード19量はf差0、最大相対差8.882e-16。履歴・形状写像・曲線内導体等と全計画は未完。親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
追跡GUI標準4607は終了0・2098.608秒、主2unit/33ジョブ/5CLIも終了0。主640source。
/tmp/integrate-hphi-tracking-gui-20260912.pyと/tmp/finalize-hphi-tracking-gui-docs-20260912.pyは実行済み。再実行しない。
追跡GUIの全ブラウザー/サーバーは停止済み。ROOT=out/hphi-tracking-gui-browser-server-20260912には元2ジョブをmoved-original-sourcesへ移動した検証状態を保持する。
次の履歴候補/tmp/superfish-hphi-tracking-history-20260912は639source固定。追加9unit67890は421.101秒で終了0。独立初回11885は元ディレクトリ移動後のmanager.closeで終了1。管理器を先に閉じる検証器修正だけを行い、独立再実行74139、標準96229が継続中。製品/testsは不変。候補を変更しない。ブラウザーは準備中。
履歴初回8unit20853は試験中のGUI編集を検知して1件ERROR（258.420秒）。条件を変えず固定後の9unitがPASS。履歴と全計画は未受入・未完。
Wine追加探索out/wine-runtime-additional-location-scan-20260912も対象ファイル未発見だが、権限/欠落パスがある不完全探索。Wine本体は存在する。旧版コード/バイナリ内容は未参照。
以下よりこの冒頭を優先する。

2026-09-12：[Hφ部分空間対応の所有保存・worker・CLI](HPHI_TRACKING_JOBS.md)を主ツリーへ統合・限定受入。
前後のProject/nativeを所有保存し、元パス移動後も完全再生する。実行complete、数値PASS/UNVERIFIED、個別ID完了を区別する。
標準1071件（1068合格・3skip）、独立10追跡worker/34再起動/10CLI、主3unit/3CLIがPASS。旧seed9モード19量はf差0、最大相対差8.882e-16。
GUI・履歴・形状写像等と全計画は未完。親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
追跡保存標準91811は終了0・2188.351秒、主3unit/3CLIも終了0。主638source。
/tmp/integrate-hphi-tracking-jobs-20260912.pyと/tmp/finalize-hphi-tracking-jobs-docs-20260912.pyは実行済み。再実行しない。
GUI634sourceは固定、標準4607が継続中。API2unit、新Chrome14/再起動8/旧40、独立6GUI/12取込/18再起動/6CLI、artifact33ジョブ/226native/5CLIはPASS。全ブラウザー/サーバーは停止済み。
GUI統合用/tmp/integrate-hphi-tracking-gui-20260912.pyは準備済み・未実行。標準実終了後のみ6sourceを主640sourceへ統合し、主2unit/保存artifactを確認する。
次の履歴候補/tmp/superfish-hphi-tracking-history-20260912は639sourceを検証用に固定。9unit67890、独立8種チェーン11885が継続中。候補を変更しない。
履歴初回8unit20853は試験中のGUI編集を検知して1件ERROR（258.420秒）。仕様/しきい値変更ではなく、固定後の9unitで再検証する。全計画は未完。
以下よりこの冒頭を優先する。

2026-09-12：[同じ真空領域のHφ部分空間対応](HPHI_SAME_DOMAIN_TRACKING.md)を主ツリーへ統合・限定受入。
元E/Hの全方向の対応と有限比較空間・guardを確認し、縮退群はID集合として保持する。
標準1068件（1065合格・3skip）、独立36比較と縮退/順位逆転12正逆比較、主4unitがPASS。旧seed9モード19量はf差0、最大相対差8.882e-16。
有限FEM間の数値対応で、連続した変形の同一性や誤差上界は保証しない。親33課題の8受入/11進行/13他未受入/1範囲外と全計画未完を維持する。
追跡API標準64006は終了0・2284.575秒、主4unitは終了0・22.281秒。主635source。
/tmp/integrate-hphi-same-domain-tracking-20260912.pyと/tmp/finalize-hphi-same-domain-tracking-docs-20260912.pyは実行済み。再実行しない。
保存/worker/CLI候補632sourceは固定、標準91811が継続中。3unitと10worker/34再起動/10CLI独立は合格、未統合。
GUI候補/tmp/superfish-hphi-tracking-gui-20260912は現在634source。API2unitと新Chrome14は合格、独立/旧画面/再起動の進捗と稼働ハンドルは最新ツール結果を参照。
GUI server 99337、ROOT=out/hphi-tracking-gui-browser-server-20260912。候補の数値実装は不変。全計画は未完。
以下よりこの冒頭を優先する。

2026-09-12：[Hφの有限比較空間スペクトル診断](HPHI_SPECTRAL_RESOLUTION.md)を主ツリーへ統合・限定受入。
元場のL2射影とシフト逆行列のM残差から、明示した比較空間の近傍固有値の数値区間を求める。
標準1064件（1061合格・3skip）、独立24FEM/native・48全固有分解、主3unitがPASS。旧seed9モード19量はf差0、最大相対差8.882e-16。
有限空間の数値診断で、順位の同定・保証された区間・連続問題の誤差上界ではない。親33課題の8受入/11進行/13他未受入/1範囲外と全計画未完を維持する。
有限スペクトル標準71526は終了0・1984.206秒、主3unit14791も終了0・0.961秒。主632source。
/tmp/integrate-hphi-spectral-resolution-20260912.pyと/tmp/finalize-hphi-spectral-resolution-docs-20260912.pyは実行済み。再実行しない。
同領域追跡629source標準64006が継続中。追跡APIの4unit/36独立比較/12縮退正逆比較は合格済み。候補は不変、主へ未統合。
保存/worker/CLI候補/tmp/superfish-hphi-tracking-jobs-20260912は現在632source、未freeze。3unit82077は47.991秒で終了0。
独立初回69612は8比較全文書一致の後に検証器abs(list)で終了1。元出力out/hphi-tracking-jobs-independent-20260912を保持し、配列化だけを修正した。製品sourceと数値条件は不変。再実行70390（out/hphi-tracking-jobs-independent-complete-20260912）が継続中。
GUI接続はGUI_HPHI_TRACKING_PLAN.mdを準備済み。次の別候補で進める。全ブラウザー/サーバーは停止済み。元要求と全計画未完を維持し、以下よりこの冒頭を優先する。

2026-09-12：[同領域Hφの質量内積とL2射影](HPHI_MASS_PROJECTION.md)を主ツリーへ統合・限定受入。
独立P1/P2メッシュの元q/uを、全穴・軸を保つ質量内積で射影し、失った場を元要素から直接積分する。
標準1061件（1058合格・3skip）、独立48比較/144係数列、主4unitがPASS。旧seed9モード19量はf差0、最大相対差8.882e-16。
射影係数は新しい固有解ではなく、周波数/RF/IDを付与しない。親33課題の8受入/11進行/13他未受入/1範囲外と全計画未完を維持する。
質量射影標準48376は終了0・1847.094秒、主4unit4983も終了0・4.626秒。主629source。
/tmp/integrate-hphi-mass-projection-20260912.pyと/tmp/finalize-hphi-mass-projection-docs-20260912.pyは実行済み。再実行しない。
有限スペクトル626source標準71526、同領域追跡629source標準64006は継続中。各候補を変更しない。主には未統合。
追跡APIは4unit22.137秒、独立48FEM/native・36比較148.283秒、縮退/実順位逆転12FEMと正逆12比較58.292秒でPASS。縮退helper84290も終了0、source629一致。個別IDは未分離のままID集合を保持する。
次の保存/worker/CLI候補/tmp/superfish-hphi-tracking-jobs-20260912は編集中、未freeze。両元Projectとnativeを所有したHphi取込ジョブとして保存し、元パス非依存で再生する。追加3unit82077は47.991秒で終了0。独立操作検証と標準はまだ。
全ブラウザー/サーバーは停止済み。UIの丸め許容表示修正は未実施。元の完走要求と全計画未完を維持し、以下よりこの冒頭を優先する。

2026-09-12 12:05 UTC続報：主fe6379d・626source。細分差のAPI/保存/CLI/worker/GUIは限定受入済み。
質量射影623sourceの標準48376、有限スペクトル626sourceの標準71526が継続中。候補は不変、本体へ未統合。
スペクトル追加3unit0.716秒と独立24FEM/native・48全固有分解31.978秒は終了0。有限区間とスペクトル展開が一致、120native不変。製品判定は34PASS/14UNVERIFIED。
後続の同領域E/H部分空間対応は/tmp/superfish-hphi-same-domain-tracking-20260912（現在629source、未freeze）。追加4unit74020は22.137秒、独立48FEM/native・36比較39604は148.283秒で終了0。元物理Gram差3.243e-15、主内積差2.554e-15、相似差1.219e-13。
同軸の試行70888は終了0：6x12と12x6でTEMの順位が1→2へ実際に逆転し、二次元SUBSPACEを保持して個別IDを未確定にした。正式な二尺度/P1/P2同軸と軸TM011/TM020縮退検証84290が継続中（out/hphi-tracking-degeneracy-20260912）。API検証器の失敗があれば出力を保持し、実装のしきい値を緩めない。
/tmp/integrate-hphi-{mass-projection,spectral-resolution,same-domain-tracking}-20260912.pyは準備済み・未実行。先行主626→629→632→635の順で、標準実終了/seed/source照合後に各3sourceだけ統合し主unitを行う。期待標準1061/1064/1068、未終了を合格に数えない。
Wine追加探索では両既存prefixをfilename-onlyで--no-ignore検索し、対象名のregistry設定だけを確認した。SUPERFISH本体/設定登録は未特定、/opt/containerdの権限エラーで完全探索ではない。存在しないと断定しない。out/wine-runtime-location-extra-scan-20260912/report.json。旧版のコード/バイナリ内容は未参照。
GUI表の「差の減少」は丸め許容を明確化する後続表示修正が残る。全ブラウザー/サーバーは停止済み。元要求と全計画未完を維持し、以下よりこの冒頭を優先する。

2026-09-12：[Hφ細分差診断のworker・GUI](HPHI_CONVERGENCE_WORKSPACE.md)を主ツリーへ統合・限定受入。
明示Project列の実行/取消、全水準の所有保存・完全再生、要求と各量の判定理由の復元、元水準の場・全成分CSVを接続した。
標準1057件（1054合格・3skip）、独立7worker/21水準、Chrome新14/復元6/旧25操作、主2unit/26保存ジョブ/4CLIがPASS。元180nativeは不変、PNG/CSVはブラウザー・CLI・再起動後で一致した。
旧seed9モード19量はf差0、最大相対差8.882e-16。曲線内導体・部分空間追跡・旧版照合等と全計画は未完。親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
操作標準43622は終了0・1683.000秒。主2unit12339は30.119秒、主保存照合10620は25.087秒で終了0。主626source。
/tmp/integrate-hphi-convergence-workspace-20260912.pyと/tmp/finalize-hphi-convergence-workspace-docs-20260912.pyは実行済み。再実行しない。全ブラウザー/サーバーは停止済み。
次はHphi質量内積/L2射影。候補/tmp/superfish-hphi-mass-projection-20260912は623source固定、標準48376（out/validation-hphi-mass-projection-candidate-20260912）が継続中。追加4unit18770・独立48比較/144係数列44889は終了0。主には未統合。
射影のscalar場は固有解ではなく、周波数/RF/IDを付与しない。原係数不変、直接積分誤差・質量直交性・解析質量と二尺度を確認した。比較空間のスペクトル診断と部分空間追跡は未実装。
UIの「差の減少」表現は丸め許容分を明示する修正を検討中。固定候補にはまだ手を入れない。
元の完走要求と未完状態を維持する。以下の古い稼働記録よりこの冒頭を優先する。

2026-09-12：[明示Hφメッシュ列の細分差診断](HPHI_CONVERGENCE.md)のAPI・全水準保存・完全再生・CLIを主ツリーへ統合・限定受入。
元E/Hの対応、周波数近傍、最後2組のf/E/H/各RF・壁線分・複素Vaccを別々に判定する。縮退・guard不足・粗さ未達はUNVERIFIEDを保持する。
標準1055件（1052合格・3skip）、独立24系列/72FEM、細かい円筒解析4系列/12FEM、縮退3FEM、主5unit/4CLIがPASS。旧seed9モード19量はf差0、最大相対差8.882e-16。
有限メッシュ列の診断であり、連続問題の誤差上界・表面ピーク精度・永続モードIDは保証しない。親33課題の8受入/11進行/13他未受入/1範囲外と全計画の未完状態を維持する。
細分差標準65005、主5unit83160、主4CLI52449は全て終了0。主623source。
/tmp/integrate-hphi-convergence-20260912.pyと/tmp/finalize-hphi-convergence-docs-20260912.pyは実行済み。再実行しない。
操作候補/tmp/superfish-hphi-convergence-workspace-20260912は620source固定、標準43622が継続中。
新Chrome14・復元6・旧軸Hφ12/旧正半径Hφ8/旧TMTE平面5は全て終了0。保存artifact63916も終了0、26再起動ジョブ23完了/3取消、元180native不変、5ファイルDL・PNG/CSV・4CLI一致を確認した。復元画面も目視済み。
全ブラウザーと両GUIサーバーは停止・終了0。操作標準の実終了と結果確認後にだけ9source差分を統合し、主2unit/CLIを行う。表示「差の減少」は後で「増加の検査／許容内」へ明確化する。620固定候補には今は手を入れない。
元要求と未完状態を維持し、以下の古い稼働記録よりこの冒頭を優先する。

2026-09-12 11:23 UTC続報：主f91090f・618source。明示細分差の標準65005と操作拡張の標準43622が継続中。
操作620sourceは固定。新Chrome14、旧軸接続Hφ12、旧正半径Hφ8、旧TM/TE/平面5操作は全て終了0。各browserのreportはout/hphi-convergence-*-browser-20260912（新はbrowser-complete）。同じworkspaceのブラウザーを順に実行した。
GUI最初のサーバー66478は停止・終了0。再起動前180nativeファイルのhashと24トップジョブ（21完了/3取消）の状態をout/hphi-convergence-workspace-development-20260912へ保存。
同じROOT=out/hphi-convergence-workspace-browser-server-20260912でサーバーを再起動し、復元Chromeを開始（ハンドルは最新ツール結果）。まだ復元合格・artifact照合は未確認。
元要求と全計画未完を維持。以下よりこの冒頭を優先する。

2026-09-12 続報：主f91090f・618source。元E/H体積内積まで統合・限定受入済み。
明示細分差617sourceの標準65005は継続中。/tmp/integrate-hphi-convergence-20260912.pyを準備したが未実行。標準実終了後に全1055件/seed/sourceを確認して6source差分を統合し、主5unit/CLIを行う。
操作候補620sourceをfreeze済み。独立51380は終了0・260.864秒、7worker/21水準+単独同軸3水準/21取込/30再起動/2取消/7CLIがPASS。最終2unit65325は30.396秒で終了0。
新Chrome94110は終了0・14操作、旧軸接続Hφ14362は終了0・12操作。初回Chrome90782は検証器のDOM式の引用符で失敗し、製品source不変で直して再実行した。
新診断PASS/guard未検証/二穴場の画面を目視済み。表/描画の横はみ出しなし、穴は空白。
操作標準43622が継続中（out/validation-hphi-convergence-workspace-candidate-20260912、期待1057件）。候補620sourceは変更しない。
GUIサーバー66478が稼働中。ROOT=out/hphi-convergence-workspace-browser-server-20260912。旧正半径Hφブラウザーを開始済み（ハンドルは最新ツール結果）、次は旧TM/TE/平面、再起動とartifact照合。ブラウザーの同じworkspaceへの並行投入はしない。
UIの「差の減少」表示は数値の丸め許容量を含む判定である。全工程統合後の小さな表示修正では「増加の検査／許容内」等へ明確化することを検討。凍結sourceには今は手を入れない。
全計画は未完。以下の古い稼働記録より、この冒頭を優先する。

2026-09-12：[元Hφ電場・磁場の体積内積](HPHI_FIELD_OVERLAP.md)を主ツリーへ統合・限定受入。
同一真空領域の独立P1/P2メッシュで、元場と位相・規格化を保持した全3DのE/H自己・交差内積を検証した。
標準1050件（1047合格・3skip）、独立48FEM/native・48比較、解析8FEM、主4unitがPASS。旧seed9モード19量はf差0、最大相対差8.882e-16。
この物理積分から順位対応や一般の精度を宣言しない。親33課題の8受入/11進行/13他未受入/1範囲外と全計画の未完状態を維持する。
物理内積標準46867は終了0・1633.992秒、主4unit57573も終了0。主618source。
/tmp/integrate-hphi-field-overlap-20260912.pyと/tmp/finalize-hphi-field-overlap-docs-20260912.pyは実行済み。再実行しない。
明示細分差617sourceの標準65005が継続中。独立24系列/72FEM・細かい解析4系列/12FEM・縮退3FEM・5unit/4CLIは終了0。
操作候補/tmp/superfish-hphi-convergence-workspace-20260912は現在620source。新2unitは初回30.178秒、初回UI sourceのPython2unit72353も終了0。JS挿入構文エラーは修正しnode --check合格。
独立操作51380（out/hphi-convergence-workspace-independent-20260912）が継続中。実ブラウザーと操作候補標準はまだ。
元の完走要求と未完状態を維持し、以下よりこの冒頭を優先する。

2026-09-12 続報：主d43da1a・614source。共通幾何は統合・限定受入済み。物理内積612sourceの標準46867は継続中。
明示細分差617sourceをfreeze済み、標準65005（out/validation-hphi-convergence-candidate-20260912）が継続中。5unit24.543秒、24系列/72FEM202.061秒、4実CLI15.609秒は終了0。
細かい解析4系列/12FEM10787は終了0・348.806秒。n=4/8/16の両物理・両尺度が元の条件でPASS、f/E/H/全壁/軸Vacc/両R/Qの独立解析誤差も減少。初回の一壁非単調を保持し閾値は不変。
縮退解析27232も終了0・15.584秒。正確に縮退するTM011/TM020の両順位をUNVERIFIEDに保ち、最終周波数誤差2.735e-7/3.370e-7を確認した。
次の操作候補/tmp/superfish-hphi-convergence-workspace-20260912は617sourceから分離。専用Job/GUI API/要求フォームと各量の判定・水準取込表示を追加中。
新2unit92382は30.178秒でPASS。UI組込初回はonchange代入途中への挿入によりnode構文チェックが失敗した。72353のPython2unitは終了0だがブラウザー合格とは数えない。挿入箇所をstartup前へ修正し、JS2ファイルのnode --checkは終了0。実ブラウザー・最終unit・標準はまだ。
操作候補sourceは未freeze。HPHI_CONVERGENCE_WORKSPACE_PLAN.mdを参照。全計画未完、以下よりこの冒頭を優先する。

2026-09-12：[同一真空領域の元要素共通分割](MERIDIONAL_OVERLAP.md)を主ツリーへ統合・限定受入。
軸あり/なし・全PEC穴を含む厳密な同形状と各元要素の被覆、独立メッシュの重心座標・多項式積分を確認した。
標準1046件（1043合格・3skip）、独立48組/288積分、主4unitがPASS。旧seed9モード19量はf差0、最大相対差8.882e-16。
この幾何基盤から物理場の対応や収束/追跡を宣言しない。親33課題の8受入/11進行/13他未受入/1範囲外と全計画の未完状態を維持する。
幾何標準56573は終了0・1625.536秒、主4unit56309も終了0。主614source。
/tmp/integrate-meridional-overlap-20260912.pyと/tmp/finalize-meridional-overlap-docs-20260912.pyは実行済み。再実行しない。
物理内積612sourceの標準46867は継続中。本体へは未統合。
後続の明示細分差617source候補は独立24系列/72FEM、最終5unit7586（24.543秒）、4CLI79707（15.609秒）が終了0。未freeze・標準は未開始。
細かい円筒解析10787と縮退解析27232が継続中。初回の円筒一壁非単調を保持し、閾値は不変。
元の計画完走要求を維持し、候補を受入へ数えない。以下よりこの冒頭を優先する。

2026-09-12 継続中：主b82d0f2・611source。幾何標準56573と物理内積標準46867が継続中。まだ本体へ統合しない。
次の明示Hφ細分差候補は/tmp/superfish-hphi-convergence-20260912（現在617source、未freeze/未標準）。API/全水準native保存/完全再生/CLIを追加した。ジョブ/GUIは未接続。
追加3unit10.994秒、保存2unit12.741秒がPASS。その後に要求のquadrature_order固定検査を追加し、全5unitを再実行中。
独立61945は終了0、24系列/72実FEM・全native再生/4CLI・符号反転・guard不足/厳しい閾値・二尺度が202.061秒でPASS。相似差最大3.120e-13。out/hphi-convergence-independent-20260912。
最初の解析58383は終了1：Lの長い円筒の外壁1線分のみ差が1.262e-6→3.031e-6と増え、製品は正しくUNVERIFIED。検証器の全系列PASSという予想が誤り。初回出力out/hphi-convergence-analytic-20260912を保持し、閾値を変更しない。
より細かいn=4/8/16の解析4系列/12FEM/native10787が継続中。out/hphi-convergence-analytic-finer-20260912。独立参照の親セル探索は256区画ずつに分けてメモリを制限し、元の物理多項式を評価する。
/tmp/verify-hphi-convergence-cli-20260912.pyの4CLIと最終5unitも継続中（ハンドルは最新ツール結果）。独立入力と出力の完全一致を確認する。
候補ソースは主の受入へ数えず、全33課題の完走要求と未完状態を維持する。以下よりこの冒頭を優先する。

2026-09-12 10:35 UTC続報：主b82d0f2、611source。軸接続HφのProject/GUI/独立Studyは統合・限定受入済み。
共通幾何608sourceの標準56573が継続中。/tmp/integrate-meridional-overlap-20260912.pyは準備済み・未実行。実終了後にsource/seedを照合し3sourceを統合、主4unitを検証して受入文書を更新する。
後続の物理内積候補/tmp/superfish-hphi-field-overlap-20260912は612source固定。新4unitは2.057秒、独立48FEM/native・48比較は13.826秒（3336終了0、参照差1.797e-14・相似差2.407e-13）、解析8FEM/4細分比較は2.901秒（84360終了0）でPASS。
物理内積標準46867が継続中（out/validation-hphi-field-overlap-candidate-20260912）。幾何/物理候補は変更しない。
48比較のsource611に、解析検証スクリプト1本のみ後から追加して612となった。製品・tests・独立検証器の全byteは不変。archive.jsonへ差分を記録済み。標準・解析は612source。
未完了の標準を合格に数えない。場の積分基盤は順位対応/縮退/収束判定ではなく、全計画は未完。
以下の旧稼働記録より、この冒頭を優先する。

2026-09-12：[軸接続HφのProject・表示・独立Study](AXIS_HPHI_WORKSPACE.md)を主ツリーへ統合・限定受入。
軸区間・位相原点・betaの編集/復元、実worker・保存取込/取消/再起動、穴を除いた場と全18成分SIプローブ、複素Vacc/両R/Qを接続した。
標準1042件（1039合格・3skip）、独立28FEM点、実Chrome新12/復元6/旧Hφ8/旧TMTE平面5操作、主4unit/5CLIがPASS。
既存seed9モード19量はf差0、最大相対差8.882e-16。ベンチマーク不変。
独立Studyの順位は追跡IDではない。曲線穴・収束/追跡・旧版照合等とP03/O02・全計画は未完。親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
Workspace標準63850は終了0・1635.683秒、主4unit24200・5CLI47913も終了0。主611source。
/tmp/integrate-axis-workspace-20260912.pyと/tmp/finalize-axis-workspace-docs-20260912.pyは実行済み。再実行しない。
Workspaceの全ブラウザー・サーバー・独立FEM・保存検証は終了済み。
次は[同一真空領域の共通積分幾何](HPHI_OVERLAP_PLAN.md)。別候補/tmp/superfish-meridional-overlap-20260912へ元要素の厳密交差と穴を除いた全被覆だけを追加した。
追加4unitは0.947秒、独立48幾何/288多項式積分は6.327秒（97940終了0、最大差9.992e-16）でPASS。
608source固定と内部作業archiveはout/meridional-overlap-development-20260912。標準56573（out/validation-meridional-overlap-candidate-20260912）が継続中。本体統合はまだ。FEM対応・収束/追跡は含めない。
全計画は未完。以下の古い稼働記録は、この冒頭を優先する。

2026-09-12：[軸区間・PEC穴を持つ真空HφのFEM・保存](AXIS_HPHI_RF.md)を主ツリーへ統合・限定受入。
正則u=Hφ/rのP1/P2・全壁RF・明示した複素軸Vacc/両R/Q・専用native/CLIを接続した。
標準1038件（1035合格・3skip）、独立16FEM/native、12幾何/72モード、凹形4FEM/native、主8unit/6CLIがPASS。
既存seed9モード19量はf差0、最大相対差8.882e-16。ベンチマーク不変。
Project/GUI/Study接続・曲線穴等とP03/O02・全計画は継続し、親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
RF標準3210は終了0・1749.380秒、主8unit41549・6CLI52485も終了0。主607source。
Workspace標準63850のみ継続中。全ブラウザー・サーバー・独立FEM・保存検証は終了済み。
605sourceのWorkspaceは新12/復元6/旧Hφ8/旧TMTE平面5の実Chrome、27ジョブ（25完了/2取消）、元140native不変、4CLIとCSV/PNG byte一致までPASS。
/tmp/integrate-axis-workspace-20260912.pyは未実行。標準実終了後、605候補と607主source・seedを確認してから15差分sourceを統合する。
全計画は未完。

以下の古い稼働記録は、この冒頭を優先する。

2026-09-12 進捗続報：主基盤コミット42e4d38・599source。基盤標準9082（1030件1853.617秒）と主4unitは終了0。
RF候補601source：8unit、独立16FEM/native（28696終了0・1060.310秒・相似最大1.033e-13）、12幾何/72モード（65489終了0・2.394秒）がPASS。
RF標準3210は継続中。out/validation-axis-rf-candidate-20260912。
Workspace候補605source：4unit、Hφ関連51unit（50合格/HTTPskip1）、4Project/12Study/28FEM/48再起動/8CLI（11296終了0・50.348秒）、Chrome新12/再起動6/旧Hφ8/既存TMTE平面5がPASS。
Workspace標準63850（out/validation-axis-workspace-candidate-20260912）は継続中。605sourceは固定。
ブラウザーは全終了。最初のサーバー58973は終了0、再起動サーバー4936へstopを置いたので実終了を確認する。
ブラウザー初回の15秒待機、旧Hφの前workspace参照、並行投入でTM検証器が別Hφ行を選んだ失敗を保持。いずれも製品source不変で、待機/パス修正と単独再実行で合格した。
新RFの最終P2解析対象の図54837/27655が継続中。out/axis-rf-analytic-plots-20260912。図はまだ目視していない。
RF統合用/tmp/integrate-axis-rf-20260912.pyは未実行。標準実終了後に601source/旧seedと599主sourceを確認して統合する。
Workspaceの統合はRF受入後。独立報告・ブラウザー・再起動前140nativeファイルを照合し、主で新unit/CLIを確認してから受入する。
全33課題の完走要求と未完状態を維持する。P03/O02と全計画を完了へ変更しない。

以下は各工程の記録。稼働ハンドルはこの冒頭を優先する。

2026-09-12：[軸区間・PEC穴の幾何とK/M基盤](AXIS_CONNECTED_MESH.md)を限定受入。
軸/PECの分離、元境界の厳密被覆、穴を除いた多項式モーメント、軸自由度の保持・正スペクトル/Ritzを確認した。
標準1030件（1027合格・3skip）、主4unit（0.234秒）がPASS。
seed9モード19量は周波数差0、最大相対差8.882e-16。既存ベンチマークは不変。
RF/保存/GUIは後続工程で、P03/O02と全計画・親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
標準9082は終了0、1853.617秒。主4unitも終了0で、主599sourceを照合した。
RF/Workspace候補の未終了ハンドルは以下の記録を参照し、実終了を確認してから受入する。

以下は基盤統合前の工程記録。現在の主ソースと基盤受入はこの冒頭を優先する。

2026-09-12 継続中：軸接続メッシュ基盤の固定候補593source、標準9082（out/validation-axis-connected-mesh-candidate-20260912）は未終了。
製品RF候補/tmp/superfish-axis-rf-20260912を601sourceで固定。8unit（2.909秒）、一穴/二穴×P1/P2の8FEM診断（236.240秒）は合格。
固定ゲートのf/E/H/全PEC線分損失/複素Vacc/両R/Qと実細分での減少を確認したが、診断は一尺度・nativeなしで受入にはしない。
RF標準3210（out/validation-axis-rf-candidate-20260912）、二尺度16FEM/native独立28696（out/axis-rf-independent-20260912）が継続中。
601sourceと内部作業用archiveはout/axis-rf-development-20260912。未終了検証を合格に数えず、候補sourceを変更しない。
後続Project/表示/GUI/独立Study接続はAXIS_HPHI_WORKSPACE_PLAN.md、別コピー/tmp/superfish-axis-workspace-20260912で進める。
主ソースはまだStudyの051845c・595sourceのまま。全33課題の完走要求と未完状態を維持する。

以下の開始時点より、この冒頭の稼働ハンドルを優先する。

2026-09-12：[正半径Hφの独立Study](HPHI_STUDY.md)を主ツリーへ統合・限定受入。
尺度・全3Dエネルギー・壁導電率・円筒寸法の掃引、全点native/CLI・実worker・GUI・保存再起動を接続した。
標準1026件（1023合格・3skip）、独立18worker/36FEM/18CLI、Chrome新9/復元3/既存13操作、主12unit/4CLIがPASS。
順位は独立スペクトルで追跡未実施。収束・追跡等、P03/O02と全計画は継続し、親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
Study標準12034は終了0、1026件・1772.387秒。主12unit/4CLIも終了0。固定589sourceと主595sourceの同一性を確認。
GUI/Studyの全計算・Chrome・ローカルサーバーは終了済み。HPHI_STUDY.mdに契約と証拠を記載した。

次はAXIS_CONNECTED_HOLES_PLAN.md。隔離候補/tmp/superfish-axis-holes-20260912には軸区間/PEC穴の幾何・canonical P1/P2 K/Mだけを追加した。
4unit（0.240秒）、4解析恒等式、18の解析磁場対応による試作FEMまで確認。製品Case/solve/native/CLI、全壁RFは未完。幾何・行列基盤の標準回帰9082は継続中。
source593と作業アーカイブはout/axis-hole-reference-20260912/prototype-source-sha256.json、mesh-form-prototype-source.tar.gz。
周波数最近傍が別の場を選ぶ反例はout/axis-hole-spectrum-prototype-20260912へ保持。対応版はout/axis-hole-field-matched-prototype-20260912（62253終了0、143.046秒）。
最終水準は一穴/二穴ともf/E/H/Vaccが計画の固定ゲート内だが、未確認の全壁RF・保存・全回帰を受入扱いしない。
固定593sourceの標準はout/validation-axis-connected-mesh-candidate-20260912、ログはout/axis-connected-mesh-development-20260912/standard.log。
その候補は変更せず、製品RF候補を/tmp/superfish-axis-rf-20260912へ別コピーした。
主ツリーへ軸穴候補はまだ統合していない。全33課題の完走要求と未完状態を維持する。

以下は以前の工程履歴。稼働/完了は冒頭の記録を優先する。

2026-09-12：[正半径Hφの表示・GUI](GUI_HPHI.md)を主ツリーへ統合・限定受入。
元P1/P2の符号付き全場、穴を除いた描画、境界/線分壁損失、Project/実worker/取込/保存/再起動を接続した。
標準1014件（1011合格・3skip）、独立8件/16CLI、Chrome新9/既存5操作、統合後7unitと2CLIがPASS。
任意NGSolveの2skipと、別の許可実行で合格したローカルHTTPの環境skip 1件を区別する。
Study・追跡等とP03/O02・全計画は継続。親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
GUI標準18403は終了0、1014件・1812.958秒。主7unit（実HTTP含む）・2CLIも終了0、587sourceを照合済み。
前の標準65753は終了143で中断し、結果なし・子プロセスなしを確認。中断理由は未特定で、受入には使わない。
全GUI/ブラウザーサーバーは終了。GUI_HPHI.mdに契約と証拠を記載した。

Study候補/tmp/superfish-hphi-study-20260912は589source固定、標準ハンドル12034が継続中。out/validation-hphi-study-candidate-20260912。
12unit・18worker/36FEM/18CLI/36再起動、Chrome新9/復元3/旧Hφ8/既存TMTE平面5、保存14完了/2取消と元30ファイル不変がPASS。
HPHI_STUDY.mdは候補の契約。標準の実終了と589source/seedを確認してから、/tmp/integrate-verified-hphi-candidate-20260912.py studyで14差分sourceを統合できる。
GUI/Studyの固定sourceアーカイブは各out/*-development-20260912/frozen-candidate-source.tar.gzとarchive.json。配布用パッケージではない。

次の軸穴試作/tmp/superfish-axis-holes-20260912は幾何・canonical P1/P2 K/Mだけを追加し、4unit合格。製品Case/solve/native/CLI未実装。
AXIS_CONNECTED_HOLES_PLAN.md、out/axis-hole-reference-20260912に4解析恒等式。周波数最近傍が別場を選ぶ反例をout/axis-hole-spectrum-prototype-20260912へ保持。
磁場の全域内積で対象を選ぶ18試作FEMは62253終了0・143.046秒。out/axis-hole-field-matched-prototype-20260912。
最終水準のf/E/H/Vaccは固定ゲート内だが、全壁RF・保存・全回帰は未検証で受入にはしない。

Wine 9.0は/usr/lib/wine/wine64で再確認済み。ファイル名だけの拡張検索でもSUPERFISH本体/prefixは未特定。既存desktopは旧/tmp保存先を指す。
検索は一部読めない場所があり全ファイルの不存在証明ではない。out/wine-runtime-location-scan-20260912。旧版の新しい実行・バイナリ内容閲覧はなし。
全33課題の完走要求を維持する。goal toolは以前blockedを返したが、進行可能な独立工程を続ける。

以下は以前の工程履歴。現在の稼働ハンドルは冒頭を優先する。

2026-09-12：[正半径HφのProject・ローカルジョブ](HPHI_JOBS.md)を限定受入。
閉同軸円筒/一般断面の専用入力、実worker、直接/管理済み取込、中止・再起動・完全保存検証を接続した。
標準1007件（1005合格・2skip）、独立8worker/16取込/再起動24件、統合後8unit・2例題CLIがPASS。
GUI・Study・追跡等とP03/O02・全計画は継続。親33課題の8受入/11進行/13他未受入/1範囲外を維持する。
標準65939は終了0。候補574sourceと主580source（不変egg-info 6件を含む）を照合し、主8unit/2CLIも合格した。
全Project/Job検証プロセスは終了。証拠はHPHI_JOBS.mdとout/validation-hphi-jobs-candidate-20260912/seed_regression.json。
GUI候補は/tmp/superfish-hphi-gui-20260912。表示3unit・GUI4unit（許可された実HTTP）が合格。
実ブラウザー初回out/hphi-gui-browser-first-20260912は7操作合格後、ページ遷移直後に検証器が未定義selectedを読んで失敗。ログを保持し、ロード待ちを修正する。ハンドル57689の終了を確認する。ローカルサーバー15360はout/hphi-gui-browser-server-20260912。
終了にはサーバーフォルダーへstopファイルを置き、15360をpollする。ブラウザー・全体回帰の未確認部分を受入扱いしない。
Wine 9.0は/usr/lib/wine/wine64で起動確認済み。旧desktopのprefix保存先は消失、本体/prefixの現存パスは未特定。
全33課題の完走要求は継続。goal toolはblockedを返したが、この工程は進行できるので再度blockedへ更新しない。

2026-09-12：[正半径の一般断面・複数PEC穴のHφ FEM](HPHI_MESH_RF.md)を限定受入。
strictな外周/穴/接続検査、P1/P2、全壁損失、専用native・CLI・SIプローブを接続した。
追加12unit、独立16FEM/native、番号入替/鏡映12FEM・72モード比較、同梱3例題9CLI、旧円筒native16件の再生を確認。
標準999件（997合格・2skip）とseed9モード19量がPASS。f差0e+00、最大相対差8.882e-16。
軸接続の穴付き領域・曲線内導体・Project/Job/GUI等、P03と全計画は未完。
主標準38338は終了0、999件・2002.472秒。独立55923、例題56656、追加幾何10586も終了0。全573source一致。
証拠はHPHI_MESH_RF.mdとout/validation-hphi-mesh-20260912/seed_regression.json。
2026-09-12：[閉じた真空同軸円筒のm=0 Hφ族](COAXIAL_RF.md)を限定受入。
q=rHφのP1/P2 FEM、静的循環零空間の除外、全E/H・内外導体/両端板損失、専用native/CLI・SIプローブを接続した。
追加8unit、独立16FEM/native・TEM/TMの64モード比較、主例題2件の6CLI操作、全体987件（985合格・2skip）でPASS。
seed9モード19量はf差0e+00・最大相対差8.882e-16。
一般内導体・複数断面境界・Project/Job/GUI・旧版照合等、親P03と全計画は未完。
標準987件は1626.390秒、独立16件は66.247秒、主8unitは1.968秒。全実行は終了済み。
標準26364・旧標準19541・独立56227・主unit87822・例題36857は完了。関連サーバーや旧版実行はない。
固定一時コピーの全標準と主ツリー556sourceの同一性、旧6egg-info不変を記録し、主ツリーでも新unit/例題を再実行した。
証拠はCOAXIAL_RF.mdとout/validation-coaxial-frozen-candidate-20260912/seed_regression.json。旧ベンチマーク不変。
親33課題は8受入/11進行/13他未受入/1範囲外へ更新。P03を進行へ移し、完了には数えない。
次はCOAXIAL_GENERAL_MESH_PLAN.md。穴付き矩形断面のq=cos(3πz/L)という独立解析例を用意し、積分恒等式だけ確認済み。
一般メッシュ/複数境界、Project/Job/GUI、旧版照合は未実装・未確認。全計画goalはactiveのまま。
ユーザーはこのマシンにも実行環境があると回答。/usr/lib/wine/wine64でWine 9.0の起動を確認した。SUPERFISHのdesktop設定は以前の/tmp/superfish-wine-runtime/prefix-readyを指し、そのパスは現在見つからない。現存SUPERFISH本体と対応prefixは引き続き所在確認。旧版ソース/バイナリの内容閲覧・複製は禁止のまま。

以下は各工程完了時の履歴。現在の検証結果・環境確認・次工程は冒頭を優先する。

2026-09-12 O01運用修正：ジョブ管理/GUIの起動失敗・中断時にもOSロックを解放する。
既存ResourceWarningはtest_gui_mode_trackingのクラスcleanup漏れと特定し、5件だけの再現ログを保持して修正した。
別途、壊れたjob.json・復旧書込失敗/中断・GUIキャッシュ競合・ブラウザー失敗でロックが残る先行反例を確認。
追加6件を含む関連29unitが1.443秒・警告なしでPASS。実HTTP6確認もPASSで、全サーバー終了済み。
契約・制限は[JOB_STARTUP_CLEANUP.md](JOB_STARTUP_CLEANUP.md)、証拠はout/job-startup-cleanup-20260912。
数値実装は下記dabc302と同じ。非数値修正後に全体979件を再実行したとは主張しない。
直前のP02版7はローカルコミットdabc302として完了。全計画goalと親33課題の未完状態を維持する。
C00/K10は旧版実行環境を確認したが、以前の/tmp/superfish-wine-runtime、/usr/bin/wine、/usr/bin/Xvfbが存在しない。
PATHのwine/wine64/Xvfbも未検出。/home/sin/.wineはあるが既知のdrive_c/LANLはなく、ソース/バイナリ内容は未閲覧。
既存Wine実行ファイルとWINEPREFIXの別保存先をユーザーへ非同期で質問済み。新しい旧版実行や環境構築はしていない。
この確認待ちだけで全計画goalをblockedにしない。独立した未完課題は継続できる。

2026-09-12 P02厳密アフィン追跡版7を接続・限定受入。
正逆の元電場移送・有限細分診断、完全保存再生、CLI/実worker/GUI/所有履歴を接続した。
追加9unit（83.359秒）、独立16条件32FEM/native・正逆32対応（1088.988秒）、
Chrome新版10/旧版9操作、管理器再起動後の保存14ジョブ、旧版1〜6保存全文再生がPASS。
標準973件（971合格・2skip、1577.700秒）、convergenceとseed9モード19量がPASS。
f差0e+00、最大相対差8.882e-16。主ツリーの553 sourceを固定・照合した。
独立コピーとの差5ファイルはGUI/検証/説明だけで、数値実装・検証器の同一性を独立source比較に記録。
最終契約・失敗履歴は[PLANAR_EXACT_AFFINE_TRACKING.md](PLANAR_EXACT_AFFINE_TRACKING.md)。
証拠はout/planar-exact-affine-tracking-20260912、標準はout/validation-planar-exact-affine-tracking-20260912。
初回BLAS未固定標準は中断記録。最終受入は1スレッド固定。既存の `.manager.lock` のResourceWarningは最終標準でも観測し、未解決として保持する。
この区切りの全計算・GUIは終了。ユーザーの全計画完走goalはactiveのままで、完了にしない。
親33課題は8受入/10進行/14未受入/1範囲外を維持。一般の丸めた境界・非線形変形・曲線、親P02は未完。
次の候補はC00/K10の旧版Cartesian実行・成分/単位長量の仕様照合。C00_TE_COMPLEMENTARY_PLAN.mdにR25の既読要約があるが、
参照した/tmp/superfish-wine-runtime/input-spec/SFCODES.txtは現在存在せず、資料・実行環境の再確認が必要。
新たな参照閲覧・旧版実行は今回行っていない。旧版ソース/バイナリを閲覧・複製しない契約を維持する。
以下の古い開始点は各実行時点の履歴として読む。

2026-09-12 P02：境界分割独立の厳密アフィン共通分割APIを限定受入。
`planar_tracking_exact_affine.exact_affine_polygon_overlay` は、写像/逆写像・BVH・交差を有理数で評価し、
元要素ごとの厳密面積被覆を確認する。反射でも元の要素番号/重心座標列を保持し、正逆とも現在xy面積で積分する。
追加8unit（1.414秒）、独立16条件32FEM/32native（158.862秒）、標準964件（962合格・2skip、1523.747秒）でPASS。
P2最終最大はf 4.506e-7、E L2 3.583e-4、H L2 9.495e-4、G 2.394e-3、Q 2.395e-3、壁損失2.401e-3、Gram 7.531e-8。
二尺度相似最大5.029e-14。seed9モード19量はf差0・最大相対差8.882e-16。標準/独立551source一致、旧548sourceは全て不変。
証拠は `out/exact-affine-overlay-20260912` と `out/validation-exact-affine-overlay-20260912`。
契約・反例・失敗履歴は[PLANAR_EXACT_AFFINE_OVERLAY.md](PLANAR_EXACT_AFFINE_OVERLAY.md)。
初回標準はソース追加中の検出と既存RF最適化replay不一致で2 error。ソース固定/OPENBLAS_NUM_THREADS=1の最終標準は合格し、RFジョブ個別4件も合格（206.014秒）。未固定環境の不一致原因と既存.manager.lock警告は未解決として保持する。
既存追跡版1〜6の意味は変更していない。次工程は厳密写像の専用要求/結果版、場の正逆移送・有限細分診断、全保存再検証、worker/CLI/GUI/所有履歴への接続。一般の丸めた境界・非線形/曲線・親P02と全計画は未完。
この作業環境は `/home/sin/code/agent/reserch/superfish-ng`。旧記載の `/home/sin/code/superfish` は存在せず、移動/入れ子作成は行っていない。Pythonは `.venv/bin/python`（3.12.3、NumPy 2.5.2、SciPy 1.18.1）を使った。

2026-09-11 可逆アフィン＋独立内部メッシュの合成追跡（要求/結果版6）の最終状態：明示多角形の厳密に可逆な宣言アフィン写像（せん断・異方尺度・鏡映・一般成分を含む）と独立内部メッシュの元電場追跡を限定受入。要求/結果版6、余因子 `adj(E)=det(E)E^{-1}` によるTE移送、向き反転時の境界・三角形正規化とbarycentric復元、正逆の元電場積分、完全保存再生・CLI/実worker/GUI・所有履歴を接続した。標準956件（954合格、2skip、1513.289秒）、追加9unit（26.041秒）、独立解析26条件（反射8・異方8・順位交差2・せん断8、75.754秒、解析恒等残差最大2.221e-16、P2最終FEM Gram最大1.038e-4・周波数3.335e-4、P1最終cross最大4.669e-3、異方P2周波数8.785e-5、せん断P2移送2.908e-16、モーメント1.554e-15）、6拒否、実Chrome9操作（外部HTTP 0、source不変）を確認。証拠は`out/planar-affine-remesh-independent-20260911`、`out/browser-planar-affine-remesh-20260911`、標準`out/validation-planar-affine-remesh-final-20260911`。seed9モード19量は周波数差0・最大相対差8.882e-16。境界密度独立の一般合成・非線形変形・異なる多角形形状・曲線・親P02と全計画は未完。契約はPLANAR_AFFINE_REMESH_TRACKING.md、経過はPLANAR_AFFINE_REMESH_TRACKING_PLAN.md。既存`.manager.lock`のResourceWarningは未解決として保持する。

2026-09-11 相似変換＋独立内部メッシュの合成追跡（要求/結果版5）の最終状態：宣言相似変換で前の境界節点列を厳密に写し、内部の節点・対角線・接続だけを独立に再メッシュした元電場追跡を限定受入。正逆の元電場積分、完全保存再生・CLI/実worker/GUI・所有履歴を接続した。標準947件（945合格、2skip、1514.373秒）、追加8unit、独立解析16条件、Chrome9操作を確認。最初の「前のメッシュ全体を変換して厳密被覆」案は境界節点のbinary64丸めでスリヴァーを残すため拒否し、その反例を`out/planar-similarity-remesh-boundary-sliver-20260911`へ保持した。せん断・鏡映・異方尺度は[可逆アフィン合成追跡](PLANAR_AFFINE_REMESH_TRACKING.md)（版6）として限定受入済み。境界密度を独立に選ぶ一般合成・非線形変形・曲線・親P02と全計画は未完。証拠は`out/planar-similarity-remesh-independent-final-20260911`（70.0秒）、`out/browser-planar-similarity-remesh-20260911`（9項目、外部HTTP 0）、標準`out/validation-planar-similarity-remesh-final-20260911`。契約はPLANAR_SIMILARITY_REMESH_TRACKING.md、経過はPLANAR_SIMILARITY_REMESH_TRACKING_PLAN.md。既存`.manager.lock`のResourceWarningは未解決として保持する。

2026-09-10 セミナーレポート可視化追補：ユーザー指定のローカル納品フォルダに05-visualizationsを追加。原本不変、各冊22場図を実験節へ移動し、保存CSV/JSONから13新図。HTML各42画像、251リンク、67入力hash、PDF本家49/NG39ページを確認。標準unittestは未インストール環境の子worker import失敗で中断（合格扱いせず）、PYTHONPATHを明示した該当2workerは90.130秒PASS。仕様・再生成・検証はSEMINAR_VISUALIZATIONS.md。数値コード・ベンチマーク不変、納品資料はソースコミット対象外。

独立再メッシュ版4の最終状態（以下の実行中メモを置き換える）：同じ多角形の独立メッシュ間の元電場追跡を限定受入。要求/結果版4、厳密な領域・各元要素面積・候補予算、全保存再生・CLI/実worker/GUI・所有履歴を接続した。標準939件（937合格、2skip、1486.136秒）、追加7unit、独立32 FEM/32対応、混次数16比較、幾何24条件、解析16条件、縮退16 FEM、実追跡32/履歴16worker、中止/再起動、Chrome96操作とGUI63保存ジョブを確認。旧版1〜3・38履歴・TM/TE/平面回帰と538sourceも合格。形状変更との合成・曲線・親P02と全計画は未完。 全実行・GUIは終了、最終outのverify_completion.py/seed_regression.jsonで538sourceと全保存hashを照合した。ユーザーの「切りのいいところでcommit」に従い、この実装と受入記録を一つのコミットにまとめる。標準unittest1486.136秒/command1486.520秒、convergence0.256秒。既存.manager.lock ResourceWarningは未解決として記録。新しい課題への実装着手はこの区切りに含めていない。全計画のgoalは未完のまま維持する。

コミット前の最終待機: 実worker7484は976.017秒で終了0。32追跡・16履歴・中止2・再起動完全再生・CLI・改変拒否を全て確認。残る実行は標準14872だけ。GUI等はすべて終了。標準終了後、最終outのverify_completion.py→finalize_docs.py、diff/リンク確認、ローカルコミットを行う。ユーザーは今回の区切りでのcommitを明示依頼済み。538source固定。

ユーザーの「切りのいいところでcommit」に対応し、独立再メッシュ版4を今回の区切りにする。次の機能へ進まず、全検証後に一つのローカルコミットを作る。GUI保存73887は63件（8履歴）で79.687秒PASS、候補費用72734とnative32件28662も終了0。現時点の残実行は標準14872と実worker最終再生7484。workerは32追跡/16履歴の全16系列と中止2件の状態まで確認済み。out/validation-planar-remesh-fixed-final-20260910にverify_completion.pyとfinalize_docs.pyを準備済み、まだ未実行。538sourceは固定。

再メッシュ検証続報: 旧Chrome65872は78項目、新Chrome修正版51436は8項目、再起動87830は10項目で終了0。GUI7035と再起動58484は終了済み。保存全63想定ジョブの全再生はout/planar-remesh-gui-persistence-20260910で実行中。旧版3の32pair/16history＋旧22history（計70保存）の全再生42254、旧native/矩形/Study/細分/追跡回帰91005、追加縮退16FEM39318、混次数16比較86062、CLI履歴31875は終了0。幾何候補費用72734/out/planar-remesh-candidate-cost-20260910も測定中。標準14872、実32追跡/16履歴7484は継続。新コードとtests/scripts/examplesは538source固定。

独立再メッシュの検証切替: 開発Chrome55932はメッシュ生成の端点(.2*6/6)が外周.2と丸め不一致で拒否され終了1。scriptを.2*(i/n)へ修正、失敗out保持。標準52040/子1936705をSIGINTで止めて終了254、out/validation-planar-remesh-development-20260910に中断ログ。修正後の固定538source標準は14872/out/validation-planar-remesh-fixed-final-20260910。新旧59unitは160.779秒で終了0、旧独立32FEM/32対応4520は100.896秒PASS、修正後3271/out/planar-remesh-fixed-independent-20260910も終了0。旧回帰40149はscript hash変更検出で終了1、修正後91005/out/planar-remesh-fixed-regressions-20260910を実行中。GUI旧回帰65872はpackage src不変で継続中、終了後にrun-fixed.pyで新Chromeを同じworkspaceで再実行する（同じworkspaceのブラウザーは並走させない）。実worker7484/out/planar-remesh-workflow-20260910、旧版3の32pair/16historyと旧22history全再生42254/out/planar-remesh-old-similarity-replay-20260910を実行中。独立幾何24条件54157と解析三角形16条件は終了0。

独立再メッシュ追跡版4の実装中（基準 ddb585d）。前回は相似写像版3をコミットまで完了した進捗。新PolygonRemeshMapping/元要素交差・BVH候補予算・両側各要素の厳密面積を追加、要求/結果版4・保存/worker/CLI・GUI・履歴へ接続。追加7unitは13.865秒で合格。新旧追跡 suite session47460、独立32FEM/32対応 session4520（out/planar-remesh-independent-development-20260910）、全体標準 session52040（out/validation-planar-remesh-development-20260910）を実行中。GUI session7035（out/planar-remesh-gui-development-20260910）、新Chrome session55932（out/browser-planar-remesh-development-20260910）。538sourceを固定。まだ受入/コミットしていない。最初の幾何unitは存在しない外周節点(.5)を宣言したfixtureで失敗、実在する1/3へ直し既存mesh契約を保持。以下の旧版の最終状態と区別する。

相似写像版3の最終状態（下記の実行中メモを置き換える）：明示多角形の正の尺度・回転・SI平行移動による追跡を限定受入。要求/結果版3、正逆の元電場積分、完全保存再生・CLI/実worker/GUI・所有履歴を接続した。標準932件（930合格、2skip、1447.175秒）、追加9unit、独立64 FEM/128対応、解析32条件、縮退16 FEM、実追跡32/履歴16worker、中止/再起動、Chrome87操作とGUI56保存ジョブを確認。旧版追跡・22履歴・TM/TE/平面数値回帰と535sourceも合格。一般変形・親P02と全計画は未完。 全検証とGUIは終了。最終outのverify_completion.py/seed_regression.jsonで535sourceと保存hashを照合済み。次は[同じ多角形の独立再メッシュ](PLANAR_REMESH_TRACKING_PLAN.md)を進める。隔離候補8FEM・全元要素面積一致はあるが、新版要求/製品/保存/worker/GUIは未実装。親P02と一般変形等をこの相似写像の受入で完了に数えない。標準終了時の既存.manager.lock ResourceWarningは未解決として保存。

相似写像版3: 実worker workflow41291は終了0、追跡32/履歴16・中止2・再起動全再生・CLI・改変拒否が合格。GUI保存56件（6履歴）と再起動取込、CLIの新写像履歴の作成/追加/再生、72native再生も終了0。残る実行は標準57454だけ。out/validation-planar-similarity-final-20260910のverify_completion.pyとfinalize_docs.pyは未実行、標準終了後に実行する。次課題の独立再メッシュはdocs/PLANAR_REMESH_TRACKING_PLAN.mdに反例8FEMと元要素面積の隔離候補を記録、製品未接続。535sourceは引き続き固定。

相似写像版3の進捗続報: 最終64 FEM / 128対応281.423秒、縮退16 FEM110.119秒、解析三角形32条件2.196秒、旧native/矩形/Study/細分/保存と旧22履歴の回帰が終了0。Chrome78項目と再起動後9項目が合格、GUI session34245/40943は終了済み。全体標準57454、実worker workflow41291（out/planar-similarity-final-workflow-20260910）、GUI保存再検証を継続中。workflow補助driverの結果キー参照誤りは隔離失敗outに保持し、実装の結果版キーresult_versionに修正して再実行。製品535sourceは固定。

相似写像版3の最終検証中（2026-09-10）。基準 a2cc64a、追加9 unit は21.637秒で合格。製品535sourceを固定し、標準 session 57454 / out/validation-planar-similarity-final-20260910、64 FEM / 128対応 session 95769 / out/planar-similarity-final-independent-20260910、縮退16 FEM session 82622 / out/planar-similarity-final-subspaces-20260910 を実行中。最終GUI session 34245 / out/planar-similarity-final-gui-20260910。まだ限定受入ではない。最初のブラウザー形状拒否と成分式による完全再構築の修正、失敗出力は PLANAR_SIMILARITY_TRACKING_PLAN.md を参照。全計画は継続中。

# ローカルCodexへの引継ぎ

## 2026-09-10 平面追跡履歴の限定受入

平面モード追跡の保存履歴を限定受入。保存場・帯域・ID集合の連続性を全再検証し、未解決・段階上限での停止、所有コピーへの追加、CLI/実worker/GUIを接続した。標準923件（921合格、2skip、1417.539秒）、追加15unit、独立18履歴worker、Chrome76操作、GUI47保存ジョブと再起動後取込を確認。532sourceと旧TM/TE/平面の保存・周波数/RF回帰も合格。親P02と全計画は未完。

正本は[仕様・証拠](PLANAR_TRACKING_HISTORY.md)と[開発経過](PLANAR_TRACKING_HISTORY_PLAN.md)。標準outは`out/validation-planar-history-budget-fixed-final-20260910`。verify_completion.py/seed_regression.jsonでTM seed9モード19量（f差0.000e+00、RF最大8.882e-16）と全532sourceを確認した。旧未完標準54211は段階予算反例の修正前に停止・終了254。未完標準を合格に数えていない。

最終実行32771、独立67986、旧回帰6457、Chrome75771、保存3692、再起動82278、取込89097は完了。GUI8524/76544は停止済み。成果物を上書きしない。標準923件のうち2件はskip、hosted CIは観測していない。終了時の既存.manager.lock ResourceWarningは残る。親課題集計8受入/10進行/14未受入/1範囲外=33は維持する。

次工程はPLANAR_SIMILARITY_TRACKING_PLAN.md。主ツリーの回転/平行移動対応はまだない。out/planar-similarity-geometry-direction-20260910の明示逆方向付き幾何16条件32方向、field-candidateの8FEM/16電場比較、resolution-candidateの面積由来シフト8条件、tracking-core-candidateの16方向API候補もPASS。いずれも保存format・worker/CLI/GUI/履歴は未接続で、主ソースへ自動でコピーしない。旧geometry候補のNumPy scalar入力拒否と逆係数再計算の座標照合失敗は保持済み。許容差を広げず、元変換の向きを明示する候補へ進んだ。


## 明示多角形の一様尺度追跡：限定受入

基準a297692。明示多角形の原点一様尺度による電場モード追跡を限定受入。宣言した接続/四分割、局所精度と演算順の幾何検証、要求/結果版2、完全保存再生・実worker・CLI・GUIを接続した。標準908件（906合格、2skip、unittest1320.887秒）、追加9unit、32対応・三角形解析16条件・縮退8比較16FEM、16worker、Chrome58操作、保存22追跡/44nativeと取込10件を確認。旧矩形追跡11件・Study29件61点・細分18件54水準・平面32件/TE10件、TM seed9モード19量、527sourceも回帰合格。任意変形/回転・履歴連鎖、親P02と全計画は未完。

標準64505は終了0、総合照合は `out/validation-polygon-tracking-order-fixed-final-20260910/seed_regression.json` PASS。
関連28unit87631、32対応53124、解析64943、縮退52727、16worker/CLI77137、GUI独立38941、旧保存36605、最終保存3294は全て終了0。
Chrome91621/36046は計58操作終了0。GUI18212/PID1717537、再起動13617/PID1725649はSIGINT終了0。生存中の検証/GUIなし。
標準末尾には既存の `.manager.lock` 未close ResourceWarningが残る。未解決事項として保持。

遠方小形状の誤認により標準61676、正当な演算順差の拒否により32050をSIGINT終了130とした。どちらも受入の標準合格には数えない。
修正前のmain対応4498/worker18925の終了1、browser39148の非同期null参照と修正、隔離段階の失敗を元outへ保持。最終sourceの証拠はfinal系に限定する。
検証対象・数値・限界は[契約](PLANAR_POLYGON_TRACKING.md)と[受入計画](PLANAR_POLYGON_TRACKING_PLAN.md)。

次は[全履歴の連鎖検証](PLANAR_TRACKING_HISTORY_PLAN.md)。主ツリーに履歴API/保存/GUIはまだない。
`out/planar-tracking-history-preflight-20260910`（26456終了0）は、個別PASS/同ID名でもnative不連続なら偽の連鎖となる先行確認。
`out/planar-tracking-history-candidate-20260910`（36641/11541終了0）に主ツリー外の候補あり。所有コピーの可搬性、ID捏造拒否、未解決末尾保存と延長拒否の7項目が合格。
この候補の実worker/厳密入力/途中変更/CLI/GUI/多角形連鎖は未検証。製品へそのまま受入としない。
任意の多角形変形/回転、親P02と全計画も未完。親集計8受入/10調査実装/14その他/1除外（33件）は維持する。

## 矩形平面モード追跡：限定受入

基準4045ac1。矩形平面RFの宣言写像による電場モード追跡を限定受入。独立格子の元要素積分、順位交差、縮退ID集合、帯域guardと有限細分空間の診断、コピー保存/再生・実worker・CLI・GUIを接続した。標準899件（897合格、2skip、unittest1302.292秒）、追加20unit、独立8比較16FEM・縮退/退出18FEM・永続8worker、Chrome51操作、保存11追跡/22スペクトルと取込6件を確認。旧Study29件61点、細分18件54水準、平面32件/TE10件、TM seed9モード19量（f差0、RF最大8.882e-16）も回帰合格。一般多角形の追跡・履歴連鎖、親P02と全計画は未完。

最終標準76925終了0、最終照合 `out/validation-planar-tracking-final-20260910/seed_regression.json` PASS。
独立13978、特殊33045、GUI独立6031、保存1007、旧細分35168・旧Study85233・旧native18083とChrome47828/73797/12612は終了0。
永続worker8件は `out/planar-tracking-workflow-20260910/report.json`（185.462秒）で終了結果と再起動を確認。
GUI81285/PID1637218、再起動7814/PID1659427はSIGINT終了0。全製品ソースは検証中固定、最終source523件。
早期独立二報告の差はbrowser検証scriptの非同期select待ち修正1件のみで、最終照合に旧/新hashを記録した。
標準末尾には既存 `.manager.lock` 未closeのResourceWarningが残る。合格数とは別の未解決事項として保持する。

次は[平面追跡計画の残工程](PLANAR_TRACKING_PLAN.md#残る工程)。一般多角形一様尺度を独立契約に限定し、先行幾何/場不変量から進める。
今回の集合引継ぎは二スナップショット検証で、履歴連鎖全体の証明ではない。
親課題集計8受入/10調査実装/14その他/1除外（33件）は変更しない。全計画の目標は継続する。


## 平面同形状細分診断：限定受入

基準6e3b848。平面RFの同形状細分診断を限定受入。元領域の四分割・係数移送、f/E/H/RF別判定、縮退/不足帯域UNVERIFIED、全水準保存再生・worker・CLI・GUIを接続した。標準879件（877合格、2skip、unittest1304.306秒）、追加14検査、独立16条件48FEM・特殊形状16条件48FEM、永続16worker、Chrome42操作、保存18診断54水準と取込2件を確認。旧平面32件/TE10件、TM seed9モード19量と513sourceも一致した。真の誤差上界・表面ピーク精度は保証しない。モード追跡、親P02と全計画は未完。

最終標準98787、独立68735（241.133秒）、特殊形状42973（33.467秒）、GUI独立71367（14.516秒）、worker8508（391.295秒）、保存14974（71.436秒）、旧native62518、Chrome31810/22263/77052と最終照合は終了0。GUI14135/PID1557141、31133/PID1571542、51372/PID1578861はSIGINT終了0。ソース固定を解除し、[平面追跡計画](PLANAR_TRACKING_PLAN.md)へ進める。

異領域移送の質量不変量破れと正方形P1 TM12/TM21の離散分裂は先行反例を保持して修正。隣接間隔は固定閾値と近傍の細分周波数変化の2倍を超える条件を要求する。粗いP1のUNVERIFIEDと細かいP2のPASSを独立解析で分けた。P2矩形8→16→32のRF未達は閾値を変えず16→32→64へ細分。初期標準47080は編集に伴うsource変更検出で終了1、修正前標準35092/大規模P1比較85233はSIGINT終了130。検証スクリプトのbool JSON・余分なjobsパス、旧サーバーによるbrowser失敗も元logを保持。詳細はPLANAR_CONVERGENCE.md。

513source固定中、out/planar-tracking-candidate-20260910で既存矩形TE交差nativeの物理E面積内積・順位交換と正方形の部分空間主角を確認。任意基底回転に不変、source不変でPASS。候補のみで製品追跡の受入ではない。

## 平面独立Study：限定受入

基準2aac376。平面RFの独立Studyを限定受入。全点先行検証・実worker・完全保存再生・CLI/GUI・点取込を接続し、標準865件（863合格、2skip、unittest1238.644秒）、追加9検査、独立24掃引48点＋参照8FEM、交差/例題CLI、Chrome35操作と保存29Study/61点を確認。旧平面32件/TE10件、TM seed9モード19量f差0/RF最大8.882e-16、505sourceと保存hashも一致した。収束診断・追跡、親P02と全計画は未完。

標準10422、独立86003（34.995秒）、交差/例題48062（5.155秒）、GUI独立70301、旧native98399、Chrome71114/14703/96225/12118と空でない候補一覧確認、保存監査35167と最終照合は全て終了0。専用GUI18475/PID1502485、40600/PID1512507、11843/PID1530349はSIGINT終了0、残る実行はない。全点/strict文書・source/queued/再投入・要約再hash/種別逃避・保存失敗の新8unitとGUI新1がPASS。主ツリー505source固定を解除して次へ進む。証拠PLANAR_STUDY.mdとout/validation-planar-study-final-20260910。

次はPLANAR_CONVERGENCE_PLAN.md。隔離候補out/planar-refinement-candidate-20260910/refine.pyは四分割と疎なP1/P2係数移送だけ。32条件の元点/重心写像/多項式/PEC・PᵀM_fP/M_cとKの一致が50502終了0。収束診断/保存/製品APIへ未接続。同形状のf/E/H/RF、縮退部分空間/UNVERIFIED、三水準・保存再生を別に受け入れる。親集計8受入/10進行中/14他/1候補=33と全体目標を維持。

## 平面表示/GUI：限定受入

基準7ae2212。平面RFのxy場表示・SIプローブ・専用GUIを限定受入。標準856件（854合格、2skip、unittest1238.757秒）、追加7unit、Chrome13操作・旧軸対称10操作・再起動後3操作、独立表示場/回転・CLI・保存/HTTP照合を確認。旧平面32件/TE10件、TM seed9モード19量（f差0、RF最大8.882e-16）、499sourceと保存hashも一致した。平面Study・収束比較・追跡等と親P02は未完。

標準96991、独立表示73277（21.591秒）、GUI独立69813、旧native28962、Chrome75514/11200/21472、保存監査2096と最終照合は全て終了0。専用GUIサーバー69895/PID1453592、2157/PID1462168、92703/PID1470780はSIGINTで全て終了0。残る実行はない。証拠・失敗履歴はGUI_PLANAR.mdとout/validation-planar-gui-final-20260910。初回の管理器id比較、ブラウザー非同期待機、query付きURLの404は修正済み。製品FEMと許容差は不変。source固定を解除して次へ進む。

次はPLANAR_STUDY_PLAN.md。専用文書・全点先行検証・独立掃引、同形状の場/RF収束診断、宣言写像による追跡を別に受け入れる。軸対称Study/rz重み/全長RFを流用しない。親集計8受入/10進行中/14他/1候補=33と全体目標は維持。

後続の隔離候補はout/planar-study-input-candidate-20260910/planar_study.py。strict入力・全点Project生成のみで未接続。入力検証と56実FEMの相似/規格化/導電率則が終了0（99531/3071）。順位交差3FEMはout/planar-study-crossing-preflight-20260910で終了0。PLANAR_STUDY_PLAN.mdに証拠を記録し、GUI製品対応数に含めない。

## P02平面Project/Job：限定受入

基準461f4c4。専用PlanarProjectと実worker、直接/管理済み取込、再起動・再実行を限定受入。標準849件（847合格、2skip、unittest1234.561秒）、新14unit、独立16条件workflow・8workerのf/場/G/Q、72保存ジョブと2同梱CLI例を確認。旧平面32件/TE10件/管理済み8件、TM seed9モード19量（f差0、RF最大8.882e-16）、491sourceと保存hashも一致した。GUI・Study・追跡等と親P02は未完。

標準53788、物理53222、workflow3102、旧native70626、保存再起動54771、旧管理済み57596と最終照合は全て終了0。証拠はPLANAR_JOBS.mdとout/validation-planar-jobs-final-20260910。queued後/完了中の入力変更、worker再投入の失敗を先に記録し修正した。worker.claimは重複防止だけで生存証拠にしない。監査driverのcontext manager誤用も初回失敗を保持し修正済み。source固定を解除して次へ進める。

次はPLANAR_GUI_PLAN.md。現行plot_modeが平面Caseを拒否する反例out/planar-display-development-20260910/preflight.log（終了1）を保持。xy/位相/単位長RFを扱う専用表示からGUI接続へ進む。親集計8受入/10進行中/14他/1候補=33と全体目標は維持。

## P02単純多角形RFの主ツリー接続：限定受入

基準c2e5679。PlanarPolygonCase/Case-native版2・load dispatcher・CLI・厳密点検索、大規模辺集合のBVH（同じ厳密線分述語）を接続。旧矩形版1を保持。標準835件（833合格、2skip、unittest1233.849秒）、独立三角形24FEM、回転/尺度16FEM＋参照4FEM、CLI・32プローブ/16replay・凹L字・規格化を確認。旧平面32件/TE10件、TM seed9モード19量と486source、36新規native hashも照合した。

標準41902、物理65542（691.829秒）、変換29034、旧保存36570、全probe34550、凹L字64092は全て終了0。規格化4FEM/4native再生と例題2CLI/API、最終seed照合も終了0。残る実行はない。 最終照合driverの生成時SyntaxErrorは元ファイルを保持して修正し、照合終了0。製品ソースと条件は不変。標準末尾の既存.manager.lockのResourceWarningは未解決。主ツリーの証拠と最大誤差はPLANAR_POLYGON_RF.md末尾。ソース486は全最終報告/標準/現在で一致。旧隔離59036は859.563秒で終了0、初回P1粗分割未達と本体smokeの未達は保持して許容差を維持した。

次はPLANAR_JOBS_PLAN.md。専用PlanarProject、planar_solve worker・state/manifest/Project/nativeの完全結合、JobManager start/import、実中止/再起動/再実行、既存数値回帰を実装する。現行軸対称ProjectにダミーCaseを渡さず、平面nativeにないmodes.csvを要求しない。Project/Job/GUI・曲線/材料/穴/伝搬などと親P02全体は未完。親8受入/10進行中/14他/1候補=33と全体目標を維持する。

## P02多角形の明示xyメッシュ基盤：限定受入

基準7bac43a。専用PlanarMeshのstrict入力、正Jacobian・連結disk・辺交差/T字/重なり拒否・全宣言境界被覆、矩形から分離した面積K/Mを実装。追加11unit、旧矩形12条件の全配列/疎行列一致、回転二尺度24条件/凹L字8パッチがPASS。標準824件（822合格、2skip、1233.985秒）、convergence、TM seed9モード19量と既存平面32件/TE10件の再生、480source一致まで確認した。

標準92838、native回帰24717、費用43939と独立検証は終了0。最終seed照合も終了0。証拠はPLANAR_POLYGON_MESH.mdとout/validation-planar-polygon-mesh-final-20260909。負向き三角形の丸め反転を厳密方向/未解像Jacobian拒否で修正し、初回失敗と標準5903の意図的中断130を保持。L字期待モーメントの誤記も独立積分で修正し履歴を保持。許容差を緩めていない。

次工程はPLANAR_POLYGON_RF_PLAN.md。隔離候補/tmp/planar-polygon-candidate-20260909（複製はout/planar-polygon-product-candidate-20260909/candidate-source）にCase/native版2・CLI・点検索がある。変換16FEM/4CLIと矩形10unit、strict/保存改変/薄いセル内外はPASS。三角形初回12FEMはP1精度未達で終了1、P2 n64は三ゲートを満たした。追加P1 n448/P2 n64の実行59036は実ハンドル/終了報告を確認して継続する。製品主ツリーへは未適用。一般断面のCase/solve/native/CLI、Project/GUI、曲線/材料/多重連結は残件で、親集計8受入/10進行中/14他/1候補=33と全体目標を維持する。

## P02矩形平面RFの主ツリー接続：限定受入完了

基準256dc44。[矩形の平面TE/TM遮断問題](PLANAR_RF.md)を専用PlanarCase・P1/P2 FEM・場/RF・native再検証・CLIへ接続し、限定受入。U′[J/m]・側壁損失[W/m]、TE定数零空間除外、全real/quadrature成分と加速量N/Aを保持する。48 API FEM＋16 CLI計算、32 CLIプローブ/16 replay、標準813件（811合格、2skip）と既存TM/TE数値回帰を確認。一般断面・曲線・材料・伝搬・Project/GUIは未接続。

最終独立33538・プローブ95874・永続曲線tune62306は終了0。標準47107は813件/811合格/2skip、1226.870秒（command1227.257秒）、最終数値照合も終了0。TM seed f差0/RF最大8.882e-16、旧TE10件差0。source478と32新規native hashを照合済み。証拠はPLANAR_RF_PLAN.md冒頭とout/validation-planar-rf-final-20260909。開始時803件は既存曲線tune一件で失敗したが、単独5件・永続worker19.881秒・再起動・固定ソースの最終全体では再現せず、原因は断定しない。初回の縮退G比較/不正出力/例配置の修正、停止/失敗ログを保持し、許容差は変更していない。関連プロセスは全て終了済み。

次はPLANAR_RF_PLAN.md末尾の、宣言した単純PEC多角形と明示xyメッシュ。旧矩形native v1を保持し、一般メッシュの正Jacobian/連結disk/境界被覆、平行移動・回転・P1/P2・場・RF・保存とCLIを検証する。axis/rz readerへ偽Caseを渡さない。多重連結/TEM・曲線・材料・Project/GUIは残件。親集計は8受入/10調査実装中/14他/1候補=33を維持し、P02全体や全計画の完了ではない。

最新集計は8受入/10調査実装中/14他/1候補=33。P02の仕様と隔離FEM調査を開始したため分類を更新した。以下の8/9/15/1は以前の記録。P02製品対応や親受入は未完。

C00/K09の[TE相補解比較器](C00_TE_COMPLEMENTARY_PLAN.md)を限定受入。基準ff0b572。独立46759は12旧版計算＋2P2 FEM、追加Q照合47913、標準87077（803件/801合格/2skip、1237.336秒）、最終33982は全て終了0。TM seed f差0/RF最大8.882e-16、旧TE10件差0、source472一致。専用Xvfb95359/PID1203189もSIGINT終了0。生データはout/c00-te-complementary-independent-20260909、最終回帰はout/validation-c00-te-complementary-20260909。既存Wine wrapperは出力を生成せず、明示Wine/prefix＋専用画面で実行した。失敗ログは開発outに保持。

次は[平面RF契約](PLANAR_RF_PLAN.md)の主ツリー実装。隔離候補out/planar-rf-subspace-candidate-20260909は48実FEM・8モードのP2最終f/場/G・零空間・縮退/相似がPASS。P1追加out/planar-rf-p1-fine-candidate-20260909も24実FEM・n512で同じゲートを満たした。両方のverify.py/report.json/execution.logを保持し、全実行は終了0、source472不変。候補はstrict Case/保存/CLI未接続であり製品対応ではない。旧版Cartesian実行も未検証。

## 同端条件のTE円筒/鏡映追跡：限定受入完了

[同端条件のTE円筒追跡](TE_SECTOR_TRACKING_PLAN.md)を半領域・鏡映部分スペクトルへ拡張し、限定受入。同じ側の一対称面を持つ直線P1/P2円筒が対象。実Eφで対応し、異なる端条件・通常/鏡映の混在を拒否する。独立32FEM、8Study、Chrome9操作、旧追跡8文書の再生、標準801件（799合格、2skip）と既存TM/TE数値回帰を確認。一般形状の追跡・TE調整は未対応。

全検証の証拠・失敗履歴はTE_SECTOR_TRACKING_PLAN.md冒頭。専用GUIを停止済み。470source照合、標準/最終数値比較は終了0。親集計8受入/9進行中/15他/1候補=33は維持。以下は過去の引継ぎ記録であり、候補から主ツリーへの接続は完了している。

## TE鏡映元半領域の収束比較：限定受入完了

基準7fcf4a7。標準47383・最終数値照合27419は終了0。795件中793合格/2skip（1230.296秒/command1230.670秒）。TM seed9モード19量f差0/RF最大8.882e-16、旧TE通常7件＋鏡映3件差0。標準/最終独立/GUI照合/固定時/現在467source一致。out/validation-te-reflected-convergence-20260909に全証拠、TE_REFLECTED_CONVERGENCE_PLAN.md冒頭に範囲・失敗履歴を集約。関連実行は全て終了し、GUI83516/PID1110446もSIGINT終了0。今回のローカルコミットに含める完了変更。親集計は8受入/9進行中/15他/1候補=33のまま、全計画は継続。

次はTE_SECTOR_TRACKING_PLAN.md。一時パッケージ/tmp/superfish-te-sector-tracking-candidate-20260909（主ツリーへ未適用）に同端条件のTE円筒/鏡映追跡の候補あり。out/te-sector-tracking-candidate-20260909/candidate.patch、70770終了0（8FEM）、71233終了0（両次数/両尺度32FEM）、58725終了0（縮退/帯域退出4FEM・保存API replay/metadata改変拒否）、main467source不変。製品実装では旧閉PEC文書を保持する分岐が必要。厳密拒否・実ファイル変更中追跡・CLI/Study/GUI・標準回帰を行ってから限定受入する。候補を製品対応とは数えない。

## TE鏡映の限定受入完了 — 2026-09-09

基準be212b7。標準17381・最終数値照合4175は終了0。790件中788合格/2skip（1193.336秒/command1193.711秒）。TM seed9モード19量f差0、RF最大8.882e-16、旧TE版2/3保存7件差0。標準/独立/GUI照合/worker/改変検証/固定時/現在464source一致。out/validation-te-reflection-20260909に全ログとseed_regression.json。TE_REFLECTION_PLAN.md冒頭に実装範囲/証拠/初回失敗を集約。個別新規実行は全て終了、検証用GUI PID1064077はSIGINT停止済み。7fcf4a7としてローカルcommit済み。

次工程はTE_REFLECTED_CONVERGENCE_PLAN.md。直接全領域のDuffy積分の2倍不変量は磁場の片側値等の影響で不合格（通常/対称化規則の2初回ログ保持）。元半領域方式の候補は円筒/曲面×両対称の8FEMで元の比較文書と完全一致。数値FAIL/UNVERIFIEDを維持した。一時パッケージ/tmp/superfish-te-reflected-convergence-candidate-20260909のAPI候補も4保存比較一致、out/te-reflected-convergence-adapter-candidate-20260909/candidate.patchに保持。主ツリーには未適用。次はこの限定方式の改変/混在拒否、Study/CLI/GUI、標準回帰を実装・検証する。全計画の親集計は8受入/9進行中/15他/1候補=33を維持。

## TE鏡映API初期の経過（現在の状態は冒頭を優先） — 2026-09-09

基準be212b7（TE収束785件/460source/独立21FEM・回帰受入commit完了）。te_reflection.py新規、TESolution.reflection_source_case、symmetryのTE分岐、reflect_curved_spaceの明示coefficient_parityを実装。直線P1/P2/曲線P2・左右/両対称で元振幅の係数移送、TE拘束/free残差/EPS0規格化と元Case保持。TE通常nativeへの誤保存はsave_te_runで作成前拒否。Project.reflect_fullはまだTE拒否。
新3unit6788終了0（1.606秒）、既存TM含むreflection11件92484終了0（9.558秒）。out/te-reflection-development-20260909にログ。TE全体のsessionは次の追記参照。未コミット、標準は未開始。
TE全体31116終了0、45件19.720秒PASS。全実行終了。その後公開API docstringに部分スペクトル番号とエネルギー/損失を明記した（挙動変更なし）。
次は[TE鏡映計画](TE_REFLECTION_PLAN.md)の専用native版を実装。半領域Case/mesh/係数と反射後係数/幾何を保存し、読込で半領域行列・境界条件・規格化を再検証して反射再構成を完全照合する。全必要ファイルをsnapshotsへ追加、Project/Job取込とrerun、GUI部分スペクトル表示を接続。既存TE版2/3とTMは維持。現段階はAPIのみで、実装全体の完了ではない。


## 専用nativeとProject接続中

結果版4を鏡映TE専用とし、results.reflectionに元半領域Case・side/parity・mesh役割・部分スペクトル番号/規格化を明記。mesh.jsonは元半領域、source_fields.npzは元係数/周波数、fields.npzと曲線geometry.npzは反射後を保存する。完了manifestに元係数を必須追加。通常TE版2/3は保持する。

read_te_runは元Case/meshでFEM行列・拘束・規格化を再検証し、同じ反射APIで全Case/係数/曲線幾何を再構成して保存値と照合する。再固有値計算や振幅合わせはない。共通の_restore_fieldsへ通常TE読込の数値検査を移した。source_fieldsを_run_namesでprobe/Job/保存追跡/収束の前後snapshotにも含める。probe metadataにも部分スペクトルのreflectionを保持。

Project.reflect_fullのTE拒否を、対称面一つ/もう一端PECの検査に変更。Job検証は元半領域とreflect_fullを照合し、直接取込は元Case/meshとreflect_fullを保持する。GUI結果の要約とRF詳細に部分スペクトルを表示する。部分スペクトル自体の追跡/収束比較は未接続として拒否し、元半領域の比較を案内する。

69316終了0、native往復3件3.160秒PASS（直線8/曲線4条件）。追加Project/改変テストの25119はJobManagerを未対応with構文で使ったテスト誤りで終了1、初回log保持。closingで明示closeへ修正し85589終了0、5件3.375秒PASS。TE全体41861終了0、47件21.485秒PASS。out/te-reflection-development-20260909へ保持。全native/Project単体検証は終了、標準はまだ未開始。

CLI/API6FEMは74235実行中、out/te-reflection-cli-20260909/verify.py/command.log。P1磁気・P2電気・曲線磁気の3条件でsolve --reflect-full/専用read/API係数一致を検査する。case/project JSONもGUI検証用に生成。終了までソース変更を保留する。GUI実操作・独立物理解析・全保存改変/再起動・旧TM/TE/標準回帰・文書確定/commitは継続中。


CLI74235は終了0、3条件（P1磁気/P2電気/曲線磁気）・計6FEMで版4保存/read/API係数と周波数が完全一致。report.json/source_sha256保持。全実行終了、ソース固定は解除できる。次は生成済み3project JSONを用いたGUI実操作、独立解析/全domain比較、改変・再起動・標準回帰。

## 最新: TE収束Study — 2026-09-09

基準9010591。TE収束比較/API/Study/GUIの限定受入を完了し、全実行終了・ソース固定解除。
標準18688・最終照合16153は終了0。785件中783合格・2skip（unittest1181.171秒、command1181.523秒）。TM seed9モード19量の周波数差0、RF/エネルギー最大相対差8.882e-16、旧TE保存7件差0。標準・独立・GUI・固定時・終了後460対象hashが一致。out/validation-te-convergence-20260909にtests.log/command.log/validation.json/source-fixed.json/verify_completion.py/comparison.log/seed_regression.jsonを保持。
円筒最終26448・球形2536の独立21FEM、10unit9.894秒、Chrome66312の4項目・三判定表示、CLI84435/worker86671、GUI独立74040の再起動4job/解析Case・係数・数値/比較一致、旧TM Study44586の3保存比較/追跡完全一致がPASS。CLI/GUIのCase hash差は0.0/0等の表記差、各元hashを個別検証して保持した。
次工程: [TE鏡映](TE_REFLECTION_PLAN.md)。解析符号と直線右端4FEMの予備移送はPASSだが未実装。左右/曲線、自由方程式、専用native/元半領域/部分スペクトル・Project/CLI/GUIの契約を実装し検証する。親8受入/9進行中/15他/1候補=33を維持し、全計画は継続。以下の実行中記述は過去の経過で、すべて終了済み。

## TE収束Studyの実装経過（終了済み） — 2026-09-09

基準9010591（前回TE掃引775件/455source受入・commit完了）。主ツリーte_convergence.py（新規）、studies.py偏波分岐/Study全TE拒否解除/固定曲線reader、model capability、web/app.jsのTE比較表示/index説明を実装。tests/test_te_convergence.py新8件、既存TE Study/Jobの拒否テストを正しいstrictパラメータ拒否へ更新。
API5件83855終了0（1.953秒）。Study追加8件97081終了1は曲線map.evaluateがN×2座標を要求するのにbaryN×3を渡した誤り、bary[:,1:]へ修正。3234終了0（8.917秒）。旧TM Study11件57933終了0、TE関連33件55959終了0（16.847秒）。ログout/te-convergence-development-20260909。
独立経路49713終了0、out/te-convergence-study-kinds-20260909/verify.py/command.log/report.json。8FEM・四種Studyとnative/再比較一致。mesh/explicit PASS、fixed-curved UNVERIFIED、geometry FAIL。粗い系列の精度が未達であることを保存している。ソース前後一致。全実行終了、まだソース固定/最終標準は開始していない。
次は[TE収束Study計画](TE_CONVERGENCE_STUDY_PLAN.md)の最終独立解析・CLI/worker/GUI・磁気対称/混合拒否・旧TM/標準回帰。元候補6FEMの解析/体積場データとredはout/te-convergence-field-candidate-20260909。新比較は両native分割全セル・次数3/5を128セルbatchで積分、電場/磁場/適用RF量別ゲート、積分安定性や縮退未達はUNVERIFIED。許容差やFEM数式変更なし。未コミットで全計画継続。


## 独立解析・実操作の追加進捗

円筒独立35049終了0、out/te-convergence-cylinder-independent-20260909。12新FEM、P1/P2×両尺度×3水準、Bessel f/電場・磁場体積L2/G誤差減少・Maxwell則・保存比較再計算一致。P1最終UNVERIFIED、P2最終PASSかつ解析精度条件を満たす。検証器はscripts/validate_te_convergence.py。
追加の磁気対称細分/mixed TE-TM拒否で10unit31275終了0（9.894秒）。GUI66312終了0、out/browser-te-convergence-20260909、Chrome4項目/3実Study6FEM/三判定/電場・磁場/RF/N/A理由と場取込がPASS。fixed-curved.png目視。実装hash前後一致・外部要求0。driverはscripts/verify_gui_te_convergence.mjsへ保持。GUI38411/PID1008734はSIGINT終了0。
worker86671終了0、out/te-convergence-worker-20260909、実worker中止・2点完了・管理器再起動・追跡/replayPASS。CLI84435終了0、out/te-convergence-cli-20260909、固定曲線の未確認判定を保存。
GUI独立初回20977終了1はCase JSONの0.0/0等の表記でshaが違うため全文書比較が失敗。失敗log/driverとcase-serialization.diffを保持。修正版74040終了0、out/te-convergence-gui-independent-20260909: 再起動4job verify=True、GUI/保存要約一致、全比較再計算一致、CLI/GUIの各元case hashを個別検証し、解析Case・全係数/周波数・数値/判定が完全一致。hashを同一視していない。
球形の両尺度/磁気半領域×3水準9FEMは2536実行中、out/te-curved-convergence-independent-20260909、log /tmp/te-curved-convergence-independent-20260909.log。scale1-full PASS出力済み、全完了はまだ確認していない。検証器scripts/validate_te_curved_convergence.py。最終ソースで円筒再検証26448も実行中、out/te-convergence-cylinder-final-20260909、log /tmp/te-convergence-cylinder-final-20260909.log。両実行が終わるまでsrc/tests/scripts/examplesの変更は保留。標準は未開始。


円筒最終26448は終了0。12FEM・Bessel解析・両尺度・全保存比較一致PASS、460source一致。球形2536のみ継続中。両独立完了後に標準validateと最終旧TM/TE数値比較を実行し、README/対応表/実装状況/物理・来歴を更新、commitする。


標準検証18688を開始、out/validation-te-convergence-20260909、log /tmp/validation-te-convergence-20260909.log。source-fixed.jsonの460対象を終了まで固定。球形2536も継続中。最終比較用verify_completion.pyを標準outに準備（未実行）、円筒12FEM/球形9FEM/GUI4job/旧TM Study3件/旧TE保存7件/seed9mode19量を要求する。旧TM Study再検証44586は実行中、out/te-convergence-development-20260909/old_studies.log。README/対応表/計画/実装状況・物理モデル/来歴に接続・最終検証中の範囲を追記。


球形2536終了0、out/te-curved-convergence-independent-20260909/report.json/command.log。9FEM（両尺度の全領域・磁気半領域×3水準）で最終比較PASS、解析相対誤差最大f2.508e-5/G1.999e-3/場成分3.836e-3、Maxwell相似PASS、460source一致。旧TM Study44586終了0、3保存Studyの全細分比較と旧追跡文書full replayが完全一致。標準18688のみ継続中、ソース固定。全独立・GUI・CLI・workerは終了。


待機中の後続設計: docs/TE_REFLECTION_PLAN.md。既存TM鏡映の符号はTEと逆なので専用符号/拘束/native部分スペクトル契約が必要。out/te-reflection-contract-20260909で現行TE拒否・円筒解析2モードのEφ/Hr/Hz偶奇を確認、新FEM0。初回ゼロ点付近の絶対SI比較失敗を保持し、成分振幅で無次元化した1e-12比較で終了0。TE鏡映は未実装。標準18688は継続中、主ツリー実装は変更していない。


## 直線離散場の予備検証

out/te-reflection-discrete-candidate-20260909/verify.py/command.log/report.jsonは終了0。P1/P2×磁気/電気対称の4実FEMを半領域で解き、右端鏡映メッシュへTE係数を直接移送した。全領域の自由方程式残差・電気エネルギー規格化/直交性、蓄積エネルギー/損失2倍、f/Q0/G不変、Eφ/Hr/Hzの鏡映符号がPASS。振幅合わせや全領域の再解はしていない。主ツリー460source不変。
この候補は右端の直線移送の確認であり、左端/曲線・一般形状・保存契約/部分スペクトル表示・Project/GUIの製品受入ではない。移送場を通常の全スペクトルnativeとして保存していない。

## 最新: TE Study — 2026-09-09

基準324dc20。TE独立掃引の実装・限定受入を完了。全関連実行は終了しソース固定を解除。追加4unit/既存TE Job8件、旧TM Study関連11件、実worker中止/2点完了/再起動/追跡replayPASS。
標準48904・最終比較22868はともに終了0。775件中773合格・2skip（unittest1179.803秒、command1180.149秒）。TM seed9モード19量の周波数差0、RF/エネルギー最大相対差8.882e-16、旧TE保存7件差0。標準・独立・GUI・固定時・終了後455対象hashを照合し一致。out/validation-te-study-20260909に全ログ・比較driver・source-fixed.json・seed_regression.jsonを保持。
初回独立82140終了1: P1nr64/nz96の高位f誤差.00109154>条件.0008。許容差維持、P1nr96/nz144へ細分。62766終了0、out/te-study-independent-refined-20260909に16FEM/P1P2/両尺度/規格化/CLI追跡4組PASS、driver/log保持。P1最大.000485641、P2最大3.515e-7。次に最終ID順序解析照合を検証器へ追加し、GUI driverの候補由来main_tree_implementation=falseをtrueへ修正した。
最終独立4976終了0、out/te-study-final-independent-20260909。16FEM/解析ID順序/CLI追跡4組・規格化・両尺度PASS、command.log保持。
CLI実掃引55045終了0、out/te-study-cli-product-20260909、log /tmp/te-study-cli-product-20260909.log。Chrome初版68372終了0だが候補false metadataが残った旧driver。最終10613終了1は既存ジョブのあるworkspaceでactiveStudyを開けずtimeout（out/browser-te-study-final-20260909）。新workspaceで同じ最終driver12749終了0、out/browser-te-study-fresh-final-20260909、2項目PASS、外部HTTP0、実装hash一致、study.png目視。両GUI89355/PID964363・44941/PID968341はSIGINT終了0。
GUI独立12518終了0、out/te-study-gui-independent-20260909/verify.py/command.log/report.json。新管理器2job verify=True、GUI要約==保存文書、CLI/GUI2点全係数/周波数/全RF結果完全一致、Study追跡/replayPASS、455source一致。
次工程: [TE収束Study](TE_CONVERGENCE_STUDY_PLAN.md)。下記の6FEM体積場候補とred.jsonを起点に、TE専用比較・物理一致/縮退/標本依存・RF/電磁場別ゲート・Study/API/CLI/GUI/保存契約を実装する。掃引と収束を混同しない。親8受入/9進行中/15他/1候補=33を維持し、全計画は継続。


追加曲線TE掃引6889終了0、out/te-study-curved-independent-20260909/verify.py/command.log/report.json。球形P2の2FEMで規格化振幅・損失比例/f,G,Q不変・N/A維持・未対応円筒追跡拒否PASS、455source一致。最終比較driverへ証拠照合を追加。README/対応表/計画/実装状況と物理/来歴に掃引の接続・標準待機状態を追記済み。後続docs/TE_CONVERGENCE_STUDY_PLAN.mdは設計のみ。標準48904と最終比較は終了0。


## 独立の体積場比較候補

主ツリーを変更せず、out/te-convergence-field-candidate-20260909/verify.pyを実行。94381終了0、6実FEM（P1/P2×nr12/24/48）・Gauss標本次数48/96で2モードの解析周波数・Eφ体積L2・Hr/Hz体積L2・G誤差が細分ごとに減少した。各隣接水準の場変化も別に保持。既存R35の円筒解析を再利用し、候補のreport.json/command.log/6保存結果を保持。主ツリー455source不変。
同一保存TEをcompare_refinementへ渡してもTM readerで拒否される現行不適合をred.jsonに記録した。これは候補計測であり、一般形状/曲線・縮退・Study/API/GUIへの収束接続や最終精度の合格ではない。


旧TM保存Studyの追加照合84108終了0。out/te-study-development-20260909/verify_old_studies.py/old_studies.log/old_studies.jsonに保持。固定曲線3水準と明示元mesh P1/P2の計3Studyで全細分比較が保存時と完全一致、旧曲線Study追跡文書のfull replayも完全一致。最終比較driverにこの証拠も要求する。

## 最新: TE円筒追跡 — 2026-09-09

基準c5b4409。TE円筒追跡API/保存/CLI/GUI履歴の限定受入を完了。[計画・失敗履歴](TE_TRACKING_PLAN.md)。全関連実行は終了し、ソース固定を解除。
標準9994・最終比較40142とも終了0。標準771件中769合格・2skip（unittest1200.915秒、command1201.284秒）。TM seed9モード19量の周波数差0、RF/エネルギー差最大8.882e-16、旧TE保存7件の差0。標準・独立・固定時・終了後452対象hashとブラウザー実装hashが一致。out/validation-te-tracking-20260909に全ログ・比較結果を保持。
最終独立84610終了0、out/te-tracking-final-independent-20260909/report.json/command.log。8FEM/両次数/両尺度/3標本次数、全6ID解析順位/符号振幅/Maxwell、4組CLI/save/replay/API全文書一致PASS。452source前後一致。
Chrome2587終了0、out/browser-te-tracking-20260909、8項目PASS・外部要求0・実装hash一致、driver.mjsとtracking-history.png保持/目視。独立3FEMの取込、merge/splitで個別ID未確定の集合保持、保存replay/改変拒否、UNVERIFIED継続禁止。GUI86416/PID925463はSIGINT終了0。
GUI独立48208終了0、out/te-tracking-gui-independent-20260909/verify.py/command.log/report.json。新管理器取込3件verify=True、元TE全係数/周波数/RF/Projectmesh一致、download履歴全replay、部分空間IDへ個別周波数拒否。旧TM profile pair/historyと円筒merge/split historyの3文書も全文書一致、old_tm_tracking.jsonへ保持。
実装: te_mode_tracking.py専用Eφ正規化円筒比較、mode_trackingのTE分岐、saved_mode_tracking TE全native/marker snapshot/read_te_run・混合TE/TMと他mapping拒否、model capability文言/GUI説明。新test_te_mode_tracking5件1.447秒PASS・旧TM保存追跡6件.277秒PASS。初回unit16689のTM生Solutionにcaseがないテスト誤りは保存TMへ修正。独立初版11411もPASSだがGUI説明前の451sourceなので最終版は84610を使う。
待機中の次工程候補: /tmp/superfish-te-study-candidate-20260909にsrcコピーを作り、studies.pyとstudy_mode_tracking.pyだけTEパラメータ掃引/TE読込の試作を実施。主ツリーへ未適用。初回NumPy scalar拒否・修正版12908の追跡TMreader拒否を経て82377終了0、out/te-study-tracking-candidate-20260909の2FEM/6mode解析/N/A/独立スペクトルUNVERIFIED/別途trackingPASS。candidate.patch/driver/report/log保持。main452hash不変。追加44311終了0、out/te-study-worker-candidate-20260909で実worker中止→2点完了→再起動→Study tracking/replayがPASS。既存Study表はnull R/Qを0.000000と表示する実反例を確認し、一時web/app.jsだけN/A理由へ修正。3ファイルcandidate.patchとgui-null-red.json保持、その後候補GUI69859終了0、out/browser-te-study-candidate-20260909でChrome2項目（2点実FEM/全R/Q N/A・独立スペクトル説明、点取込/TE描画）PASS/目視。配信したtmp実装hash前後一致、外部要求0。GUI38921/PID940536はSIGINT終了0。最新4ファイルcandidate.patch/driverはout/te-study-gui-candidate-20260909。後続Studyの実装をこの候補から進められるが、製品受入は未完了。
[後続TE Study計画](TE_STUDY_PLAN.md)に候補の範囲と証拠を整理。追加75271終了0、out/te-study-integrity-candidate-20260909で未対応収束/後続不正値拒否、N/A→0の要約改変をouter hash更新後も拒否、復元replayPASS。候補の全実行終了。
次工程: [TE Study計画](TE_STUDY_PLAN.md)。上記候補を主ツリーへ適用し、標準・独立解析・保存/CLI/GUI・既存TM Studyの受入を実施する。TE一般形状/曲線tracking/調整等と親D01/O02/P01・全計画は継続。親8/9/15/1=33維持。


## 最新: TE GUI — 2026-09-09

基準449d1ef。[仕様/失敗履歴](GUI_TE.md)。通常TE GUIの実装・拡張受入・独立照合・標準/回帰を完了し、一つのローカル変更にまとめる。全関連実行は終了、ソース固定解除。

標準67203終了0、out/validation-gui-te-20260909。最終比較80319終了0。標準766件中764合格・2skip（unittest1175.340秒、command1175.692秒）。TM seed9モード19量の周波数差0、RF最大8.882e-16、旧直線/曲線TE保存7件のRF差0。標準・独立・固定時・終了後448対象hashとブラウザー実装hashが一致。
command.log/tests.log/validation.json/source-fixed.json/verify_completion.py/comparison.log/seed_regression.jsonを標準outへ保持。検証は標準unittestで、pytest/Hosted CI/他OS/Wineの新規実行なし。

拡張Chrome10868終了0、out/browser-te-expanded-wait-20260909、10項目PASS・外部要求0。P1 TE/曲線P2実FEM・画像・プローブdownload、明示モデル/strict正規化Project往復、N/A理由、TM専用reference/band/peaks無効化とTM復帰。画像を目視し日本語名表示も確認。driver.mjs保持。GUI21290/PID882385はSIGINT終了0。
独立72935終了0、out/te-gui-independent-20260909/verify.py/command.log/report.json。新管理器全3件verify=True、download全成分/TE全native hash/規格化/B=μ0H、3新規API FEMと係数/周波数完全一致。球形3mode max相対f2.500e-5/G2.824e-3/fields1.506e-3 PASS。GUI低分割P1は操作/保存一致の検査で精度合格ではない。

実装: te_display/te_visualize/te_probe、通常plot/probe分岐、GUI cache TE実装hashとTE case digest、偏波選択/N/A・未対応結果操作の理由。曲線場は基準中心写像、磁場+i quadrature、rEφ磁力線、SI CSVを保持。既存日本語font選択のみでfontを取得/配布しない。物理精度許容差/FEM数式/依存は無変更。
初回test呼出し誤り・検証器の結果選択省略/古いDOM/未正規化比較・15秒download待機超過を記録。TE画像生成後のcacheがTM専用case_sha256を要求する実不具合を修正。詳細と全driver/reportはGUI_TE.md/各out。最後の追加3unit1.350秒、標準にも含む。

次工程: [TE追跡計画](TE_TRACKING_PLAN.md)。out/te-tracking-candidate-20260909の2FEM/6mode交差候補と、out/te-tracking-crossing-scales-20260909のP1/P2×2尺度×交差前後8FEM（38529終了0）、3標本次数の全ID/符号振幅不変/Maxwell則PASSを保持。いずれも製品TE追跡ではない。混合TE/TM拒否・近接縮退/帯域退出・専用保存/replay・CLI/GUIを実装検証する必要がある。TE Study/調整/適応等も未接続。親8受入/9進行中/15他未受入/1候補=33、O02/P01と全計画は継続。


## 最新: TE Project/JobManager — 2026-09-09

基準d2d53de。[仕様/受入](TE_JOBS.md)。前回は曲線TEの実装・検証・コミットで進捗あり。開始時は直前標準755件と現在440対象hash一致を確認し、同一基準の標準テストを重複実行しなかった。TE Project往復redは旧全TE拒否で終了1（/tmp/te-project-red-20260909.log）。

最終標準78312終了0、独立80174終了0、追加再起動66118終了0。標準763件中761合格・2skip（unittest1158.285秒、command1158.633秒）。独立8実FEM・8取込と再起動後の明示verify=True全8件がPASS。TM seed9モード19量の周波数差0、RF最大8.882e-16、旧直線/曲線TE保存7件のRF差0。標準・独立・再起動検証・終了後443対象hash一致。最終比較もpassed=trueと末尾の全結果を出力済み（session1159は後続pollでUnknown processとなり、終了コードの再取得は不可）。出力はout/validation-te-jobs-verified-20260909とout/te-jobs-verified-independent-20260909。command.log、comparison.log、seed_regression.json、restart_verified.json、各driverを保持。検証は終了、ソース固定解除。

初回独立18269は終了0・PASS（out/te-jobs-independent-final-20260909、command.log保持）、8実FEM・8取込・再起動・円筒6/球形3モード両尺度、443対象hash一致、相似最大8.194e-14。その後、native再読込後にCSVを書き換えてもread_jobがcompleteを返す実反例を確認（out/te-jobs-verification-race-20260909、driver/AssertionError保持）。初回標準53643は自分のvalidate810241/unittest810243をpsで特定しSIGTERM停止、終了143。out/validation-te-jobs-final-20260909/interruption.jsonを保持。Gateway等の他プロセスは触っていない。

修正はTE job verifierの終点で全必要ファイルのhash/リンク/存在と外側manifestの一致を再検査すること。追加race検査はnative CSVと外側manifestの変更を別確認。修正版8件80160終了0・1.901秒。logはout/te-jobs-development-20260909/race-fixed-unit.log。初回独立のソースと修正版はte_jobs.py/test_te_jobs.pyが異なるので、修正版の独立と標準を上記の新出力先へ再実行しPASS。

実装: ProjectはTE通常計算を受理しreflect_fullは拒否。te_jobs.pyが通常read_jobへTE専用完了/全必要ファイル・Project Case/保存Case・明示mesh/保存source一致とread_te_runを接続。JobManager.import_resultはTEを専用経路へ分岐、元ファイル/管理済みProject・manifest・job状態を前後hash照合しmarker最後のコピー。直接nativeは元meshをProject版2へ保持、管理済みは元Project維持。origin=imported/not_checkedを保持。Study/tuning/rf_optimizationでTE未接続を入口拒否。TM read_solutionはTE拒否のまま。

当初のtest_te_jobs.py 7件: P1/P2/曲線Project/API/native、必要geometry非掲載/Case不一致、全hash更新済み係数不正、外部meshの直接取込/再実行と管理済み取込/不一致、実worker中止→再実行/管理器再起動、コピー中source変更、未接続workflow拒否。初回12962終了1は改変testがProject.saveの上書き禁止に抵触。write_textで意図した不正を作るtestへ修正し58162終了0・1.766秒。元mesh不一致も確認したrace修正前31590終了0・1.736秒。既存TE12件55386終了0・2.130秒、jobs7件終了0・.913秒。各logは/tmp/te-jobs-*および/tmp/te-project-existing-*にある。前回test_teのProject拒否はreflect_full拒否へ更新し、TE意味の検査を維持。

GUI read-only調査: app.js applyProjectはexplicitModelをclone保持し、collectProjectは明示モデルを再保存する。TMの自動生成はexplicitModel===nullのときだけ。今回のProject許可で無言TM化するとの懸念は実コードでは成立しなかった。通常RF表もnullを未定義として表示。GUIのTE選択/成分描画等は未接続・新規Chromeなし。source固定中にGUIの未検証な変更は入れていない。

実装・検証・関連文書を一つのローカル変更にまとめる。P01/O02/全体は未完、親8受入/9進行中/15他未受入/1候補=33。次はTE GUIのモデル選択・N/A理由・正しい場成分/単位での描画、実Chrome/保存/実FEMまで接続する。待機中に保存球形TEの描画だけを試作し、out/te-gui-display-accepted-candidate-20260909へdriver/fields.png/samples.npz/scope.jsonを保存して目視。80819終了0、新規FEM/GUI製品接続ではない。初回34838はNumPy scalarのprobe zが既存strict APIで拒否され、float変換した候補へ修正。初回driver/logはout/te-gui-display-candidate-20260909へ保持。将来はsigned Eの対称color範囲、TEプローブ/メタデータ/UI、GUI描画cacheの新module hashも接続する。新規依存/外部数学参照/legacy/Wine/Hosted CI/他OS/サブエージェントなし。

## 最新: 曲線P2 TEの通常solve・native接続 — 2026-09-09

基準e243205。[仕様/方式/失敗履歴](CURVED_TE_PLAN.md)。前回は球形試作と受入条件の具体化で進捗あり。今回、一時コピーで実装・検証後、開始時標準session1151終了0（750件中748合格/2skip、1155.964秒）を確認して主ツリーへ反映した。主ツリーTE12件session69453終了0、2.028秒。te.py/te_curved.py/te_saved.py/curved_solution.py/model.py、tests/test_te.py/test_te_curved.py、scripts/validate_curved_te.py、examples/te/sphere.jsonが変更対象。最終検証までソースを固定し、全実行終了後に固定解除した。

最終標準42758終了0、out/validation-curved-te-final-20260909。755件中753合格/2skip、unittest1157.101秒、command1157.463秒。最終独立24369終了0、out/curved-te-independent-final-20260909。比較18306終了0、seed9モード19量f差0/RF最大8.882e-16、旧直線TE版2 native/CLI4件全RF差0。標準/独立/終了後440対象hash一致。verify_completion.py/seed_regression.json/comparison.log/command.logを標準outに保存。全関連実行は終了。

実装: 二次写像からTE勾配/場を復元、PEC側要素の接線磁場を2πr dsで積分する。TE用constrained_dofsを保持。点検索はQuadraticLocator、領域外とUNVERIFIEDを区別。専用結果版3とgeometry.npzで実節点/接続/タグを保存再照合、二次VTKと実軸節点CSV。直線TE版2は不変。Caseの一様/局所履歴を再構築し最後にTE拘束集合を作る。既存TMのCurvedSpace追跡/適応APIを直接TEへ受入したわけではない。

一時コピー /tmp/superfish-te-curved-20260909 は主ツリーの最終基準ではない。候補初回7 unitの1FAILは旧curved拒否regexの期待をgeometry前提拒否へ更新。追加12件の1ERRORはmarked入力の最小角未指定を修正。その後12件2.109/2.073/2.059秒でPASS。独立3915終了1は第3モードG1.133%未達、同一幾何で一様4段へ追加。72877終了1は両尺度3モードの条件を満たしたが半領域の軸始点0規約に違反。平行移動した62291終了0、10全領域FEM＋1半領域FEMでPASS。最終18625係数、f最大2.500e-5/場1.506e-3/G2.824e-3、相似1.219e-13。半領域/全領域f1.368e-8/G8.484e-5/壁損失1/2則8.481e-5。旧直線TE版2 native/CLI4件の再読込は差0（54762終了0）。各一時結果・失敗/logはout/te-curved-draft-20260909に保存。合格後のcapabilities説明/例題/壁mode検査も最終検証に含める。

最終独立の収束図を作成し、2尺度のf/G/場と受入線を目視した。convergence.png/描画driver/command.log/unit.logを同じoutへ保存。README/対応表/計画/実装状況/PHYSICS/MODEL_CONTRACTのTE対応範囲を揃えた。全体/P01は未完、親8受入/9進行中/15他未受入/1候補=33。次はProject/Job/GUI等のO02統合。入口・worker・read_job・import_result・GUIモデル生成の読取調査はout/te-curved-draft-20260909/next_project_integration.json。入口の拒否解除だけで完了としない。TE直接nativeの取込ではsource_mesh_dataをProject版2へ引き継ぎ、再実行時に元メッシュを失わないことも受入条件へ含める。サブエージェント/新規依存/legacy参照/新規ブラウザー・Wine・Hosted CI・他OS実行なし。

## 最新: 真空m=0 TEの直線P1/P2 — 2026-09-09

基準b0f8b0c。[仕様・独立検証](AXISYMMETRIC_TE.md)。P01を進行中へ更新。明示Modelのpolarization=teだけを別TESolutionへ分岐し、Eφ/rを未知数としてTE PEC/電気対称の本質条件、磁気対称の自然条件を解く。既存の自作P1/P2 curl行列・幾何を再利用するが、TMのuへ別名を付けない。軸のEφ/Hr=0、Hz有限を保持し、+iωtの磁場quadrature、電気/磁気エネルギー、PECだけの壁損失/Q0/Gを評価する。軸方向加速量と両R/Qはnullと理由を保存する。解析式を製品solverへ入れていない。

通常solve/API、外部直線mesh、TEFieldSampler、専用schema_version=2結果/NPZ/CSV/VTK、replay-teを追加。TE完了marker/hash、Case/場空間/単位/phasor/版・環境、係数のBC/残差/直交/エネルギー規格化、保存場からのRF再積分を検証する。RF照合相対1e-10は再積分の丸め用で物理精度許容差とは別。Project/Job/GUI、追跡、曲線、鏡映等は明示拒否し、既存TM readerはTE markerだけでなく読んだCaseでもTEを拒否する。

事前独立不変量は円筒TE011とTM自然壁の周波数差41.9%でFAILを確認。TE追加テストの最初の軸値FAILはqueried r=0を厳密処理して修正。TM形式のCaseだけをTEへ変えhashも更新した不正保存を旧readerが誤受入するredを確認し、Case段階の拒否と回帰検査を追加した。初回標準64170はこの実不具合の修正のため自身のvalidate/unittestだけを停止（143、interruption.json保持）。関連のないプロセスは停止していない。

最初の独立1735終了1、out/te-independent-20260909。P1 n=256はf条件を満たしても場約1.83%/G約1.09%でFAIL。交差格子の追加観測も未達で不採用。次の47582終了1、out/te-independent-accepted-20260909では対角格子P1 n=768の両尺度はPASS、P2 n=32高次モードG約0.999%でFAIL。各失敗log/driver/部分値を保持し許容差は不変。P2 n=64の追加対照64053終了0を経て最終両次数/両尺度を再計算した。

最終独立32360終了0、out/te-independent-final-20260909。scripts/validate_te.pyで6モード×2尺度、P1の5水準/P2の4水準の18 API FEMと2 CLI FEM。最終P1/P2の最大相対差はf 7.861e-6/3.509e-7、場5.148e-3/1.492e-3、G3.690e-3/2.505e-3。電磁エネルギー比最大1.599e-12、Maxwell f/G/Q0相似最大1.219e-12。P2 CLI/API/nativeの係数・RF一致。Besselの正零点は独立検証だけで使う。保存値の収束図を作成し目視、図とdriver/logをoutに保持。TE追加7 unitは0.302秒PASS（外部mesh/共通sampler/不正tagも含む）。

中間標準44221は終了0、749件中747合格・2skip、1157.734秒。終了してから最終の保存版・環境メタデータ/外部mesh検査/例題・独立P2分割64へ変更し、最終標準を再実施した。この中間結果を最終版の証拠には使わない。

最終標準61417終了0、out/validation-te-final-20260909。750件中748合格・2skip、unittest1150.683秒（command全体1151.029秒）。seed9モード19量のf差0/RF最大8.882e-16。標準/最終TE独立/終了後436対象hashが一致。verify_completion.pyとseed_regression.jsonを標準outへ保存。全関連実行は終了、ソース固定解除。

P01/全体は未完。親8受入/9進行中/15他未受入/1候補=33。次はP01の曲線TEとO02のProject/Job/GUI統合へ進め、場・壁損失と保存再検証を保つ。TE追跡/Study/設計探索も残る。今回GUI/ブラウザー・Wine・Hosted CI・他OSの新規実行はなし。新規依存なし、公開数学R35と独立Maxwell導出をREFERENCES/PROVENANCEへ記録した。

## 最新: RF探索の実行内祖先再利用 — 2026-09-09

基準9fe3ff2。[仕様・証拠](RF_OPTIMIZATION_REUSE.md)。rf_optimization.pyのprivate _VerifiedPrefixは実行ごとに生成し、検証済みtrial/全3水準sourceを深いコピーで保存。要求/祖先順/実装hash/全ファイル変更とリンクを検査して新試行だけを再評価する。終了時の二重native再読込は全ファイルhash一致へ置換。公開replayはcacheなしで全試行をnative場から再構築、再開は空cacheで全replayしてから追記する。式・許容差・保存schema・GUI操作は不変。

開始時85668終了0、RF探索5件386.355秒。新規privateキャッシュ保護1件0.100秒PASS（合成ファイルのコピー分離・request/ancestry/implementation・内容/削除/追加/リンク変更拒否）。既存実FEMテストへ再開の評価回数3・公開replayの全3評価・新候補評価後の祖先Projectバイト変更拒否/以前checkpointとcache保持を追加。今回初回失敗なし。

変更前73739終了0、out/rf-optimization-prefix-before-20260909、保存済み4試行の1/2/3/4prefix評価が220.994秒、RF評価累計10回。変更後94776終了0、out/rf-optimization-prefix-after-20260909、109.735秒/4回。全4段階の全文書が変更前後と既存CLI文書に完全一致。並行負荷は同一でない単一観測なので一般速度倍率としない。保存場の評価であり新しいFEMではない。

独立6767終了0、out/rf-optimization-reuse-independent-20260909。4試行/12水準を新規FEM。両倍率[1,1]→[1.01,1]→[1.01,1.01]→最終同値、SEARCH_COMPLETE/TRIAL_LIMIT。公開replay全文書一致、既存CLIの12Project/modesと試行列/判定が完全一致。最終球形解析f2.472e-5/RQ2.525e-6/G1.077e-7/E比2.314e-4/B比6.077e-6で既存許容差PASS。

標準20025終了0、out/validation-rf-optimization-reuse-20260909、743件中741合格・2skip、1161.975秒。seed9モード19量f差0/RF最大8.882e-16。標準/新規独立/変更後計測/終了後431対象hash一致。driver/logは各outへ保存。全関連実行は終了、ソース固定解除。GUI/ブラウザー・Wine・Hosted CI・他OSの新規実行はなし。

D03/全体は未完。親8受入/8進行中/16他未受入/1候補=33維持。既存2変数探索のGUIと今回の実行内再利用は接続済み。次は計画の親要件と不足証拠を照合し、一般変数や追加物理など未実装の主機能へ進める。部分性能改善を重ねただけで全計画の完了とはしない。追加物理P01等ではMODEL_CONTRACTとPHYSICSを明示拡張し、独立解析の場/境界/エネルギー・保存/CLIの受入を先に定める。TMへの無言フォールバックは禁止。

## 最新: RF探索GUIとpreflightのロック解除 — 2026-09-09

基準8b2ac14。[仕様・受入証拠](GUI_RF_OPTIMIZATION.md)。gui_rf_optimization.pyとwebのRF探索カードを追加し、2変数/目的関数/複数制約尺度/予算の生成・要求保存復元、ジョブ開始/中止後checkpoint選択/保存再開、数値状態/停止理由の別表示、試行3水準の個別ID実rankによるnative場取込へ接続。raw JSONはstrict parse。再開は検証済み文書の要求を使い、未確認個別IDにrankの代用を与えない。start_rf_optimizationの全preflightをmanager.lock外へ移し、前後のclosed確認と起動登録のロックを維持。開始HTTP要求そのものの同期的完全検証は重いまま。FEM/RF/探索式・許容差は変更なし。

並行性red56390終了1（2件中1FAIL、2.050秒）で実際の別ローカルワーカーのstatus/cancel/close阻害を確認。green2件0.024秒、再実行2件0.027秒PASS。GUI transport2件PASS（入力往復/strictとmockによるrank3/2/4選択・未確認/不正index拒否）。実FEM経路は下記ブラウザーで検証。

初回ブラウザー79579/Node597169とGUI65765/PID596792は、検証器の保存水準0省略値の扱いを修正するため明示停止（終了143/0）。out/browser-rf-optimization-20260909/interruption.jsonと部分結果を保持。全終了後、検証器の??0・画像完了/保存読込待機とフォーム幅を確定して再実行。修正版93936終了0、out/browser-rf-optimization-accepted-20260909、Chrome13項目PASS/外部要求0。フォーム完全往復/strict・実中止・候補選択/全replay・download/reload/改変拒否・編集要求と分離した再開・6解/TRIAL_LIMIT・最終1/2/3細分・初期/最終場取込/実順位/画像読込。フォームと結果表の画面を目視。GUI25233/PID606355はSIGINT停止終了0。

保存経路初回64647終了1、out/gui-rf-optimization-interface-20260909。検証器が.plot-cacheをジョブとして読んだため、job.jsonがある対象だけに修正。失敗driver/log保持。修正版18868終了0、out/gui-rf-optimization-interface-accepted-20260909。再起動したJobManagerで完全再検証、GUI文書/API一致、初期3水準は既存CLI first-1/trial-001、最終3水準は前回JobManager trial-002とProject/modes完全一致。取込2件の出所/結果一致。GUIで実計算した最終球形の解析相対差f2.472e-5/RQ2.525e-6/G1.077e-7/E比2.314e-4/B比6.077e-6で既存許容差PASS。追加FEMではなく保存結果の照合。

標準12165終了0、out/validation-gui-rf-optimization-20260909、742件中740合格・2skip、1219.642秒。seed9モード19量f差0/RF最大8.882e-16。標準/保存経路/終了後430対象hashとブラウザー対象hash一致。driver/logは各outへ保存。全関連実行/ワーカー/GUI終了、ソース固定解除。新規Wine/Hosted CI/他OS受入なし。

D03/全体は未完、親8受入/8進行中/16他未受入/1候補=33維持。次はD03の残件と親受入条件を照合し、一般変数・反射/組立/履歴・一般性能を限定機能の合格と区別する。今回の基本GUI操作は接続済み。重い保存再検証の重複削減や別分岐経過時間合算を進める場合は、全replay/出所改変拒否・完全一致と費用の定義を保持し、独立した性能観測と受入条件を先に置く。

## 最新: RF探索JobManager — 2026-09-09

基準5229c33。[仕様・証拠](RF_OPTIMIZATION_JOBS.md)。rf_optimization_jobs.pyは既存自作tuning_jobsのワーカー・投入入力/実装hash・manifest・祖先/予算照合をRF探索の3水準へ適用。JobManager.start_rf_optimizationとread_jobのkind/manifest検証を追加。kind=rf_optimization、optimization_status/can_resume/computed_trials/computed_fem_solvesを照合し、numerical_validation=not_checkedを保つ。rf_optimization_checkpoints.pyは停止した当該ジョブの番号一覧（未検証）と、open時の全replay・所属/予算/祖先/リンク拒否を行う。GUI前面/HTTP操作は未追加。FEM/RF/探索の式は無変更。

開始時81046終了0、既存tuning jobs7件5.571秒。新規14348終了0、3件216.357秒（実FEM中止/再起動/数値未達の再開/別ジョブ拒否/3水準manifest欠落/祖先改変、事前入力、入力race）。その後投入予算超過checkpointのguardを追加、個別1件0.043秒PASS。初回失敗なし。
独立61057終了0、out/rf-optimization-jobs-independent-20260909。最初の管理ジョブ20260909-130739-f4f5257df0はcomplete/PAUSED/3解、再起動後の20260909-130847-4a9796230aはcomplete/SEARCH_COMPLETE/6解。再起動/全再検証PASS。初期3水準のnative Projectとmodesが既存CLI（前回のfirst-1/trial-001）と完全一致。最終球形解析f2.472e-5/RQ2.525e-6/G1.077e-7/E比2.314e-4/B比6.077e-6で既存独立許容差PASS。
標準8265終了0、out/validation-rf-optimization-jobs-20260909、738件736合格・2skip、1202.231秒。seed9モード19量f差0/RF最大8.882e-16。標準/独立/下記単一観測/終了後426対象hash一致。全driver/logをoutへ保存。全関連実行/ワーカーは終了、ソース固定解除。新規GUI/ブラウザーなし。

追加75268終了0、out/rf-optimization-job-preflight-20260909。既存requestの読み取り専用単一計測で新規preflight0.00782秒、1試行の再開preflight16.498秒。start_rf_optimizationはその間manager.lockを保持する。次はGUI接続に先立って重い検証をロック外へ移し、初期/起動直前のclosed確認と、検証中のclose/cancel/status応答をテストする。GUIで長い再検証自体をワーカーへ渡す場合も、strict入力・元requestとの一致・起動後の完全replayを維持する。現在この応答性修正は未実装。
GUIはgui_tuning.py/web/app.jsのカードを参照し、2変数/目的関数/複数制約と尺度/予算の生成保存復元、ジョブ/数値状態の別表示、中止checkpoint選択再開を接続する。RF探索はtrial_directories配下level-0/1/2の3水準なので、単一trial_runsのtune操作をそのまま使わない。各水準の保存個別IDと実rankを確認して既存native import/field表示へ渡す。実ブラウザーで操作・出所・CLI/Python一致・外部要求なしを検証する。
今回computed_fem_solvesは完了した試行の解数で、以前の中止/失敗した別分岐の費用をゼロとも全体予算へ算入済みとも主張しない。元部分出力・elapsed_secondsは保持。D03/全体は未完、親8受入/8進行中/16他未受入/1候補維持。

## 最新: D03 曲線2変数RF探索 — 2026-09-09

基準f976091。[仕様・証拠](RF_OPTIMIZATION.md)。rf_optimization_search.pyはradial/axialの有界座標試行、明示尺度による最大制約違反の減少→実行可能時だけの目的関数改善、step半減/訪問済み除外/最終試行予約を実装。rf_optimization.pyは各候補の3水準実FEM、相対アフィン写像で全個別ID確認、RF設計評価、全試行/入力/場/判定の再構築・保存再開を接続。最終は1段細かい3水準を新規solve。max_trialsは初期/最終を含み、3*max_trialsがFEM上限。失敗はfailure文書/呼出し数を残し例外停止し、採用値/成功checkpointへ変換しない。失敗前checkpointからの別分岐は利用者全体の予算とは別。CLI optimize-rf/resume-rf-optimization/replay-rf-optimizationと合成球形の例題examples/optimization/curved_rf.jsonを追加。

開始時45954終了0、RF設計5件21.537秒。追加17597終了0、4件377.610秒（実FEM9解・pause/resume/final/replay/改変/終端拒否、探索predicate）。その後CLI/例題/検証scriptを追加。失敗注入追加1件0.133秒PASS。初回失敗なし。全ログをout/rf-optimization-independent-20260909へ保存。
独立24265終了0、out/rf-optimization-independent-20260909。両尺度4試行/12FEM、値[1,1]→[1.01,1]→[1.01,1.01]→final同値。探索段数0/1/2→final1/2/3。CLI pause/replay/resumeと最終APIreplay、最終解析f相対差両尺度2.472e-5、観測包絡のMaxwell相似最大4.930e-14。SEARCH_COMPLETEだが停止理由TRIAL_LIMITを保持し、最適性としない。
追加82660終了0、同out/restoration-validation.json。既存native試行を解析f上限（元球形f/1.005）の追加制約で再評価し、両尺度で初期CONSTRAINTS_VIOLATED/採用値null→最終SEARCH_COMPLETEの同じ試行列と公開replay一致。新しいFEM実行とは主張しない。最終球形解析f2.472e-5/RQ2.525e-6/G1.077e-7/E比2.314e-4/B比6.077e-6で既存独立許容差PASS。driverはoutに保持。
標準44857終了0、out/validation-rf-optimization-20260909、734件732合格・2skip、991.980秒。seed9モード19量f差0/RF最大8.882e-16。標準/独立/追加再評価/終了後422対象hash一致。新規JobManager/GUI/ブラウザーなし。全関連実行は終了、ソース固定解除。

D03親/全体計画は未完了、親8受入/8進行中/16他未受入/1候補=33。次は既存tuning_jobs等を参照して、このRF探索のJobManager中止・チェックポイント読込/再開とGUI操作へ接続する。3解の試行単位の保存と途中失敗を分け、元ジョブへの所属・改変拒否・管理器再起動を検証する。原始評価器surface_convergenceの制限を引き継ぎ、反射/組立/curved_refinement_steps配列（一様だけでも）・一般変数/せん断は未対応。curved_refinement_levelsは対応。一般性能/任意形状の受入と最適性/物理誤差保証は残る。既存場の再読込を何度も行うため小例題の実行/完全replayにも数分を要する。効率改善は証拠一致を保った独立課題とする。

## 最新: D03 RF設計制約評価基盤 — 2026-09-09

[仕様・証拠](RF_DESIGN_CRITERIA.md)。基準3b80839。rf_design.pyはstrictな一目的関数/複数制約、既存の保存個別追跡付き固定曲線P2三水準の再検証、最後3区間の包絡を実装。全区間内MET/全区間外VIOLATED/重なりUNRESOLVED。既存表面収束・形状診断未達ならUNVERIFIED。CRITERIA_METだけが最大化の下端/最小化の上端をeligible_valueとして持ち、他はnull。回路RQは定義どおり加速器RQの半分を外向き丸め。観測包絡は物理誤差上界でない。保存・再読込・全文書再構築照合あり。API基盤のみ、探索器/CLI/Job/GUIは未接続。

開始時56875終了0、既存表面5件21.806秒。追加初回8100終了1、quantity配列2例がTypeErrorとなるstrict検査の不備。数量名の型確認でValueErrorへ修正、64878終了0、5件21.539秒。最初の修正用コマンドはpythonがPATHになく終了127で無変更、その後.venv/bin/pythonで適用。初回/修正後/基準ログはout/rf-design-independent-20260909に保持。
独立85428終了0、out/rf-design-independent-20260909。球形両尺度・正規化1/4 J、36/144/576要素の新規FEM。独立球形解析f最大2.483e-5/RQ6.489e-6/G8.807e-7/E比2.657e-4/B比3.847e-5。先に指定した解析6量±5%の設計制約と既存の厳しい収束停止を両方PASS、意図した周波数制約違反は採用値null。全包絡相似差最大4.930e-14、保存再検証PASS。
最終標準61901終了0、out/validation-rf-design-20260909、729件727合格・2skip、612.057秒。seed9モード19量f差0/RF最大8.882e-16。標準/独立/内部FEM/終了後417対象hash一致。新規GUI/ブラウザーなし。全関連実行終了、ソース固定解除。

D03着手により親集計8受入/8進行中/16他未受入/1候補=33。次はD03の有限予算・複数変数探索を仕様化して実装する。曲線Project共通baseのradial/axial変形と相対写像で個別IDを継承し、初期/最終の独立細分、全試行と失敗、停止/予算/保存再開を接続する。制約違反から実行可能領域へ移る方針と、未確認を採用しない条件を区別する。本評価器は既存surface_convergenceの制限（native曲線P2、段数増分、同じ元mesh/Case）を引き継ぎ、局所履歴や直線P1/P2は未接続。大域最適性・物理誤差の証明はしない。D03親と全体計画は未完了。

## 最新: O02 外部mesh単体GUIと直線固定Study — 2026-09-09

[外部mesh操作](EXTERNAL_MESH_WORKFLOW.md)。project_mesh_operations.replace_project_meshはCase/Projectと新meshをstrict検証後に置換/解除。古いmeshが編集後のCaseと合わなくても置換可能で、他のCase/Projectフィールドはstrictのまま。raw JSONのduplicate keyとファイルnullは拒否し、明示null操作のみ解除。marked履歴は旧/新（自動生成へ戻す場合も）の完全一致がないと拒否し、履歴を明示解除させる。GUIreplace-mesh操作、file picker/解除・失敗時保持/保存/実計算へ接続。
Study.fixed_geometry_convergenceはgeometry_order=1の明示meshでもadditional_uniform_refinementsの0,1,2…を受理。既存共有辺splitterで全辺を分割し、元頂点番号/境界タグ/多角形を維持。250000またはcontour_mesh.max_trianglesを事前の4^levelで検査。曲線二次の既存経路/文書は維持。追加の角度閾値を導入しない。GUI固定Studyのラベル/項目/説明も直線対応。
基準22d51af標準720件を確認。開始時21680終了0/11件5.213秒。旧Studyモジュールに新しいP1/P2不変量試験を適用すると未対応として拒否（旧コードは/tmp別モジュールで読み、製品は巻き戻さない）。unit初回はelement_geometryの戻り値の取り違え1ERROR、次に点配列を面積にして失敗。det/2に修正し4件0.376秒PASS。ログはout/external-mesh-interface-20260909に保持。
独立初回は保存P1解にmassがないのにquantitiesを呼んで失敗、検証器を実FEMのRF出力読込へ修正。70882終了0、out/external-mesh-study-independent-accepted-20260909、P1/P2×尺度1/2の24→96→384要素、Ritz/解析f（P1最大2.963e-5/P2最大6.788e-8）/Maxwell f・両RQ・G（最大3.709e-14）、CLI/Python Study全3段のmodes完全一致、管理器再起動PASS。失敗outは保持。
Chrome68081終了0、out/browser-external-mesh-20260909、26項目PASS/外部要求0。単体読込/解除・不正duplicate keyで保持、Project保存/FEM/適応引継ぎ、直線Study生成/実計算/表示と既存調整を確認。GUI54203/PID448617はSIGINT停止終了0、新規画像目視なし。out/external-mesh-interface-20260909は終了0、同じGUI入力でCLI/Python/GUIのmodes/mesh完全一致、GUI/Python Studyの2段完全一致、管理器再起動PASS。独立/経路一致/終了後414対象とChrome対象hash一致を確認。
標準15142終了0、out/validation-external-mesh-20260909、724件中722合格・2skip、579.489秒。seed9モード19量f差0/RF最大8.882e-16。標準/独立/CLI・Python・GUI経路比較/終了後414対象hashとChrome対象hashが一致。全関連実行/GUI終了、ソース固定解除。22d51af基準。
親集計は8受入/7進行中/17他未受入/1候補=33。実装状況の進行中一覧に抜けていたO02を追加し、対応表/計画の外部mesh項目を更新した。O02全体は高次/追加物理の各統合・到達点再受入が残る。次は計画の依存と親要件を照合し、O02の残件を未実装物理から区別して進める。全体計画を完了扱いしない。

## 最新: D02 曲線アフィンtuneと直交角の保存評価方式 — 2026-09-09

[曲線tune](CURVED_TUNING.md)第4版。curved_tuning.pyの3多項式係数から同じbase Project/元メッシュを毎回変形、親試行→現在の相対写像を導出する。rf_coordinatesはfixed/axial必須、controls.mapping=affine_remeshだがユーザーaffine_mapは拒否。refinement_scaleは2の累乗で元二次写像の一様制限を追加し、局所履歴も維持する。既存tuning._request/_project/_assembleへ接続、CLI/JobManager/再起動/GUI入力復元・再開・場表示へ接続。例題examples/tuning/curved_affine_scale.json。v1～3の分岐/保存は維持。
直前基準01f541a標準712件を確認、調整関連baseline89779終了0/32件46.019秒。新API redの後4件42.009秒、CLI/管理器再起動を足して30423終了0/5件97.049秒。最初の標準42294終了0、out/validation-curved-tuning-20260909、717件715合格/2skip、584.112秒。初回円筒独立92723終了0、out/curved-tuning-independent-20260909、m/1×尺度1/2全4系列各4試行TUNED、TM011順位3→2、最終解析f差1.393e-6、長さ差2.221e-16、f/両RQ/G相似・単位差最大1.621e-14。初回標準/独立/旧保存再検証/終了後410対象hash一致。
Chrome初回18415終了1は私のbaseline入力を6×8へ粗くしたため既存profileがREFINEMENT_FAILED。製品/許容差を変更せず、以前の12×16/1e4 Hz入力に戻し11413終了0/20項目PASS/外部要求0。GUI73938/PID399329はSIGINT停止終了0。旧v1/v2/v3の17/15/18試行TUNED保存の完全再検証79265終了0、out/curved-tuning-legacy-replay-20260909。
追加鏡映50932終了1はz_max半楕円の1.2倍で接続証明UNVERIFIED。半軸だけ伸縮する試作も同じ失敗で、cos(pi/2)残差が中心.12 mに加算され1 ulp端面外側へ出るためと特定。接続許容は緩和せず[直交角評価](EXACT_CARDINAL_ELLIPSE.md)を保存方式として実装。EllipseArc.parameter_evaluation省略/numpyは従来値/JSONキー不変、exact_cardinalはθが厳密にk*(pi/2)と等しいときだけsin/cosを0/±1にする。隣接floatはスナップしない。非恒等アフィン楕円に方式を明示、恒等変換/旧保存は従来どおり。
別置き試作88574終了0/左右両対称変形と旧native読込、53165終了0/関連23件5.974秒。初回標準と円筒独立の終了後に製品へ反映。追加3検査0.757秒PASS。最終鏡映81801終了0、out/curved-tuning-reflection-accepted-20260909、同じ[1,1.2]を保ち左右×両対称の4例各2試行PAUSED/追跡/再検証/位相原点0がPASS。失敗ログも同ディレクトリへ保持。
最終Chrome48415終了0、out/browser-curved-tuning-final-20260909、20項目PASS/外部要求0。GUI30970/PID419627はSIGINT停止終了0。新規スクリーンショット目視なし。最終再検証45953終了0、out/curved-tuning-final-replay-20260909、円筒4系列全試行と過去の楕円/双曲線/円筒nativeを現在の実装で再読込。初回円筒FEMは全てLineSegmentで、追加評価方式は使用しない。初回後の差はconics.py/affine_conics.pyと追加testのみとcoverage.jsonへ明記し、最終FEMを再実行したとは言わない。正の二乗倍率20387終了0、out/curved-tuning-polynomial-20260909、両単位表現の実FEM相似最大8.405e-14、独立べき乗和12比較PASS。
最終標準57435終了0、out/validation-curved-tuning-final-20260909、720件中718合格/2skip、588.051秒。seed9モード19量f差0/RF最大8.882e-16。最終標準/円筒再検証・旧native/鏡映/二乗倍率/終了後411対象hashとChrome対象hashが一致。初回円筒FEMとの3ファイル差はcoverage.jsonに明記済み。全関連計算/GUI終了、固定解除。01f541a基準。
親8受入/7進行中/17他未受入/1候補=33は維持。アフィン曲線tuneを接続したが、非アフィン曲線編集/任意関数の連動・任意局所細分の輸送・制約付き多変数最適化・全体計画は未完了。次は対応表/計画のD02残件とD03等を再照合し、実測された制約を保った次の機能へ進める。

## 最新: D02 曲線Project一括変形 — 2026-09-09

[仕様・証拠](CURVED_PROJECT_TRANSFORM.md)。curved_project_transform.transform_curved_projectは元Case/メッシュを新しいProject第2版へアフィン変形し、元の自動弦分割も固定数へ確定する。元メッシュ未指定なら元形状で一度生成。rf_coordinatesは必須fixed/axial、間隙・最小曲率/生成/品質/材料/正規化条件は固定、弦/接合近似予算は最大特異値で伸縮して再検査。二次空間の各履歴prefixの接続/点/境界fractionを照合し、最長辺/対角線選択が変わる局所細分はUNVERIFIED拒否。relative_affine_mapは同じbaseからの2変形のcurrent @ inverse(previous)を導出する。
開始時59659終了0、706件704合格・2skip、477.917秒。API未存在で追加検査red。別置き試作93329終了0/5件2.129秒、試作独立86936終了0/8例は最終証拠と区別。鏡映追加58964終了1/6件2FAILは、未指定phase_origin_mを明示0にした際のz_min反射後の原点移動。未指定は未指定のまま保つ修正で既存の全体空洞既定0を維持、明示原点は変換後に既存の鏡映規約を適用。最終unit71542終了0、6件3.792秒。左右×両対称の実Job/保存RF条件も確認した。
最終独立82969終了0、out/curved-project-transform-final-20260909の8例。楕円/双曲線/円筒/円錐の通常Job保存再読込、相似4例最大1.710e-14、円筒解析f2例最大1.053e-7、円錐せん断も含む体積a²c則最大1.111e-16、二次点誤差最大2.776e-17 m、相対写像での実追跡4例PASS。局所細分追加63640終了0、out/curved-project-marked-20260909、marked集合[0]/[0,2]→uniformの0.5/2倍4例、100/108要素接続/保存完全一致、f/両RQ/G相似最大3.753e-14。driverとsource hashを保持。
最終標準98159終了0、out/validation-curved-project-transform-20260909、712件中710合格・2skip、481.768秒。seed9モード19量f差0/RF最大8.882e-16。標準/最終独立/局所細分追加/終了後406対象hashが一致。GUI変更なし/新規Chromeなし。全関連実行終了、ソース固定解除。主ツリーe30a312を基準とする。
次はtuning.pyの_request/_project/_assembleを曲線アフィン試行へ接続する。各試行は同じbaseから変換し、親試行→現在の写像を上記relative_affine_mapから導出してbuild_saved_mode_trackingへ渡す。固定ユーザー写像の使い回しは不可。最終細分は元二次幾何の一様制限として追加し、再メッシュ/再投影しない。旧v1/v2/v3文書と判定は保持、曲線版の単位・係数・RF方針・無効内部形状・保存再開・CLI/Job/GUIを明示検証する。局所履歴の任意変形は分割選択そのものの輸送契約が未実装。親8受入/7進行中/17他未受入/1候補=33、全体とD02未完了。

## 最新: D02 曲線と元メッシュの固定分割契約 — 2026-09-09

[弧ごとの分割数](FIXED_CURVE_PARTITIONS.md)を限定受入。Case v3 geometryの任意segments_per_curveを正整数配列としてstrict受理、Pythonではtuple。既存弦誤差上界と接合補正の予算内でuniform fraction分割を保持する。不足時は拒否し自動増加しない。曲線二次写像・native保存/再構築・鏡映・GUI入力復元/保存へ接続。例題examples/projects/curved_fixed_partition.json。
独立不変量は非等方変形後の対応点/Jacobian、実モード追跡、Maxwell相似と鏡映。初回4検査1ERRORは細分済み辺数を元分割数と取り違えた検証入力。元ChordApproximationから数えて修正、4件1.629秒PASS。初回独立は接合許容長の尺度変換漏れで拒否、標準終了後に検証scriptだけを修正し6例PASS。製品の許容差は変更しない。失敗ログはout/curve-partitions-independent-accepted-20260909に保持。
標準59355終了0、out/validation-curve-partitions-20260909、706件中704合格・2skip、484.571秒。9モード19量seed周波数差0/RF最大8.882e-16。修正後独立77329終了0、点尺度誤差2.776e-17/Jacobian差1.111e-15/f・RQ・G相似差5.330e-15以下、実追跡6例と保存一致PASS。standard-coverage.jsonは標準後の独立scriptだけの差を明記。現在/独立403対象とChrome対象hash一致。
Chrome12522終了0、out/browser-curve-partitions-20260909の22項目PASS/外部要求0。GUI3237/PID342316はSIGINT停止後PID消滅を確認、終了コードの再取得は不可。新規スクリーンショット目視なし。全実行終了、固定解除。主ツリー960c9f3基準。
次はCase/曲線/元メッシュを一括変換するProject操作と、tune各試行の写像導出。今回の明示分割は境界対応を維持するための前提のみ。RF評価区間・最小曲率/間隙条件等の固定/連動も明示してから接続する。親8受入・7進行中・17他未受入・1候補、計33は維持し、計画全体とD02は未完了。

## 最新: O02/D02 Project第2版の明示元メッシュ — 2026-09-09

[Projectメッシュ](PROJECT_MESH.md)を限定受入。版2必須mesh_dataを既存strictメッシュ検査で正規化・コピーし、通常Jobのsolveへ渡す。旧版1文書は不変。GUIフォーム/保存/実行/結果読込で保持、明示使用表示・新規時解除、曲線図上選択と適応initial_meshへ接続。固定曲線細分Studyは元メッシュを維持、他Study/tuneは試行ごとの変形契約がないため明示拒否する。完全Project例題はexamples/projects/explicit_mesh.json。メッシュ単体専用インポートや曲線tune接続は残る。
Project試験初回はJobManagerの未対応context managerを検証器が使って1ERROR。close契約へ修正し8件0.694秒PASS。後に番号置換前とのf一致と実行中project変更の検査を追加。変更検査は旧実装でred、jobsが開始時project hashを保持し、終了時照合とmanifestへ同じhash使用を追加。9件0.761秒PASS。ログはout/project-mesh-final-20260909に保存。
最初の標準30857は終了1、out/validation-project-mesh-20260909、701件中697合格・2ERROR・2skip、478.010秒。Project例題をCase専用examples直下へ置いたため既存Case往復検査が拒否。専用サブディレクトリへ移し、パーサーと既存検査のstrict契約を維持した。
Chrome49357は終了1、out/browser-project-mesh-20260909。適応入力生成前の空欄をJSONとして読む待機条件の不備。製品ソースを固定し/tmpの修正版で87258再実行、21項目PASS/外部要求0/終了0。GUI70632/PID306042は正常停止終了0。初回標準終了後、待機修正をscriptsへ反映し、入力hash補強と例題移動を含めて最終検証を全て再実行した。
最終独立62882は終了0、out/project-mesh-final-20260909。P2円筒の両尺度解析/両RQ/G相似（最大1.510e-14）、左右×両対称4曲線鏡映（既存経路f差最大6.662e-16）、曲線固定Study16→64要素/Ritz/元メッシュ保持がPASS。最終Chrome67950は終了0、out/browser-project-mesh-final-20260909の21項目PASS/外部要求0。GUI53953/PID319924は正常停止終了0。新規スクリーンショット目視なし。
最終標準83910は終了0、out/validation-project-mesh-final-20260909、702件中700合格・2skip、unittest476.257秒。seed9モード19量f差0/RF最大8.882e-16。最終独立/標準/終了後399対象hashとChrome対象hashが一致。全関連実行は終了、ソース固定解除。主ツリー83fd8faを基準とする。
O02着手として親集計は受入8・進行中7・他未受入17・拡張候補1、計33。O02/D02全体と全体計画は未完了。次はアフィン曲線/Case/元メッシュの同時変形とtune試行間写像の導出。Caseの自動弦分割と変形した元メッシュの境界対応が一致するかを独立に検査し、異なる二次境界を黙認しない。RF評価区間/最小曲率条件等の固定・連動も明示する。

## D02曲線調整のアフィン幾何基盤 — 2026-09-09

[アフィン弧変換](AFFINE_CONIC_TRANSFORM.md)を限定受入。affine_conics.transform_curveは既存affine_mapで線分・回転楕円・双曲線両枝を変形し、同じfractionの対応を保持。楕円SVD角シフト、双曲線直交化の双曲線シフトでnative形式へ戻す。分解再構成/正方向/直交性と4096εの解像条件を検査、未確認を拒否。閉輪郭やCaseの妥当性は別検査であり、tune接続は未実装。
新API未存在でred失敗。その後3検査0.400秒PASS。点/接線/曲率/面積/逆変換、strict/未解像拒否、native二次メッシュを明示2倍にした実FEM/追跡/f/RQ/Gを確認。ログはout/affine-conics-random-accepted-20260909/tests-{red,initial,native}.log。
乱数初回は入力にNumPy scalarを使った検証器の誤りで変形前に拒否。out/affine-conics-random-20260909/failure.jsonを保持。built-in floatへ修正し、out/affine-conics-random-accepted-20260909/validation.jsonは360例/3尺度/各33fractionでPASS。位置/接線/曲率誤差最大1.777e-15/1.728e-15/2.887e-15、基準1e-10は不変。有限標本を全域証明としない。
標準90413は終了0、out/validation-affine-conics-20260909、698件中696合格・2 skip、unittest474.010秒。seed9モード19量f差0/RF最大8.882e-16。独立/標準/終了後397対象hash一致。新規GUI/ブラウザー検証なし。全関連プロセス終了、ソース固定解除。主ツリーcb39acaを基準とする。
次の接続点を文書化。jobs._execute_preparedはsolve(project.case)を呼び、Projectに明示元メッシュの保存項目がない。solver自体のmesh_data/native保存は既存。O02/D02の版付きProject/Jobメッシュ入力契約を先に整え、同じ元メッシュ/曲線を変形してM_current M_parent^-1で追跡する。独立再メッシュで二次境界が同じと仮定しない。RF区間・製造制約の固定/連動も明示する。曲線tune・親D02・全体計画は未完了、受入親数8を維持。

## D02多項式の非線形座標連動 — 2026-09-09

[多項式連動](POLYNOMIAL_TUNING.md)を限定受入。tune request版3は版2と同じ項目、bindingはpath/coefficients（定数項から昇順）。Horner評価して全profile座標を同時更新。単位はm/(変数単位)^k、変数はm/無次元。各試行で形状検査、内部不正はfailureと先行保存を残して停止。全範囲有効性/単調性/全根を証明しない。FEM/追跡/二分法/最終ゲート不変。GUI式選択・係数/単位復元と例題pillbox_radius_squaredを追加。
初回62543は9検査中1FAIL、12.047秒。係数1e308をオーバーフローとした試験誤り（x=1.1では有限）を1.79e308へ修正。実装許容差変更なし。26008は9件12.287秒、終了0。初回/修正後ログをout/polynomial-tuning-20260909に保持。
独立4035は終了0、out/polynomial-tuning-20260909。長さ/無次元×尺度1/2を実JobManager再起動・再開で全18試行TUNED。半径解析差最大9.376e-7、最終形状f解析差4.337e-9。f/RQ/G相似最大4.475e-14、単位変更最大7.805e-14。旧自作5936dceをgit blobからout/polynomial-tuning-legacy-20260909へ保存し、旧版が多項式未対応であること、版1/2の実2試行checkpointが新旧replay全文書一致することを検証。
Chrome26897は終了0、out/browser-polynomial-tuning-20260909の27項目PASS/外部要求0。版1/2・取消し復旧を含む23項目と多項式4項目。polynomial-result.pngを実表示。GUI47069/PID259711はSIGINT正常停止、終了0。rawジョブはout/gui-polynomial-tuning-20260909に保持。
標準80226は終了0、out/validation-polynomial-tuning-20260909、695件中693合格・2 skip、unittest476.626秒。seed9モード19量f差0/RF最大8.882e-16。標準/独立/旧版比較/終了後の395対象hashとChrome対象hash一致。全関連実行は終了、ソース固定解除。主ツリー5936dceを基準とする。
README/対応表/計画/実装状況/TUNINGの非線形未対応記述を同期した。親D02の一般曲線/非多項式連動、D03制約付き最適化と他親課題は継続。親受入数8は増やさない。次はD02一般形状の写像・変形契約、D03の独立細分を含む制約付き設計、または他未完親課題の実装へ進む。

## 周波数調整の途中保存一覧・復旧 — 2026-09-09

[D02 GUI復旧](GUI_TUNING_CHECKPOINTS.md)を限定受入。停止したtuneジョブに「途中保存を選ぶ」を追加し、保存済み試行を未検証候補として一覧表示。選択時は公開replayに加えて元ジョブrequest、保存番号、今回の試行の所属、再開前祖先を照合する。PAUSEDだけ既存操作で別ジョブへ再開する。空一覧/改変/別ジョブ差替え/symlink/実行中を拒否・区別。FEM/追跡/二分法/最終ゲート不変。
API91592は終了0、5検査17.017秒。実中止→管理器再起動→最初の保存を選択→1試行追加を確認。ログは標準out/gui-tests.log。
Chrome84581は終了0、out/browser-tune-checkpoints-20260909の17項目PASS/外部要求0。従来13項目に空一覧、未検証一覧、前の保存選択、実中止後再開を追加。checkpoint-recovery.pngを実表示。復旧元20260909-092352-af4bd6dd68はcancelled、再開先20260909-092355-7a9ef2eed0はcomplete/PAUSEDで2試行。rawジョブはout/gui-tune-checkpoints-20260909に保持。GUI64611/PID238249はSIGINT正常停止・終了0。
標準46473は終了0、out/validation-tune-checkpoints-20260909、692件中690合格・2 skip、unittest471.722秒。seed9モード19量f差0/RF最大8.882e-16。標準392対象ファイルと終了後source、Chrome対象hash一致。全関連実行は終了しソース固定解除。主ツリー6b2a592を基準に実装した。
README/対応表/計画/実装状況/TUNINGの残件を同期。親D02の一般形状/非線形変数とD03の制約付き最適化は残る。次はD02の残る設計変数/形状契約か、他未完了親課題の実装へ進む。親課題の受入件数8は増やさず、全体目標を継続する。

## 二次境界の空間候補選別 — 2026-09-09

[限定受入](QUADRATIC_BOUNDARY_CANDIDATES.md)。curved_spaceの既存箱木をbox_candidatesへ移し、check_quadratic_boundaryにも適用。厳密に分離した箱だけを除外、隣接辺と辞書順を維持。boxes_checkedは旧相当の論理数であり実呼出し数ではない。FEM式・許容差・探索上限を変更しない。
正64角形の呼出し検査は変更前1,952回でFAIL、変更後に関連9件PASS。旧自作d319dc2のモジュールと24条件で証明/最初のエラー完全一致。git blob照合済み。独立測定out/boundary-candidates-comparison-20260909はPASS、交互3回中央値で正512角形0.911→0.0366秒、native 2,744辺23.975→0.203秒。境界単体であり全workflowの速度とは扱わない。native入力は中断実験event-028から取り、元実験の完走とは扱わない。
標準out/validation-boundary-candidates-20260909はPASS、690件中688合格・2 skip、unittest469.939秒、子コマンド終了0。seed9モード19量f差0/RF最大8.882e-16。独立/標準/終了後の全392対象hash一致。新規ブラウザー検証なし。ログは各out/execution.logにも保存。
独立・標準プロセスは終了済み（標準PID213861/213862消滅と最終PASS報告確認）。実行ハンドルは出力切詰めで失われたため親の終了コードを再取得したとは記録しない。ソース固定解除可。主ツリー上の変更で、前回統合d319dc2を基準とする。次は未完了親課題の仕様/受入条件を再照合する。N04一般精度/効率と全体計画は継続中。

## RF適応の改善を主ツリーへ統合 — 2026-09-09

fc76e64（祖先ジョブの観測時間）、81fc416（次計画共有）、ee455eb（明示した表面細分方針）を主ツリーへ統合。README/対応表/計画/実装状況を更新。主ツリーの検証対象384ファイルはee455ebの実装・tests・scripts・examplesと完全一致。主ツリーだけにあるeditable-install egg-info 6ファイルは統合前から不変。installed .venvで主ツリーの新request検証/importもPASS。
標準689件（687合格・2 skip、472.620秒）、実Chrome19項目、旧文書全prefix一致、CLI、非球形両尺度、最終公開native replayが完了。標準後の変更は比較scriptの初期同一性修正だけで、修正後に両尺度を再実行PASS。数値コア/GUI/全testsは標準時点と一致。新しく全件回帰を主ツリーで繰り返したとは扱わない。
両尺度は同じ12回予算/初期写像/五量許容差で6イベント、最終7232要素/14665自由度。親採用と停止合格を区別し、未達確認採用の合格数0から一様2回合格。追加参照との差、Ritz、初期一致、体積、Maxwell最大4.923e-13がPASS。全execute104.942/105.398秒。参照は以前の自作一様FEM reportであり、絶対RF誤差上界ではない。詳細は[明示方針](CURVED_RF_SURFACE_POLICY.md)。
関連summary・スクリーンショットを主ツリーoutへコピーし、各source-location.jsonに元パス/hashを記録。native実出力と絶対パスcheckpointは /tmp/superfish-rf-cost-worktree-20260909/out に保持。移動/削除しない。out/rf-surface-nonsphere-accepted-20260909/integration-source-check.json が統合照合証拠。
従来の12回R/Q単独は両尺度LEVEL_LIMITを保持。任意の48回拡大60815/PID76757は新方針の両尺度完走を受けてSIGINT、終了130。checkpoint27/solveログ28、直前観測4745秒。中断を完走や尺度2結果と呼ばない。interruption.jsonと全native出力を保持。
全プロセス・GUI・ブラウザーは終了済み。ソース固定なし。次は未完了親項目の再照合と、必要ならnative空間再構築/曲線境界ペア検査の改善。中断スタックはnested transfer再構築→check_quadratic_boundary→separated_edges。公開拒否と既存文書/数値一致を維持して実測する。N04一般精度/一般効率と全体計画は未完了。

以下は統合前の時点別記録。進行中/未統合/未実装という表記は当時の状態を示す。

## 明示した表面細分方針の検証完了 — 2026-09-09

[方針と証拠](CURVED_RF_SURFACE_POLICY.md)。版5任意surface_refinement_policyを追加。未指定/rf_goalは旧動作、uniform_when_rf_passesはRF三量合格・表面だけ未達時に確認解を次の親へ採用し、合格数0から一様細分。五量連続2回だけで停止する。GUI明示選択/未達表示/方針復元/一様再開、CLI例題を追加。
新4検査12983は32.842秒で終了0。CLI70586は終了0。Chrome17410は19項目PASS/外部要求0で終了0、rf-surface-progress.png実表示、GUI80722/PID161243は停止終了0。旧文書比較81886は終了0、旧fc76e64と半球/非球形初期5イベント全prefix/最終文書完全一致。
初回非球形89100は両尺度6イベントTARGETS_METだがverifierの初期一致式が区間幅を差に算入して終了1。端点は完全一致で差0、誤った差約3.686e-7。out/rf-surface-nonsphere-initial-20260909 と診断を保持。
標準99231は終了0、out/validation-rf-surface-policy-20260909 は689件/687合格/2 skip、472.620秒PASS。seed9モード19量f差0/RF最大8.882e-16、終了時全source/旧文書比較/browser対象hash一致。標準終了後、scripts/validate_curved_rf_nonsphere.pyの初期同一性だけを対応端点差へ修正。数値コア/GUI/全検査は不変。標準をこの修正後に再実行したとは扱わない。
修正後78250は終了0、out/rf-surface-nonsphere-accepted-20260909 両尺度PASS。同じ12回予算/初期写像/五量許容差、80→320未採用→113→452未達の親採用→1808→7232、6イベント/14665自由度。合格数0,0,0,0,1,2。追加一様対照164481自由度に対するf/RQ/G/E/B差は全基準内、Ritz/初期一致/native解析体積/固定体積/Maxwell（最大4.923e-13）PASS。全execute104.942/105.398秒、全solve12.224/12.249秒。過去版4/一様時間とは同一プロセス試験でない。
最終native replay51871も終了0、out/rf-surface-native-replay-20260909。両尺度checkpoint006をeigsh禁止で公開再検証、文書完全一致91.725/91.673秒。最終sourceと修正後両尺度/再検証hash一致、標準との差は比較script1本だけ（standard-coverage.json）。
主ツリー旧48回拡大60815/PID76757は、新方針が元の12回予算で両尺度PASSとなったためSIGINT、終了130。直前観測4745秒、verified checkpoint027・solveログ28。out/curved-rf-nonsphere-expanded-20260909/interruption.jsonと全出力を保持し、純RFの完走/尺度2結果とは扱わない。主ツリーのソース固定は解除できる。中断スタックはnested transferでの空間再構築とcheck_quadratic_boundary/separated_edgesにあった。
全関連実行は終了。現在は/tmp/superfish-rf-cost-worktree-20260909、branch feature/rf-surface-uniformで、費用表示fc76e64と次計画共有81fc416を祖先に含む。主ツリー統合と証拠summaryの保存が必要。N04/RFA一般精度/一般効率/全体計画は未完了。次の性能課題はnative空間再構築と境界検査の共有/候補選別（公開拒否と文書一致を維持）。

## 版5次計画の実行内共有 — 2026-09-09

[共有化](RF_ADAPTIVE_PENDING_PLAN.md)を /tmp/superfish-rf-cost-worktree-20260909 のbranch perf/rf-adaptive-pending-planで実装。親/確認からRF選択を導出した次計画をVerifiedRFPrefixへ一つ保持し、実装/request/祖先/native snapshot照合後だけ再利用。公開replayは全判断を再導出、新保存場のCase/mesh/二次写像照合も維持する。数値文書や停止条件の変更はない。
呼出し回数red71948は終了1（旧2回）。変更後65973は6検査25.070秒で終了0。実3イベントRF選択1回、元親・marked対応、公開replay完全一致、変更拒否、外部decision変更が内部へ伝播しないことを確認。
旧自作モジュールfc76e64をout/rf-pending-baseline-20260909へ保存し、git blob hash完全一致を確認。比較11865は終了0、out/rf-pending-comparison-20260909。半球/非球形初期5イベントを旧/新同一プロセスで交互3回。各prefix全文書とnative入力最終文書が完全一致、eigsh禁止。RF選択は2→1/4→2回、中央値5.533→5.127秒/16.805→14.238秒（旧/新1.079/1.180）。新solve/保存を含む全workflow時間ではない。
標準3145は終了0、out/validation-rf-pending-20260909 は685件中683合格・2 skip、434.058秒PASS。seed9モード19量f差0/RF最大8.882e-16、最終全対象sourceと標準/独立比較hash一致。新規ブラウザー検証はなし（先行費用表示はfc76e64でChrome15項目PASS）。共有化側の実行は全て終了。
主ツリーmainの非球形60815/PID76757は引き続き実行中（ログ/tmp/curved-rf-nonsphere-expanded-20260909.log）。その終了まで主ツリーsrc/tests/scripts/examplesは固定する。費用表示fc76e64と本変更は主ツリーへ未統合。現在の作業ブランチは費用表示コミットを祖先に含む。
次は[表面だけ未達時の明示的一様細分方針](RF_SURFACE_CONFIRMATION_PLAN.md)の検討/実装、または残るnative空間再構築共有。現状のR/Q選択はEpk差約2.4%で停滞する非球形例を抱える。方針を加えるなら旧request未指定は旧動作、五量2回連続合格だけで停止、未達確認を親へ採用しても合格数0とする。案は未実装であり受入済みと呼ばない。元の難しい非球形/尺度/許容差を維持して検証する。
全体目標、RFA-6、親N04は未完了。主ツリーへの統合時に両ツリーの最新引継ぎ・計画を保つ。

## 適応祖先ジョブの時間表示 — 2026-09-09

[費用表示](GUI_RF_ADAPTIVE_COST.md)を追加。native checkpoint再検証後、現GUI作業領域内の所有者ジョブをrequest/祖先sourceと照合して一度ずつ時間を合算。中止時にも経過時間を保存。未知/欠測/外部は部分合計と不明回数を表示する。
数値checkpointの文書・保存文字列は不変。GUI応答のexecution_costは観測metadataなので、ジョブ状態が変われば再計算する。記録されたworker時間であり、事前検証を含む全workflow時間ではない。保存場のない別試行は祖先に入らない。
2検査PASS、実JobManager5176は7検査19.203秒で終了0。実Chrome3062は終了0、out/browser-rf-cost-initial-20260909 の15項目PASS/外部要求0。3ジョブ合算、保存再読込、中止→再開、外部不明を実FEMで確認。rf-branches.pngを実表示済み。GUI85156/PID103279は引数確認後停止、終了0。
最初の標準48730は終了1、out/validation-rf-cost-20260909 は683件/680合格/1失敗/2 skip、426.102秒。時間記録を消した後も応答全体一致を要求した旧GUI検査を、数値文書/保存文字列完全一致+欠測不明の検査へ更新。GUI65956は5検査33.329秒で終了0。数値実装や許容差の変更ではない。
最終標準60286は終了0、out/validation-rf-cost-accepted-20260909 は683件/681合格/2 skip、428.580秒PASS。seed9モード19量、f差0/RF最大8.882e-16。全対象sourceと標準、browser対象hash一致。全費用表示検証は終了。
この変更は /tmp/superfish-rf-cost-worktree-20260909、branch feature/adaptive-refinement-cost。主ツリーmainは01aa584の非球形検証を実行中（60815/PID76757、out/curved-rf-nonsphere-expanded-20260909、ログ/tmp/curved-rf-nonsphere-expanded-20260909.log）。主ツリーsrc/tests/scripts/examplesはその終了まで固定。先に変更を混ぜない。
主ツリーの12回上限は両尺度LEVEL_LIMIT。48回検証はまだ尺度1途中で、Epk差約2.4%が停滞。プロフィール89107は終了0、out/curved-rf-nonsphere-profile-20260909 で親1723/確認6892要素の読込27.766秒/指標36.873秒。指標はcheckpointと完全一致。再構築/辺検査の重複が主因候補。全workflowプロファイルではない。
次は非球形の実行結果確認・記録、主ツリーへの費用ブランチ統合、検証済み空間の実行内共有の検討。RFA-6/親N04/全体計画は未完了。

## 統合前の主ツリー記録（進行中表記は当時の状態）

### 最新: 次計画共有も別ブランチで検証済み — 2026-09-09

/tmp/superfish-rf-cost-worktree-20260909 は現在branch perf/rf-adaptive-pending-plan、HEAD81fc416。費用表示fc76e64を祖先に含む。主ツリーへは未統合。主ツリーsrc/tests/scripts/examplesは60815終了まで固定する。
81fc416は、VerifiedRFPrefixに一つの次計画を保持し、実装/request/祖先/native sourceを再照合した後だけ使う変更。実行3イベントのRF指標は2→1回、公開replayと全数値文書は不変。新規保存場のCase/mesh/二次写像照合も残る。
呼出し回数red71948は終了1、変更後65973は6検査25.070秒で終了0。比較11865は終了0、別ツリーout/rf-pending-comparison-20260909。fc76e64モジュールはgit blobとhash完全一致。半球/非球形初期5イベントで、全prefixと入力最終文書が旧/新完全一致、eigsh禁止。3回交互中央値は5.533→5.127秒/16.805→14.238秒、RF選択2→1/4→2回。incremental assembleのみで全workflow費用ではない。
標準3145は終了0、別ツリーout/validation-rf-pending-20260909 は685件/683合格/2 skip、434.058秒PASS。seed9モード19量f差0/RF最大8.882e-16、最終全対象sourceと標準/独立比較hash一致。共有化側の実行は全て終了。新規ブラウザー検証は行っていない。費用表示のChrome15項目はfc76e64時点の証拠。
主ツリー非球形60815/PID76757は実行中、/tmp/curved-rf-nonsphere-expanded-20260909.log。直近はcheckpoint-026.json PAUSED/31224要素確認、イベント27の11182要素局所solve後の評価中。観測タイムアウトで再起動しない。
次の候補は別ツリーdocs/RF_SURFACE_CONFIRMATION_PLAN.md（未実装）。R/Q選択だけでは表面ピーク差約2.4%が停滞するため、RF三量合格・表面だけ未達時は確認解を次の親へ採用し、合格回数0から一様細分を続ける明示指定を検討。旧request未指定の判断は変えず、五量2回連続合格だけで停止する。元の非球形/両尺度/許容差と予算で検証する。native空間の実行内共有も残る。
全体目標/RFA-6/親N04は未完了。主ツリー統合時はfc76e64と81fc416の両方を取り込み、両ツリーの最新引継ぎ/計画を保つ。

### 最新状態: 費用表示コミット・非球形実行継続 — 2026-09-09

費用表示は別ツリー /tmp/superfish-rf-cost-worktree-20260909、branch feature/adaptive-refinement-cost の fc76e64 にコミット済み、作業ツリーclean。主ツリーへは未統合。主ツリーsrc/tests/scripts/examplesは60815の終了まで固定し、先にcherry-pickしない。
最終標準60286は終了0、out/validation-rf-cost-accepted-20260909 は683件/681合格/2 skip、428.580秒PASS。seed9モード19量でf差0/RF最大8.882e-16、最終全対象hashと標準/browser対象hash一致。最初の標準48730は応答metadata完全一致の旧検査1件で失敗し、数値文書/保存文字列完全一致+欠測不明の検査に更新。失敗ログ保持。Chrome3062の15項目PASS、GUI85156/PID103279も終了0。費用表示側の実行は全て終了。
主ツリーの拡大非球形60815/PID76757は実行中。out/curved-rf-nonsphere-expanded-20260909、/tmp/curved-rf-nonsphere-expanded-20260909.log。checkpoint-025.json PAUSED、尺度1の採用7806要素まで確認。Epk差約2.4%が律速、完走/両尺度PASSはまだ主張しない。初回12回の両尺度LEVEL_LIMITは保持。ソースhashは初回から一致。
GDBは2度ともPythonスタック取得不可でdetach済み。独立プロファイル89107は終了0、out/curved-rf-nonsphere-profile-20260909。nativeイベント17/18（1723/6892要素）の読込27.766秒、RF指標36.873秒（cProfile負荷込み）。4回のcase_curved_spaceが累積45.144秒、71回のcheck_curved_edgesが34.652秒。指標はcheckpoint-018のdecisionと完全一致、ソースhash一致。初回driver名profile.pyは標準ライブラリーを隠して失敗、measure.pyへ変更し初回ログ保持。
次は60815の結果確認/記録とfc76e64統合。長時間実行中の独立作業なら別ツリーで行う。実行内の検証済み空間/次plan共有は具体的な次の性能課題: RF指標が確認後と次の局所組立時に重複評価され、saved trackingでも場再読込と空間再構築が重なる。公開再検証や拒否条件を省かず、旧文書/指標/選択の完全一致を先に受入条件にする。
全体目標、RFA-6、親N04は未完了。費用表示は記録済み祖先ジョブ時間であり、事前検証を含む全workflow時間とは区別する。

### 版5非球形検証・費用表示の並行作業 — 2026-09-09

主作業ツリーに scripts/validate_curved_rf_nonsphere.py と仕様を追加。既存両尺度reportとの一致とhashを検査し、全イベントの時間・親子Ritz・体積・Maxwell・追加対照差を保存する。
初回43989は終了1、out/curved-rf-nonsphere-initial-20260909。両尺度12回でLEVEL_LIMIT、124.582/124.566秒。イベント構造一致・尺度差最大5.089e-13。未達を受入へ変更しない。
直前の標準681件の全対象既存ファイルは不変、baseline-coverage.jsonに記録。新しい全件回帰を主ツリーで実行したとは扱わない。
拡大60815/PID76757は実行中。out/curved-rf-nonsphere-expanded-20260909、ログ /tmp/curved-rf-nonsphere-expanded-20260909.log。max-events48以外は同じ条件。尺度1の24イベント/確認20928要素まで進行。電場ピーク差約2.3〜2.4%で停滞、他4量が合格しても停止しない。終了までsrc/tests/scripts/examplesを固定する。
GDB一度接続はPythonスタック情報なしでdetach済み。計算継続。別ツリーの検証も並行するため、時間は専有環境の速度試験ではない。
別ツリー /tmp/superfish-rf-cost-worktree-20260909、branch feature/adaptive-refinement-cost で累積費用表示を実装中。主ツリーの数値検証終了まで変更を混ぜない。費用2検査と実JobManager7検査PASS、Chrome3062は終了0で15項目PASS/外部要求0。GUI85156/PID103279は停止・終了0、画像実表示済み。標準48730は実行中。詳細はそのツリーの docs/GUI_RF_ADAPTIVE_COST.md。
全体目標/RFA-6/親N04は未完了。両方の実行結果・ソース一致を確認して記録し、費用ブランチを主ツリーへ統合する必要がある。

## RF適応版5 GUI — 2026-09-09

[版5 GUI](GUI_RF_ADAPTIVE.md)を追加。曲線入力・全計算予算を有効にし、親/採用列/最終連続確認数を表示。
五量は確認イベントの親比較から前/最後の区間を取り出す。decisionの最後の1比較だけに依存しない。
全イベントの積分表を表示。場の選択を追加し、版5は最後の採用解、旧版は最終水準を初期選択。
明示した未採用確認も再検証後に開ける。曲線版5で直線表面評価ボタンを無効にした。
実Chrome15335は終了0、out/browser-rf-adaptive-initial-20260909 の11項目PASS、外部要求0。
フォームから実FEMを開始し、初期10→確認40（未採用）→元親から局所20→確認80→確認320を確認。
採用列1→3→4→5、2区間五量、保存/再読込、親改変拒否、未採用40要素の場表示がPASS。
実ジョブ中止後のcheckpointから再開し、親source保持を確認。版4旧7水準表示もPASS。
rf-branches.pngを実表示して確認。全ジョブはcomplete/cancelled。
GUI52150/PID47184は起動引数確認後SIGINT、終了0。Chromeも終了済み。
標準57651は終了0、out/validation-gui-rf-adaptive-20260909 がPASS。
681件中679合格・2 skip、422.576秒。seed9モード19量の周波数差0/RF最大8.882e-16。
最終全対象hashと標準、ブラウザー対象hashが一致。全実行終了、ソース固定を解除。
数値コア・新規依存・外部サービスの変更はない。
次はRFA-6の非球形・両尺度・総費用比較と、RFA-5の全再開履歴に対する累積費用の専用表示。
親N04と全体計画は未完了。


## RF適応版5 API/CLI/JobManager — 2026-09-09

[版5](CURVED_RF_ADAPTIVE_REFINEMENT.md)のstrict入力、親参照付きイベントplanner/実行/replayを追加。
同じcheckpoint外形のlevels/level_runsは全solveイベントを表し、accepted_event_indicesが採用列。
確認未達なら元親から局所、合格なら確認を採用し、連続2回の一様五量合格だけで停止する。
初回もnativeを再読込し、λ規約をreplayと一致させる。出力はevent-NNN。
追加4検査はstrict/分岐/確認後再開/改変/五量個別/2回確認/積分未確認でPASS（17.948秒）。
初回74267・最終37263とも終了0。未実装の版5拒否ログも保持。
独立CLI82450は終了0、out/curved-rf-adaptive-initial-20260909 がPASS。
元の電気半球requestから版番号のみ変更し、f=1e-4/RQ,G=.005/E,B=.01を維持。
イベントは初期10→確認40（不採用）→元親から局所20→確認80→確認320要素、5イベントでTARGETS_MET。
採用イベント0,2,3,4。全checkpointはeigsh禁止で完全一致、全親子Ritz減少。実行7.682秒。
解析66239は終了0、out/curved-rf-adaptive-analytic-20260909 の球形五量も同基準内。
版4旧7水準のreplay59632は終了0、文書完全一致（out/curved-rf-adaptive-v4-replay-20260909）。
標準48118は終了0、out/validation-curved-rf-adaptive-20260909 は681件中679合格・2 skip、422.318秒でPASS。
seed9モード19量の周波数差0/RF最大8.882e-16。独立CLIと標準の全対象hash一致。
標準終了後、adaptive_refinement_jobs.pyの出力名検証2行だけを追加（版5 event/旧版level）。
数値・CLI・全検査は標準時点から不変。全件回帰をこの修正後に再実行したとは扱わない。
版4実ジョブ53344は終了0（1検査4.409秒）。版5実ジョブ20084も終了0。
out/curved-rf-adaptive-jobs-20260909で確認後の中断再開・元親から局所・manifest・確認出力改変拒否を確認。
両JobManagerはclose済み。最終ジョブ検証は最終全対象hashと一致。全実行終了。
RFA-1〜4とRFA-5のCLI/JobManagerを部分受入。次は版5 GUI入力・分岐/採用表示・取消し検証、
RFA-6の非球形・両尺度・全solve/指標費用比較。親N04と全体計画は未完了。


## RF指標の移送共有と版5の状態遷移 — 2026-09-09

[検証済み移送の共有](CURVED_RF_GOAL_REUSE.md)で重複したnative再構築と一様制限を削減。
公開追跡は従来通り再検証。内部だけ `_track_prepared_nested_modes` を使い、永続入力からは信頼しない。
最初はmapping変数の切出し漏れで失敗、修正後RF4検査と公開追跡5検査がPASS。
さらにsolve直後の指標との完全一致は、変更前コード自身でも丸め差を生じた。
再solveで係数/周波数/K/M完全一致、λの差2.274e-13を戻すだけで文書を完全復元できた。
確認nativeの読込はωからλを再構成するため、以後checkpointは初回も保存場読込で組み立てる。
旧コードをnative読込へ適用した基準を out/curved-rf-goal-native-replay-reference-20260909 に保存。
旧solve直後文書との差最大1.550e-13、選択・追跡は一致。共有化の新旧比較は許容差なしの完全一致。
旧自作モジュールは out/curved-rf-goal-reuse-baseline-20260909、4681e67内容とhash完全一致を確認。
初回75363/35129/36268は終了1、修正検査91326は終了0、旧文書比較53772は終了1。
丸め切分64074/22793、最終比較11640は終了0。全ログと旧出力を保持。
最終 out/curved-rf-goal-reuse-verified-20260909 は3形状×各3回で新旧指標完全一致。
中央値の旧/新は1.9101、1.8785、1.9042。同一プロセス交互測定、標準回帰は別プロセスで並行。
標準95704は終了0、out/validation-curved-rf-goal-reuse-20260909 がPASS。
677件中675合格・2 skip、405.381秒。seed9モード19量の周波数差0/RF最大8.882e-16。
最終全対象hashと独立比較/標準回帰のhashが一致。全実行終了、ソース固定を解除。

[版5の決定記録](CURVED_RF_ADAPTIVE_PLAN.md)はまだ未実装。
確認と局所解は同じ元親から分岐するため、版4の一本道へ暗黙挿入せずイベントと採用列を保存する。
確認もmax_levels/費用に数え、確認直後から保存再開し、最終2回連続の一様五量合格だけで停止。
次はRFA-1〜6のうちstrict request・イベントplanner・dispatchから実装。
版4の文書完全一致と拒否条件、初回/replay双方のnative読込を維持する。
親N04と全体計画は未完了。


## RF重み付き親要素選択 — 2026-09-09

[親残差のRF局所化API](CURVED_RF_GOAL_INDICATOR.md)を追加した。
同一native二次幾何・一様1段の実確認解から個別追跡し、周波数項を含む随伴の親補間を除去。
子要素残差作用を親ごとに集約し、絶対符号付き親寄与[Ω]のbulk選択を返す。
多段確認・変更Case・鏡映構築・cluster等は拒否。通常の停止・適応版4は未変更。
追加4検査は局所/全体作用、振幅/符号、strict入力、選択から実FEM/RitzがPASS（2.526秒）。
初回24944は試験の周波数逆順が既存契約に拒否され終了1。修正後82484・最終17586は終了0。
独立97249は終了0、out/curved-rf-goal-initial-20260909 が3形状ともPASS。
親/全域確認/局所DOFは楕円体391/1501/470、電気半球89/329/122、磁気半球120/451/146。
全域R/Q対照差は親から局所へ3.582%→2.196%、0.1871%→0.02301%、0.7478%→0.06961%。
局所/全体作用差最大1.792e-16、全例でRitz減少。絶対RF誤差や反復収束とは扱わない。
図4277は終了0、out/curved-rf-goal-figures-20260909 にPNG/PDF/生成コード/データを保存・実表示確認。
確認/指標/局所solveの費用をすべて表示。指標は確認solveより高価で、効率優位は未主張。
標準47763は終了0、out/validation-curved-rf-goal-20260909 はPASS。
677件中675合格・2 skip、406.717秒。seed9モード19量の周波数差0/RF最大8.882e-16。
最終全対象hashと独立/標準回帰のhashが一致。全実行終了、ソース固定を解除。
次は既存の全域確認経路への接続・再構築/組立共有・反復適応の五量と総費用の受入。
親N04と計画全体は未完了を維持する。


## RF角周波数偏微分 — 2026-09-09

[角周波数偏微分API](CURVED_RF_FREQUENCY_SENSITIVITY.md)を追加した。
位相三次モーメント・電場1/ω・電気エネルギー1/ω²を独立微分し、両R/Qを返す。
固定u/K/M/幾何の偏微分。Hz当たりは2π倍。形状の直接寄与や誤差上界は含まない。
追加3検査は定数場閉形式・一般係数差分・位相/振幅不変・ゼロ電圧・随伴結合がPASS。
初回結合試験は周波数寄与不足でFAIL、質量比例の固有値移動を加えた試験で再確認。
独立初回64498はJSON真偽値の型問題で終了1、修正後92383は終了0。
最終 out/curved-rf-frequency-accepted-20260909 は5場の両R/Q差分最大1.767e-10、
電気/磁気半球の2倍尺度則最大2.066e-14でPASS。初回ログはout/curved-rf-frequency-evidence-20260909に保持。
標準12724は終了0、out/validation-curved-rf-frequency-20260909 はPASS。
673件中671合格・2 skip、404.196秒。seed9モード19量の周波数差0/RF最大8.882e-16。
標準終了時に全対象hash一致、その後変更したのは検証スクリプトのfloat変換1行のみ。
数値API・全検査・全既存対象は標準時点と一致し、独立再検証は最終全対象hashと一致。
JSON修正後に全件回帰を再実行したとは扱わない。全実行は終了済み。
次は親子空間での随伴重み付き残差・局所選択・精度/効率比較へ進む。
結合微分のためのλ方向係数は qλ=qω*ω/(2λ)。固定周波数随伴の質量直交ゲージを
-zのλ微分条件へ拡張するか、λ項を別に足す必要がある（次の実装・独立検証で決める）。
親N04と計画全体は未完了を維持する。


## 固定周波数RFの制約付き随伴 — 2026-09-09

[疎随伴API](CURVED_RF_ADJOINT.md)を追加。質量直交拘束で振幅方向を除き、
両R/Q係数勾配から随伴を解く。元の拘束・SI係数を保持し、未収束/近接供給固有値を拒否。
未計算固有値の単純性を証明するものではない。
先頭3モードの全固有モード展開・行列摂動差分・振幅/拒否の追加3検査はPASS。
初回差分2.008e-6は基準2e-6未達。刻みの二次収束を確認し1e-7へ変更、許容差は不変。
初回FAILを含むログは out/curved-rf-adjoint-evidence-20260909 に保持。
独立37910は終了0、out/curved-rf-adjoint-initial-20260909 はPASS。
回転楕円体/電気・磁気対称半球の9方向の相反関係は最大差5.005e-12。
標準18530は終了0、out/validation-curved-rf-adjoint-20260909 はPASS。
670件中668合格・2 skip、403.060秒。seed9モード19量の周波数差0/RF最大8.882e-16。
最終全対象hashと独立/標準回帰のhashが一致。全実行終了、ソース固定を解除。
次は周波数方向のRF目的関数微分と、親子空間での随伴重み付き残差・選択の検証。
今回のAPIは固定周波数の場方向感度で、形状全微分・細分誤差上界・効率受入ではない。
親N04と計画全体は未完了を維持する。


## 固定周波数の曲線RF係数感度 — 2026-09-09

[RF係数感度](CURVED_RF_SENSITIVITY.md)を追加。複素電圧の係数共変ベクトルと
両R/Qの実係数勾配を提供する。電場・磁場の両エネルギーを保持し、制約成分はゼロ。
固定周波数/幾何/RF規約の偏微分であり、形状・固有モード全微分や誤差上界ではない。
追加4検査は解析軸積分、一般係数での有限差分、位相/振幅不変、Maxwell尺度則を確認。
回転楕円体・電気/磁気対称半球の保存場で9方向の独立検査もPASS。
独立42670は終了0、out/curved-rf-sensitivity-initial-20260909。
標準33963は終了0、out/validation-curved-rf-sensitivity-20260909 はPASS。
667件中665合格・2 skip、402.596秒。seed9モード19量の周波数差ゼロ/RF最大8.882e-16。
最終全対象hashと独立/標準回帰のhashが一致。今回の全実行は終了済み。
次は制約付き随伴問題とRF向け細分指標の独立検証・効率比較。
既存選択器は未変更で、親N04の一般精度/効率は引き続き未受入。


## 曲線メッシュの図上選択 — 2026-09-09

[図上選択](GUI_CURVED_MESH_SELECTION.md)を実装。現在の全履歴後の実二次空間から
0始まり要素番号を選び、新しいmarkedを末尾に追加する。表示は5000要素まで。
表示配列の完全一致/不適切な幾何・上限拒否の追加2検査と、
実ブラウザーの履歴入力/一様段数入力各6項目・両実FEMがPASS。
入力/履歴変更時の古い選択を拒否。一様段数は同数のuniform履歴へ変換して保持する。
初回ブラウザーの検査式引用符誤りも保持。再実行20157・最終2経路33943は終了0。
GUI63491/PID4110737は起動引数確認後SIGINT、終了0。
標準回帰89998は終了0、out/validation-gui-curved-mesh-selection-20260909 がPASS。
663件中661合格・2 skip、401.572秒。seed周波数差ゼロ/RF最大8.882e-16。
最終全対象hashと両ブラウザーの対象hashが一致。全実行は終了済み、ソース固定を解除する。
大規模表示・履歴途中への図上挿入、一般精度/効率と親N04全体は未受入を維持する。

## 磁気対称の最終適応確認 — 2026-09-09

[磁気対称の両尺度](CURVED_MAGNETIC_ADAPTIVE.md)も6水準TARGETS_MET、
6272要素の追加一様対照と全水準Maxwell相似がPASS。初回15790・最終2121とも終了0。
新規validate_curved_magnetic_adaptive.pyの入力条件を厳密化し、形状/モード/許容差の拒否も確認。
初回と最終の数値報告は完全一致。磁気対称の最終停止未検証は解消したが、絶対RF解析誤差は主張しない。
数値コア/既存検査/例題はbfa48f4から不変で、全既存661検査の対象hashと一致。
新規検証スクリプトのみを実行して確認し、標準全件を再実行したとは記録しない。
最終出力 out/curved-magnetic-adaptive-accepted-20260909、補助拒否検査 out/curved-magnetic-verifier-rejections-20260909。
全実行終了済み。次はN04一般精度/効率・一般接続/幾何誤差等の残件。

## 曲線適応の単一対称半領域 — 2026-09-09

[鏡映による表面前提](CURVED_ADAPTIVE_SYMMETRY.md)を版4に追加した。
半領域を鏡映した全PEC輪郭の滑らかさを検査し、元半領域のRF量をそのまま評価する。
既存の全PEC診断文書と単体RFピーク診断は変更しない。
追加3検査、半球両尺度7水準の独立球形五量/Maxwell相似、
磁気対称2水準の実適応/追跡/積分と全保存文書一致、直接電磁エネルギー2倍則がPASS。
全PECの旧版4最終checkpointの文書完全一致も確認した。

独立3815・磁気2210・旧replay65596・GUI再実行26222は終了0。
GUI初回は補助CDPスクリプトの変数名衝突で終了1、再実行は2項目PASS。
GUI11021/PID4078729は起動引数を確認してSIGINT、終了0。
標準回帰43275は終了0、out/validation-curved-adaptive-symmetry-20260909 がPASS。
661件中659合格・2 skip、406.873秒。seed周波数差ゼロ/RF最大8.882e-16。
独立/ブラウザー/標準のhashと最終ソースが一致。今回の全実行は終了済み、ソース固定を解除する。
磁気対称の最終適応収束・一般曲線/幾何誤差と親N04全体は未受入を維持する。

## 非球形両尺度の最終対照が完了 — 2026-09-09

handle96442/PID3978483は終了0、dc795e9固定ソースで両尺度PASS。
[最終結果](CURVED_NONSPHERE_COMPARISON.md)と[N04照合](N04_ACCEPTANCE.md)を更新。
尺度1旧報告との時間以外完全一致、両尺度五量相似最大8.362e-12、
体積保存/8倍則・Ritz・追跡・積分・追加対照差・終了後source hash一致を確認した。
適応100917対一様確認41281自由度で、適応優位は得られなかった。
一般精度/効率と親N04全体は未受入のまま。

本体 out/curved-nonsphere-spatial-search-20260909 に報告JSON/CSV/PNG/PDFとplot.pyを保存。
元の全native結果は /tmp/superfish-curved-edge-search-worktree-20260909/out/curved-nonsphere-spatial-search-20260909 に保持する。
source-location.jsonに元位置とソースcommit・hash照合を記録。絶対保存先を使う検証もあるため
このworktree/元結果は削除・移動しない。本体は後続GUI/Study変更を含み、
両尺度ベンチマークを最新版で再実行したとは扱わない。

現在、今回追跡した検証・GUI・CLIプロセスはすべて終了済み。
数値検証のためのソース固定は解除できるが、元成果物の再現用worktreeは保持する。
最新版の標準658件・Chrome23項目はfae2bc4で完了済み。以後は文書/出力のみ変更した。
次は受入照合表の一般形状/表面前提、RFを意識した選択と全域確認費用の残件を具体化する。

## N04要件の照合 — 2026-09-09

[N04_ACCEPTANCE.md](N04_ACCEPTANCE.md)に原要件・実証・限界・次の残件を集約した。
現状欄のGUI履歴編集/固定形状Studyの古い未対応表記を修正。
親N04と計画全体は未受入を維持。実装ソースはfae2bc4から変更していない。
非球形96442は最終追加一様水準5で実行中。終了の確認までは同じhandleを追跡する。
尺度1は旧/新報告の時間以外の全項目一致を
専用worktree出力のscale-1-prechange-comparison.jsonへ保存済み。

## 履歴対応の固定形状Study — 2026-09-09

[履歴を保持する収束Study](CURVED_HISTORY_STUDY.md)を追加。
固定形状Studyのadditional_uniform_refinementsは既存履歴の後への追加段数。
0で元Caseそのまま、旧curved_refinement_levelsの意味は変更しない。
変更後メッシュへの番号流用は引き続き拒否する。
追加2検査は固定体積・Ritz単調性と保存往復/strict拒否を実計算で確認。
Chrome23項目PASS、GUI Studyの180→720要素と履歴・元メッシュhashも確認。
GUIサーバー21475/PID4039112は引数確認後SIGINT、終了0。
ブラウザー61621も終了0。標準回帰7227は終了0、
out/validation-curved-history-study-20260909 がPASS。
658件中656合格・2 skip、404.889秒。seed周波数差ゼロ/RF最大8.882e-16、
最終hashとブラウザー検証ソースが一致。本体の検証用固定は解除済み。
CLI58793は数値RF判定FAILを正しく返して終了1、GUIと報告完全一致。
これは収束未達の受入例であり、物理収束合格とはしない。

非球形の別worktree検証96442は尺度2の適応を終え、最終の追加一様対照水準5へ進んだ。
両尺度最終報告の公開とhash確認までは完了扱いにしない。

## 曲線履歴GUIの保持・編集 — 2026-09-09

[GUI履歴編集](GUI_CURVED_REFINEMENT_HISTORY.md)を実装。修正前のGUI往復は履歴を落とし、
修正後はChrome 19項目と実FEM/nativeのCase/メッシュ/場空間・周波数/RF一致がPASS。
初回拡張検査のページ遷移待ちFAILも保持。ブラウザー77546は終了0、
自分のGUIサーバー83492/PID4004824はargv完全一致後SIGINT、終了0を確認した。
標準検証41261は終了0、out/validation-gui-curved-history-20260909 がPASS。
656件中654合格・2 skip、404.847秒。seed周波数差ゼロ/RF最大8.882e-16、
最終ソースhashとブラウザー検査ソースが一致。本体の検証用固定は解除済み。
図上の要素選択・履歴対応Study・一般精度/効率と親課題全体は未受入。

別worktreeの非球形検証96442は継続中。尺度1は追加対照までPASS、尺度2適応へ進んだ。
同検証のソースはdc795e9時点で固定され、今回のGUI変更を含まない。
引き続き /tmp/superfish-curved-edge-search-worktree-20260909 の計算対象ファイルを変更しない。

## 非球形尺度1の確定と高速化ブランチの本体反映 — 2026-09-09

旧942860bの尺度1報告 out/curved-nonsphere-expanded-20260909/scale-1.json はPASS。
適応11水準/100917自由度、一様確認41281自由度、追加対照164481自由度。
五量比較・追加対照の二区間条件・追跡・高次積分・独立体積/保存/Ritzが合格。
相対差と時間は[非球形比較](CURVED_NONSPHERE_COMPARISON.md)。適応自由度の優位は得られなかった。
報告と元ソースhash一致をtransition.jsonへ保存し、argv確認したPID3901559へSIGINT。
handle71658の終了130を確認。旧実行の全両尺度検証は未完了として保持する。
移行理由は標準656件・球形・旧版保存・非球形100917自由度の完全再検証を通した高速化であり、
観測タイムアウトを終了とみなしたものではない。

perf/curved-edge-searchを本体へfast-forwardし、dc795e9を反映。
本体の全検証対象ソースは、完了した隔離標準656検査のhashと一致。
最初の全hash集合一致検査は、本体にだけ存在する既存.egg-info6ファイルによりFAILした。
実装/検査ファイルの差はなく、その6ファイルも元942860bの標準検証hashと一致した。
詳細は out/curved-edge-nonsphere-replay-20260909/main-integration-source-check.json。
同じ実装・検査に全体回帰を重複実行せず、既存インストールメタデータも変更しない。

高速化版の両尺度対照はhandle96442で継続中。
worktree /tmp/superfish-curved-edge-search-worktree-20260909、
出力 out/curved-nonsphere-spatial-search-20260909、ログ /tmp/curved-nonsphere-spatial-search.log。
このworktreeのsrc/tests/scripts/examplesは完了まで固定する。
旧大規模replay47014、旧標準24254等は全て終了済み。新対照96442だけが今回の数値実行として残る。
一般精度/効率・親課題区分と全体目標の未完項目は維持する。

## N04非球形大規模系列の新候補検索による再検証 — 2026-09-09

非球形の追加再検証 out/curved-edge-nonsphere-replay-20260909 もPASS。
本体で保存した11水準・100917自由度の全checkpoint文書がcanonical JSONで完全一致。
曲線eigshを禁止し、幾何・場/RF・追跡・指標・ピーク・高次積分を全水準で再検証した。
756.602秒。独立replayは全先祖を検証するため、実行内再利用のworkflow時間とは比較しない。
記録hashと専用ブランチのソースは一致し、handle47014は終了0。
初回は出力親ディレクトリ欠落で計算前に終了1。親作成を修正した補助スクリプトで再実行し、
初回ログも保存した。実装ソース・数値基準の修正はない。
本体の両尺度比較handle71658は継続中であり、今回のreplay合格とは区別する。

## V02ローカル配布の部分確認 — 2026-09-09

対象は専用ブランチ3386a5f。[記録](LOCAL_DISTRIBUTION_20260909.md)。
同一ソースZIPのバイト一致・全manifest、wheelの全RECORDと111コード/画面資源、
LICENSE/NOTICE、wheel由来モジュールのCLI help/曲線FEM/native保存再読込を確認した。
f/RQ/Gはソース版対照と差ゼロ。依存は既存環境を利用し、新規ダウンロードなし。
記録は本体の out/curved-edge-distribution-20260909。初回のビルド環境不足ログも保持。
現在の追加記録は元ソースZIPの対象コミットに含まれない。
これはローカルsmokeであり、V02全体・別OS・公開リリースの受入にはしない。
本体の非球形検証71658は継続中。専用ブランチの大規模replay47014は後続検査で終了0/PASS。
ソースZIP作成とwheelビルド/インストール/実行は全て終了済み。

## N04曲線辺の空間木による候補検索 — 2026-09-09

直前基準942860b。[仕様](CURVED_EDGE_SEARCH.md)。非球形検証の費用測定から、
曲線辺の全対候補検索が辺数の二乗に比例していることを確認した。
候補を包囲箱の中央値分割木から取得し、従来の辞書順に戻す。
閉区間接触・パディング・辺の正則性・隣接/分離検査・検査予算は維持する。
元の全探索との比較で候補数/順序と完全な幾何報告・最初の失敗を確認した。
新規外部参照・依存・物理式はない。既存のBezier箱と幾何検査を使用する。

本体の非球形実行はソースhashを固定するため、942860bの追跡ファイルを
/tmp/superfish-curved-edge-tree-20260909へ展開した隔離コピーで実装・検証した。
追加3検査0.122秒PASS。初回はfixtureクラスの直接importで既存3件も再発見されたため、
module importに直して重複をなくし、3件で再実行した。検査の失敗ではない。
標準656件中654合格・2 skip（403.720秒）、PASS。
seed全9モード・従来19量の周波数差ゼロ、RF/エネルギー差最大8.882e-16。
変更前baselineは653件中651合格・2 skip（401.164秒）。基準は変更していない。

記録は上記隔離コピーの out/validation-curved-box-tree-isolated-20260909、
out/curved-box-tree-efficiency-isolated-20260909、out/curved-box-tree-replay-isolated-20260909。
球形の適応5水準/2661自由度・一様3水準/1201自由度と全水準五量の区間端点差ゼロ。
旧版1〜4は曲線eigsh禁止下でcanonical JSON完全一致。記録hashは専用ブランチのソースと一致。
球形全体22.070秒/7.340秒で、この小さい例から加速は主張しない。
約18947辺の候補検索は単発観測5.369秒→0.682秒。完全な幾何検査の費用と区別する。
試作/プロファイル記録は本体の out/curved-box-tree-prototype-20260909、
out/curved-box-tree-full-check-20260909、out/curved-tracking-profile-20260909 に保持。

検証済みの同一バイトを専用worktree /tmp/superfish-curved-edge-search-worktree-20260909 の
perf/curved-edge-search ブランチへ移した。本体の作業ツリーと実行中のソースは変更しない。
本体の非球形検証はhandle71658 / PID3901559で継続中。
尺度1適応は11水準・50256要素/100917自由度でTARGETS_MET、一様側は追加81920要素を計算中。
両尺度の最終結果を確認してから本ブランチを反映し、非球形の記録も更新する。
標準検証handle24254、球形96863、旧版再検証19211は終了0。
8受入・6進行中・18未受入・X01候補は維持する。GUI/Wine/Hosted CIの新規実行はない。

## N04曲線の順序付き組立と非球形対照 — 2026-09-09

直前基準465e09f。README・対応表・計画・現状を照合し、N04の非球形対照へ進めた。
独立合成回転楕円体（半長0.16 m、最大半径0.08 m）で、残差選択だけでは
RQの二区間条件が8水準以内に揃わなかった。一様側の最初の確認は20480要素/41281自由度。
初回8水準・適応20000要素・対照32000要素では、尺度1がLEVEL_LIMIT / REFERENCE_BUDGET。
独立native解析体積の相対差0、固定二次領域の体積保存差2.221e-16、Ritzと初期五量一致はPASS。
解析体積に対する二次領域の体積差1.464e-5はRF誤差へ変換しない。

初回 out/curved-nonsphere-initial-20260909 と /tmp/curved-nonsphere-initial-20260909.log を保持。
尺度2は組立高速化へ移るため、argv照合済み所有PID3860581へSIGINT、実行handle95967の
終了130を確認した。時間切れや物理合格として扱わない。途中のread-only gdbは
PID名前空間差でPython stackを得られずdetach済み。完全な両尺度報告は未作成。

高次積分のPython点ループを、同じスカラー演算順序の基底配列と
初期ゼロを含むnp.add.accumulateへ置換。半径三乗のスカラー丸めも保持し、
返却する6×6行列をコピーして全積分点の累積記憶を解放する。
新規外部数学・外部コード・依存はない。本実装の変更前演算を比較器として保持した。
[仕様・独立物理検査](CURVED_ORDERED_ASSEMBLY.md)、[非球形比較](CURVED_NONSPHERE_COMPARISON.md)。

追加3検査PASS（0.332秒）。独立曲線場積分、Maxwell行列相似、評価/行列バイト一致を確認。
旧版1〜4の全保存文書も曲線eigsh禁止下でcanonical完全一致。
out/curved-ordered-replay-20260909 PASS、局所測定 out/curved-ordered-local-20260909 PASS。
局所次数24は約1.027秒→0.133秒。測定スクリプト・環境・hashを同ディレクトリに保存。
球形対照 out/curved-ordered-efficiency-20260909 PASS。適応5水準/2661自由度、一様3水準/1201自由度、
解析五量と停止を維持。変更前との全水準五量の区間端点差ゼロ。
適応全体21.651秒、一様7.196秒。並行標準検証のあるローカル観測で、一般加速率ではない。

新しい非球形の例は12水準・適応100000要素・追加対照100000要素へ予算だけを増やした。
閾値・形状・正規化・初期メッシュの方式は維持する。
out/curved-nonsphere-expanded-20260909 は実行中。最初の8水準の五量は初回と完全一致。
この実行が終了するまでsrc/tests/scripts/examplesを変更しない。
8受入・6進行中・18未受入・X01候補は維持する。一般精度/効率は未受入。
ブラウザー・Wine・Hosted CIの新規実行はない。

標準 out/validation-curved-ordered-20260909 は653件中651合格・2 skip（401.164秒）、PASS。
変更前baselineは650件中648合格・2 skip（621.030秒）。
seed全9モード・従来19量は周波数差ゼロ、RF/エネルギー差最大8.882e-16。
最初の補助比較は丸め誤差程度のenergy_balance_relativeにも相対比を取ったためFAIL。
これは物理量ではなく既に相対化された欠損量で、実値は約1e-16〜9e-15。
従来の19量と同じ比較を用いて上記PASSを確認し、数値回帰の基準・データは変更していない。
標準・球形対照・独立replay・局所測定のhashは最終ソースと一致。
それらの実行handleは終了済み。非球形拡大検証のみhandle71658 / PID3901559で継続中。
ログ /tmp/curved-nonsphere-expanded-20260909.log。途中結果を完了扱いにせず、同じhandleを待つ。

## N04曲線適応の検証済み先祖の再利用 — 2026-09-09

直前基準07dac27。[仕様](CURVED_VERIFICATION_REUSE.md)。前回の球形対照でFEM合計約7.35秒に
対し全体約119秒を要したため、水準追加ごとの先祖の場/指標/ピーク/積分の重複評価を削減した。
要求・実装hash・出所の内容hashを照合する実行内状態に、検証済み報告と最後のnative場だけを保持。
新水準は完全検証し、評価/次計画の作成後にも出所照合する。変更を拒否し次checkpointを公開しない。
再開では厳密な文書照合と計画取得を一回にまとめた。保存文書を信頼済みデータとして受理しない。
独立replayは全水準を評価する。共通の文書照合をprivate helperへ抽出したが、旧版の意味は維持する。
FEM式・指標・追跡・ピーク・積分・五量停止・保存形式の変更はない。新規依存・外部参照もない。

着手前647件中645合格・2 skip（625.183秒）。変更前の追加検査は当初、評価回数と拒否メッセージの
表現差で3項目FAIL。拒否検査を文言に依存しない形に整えると、改変拒否2項目はPASSし、
3水準の評価回数6対要求3だけがFAIL（19.716秒）。実装後の初回は検査中に引数名を整理してしまい、
実装hashの変更検出で1件ERROR（29.230秒）。ログを保持し、実装を固定して再実行した。
最終追加3検査はPASS（34.166秒）。3水準評価3回・3水準からの1水準再開で計4回、
独立全水準replayの文書一致、保存文書改変の再開前拒否、solve後/新水準評価中の先祖改変拒否を確認。
ログはout/curved-prefix-development-20260909に保持した。

初回対照 out/curved-prefix-efficiency-20260909 はPASS、適応全体83.050秒。
その後、比較スクリプトに残る「先祖を毎回再評価」という説明だけを修正して再測定した。
最終対照 out/curved-prefix-efficiency-final-20260909 はPASS。適応全体82.055秒、FEM合計7.215秒、
一様全体32.577秒。前回の適応118.974秒に対し比0.6897、約31%短い単発ローカル観測。
計測値は性能保証ではなく、再利用による処理回数削減を別途検査している。
適応の5水準/2661自由度・一様の3水準/1201自由度と五量解析目標は維持される。
独立再検証 out/curved-prefix-replay-20260909 はPASS。実保存版1/2/3と新規版4の全4文書が
canonical JSONで完全一致し、曲線の固有値再計算禁止下でも確認した。
最適化前後の球形対照は適応/一様とも全水準のf/RQ/G/E比/B比の区間端点差ゼロ。
最終対照と独立再検証の記録hashは最終ソースと一致する。

最終標準検証 out/validation-curved-prefix-20260909 は650件中648合格・2 skip（632.889秒）、PASS。
seed全9モード・19量は周波数差ゼロ、RF/エネルギー差最大8.882e-16。ベンチマークは変更なし。
最終対照・独立再検証・標準検証の記録hashは最終ソースと一致し、全実行プロセスは終了済み。
GUIコードは未変更。ブラウザー・Wine・Hosted CIを今回新規実行したという主張はしない。

これは確認費用の改善であり、適応細分方式そのものの一般効率・精度を受入済みにしない。


## N04曲線の一様細分対照 — 2026-09-09

直前基準89aa81d。[比較仕様・結果](CURVED_REFINEMENT_EFFICIENCY.md)。
計画N04の誤差対DOF/時間の対照を scripts/benchmark_curved_refinement.py として追加した。
同一初期メッシュ・二次写像・積分・正規化の球形を、実版4と親写像を保つ一様細分で計算する。
観測wrapperは元のsolveを呼んで時間だけ記録し、数値処理・停止条件を変更しない。
全体時間は先祖再検証の負荷が異なるので、細分方法の加速率には使わない。
新規外部参照・依存・Wine・Hosted CIはない。既存のSphereTM公開数学実装とnative検証を再利用した。

着手前647件中645合格・2 skip（631.966秒）。独立対照の初回結果はPASS、
out/curved-efficiency-initial-20260909 に保存。図はPNG/PDF、CSVと再生成plot.pyも保持した。
初期五量完全一致、Ritz単調性、追跡ID、高次積分、最終解析五量（ピーク両端）を確認した。
適応は36→58→81→324→1296要素/最終2661自由度、一様は36→144→576要素/最終1201自由度。
両者とも初期85自由度で解析目標内だが、細分差確認は適応5水準・一様3水準を要した。
最終solveは5.213秒対2.270秒、適応が約2.296倍。単一ローカル観測で性能保証ではない。
この球形例で適応優位は得られなかったため、一般効率を受入済みにしない。

最終標準検証 out/validation-curved-efficiency-20260909 は647件中645合格・2 skip（620.311秒）、PASS。
seed全9モード・19量の周波数差ゼロ、RF/エネルギー差最大8.882e-16。ベンチマークは未変更。
独立対照と標準検証の記録hashは最終ソースと一致した。全実行プロセスは終了済み。
今回GUIコードは変更せず、ブラウザーやWine比較を新規実行したという主張はしない。

次は滑らかな非球形で局所誤差が集中する対照、RFに対応した選択と確認費用の改善。
全域2回確認・五量の許容差は維持する。任意履歴の直接GUI編集など他の残件も保持する。


## N04曲線適応版4のGUI — 2026-09-09

直前基準3671707。[操作・範囲](GUI_CURVED_ADAPTIVE_REFINEMENT.md)。既存の版4エンジンへ、
GUIの明示選択・厳密な入力作成・五量/高次積分比較表示・保存再開を接続した。
頂点接線間の最小角を初期弦メッシュの最小角と区別し、保存再読込で専用設定を復元する。
版1〜3へ戻ると積分表を消去する。版4結果では直線専用の別表面評価ボタンを無効にする。
計算式・追跡・許容差・保存形式の変更はない。新規外部参照・依存・Wine・Hosted CI実行なし。

着手前647件中645合格・2 skip（624.058秒）。最終標準validateも同件数でPASS（632.244秒）。
out/validation-gui-curved-adaptive-20260909 に記録。全9モード・19量のseed比較は周波数差ゼロ、
RF/エネルギー差最大8.882e-16。元ベンチマークは変更していない。
旧版1〜3の実Chrome15操作は初回PASS、out/browser-affine-adaptive-regression-20260909。

今回GUIフォームから作成した球形要求は36→58→81→324→1296要素の実FEMで五量と全域2回を達成。
そのダウンロードしたnativeチェックポイントを固有値再計算禁止下で再検証し、独立球形解析の五量と
ピーク比区間の両端を照合した。out/gui-curved-adaptive-physics-20260909 はPASS。
相対差はf 2.472531e-5、RQ 3.151849e-5、G 1.590683e-7、E比2.706184e-4、B比2.054552e-5。
これは今回のGUI実計算の照合であり、前回の両尺度検証を再実行したという主張ではない。
検証補助スクリプト・着手前ログはout/gui-curved-adaptive-development-20260909に保持する。

版4の実Chrome11操作は初回PASS。out/browser-curved-adaptive-initial-20260909/report.json に記録。
4+1水準の実行/再開、五量/積分/品質設定の復元、保存JSON完全一致・改変拒否・再読込・対象場、
QUADRATURE_UNVERIFIED停止、版3切替を確認した。旧版15操作と合わせて外部HTTP要求なし。
7適応ジョブと2場取込ジョブは全て終了し、今回の検証用GUIサーバーも停止済み。
標準検証・今回の解析照合・両ブラウザーの記録hashは最終実装と一致する。
検証スクリプトの使用法表示と必須引数検査を実行中に補正したが、実装ファイルは全検証中変更なし。

任意局所履歴の直接GUI編集、一般形状の精度/効率、幾何近似誤差の受入は残る。
親課題の限定受入8・着手6・その他未受入18・対象外候補1は変えず、計画全体の完了とはしない。


## N04曲線適応計算版4 — 2026-09-09

直前基準ba36a86。[仕様](CURVED_ADAPTIVE_REFINEMENT.md)。曲線の残差選択・順序付きnative履歴・
親子質量内積追跡を、版4の適応停止/保存再開API・CLI・JobManagerへ統合した。
既存の表面評価と同じ滑らかな元PEC接続/軸極の前提を持つ閉PEC/axis曲線に限定し、
対称半領域や未確認の角を表面量合格へ拡張しない。局所品質はmapped corner angle、
初期弦メッシュ生成のmin_angleとは別定義で検査する。
直線版1/2/3の演算・入力/保存形式は維持し、版4だけ別エンジンへ分岐する。

全個別IDの確認後、対象場のf/RQ/Gと連続離散E/Bピーク比区間の直近2区間を別判定する。
RF候補後に全域細分へ移り、最後の2水準が全域確認で、五量が通るときだけTARGETS_MET。
高次積分の残差三成分L1/全指標二乗・対象場Rayleigh周波数・質量形式の比較も必須とし、
未達はQUADRATURE_UNVERIFIED。許容値と高次次数を要求に明示する。物理誤差上界は常にnull。
各水準のCase/元弦メッシュ・履歴・場/RF・追跡/積分/停止判断を再検証し、PAUSEDだけ再開する。
再検証は固有値を解き直さず、追加計算数・要求/出所一致・実行失敗時の前段保存を維持する。

着手前642件中640合格・2 skip（407.376秒）。追加検査の未実装失敗を確認して接続した。
初回4検査（505.347秒）は、停止/再開/CLI再検証/改変拒否/厳密入力がPASSし、
検査側の不存在manager.read_job呼出しだけがERROR。正しいstatus/verify呼出しへ修正した。
初回の実FEMは36→58→81→324→1296要素、最後の全域2回と五量を満たした。
高次の指標と場形式で同じ行列を二度組み立てていたため、検証済み空間上の一回の高次行列を共用。
完全検証版の指標と残差三成分の差分が完全一致する検査を追加した。物理式・許容差は変更なし。
単体のインターフェース検査は最大弦メッシュ辺を0.128 mの軽量fixtureへ分離し、同じ全条件を検査。
重複した再検証呼出しも統合した。独立物理検証の球形0.064 mの条件と解析許容値は維持する。
修正後5検査PASS（219.397秒）。JobManagerで1水準開始→別ジョブで1水準追加の再開も確認した。
時間差を行列共用だけの性能改善とは扱わない。開発ログはout/curved-adaptive-development-20260909。

独立検証の初回out/curved-adaptive-initial-20260909はPASS。
尺度1/2とも球形の実FEMが36→58→81→324→1296要素、5水準でTARGETS_MET。
尺度1はCLIで3水準まで保存→別出力先へ再開。尺度2はAPI実行で、両者とも保存再検証中の固有値計算を禁止した。
f=1e-4、RQ/G=.005、E/Bピーク比=.01の独立解析基準を、ピーク区間の両端点を含めて満たした。
両尺度の最大解析差はf=2.473e-5、RQ=3.152e-5、G=1.591e-7、Epk/Eacc=2.707e-4、Bpk/Eacc=2.055e-5。
五量相似則差最大5.685e-14、高次積分比較差最大2.874e-14。最後の全域確認2回と全個別IDを保持した。
最終周波数変化は約2.009e-7でも球形解析差は約2.473e-5で、固定二次幾何の細分差を全物理誤差上界にできない。

旧保存互換性out/curved-adaptive-old-replay-20260909もPASS。実保存の版1/2/3チェックポイントを再検証し、
全判断・状態を含む文書が完全一致。版1/2のsurface_status=UNASSESSED、版3のTARGETS_METを維持した。
独立・旧保存検証中のソース変更なし、記録hashは最終ソースに一致する。

最終標準検証 out/validation-curved-adaptive-20260909 は647件中645合格・2 skip（629.257秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立球形・旧保存互換性の記録hashは最終ソースに一致し、検証中のソース変更なし。

新規外部資料・コード・依存・legacy参照なし。既存の自作曲線FEM/残差/係数移送/追跡、
連続離散ピーク区間、球形解析参照を再使用。既存の固定幾何表面前提・物理許容値は変更していない。
GUI版4入力/表示、対称/一般曲線の表面前提、一般形状の精度/効率、幾何近似誤差と物理誤差上界は残る。
33親課題は8限定受入・6進行中・18未受入・X01候補を維持する。
今回GUI変更/実ブラウザー、新規Wine比較、Hosted CIは実行していない。
次はGUIの版4入力・高次積分/五量/品質表示・保存再開を接続し、実ブラウザーで確認する。
GUI版3が入力するminimum_angle_degと版4のminimum_corner_angle_degは定義が異なるため、単に項目名を流用しない。
以下は過去の各時点の履歴である。

## D01/N04曲線親子空間の質量内積追跡 — 2026-09-08

直前基準8ae8037。[仕様](NESTED_CURVED_TRACKING.md)。nested_curvedをAPI/保存追跡/CLIへ追加した。
元弦メッシュと細分指定以外のCase一致、履歴の真の拡張、再構築した全幾何配列を検査する。
局所marked/全域uniformの複数追加操作の係数移送を合成し、旧levelsもuniform列として照合する。
両対称条件、両側が鏡映済みの場合の宣言偶奇部分空間を扱う。直接/鏡映の混在は拒否。
鏡映は元半領域の係数を取り出して移送し再鏡映するもので、任意の全領域係数への写像ではない。

既存の薄いQR/小行列Choleskyによる質量座標をmass_trackingへ分離し、直線側は同じ演算/診断を維持。
曲線側は8点Duffy積Gaussで質量行列を構築する。r³×P2場積×det Jは参照座標で最大次数12。
この多項式積分の事実を剛性/RF積分の有理式へ拡張しない。特徴数上限8388608、
内積再現差1e-10、数値割当余裕下限と既存の重なり/クラスタ/特異値判定を維持する。
縮退回転は部分空間に留め、ランク低下や曖昧な対応はUNVERIFIEDとする。

着手前637件中635合格・2 skip（395.581秒）。追加検査の未実装による失敗を確認してから接続。
追加5検査は初回PASS（14.391秒）。複数移送の手動合成、独立12点積分との質量Galerkin/全Gram、
符号/順位交換、縮退回転/ランク低下、両対称/鏡映、磁気対称鏡映のnative保存再検証、
旧levels、不正入力/履歴/予算を確認。人工的な係数交換・縮退設定は判定用で、新FEM固有対ではない。
開発ログはout/nested-curved-development-20260908に保持する。

独立検証の初回out/nested-curved-initial-20260908はPASS。
既存out/curved-indicator-selection-set-20260908の合成円筒/楕円/双曲線×尺度1/2×3水準の
18 native場を再検証し、12組を追跡した。最初の組はCLIの作成/再検証を実行した。
API保存/再検証中の固有値計算を禁止し、元nativeファイルの同一性も確認した。新規固有値計算ではない。
全12組で先頭2個別IDを保持。最小主重なり0.9999995273989757、質量Galerkin相対差最大1.288e-15、
特徴の内積再現差最大1.057e-15。尺度間の重なり差ゼロ、五量相似則差最大1.033e-13。
円筒五量の解析許容値も維持した。細分前後のf/RQ/G/ピーク比差はそれぞれ別記録。
独立検証中のソース・元nativeファイル変更なし、記録hashは最終ソースに一致する。

最終標準検証 out/validation-nested-curved-20260908 は642件中640合格・2 skip（409.930秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立検証の記録hashは最終ソースに一致し、検証中のソース変更なし。

新規数学資料・外部コード・依存・legacy参照なし。既存の自作二次幾何制限・質量弱形式・
QR/Cholesky特徴・主角/ID判定を再使用した。新しいモード追跡を物理誤差証明とは扱わない。
曲線の追跡付き適応停止/保存再開/GUI、一般形状の精度/効率・幾何近似誤差・物理誤差上界は残る。
33親課題は8限定受入・6進行中・18未受入・X01候補を維持する。
今回GUI変更/実ブラウザー、新規Wine比較、Hosted CIは実行していない。
次は曲線残差選択・native履歴・nested_curved追跡を適応停止/保存再開へ結ぶ。
以下は過去の各時点の履歴である。

## N04二次曲線FEMの残差指標 — 2026-09-08

直前基準6261292。[仕様](CURVED_RESIDUAL_INDICATOR.md)。物理座標の二階連鎖律でラプラシアンを求め、
軸重み付き強形式・内部辺ジャンプ・PEC/電気対称の自然流束を曲線要素へ拡張した。
親二次幾何を再構築して配列を照合し、指標用の行列・積分を計算する。既存残差APIから分岐し、
bulk選択とCaseの順序付き局所履歴へ接続できる。元のFEM/RF核・直線指標の数式は変更しない。
要素尺度はBernstein制御点凸包直径、辺尺度はGauss弧長。既定12点、2〜32点の明示比較を提供する。
曲線の有理被積分関数を厳密積分したとは扱わず、物理誤差上界は常にnull。

着手前632件中630合格・2 skip（390.927秒）。実装前の逆Jacobianのみの試作を、物理一次場の
Δu=0という独立不変量で棄却（誤って18.75、out/curved-indicator-development-20260908/chain-rule-red.log）。
幾何Hessianを含む連鎖律を実装し、既知一次/二次場・独立体積/曲線壁積分・直線極限で検査した。
最初の追加検査では、参照体積積分が頂点直径を使った誤りを修正した。制御点凸包直径の二乗は0.0416 m²で、頂点の0.04 m²とは異なる。許容差変更なし。
電気対称は弱い自然条件であり、鏡映後は対称面流束の2倍の内部ジャンプになる。
半領域の規格化対称面二乗残差をbとすると全指標二乗はbだけ増加する。この変換則を検査し、
磁気対称の指標一致とは分離した。native再読込は周波数から固有値を復元するため1 ulp差があり、
同じ復元固有値での指標完全一致と元指標の丸め範囲一致を確認した。
追加5検査は最終PASS（5.700秒）。非有限/ゼロ場・不正次数・拘束違反等を拒否する。
開発中の検査ログはout/curved-indicator-development-20260908に保持した。

独立検証の初回out/curved-indicator-initial-20260908はFAILとして保持する。
円筒/楕円/双曲線×尺度1/2×3水準の数値条件は全て満たしたが、円筒のほぼ同値の残差順位が
尺度間で入れ替わり、優先順位リストの完全一致を要求した検証が失敗した。選択集合は全水準で同一。
細分APIは集合をソートして操作するため、実際の選択集合一致を検査し、順位一致は別の事実として記録する。
数値許容差・物理条件・指標や選択アルゴリズムは変更していない。

最終独立検証 out/curved-indicator-selection-set-20260908 はPASS。18 native結果で、
円筒64→96→140、楕円360→423→589、双曲線216→250→354要素となった。
尺度1で指標はそれぞれ0.01267→0.004646、0.01634→0.005746、0.01650→0.006431へ減少。
全系列の最低周波数はRitz単調性を満たし、先頭2固有対の残差は最大7.676e-14。
12対24点積分の三成分L1差/全指標二乗は最大4.218e-13。
指標相似則差最大3.165e-13、五量相似則差最大1.033e-13。全水準で選択集合は同一。
円筒の最終解析差はf=1.263e-7、RQ=2.077e-4、G=2.414e-7、Epk/Eacc=2.676e-4、Bpk/Eacc=1.495e-4。
指標計算（幾何/行列再構築込み）の最大実測時間4.662秒。一般効率の受入ではない。
独立検証中のソース変更なし、記録hashは最終ソースに一致する。

最終標準検証 out/validation-curved-indicator-20260908 は637件中635合格・2 skip（395.995秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立検証の記録hashは最終ソースに一致する。検証中のソース変更なし。

既存PHYSICS/RESIDUAL_INDICATORの独自弱形式とR33の背景を継承し、二階連鎖律と鏡映変換を導出。
新規外部資料・外部コード・依存・legacy参照はない。独立積分は検証専用で製品値を置換しない。
曲線の追跡付き適応停止/保存再開/GUI、一般形状の精度・効率、幾何近似誤差と物理誤差上界は残る。
33親課題の8限定受入・6進行中・18未受入・X01候補を維持する。
今回GUI変更/実ブラウザー、新規Wine比較、Hosted CIは実行していない。
次は局所曲線空間の親子係数移送と質量内積によるモード追跡を接続し、曲線の適応停止へ進む。
既存curved_same_domainはPEC/axis限定の標本比較で、nested_affineは直線専用。
曲線履歴の親子関係・全空間の同一性を検証し、既存QR/Cholesky質量特徴とID判定を再使用する方針。
以下は過去の各時点の履歴である。

## N04曲線局所細分のCase履歴とnative統合 — 2026-09-08

直前基準84a49e4。[仕様・検証](CURVED_REFINEMENT_HISTORY.md)。mesh.curved_refinement_stepsに
厳密なuniform/markedの順序付き履歴を追加し、通常FEM/CLIとnative保存再構築へ接続した。
要素番号は各操作直前のメッシュに属し、親二次写像を制限して再投影しない。
既存levelsは維持し、正のlevelsとの併用を拒否。Caseの全体要素数予算を各操作に適用する。
履歴を無関係な番号へ適用しないため、履歴付きStudyは明示拒否。
鏡映の半領域履歴はreflection.source_caseに保持し、全領域Caseからは除く。
既存native検証を通じ、幾何配列完全一致・拘束・K/M・規格化/残差・RFを再計算する。

既存の自作曲線制限・FEM・保存completion契約を再使用。新規数学資料・外部コード・依存・
legacy参照はない。密行列FEMは独立の検証用固有値解法で、製品ソルバーを置換しない。
解析円筒は検証参照のみ。小残差や相似則一致を物理離散化誤差の上界とは扱わない。

着手前628件中626合格・2 skip（382.837秒）。追加4検査PASS（6.296秒）。
混在履歴と手動細分の完全一致・旧全域互換・strict入力/予算・native保存改変拒否・磁気対称鏡映を確認。
独立検証の初回out/curved-native-initial-20260908はPASS。
円筒/楕円/双曲線×尺度1/2の6 native結果で、通常実FEMを別の密行列FEMと比較した。
円筒尺度1はCLI実計算。全結果を固有値再計算を禁止して再読込し、手動構成した幾何と完全一致。
先頭2周波数差最大3.162e-13、基本モード五量差最大2.387e-12、相似則差最大5.685e-14。
円筒解析差はf=8.658e-7、RQ=2.150e-4、G=7.497e-7、Epk/Eacc=2.953e-4、Bpk/Eacc=2.261e-4。
一般形状の物理精度・効率の受入ではない。

最終標準検証 out/validation-curved-native-20260908 は632件中630合格・2 skip（394.048秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立検証の記録hashは最終ソースに一致し、独立検証中のソース変更なし。

曲線の残差指標/追跡付き適応停止、GUI履歴編集、履歴対応Study、一般精度/効率、
幾何近似誤差と物理誤差上界は残る。33親課題は8限定受入・6進行中・18未受入・X01候補を維持する。
今回GUI変更/実ブラウザー、新規Wine比較、Hosted CIは実行していない。
以下の以前の未接続記述は各時点の履歴である。

## N04曲線要素の局所適合細分基盤 — 2026-09-08

直前基準9af9cf6。[仕様](CURVED_MARKED_REFINEMENT.md)。CurvedSpaceの選択要素と必要な隣接要素を
参照三角形テンプレートで細分し、親の二次幾何写像とP2場を制限するAPIを追加した。
既存全域細分の6節点規約・4子テンプレートと、直線細分の最長弦閉包/遷移分割の数学を再使用。
共有節点を位相で識別し、解析曲線へ再投影しない。曲線番号と境界区間、軸と磁気対称拘束を保持。
正Jacobian/半径/辺交差/適合性と頂点接線角を検証し、要素数・角度の上限/下限未達は拒否する。
親空間を変更せず、係数移送と親参照座標を返す。既存全域細分・保存再構築・FEM/RF核は変更なし。

Caseの局所履歴/native保存再構築・CLI/JobManager/GUI・曲線適応停止は未接続。
係数移送を固有値計算や誤差推定として扱わない。幾何近似誤差と物理誤差上界の保証はない。
新しい数学文献・外部コード・依存・legacy参照はない。既存の自作二次写像・Galerkin弱形式を使用。

着手前623件中621合格・2 skip（378.443秒）。追加APIが存在しない失敗を確認して実装。
追加5検査PASS（6.647秒）。親参照領域の分割、局所性、幾何/場/勾配、Galerkin K/M、
全要素選択時の旧全域細分との完全一致、解析曲線へ再投影しないこと、軸/磁気対称保持、
不正入力/予算/品質/祖先情報の拒否を確認した。
独立検証の初回out/curved-local-initial-20260908もPASS。
その後、移送場を新しい固有対と混同しないため移送後の残差メタデータを明示計算/記録して再実行。
数値条件・基準は変えていない。


最終独立検証 out/curved-local-residual-metadata-20260908 はPASS。
尺度1/2とも円筒64→72、楕円360→369、双曲線216→224要素。
Galerkin K/Mの最大相対差3.552e-16、移送した旧場のRF最大相対差2.443e-15、ピーク端点差0。
別の密行列FEM固有値解法による先頭2固有値はRitz単調性を満たし、最大残差3.486e-13。
移送した旧場の細分後残差は最大7.392e-3であり、新しい固有対として扱っていない。
円筒の最大解析差はf=8.658e-7、RQ=2.150e-4、G=7.497e-7、Epk/Eacc=2.953e-4、Bpk/Eacc=2.261e-4。
Maxwell相似則最大相対差3.656e-12。一般物理精度・誤差対DOF/時間の改善受入ではない。
最終検証中のソース変更なし、最終ソースhash一致。


最終標準検証 out/validation-curved-local-20260908 は628件中626合格・2 skip（380.127秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立検証の記録hashは最終ソースに一致する。
この基盤APIの追加ではGUI変更/実ブラウザー検査、新規Wine比較、Hosted CIは実行していない。

一般形状の精度/効率、曲線局所細分の製品経路、幾何近似誤差・物理誤差上界は残る。
33親課題の8限定受入・6進行中・18未受入・X01候補を維持する。

## N03通常RF結果の連続離散ピーク統合 — 2026-09-08

直前基準add9938。[仕様と操作](RF_DISCRETE_PEAKS.md)。直線P1/P2・二次曲線P2の
保存場を再検証し、E/H/Bと電場/磁場ピーク比上下界を通常RF画面から評価・保存・再読込できる。
元のRF推定値・規約・エネルギーを併記し、DISCRETE_BOUNDS_ONLYと角診断を表示する。
単一メッシュの物理収束・幾何誤差・正則性を合格扱いしない。
APIとassess-rf-peaks/replay-rf-peaks CLIも追加。結果/順位を変えると旧評価を消去し、
遅れて届いた別順位の応答を破棄する。保存文書を別ジョブ/順位へ誤って付けない。
過去のNG曲線RF形式のピーク列欠落にも対応し、加速電圧有意性は既存RF核の判定を再使用。
元のnative結果の値/形式、FEM/固有値/RF核・極値核・停止基準に変更はない。
新規数学資料・外部コード・依存・legacy SUPERFISH参照はない。

着手前618件中616合格・2 skip（366.787秒）。追加5検査PASS（7.984秒）。
P1/P2のUを4倍→絶対ピーク2倍・規格化比不変、曲線の再読込時に固有値計算なし、
CLI・再入角・改変拒否・GUI対象順位/重複JSON拒否・旧NG曲線形式を確認した。
初回の改変テストがnullをnullに変更していた点はテストデータを修正。
旧曲線のピーク列欠落でKeyErrorを確認してから保存場による評価を接続した。
実Chrome13検査PASS（out/browser-rf-peaks-expanded-20260908）。
初回out/browser-rf-peaks-initial-20260908は取込欄が閉じたままのクリックで失敗し、
検査スクリプトに展開操作を追加。数値条件や本体の操作条件は緩和していない。
実応答の受渡しを遅らせたモード変更競合も確認。外部HTTP要求なし、ソース変更なし。
スクリーンショットを目視確認し、保存推定値/上下界・物理収束未確認の区別を確認。
3取込ジョブを再検証し、終了確認後に自身の正確なargvに一致するGUIをSIGINT停止した。


独立検証 out/rf-peaks-physics-initial-20260908/validation.json はPASS。
P1/P2円筒×尺度1/2の実FEMで、f 1e-4・RQ/G 0.005・ピーク比両区間端点0.01の基準を満たした。
P1の最大解析RQ差2.867e-3、最大ピーク比端点差1.485e-3。
P2は同じ順に6.556e-7、3.680e-7。相似則最大相対差2.743e-14。
曲線の規格化エネルギー4倍に対する絶対ピーク2倍/規格化比不変の差は0。
保存再検証もPASS。単一メッシュ評価の状態はDISCRETE_BOUNDS_ONLYを維持する。
検証中のソース変更なし、最終ソースhash一致。


最終標準検証 out/validation-rf-peaks-20260908 は623件中621合格・2 skip（375.473秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立物理・ブラウザーの記録hashは最終ソースに一致する。
Hosted CIや新規Wine比較を実行したという主張はしない。

一般形状の精度/効率、曲線局所細分、幾何近似誤差と物理誤差上界は残る。
33親課題の8限定受入・6進行中・18未受入・X01候補の区分は維持する。

## N04版3適応停止のGUI接続 — 2026-09-08

直前基準9cee5a4。[操作仕様](GUI_ADAPTIVE_SURFACE_STOPPING.md)。版3のピーク比閾値入力、
五量の2区間判定、全水準の連続離散ピーク比上下界と元多角形診断を表示する。
全域確認途中・達成・上限停止・未確認を区別し、RFだけの条件達成でピーク未達を隠さない。
版3をGUIで明示拒否していた通信制限を解除し、実JobManagerの開始・部分実行・保存再開へ接続。
保存要求は入力欄編集から独立して再検証し、対象場は最終水準の追跡対象順位で開く。
版1/版2を開くと旧ピーク表を消去してUNASSESSEDを表示し、標本追跡/全域確認の違いを維持する。

FEM/固有値/RF核、追跡、ピーク上下界、停止条件/閾値に変更はない。
既存gui_adaptive_refinementの通信とweb/app.js・index.htmlの表示を拡張した。
新規数学資料・外部コード・依存・legacy参照はない。

着手前617件中615合格・2 skip（351.007秒）。変更前に版3 GUI開始が明示拒否されることを確認。
GUI通信5検査PASS（32.781秒）、実Chrome15操作が初回PASS。
入力作成で2つの閾値を区別し、実P2対象順位2を4+1水準で再開、五量/上下界を表示。
保存JSONの完全一致・ページ再読込・改変拒否・対象順位2の場表示を確認した。
再入角の事前拒否で旧結果保持、RF3量は条件内だがピークだけが未達のLEVEL_LIMIT、
版2の表面未評価と表の消去、版1入力の標本追跡も確認した。
スクリーンショットで5量の判定/水準/ピーク上下界を目視確認。
ブラウザー証拠: out/browser-n04-surface-stop-initial-20260908/report.json。
外部HTTP要求なし、検証中のソース変更なし。
GUI作業領域out/gui-n04-surface-stop-20260908の4適応ジョブと1場表示用ジョブは全て終了。
検証用GUIは自身の正確なargvを照合してSIGINTで停止した。


GUI接続後の独立検証 out/n04-surface-stop-gui-physics-20260908/validation.json はPASS。
P1/P2×尺度1/2の全系列で停止と表面判定がTARGETS_MET、解析五量の区間端点差と相似則もPASS。
P1は10水準/79168要素/39817自由度、最大RQ差3.916e-4・最大ピーク比差1.955e-4。
P2は5水準/1872要素/3853自由度、最大RQ差1.674e-6・最大ピーク比差5.350e-7。
相似則の最大相対差8.269e-13。独立検証中のソース変更なし、最終ソースhash一致。
前回と同じ基準で確認しており、一般的な精度/効率や物理誤差上界の受入ではない。


最終標準検証 out/validation-n04-surface-stop-gui-20260908 は618件中616合格・2 skip（375.960秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立物理・ブラウザーの記録hashは最終ソースに一致する。
Hosted CIや新規Wine比較を実行したという主張はしない。

通常RF画面への連続離散ピーク統合、一般形状の精度/効率、曲線局所細分、物理誤差上界は残る。
33親課題の区分は8限定受入、6進行中、18未受入、X01候補を維持する。

## N04連続離散ピーク比を含む適応停止 — 2026-09-08

直前基準7645883。[版3仕様](ADAPTIVE_SURFACE_STOPPING.md)。要求版3を追加し、
既存の連続離散ピーク上下界と水準間区間変化を、実FEM適応計算の停止条件へ接続した。
RF候補後に全域細分を最低2回行い、最後の2区間でf/RQ/GとEpk/Eacc・Bpk/Eaccを別々に確認する。
RFだけが条件内でもピークが未達なら全域細分を継続する。未確認区間・個別ID・予算停止は合格しない。
元の正確な多角形の角/境界接続診断を必須とし、再入角・弦近似・未確認接続は入力時に拒否する。
物理誤差上界や一般的な正則性を証明したものではない。

API/CLI/JobManagerで開始・部分実行・保存再開・全native再検証を使える。
版1/版2の判断・surface_status=UNASSESSEDは変更しない。
版3のGUI操作は次段階とし、既存フォームで誤表示しないよう通信入口で明示拒否する。
別途の直線表面評価APIは版3も全域確認条件付きで評価し、固定N03閾値を維持する。
FEM/固有値/RF核は変更せず、新規数学文献・外部コード・依存・legacy参照はない。
区間の最悪比変化は既存surface_convergenceの厳密有理数と外向き丸めを再使用した。

着手前613件中611合格・2 skip（327.193秒）。RF一定でピークだけ変化する反例が
変更前には誤ってTARGETS_METとなることを確認。追加4検査は24.033秒でPASS。
実P2対象順位2の4+1水準再開、区間/元場改変拒否、CLI再検証、管理ジョブ状態とGUI版3拒否を確認。
初回追加テストは管理器closeより先に一時結果を削除していたため終了順序を修正。
数値閾値・本体の終了処理は変更していない。
過去の版1/版2nativeチェックポイントも最終コードで内容が完全一致する再検証に成功。
証拠: out/n04-surface-stop-old-replay-20260908/validation.json。


独立初回 `out/n04-surface-stop-initial-20260908/validation.json` はPASS。
P1は10水準（最後2回が全域細分）、79168要素・39817自由度。
尺度1/2の最悪解析端点差は f=7.005e-8、R/Q=3.916e-4、G=2.819e-7、
Epk/Eacc=1.802e-4、Bpk/Eacc=1.955e-4。
P2は5水準、1872要素・3853自由度。同じ順で6.953e-10、1.674e-6、2.756e-9、4.403e-7、5.350e-7。
いずれも停止状態/独立表面判定がTARGETS_MET、相似則の最大相対差8.269e-13。
前回のP1は8水準予算で全域確認待ちだったが、今回は予算を10水準へ増やして確認を完了した。
f/RF/ピーク比の許容値は変更していない。高いP1計算量は残り、一般効率の受入ではない。
独立検証中のソース変更なし、記録hashと最終ソースが一致する。


最終標準検証 `out/validation-n04-surface-stop-20260908` は617件中615合格・2 skip（354.760秒）、PASS。
benchmarks/validationの全9モード・19量に対する周波数差はゼロ、RF/エネルギー差最大8.882e-16。
固有値/RF核の変更はない。標準・独立検証のsource hashは最終コードに一致。
追加実装後の実ブラウザー検査やHosted CI/Wine比較を行ったという主張はしない。

次は版3のGUI統合。通常RF表示統合、一般形状の精度/効率、曲線局所細分、物理誤差上界は残る。
33親課題の区分（8限定受入、6進行中、18未受入、X01候補）は維持する。

## N03直線表面収束評価のGUI接続 — 2026-09-08

直前基準b648932。適応細分GUIで3水準以上の結果を開き、任意の確認済み個別IDを指定して
直線表面収束評価を実行できるようにした。元の細分対象と評価対象を区別する。
全水準の細分方式・対象順位・f/RQ/G・連続離散ピーク上下界、全区間の五量の差/基準/判定を表示。
最後の2区間と過去の履歴を区別し、版1の局所差のみ/版2の全域確認条件と元適応判定も明示する。
元多角形の再入角/凸角・未確認幾何を表示し、達成/確認待ち/未収束/再入角/形状未確認を分ける。
[GUI仕様](GUI_AFFINE_SURFACE_CONVERGENCE.md)。物理誤差上界なし、元適応の表面未評価・停止判定は維持。

保存はサーバーが全再検証して返したJSON文字列そのもの。ページ再読込後、適応文書を未選択のままでも
保存評価から再検証・表示できる。入力や上の適応結果を変えても前評価を自動変更せず、
改変文書・未確認ID・元場変更の拒否時にも最後の確認済み評価を保持する。
対象場ボタンは表面評価を再検証し、その最終水準のmode_indexで開く。順位1や元細分対象へ戻さない。

既存gui_surface_convergenceの通信入口に直線用の2操作を追加し、数値判定は既存APIをそのまま使う。
曲線評価の分岐、FEM/固有値/RF核、保存・追跡・表面評価の数値基準は変更していない。
新規数学文献・外部コード・依存・legacy参照はない。

着手前610件中608合格・2 skip（315.704秒）。新しいGUI操作がunknownで失敗することを先に確認。
通信3検査PASS（14.390秒）。実適応P2系列に対する対象順位2、保存文字列と全再検証、
確認待ち/短い系列、厳密フィールド/重複キー、改変評価・元ファイル拒否を確認した。

実Chrome out/browser-affine-surface-initial-20260908は初回16操作PASS。
新規適応開始→1水準で評価無効→4水準で全域確認待ち→5水準で表面達成、
元細分対象fundamentalと別のsecondの評価/順位2の場表示、五量の最後2区間と全ピーク区間表示、
正確なJSONダウンロード・改変/未確認IDで前評価保持・ページ再読込後の保存再検証を確認。
さらに再入形状、非直交対称面の形状未確認、粗い版1P1の未収束を実計算から表示した。
達成/再入角の結果画像を確認。外部ページリクエストなし。専用GUIは全7ジョブの終端を確認して正常停止。

独立out/n03-affine-surface-gui-physics-20260908もPASS。
前回と同じP1/P2円筒×尺度1/2・U=尺度²、解析f1e-4/RQG0.005/ピーク比0.01の端点比較、保存再検証を実行。
P2は全域2回を含む5水準でTARGETS_MET。P1は8水準のLEVEL_LIMIT/CONFIRMATION_PENDINGを保持。
解析値との差が基準内でもP1の確認完了とは数えない。相似則差最大2.77556e-14。

標準out/validation-n03-affine-surface-gui-20260908は613件中611合格・2 skip、PASS（328.149秒）。
seed全9モードの周波数差ゼロ、RF/エネルギー差最大8.88179e-16。
標準・ブラウザー・独立のsource_sha256は最終コードと一致。検証中のsrc/tests/scripts/examples変更なし。
GUIと独立検証のsource hashは最終コードと一致。hosted CI/Wineは未実行。

次は表面量を含む適応停止と保存再開への統合。通常RF画面への評価統合、一般形状の精度/効率、
曲線局所細分は未完。8受入・6進行中・18未受入・X01候補を維持し、N03/N04親課題全体は未受入。

## N03元多角形の角診断・追跡済み直線表面収束評価 — 2026-09-08

直前基準395e6de。affine_cornersでCaseの元多角形を診断する。
二進頂点を厳密有理数へ変換して外積/内積の符号で凸角・再入角・直線接続を分類。
軸接続は厳密な直交、PEC/電気・磁気対称面接続は凸直角だけを確認する。
細分節点の丸めを新しい角に数えず、元の軸/境界の分割点を区別する。
弦近似は元解析幾何未確認、再入角はSINGULAR_GEOMETRY、その他の未確認接続はUNVERIFIED_GEOMETRY。
NO_REENTRANT_CORNERSは必要な幾何検査であり、物理正則性や特異項の係数の証明ではない。

affine_surface_convergenceで保存適応チェックポイントを全再構築し、最低3水準の確認済み個別IDについて
native場・RF・連続離散ピーク上下界を再検証する。対象は元の細分対象IDと異なっていてもよい。
f1e-4、加速器RQ/G各0.005、ピーク比各0.01の既存N03基準を維持。
比を有理数で計算・外向き丸めし、直近2区間の上限を全五量で別判定する。
版2で最後の全域確認2水準が足りなければ、細分差が達成してもCONFIRMATION_PENDING。
未確認幾何は数値達成で消さない。元適応の停止/上限/表面未評価状態を書き換えない。
[契約](AFFINE_SURFACE_CONVERGENCE.md)。新規保存・CLI評価/再検証、文書全体/元場の改変拒否を追加。

前回の直線ピーク囲い込み、既存適応再検証、曲線表面評価の区間比較を再利用。
新しい数学文献・外部コード・依存・legacy参照はない。FEM/固有値/RF核、通常保存形式、
旧曲線表面評価契約や適応停止閾値は変更していない。一般の物理ピーク誤差上界はnull。

着手前605件中603合格・2 skip（275.572秒）。未実装module importで先に失敗を確認。
追加5検査PASS（37.963秒）。既知凸角/再入角、2の±100乗尺度、軸/境界分割、
非直交軸・対称面・弦近似の未確認、実P2系列の全域確認途中/対象順位2・保存/CLI、
短い系列/未確認ID・改変文書/元場拒否、再入形状の実FEM3水準の非受入を確認した。
版1は別途out/n03-affine-surface-v1-20260908で新規実計算3水準・保存全再検証を実施。
局所差TARGETS_MET、uniform_confirmation_required=false、two_uniform_steps_present=nullを確認。

独立out/n03-affine-surface-initial-20260908は初回PASS。P1/P2円筒×尺度1/2、U=尺度²の新規適応計算。
半径0.1・長さ0.08、初期nr6/nz4/modes1、f1e-4/RQG0.005、最大8水準/150000要素。
各水準のピークと保存全再検証、最終区間の両端の解析f/RQ/G/ピーク比差、相似則を独立に確認。
P2は48→79→117→468→1872要素、最終3853 DOF、全域確認2回を含む5水準TARGETS_MET。
最終解析差はf 6.95288e-10、RQ 1.67351e-6、G 2.75546e-9、E比4.40238e-7、B比5.34992e-7以内。
P1は48→103→217→356→777→1325→2707→4948要素、最終2533 DOF、8水準ですべて局所細分。
元適応はLEVEL_LIMIT、表面はCONFIRMATION_PENDINGを保持。確認完了・再開可能とは数えない。
最終解析差はf 1.08542e-6、RQ 0.00393375、G 5.12969e-6、E比0.000818583、B比0.00198014以内。
P1の解析差が基準内でも版2の全域確認不足を達成へ置換しない。相似則差最大2.77556e-14。
P1の保存checkpoint-008をCLIで再評価し、確認待ち文書の保存と終了値1も確認した。

標準out/validation-n03-affine-surface-20260908は610件中608合格・2 skip、PASS（313.049秒）。
seed全9モードの周波数差ゼロ、RF/エネルギー差最大8.88179e-16。
標準・独立のsource_sha256は最終ソースと一致し、検証中のsrc/tests/scripts/examples変更なし。
今回GUI/Chrome/hosted CI/Wineは実行していない。独立検証のsource hashは最終コードと一致。

次はこの直線表面評価のGUI接続と、表面量を含む適応停止・再開への統合。
一般形状の精度/効率、通常RF画面への評価統合、曲線局所細分は引き続き未完。
8受入・6進行中・18未受入・X01候補を維持し、N03/N04親課題全体は未受入。

## N03直線P1/P2の連続離散ピーク囲い込み — 2026-09-08

直前基準972f46e。表面収束評価・適応表面量停止へ向けた前提として、直線P1/P2のPEC辺上の
電場/磁場ノルム最大を上下から囲むaffine_extremaを実装した。
保存二進頂点の差からアフィンJacobianを厳密有理数で構成し、元P1/P2係数の参照多項式を制限する。
丸め済み物理勾配やP2中点座標を幾何として再補間しない。全PEC閉辺の片側微分を保持し、軸/対称面を除外。
既存rational_boundsのBernstein境界・二分・外向きsqrt丸めを再利用する。
既定囲い幅1e-6、辺/量ごと10000区間。予算/表現限界は未確認の例外とし、標本成功へ切り替えない。
[仕様](AFFINE_SURFACE_EXTREMA.md)。PASSは表現された離散場の極値だけで、物理誤差上界はnull。

APIのmodeは0始まり、bound-affine-peaksの--modeは1始まりの周波数順位。永続IDとは区別する。
native保存場をK/M・固有対・正規化・RFまで再検証し、元source hashと上下界を別文書へ新規保存。
replay-affine-peaksで元場・上下界・文書全体を再構築する。改変/元ファイル変更は拒否する。
直接APIは製造解検査のため非固有場も許すが、それを固有対と認定しない。
既存FEM/固有値/RF値・保存形式・曲線ピーク契約・適応のsurface_status=UNASSESSEDは変更しない。

既存のMaxwell縮約とP1/P2参照形状関数から今回の辺多項式を独立に導出。
本PJの曲線ピークと厳密有理数境界の方法を再利用した。新規文献・外部コード・依存・legacy参照はない。

着手前600件中598合格・2 skip（274.042秒）。未実装module importで先に失敗を確認。
追加5検査PASS（0.242秒）。傾斜要素の既知一次/二次場と独立物理微分、
H=r(1.5-r)の最大0.5625とH=r(1-r²)の最大2/(3sqrt(3))、区間予算不足、
1e±100の振幅/符号/零場、対称面除外、入力/正規P2空間、native保存/CLI/改変拒否を確認。
初期テストfixtureのCase最小メッシュ/必須profileと、磁場絶対値の端点最大を見落とした製造解を修正。
物理の許容差・囲い幅を緩める変更はない。

独立out/n03-affine-extrema-initial-20260908は初回からPASS。その結果を受入証拠として保持。
半径0.1・長さ0.08の円筒を基準にP1/P2×尺度1/2、U=尺度²、nr=8/16/32とnz=nr/2で計12実FEM。
全native保存とピーク再検証、Ritz単調性、f/RQ/G/ピーク比相似則を確認。
最終解析差はP1 f 4.25415e-6、RQ 0.00286664、G 3.78151e-7、
P2 f 1.35530e-9、RQ 6.55518e-7、G 1.17896e-8。
f<1e-4、RQ/G<0.005を維持する。ピーク比較値の中点と囲い幅は区別して保存する。
追加peak_interval_reference.jsonで最終上下界の両端とも解析ピーク比との差<0.01を確認。
最大端点差はP1 E比0.000790979、B比0.00148421、P2 E比2.75601e-7、B比3.67996e-7。
相似則差最大3.99681e-14。これらは円筒の独立比較であり、物理値の区間保証ではない。

標準out/validation-n03-affine-extrema-20260908は605件中603合格・2 skip、PASS（274.554秒）。
seed全9モードの周波数差ゼロ、RF/エネルギー差最大8.88179e-16。
標準・独立のsource_sha256は最終ソースと一致し、検証中のsrc/tests/scripts/examples変更なし。
今回GUI/Chrome/hosted CI/Wineは未実行。独立検証時のsource hashは最終コードと一致。

次は直線要素の角診断と、保存追跡済み3水準の表面収束評価への統合。
通常RF/GUIへの囲い込み統合、適応表面量停止、一般形状の精度/効率、曲線局所細分は未完。
N03/N04の親課題全体は受入せず、8受入・6進行中・18未受入・X01候補を維持する。

## N04追跡付き適応細分GUI — 2026-09-08

直前基準6f65e48。適応計算の両版をローカルGUIへ接続した。
現在のCaseから確認方式・追跡閾値・全ID/対象ID・資源/品質制約・三量の相対基準を明示して入力作成。
既存JobManagerで開始/中止し、各水準の初期/局所/全域確認、要素数/DOF、対応/対象順位、
f・加速器規約R/Q・Gを表示する。直近2区間の各量の差と判断を別表にし、
全域確認1回のPAUSED、対応未確認、各種上限停止を達成と分離する。
保存はサーバー再検証後のJSON文字列そのもの。再読込・再開で元要求・先祖を維持し、新規水準だけ計算。
中止後の完成済みexecution/checkpoint-NNN.jsonからも再開できる。
対象場は再検証した最終水準のmode_indexを使う。未確認の場表示を無効にする。
[操作と制限](GUI_ADAPTIVE_REFINEMENT.md)。表面未評価・物理誤差上界なしの表示を維持。

GUI transport、既存JobManager、既存native再検証を再利用し、FEM/固有値/RF核や停止閾値は変更していない。
数学の新規引用・外部コード転記・新規依存・legacy参照はない。
README/PHYSICS/ROADMAPの過去の「追跡/適応未実装」「C01開始前」等の記載も現状へ修正した。
一般対応の完了を意味せず、対応表の親課題8受入・6進行中・18未受入・X01候補は維持する。

着手前596件中594合格・2 skip（256.895秒）。GUI transportの未実装importで先に失敗を確認。
当初3検査PASS。入力経路の見直しで、ブラウザーのJSON.parseが重複キーを消す問題を確認。
文字列要求の未対応を先に失敗させ、入力欄を文字列のまま送信し、既存parse_jsonで厳密に解析するよう修正。
最終4検査PASS（18.255秒）。入れ子の重複キーの事前拒否、実workerの確認途中再開、
版1保存再検証、改変文書/元ファイル/異種ジョブ拒否、未確認・中止状態の分離を確認した。

初回Chrome out/browser-n04-refinement-initial-20260908は再読込検査でFAIL。
同じURLへの移動だけではhash遷移になり、ページが再読込されなかった検証手順の問題。
Page.reloadを明示し、out/browser-n04-refinement-final-20260908で18操作PASS。
その後の厳密JSON経路も含めた最終out/browser-n04-refinement-strict-20260908で19操作PASS。
両版入力、全域確認途中の保存/再開、ページ再読込、元条件保持、三量の2区間個別差、
対象順位2の場表示、未確認/水準上限、生きたジョブの中止と途中保存からの再開を実操作で確認。
外部ページリクエストなし。最終結果画像で全域2回・f/RQ/G表・未評価表示も確認した。

独立out/n04-refinement-gui-strict-physics-20260908はPASS。
既存検証スクリプトの版1/版2 P2円筒×尺度1/2、計8実workerで途中再開・管理器再生成を確認。
f<1e-4、RQ/G<0.005の独立解析基準と相似則を維持。相似則差最大5.34018e-14。
版1解析RQ差最大1.20398e-3、版2は7.49664e-6。
先祖保持・新規水準のみ計算・保存全再構築もPASS。GUI操作の成功を物理検証に代用しない。
厳密JSON修正前のout/n04-refinement-gui-physics-20260908もPASSとして保持。

最終標準out/validation-n04-refinement-gui-strict-20260908は600件中598合格・2 skip、PASS（274.706秒）。
seed全9モードの周波数差ゼロ、RF/エネルギー差最大8.88179e-16。
標準・ブラウザー・独立のsource_sha256は最終ソースと一致。検証中のsrc/tests/scripts/examples変更なし。
厳密JSON修正前のout/validation-n04-refinement-gui-20260908は599件中597合格・2 skip、PASS。
最終ブラウザーと独立検証のsource_sha256は最終コードと一致。hosted CI/Wineは未実行。
過去の版1RF改善FAILや初回ブラウザーFAILは上書きしない。

N04のGUI接続はここで受入。一般形状の精度/効率、曲線局所細分、表面量停止は残る。
次の候補はN03の直線P1/P2表面評価統合と、N04の表面量を含む適応停止への接続。
まず直線離散場のピーク評価・角診断・独立円筒の物理不変量を照合する。親課題全体は未受入。

## N04適応計算JobManager接続 — 2026-09-08

直前基準d6064fb。版1/版2の適応計算をJobManagerの別プロセス実行へ接続した。
部分実行、取消し、保存チェックポイントからの新規ジョブ再開、管理器再生成後の完了検証を追加。
先祖水準は再計算せず、要求・予算・先祖・全水準・概要・manifestを照合する。
事前の不正要求はジョブを予約せず拒否。実行失敗や要求/実装変更では完了を公開しない。
数値のTARGETS_MET/PAUSED/UNVERIFIED/上限停止とworkerのcomplete/failed/cancelledを分離する。
physical_error_bound=null、surface_status=UNASSESSED、numerical_validation=not_checkedを維持。
[JobManager仕様](ADAPTIVE_REFINEMENT_JOBS.md)。FEM/固有値/RF核、版1/版2の停止基準は変更していない。
既存のtuning_jobsと適応APIを再利用。新規数学文献・外部コード・依存・legacy参照はない。

着手前589件中587合格・2 skip（242.551秒）。未実装moduleのimportで先に失敗を確認。
追加7検査PASS（最終17.660秒）。実workerの部分実行/再開、数値未確認/上限停止、
生存中取消しとチェックポイント保持、管理器再生成、改変/manifest欠落拒否、
実行失敗/要求変更での非公開を確認した。

独立out/n04-adaptive-jobs-initial-20260908は初回PASS。その出力を受入証拠として保持。
P2円筒、要求版1/版2×尺度1/2（U=尺度²）で計8実ジョブを実行し、
先祖を保持した途中再開と管理器を開き直した後の保存全再検証を確認。
版1は3水準、版2は局所3水準＋全域2水準でTARGETS_MET。
解析相対差の最大値は版1 f 5.31040e-7、RQ 1.20398e-3、G 3.28083e-6、
版2 f 2.38324e-9、RQ 7.49664e-6、G 1.55636e-8。
独立基準f<1e-4、RQ/G<0.005を満たし、相似則差最大5.34018e-14。
例の停止許容値が広くても独立検証基準は緩めていない。

標準out/validation-n04-adaptive-jobs-20260908は596件中594合格・2 skip、PASS（257.481秒）。
seed周波数差ゼロ、RF/エネルギー差最大8.88179e-16。
標準・独立のsource_sha256は最終ソースと一致し、実行中のsrc/tests/scripts/examples変更なし。
今回GUI/Chrome/hosted CI/Wineは実行していない。過去の独立FAILと全域確認の証拠は保持。

次は適応計算のGUI接続。一般形状の精度/効率、表面量停止、曲線局所細分は引き続き未完。
親課題8受入・6進行中・18未受入・X01候補を維持し、N04全体は未受入。

## N04全域細分によるRF確認・親子メッシュ内積追跡 — 2026-09-08

直前基準b0a809e。前回の円筒P1で局所細分差が達成してもR/Q解析差1.96%が残り、
Gの解析誤差も初期より僅かに悪化した事実を、今回の改善対象とした。
版2要求にconfirmation="uniform_two_steps"を追加。局所候補が直近2区間のf/RQ/G基準を
満たした後は全要素4分割へ移り、最低2回の全域細分と直近2区間の三量達成を要求する。
全域確認が未達なら全域細分を続ける。版1の判定・保存文書を自動変更しない。
確認の段階も保存・全再構築・途中再開・CLI再検証へ接続した。
[版2仕様](ADAPTIVE_REFINEMENT.md)、例examples/adaptive_refinement/pillbox_confirmed.json。

全域確認を進めると旧same_domainの標本上限を超えるため、明示親子細分用のnested_affineを追加。
選択と旧メッシュから全細分を再構築し、新側の座標/接続/全タグと照合する。
係数移送Pと既存の細メッシュ質量Mで∫r³uvを計算し、薄いQRと小行列Choleskyで
同じ内積を持つ少数行の座標へ変換して既存SVD/対応核へ渡す。
列Gramの直接平方根化・負固有値切捨て・対角正則化はしない。従属性をRに残す。
再構築内積差と正定値性を検査し、作業量はfine_dofs*(old_modes+new_modes)<=8388608を要求。
物理点標本とは区別して保存する。旧same_domainの上限/計算法は変更しない。
[内積仕様](NESTED_AFFINE_TRACKING.md)。追加の生きたnative対応で作業量上限の拒否も確認した。

R34のLAPACK公開マニュアルでQR/Choleskyの一般式を確認し、本PJの質量形式への組合せを独立に導出。
既存NumPy/SciPyだけを使用。外部コード・本文・図の転記、新規依存、legacy参照はない。
FEM/固有値/RF核や物理基準は変更していない。有限次元内積の一致を物理離散化誤差の保証にはしない。

着手前583件中581合格・2 skip（231.705秒）。親子内積の未実装importで先に失敗を確認。
追加6検査PASS。内積3件（最終0.183秒）はP1/P2の次数6独立積分、同一場の符号/順位置換、
従属モードの未確認、native保存再検証・誤った細分指定/不正閾値拒否を含む。
全域確認3件（8.540秒）は局所候補後の2回の実FEM全域細分、確認途中の再開で新しいsolve1回、
版2CLI再検証・段階の改変拒否、全域確認でのRF未達を局所達成で消さないことを含む。
過去の版1 out/n04-adaptive-refinement-final-20260908/cylinder-p1-s1.jsonも文書全体一致で再検証した。

独立out/n04-rf-confirmation-initial-20260908は初回からPASSで、その出力を受入証拠として保持。
前回のf1e-4、RQ/G各0.005、解析RF改善条件、相似則、Ritz/解析周波数改善は維持。
追加確認のため資源予算のみ円筒P1最大8水準/他5水準・250000要素へ増やした。
円筒/合成折返しP1/P2×尺度1/2、native保存後の全再構築、一様3水準対照、
全比較の次数6内積を検査。内積の絶対差最大1.11023e-15、f/RQ/G相似則差最大4.39316e-13。

尺度1の円筒P1は局所5水準の後、全域3回で8水準TARGETS_MET。
三角形1495→5980→23920→95680、最終48069 DOF。
直近RQ変化は0.440738%/0.137773%。最終解析差はf 1.18408e-7、RQ 5.61596e-4、G 7.12550e-8。
R/Q差は前回1.95839%から0.056160%へ減り、Gも初期より改善して前回のRF改善FAILを解消した。
円筒P2は局所3水準＋全域2回、5水準TARGETS_MET、3664要素/7485 DOF。
最終解析差はf 5.92170e-10、RQ 1.77008e-6、G 3.77937e-9。
折返しP1/P2は5水準でLEVEL_LIMITを保持。一般形状の収束を達成と偽らない。

標準out/validation-n04-rf-confirmation-20260908もPASS。
589件中587合格・2 skip（241.258秒）。seed周波数差ゼロ、RF/エネルギー差最大8.88179e-16。
標準・独立のsource_sha256は最終ソースと一致。実行中のsrc/tests/scripts/examples変更なし。
GUI/hosted CI/Wineの再実行は含めない。前回の独立FAIL・pilot・版1結果も保持する。

全域確認後もphysical_error_bound=null、surface_status=UNASSESSED。
P1で約4.8万DOFを要したため、精度改善を効率優位の受入へ代用しない。
RFに対応する効率的な選択、一般形状の精度/効率、表面量の停止、曲線局所細分、GUI/JobManagerは残る。
親課題8受入・6進行中・18未受入・X01候補を維持し、N04全体は未受入。

## N04追跡付き適応細分・保存再開API/CLI — 2026-09-08

直前基準484e777。adaptive_refinementで同じ直線領域の残差→割合選択→適合細分→実FEMを接続。
初期Case/メッシュ、全個別ID、対象ID、品質/要素/水準上限、追跡controls、f/RQ/G基準を明示。
直近2区間の三量がすべて基準内ならTARGETS_MET、追跡曖昧・上限・不正量は別状態で停止。
物理誤差上界はnull、表面量はUNASSESSEDを保持する。[仕様](ADAPTIVE_REFINEMENT.md)。

各水準をnative保存し、選択/全メッシュ/全追跡/全判定を保存場から再構築するチェックポイントを追加。
再開は新しい出力先で新しい水準だけをsolveする。実装/先祖ファイル変更・改変文書を拒否し、
失敗記録を保存して前のチェックポイントを保持する。APIとadaptive-refine/
resume-adaptive-refinement/replay-adaptive-refinement CLIを追加。
PAUSED/TARGETS_METは終了値0、他の数値判定は1。PAUSEDを完了とはしない。

通常の直線read_solutionは行列を持たず、前回の残差指標仕様の利用例説明が不正確だった。
affine_saved.read_verified_affine_solutionを追加し、K/M再組立て、拘束・正規化/直交性・
固有対残差・全RFを再検証して行列付き解を返す。閾値は既存曲線保存検査と同じ。
通常readerの契約は変えず、残差指標仕様をこの専用readerへ訂正した。
same_domainは同じ電気/磁気対称面タグの保存場比較にも対応。全境界被覆とタグ一致は維持。
FEM/固有値核・RF式・追跡重なり核の変更、外部依存/新規資料/legacy参照はない。

着手前576件中574合格・2 skip（224.593秒）。未実装importで先に失敗を確認した。
新規7検査の最終実行はPASS（6.024秒）。P1/P2解析円筒周波数の変分改善とID、
二つの区間/各RF量の未達保持、全再構築、再開solve数、失敗・改変拒否、対称面、
要素/標本予算と追跡未確認、CLIの作成/再開/再検証/非合格終了を含む。
最初のfocused検査はテスト側のcluster_gap=1が既存の厳密入力で拒否され、
許される0.9へ訂正して未解決部分空間の停止を検査した。実装の追跡閾値は変えていない。

初回標準out/validation-n04-adaptive-refinement-20260908は583件のうち2件ERROR。
要求JSON例をCase専用examples直下へ置いたためで、既存テストを変更せず、
examples/adaptive_refinement/pillbox.jsonへ移動した。初回ログを保持する。
最終out/validation-n04-adaptive-refinement-final-20260908はPASS、
583件中581合格・2 skip（230.396秒）。seed周波数差ゼロ、RF/エネルギー相対差最大
8.881784197001252e-16。標準・最終独立のsource_sha256は最終ソースと一致。
検証中のsrc/tests/scripts/examples変更なし。GUI/hosted CI/Wine再実行は含めない。

独立検証は未達を保持する。初回out/n04-adaptive-refinement-initial-20260908では
円筒P1が3水準でR/Q基準を満たさずLEVEL_LIMIT、総合FAIL。
fは基準内でもRQの0.830%/1.740%変化を別判定した。
基準f1e-4、RQ/G各0.005は変えず、別pilotで予算7水準を試し、5水準でTARGETS_MET。
最終out/n04-adaptive-refinement-final-20260908では円筒P1のみ予算7、他は3水準、
一様対照は各3水準を実FEMで計算。P1は5/P2は3水準で細分差達成、折返しP1/P2は
LEVEL_LIMIT。全個別IDは追加次数4でも一致し、完全再構築・尺度間選択一致・
Ritz単調性・解析周波数改善・f/RQ/G相似則（最大1.82965e-13）は確認できた。

しかし最終独立検証も円筒P1のRF改善条件で総合FAIL。
P1局所の解析R/Q差は初期4.88971%から1.95839%へ改善したが、一様対照の0.472912%より大きい。
G解析誤差は初期1.04284e-5に対し最終1.05812e-5と僅かに増加した。
P1最終DOFは局所777/一様825、周波数誤差7.10881e-6/7.55376e-6。
P2局所DOF498でf誤差1.38174e-7、RQ差3.07434e-4、G差8.51606e-7。
全RF/選択/DOFと時間を保存し、適応のworkflow時間と一様の細分/solve時間を同じ時間定義にしない。
細分差の達成を物理RF受入へ読み替えず、RF改善条件・許容差を緩めない。初回/pilot/最終の全出力を保持。

次はRF精度に対応する選択/独立確認を改善・評価する。表面量の停止、曲線局所細分、
GUI/JobManager、一般の誤差対DOF/時間受入も残る。N04全体は未受入。
親課題8受入・6進行中・18未受入・X01候補を維持する。

## N04重み付き残差指標と細分対象選択 — 2026-09-08

直前基準cb3cd3f。residual_indicatorとmark_bulkを追加。
PHYSICS.mdのTM強形式からr Δu+3u_r+λr uを導出し、r重み付き二乗残差を要素長で尺度化。
内部辺の法線微分ジャンプを一度だけ両隣へ配分し、PEC壁の2 n_r uを保持する。
軸の有限u・電気対称面の自然条件・磁気対称面の本質条件を分離。
全量を正のu.T K uで割り、場の符号/正規化に依存しない優先度として返す。
非有限・ゼロ場・不正モード・次数/全境界不一致・拘束違反・二次曲線幾何は拒否する。
二乗指標の指定割合を覆う最短の降順先頭列を選び、同値は要素番号順。
全ゼロは空、割合1は正の全要素。上限と品質は既存の適合細分APIが検査する。
[仕様](RESIDUAL_INDICATOR.md)。FEM/固有値/既存RF核、基準・許容差は変更していない。

R33の公開一次資料で一般の要素/辺残差分解を確認し、本重みはTM弱形式から独立に導出。
r³が軸で退化する固有値問題へ、一般楕円型問題の誤差上界定理をそのまま適用しない。
physical_error_boundはnullで固定。代数残差・周波数・RF/ピークの誤差とは区別する。
コード・本文・PDFの転載、新規依存、legacy参照はない。

着手前571件中569合格・2 skip（225.147秒）。独立不変量は全体多項式の体積/壁積分と
区分線形の辺ジャンプ一回配分。未実装importで先に失敗を確認した。
追加5検査の最終実行はPASS（0.139秒）。軸/両対称面、任意振幅・極端な1e±200倍率、
長さ/エネルギー相似、代数残差が小さくてもゼロでない本指標、選択順序・厳密入力を含む。
追加の独立SciPy積分で非ゼロλの符号と傾斜PEC壁の法線式も確認し、相対差最大4.66294e-15。
その記録は最終独立出力のpolynomial_checks.json。

初回out/n04-residual-indicator-initial-20260908はPASS、標準
out/validation-n04-residual-indicator-20260908も576件中574合格・2 skip（224.926秒）でPASS。
完了後の入力レビューで0次元配列の明示拒否を追加し、整数場の浮動小数点化と総和の
範囲逸脱診断を整備。極端振幅の検査も追加した。初回出力は保持し、最終ソースで再実行した。

独立out/n04-residual-indicator-final-20260908はPASS。円筒/合成折返し×P1/P2×尺度1/2で、
孤立した最低モードを指標50%選択と一様細分で各2回再計算。全水準の場/RF/指標・
要素/DOF・指標時間・細分/solve時間を保存した。どの系列も指標が減少し、
円筒解析周波数誤差も改善、Ritz単調性・同じ尺度間選択を確認。
指標相似則差最大3.18190e-13、f/RQ/G相似則差最大1.82965e-13。
円筒局所の周波数相対誤差はP1 1.10296e-4→2.50387e-5、P2 1.04035e-6→1.38174e-7。
局所最終DOFはP1 239/P2 498、一様825/3185。一様の誤差は7.55376e-6/4.31362e-9。
折返し局所最終DOF197/527に対し一様1497/5809。少ないDOFだけで効率優位とは結論しない。
一般モード追跡付き適応停止・RF/表面量の個別停止・曲線局所細分・製品CLI/GUI/保存再開は残す。
親課題は8受入・6進行中・18未受入・X01候補を維持する。

最終out/validation-n04-residual-indicator-final-20260908はPASS。
576件中574合格・2 skip（227.598秒）。seed周波数差ゼロ、RF/エネルギー相対差最大
8.881784197001252e-16。標準・独立のsource_sha256は最終ソースと一致。
検証実行中はsrc/tests/scripts/examplesを変更していない。GUI/hosted CI/Wineの再実行は含めない。

## N04選択要素の適合細分・P1/P2係数移送 — 2026-09-08

直前基準7c70334。N04の局所細分基盤としてrefine_marked_cellsを追加。
明示した直線三角形の3辺を分割し、最長辺による隣接閉包を求める。既存contour_meshの
_split_marked_edgesを再利用し、共有辺中点・境界タグ・全領域の検証は従来処理を保持する。
既存の辺長指定細分・曲線一様細分・FEM核は変更していない。

各子要素の親と親重心座標を記録し、二進分数の位置で旧P1/P2基底を評価してCSR移送行列を作る。
共有自由度の係数行が一致することを確認する。入力メッシュは再読込コピーを使い、変更しない。
指定要素、実分割辺、親対応、品質を返す。Caseと呼出し側のうち厳しい要素上限/最小角を守り、
不正選択・予算超過・品質未達・二次曲線幾何は明示拒否する。
自動誤差指標・適応停止・曲線の局所細分やUI接続はまだ含めない。[仕様](MARKED_REFINEMENT.md)。

着手前567件中565合格・2 skip（226.719秒）。独立不変量としてP.T A_new P=A_oldと
任意係数の場/勾配保持、同一演算子の変分単調性を選び、未実装importで先に失敗を確認。
追加4検査PASS（0.455秒）。局所性、面積/体積/タグ、P1/P2の場/勾配/剛性/質量、
磁気対称面拘束と軸、全選択の4分割、実FEMの単調性、折返し輪郭、入力不変、厳密拒否を含む。

独立out/n04-marked-refinement-initial-20260908は初回からPASS、実行中のsource変更なし。
円筒/合成折返し輪郭×P1/P2×尺度1/2、局所/一様の各2段階を実FEMで再計算・保存。
Galerkin相対差最大1.74568e-15、体積差最大6.66134e-16、f/RQ/G相似則差最大1.82965e-13。
すべての細分で固有周波数が減少し、円筒の各周波数は独立Bessel値より上。
全水準の円筒相対誤差範囲はP1 7.55375e-6〜0.00576838、P2 4.31361e-9〜1.68298e-5。
局所2段階の円筒639要素に対し一様1536、折返し728に対し一様2816。
DOF・時間・全RF量も保存。局所選択は座標で明示した領域であり、誤差駆動の最適な選択とはしない。
少ない要素数だけで誤差/効率が優れると結論しない。RF/ピークの物理収束受入ではない。
新規外部資料・依存・legacy参照なし。既存公開数学由来の基底とGalerkin形式を用いた。

最終out/validation-n04-marked-refinement-20260908はPASS。571件中569合格・2 skip（226.986秒）。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001252e-16。基準・許容差変更なし。
標準と独立検証のsource_sha256は最終ソースと一致。初回の独立出力はそのまま受入証拠として保持する。

親課題は8受入・6進行中（N04追加）・18未受入・X01候補。N04全体の完了とはしない。

## N03表面収束評価のGUI接続 — 2026-09-08

直前基準21fb6a0。保存したモード履歴/追跡済みStudyから個別IDの表面収束評価を実行する
GUI transportと画面を追加。Study文書自体を再検証してから履歴を数値APIへ渡す。
既存read_surface_convergenceの再構築処理をreplay_surface_convergenceへ切り出し、
API/CLIの計算・判定・保存契約は維持する。新規依存や外部サービスは追加していない。

画面は各水準の周波数/RQ/G、ピーク比の上下界、各区間の最大相対変化/基準/判定対象を分離。
基準達成（細分差）・未収束・特異形状・形状未確認を表示し、元結果と角診断も保持。
評価はサーバーで行い、表示丸めを判定へ使わない。元JSON文字列を保存/再検証し、
ID変更や改変ファイルの拒否時に直前の検証済み評価を上書きしない。
履歴/IDの変更後は再評価が必要と明示し、3水準未満では評価ボタンを無効にする。

着手前567件中565合格・2 skip（223.938秒）。既存表面評価5検査PASS（29.573秒）。
数値評価核・基準・FEM・既存RF/Studyの未認証表示に変更なし。
実Studyはout/n03-gui-study-final-20260908の固定二次幾何3水準を新規計算して追跡PASS。
最初の準備はパラメータ名にJSON pointerを指定せず入力検査で拒否された。空の
out/n03-gui-study-20260908を保持し、正しい/case/mesh/curved_refinement_levelsで別出力へ実行した。

実Chrome out/browser-n03-surface-20260908は51項目PASS（追加11/既存40）、外部要求0。
保存履歴からの評価、3水準のRF/ピーク上下界、個別IDと基準、元JSON保存/再検証、
誤ID/改変時の前評価保持、再入角の未認定表示と再検証、追跡済みStudyの評価を確認。
surface-targets.pngとsurface-singular.pngを画像確認。球形36/144/576要素の達成表示と、
再入角18/72/288要素の未認定表示・ピーク比・各基準を確認。専用GUIはargv完全一致で停止済み。
新規外部資料・legacy参照なし。GUI追加のため、数値不変量は既存独立球形系列で再確認する。

最終out/validation-n03-surface-gui-20260908はPASS。567件中565合格・2 skip（224.781秒）。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001252e-16。基準・許容差変更なし。
独立out/n03-surface-gui-final-20260908は球形2系列でPASS、相似則差最大4.92940e-14。
標準・独立・Chrome検証のsource_sha256はいずれも最終ソースと一致。

一般形状・幾何近似誤差・直線要素の収束評価、通常RF結果画面への評価統合は残る。
親課題8受入・5進行中・19未受入・X01候補は維持する。

## N03固定曲線幾何の表面収束評価API/CLI — 2026-09-08

直前基準904c72b。N03へ着手し、追跡済み個別IDの保存履歴から固定曲線P2の
周波数/RQ/G/ピーク比を評価するsurface_convergenceを追加。最低3水準・直近2区間を要求し、
元Case/元メッシュ不変とcurved_refinement_levelsの厳密増加を検証する。
curved_same_domainの全境界照合と保存場再検証を用い、rankを固定IDと取り違えない。

f 1e-4、accelerator R/QとG各0.005、Epk/EaccとBpk/Eacc各0.01を別判定する。
ピーク上下界をEaccで割った区間から最大相対変化を計算。二進入力をFractionで厳密に扱い、
外向き丸めでピーク探索区間の不確かさを消さない。範囲逸脱や有意でない加速電場は未確認。
元解析曲線の再入角はSINGULAR_GEOMETRY、他の未分類角/非直交軸接続はUNVERIFIED_GEOMETRY。
球・楕円体の直交極は明示角度許容差で検査し、軸の内部分割点は物理角と数えない。
TARGETS_METは二つの細分差の達成であり、物理誤差上界や解析境界への収束証明ではない。
既存RF/Studyの未認証表示は変更していない。

assess-surface-convergence/replay-surface-convergenceを追加。新規ファイルへ評価・全履歴・
基準・全水準を保存し、再構築時に評価やsourceの変更を拒否する。未達/特異でも診断は保存。
GUI品質表示、一般形状/幾何近似の収束、直線要素統合等は残す。[仕様](SURFACE_CONVERGENCE.md)。

着手前562件中560合格・2 skip（194.363秒）。独立の区間不変量を含む新規テストは
未実装のimportでまず失敗。追加5件PASS（29.637秒）：同じ上側推定値でも広い区間を拒否、
直近2区間の各量判定、外向き比の包含、球極/円錐先端/再入角、実FEM保存履歴・逆細分拒否・
改変拒否・上書き拒否。FEM、既存追跡核、ピーク探索核と数値基準を変更していない。

初回out/n03-surface-convergence-initial-20260908は数値項目PASSだが、テスト追加を検知して
総合FAIL。36/144/576要素の球形、長さ1/2とエネルギー1/4の二系列でTARGETS_MET。
最終解析差はf最大2.48230e-5、RQ 6.48881e-6、G 8.80690e-7、
Epk/Eacc 2.65676e-4、Bpk/Eacc 3.84609e-5。相似則差最大4.92940e-14。
解析式は既存SphereTMの独立参照のみで、FEMに使用しない。新規外部資料・依存・legacy参照なし。
初回結果を保持し、最終固定ソースの検証を別出力へ記録する。

最終out/validation-n03-surface-convergence-20260908はPASS。567件中565合格・2 skip（225.948秒）。
seed周波数差ゼロ、RF/エネルギー差最大8.881784197001252e-16。基準・許容差変更なし。
独立out/n03-surface-convergence-final-20260908もPASS、標準/独立のsource_sha256は最終ソースと一致。
CLI out/n03-surface-convergence-cli-20260908.jsonの作成・再検証はTARGETS_MET、終了値0。

再入角を持つ実FEM18/72/288要素のout/n03-singular-cli-20260908でも、CLI作成/再検証は
SINGULAR_GEOMETRYを保存して終了値1。角診断は再入角1/凸角3、細分診断自体もNOT_CONVERGED。
特異形状を有限ピーク合格として扱わない経路を、合成行データだけでなくnative保存系列で確認した。

親課題は8受入・5進行中（N03追加）・19未受入・X01候補。N03全体の完了とはしない。

## D01曲線P2のアフィン再メッシュ追跡 — 2026-09-08

直前基準18f63e2。既存affine_remesh controlsを曲線P2へ拡張。双方のnative primitiveの
番号/パラメータ対応を契約とし、逆変換した新側二次境界のBernstein係数を共通区間で照合する。
全辺位置差の上界・全区間被覆・タグを検査し、誤写像と再投影境界を拒否。
実曲線FEM場を双方の物理積分点で相互評価し、新側Hphi/aと体積/(a²c)を用いる。
元のFEM行列・固有値・係数、既存直線アフィン/同一曲線領域の再検証契約は維持。
GUIは既存の係数入力・逆変換・履歴/保存経路を使用し、曲線境界条件を説明に追加。

着手前558件中556合格・2 skip（185.583秒）。既知多項式場のアフィン引戻しによる
重なり1と体積比を独立不変量として追加し、実装前に4件のFAIL/ERRORを確認。
新規4検査と既存直線アフィン6検査PASS（9.744秒）。恒等写像、異方倍率の実FEM往復、
保存/履歴再検証、境界中点差・誤倍率・再投影・非PEC/混在拒否を含む。
せん断は合成多項式場のadapter検査に限定し、せん断曲線Caseの実固有モード受入とはしない。

独立数値検証は球形102/408要素と合成楕円体90/360要素を半径1.2倍・軸0.8倍し、
尺度1/2・積分次数3/5・保存逆方向を確認する。球形解析周波数差最大2.8990e-5、
f/RQ/G相似則差最大2.62013e-14、次数による重なり差最大2.572991e-7、
往復差最大3.33067e-16、体積比の相対差最大4.44090e-16。
解析楕円体体積との差7.38411e-5は二次境界近似の差であり、丸め差とは扱わない。
異方変形によりf/RQ/G自体は変わる（球形の相対変化は約−0.1514/+1.7173/−0.1799、
楕円体は−0.1476/+4.4377/−0.1439）。追跡PASSをRF不変・RF収束と解釈しない。

初回out/d01-curved-affine-initial-20260908は数値項目PASSだがGUI説明更新を検知して総合FAIL。
固定ソースでout/d01-curved-affine-final-20260908とout/d01-curved-affine-verified-20260908はPASS。
後続の検証スクリプト修正があるため、最終受入では再度ソースfingerprintを照合する。
ブラウザー初回out/browser-curved-affine-20260908とverified版は、追加検査が保存文書の種別を
mode_tracking_pairと誤記して待機し停止した（正しくはsaved_mode_tracking）。
途中のfinal版は既存Job入りのworkspaceで初期件数条件を満たさず停止。各失敗結果は保持。
クリック位置安定待ちも既存tuning検証と同方式へ統一したが、種別誤記の原因修正とは区別する。
製品の追跡・境界判定や許容差を緩めていない。新規外部資料・依存・legacy参照なし。

Chrome最終out/browser-curved-affine-accepted-20260908は40項目PASS（追加5/既存35）、
外部要求0、ソース変更なし。逆係数a=0.8333333333333334/c=1.25/b=0と境界条件の
画面表示をcurved-affine-history.pngで画像確認。専用GUI三件はargv完全一致で特定し停止済み。

最終out/validation-d01-curved-affine-final-20260908はPASS、562件中560合格・2 skip（199.245秒）。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001252e-16、基準・許容差変更なし。
独立out/d01-curved-affine-accepted-20260908もPASS。境界係数距離最大2.22045e-16 m。
標準・独立・Chrome検証のsource_sha256は最終ソースと一致。CLIの比較保存と再検証も
out/d01-curved-affine-cli-20260908.jsonでPASS。コード・テスト・検証スクリプトを固定して最終検証した。

一般非線形曲線写像、再近似領域の対応、対応推定、個別枝回復は残る。
親課題8受入・4進行中・20未受入・X01候補は維持する。

## D02連動座標の周波数調整 — 2026-09-08

直前基準c5233d9。tune request第2版にparameter名・parameter_unit（m/1）・bindingsを追加。
座標[m]=multiplier×変数+offset_m。全profile座標を同時更新してから形状を検査し、
順序依存の中間不正形状で有効な連動変形を拒否しない。重複/未知座標、非有限/範囲外、
全ゼロ倍率・丸めで形状が変わらない変数を拒否。既存の単一座標v1経路とcheckpoint版1は維持。
API/CLI/JobManager/GUIの共通tune経路で扱い、変更したbindingによる履歴再開/改変を拒否。
GUIは連動指定と単位の入力/復元・結果列の単位表示、保存文書の条件による再開へ接続。

着手前552件中550合格・2 skip（177.358秒）。既存のv2拒否で5件のFAIL/ERRORを確認後、
追加6検査PASS（6.865秒）。同時更新/順序不変、m/無次元と負倍率、厳密拒否、
実円筒半径の解析目標、CLI/保存/再開/改変拒否を確認。v1の既存
out/d02-tuning-example-resumed-20260908/checkpoint-017.jsonも再検証してTUNED。

out/d02-coupled-tuning-final-20260908は長さ/無次元×尺度1/2の4系列でPASS。
実workerで管理器再起動・2試行から再開し、各15試行でTUNED、元source不変。
半径相対差5.25034e-6、最終形状の解析周波数差最大4.33668e-9、
f/RQ/G相似則相対差最大2.57572e-14。mと無次元の表現間ではf/RQ/G差ゼロ。
解析式は検証専用の既存円筒TM010関係。FEM/追跡/探索核・基準・許容差変更なし。

Chrome out/browser-coupled-tuning-final-20260908は19項目PASS（連動追加6/既存13）、外部要求0。
coupled-result.pngで変数の無次元表示・15試行・最終細分を画像確認し、円筒を保つ最終場も確認。
初回out/browser-coupled-tuning-20260908は非同期入力生成を待つ前の検査でFAIL。
生成完了待ちを追加して全項目を再実行し、初回も保持。製品判定は変更していない。
専用GUIはargv完全一致で特定して停止済み。新規外部資料・依存・legacy参照なし。

一般曲線/折返し/組立、非線形結合、複数独立変数の制約付き最適化、
細分未達後の自動再探索・個別枝回復は残る。親課題8受入・4進行中・20未受入・X01候補を維持。

最終out/validation-d02-coupled-tuning-20260908はPASS。558件中556合格・2 skip（187.376秒）。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001252e-16。
標準・独立・Chrome検証のsource_sha256は最終ソースと一致。基準・許容差変更なし。

## D02周波数調整のGUI接続 — 2026-09-08

直前基準0b40a5e。GUI transportのstart/result/replay/resumeをJobManagerへ接続。
形状・追跡設定からの入力作成、座標範囲・目標MHz・二つのHz許容差・探索/細分上限、
開始/中止/結果表示、検証済み元JSON保存/再検証/再開を追加した。
Job処理完了とTUNED/未確認/細分未達を分け、試行表に探索/最終細分・対象順位・周波数・目標差を表示。
表示の小数は丸めるが元JSONを変更しない。再開は入力欄でなく検証済み文書の条件を使う。

TUNEDの最終場を開く際は文書を再検証し、最終native Jobを通常結果へ取り込んで、
対象IDの現在順位を選択する。一般openResultの既定順位選択は維持する。
調整Jobを単独解の選択欄へ混ぜない。物理誤差上界やRF/ピーク収束は保証しない。
着手前549件中547合格・2 skip（168.278秒）。未実装import失敗後、transport追加3検査PASS（10.197秒）。

Chromeはout/browser-tuning-final-20260908で13項目、既存追跡は
out/browser-tuning-tracking-regression-20260908で35項目、既存Studyは
out/browser-tuning-study-final-20260908で11項目PASS。全59項目、外部要求0。
tuning-result.pngで二つのゲート・17試行・順位3→2・最終細分を画像確認した。
最終場は対象の順位2で描画することも確認。
初回Studyのout/browser-tuning-study-regression-20260908はスクロール中の誤クリックで
期待ファイルがなくFAIL。別ダウンロードdownloads.htmlも含め出力を保持した。
既存adaptive検証と同じ即時スクロール・2描画待ち・実ヒット対象確認へverifierを修正し、
11項目を再実行。製品の保存規約や許容差は変更していない。

out/d02-tuning-gui-final-20260908のJobManager経由独立検証はPASS。
尺度1/2各17試行、長さ相対差5.88291e-6、解析周波数差最大1.14697e-7、
f/RQ/G相似則最大4.64074e-14。標準と独立検証はverifier修正後に再実行。
独立・3ブラウザーのsource_sha256は最終ソースと一致。専用GUI2件を完全一致argvで停止済み。
新規外部資料・依存・legacy参照なし。FEM/RF/追跡/探索核・基準・許容差変更なし。

一般写像・個別枝回復、曲線/折返し/連動変数、細分未達後の自動再探索、制約付き最適化、
取消し後のcheckpoint自動一覧選択は残る。親課題8受入・4進行中・20未受入・X01候補を維持。

最終out/validation-d02-tuning-gui-final-20260908はPASS。552件中550合格・2 skip（178.806秒）。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001252e-16。
標準・独立・3ブラウザーのsource_sha256は最終ソースと一致。基準・許容差変更なし。

## D02周波数調整のJobManager接続 — 2026-09-08

直前基準5f280cb。JobManager.start_tuneとtuning_jobsの実workerを追加。
別プロセスFEM、取消し、PAUSED再開、管理器再起動へ接続した。
job status=completeとtuning_statusのTUNED/PAUSED/UNVERIFIED/細分未達/探索限界を分離。
通常のnumerical_validationはnot_checkedを維持し、全般的な精度保証へ読み替えない。

完了時はrequest/results・全executionのhashを公開する。read_job(verify=True)で
保存場と探索判断を再検証し、再開元hash・Job種類/要約・試行上限・今回の保存先・
必須checkpoint/試行ファイルを照合する。実行中の入力/実装変更は完了公開前に拒否。
実行失敗と数値未達を区別し、完全保存済みのcheckpointを再検証して別Jobへ再開する。
取消し中の書きかけJSONを確認済みとは扱わない。

着手前542件中540合格・2 skip（162.734秒）。未実装import失敗を確認後、
追加7検査PASS（5.483秒）。実workerの停止/再開、順位交換、祖先改変、取消し後の再開、
再起動、厳密入力、要約/種類/上限/manifest欠落、実行失敗、実行中入力変更を確認した。
既存JobManagerの専有workspace・プロセス取消しと既存tuning APIを再利用。
FEM・RF・追跡・探索核と許容差/seed変更なし。新規外部資料・依存・legacy参照なし。

out/d02-tune-jobs-20260908のvalidate_tuning.py --backgroundはPASS。
尺度1/2それぞれ管理器を再起動して2試行から再開し、17試行でTUNED。
長さ相対差5.88291e-6、最終形状の解析周波数差最大1.14697e-7、
f/RQ/G相似則差最大4.64074e-14。初期順位3→最終2、元2試行hash不変。
独立検証source_sha256は最終ソースと一致。全workerは管理器closeで回収済み。

GUI・曲線/折返し/連動変数・細分失敗後の自動再探索・制約付き最適化は残る。
親課題8受入・4進行中・20未受入・X01候補を維持。D01/D02親課題全体は未受入。
再現手順・Job状態の意味は[TUNING.md](TUNING.md)を参照。

最終out/validation-d02-tune-jobs-20260908はPASS。549件中547合格・2 skip（168.758秒）。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001252e-16。
標準・独立検証のsource_sha256は最終ソースと一致。FEM/RF核・基準・許容差変更なし。

## D02追跡付き1変数tune初期実装 — 2026-09-08

直前基準64a086f。tuning.pyに明示円筒/profile写像の二分探索、保存場による個別ID確認、
全試行の不変チェックポイント・停止/再開・最終同一形状の細メッシュ判定を追加。
tune/resume-tune/replay-tune CLIとexamples/tuning/pillbox_length.jsonを接続した。
全個別IDが確認できない試行を周波数評価へ渡さず、部分空間/曖昧対応は停止する。
目標誤差と粗細周波数差を別々に判定し、二水準差を離散化誤差上界とは呼ばない。
FEM核・RF核・許容差・seed値は変更なし。

実装判断: 一般追跡全体の完成待ちから、受入済み写像と各試行の全個別ID確認を
条件にした限定tuneの段階実装へ進めた。D01一般写像/枝回復の残要件は維持する。
同じJob/source検証、Studyの変数適用/細分、保存場追跡を再利用。二分法は目標との差の
符号を保持する今回の独立実装。新規外部資料・依存・legacy参照なし。

着手前531件中529合格・2 skip（151.481秒）。未実装import失敗を確認。
初回6×8の83 mm目標で、粗目標差−87252.09 Hzに対し細目標差−139668.35 Hzとなり、
REFINEMENT_FAILED。out/d02-tune-refinement-failed-20260908を保持し拒否テストを追加。
成功側は許容差を変えず12×16へ細分した。
最初の標準回帰は調整requestをexamples直下に置いたため既存Case検査2件が失敗。
out/validation-d02-tuning-20260908を保持し、通常Caseの検査は維持して
examples/tuningへ移動。ソースを固定して標準・独立検査を再実行した。

out/d02-tuning-accepted-20260908は尺度1/2とも17試行でTUNED。
目標長相対差5.88291e-6、最終形状での解析周波数差最大1.14697e-7、
f/RQ/G相似則差最大4.64074e-14。初期順位3から2へ交換し、再開前2試行のhash不変。
同梱例のCLIもout/d02-tuning-example-20260908から別出力へ再開してTUNED、
checkpoint-017.jsonの再検証成功。詳細と再現手順は[TUNING.md](TUNING.md)。

GUI/JobManager、曲線/折返し/連動変数、細分失敗後の自動再探索、制約付き最適化は残る。
親課題は8受入・4進行中（C00/G03/D01/D02）・20未受入・X01候補。D02全体は未受入。

最終標準回帰out/validation-d02-tuning-final-20260908はPASS。542件中540合格・2 skip
（163.391秒）。seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001252e-16。
標準・独立検証のsource_sha256は最終ソースと一致。追加11検査PASS。
数値基準・FEM核・RF核変更なし。新規依存と外部サービスなし。

## D01同一二次曲線領域のGUI接続 — 2026-09-08

直前基準a38f83a。curved_same_domainの写像選択・保存復元と適用条件表示を追加。
比較診断に物理写像の証拠を表示する。固定境界の曲線再メッシュを比較・履歴継続でき、
解析曲線が同じでも再投影で二次境界が変わる場合は拒否して確認済み履歴を保持。
数値核は変更なし。

着手前531件中529合格・2 skip（151.751秒）。変更前Chromeの写像復元FAILを確認。
最終out/browser-curved-domain-final-20260908は35項目PASS（追加5/既存30）、外部要求0。
条件表示と履歴保持を画像確認し、境界証拠を含む保存内容も照合。
再投影例out/curved-gui-reprojected-20260908は元楕円体の弦許容値を1/4にして独立solve/save。
156三角形。生成条件・実行再現・初回FAIL出力はGUI_ACCEPTANCE.mdに記録。
今回専用GUI2件は起動引数の完全一致で特定して停止済み。
曲線変形/再近似間の一般写像、対応推定、個別枝回復・tune等は残る。
新規外部資料・依存・legacy参照なし。親課題は8受入・3進行中・21未受入・X01候補を維持。

最終531件中529合格・2 skip（153.144秒）。out/validation-d01-curved-domain-gui-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001248e-16。
out/d01-curved-domain-gui-20260908の独立球形/楕円体・体積・相似則もPASS。
標準・独立・Chrome検証のsource_sha256は最終ソースと一致。FEM・基準・許容差変更なし。

## D01同一二次曲線領域の再メッシュ比較 — 2026-09-08

直前基準03c010d。curved_same_domainを追加。同じnative曲線宣言・パラメータ付けの下で、
共通区間の二次Bézier係数を照合する。係数差の最大ノルムが辺全体の位置差を抑える
Bernstein凸包性を利用し、座標尺度×512εの浮動小数点丸め幅を診断へ保存。
端点一致だけでは受理しない。固定曲線細分を受理し、解析曲線への再投影で異なる境界は拒否。
既存QuadraticEdge・固定曲線細分・曲線場評価を再利用。新規外部資料・依存・legacy参照なし。

双方の曲線要素積分点で物理Hphiを比較し、半分ずつの正体積測度を使う。
Case/保存API・CLIへ接続。境界を保つ任意の接続に依存しない実装で、受入例は一様4分割。
GUI、曲線変形/再近似領域の一般写像・対応推定・個別枝回復・tuneは残る。

着手前525件中523合格・2 skip（150.396秒）。未実装import失敗後、追加6件PASS（1.919秒）。
同じ場の延長で重なり1、境界細分一致、端点のみ一致する不正辺と再投影差の拒否、
往復対応/保存再検証、物理/controls拒否を確認。
初回の再投影拒否fixtureはCaseの輪郭キャッシュをclearする設定へ修正。

out/d01-curved-same-domain-final-20260908で球形102対408、楕円体90対360三角形を比較。
球形解析周波数相対差最大2.8989987247873827e-5、相似則f/RQ/G最大3.197442310920451e-14。
次数3/5の重なり差最大2.070565485734477e-8、固定領域体積差最大2.220446049250313e-16。
解析体積との差は最大7.384108983687909e-5で、幾何近似誤差として区別する。
共通区間係数距離最大1.2412670766236366e-16 m。独立検証と保存/再検証CLI PASS。
最初の独立検証後に端点のみ一致の追加テストを加え、最終ソースで独立検証を再実行した。
楕円体は合成幾何。物理RF収束の受入ではない。親課題区分は8受入・3進行中・21未受入・X01候補。

最終531件中529合格・2 skip（152.530秒）。out/validation-d01-curved-same-domain-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001248e-16。
標準・独立検証のsource_sha256は最終ソースと一致。FEM・基準・許容差変更なし。
D01全体の受入ではなく、GUI・曲線変形/再近似・対応推定などの残件を維持する。

## D01区分アフィン再メッシュのGUI接続 — 2026-09-08

直前基準8870204。比較写像・完全な比較メッシュ2件のJSON入力/復元・旧新交換を追加。
交換は入力だけを更新し、比較時に完全被覆/境界/向きを検査する。不正な配列は部分更新しない。
逆方向へ未交換のまま継続すると拒否し、確認済み履歴を保持。他写像では宣言を送らない。
数値追跡核・FEMは変更なし。

着手前525件中523合格・2 skip（149.054秒）。変更前Chromeの写像復元FAILを確認。
初回Chromeは新ファイル名を探す保存検査でFAIL。実ファイルは同名で上書きされ、
piecewise_remeshの2段階履歴を保持していた。検査だけを内容照合へ修正。
最終out/browser-piecewise-recheck-20260908は30項目PASS（追加7/既存23）、外部要求0。
入力/交換画面を画像確認。失敗出力は保持しGUI_ACCEPTANCE.mdへ記録。

最初の標準回帰out/validation-d01-piecewise-gui-20260908は525件中523合格・2 skip
（150.207秒）でPASS。検査スクリプト修正後の最終ソースと検証証拠を揃えるため再実行した。
out/d01-piecewise-gui-recheck-20260908で独立profile/折返し変形の体積/相似則もPASS。
初期円筒Bessel相対差最大1.4076898846582253e-7、相似則f/RQ/G最大1.9539925233402755e-14。
今回専用GUI3件は起動引数の完全一致で特定して停止済み。
曲線領域、対応推定、個別枝回復・tune等は残る。物理収束の受入ではない。
新規外部資料・依存・legacy参照なし。親課題の8受入・3進行中・21未受入・X01候補を維持。

最終525件中523合格・2 skip（149.589秒）。out/validation-d01-piecewise-gui-recheck-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001248e-16。
標準・独立・Chrome検証のsource_sha256は最終ソースと一致。FEM・基準・許容差変更なし。

## D01明示比較メッシュによる区分アフィン変形 — 2026-09-08

直前基準a24c12e。piecewise_remeshとcomparison_meshesを追加。
対応する旧/新比較メッシュの同じ三角形重心座標で実保存場を直接評価する。
FEMの接続と比較メッシュの接続は独立。双方の比較メッシュを既存mesh validatorで
Case全領域の連結円板/正三角形/完全境界として検証し、実FEMの境界とも照合する。
可変sqrt(r*detJ)を保持した共通測度で部分空間を比較。比較meshの接続/番号は明示一致。
API・保存/履歴CLIとStudy controls JSONへ接続。GUI入力・二次曲線領域・対応推定は残る。

着手前520件中518合格・2 skip（149.324秒）。未実装import失敗後、追加5件PASS（0.307秒）。
可変体積因子の重なりは独立二重積分と小数8桁で一致。反転・欠損・境界不一致拒否、
入れ子schema・独立FEM接続・保存/往復履歴も確認。
初回の比較meshテストはCaseのnr最小値、次は同一直線上の許される境界頂点移動を
不正としていたfixtureを修正。FEMや許容差は変更していない。

out/d01-piecewise-remesh-20260908 PASS。比較/旧FEM/新FEM三角形数はprofile8/240/468、
折返し44/74/167。次数6/10の重なり差最大9.076858813461541e-7、
相似則f/RQ/G相対差最大1.9539925233402755e-14、体積差最大5.551115123125783e-16。
初期円筒Bessel相対差最大1.4076898846582253e-7。保存・再検証CLIもPASS。
形状変化後の厳密固有周波数や物理RF収束はこの受入に含めない。折返しは合成幾何。
新規外部資料・依存・legacy参照なし。親課題は8受入・3進行中・21未受入・X01候補を維持。

最終525件中523合格・2 skip（152.241秒）。out/validation-d01-piecewise-remesh-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001248e-16。
標準・独立検証のsource_sha256は最終ソースと一致。FEM・基準・許容差変更なし。
残件はGUI入力、曲線領域、対応推定、個別枝回復・tune等。D01全体の受入ではない。

## D01アフィン再メッシュのGUI接続 — 2026-09-08

直前基準a9f7324。アフィン写像の選択・3係数入力/復元と明示逆変換を追加。
逆変換は入力だけを1/a、1/c、-b/(a*c)へ変え、不正時は部分更新しない。
比較結果の選択は利用者が行う。逆方向に元の係数を使うと拒否され、確認済み履歴を保持。
他写像を選ぶとアフィン係数を送らない。数値追跡核は変更なし。

着手前520件中518合格・2 skip（148.922秒）。変更前Chromeの写像復元FAILを確認。
最終out/browser-affine-final-20260908は23項目PASS（追加6/既存17）、外部要求0。
逆変換係数と操作説明を画像確認。初回FAIL出力を保持しGUI_ACCEPTANCE.mdへ記録。
out/d01-affine-gui-20260908で独立異方円筒/せん断三角形もPASS。
Bessel相対差最大1.412226489083679e-7、相似則f/RQ/G最大4.518607710224387e-14。
この限定受入は非アフィン写像や物理収束の受入ではない。
新規外部資料・依存・legacy参照なし。親課題は8受入・3進行中・21未受入・X01候補のまま。
残件は非アフィン再メッシュ写像、曲線領域対応、個別枝回復・tune等。

最終520件中518合格・2 skip（150.041秒）。out/validation-d01-affine-gui-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001248e-16。
標準・独立・Chrome検証のsource_sha256は最終ソースと一致。FEM・基準・許容差変更なし。
検証専用GUI2件は起動引数の完全一致で特定して停止済み。

## D01明示アフィン変形の独立再メッシュ比較 — 2026-09-08

直前基準9635929。affine_remeshと厳密affine_map controlsを追加。
旧から新へのr'=a r、z'=b r+c zを明示し、a,c>0。軸/原点を保持する。
新メッシュを逆変換し、旧領域との境界全辺/タグ一致を確認する。P1/P2場の接続を
保持して評価し、Hphi_new/aと一定体積比a²cは正規化で相殺。FEMを変更しない。
API・保存/履歴CLIへ接続。GUI入力、曲線二次幾何、非アフィン一般写像は残る。

着手前514件中512合格・2 skip（149.167秒）。未実装import失敗後、独立多項式P1/P2・
逆変換/恒等一致・不正map/境界拒否・保存/履歴の追加6件PASS（0.269秒）。
計算直後と保存後でメッシュ保持形式が異なることによる初回保存テスト失敗を修正。

out/d01-affine-remesh-verified-20260908 PASS。異方倍率円筒240対442、せん断三角形32対64。
円筒Bessel相対差最大1.412226489083679e-7、体積差最大6.661338147750939e-16。
全長2倍の相似則f/RQ/G相対差最大4.518607710224387e-14、
次数3/5の重なり差最大1.0408429140795761e-7。保存・再検証CLIもPASS。
旧same_domainの円筒/折返し保存文書2件も再検証PASS。
三角形は合成幾何。せん断後の厳密固有周波数や物理RF収束はこの受入に含めない。

初回out/d01-affine-remesh-20260908は検証スクリプトの境界タグキー名、
次のout/d01-affine-remesh-final-20260908はNumPy真偽値のJSON化で停止。
正規のedge_tagsとPython boolへ修正し、新出力先で再実行。失敗出力は保持。
新規外部資料・依存・legacy参照なし。親課題は8受入・3進行中・21未受入・X01候補のまま。

最終520件中518合格・2 skip（150.011秒）。out/validation-d01-affine-remesh-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001248e-16。
標準・独立検証のsource_sha256は最終ソースと一致。FEM・基準・許容差は変更なし。
残件はGUI入力、非アフィン再メッシュ写像、曲線領域対応、個別枝回復・tune等。

## D01同一領域再メッシュのGUI接続 — 2026-09-08

直前基準aac49fc。same_domainの写像選択・保存設定復元をGUIへ追加。
直線境界全体の一致、標本次数確認とRF収束の区別を選択時に表示する。
頂点対応を要求せず、折返し形状の独立メッシュを比較してID履歴を継続する。
異なる領域への継続は拒否し、最後の確認済み履歴を保持する。数値核は変更なし。

着手前514件中512合格・2 skip（150.833秒）。変更前Chromeで写像復元FAILを確認。
最終out/browser-same-domain-final-20260908は17項目PASS（追加4/既存13）、外部要求0。
写像・適用条件・履歴保持を画像確認した。初回FAILを保持しGUI_ACCEPTANCE.mdへ記録。
out/d01-same-domain-gui-20260908で独立円筒/折返し再メッシュ検証もPASS。
Bessel相対差最大5.015392986473799e-6、相似則f/RQ/G最大3.042011087472929e-14。
この検査は物理収束受入ではなく、粗い折返し例のRF差は前回記録のとおり残る。

形状変化と再メッシュを伴う一般写像、二次曲線領域の対応、個別枝回復・tune等は残る。
新規外部資料・依存・legacy参照なし。親課題の8受入・3進行中・21未受入・X01候補を維持。

最終514件中512合格・2 skip（149.452秒）。out/validation-d01-same-domain-gui-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001248e-16。
標準・独立・Chrome検証のsource_sha256は最終ソースと一致。FEM・許容差・基準変更なし。
今回専用GUI2件は起動引数の完全一致で特定して停止済み。

## D01同一領域の独立再メッシュ比較 — 2026-09-08

直前基準e0c465b。same_domain写像を追加。双方の物理境界全辺の被覆とPEC/axisタグを
双方向に検査し、辺細分を許して異なる頂点数・接続のHphiを共通物理座標で比較する。
両メッシュの正の体積積分点を半分ずつ使う対称測度。P1/P2と折返し多角形に対応。
メッシュ交差上の厳密積分ではなく、形状変形や二次曲線幾何の一般写像も未実装。
API・2時点/履歴CLIへ接続。GUIの写像選択は後続。標本対応を物理収束へ読み替えない。

着手前508件中506合格・2 skip（148.482秒）。未実装APIのimport失敗を確認後、
独立多項式場の重なり1・円筒体積・P1/P2双方向一致・境界/タグ/曲線/上限拒否・
保存/履歴再検証の追加6件PASS。初回テストのCase保持と上限設定の誤りを修正。

独立検証out/d01-same-domain-final-20260908 PASS。円筒240対442、折返し44対76三角形。
円筒Bessel相対差最大5.015392986473799e-6、体積相対差最大5.551115123125783e-16。
Maxwell相似則f/RQ/Gの相対差最大3.042011087472929e-14、
次数3/5の重なり差最大5.191530004777789e-7。保存/再検証CLIもPASS。
初回out/d01-same-domain-20260908は検証スクリプトの存在しないContour.from_dict呼出しで停止。
多角形の一次モーメント式による独立体積計算へ修正し、新出力先で再実行。初回出力は保持。

メッシュ間差もremesh_differences.jsonへ保存。円筒2モードの最大相対差f/RQ/Gは
3.6281e-6/2.6531e-4/1.8258e-5。粗い折返し例は0.006614/0.02811/0.01022で、
対応は確認できても物理収束の受入ではない。許容差やFEMを変更していない。
新規外部資料・依存・legacy参照なし。親課題の8受入・3進行中・21未受入・X01候補を維持。

最終514件中512合格・2 skip（150.555秒）。out/validation-d01-same-domain-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001248e-16。
標準・独立検証のsource_sha256は最終ソースと一致。既存FEM・基準・許容差変更なし。
残件はGUI写像選択、形状変化を伴う再メッシュ写像、曲線領域の対応、個別枝回復・tune等。

## D01多対多集合継承のGUI方式選択 — 2026-09-08

直前基準6f011b7。集合継承の有効チェックと方式選択を分け、従来合流/分裂を既定、
多対多を含む方式を明示選択にした。保存文書を開いた際の新policy復元漏れを修正。
無効時はpolicy/linkを送らず、履歴継続へ選択方式を反映する。数値追跡核は変更なし。

着手前508件中506合格・2 skip（148.844秒）。変更前Chromeで新policy復元FAILを確認。
最終Chrome13項目PASS、外部要求0（out/browser-connected-policy-final-20260908）。
既存8項目と追加5項目。画面の方式と個別ID未確定の説明も画像確認。
修正直後は検証ワークスペース再利用で取込件数条件に失敗し、空の専用環境で再実行。
初回FAIL2件の場所・原因・再現条件はGUI_ACCEPTANCE.md。検証専用GUI2件は停止済み。

最終508件中506合格・2 skip（149.150秒）。
`out/validation-d01-connected-policy-gui-20260908` PASS。seed周波数差ゼロ、
RF/エネルギー相対差最大8.881784197001248e-16。FEM・基準・許容差変更なし。
`out/d01-connected-policy-gui-20260908` で独立Bessel周波数/保存再検証もPASS。
5周波数の解析相対差最大2.5527978976036536e-5。意図的な初期不確定集合を持つ
自己比較であり、実形状掃引による集合発生/個別枝回復の証拠ではない。
標準・独立・ブラウザーのsource_sha256は最終ソースと一致。
新規外部資料・依存・legacy参照なし。次は一般再メッシュの比較写像など一般追跡の残件。
個別枝回復・tune・非幾何/非単調適応掃引・電源断回復保証も残る。
親課題は8受入、C00/G03/D01の3進行中、21未受入、X01候補のまま。

## D01多対多の保守的ID集合継承 — 2026-09-08

直前基準7eedad8。retain_connected_subspaceを明示した場合のみ、複数クラスタ間の
リンク連結和を候補とする。両側に多次元クラスタが必要で、合計次元・全ランク・
最悪主角・競合余裕を再検査する。REPARTITIONは集合対応だけを意味し個別IDはnull。
既存retain_subspaceの条件と再検証結果は維持。一般枝回復の代用にはしない。

着手前502件中500合格・2 skip（148.092秒）。新policy未実装の6件失敗を確認後、
重み付き直交空間の分割変更、回転/符号/倍率不変、非連続順位、曖昧混合・方向喪失・
ランク不足・次元不一致の拒否、実保存/履歴再検証の追加6件PASS。既存6件もPASS。
最終508件中506合格・2 skip（148.921秒）。
`out/validation-d01-cluster-repartition-20260908` PASS。seed周波数差ゼロ、
RF/エネルギー相対差最大8.881784197001248e-16。FEM・基準・許容差変更なし。

`out/d01-cluster-repartition-20260908` は解析TM020/TM012縮退のP2円筒を計算し、
5周波数の解析相対差最大2.5527978976036536e-5。標本次数12/18で集合継承と
保存/履歴再検証PASS。同じ保存場に意図的な不確定初期集合を与える検査であり、
その集合を生んだ実形状掃引の証拠ではない。2時点/履歴CLI再検証もPASS。
過去out/d01-cluster-transitions-20260908の旧policy履歴4件も再検証PASS。
標準・独立検証のsource_sha256は最終実装と一致。新規外部資料・依存・legacy参照なし。

API/CLIとStudyのcontrols JSONで指定できる。個別比較GUIの新policy選択操作は残る。
多対多の個別枝回復、接続変更を伴う一般再メッシュ、tune、非幾何/非単調適応掃引、
電源断回復保証も未完。親課題は8受入、C00/G03/D01の3進行中、21未受入、X01候補を維持。
今回の集合継承をD01全体の受入へ数えない。

## D01適応二分のGUI接続 — 2026-09-08

直前基準f812d2c。共通追跡GUIへ適応制限入力・request作成、Job開始/中止/結果、
元JSON保存/再検証/再開を接続した。通常追跡と適応実行は別API・保存形式として検証する。
開始はJSON内のadaptive指定、再開は検証済み文書の方式/ID/閾値/上限を使う。
入力欄とチェックボックスの変更で再開条件を差し替えない。

計算済み/採用点数・比較回数・元目標の到達数を区別し、元目標/追加点と採用順を表示。
全比較のPASS/UNVERIFIEDと採用/二分/停止、追加中点、待ち列、未到達目標、停止理由を表示する。
COMPLETE後も粗い失敗比較を保持。適応Jobを個別結果選択欄に混ぜない。

着手前499件中497合格・2 skip（145.928秒）。未実装GUI操作の追加3件失敗を確認後、
開始/結果/保存再検証/再開、厳密入力/誤ったJob・文書種別、判断改変/上限停止がPASS。
通常追跡GUI3件と併せ6件PASS（5.497秒）。最終502件中500合格・2 skip（149.378秒）。
`out/validation-d01-adaptive-gui-20260908` PASS。seed周波数差ゼロ、
RF/エネルギー相対差最大8.881784197001248e-16。FEM・基準・許容差変更なし。

実Chromeは`out/browser-adaptive-execution-recheck-20260908`で適応10項目PASS、
`out/browser-adaptive-normal-regression-20260908`で通常追跡11項目PASS、
`out/browser-adaptive-pair-regression-20260908`で既存比較/履歴8項目PASS。外部要求はいずれも0。
adaptive-complete.pngで採用順[0,2,1]と失敗比較の保持を画像確認した。
初回`out/browser-adaptive-execution-20260908`は保存クリック後にダウンロードを観測できずFAIL。
スクロールを即時化し、描画後の実ヒット対象を確認するよう検証スクリプトを変更して全項目再実行。
初回FAILも保存し、製品側の保存形式や判定閾値は変更していない。検証用GUIは停止済み。

`out/d01-adaptive-gui-final-20260908`で実ワーカーの途中再開/相似則/上限停止を再検証。
P2/12×20基本モードで全寸法2倍の判断は同じBISECT→ACCEPT→ACCEPT、
Maxwell相似則の最大相対差f 9.104e-15、R/Q 4.174e-14、G 1.221e-14。
標準/独立/3ブラウザー記録のsource hashは最終コードと一致。Wine・hosted CIは今回未実行。
新規外部資料・依存・legacy参照なし。

非幾何/非単調掃引、一般再メッシュ写像、多対多/個別枝回復・tune・電源断回復保証は残る。
中止/失敗Jobの途中文書の一覧自動選択も未実装。標本対応を連続枝/物理収束の保証にしない。
親課題区分は8受入・3進行中・21未受入・拡張候補1のまま。計画全体は継続する。

## D01適応二分のJobManager接続 — 2026-09-08

直前基準9245529。JobManager.start_adaptive_studyとadaptive_study_jobs.pyを追加。
共通の適応FEM/保存場追跡APIを別プロセスで実行し、status/cancel/list/closeへ接続。
入力・制限値・再開文書を事前検査し、二分待ちのPAUSEDから新しいJobへ再開する。

Job種別adaptive_study、request/結果/manifestをルートへ、点とチェックポイントをexecution/へ保存。
計算済み点数・採用点数・比較回数・未到達目標を区別する。Job completeと追跡状態を分け、
numerical_validation=not_checkedを保持。verify=Trueは前のJobの保存場、失敗比較、
二分判断も再検証し、要約の改変を拒否する。中止・異常終了で成功を公開しない。

着手前494件中492合格・2 skip（143.847秒）。未実装メソッドによる追加5件の失敗を確認後、
実ワーカーの二分待ち再開/過去端点変更検出、上限停止、中止/再起動、事前検査/要約改変、
非対応写像での失敗処理がPASS。既存追跡Job5件と併せ10件PASS（5.430秒）。
最終499件中497合格・2 skip（146.928秒）。
`out/validation-d01-adaptive-jobs-20260908` PASS。seed周波数差ゼロ、
RF/エネルギー相対差最大8.881784197001248e-16。FEM・基準・許容差変更なし。

`python scripts/validate_adaptive_study_jobs.py --out out/d01-adaptive-jobs-20260908` PASS。
合成profile局所半径0.055→0.08 m、P2/12×20/基本モードを3つのJobで実行。
最初は粗い比較失敗を保存して二分待ち、次は中点のみ計算、最後は保存済み端点だけで完了。
元文書不変と最後のJobに点ディレクトリがないことを確認。全寸法2倍でも同じ判断となり、
Maxwell相似則の最大相対差f 9.104e-15、R/Q 4.174e-14、G 1.221e-14。
max_depth=0の別Jobは未到達[1]・計算済み2点/採用1点でUNVERIFIEDとして終了。
標準/独立検証のsource hashは最終コードと一致。検証用JobManagerはclose済み。
GUI・Wine・hosted CIは今回未実行。新規外部資料・依存・legacy参照なし。

適応GUIの開始/中止/結果/再開操作は次段階。非幾何/非単調掃引、一般再メッシュ写像、
多対多/個別枝回復・tune・電源断回復保証も残る。標本対応を連続枝/物理収束の保証にしない。
親課題区分は8受入・3進行中・21未受入・拡張候補1のまま。計画全体は継続する。

## D01適応二分の途中保存・再開 — 2026-09-08

直前基準8184770。適応実行の保存版2へPAUSED/can_resume/pending_targetsを追加し、
各比較後のcheckpoint-NNN.json保存とresume-adaptive-study CLIを接続。
max_new_attemptsは今回の新規比較上限。元requestの総比較回数/深さ/最小幅は維持する。
二分待ちの失敗比較と確認済みID履歴、全保存場を再検証して新出力先へ再開する。
過去点を再計算せず、過去文書も変更しない。COMPLETE/UNVERIFIEDからの再開は拒否。

版1の再検証意味を維持し、新規文書は版2。requestのschema_versionは1のまま。
再開時は保存場だけで過去判断と待ち列を復元し、元チェックポイントとの一致を確認する。
新たな計算が失敗しても、それ以前の有効なPAUSED文書から別出力先へ再開可能。
書込み途中の破損文書は再開対象とせず、電源断回復/実行中プロセス再接続は保証しない。

着手前489件中487合格・2 skip（141.634秒）。新テスト5件の未実装失敗を確認後、
二分待ち→中点→保存端点の再開、総上限維持、request/待ち列/過去ソース改変拒否、
中点計算失敗からの再開、版1互換/CLIを追加。既存6件と併せ11件PASS（5.051秒）。
中点再開は1点だけを計算し、最後の再開はFEM呼出しを禁止して保存端点だけで完了を確認。
最終494件中492合格・2 skip（144.445秒）。
`out/validation-d01-adaptive-resume-20260908` PASS。seed周波数差ゼロ、
RF/エネルギー相対差最大8.881784197001248e-16。FEM・基準・許容差変更なし。

`python scripts/validate_adaptive_study.py --out out/d01-adaptive-resume-20260908 --pause-and-resume` PASS。
合成profileの半径掃引0.055→0.08 m、P2/12×20/基本モードを比較1回ずつで一時停止・再開。
粗い未確認比較を保持し、中点だけを追加して、最後は既計算端点を使いCOMPLETE。
全寸法2倍でも判断はBISECT→ACCEPT→ACCEPT、相似則の最大相対差f 9.104e-15、
R/Q 4.174e-14、G 1.221e-14。円筒Bessel周波数差最大6.911e-8。元文書不変を確認。
標準/独立検証のsource hashは最終コードと一致。GUI・Wine・hosted CIは今回未実行。

`out/d01-adaptive-resume-legacy-20260908/checks.json`に、前回の実保存版1の5文書
（profile/相似拡大/円筒/複数目標完走/未到達停止）の再検証PASSを記録。
新規外部資料・依存・legacyソルバー参照なし。ここでの旧版は本実装の保存schema_version 1。

適応実行のJobManager/GUI、非幾何/非単調掃引、一般再メッシュ写像・多対多/個別枝回復・tuneが残る。
標本対応を連続枝/物理収束の保証にしない。親課題区分は8受入・3進行中・21未受入・拡張候補1のまま。
計画全体は継続する。

## D01幾何掃引の適応二分API/CLI — 2026-09-08

直前基準710cdd8。adaptive_study.pyとexecute-adaptive-study/replay-adaptive-studyを追加。
単調な幾何パラメータ掃引で対応が未確認となった区間を二分し、実FEMで中点を計算する。
元区間のcontrolsを維持し、確認済みの点だけをID履歴へ追加する。失敗した比較も保持。
既計算の端点は再利用し、同じ値を再計算しない。深さ/比較回数/最小幅/浮動小数点分解能で停止。
停止時は未到達の元目標を明示し、後続目標を飛ばさない。

再読込は保存場だけで決定的な二分手順を再実行し、追加点の順序、全比較/採否/停止理由、
入力とsource hash、確認済みID履歴を照合する。実行中の先行点変更も拒否する。
対象は/case/geometry/の数値sweep。未対応写像・入力不正・計算失敗を細分で隠さない。
適応実行の途中再開・JobManager/GUI接続は次段階。通常の指定点列の実行/再開は変更なし。

着手前483件中481合格・2 skip（136.952秒）。まず既存FEM保存場で粗い比較が0.968252で
閾値0.99に届かず、二分すると0.991139/0.992832となる独立した失敗条件を確認。
未実装APIのテスト読込失敗後、粗い失敗保持/端点再利用、各上限、減少掃引/事前検査、
判断/ソース改変、計算中の先行点変更、CLIの6テストPASS（2.343秒）。
最終489件中487合格・2 skip（140.335秒）。
`out/validation-d01-adaptive-study-20260908` PASS。seed周波数差ゼロ、
RF/エネルギー相対差最大8.881784197001248e-16。FEM・基準・許容差変更なし。

`python scripts/validate_adaptive_study.py --out out/d01-adaptive-study-20260908` PASS。
合成profileの局所半径0.055→0.08 m、P2/12×20/基本モードで粗い重なり0.968190が未確認、
中点0.0675 mにより0.991113/0.992825で確認。BISECT→ACCEPT→ACCEPTと失敗証拠を保持。
全寸法2倍でも二分判断が一致し、Maxwell相似則の最大相対差はf 9.104e-15、
R/Q 4.174e-14、G 1.221e-14。円筒では不要な追加なし、Bessel周波数差最大6.911e-8。
標準/独立検証のsource hashは最終コードと一致。GUI・Wine・hosted CIは今回未実行。

`out/d01-adaptive-multiple-targets-20260908`には元目標0.055/0.08/0.085 mの追加実行を保存。
全3目標への到達と再検証がPASS。max_depth=0では未到達[1,2]となり、0.085 mを計算しない。
request.jsonとstopped-request.jsonをexecute-adaptive-studyへ新しい出力先で渡して再現できる。

新規外部資料・依存・legacy参照なし。COMPLETEは標本対応であり、区間内の未観測交差・
縮退の不存在や連続枝、物理収束を保証しない。適応再開/JobManager/GUI、非幾何/非単調掃引、
一般再メッシュ写像・多対多/個別枝回復・tuneが残る。
親課題区分は8受入・3進行中・21未受入・拡張候補1のまま。計画全体は継続する。

## D01追跡付きStudyのブラウザー操作 — 2026-09-08

直前基準2c23365。共通JobManagerへ開始/結果/再開/保存再検証のGUI APIを接続。
通常Study欄と追跡設定からrequestを作成し、JSONを確認して開始できる。
計算一覧で中止・結果表示、点数上限、初点だけのPAUSED、部分空間の個別ID未確定、
未確認後のNOT_COMPUTEDを表示する。追跡Jobを個別結果の比較欄へ混ぜない。
再開は検証済みの元JSON文字列を用い、編集欄からID・閾値を差し替えない。
COMPLETE/UNVERIFIEDでは再開を無効にし、最後に検証した結果を保持する。

変更前480件中478合格・2 skip（135.155秒）。未実装GUI APIのテスト読込失敗を確認後、
開始/結果/文字列再検証/再開、厳密入力と改変、未確認/個別Job拒否の3テストPASS（2.354秒）。
最終483件中481合格・2 skip（139.217秒）。
`out/validation-tracked-execution-gui-final-20260908` PASS。seed周波数差ゼロ、
RF/エネルギー相対差最大8.881784197001248e-16。FEM・基準・許容差変更なし。

`out/d01-tracked-gui-final-20260908`で実ワーカーの解析円筒縮退と集合再開を再検証。
解析周波数差最大5.613031772924436e-6、未確認後の3点目未計算を確認。
最終実Chromeは`out/browser-tracked-execution-final-20260908`の11操作、
既存比較/履歴は`out/browser-tracked-execution-final-pair-20260908`の8操作がPASS。
両方とも外部要求0。tracked-execution.pngで入力欄と点状態表を画像確認した。
標準/独立/両ブラウザーのsource hashは最終コードと一致。検証用GUIは停止済み。

初回`out/browser-tracked-execution-20260908`はファイル読込完了前に検証スクリプトが
入力欄を参照してFAIL。復元された値を待つよう修正し、recheck記録で10操作PASS。
その画像で新規JSON入力欄が狭いことを検出し、既存textareaスタイルを適用。
最終は入力幅も含め11操作と標準validateを再実行した。初回FAILと表示修正前の記録も保持する。

新規外部資料・依存・legacy参照なし。Wine・hosted CIは今回未実行。
中止/失敗Jobの途中文書は保存ファイルを再検証して開けるが、一覧からの自動選択は未実装。
適応的点追加、tune、多対多/個別枝回復、接続変更を伴う再メッシュ写像、電源断回復保証は残る。
親課題区分は8受入・3進行中・21未受入・拡張候補1のまま。計画全体は継続する。

## D01追跡付きStudyのJobManager接続 — 2026-09-08

直前基準7dd3431。JobManager.start_tracked_studyとtracked_study_jobs.pyを追加。
既存逐次FEM/追跡APIを別プロセスで実行し、共通status/cancel/list/closeへ接続する。
全点/controlsと再開証拠を出力確保前に検査する。request・結果・点出力をmanifestへ保存。
verify=Trueでは継承した過去Jobの点と保存履歴も検証し、要約の追跡状態/点数/再開可否を照合。

Jobのcompleteは処理/保存完了。追跡はPAUSED/COMPLETE/UNVERIFIEDを別記し、
numerical_validation=not_checkedを保持する。中止・ワーカー失敗は成功にしない。
アプリ再起動時のinterruptedでJob種別が失われる既存処理も修正した。
ブラウザー専用操作はまだ未接続。共通JobManager APIの受入でありGUI完了とは扱わない。

着手前475件中473合格・2 skip（132.534秒）。未実装メソッドによる4テスト失敗を確認後、
実ワーカーでの一時停止/再開/過去点再計算禁止と過去Job変更検出、未確認後の未計算、
中止/再起動、入力事前検査、要約改変と実ワーカー失敗の5テストがPASS（2.593秒）。
最終480件中478合格・2 skip（134.746秒）。
`out/validation-d01-tracked-study-jobs-20260908` PASS。seed周波数差ゼロ、
RF/エネルギー相対差最大8.881784197001248e-16。FEM・基準・許容差変更なし。

`python scripts/validate_tracked_study_jobs.py --out out/d01-tracked-study-jobs-20260908` PASS。
半径0.1 m、長さ0.055→Bessel解析縮退位置→0.075 m、P2/12×12/3モードの実ワーカー。
2点目の縮退ID集合をPAUSEDとして保存し、別Jobで個別IDを恣意的に回復せず集合継承して完走。
解析周波数差最大5.613031772924436e-6。集合継続なしの別Jobは2点目でUNVERIFIEDとし、
3点目を計算しない。元チェックポイント不変・過去点再計算なしを確認。
標準/独立検証のsource hash一致、実行中コード変更なし。検証用JobManagerはclose済み。
GUI・Wine・hosted CIは今回未実行。新規外部資料・依存・legacy参照なし。

次はブラウザーの開始/中止/結果/再開操作。適応的点追加、tune、多対多/個別枝回復、
接続変更を伴う再メッシュ写像、電源断回復保証は残る。
親課題区分は8受入・3進行中・21未受入・拡張候補1のまま。計画全体は継続する。

## D01追跡付きStudyの逐次実行・停止・再開 — 2026-09-08

直前基準dc23102。tracked_study.pyとexecute-tracked-study/resume-tracked-study/
replay-tracked-study CLIを追加。各点を共通execute_projectで実FEM計算し、保存場を
追跡してから次の点へ進む。未確認の対応で停止し、後続点はNOT_COMPUTEDと記録。
通常Studyの全点後処理と異なり、未確認後の点を計算しないことを実行回数と出力で検証した。

点ごとの新規チェックポイントはPAUSED/COMPLETE/UNVERIFIEDを区別する。
PAUSEDからは全入力・保存場・Job hash・履歴を再検証して新出力先へ再開できる。
過去の点は再計算せず、元の絶対パスと証拠を保持する。request/閾値/IDの変更と
次点の計算中の先行ソース変更を拒否する。後続計算失敗後にも直前証拠から再開可能。
既存出力の上書きなし。電源断/OS強制終了の回復保証は今回の受入範囲外。

変更前469件中467合格・2 skip（135.887秒）。API未実装でテスト読込失敗を確認後、
再開/過去点再計算禁止、未確認後の未計算、計算失敗からの再開、厳密入力/改変、
計算中の先行ソース変更、CLIの6テストを追加。6件PASS（1.904秒）。
最終475件中473合格・2 skip（134.880秒）。
`out/validation-d01-tracked-study-execution-20260908` PASS。seed周波数差ゼロ、
RF/エネルギー相対差最大8.881784197001248e-16。FEM・基準・閾値の変更なし。

`python scripts/validate_tracked_study.py --out out/d01-tracked-study-execution-20260908` PASS。
半径0.1 m、長さ0.055→Bessel零点による解析縮退位置→0.075 m、P2/12×12/3モード。
初点で一時停止し、別出力先で合流/分裂をID集合として継承して完走。
独立解析周波数との差最大5.613031772924436e-6。集合継続を無効にすると2点目で
UNVERIFIEDとなり3点目のディレクトリを作らない。両証拠の再検証と初点文書不変を確認。
標準/独立検証のsource hashは最終コードと一致。GUI・Wine・hosted CIは今回未実行。

新規外部資料・依存・legacy参照なし。COMPLETEは全指定点の計算と標本対応の確認であり、
物理収束や連続枝保証ではない。GUI JobManagerへの組込、適応的点追加、tune、
多対多/個別枝回復、接続変更を伴う再メッシュ写像は残る。親課題区分は
8受入・3進行中・21未受入・拡張候補1のまま。計画全体は継続する。

## D01完了Studyの追跡GUI — 2026-09-08

直前基準406e636。完了Studyの選択、共通/段階別controls、全点の追跡状態と個別ID、
保存・再読込を既存study_mode_tracking APIへ接続。未確認後の点を未追跡として表示し、
Study文書を一般履歴として延長する操作を禁止する。再読込は元JSON文字列を保持する。
元Studyのスペクトル・収束判定は変更しない。新規外部資料・依存・legacy参照なし。

変更前466件中464合格・2 skip（129.603秒）。追加GUI接続3テストは実装前に失敗し、
接続後は既存5件と併せ8件PASS。最終標準469件中467合格・2 skip（130.237秒）。
`out/validation-d01-gui-study-20260908` PASS。seed周波数差ゼロ、RF/エネルギー差最大
8.881784197001248e-16。FEM変更なし、閾値緩和なし。

`out/d01-gui-study-20260908`の独立3点P2 Studyで解析縮退位置を通る集合継承と
未確認停止を再検証。Bessel解析周波数との差最大5.6130317729330415e-6。
元Study不変を確認。`out/browser-d01-gui-study-20260908`の実Chrome7操作と
`out/browser-d01-study-pair-regression-20260908`の既存比較/履歴8操作がPASS。
外部要求0。study-tracking.pngで未確認/未追跡表を視認。全4記録のsource hash一致。
Wine・hosted CIは未実行。

判断: 完了済みStudyを追跡する後処理を提供する。追跡付きStudyの自動実行/再開、
適応的点追加、tune、多対多/個別枝回復、接続変更を伴う再メッシュ写像は残る。
33親課題の区分は8受入・3進行中・21未受入・拡張候補1のまま。計画全体は継続する。

## D01完了Studyの保存場を順序追跡 — 2026-09-08

直前基準1f68d45。study_mode_tracking.pyとtrack-study-modes/replay-study-mode-tracking CLIを追加。
完了Studyと各点のmanifest、Study宣言/値/順序、生成Project、各点のcase hash/モード要約を照合する。
隣接点ごとのstep_controlsを明示し、全段階の項目・範囲を先に検査する。
保存場から履歴を作り、最初のUNVERIFIEDで停止。後続点をNOT_VISITEDとして明示保存する。
元Studyの独立スペクトル・mode_tracking記述・numerical_statusは書き換えない。
Study/子Jobのhashと履歴を別文書へ保存し、全体再検証で入力変更・文書改変を拒否する。

着手前460件中458合格・2 skip（131.309秒）。新API未実装で失敗を確認後、6検査を追加。
実Study交差/保存再検証、未確認停止と未使用controls検査、失敗点、manifestを更新した順序改変、
途中変更/文書改変、CLIと厳密requestがPASS。既存2時点保存6検査もPASS。
最終466件中464合格・2 skip（129.715秒）、`out/validation-d01-study-tracking-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
同ディレクトリseed_comparison.jsonに内訳。FEM・基準値・許容差の変更なし。

`python scripts/validate_study_tracking.py --out out/d01-study-tracking-20260908` PASS。
半径0.1 m、長さ0.055→解析縮退位置→0.075 m、P2/12×12/3モードの実Studyを実行。
独立解析周波数相対誤差は最大5.6130317729330415e-6。3点すべてを追跡し、
最終TM010は個別、TM011/TM020は集合を保持する。集合継続を無効にした別requestでは
最初の未確認で停止し、点2を未追跡と記録。両文書の再読込と元Study不変を確認。
同requestから `out/d01-study-tracking-cli-20260908.json` をCLI新規保存/再検証PASS。
stopped-study-tracking.jsonのCLI再検証はUNVERIFIEDを維持。
標準/独立Study検証のsource hashは最終コードと一致。GUI・Wine・hosted CIは今回未実行。

判断: 保存Studyとの対応根拠を明示し、失敗/未確認点を飛ばした履歴や収束合格への読み替えを作らない。
新規外部資料・依存・legacy参照なし。追跡付きStudy自動実行/再開、専用GUI、適応的点追加、tune、
一般追跡の多対多/個別枝回復/再メッシュ写像が残る。親課題は8受入、C00/G03/D01の3進行中、
他21未受入、X01拡張候補1で変わらず。全計画は未完了。[仕様と再現](MODE_TRACKING.md)。


## D01 GUI対応比較・追跡履歴 — 2026-09-08

直前基準abf856f。gui_mode_tracking.pyで完了個別Jobの選択と既存native追跡/再検証APIを接続。
GUIに写像・閾値・ID入力、個別/部分空間の対応表、未確認理由、履歴開始/継続、保存/再読込を追加。
履歴中は手入力IDを使わず基準結果を表示し、UNVERIFIED履歴の継続を無効化する。
サーバー生成の文書文字列をダウンロード・再送し、数値表記を保持する。
GUIの既存loopback/token/4 MiB上限と厳密入力を維持。FEM・追跡の数値条件は変更していない。

着手前455件中453合格・2 skip（128.376秒）。新接続API未実装で失敗を確認して接続4検査を追加。
初回Chromeは7操作後、minimum_overlap=1の未確認文書をJavaScriptで再JSON化して1.0→1となり、
履歴開始の厳密再検証で失敗。out/browser-d01-mode-tracking-20260908/report.jsonと初回検証出力を保持。
サーバー文書文字列をそのまま開始/継続へ渡す修正と回帰1検査を追加。検証条件を緩めていない。
ID欄の幅と、履歴中の基準結果表示も修正した。
最終460件中458合格・2 skip（128.587秒）、`out/validation-d01-gui-tracking-final-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
同ディレクトリseed_comparison.jsonに内訳。基準値・許容差の変更なし。

`out/d01-gui-tracking-final-sources-20260908` の実FEM縮退合流/分裂もPASS。
`out/browser-d01-mode-tracking-final-20260908/report.json` でChrome8操作PASS、外部要求0。
取込/結果選択、合流の部分空間表示、履歴ID編集禁止、分裂継続、ダウンロード一致、
ファイル再検証とcontrols復元、改変拒否、未確認履歴の保存可能/継続禁止を実操作で確認。
tracking-history.pngを視認し、部分空間未確定表示とボタン状態を確認。
標準・独立FEM・ブラウザーのsource hashは最終コードと一致。検証用GUI2プロセスは停止した。
今回ブラウザー例は円筒写像。profile/paired_meshのGUI選択は共通API接続であり、各写像の新しいブラウザー受入ではない。
Wine・hosted CIは今回未実行。

判断: GUI独自のID推測や数値再計算を作らず、保存場APIの確定/未確認状態を製品操作へ伝える。
新規外部資料・依存・legacy参照なし。多対多再構成、個別枝回復、接続の変わる再メッシュ写像、
適応的ステップとStudy/tune統合は残件。親課題は8受入、C00/G03/D01の3進行中、
他21未受入、X01拡張候補1で変わらず。全計画は未完了。[仕様](MODE_TRACKING.md)。


## D01合流/分裂をID集合として継続 — 2026-09-08

直前基準826c647。明示controls cluster_transition_policy=retain_subspace とminimum_cluster_linkを追加。
基底不変の部分空間投影量から二部グラフを作り、多対一/一対多・合計次元保存の場合だけ
集合候補を作る。再直交化後に既存の最悪主角・ランク・割当分離を全て再検査する。
単一モード同士の曖昧な回転、多対多、方向喪失をまとめて合格にしない。
分裂後もID集合を保持して個別周波数を拒否する。集合順位は非連続にも対応し、昇順/一意/全分割を維持。
元クラスタ・リンク行列・MERGE/SPLIT候補と判定を保存/履歴へ接続した。
既存policy未指定requestの計算結果・停止意味は維持する。

着手前449件中447合格・2 skip（128.470秒）。新controls未実装で追加6検査の失敗を確認した。
解析基底回転での合流、非連続分裂/継承、曖昧混合、方向喪失/ランク不足、厳密controls、
実FEM縮退の保存再開/改変拒否を追加してPASS。既存部分空間5検査もPASS。
最終455件中453合格・2 skip（128.737秒）、`out/validation-d01-cluster-transitions-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
同ディレクトリseed_comparison.jsonに内訳。FEM・基準値・許容差を変更していない。

`python scripts/validate_cluster_transitions.py --out out/d01-cluster-transitions-20260908` PASS。
R=0.1 m、L=0.055→0.06322753439669529→0.075 mをP2/12×12/3モードの実FEMで解いた。
中央LはBessel零点から独立に求めたTM020/TM011縮退位置。解析周波数相対誤差は最大5.6130317729330415e-6、
中央の数値周波数相対gapは1.0283783478115538e-6で、明示クラスタgap1e-3内。
標本次数12/18の両方でMERGE/SPLIT候補がPASS。最終最悪主角は0.9999999999890008 / 0.9999999999872012。
最終TM010だけ個別ID、TM011/TM020は集合として保持。個別枝を回復したとは扱わない。
同出力history-c-12.jsonをCLI再検証PASS。以前のout/d01-subspace-history-second-20260908.jsonもPASS。
標準/独立検証のsource hashは最終コードと一致。GUI・Wine・hosted CIは今回未実行。

判断: 次元保存と全方向の重なりが確認できた集合だけを継続し、個別IDを捏造しない。
公開された数値コード等は参照せず、射影の基底不変性と円筒分離解から独立実装。新規外部資料・依存・legacy参照なし。
多対多の再構成、分裂後の個別枝回復、接続が変わる再メッシュの写像、適応的ステップ、GUI/Study/tuneが残る。
親課題は8受入、C00/G03/D01の3進行中、他21未受入、X01拡張候補1で変わらず。
全計画は未完了。[仕様と再現](MODE_TRACKING.md)。


## D01明示メッシュ対応による折返し/曲線場の追跡 — 2026-09-08

直前基準3e0d6a3。`paired_mesh_tracking.track_paired_mesh_modes` と保存/履歴/CLIへ
mapping=paired_meshを追加。controls.vertex_pairsで全幾何頂点の0始まり全単射を必須指定する。
三角形接続と軸/PEC境界を保存する対応だけを受け付け、番号の一致から対応を推測しない。
三角形重心座標を局所頂点対応で並べ替え、直線/二次幾何とP1/P2係数から直接場を評価する。
体積要素2π r detJから、Hphiに正規化したsqrt(r detJ)を掛けて共通参照積分で比較する。
曲線を弦へ置換せず、実二次Jacobianを使用。次数2〜32、総標本262144以下。

着手前444件中442合格・2 skip（127.977秒）。新API未実装を確認後、5検査を追加。
初回FEM fixtureはgeometry_orderをsolverに置いたため厳密入力で失敗し、正しいmesh項目へ修正。
変動曲線Jacobianの独立積分、全単射/境界/接続/予算、折返し相似と番号置換、
native曲線相似、保存履歴がPASS。
最終449件中447合格・2 skip（128.227秒）、`out/validation-d01-paired-mesh-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
同ディレクトリseed_comparison.jsonに内訳。FEM・基準値・許容差を変更していない。

`python scripts/validate_paired_mesh_tracking.py --out out/d01-paired-mesh-20260908` PASS。
合成折返し/楕円曲線のP2 FEM、2倍相似、頂点逆順・要素逆順・局所巡回置換を明示対応で比較した。
相似則の相対差（f/RQ/G）は、折返し7.438494264988549e-15 / 1.4210854715202004e-14 / 9.2148511043888e-15、
楕円2.220446049250313e-16 / 3.375077994860476e-14 / 2.55351295663786e-15。
両形状とも次数3/5の最小主角重なりは丸め上1.0。同じID対応と保存後の履歴往復を確認。
同出力のfolded-requestから `out/d01-paired-mesh-cli-20260908.json` をCLI保存/再検証PASS。
ellipse-history.jsonもCLI再検証PASS。標準/独立検証のsource hashは最終コードと一致。
GUI・Wine・hosted CIは今回未実行。

判断: 一般輪郭で番号だけを一致とみなさず、明示的な位相対応と体積整合を契約にする。
変数変換から独立導出し、新規外部資料・依存・legacy参照なし。
接続が変わる再メッシュ間の写像、合流/分裂解決、適応的ステップ、GUI/Study/tuneが残る。
親課題は8受入、C00/G03/D01の3進行中、他21未受入、X01拡張候補1で変わらず。
全計画は未完了。[仕様と操作](MODE_TRACKING.md)。


## D01半径可変profileの体積整合写像 — 2026-09-08

直前基準fd1d4ed。`profile_mode_tracking.track_profile_modes` と保存/履歴/CLIへ
mapping=normalized_profileを追加。正の連続折れ線半径と両端PECだけに限定する。
r=rho R(L zeta), z=L zetaの体積要素2π L R² rhoから、標本をHphi*R/Rmaxとした。
定数2π L Rmax²だけを正規化で除き、変動する体積要素を保持する。
両形状の正規化節点の和集合で積分区間を分け、写像・倍率・点・重みを記録する。
総標本262144上限、未対応形状/対称端・参照節点の潰れ等を明示拒否。
従来normalized_cylinderの計算/保存意味は維持する。FEM自体の変更なし。

着手前438件中436合格・2 skip（127.238秒）。新API未実装を確認して追加6検査を実装。
初回2件はCaseを含まない生Solutionをテストから渡したため失敗し、契約どおり保存解を再読込して修正。
独立多項式体積積分、節点不変性、未対応入力、実FEM相似則/標本次数、保存履歴、円筒極限がPASS。
最終444件中442合格・2 skip（128.693秒）、`out/validation-d01-profile-tracking-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
同ディレクトリseed_comparison.jsonに内訳。基準値・許容差を変更していない。

`python scripts/validate_profile_tracking.py --out out/d01-profile-tracking-20260908` PASS。
合成profile、P2、12×20、3モードの2倍相似で、相対差はf:9.103828801926284e-15、
R/Q:4.007905118896815e-14、G:7.327471962526033e-15。
局所半径1%変更の最小主角重なりは次数8:0.9999457659745057、次数12:0.9999457604718266。
両方で同じID対応を得て、保存後の履歴再開もPASS。点間の連続物理枝の証明ではない。
同出力pair/historyをCLI再検証し、requestから `out/d01-profile-tracking-cli-20260908.json` を
CLI新規保存/再検証してPASS。標準/独立検証のsource hashは最終コードと一致。
GUI・Wine・hosted CIは今回未実行。

判断: 円筒の定数Jacobianを半径可変形状へそのまま流用せず、体積整合の明示写像を追加。
数式は変数変換から独立導出し、新規外部資料・依存・legacy参照なし。
折返し・曲線等の一般写像、合流/分裂解決、適応的ステップ、GUI/Study/tuneは残件。
親課題は8受入、C00/G03/D01の3進行中、他21未受入、X01拡張候補1で変わらず。
全計画は未完了。[仕様と再現](MODE_TRACKING.md)。


## D01部分空間ID集合の履歴継承 — 2026-09-08

直前基準14438fa。標本追跡にprevious_identity_groupsを追加し、現在順位集合とID集合を
個別基底への仮割当なしで次段階へ継承する。全順位の分割、ID一意性、次元、連続順位を厳密検査。
旧集合を保持して新周波数クラスタと比較し、閾値変更で旧集合を勝手に再分割しない。
合流/分裂は未確認。個別周波数の受渡しは多次元集合内で引き続き拒否する。
2時点request第2版はprevious_groupsを使用。履歴第2版はcurrent_identity_groupsと
individual_ids_completeを保存し、部分空間対応PASSなら集合として再開する。
第1版は元の停止意味を含め再検証互換。旧停止文書を自動でPASSへ変更しない。

着手前433件中431合格・2 skip（127.209秒）。未実装で新しい5テストの失敗を確認した。
3時点の独立直交基底回転/順位交差、分裂、厳密分割、native保存場履歴/改変拒否、旧停止互換を追加。
既存履歴2検査は第2版の集合継承契約に更新し、個別ID不確定を確認し続ける。
最終438件中436合格・2 skip（127.959秒）、`out/validation-d01-subspace-history-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
内訳は同ディレクトリseed_comparison.json。FEM・基準値・許容差の変更なし。

`out/d01-subspace-history-sources-20260908` の独立円筒交差PASS。
長さ0.055/0.075/0.08 m、半径0.1 m、P2、12×12、3モードの保存場で、
gap=.9を明示して3モードを一つの集合にまとめ、CLI履歴を作成/延長/再検証した。
`out/d01-subspace-history-first-20260908.json` とsecond版を新規保存、PASS。
最終ID集合はTM010/TM011/TM020、個別IDは全null、individual_ids_complete=false。
これは広い周波数集合の保存検証であり、実FEMの3モードが縮退しているという主張ではない。
前回保存の `out/d01-history-second-20260908.json` （第1版）もCLI再検証PASS。
標準/独立検証のsource hashは最終コード一致。GUI・Wine・hosted CIは今回未実行。

判断: 基底のラベルを捏造せず、集合の同一性を履歴へ渡す。一般写像、合流/分裂の追跡解決、
適応的ステップ制御、GUI/Study/tuneが残る。新規外部資料・依存・legacy参照なし。
親課題は8受入、C00/G03/D01の3進行中、他21未受入、X01拡張候補1で変わらず。
全計画は未完了。[仕様](MODE_TRACKING.md)。


## D01順序付き履歴・個別ID再開 — 2026-09-08

直前基準3d4401b。`mode_tracking_history.py` とstart/extend/replay-mode-history CLIを追加。
確認済みの2時点文書から開始し、全段階の元保存場を再検証して、隣接source/hashとID継承を確認する。
延長requestはcurrent_run/controlsだけを受け付け、以前のcurrent_mode_idsを自動継承する。
元履歴を変更せず、新規出力へ保存する。過去入力の変更や、単独では有効でも接続しない対応を拒否する。
UNVERIFIED段階も保存するが、その後の延長は停止する。部分空間対応がPASSでも個別ID不確定なら
履歴はUNVERIFIEDとし、基底への恣意的ID付与を避ける。全元入力と数値環境が再検証に必要。

着手前427件中425合格・2 skip（127.254秒）。新API未実装時の失敗を確認後、追加6件PASS。
実FEM3時点交差/保存再開、未確認保存/停止、部分空間停止、段階間不連続、過去入力変更、CLIを検証。
最終433件中431合格・2 skip（127.204秒）、`out/validation-d01-history-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
内訳は同ディレクトリseed_comparison.json。FEM・基準値・許容差を変更していない。

`out/d01-history-sources-20260908` の独立円筒交差PASS。
半径0.1 m、長さ0.055/0.075/0.08 m、P2、12×12、3モードの保存場を使用。
CLIで `out/d01-history-first-20260908.json` を作り、延長requestから
`out/d01-history-second-20260908.json` へ保存、再検証もPASS。
最後のIDはTM010/TM011/TM020で、交差後のIDを次段階へ継承した。
標準検証・独立交差のsource hashは最終コードと一致。GUI・Wine・hosted CIは今回未実行。

判断: 離散段階の履歴と再開を実装し、標本間の連続物理枝の証明とは区別する。
一般写像、部分空間ID集合の多段階継承、合流/分裂、適応的ステップ、GUI/Study/tuneは残件。
失敗からは最後の確認済み履歴を使って別出力へ分岐できるが、自動分岐管理は未実装。
新規外部資料・依存・legacy参照なし。親課題は8受入、C00/G03/D01の3進行中、
他21未受入、X01拡張候補1で変わらず、全計画は未完了。[仕様と操作](MODE_TRACKING.md)。


## D01の2時点対応保存・再検証CLI — 2026-09-08

直前基準a26280d。独立FEM場の対応核を `saved_mode_tracking.py` とCLIへ接続した。
厳密request版1、request所在からの相対入力解決、元保存場の主要ファイルと完了markerのSHA256、
比較前後の同一性検査、絶対入力パス、controls/重み/ID対応を保存する。
再読込は元native保存の整合性検査と場比較を再実行し、文書全体を照合する。固有値問題は再計算しない。
入力変更・対応改変を拒否し、UNVERIFIEDも理由付きで保存/再検証する。既存出力は上書きしない。
元入力のパスとバイト同一性が必要で、移動後の透過的再開・署名・連続履歴の保証ではない。

着手前421件中419合格・2 skip（125.977秒）。追加6件は実FEM交差の往復、改変、
比較中の変更、バイト同一性、UNVERIFIED、CLI/厳密requestを検証。
最終427件中425合格・2 skip（126.690秒）、
`out/validation-d01-saved-tracking-20260908` PASS。
seedの周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
比較内訳は同ディレクトリseed_comparison.json。基準値・許容差・FEMは変更していない。

`out/d01-saved-tracking-sources-20260908` の独立実FEM円筒交差PASS。
`out/d01-saved-tracking-request-20260908.json` からCLIで
`out/d01-saved-tracking-20260908.json` を新規保存し、再検証もPASS。
周波数順位の入替え後もTM010/TM011/TM020の対応を確認した。
両検証のsource hashは最終コードと一致。今回GUI・Wine・hosted CIは実行していない。

判断: 2時点の保存とCLIを先に具体化し、連続履歴や一般写像の完成とは区別する。
新規外部資料・依存・legacy参照なし。一般形状写像、クラスタ合流/分裂、
多段階履歴/安定ID再開、GUI/Study/tuneは残件。親課題の受入件数は8、
進行中C00/G03/D01が3、他21未受入、X01拡張候補1で変わらず、全計画は未完了。
詳細と再現用requestは[モード追跡](MODE_TRACKING.md)。


## D01標本部分空間追跡と明示円筒写像 — 2026-09-08

G03の残件を保持し、計画上独立に着手可能なD01を開始した。
mode_tracking.pyは共通標本の実場/正重み/写像説明を要求し、周波数クラスタごとに
重み付きSVD直交基底を作る。最悪主角の重なりと行/列の競合差から等次元クラスタを対応付ける。
以前のIDを継承し、mode_indexは周波数順位のまま。多次元は部分空間だけを識別し個別IDを付けない。
曖昧・欠落/追加・ランク不足・合流/分裂を未確認で残す。
tracked_frequency_hzは追跡全体の未確認と部分空間内の個別周波数を拒否する。tune本体は未実装。

track_cylindrical_modesはmapping=normalized_cylinderを明示必須とし、一定半径profile・両端PECに制限。
保存後に読み直した実P1/P2場のHphiをr=R*rho,z=L*zetaへ写し、rho重みのGauss積則で比較する。
形状依存の定数Jacobianは正規化で消える。一般形状へこの写像を暗黙適用しない。
結果に比較点/重み/寸法/次数/場の規約を記録し、既存の場・RF・同形状比較は変更しない。

追加9テストは解析交差/近接、縮退基底回転、曖昧同点、欠落/ランク不足/合流、
重み/標本順/符号/極端振幅、厳密入力、部分空間の一方向喪失、保存後の実FEM円筒交差。
実装前ModuleNotFoundErrorを確認。変更前412件中410合格・2 skip（126.677秒）。
最終421件中419合格・2 skip（128.101秒）、out/validation-d01-mode-tracking-20260908 PASS。
同所seed_comparison.jsonでcase hash一致、周波数差0、RF/エネルギー差最大8.882e-16。
FEM本体/数値基準変更なし、検証中ソース変更なし、最終fingerprint一致。

scripts/validate_mode_tracking.pyの独立実行out/d01-cylinder-crossing-20260908/mode_tracking.json PASS。
R=0.1 m、L=0.055/0.075 mのP2円筒を12×12分割/3モードで実計算・保存・再読込した。
Bessel解析周波数で旧順位010/020/011、新順位010/011/020を確認し、最大相対周波数差5.600337e-6。
追跡は解析式でなく保存Hphiから行い、12×12と18×18標本で同じID対応を確認。
最小principal overlapはそれぞれ0.999999999965、0.999999999961。
両実行のソースhash一致。GUI/Wine新規実行なし。合成円筒であり測定構造ではない。

[追跡仕様](MODE_TRACKING.md)を追加し、README・対応表・計画・実装状況を同期。
重み付き内積・SVDの基底不変性と既存SciPy割当から独立実装。新規外部資料/コード/依存/旧資産参照なし。
D01は部分実装。一般写像・合流/分裂・連続履歴/安定ID保存・CLI/GUI/Study/tune統合は残件。
G03の一般弧端/重解・旧入力/物理収束も継続。8親課題の限定受入は維持し、
進行中はC00/G03/D01の3件、他21親課題未受入、X01は拡張候補。全計画目標は未完了。


## G03曲率・最小半径の極端な尺度への修正 — 2026-09-08

conics.pyの曲率/最小半径の積商を、frexpの仮数/二進指数で合成してldexpで戻す計算へ変更。
中間の三乗・積・比の範囲逸脱を避け、最終値が表現できない場合は明示ValueErrorとする。
曲率の分子に二進回転行列のdet、最小半径に一様回転尺度を含める。
点/接線/角度パラメータや有限弧候補の数値評価方法は変更していない。
これらの数値評価を、最小子午面半径制約の有理数区間証明としては使わない。

修正前に楕円軸(2s,s)、s=1e±200で、表現可能な最小半径s/2がNaNになることを確認。
双曲線軸(1e-300,1e-300)、u=460..461では半径infと曲率評価エラーを確認した。
追加4テストの修正前実行は2エラー/1失敗。修正後は4件と既存円錐曲線テストの計28件PASS。
双曲線は80桁Decimalの独立指数関数・平方根・曲率式で照合した。
初期subnormal fixtureはnp.float64を渡して厳密入力に拒否されたためbuiltin floatへ訂正。
製品の厳密型検査や許容差は緩めていない。

変更前408件中406合格・2 skip（124.645秒）。
最終412件中410合格・2 skip（127.394秒）、out/validation-g03-conic-scale-20260908 PASS。
同所seed_comparison.jsonでcase hash一致、周波数差0、RF/エネルギー差最大8.882e-16。
FEM本体・数値基準変更なし、検証中ソース変更なし、最終fingerprint一致。
scale_examples.jsonに再計算した極端尺度の入力/数値を保存。
双曲線の最小半径7.496180459261836e298 m、始点曲率1.334012708784858e-299 /mを確認した。
これをFEMの対応寸法範囲や任意の極端な軸比の精度保証へ拡張しない。

construction_replay.jsonで既存構築版1〜6と半径制約付き版6を再読込CASE_VALIDATED。
前回GUIからダウンロードした構築診断も再検証し、元Caseの合格を維持した。
GUI/Wineの新規実行なし。README・対応表・計画・実装状況・幾何仕様・G03照合表を同期。
初等積商の指数分離と既存の曲率式から独立修正し、新規外部資料/コード/依存/旧資産参照なし。
次は一般の弧端/重解と退化候補構築、旧入力/物理収束の残件。
8親課題の限定受入を維持し、G03全体と全計画目標は未完了。


## G03最小子午面曲率半径のCase制約 — 2026-09-08

meridional_radius.pyと任意geometry.minimum_meridional_radius_mを追加。
有限正数を要求し、未指定なら旧JSONのキー・Case hashを維持する。
PEC曲線内部の|k|を距離0の法線オフセット区間で囲み、全域|k|<=1/Rを検査する。
違反点の下界が1/Rを超えればFAIL、幅/級数/箱数予算不足はUNVERIFIED。両方をCaseで拒否。
PEC-PECは1e-8 radのG1数値検査も要求。軸/対称境界と周方向主曲率は対象外。
構築選択後の完成Case、保存再読込、鏡映、GUIでの形状保持へ接続した。
専用GUI入力欄はない。制約は解析曲線に対するもの。FEM精度や物理ピーク収束の保証ではない。

実装前のModuleNotFoundErrorを確認。追加6テストは円/直線・1 ULP差、楕円/双曲線極値と
有限弧/尺度/向き、予算不足、PEC角拒否/厳密入力/旧JSON、構築/GUI・実FEM不変/保存再読込、
両対称タグの鏡映後再検査。予算不足fixtureの初期要求3.9 mは実最小約3.870707 mを超え、
実装が正しくFAILを返した。要求を3.8 mへ修正し、1箱UNVERIFIED/既定予算PASSを確認。
製品の判定や許容差は緩めていない。
変更前402件中400合格・2 skip（121.781秒）。最終408件中406合格・2 skip（125.496秒）。
out/validation-g03-meridional-radius-20260908 PASS、seed_comparison.jsonでcase hash一致、
周波数差0、RF/エネルギー差最大8.882e-16。FEM本体/数値基準変更なし、最終source hash一致。
同所construction_replay.jsonで版1〜6の既存保存を再読込。radius_constraint.jsonに区間証拠を保存。

out/gui-meridional-radius-browser-20260908/report.jsonでChrome11操作PASS、外部要求0、
実行中ソース変更なし。保存された構築・適用・FEM計算で0.019 mの制約保持を確認。
tangent-construction.pngの表示も確認。検証GUIは停止済み。今回Wine新規実行なし。
例examples/construction/radius_constrained_fillet_request.jsonはR20 mmのフィレットへ下限19 mmを指定。
21 mm指定は違反として拒否し、半径は自動変更しない。
実CLIはout/g03-radius-constrained-construction-20260908.json、out/g03-radius-constrained-case-20260908.json、
out/g03-radius-constrained-solve-20260908。周波数1258432805.464176 Hz、R/Q(acc)=140.166774 ohm、
制約なしの同一形状と一致。合成形状であり測定空洞ではない。

[制約仕様](MERIDIONAL_RADIUS.md)を追加。README・対応表・計画・実装状況・G03照合表を同期。
既存区間曲率核から独立実装し、新規外部資料/コード/依存/旧資産参照なし。
次は一般の弧端/重解と退化候補構築、旧入力/物理収束の残件。
8親課題の限定受入を維持し、G03全体と全計画目標は未完了。


## G03構築診断の保存・CLI/GUI接続 — 2026-09-08

construction_diagnostics.pyを追加し、版5/6構築の実探索証明から区間・符号付き距離を
有理数で取り出して既存の特殊ケース診断へ渡す。延長線分も実際の探索区間を使う。
元構築全体・parameter_domain_box・診断を別の版1文書として保存する。
文書型はconstruction_offset_diagnosis。再読込は元構築と診断を再計算し全体照合する。
既存構築版1〜6の保存内容は変えない。診断CERTIFIEDとCASE_VALIDATEDは別判定。
通常交点の診断がUNVERIFIEDでも、認証候補/閉輪郭検査に合格したCaseを取り消さない。

GUIは診断/全領域分類の状態を別欄に表示し、「中心軌跡の診断を保存」で元構築ごと保存。
同じ構築ファイル入力で再検証して開ける。要求/候補の変更、改変拒否で診断保存も無効化。
CLI diagnose-constructionは保存構築または保存診断を受け、既存出力へは上書きしない。
診断用の要求から元の計算プロジェクトへ自動適用しない。

追加5テストは弧端接触の証明と未完成Caseの分離、明示延長の実探索範囲、通常合格と
特殊ケース未分類の両立、旧版維持、改変拒否、CLI保存再実行/上書き拒否。
実装前のModuleNotFoundErrorを確認。変更前397件中395合格・2 skip（121.122秒）。
最終402件中400合格・2 skip（121.903秒）、out/validation-g03-construction-diagnosis-20260908 PASS。
同所seed_comparison.jsonでcase hash一致、周波数差0、RF/エネルギー差最大8.882e-16。
FEM本体/数学分類核/許容差/数値基準変更なし。検証中ソース変更なし、最終fingerprint一致。
同所construction_replay.jsonに版1〜6の既存実保存ファイル再読込CASE_VALIDATEDを保存。

out/gui-construction-diagnosis-browser-20260908/report.jsonはChrome11操作PASS、外部要求0、
実行中ソース変更なし。元の8操作に診断表示/ダウンロード/再読込、診断改変拒否、
弧端接触を証明しても未確認構築の適用を許可しない3操作を追加した。
tangent-degenerate.pngで診断表示と適用不可を視認。元プロジェクト不変も確認。
ダウンロードした診断はPythonでも再読込し、診断UNVERIFIED/構築CASE_VALIDATEDを確認。
検証用GUIは停止済み。今回Wine新規実行なし。

例examples/construction/degenerate_fillet_request.jsonを実CLIで構築するとUNVERIFIED（exit 1）。
out/g03-degenerate-fillet-construction-20260908.jsonへ保存し、diagnose-constructionで
out/g03-construction-diagnosis-20260908.jsonへSINGLE_TANGENCY / finite_domain_complete=trueを保存。
診断はexit 0でも構築はUNVERIFIED、Caseなしのまま。例は未完成の編集/診断要求であり測定空洞ではない。

README・対応表・計画・実装状況・G03照合表・診断/GUI仕様を同期。
既存核の製品接続で、新規外部資料/コード/依存/旧資産参照なし。
次は一般の弧端/重解と退化候補構築、最小半径契約、旧入力/物理収束の残件。
8親課題の限定受入を維持し、G03全体と全計画目標は未完了。


## G03弧端・退化の厳密特殊ケース診断 — 2026-09-08

offset_degeneracies.pyとdiagnose-offsets CLIを追加。元パラメータが一致する円/楕円/双曲線の
オフセットについて、方向補正した距離を照合し、共通区間の無限対/共有端点を証明する。
この証拠を別パラメータの交差まで含む全解数へ拡張しない。
有理数で表せる円のオフセットと直線では、外接/内接/離隔、潰れ、平行重複を分類。
支持接点を元の有限範囲へ戻し、円弧は既存の区間所属検査を使う。
中心点の個数とパラメータ対の無限性、証明した事実とfinite_domain_completeを区別する。
一般二進回転/直線長の平方根を1や有理数近似へ置換しない。未対応/予算不足はUNVERIFIED。

追加9テストは独立円の外接/内接と1 ULP差、有限弧端点/外部/予算不足、潰れと無限対、
楕円/双曲線の共有区間/方向反転/共有端点、直線と円/平行直線、尺度/交換、
支持円一致と有限所属の区別、厳密入力とCLI保存再実行・未確認出力・上書き拒否。
実装前のModuleNotFoundErrorを確認。変更前388件中386合格・2 skip（121.553秒）。
最終397件中395合格・2 skip（121.847秒）、out/validation-g03-offset-degeneracy-20260908 PASS。
同所seed_comparison.jsonでcase hash一致、周波数差0、RF/エネルギー差最大8.882e-16。
FEM・許容差・数値基準変更なし。検証中の実装変更なし、最終source fingerprint一致。

例はexamples/construction/offset_tangency_diagnosis_request.json。弧の始点で接する円の中心軌跡を
out/g03-offset-tangency-diagnosis-20260908.jsonへ実CLI保存し、SINGLE_TANGENCY / 完全分類を確認。
診断要求版1は構築要求版1やCase版1とは別契約。出力にdocument_type・要求/hash・software版を保持する。
validation内diagnostic_examples.jsonに反転円オフセット、直線上への潰れ、共有端点の追加実行を保存。
同所construction_replay.jsonに版1〜6の実保存ファイル再読込CASE_VALIDATEDを保存した。
GUI新規実行なし、Wine新規実行なし。既存構築の候補/保存結果へ診断を暗黙に適用しない。

[診断仕様](OFFSET_DEGENERACIES.md)を追加し、README・対応表・計画・実装状況・G03照合表を同期。
既存区間演算と初等円幾何/線形代数から独立実装。新規外部資料/コード/依存/旧資産参照なし。
次は一般の弧端/重解、診断の構築/GUI接続、最小半径契約、旧入力と物理収束の残件。
8親課題の限定受入を維持し、G03全体と全計画目標は未完了。


## G03版6直線・有限弧フィレット — 2026-09-08

normal_offsets / offset_intersectionsを線分の支持直線へ拡張し、conic_filletと
構築schema_version=6で直線と有限弧の指定半径フィレットを保存/Case/CLI/GUIへ接続した。
二進端点の線分を有理数アフィン式で扱い、単位法線の平方根を外向き区間で囲む。
延長なしは[0,1]、明示allow_extension=trueでは有限弧の中心軌跡を線分方向へ射影して
必要な有限探索範囲を導く。弧は延長しない。配列順に線分の始点/終点を保持し、
空/逆向きになる保持線分を拒否する。生成接点/保持端/中心の位置上界を検査し、
元線分との方向差とG1角度は数値検査として区別する。

実装前には線分normal_offset_boundsのValueErrorとallow_extension未対応のTypeErrorを確認。
追加6テストは3-4-5線分法線区間、既知円/双曲線接点、明示延長と両順序、逆向き拒否、
保存/再構築/GUI・解析面積/体積、実曲線FEMの相似則。変更前382件中380合格・2 skip。
最終388件中386合格・2 skip（124.074秒）、out/validation-g03-line-conic-fillet-20260908 PASS。
同所seed_comparison.jsonでcase hash一致、周波数差0、RF/エネルギー差最大8.882e-16。
FEM本体・数値基準・許容差変更なし。検証中の実装変更なし、最終fingerprint一致。

out/gui-line-conic-fillet-browser-20260908/report.jsonはChrome8操作PASS、外部要求0、
実行中ソース変更なし。半径/回転方向/円弧長/接点上界、明示選択・ダウンロード・再構築・
適用・FEM/描画・改変拒否まで確認。tangent-construction.pngの表示も確認し、GUIは停止済み。
validation内construction_replay.jsonに版1〜6の実保存ファイルのCASE_VALIDATEDを保存した。

合成例はexamples/construction/line_conic_fillet_request.json。z=0.15 mの直線壁と
半径0.1 mの円弧を半径0.02 m、反時計回りの円弧で接続する。延長なし、二次幾何/二次場。
CLIはout/g03-line-conic-fillet-construction-20260908.json、out/g03-line-conic-fillet-case-20260908.json、
out/g03-line-conic-fillet-solve-20260908へ保存。周波数1258432805.464176 HzはGUIと一致し、
R/Q(acc)=140.166774 ohm。接点位置誤差上界最大2.568e-17 mで要求1e-12 m以内。
保持線分の方向差0、延長なし、端点内側調整なし。この形状のRF/物理ピーク収束は未検証。

既存の認証交点核・初等線形射影から独立実装。新規外部資料/コード/依存/旧資産参照なし。
Wine新規実行なし。README・対応表・計画・実装状況・G03照合表を同期。
次は弧端/退化の追加分類、輪郭全体の最小半径契約、旧入力と物理収束の残件。
8親課題の限定受入を維持する。G03全体と全計画目標は未完了。


## G03版5有限弧フィレット・保存/CLI/GUI統合 — 2026-09-08

conic_filletと構築schema_version=5を追加。両有限弧の中心軌跡に同じ符号付きRを使い、
根箱から元の接点を復元して元弧/指定半径円弧/元弧へ切り詰める。
半径・回転方向・最大円弧角を明示し、大回り上限超過や空/表現不能・未達は選択不可。
元弧端点/フィレット端点/保持外端/中心の誤差上界を確認し、G1角度は数値検査として区別。
float中点が根箱内にあるかも記録するが、接点一致の根拠にはせず位置上界で検査する。
版1〜4の経路を維持し、版5保存/再構築・Case/CLI/GUIまで接続した。

初回の合成Caseは隣接検査で約3e-17 mの丸め重なりを拒否した。
out/g03-conic-fillet-overlap-before-20260908.jsonへ元の要求/候補/拒否理由を保持。
検査は緩めず、必要時だけフィレット両端を明示位置/角度許容差内で内側へ取り、
中心/Rを保持して全上界・G1・進行方向分離を再検査する処理を追加した。
合成例の内側角は3.125e-12 rad、元弧接点上界約1.09e-15 m、フィレット約6.36e-14 m。
要求の1e-12 mより小さいことを確認。初期fixtureのjoin_toleranceは軸長制限より
大きかったため1e-12 mへ厳しくし、製品の制限・許容差は緩和していない。

追加6テストは既知円の接点/半径/小回り・大回り、楕円/双曲線四分円、
方向反転・厳密指定/未達、保存/GUIと解析面積/体積、二次曲線FEM相似則。
変更前376件中374合格・2 skip、最終382件中380合格・2 skip（119.905秒）。
out/validation-g03-conic-fillet-20260908 PASS。同所seed_comparison.jsonでcase hash一致、
周波数差0、RF/エネルギー差最大8.882e-16。FEM本体/数値基準変更なし。
検証中の実装変更なし。Wine新規実行なし。

out/gui-conic-fillet-browser-20260908/report.jsonのChrome8操作PASS、外部要求0、
実行中ソース変更なし。tangent-construction.pngの半径/時計回り/円弧長/接点上界表示を確認。
明示選択・保存ダウンロード・再構築・適用・曲線FEM/描画・改変拒否まで実操作済み。
検証用GUIは停止済み。validation内construction_replay.jsonには版1〜5の
実保存ファイル再読込をCASE_VALIDATEDで保持する。

例はexamples/construction/two_lobe_fillet_request.json。2円弧をR=0.02 mの時計回り円弧で
つなぐ合成2山形状で、geometry_order=2 / element_order=2を明示する。
実CLI記録はout/g03-conic-fillet-construction-20260908.json、out/g03-conic-fillet-case-20260908.json、
out/g03-conic-fillet-solve-20260908。周波数1310579815.6725943 Hz、R/Q(acc)=85.595228 ohm。
GUIと同じ周波数を確認。解析面積/体積と相似則を、この形状のRF/物理ピーク収束へ読み替えない。

既存の認証交点/端点区間核と初等円幾何から独立実装。新規外部資料/コード/依存/旧資産参照なし。
README・対応表・計画・実装状況・G03照合表を同期。
次は線分と弧のフィレット、弧端/退化の追加分類、旧入力と物理収束の残件。
8親課題の限定受入を維持し、G03全体・全計画目標は未完了。


## G03中心軌跡の有限領域交点探索 — 2026-09-08

offset_intersections.intersect_normal_offsetsを追加。符号付き法線距離を指定した
2円錐曲線の有限fraction領域で、F=C1−C2の孤立交点を探す。
有理数のKrawczyk内部包含と∞ノルム収縮上界<1で存在/一意性を確認し、
根のparameter_box・center_box・証明領域/行列/収縮上界を保持する。
座標包絡/Krawczyk箱が交わらない場合だけ除外し、包含で縮小して根を失わない。
認証後も指定fraction幅まで縮小する。96 bit既定の外向き二進格子で分母増大を制御し、
格子精度/級数/箱数の予算不足、接触・潰れ・同一・弧端/共有境界は未確認を保持する。
全体PASSには未処理/未確認領域なしと全根の幅達成を要求する。

追加7テストは円の2交点、楕円陰関数からの4交点、非零距離の楕円/双曲線頂点交点、
有限弧制限/離隔、接触/同一/潰れ/弧端、尺度/交換、格子/級数/箱数予算と厳密入力。
未実装ImportErrorを先に確認。初期接触fixtureが接点を有限弧から外していたため、
接点を含む弧へ訂正した。製品の正しい無交点判定や許容差は変更していない。
変更前369件中367合格・2 skip、最終376件中374合格・2 skip（98.680秒）。
out/validation-g03-offset-intersections-20260908 PASS。同所seed_comparison.jsonで
case hash一致、周波数差0、RF/エネルギー差最大8.882e-16。FEM/数値基準変更なし。
検証中の実装変更なし。GUI/Wineは今回未実行。

同所intersection_examples.jsonに入力・controls・根箱・認証証拠を保存（136349 bytes）。
円2交点PASS（121箱）、楕円4交点PASS（99箱）、楕円/双曲線1交点PASS（8箱）。
接触例は40箱予算で2領域を未確認として保持しUNVERIFIED。未確認を根なしに変えない。
既知座標との照合にはDecimal100桁の別計算を使用した。

R32としてRump (2010)の著者所属機関公開原稿Theorem 13.3、§13.1–13.2の数学的条件を確認。
出版社で書誌も照合し、REFERENCES.md / references.bibへ記録した。
区間演算・分割・証拠保存は既存Fraction核から独立実装。論文本文/掲載コードは転記せず、
INTLABや第三者PDFは同梱しない。新規依存/旧資産参照なし。

G03照合表・README・対応表・計画・実装状況を同期。
次は根箱からの有限接点復元、左右/半径の組合せ、有向円弧と空弧の検査、
線分中心軌跡、弧端/退化の追加分類、保存/Case/CLI/GUI、独立形状/FEM検証。
8親課題の限定受入を維持し、G03全体・全計画目標は未完了。


## G03法線オフセット区間と要件照合 — 2026-09-08

normal_offsets.normal_offset_bounds / partition_normal_offsetを追加。
円錐曲線フィレットの中心軌跡C=x+dNとC'=(1−dκ)x'を有理数区間で囲む。
二進回転係数のc²+s²を保持し、符号付き曲率/速度に反映する。
sin/cos中点級数+Lipschitz、sinh両端、coshと速度の有理数平方根境界を使用。
円の定曲率では相関を使い、半径分の内側オフセットが中心へ潰れることを保持する。
正則FORWARD/REVERSED、円のCOLLAPSED、ゼロを含むUNVERIFIEDを区別する。
全有限fraction区間を被覆し、予算不足/分離不足で未処理区間を除外しない。
PASSは全区間の正則性だけで、交点・尖点の存在/根数・フィレット候補完成ではない。

追加6テストは円の半径変化/潰れ、楕円/両枝双曲線頂点、点/数値微分の包含、
既知楕円折返し位置の保持と全区間被覆、予算/厳密入力、方向/尺度、
Decimalによる二進回転頂点の独立照合。未実装ImportErrorを先に確認した。
双曲線頂点の中心方向の初期テスト期待値は法線符号から訂正し、閾値緩和なし。
変更前363件中361合格・2 skip、最終369件中367合格・2 skip（94.587秒）。
out/validation-g03-normal-offsets-20260908 PASS。seed_comparison.jsonでcase hash一致、
周波数差0、RF/エネルギー差最大8.882e-16。FEM/数値基準の変更なし。
検証中の実装変更なし。GUI/Wineの新規実行なし。

同所offset_partitions.jsonは要求曲線/controls/区間結果を有理数表記で保存。
円はSINGULAR（1区間）、楕円は39区間処理後に18正則・2未確認を保持してUNVERIFIED、
双曲線は全区間正則でPASS。楕円の未確認を失敗根除外や尖点数証明へ読み替えない。
この基盤は通常Case/GUIからの弧フィレット構築へまだ接続していない。

G03_ACCEPTANCE.mdを新設し、CONIC_GEOMETRYの5段階と計画G03の要件を照合した。
曲線FEM/幾何別細分の既存comparison.jsonのPASSと、前回Chrome8操作のpassed=trueを
現在のファイルで再確認。全曲線入力互換・弧を含むフィレット・物理ピーク収束は不足を明示。
最小半径のプリミティブ値と、任意輪郭への制約契約も区別する。
README・対応表・計画・実装状況・バックログを同期した。

新規外部資料/コード/依存/旧資産参照なし。初等微分幾何と既存有理数区間核から独立導出。
次は中心軌跡の交点探索、有限接点/有向切詰め、保存/CLI/GUI、独立形状/FEM検証。
8親課題の限定受入を維持し、G03全体・全計画目標は未完了。


## G03版4指定半径の線分間フィレット — 2026-09-08

line_filletと構築schema_version=4を追加。2本の有向線分の支持交点を二進入力から
有理数で求め、R tan(|θ|/2)の切詰め距離で小円弧を構築する。交点以降の生成幾何は
浮動小数点を含み、支持直線距離・有限範囲・G1・保持方向を数値検査する。
版2/3の区間認証とは区別し、GUIにも指定半径・円弧長・数値検査と表示する。
有限線分の延長は明示bool、空/逆向き保持線分・平行/反転・数値未達を拒否し、
半径を自動縮小しない。線分/円弧/線分を完成Case全体の検査へ通す。

既知直角接点/中心/1/R曲率/除去面積を先にテスト化し、未実装ImportErrorを確認。
追加7テストは回転/鏡映/尺度/逆順、浅い/鈍い転向、過大半径/延長/厳密指定、
保存改変拒否/GUI共通APIと解析面積、二次曲線FEM相似則までPASS。
初期テストのNumPy scalar入力をbuilt-in floatへ修正し、数値未達用fixtureは
端点がfloatで一致する直角から非直角へ訂正した。製品の型契約・許容差は緩和していない。
変更前標準356件中354合格・2 skip、最終363件中361合格・2 skip（94.553秒）。
out/validation-g03-line-fillet-20260908 PASS。seed_comparison.jsonでcase hash一致、
周波数差0、RF/エネルギー相対差最大8.882e-16。FEM本体/数値基準の変更なし。

out/gui-line-fillet-browser-20260908/report.jsonのChrome8操作PASS、外部要求0、
実行中ソース変更なし。tangent-construction.pngの半径/長さ/検査範囲表示を確認。
明示選択・保存ダウンロード・再構築・適用・曲線FEM/描画・改変拒否まで実操作済み。
検証用GUIサーバーは停止済み。validation内construction_replay.jsonには
以前の版1/2/3と今回の版4の実保存ファイル再読込をCASE_VALIDATEDで記録した。

例はexamples/construction/corner_fillet_request.json。合成長方形断面の右上角を
R=0.02 mで丸め、geometry_order=2 / element_order=2を明示。
実CLI構築/Case/solveはout/g03-line-fillet-construction-20260908.json、
out/g03-line-fillet-case-20260908.json、out/g03-line-fillet-solve-20260908。
周波数1152045668.073337 Hz、R/Q(acc)=57.172456 ohm。GUIと同じ値を確認。
幾何の解析不変量とFEMの相似則の証拠であり、この形状のRF/ピーク収束は未検証。

式は初等直線/円幾何から独立導出。新規外部資料/コード/依存/旧資産参照なし。
Wine新規計算なし。次は円/楕円/双曲線弧を含むフィレットとG03全要件照合。
線分間の部分受入で全フィレット対応とは扱わず、8親課題の限定受入を維持する。
G03全体・全互換目標は未完了。


## G03版3固定支持直線・有限弧の構築統合 — 2026-09-08

line_arc_tangentと構築schema_version=3を追加。固定支持直線の接線条件w²=nQnと
接点c+Qn/wを二進入力から厳密有理数で求める。非接線・無限遠接点を区別し、
有限線分の延長可否と元の順序/保持端点を明示する。枝/有限弧/fractionを区間判定し、
空線分/空弧・逆向き・未確認は接続しない。生成端点と保持弧外端の位置誤差を囲む。
G1角度は数値検査。近傍線の自動補正・任意フィレット・角度区間認証とは区別する。
要求/保存/再構築・Case/CLI/GUIへ接続し、版1/2の既存保存文書も実再読込できた。

追加7テストは既知円/双曲線接点、枝/端点/延長/方向、非接線/漸近線、予算/厳密controls、
保存/GUI共通API、合成カプセルの解析面積/体積と実FEM相似則。
標準356件中354合格・2 skip（92.557秒）、out/validation-g03-line-arc-20260908 PASS。
同所seed_comparison.jsonでcase hash一致、周波数差0、RF/エネルギー相対差最大8.882e-16。
数値基準/FEM本体/許容差の変更なし。

out/gui-line-arc-browser-20260908/report.jsonのChrome8操作PASS、外部要求0、
実行中ソース変更なし。tangent-construction.pngで保持端/接点と誤差上界の表示を確認。
保存ダウンロード・再構築・明示適用・FEM/描画・改変拒否まで確認し、GUIサーバーは停止済み。
実CLI記録はout/g03-line-arc-construction-20260908.json、out/g03-line-arc-case-20260908.json、
out/g03-line-arc-solve-20260908。例はexamples/construction/capsule_line_arc_request.json。
版1のout/gui-tangent-browser-final-20260908/downloads/tangent-construction.json、
版2のout/g03-certified-capsule-construction-20260908.jsonもCASE_VALIDATEDで再読込した。

版2/3カプセル比較はvalidation内capsule_v2_v3_comparison.json。
双方617節点/1152三角形で、f相対差2.32491e-8、両RQ差0.626214%、G差8.12673e-8、
TTF差0.310662%。微小な構築差から再生成したメッシュ同士の比較であり、純幾何誤差と
FEM/RF誤差を分離していない。このカプセルのRF精度収束は未検証として保持する。
接点誤差上界をRF精度保証に読み替えず、差を隠す補正も行わない。

式は既存二次形式と初等幾何から独立導出。新規外部資料/コード/依存/旧資産参照なし。
Wine新規計算なし。次はフィレットとG03全要件照合。8親課題の限定受入を維持し、
G03全体・全互換目標の完了は宣言しない。


## G03版2区間付き構築・保存・CLI/GUI統合 — 2026-09-08

certified_constructionと構築schema_version=2を追加。確定fraction区間内のfloat位置を選び、
生成弧の数学的端点と出力floatを囲むboxから、厳密接点への距離上界を検査する。
外側の保持端点も誤差上界を確認する。G1角度は生成プリミティブの数値検査として区別。
第1弧END/第2弧STARTは元弧を再利用し、空弧・零長・逆向き・未達は候補と理由を残して選択不可。
版1の従来経路と保存文書の実再読込を維持。版2は同じCLI/GUIで保存/再構築/Case/FEMまで接続した。

最終標準349件中347合格・2 skip（91.637秒）、標準数値回帰PASS。
out/validation-g03-certified-construction-20260908のseed_comparison.jsonでcase hash一致、
周波数差ゼロ、RF/エネルギー相対差最大8.882e-16。基準更新なし。
Chrome8操作はout/gui-certified-construction-browser-20260908/report.jsonでPASS。
外部要求0・実行中ソース変更なし、tangent-construction.pngの誤差上界表示を確認。
検証用GUIサーバーは停止済み。Wine新規計算なし。

追加5テストは区間内切詰め/誤差上界、端点再利用/空弧拒否、版2保存/版1継続、
不正指定/位置未達、GUI応答と合成カプセルの解析面積/体積・実FEM相似則。
例題はexamples/construction/capsule_certified_request.json。
実CLIの構築/Case/solveはout/g03-certified-capsule-construction-20260908.json、
out/g03-certified-capsule-case-20260908.json、out/g03-certified-capsule-solve-20260908。

版1/2カプセル比較はcapsule_v1_v2_comparison.json。617節点/1152三角形は同数だが
メッシュ座標/接続は異なり、f差1.41259e-8、RQ差0.312004%、TTF差0.154291%を記録した。
接点位置誤差の保証をRF精度保証にせず、この形状のRF収束は未検証。補正/閾値変更なし。
仕様・再現・初期版との区別はTANGENT_CONSTRUCTION.mdとGUI_ACCEPTANCE.md。
新規外部資料/コード/依存/旧資産参照なし。

次は直線と弧の接線/フィレットとG03全要件照合。G03全体と全互換目標は未完了。


## G03有限弧所属とfractionの有理数区間 — 2026-09-08

certified_arcs.certified_finite_arc_tangentsを追加。支持曲線の接点boxから有限弧の
INTERIOR/EXTERIOR/START/END/UNVERIFIEDを判定し、fractionを有理数の閉区間で返す。
楕円は2 rad以下のsectorの和集合、双曲線は枝とsinhの単調性を使う。
端点sin/cosはTaylorのLagrange剰余、sinhは正項級数の幾何残尾で囲む。
float atan/asinhや経験的epsilonは判定根拠にしない。厳密な一点一致だけをSTART/ENDにする。
fractionはprefix所属の二分で囲み、未分離/予算不足では最後の有効区間を保持する。

最終標準344件中342合格・2 skip（86.157秒）、標準数値回帰PASS。
out/validation-g03-certified-arcs-20260908のseed_comparison.jsonでcase hash一致、
周波数差ゼロ、RF/エネルギー相対差最大8.882e-16。基準更新なし。GUI/Wineは今回未実行。

対象は保存された二進パラメータと支持係数。元の実数入力の丸め前まで認証しない。
独立8検査で10^-20 rad端点近傍、周期/逆向き/内部sector境界、双曲線枝/端点、
Decimal.expによる独立sinh照合、既知fractionの1/2・1/3・2/3、各予算不足を確認。
元の合成カプセル候補1件も両点INTERIORとfraction幅2^-32でPASS。
有理数レポートはout/validation-g03-certified-arcs-20260908/capsule_membership.json。
仕様と式は[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md)。新規外部コード/資料/依存/旧資産参照なし。

次は区間から選んだ切詰め位置の接点誤差上界と明示位置許容差の検査、空弧/端点再利用の操作契約、
版付き構築・保存・CLI/GUIへの統合。既存の版1構築/GUIは数値ガード判定のまま保持する。
直線と弧の接線・フィレット・G03全要件照合は継続。全互換目標は未完了。


## G03支持曲線の接点座標区間 — 2026-09-08

contact_enclosures.supporting_contact_enclosuresを追加した。既存の孤立法線根区間から、
接触定数・接点座標を有理数区間で伝播する。厳密根は一点として扱い、D=0の±sqrt分岐を保持する。
分母の0分離に失敗すれば未確認。box幅上限の未達でも生成boxと候補番号を保存する。
返却float接点から厳密接点までの距離上界も別に返す。

最終標準336件中334合格・2 skip（85.740秒）、標準数値回帰PASS。
out/validation-g03-contact-enclosures-20260908に検証ログとseed_comparison.jsonを保存。
seed case hash一致、周波数差ゼロ、RF/エネルギー相対差最大8.882e-16。基準更新なし。

局所座標の厳密逆行列から双曲線指定枝を区間符号で検査する。
二進cos/sinのc²+s²を1と仮定しない。回転0.37 radの有理単位円点(3/5,4/5)の
順逆変換が一点boxで厳密一致する追加検査はlocal_inverse_invariant.jsonに保存した。
支持曲線の二進係数に対する区間であり、元の実数回転・測定寸法や有限弧端の所属を認証しない。
既存の有限弧構築・保存形式・CLI/GUI判定にはまだ接続せず、別APIとして公開する。

独立8検査は既知円/楕円/双曲線の無理数接点の二乗比較、根幅→box幅減少、
直角回転/移動/2^-20〜2^20尺度、返却接点誤差上界、指定枝反転、幅未達・未完根・一致曲線・不正幅。
仕様と再現は[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md)。
新規外部資料/コード/依存/旧資産の参照なし。接触式と既存有理数境界から独立実装した。

次は局所接点boxと有限弧端の比較、内外/端点判定と区間に基づく切詰めの版付き構築統合。
双曲線の有限区間・楕円の有向周期区間、直線と弧の接線/フィレット、G03全要件照合は残る。
全互換目標は未完了。GUIは前回受入のままで今回新規実行しない。


## G03接線構築GUI受入 — 2026-09-08

GUIへ構築要求/保存結果の読込、接点・長さ・方向の候補表、明示選択、閉輪郭検査、
構築保存、編集画面への明示適用を追加。tangent_documentはCLIと同じ構築/再構築/Case経路を使う。
要求の編集・候補変更・別ファイル読込で古い結果を解除し、非同期の古い応答も除外する。
読み込み/候補表示だけでは現在のプロジェクトを変更しない。適用時は要求の計算条件も反映する。

最終標準328件中326合格・2 skip（85.344秒）、標準数値回帰PASS。
out/validation-g03-tangent-gui-final-20260908のseed_comparison.jsonでcase hash一致、
周波数差ゼロ、RF/エネルギー相対差最大8.882e-16。ベンチマーク更新なし。
out/gui-tangent-browser-final-20260908のChrome7操作PASS、外部要求0、実行中ソース変更なし。
保存再読込→適用→FEM→場表示、改変拒否まで実操作し、tangent-construction.pngを表示確認した。
GUI合成カプセルf=1170098360.3437803 Hz。物理精度収束や旧版照合の証明ではない。

初回out/gui-tangent-browser-20260908はJavaScript JSON再生成で1.0等の表記が変わり、
保存後の厳密再構築照合がFAIL。サーバーが生成したserialized文字列をそのまま保存する修正後に再検証した。
初回数値回帰はPASSだったがGUI未受入であり、最終版とは区別する。失敗ログは保持。
再現と操作はGUI_GUIDE.md、GUI_ACCEPTANCE.md、TANGENT_CONSTRUCTION.md。
検証用GUIサーバーは停止済み。新規外部資料/コード/依存/旧資産参照なし。

次は接点区間/弧端認証、直線と弧の接線・フィレットとG03全要件照合。
GUIの追加をG03全体の完了や全互換目標の完了とは扱わない。


## G03接線構築の保存・Case・CLI — 2026-09-08

tangent_construction.pyに版1の構築要求/結果と保存後の再構築照合を追加した。
case_templateは未完成の編集文書、候補未選択のcaseはnullと明示する。
連続する2つのPEC弧を明示選択で弧/線/弧へ置換し、既存Caseで閉輪郭と全設定を検査する。
construct-tangent/export-constructed-caseを追加し、既存solveまで接続。
primitiveのstrict読書きを既存CurvedContourと共通化。計算式と依存は変更していない。

最終標準326件中324合格・2 skip（86.428秒）、標準数値回帰PASS。
out/validation-g03-construction-cli-20260908にtests.log/validation.json/seed_comparison.jsonを保存。
seedのcase hash一致、周波数差ゼロ、RF/エネルギー相対差最大8.882e-16。基準更新なし。
検証実行中のsrc/tests/scripts/examples変更なし。GUI/Wineの新規実行なし。

合成カプセルの解析面積/回転体積、実FEMの寸法2倍でf半減・両RQ/G/TTF不変、
保存再構築/改変検出・未確認出力・不正設定/上書き拒否など追加7検査を実装した。
初回例題は長さ0.2 mから0.6 mへ変えた際のjoin_toleranceを流用して境界padding検査に失敗。
入力の許容差を1e-12 mと明示し、既存の許容差上限や判定は変更しなかった。
詳細と再現コマンドは[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md)。

例題はexamples/construction/capsule_request.json。実CLIの構築/書出/solveは
out/g03-capsule-construction-20260908.json、out/g03-capsule-case-20260908.json、
out/g03-capsule-solve-20260908。基本モード1170.098360 MHz。
これは合成例の動作/相似則検証であり、この形状の物理精度収束・旧版照合ではない。

次はGUIの候補表示/明示選択/保存/Case適用。厳密接点区間/弧端認証、直線と弧の接線、
フィレット、G03全要件照合は継続。全計画目標は未完了。
新規外部資料/コード/依存/旧資産の参照なし。


## G03有限弧数値判定と明示選択G1接続 — 2026-09-08

arc_tangents.pyへ有限有向弧の区間/枝判定、方向記録、明示選択の切詰め・局所G1接続APIを追加。
既存の支持曲線列挙を保持し、候補を勝手に選ばず、元曲線の中心/半軸/回転/枝を変えない。
弧端はガード付き未確認。fractionは数値推定であり、厳密な接点区間包囲ではない。
仕様・独立9検査と初回期待値の訂正理由は[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md)。

開始時310件中308合格・2 skip。追加後の独立全テストは、実行中にmodule docstringを
編集してStudyのソース変更検査1件が作動した。数値実装の変更ではないが失敗を保持する。
標準validate内の最終全319件中317合格・2 skip（85.826秒）、標準数値回帰PASS。
出力はout/validation-g03-finite-arcs-20260908、初回失敗はinitial_parallel_tests_source_changed.log。
seed_comparison.jsonで円筒6/成形セル3モードのcase hash一致、周波数差ゼロ、
RF/エネルギー相対差最大8.882e-16。ベンチマークは変更していない。GUI/Wineの新規実行なし。

次は構築要求/選択結果の保存・Case/CLI/GUI・閉輪郭検証への接続。
厳密な接点区間/弧端の認証、直線と弧の接線、フィレット、G03全要件照合は残る。
全33親課題の継続目標は未完。新規外部資料/コード/依存/旧資産の参照なし。


## 主要文書の現状同期 — 2026-09-08

製品基準e68002fにREADME・IMPLEMENTATION_STATUS・COMPATIBILITY_MATRIX/PLAN・BACKLOGと
曲線要素/物理仕様の入口を同期。現在の8親課題の限定受入とG03残件を冒頭に集約した。
以下の実装履歴は当時の記録として保持する。文書のみの変更で製品状態は変わらない。
標準310件中308合格・2 skip（85.808秒）を再確認。validate/GUI/Wineの新規実行なし。
次の実装は下節の有限弧制限・G1接続。全互換目標の新規開始/完了を意味しない。


## G03共通接線の四次式と接点再構成 — 2026-09-08

conic_tangents.supporting_conic_tangentsを追加し、[接線構築仕様](TANGENT_CONSTRUCTION.md)の
四次消去式を有理数で生成してSturm根分離へ接続した。
入力有限弧が属する円錐曲線全体を扱い、有限区間と双曲線の指定枝はまだ制限しない。
arc_filter_status=NOT_APPLIEDを返し、候補を自動選択/切詰め/Case化しない。

2つの法線座標表示で全方向を扱い、境界±1は第1表示へ割り当てる。
D=0の有理根を復元して、同じ法線に対応する2つの直線定数を保持する。
区間全体での負の接触二次式、厳密な無限遠接点を区別して除外する。
根分離/分母分離/座標再構成が未確認なら、その根区間と理由を残す。
同一円等の零消去式を「候補なしPASS」としない。

戻り値のfloat接点・法線・中心相対の直線定数を使って、陰関数・直線上の位置・
陰関数勾配との接線方向を再検査する。座標の桁落ちで接点を表せないケースもUNVERIFIED。
既定無次元残差1e-10を絶対位置誤差上界や元実数曲線の存在保証とは呼ばない。
接点距離の非有限値は拒否し、float接点の一致は出力精度での一致と明記する。

独立8検査: 円の4接線と既知距離、接触/交差/包含/同一円、回転/移動/尺度の楕円、
異なる半軸/回転と同中心の楕円、双曲線陰関数、漸近線、予算不足、座標精度不足。
最初はfixtureの一周弧/NumPy数値型が既存conics入力に拒否され、半周/Python数値型へ修正した。
conicsの入力制約を緩めていない。
最終標準310件中308合格・2 skip、対象8件PASS。
標準物理回帰validation-g03-conic-tangents-regression-20260908は返却値再検査強化前にPASS。
強化後は標準310件を再実行した。FEMソルバーの変更はない。

次は有限弧の区間/枝/進行方向による候補制限、明示許容差での切詰めとG1線分接続。
続いて候補選択/保存/CLI/GUI・閉輪郭の全体検査へ接続する。
円錐曲線全体の候補PASSを有限弧の接線構築完成とは扱わない。
既存R30/R31の数学を参照した独自実装であり、新規外部コード/旧資産の参照はない。
G03全体と全互換目標は継続。

## G03接線構築仕様と実根分離基盤 — 2026-09-08

[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md)で共通直線接線の候補列挙を仕様化。
有限有向弧、指定双曲線枝、複数候補の明示選択、元曲線非変更、ゼロ長接続/無限候補/
無限遠接点と候補なしの区別を定めた。曲率指定フィレット等を完了扱いにはしない。
中心とQ行列から接触条件を立て、2条件の消去による同次四次式を独自導出。
2つの法線座標表示で垂直接線を失わず、D=0・二乗の余分な根・元弧への制限を別処理する。
四次式の生成/接点再構成/候補選択/Case・CLI・GUI接続は未実装。

実装したのはpolynomial_roots.isolate_real_roots。
既存の有理数多項式係数規約を使い、除算/gcdで平方因子を除いてからSturm列で根数を数える。
閉入力区間の端点根は厳密点、非点の分離区間は開区間とする。
重根も異なる根として一度数え、予算不足時は未分離区間とその厳密根数を残す。
PASSは指定区間内の全根の分離と幅条件の達成を表し、係数の入力不確かさは対象外。
ゼロ多項式は無限根として拒否。予算は区間処理数の上限であり、演算時間上限ではない。

独立検査5件は既知有理根の積、複素因子、端点三重根、10^-40間隔の根、
係数の符号/尺度、±sqrt(2)、一点区間、入力拒否と予算不足時の根数保存。
標準302件中300合格・2 skip、validation-g03-tangent-roots-regression-20260908 PASS。
この基盤だけを接線自動構築の完成証拠にしない。次は四次式/接点再構成への接続。

新規参照R30は双対円錐曲線の接触条件、R31は端点を含むSturm根数と重根の扱い。
大学掲載のチュートリアルと著者公開論文を確認し、本文・コード・図の転記はない。
MIT講義のSturm節は未完成だったため、根数実装の根拠から除いた。
G03全体と全互換目標は継続。

## G03二次幾何近似の追加系列受入 — 2026-09-08

前回からのsession 24316を継続して確認し、exit 0で完了した。
out/validation-g03-native-geometry-separated-20260908/comparison.jsonはPASS。
対象は既存の合成楕円と双曲線、弦許容差倍率1,.0625,.015625の3段階。
各幾何段階で固定二次写像のFEM細分0→1を行い、全6比較がPASS。
面積/回転体積相対誤差の各段階での減少、最細各1e-5未満、最後の幾何近似間比較も全ゲートPASS。

| 対象 | 最細要素数 | 最細面積相対誤差 | 最細体積相対誤差 | 最後の周波数相対差 | 軸場L2相対差 | R/Q相対差 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 合成楕円 | 13452 | 1.2881e-8 | 1.9322e-8 | 1.0050e-7 | 6.3866e-6 | 1.0284e-5 |
| 合成双曲線 | 7684 | 5.7777e-10 | 1.1497e-9 | 4.0238e-8 | 7.2460e-6 | 3.5673e-6 |

磁場重なりは楕円0.999999999997、双曲線0.999999999968で同定PASS。
Q0、幾何因子、壁損失、通過時間係数、両R/Q定義の既存RFゲートもPASS。
周波数/軸場/RF閾値は1e-3/1e-2/1e-2の既存値から変更していない。
面積/体積は検証専用の直接積分式との照合であり、FEM解への解析式の代入はない。

初回倍率1,.25,.0625のFAILは
out/validation-g03-native-geometry-convergence-20260908/comparison.jsonへ保持する。
停滞/中間増加を丸めてPASSへ変更しない。
検証スクリプトの既定倍率を今回の受入系列へ変更し、旧系列は
--factors 1 .25 .0625で明示して再現できる。保存再検証と幾何間比較の開始ログも追加。
この変更は引数の既定とログのみ。受入計算は同じ倍率を明示して実行した結果であり、
物理計算/ゲートを変えていない。最終の--help実行でCLIを確認した。
前回の標準297件中295合格・2 skipを保持し、同じ数値ソルバーを再試験していない。

この受入は2つの合成例の3段階系列である。幾何間の場/RF差には残るFEM誤差も含む。
積分モーメントから局所境界最大誤差や物理ピーク誤差を保証しない。
物理ピーク収束はUNVERIFIED。次は接線の自動構築とG03全要件照合。
本節を最新状態とし、過去の実行中記録は履歴として残す。全互換目標は継続する。

## G03二次幾何近似の独立検証 — 2026-09-08

scripts/validate_curved_geometry_convergence.pyを追加した。合成楕円/双曲線の
弦許容差を3段階に変え、各段階で固定二次幾何のFEM細分0→1を行う。
各FEM比較は既存Studyの周波数/軸場/RF/同定閾値を使用し、形状近似間も
細分段数1の保存結果を比較する。形状間の場/RF差には残るFEM誤差も含む。

独立参照は例題を明示的に積分する。楕円は半軸a=.1、b=.08の上半面で
面積πab/2、回転体積4πab²/3。双曲線はr=a sqrt(1+(x/b)²)、
x=z−.05、a=.05、b=.08、−h<=x<=h、h=.05であり、
面積a[h sqrt(1+(h/b)²)+b asinh(h/b)]、体積πa²[2h+2h³/(3b²)]。
例題がこの参照と異なれば拒否し、式をソルバーには使用しない。
二次写像のdet Jと2πr det Jを各方向6点のGauss積分規則で積分して比較する。
これは多項式モーメントの検査であり、局所境界の最大誤差を保証しない。

受入条件は各段階のFEM PASS、面積/体積相対誤差の段階ごとの減少、
最細モーメント誤差各1e-5未満、最後の幾何近似間比較PASS。
--factorsは正・有限・厳密減少の3数を要求する。
初回の既定1,.25,.0625はout/validation-g03-native-geometry-convergence-20260908へ保存しFAIL。
楕円の最初の2段階は面積/体積誤差3.0930e-6/4.6374e-6で停滞した。
双曲線は中間で8.6724e-8/1.7258e-7から1.2283e-7/2.4445e-7へ増加した。
全段階のFEM比較と最後の幾何間比較、最細モーメント閾値はPASSだが、減少条件はFAIL。
弦許容差だけを細かくしても、メッシュ制御の分割により同じ二次境界になり得る。
初回結果を上書きせず、閾値を緩和せず、より細かい近似を含む1,.0625,.015625を追加実行する。

楕円初回0/1のPEC境界を元曲線の向きに揃えて照合した。
16辺の元曲線区間差は最大1.388e-17、節点座標差は最大3.470e-18 mであり、
ビット単位で同一ではないが、丸め誤差の範囲の変化しかない。
標準297件中295合格・2 skip。ソルバーの変更や受入閾値緩和はない。

追加系列の実行中記録（完了証拠ではない）:
コマンドは同スクリプト --factors 1 .0625 .015625
--out out/validation-g03-native-geometry-separated-20260908。
実行ハンドルはexec_command session 24316、ログ/tmp/g03-native-geometry-separated.log。
最後の確認で稼働中。楕円0/1はFEM PASS、モーメント誤差は
3.0930e-6/4.6374e-6から1.9348e-7/2.9019e-7へ減少。
楕円最細13,452要素のpoint-002保存は完了し、保存後の再検証/比較が進行中。
追加系列の総合合否は未確定。次の継続で同じハンドルをpollし、
完了していればcomparison.jsonを検査する。観測待ちだけを理由に再実行しない。
全互換目標を継続し、幾何近似収束を完了に変更しない。

## G03曲線鏡映GUI受入 — 2026-09-08

RF詳細へ鏡映結果の部分スペクトル表示を追加した。直線のreflection_source_caseと
曲線のreflection宣言を対象に、全空洞の固有周波数順位ではないことを明示する。
物理ピーク収束の未確認表示は保持する。

verify_gui.mjsに--curved-reflection yesを追加。
--contour-case examples/curved_hyperbola.json --contour-auto yes --curved-fem yesと併用し、
双曲線の左右端×電気/磁気対称の4入力を検証出力先へ生成してファイル読込する。
各入力で鏡映チェックボックスを実クリックし、計算・保存結果選択・描画まで操作する。
保存された面と偶奇、全Caseの規格化2倍、RFの蓄積エネルギー、部分スペクトル文を検査する。
既存の入力/往復/曲線P2/固定Study7操作に加え、計11操作がPASS。

out/gui-curved-reflection-accepted-20260908/report.jsonはpassed=true、
source_changed_during_run=false、external_requests=[]。
curved-reflection.pngで角診断、物理ピーク未確認、部分スペクトルの日本語説明、
U=2 J（電気/磁気各1 J）を確認した。検証後にGUIサーバーを停止。
標準297件中295合格・2 skip。JavaScript構文検査もPASS。
数値ソルバーや受入閾値の変更はない。

次は二次曲線の幾何近似収束と接線構築の要件照合。
曲線鏡映GUIの限定操作を受入済みとして更新するが、G03全体と全互換目標は継続する。

## G03楕円/双曲線の固定幾何FEM・双曲線鏡映/GUI — 2026-09-08

scripts/validate_curved_shapes.pyを追加し、既存の合成楕円と双曲線をgeometry_order=2、
quadrature_order=12で通常Studyへ渡す。固定二次幾何の細分段数0→1を比較し、
周波数、磁場の同定、軸場L2、RFを既存閾値で評価する。
out/validation-g03-additional-native-shapes-20260908/comparison.jsonはPASS。
楕円は周波数相対差9.2214e-7、軸場L2差1.0679e-4、R/Q相対差4.8770e-4。
双曲線は周波数相対差1.9776e-6、軸場L2差2.7972e-4、R/Q相対差4.3213e-4。
磁場重なりはそれぞれ0.9999999980と0.9999999887。同定/周波数/軸場/RF全ゲートPASS。
これは固定二次境界に対するFEM細分の比較であり、元解析曲線への幾何近似収束は評価しない。

双曲線の左右端をそれぞれ電気/磁気対称として、通常solve→reflect_solution→save→readを実行。
4条件すべてで全領域残差・場の偶奇性・エネルギー/壁損失2倍の不変量がPASS。
最大残差5.1186e-14、場の偶奇相対差6.1084e-12、2倍からの相対差5.3291e-15。
端で鏡映した双曲線の壁には元の曲線接線に応じた角があり、保存した角診断を保持する。
物理ピークの収束はUNVERIFIED。有限の離散極値や小さな残差を物理ピーク認証に読み替えない。

実ブラウザーはverify_gui.mjs --contour-case examples/curved_hyperbola.json
--contour-auto yes --curved-fem yesで7操作PASS。
out/gui-curved-hyperbola-native-accepted-20260908/report.jsonは
source_changed_during_run=false、external_requests=[]。
双曲線の入力/自動メッシュ/保存往復、二次幾何・積分次数12・細分段数1、
固定幾何Study 0→1とその場の表示を操作した。GUIでの鏡映チェックボックスは今回の7操作には含まない。
curved-controls.pngとfixed-study.pngで設定値とStudy PASS/結果表を画像確認。
検証後にローカルGUIサーバーを停止。標準297件中295合格・2 skip。
今回の変更は検証スクリプトと文書であり、数値ソルバーの変更や閾値緩和はない。

次は二次曲線の幾何近似収束、曲線鏡映のGUI操作、接線構築の要件照合。
G03全体の受入は未完で、全32項目/33親課題の目標を維持する。

## G03曲線鏡映の通常API・保存・CLI接続 — 2026-09-08

reflect_solutionはgeometry_order=2の曲線解を固定写像で鏡映する。
入力Caseと解の一致を要求し、全領域の残差と正規化/直交性を再確認する。
固有値の再計算や振幅再調整はない。元の半領域係数を偶奇に従って移し、
全領域Caseのnormalization_jは2倍。mode indexは偶奇部分スペクトルの順序である。
既存のreflected_acceleration_parametersによりユーザー指定の加速長、電圧積分区間、
位相原点も変換する。両端面と両対称タグの保存往復で非既定値を検証した。

保存results.reflection第1版は元Case、面、偶奇、固定写像再構成と振幅の契約を保持する。
mesh.jsonは半領域の元弦メッシュであり、results.mesh.sourceにその用途を明記する。
再読込は元Case+弦メッシュから二次写像と固定細分を再構成した後に鏡映し、
導出した全Caseと保存Caseを照合する。幾何配列の完全照合、係数の偶奇完全照合、
全領域残差、エネルギー規格化、全RF値の再検査を実施する。
直解と鏡映のfield_constructionも厳密照合する。未知の版、面/偶奇/元Case改変、
宣言削除、構成表示の偽装、係数改変はhash更新後も拒否する。
再読込した鏡映解の再保存も可能。既存の直解の保存形式は維持する。

新規tests/test_curved_reflection_saved.pyの4検査は左右×電気/磁気対称の保存/再保存、
再固有値計算の禁止、正規化/場の一致、7種の改変拒否、CLI --reflect-full、
Case不一致と二重鏡映の拒否を含む。
標準297件中295合格・2 skip、validation-g03-reflection-integration-regression-20260908 PASS。
scripts/validate_curved_reflection.pyは通常APIの鏡映をsave/readした結果で物理不変量を検証する形へ更新。
out/validation-g03-curved-reflection-storage-20260908/comparison.jsonの合成半球4ケースはPASS。
最大残差8.695e-14、場の偶奇相対差1.350e-12、エネルギー/壁損失の2倍からの相対差1.433e-14。
周波数値を移したことと全方程式の残差は確認したが、これを物理的な離散化誤差の認証とは扱わない。

保存結果のplot CLIも実行。初回画像は曲線鏡映の部分スペクトル注記が欠けていたため、
visualizeの既存直線鏡映判定を曲線のreflection宣言にも対応させた。
同じ保存結果からreflected-plot-final.pngを出力し、全曲線形状・場・軸/半径プローブ、
U=2 J、部分スペクトルで全固有値順位ではない注記を画像で確認した。
図の修正は標準検査後であり、最終plot CLI実行と画像で確認した。
GUIブラウザー操作は今回未実行。追加形状、GUIを含むG03全要件の照合は次の作業。
物理的な角ピークの収束は引き続きUNVERIFIED。G03全体と全互換目標は継続。

## G03固定二次空間の鏡映核 — 2026-09-08

curved_reflection.reflect_curved_spaceは元の二次写像を鏡映し、対称面の節点を
境界の接続情報で共有する。全要素の向きを保つため局所節点を0,2,1,5,4,3へ並べ替える。
元曲線を再投影せず、固定細分済み空間にも適用する。元曲線の番号と区間は
CurvedContour.reflectedの全輪郭へ写し、鏡映側の曲線パラメータは1−tとなる。
全辺の交差/共有接続、境界閉鎖、全要素Jacobianを既存の検査で再確認する。

係数写像は電気対称で偶、磁気対称で奇。applyは磁気面の非零係数、
不一致の節点数、非有限値を拒否する。場ではHphiとEzがこの偶奇、Erが逆の偶奇となる。
独立不変量は変換行列Pに対するP^T K_full P=2 K_halfと
P^T M_full P=2 M_half（磁気の場合は半領域の自由空間へ制限）、
物理座標と勾配の鏡映則。左右の面、両対称タグ、固定細分段数1で確認した。

最初の右端面検査は細分の浮動小数点評価による約1.4e-17 mの座標差で失敗した。
面は座標の完全一致で探索せず、タグ付き境界の節点を使う。
512 eps×領域寸法以内の面座標だけ丸め誤差として揃える。実際のずれ1e-8 mは拒否する。
軸辺の中点もRFの厳密なアフィン軸規約へ揃える。
既存の親空間や保存結果は変更しない。写像/勾配/行列不変量の許容差緩和はない。

scripts/validate_curved_reflection.py --out out/validation-g03-fixed-curved-reflection-20260908
は合成半球の左右×電気/磁気対称4ケースを計算し、全領域では固有値を再計算せず係数を移す。
全領域残差最大8.695e-14、場の偶奇相対差最大1.350e-12、
電気/磁気/総エネルギーと壁損失の2倍からの相対差最大1.433e-14でPASS。
これは半球メッシュの物理的離散化誤差や表面ピーク収束の認証ではない。
開始時289件中287合格・2 skip。変更後293件中291合格・2 skip。
最後に行列全体の不変量も追加し、対象4件PASS。
validation-g03-reflection-core-regression-20260908もPASS。

通常reflect_solutionは曲線解をまだ拒否する。保存・CLIへの接続は次の必須作業。
半領域Caseと元弦メッシュ、細分段数、鏡映版/面/偶奇を保存し、再読込では
半領域の二次空間を再構成して同じ鏡映を行ってから、全Case・幾何配列・係数・RFを照合する。
全Caseからの再メッシュでは元写像を再現できないため使用しない。
規格化は半領域の2倍、モード番号は偶奇で選ばれた部分スペクトルと明記する。
未実装の保存経路をPASSとは扱わない。G03全体と全互換目標は継続。

## G03元曲線の角診断と保存第2版 — 2026-09-08

curved_corners.classify_curve_joinsは元の解析曲線の接続点を対象とし、メッシュ細分の
継ぎ目を角に数えない。正向き(z,r)輪郭の接線から符号付き旋回角を求め、
軸外のPEC同士では真空内角=π−旋回角として凸角/再入角を分類する。
軸接続、異種境界接続、非PEC同士は分け、平面の角として物理性を推定しない。
角度許容差は1e-8 rad。許容差内の接線一致は厳密な滑らかさの証明ではない。
端点位置と接続隙間、曲線番号、タグ、角度、分類を保持する。
この診断は幾何学的な注意箇所の識別であり、モード固有の発散/有限性を断定しない。
physical_peak_statusはUNVERIFIED。再入角は専用のピーク収束評価を必要とする。

新規results.surface_extremaはversion=2、corner_diagnostics_version=1を持ち、
surface_corner_diagnosticsを必須とする。読込時は元Caseから再計算して照合する。
第1版と宣言なしの旧結果を保持。旧版に後付けした診断も、存在するなら常に再検証する。
診断欠落や物理ピーク状態をPASSへ変えたデータは、hash更新後も拒否する。
第1版の実保存結果validation-g03-peak-rf-surface-final-20260908/level-1も再読込確認。
GUIのRF詳細へ分類数と物理ピーク収束未確認を追加。旧結果の未提供欄は未評価と表示する。

独立検査は段差の270度再入角・凸角数、1e-5/1/1e5寸法倍率、曲線分割による角数不変、
球の軸接続と異種境界接続。最初の混合タグfixtureは内側の線へ対称タグを指定して拒否されたため、
既存契約どおり端面のタグへ修正した。境界契約の緩和はない。
scripts/validate_curved_corners.py --out out/validation-g03-native-corner-diagnostics-20260908
は同じ段差の段数0/1をsolve/save/readし、各270度診断と保存整合がPASS。
周波数相対変化1.00935e-3、離散Eピーク比1.0735116を観測。
これは周波数/物理ピークの収束PASSではなく、physical_peak_status=UNVERIFIEDを保持する。
標準289件中287合格・2 skip、validation-g03-corner-diagnostics-regression-20260908 PASS。
最終の旧版後付け診断の検証強化は保存関連8件で確認。

最終GUI検証out/gui-curved-corners-final-20260908/report.jsonは7項目PASS、
source_changed_during_run=false、external_requests=[]。
RF詳細の角診断文はDOM検査で確認した。corner-diagnostics.pngは詳細表の中央を撮影しており、
診断文自体は画面外のため、その文の視覚確認証拠には使わない。
画像ではRF値と未評価表示を確認。検証後にローカルGUIサーバーを停止した。

次は曲線鏡映と追加形状の総合受入。物理的な角の有限ピークを認証したとは扱わない。

## G03連続離散ピークのRF/保存/GUI接続 — 2026-09-08

quantities_curvedは既定で連続離散ピークの上下界を計算する。
E/Hの下界と上界を別の数値欄に出し、共通のEpk/Bpk推定値欄には上界を使う。
Epk/EaccとBpk/Eaccも上界から計算し、|Vacc|<=1e-12*絶対軸積分の場合はNone。
peak_statusは物理的な角とメッシュ収束の未認証を明記し、離散極値PASSと混同しない。

新規保存results.surface_extremaはversion=1、厳密有理数Bernstein方式、相対幅1e-6、
辺あたり区間上限10000、PEC閉辺/片側微分、上界を推定値に使う契約を持つ。
readは宣言を型を含め厳密照合し、保存係数からピークを再計算して全RF欄と照合する。
宣言を除去して新しいピーク欄だけ残したデータや、hashを再生成したピーク改変も拒否する。
宣言なしの旧曲線結果はinclude_surface_peaks=Falseの従来RF契約で再検証し、元の未評価を保持。
旧実出力validation-g03-native-storage-20260908/runの読込も確認した。
将来評価方式を変更するときは版を分け、既存版の再検証を維持する。

GUIのRF詳細に離散E/Hピークの上下界名を追加し、共通EpkラベルのP1限定表記を修正。
Studyはピーク数値の存在と物理収束の受入を分け、表面収束を判定していないと表示する。
テストは旧保存形式、評価版/値の改変拒否、U×4→ピーク場×2・Epk/Eacc不変、
一定軸場の位相相殺によるピーク比未定義を検査する。

標準285件中283合格・2 skip、validation-g03-peak-rf-regression-20260908 PASS。
validation-g03-peak-rf-surface-final-20260908/comparison.jsonの球形表面/連続極値は両段階PASS。
新規保存の段数1はE最大[8729690.67140714,8729694.094318945] V/m、Epk/Eacc上界推定1.8812138684。
従来の周波数/体積場/RF積分の許容差と基準結果は変更なし。
out/gui-curved-peak-accepted-20260908/report.jsonは実ブラウザー7検査PASS。
評価版・有限なピーク比・物理未認証表示を確認。外部通信0、実行中ソース変更なし。
ブラウザーとGUIサーバーは終了済み。
次は物理的な角の扱い、曲線鏡映、追加形状の総合受入。G03と全互換目標は継続。

## G03離散曲線場の連続極値上界 — 2026-09-08

rational_bounds.bound_rational_normは[0,1]上のsqrt(ΣN_i²)/D、D>0を上下から囲む。
係数は昇べき順。入力floatはその二進値を厳密なFractionへ変換し、以後の多項式演算、
Bernstein変換・次数上げ・中点de Casteljau分割と上界比較は有理数で行う。
ΣN_i²とD²を同じBernstein次数に揃え、D²の全係数が正なら係数比の最大が上界。
これは商を正の重み付き平均で表せることによる。D²の正値と端点D>0から符号を保持する。
正値を囲めない区間は分割し、評価点でD<=0なら拒否する。

端点/中点の厳密値を下界候補とし、最大上界の区間から分割する。
既定相対幅1e-6、生成区間予算10000。予算不足はUNVERIFIED。
戻り値の平方根floatは、二乗をFractionで比較して外向きに丸める。
二乗値がdouble範囲外でもノルムを出力できるよう2の冪で正規化する。
外向き丸めで幅を超えれば追加分割し、厳密最大値自体のfloat幅が不足ならUNVERIFIED。
下界を得たパラメータはfloatと厳密分数を保持する。

curved_extrema.edge_field_polynomialsは保存された6節点/係数から式を直接作る。
H=r*uは4次。Er/Ezは4次以下の分子とomega*epsilon*det(J)の分母からなる。
曲線境界の向きと物理勾配を既存CurvedSurfaceSamplerに照合した。
bound_surface_peaksは全PEC辺を閉区間として評価し、全下界/上界の最大を返す。
返す辺番号と点は下界の評価位置であり、一意な最大点の証明ではない。
角の各セル側を保持する。PASSは保存された離散場の連続極値の囲い込みを意味し、
物理的ピークのメッシュ収束や角特異性の解消を意味しない。
通常RF/保存のpeak_statusはまだ変更していない。

独立検査: 33等間隔点が最大値の1/1000未満しか拾わない狭い有理ピーク、
端点/内部/ベクトル/ゼロ、分母の内部ゼロ、1e-300/1e300尺度、予算/出力精度不足。
一定uでH最大=.08 m相当、E一定=2/(omega*epsilon)の既知値も囲む。
楕円の全辺で有理式と直接の物理勾配評価が一致し、65点/辺のサンプルも上界内。

out/validation-g03-continuous-extrema-20260908/comparison.jsonは保存後の球形段数0/1でPASS。
段数1のE最大は[8729690.67140714,8729694.094318945] V/m、
H最大は[31789.659659353736,31789.678147827413] A/m。
E/Hの区間全体と独立球形の厳密最大との差は各2.58738e-5、3.28173e-6以内（ゲート1%）。
各辺で相対幅1e-6以内。段数1の生成区間数はE合計64、H合計60。
再現: scripts/validate_curved_surface.py --out <新規ディレクトリ>。
標準282件中280合格・2 skip、validation-g03-continuous-extrema-regression-20260908 PASS。
最後のfloat幅停止条件の調整は関連7検査で確認した。
次は通常RF/保存再読込/GUIへの版付き接続と物理的な角の扱い。曲線鏡映も継続。

## G03曲線表面場の片側評価 — 2026-09-08

curved_surface.CurvedSurfaceSamplerが境界辺の唯一の隣接セルを求め、二次写像上で
Hφ、Er/Ez、外向き法線/接線、En/Et、|E|と弧長微分を評価する。
パラメータは保存辺の端点順。接線は正のJacobianを持つセルの反時計回り順で、
外向き法線(r,z)=(t_z,-t_r)。保存辺の順序を反転しても法線は反転しない。
角/共有節点は各隣接境界セルの微分を保持し、平滑化や平均化をしない。

sampled_surface_summaryはPEC辺だけを対象に、各辺の端点を含む等間隔サンプルの
最大|E|/|Hφ|/|Et|、位置、辺番号、パラメータを返す。既定17点/辺。
返却statusに有限サンプルの推定と明記し、連続境界の極値や収束を保証しない。
通常RFのpeak_statusは引き続き未評価。サンプル推定を従来のピーク欄へ代入しない。

独立検査は物理線形u=1+2r+3zの表面射影、凸楕円の外向き法線、辺順序反転、
乱数係数での節点片側微分の不連続保持、strict引数とPEC限定を使う。
scripts/validate_curved_surface.py --out out/validation-g03-curved-surface-traces-20260908
は球形R=.08 m、二次幾何/場、固定幾何段数0/1を通常solve/save/read後に比較する。
壁面の8点Gauss×2πr dsで電磁場の相対L2を評価し、33点/辺で最大サンプル値を比較。
球形参照は表面|E|∝|cosθ|、|Hφ|∝sinθより極/赤道に厳密な最大値を持つ。
参照E最大8.72991655 MV/m、H最大31789.764 A/m。各誤差ゲートは1%。

| 相対量 | 段数0 | 段数1 |
|---|---:|---:|
| 表面電場L2 | 5.40773e-3 | 1.51948e-3 |
| 表面磁場L2 | 4.29670e-5 | 5.54276e-6 |
| 最大Eサンプルと厳密最大の差 | 4.00616e-4 | 2.58738e-5 |
| 最大Hサンプルと厳密最大の差 | 2.90061e-5 | 3.28173e-6 |
| 最大Etサンプル / 参照E最大 | 6.82912e-3 | 1.84038e-3 |

標準275件中273合格・2 skip、validation-g03-surface-traces-regression-20260908 PASS。
全ゲートPASS。実際の二次壁は解析球面の近似であり、接線成分には幾何近似の影響も含む。
この比較は体積場/周波数/RF積分と独立した表面検査で、連続極値の探索受入とは別。
次は連続境界の極値の上界/停止条件と角の扱いを実装し、通常RF/保存/GUIへ接続する。
曲線鏡映と追加形状の総合受入も継続する。

## G03曲線計算設定と固定幾何StudyのGUI — 2026-09-08

曲線入力に計算形状（弦/二次）、体積積分次数、固定幾何の細分段数を追加。
弦を選択中は積分次数/段数を無効化し、二次を選択すると通常Caseへ明示する。
固定幾何Studyを操作一覧へ追加し、既定の比較段数は0,1。
通常のメッシュ細分では二次境界も変わり得ることを説明する。
曲線ピーク未計算の表セルはNaNではなく未評価と表示する。
プレビューは初期分割用の弦であり、選択した二次計算形状とは区別して説明する。

verify_gui.mjs --contour-case examples/curved_ellipse.json --contour-auto yes --curved-fem yes
で通常の入力・エラー保持、曲線設定編集、計算/描画、書出し往復、固定幾何Studyを検査。
対象は合成楕円、幾何次数2、体積積分12、段数1、元メッシュ最大辺長.02 m。
最初の検証は追加ヘルパーのスコープ不具合で停止。修正後の7検査はPASS。
その画面で見つけた旧説明「曲線FEMではありません」を修正。
out/gui-curved-native-accepted-20260908/report.jsonの最終7検査もPASS。
外部通信0、実行中のソース変更なし。curved-controls.png / fixed-study.pngを目視確認。
GUIで実行した固定幾何Studyは520→2080要素、周波数/軸/RF比較PASS。
ブラウザーとローカルGUIサーバーは終了済み。
最初の失敗/中間成功の記録はgui-curved-native-check-20260908 / gui-curved-native-check-final-20260908に保持。
標準271件中269合格・2 skip。今回はUIと検証スクリプトの変更でFEM/RF数式の変更なし。
曲線表面ピーク・鏡映・追加形状を含む総合受入は継続。

## G03固定幾何細分の通常経路 — 2026-09-08

v3 mesh.curved_refinement_levelsを追加。非負整数、既定0、省略時は従来JSONを保持。
明示JSON指定はgeometry_order=2のみ。case_curved_spaceをsolveとreadで共用し、
元メッシュから初期二次幾何を作って指定回数の制限細分を行う。
各段の生成前に4倍後の要素数をcontour_mesh.max_trianglesで検査する。
外部元メッシュでcontour_meshなしの場合の上限は250000。超過は拒否し自動変更しない。
軸子中点は端点平均で表現し、RFの厳密なアフィン軸条件を保持する。

保存は細分段数をCase/field_spaceへ記録し、元弦メッシュを保持する。
readは同じ段数を再構成して全配列・残差/正規化/RFを照合する。
細分後は元弦からの移動量配列を出さず、元曲線パラメータを祖先区間と明記。
段数0の既存保存形式と読込を維持する。

Studyの新種別fixed_geometry_convergenceは
parameter=/case/mesh/curved_refinement_levels、values=[0,1]などの増加非負整数を受け取る。
元メッシュを再読込して点間の完全一致を検査し、固定した二次幾何の比較と記録する。
従来mesh_convergenceの境界再投影を含む比較とは区別する。
GUIフォームは段数を保持するが、選択UIと実ブラウザー受入は次段階。

scripts/validate_curved_study.py --fixed-geometry --out out/validation-g03-fixed-native-study-20260908
で球形段数0→1の保存後比較PASS。元メッシュhash一致、周波数1.6363983269→1.6363973727 GHz。
独立球形参照への相対誤差は周波数9.33016e-7→3.49885e-7、R/Q 2.01474e-4→2.33410e-5。
磁場重なり0.9999999975、軸差2.14213e-4、RFと周波数の全ゲートPASS。
これは当該2段階の検証であり任意形状/任意段数の収束を保証しない。
標準271件中269合格・2 skip、validation-g03-fixed-native-regression-20260908 PASS。
次は曲線GUIの入力/Study/表示の実操作、表面ピークと鏡映。G03と全互換目標は継続。

## G03固定二次幾何の空間細分 — 2026-09-08

curved_refinement.refine_curved_spaceで全参照三角形を4分割し、親写像を子へ制限する。
共有節点は位相上の辺IDで同定し、共有点座標と親係数への補間行の一致を検査する。
親の全P2節点は子の頂点として保持。子中点は親写像で評価し、解析曲線へ再投影しない。
境界タグ・元曲線番号・パラメータ区間を継承し、全子Jacobian・境界・全辺を再検査。
元曲線パラメータは祖先区間の記録であり、解析曲線上への点配置を意味しない。

戻り値はCurvedRefinement(space, prolongation, parent_cells, parent_reference_vertices)。
prolongationは親uを同一の物理場として細分空間へ移す疎行列P。
RestrictedGeometryは元弦からの移動量を捏造せず、既存の再投影候補と別の幾何型を使う。
このAPIは空間/行列の段階。通常Case/solve/save/read/Studyの細分段数接続は未実装。

楕円360→1440要素で写像、ランダムP2場と物理勾配の一致を検証。
境界1/4点が親の二次補間と一致し、解析曲線への再投影点とは異なることを確認。
直線対照の2回細分では軸r=0と磁気対称拘束を厳密に保持。
P^T K_child PとK_parentの相対行列差は積分次数8で1.85819e-11、12で2.29779e-15。
質量行列差は各1.53e-15、1.21e-15。各ゲート1e-10でPASS。
これは同じ場のエネルギー保存の検査であり、固有周波数やRFの離散化誤差の受入ではない。
再現: scripts/validate_fixed_curved_refinement.py --out out/validation-g03-fixed-curved-refinement-20260908。
validation-g03-fixed-curved-refinement-regression-20260908 PASS。
標準268件中266合格・2 skip。通常solve/保存/Studyへの接続と独立物理収束を次に行う。
GUI・表面ピーク・鏡映を含めG03と全互換目標は継続。

## G03曲線Studyの保存比較 — 2026-09-08

compare_refinementを曲線保存解へ接続。最初のメッシュの参照重心を物理座標へ写し、
Jacobian×半径の重みと両解の共通領域で磁場の重なりを評価する。
軸は曲線空間の軸自由度を使い、両軸節点の和集合で区間分割して3点Gauss積分。
積分次数は物理同一性判定から除外するが、betaなど実際の物理/RF条件は保持する。
表面ピークは未評価と明記する。

曲線境界節点を各再メッシュで解析曲線へ置くため、mesh_scaleの変更でも
二次境界自体が変わり得る。これは同じ解析形状の離散化比較であり、
離散幾何を固定したFEM誤差推定とは扱わない。固定二次写像のh細分は残件。

scripts/validate_curved_study.py --out out/validation-g03-native-curved-study-20260908
は球形R=.08 m、幾何/場次数2、弦許容差.0008 m、最大辺長.02→.01 m。
保存後の比較312点、磁場重なり0.9999999977、軸差2.13699e-4、全比較ゲートPASS。
独立球形参照に対する周波数誤差9.33016e-7→5.81020e-8、
R/Q誤差2.01474e-4→1.51583e-5。両段階の全RFゲートもPASS。
最初の出力名は既存ディレクトリのため拒否され、新規名で実行。既存結果は未変更。
標準264件中262合格・2 skip、validation-g03-curved-study-regression-20260908 PASS。
次は固定離散幾何の細分・GUI・表面ピーク・鏡映。G03/全目標は継続。

## G03曲線保存プローブと描画 — 2026-09-08

曲線境界をzの極値で単調区間へ分け、二分法で半径プローブの外側交点を計算。
膨らみ・折返しの複数交点・接点・同一平面内の半径極値を検証。
保存CSVプローブとplotを接続し、領域の隙間は曲線逆写像のinside/NaNを保持。
境界線は各二次辺17点、色/等高線は既存の4直線表示三角形による近似。
球形保存解の実描画 out/g03-curved-sphere-plot-20260908.png を目視確認。
標準261件中259合格・2 skip。その後追加の保存プローブを含む5件も合格。
validation-g03-curved-queries-20260908 PASS。FEM/RFの数式・係数・許容差は変更なし。
次は曲線解のStudy/GUI経路と表面ピーク・鏡映。G03/全互換目標は継続。

## G03通常曲線Caseと保存往復 — 2026-09-08

v3 mesh.geometry_order=2 / solver.element_order=2 / quadrature_order既定8を追加。
通常solve・RF・FieldSamplerへ接続。curved_saved.pyで元メッシュ/全曲線配列保存と
空間再構成・幾何照合・K/M再組立て・正規化/残差/RF照合。固有値再計算なし。
VTKは4直線表示三角形、計算用曲線幾何はNPZ。保存完了/上書き禁止を継承。
GUIフォーム次数保持のみ追加、実ブラウザー未検証。plot/鏡映は明示的に未対応拒否。
標準259件中257合格・2 skip、validation-g03-native-storage-regression-20260908 PASS。
validation-g03-native-storage-20260908/comparison.jsonは保存後の球形全ゲートPASS。
次は曲線解の描画/保存プローブ/Study/GUIと表面ピーク・鏡映。G03/全目標継続。

## G03曲線物理座標プローブ — 2026-09-08

curved_sampling.QuadraticLocator/CurvedFieldSamplerで物理座標から逆写像。
減衰Newton＋参照三角形4分割のBezier包絡。外部証明時だけNone/NaN、予算不足はUNVERIFIED。
曲線の膨らみ・境界/軸/寸法変換と楕円10要素の場一致を検証。
out/validation-g03-curved-probe-final-20260908/comparison.jsonは球形物理点/全軸/既存RF等PASS。
物理点H誤差6.26e-5、E誤差1.15e-3、軸Ez2.14e-4。
標準255件中253合格・2 skip、validation-g03-probe-regression-20260908 PASS。
次は通常Case幾何次数と入力/保存/再読込。ピーク/鏡映/Study/GUIも残り、全目標継続。

## G03曲線RF積分 — 2026-09-08

curved_rfに壁H²弧長積分、軸P2電圧、Q0/G/RQ等を接続。
PECのみ損失、R01 overrides保持。軸中点は端点平均との完全一致を要求。
直線3境界条件と部分電圧/位相設定、独立円柱壁積分を検証。
out/validation-g03-curved-rf-final-20260908/comparison.jsonは球形全RFゲートPASS。
R/Q誤差2.01e-4、壁損失7.19e-6、壁積分8/12差2.22e-16。
標準252件中250合格・2 skip、validate PASS。
次は物理座標逆写像/プローブと通常入力/保存/再読込。ピーク/鏡映/Study/GUIも残る。
G03と全互換目標は継続。

## G03曲線解と体積場 — 2026-09-08

curved_solution.solve_curvedで昇順固有値・残差・質量直交性・指定Uを接続。
fields_in_cellは参照座標を受け、曲線写像の物理勾配からH/Er/Ezを評価。
直線3境界条件との一致、曲線上の物理線形場を検証。
validate_curved_fields.py: out/validation-g03-curved-fields-final-20260908/comparison.json PASS。
球形H誤差7.27e-5、E誤差1.12e-3、各エネルギー0.5 J。
標準250件中248合格・2 skip、validation-g03-curved-solution-20260908 PASS。
次は曲線壁/軸RF・物理座標逆写像、通常入力/保存/再読込/GUI。G03/全互換目標は継続。

## G03全体曲線空間/行列 — 2026-09-08

curved_space.CurvedSpaceへ共有/向き/境界incidence/連結/Euler=1を集約。
内部を含む全二次辺の交差を凸包候補＋既存離隔検査で確認。
assemble_curvedで局所行列をCSR化。直線P2との一致・破損/内部交差拒否を検証。
validate_curved_space.py: out/validation-g03-global-curved-space-20260908/comparison.json PASS。
球形周波数誤差9.33e-7、積分次数8/12差約6e-15。場/RF精度とは別の限定受入。
標準248件中246合格・2 skip、validation-g03-space-regression-20260908 PASS。
次は曲線解の正規化・場・RFと入力/保存/再読込。G03/全互換目標は継続。

## G03二次境界の検査 — 2026-09-08

quadratic_boundaryで二次Bezier境界の単一閉サイクル・折返し・全辺対離隔を検査。
隣接辺は共有点近傍の単調投影と残区間対の分割検査。丸め/予算未確定はUNVERIFIED。
楕円32辺/双曲線28辺PASS。端点が単純でも曲線交差する例と隣接辺の再交差を拒否。
共有候補の最後へ接続しboundary_checkを保持。
次は元の円板位相・共有辺・全域Jacobian・単純境界を集約した全体空間と行列。
標準245件中243合格・2 skip、validation-g03-boundary-final-20260908 PASS。
G03の製品solve/保存/場/RFと全互換目標は継続。

## G03共有二次幾何候補 — 2026-09-08

弦ごとの元曲線fraction区間を追加し始点回転/保存へ保持。
curved_mesh.curve_geometry_candidateで境界頂点/共有辺中点を元曲線へ移動。
内部点保持、共有整合/軸固定、全要素Jacobian/半径検査。独立面積/体積が弦誤差の1/10未満。
双曲線の粗い弦4 mm/細かい辺5 mmは要素89で曲線化反転を拒否し、元メッシュ不変。
JacobianはBernstein下界で先に判定し、下界不十分時だけ極値候補を検査。
次は全体二次境界の交差/適合性と全体空間/行列。候補型はsolve/保存済み解へ未接続。
標準240件中238合格・2 skip、validation-g03-shared-geometry-20260908 PASS。
G03と全互換目標は継続。

## G03二次写像と局所行列 — 2026-09-08

quadratic_geometry.QuadraticTriangleで6節点写像と全域det J最小値候補を検査。
節点だけ正の反転反例を拒否し、面積/回転体体積/物理勾配を検証。
curved_fem.mapped_element_matricesで局所P2行列を積分、一定/線形場と直線極限を検証。
CURVED_ELEMENTS.mdへ全体共有性/入力/保存/場/RF/Study/GUIの未接続契約を記録。
次は元曲線パラメータ区間と共有二次幾何節点・全体適合性。
標準237件中235合格・2 skip、validation-g03-quadratic-map-20260908 PASS。
局所コアのみでG03/全互換目標は未完、継続。

## G03球形の独立電磁場参照 — 2026-09-08

analytic_sphere.SphereTMで球形PECの正則l=1,m=0 TM参照を独立実装。
DLMF R28の関数定義からPEC条件/正規化/RFを導出。中心/接線場/2Dエネルギー/有限差分curlを検証。
validate_sphere.py: out/validation-g03-sphere-reference-20260908/comparison.json。
弦0.8/0.2 mmはFAIL、0.05 mmはf/場/軸/RQ/G/壁損失の全ゲートPASS。
標準230件中228合格・2 skip、既存validate PASS。次は曲線要素写像と正Jacobian/積分/場/RF/保存の設計。
接線構築/旧形式対応と全互換目標も継続。

## G03双曲線の総合経路 — 2026-09-08

双曲線例curved_hyperbola.jsonを追加。独立z積分の面積/体積、弦体積差の正符号/減少、
両端×電気/磁気4鏡映・別全領域solve・保存再読込、寸法3倍のf/RQ/G/TTF不変量を検証。
直角rotationを完全一致時のみ座標入替えとして扱い、接続の丸め誤差を修正。
幾何/FEM最終比較PASS: out/validation-g03-hyperbola-refinement-20260908/summary.json。
実ブラウザー5検査PASS: out/gui-g03-hyperbola-browser-20260908/report.json。
標準226件中224合格・2 skip、validate PASS。
次は独立の電磁場参照と曲線FEM設計/実装。接線構築/旧形式対応と全互換目標も継続。

## G03メッシュ停滞解消と独立細分 — 2026-09-08

低品質内点に8方向×4段階の候補を追加し、平均位置で停滞する独立矩形扇を検証。
境界/正面積/面積/回転体体積/サイズ制約を保持。楕円の品質停滞を解消。
out/validation-g03-directional-smoothing-20260908/summary.jsonは幾何/FEM最終比較PASS。
幾何の粗い比較はFAILを保持。最細メッシュ29007三角形・最小角10.1878度。
標準222件中220合格・2 skip、validation-g03-directional-regression-20260908 PASS。
次は双曲線等の総合受入と独立の電磁場参照、曲線FEM/接線構築/旧形式対応。
G03と全互換目標は継続。

## G03メッシュ停滞の切分け — 2026-09-08

対角線交換に明示max_edge_mを追加し、サイズ内の長くなる交換を許可。
独立四角形で角度10.49→24.78、面積/体積/境界不変。品質生成へ接続。
標準221件中219合格・2 skip、validate PASS。
out/validation-g03-bounded-flips-20260908/summary.jsonはFEM PASS、幾何列は依然品質FAIL。
1反復後の最悪三角形は軸上2点とr=.0002188 mの内点。次は内点移動候補を切分ける。
G03と全互換目標は継続。

## G03の独立細分列 — 2026-09-08

幾何/FEM独立列をscripts/validate_curved_refinement.pyで再現。
24反復の幾何列は0.125 mmで最小角7.60043279度のまま品質FAIL、数値UNVERIFIED。
FEM列は弦0.03125 mm固定で20/10/5 mmの両比較PASS。
out/validation-g03-separated-refinement-round24-20260908/summary.jsonに保存。
次は幾何列のメッシュ品質停滞を再現し、独立幾何不変量を保って修正する。
標準220件中218合格・2 skip、validate PASS。G03全体/全互換目標は継続。

## G03の解析曲線GUI — 2026-09-08

元曲線保持・弦誤差/分割上限編集・幾何誤差表示・P2計算/保存再読込を接続。
実ブラウザー5検査PASS: out/gui-g03-curves-browser-20260908/report.json。
標準220件中218合格・2 skip。次は独立した幾何/FEM収束と双曲線等の総合受入。
曲線FEM/接線構築/旧入力対応を含むG03と全互換目標は継続。

## G03の幾何/FEM Study分離 — 2026-09-08

curved_contourのgeometry_convergenceを追加。弦誤差だけを変更し元曲線/FEM設定を保持。
mesh_scaleは弦Contourを保持し最大辺長を変更。Study各点へ幾何誤差記録を転記、P2表示修正。
標準219件中217合格・2 skip、validation-g03-curved-study-20260908 PASS。
examples/curved_ellipse.jsonを追加。study-g03-ellipse-geometry-20260908は操作成功だが数値判定FAIL。
弦体積誤差は減少。次はGUI元曲線/弦誤差/表示接続と、G03総合の幾何/FEM収束を続ける。
曲線FEM/接線構築/旧入力対応も残り、全互換目標は継続。

## G03の曲線鏡映/FEM — 2026-09-08

CurvedContour.reflectedで元曲線を鏡映/逆順接続し、全閉輪郭を再検証。
reflect_solutionへ接続して全Caseの弦Contourを再導出。楕円の両端×電気/磁気4条件で
解析面積/体積/U2倍、全メッシュ別solveのf/RQ/G一致、保存再読込を検証。
標準218件中216合格・2 skip、validation-g03-curve-reflection-20260908 PASS。
次はGUI/Studyへcurved_contourと幾何/FEM細分を接続、双曲線等の追加総合受入も残る。
曲線FEM/接線構築/旧入力対応と全互換目標は継続。

## G03の解析回転体体積 — 2026-09-08

curve_moments.pyで-π∮r²dzを線分/楕円/双曲線の解析指数積分として実装。
CurvedContour.volume_m3と保存geometry_approximationに解析体積・弦体積・差を追加。
円柱/円錐台/楕円体、双曲線の別変数積分、回転開弧の細分積分で独立検証。
標準217件中215合格・2 skip、validation-g03-analytic-volume-20260908 PASS。
次は元曲線の鏡映とGUI/Study連携。曲線FEM/接線構築/旧入力対応・全互換目標は未完。

## G03の元曲線Case/保存 — 2026-09-08

v3 geometry.type=curved_contour、曲線列のstrict入出力と弦誤差/全体分割上限をCaseへ追加。
Case.contourは導出、同時指定時は完全一致を要求。保存に弦表現/元曲線対応/調整/面積差を記録。
P2再読込と再計算係数が一致。標準214件中212合格・2 skip、validation-g03-curved-case-20260908 PASS。
解析曲線の鏡映は明示拒否。GUI/Studyは未移行なので次に元曲線/解析体積と併せて接続する。
Case置換で弦誤差を変えるときはcontour=Noneを指定して再導出。
曲線FEM、接線構築、旧入力対応と全互換目標は未完。

## G03の弦Contour変換 — 2026-09-08

CurvedContour.linearize→ChordApproximationを追加。タグ/元曲線対応・端点調整・解析面積差を保持。
端点調整を誤差予算から差引き、全体分割数上限とContour再検証・向き検査を行う。
半楕円の面積/独立楕円体体積収束、タグと元曲線不変を検証。
標準212件中210合格・2 skip、validation-g03-chord-contour-20260908 PASS。
次はCaseへ元曲線/弦誤差を保持する契約と保存、一般の解析体積。曲線FEM等は未完。
G03と全互換目標は継続。

## G03の単一曲線閉輪郭 — 2026-09-08

curved_contour.CurvedContourを追加。軸鎖/タグ/範囲/全辺対/正面積を検査し、
検査用二分で軸+半楕円の2辺形状も扱う。位置許容差は軸長1e-10以下、元形状は修復しない。
半楕円解析面積/寸法変換・分割軸混在タグ・交差/不正タグ/隙間を検証。
標準210件中208合格・2 skip、validation-g03-closed-curves-20260908 PASS。
次は弦近似Contour変換と幾何誤差/体積、Case元曲線保持。曲線FEM/旧入力対応も未完。
G03・全互換目標は継続。

## G03の隣接曲線検査 — 2026-09-08

directional_derivative_boundsとcertify_adjacent_curvesを追加。共有端点近傍は共通方向の
厳密な投影単調性、残り区間対は通常の離隔検査。許容差内の逆順重なりをUNVERIFIEDで拒否。
中心差分・線分/楕円・直角・逆向き・探索上限を検証。標準207件中205合格・2 skip、
validation-g03-adjacency-20260908 PASS。次は閉輪郭/軸連続性/辺タグ/全辺対/モーメント統合。
Case/GUI/曲線FEMは未接続、G03と全互換目標は継続。

## G03の区間包絡と離隔 — 2026-09-08

curve_bounds.pyに線分/楕円/双曲線の座標極値と余裕付き包絡箱、区間対細分の離隔検査を追加。
距離不足FAILと探索上限UNVERIFIEDを分離。共有端点を持つ隣接辺にはまだ適用しない。
解析極値・軸横切り・既知距離・交差/接触・同心円弧の検証が合格。
標準205件中203合格・2 skip、validation-g03-bounds-20260908 PASS。
次は閉輪郭への統合、共有端点近傍と非隣接辺の検査、軸/タグ契約。
Case/GUI/曲線FEM・旧入力対応は未完、全互換目標は継続。

## G03の線分・接線接続検査 — 2026-09-08

LineSegmentとcheck_curve_joinを追加。端点SI許容差と有向接線角を別判定し、形状を修復しない。
G1とC1/曲率連続を区別。線分↔楕円↔双曲線接線、逆向き/隙間/角/元形状不変を検証。
標準202件中200合格・2 skip、validation-g03-joins-20260908 PASS。
次は曲線区間の位置/誤差包絡、閉輪郭の交差/軸/隙間検査。
Case/GUI/曲線FEMと旧入力対応は未完、G03と全互換目標は継続。

## G03の双曲線弧コア — 2026-09-08

conics.HyperbolaArcに有限区間/枝±1、点/接線/曲率/最小半径/面積寄与/弦近似を追加。
両枝の陰関数・勾配直交・頂点半径・反転/面積・寸法と誤差を検証。
標準199件中197合格・2 skip、validation-g03-hyperbola-20260908 PASS。
次は線分/楕円/双曲線の接線接続契約と、曲線境界の交差/軸/隙間検査へ進む。
旧入力対応、Case/GUI/曲線FEMは未接続。G03と全互換目標は未完。

## G03の楕円弧コア — 2026-09-08

CONIC_GEOMETRY.mdで幾何/曲線FEMを分けた仕様段階を定義。
conics.EllipseArcに回転楕円の点/接線/曲率/最小半径/面積寄与/誤差上限付き弦近似を実装。
陰関数・直交・円極限・回転/反転・四分面積・寸法変換で独立検証。
標準196件中194合格・2 skip、validation-g03-ellipse-core-20260908 PASS。既存mode/hash不変。
次は双曲線プリミティブと接線接続契約、曲線の交差/軸/隙間検査へ進む。
Case/GUI/曲線FEM未接続、G03および全互換目標は未完。

## G02受入完了 — 2026-09-08

GENERAL_MESH.md末尾で全要件/実装/証拠を照合しG02.S/I/Vを受入。
実Chrome初回で結果表示のprofile前提を検出し、長さ取得/掃引/バンドを修正。
再検証5操作PASS、外部通信0、サーバー停止済み。細分Studyが最大辺長を変更しない問題も修正。
標準192件中190合格・2 skip、validation-g02-gui-fixed-20260908 PASS、旧mode/hash不変。
次はG03.S（円/楕円/確認済み双曲線、接線・曲率・丸め、幾何と曲線FEMの分離）へ進む。
C00未確認と残り親課題・全互換目標は継続。

## G02の自動solve/CLIとGUI欄 — 2026-09-08

make_meshをCase.contour_meshへ接続、未指定時は明示拒否を維持。自動/明示mesh一致、
保存Case再計算係数一致を検証。実CLIの合成folded例も全RF/hash/係数完全一致。
GUIに4設定欄とSI保持を実装し、contourでnr/nz/triangulationを無効化。
標準191件中189合格・2 skip、validation-g02-auto-20260908 PASS、JS構文PASS。
次は実Chromeでcontour読込→設定編集→solve→出力/再読込を検証し、G02全要件を照合。
examples/contour_folded.jsonは粗い操作例。全互換目標とG02は継続。

## G02の方式判断とCase制御契約 — 2026-09-08

ADR-017で測定に基づき自前品質判定方式を選択。ContourMeshControlsとv3
mesh.contour_meshへ最大長/最小角/要素・反復上限を追加しstrict解析・保存往復を検証。
標準191件中189合格・2 skip、validation-g02-controls-20260908 PASS。
次はmake_meshが設定から自動生成する接続とCLI/保存再実行、GUIの欄/読込保持/実操作。
現時点make_meshのcontourはまだ拒否する。新設定をGUIcollectはまだ保持しないので要対応。
G02全体・全互換目標は未完。

## G02の非円筒独立照合 — 2026-09-08

compare_contour_ngsolve.pyを追加。円錐台はPASS、折返しの初回周波数未収束FAILを残し、
.0015/.00075/.000375の双方追加細分でPASS。CONTOUR_RF_COMPARISON.mdに閾値/数値/費用を記録。
最終差f1.34e-5/RQ1.56e-5/G1.54e-5、内部H/EもPASS。最細NG36万DOF/84秒。
標準189件中187合格・2 skip、参照専用7件PASS。全ジョブ完了。
検証環境/tmp/superfish-g02-reference（隔離、NGSolve6.2.2606/NumPy2.5.3/SciPy1.18.1）。
次は方式ADRと製品のサイズ/品質/停止上限のCase契約、保存/CLI/GUI接続へ進む。
一般輪郭make_meshはまだ明示拒否。表面角ピークは未受入、G02・全互換目標は継続。

## G02の点追加と品質判定 — 2026-09-08

quality_contour_meshで悪い要素の最長辺へ境界を含む点追加、組替え/移動を反復。
目標最小角を全要素で達成したときだけ返し、反復/要素上限は明示失敗する。
測定mesh-g02-quality-20260908: 幅0.05は831要素12.61度、0.01は2336要素10.03度。
幅1e-5は4000要素上限でFAIL。標準188件中186合格・2 skip、validation-g02-quality-20260908 PASS。
次は独立非円筒RF参照との収束、方式/資源判断、Caseサイズ品質契約と製品経路を進める。
G02全体および全互換目標は未完。make_meshのcontour公開はまだ拒否のまま。

## G02の内部頂点移動 — 2026-09-08

smooth_contour_interiorで境界を固定し、関係要素の最小qを改善する内部点移動を追加。
正の向き・サイズ・タグ・独立モーメント/再現性を検証。標準187件中185合格・2 skip、
validation-g02-smoothing-20260908 PASS。幅0.5で最小角14.0→15.6度、幅1e-5は
0.000286→0.000368度に留まる。次は境界点追加を含む配置/必要要素数/品質拒否条件を評価。
G02の製品契約/自動solve/独立非円筒RFも未完。全互換目標は継続中。

## G02の内部辺組替え — 2026-09-08

improve_contour_anglesで境界/頂点を保ち2要素の最小角が改善する内部対角辺だけ交換。
最大長/局所サイズ保持、幾何モーメント、再現性/固定点を検証。標準186件中184合格・
2 skip、validation-g02-flips-20260908 PASS。測定mesh-g02-flips-20260908では品質中央値は
改善したが狭い経路の最小角は不変。次は頂点配置/追加方式と必要要素数を評価する。
Caseサイズ契約/自動solve/独立非円筒RF受入も残り、G02・全互換目標は未完。

## G02の適合細分化と品質測定 — 2026-09-08

refine_contour内部APIで共有中点/最長辺閉包/タグ継承、全域・境界・角サイズと停止上限を
実装。独立面積/体積・局所タグ長とサイズ達成が合格。標準185件中183合格・2 skip、
validation-g02-refinement-20260908 PASS。measure_contour_mesh.pyの測定で狭い経路の
最小角は細分しても改善しない（幅1e-5で0.000286度）。次は品質改善方式と必要要素数・
失敗条件/依存判断を測定。Case全域サイズ契約/自動solve/独立非円筒RF参照も残る。
G02は未受入、全互換目標は継続。

## G02の初期三角形分割 — 2026-09-08

GENERAL_MESH.mdで段階と受入条件を定義。contour_mesh.triangulate_contourは
全頂点/辺タグを保つ初期分割を実装し、独立矩形/円錐モーメント・狭い経路を検証。
標準182件中180合格・2 skip、validation-g02-initial-20260908 PASS。
make_meshの一般輪郭はまだ明示拒否。次はタグ継承を保つ細分化、全域/局所サイズ契約、
品質改善と停止制限を実装・測定する。G02.S進行中/I部分/V未受入、全互換目標は継続。

## G01受入完了 — 2026-09-08

GENERAL_CONTOUR.md末尾で要件/実装/証拠を照合しG01.S/I/Vを受入。
一般輪郭と混在タグのGUI実ChromeもPASS。最終標準178件中176合格・2 skip。
能力表はcontour対応と外部mesh必須を別表示。次はG02.Sの一般輪郭自動メッシュ方式・
品質検査・依存採用判断を仕様化し、実装/検証へ進める。全互換目標は継続中。

## G01の後処理点検 — 2026-09-08

一般輪郭のradial probe/plotは領域外の隙間をNaNで表現。CSVにinsideと
metadata規約を追加し、矩形分割の既知ギャップで検証。円筒参照/バンド/反復組立は
適用外を明示拒否。標準178件中176合格・2 skip、validate PASS。
次は混在タグGUIの実ブラウザ確認とG01全要件の受入照合。自動meshはG02。

## G01の局所端面タグ — 2026-09-08

混在端面をCaseの導出mixed要約で保持し、外部meshは辺タグを正として検証。
P2局所拘束と全面PEC/部分磁気/全面磁気の変分周波数順序、鏡映拒否が合格。
178 tests中176合格・2 skip、標準validate PASS。
GUI混在要約を実装・構文確認済み。次は混在GUIの実ブラウザ確認と、G01全経路の
未対応profile前提（解析比較/半径プローブ/組立等）を点検し、適切に移行/拒否して受入する。

## G01の実ブラウザ往復 — 2026-09-08

一般輪郭のファイル読込/8頂点表示/Case出力/再読込が実ChromeでPASS。
端面欄の無視される編集を修正し、読込辺タグの無効化表示にした。
証拠gui-g01-browser-final-20260908/report.json、標準validate PASS。サーバー停止済み。
次は局所端面タグをCaseで制限している箇所を整理し、G01仕様/証拠を最終照合する。
G01全体は未受入。

## G01の一般輪郭プレビュー接続 — 2026-09-08

gui.preview_documentを追加し、閉輪郭/タグ/面積/体積を返す。web/app.jsは
読込contourを保持し閉多角形として描画。ファイルによる形状編集を画面で説明する。
API往復・解析モーメントとJS構文は合格。次は実Chromeでcontourファイル読込・
プレビュー・Project/Case出力・再読込を検証する。局所タグ制限整理も残る。G01未完。

## G01のCase/FEM鏡映 — 2026-09-08

reflect_solutionでContour.reflectedを全Caseへ渡し、P2外部meshの
全領域再計算とf/RQ/損失を比較した。z折返しの両端×電気/磁気4条件PASS。
標準176件中174合格・2 skip、validate PASS。
次はgui.pyの/api/preview付近のlinearize_profile前提とweb/app.jsの形状保持を
一般輪郭へ移行する。局所端面タグの暫定制限も整理し、G01受入へ進む。

## G01の外部メッシュ接続 — 2026-09-08

mesh_from_dictを一般輪郭へ対応。辺単位タグ/投影区間の完全被覆、面積/接続/軸を検査。
矩形分割のz折返し外部meshでP2 solve→保存→読込が合格。
176 tests中174合格・2 skip、標準validate PASS。
次はプレビューと鏡映Case/FEMをprofile前提から移行し、局所端面タグの制限も整理する。
自動生成はG02まで未対応。G01全体は未受入。

## G01のCase v3連携 — 2026-09-08

Case((),contour=...)とv3 contour geometryを追加。profileは偽造せず空、
length/areaは輪郭から取得。175 tests中173合格・2 skip、標準validate PASS。
make_meshはG02、mesh_from_dictはG01検証移行待ちとして明示拒否中。
次は外部meshの境界検証・プレビュー・鏡映Case/保存を移行する。
同端面内の混在タグはCaseで暫定拒否。局所タグ契約も移行時に解決する。G01未完。

## G01の変換・鏡映 — 2026-09-08

Contour.from_profileとreflectedを実装。独立円錐台体積・z折返し鏡映の
面積/体積2倍を検証。標準174件中172合格・2 skip、validate PASS。
次はCase v3のcontour geometryを追加し、profile前提の長さ/境界/プレビュー/保存を
移行する。一般輪郭の外部mesh検証もG01対象。自動メッシュはG02まで未対応と明示する。

## G01の一般輪郭コア — 2026-09-08

GENERAL_CONTOUR.mdへ仕様を追加。contour.Contourでz折返し多角形の
厳密検証・向き/始点正規化・面積/体積を実装。矩形分割・円錐・寸法変換で独立検証。
172 tests中170合格・2 skip、標準validate PASS。
次は既存profile変換・鏡映・Case v3統合・外部mesh検証を進める。
G02の一般輪郭メッシュ生成は別段階で、現行R(z)生成へ黙って通さない。G01未完。

## N02受入完了 — 2026-09-08

HIGH_ORDER_FIELDS.md末尾で仕様・実装・証拠を照合しN02.S/I/Vを受入。
能力表・現在仕様をP1/P2へ更新。標準169件中167合格・2 skip、総合13チェックPASS。
次はG01.S（z折返し可能な単一外周・軸閉領域・厳密な不正輪郭拒否）から実装/検証へ進む。
G02の任意輪郭メッシュは別依存段階。C00の未確認行とC03/C04、他の全親課題は継続対象。

## N02の総合数値検証 — 2026-09-08

validate_quadratic_fields.pyで独立J0/J1/cos/sin場・ピーク・RF・同DOF比較を検証。
13チェックPASS、証拠quadratic-fields-n02-final-20260908/fields.json。
Job取込再実行の係数/RF一致と寸法スケーリングも追加。標準169 tests中167合格・2 skip。
次は能力表・PHYSICS/README/進捗のP1限定記述を現実装へ整え、N02.Sの全移行箇所・
受入条件と証拠を照合してN02を受入する。全32項目・33親課題の目標は引き続き未完。

## N02のGUI次数選択 — 2026-09-08

P1/P2選択、v3/model生成、Project読込往復を接続。実Chromeの4操作と
標準validate PASS。証拠はgui-n02-order-browser-final-20260908/report.json。
今回のGUIサーバー停止済み。次は能力表・現在仕様の記述を更新し、
Bessel全場/ピーク/誤差対DOF/Job再実行を総合検証してN02全体を受入する。

## N02のCase/CLI次数 — 2026-09-08

v3 solver.element_orderで1/2をstrict受理。solveが次数を選択し、Project・保存・
再読込・再実行まで保持。旧Case研究P2保存は次数2をCase/鏡映元へ明示する。
167 tests中165合格・2 skip、標準validate PASS、P1 mode/hashは不変。
次はGUIの次数選択と入出力保持、能力表/文書を更新し、総合Bessel場・ピーク・
誤差対DOF/半全・Job再実行を検証する。N02全体は未完。

## N02のバンド・細分比較 — 2026-09-08

analyze_bandはP2セル中心と軸停留点、compare_refinementは高次Hと
P1/P2差の正確な軸積分を使用する。既定read_solutionでP2を読める。
165 tests中163合格・2 skip、標準validate PASS、P1のRF全量/hashは不変。
次はCase/Project/CLI/GUIへ次数を保持して再実行を可能にする。
Job取込は保存P2を保持できるが、Case次数がまだ無いため再実行の次数保持は未完。
Bessel場/ピーク/誤差対DOFの総合証拠を整え、N02全体を受入する。

## N02の保存P2解析/probe — 2026-09-08

export_radial_probeとcompare_pillboxが高次reader/samplerを使用する。
円筒解析の軸L2はP2軸辺の8点Gauss評価へ対応。3モード同定・全ゲート、
元解とのCSV場一致を検証。164 tests中162合格・2 skip、標準validate PASS。
次はanalyze_bandとstudiesの高次場/軸評価を移行し、既定読込の暫定拒否を撤去。
Case/CLI次数指定と総合Bessel/ピーク/DOF比較も残る。

## N02の保存P2描画 — 2026-09-08

plot_modeを検証済みreader/display_fields/高次samplerへ移行。保存P2から
電場・磁場・軸・radialを描画し、元解とのprobe一致と未完了拒否を検証。
163 tests中161合格・2 skip、標準validate PASS。PNG目視証拠は
out/p2-plot-20260908/mode2.png。次はsaved解析/probe・studiesへ高次場を渡し、
read_solutionの既定拒否を撤去する。Case/CLI次数と総合N02検証も残る。

## N02のP2保存・明示読込 — 2026-09-08

save_runでP2全係数/4空間配列/field_space宣言を保存。read_solutionの
allow_quadratic=Trueで再構成空間との一致を検証して読める。
162 tests中160合格・2 skip、標準validate PASS、P1のRF全量/hashは不変。
次はsavedのprobe/比較/バンド、visualize、studiesへ空間を渡す。移行完了後に
読込の暫定制限とplot_modeの拒否を撤去する。Case/CLI次数指定も残る。N02未完。

## N02の表示用分割・VTK — 2026-09-08

display.pyへP2の4分割表示データを追加し、write_vtkに接続。
二次多項式の場・面積・VTK値を検証。161 tests中159合格・2 skip、標準validate PASS。
P1のRF全量/hash/VTKバイト列は不変。次はsave_run/read_solutionへ次数・全係数・
接続情報を保持して移行し、plot_modeと追跡へつなぐ。N02全体は未完。

## N02のP2鏡映 — 2026-09-08

reflect_solutionを全中点の偶奇写像へ拡張。両端×電気/磁気対称について
独立全領域solveと周波数/RQ/損失の一致、場の偶奇、U/損失2倍を確認。
159 tests中157合格・2 skip、標準validate PASS、P1のRF全量/hashは不変。
次はP2保存/再読込/表示/追跡とBessel場・ピーク/誤差対DOF証拠を進める。
HIGH_ORDER_FIELDS.mdに記録。N02全体の受入とCase/CLI次数公開は未完。

## N02の表面積分とRF量 — 2026-09-08

quadratic_rf.surface_integrals_p2を実装し、rf.quantities/cell_fieldsへP2を接続。
既知多項式の損失/内部極値、3モードのRQ/G収束・Uスケーリングを検証。
158 tests中156合格・2 skip、標準validate PASS。P1 mode全量とhashは不変。
次はBessel全場/ピーク/誤差対DOFの証拠とP2保存・再読込・鏡映/描画/追跡統合。
HIGH_ORDER_FIELDS.mdを参照。Case/CLIのP2指定はまだ未公開でN02は未完。

## N02の軸電圧積分 — 2026-09-08

quadratic_rf.pyへ二次軸場の複素電圧/絶対値積分とP2解アダプタを追加。
低beta・部分区間・符号反転を独立積分で検査。155 tests中153合格・2 skip、
標準validate PASS。HIGH_ORDER_FIELDS.mdに式と証拠を記録した。
次はPEC表面損失/極値、quantities/cell_fields統合、その後保存/描画/鏡映/追跡。
N02全体と継続目標は未完。

## N02の場評価を開始 — 2026-09-08

HIGH_ORDER_FIELDS.mdにN02仕様と全移行箇所を記録。FieldSamplerは明示したP2空間の
6係数を保持し、from_solutionで次数整合を検証する。独立多項式/軸極限テスト合格。
152 tests中150合格・2 skip、標準validate PASS、P1の周波数/RFとhashは不変。
次は二次軸電圧の安定積分・PEC辺積分/極値。その後RF/保存/表示/鏡映/追跡を統合する。
N02は実装途中であり、全体の受入は未完。

## N01のP2固有値コア — 2026-09-08

N01.S/I/Vを受入。QUADRATIC_ELEMENTS.mdに独立積分・収束・再現手順を記録。
研究用high_order.solve_p2のみ公開し、P1用の場/RF/保存/鏡映はP2解を明示拒否する。
150 tests中148合格・2 skip、標準validate PASS。既存の円筒/成形セルのmode全量は直前と一致。
次はN02.Sで高次係数を保つ場評価・RF積分・保存・描画・鏡映・追跡を設計し、実装/検証する。
32項目・33親課題全体の目標は継続中。以下の古い開始点は履歴として読む。

## R01の加速量規約 — 2026-09-08

R01.S/I/Vのnative範囲を完了。ACCELERATING_CONVENTIONS.mdに仕様・再現・失敗履歴を記録。
v3 rfのactive_length_m、voltage_interval_m、phase_origin_mを追加し、旧既定値/hashを保持。
解析比較、鏡映写像、CLI/GUI/保存を更新。143 tests中141合格・2 skip、標準validate PASS。
最終GUIはout/gui-r01-browser-accepted-20260908、数値はout/validation-r01-final-20260908。
初回の区間外掃引拒否と撮影待ちFAILを保持する。旧入力の任意ZCTR等はまだ受け入れない。
次はN01.SのP2要素/解契約→N01.I/V、N02の場/RF/保存・表示への移行を進める。
N02受入まで高次RFを製品公開しない。C00の未確認行とC03/C04も継続対象。

## O01の保存完了管理 — 2026-09-08

O01.S/I/Vのローカル契約を完了。SAVE_COMPLETION.mdに仕様と受入を記録した。
save_runは出力先を排他予約し、内部一時領域で全ファイルを作り、非置換hard linkで
完了マーカーを最後に公開する。read_solutionは全必須出力のhashを検査し、旧形式も読む。
Job取込の外部meshコピー漏れを修正し、新しい直接保存の完了証拠を区別して保持する。
137 tests中135合格・2 skip、out/validation-o01-accepted-20260908がPASS。
R01の加速量規約とN01/N02、C00調査、C03/C04は未完。次はR01.Sから進める。

## C02限定AF読込の受入 — 2026-09-08

LEGACY_INPUT.mdのC02初期部分集合を仕様・実装・検証まで完了。
import-afはnr/nz/modes/導電率/正規化を明示必須とし、DX/FREQ等の無適用を診断に記録する。
単一REG・全PEC・軸接続真空TM・直線/段差/NT4/5短円弧のみ受理。その他は位置付き拒否。
128 unittest中126合格・2 skip、out/validation-c02-final-20260908がPASS。
保存AF2形状からの新規NG4計算と既存SFO照合はout/c02-import-acceptance-20260908。
新規旧計算・場全体/表面ピークの受入ではない。C00/C03/C04と汎用旧入力は未完。
次はR01の加速量規約、またはO01の直接保存完了管理を仕様化して実装する。

## C01共通契約の受入 — 2026-09-07

C01.S/I/V完了。仕様・実行証拠・再現はMODEL_CONTRACT.md。
v3 modelとcapabilities/migrate-caseを実装し、v1/v2のhashと既存解を保持した。
Project/Study/GUI/鏡映/外部meshの保存でmodelを失わず、追加物理は計算前に拒否する。
122 unittest中120合格・参照環境専用2 skip、標準validateとChrome 8操作検査PASS。
最終証拠はout/validation-c01-final-20260907、out/gui-c01-browser-final-20260907。
次はC02.SでDXのNG指定への写像、FREQ等の探索指定、未指定導電率/正規化の扱いを
明記し、確認済みAF部分集合のstrict読込と変換記録を実装する。C00調査は未完了のまま継続。

## 互換開発goal開始 — 2026-09-07

ユーザーが32対応項目・33親課題の完遂をgoalに指定。作業checkoutは
`/home/sin/code/agent/reserch/superfish-ng`。C00の最新記録はCOMPATIBILITY_BASELINE.md。
全32項目の受入軸、限定TM辞書と未確認事項、保存出力のAutomesh/Fish/SFO/SF7版、
参照ファイルhashを記録した。C00.Vは未完了。次はC01.Sの共通契約とC02.Sの
メッシュ/探索/未指定RF設定の変換契約を具体化し、C00の追加ツール調査も継続する。
開始時114 unittest中112合格・参照環境専用2 skip。今回の旧計算再実行はなし。
以下の計画整備のみを対象とした指示より本節を優先する。

## 現在の入口 — 2026-09-07 計画整備

最新指示は「実態に合わせて計画更新→互換対応表→作業分割」。このターンは計画を整備する。
計画整備v0を完了。[COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md)のK01〜K32と
[COMPATIBILITY_PLAN.md](COMPATIBILITY_PLAN.md)の.S/.I/.Vを次の作業単位とする。
次はC00の版・入力集合の確定→C01.Sの共通契約。高次要素へ直ちに飛ばない。
表のH/Uは対象版未確認、Xは互換必須集合外。仕様調査未完を互換完成と混同しない。
[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)と[BACKLOG.md](BACKLOG.md)を正本とし、
以下の履歴内の「次は…」やseed開始プロンプトより優先する。
製品基準1f5cd84で114テスト中112合格・2 skipを再確認。物理範囲や製品コードの変更はない。
P1-03は平坦z端で完了、P2-04はGUI範囲で完了。一般追跡・tune・直接保存の原子的完了は残る。

以下は日付付きの実施履歴。テスト件数・実行環境は各時点の値を保持する。

## 互換性拡張の再開 — 2026-09-07

ユーザーは可能な範囲で互換拡張を進め、区切りごとのローカルコミットを指示した。
P0-01のNGSolve独立照合を完了。仕様と再現はINDEPENDENT_COMPARISON.md。
通常環境の基準101テストは合格。検証専用venvは
`/tmp/superfish-ng-independent-20260907`。本体の依存・FEM・RFは変更していない。
次はP0-02のタグ付き非構造メッシュ。旧入力互換や物理範囲拡張の完了ではない。

同日P0-02/P0-03も完了。`solve case.json --mesh mesh.json --out ...` と
`solve(case, mesh_data=...)` を追加。仕様・受入はMESH_INPUT.md。
114件中112件合格・参照環境専用2件skip、標準数値検証PASS、既存周波数差ゼロ。
次の数値拡張候補はP1-01。メッシュの読込で対応物理範囲は増えない。

## 汎用GUI・共通入出力の計画 — 2026-09-06

ユーザー依頼に基づき [GUI_IO_PLAN.md](GUI_IO_PLAN.md) を作成した。
例題専用の処理を作らず、対応物理範囲の汎用操作を提供し、KEK対象操作と例題外の
合成ケースで受け入れる。追加機能・抽象化は全体品質への寄与で判断する。
追加指示でG0〜G5の受入完了を `/goal` に設定した。ADR-009/010により
Project・JobManager・保存結果読込・Study・ローカルGUIを共通化した。
新規Web/Qt依存なし。形状編集、旧結果取込、掃引/収束/比較/分散を実装済み。
32数値受入、101 unittest、別環境へ展開したwheelのGUI計算/描画がPASS。
G0〜G5の技術的受入を完了。実行証拠・対象外・主観評価の未実施はGUI_ACCEPTANCE.md、
操作はGUI_GUIDE.mdを参照。
`python -m superfish_ng gui --workspace out/gui-workspace` で起動する。
既存の半端部バンド同定を任意形状へ適用しない。一般mode tracking・tuneは本計画の対象外。

## 境界・局所メッシュ改善 — 2026-09-06

任意のv2 mesh設定で境界辺と角周辺の内部辺を実長制御する。既定は従来経路。
設定仕様はINPUT_OUTPUT.md、検証数値と制約はPHYSICAL_MESH_REFINEMENT.md。
最終9計算は `out/physical-mesh-final-20260906/`。1 mm固定点変化26.14%→2.21%、
PEC接線比7.95%→1.52%。節点約3.25倍であり同コスト優位の証明ではない。
円弧には境界サイズのみ対応。P1電場復元と鋭角特異性は変わらない。

## 角部診断の追加 — 2026-09-06

ユーザーの質問を受け、P1-04の切り分け評価を実施。
[SURFACE_FIELD_DIAGNOSTICS.md](SURFACE_FIELD_DIAGNOSTICS.md)に新規計算と解釈を記録する。
鋭角のEpkは細分で上昇するため、過去のNG–Wine差14.8%を有限厳密値の誤差と解釈しない。
実装本体は変更していない。現checkoutには過去out/がなく、ユーザー許可でWine比較環境も新設した。
NG25計算（元の19＋真空側固定点6）とWine鋭角/接線円弧各4段階を完了。
最終参照は `out/surface-wine-arcs-20260906/report.json`、図と集約値は
`out/surface-wine-report-final-20260906/`。鋭角の生結果は検査して再利用した。
Wine最細の鋭角ピーク変化17.48%、丸み対照ピーク変化2.81%を未収束として残す。
丸み対照のNG–Wine差は1.21%。今回の診断をP1-04全体の完了やEpk精度保証と呼ばない。
78テストと `out/validation-surface-final-20260906/` の既存数値検証は合格。
Wineランタイムは `/tmp/superfish-wine-runtime/`。一時領域の掃除後は再作成が必要。

## 現在の優先目標（2026-09-05更新）

ユーザー指定の [セミナー4資料の例題計算・可視化](MILESTONE_SEMINAR.md) は完了。
最終結果は `out/seminar-suite-final-20260905/index.html`、受入監査は [MILESTONE_ACCEPTANCE.md](MILESTONE_ACCEPTANCE.md)。
9数値ジョブ・69テスト・7ページ検査がPASS。全NGは新規計算、Wineは入力・hashを検査して再利用した。
最終suite.jsonはPASSかつsource_changed_during_run=false。継続待ちの計算プロセスはない。
以下の個別試行・失敗も履歴として保持する。次の機能拡張はユーザーの次の指示で選ぶ。
Wine版SUPERFISHとの3形状の基本モード照合は完了し、[比較結果](SUPERFISH_COMPARISON.md) を保存した。
S1の全領域TM010/TM011・長さ掃引・図・CSV・HTMLとWine/SF7照合は実装済み（[記録](SEMINAR_PILLBOX.md)）。
S1の半領域の電気／磁気対称境界・全空洞鏡映も完了。`seminar_symmetry.py` で再現可能。
段差・円弧、4/7モード同定と分散曲線も実装済み。[記録](SEMINAR_MULTICELL.md)を参照。
flat4はNG nr=128/256/512とWine dx=0.05/0.025/0.0125/0.01で全照合・収束PASS。
`out/seminar-flat-ready-20260905` とheadless検査 `out/gallery-test-flat-ready-20260905` が最終結果。
rounded4はNG・形状近似・Wine3段階の全検査合格（`out/seminar-rounded4-wine-comparison-20260905`）。
rounded7は任意のcrossed分割を追加し、nr=64/128/256で全量PASS。
`out/seminar-rounded7-crossed-native-20260905` と `out/seminar-rounded7-crossed-geometry-20260905` を参照。
円弧半領域の鏡映にも対応したが、対称反射だけのR/Q改善試験は不成功。失敗試験も保存済み。
rounded7のWine3段階は `out/seminar-rounded-wine-20260905/rounded7` で完了。
full-end切断面を実装した `scripts/seminar_end_cells.py` も追加。初回検査はflat/halfのR/Qだけ1.1521%でFAIL。
追加nr=384で変化0.32373%を確認し、`out/seminar-end-cells-ready-20260905` の最終レポートはPASS。
`out/gallery-test-end-cells-ready-20260905` で全8選択肢・51リンク/画像のheadless検査も合格した。
Pillbox/rounded4/7のHTMLはheadless Chromeの実キー入力で検証済み。Orcaの既存デスクトップ操作は行っていない。
S6の `scripts/seminar_suite.py` と入口HTML生成を実装し、`out/seminar-suite-20260905` の全NG計算・全7画面検査は終了。
全体FAILの原因は7セルπモードのWine側R/Q細分1.98217%とTTF。NG–Wine差は全モード合格。
RAM設定で追加DX=0.01/0.011 cmはSFO生成前に失敗。ローカルSF.INIのStoreTempDataInRAM=Noを使う
`out/seminar-rounded7-wine-extra-20260905/disk-dx0.01/mode7` が正常終了。既設SF.INIは変更していない。
πの追加R/Q細分変化0.658403%、NG–Wine差0.757236%で合格。元の未達履歴は消さない。
モード別追加細分の検証を実装し、`out/seminar-suite-final-20260905` で全NGを再び新規計算してPASS。
参照は既存Wine生出力を検査して再利用し、必要なrounded7出力は最大14400秒の読取専用待ちを明示した。
開始時のsource/tests/scripts/examples hashと終了時の一致を確認した。今後も一括実行中にはソースを編集しない。
最終suite.json、全子レポート、参照ファイル、画面とリンク先のhashも再監査した。
追加参照を含む比較はfinal_legacy_modesを読む。legacy[-1]は追加前の履歴であり、πの旧FAILが意図的に残る。
操作手順と判定仕様は [SEMINAR_SUITE.md](SEMINAR_SUITE.md)。
以下の開始プロンプトはseed時点の記録で、次課題P0-01の優先順はこの更新で置き換える。

## 開始プロンプト

以下をそのままCodexへ渡せる。

```text
このSuperfish-NGリポジトリを継続開発せよ。
AGENTS.md、README.md、docs/PHYSICS.md、docs/PROVENANCE.mdを最初に読み、
docs/TESTING.mdに従い、変更対象と影響先のテストを選ぶこと。
着手時に全件を回さず、必要なseed数値検証はscripts/validate.py --skip-testsで分離すること。
旧SUPERFISHのソースやバイナリは参照・使用せず、公開された数学と
明示的なライセンスを持つ現代のOSSだけを使用する。

次の目標はdocs/BACKLOG.mdのP0-01「外部ソルバでの独立照合」である。
同じ幾何形状・境界・phasor・単位・R/Q規約を固定し、NGSolve等で
独立に計算して比較する。参照ソルバを導入できなければ、比較済みとは
主張せず、実行可能な比較用入力と未実行の理由を残すこと。
その後P0-02の境界タグ付き非構造メッシュ対応へ進む。

科学的な回帰を起こさず、小さなコミットで進めること。
周波数だけを解析値に合わせてRF量の精度を保証したことにしない。
変更内容、検証結果、未解決事項、次に実行するコマンドを最後に報告せよ。
```

## 現在の動作経路

`Case.load → make_mesh → assemble → solve → quantities → save_run`。
式と積分は `src/superfish_ng/fem.py` と `rf.py`、独立解析解は `analytic.py`。
テストは `unittest` 69件。seedの主要数値は `benchmarks/validation/`、最新照合は `docs/SEMINAR_PILLBOX.md` と `docs/SEMINAR_MULTICELL.md`。
出力は別の新規ディレクトリへ作る。既存ベンチマークを直接上書きして初期値を失わないこと。

## 直近の注意点

- P1のuはr³重みのエネルギーでは良好でも、軸上Ezの点値収束はより遅い。
- 自由度は節点u=Hφ/r。VTKに出すHφはrを掛ける。軸上uを0にしない。
- 電場のP1微分を節点平均で平滑化すると見た目は改善してもピーク値が偏る。未評価の平滑化を設計指標に混ぜない。
- 無限に鋭い角を持つ形状ではEpkのメッシュ独立値が存在しない可能性がある。丸め半径を仕様にする。
- 既定のactive lengthは全長。多セルやビームパイプ追加時に自動流用しない。
- seedのQR/直交化はeigshに任せ、物理的な勾配nullspaceを除去したことにはしない。現在のTM縮約に3D機能を足す際に再設計する。
- `save_run`は出力ディレクトリを新規作成するが、ディスク書込み全体のトランザクション化は未実装。途中失敗したディレクトリは完了扱いしない。

## 環境の再現

通常は `pip install -e .`。納品時のPython 3.12系に揃える場合は
`pip install -r requirements-reproduce.txt` の後 `pip install -e . --no-deps`。
このファイルはプラットフォームごとの依存ハッシュを固定したlockfileではない。
OS・BLAS・CPUや縮退モードの基底は変わり得る。期待値は許容誤差で比較する。

CIはLinux/Python 3.10と3.12を対象とする定義を同梱したが、納品時の実行実績はローカルPython 3.12のみ。
依存環境を整えたユーザーPCでのテスト結果を次の記録として保存する。

## 完了報告の基準

新しいバックエンドは、関数がimportできるだけでは完了ではない。
入力ケース、出力、参照値、誤差、実行バージョン、未対応条件を記録して初めて完了とする。
外部参照値が入手できないときはその事実を示し、架空のSUPERFISH/CST比較表を作らない。

最新メッシュ改善の検証: 82テスト、`out/validation-physical-mesh-final-20260906/` PASS。
seed周波数差ゼロ、RF相対差最大6.67e-16。既存ベンチマークの更新なし。


継続作業：辺候補のBVH試作out/planar-edge-candidates-20260909は10042/86257終了0。候補集合の総当たり一致と主ツリー11unit、全メッシュ配列一致を確認。小規模の遅化も含む実測を保持し未採用。追加三角形59036のP1 TE n448は三ゲートPASSの途中出力あり、TM以降とreport終端はまだ確認していない。標準92838は824件PASSで終了0、最終seed照合と/tmp/finalize-planar-mesh-docs.pyも実行済み。既存workspace/.manager.lockのResourceWarningは再度出たため未解決の資源解放警告として保持。
2026-09-21 JST：週次レビューのHφ調整2件を修正。GUI再開後の継承/追加checkpointは
所有パスとnative/RFのhash・判断履歴で検証する。投入時と保存後の検証を分離し、元出力移動後も
worker/GUIを所有コピーだけで再検証する。元投入記録は不変、コピー改変/欠落/リンクは拒否。
`test_hphi_tuning_jobs test_gui_hphi_tuning`は6件PASS（185.788秒、終了0）。
修正前の2経路の失敗も再現済み。実worker中止/再開を含み全プロセス終了。
数値核/schema変更なし、数値validator・seed/full・実ブラウザークリック列は未実行。
詳細と実行コマンドは[HPHI_TUNING.md](HPHI_TUNING.md#2026-09-21-レビュー修正)。

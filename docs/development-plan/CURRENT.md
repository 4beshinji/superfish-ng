# 現行の作業入口

## 科学レビュー後の挿入工程（2026-10-13）

今回の実装は[科学レビュー](../SCIENTIFIC_REVIEW_2026-10-13.md)を受けたリファクタリング11枚を対象とする。
[RF-01〜RF-11](../REFACTORING_PLAN.md#順序と区切り)をTSVへPLANNEDで登録し、
現行141枚に11枚を追加した全152枚を対象とする。既存カードの受入状態は変更しない。
以下の先頭追記と「次は」は従来工程の履歴であり、次の着手順はこの節を優先する。

1. 進行中ADD-N04-rf-goal-04の現在の変更単位を完了保存し、実行中処理の終端とソース固定解除を確認する。
   全04完了までは待たず、そのコミット境界でRF-11（入力と実解の対応）→RF-01（validator前後監査）を行う。
   ADD-N04-rf-goal-05の固定36実行や新しい長時間受入は両カードの受入後に進める。
2. RF-09で現行仕様と履歴を整理し、RF-02→RF-03で環境と下位共通処理の境界を固定する。
3. RF-04/05/08を次に触るworker/調整経路ごとに進め、RF-06/07のCLI/HTTP/画面分離を操作受入へ接続する。
   RF-10は移行後に測定し、効果のある箇所だけ改善する。
4. V02/V03/V05の追加先行条件でこの工程を確認する。S03/S04の量別・限定保証と、
   S05の実測/不確かさ不足は従来の検証/L06/L07から省かない。

RF-11を[求解契約の受入](../AFFINE_SOLUTION_CONTRACT.md)、RF-01を
[validator前後監査](../VALIDATOR_SOURCE_AUDIT.md)、RF-09を[現行入口と履歴の索引](../ARCHITECTURE.md#current-architecture)で完了した。
RF-02を[core/GUI・Python版別の環境契約](../DEPENDENCIES.md#current-environments)で完了した。
RF-03は値検査の元bodyを抽出し、config転送/同軸入口と直接10unit・75互換probeを確認した。
JSON/canonicalも元bodyを抽出し、Project/旧canonical転送・同軸native、直接17unit/143互換probe/113例題hash一致を確認した。
来歴も元SHA/JSON置換bodyを抽出し、jobs/completion転送・Hφ所有hash、直接25unitとbyte/例外/失敗保存保持を確認した。
三段階の初回広範統合fullは固定1492 source/8 processで終了1（out/validation-rf03-integration-20261014）。
2689 test/528 moduleを収集し、8 moduleの2 FAIL/18 ERRORと3 SKIPを保持した。実validatorの前後監査はUNCHANGEDで、失敗reportを残してseed計算へ進まなかった。
計測alias・反射の拒否順・独立比較のCase・保存場fixtureの求解契約・失敗reportの旧期待値という5点を修正した。
隔離した自作sourceで58個別unitを分割PASSし、実P2の一回組立計測と行列/場/全RF一致、独立Bessel f/H/E/壁loss/RQ、3形状54 FEMのpause/resume/完全再生を確認した。
終端後に検証した5ファイルだけを主ツリーへbyte一致で反映。他1487 sourceは不変。rawはout/rf03-lower-helpers-20261013/integration-followup-applied.json。
[RF-03の固定full受入](../LOWER_SHARED_HELPERS.md)：2689 test/528 module、3910.941秒、終了0/PASS、FAIL/ERROR0/既存SKIP3。前後1492 sourceは完全一致。
同fullのseed全RFと保存再構築を照合し、f差ゼロ・物理量相対差最大8.882e-16。初回失敗/分割58件はそれぞれ元scopeで保持する。
[RF-04所有worker](../OWNED_TUNING_WORKER.md)もDONE。worker14＋GUI service6の20個別unit、旧新12 FEMのnative/Project/全RF/判断一致、元六成果物の追加求解なし再生を確認。
検証済み四ファイルを主ツリーへbyte一致で反映、他1489 source不変、JobManager/数値核/schema不変。GUI証拠はserviceで実ブラウザーではない。
RF-05は隔離sourceで元decisionを抽出し、114旧新判断/174専用adapter/AST照合PASS。10直接tuning/回復moduleの実unitを実行中で主ツリーへ未反映。
全152は97 DONE/4 IN_PROGRESS/51 PLANNED、RF-03/04はDONE、RF-05はIN_PROGRESS、他4枚はPLANNED。次はRF-05受入→RF-08/06/07/10。
既存prefix・失敗・未確認の証拠と配布/統合依存を保持する。

2026-10-13 ADD-N04-rf-goal-04 **IN_PROGRESS**：[随伴C-call計測と部分保存/資源停止](../CURVED_RF_GOAL_EFFICIENCY_FAILURES.md)。元数学sourceをbyte維持し、随伴関数内だけのC観測で長球の元全branch一致・factorization/C solve各2回・新FEM0を確認。書込中の実SIGINT/45秒wall/192MiB RSS上限で完全prefixと部分stagingを分離保持、SIGINT後の再開もPASS。新worker7 FEMの全73配列/全RFが元と一致、Ue/Uh最大差1.333e-15。unit内5 FEMは別計上、新8＋直接11の19個別unit分割PASS。旧観測版1の四prefixも維持。元1481中他1478源byte不変、新IO/観測/test込み1484。初稿源SHA停止/Mock ERRORと観測負荷の大きい初稿を保全、全handle終端。新固定36/seed/full/GUI/legacy0。全process manifest/最終書込費用・CLI・幾何/追跡予算停止のreader整合と一般kill再開は残り04未完。全141は91 DONE/3 IN_PROGRESS/47 PLANNED、原123は76/2/45、親N04/全goalは継続。

2026-10-13 ADD-N04-rf-goal-04 **IN_PROGRESS**：[実SIGINT・二段階再開・追加一様確認](../CURVED_RF_GOAL_EFFICIENCY_RESUME.md)。新11native完了＋実中断1試行を保持。球の元checkpointから1＋2event再開と三方式各1event継続、無中断4eventを比較し、164 native配列/64 sample配列・全RF/独立誤差が完全一致。初回達成1/確認3、公開3eventは凍結。Ue/Uh最大差3.442e-15、長球棄却320から元親80→113局所の再開計画も新FEM0で一致。新4＋直接7の11個別unit、元/新版archiveの親連鎖再生を確認。元1479中他1477源byte不変、新resume/test込み1481。旧費用・失敗/終了-2と全束縛を保持し、新固定36/seed/full/GUI/legacy0。C線形solve/全process manifest・CLI・資源停止/部分書込が残り04未完。全141は91 DONE/3 IN_PROGRESS/47 PLANNED、原123は76/2/45、親N04/全goalは継続。

2026-10-13 ADD-N04-rf-goal-04 **IN_PROGRESS**：[全native・全場・停止判断の保存再検証](../CURVED_RF_GOAL_EFFICIENCY_REPLAY.md)。球三方式/長球rf_goalの全12event・24sample・5,007,024成分が一致、4process終了0・新FEM0。親/棄却probe/確認/初回達成/初期ID/実Erの6再hash改変を拒否し、新7＋直接1の8個別unitを分割PASS。元費用を保持しRSS/投入時計/phase算術を検査、初回JSON型ERRORと費用guard先行FAILを保全。元1477中他1476源byte不変、新reader/test込み1479、既定writer/科学再構築ASTと全1,756束縛を監査。全handle終端、seed/full/CLI/GUI/固定36実行0。実中止再開・追加一様確認・C線形solve/全process費用・CLIが残り04未完。全141は91 DONE/3 IN_PROGRESS/47 PLANNED、原123は76/2/45、親N04/原32要件/全goalは継続。

2026-10-13 ADD-N04-rf-goal-04 **IN_PROGRESS**：[実native分岐/全域場/費用記録の接続](../CURVED_RF_GOAL_EFFICIENCY_EXECUTION.md)。球三方式と長球rf_goalの各3event、計12新FEM・四process終了0。長球80→320棄却→元親80から113局所の全分岐と公開完全再構築が一致、全場/実ID/両次数と未達を保持。球native TARGETS_METも比較側PAUSEDを維持。新/直接8個別unitを分割PASS、制御例外の元object/部分費用/alias復元も確認。元1475中他1474源byte不変、metric結合一源修正と新worker/testで1477。成功12native後の二記録guardはASTと元12状態へ再結合し新FEM0。全handle終端、seed/full/CLI/GUI/36benchmark0。実workerのfresh APIまで接続、全journal再生/実中止再開/追加一様確認/全観測とCLIは未完。全141は91 DONE/3 IN_PROGRESS/47 PLANNED、原123は76/2/45、親N04/原32要件/全goalは継続。

2026-10-13 ADD-N04-rf-goal-04 **IN_PROGRESS**：[比較指標と採用祖先の停止判定](../CURVED_RF_GOAL_EFFICIENCY_WORKER.md)。同じ全域gridの元場/単一符号/前場ノルム・両R/Q/peak区間、両Gauss次数、三採用祖先と二一様辺を検査。棄却probe/local・native TARGETS_METの誤昇格を拒否、新9＋旧accuracy8の17個別unitを分割PASS。実追跡のnull IDによる初稿ERRORを保全し、非採用UNVERIFIEDとして保持する修正後branch5件0.011秒・終了0。元1473源byte不変、新2源込み1475、新FEM/seed/full/CLI/GUI/36benchmark0。実worker/全event費用/保存完全再生/中止再開は未実装で04は未完。全141は91 DONE/3 IN_PROGRESS/47 PLANNED、原123は76/2/45、親N04/原32要件/全goalは継続。

2026-10-13 ADD-N04-rf-goal-03 **DONE**：[独立全域参照の六ケース受入](../CURVED_RF_GOAL_EFFICIENCY_REFERENCE.md)。球の独立解析式と長球/丸めの三h・全五modeをGauss16/24へ結合。全12grid・体積1181440/軸56800点、Green三積分差最大5.885e-15・全E/H/軸/両R/Q/G/peakと二尺度を確認。新9＋旧関連13の22個別unitを分割PASS、長球準備38.833秒/最大RSS6.121 GB・終了0。旧source SHAの停止は元八fileの同一byte archiveで解消し、旧reader/現行源/閾値は不変。元1470源byte不変、新3源込み1473、全handle終端、新FEM/seed/full/GUI/36benchmark0。全141は91 DONE/2 IN_PROGRESS/48 PLANNED、原123は76/2/45。次は04の実worker/全event費用/保存完全再生、native精度/親N04/原32要件/全goalは継続。

2026-10-13 ADD-N04-rf-goal-02 **DONE**：[固定計画と全36要求のstrict検査](../CURVED_RF_GOAL_EFFICIENCY_INPUT.md)。13項目/全行/元Case・明示mesh/全ID/二方針・一様版4変換、厳密型/重複/未知/再hash改変/コピー隔離を確認。全11fileの読取前後SHAとsymlink/FIFO・検査中変更拒否、新12＋旧N05/版5関連6の18個別unitが10.751秒・終了0/PASS。先行未実装ImportErrorを保全、元1468源byte不変、新module/testの2源だけ追加。新FEM/seed/full/GUI/legacy0、handle60298終端。全141は90 DONE/2 IN_PROGRESS/49 PLANNED、原123は76/2/45。次はADD-N04-rf-goal-03の独立全域参照、親N04/原32要件/全goalは継続。

2026-10-13 ADD-N04-rf-goal-01 **DONE**：[版5の固定36実行/独立精度/全event費用仕様](../CURVED_RF_GOAL_EFFICIENCY_SPEC.md)。球/長球/丸め×二尺度×三方式×二反復、六元要求と全ID/壁/両R/Q/peak/全E/H/物理軸を固定。初期幾何のGreen/別P2積分差最大6.662e-16、4/8/32尺度・現行六拒否をFEM0で確認。初回probeの戻り値取扱いERRORを保全し修正。元1458源byte不変、独立候補79源と参照anchorの現存を確認。新比較器/参照package/実36行/GUIは後続02〜06、新unit/seed/full/GUI/legacy0。全141は89 DONE/2 IN_PROGRESS/50 PLANNED、原123は76/2/45。次はADD-N04-rf-goal-02、親N04/原32要件/全goalは継続。

2026-10-13 ADD-N04-boundary-remesh-06 **DONE**：[独立幾何・解析場/RF・6 nativeの受入](../CURVED_BOUNDARY_REMESH_ACCEPTANCE.md)。固定6新FEMは58.057秒・終了0/PASS。全254区間/三Green積分/4・8・32尺度、親子K/M最大1.436e-15、円筒f最大3.316e-7/両R/Q1.274e-4/E場8.152e-4を原gate内で確認。非アフィンRF尺度3.855e-14/各場成分1.402e-14、全6×10配列/54file・元Project/全RF/規約保持。追加境界/旧履歴6反例はFEM0でPASS、元数値関数AST不変。03/04のunitと05の42 GUI操作/7 FEMをsource・SHAに再結合、新unit/seed/full/legacy0、全handle終端。全136は88 DONE/2 IN_PROGRESS/46 PLANNED、原123は76/2/45。次はADD-N04-rf-goal-01、親N04/原32要件/全goalは継続。

2026-10-13 ADD-N04-boundary-remesh-05 **DONE**：[生成文書のStudy GUI/実worker受入](../CURVED_BOUNDARY_REMESH_GUI.md)。新版20・無変更旧版21・再起動復元1の計42実Chrome操作、HTTP2個別unitがPASS。queued worker中止/管理器再生成/元checkpoint再開・全保存再生を確認、元24file/各10配列保持。GUI対workerも2点の全配列/全RF一致、JSON表記とSHA差は別記。パス誤記/並行領域ロック拒否を保全し完了2点を再利用、全工程7新FEM、後続worker361.139秒・終了0。科学核/閾値不変、全handle終端、新seed/full/legacy0。全136は87 DONE/2 IN_PROGRESS/47 PLANNED、原123は76/2/45。次は06の独立幾何/専用6FEM、親N04/全goalは継続。

2026-10-13 ADD-N04-boundary-remesh-04 **DONE**：[生成条件の完全保存再生/CLI](../CURVED_BOUNDARY_REMESH_SAVED.md)。七項目文書・九検証値を全再構築し、元Project/設定/固定plan・全prefix/型/改変/予算/重複を検査。旧版/Study、原子的排他保存/中断/失敗と矩形閉式を計20個別unit（19＋1）で確認。実CLI六起動は終了0、版1/2文書API一致・再生/既定plan全byte一致。元生成bodyと当該入口以外のCLIはAST不変、FEM/RF核不変、新FEM/seed/full/GUI/legacy0。全136は86 DONE/2 IN_PROGRESS/48 PLANNED、原123は76/2/45。次は05のStudy/GUI・実worker、親N04/全goalは継続。

2026-10-13 ADD-N04-boundary-remesh-03 **DONE**：[元P2境界を分割する生成API](../CURVED_BOUNDARY_REMESH_CORE.md)。全区間/三幾何積分・Green/Hφ=r質量・親子K/M・4/8/32尺度、Case全サイズ、512/64→128/32粗化、固定履歴/事前予算/TE両端二タグ×反射を確認。初回41件40 PASS/1 ERRORを保全し、暗黙sourceがseed条件で再生成される不具合を元mesh明示で修正、一件再検査3.705秒PASS。計41個別PASS、旧bodyは版2分岐以外のAST一致、FEM/RF核不変。新FEM/seed/full/GUI/legacy0。全136は85 DONE/2 IN_PROGRESS/49 PLANNED、原123は76/2/45。次は04完全保存再生/CLI、親N04/全goalは継続。

2026-10-13 ADD-N04-boundary-remesh-02 **DONE**：[生成版2のstrict入力](../CURVED_BOUNDARY_REMESH_INPUT.md)。九共通項目＋一履歴の型/版/有限/予算/固定pattern/コピー・raw重複と旧版を、新9＋旧生成9の18個別unitで確認、16.186秒・終了0。先行helper未実装ERRORは保全。元1451対象の他1450源byte一致、新helper以外の旧module全AST一致、公開版2はまだ拒否。新FEM/seed/full/GUI/legacy0。全136は84 DONE/2 IN_PROGRESS/50 PLANNED、原123は76/2/45。次はADD-N04-boundary-remesh-03、親N04/全goalは継続。

2026-10-13 ADD-N04-boundary-remesh-01 **DONE**：[元P2境界分割を変更する生成版2仕様](../CURVED_BOUNDARY_REMESH_SPEC.md)。矩形/非アフィンの現行サイズ拒否を先に再現し、既存固定履歴で境界32/28辺・全P2/三幾何積分保存を確認。旧64→32辺の粗化と再投影の体積差2.176e-4/拒否も確認。元1444源byte不変、solve禁止の表現probeのみで新FEM/unit/seed/full/GUI0。九項目＋一履歴・七項目保存・五後続と独立6FEMゲートを固定、公開版2は未実装。全136は83 DONE/2 IN_PROGRESS/51 PLANNED、原123は76/2/45。次はADD-N04-boundary-remesh-02、親N04/全goalは継続。

更新：2026-10-13、P07/P08/P09/N03全条件受入済み。原123カードは76 DONE/2 IN_PROGRESS（H17、C07-planar）/45 PLANNED。
N04既存残件の追加13カードを含む全136カードは88 DONE/2 IN_PROGRESS/46 PLANNED。全goalと原互換32要件は継続中。
このページを現行入口とし、各文書の日付付き追記は履歴として読む。

2026-10-08 ADD-N04-selection-charts-04 **DONE**：[版2の完全保存再生とCLI](../CURVED_SELECTION_CHARTS_SAVED.md)。両Project/元requestから全参照分割・全selection・十項目を再計算して型/改竄/予算/欠落を拒否し、旧版1を維持。新saved6/旧selection8/strict JSON1の15個別PASS、7.502秒・終了0、solve guard全0。実CLI四起動は両policyのtransfer/replay終了0、保存全文書API一致。元round-trip ERRORを保全し、旧selection ASTは新helper/dispatch以外一致・CLIは三helpだけ変更。全1440対象/1227 Python源固定・他1437源byte一致、03の独立幾何/元TM/TE科学証拠を再利用。新FEM/seed/full/GUI/専用validator/legacy0。全131は80 DONE/2 IN_PROGRESS/49 PLANNED、原123は76/2/45、次は05のGUI。親N04/原32要件/全goalは継続。

2026-10-08 ADD-N04-selection-charts-03 **DONE**：[独立初期接続の版2選択移送API](../CURVED_SELECTION_CHARTS_CORE.md)。全有理親被覆と旧選択各要素の面積保存、二policy、独立番号/逆方向/非nested/frozen/非アフィンと尺度4/8/32則・原TM対称/予算拒否を確認。初回38件は35 PASS/3 import ERROR、補完初回のsibling import ERRORを保全し、新test読み込み修正後3件10.443秒・終了0。38個別PASSを分割受入、成功35件を重複実行しない。旧selection ASTと元default builderの全report/評価配列一致、元1439中他1437源byte一致・新1440対象/1227 Python源。新幾何FEM0、旧TM実6求解を観測（TE経路はwrapper未計測）、full/seed/GUI/専用validator0。全131は79 DONE/2 IN_PROGRESS/50 PLANNED、原123は76/2/45、次は04の完全再生/CLI。親N04/原32要件/全goalは継続。

2026-10-08 ADD-N04-selection-charts-02 **DONE**：[明示参照座標の版2 strict入力検査](../CURVED_SELECTION_CHARTS_INPUT.md)。七項目の未知/欠落/型/版混用、選択番号/予算、二chart/list/有限/巨大int、raw重複/NaNと入力不変を新7個別unitで確認。直接消費の旧選択移送8件と合わせ15件1.761秒・終了0。先行ImportError/1 test4 errorsを保全し、新helper以外の元module全AST一致・他1437源byte一致を監査。新1439対象/1226 Python源、新FEM/seed/full/GUI/legacy0。公開版2の計算/保存/GUIは未接続で拒否を維持、03〜06は後続。原123は76/2/45、全131は78 DONE/2 IN_PROGRESS/51 PLANNED。次はADD-N04-selection-charts-03、親N04/原32要件/全goalは継続。

2026-10-08 ADD-N04-selection-charts-01 **DONE**：[異なる初期接続への選択移送版2仕様](../CURVED_SELECTION_CHARTS_SPEC.md)。旧2/新3要素・追加軸頂点の六正常/拒否例を固定し、全有理被覆・二policy/無次元面積と物理三積分を分離。現行の版1/版2拒否を先に再現、既存chartの被覆率2/3・1/3・1/2と閉式三積分は最大相対3.331e-16でPASS。元版1の磁気対称はPASS/既存chartは拒否の差を再現し、新版callerのstrict opt-inと旧consumer不変を指定。初回fixture contour ERRORを保全して入力生成だけ訂正、新FEM/unit/seed/full/legacy0、元1432源byte不変・六例追加後1438。要求七項目/保存十項目・raw/改竄/予算・GUI・独立gateを固定し、必須五後続カードを追加。原123は76/2/45、全131は77 DONE/2 IN_PROGRESS/52 PLANNED。次はADD-N04-selection-charts-02、親N04/原32要件/全goalは継続。

2026-10-08 N08 **DONE**：[公開適応六系列/30保存水準と現行GUI30操作の受入](../N08_ACCEPTANCE.md)。公開選択/停止・RF/表面/求積とcheckpoint全文書が完全一致、保存監査の新FEM0。実GUI中止再開/上限/積分未達を確認し、直線初回の説明文FAILは保全して11+8操作で補完、曲線11操作PASS。全1432源固定、元N03全1405源byte一致と66個別PASSを再利用、1747入力/795出力再hash、全handle/12 GUIジョブ/server/browser終端。親N04は既存残件を保持してIN_PROGRESS、追加3仕様カードを[具体化](../N04_REMAINING_CARDS.md)。原123は76 DONE/2 IN_PROGRESS（H17/C07-planar）/45 PLANNED、追加3 PLANNED込み全126は76/2/48。次はADD-N04-selection-charts-01、原32要件/全goalは継続。

2026-10-08 N08 **IN_PROGRESS**：[公開適応/保存/GUIと原N04四群の受入監査](../N08_ACCEPTANCE_PLAN.md)。N07はa860099でDONE。N06/N07の三形状・固定12行/全場/費用を再利用し、六adaptive nativeを公開engine自身で再構築・保存replay照合する。元選択/停止・公開保存/再開は無変更、solve禁止・新FEM0で検査する。N03全検証の実中止再開/上限/GUIと現行関連源の一致は確認済み、原N04_ACCEPTANCEの四群を保持して監査する。原123は75 DONE/3 IN_PROGRESS（H17/C07-planar/N08）/45 PLANNED。未達が残る場合は親を閉じず、全goal/原32要件は継続。

2026-10-08 N07 **DONE**：[同じ高次native組立の実測と採用](../N07_ACCEPTANCE.md)。固定12/12 TARGETS_MET・50新FEM水準、900量別誤差を全保存配列から再計算PASS。全1432源を固定し、前後546 native file/100全場NPZは全byte・全配列・全modeで完全一致。選択/実ID/元停止/RF/求積・N06元795出力を保持し、次数24の重複組立34回を省いた。曲線8行の全体時間は同じ反復で6.2–9.2%短縮、円筒の微増とRSS増加も保持。共有は専用診断区間だけに採用し、公開適応全体の加速とは呼ばない。新9個別unit/元marked massの証拠を再利用、開発FEM6とbenchmark50を分離、新監査FEM/標本/seed/full/legacy0。全handle終端、六図視覚確認。原123は75 DONE/2 IN_PROGRESS（H17/C07-planar）/46 PLANNED、次はN08。親N04/原32要件/全goalは継続。

2026-10-08 N07 **IN_PROGRESS**：[同じ高次native組立一箇所の共有](../N07_HIGH_QUADRATURE_REUSE.md)。N06実測の24次数重複を実保存場で先に再現し、新9個別unit＋元marked mass一検査を分割受入。独立Maxwell/Green積分・親子Galerkin保存、実adaptive二水準の元場/RF/求積、厳密型/コピー変異/失効/予算/元例外/競合/threadを確認。初回RestrictedGeometry欠落と型不正の命中FAILを保全して必要分だけ訂正。開発FEM6回、元worker archive/1429源不変、新1432対象/1225 Python源。次は元N05の固定12行/二反復/目標/予算で前後実測、採用判断は未確定。原123は74 DONE/3 IN_PROGRESS（H17/C07-planar/N07）/46 PLANNED、全goal/N04は継続。

2026-10-08 N06 **DONE**：[固定12実行の独立精度/費用と終端監査](../N06_ACCEPTANCE.md)。12/12 TARGETS_MET・50新FEM水準・全900量別誤差の保存配列再計算PASS。全1430源、546 native file/100全場NPZ/1747束縛入力/795元出力を監査。円筒/丸めは一様、球は適応が確認DOF・時間で有利な範囲を二反復で報告し、一般優位を主張しない。plotだけの視覚修正は旧script/CSV/図を保全してAST同一を確認、新FEM/seed/full0。原123は74 DONE/2 IN_PROGRESS（H17/C07-planar）/47 PLANNED。次はN07の同じ高次組立の重複一原因の修正採否、N04/原32要件/全goalは継続。

N06の[元FEM/全参照/実停止とfresh直列実行器](../N06_FRESH_EXECUTION.md)を限定受入。
新15個別unit（N06計74）、実球/直線adaptiveの元prefix一致、独立全場、参照未達時の継続、
例外/費用非重複、固定12行/上限/失敗保全を確認した。検査double・元refinement名・log parserの
初回ERROR/FAILは保全し、関係分だけ訂正確認。開発新FEM23回（累計46）、12benchmarkは0。
元1425対象源不変、新1430対象/1223 Python源。新seed/full0、N06/全goalは継続。
次は同じcommit/sourceで固定12実測、両反復の量別精度/費用と全入力/出力の終端監査。

N06：[全供給点の元TM場評価](../N06_NATIVE_FIELD_LOOKUP.md)を限定受入した。
物理一次uの独立E/H微分、全候補box一致、球/円筒の実保存場と元全点/全モード値、
未確認/中断/欠測拒否を新6個別unitで確認。Case/space係数数の強化後0.583秒・終了0/PASS。
反復分は件数へ加算せず、開発FEM4回。元1419対象源は不変、新1421対象/1214 Python源。
N06計47個別unit、旧full/seedを新源へ昇格しない。N05の12benchmarkは0。
次は丸め参照格子の全点照合と元source/domain/個別ID束縛、実費用比較への接続。

丸め保存場の全格子consumerも受入：[元保存場/全域/実ID/独立参照](../N06_NATIVE_FIELD_LOOKUP.md#元丸め保存場と独立全格子の実consumer)。
全76736点/三native mode/690624成分をN03元場と完全一致で再現し、全五参照mode/三h、
全Case/source/P2境界・元matrix ID、1505束縛byteを確認。両Gauss次数の全九gate PASS。
元Uの厳密float比較FAILは検証器だけ訂正して保全、51.600610秒・終了0/PASS、
peak RSS1196466176 bytes。全1421源不変、新FEM/12benchmark/seed/full0。
これはN03保存FEM2の再生費用であり、N06の新一様/適応実測は後続。

[元保存readerから直線/曲線場へ接続](../N06_NATIVE_FIELD_LOOKUP.md#元保存readerからの直線曲線接続)
するclassmethodを追加。新二unit0.242秒・終了0/PASS、実円筒のsolveなし全mode再生一致、
未対応Case拒否/元例外/元曲線object保持を確認。旧module/六検査の全ASTは追加分以外不変。
1421対象/1214 Python源、1419点不変・二点だけ追加。N06計49個別unit。
旧二byteを明示archiveで解決し、元全格子consumerの証拠を再利用する。
新二検査の開発FEM2回、N05の12benchmark/seed/fullは0、N06は継続中。

[固定円筒/球の全域解析参照格子](../N06_ANALYTIC_REFERENCE_GRIDS.md)を新5個別unitで分割受入。
全体積/全軸、独立Ue/Um各.5 J、全P2球radial-fanと独立Green体積、全壁loss/ピーク/両R/Qを確認。
元meshキー仮定ERRORは検査器だけ訂正して0.703秒・終了0/PASS、四数学検査の元証拠を再利用。
元1421対象源は不変、新1423対象/1216 Python源、N06計54個別unit。
新FEM/12benchmark/seed/fullは0。次は共通参照packageと元保存native/domain/IDの実費用接続。

円筒/球の四[共有参照package](../N06_ANALYTIC_REFERENCE_GRIDS.md#共有参照packageの実保存終端監査)は
実生成/全配列lossless再読込/元1423源と入力・出力SHAの終端監査PASS。
0.995978秒・終了0、peak RSS89391104 bytes、新FEM/12benchmark/seed/full0。
次数16/24の完全体積/軸点を全保存し、両R/Q/全壁/解析ピークと元Case/sourceを保持する。
12独立native実行・域/実ID/量別精度と費用は引き続き実装中。

[完全Case/sourceと保存全領域の束縛](../N06_SAVED_DOMAIN_BINDING.md)も限定受入。
解析曲線が同じでも全P2境界が異なる独立反例を先に再現し、Case/source混合は元validatorの拒否を保全。
新5個別unit2.248秒・終了0/PASS、実円筒/球初回と全域細分、違う初期source/同じ曲線の別chord Case拒否、
linked/TE/遅いCSV変異と全native前後SHAを確認。DOMAIN_VERIFIEDと実ID/精度を分離する。
開発FEM6回（N06計23回）、N05の12benchmark/seed/fullは0。
元1423対象源不変、新1425対象/1218 Python源、N06計59個別unit。
次は参照bundleと元domain/ID判定・全段階費用をfresh workerへ接続し、固定12行を実測する。

## N03元条件：DONE、全検証/別seed照合終端

2026-10-08 JST：N03 **DONE**。五合成系列の元場/RF・両側二区間と失敗保全を受入。修正環境の全validate handle64569は2485検査/499モジュール、4772.019秒・終了0/PASS。0FAIL/0ERROR、skipは3件で未実行物理へ数えない。全1405対象源は開始/終端/監査時一致。seed9モードの周波数・RF207量を元相対1e-10で別照合し、最大相対差f=0/RF=8.88178e-16。既知の入力domain/scope注記だけを厳密に確認し、元Case/mesh/両PEC端・旧規約は不変。元1199源は明示した変更前三源archiveで解決し、全523bound入力を再hash。初回HTTP環境FAIL/244モジュールの終了130と元長楕円体R/Q FAILは保全。原123は73 DONE/3 IN_PROGRESS（H17/C07-planar/N06）/47 PLANNED。N04/親G03・原互換32要件・全goalは継続。詳細は[N03の条件別受入](../N03_ACCEPTANCE.md)。

主1405源の固定を解除。受入済みN06基盤を同byteで主統合した。
temp371b800の四module/四testと丸め二入力を追加し、元1405源は全byte不変、
主1415対象/1208 Python源。28個別unitの別証拠を再利用、追加前fullを新源へ昇格しない。
新FEM/seed/full/12benchmarkは0。N06はIN_PROGRESS、原123の73/3/47は不変。
次は独立参照/段階費用と均等・適応の実比較へ接続する。
[一様worker](../N06_UNIFORM_WORKER.md)は別ツリーtemp f5eaf4bで新5個別unitを分割受入し、
同byteで主へ統合した。円筒の実三水準Bessel元場/f/全壁loss/両R/Q/U1、
球の元P2境界/Ritz/ID/12・24求積/独立根RF、次solve前の上限停止/元solver失敗を確認。
検査側marker名とboundary status仮定のFAIL/ERRORは保全して必要分だけ再検査した。
開発FEM11回、N05の12benchmarkは0。元1415源は不変、新1417対象/1210 Python源。
既存fullは追加前1405源、新五unitは別証拠。独立参照判定と完全再生/resumeは後続、N06はIN_PROGRESS。

[元振幅・共通符号・量別参照/ピーク両端の有限標本leaf](../N06_SAMPLE_ACCURACY.md)を
temp611f548で新8unit0.001秒・終了0で受入し、同byteで主統合した。
手計算の0.006/1.006、Eだけ逆符号の差2、peak上端1.02のFAIL、欠測/ゼロnorm/RQ規約と
重みunderflowのUNVERIFIEDを確認。元[0,2]の下端0を欠測としたFAILは保全してvalidatorを訂正。
元1417源は不変、新1419対象/1212 Python源。六moduleは41個別unitの別証拠、新FEM/12比較0。
有限標本PASSを物理受入にしない。完全元Case/P2領域・被覆/実ID/独立参照byteとの接続は次工程。

## N06費用記録器：別ツリー限定受入、主統合待ち

追加：新プロセスの[時間/RSS超過・group停止と終端費用](../N06_PROCESS_SUPERVISOR.md)を
temp commit9d39451で限定受入した。実workerの10個別unitは1.037秒・終了0、
元1200源/既受入計測器二源は不変、temp1204/主全検証1405を確認。
全RSS欠測は非成功、退出0も物理合格にしない。丸め共有参照は全三h/五モードを保持し、
96空間点/480場vectorと保存元が完全一致、NPZ再読込も完全一致。
実参照準備4.562449秒/peak RSS1340436480 bytesは共有費用で12benchmarkには数えない。
主統合と12実比較は未実施、N03 full handle64569は固定源で継続中。

入力の追加：[共通Case/source meshと交替12行の固定計画](../N06_FIXED_EXECUTION_PLAN.md)を
temp commit8dbf122で限定受入。新5unit1.396秒・終了0、全四入力のSHA/欠落/symlink拒否と
元controls/初期領域・独立copyを確認。丸めCase/meshはN03保存元の完全同byte。
元1200＋既受入四源は不変、temp1206 Python/全1407、main全1405は固定。
最初の監査で主の生成egg-info六点のtemp不在を見落とした点数仮定は失敗を保全し訂正。
計画12行は全NOT_RUN、新FEM0。主へ入力/実装を統合して実workerへ接続する工程は後続。

計測接続の追加：[引数/返り値/元例外を保つserial呼出し観測](../N06_CALL_OBSERVATION.md)を
temp commit0c336fbで限定受入。新5unit0.001秒・終了0、独立10秒の配分・binding復元と
部分登録失敗/外部置換の保全を確認。元1200＋既受入六源は不変、temp1208 Python/全1409。
四moduleの27個別unitを別証拠として保持し、既存反復分を重複加算しない。
主1405源は固定、実FEM/12比較の計測接続と主統合は後続。

2026-10-08 JST：終端RSSの[子孫高水位scope](../N06_PROCESS_SUPERVISOR.md#終端メモリscopeの訂正)を
実プロセスで確認してtemp commit371b800で表示metadataだけ訂正した。
live worker VmHWMとwait4（回収済み子孫を含み得る最大高水位）を別に名付け、同時tree合計とは呼ばない。
旧scopeのKeyErrorを元byteで再現。検査側の不要な3倍仮定FAILは保全し、必要なselfとの差へ訂正。
同じ修正helperの既存10件PASS＋訂正した新1件0.104秒PASSを分割受入、四moduleは28個別件。
計算法AST/元10検査bodyは不変、main1405源とtemp1208/全1409を固定。N06はIN_PROGRESS。

2026-10-07 N06費用記録器 **IN_PROGRESS**：[serial stageのinclusive/exclusive・失敗/欠測](../N06_EFFICIENCY_TIMING.md)。主N03全validate handle64569の1405対象源を固定し、別ツリーで新二源だけを追加。独立18秒配分/未配賦、元失敗/中断・非有限/逆行時計・未知RSS・未完了/完成後・foreign threadを新7unit0.002秒・終了0で確認。元1200 Python源のbyte一致/temp1202固定、主統合/物理系列/予算執行/12benchmark実行は後続。N06全受入へ数えず新FEM/seed/full/benchmark0、原123は72 DONE/4 IN_PROGRESS（H17/C07-planar/N03/N06）/47 PLANNED、原互換32要件/全goalは継続。

## N03全検証：localhost環境修正後handle64569を実行中

2026-10-07 N03全validate実行条件の修正：[独立五系列の受入と節目検証](../N03_PHYSICAL_SERIES.md)。初回handle72074は244/499モジュール完了時に停止、1919.016秒・終了130・全1405源不変。HTTP一件はsocket作成でPermissionError（sandboxのOperation not permitted）、同じsource/元HTTP条件をlocalhost可の環境で再検査し1件2.792秒・終了0/PASS。数値修正/閾値変更はなく、元FAILと中断/費用を保全。原初回をfull受入へ数えず、正しい環境の全validate handle64569を新out/validation-n03-milestone-localhost-20261007で再実行中。前後開始snapshot1405は完全一致、src/tests/scripts/examplesを固定。N03はIN_PROGRESS、原123は72 DONE/3 IN_PROGRESS/48 PLANNED、N05/V01仕様DONEと親G03/原互換32要件/全goalの未完を維持。

## V01統合受入仕様：DONE（実受入は後続）

2026-10-07 V01仕様 **DONE**：[統合受入の環境/原32行F・I・O・N・W/業務/移行/配布境界](../V01_INTEGRATED_ACCEPTANCE_SCOPE.md)。現行Linux実機＋Python3.12.3/NumPy2.5.2/SciPy1.18.1を候補とし、追加OS/実業務の未決には具体的選択肢を示す。原32行を全保持し、製品の専用validator/元受入と旧対象版の未確認を対応付け、V02の新規環境/各公開保存reader、V03の固定源full＋別seed f/RF、V04の本人評価/自動UIの区別、配布allowlist/依存ライセンス/旧資産非同梱を固定。文書のみ、リンク/実在入口/32行網羅とB03依存を確認、1405全検証対象源不変、新unit/FEM/seed/full/配布0。V02〜V05/原互換32要件/全goalは未受入。原123は72 DONE/3 IN_PROGRESS（H17/C07-planar/N03）/48 PLANNED、N03 full handle72074は継続。

## N05比較仕様：DONE（N03全検証と別の文書作業）

2026-10-07 N05仕様 **DONE**：[三対照の同一初期領域・量別精度・固定費用比較](../N05_ADAPTIVE_EFFICIENCY_PLAN.md)。円筒/球とN01丸め二ローブ幾何2を選び、元Case/source/P2・両側同じ初期求解/全壁/個別ID、元五量・独立元場と二回全域確認を固定。各方式2回・順序交替の計12実行、8水準/250000要素/3600秒/32GiB・BLAS1、段階/全体時間・RSSと共有参照費用の計測境界を実行前に指定。旧球の適応非優位を保持し、精度達成と効率改善を別条件にする。文書だけの受入、新unit/FEM/seed/full0、主1200源不変。N06/N07/N08/N04と全goalは後続。原123は71 DONE/3 IN_PROGRESS（H17/C07-planar/N03）/49 PLANNED。別実行のN03全validate handle72074は継続し、src/tests/scripts/examplesを固定中。

## N03五系列監査PASS・節目の全検証中

全検証中の読取で [D07の評価leafと最終系列の不足](../D07_RF_CONSTRAINT_PREFLIGHT.md) を整理した。
D07はPLANNED、N03全受入前の実装/数値は行わない。主1200源を固定し、
次の実装は元直線候補の量別三水準評価から範囲を区切る。

2026-10-07 N03五系列の元条件監査PASS、節目の全検証中：[全域の独立場/RF・両側二区間](../N03_PHYSICAL_SERIES.md)。楕円PASS、元長楕円体のFAILは保存し追加2/3/4＋最終FEM4独立比較PASS（全1017.615秒・終了0）。元45＋追加六native、五形状の実三ID/元場/量別gate・全参照byteと1199源を終端後に再hash、監査は新FEM/標本0。版4は検証済みtemp commit81bce60と全1200源byte一致で本体へ統合、commit a907036。新7＋直接3unitの証拠を再利用し、独立比較handle22395/64791を含む旧ジョブはすべて終端。主公開は版1/2/3/4、元FEM/RF核・閾値不変。全validate handle72074を新out/validation-n03-milestone-20261007で一度実行中（2485検査/499モジュール・8 process）。主src/tests/scripts/examplesを固定し、完了前にfull受入とは呼ばない。N03はIN_PROGRESS、原123は70 DONE/3 IN_PROGRESS/50 PLANNED、親G03/互換32要件/全goalは継続。rawは out/n03-native-surface-series-20261007/completed-physical-series-acceptance.json と appended-main-integration.json。

## N03追加水準と独立参照実領域：IN_PROGRESS

2026-10-07 N03追加水準 **IN_PROGRESS**：[元失敗系列/実ID来歴/参照実領域](../N03_APPENDED_FEM_WINDOW.md)。長楕円体の元source/P2にFEM3/4六点を保存、460.209秒・終了0・1199源不変。別ツリーの版4は元plan/0・1の実Hφ来歴を保ち2/3/4を評価し、次数10/全9248000点のため資源上限16777216を明示する。新7＋直接3の10個別unit分割PASS、主版1/2/3と元物理閾値は維持、実9＋来歴2点は1034.638秒・終了0・PASS・新FEM0、temp1200源不変。独立丸め形状PASS、鋭角は非ピークPASSとSINGULARを保持。ellipse/prolateの粗参照の領域外点を保全し、参照実境界の全polar fan/体積/lookup六件を確認、体積差最大1.866e-14・欠測0。失敗二形状の独立比較handle22395と追加長楕円体の最終FEM4照合handle64791は主1199源を固定中。N03/親G03/原123/互換32要件/全goalを維持、全物理受入は後続。rawは out/n03-native-surface-series-20261007/appended-window-checkpoint.json。

## N03全行列と独立球：IN_PROGRESS

2026-10-07 N03後続 **IN_PROGRESS**：[版3全行列と独立球](../N03_CURVED_TRACKING_RESOURCES.md)。保存45点の再評価は1025.114秒・終了0・新FEM0・1199源不変。球/楕円/丸め形状は全条件PASS、鋭角はSINGULAR_GEOMETRYとnumerical PASSを別表示、長楕円体はR/Qの二変化未達をFAILで保持。同じ元メッシュ/P2幾何にFEM3/4を六点明示追加中。独立球の全領域対応/Gauss16・24/三個別ID/両側二変化/元場RFは44.191秒・終了0でPASS。解析領域外点、未分割fan体積、参照root誤記の検査側失敗を保全し、曲線partitionと単位的体積密度規約を明示した。非球形/鋭角の独立比較と追加長楕円体は続行中、実行中は1199源を固定。原123は70 DONE/3 IN_PROGRESS/50 PLANNED、原互換32要件/親G03/N03/全goalを維持。rawは out/n03-native-surface-series-20261007/matrix-and-sphere-checkpoint.json。

## N03初回系列：IN_PROGRESS

2026-10-07 N03 **IN_PROGRESS**：[元45点終端と曲線親子比較の明示資源](../N03_CURVED_TRACKING_RESOURCES.md)。SHA固定N01五形状の45/45 nativeは2995.296秒・終了0、元1197源/catalog不変。追跡予算停止を保存し、版3の宣言資源と全P2子写像検査で元場・全求積点/個別IDを評価する拡張を統合。新/直接13個別unitを分割受入、球312000点の元比較は全三ID/元場PASS・3.479秒・新FEM0。既定逆写像/262144上限・科学核/RF/閾値は不変。独立MIT固定源79を隔離uv環境へ復元、参照15＋追加10求解は終端、球粗二水準のG等FAILは保持。rawは out/n03-native-surface-series-20261007/。全行列・元場/RF/ピーク二区間・両側独立精度の受入は後続、物理上界null。原123は70 DONE/3 IN_PROGRESS（H17/C07-planar/N03）/50 PLANNED、親G03/N03/互換32要件/全goalを維持。

元handle78851と独立参照25求解、拡張unit/一比較はすべて終端。
次は保存45点を版3で再評価し、独立参照最細三水準の実H対応/両側二区間を確認する。
次の数値実行中もsource/tests/scriptsを固定し、旧失敗と費用を保持する。
N02の受入をN03物理精度/全goalへ昇格しない。

## N02全条件：DONE、次はN03

2026-10-07 N02 **DONE**：[保存3×3行列の別量評価・原条件受入](../N02_GEOMETRY_SURFACE_MATRIX.md)。厳密な全Case九点・元source mesh/個別ID・completion全byteを保持し、幾何/FEM/求積12・16・24/元場/離散peak上下界を別判定。新10＋直接7の17個別unitを分割受入。新粗い三モード九点は7新FEM＋2再利用、243.639秒・終了0、全ID/場/求積成立でも初回RQ/磁場peak未達で正しくFAIL。元楕円9 nativeは391.579秒・終了0、原五量/全変化/場/求積/全ゲート完全一致PASS、新FEM0。CLI検査側参照ディレクトリFAILとreceipt SHAキー誤記を保全し必要分だけ修正、数値再実行なし。元1194源の変更はCLI一つ、旧helper/数値body AST同一・新3源込み1197前後固定。全handle終端、新seed/full/legacy0。独立物理/物理peak誤差は未確認/nullを維持。原123は70 DONE/2 IN_PROGRESS（H17/C07-planar）/51 PLANNED、親G03/N03/互換32要件/全goalは継続。次はN03各滑らかな実精度系列・両側細分。rawは out/n02-surface-matrix-20261007/acceptance.json。

全処理handle終端、source固定解除。次はN03の元五Case・45点を専用validatorで実行し、
原二区間条件・独立参照の有無・費用を記録する。粗い反例や旧一モード楕円を新精度受入へ昇格しない。

## N02場対応工程：IN_PROGRESS

2026-10-07 N02場対応工程 **IN_PROGRESS**：[元P2場・個別ID・欠測の比較](../N02_GEOMETRY_SURFACE_FIELDS.md)。元Hφ/Er/Ezと単一符号・絶対軸Ez、全centroid/重み/欠測を保存し、固定P2はN01の強い追跡も要求。振幅2%/直交不一致/ゼロ軸/真の順位交換/近縮退・予算停止、実2 FEM/3モード・completion全byte/保存完全再生・CLI一致/後export変異を確認。新10＋直接4の14個別unitを分割受入。ゼロ軸FAILをUNVERIFIEDへ修正し、Case製造ERRORの1件だけ再検査。旧楕円の9 native/8元場区間は166.641秒、終了0、元Study報告完全一致・全欠測0・新FEM0。旧1モードの互換証拠を新3モード/独立物理へ昇格しない。元1192源の変更はCLI一つ、科学核/閾値とarchive数値bodyは不変、新2源を加え1194・全handle終端。新seed/full/legacy0。原123は69 DONE/3 IN_PROGRESS（H17/C07-planar/N02）/51 PLANNEDを維持。次はN02保存3×3行列の五量/幾何/求積/peak別評価、親G03/N03/原互換32要件/全goalは継続。rawは out/n02-surface-fields-20261007/。

全処理handle終端、source固定解除。
次はSHAで結んだ新保存3×3行列に、独立幾何/固定FEM二変化/求積12・16・24/peak区間二変化を追加する。
故意のピーク未収束・幾何未確認と、旧楕円全量の新集約判定一致までN02を閉じない。
その後N03実精度検証→D07。全goalは未完。

## N02入力・来歴工程：IN_PROGRESS

2026-10-07 N02第一工程 **IN_PROGRESS**：[幾何/表面比較の入力・来歴計画](../N02_GEOMETRY_SURFACE_PLAN.md)。五Case/全45点のstrict指定、独立面積・体積/全曲線/鋭角、解析球の元根条件、旧4 reportのSHA/PASS/楕円区間、欠落UNVERIFIED・自作FEM参照拒否、排他的保存/完全再生を接続。新8＋直接6の14個別unitを分割受入、実CLIのplanned45/newFEM0も確認。初稿baseline項目・affine selector誤記は失敗を保全して必要分だけ修正。元1190源の変更はCLI一つ、旧数値全関数/楕円数値bodyはAST同一、新2源を加え1192。新FEM/seed/full/legacy0、全handle終端。N02の実保存場・5種差分/反例・楕円新判定再生は後続。原123は69 DONE/3 IN_PROGRESS（H17/C07-planar/N02）/51 PLANNED、親G03/N03/原互換32要件/全goalを維持。次はN02保存行列・場/ピーク/求積の比較。rawは out/n02-geometry-surface-plan-20261007/。

全処理handle終端、source固定解除。数値/FEM実行は0。
次は元保存3×3行列と個別ID、幾何/FEM/求積/場/peak差の実報告。
共通領域の被覆・欠測を記録し、未収束/場不一致/幾何未確認の反例と旧楕円判定一致を確認する。
N03実検証の後にD07、N02未完のまま親G03/N03や全goalを閉じない。

## N01仕様：DONE、次はN02

2026-10-07 N01仕様 **DONE**：[幾何3×FEM3・元場/RF/ピーク/独立参照の五合成ケース](../N01_GEOMETRY_SURFACE_CASES.md)。球/楕円の旧成功と元五量閾値を保持し、長楕円体・接線連続丸め二ローブ・鋭い導体先端を固定。五Case/15幾何入力のstrict解析、独立面積/体積とsmooth/singularをmetadataだけで確認。初稿端点projection UNVERIFIEDを保全し別明示寸法を選択、製品/閾値は変更せず1190 Python源不変。独立非球形Maxwell/物理peak参照はnull/未確認のままA01固定隔離環境と許可済みblack-boxの経路/両側細分を指定。図を目視確認、新FEM/unit/seed/full/legacy0。原123は69 DONE/2 IN_PROGRESS/52 PLANNED、親G03/N03/原互換32要件/全goalは継続、次はN02。rawは out/n01-geometry-surface-cases-20261007/。

数値/FEM検証は未実行。全源固定解除、live numerical handleなし。
次はN02のcatalog入力一般化・幾何/FEM/求積/元場/peakの別報告と、
故意の未収束/場不一致/幾何未確認・独立参照欠落の拒否を実装する。
N03実検証後にD07へ進む。

## D06原条件：DONE、次はN01

2026-10-07 D06 **DONE**：[元直線TM候補の実座標探索/三水準個別ID/所有保存再開](../STRAIGHT_RF_CANDIDATE_SEARCH.md)。3形状で両変数6候補/18 FEM、独立Bessel f/H/E/全壁loss/両R/Q、実順位交換ID、invalid候補FEM0・曖昧2モード即停止・予算/祖先保全を確認。先行33＋新8の41個別unitを分割受入。曲線版1〜3の10元試行/30 native水準を完全再生（新FEM0）。検査側mass/contour条件・端点1 ulp ERRORを保全し不足分だけ再検査。全RF assessment null、例の18 FEM成果物もFINAL_UNVERIFIEDを保持。旧数値AST/許容差不変、1190源の検査修正以外固定・全handle終端、新full/seed/legacy0。原123は68 DONE/2 IN_PROGRESS/53 PLANNED、親D03/原互換32要件/全goalは継続。次はN01（N02/N03→D07の依存準備）。rawは out/d06-straight-native-search-20261007/acceptance.json。

全製品/数値源固定・全handle終端、source固定解除。
次はN01の幾何3水準/FEM3水準・独立参照・場/RF/peakの元精度条件を確認する。
N02/N03を先に満たしてからD07へ進む。D08も依存成立、D04はH18/P10/C07-TE待ち。

## D06第一工程の履歴

## D06第一工程：候補台帳、IN_PROGRESS

2026-10-07 D06第一工程：[直線TMの多変数候補台帳](../STRAIGHT_RF_CANDIDATES.md)。元Project/全境界owner/SI式から3形状を独立生成し、変数/候補順・分割再開の実形状一致、invalid候補と上限・null assessment/IDを保存。新6＋直接25＋単変数物理2の33個別unitを分割受入、実段差2 FEMのH/E尺度差最大4.498e-14。TE selector誤記loader ERRORは元logを保全し正しい1件だけ追加。旧RF全関数AST/5入口源byte不変、1188 Python snapshot以後不変、全handle終端、新full/seed/legacy0。既存RF入口の能力規約は維持。D06はIN_PROGRESS、探索器/実候補ID・所有solve checkpointと全条件監査が残る。原123は67 DONE/3 IN_PROGRESS/53 PLANNED、全goal/原互換32要件を維持。rawは out/d06-straight-candidates-20261007/acceptance.json。

次は同じ元候補を座標探索・実native個別ID/所有solve履歴へ接続する。
D05の能力規約に従い、収束評価未実装の量を目的/制約として受け付けない。
全handle終端、source固定解除。

## D03原条件：DONE、次はD06

2026-10-07 D03原カード **DONE**：[直線TE調整の原条件監査](../STRAIGHT_TE_TUNING_ACCEPTANCE.md)。元版9法則をTE Eφ/対称半領域/鏡映・固定RF/N/Aへ接続し、独立Bessel f/Eφ/Hr/Hz/全PEC壁loss、実段差/独立細分/両端二偶奇、未確認/無効形状停止・所有保存再開を照合。追跡39＋調整35の74個別unitを源/元logに結合し、実Chromeは分割9項目PASS。API/CLI/GUIの元要求/decision/最終Eφ/Hr/Hzと7 RF量は相対差0、両R/Q N/A、表示importの元6科学ファイルbyte一致。磁気対称段差は通常/鏡映とも元10 kHz条件内8.974 kHz、閉PEC/電気対称25.043 kHzと粗折返し輪郭1.348 MHzの未達は保持。混在端がsampleへ進む反例を先に再現して拒否を追加。検査のcontour boundaries、独立peak振幅係数、RF表の行/列selector ERROR/FAILを保全し、不足分を修正して再検査した。1279源固定・全handle/server/browser終端、slot 0、新full/seed/legacy0。D03だけDONEへ変更、原123は67 DONE/2 IN_PROGRESS/54 PLANNED。親P01/D02/全goal/原互換32要件は継続。次は依存成立のD06、D04はH18/P10/C07-TEを待つ。rawは out/d03-whole-acceptance-20261007/acceptance.json。

D06はD02/D05の依存成立。元直線TM法則によるRF探索候補、invalid candidateと
未確認/細分条件の保持を実装・検証する。D07の収束/独立評価とN03は別条件で保持する。
全handle/server/browser終端、source固定解除。全goalは未完。

## D03限定受入の履歴

## D03直線TE追跡コア：IN_PROGRESS

2026-10-07 D03第一実装：[直線TEの元Eφ/回転体積・鏡映追跡](../STRAIGHT_TE_TRACKING.md)。独立非一様体積積分で現行Hφ読取KeyErrorを先に再現し、schema1の元Eφ専用比較を接続。元セクター/通常・鏡映混在/全境界をsample前に拒否し、元半meshを全鏡映領域へ導出する。新10＋直接消費29の39個別検査を分割受入、実段差/折返し/保存完全再生・両端/二偶奇/P1/P2・真の二ローブsample・G/QとEφ/Hr/Hz尺度則（最大4.637e-15）/両R/Q N/Aを確認。低overlapのmatches空配列を参照した検査ERRORを保全し、元overlap_matrixの検査へ修正。1184 Python源固定、旧製品変更2ファイル/3関数、科学核/RF閾値不変。新full/seed/legacy0・全handle終端。D03だけIN_PROGRESS、全123は66 DONE/3 IN_PROGRESS/54 PLANNED。版9TE調整/独立細分/操作接続とD03全監査、全goal/原互換32要件は未完。rawは out/d03-te-straight-tracking-20261007/acceptance.json。

次は元版9法則をTE調整へ接続し、Bessel円筒のf/Eφ/Hr/Hz、
実段差/独立細分と対称偶奇、未確認停止・保存再開を検査する。
現行版9のTE拒否を維持して追跡コアだけ先に受入。全handle終端、source固定解除。

## D02原条件：DONE、次はD03

2026-10-07 D02原カード **DONE**：[直線TM調整の条件別監査](../STRAIGHT_TM_TUNING_ACCEPTANCE.md)。D01法則からの試行/追跡/独立細分/保存再開、独立円筒f/H/E/壁loss/両R/Q、実段差の元境界/体積/個別ID、無効中間形状の求解前停止、API/CLI/実Chromeの元要求/最終場/両R/Q一致を原6条件群で照合。52個別unit＋実Chrome7項目を源/元logへ再結合し、監査内の新FEM/unit/full/seed/legacy0。一般折返し輪郭は正しい未達停止/完全再生を受入し、追加二系列の差71.166/31.378 kHzをTUNEDへ変更しない。初稿監査の「折返し輪郭成功」は原カードを超える追加条件だったため、原文との照合記録を残し、原条件へ戻した。全1275源固定・全handle/server/browser終端、slot 0。原123はD02だけDONEへ変更、66 DONE/2 IN_PROGRESS（H17/C07-planar）/55 PLANNED。親D02/P01/全goal/原互換32要件は継続、次はD03（TE階段/一般輪郭）。rawは out/d02-whole-acceptance-20261007/acceptance.json。

D03の受入条件はTE Eφ独立解析、実段差と独立細分・対称偶奇、
未確認停止/所有保存再開。TM境界条件を流用せず、現行版9のTE拒否を維持して着手する。
既存曲線TEの受入を再実装へ戻さない。全handle/server/browser終端、source固定解除。

## D02限定受入の履歴

## D02コア限定受入：IN_PROGRESS

2026-10-07 D02操作限定受入：[版9直線TMのGUI/入口一致](../STRAIGHT_TM_TUNING.md#guiと入口一致)。実Chromeで版9法則がlinearへ誤復元される不具合を終了1で再現し、専用法則入力・元Project/追跡条件復元・raw法則のstrict parser渡しを修正。既存checkpointから追加検索/細分へ再開し、完全要求再構築、重複キー求解前拒否、保存/改竄拒否、二周波数gate、追跡順位の最終場表示の7項目PASS（終了0/外部通信0）。独立API/CLIの元要求・decision・元最終H/E・9 RF量/両R/QはGUIと相対差0、表示importの元6科学ファイルもbyte一致。比較runnerのファイル名誤りを終了1で保全し、原nativeを読み直すだけで終了0に修正（追加求解0）。全1275源固定、Python科学核/52個別検査の源不変。全browser/server終端、slot 0、新full/seed/legacy0。D02全条件/一般輪郭成功系列は後続、全123/原互換32要件/全goal継続。rawは out/d02-straight-gui-20261007/leaf-audit.json。

2026-10-07 D02コア限定受入：[直線TM形状法則](../STRAIGHT_TM_TUNING.md)。版9の元全境界owner/SI式/まとめた座標更新・実区分比較を通常tune、最終細分、保存再開、版6回復wrapperへ接続した。新metadata6＋実物理6＋直接消費40の52個別検査を分割受入。独立円筒Bessel f/H/E/全壁loss/両R/Q、実段差の元場尺度則・完全再生、無効中間形状の求解前拒否、曖昧ID停止を確認。粗段差83.248 kHzは失敗を保持し、角局所細分の別系列は元10 kHz条件内6.240 kHzでTUNED。一般折返し輪郭は元1 Hz細分条件未達を保持。検査側ERRORと粗系列FAILの元logを保全し、成功済みケースは繰り返さず不足分を補った。1182源の固定、旧製品変更2ファイルの4関数に限定、科学核/RF定義/許容差不変。全handle実終端、新full/seed/legacy0。D02はIN_PROGRESS（実GUI/API/CLI一致と全条件監査が残る）、全123は65 DONE/3 IN_PROGRESS/55 PLANNED、原互換32要件/全goal継続。rawは out/d02-straight-tuning-20261007/bounded-audit-pre-docs.json。

次は一般輪郭の実成功系列とD02全原条件監査。全handle/browser/server終端、slot 0。

## D01仕様：DONE、次はD02

2026-10-07 D01仕様 **DONE**：[非曲線TM/TEの形状・区分写像・対称/最終細分](../NONCURVED_TUNING_SCOPE.md)。profile/階段/単一一般輪郭の六正常/拒否要求と元追跡先を固定。現行profile正常2、未対応4、不正6、将来六領域の両bounds/面積・体積尺度と不正拒否、未実装版9拒否、TE異セクター事前拒否をmetadataだけで確認。136式は既存SI parserに適合し、初稿leaf拒否/runner引数順ERRORを保全して修正。製品/テスト/script1179源不変、新FEM/unit/seed/full/legacy0。現在の区分TM追跡と不足するTM調整/TE直線区分追跡を分離し、既存曲線TEを再実装へ戻さない。原123台帳はD01状態だけ変更、65 DONE/2 IN_PROGRESS/56 PLANNED。D02/D03実装・親D02/P01/全goal/原互換32要件は継続、次はD02。

D02の受入条件は、元Project/固定区分法則からの実TM試行・個別ID・独立細分、
無効形状停止、API/CLI/実GUIの元要求と最終場/両R/Q一致。直線schema9のTMコアは限定受入済み。実GUI/API/CLI一致と全条件監査が残る。
影響先はtuning・saved_mode_tracking・piecewise tracking・jobs/gui_tuning。
[仕様の全六要求と検査](../NONCURVED_TUNING_SCOPE.md)とTESTINGから必要な直接消費検査を選ぶ。
処理handle/worker/serverはなし。H17/C07-planarの未確認を保持して実装可能なD02を進める。

## D09全原条件：DONE

2026-10-07 D09全原条件 **DONE**：[Hφ RF評価の条件別監査](../HPHI_RF_DESIGN_ACCEPTANCE.md)。単一/材料/直線真空/曲線P2の四受入receipt、独立同軸TEM/TM・一様/二層・全PEC壁・有効/不正軸経路、実個別E/H・有限guard・量別二変化/全包絡採用・保存完全再生を照合。過去76個別test IDの源/元log hashを再結合した読取監査で、新FEM/unit/seed/full/legacy0。粗曲線の数値未達はUNVERIFIEDを維持、peak/連続誤差は保証しない。過去真空receiptのコマンド表記5件（二重method suffix）は元記録を保全して訂正版を別保存。原123台帳はD09状態だけ変更、64 DONE/2 IN_PROGRESS/57 PLANNED。H17追加損失判断・D10-hphi探索運用・親D03/原互換32要件/全goalは未完。次は依存が揃ったD01の非曲線TM/TE形状対応仕様。

実装コミット `c91583a` と全四receipt、同軸TM原15byte hashを照合。
rawは `out/d09-whole-acceptance-20261007/conditions.json` / `audit.log`。
過去の限定受入/「次は」の節は当時の履歴。現在の次工程はD01で、D10-hphiの先行D07は未受入。
H17/C07-planarの資料・環境未確認を保留したまま独立カードを進める。

## D09限定受入の履歴

## D09曲線三水準：限定受入

2026-10-07 D09曲線三水準の限定受入：[完全P2参照・元chart/実個別E/H/全PEC壁RF](../CURVED_HPHI_RF_CONVERGENCE.md)。新8＋直接消費8＋独立同軸TM追加1の17件は分割PASS・全実終了0。解析TEMとTMのf/H/E/壁loss誤差減少、真正曲線穴の全領域/壁・尺度則と粗系列UNVERIFIED、strict能力・guard/予算/phase・保存移動/型偽装/元変異拒否を確認。等価な有理chart表記のFEM0反例を修正し、元数値AST/正常chartを保持。初期1177/修正後1178源の固定と元423製品源中421不変を監査。最後の保存完全再生1件1925.090秒も終了0。原同軸TM三nativeを保存後、NumPy scalar拒否のrunner ERRORを保全し、float入力で元場を再利用した1件49.705秒を受入。専用validatorは成功数値core/元creatorとsource結合し、CLI help/既存出力拒否を別確認、全数値CLIの重複求解は実施しない。rawは out/d09-curved-rf-convergence-20261007/acceptance.json。D09全条件監査は後続、全123台帳・原互換32要件・全goalを維持。科学核/旧RF定義/許容差不変、新full/seed/legacy0、全handle終端。

rawの `observed-handles.json` は全handle終端/live=[]。保存完全再生3558も実終了0。
数値固定は解除、専用TM validator配置は全終端後に実施。全数値coreと元creatorを既存実結果へ結合し、
CLI help/既存出力拒否だけを追加確認した。次はD09の原条件別監査・記録と状態判定。

## D09直線真空三水準：限定受入

2026-10-07 D09直線真空三水準の限定受入：[元個別E/H・有限guard/全PEC壁・RF制約](../VACUUM_HPHI_RF_CONVERGENCE.md)。新同軸1件25.044秒、軸/一般穴2件96.598秒、残新4件210.948秒、追加実ID順序継承1件58.180秒、直接消費17件54.389秒は実終了0。独立TEMとBessel TM010のf・元E/H・全壁loss/RQ誤差は各水準で減少。粗い一般穴はID成立でもf/E/局所壁gate未達をUNVERIFIEDに保持。保存移動/型偽装/遅い元変異・phase・guard/予算/数値未達と実二ID順序入替え拒否を確認。全25検査の分割受入で、既存422製品ファイル中420不変、旧RF評価定義/科学核/許容差不変、旧optimizerは三import追加だけ。元数値開始snapshotと追加検査源を別に固定し、全123台帳・D09 IN_PROGRESSを維持。全handle終端、新full/seed/専用validator/legacy0。曲線三水準/D09全条件と全goalは継続。

raw/元source/台帳の監査は `out/d09-vacuum-rf-convergence-20261007/acceptance.json`。
次は曲線P2全参照/元chartを保つ専用RF三水準アダプタ、その後D09全条件監査。

## D09材料三水準：限定受入

[元全材料/個別E・H/有限guardと量別RF・制約](../MATERIAL_HPHI_RF_CONVERGENCE.md)を限定受入。
独立二層TEM三水準の新1件103.018秒＋残新5件1168.208秒、直接消費15件61.074秒は実終了0。
原領域IDを入れ替え同じIDの体積が半減するメタデータ反例は終了1。初回runner root欠落ERRORも保全。
数値終端後に隣接material/region対応のidentity拒否Ifだけ追加、新1件7.140秒（FEM0）がPASS。
全22検査を分割受入し、元科学AST・元全テストASTはarchiveと完全一致、追加Ifは既存正常fixtureでfalse。
既存421源中419不変、既存adapterには四関数追加/旧全AST不変、既存探索には三import追加のみ。
数値段階1368 hashとarchive/現行の互換監査を行い、文書/拒否追加のために数値を再実行しない。
全123カード・D09 IN_PROGRESS・原条件/依存は維持。全handle終端、生存処理/worker/browserなし。
raw/受入監査は `out/d09-material-rf-convergence-20261007/acceptance.json`。seed/full/専用validator/legacy追加0。
次はD09真空/曲線の三水準アダプタ。元E/Hの個別IDと有限guardを別に要求し、
各水準の実選択rankを使い、同順位診断をID追跡へ読み替えない。曲線壁は元二次referenceへ全積分を集約する。
D09全原条件・親D03/原互換32要件/全goalはACTIVEで継続する。以下の第一実装は既存履歴。

## D09第一実装受入履歴：五nativeのRF観測

[能力判定/元全RF量/保存再生](../HPHI_RF_DESIGN.md)を第一実装。新6件9.674秒＋直接利用18件51.316秒は終了0。独立同軸TEM/二尺度・一様/二層のf/場/全壁loss、五native・有効真空軸/両R/Q・移動再生/変異拒否を確認。単一場はUNVERIFIED/採用値・個別ID null。旧420源の科学定義は全不変、新adapterと既存入口importのみ。次は専用三水準/元E・H個別ID/guardと量別収束・包絡採用。D09全原条件・親D03/全goalは継続。全handle終端、seed/full/専用validatorの追加実行なし。

## D05仕様受入と次の開発

[物理別の目的/制約・能力/N/A](../RF_OPTIMIZATION_SCOPE.md)を受入した。現行六量を変えず、追加評価と探索運用の後続範囲を固定。全体のrefinement未確認は局所METを覆し採用値null、初期/最終は独立三水準、静的設計/熱はL02/L03。読取監査のみ、420製品源不変、新FEM/unit/seed/full/legacy実行0。既存fullの関連結果を重複実行数へ加算しない。原123カードはD05の状態だけを変更、親D03/原互換32要件/全goalは継続。

## 現在の受入状態（2026-10-07、P09 DONE）

[P09元14条件＋追加公開不変量の最終監査](../PLANAR_CURVED_TRACKING_TUNING_ACCEPTANCE.md)を受入した。
円TM/非円形TEの両周波数gate、元E/Hと実順位/過去anchor、固定二次境界・全元場、
曖昧/予算不足停止、所有移動/再生、実CLI-worker取消し/再起動/再開、実Chrome/大容量保存を確認済み。
16歴史的receipt/91 entryのhashと科学源互換性を最終照合し、限定証拠を新規全実行数へ加算しない。

元全validate handle60083は2354検査/478モジュール、3200.524秒、2FAIL・5ERROR・3skipで終了1。
途中JSON公開による実取消しERRORと分類/検証器の失敗を保全した。
[共有checkpointの完全公開](../PLANAR_CHECKPOINT_PUBLICATION.md)を修正し、元JSON byte/上書き拒否を維持。
限定45検査66.391秒＋実取消し/移動/再開/管理器再作成1検査40.442秒は終了0/PASS。
保存2源の変更定義は `_write`/`execute_planar_tune` のみ。他7/9定義は元archiveとAST同一。
歴史的大容量GUIの420源不変（e395996基準）と今回の保存2源変更を区別する。

修正後の全validate handle69844は別root `out/validation-p09-publication-20261007` で終了0/full PASS。
2359検査/479モジュール、3215.343秒、失敗0/エラー0/skip3、全1366源は開始/終端/P09受入時一致。
事前全discoveryの重複実行なし。元5失敗モジュールと共有保存消費先も成功した。
seed9モード/207量は相対1e-10で別照合、最大相対差f=0/RF=8.881784197001248e-16。
初回metadata全体一致AssertionErrorは保全し、既知domain/scope注記を厳密確認、
Case/mesh/閉PEC端/全旧規約一致を要求してPASS。数値許容差は変更していない。
任意NGSolve2件と専用native rootを要する1件のskipを実行済み物理へ数えない。
専用円/TE取込・移動再生は既存実検査865.527秒PASSの限定証拠として維持する。
raw終端/最終監査は `out/p09-checkpoint-publication-20261007/new-full-terminal.json` と
`p09-final-acceptance.json` / `p09-final-card-audit.log`。監査は新FEM/物理再生0。
生存handle/worker/serverはなし、歴史的Chrome slot 0、源固定解除。文書用の数値再実行なし。
P09だけをDONEへ変更し、全123カードの内容/依存と原互換要件を維持した。

## C07-planar進行中：参照比較準備

元入力16件（polygon/区分試行/曲線両偏波/尺度・非一様・true doublet）をhash/receipt付きで追加した。
矩形6を含む22行/106入力の生成は終了3。全case byte/全二次midを保持、準備内FEM/再生0・旧実行0。
前回NG commandの汎用solve拒否を実終了2で再現しsolve-planarへ修正。新4＋前回12の16件1.097秒PASS、
読込エラー処理追加後の関連4件0.292秒PASSは再検査。unit内矩形CLI/FEMは計2回、局所解析f/1 J/m/両R/Q N/Aを確認。
`docs/planar_superfish_source_catalog.json` と `out/c07-planar-scope-20261007/scope-acceptance.json` が入力/証拠を束縛する。
曲線/任意polygon AFの未用意はnull/理由付き、legacy四量/全受入軸と実対応/両側細分はUNVERIFIED。
製品420源と全123台帳不変、生存handleなし。次は原C07条件ごとの欠落と再実行入力契約の監査。

[矩形候補と全未確認ケース表](../PLANAR_SUPERFISH_COMPARISON.md)を既存比較入口へ接続した。
二尺度TE10/TE01/TM11の6ケース/18水準/90入力、終了3（UNVERIFIED）、旧/NG新求解0。
新5＋旧比較7の12検査0.772秒は終了0。四量・F/I/O/N/W・実モード対応と両側細分は全未確認。
Wine/Xvfb/以前のprefixが不在。7.17の偏波/場成分/単位長量を推測して変換しない。
P09受入後の変更は比較入口/新準備helper/新offline検査と文書で、製品src420源は不変。
P09直前全検証と今回の限定検査を重複集計しない。現行処理の生存handleなし。
上記元領域表へ入力を対応付けたが、旧版入力/四量/両側実細分の受入は残る。
C07-planar全条件と全goalは継続し、未確認をPASSへ変えない。

## 横断レビューと計画（2026-09-22）

この節は作成時の履歴。2026-10-13の組込みと現行着手順は冒頭の「科学レビュー後の挿入工程」を参照する。

ユーザー依頼のREVIEW-01として、`a191b4e`基準の[既存実装レビュー](../IMPLEMENTATION_REVIEW_2026-09-22.md)と
[リファクタリング計画](../REFACTORING_PLAN.md)を作成した。所見10件とRF-01〜RF-10の依存・受入・検証・撤回方法を記録。
依存不在のGUIテストエラーを限定再現したが、製品・テスト・検証器は未変更、修正カードは全てPLANNED。
次にリファクタリングを実施する場合の推奨はRF-01（検証来歴）→RF-02（環境/任意依存）。
既存115開発カードの状態は維持する。以下は既存機能開発の次着手であり、今回の文書作成の継続作業ではない。

## 次の着手

**[D09：HφのRF制約評価を追加する](04-design.md#d09)**。先行D05/H16はDONE。
真空/内導体/確認済み材料の全領域・全PEC壁と有効な真空軸経路を専用評価へ接続する。
同軸/一様材料/二層のf・場・壁loss/保存再生を別確認し、未実装peak/損失と軸無し加速量の拒否/N/Aを保つ。
H17追加損失の採否は対象版資料待ち、未受入モデルを追加しない。
C07-planarは既設Wine実行ファイル/prefix情報の回答待ち。元条件と22行/106入力、全UNVERIFIEDを維持する。
参照環境に依存しない開発を続け、leaf受入を全goal完了へ読み替えない。

## P07〜P09の受入履歴

**[P09：平面曲線の比較・調整を接続する](03-planar.md#p09)**。先行P04/P08はDONE。
[P07全条件監査](../PLANAR_CURVED_ACCEPTANCE.md)で二尺度円絶対/固定最終差/独立A/B、求積、
八幾何系列、楕円・再入角両偏波、共変則、五source bridge/三補足と主source統合を受入した。
元失敗・全raw/source/archiveを保持し、最終主401は受入kernelと完全一致、元主源から四変更/397不変。
最初の有界変更として[版3専用native](../PLANAR_CURVED_NATIVE.md)の全配列/RF再構築・改変拒否を実装。
新7件＋旧版1/2直接利用5件は終了0/1.684秒PASS。曲線/共有P2/seedの数値源は変更していない。
続く[共通Case/Project/CLI-worker/Study/表示](../PLANAR_CURVED_OPERATIONS.md)を実装。
新9件は7件＋修正2件の分割受入、直接利用先48件32.964秒PASS。実worker中止/終端/新job再起動・元byte importも確認。
続く[P08全条件監査](../PLANAR_CURVED_OPERATION_ACCEPTANCE.md)で、実Chrome15＋旧13＋新server7、計35項目を受入した。
全元五native/全RF/12場、Project往復/元byte import、曲線Study・中止/新job/別server再生がPASS。
専用数学は不変、全403実装hashも各browser実行中不変、外部要求0。全job/両server終端、Chrome slot 0。
元FAIL/成功・全rawを保持し、新FEM0の最終hash監査をPASS。P08をDONEとする。
Project/dispatcher/CLI-worker/Study/GUIと実中止/再起動/旧版再生はP08の必須範囲。
上記APIと実ブラウザー・全条件監査を別に受入し、限定unitだけで完了へ数えていない。
P09の[元二次写像・完全比較分割](../PLANAR_CURVED_COMPARISON.md)は新7＋関連12、19件2.151秒PASS。
全mid・全被覆・全PEC・累積予算と独立面積/一次moment/正逆を確認し、元403製品不変。
P09の[元E/H自己・交差Gram](../PLANAR_CURVED_FIELD_COMPARISON.md)も新8＋関連10を分割受入。
strided解の導出診断末尾bitを修正し、微小residualでも未解決energyを拒否、元404製品不変。
[固定二次境界の有限guard](../PLANAR_CURVED_SPECTRAL_RESOLUTION.md)も新4＋関連6、10件3.689秒PASS。
TE/TM dense spectrum・二尺度/回転・全予算preflightを確認し、元405製品不変。
[元E/H追跡核](../PLANAR_CURVED_TRACKING.md)も新8＋既存14を20＋追加1＋追加1で受入。
実TE楕円rank交換は反射parity/全RFと照合、円doubletと周波数一致/E不一致は個別IDを発明しない。
元406製品不変。[専用個別ID回復核](../PLANAR_CURVED_IDENTITY_RECOVERY.md)も新4＋関連6、10件26.658秒PASS。
実反射parity/rank交換→回復→後続と全元byte/RF、真縮退/guard/集合越境/予算停止を確認、元407製品不変。
[元全二次節点の形状則](../PLANAR_CURVED_SHAPE_LAW.md)も新4＋関連4、8件1.249秒PASS。
proper affineの全区間det・全mid/PEC・実円f/energy/G/Q尺度、元408製品不変。
[検索/最終trial生成](../PLANAR_CURVED_TUNING_TRIALS.md)も新4＋関連11、15件10.289秒PASS。
元全六節点の独立式・累積元chart/512ε/全PEC・全予算preflight・実元E/H energy/全RF、元409製品不変。
[実FEM調整・二gate・完全native再生](../PLANAR_CURVED_TUNING.md)も新8種類＋関連11を分割受入。
円TMの解析絶対差/二gate、非円形TEの独立dense spectrum/反射parity付き実rank交換・検索/最終anchor回復、
真doublet/上位guard/予算停止とnull周波数、先行全byte保全・異試行/保存改変拒否を確認した。
絶対係数差の検査誤り・不正checkpoint入力拒否を修正し元FAIL/rawを保持。
元410製品と全123カード台帳/依存/文書anchorは不変、全handle実終端。
[所有調整・移動後完全再生](../PLANAR_CURVED_TUNING_SAVED.md)も新7種類＋関連3を分割受入。
元九byte/claim/creator、相対prefix/初回・途中失敗checkpoint/別owner再開、strict/再hash拒否を確認。
元受入円TM/回復付きTEの全取込・移動再生1件865.527秒PASS、両gate/元RF/全ID/過去anchor一致。
元411製品/全123カード不変、元rawと失敗を保持、全handle実終端。
[所有二点・独立履歴/過去anchor・移動再生](../PLANAR_CURVED_TRACKING_HISTORY.md)も新13種類＋関連10を分割受入。
native五/完了job九/import job八の元byte/Project/creator/claimを保持し、反射parity付き実rank交換、
円subspace→過去anchor回復→後続継承、新owner回復/延長、誤anchor/断絶/ID置換/真縮退/guard/max停止を確認。
後のコピー中に先のsourceを変える検出漏れを実再現・修正。変異試験の相対path誤りも明示し元FAIL保全。
修正2件8.128秒、通常/移動/import3件44.114秒、関連10件41.362秒PASS。
最終byte監査PASS：元412製品/全123カード・依存/anchor不変、9所有履歴/23内包二点を照合、全handle実終端。
[所有比較CLI-worker](../PLANAR_CURVED_TRACKING_JOBS.md)も新6種類＋関連10を分割受入。
元五/九byte/creator・元source移動後worker完了、kind降格/再hash報告拒否を確認。
実running取消し−15→新job終了0→管理器再起動/移動後完全再生、実CLI PASS=0/guard=1。
初回1件8.741秒、安全3件13.829秒、runtime2件25.711秒PASS。
関連9成功/1読込ERROR（指定名誤り）を保持し、不足1件1.800秒PASSで補完した。
最終監査PASS：元414源の変更はjobs/cliへの入口追加のみ、元412科学/その他源と全123カード不変、全handle実終端。
[独立履歴CLI-worker](../PLANAR_CURVED_TRACKING_HISTORY_JOBS.md)も新8＋関連5を分割受入。
元二点/比較job全byte/creatorとnative/ID連鎖、実過去anchor・親不変/optional回復付き延長、
誤anchor/投入変異/再hash回復fの拒否、true doublet/guard/max停止を確認。
初回1件30.142秒、安全3件80.759秒、回復/停止2件142.987秒、実worker/CLI2件199.504秒、関連5件43.202秒PASS。
実running取消し−15→新履歴・回復・延長worker全0、管理器再起動/移動後全再生と全CLI/終了コードも確認。
生存中の元native/二点移動もworker caseだけを強化して1件115.147秒追加PASS、他7新method不変。
最終監査PASS：17完了履歴job/73二点snapshot、全416作成源、元415源の変更はjobs/cli入口追加のみ、413源/全123カード不変。
[所有調整CLI-worker](../PLANAR_CURVED_TUNING_JOBS.md)も新8＋関連5を分割受入。
元九byte/creator/claim、停止checkpointの要求/投入prefix束縛とゼロ/途中失敗の再開、再hash/kind拒否を確認。
円TM実FEMの独立絶対差2.764e-5と両gate、真TE doubletのnull/UNVERIFIED、全CLIと移動再生がPASS。
実running取消し−15→新worker終了0、旧管理器を閉じて新管理器で再開し、元source生存中移動/再起動を確認。
後片付けERROR/関連相対path FAILを保全し、不足各1件だけ補完。
最終監査PASS：9完了job/15trial snapshot、元416源中414/全123カード不変、jobs/cli追加入口のみ。
[専用曲線GUI](../PLANAR_CURVED_GUI.md)も19 strict操作/独立ページ、新API8＋関連6種類を分割受入。
実Chrome調整6＋再開1、表示修正後render-only1項目PASS。元socket/検証器/監査器ERRORとrawを保持し不足だけ補完。
最終byte監査PASS：16完了job/768 entry/全420 creator源、元五byte import/九byte prefix、元417源中412/全123カード不変。
全handle/両server終端、Chrome slot 0/外部要求0。
[実Chrome比較・履歴回復/延長・取消し](../PLANAR_CURVED_GUI_HISTORY.md)も13＋null表示1の分割14項目PASS。
元TE四native、実順位/真doublet・元場連鎖・過去anchorと最大段数停止・全元五byte/親不変/画像を確認。
検証器期待/非同期待ちERRORと実Page is too largeを保持し、全文scroll/null明示の表示2件だけ修正。
最終監査PASS：7完了job/510 entry/全420 creator源、元420源中418科学/その他源と全123カード不変。
実取消し−15/他7worker0、全3server/Chrome終端、外部要求0/slot 0。
P09はIN_PROGRESS、次は受入円/非円形TEの大容量調整checkpoint実GUIと全条件監査。不変量を先に再現し、
周波数・場・RF・表面量を分け、mode rankをidentityへ読み替えない。保存/追跡/調整/所有再開は続く必須範囲。
P04/P05/P06/P07/P08はDONE、原互換親P02/D02とH17/H18、P09と原要件を含む全123カードgoalは未完了。

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

現行checkpoint：[P09所有調整CLI-worker・停止checkpoint・実取消し/再開・移動再生](../PLANAR_CURVED_TUNING_JOBS.md)。新8＋関連5分割受入、最終byte監査終了0。生存処理/製品source固定なし。
5437/80226/14801/95624/62893/50083/1548/70391と最終監査は全実終端。14801はCLI成功/後片付けERRORの終了1、62893は関連4成功/相対path FAILの終了1を保持し、1548/50083で不足各1件を終了0で補完。実取消しworker−15/再開worker0も回収した。全417製品sourceを最後の数値handle終端まで固定した。
先行checkpoint：[P09独立履歴CLI-worker・回復/延長・実取消し/再起動・移動再生](../PLANAR_CURVED_TRACKING_HISTORY_JOBS.md)。新8＋関連5分割受入、最終byte監査終了0。生存処理/製品source固定なし。
37608/34617/53610/54618/71078、追加83912と両監査14029/17875は全実終端0。生存handleへの観測timeoutでは同じ実行を追跡し、実終端まで全416製品sourceを固定した。実取消しworker−15/新履歴・回復・延長worker全0も回収し、生存中の元source移動も確認した。
先行[P09所有比較CLI-worker・実取消し/再起動・移動再生](../PLANAR_CURVED_TRACKING_JOBS.md)も新6種類＋関連10分割受入、最終byte監査終了0。
61167/39091/75840/95073/41610は全実終端。95073は9成功/指定名読込ERRORの終了1、41610で不足1件を終了0で補完。実取消しworker−15/成功worker0も回収した。
先行[P09所有二点・独立履歴・過去anchor/移動再生](../PLANAR_CURVED_TRACKING_HISTORY.md)も全13新種類＋関連10分割受入/最終byte監査終了0。
65155/12200/55397/23678/55353/12906/80164/32393/84387/25747は全実終端。55353/12906の変異未発火FAILと80164の実変異FAILは保存し、32393の修正2件PASS/84387の通常3件PASSを区別する。
先行[P09所有調整の元受入native取込・移動再生](../PLANAR_CURVED_TUNING_SAVED.md)のhandle46796/最終監査11391も終了0、全元九byte/両gate/全ID/anchorを保持。
所有保存の初回/安全/関連は51684/61711/12626/10261が全実終端。先行実調整の61861/15076/22872/89290/75862/60455/81561/73075も全実終端。
[P07全条件受入](../PLANAR_CURVED_ACCEPTANCE.md)の元証拠も保持する。
元円38783は終了0、全四case/12B解/全66artifact/元401源/5validatorの照合・保全後に主統合した。
旧source/validatorは元hashでarchiveへ明示解決し、元成功/失敗の条件を保持する。
以下の古い日付付き段落は当時の状態であり、現在の生存handleはこの表を優先する。

| 処理 | 生存handle / 出力（全てout/以下） |
| --- | --- |
| P09所有取込・移動後完全再生 | 46796/11391は終了0。`out/p09-planar-curved-owned-tuning-20261007/accepted-case-test.log` / `owned-acceptance.json`。元rawを保持 |
| その他の数値処理 | なし。旧handle38783/16323/8632等は全実終端済み |

終端を観測した元非円形：TE楕円二尺度は成功25516/25128。
楕円TM尺度1/12945は終了1（B L4 RF未達）、角TE68744/27629と角TM35844/70344も終了1。
楕円TM尺度2/92077は終了143、原因未確定。元五保存解を別復旧先で物理再検証する。
角TM尺度1追加/15560は幾何検査1億回予算切れで終了1、新FEM0。元失敗rawも保持する。
旧38783の検証器5本、現行幾何10本/追加細分9本/復旧10本と全401製品を固定し、
最後の利用handle終端まで変更しない。上のhandleはwrite_stdinで終端確認し、timeoutで再起動しない。
N16の元成功を全hash/物理再構築して再利用。TM N32は全四例PASS、N64は元四例の幾何予算終端を保持して分離branchで未実行L4を継続。
TE尺度2N64のhandle99240/35751は終了0を観測。新混合細分validatorの使用10本も終端まで固定する。
楕円TM尺度1追加49794は1739.032秒/終了1、B L5元親chartの累積丸め上限未達、新FEM0。
元失敗を保持し、新2unitは3.101秒PASS。別B追加二分72293も終了1/1642.629秒、同じ累積元map丸め上限未達、新FEM0。全原失敗を保持し、許容値を緩和しない。
TEのN16/32/64は四系列（円/楕円二尺度）で限定監査PASS、handle25430終了0/13.845秒。
N16の先行物理証拠を全hash/source/数値gate付きで再利用し、新FEM/unit/物理再構築0。
11証拠Directory/239ファイルを保持する。初回二監査の引数/schema参照エラーと終端auditも保持。

main源固定中の独立作業：branch `p07-geometry-bvh` / `a1def65`、worktree `/tmp/superfish-ng-p07-geometry-bvh`。
geometry一製品ファイルだけを閉AABB候補探索へ変更、新4/直接利用先19unitは5.964秒PASS。
main製品401は不変、未統合。別実検査handle27869、出力 `out/p07-planar-geometry-bvh-20261007/`。
元A4の全係数/周波数bitwise/全RF metadata一致と独立energy/壁≤6.968e−12を確認。
分離実測27869は終了0、実L5の98304cell/147968edge・7452020box検査/同じ1e8予算でPASS。
元親map丸め1.875377e−14、解析面積/周長もPASS。新FEM0。
実uniform A5 TMのhandle34914は終了0/3011.913秒PASS、出力同親corner-tm-s1-uniform-A5 / solve-corner-A5.log。
400旧製品不変/geometry一ファイル変更、全prepared/元A4 artifactを照合して新実FEM一回を検証する。
main401は不変、34914の源固定は終了し、branch401/使用検証器は残る43214とN64四handleの終端まで固定。A4→A5対象f/E/H/全RF差は全PASS、独立B/尺度2/全P07は未受入。
分離保存B5復旧43214も開始、出力同親corner-te-s2-saved-B5-recovery / recover-corner-te-s2.log。
旧35422は終了143、cause不明、B5全rawが保存済みなので再FEMせず物理再構築/比較だけで復旧する。
N64 TMの25663/5330/19527は1e8 geometry予算切れで終了1、各L0〜L3保存済み。別終端audit保持。
楕円TM尺度1N32/99546は2457.414秒PASS、L3→L4全gate、新FEM5、401製品不変/全31artifact保持。
N64 TM/残P07は未受入。元完了解の再solveを避け、次の許容差不変の細分へ繋ぐ。
P07 IN_PROGRESS、全123カードgoal ACTIVE。seed/full validate/GUIを実行したとは扱わない。


2026-10-07追加checkpoint：角TE尺度1の53536は終了0/3811.488秒、新実FEM1でA3/B5受入。
円TM尺度1/2のN32（1671/23517）と楕円TM尺度2N32/65048は終了0、各L0〜L4の5実FEM。
既成功楕円TM尺度1N32を合わせTM N32全四例がPASS。全401製品/使用validator不変。
別限定監査31961は終了0、新FEM/unit/物理再構築0、四例105全artifactと数値gate/規約を保持。
N64円TM尺度2/66415も終了1/2501.715秒、L0〜L3保存、L4幾何予算1e8切れ。
分離driver `out/p07-planar-geometry-bvh-20261007/continue-N64-TM.py` を構文検査後に開始。
円s1/s2は92778/3796、楕円s1/s2は86568/16110、出力同親 `<shape>-tm-s<scale>-N64-L4-continuation/`。
全元10validator/source/hash/実終端と400旧製品不変/geometry一変更を照合し、
保存L3の全元chart/native/係数・周波数bitwise/全RF完全一致/独立積分を物理再検証する。
元完了FEMを繰り返さず、未実行L4のみ新実solve。1e8予算/512ε/全物理gateは不変。
branch401/共用11validator/新driverを34914/43214/上の四handleの終端まで固定する。
main401も残る旧三handle38783/50414/27391の終端まで固定。P07/全goal ACTIVE、N64実受入は未確認。


独立追加branch `p07-boundary-refinement`、worktree `/tmp/superfish-ng-p07-boundary-refinement`。
元楕円TM B4の壁RF未達と一様/二分の丸め終端に対し、明示的な境界cell適合細分を実装した。
[元map/energy不変量と実検証範囲](../PLANAR_CURVED_BOUNDARY_REFINEMENT.md)。
新3/旧直接利用10の計13unitは8.048秒PASS/59598終了0、変更前の独立一件ERRORを保持。
新実handle99269、出力 `out/p07-planar-boundary-refinement-20261007/ellipse-tm-s1-boundary/` と同名log。
旧399製品不変・geometry/refinement二変更、全元8/9/10validator、実終端、元係数/全RF完全一致を必須とする。
三保存解を物理再構築し、元Aの受入を再確認後、一回の新境界B FEM/元E/H/全RFを検査する。
branch401/使用10validatorは終端まで固定、main/bvh branch源を変更しない。RF/P07成功は未確認。


独立性能branch `p07-reference-basis-cache`、worktree `/tmp/superfish-ng-p07-reference-basis-cache`。
[参照表のbitwise保存・実測・strict残件](../PLANAR_CURVED_REFERENCE_CACHE.md)。
参照basisだけを最大32表/各4096点まで再利用、実J/K/M/場/係数/RFは再計算する。
新3/旧直接利用22の25種類は分割成功。初回24PASS/既存一ULP所属への期待1FAILを保持し、
cache互換範囲のその一件だけ0.003秒PASS（68737）。元APIの一ULP外参照受理は別reproducerで確認した。
単要素order8/12/16実測は14〜17倍、全mapped配列/K/M bitwise一致。
保存済みellipse TM A4の実物理再構築78576は終了0/288.568秒PASS、新FEM0、出力 `out/p07-planar-reference-basis-cache-20261007/results/`。
前後branch401/使用11コード不変、全元係数/周波数bitwise・全RF metadata完全一致、独立積分最大1.037e−13。
cache単独source固定を解除し、次はstrict参照所属を是正する。main/BVH/boundaryの生存源固定は継続。
既存strict参照の和丸め不備はP07完了前に是正する必要があり、性能成功から解消済みとはしない。
壁参照/元場/locatorの厳密閉所属を整合し、内部boundary表現と実壁RFを別検証する。
全goal/P07 ACTIVE、P08/P09と全原要件を維持。


strict参照修正：[独立反例・閉壁整合](../PLANAR_CURVED_EXACT_REFERENCE.md)。
source固定が解けたcache branchでgeometry/元場/validator/locatorの厳密閉所属を実装した。
新4/旧直接利用24の28種類は分割成功。初回25PASS/閉壁probe二ERRORを保持し、その二件だけ0.217秒PASS、
実TM PEC壁Ez=0の追加一件は0.101秒PASS。許容値は不変、他25成功を繰り返さない。
新物理再構築74571、出力 `out/p07-planar-exact-reference-20261007/physical-replay/` と `replay.log`。
旧397製品不変・geometry/location/refinement/solver四変更を明示し、TE L3/TM A4の全係数/周波数bitwise、
全RF metadata完全一致と閉壁parameterの丸め差≤1e−12/独立積分≤1e−8を検証する。
74571は終了0/230.797秒PASS、新FEM0。全係数/周波数bitwise・全metadata完全一致、RF差TE0/TM最大2.221e−16。
branch401/使用7code/元artifact不変、独立積分最大1.037e−13。branch単独source固定を解除する。
main/BVH/boundaryの生存源を変更せず、全P07と統合は未受入。


楕円TM尺度2の復旧70467は6484.605秒PASS/終了0。元143/原因未確定・五保存解を保持し、
元五解を物理再構築後、未保存のB4/B5だけ二実FEMを追加、A4/B5全gate受入。
B4→B5全RF差最大1.767055e−3、A4対B5最大1.213063e−4、前後401製品/使用10validator不変。
全15artifact snapshot/別terminal auditを保存する。楕円TM尺度1と全P07は未受入。


円独立38783のTM半径0.01 B5は81920cellの全Case/係数・周波数/chart/patternsが保存済み、gateは未保存。
元APIはcellごとに全point vectorをmaskし、order8全域5242880点では一mode当たり429496729600要素を走査する。
読取証拠 `out/p07-planar-exact-reference-20261007/original-circle-field-scan-audit.json`。
次のbounded改善は、pointを一回だけowner別に整理し全元出力をbitwise保持すること。
現handleは生存/源固定を継続し、timeoutによるrestartや保存済みB5の再FEMをしない。

### 先行実行の履歴

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


## 楕円TM境界B・角TE尺度2の終端と角TM残件（2026-10-07）

99269は2464.466秒PASS/終了0。元A3/A4/B4を物理再構築し、新境界Bの実FEMだけ一回追加した。
21760cell（旧B4は20480）、最終元map丸め7.028348e−14。B4→境界Bの対象f差最大2.1547e−8、
E差4.0985e−6、H差2.076318e−4、全RF差1.701740e−3。独立A4対BのRF差最大5.874163e−5。
完全band/独立energy・実壁積分も原gateでPASSし、楕円TM尺度1 A4/境界Bを受入した。
元399製品不変・geometry/refinement二変更、前後401分離製品/使用10validator/全元artifact不変。
別終端auditと全12artifact snapshotを保持。楕円二尺度の両偏波は各固定FEM条件を満たした。

角TE尺度2の保存済みB5復旧43214も3891.121秒PASS/終了0、新FEM0。
元終了143の原因は依然未確定。A3/B4/B5を全元chart/nativeから再構築し、全係数/周波数bitwiseと
元A3/B4全RF完全一致を確認した。対象B4→B5のf差1.101088e−5、E差4.222931e−3、
H差1.208029e−4、RF差3.629551e−5、独立A3対B5 RF差3.721745e−6。
完全band/独立積分もPASSしA3/B5を受入、角TE両尺度の固定FEM条件を満たした。
400旧製品不変・geometry一変更、前後401分離製品/使用10validatorと元39artifact不変。
復旧出力全8artifactのsnapshot/終端auditを保持し、保存済みFEMを再solveしない。

角TM混合細分50414/27391は終了1、7130.991/7129.920秒。各新3実FEMでAの混合細分は受入したが、
Bの第3対象群は最後二水準RF差5.514924e−3（0.551492%）で0.5%gate未達。
対象第1/2群RF差4.502693e−3/4.409091e−3、全f/E/Hと独立A/B（RF最大2.182286e−3）はPASS。
全401製品/使用10validator/元22artifact不変、各全21artifact snapshotと実終端auditを保持する。
B/角TM/P07を受入せず、既存境界patternで各尺度の保存Bへ局所細分を一回だけ追加する。
新driver `extend_planar_curved_corner_boundary.py` の全source/終端/raw preflightは二尺度PASS。
元accepted Aと最終Bを全chart/native/RFから物理再構築し、再FEMせず、新境界Bだけ各一実FEMを検証する。
boundary branch401製品/使用10validatorをhandle37232/67404の終端まで固定する。
出力 `out/p07-planar-boundary-refinement-20261007/corner-tm-s{1,2}-boundary/` と同名log。
1e8 geometry予算・512ε元map丸め・f/E/H/RF許容値・完全guard・独立積分は全て維持する。

上記終端四件の限定監査は新FEM/unit/物理再構築0。全前後hashと数値gateを照合し、受入を
証明済み形状/偏波/尺度に限定する。元円独立mesh38783、N64 TM四件、全P07とP08/P09は継続する。

[元場point groupingの反例・bitwise条件・14unitと保存実解測定](../PLANAR_CURVED_FIELD_GROUPING.md)を追加。
95559は終了0/1.464秒PASS。新測定42739は実終端までcache branch401/使用8codeを固定する。
元38783は半径.01両偏波を受入済み、半径.02 TE B3生成済みで生存中。旧源を改変せず継続する。
現行源固定はmainの38783のみ、BVHのN64四件、boundaryの角TM二件、cacheの42739。
終端99269/43214/50414/27391は上表から外した。先行する過去記録中の「生存」はその時点の記述である。
mainは文書のみ変更、全401製品hash不変。P07/全goalは未完了であり、全123カード範囲を維持する。


## 楕円TM N64両尺度のL4終端受入（2026-10-07）

分離継続86568/16110は終了0、3918.479/3921.632秒PASS。元L0〜L3四保存解と予算切れ終端を保持した。
保存L3の全元chart/native/K/M/係数・周波数・RFを再構築し、未実行L4だけ各一新実FEM。
各114688cellのL4で、対象L3→L4最大f差8.281288e−8、E差7.256088e−6、H差4.070364e−4、
全RF差1.435390e−3。真面積/周長/境界距離、全band、独立energy・壁も原gateでPASS。
最終元map丸め尺度1/2は9.256923e−14/5.064288e−14、512ε以下。
400旧製品不変・geometry一変更、前後401分離製品/使用12code/元各25artifact不変。
各全13artifact snapshotと観測終端auditを同親に保持。限定監査は新FEM/unit/物理再構築0。
楕円TMのN16/32/64二尺度の条件別実証拠が揃った。TEの先行四系列受入と分けて記録する。
元円独立全尺度、円TM N64二尺度92778/3796、角TM境界B二尺度37232/67404、grouping実測42739は継続中。
P07全条件監査・source統合は未完了、P08/P09と全123カードgoal ACTIVEを維持する。
BVH branch401/使用12codeは残る円N64二handle終端まで固定する。


## 楕円TMの有限幾何系列監査（2026-10-07）

楕円TM二尺度のN16/32/64を限定監査36705で受入、4.167秒/終了0。
元source版をmain旧401、geometry一変更のBVH401、geometry/refinement二変更のboundary401へ明示分離し、
全accepted artifact snapshot/前後source/元validatorを照合した。各完全6モードと三対象群のf/E/H/全8RF差、
完全guard gap、U′=1・peak +iωt・J/m/W/m、両R/Qと加速量の理由付きnull、独立energy/壁を数値で検査する。
各元Domainのareaとfine RF areaも照合した。真面積/周長/境界距離は元N16/32/64を小規模再生成して別検査し、
三誤差が単調減少しN64で各1e−4以下を確認した。異なる幾何Domain間の場差は計算していない。
六証拠Directory/計115artifactを保持、新FEM/unit/物理再構築0。
出力 `out/p07-planar-curved-geometry-20261007/ellipse-tm-geometry-series-audit/`、全7audit artifact snapshot/終端も保存。
先行TE四系列とは別のTM楕円二系列受入。残る円TM N64/角TM/元円独立全尺度/source統合/P07全条件を維持する。


## 円TM N64の二尺度L4終端（2026-10-07）

92778/3796は4279.750/4256.249秒PASS/終了0。元L0〜L3四保存解と1e8幾何予算切れ終端を保持し、
元L3の全chart/native/係数・周波数・RFを物理再構築した後、未実行L4だけ各一新実FEMを追加した。
対象L3→L4のf差最大6.739720e−8、E差6.676226e−6、H差3.672057e−4、全RF差1.492751e−3。
完全Bessel f/E/H/G、真幾何、独立energy/実壁、512ε元map上限もPASS。
最終元map丸め両尺度2.545328e−14。前後401branch/使用12code/元各25artifact不変、
400旧製品不変・geometry一変更。各全13artifact snapshotと実終端auditを保持する。
N64 TM四例は全てL4受入、BVH branchの数値handleは全終了しsource固定を解除する。
円/楕円、両偏波、二尺度のN16/32/64各FEM証拠が揃った。有限系列の監査を受入してからP07条件へ数える。
角TM境界B二尺度と元円独立半径.02/source統合を維持する。全P07/goalは未完了。


## 実保存B5の終端・測定範囲（2026-10-07）

42739は502.301秒PASS/終了0、新FEM0。元円TM半径.01 B5の81920cell・全元chart/native/K/M/最低帯を再構築した。
全係数/周波数bitwise、全RF metadata完全一致、閉壁parameter丸めによるRF差最大2.221e−16、
独立energy/壁最大8.276e−13を確認した。前後401branch製品/使用8code/元完了B5全artifact不変。
各1024owner/65536点の元scalar/全mode APIで、順序付き/randomとも全返却配列bitwise一致。
実測旧/新は順序付きscalar 0.2070/0.1910秒（1.084倍）、全mode 0.2410/0.2021秒（1.192倍）。
random scalar 1.0987/1.7597秒（0.624倍）、全mode 1.1443/1.0942秒（1.046倍）。
この単回・並行実行下のrandom scalar測定は低速化を示しており、全入力の速度改善や全FEMの倍率を主張しない。
受入は全点反復走査の除去、owner内演算と出力のbitwise保存、独立物理gateに限定する。
順序付きは線形、任意順序はstable sortでgroupingする。全81920owner/5242880点のAPI実測はしていない。
全6artifact snapshotと観測終端auditを保持。cache branch単独のsource固定を解除する。
mainの38783とboundaryの37232/67404の生存源は変更しない。source統合/P07全条件は未受入。


## 円TM有限系列・全幾何系列の条件別監査（2026-10-07）

円TM二尺度のN16/32/64限定監査86826は2.114秒PASS/終了0。
元18円解の物理audit/全raw/hash/元validatorと、新N32/N64の全accepted snapshot・前後sourceを照合した。
完全6モード（対象群[1,2]とguard群[2,1]）のlast-two f/E/H/全8RF、独立Bessel絶対f/E/H/G、
独立energy・壁、全正RFとU′/phasor/SI/null理由、元Domain areaとfine RF areaを数値検査する。
N16/32/64の真面積/周長/境界距離は元Domain小規模再生成で別判断し、三誤差の単調減少と最終各1e−4以下を確認。
五Directory/計109artifactを保持、新FEM/unit/物理再構築0。全7audit artifact snapshot/観測終端も保存。
main旧401とgeometry一変更のBVH401を明示区別する。異なる幾何Domain間の場差は比較していない。

先行TE四系列/239artifact監査、TM楕円二系列/115artifact監査と本円TM二系列を合わせ、
円/楕円・両偏波・両尺度の有限N16/32/64八系列にそれぞれ元P05 gateの証拠がある。
この受入は全P07ではない。角TM二尺度、元円独立A/B半径.02、source統合と全条件照合を継続する。


## 統合前の元modern source保全（2026-10-07）

mainの全401独立modern製品と15数値validatorを、ignored
`out/p07-planar-exact-reference-20261007/before-main-integration/` に新規保存し全元hashを照合した。
sourceは正しい `modern-independent-source/superfish_ng/` package構造で保持する。
保存対象は本実装の自作源のみ、legacyコード/バイナリ/ユーザー所有assetsは含まない。
strict/cache/groupingの統合予定を四製品・二strict validator・六test fileへ限定したinventoryを保存。
歴史的な失敗延長scriptの変更を一括取り込まず、元raw/hash/source版と新kernelの物理bridgeを明示する。
main源を変える前提は38783の実終端。現在は半径.01 TE/TMと半径.02 TEがPASS、最後の半径.02 TMを継続する。
角TM境界B37232/67404も元Aの物理再構築を終えBを再構築中。両branchのsource固定を維持する。
source保全自体に新FEM/unit/物理再構築はない。P07と全123カードgoalはACTIVE/未完了。


[元accepted解と新strict/cache/grouping sourceの物理bridge](../PLANAR_CURVED_SOURCE_BRIDGE.md)を開始。
新validator3unitは0.007秒PASS。新FEM0で三例の全元chart/native/K/M/最低帯・係数bitwise・全RF metadataと
canonical閉壁浮動差≤1e−12/独立積分≤1e−8/全signed公共場/実TM PEC zeroを検査する。
cache branch401製品/使用10validatorを78620/54876/89737の実終端まで固定する。
main38783とboundary37232/67404も固定継続。全P07/source統合は未受入、全goal ACTIVE。


[原P07/P05の条件別監査（作業中）](../PLANAR_CURVED_ACCEPTANCE.md)を追加。
全条件と局所証拠・残る実終端/source bridge/統合を対応付け、未確認を完了扱いしない。
P07 IN_PROGRESS、P08/P09と全123カードgoalは継続する。文書監査追加によるFEM/unitの再実行はない。


## 三実bridge終端とTM全帯trace補強（2026-10-07）

78620/54876/89737は終了0、157.838/551.566/555.269秒PASS、新FEM0。
楕円TM境界Bと角TE二尺度B5の全元chart/native/K/M/最低帯を新kernelで再構築し、
元係数/周波数の一致・全RF metadata完全一致を確認。RF浮動差最大3.331e−16、
独立energy/壁最大1.288e−11、signed公共場/literal差最大1.343e−16。
前後401製品/使用10validator/全元accepted rawは不変、各全6artifact snapshotと実終端auditを保存。
三旧validatorの全10コードは `source-bridge-validator-before-all-mode-PEC/` に元hash付きで保全した。
旧bridge内の明示TM壁probeはmode0だけだった。共通 `_restore` は元から全modeの拘束係数≠0を拒否しており、
旧受入eig状態の全帯PEC拘束は保持されるが、独立trace probeの範囲を全帯へ補強する。

実TM3帯でmode0を保持しmode1の壁係数だけを変更する独立反例は、旧probeが未拒否でFAIL/0.031秒。
この孤立trace検査用tamperは有効固有対ではない。原logを保持する。
旧三実handleの終端・コード保全後に、32Gauss実壁の公共 `all_fields_at_reference` で全正mode Ez=0を検査へ変更。
同じ一件だけ0.025秒PASS。新bridge unitは先行3＋新1の計4種類を分割確認、他成功を繰り返さない。
元配列保存にはdtypeとtobytes比較も追加し、signed zeroを含むbitwise条件を明示した。
製品401/物理演算/許容値は未変更。独立trace checkerのcoverage補強であり、全RFや再構築の代用ではない。

別 `check_planar_curved_bridge_fields.py` は既に物理受入したbridgeの全source/archive/rawを照合し、
同じnative geometryと元係数上の公共field methodだけで全signed E/H・全mode PEC・配列bytesを追加検査する。
solver state/代数診断を作らず、行列/スペクトル/独立energy・壁積分を再実行しない。
楕円TM補足76506は27.817秒PASS/終了0、新FEM/物理再構築0。全6modeの各実壁32Gauss Ez=0を確認した。
角TE二尺度の補足54225/85631は実検証中。branch401/使用4validatorを両実終端まで固定する。
出力は各元bridge名に `-fields` を付けた同親folder/log。
新源への角TM二尺度bridgeと主source統合は残条件であり、全P07/全goalは未完了。


## 三例のbyte/全帯trace補足終端（2026-10-07）

76506/54225/85631は27.817/149.105/150.160秒PASS/終了0。
三物理bridgeの全accepted raw/sourceとのbindingを保ち、同じ元配列dtype/tobytesをsigned zeroまで照合した。
楕円TMは全6正modeの全実壁32Gauss点でEz厳密zero、全signed公共E/Hも独立literal式と1e−12以下で一致。
角TE二尺度も同じbyte/公共signed場条件を確認。代数diagnosticsやsolver stateは作っていない。
新FEM/行列・スペクトル再生/独立energy・壁積分の再実行は全0。元三物理bridgeの実証拠を再利用する。
前後401製品/使用4validator/全親bridge・元rawは不変、各全6artifact snapshotと実終端auditを保持。
旧bridge validator10コードは元hashで別保全し、TM mode0だった古いprobeの範囲を上書きしない。
cache branchの数値利用handleは全終了しsource固定を解除した。main38783とboundary37232/67404は生存固定。
角TM二尺度と円独立半径.02 TMの全gate、統合予定sourceへの残bridge/主統合/P07全条件監査を継続する。


## 主branch由来の限定統合候補（2026-10-07）

主sourceの生存38783を保持した別worktree `/tmp/superfish-ng-p07-final-integration`、branch `p07-final-integration` を作成。
主HEAD 02ae90aから、検証済みsourceの四製品、strict二validator、bridge二validator、対応七testだけを取り込んだ。
全401製品hashは既物理受入kernelと完全一致、旧主sourceから四変更/397不変を照合。
取り込んだ四validator/七testの全hashもcache branch検証済み版と完全一致する。
同じsourceの成功を再利用し、新unit/FEM/物理再構築0、`git diff --check` PASS。
歴史的失敗延長scriptの版を一括変更していない。source/archive/旧数値証拠を保全し主源を固定する。
照合はignored `out/p07-planar-exact-reference-20261007/final-integration-candidate-hashes.json`。
この候補の作成は主branchへの統合やP07完了ではない。元円独立半径.02 TMと角TM二尺度、残source bridge、
主source統合/全条件監査を実終端後に完了する。P08/P09と全123カードgoalを維持する。

## 角TM二尺度境界Bの実受入（2026-10-07）

37232/67404は終了0、4200.212/4189.588秒PASS。既存A/Bを物理再構築し、新FEMは各一回だけ。
元B69632cellから73442cellへの境界局所細分で、対象三群の最後二水準RF最大0.002367392、
独立A/B RF最大0.004554814となり、元0.005条件を両尺度で満たした。f/E/H・全六帯guard・独立積分もPASS。
独立積分差最大1.284e−12、元map相対bound4.126e−14。混合B第3群0.551492%の元FAILは保持する。
全401製品/使用10validator/全旧raw不変を終端後にも照合し、各全11artifactのsnapshotと観測終端auditを保存。
boundary branchの数値handleは全終了。統合kernelへのV2 source bridgeを16323/8632で開始した。
新FEM0、全元chart/native/K/M/最低帯・元配列bytes・全RF metadata・全六TM壁traceを検査する。
cache branch全401と使用10validatorを両実終端まで固定する。主源38783も固定継続。
円半径.02 TM/source bridge/主統合/全条件監査が残り、P07 IN_PROGRESSと全123カードgoalを維持する。

## 終了済み物理gateの横断照合（2026-10-07）

[元条件別監査](../PLANAR_CURVED_ACCEPTANCE.md)の既存円四case/非円形八case/求積四case/共変六case/幾何八系列を
元数値限界・全対象/guard rank・全RF schema/理由付きN/A・元map boundで照合した。
読取report/source manifest前後hashと監査コードhashを
`out/p07-planar-exact-reference-20261007/completed-physical-gates-bound-inputs.json` に保存。
report形式差による監査側三KeyErrorは元logを保持して明示対応し、製品/raw/gateを変更していない。
新FEM/物理再構築/unitは全0。元38783と角TM bridge16323/8632は実行中、source固定を継続する。
未終端/主統合を受入へ数えず、P07 IN_PROGRESSを維持する。
[P08実装準備](../PLANAR_CURVED_INTEGRATION_PLAN.md)でnative/Project/CLI-worker/Study/GUIの直接利用先と
独立受入・旧版再生の順序を確認した。コード読取のみでP08実装/受入ではない。全123カードgoalを継続する。

## 角TM二尺度V2 source bridge終端（2026-10-07）

16323/8632は終了0、718.140/719.193秒PASS、新FEM0。各元受入B73442cellの全元chart/native/K/M/最低帯を
統合候補と同一401製品kernelで再構築した。元係数/周波数dtypeとbytes、全RF metadataは完全保存。
RF相対丸め差最大0/2.221e−16、独立20次energy/実壁差最大1.284e−12、signed公共場/literal差最大1.575e−16。
全六正TM modeの全実壁32Gauss点でEz厳密zero、元map相対bound4.126e−14も維持した。
全401製品/使用10validator/全accepted元raw不変を終端後にも照合し、各全6artifact snapshotと観測終端auditを保存。
cacheと統合候補の全401hashも一致。cache branchの数値handleは全終了しsource固定を解除した。
必要な非円形五source bridgeと三補足は受入済み。主源38783の実終端、主統合とP07全条件監査が残る。
元円独立半径.02 TMを継続し、P07 IN_PROGRESS、P08/P09と全123カードgoalを維持する。

## P07全条件受入と主source統合（2026-10-07）

元38783は終了0/17267.586秒。円二尺度両偏波のTE B4/TM B5全四caseが原gateでPASS。
12実B解の粗いFAILも保持し、全66artifact/元401製品/使用5validatorと元A全raw不変を終端後に照合した。
元401source/15validatorのarchiveを再確認し、受入候補fe25aadを主branchへfast-forward統合した。
最終主401は既物理受入kernelと完全一致、元主源から専用四製品だけ変更/397不変、11validator/testも受入版と完全一致。
`out/p07-planar-exact-reference-20261007/final-p07-acceptance.json` は全18原条件、元数値gateの12集約、
円/五物理bridge/三補足の九実終端と全raw snapshot、元codeの現存/履歴archive、成功unit logsを照合した。
集約件数13の初回誤記AssertionError logを保持し、実12集約と八非円形全組へ修正。製品/数値gateは変更していない。
既存成功と同一sourceの証拠を再利用し、新FEM/物理再構築/unit/full/seed/GUIは全0。
共有P2基底/seed TM経路・依存は未変更。P07をDONEとし、P08 native/操作経路へ進む。
全数値handle終端、source固定解除。P08/P09と全原互換条件/全123カードgoalは継続する。

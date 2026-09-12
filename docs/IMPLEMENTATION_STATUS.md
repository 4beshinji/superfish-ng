# 実装・検証の現状

2026-09-12：[境界分割独立の厳密アフィン共通分割API](PLANAR_EXACT_AFFINE_OVERLAY.md)を追加。
P02の幾何基盤として有理数写像・元要素被覆・元重心座標を実装する。
追加8unit・独立16条件32FEM/native・標準964件とseed周波数/RF回帰で限定受入した。
専用追跡要求/保存/worker/CLI/GUIと、一般の丸めた境界対応は未接続。
親課題の受入件数は変えない。

[可逆アフィン変換＋独立内部メッシュの合成追跡](PLANAR_AFFINE_REMESH_TRACKING.md)：明示多角形の厳密に可逆な宣言アフィン写像（せん断・異方尺度・鏡映を含む）と独立内部メッシュの元電場追跡を限定受入。要求/結果版6、余因子移送、正逆の元電場積分、完全保存再生・CLI/実worker/GUI・所有履歴を接続した。標準956件（954合格、2skip、1513.289秒）、追加9unit、独立解析26条件（反射8・異方8・順位交差2・せん断8、解析恒等残差最大2.221e-16、P2最終FEM Gram最大1.038e-4・周波数3.335e-4）、6拒否、Chrome9操作と要求/結果/URL復元を確認。seed9モード19量はf差0・最大相対差8.882e-16。境界密度独立の一般合成・非線形変形・曲線・親P02と全計画は未完。

[相似変換＋独立内部メッシュの合成追跡](PLANAR_SIMILARITY_REMESH_TRACKING.md)：宣言相似変換で前の境界節点列を厳密に写し、内部だけを独立に再メッシュした元電場追跡を限定受入。要求/結果版5、正逆の元電場積分、完全保存再生・CLI/実worker/GUI・所有履歴を接続した。標準947件（945合格、2skip、1514.373秒）、追加8unit、独立解析16条件（P1 16/32・P2 8/16、解析Gram最大残差2.221e-16、P2最終FEM Gram最大1.038e-4・周波数3.335e-4・G 4.934e-3・Q 4.135e-3・壁損失8.513e-3）、Chrome9操作と要求/結果/URL復元を確認。せん断・鏡映・異方尺度は版6で限定受入済み。境界密度独立の一般合成・非線形変形・曲線・親P02と全計画は未完。

[同じ多角形の独立再メッシュ](PLANAR_REMESH_TRACKING.md)：同じ多角形の独立メッシュ間の元電場追跡を限定受入。要求/結果版4、厳密な領域・各元要素面積・候補予算、全保存再生・CLI/実worker/GUI・所有履歴を接続した。標準939件（937合格、2skip、1486.136秒）、追加7unit、独立32 FEM/32対応、混次数16比較、幾何24条件、解析16条件、縮退16 FEM、実追跡32/履歴16worker、中止/再起動、Chrome96操作とGUI63保存ジョブを確認。旧版1〜3・38履歴・TM/TE/平面回帰と538sourceも合格。形状変更との合成・曲線・親P02と全計画は未完。

[多角形の宣言相似写像](PLANAR_SIMILARITY_TRACKING.md)：明示多角形の正の尺度・回転・SI平行移動による追跡を限定受入。要求/結果版3、正逆の元電場積分、完全保存再生・CLI/実worker/GUI・所有履歴を接続した。標準932件（930合格、2skip、1447.175秒）、追加9unit、独立64 FEM/128対応、解析32条件、縮退16 FEM、実追跡32/履歴16worker、中止/再起動、Chrome87操作とGUI56保存ジョブを確認。旧版追跡・22履歴・TM/TE/平面数値回帰と535sourceも合格。一般変形・親P02と全計画は未完。

[平面追跡の保存履歴](PLANAR_TRACKING_HISTORY.md)：平面モード追跡の保存履歴を限定受入。保存場・帯域・ID集合の連続性を全再検証し、未解決・段階上限での停止、所有コピーへの追加、CLI/実worker/GUIを接続した。標準923件（921合格、2skip、1417.539秒）、追加15unit、独立18履歴worker、Chrome76操作、GUI47保存ジョブと再起動後取込を確認。532sourceと旧TM/TE/平面の保存・周波数/RF回帰も合格。親P02と全計画は未完。

[明示多角形の一様尺度追跡](PLANAR_POLYGON_TRACKING.md)：明示多角形の原点一様尺度による電場モード追跡を限定受入。宣言した接続/四分割、局所精度と演算順の幾何検証、要求/結果版2、完全保存再生・実worker・CLI・GUIを接続した。標準908件（906合格、2skip、unittest1320.887秒）、追加9unit、32対応・三角形解析16条件・縮退8比較16FEM、16worker、Chrome58操作、保存22追跡/44nativeと取込10件を確認。旧矩形追跡11件・Study29件61点・細分18件54水準・平面32件/TE10件、TM seed9モード19量、527sourceも回帰合格。履歴連鎖は上記で接続。回転/平行移動は上記版3で接続。任意変形、親P02と全計画は未完。

[矩形平面モード追跡](PLANAR_TRACKING.md)：矩形平面RFの宣言写像による電場モード追跡を限定受入。独立格子の元要素積分、順位交差、縮退ID集合、帯域guardと有限細分空間の診断、コピー保存/再生・実worker・CLI・GUIを接続した。標準899件（897合格、2skip、unittest1302.292秒）、追加20unit、独立8比較16FEM・縮退/退出18FEM・永続8worker、Chrome51操作、保存11追跡/22スペクトルと取込6件を確認。旧Study29件61点、細分18件54水準、平面32件/TE10件、TM seed9モード19量（f差0、RF最大8.882e-16）も回帰合格。多角形の一様尺度追跡は上記で接続。履歴連鎖は上記で接続。回転/平行移動は上記版3で接続。任意変形、親P02と全計画は未完。

[同形状細分診断](PLANAR_CONVERGENCE.md)：平面RFの同形状細分診断を限定受入。元領域の四分割・係数移送、f/E/H/RF別判定、縮退/不足帯域UNVERIFIED、全水準保存再生・worker・CLI・GUIを接続した。標準879件（877合格、2skip、unittest1304.306秒）、追加14検査、独立16条件48FEM・特殊形状16条件48FEM、永続16worker、Chrome42操作、保存18診断54水準と取込2件を確認。旧平面32件/TE10件、TM seed9モード19量と513sourceも一致した。真の誤差上界・表面ピーク精度は保証しない。モード追跡、親P02と全計画は未完。

[平面独立Study](PLANAR_STUDY.md)：平面RFの独立Studyを限定受入。全点先行検証・実worker・完全保存再生・CLI/GUI・点取込を接続し、標準865件（863合格、2skip、unittest1238.644秒）、追加9検査、独立24掃引48点＋参照8FEM、交差/例題CLI、Chrome35操作と保存29Study/61点を確認。旧平面32件/TE10件、TM seed9モード19量f差0/RF最大8.882e-16、505sourceと保存hashも一致した。収束診断・追跡、親P02と全計画は未完。

[平面表示/GUI](GUI_PLANAR.md)：平面RFのxy場表示・SIプローブ・専用GUIを限定受入。標準856件（854合格、2skip、unittest1238.757秒）、追加7unit、Chrome13操作・旧軸対称10操作・再起動後3操作、独立表示場/回転・CLI・保存/HTTP照合を確認。旧平面32件/TE10件、TM seed9モード19量（f差0、RF最大8.882e-16）、499sourceと保存hashも一致した。平面Study・収束比較・追跡等と親P02は未完。

[平面Project/Job](PLANAR_JOBS.md)：専用PlanarProjectと実worker、直接/管理済み取込、再起動・再実行を限定受入。標準849件（847合格、2skip、unittest1234.561秒）、新14unit、独立16条件workflow・8workerのf/場/G/Q、72保存ジョブと2同梱CLI例を確認。旧平面32件/TE10件/管理済み8件、TM seed9モード19量（f差0、RF最大8.882e-16）、491sourceと保存hashも一致した。GUI・Study・追跡等と親P02は未完。

[TEの収束Study](TE_CONVERGENCE_STUDY_PLAN.md)を接続。同一物理Caseの電場・磁場・RFを個別比較し、縮退や積分不安定時はUNVERIFIED。円筒/球形の独立21FEM・GUI三判定・CLI/worker/再起動・標準785件と数値回帰が合格。細分差は物理誤差上界や表面ピーク精度の保証ではない。

[TEの独立パラメータ掃引](TE_STUDY_PLAN.md)を接続。全点の入力検証、TE native保存と別操作の円筒追跡、GUIのR/Q N/A表示を追加。円筒/曲線の独立18FEM・CLI/GUI保存一致・再起動・標準775件と数値回帰を確認。一般形状の追跡は未対応。

[円筒TEのモード追跡](TE_TRACKING_PLAN.md)を接続。Eφによる順位交差・部分空間、全native保存/replay、CLIとGUI履歴へ接続。独立8実FEM・Chrome8項目・標準771件（769合格、2skip）と既存数値回帰を確認。一般形状/曲線写像は後続工程。

[TEのGUI接続](GUI_TE.md)を接続。Eφ/Br/Bzの場表示・SIプローブ・偏波選択とN/A理由を追加。Chrome10項目・独立保存照合/球形解析・標準766件と既存数値回帰を確認した。

[TEのProject・ローカルジョブ](TE_JOBS.md)を接続。通常CLI/worker、完了時の保存場再検証、直接/管理済み取込、元メッシュ保持と管理器再起動を扱う。通常GUIのTE操作は上記で接続。TE追跡等は継続する。

[真空m=0 TE](AXISYMMETRIC_TE.md)を追加。Eφ/rの独立未知数、TEのPEC拘束、場・エネルギー・壁損失、加速量N/A、専用保存/再検証とCLIに対応。直線P1/P2と[曲線P2](CURVED_TE_PLAN.md)に対応し、通常GUIは上記で接続し、追跡等の統合は継続する。

[RF探索の実行内再利用](RF_OPTIMIZATION_REUSE.md)を追加。再開時の完全replayと全nativeファイルの変更検出を維持し、同じ実行内の確認済み祖先の追跡/RF評価を再利用する。保存書式と数値条件は不変。一般性能の受入は継続する。

[RF探索GUI](GUI_RF_OPTIMIZATION.md)を接続。2変数・目的関数・複数制約の入力保存復元、実ジョブの中止と保存再開、試行・水準ごとの個別ID確認付き場表示を行う。再開前の重い検証を管理器のロック外へ移した。開始要求自体の完全検証には引き続き時間を要する。

[RF探索のローカルジョブ](RF_OPTIMIZATION_JOBS.md)を追加。JobManagerで実行・中止・再起動・停止後のcheckpoint選択/再開を行い、3水準のmanifest・祖先・投入予算・所属を再検証する。GUI操作も接続済み。

[RF制約付き2変数探索](RF_OPTIMIZATION.md)を実装。各候補の3水準実FEM、相対写像による個別追跡、制約違反の改善と目的関数探索、予算内の最終細分、全試行の保存再開を接続する。一般変数・一般性能の受入は残る。

[RF設計制約の評価基盤](RF_DESIGN_CRITERIA.md)を追加。保存場を再検証した3水準の包絡で目的関数・複数制約を判定し、未収束/未解決の試行に採用値を与えない。D03の2変数探索器・初期/最終比較へ接続済み。

[外部メッシュ単体の読込と固定形状Study](EXTERNAL_MESH_WORKFLOW.md)を追加。GUIで読込/解除・不正入力時の保持を行い、P1/P2の直線元メッシュを一様細分して比較できる。曲線二次Studyも従来どおり。O02全体は継続中。

[曲線アフィン周波数調整](CURVED_TUNING.md)を追加。設計変数から曲線/元メッシュを変換し、試行間写像を導出して実FEM・追跡・最終細分・保存再開へ接続する。非アフィン曲線変更や制約付き多変数最適化は残る。

[曲線Projectと元メッシュの一括変形](CURVED_PROJECT_TRANSFORM.md)を追加。元分割・接続と二次写像の対応を検査し、RF座標方針と試行間相対写像を明示する。アフィン曲線tuneへ接続済み。一般曲線変更は残る。

[弧ごとの固定分割数](FIXED_CURVE_PARTITIONS.md)を追加。弦誤差条件を維持しながら分割と元メッシュの対応を保存し、曲線二次写像・鏡映・GUIへ接続した。一括変形APIへ接続済み。アフィン曲線tuneへ接続済み。一般曲線変更は残る。

[Project第2版の明示元メッシュ](PROJECT_MESH.md)を追加。通常CLI/Job・GUI読込/保存/実行で指定した接続を保持し、曲線固定幾何Studyと適応入力へ引き継ぐ。曲線tuneの試行ごとのアフィン変形へ接続済み。

[弧の対応を保持するアフィン変形](AFFINE_CONIC_TRANSFORM.md)の幾何APIを追加。回転した楕円・双曲線の両枝を含み、同じfractionの位置・接線・曲率を保持する変換を検査した。Case/元メッシュの一括変形APIへ接続済み。アフィン曲線tuneへ接続済み。一般曲線変更は未実装。

[多項式による非線形座標連動](POLYNOMIAL_TUNING.md)を周波数調整へ追加。設計変数の多項式からprofile座標を作り、実FEM・追跡・二分法・最終細分を行う。両単位表現/両尺度の円筒解析対照がPASS。一般曲線・非多項式関数・制約付き最適化は残る。

[周波数調整の途中保存選択](GUI_TUNING_CHECKPOINTS.md)をGUIへ追加。中止したジョブの保存済み試行を一覧から選び、元ジョブと保存場を再検証して再開できる。一般形状/非多項式連動・制約付き最適化は残る。

[二次境界の空間候補選別](QUADRATIC_BOUNDARY_CANDIDATES.md)を追加。旧自作実装との証明・交差等の最初の拒否理由を維持し、保存済み2,744境界辺の検査単体を中央値23.975秒から0.203秒へ短縮した。全FEM実行や一般形状の速度倍率とは区別する。

[RF合格・表面未達時の明示的一様細分](CURVED_RF_SURFACE_POLICY.md)を追加。元の非球形両尺度・許容差・12回予算で、6イベント/14,665自由度の検証がPASS。既定のR/Q選択は保持し、親採用と五量の停止合格を区別する。

[版5の次計画共有](RF_ADAPTIVE_PENDING_PLAN.md)で、同じ親・確認場のRF選択の再計算を減らした。保存場・request・実装の照合と公開replayを維持し、旧実装との全文書一致を確認した。従来R/Q単独方針の一般収束は未受入。

[適応計算の祖先ジョブ時間](GUI_RF_ADAPTIVE_COST.md)を表示する。再開前・中止したジョブを重複なく合算し、時間未記録・外部出力は不明と表示する。記録されたジョブ時間であり、全workflowの測定とは区別する。

[RF適応版5のGUI](GUI_RF_ADAPTIVE.md)を追加。親・採用列・連続確認を表示し、確認場/採用場の選択、保存再読込、中止後の再開を実ブラウザーで確認した。非球形/両尺度/全workflow費用は、明示した表面細分方針で限定対照を確認した。

[RF適応版5の分岐・保存再開](CURVED_RF_ADAPTIVE_REFINEMENT.md)をAPI/CLI/JobManagerへ接続。元親からの局所細分と確認2回の五量停止を実装し、半球で5イベントの停止・全保存再検証・独立解析五量を確認した。GUI・一般形状/尺度/総費用の受入は残る。

[RF指標の重複再構築](CURVED_RF_GOAL_REUSE.md)を削減。[自動適応の分岐・保存再開の設計](CURVED_RF_ADAPTIVE_PLAN.md)を具体化した。版5の実行・CLI/GUI・反復受入は未実装。

[RF重み付き親要素選択](CURVED_RF_GOAL_INDICATOR.md)を追加。実全域確認の随伴で親残差を局所化し、選択番号から実FEMまで接続した。3形状のR/Q対照差は減少したが、確認/指標費用を含む効率と適応版4への接続は未受入。

[RFの角周波数偏微分](CURVED_RF_FREQUENCY_SENSITIVITY.md)を追加。位相・電場・電磁エネルギーの周波数依存を解析的に微分し、係数随伴との結合を検査した。親子残差と細分選択・効率受入は残る。

[固定周波数のRF随伴](CURVED_RF_ADJOINT.md)を追加。振幅方向を除いた疎連立系と全固有モード展開・行列摂動の照合を実装した。周波数全微分、細分選択器への接続と効率受入は残る。

[固定周波数のRF係数感度](CURVED_RF_SENSITIVITY.md)を追加。複素加速電圧のP2係数ベクトルと両R/Q勾配を、解析積分・有限差分・振幅/位相・Maxwell尺度則、実native場で確認した。適応選択器への接続と効率受入は残る。

[曲線メッシュの図上選択](GUI_CURVED_MESH_SELECTION.md)を追加。実計算空間の要素番号を選び、履歴末尾へ追加する。入力/履歴変更後の古い選択は拒否し、既存履歴・一様段数の両経路で実FEMまで確認。表示は5000要素までで、大規模選択は残る。

[磁気対称の両尺度適応検証](CURVED_MAGNETIC_ADAPTIVE.md)がPASS。6水準の最終停止と追加一様対照の五量差・追跡・高次積分、全水準相似最大1.710e-14を確認した。追加対照差を絶対RF誤差とは扱わず、一般精度/効率は残る。

[曲線適応の単一対称半領域](CURVED_ADAPTIVE_SYMMETRY.md)を追加。鏡映した全PEC境界の滑らかさを確認し、元半領域のRF規約で計算する。両対称/両端の鏡映不変量と半球の両尺度・独立球形五量がPASS。一般接続・幾何誤差・一般精度/効率は残る。

[非球形の両尺度対照](CURVED_NONSPHERE_COMPARISON.md)がPASS。全五量相似差最大8.362e-12、体積保存・Ritz・追跡・積分と追加対照差を確認した。両尺度とも適応100917対一様確認41281自由度で、適応優位は得られなかった。検証対象はdc795e9。一般精度/効率と親N04は未受入。

[履歴を保持する収束Study](CURVED_HISTORY_STUDY.md)を追加。既存の局所細分履歴の末尾へ一様細分を追加し、固定形状の体積不変とRitz単調性、GUIからの作成/保存/実計算を確認した。形状・初期メッシュを変える履歴付き掃引は引き続き拒否する。

[曲線細分履歴のGUI編集](GUI_CURVED_REFINEMENT_HISTORY.md)を追加。局所履歴が保存時に失われる不具合を修正し、段階の追加・順序変更・削除とstrict入力を接続した。Chrome 19項目と実FEM/native一致を確認。5000要素を超える図上選択・形状変更を伴う履歴付き掃引・一般精度/効率は残る。

[曲線辺の候補検索](CURVED_EDGE_SEARCH.md)を空間木へ変更。従来の比較候補・順序・幾何検査報告と拒否条件を維持し、全辺同士の候補検索を削減する。旧保存版1〜4と球形五量は完全一致し、標準656件中654合格・2 skip。非球形の両尺度対照は後続検証でPASS。一般精度/効率は継続する。

[曲線要素の順序付き組立](CURVED_ORDERED_ASSEMBLY.md)を追加。基底・積分寄与を配列化し、従来の加算順序と保存再検証の整合性を維持する。[非球形対照](CURVED_NONSPHERE_COMPARISON.md)は初回の予算不足を保持し、拡大予算の尺度1追加対照がPASS。適応100917自由度に対し一様確認41281自由度で、適応優位は得られなかった。高速化版の両尺度検証も完了しPASS。N04全体の精度・効率は未受入。

[曲線適応の検証済み先祖の再利用](CURVED_VERIFICATION_REUSE.md)を追加。実行中だけ先祖の場/ピーク/積分の重複評価を省き、要求・実装・元ファイル内容の照合と新水準の完全検証を維持する。独立replayは全水準を評価する。細分の一般精度/効率の受入とは区別する。


[曲線適応と一様細分の対照](CURVED_REFINEMENT_EFFICIENCY.md)を追加。同じ初期二次写像の球形で、独立解析五量・追跡・積分・二区間確認と誤差対DOF/時間を実測した。一様3水準/1201自由度に対し適応5水準/2661自由度を要し、この例で効率優位は得られなかった。一般精度/効率の受入は継続する。


[曲線の適応計算版4](CURVED_ADAPTIVE_REFINEMENT.md)をAPI/CLI/JobManagerへ接続。残差選択・native履歴・質量内積追跡、高次積分比較、五量の区間判定、全域確認2回、保存再開を統合する。滑らかさを確認した閉PEC曲線が対象。版4のGUI入力・五量/高次積分表示・保存再開も接続した。一般精度/効率・幾何誤差の受入は残る。

[曲線の親子空間の質量内積追跡](NESTED_CURVED_TRACKING.md)をAPI/保存/CLIへ追加。局所・全域の複数段階履歴、両対称と鏡映の偶奇部分空間を検証し、係数移送からモードID/部分空間を対応付ける。版4の適応停止とGUIへ接続した。一般精度・効率は残る。

[二次曲線FEMの残差指標](CURVED_RESIDUAL_INDICATOR.md)を追加。物理座標の二階微分・曲線流束を評価し、既存の選択APIとCase局所履歴で実細分できる。指標は物理誤差上界ではなく、曲線の適応停止とGUIは版4へ接続した。

[曲線要素の局所適合細分](CURVED_MARKED_REFINEMENT.md)を[Caseの順序付き履歴・native保存再構築](CURVED_REFINEMENT_HISTORY.md)へ接続。通常FEM/CLIと半領域鏡映の保存再検証を確認した。曲線適応停止は版4へ接続した。履歴対応Study・GUI編集は未接続。

[通常RF結果の連続離散ピーク評価](RF_DISCRETE_PEAKS.md)をAPI/保存/CLI/GUIへ追加。直線P1/P2・二次曲線P2の上下界、元RF推定値、規格化、角診断を同じ画面で確認できる。単一メッシュの物理収束合格ではない。

[版3の表面量を含む適応停止](ADAPTIVE_SURFACE_STOPPING.md)をAPI/CLI/JobManagerへ追加。最後の2回の全域細分でf/RQ/Gと連続離散ピーク比上下界を別判定する。版1/版2は維持。版3のGUI入力/表示/保存再開も接続。一般精度/効率は未完。

確認日: 2026-09-10。平面独立再メッシュ追跡版4の実装後。コードと最新の個別受入記録を照合した。標準検証の最終状態は冒頭と個別仕様を参照。
作業checkoutは `/home/sin/code/agent/reserch/superfish-ng`。
過去の `/home/sin/code/superfish` は当時の配置であり、移動やルートの作り直しは行わない。

## 互換計画の進捗

33親課題のうち、C01、限定C02、ローカルO01、native R01、N01、N02、G01、G02の
8件が記載範囲で.S/.I/.V受入済み。P01・P02・O02・G03・D01・D02・D03・N03・N04は部分実装・部分検証、C00は調査継続中（計10件）。残り14件は未受入、X01の1件は必須集合外。
他の親課題は未受入で、既存の掃引・GUI等を親課題全体の完了へ数えない。
X01は互換必須集合外の拡張候補。課題数は工数消化率や互換率ではない。
詳細と33件の区分は [COMPATIBILITY_PLAN.md](COMPATIBILITY_PLAN.md)。

## 現在提供する範囲

| 分野 | 実装・入口 | 制約・残件 | 証拠 |
|---|---|---|---|
| 物理 | 真空、軸接続m=0 TM/TE、PEC・平坦z端の電気/磁気対称。別契約で矩形/単純多角形の平面TE/TM遮断問題 | 内導体、複数材料、静的場は未実装。平面はβ=0で、曲線・多重連結/TEMは未対応 | [PHYSICS.md](PHYSICS.md)、[AXISYMMETRIC_TE.md](AXISYMMETRIC_TE.md)、[PLANAR_POLYGON_RF.md](PLANAR_POLYGON_RF.md) |
| TE・平面の操作 | 専用native/Project/worker・CLI/GUI、場表示とSIプローブ、独立Study・同形状細分、限定追跡。平面は所有履歴、宣言相似写像版3、同一領域再メッシュ版4、相似変換＋独立内部メッシュ版5、可逆アフィン＋独立内部メッシュ版6を接続 | TE追跡は同端条件の円筒。平面追跡は矩形宣言写像または検証済み多角形尺度/相似関係、同一多角形の独立メッシュ、厳密に写した境界上の独立内部メッシュ（相似または可逆アフィン）。境界密度独立の一般形状変更、非線形変形の追跡・調整は未対応 | [GUI_TE.md](GUI_TE.md)、[GUI_PLANAR.md](GUI_PLANAR.md)、[PLANAR_TRACKING_HISTORY.md](PLANAR_TRACKING_HISTORY.md)、[PLANAR_SIMILARITY_TRACKING.md](PLANAR_SIMILARITY_TRACKING.md)、[PLANAR_SIMILARITY_REMESH_TRACKING.md](PLANAR_SIMILARITY_REMESH_TRACKING.md)、[PLANAR_AFFINE_REMESH_TRACKING.md](PLANAR_AFFINE_REMESH_TRACKING.md) |
| 入力契約 | v3明示モデル、能力表、v1/v2移行、未対応指定の拒否 | 軸対称TEと専用平面TE/TM以外の追加物理を受理する契約ではない | [MODEL_CONTRACT.md](MODEL_CONTRACT.md) |
| 幾何 | 折れ線・段差・短円弧、z折返し単一輪郭、native円/楕円/双曲線弧 | 穴・内導体・任意CADなし。有限弧の数値判定/明示選択G1接続APIと支持曲線接点区間APIあり。保存・Case/CLI/GUI接続済み。有限弧所属/fractionの区間APIあり。版2で位置誤差上界付き切詰めを統合済み。版3で固定直線と有限弧の接続/明示延長を統合。版4は指定半径の線分間フィレットを統合（接点/G1は数値検査）。版5/6は有限弧間/直線と弧のフィレットを接点位置上界付きで統合。G1は数値検査 | [GENERAL_CONTOUR.md](GENERAL_CONTOUR.md)、[CONIC_GEOMETRY.md](CONIC_GEOMETRY.md)、[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md) |
| メッシュ・FEM | タグ付きJSON、品質条件付き自動生成、P1/P2、二次曲線写像、固定幾何細分、選択直線要素の適合細分と係数移送 | 品質未達は拒否。二次境界は元の解析曲線の近似。残差指標/対象選択APIあり。f/RQ/G停止・保存再開API/CLI/JobManager/GUIあり。版3の表面量停止はAPI/CLI/JobManager/GUIへ接続。曲線局所細分の空間/係数移送APIあり。曲線局所履歴の保存/CLI・曲線残差指標あり。曲線版4の五量停止/保存再開API/CLI/JobManager/GUIあり。高次積分比較も表示。物理誤差上界は未実装 | [GENERAL_MESH.md](GENERAL_MESH.md)、[HIGH_ORDER_FIELDS.md](HIGH_ORDER_FIELDS.md)、[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md)、[MARKED_REFINEMENT.md](MARKED_REFINEMENT.md)、[RESIDUAL_INDICATOR.md](RESIDUAL_INDICATOR.md)、[ADAPTIVE_REFINEMENT.md](ADAPTIVE_REFINEMENT.md) |
| 固有値・場 | 実FEM、複数モード、残差/直交性/エネルギー検査、物理座標プローブ | 残差は離散化誤差保証でない。全モード探索/一般追跡なし | solver.py、curved_solution.py、curved_sampling.py |
| RF・表面場 | f/U/Q0/G/V/RQ/シャント/TTF、加速長/区間/位相、P1/P2片側場、直線/曲線の連続離散極値の囲い込み、曲線角診断 | peak phasor・RQ二規約。TE/平面の加速量は理由付きN/A。平面は単位長エネルギー[J/m]・側壁損失[W/m]。常伝導摂動損失。離散極値の囲い込みは物理ピーク収束を保証しない | [ACCELERATING_CONVENTIONS.md](ACCELERATING_CONVENTIONS.md)、[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md) |
| 表面収束評価 | 固定曲線P2の3水準・追跡ID・ピーク上下界によるf/RQ/G/ピーク比判定API/CLI/GUI、元多角形角診断・追跡済み直線P1/P2の表面評価API/保存/CLI/GUI | 幾何近似誤差/一般形状の精度・効率は残件。物理誤差上界ではない | [SURFACE_CONVERGENCE.md](SURFACE_CONVERGENCE.md) |
| 条件群・鏡映 | 掃引、同一形状細分比較、条件付きバンド同定、曲線の幾何/FEM別Study・鏡映 | D01は重み付き標本部分空間・円筒/profile写像・明示メッシュ対応による追跡と2時点保存/再検証CLI/GUIと個別IDと部分空間ID集合の順序付き履歴/再開、完了Studyの隣接点追跡と点状態表示・保存再検証GUI、追跡付き逐次計算・停止・チェックポイント再開API/CLI・JobManager・GUI、幾何掃引の適応二分と途中保存・再開API/CLI・JobManager・GUI、多対多の保守的ID集合継承とGUI方式選択/復元、同一多角形領域の独立再メッシュ比較API/CLI/GUIと明示アフィン変形の比較API/CLI/GUI、明示比較メッシュによる区分アフィン変形の比較API/CLI/GUIと同一二次曲線領域の比較API/CLI/GUIを追加。曲線P2の明示アフィン変形にも、変換後の二次境界全体が一致する条件で対応。曲線領域の一般写像/個別枝回復は未実装。RF制約付き2変数探索は別行 | studies.py、symmetry.py、curved_reflection.py |
| 周波数調整・設計制約 | profile座標と曲線アフィン写像の1変数追跡付き二分探索・停止・再開・最終細分API/CLI・JobManager・GUI。保存済み3水準からの複数RF設計制約評価と曲線2変数探索/最終細分/再開API・CLI・JobManager・GUI | 個別ID確認が前提。細分差は誤差上界でない。非アフィン曲線/任意関数連動・一般変数の探索は未実装 | [TUNING.md](TUNING.md)、[RF_DESIGN_CRITERIA.md](RF_DESIGN_CRITERIA.md) |
| 操作・保存 | 共通CLI/Python/GUI、曲線計算・描画・鏡映、完了公開/hash、再読込 | 外部メッシュ単体の読込/解除UIあり。人による使いやすさ評価、電源断/他OSは未保証 | [GUI_ACCEPTANCE.md](GUI_ACCEPTANCE.md)、[SAVE_COMPLETION.md](SAVE_COMPLETION.md)、[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md) |
| 旧入力・出力 | 限定AF読込、原入力/hash/変換診断、NG JSON/CSV/NPZ/ASCII VTK | AFは単一真空/全PEC/軸接続TM。汎用旧入力、製品用旧テキスト変換、旧バイナリ互換は未実装 | [LEGACY_INPUT.md](LEGACY_INPUT.md)、C03/C04 |
| 配布 | 3386a5fの決定的ZIP・wheel内容/資源・CLI/曲線native計算のローカル確認 | wheelの全機能/GUI再受入はV02。hosted CI、他OS、公開リリースは未確認 | [ローカル配布確認](LOCAL_DISTRIBUTION_20260909.md) |

ソース名は `src/superfish_ng/` に対する表記。
GUIの「旧結果取込」は以前のNG出力であり、旧SUPERFISHバイナリの読込ではない。

## 検証の区別

| 種別 | 状態・範囲 | 記録 |
|---|---|---|
| 標準unittest | 785件中783合格・NGSolve参照環境専用2件skip。TE収束比較追加後に標準validate内で再実行 | `.venv/bin/python -m unittest discover -s tests -v`、OPENBLAS_NUM_THREADS=1 |
| 標準数値回帰 | TE収束比較追加後PASS。seed9モード19量の周波数差ゼロ、RF/エネルギー差最大8.882e-16。旧直線/曲線TE7件差ゼロ。標準・独立・終了後460対象hashとブラウザー実装hash一致 | out/validation-te-convergence-20260909、[TE収束仕様](TE_CONVERGENCE_STUDY_PLAN.md) |
| O02/P01 TE収束比較 | 独立21FEMで円筒P1/P2・球形両尺度・磁気半領域のf/電磁場/G解析、10unit・Chrome4項目・三判定表示、実worker中止/再起動、旧TM比較完全一致 | [仕様と証拠](TE_CONVERGENCE_STUDY_PLAN.md) |
| O02/P01 TE掃引 | 独立18FEMで円筒P1/P2・両尺度・規格化・曲線P2、解析ID順位とCLI追跡4組、GUI2項目・CLI/GUI保存完全一致・管理器再起動、旧TM保存Study3件完全一致 | [仕様と証拠](TE_STUDY_PLAN.md) |
| O02 TE GUI | Chrome10項目・追加3検査、GUI/API新規3FEMと係数/周波数一致、全3プローブ保存場照合・管理器再起動、球形3モードf/場/G解析PASS | [仕様・失敗履歴](GUI_TE.md) |
| O02 TEジョブ | 追加8検査・独立8実FEMとCLI/API一致、直接/管理済み8取込、再起動後verify=True全8件PASS。元mesh保持・改変/検証中変更拒否。GUI/追跡は継続 | [仕様と証拠](TE_JOBS.md) |
| P01曲線TE | 球形3モード・2尺度の5水準と磁気対称半領域で独立f/場/G/エネルギー・相似則PASS。TE12検査（追加5件）・実二次幾何保存と再構築/局所履歴・CLI/API一致。当時Project/GUI/追跡は未接続（Project/Jobは上記で接続） | out/curved-te-independent-final-20260909、[仕様と失敗履歴](CURVED_TE_PLAN.md) |
| P01直線TE | P1/P2・円筒6モード・2尺度の18 API FEMと2 CLI FEM。Bessel周波数・場成分・G・電磁エネルギー・Maxwell相似がPASS。専用native/CLIと外部mesh、TE/TM誤読拒否の追加7検査PASS。当時曲線・Project/GUI/追跡は未接続（曲線とProject/Jobは上記で接続） | out/te-independent-final-20260909、[仕様と失敗履歴](AXISYMMETRIC_TE.md) |
| N04実行内の先祖再利用 | 追加3検査PASS。出所改変拒否・独立replayを維持し重複評価を削減。版1〜4実保存の完全一致と前回対照の全水準五量差ゼロ。球形の適応全体は約119秒から約82秒の観測 | [仕様](CURVED_VERIFICATION_REUSE.md) |
| N04曲線の効率対照 | 同一二次写像の球形で解析五量/追跡/積分/二区間停止・Ritz・誤差対DOF/時間を確認。一様1201自由度に対し適応2661自由度。この例で適応優位なし、一般効率は未受入 | [比較仕様](CURVED_REFINEMENT_EFFICIENCY.md) |
| N04曲線適応GUI | 版4の実Chrome11項目・旧版15項目PASS。GUI実計算の独立球形五量もPASS。全ジョブ終了・検証サーバー停止済み | [GUI仕様](GUI_CURVED_ADAPTIVE_REFINEMENT.md) |
| N04曲線適応版4 | 追加5検査PASS。五量/全域確認/高次積分ゲート・4水準からの再開・改変拒否・CLI/JobManager。独立球形の両尺度で五量両端点・全域2回・相似則PASS。旧版1/2/3保存も完全一致。最終回帰は最新引継ぎを参照 | [仕様](CURVED_ADAPTIVE_REFINEMENT.md) |
| D01/N04曲線親子追跡 | 追加5検査初回PASS。複数履歴・質量積分・縮退/順位・両対称/鏡映・保存再検証を確認。既存18 native場の12組でCLI/ID/Galerkin/相似則PASS。適応停止/GUIは後続の版4で接続済み | out/nested-curved-initial-20260908、[仕様](NESTED_CURVED_TRACKING.md) |
| N04曲線残差指標 | 追加5検査、独立積分・直線極限・両対称変換則PASS。18 native結果の局所選択2回、積分比較・Ritz・円筒五量・相似則PASS。初回順位一致FAILも保持。追跡付き曲線停止/GUIは後続の版4で接続済み。一般精度・効率は未受入 | out/curved-indicator-selection-set-20260908、[仕様](CURVED_RESIDUAL_INDICATOR.md) |
| N04曲線局所履歴のnative統合 | 追加4検査、CLI実計算と6 native保存再読込、手動幾何完全一致・独立密行列FEM・円筒五量・相似則PASS。曲線適応停止は後続の版4で接続済み。GUI履歴編集は未接続 | out/curved-native-initial-20260908、[仕様](CURVED_REFINEMENT_HISTORY.md) |
| N04曲線局所細分基盤 | 追加5検査PASS。幾何/場/勾配・Galerkin・境界制限・全域細分との一致。円筒/楕円/双曲線の局所実FEM・RF移送・Ritz/相似則もPASS。当時は保存/適応経路未接続（保存は後続で統合） | out/curved-local-residual-metadata-20260908、[仕様](CURVED_MARKED_REFINEMENT.md) |
| N03通常RFピーク統合 | 追加5検査・実Chrome13検査PASS。直線/曲線の保存再検証、元RF保持、規格化、別順位/改変拒否、遅延応答の破棄。独立円筒解析五量/相似則・曲線U規格化PASS | out/browser-rf-peaks-expanded-20260908、out/rf-peaks-physics-initial-20260908、[仕様](RF_DISCRETE_PEAKS.md) |
| N04版3適応GUI | 通信5検査と実Chrome15操作が初回PASS。五量/上下界/全域確認/上限未達、保存再開・改変拒否・対象順位2・版1/版2切替 | out/browser-n04-surface-stop-initial-20260908、[仕様](GUI_ADAPTIVE_SURFACE_STOPPING.md) |
| N04版3表面量停止 | 追加4検査PASS。独立円筒P1/P2×尺度1/2で五量の区間端点解析比較・相似則・全域確認2回がPASS。P1は10水準/39817自由度、P2は5水準/3853自由度。版3 GUIも接続済み | out/n04-surface-stop-initial-20260908、[仕様](ADAPTIVE_SURFACE_STOPPING.md) |
| N03直線表面評価GUI | 通信3検査・実Chrome16操作PASS。適応結果から別ID評価、確認待ち/達成/再入角/形状未確認/未収束、保存/再検証・対象順位2の場表示 | out/browser-affine-surface-initial-20260908、[操作](GUI_AFFINE_SURFACE_CONVERGENCE.md) |
| N03直線表面収束評価 | 元多角形角診断・全個別ID確認済み適応系列の五量区間比較・保存/CLIの5検査PASS。独立円筒P2は全域2回で達成、P1は上限/確認待ちを保持。解析五量/相似則PASS | out/n03-affine-surface-initial-20260908、[仕様](AFFINE_SURFACE_CONVERGENCE.md) |
| N03直線離散ピーク | P1/P2の厳密有理数辺多項式と上下界、native保存/CLI/改変拒否の5検査PASS。円筒P1/P2×尺度1/2×3メッシュのf/RF/ピーク比解析比較・相似則PASS | out/n03-affine-extrema-initial-20260908、[仕様](AFFINE_SURFACE_EXTREMA.md) |
| N04適応GUI | 通信4検査と実Chrome19操作PASS。開始/中止、全域確認途中と中止後の保存再開、個別差・対象順位2の場表示、厳密JSON入力 | out/browser-n04-refinement-strict-20260908、[操作仕様](GUI_ADAPTIVE_REFINEMENT.md) |
| N04適応JobManager | 版1/版2×尺度1/2の部分実行・再開・管理器再生成、解析P2円筒f/RQ/Gと相似則PASS | out/n04-refinement-gui-strict-physics-20260908、[仕様](ADAPTIVE_REFINEMENT_JOBS.md) |
| N04適応独立検証 | 版2全域確認は円筒P1/P2のRF改善・相似則・内積独立検査PASS。P1解析RQ差約0.056%、ただし48069 DOF。折返しは上限停止。版1のFAILも保持 | out/n04-rf-confirmation-initial-20260908、[適応計算](ADAPTIVE_REFINEMENT.md) |
| 曲線FEM | 球形独立参照、楕円/双曲線の3段階幾何近似・全6固定FEM比較・最終幾何間の場/RF比較PASS。初回FAIL保持 | [CURVED_ELEMENTS.md](CURVED_ELEMENTS.md)、out/validation-g03-native-geometry-separated-20260908 |
| 接線候補 | 円/楕円/双曲線全体の四次式・根分離・接点再構成の独立8検査PASS。有限弧数値判定/明示選択G1接続の追加9検査PASS。有限弧所属/fractionと位置誤差上界を製品操作へ統合済み。固定直線と弧の追加7検査PASS。線分間フィレット追加7検査PASS。中心軌跡区間/特異性分割の追加6検査PASS。有限領域交点の追加7検査PASS。版5の有限弧フィレット追加6検査PASS、保存/Case/CLI/GUIへ統合。版6の直線・弧フィレット追加6検査PASS、同じ製品経路へ統合。弧端/退化の厳密特殊ケース診断API/CLIの追加9検査PASS。構築診断の別保存/CLI/GUI・再検証に追加5検査とChrome11操作PASS。最小子午面半径制約の追加6検査PASS、保存/鏡映/構築/GUIを確認。極端な尺度の曲率/半径の追加4検査PASS。一般分類と退化候補構築は未完 | [TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md) |
| モード追跡 | 追跡核9件・2時点保存6件・履歴6件・部分空間継承5件・profile写像6件・明示メッシュ対応5件・合流/分裂6件・GUI接続5件・Study追跡6件・Study GUI接続3件・追跡付き実行6件・JobManager接続5件・逐次実行GUI接続3件・適応二分6件・適応再開5件・適応Job接続5件・適応GUI接続3件・多対多集合継承6件・同一領域再メッシュ6件・アフィン再メッシュ6件・区分アフィン再メッシュ5件・同一曲線領域6件PASS。解析交差/近接・縮退回転・曖昧停止・保存後の実FEM円筒交差・profile相似則/局所変更、明示メッシュ対応での折返し/曲線相似。同一曲線領域GUIを含むChrome35項目PASS。一般追跡全体の受入ではない | [MODE_TRACKING.md](MODE_TRACKING.md)、out/d01-cylinder-crossing-20260908 |
| 周波数調整 | tune核11検査・JobManager接続7検査・GUI接続3検査・連動座標6検査PASS。円筒TM011の順位3→2、二分探索16回＋細分1回、独立解析周波数/相似則・CLI停止再開/再検証PASS。実workerの停止/再開・管理器再起動・改変拒否と独立計算もPASS。連動指定を含むGUI19操作PASS。既存46操作は前回受入。二つの細分判定のFAIL保持 | [TUNING.md](TUNING.md)、out/d02-coupled-tuning-final-20260908 |
| 独立NGSolve | 過去の円筒/円錐台基本モード、両側3段階、f/RQ/G/内部Hphi、円筒解析PASS | [INDEPENDENT_COMPARISON.md](INDEPENDENT_COMPARISON.md) |
| Wine比較 | 基本3形状と演習17対象モードの既存照合。限定AF読込は保存AF2形状から新規NG計算を照合。曲線全般の旧版照合ではない | [SUPERFISH_COMPARISON.md](SUPERFISH_COMPARISON.md)、[MILESTONE_ACCEPTANCE.md](MILESTONE_ACCEPTANCE.md)、[LEGACY_INPUT.md](LEGACY_INPUT.md) |
| GUI | G0〜G5と後続個別受入。曲線鏡映は左右/両対称を含む11ブラウザー操作PASS | [GUI_ACCEPTANCE.md](GUI_ACCEPTANCE.md)、[CURVED_ELEMENTS.md](CURVED_ELEMENTS.md) |
| 実機測定 | 未検証。合成幾何・演習照合を測定検証に数えない | V01 |

版5有限弧フィレットの標準validateとChrome8操作はPASS。Wineは今回未実行。
版1〜5の実保存ファイルを再構築照合した。
過去の実行中docstring変更によるStudy失敗は引継ぎに保持。今回の検証中は実装を編集していない。
out/が別環境で欠けても、過去の実行と現在再現できる状態を区別する。

## 旧計画からの訂正

- P0-01〜03を完了へ移す。Gmsh直接読込・任意輪郭生成は含めない。
- P1-03は平坦z端に限り完了。P1-01より先に実装・検証済み。
- P1-02/04、P2-01/02は部分完了。P1-06はローカルO01範囲で完了。残件は[BACKLOG.md](BACKLOG.md)。
- P2-04はGUI範囲で完了。GUI完成を一般追跡・tune完成に読み替えない。
- P0-04の比較ADRとP1-05の実機参照は残す。未実施を根拠なく廃止/完了にしない。
- seed時の期間見積もりは進捗や互換対象を反映しないため現行納期として使わない。

旧版の挙動確認では、既存Wine記録のSFO表示7.17（2006-01-13）とインストーラー名7.20を分ける。
製品単位の版・入出力仕様を一括して「7.20完全互換」と扱わない。

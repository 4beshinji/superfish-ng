# 変更範囲に応じた検証とテスト棚卸し

2026-09-15 JST：[明示参照座標による曲線比較版5](CURVED_REFERENCE_PARTITION.md)を実装・限定受入。
旧新の初期接続と境界分割が異なる場合に、各実P2写像と全親被覆を確認して保存場を比較する。
新6/既存36unitの分割42件、非アフィン4実FEM/独立重み積分/尺度則/CLI、Chrome新版11・旧版10項目がPASS。
元24ファイルとGUI取り込み4場の全配列/RF一致を確認。全handle終端回収。親33=9/17/6/1、D01親監査と全計画goalは継続する。


2026-09-15 JST：D01の[異なる初期接続の共通参照分割](REFERENCE_PARTITION.md)を計算基盤として追加。
全親面積の厳密被覆・独立二次積分・境界分割変更・二つの親内座標・番号/方向・不正入力/予算を新5件で検査。
既存交差分割4件と合わせ9件0.200秒PASS。曲線P2写像/実FEM/保存/GUIへの接続は未実装、親33=9/17/6/1を維持する。


2026-09-15 JST最終検証：[tune個別ID回復](TUNING_IDENTITY_RECOVERY.md)の曲線保存再生20解/10条件がPASS（追加FEM0）。
全339モジュール1742件の実行は1858.249秒で移行テスト3subtest ERROR、3skipを記録して終了1。
Study例をCaseとして読むテストを修正し、当該8件が0.383秒PASS。HTTP制限のskip1件も許可環境で0.563秒PASS。
最終証拠は1740件成功・任意NGSolve参照2件skipの分割実行。単一の全validate.py成功とは呼ばない。
標準数値は別の--skip-testsでPASS、既存9モード23量のf差0/最大相対差8.882e-16未満。曲線検証後のソース差は移行テスト1ファイルだけ。
受入索引out/tuning-identity-recovery-20260914/acceptance.json。全handle終端回収。親33=9/17/6/1、全計画goal ACTIVE。


2026-09-14：[tuneの個別ID回復](TUNING_IDENTITY_RECOVERY.md)は新9件195.776秒・関連51件319.436秒PASS。
追加TE直接利用先1件0.044秒と外側版6のTE拒否2確認もPASS。unit計61件。対象一覧と独立不変条件は同書。専用55FEM54.516秒、実worker19FEM13.340秒、CLI再開1新FEM、Chrome新21/旧16項目がPASS。
全17点のnative配列/RFは直接実行・worker・GUIで完全一致し、CLIの1追加点も一致。照合の追加FEM0、525元ファイル不変。
GUI外部HTTP0、全12ジョブ終端後に専用GUI停止。全suite/seed/Hosted CI/新Wine比較は今回未実行。
数値の実行範囲と追加の曲線保存解再利用はout/tuning-identity-recovery-20260914/acceptance.jsonと同書に記録する。

2026-09-14：[適応Studyの個別ID回復](ADAPTIVE_STUDY_IDENTITY_RECOVERY.md)は新8件41.647秒と関連46件83.750秒がPASS。
変更前redと最初の2不変条件22.074秒を保持。専用25FEM37.820秒、worker11FEM17.482秒、Chrome新15/旧10項目がPASS。
pilot3解は専用25解に含めない。求積次数18/逆向き保存解再検証とGUI7点の全配列/RF比較は追加FEM0。
1070ソース系/327製品SHA一致、210GUI比較元ファイル不変、外部HTTP0。全12GUIジョブ終端後に専用GUIを停止した。
対象一覧・並行範囲・全終端は同書とout/adaptive-study-identity-recovery-20260914/acceptance.json。
全suite/seed/Hosted CI/新Wine比較は今回未実行。次のtune接続ではその直接利用先を選択する。

2026-09-14：[逐次Study個別ID回復](TRACKED_STUDY_IDENTITY_RECOVERY.md)は新7件48.608秒と関連44件97.141秒がPASS。
専用20FEM53.017秒、実worker8FEM26.550秒、共有検査の既存完了Study18保存解74.532秒（新FEM0）がPASS。
全1067sourceは不変。Chrome新16/旧11/適応10項目、326製品SHA不変、外部HTTP0。全16GUIジョブ終端確認後に専用GUIを終了。
直接/API worker/GUIの全6点でnative全配列・RFが完全一致。GUI照合の追加FEM0、180保存ファイル不変。
最初の追加照合は配列/RF成功後にSHA検証器の文字列/Pathの型違いで停止し、検証器だけ補修した。
対象一覧・実行の並行範囲・全終端はout/tracked-study-identity-recovery-20260914/acceptance.json。全suite/seed/Hosted CI/新Wine比較は今回未実行。

2026-09-14：[完了StudyのID回復](STUDY_IDENTITY_RECOVERY.md)は関連50unitが19.852秒PASS。
専用18FEMは全回復検査後、解析零電場成分の相対分母により停止。E全体のノルムへ検証器を直し、同じ18解を19.333秒でPASS、追加FEM0。
曲線Study直接利用先3件237.351秒と追加の表面収束拒否1件7.055秒もPASS。最終54件の分割証拠。
Chrome新版8/単独履歴17項目PASS。数値1064source以後の差はStudyブラウザー検証器と追加テストだけで、325製品と282元保存ファイルは不変。
対象一覧・曲線Study直接消費先3件・初期失敗・全終端はout/study-identity-recovery-20260914/acceptance.json。全suite/seed/Hosted CI/新Wine比較は未実行。

2026-09-14：[個別ID回復](MODE_IDENTITY_RECOVERY.md)の新9件と直接利用先の計65unitは5.842秒PASS。
対象一覧は同書、記録はout/mode-identity-recovery-20260914/selected-tests.log。
専用検証は最初に9実FEMを保存し、RF読込の検証器不備で停止。補修後、同じ9保存解を--reuse-nativeで再検証し4.188秒PASS、追加FEM0。
Bessel解析交差/縮退、独立ID置換/集合境界、回復/再継続/拒否、長さ/エネルギー尺度則の場とRFを確認した。
Chrome17項目PASS、外部HTTP0。初回13項目後の同名ダウンロード検証器失敗も保持する。
最終レビューで旧履歴版1の回復ボタン有効化を再現・補修し、追加2項目と上記17項目を再確認した。
数値1062ソース系からの差はブラウザー検証器とapp.jsのボタン条件。325製品SHAと108nativeファイルは最終一致、全終端回収済み。
索引out/mode-identity-recovery-20260914/acceptance.json。全suite/seed/Hosted CI/新Wine比較は今回未実行。

2026-09-14 JST：[D01元要件照合](D01_CURRENT_AUDIT.md)で50件4.089秒+多対多6件0.308秒がPASS。
専用円筒交差2・合流分裂3・多対多1の計6新FEMもPASS、1059ソース系不変。全suite/seed/新ブラウザーは未実行。
元バックログの個別枝回復は未実装なので親受入は保留。コマンドと証拠は同書およびout/d01-original-acceptance-20260914/audit.json。

2026-09-14 JST：[RF探索の幾何変数版3](RF_OPTIMIZATION_GEOMETRY.md)の限定受入を完了。
新独立2件の変更前失敗を保持し、実装後4.139秒でGreen面積/体積・混合項・単位換算がPASS。
関連29unitは937.813秒で28合格/1ERROR。軸原点契約に違反した試験データ1件を軸長変化へ直し、別実行0.818秒で合格した分割証拠。
専用36FEMは6206.019秒PASS。全3系列で両変数・個別追跡・保存再生/改変拒否・Green/MaxwellのRF五量と内部三場を確認。
Chrome新版24/旧版13/追加入力11項目PASS、324製品SHA一致。粗いCLI/GUIの既存6水準はnative配列とRF数値が一致。
1059ソース系は専用実行中不変、終了後の差は合格済み試験データ1件とmodule docstringのみ。他AST一致を保持する。
初期粗系列の未収束と検証器の仮定違反は同書に記録。索引はout/rf-optimization-geometry-20260914/acceptance.json。
全suite/seed/Hosted CI/新Wine比較は今回未実行。D03の親依存全体の受入とは区別する。

2026-09-14 JST：[非アフィン曲線tune版5](CURVED_HARMONIC_TUNING.md)の関連35unitは309.382秒PASS。
新test_curved_harmonic_tuning6件と、curved_tuning/tuning/coupled_tuning/polynomial_tuning/gui_tuningを実行した。
直接利用先のtest_tuning_jobs7件も7.212秒PASS。合計42件の二つの実行記録。
幾何2件の変更前失敗/変更後15.796秒PASS、専用数値とChromeはout/curved-harmonic-tuning-20260914に保持。
全suite/seed/Hosted CIは今回実行せず、調整器と直接利用箇所に影響を限定する。
専用18FEMは758.895秒PASS、1055ソース系SHA不変。独立Green/Maxwell五量・内部三場、Bessel順位交差と無効内部形状の保存保持を確認。
Chrome新版12/旧版7項目PASS、323製品SHA一致、外部HTTP0。初回新版の検証器待機不足3項目後FAILと補修は専用文書。
CLI/GUI全4試行の保存配列完全一致・RF数値一致、原JSONごとのCase hash照合もPASS（32保存ファイル不変、新FEMなし）。
数値後の差はブラウザー検証器のみ。全終端/コマンド/出力SHAはout/curved-harmonic-tuning-20260914/acceptance.json。


2026-09-14 JST：[固定局所履歴付きRF探索](RF_OPTIMIZATION_HISTORY.md)の関連29unitは614.814秒PASS。
対象はtest_rf_optimization_history、test_surface_convergence、test_rf_design、test_rf_optimization、
test_gui_rf_optimization、test_rf_optimization_jobs、test_rf_optimization_prefix_reuse、test_rf_optimization_start_concurrency。
新5件の履歴保持/アフィン対応/strict入力/GUI往復/失敗保存と、既存の元FEM・表面量・設計評価・中止再開/改変拒否を確認。
専用24FEMとChrome新旧経路の独立検証はRF_OPTIMIZATION_HISTORYの最終記録を参照する。全suite/seed/Hosted CIは今回未実行。
専用検証は897.260秒PASS、解析五量/Green/MaxwellのRF最大7.039e-14・場最大9.762e-14。
Chrome旧版13項目PASS。新版初回は12項目成功後に検証器のJSON型変更でFAIL、修正後は既存完了文書で14項目PASS（新FEMなし）。
製品322SHAは全ブラウザー/専用/最終で一致し、専用1050SHAからの変更はブラウザー検証器1ファイルのみ。索引はout/rf-optimization-history-20260914/acceptance.json。

2026-09-14 JST：[A01候補比較](A01_BACKEND_COMPARISON.md)は新test_cavsim_comparison4件0.026秒と既存独立比較7件が合格。
既存の判定5件は初回10件実行で確認、当時の物理2skipを隔離NGSolve環境のReferencePhysicsTests2件0.113秒で補った。最終11件の分割証拠。
scripts/compare_cavsim2d.pyの最終final-correctedは36実FEM/10.436秒PASS。閉PEC円筒/円錐台の双方3水準×3回、
解析五量/境界長/面積/体積/エネルギー/内部E・Hと実DOF・交互順の時間を確認。1047ソース系と候補79ファイルSHAは不変。
初回importと公開Pillboxの端条件不一致、比較器のtuple/Case/Sampler/基底Cavityの修正前失敗はout/a01-backend-20260914に保持。
measuredの先行1回PASSには未使用Pillbox入力記録があったため、専用Cavity/Profile記録へ替えた最終36 solveを正式証拠とする。
データと誤差対DOF/時間の図をbenchmarks/cavsim2dへ保存、出典/生出力/全終端の索引はout/a01-backend-20260914/acceptance.json。
製品/求積/許容差は不変。全suite/seed/ブラウザー/Hosted CI/新Wine比較は実行していない。

2026-09-14 JST：[曲線親子追跡の共通履歴共有](NESTED_RECONSTRUCTION_REUSE.md)は最終9+32=41unitでPASS。
test_nested_curved_trackingの9件7.377秒、RF指標/適応版4・5/対称性/prefix再利用/表面方針/保存と固定patternの32件121.162秒。
新4件を含む。初回12件8.447秒の後、新側メッシュの同hash型違反1件を0.421秒FAILで再現し、厳密解析を保持して補修した。
最終validate_nested_reconstruction_reuse.pyは45.855秒PASS。同一native入力の3形状×3回交互比較で転送/追跡/RF指標完全一致。
RF指標約1.50〜1.53倍、再構築約2倍を観測。並行FEMはなし。厳密解析補修前の比較は別記録として保持した。
既存validate_nested_curved_tracking.pyも18保存場/12組・円筒解析五量/尺度則・CLI/replayがPASS、新FEMなし。
32unitとの並行実行であり、この時間を単独性能とは扱わない。最終両専用検証の1045ソース系SHAが一致、全native入力不変。
全対象/コマンド/終端はout/nested-reconstruction-reuse-20260914/acceptance.json。影響は曲線親子追跡と直接利用箇所に限定。
今回全件validate/seed/ブラウザー/Hosted CI/新Wine比較は実施していない。過去full失敗と対象補修をfull PASSへ読み替えない。

2026-09-14 JST：[共通比較分割版4](CURVED_COMPARISON_OVERLAY.md)は新test_curved_comparison_overlayの7件を2+3+2で確認。
初回独立被覆/逆方向2件API不在red、実装後0.140秒PASS。追跡/予算/保存3件1.468秒、独立番号/固定pattern2件0.318秒PASS。
既存curved_piecewise_remesh_tracking/piecewise_remesh_tracking/curved_same_domain_tracking/curved_affine_remesh_tracking/curved_comparison_correspondence/curved_selection_transfer/saved_mode_tracking/mode_tracking_history/gui_mode_trackingの56件61.240秒PASS。
選択前に全モジュールの実在を確認した。全コマンドと終端はout/curved-comparison-overlay-20260914/selected-regressions.json。
専用validate_curved_piecewise_remesh_tracking.py --common-partitionは4新FEM127.848秒PASS、1044ソース系不変。
独立二重積分/Green体積・尺度則・次数4/8・逆方向/完全保存/CLIを確認。初期26→比較111/112→共通119三角形。
実Chrome版4/旧版3の各10項目PASS、外部HTTP0、各322製品SHAが実行中不変。ブラウザーで新FEMは実行せず、両画像を目視した。
初回版4は5項目後に15秒待機で終了1。保存pairの直接逆方向再生28.241秒PASSを確認し、版4の検証器待機だけ60秒へ変更した。
数値時からブラウザー完了までの差はブラウザー待機/診断と追加2unitだけ。追加元native比較0.498秒PASS、全u/f/P2座標/接続がGUI取込前後で完全一致、36保存ファイル不変。
最終レビューでは標本評価から未使用の初期要素基底/Jacobianを除き、共通物理点/行列式だけを返すようにした。専用4保存比較の全再構築は全報告値が完全一致、新FEMなし。
この製品差はcurved_comparison_overlay.pyのみ。最終1044sourceはreviewed-source-sha256.json、受入索引はacceptance.json。全件validate/seed/Hosted CI/新Wine比較は今回実施していない。

2026-09-14 JST：[細分履歴間の選択領域移送](CURVED_SELECTION_TRANSFER.md)は新test_curved_selection_transferの8件を分割確認。
初回独立2件API不在red、実装後0.084秒PASS。最初の6件は5合格/fixture履歴方式混在1ERROR、当該修正1件0.332秒PASS。
厳密範囲/対称領域2件0.348秒、保存JSON/NumPy浮動小数修正後の関連2件0.317秒PASS。再読込のred/中間失敗も保持する。
既存はcurved_marked_refinement/curved_refinement/frozen_curved_refinement/curved_comparison_correspondence/gui_curved_mesh_selection/project/project_mesh/gui_hphiを選択。
初回は存在しないtest_curved_refinement_historyも指定し、43件43.847秒=41合格/1ERROR/HTTP1skip。
実curved_refinement_steps/planar_tracking_overlapの8件3.847秒と、許可環境の同HTTP1件0.564秒で補完。最終50件の分割証拠。
専用validate_curved_selection_transfer.pyは4新FEM6.299秒PASS。独立P2物理積分/尺度則/非nested領域/CLI/保存を確認。
Chrome新18/既存履歴20項目、各1新FEM、外部HTTP0、両321製品SHAは最終一致。初回selectorと中間replayの失敗は別記録で保持。
新validate_curved_selection_transfer_browser.pyは18.602秒PASS、新FEMなし。小規模/6,656要素の全再構築・独立物理積分、GUI/専用FEMの全native配列一致とRF11量を確認。
数値時1041sourceからの差は新native検証器/ブラウザーselector/移送replay/追加unitの4パス。最終1042sourceと23保存artifact不変、3画面目視済み。
索引out/curved-selection-transfer-20260914/acceptance.json。全件validate/seed/Hosted CI/新Wine比較は実施していない。単一全件PASSへ読み替えない。

2026-09-14 JST：[曲線比較メッシュ番号対応](CURVED_COMPARISON_CORRESPONDENCE.md)は新8件の分割検証。
初回2件API不在red、幾何2件の最終0.759秒PASS。全8件16.409秒は7PASS/境界負例1FAIL、明示境界節点へ直した当該1件0.332秒PASS。
負例は番号変更後の内部節点を動かしていたため有効だった。製品/許容差は不変。単一8件合格とはしない。
専用validate_curved_piecewise_remesh_tracking.py --automatic-numberingは4新FEM/35.946秒PASS、1037ソース系不変。
独立P2幾何・既知Hφ=rの二重積分/Green・Maxwell・完全保存/CLIを確認した。
実Chrome版3の10/従来版2の8項目、外部HTTP0、320製品SHA不変、両画面目視済み。ブラウザーで新FEMは行わない。
対象は新test_curved_comparison_correspondenceと既存curved_piecewise/piecewise/curved_same_domain/curved_affine_remesh/saved_mode_tracking/mode_tracking_history/gui_mode_tracking/curved_harmonic_study/curved_remesh_study。
既存9モジュール56件701.015秒PASS。全コマンド/終端証拠はout/curved-comparison-correspondence-20260914/acceptance.jsonとselected-regressions.log。
同じ分率方針の追加実保存場自己比較は局所→一様/132比較要素で内積1.0、6.463秒PASS、元9ファイル不変、新FEMなし。
数値/両ブラウザーのSHAは最終実装と一致し、全handle/GUIサーバーは終了。全件/seed/Hosted CI/新Wine比較を今回の証拠としない。

2026-09-14 JST：[固定二次境界の内部再生成](CURVED_REMESH_GENERATION.md)は新9件の分割証拠、既存58件を確認した。
初回独立2件はAPI不在red、最初の2件4.350秒PASS。新7件10.470秒のうち6合格、相似Case上限の入力漏れ1ERROR。
相似修正/追加凹形状2件3.892秒は1合格/方向符号前提1FAIL、凹形状修正1件0.605秒PASS、予算/粗化2件2.681秒PASS。
既存は選択49件474.822秒のうち実48件合格・誤指定test_guiのimport1ERROR、実HTTP GUI/起動清掃10件6.090秒PASS。
全一覧/コマンドはout/curved-remesh-generation-20260914/selected-regressions.json、補充はgui-regressions.log。単一全件PASSとは呼ばない。
専用最終6新FEM88.290秒PASS、実worker再生成/保存再開3 FEM304.515秒PASS。初回5 FEM後の不整合面積指定による生成失敗は別に保持。
固定辺L/底角αから面積下限L²tanα/4を独立算出し、境界を明示変更した別円筒で同じ面積/角度を検証。製品/許容差は無変更。
両実行の1035sourceはそれぞれ不変で、間の差は検証器の円筒元辺長1箇所だけ。Chrome新22/既存版3の13項目、各2 FEM、外部HTTP0、319製品SHAが現行一致。
GUIと独立Studyの全native係数/周波数/二次座標・接続一致、57ファイル不変、1.163秒、新FEMなし。画面目視済み。
索引out/curved-remesh-generation-20260914/acceptance.json。全件validate/seed/Hosted CI/新Wine/実測は未実行。並行時間を単独性能とはしない。

2026-09-14 JST：[条件別初期メッシュStudy版4](CURVED_REMESH_STUDY.md)は新8unit413.395秒、既存16モジュール78件510.514秒PASS。
変更前の独立2件は版4不在red、初回幾何2件18.157秒PASS。初回回帰起動器のvenvリンク解決誤りでsystem Pythonのimport16ERROR、FEM未実行。
起動器だけ修正した最終78件の全一覧/コマンドはout/curved-remesh-study-20260914/selected-regressions-final.json。
専用検証器の--remesh-studyは6 FEM137.626秒、--workers-only追加は3 FEM353.704秒、円筒解析交差は2 FEM112.694秒PASS。
独立Green、m換算/Maxwell、実場の順位交差、元点再利用/実二分・JobManager再生成後resume/完全replayを確認。三実行の1031source不変。
Chrome新18/既存版3の13項目PASS、各2 FEM、外部HTTP0、318製品SHA一致、画像目視済み。新GUI/CLIの同一入力/五量とnative全係数が一致。
native追加比較1.393秒PASS、57保存ファイル不変、新FEMなし。索引out/curved-remesh-study-20260914/acceptance.json。
限定Study/直接消費先の検証で、全件validate/seed/Hosted CI/新Wine/実測は未実行。並行検証時間を単独性能と解釈しない。

2026-09-14 JST：[初期メッシュ置換API/CLI](CURVED_PROJECT_REMESH.md)は新6unit7.994秒と非アフィン受渡し1件2.975秒、独立移動/番号付替え1件1.467秒PASS。
初回API不在redと、実装後のkeyword-only引数のテスト誤記による1失敗を保持する。最終新8件は6+1+1の分割合格。
既存harmonic_deformation/frozen_refinement/project_mesh/curved_same_domain/curved_piecewiseの34件75.672秒とexternal_mesh_study4件0.478秒PASS。
専用validate_curved_project_remesh.pyは53.996秒、8新FEM。独立幾何/Maxwellと元場追跡・完全保存再生、別生成円筒のf/RF解析値を確認。
実行中1,028ソース系は不変。以後の差分は独立移動/番号付替え1テストだけ、製品は不変。
索引out/curved-project-remesh-20260914/acceptance.json。新API/CLIと直接消費先に限定し、全件/seed/browser/Hosted CI/新Wine比較は未実行。

2026-09-14 JST：[単独Project変形GUI](GUI_CURVED_DEFORMATION.md)は新3unitとGUI/履歴/Projectの直接消費先を選択。
最終の新3/既存37件には分割合格証拠がある。初回選択は実31件合格と誤指定モジュール1件で終了1。
正しいProject二モジュールの9件では例題の旧分類前提1件に2エラー。専用Study往復と単独Case拒否を加え、当該1件0.204秒PASS。
Chrome新21/既存固定履歴9項目がPASS。後続の失敗状態表示/図中文字修正とRF方針/実反転等の追加6項目もPASS、新FEMなし。
新/既存browser各1とCLI1 FEMに加え、初回CLI比較パス誤指定のbrowser1 FEMを保持する。
専用保存場再検証はR/Q式誤記補修後1.489秒PASS、1,023source/27native不変。最終追加browserの316製品SHAが現行一致。
索引out/gui-curved-deformation-20260914/acceptance.json。全件/seed/Hosted CI/新Wine比較は未実行。全件の合格へ読み替えない。

2026-09-14 JST：[曲線法則Study](CURVED_HARMONIC_STUDY.md)は新7件239.756秒と追加二次法則1件6.998秒PASS。
既存14モジュール65件278.056秒PASS。全一覧/コマンドはout/curved-harmonic-study-20260914/selected-regressions.json。
専用CLI/幾何/RF/保存追跡の6 FEMは111.592秒、実適応worker再開3 FEMは223.940秒、円筒解析順位交差2 FEMは53.647秒PASS。
Chrome新14/既存アフィン11項目PASS、各Study workerの2 FEMと保存再生を含む。外部HTTP0、画像目視済み。
数値/worker時1018ソース系は不変。以後は円筒検証器と追加1テストのみ変更し、製品315ファイルは両browser/最終で一致する。
索引out/curved-harmonic-study-20260914/acceptance.json。全件/seed/Hosted CI/新Wine比較/実測は今回未実行。

2026-09-14 JST：[調和変位による曲線変形](CURVED_HARMONIC_DEFORMATION.md)の新8件は分割検証。
最初の幾何2件4.826秒PASS、新7件は35.058秒で6合格/負例前提1不合格。凸形状は有効だったため、実反転する凹形状へ検証入力だけを修正し1件2.540秒PASS。
追加の弦内境界節点/初期一様細分と標準importの幾何確認2件は3.992秒PASS。8件一括再実行とは呼ばない。
既存5モジュール33件は44.101秒PASS（全一覧は同書とselected-regressions.json）。専用4 FEM/CLI/独立尺度・場形/保存追跡再生は47.856秒PASS。
幾何の解析差は別のanalytic-geometry.json。専用実行中1,012ソース系ファイル不変、最終SHA一致。
証拠索引out/curved-harmonic-deformation-20260914/acceptance.json。新API/CLIと直接消費先に限定し、全件/seed/browser/Hosted CI/新Wine比較は未実行。

2026-09-14 JST：[曲線アフィンStudy](CURVED_AFFINE_STUDY.md)は新7件を含む14モジュール62テスト、340.117秒PASS。
モジュール一覧とコマンドはout/curved-affine-study-20260914/selected-tests.json。巨大整数の負例追加でOverflowErrorを再現し、入力エラーへの補修後、厳密入力と旧Studyの2件を0.297秒で再検査PASS。
専用validate_curved_affine_study.pyは9 FEM/CLI/独立尺度則/解析順位交差/実区間二分を111.541秒で検証。
同スクリプトの--workers-onlyは追加5 FEM、JobManager再生成・逐次/適応一時停止と再開・全保存再検証を174.721秒でPASS。既存点を再利用し、適応の実UNVERIFIEDを維持した。
Chrome最終10項目PASS後の製品変更はCSSのみ。表示3項目と画像を別検証し、新しいFEMは不要とした。外部HTTP0。
最初の入力拒否、巨大整数のred、専用楕円せん断の範囲外拒否、初回browserの非同期待機不足も保持。
証拠索引out/curved-affine-study-20260914/acceptance.json。今回の対象はStudyと直接消費先で、全件/seed/Hosted CI/新Wine比較は再実行しない。前段の全件試行と混同しない。

2026-09-14 JST：[曲線局所分割の固定](FROZEN_CURVED_REFINEMENT.md)は関連21件（14.777秒）+追加2件（2.139秒）、専用8 FEM/実TUNED（75.988秒）、Chrome新9/既存20項目がPASS。
保存契約の共有先を確認するため全validateを一度起動し、全1,602件を888.194秒で回収した。1,598合格・2skip・2不合格、終了1。
不合格は既存幾何診断の版/対応版一覧の旧期待値。製品を変えず2テストファイルを補修し、両モジュール12件を1.198秒で再実行PASS。
seedは別の--skip-tests実行でPASS、基準9モード19量の周波数差0・最大相対差8.882e-16。
初回FAILと補修後の対象再実行・seed別実行を区別し、修正後の単一full PASSとは呼ばない。以後の製品変更はなく成功証拠を再利用する。
証拠索引out/frozen-curved-refinement-20260914/acceptance.json、全件一覧out/validation-frozen-curved-refinement-20260914/test-run/report.json。
Hosted CI/新Wine比較/実測検証は未実行。
2026-09-14 JST：[曲線比較メッシュ追跡](CURVED_PIECEWISE_REMESH_TRACKING.md)は新8/直線区分5/同一曲線6/曲線アフィン4の関連23テスト。
初回20件中19合格（30.864秒）。負例Caseのcached contour修正後2件（3.014秒）、追加2件（11.563秒）が合格。
専用4実FEM/CLI/保存逆向き再生/独立体積/場形/Maxwell尺度則は28.933秒PASS。
最終Chrome8項目、外部HTTP0。初回宣言hash差と最終画像の読込待ちを検証器で修正した。
製品は専用検証後不変。比較入力/既存境界検査抽出の影響先へ限定し、全unit/seed/全validate/Hosted CI/サーバー再起動は未実行。

2026-09-14 JST：[履歴途中への図上挿入](GUI_CURVED_HISTORY_INSERTION.md)は関連4unit（10.838秒）、
新Chrome20項目、従来SVG6項目/大規模21項目、独立native検証31.223秒PASS。
前半6応答/232・26,664要素の最終履歴、独立境界積分、保存場RF9量を確認。
初回後の製品差分は列幅CSSのみで、その画像と従来操作を別途確認した。実FEMは小規模2ジョブ。
FEM/Caseスキーマは不変。全unit/seed/全validate/Hosted CI/サーバー再起動は実施しない。

2026-09-14 JST：[大規模曲線メッシュ選択](LARGE_CURVED_MESH_SELECTION.md)はtest_gui_curved_mesh_selectionの4unit（10.725秒）。
最終製品のChromeは新17+21、従来の一様/局所履歴各6チェックと実FEM。独立native再構築/境界積分は63.546秒PASS。
大規模UI競合は確認済みnative応答を再利用する制御検査、250,000要素の測定は描画器だけと明示する。
FEM/保存契約は不変で、全unit/seed/全validate/Hosted CI/サーバー再起動は実施しない。

2026-09-14 JST：[C00/K02版別入力参照](C00_CONIC_INPUT_RESEARCH.md)は文書・参照台帳だけの変更。
元入力/設定/出力7ファイルのhash/版表示、JSON/文書差分を照合。
文中の数学対応は自作36弧612点、陰関数/頂点距離/接線/線積分と負例2件で確認した。
製品ソース系988ファイル不変。AF変換受入や旧数値比較とはせず、unit/FEM/seed/全validate/GUI/Hosted CIは実行しない。

2026-09-14 JST：[G03現行照合](G03_CURRENT_AUDIT.md)は、専用validate_geometry_surface_convergence.pyを1回実行し577.959秒PASS。保存6native再検証+追加3solve、固定幾何6区間/幾何2区間の五量・場対応・解析幾何/積分・Ritzを確認。元アーカイブと988ソース系ファイルは不変。製品/FEM/GUI無変更のためunit/seed/全validate/Hosted CI/ブラウザーは再実行しない。元の全検証や旧保存を新たな全機能合格と呼ばない。

2026-09-14 JST：構築版10の[非円円錐曲線フィレット](NONCIRCULAR_CONIC_FILLET.md)は関連57unit（42.890秒）と旧版3/4の追加2unitを実行。
初回新9unitもPASS。対象モジュール/ケースは同書に記載した。
専用validate_noncircular_conic_fillet.pyの32条件61元点対、解析面積/体積と実FEM尺度則は146.511秒PASS。
初回の反転参照の誤り、保存された有限弧に合わせた検証器修正と専用全再実行を記録した。
Chrome初回56/実再起動54、計42取得/21組の保存バイト一致、3画像目視もPASS。
製品/検証器は以後不変。新幾何の専用FEMを用い、seed/全validate/Hosted CIは未実行。証拠索引はout/noncircular-conic-fillet-20260914/acceptance.json。

2026-09-14 JST：共通支持の等距離/反対枝は[EQUAL_DISTANCE_CONIC_BRANCHES.md](EQUAL_DISTANCE_CONIC_BRANCHES.md)の関連15モジュール112テストと追加1主軸変換不変量で確認。専用576条件94元点対/最近点1,080不等式、構築付属診断GUI初回/再起動の100チェック42取得を選択した。初回は凸性検証器の引数重複で停止し、検証器だけを修正して専用再実行2.404秒PASS。製品数値を変えずに追加した1テストは単独実行し、既存の受入証拠を再利用する。全validate/seed/FEM/Hosted CIを実行したとはしない。

2026-09-14 JST：一般両非零オフセットの変更は[GENERAL_CONIC_OFFSET_INTERSECTIONS.md](GENERAL_CONIC_OFFSET_INTERSECTIONS.md)の関連18モジュールを選択。118テストと追加2解析不変量、専用7条件36射影候補/87独立法線足/18元点対、構築付属診断GUIの初回/再起動を検査する。初回専用検証は数値比較7条件合格後、並行テスト編集を全ファイル不変性ガードが検出したため最終受入に使わず、入力SHA/変更パスを保存する実行器で編集終了後に一度再検証した。seed/全validateを実行したとはしない。

2026-09-14 JST。通常の開発では対象テストと影響先を選んで実行する。
着手時・小変更ごとの全件実行、全unittest直後の全validate、文書更新後の再実行は要求しない。
この手順が、過去の開発記録や開始プロンプトにある一律の全件実行指示に優先する。

## 棚卸し結果

変更前のHEAD `0a7aa37` は299テストファイル・1,456テストメソッド、
`scripts/validate*.py` 167本（総合入口1本・専用166本）。テストのAST集計と保存済み全件一覧が一致した。
下表はファイル名で重複なく分類した内訳。純粋なunit/integrationの境界ではなく、
各ファイルには解析・実FEM・保存・CLIの検査が混在する。167本は全件自動実行されるわけではない。

| 検査群 | ファイル | テスト数 | 保存済み延べ秒 |
|---|---:|---:|---:|
| `test_gui_*` | 17 | 64 | 989.107 |
| 残りのjob系（startup cleanup・start concurrencyを含む） | 17 | 106 | 964.156 |
| 残りのsaved/storage・save completion・project・static project・package | 33 | 166 | 1,148.254 |
| その他：物理・幾何・Study・入力契約・実行器等 | 232 | 1,120 | 2,355.160 |
| 合計 | 299 | 1,456 | 5,456.677 |

時間の出典は `out/validation-parallel-checkpoint-20260914/test-run/report.json`。
2026-09-14の既存16プロセス実行は壁時計718.595秒、1,453合格・3skip。
延べ秒は並行実行した各モジュールプロセスの時間の和で、CPU時間でも逐次実行時間でもない。
これは今回の再測定ではなく、同じ環境で競合の影響も受けた過去の観測値である。

| 遅いファイル（`tests/`） | 件数 | 秒 |
|---|---:|---:|
| `test_gui_static_field_studies.py` | 6 | 684.344 |
| `test_static_field_study_jobs.py` | 6 | 468.367 |
| `test_rf_optimization.py` | 5 | 376.891 |
| `test_hphi_tracking_history_saved.py` | 5 | 289.836 |
| `test_static_field_study.py` | 7 | 237.981 |
| `test_rf_optimization_jobs.py` | 4 | 222.769 |
| `test_planar_magnetic_force_material_saved.py` | 6 | 187.357 |
| `test_planar_magnetic_force_saved.py` | 6 | 132.004 |
| `test_curved_tuning.py` | 5 | 121.409 |
| `test_hphi_tracking_history.py` | 4 | 99.089 |

上位10ファイルで延べ秒の51.68%。最長の1ファイルは全体の壁時計時間に近い。
プロセス数を増やすだけでは、このファイル内の実FEM反復を短縮できない。

## 重複と判断

| 対象 | 判断・今後の扱い |
|---|---|
| 旧AGENTSの着手時全unittest＋数値変更後validate | validate内部でも全unittestを実行するため重複。着手時の一律実行を廃止し、必要なseed検証は`--skip-tests`で分離する。 |
| `test_physics.py`とvalidateの6モードpillbox | 同じ寸法・格子のsolveが重なる。前者には独立な場・RF・表面場のassert、後者には再現用出力がある。通常の修正は対象assert、seed出力比較が必要な時だけvalidateを使う。 |
| Static Project→Study→worker→GUI | `test_static_field_project.py`の19条件（8形式×P1/P2＋B-H 3形式）を複数層がループし、Studyの両パラメータ・各点を再求解する。各層の保存・中止・改変拒否は固有の契約。入力だけの変更にGUIの全条件FEM再生まで要求しない。 |
| `validate_static_field_project.py`等の専用検証 | 受入済み33参照Caseの全量比較等を行う広い受入試験。機能の初回受入や該当する数値/保存契約変更時に使い、無関係な機能追加で一括再生しない。 |
| 保存後・GUI再起動後の再求解 | 再現性・状態遷移・改変検知を確認するための固有の検査。該当契約の変更時に残す。再起動のない表示文言変更まで全バックエンドを再生しない。 |
| 独立解析・尺度則・弱形式・場・RF・表面場 | 検出する誤りが異なるので維持。周波数や代数残差だけの検査に統合しない。 |
| 全件合格後の文書・hash・件数更新、同じ変更の統合 | 検査対象と依存が同一なら既存の合格を使う。衝突修正や依存変更があればその影響先を追加する。 |
| CIのfeature pushと同じPR | PRの実行に集約。main/masterへのpushは統合確認、手動起動は配布等に使う。列挙した説明文書だけの変更では自動全件を起動しない。 |

既存テストの削除・許容差緩和は行わない。削除/縮小するなら同じ入力・同じ期待値・同じ失敗を
どのテストが引き続き検出するかを示す。「遅い」「似た名前」だけを理由に削除しない。
次に上記の遅いファイルを変更する際は、安価な全形式パーサー検査と重い実FEM統合検査を分ける。
共有UIの状態遷移は代表的な成功/実失敗で確認し、全形式の実FEM比較は該当層の変更・節目で使う。
この分割やfixture再利用の大改修を、今回の手順変更の前提にはしない。

## 変更別の選び方

| 変更 | 通常実行する検査 | 広げる条件 |
|---|---|---|
| 説明・作業記録のみ | 差分・参照・コマンドの確認 | 数式、実行例、機械が読む契約を変えたら関連チェック |
| パーサー・単位・Project | 対応する`test_*project`/入力テスト、正常往復・未対応入力拒否 | Caseを実際に変換する変更なら該当する場/尺度則 |
| GUI表示/操作 | 該当GUIテストのケースと、変えた操作のブラウザー確認 | 共通アクセス/状態管理なら影響するGUI群とworker。全物理の再計算は一律に要求しない |
| 保存・worker | 対応するsaved/jobs、成功/実失敗・中止・再開・改変拒否のうち影響する契約 | 共通保存・JobManager変更なら利用側の代表経路、影響を限定できなければ全件 |
| 幾何・メッシュ | 該当する交差/接線/面積/タグ等の独立不変量と直接の利用先 | FEMメッシュも変わるなら該当形式の数値検証 |
| FEM・材料・場・RF・追跡 | 該当形式の独立解析/物理不変量と利用先、必要な専用validator | 共通組立・求積・定数・依存の広範な変更なら全件。seed TMへ影響すればseedのf/RFも比較 |
| テスト/検証実行器 | 成功・失敗伝播・実行範囲・報告の対象テストと必要なCLI確認 | テスト収集/分配そのものを変更したら全一覧との一致。単なる報告変更で全物理を再検証しない |
| リリース・大きな節目 | 全unittestを含むvalidateを1回、変更した機能の受入証拠を確認 | 未確認の契約・環境がある時だけ追加。全専用validator/全ブラウザーの再生を自動的に追加しない |

命名と`rg`で入口・呼出元を確認して対象を選ぶ。テスト同士のhelper importもあるため、
ファイル名の一致だけから「全依存を網羅した」としない。固定した短いsmoke一式を全変更の代用にも使わない。
例えば入力専用変更で同じファイル内の重いFEMケースが無関係なら、メソッドを指定してよい。
ただし数値/保存挙動に影響する変更で安価なケースだけを選ばない。

## 実行例

インストール済み環境（このcheckoutでは`source .venv/bin/activate`）で実行する。
修正中は失敗する対象だけを回し、最後に選択した対象と利用先を一度まとめて実行する。

```bash
# 関連する複数モジュール。testsを検索パスに加えて既存のhelper importを保つ。
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests python -m unittest -v test_static_field_project test_static_field_study

# 入力契約だけの例：実FEM再生を伴う別メソッドは実行しない。
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests python -m unittest -v test_gui_static_field_studies.StaticFieldStudyGuiTests.test_all_families_parameters_units_and_strict_json_input

# 一つの領域を並列実行。既存ランナーのpattern指定を利用する。
python scripts/run_tests.py --pattern 'test_axis_bh*.py' --out out/tests-axis-bh-new

# seedの数値出力が必要な変更。全unittestの再実行は含まない。
OPENBLAS_NUM_THREADS=1 python scripts/validate.py --skip-tests --out out/validation-seed-new

# 節目・広範な共通変更：全unittestとseedをまとめて一度実行。
OPENBLAS_NUM_THREADS=1 python scripts/validate.py --out out/validation-full-new
```

出力先は毎回未使用のパスを選ぶ。`--skip-tests`は`validation.json`へ
`scope=seed-numerics`、`tests.status=NOT_RUN`と未実行項目を記録する。
`passed`はその実行範囲の判定であり、全機能の合格ではない。報告生成も未実行を表示する。
省略しない従来の入口は全件実行を保つ。並列数・中断・ログは[並列検証](PARALLEL_VALIDATION.md)を参照。

seedの出力生成と全RF量の過去基準との比較は別の操作である。validateの`passed`だけでは
全RF差分や新しい物理形式の合格を主張できない。必要な変更ではf/場/RF/表面場を別々に確認し、
差分の説明なくbenchmarksを更新しない。

結果は変更の説明に「対象・結果・必要なら未実行の範囲」を短く記録する。
対象コード・入力・参照・関連依存/環境が変わらなければ、その範囲の合格を再利用してよい。
READMEや進行記録の更新だけで全結果を無効化しない。未実行は新たなPASSと呼ばず、
今回の部分検証を過去の全件検証と足して「現版の全機能を再実行済み」とも呼ばない。
この判断のための新しい必須承認・hash台帳・検証サービスは設けない。

## 今回の確認

実行範囲・失敗伝播・既存出力保護・集計表示を検査する4テストを追加し、
既存ランナーの対象指定で4件合格（0.547秒）。初回はテストのsubprocess mockが
環境情報取得の呼出しも数えたため1件失敗し、環境情報だけを固定して修正した。
製品FEMをmockしたこの4件は実行手順の検査であり、物理の受入とは数えない。

実際の`validate.py --skip-tests`と報告生成も成功。出力は
`out/validation-scope-audit-20260914`、対象テストは`out/tests-validation-scope-20260914`。
新seedのpillbox/shaped_cellの全モード辞書（f/RFを含む）は上記の既存受入出力と完全一致した。
CIのYAMLとトリガーをローカルで確認し、Hosted CIと全unittestは今回は実行していない。
既存1,456テスト・物理許容差・benchmarksを維持して、実行条件と入口を変更した。

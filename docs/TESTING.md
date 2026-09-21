H16-bは`test_material_hphi_tuning`、`test_material_hphi_tuning_nonuniform`、`test_material_hphi_tuning_recovery`。[独立解析目標、guard、回復と粗細gate](MATERIAL_HPHI_TUNING.md)。

H16-a候補/最終細分は`test_material_hphi_tune_trials`。直接利用先は`test_material_hphi_refinement`と`test_material_hphi_shape_tuning`。[実FEM追跡と移送不変量](MATERIAL_HPHI_TUNE_TRIALS.md)。

H16-a形状則は`test_material_hphi_shape_tuning`。直接利用先は`test_material_hphi_comparison`と`test_material_hphi.MaterialHphiTests.test_strict_physics_and_only_explicit_vacuum_axis_path`。[尺度/体積と加速区間](MATERIAL_HPHI_SHAPE.md)。

H16-a細分は`test_material_hphi_refinement`、直接利用先は`test_material_hphi_fem`。[材料領域/K/M移送不変量](MATERIAL_HPHI_REFINEMENT.md)。

H15統合は`test_material_hphi_tracking_integration`と`test_material_hphi_tracking_crossing`。独立物理は`scripts/validate_material_hphi_rf.py`。[分割検査・全条件監査](MATERIAL_HPHI_ACCEPTANCE.md)。

H15-c材料ID追跡は`test_material_hphi_tracking`。直接利用先は`test_material_hphi_spectral_resolution`。[検査と残る統合監査](MATERIAL_HPHI_ID_TRACKING.md)。

H15-c有限診断は`test_material_hphi_spectral_resolution`。直接利用先は`test_material_hphi_mass_projection`、物理対照は`test_material_hphi.MaterialHphiTests.test_layered_resonance_refines_frequency_field_and_wall_separately`。[検査範囲](MATERIAL_HPHI_SPECTRAL_RESOLUTION.md)。

H15-b材料scalar射影は`test_material_hphi_mass_projection`。直接利用先は`test_material_hphi_field_overlap`。[独立積分・質量保存/損失・尺度則](MATERIAL_HPHI_PROJECTION.md)。

H15-b材料元場比較は`test_material_hphi_field_overlap`。関連は`test_material_hphi_comparison`と`test_material_hphi.MaterialHphiTests.test_uniform_material_frequency_fields_energy_and_metal_wall_scaling`。[独立積分・真空極限・元RF検査](MATERIAL_HPHI_FIELDS.md)。

H15-a材料領域/全界面比較は`test_material_hphi_comparison`。直接利用先は`test_rf_materials test_hphi_geometry_mapping test_meridional_overlap`。[独立積分・写像・誤対応拒否の記録](MATERIAL_HPHI_COMPARISON.md)。

H13-e大きい保存地点のHTTP転送は`test_gui_request_size`。直接HTTP契約は`test_gui_hphi.HphiGuiTests.test_real_http_assets_authentication_and_strict_actions`（実bind許可下でskipなしを確認）。[実ブラウザーの失敗・修正・分割再検査](CURVED_HPHI_GUI.md)。

H13-e曲線追跡/履歴GUIは`test_gui_curved_hphi_tracking`。直接利用先は`test_gui_hphi_tracking`、`test_gui_hphi_history_request`、`test_hphi_tracking_history_saved.HphiHistorySavedTests.test_gui_ordered_history_extension_and_each_original_side`。[接続範囲と検査](CURVED_HPHI_GUI.md)。

H13-e曲線調整GUIは`test_gui_curved_hphi_tuning`、元Project取込は`test_hphi_project_import`。直接利用先は`test_hphi_jobs test_gui_hphi_tuning`。[対象検査・ブラウザー範囲](CURVED_HPHI_GUI.md)。

H13-d調整回復の所有操作受入は`test_curved_hphi_tuning_recovery_saved`。CLI検索、worker最終細分、再起動/元出力移動、全native/RFと穴付きProjectを検査。[実行と条件別監査](CURVED_HPHI_TUNING_RECOVERY_SAVED.md)。

H13-d曲線追跡/履歴CLIは`test_curved_hphi_history_cli`。旧CLI互換は`test_hphi_mapped_tracking_saved.HphiMappedTrackingSavedTests.test_saved_cli_replay_owns_native_after_source_move`。[仕様・検証記録](CURVED_HPHI_HISTORY.md)。

H13-d曲線履歴・回復は`test_curved_hphi_tracking_history`。関連は`test_hphi_tracking_history`と`test_hphi_recovered_history.HphiRecoveredHistoryTests.test_strict_placements_and_failed_recovery_forbid_extension`。[検証記録](CURVED_HPHI_HISTORY.md)。

H13-d曲線追跡の所有pairは`test_curved_hphi_tracking_jobs`。直接利用先は`test_hphi_tracking_jobs test_hphi_jobs`。[検証記録](CURVED_HPHI_TRACKING_SAVED.md)。

H13-d曲線調整workerは`test_curved_hphi_tuning_jobs`。共通dispatchの直接利用先は`test_jobs`、旧直線`test_hphi_tuning_jobs`の不正入力/実中止・再開ケース。[検証記録](CURVED_HPHI_TUNING_WORKER.md)。

H13-d曲線調整CLIは`test_curved_hphi_tuning_cli`。旧互換の直接利用先は`test_hphi_tuning_saved.HphiTuneSavedTests.test_cli_tune_resume_and_replay_names_and_exit_codes`。[保存/CLI検証記録](CURVED_HPHI_TUNING_SAVED.md)。

H13-d所有調整の第一段階は`test_curved_hphi_tuning_saved`。関連は`test_hphi_tuning_saved`の所有再生/改変拒否と`test_curved_hphi_saved`。[検証範囲・記録](CURVED_HPHI_TUNING_SAVED.md)。

H13-cの曲線調整実行/回復は`test_curved_hphi_tuning test_curved_hphi_tuning_recovery`。[独立TEM/曲線FEM目標、未確認停止、目標/粗細差別判定と検証記録](CURVED_HPHI_TUNING.md)。関連は旧HphiTuneRequestTests、旧回復の形状/予算検査、新候補の構築前予算検査。

H13-cの探索/最終/比較候補は`test_curved_hphi_tune_trials`。関連は`test_curved_hphi_shape_tuning test_curved_hphi_refinement`。[二段元chart・質量保存・実曲線穴付き追跡](CURVED_HPHI_TUNE_TRIALS.md)。

H13-cの元曲線Project形状変数は`test_curved_hphi_shape_tuning`。関連は`test_hphi_geometry_mapping test_curved_meridional_geometry`。[全P2尺度則・二次shear・加速座標・軸丸め](CURVED_HPHI_SHAPE.md)。

H13-bの曲線追跡は`test_curved_hphi_tracking test_curved_hphi_tracking_crossing`。関連は`test_hphi_tracking test_curved_hphi_spectral_resolution`。[実曲線順位交換/解析縮退/guard/元native証拠](CURVED_HPHI_TRACKING.md)。

H13-bの曲線有限スペクトル診断は`test_curved_hphi_spectral_resolution`。関連は`test_hphi_spectral_resolution test_curved_hphi_mass_projection`。[独立密行列/尺度不変量と記録](CURVED_HPHI_SPECTRA.md)。

H13-bの曲線scalar射影は`test_curved_hphi_mass_projection`。関連は`test_hphi_mass_projection test_curved_hphi_field_overlap test_curved_hphi_refinement`。[不変量・実行記録と未実装範囲](CURVED_HPHI_PROJECTION.md)。

H13-aの同二次領域細分/丸め契約は`test_curved_hphi_refinement`。関連は`test_curved_hphi_comparison test_curved_hphi_field_overlap test_curved_meridional_geometry test_curved_hphi_fem`と、`test_curved_hphi_convergence`のstrict要求・実三水準/guardケース。[不変量・実行記録](CURVED_HPHI_REFINEMENT.md)。

H12-bは`test_curved_hphi_convergence`。固定P2/strict要求、三水準f/場/RFの別判定、解析TEM f/q/Q、guard/近縮退停止、保存native不変、P1軸位相を検査する。関連は`test_curved_hphi_saved test_curved_hphi_field_overlap test_hphi_convergence test_curved_hphi_comparison`。[新5件・関連19件と失敗を含む実行記録](CURVED_HPHI_CONVERGENCE.md)。

H12-aの元曲線E/H比較は`test_curved_hphi_field_overlap`。関連は`test_curved_hphi_saved test_hphi_field_overlap test_hphi_convergence test_curved_hphi_comparison`。新6/関連20件PASS。[独立積分・実FEM・保存不変の記録](CURVED_HPHI_FIELDS.md)。guard/三水準診断はH12-bの別検査。

H11の曲線比較領域は`test_curved_hphi_comparison`。関連は`test_curved_meridional_geometry test_hphi_geometry_mapping test_curved_hphi_fem test_curved_comparison_overlay`。新6件＋既存20件PASS。[独立積分・範囲・時間](CURVED_HPHI_COMPARISON.md)。場比較や調整workflowの証拠とは区別する。

H10-cと親H10を完了（2026-09-21）。[調整回復・条件別監査](HPHI_TUNING_IDENTITY_RECOVERY.md)。検索/最終細分の比較親と過去anchorを分離し、成功個別IDだけを評価へ使用。新7unit＋既存25unitとChrome4項目PASS、全350実装/24所有ファイル不変、全handle/サーバー終了0。次はH11の曲線Hφ比較領域。全goalは継続。

H10-cの検索/最終細分回復は`test_hphi_tuning_identity_recovery`、所有CLI/worker再生は`test_hphi_tuning_identity_recovery_saved`。直接利用先は`test_hphi_tuning test_hphi_shape_tuning test_hphi_tuning_saved test_hphi_shape_tuning_saved test_hphi_tuning_jobs test_gui_hphi_tuning`。実ブラウザーは`scripts/verify_gui_hphi_tune_recovery.mjs`。[独立対照・実行記録](HPHI_TUNING_IDENTITY_RECOVERY.md)。

H10-bは`test_hphi_mapped_tracking_saved`2件、`test_hphi_recovered_history`3件、`test_gui_hphi_history_request`1件と、既存の専用回帰23＋調整利用先2件がPASS。実Chrome4項目もPASS。[検証範囲・時間・失敗履歴](HPHI_RECOVERED_HISTORY.md)。GUI要求保持変更後はフォームと実ブラウザーを検査し、数値実装hashの不変部分の成功証拠を再利用した。

H10-aは`test_hphi_identity_recovery`の新8件（4+3+1の分割実行）と既存`test_hphi_tracking_history.HphiTrackingHistoryTests.test_native_spectrum_and_identity_continuity`1件がPASS。[検証記録](HPHI_IDENTITY_RECOVERY.md)。独立解析f/q/縮退部分空間、正しい順位交換と停止対照を分離。H10-b/cの保存・操作受入は含まない。

H09-d受入：両形状worker専用validator、再起動後Chrome各1、追加穴付き逆/同形状別分割1件（19.113秒）、実HTTP1件（0.616秒）がPASS。[分割証拠・失敗履歴・条件別監査](HPHI_SHAPE_TUNING_GUI.md)。src/FEM不変部分のH09-a/b/c成功証拠を再利用。全suite/seed未実施。

H09-d進行中：`scripts/validate_hphi_shape_tuning_jobs.py`と`scripts/verify_gui_hphi_shape_tuning.mjs`で要求版2のworker/GUIを検査する。[現在の証拠と未完了](HPHI_SHAPE_TUNING_GUI.md)。同軸の分割証拠を両形状の全受入とは扱わない。

H09-cの要求版2は`test_hphi_shape_tuning test_hphi_shape_tuning_saved`。同軸3寸法の実二分、strict頂点変位・軸座標・境界折曲げ、実CLI保存再開を検査する。専用`scripts/validate_hphi_shape_tuning.py --out out/<new-name>`は穴付き非一様変形の独立TEM場/周波数と所有保存を検査する。利用先は`test_hphi_tuning test_hphi_tuning_saved test_hphi_tuning_jobs test_gui_hphi_tuning`。

H09-bの非一様Hφ比較は`test_hphi_mapped_fields test_hphi_mapped_tracking`。独立TEM/Bessel縮退、E/H別Gram、q/u射影、正逆比較、H02一致、guard/ID集合を検査する。利用先回帰は`test_hphi_field_overlap test_hphi_mass_projection test_hphi_spectral_resolution test_hphi_tracking test_hphi_tracking_history test_hphi_tuning test_gui_hphi_tracking`、直接利用先の`test_hphi_convergence`。新写像の所有保存/CLI/GUIはH09-c/dの別受入。

H09-aの非一様直線Hφ交差分割は`test_hphi_mapped_overlap`で全親被覆・独立矩形モーメント・正逆写像・番号置換・予算拒否を検査する。幾何依存は`test_hphi_geometry_mapping test_meridional_overlap`。場/追跡接続はH09-bの別証拠。

H08の直線Hφ幾何対応は`test_hphi_geometry_mapping`で独立面積/体積・逆対応・境界/軸/穴の拒否を検査する。基盤変更時は`test_axis_connected_mesh test_hphi_mesh test_axis_hphi test_hphi_study`を追加する。場/追跡の対応はH09の別検証。

# 変更範囲に応じた検証とテスト棚卸し

Hφ調整の所有checkpoint/worker/GUI検証を変更する場合は
`test_hphi_tuning_jobs test_gui_hphi_tuning`を選ぶ。実workerの中止・再開・管理器再作成、
継承/追加checkpointの選択、元出力移動後の再生、native/RFのhash保持とコピー改変拒否を含む。
保存形式・standalone再生も変更する場合は`test_hphi_tuning_saved`を追加する。
実ブラウザーのクリック列はこれらのtransportテストとは別の証拠である。

Hφ調整の要求/試行生成は`test_hphi_tuning.HphiTuneRequestTests`、実FEM二分は`HphiTuneExecutionTests`。比較核は`test_hphi_tracking`/`test_hphi_field_overlap`、独立TEM・場/RF尺度と停止理由、H05の所有保存/再生は`scripts/validate_hphi_tuning.py --out out/<new-name>`を使う。H03/H04の実行範囲・分割証拠は[HPHI_TUNING.md](HPHI_TUNING.md)。worker/GUIは上記の専用テストを使う。

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

2026-09-15 JST：[TE逐次/適応Studyの実GUI](TE_TRACKED_STUDY.md)を限定検証。
Chrome逐次8/適応11項目、完了再生は新ブラウザー各1項目で補強。GUI関連6unitもPASS。
専用7実FEM、7組nativeの42配列/全RF一致、144ファイル保持。全6ジョブ・全handle終端。
他TE形状/対称セクター/回復例、TE版8・曲線対称/鏡映・他物理/D03は残る。親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[TE逐次・適応Studyのnative読取](TE_TRACKED_STUDY.md)を接続。
新2件を含む24unitが76.496秒でPASS。逐次CLIは停止/再開後COMPLETE、既存独立掃引との2組全配列/RF一致。
適応CLIは初回BISECTから再開し、10点/17試行で元終点まで到達。専用計12実FEM。
実GUI・その他のTE形状/セクター/回復例、TE版8・曲線対称/鏡映・他物理/D03は残る。
親33=10/16/6/1、全goal ACTIVE。詳細と保存再生の検証範囲はリンク先を参照。

2026-09-15 JST：[TEアフィンStudy](TE_AFFINE_STUDY.md)を直接閉PEC・固定RFで限定受入。
新規を含む23unit、GUI実経路12項目、説明修正後の定義/画面3項目がPASS。専用4実FEM。
2組nativeの12配列/全RF一致、57ファイル保持、Maxwell場/RF尺度差最大8.990e-15。
完了StudyのEφ追跡は接続済み。逐次/適応の実計算は未接続、版8・曲線対称/鏡映・他物理/D03も残る。
親33=10/16/6/1、全計画goal ACTIVE。以下の未完表記は各段階の履歴。

2026-09-15 JST：[TEアフィン調整版4](TE_AFFINE_TUNING.md)のGUI/CLI・場/RF追加検証を限定受入。
アフィン係数の重複JSONキーを元テキストのままサーバーへ渡し、FEM前に拒否する修正も実施。
Chrome TE12/TM10項目、GUI関連5件PASS。専用比較21実FEM＋解像度/目標pilot3実FEM。
7組native全配列/RF一致、元108ファイル保持。TE affine Study・版8・曲線対称/鏡映・他物理/D03等は残り、全goal ACTIVE。


2026-09-15 JST：[TEアフィン曲線調整版4](TE_AFFINE_TUNING.md)を固定RF契約でAPI接続。
Eφのアフィン/同一曲線領域比較、native保存再開、Maxwell周波数則とせん断体積比を検証。
新2件は分割で成功、関連35件134.814秒PASS。実GUI・追加場/RF尺度・TE affine Studyは後続。
版8・曲線対称/鏡映・実ID回復例・他物理/D03を保持し、全計画goal ACTIVE。


2026-09-15 JST：[曲線TE調整版5/7](TE_CURVED_TUNING.md)の実GUI・場/RF追加検証がPASS。
直接閉PEC・固定RFメタデータ・凍結履歴の範囲を限定受入。Chrome多項式14/exp式11項目、専用21実FEM。
原寸/倍寸/4倍エネルギー、全係数・全要素の場・RF/PEC積分尺度を分離検査。8組native全配列/RF一致、元108ファイル保持。
版4/8・曲線対称/鏡映・実ID回復例・他物理/D03は残る。親33=10/16/6/1、全goal ACTIVE。


2026-09-15 JST：[曲線TE調整の固定RF契約](TE_CURVED_TUNING.md)を多項式版5・式版7へ接続。
TEでは加速区間を追加せず、形状変形・凍結履歴・Eφ比較・最終細分・保存再開を保持。
新3件の分割検証と関連34件482.550秒がPASS。独立Green積分、専用TE Study2実FEMも確認。
実GUIと追加場/RF尺度検証は未実施。版4/8・曲線対称/鏡映等を保持し、全goal ACTIVE。


2026-09-15 JST：[曲線TEの宣言比較写像](TE_CURVED_TRACKING.md)をpiecewise_remesh版2/3/4/5へ接続。
実Eφと可変体積重みを保持し、非アフィン変形・独立積分・Maxwell尺度・native再生を検証。
型検査順と共通参照分割のTE入口を修正、最後の関連22件がPASS。旧TM保存互換も照合。
閉PECの直接曲線P2が対象。曲線TE tune、曲線対称/鏡映、他物理/D03は残り、全goal ACTIVE。


2026-09-15 JST：[TE一般profile調整](TE_PROFILE_TUNING.md)をnormalized_profileへ接続。
非円筒の連動寸法・局所半径式、閉PEC/半領域/鏡映、保存再開と最終粗細判定を検証。
新2件51.729秒＋関連48件94.247秒PASS。専用尺度8FEM、Chrome11項目/4FEMがPASS。
5組native全配列/RF一致、元81ファイル保持。曲線TE・他物理調整とD03は残り、全goal ACTIVE。


2026-09-15 JST：[TE一般profile追跡](TE_PROFILE_TRACKING.md)の体積重み付きEφ写像を追加。
閉PEC・同端条件の一対称面・鏡映に対応。解析積分、P1/P2左右両対称条件、保存再生、実FEM尺度則を検証。
関連40件は39成功＋失敗入力修正後1成功の分割証拠。専用4実FEMもPASS。
一般profileのtune接続と曲線TEは残る。D02と全計画goalは継続中。


2026-09-15 JST：[TE円筒チューニング](TE_TUNING.md)を同端条件の直線円筒へ接続し、限定受入。
EφによるID、半領域・鏡映の元セクター順位、加速量N/A、保存再開・回復・最終粗細ゲートを保持。
関連53unit（52＋1の分割実行）、専用44実FEM、Chrome閉PEC9/鏡映11/旧TM9項目がPASS。
8組native全配列/RF一致、元114ファイル保持。一般TE形状・他物理調整とD03は残る。
親33=10受入/16進行/6他未受入/1範囲外、D02と全計画goalは継続中。


2026-09-15 JST：[曲線分割切替tune版8](PARTITION_TUNING.md)を実装・宣言分割方式で受入。
初期接続/PEC境界分割/履歴の異なる候補を実値から選び、式変形・実FEM・比較版5・保存再開/ID回復へ接続。
関連36unit、専用39実FEM、Chrome新10/旧9項目がPASS。8組のnative全配列/RF一致、元124ファイル保持。
親D02の他物理調整とD03一般制約付き探索は残り、親33=10/16/6/1、全計画goal ACTIVE。


2026-09-15 JST：D02の[曲線分割候補](CURVED_PARTITION_SCHEDULE.md)の検証基盤を追加。
区間ごとの初期接続/境界分割/明示履歴と共通参照座標を検証する。tune/保存/GUIへの接続は次の課題。
矩形の解析面積/体積、曲線PEC分割でのP2領域差、従来の同一境界拒否を検査した。
親33=10/16/6/1、全計画goal ACTIVE。


2026-09-15 JST：[単位付き式によるtune版7](EXPRESSION_TUNING.md)の追加実経路検証がPASS。
Chrome profile9/曲線9/旧版7項目、曲線Maxwell RF/場尺度則、指数軸長の実ID回復・再開/拒否を確認。
追加58実FEM、全9GUIジョブ終端、取り込み3場の全配列/RF一致、元29ファイル保持。
親D02の境界分割変更・他物理は残り、親33=10/16/6/1、全計画goal ACTIVE。


関連8モジュール50件232.352秒PASS、回復要求の追加1件0.355秒PASS（計51件、分割実行）。
CLI/worker各1実FEM、保存12配列・全RF一致、元16ファイル保持。node --check終了0。
全検証handle終端、live processなし。実ブラウザー/曲線専用RF/版7実回復は未検証。

2026-09-15 JST：D02の[単位付き式によるtune版7](EXPRESSION_TUNING.md)をprofile/曲線の実形状生成へ接続。
実FEM円筒調整・保存再開・途中定義域エラー保持、非アフィン曲線の独立面積/体積則を検証。
GUIコードも追加したが、実ブラウザーと曲線の専用RF/場検証は残る。親33=10/16/6/1、全計画goal ACTIVE。


2026-09-15 JST：D02の[非多項式スカラー式](SCALAR_EXPRESSIONS.md)の評価基盤を追加。
単位検査、数学関数、遅延条件分岐、有限実数の定義域、構文/深さ/ノード予算を検査し、新8件0.124秒PASS。
まだtune/Project/CLI/GUIには未接続。[D02監査](D02_CURRENT_AUDIT.md)の関数連動・境界分割変更等は保持する。


2026-09-15 JST：[D01の元要件と明示後続要件](D01_ACCEPTANCE.md)を監査し、親D01.S/I/Vを受入済みに更新した。
個別ID回復の全利用先接続と、異なる初期比較接続・境界分割への対応を含む21実行報告、検査内容、現在のソースを照合。
親33=10受入/16進行/6他未受入/1範囲外。D02/D03と全計画goalは継続中。以下の旧段階の未完表記は履歴である。


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

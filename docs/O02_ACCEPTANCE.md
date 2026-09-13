# O02: Project・Study・GUIの原要件と受入証拠

2026-09-13。[照合計画](O02_ACCEPTANCE_PLAN.md)に基づく、独立実装の受入済み専用範囲の原要件照合を完了。静的Studyのworker/CLIとGUIも標準・独立比較・主ツリー検証を通過した。対象版C00.Vは未確認であり、親O02の互換受入と全計画は未完。

## 元要件と照合の範囲

[互換計画のO02](COMPATIBILITY_PLAN.md)は、C01と組込対象の受入済み物理を前提に、外部メッシュ・高次要素・追加物理をProject/Study/GUIへ渡す操作と保存を接続する。後続の物理は完成に合わせて追加し、GUIへ別のソルバーを作らない。受入はCLI/Python/GUIの入力・結果一致、再起動、失敗/中止/描画、対応外量のN/Aで確認する。

次表は受入済み専用範囲の接続と証拠の対応表である。各文書の古い「未対応」「実行中」という経過は、同じ文書の最終受入節と後続の仕様を区別して読む。過去に合格した操作の範囲を、新しい物理モデル・一般の追跡・離散化誤差保証へ広げない。

| 対象 | 接続・保存の仕様と既存証拠 | 保持する区別 |
|---|---|---|
| 外部メッシュ | [Project版2](PROJECT_MESH.md)、[GUI読込/解除・固定Study](EXTERNAL_MESH_WORKFLOW.md) | 元SIメッシュの番号/タグとCaseを保持。直線固定多角形と二次曲線の固定形状を区別 |
| 曲線形状・高次要素 | [Project変形](CURVED_PROJECT_TRANSFORM.md)、[曲線調整](CURVED_TUNING.md)、[途中保存の選択](GUI_TUNING_CHECKPOINTS.md)、[履歴編集](GUI_CURVED_REFINEMENT_HISTORY.md)、[図上選択](GUI_CURVED_MESH_SELECTION.md)、[固定形状Study](CURVED_HISTORY_STUDY.md)、[適応版4 GUI](GUI_CURVED_ADAPTIVE_REFINEMENT.md)、[RF適応版5 GUI](GUI_RF_ADAPTIVE.md)、[観測時間](GUI_RF_ADAPTIVE_COST.md)、[明示表面方針](CURVED_RF_SURFACE_POLICY.md) | 元二次写像・順序付き細分履歴を保持。実行/停止判定と一般精度/効率保証、採用された親と合格した確認、観測時間と不明を区別 |
| RF制約付き探索 | [探索GUI](GUI_RF_OPTIMIZATION.md)、[worker/保存再開](RF_OPTIMIZATION_JOBS.md) | 元要求・制約・追跡IDと試行/最終細分を保持。予算停止・実行完了・数値条件の達成を分離し、保存を再検証してから再開 |
| TE単独・掃引・収束 | [GUI](GUI_TE.md)、[独立Study](TE_STUDY_PLAN.md)、[収束Study](TE_CONVERGENCE_STUDY_PLAN.md) | Eφ/Hr/Hz、規格化、加速量N/A、電場/磁場/RFの別判定。独立掃引を追跡と呼ばない |
| TE鏡映・限定追跡 | [鏡映](TE_REFLECTION_PLAN.md)、[元半領域の収束比較](TE_REFLECTED_CONVERGENCE_PLAN.md)、[同端条件円筒の追跡](TE_SECTOR_TRACKING_PLAN.md) | 元対称条件と部分スペクトル番号、縮退群のID集合、FAIL/UNVERIFIEDを保持 |
| 平面RF | [GUI](GUI_PLANAR.md)、[Study](PLANAR_STUDY.md)、[細分差](PLANAR_CONVERGENCE.md)、[追跡履歴](PLANAR_TRACKING_HISTORY.md)、[厳密アフィン追跡](PLANAR_EXACT_AFFINE_TRACKING.md) | xy成分・単位長RF・両R/QのN/A。宣言写像と保存場の連続性を、一般形状の物理追跡へ読み替えない |
| 真空Hφ | [Project/worker](HPHI_JOBS.md)、[GUI](GUI_HPHI.md)、[Study](HPHI_STUDY.md)、[軸接続](AXIS_HPHI_WORKSPACE.md)、[曲線](CURVED_HPHI_WORKSPACE.md) | 正半径・軸接続・曲線の専用Case/native、元場・加速区間・beta・位相原点・N/Aを保持 |
| Hφ診断・追跡 | [細分差GUI](HPHI_CONVERGENCE_WORKSPACE.md)、[対応GUI](GUI_HPHI_TRACKING.md)、[所有履歴](HPHI_TRACKING_HISTORY.md) | E/H対応、個別ID/ID集合、数値状態と延長可否を分離。元ディレクトリ移動後も所有場から再生 |
| 材料Hφ | [Project・表示・独立Study](MATERIAL_HPHI_WORKSPACE.md) | 元材料/場/規格化と加速区間。未受入の材料比較/追跡・損失/分散を追加しない |
| 静的11形式のProject | [入力](STATIC_FIELD_PROJECT.md)、[worker/CLI](STATIC_FIELD_JOBS.md)、[GUI](STATIC_FIELD_GUI.md) | 全SI Case/材料/境界・B-H初期値/反復条件、成功と実非線形失敗、平面単位長量と軸対称全周量を保持 |
| 静的Study | [入力](STATIC_FIELD_STUDY_INPUT.md)・[worker/CLI](STATIC_FIELD_STUDY_JOBS.md)・[GUI](STATIC_FIELD_STUDY_GUI.md)を主受入済み | 全条件の入力順、幾何/励起尺度、元の初期値。実行完了と成功/実失敗数、枝追跡未実施を区別 |
| 磁気後処理 | [検証済み報告のGUI受渡し](S05_GUI_HANDOFF.md)、[S05原要件照合](S05_ACCEPTANCE.md) | 元nativeへ拘束した多極/力/二つのトルクと全周軸力。仮想仕事の未実施/完了/実求解失敗を保持 |

## 今回確認した証拠

`out/o02-acceptance-audit-in-progress-20260913/accepted-stages.json`に、上記の受入済み実装工程33件の`validation.json`と`seed_regression.json`の対応を記録した。全66ファイルを読み、両報告の合格、source SHAが双方にある場合の一致、主専用検証の判定フィールドがある場合のPASSを確認した。監査前後の66ファイルのSHAは不変である。この33件は実装工程の数であり、計画の親33項目の受入件数ではない。

これは既存報告の読取照合で、標準テストを今回再実行したという記録ではない。各工程の固定ソースを現在の主ツリー全体と同一とは扱わず、後続変更とその検証を別に見る。初期の報告に主専用検証フィールドがないことも、そのまま記録した。

同じ監査ディレクトリの`browser-records.json`には28工程に対応する最終ブラウザー報告46件、計586チェックを保存した。全チェックの合格、外部HTTP要求0、実行中source不変と、各報告の配信sourceが対応する受入時の標準sourceに一致することを確認した。46報告ファイルも不変で、照合不一致は0件。保存・復元・取消などの個々のチェック名を元報告のまま保持する。実サーバー再起動、管理器の再生成、同じサーバーでのファイル再読込を同一視せず、各経路の保存/復元報告へ下記のとおり対応付けた。

`persistence-records.json`には保存・復元・CLI/Python/GUI間の比較報告23件を照合した結果を記録した。全件が合格し、source SHAがある報告は対応する受入時の標準と一致、23ファイルも不変である。外部メッシュでは管理器の再生成と元メッシュ/全結果の一致、TEでは保存結果の新管理器による再検証と元Case/場/数値比較、平面/Hφでは実ブラウザーの復元と元native/画像/CSVを対応付けた。後期Hφの元ディレクトリ移動後の所有保存、静的Project/磁気報告の非同期再検証も含む。sourceフィールドのない初期報告はその欠落を記録し、存在しない開始時snapshotを補ったことにはしない。曲線履歴編集・固定Study・適応の再読込/再開はブラウザー報告内の操作証拠であり、それだけを実サーバー再起動と呼ばない。

`additional-rf-gui-records.json`でRF適応版5・観測時間・明示表面方針・調整の途中保存選択・RF制約付き探索の5仕様を追加照合した。重複を除いて4標準/seedと4ブラウザー60チェックが合格し、配信sourceは各標準と一致、関係15ファイルが不変。探索では保存結果の新管理器による再検証、GUIとAPI全文書・既存CLI/workerの6 nativeのProject/全モード一致も確認した。観測時間の古い単独報告2ディレクトリは現在存在しないため、後続の表面方針19チェックと標準689件の該当7unitへ対応付けた。欠けた報告を存在したものとして再作成せず、後続検証が同じ要件を覆うことを明記する。表面方針の標準終了後に変更されたのは独立比較driverの初期同一性検査だけであり、その記録も保存した。元FEM/GUI/unitが別sourceだったことにはしない。

静的Studyは、worker/CLIの標準1423件（1420合格/3skip）とGUIの標準1429件（1426合格/3skip）、主ツリーの専用各6unitが合格した。workerは独立API/実worker/CLI各78 Studyと再起動78、GUIは元nativeを直接参照した独立78 Studyと初回/再生成accessの各192点表示・各1266取得が一致した。全192条件の成功171/実失敗21を保持する。実Chromeは全Study・既存静的42件・磁気報告20件の初回/実サーバー再起動6報告で342チェックと元3280取得が合格し、同じ保存IDの復元、両サーバーの正常停止、9画像の目視も確認した。

最終監査は `out/o02-acceptance-audit-final-20260913/report.json`。主901sourceは受入済みGUI候補895sourceと不変egg-info 6件へ完全一致する。元seed9モード19量は周波数差0、RF等の最大相対差8.882e-16。監査自体では過去の標準/ブラウザーを再実行せず、数値結果・元報告・許容差を変更していない。

## 元要件ごとの最終判定

主ツリーの入力・求解経路は、[GUI入口](../src/superfish_ng/gui.py)のstrict操作振分けから、[共通JobManager](../src/superfish_ng/jobs.py)、[平面worker](../src/superfish_ng/planar_jobs.py)、[Hφ worker](../src/superfish_ng/hphi_jobs.py)、[静的worker](../src/superfish_ng/static_field_jobs.py)へ接続することを読取確認した。共通RFは元Caseと明示meshを`solve`へ、平面は`solve_planar`へ渡す。Hφは[hphi_native](../src/superfish_ng/hphi_native.py)で専用Caseごとの既存solver/nativeへ、静的は検査済みStaticFieldProjectのCase型に対応する既存solver/nativeへ渡す。表示長さの選択だけで元SI入力を変えない契約は各Projectと独立比較の証拠へ対応する。静的Studyも[専用GUI](../src/superfish_ng/gui_static_field_studies.py)から同じJobManagerの実workerへ渡し、[各条件の実行と再検証](../src/superfish_ng/static_field_study_jobs.py)が元専用FEMを呼ぶ。全Studyの元FEM再検証後に選択点を描画し、取得ごとに全点の保存ハッシュを再確認する。

| 元要件 | 対応する実装・証拠 | 専用範囲の判定 |
|---|---|---|
| Project/Study/GUIの入力保持 | 上表の受入工程、保存比較23報告、静的Studyの全Case/材料/初期値/順序の独立比較 | PASS。元SIと表示単位、独立Studyと追跡を分離 |
| 既存ソルバーの利用 | 上記主ツリーの振分け、各工程の標準・独立比較 | PASS。GUI専用の別FEMは作らない |
| CLI/Python/GUIの同一入力・結果 | 保存比較23報告、RF探索の元6 native比較、静的workerの78 Study/156 CLIとGUIの元参照比較 | PASS。場・全量・履歴・nativeバイトを照合 |
| 保存・再起動 | 過去の管理器再生成/再読込/実再起動を区別した報告、静的3経路の全保存IDを別サーバーPIDで復元 | PASS。新しい求解を同一Job復元の代わりにしない |
| 失敗・中止・不正入力 | 元ブラウザーチェック、静的の実非線形失敗21条件、中止/強制終了/別点改変拒否と正常復帰 | PASS。実行完了と全点成功、元場の不在を保持 |
| 元場表示・対応外量N/A | 各物理の元場/単位比較、全6静的ブラウザー報告と目視9画像 | PASS。単位長/全周、未実施/零/実失敗を分離 |

今回の照合範囲内で、追加の未接続要件は見つからなかった。物理側の未対応モデル・未受入の比較/追跡をGUIの合格へ広げず、後続の物理受入に応じた接続は引き続き必要。対象版・必須機能/出力集合はC00.V、利用者の実業務・他OS/配布再受入はV02へ残す。

対象版への適用は未確認であり、親集計33項目中8受入・17進行中・7他未受入・1範囲外を変更しない。新しい数値式・外部資料・旧版コード/実行・依存の再利用はない。

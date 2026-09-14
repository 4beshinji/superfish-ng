# 変更範囲に応じた検証とテスト棚卸し

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

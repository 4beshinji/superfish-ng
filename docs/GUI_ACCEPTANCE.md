# 汎用GUI・共通入出力の受入記録

2026-09-14：[逐次Studyの個別ID回復と再開](TRACKED_STUDY_IDENTITY_RECOVERY.md)を要求版2・CLI/JobManager/GUIへ接続。
回復指定を完了Studyと共有し、回復前後の停止・再開、未確認時の次点未計算、元JSON重複拒否と回復状態表示を追加した。
新7/関連44unit、独立20FEM・再作成worker8FEM、既存18保存解再検証、Chrome新16/旧11/適応10項目が合格。
適応Study・tuneへの回復接続と親D01は継続中。親33=9/17/6/1、goal ACTIVE。以下は各段階の記録。

2026-09-14：[完了Studyの個別ID回復](STUDY_IDENTITY_RECOVERY.md)を要求版2・API/CLI/GUIへ追加。
指定点で過去の個別場と継承集合を照合し、成功後は後続点へIDを渡す。失敗後の点は未追跡として保存する。
関連54unitの分割証拠、18保存解の解析/尺度則、新GUI8項目と単独履歴17項目が合格。逐次/適応Study・tune接続と親D01は継続中。
以下の「Study未接続」は完了Studyの回復を追加する前の記録。

2026-09-14：[個別ID回復](MODE_IDENTITY_RECOVERY.md)の単独履歴GUIはChrome17項目PASS。
過去の確認済み時点の選択、個別ID表示、元比較の保持、回復根拠のダウンロード/再生、改変拒否、回復後の継続とUNVERIFIED停止を確認。
既存D01監査の3native解を取り込み、新FEM0、外部HTTP0、325製品SHA不変。画像目視・全3ジョブ完了・専用GUI停止済み。
初回13項目後の失敗は同名ダウンロードで元履歴が上書きされた検証器による。元バイト列の別保管後、新作業領域で全17項目を確認した。
旧履歴版1で回復ボタンが不要に有効となる表示を追加再現。ID配列で判定する修正後、旧履歴2項目と上記17項目を確認した。
最終記録out/mode-identity-recovery-20260914/browser-finalとbrowser-legacy-fixed。Study/tuneの自動回復や全GUIの一括受入ではない。

2026-09-14：[多変数曲線寸法のRF探索版3](RF_OPTIMIZATION_GEOMETRY.md)はChrome新版24/旧版13項目がPASS。
入力の単位/法則/厳密JSON、実worker中止と所有保存からの再開、改変拒否、別3水準、固定履歴の表面評価再生、各試行の元場表示を確認。
追加11項目は3変数の往復と混合項、準備/ひな形の待機中の編集保護、旧版2への切替。追加FEMなし。
新版browser入力は精度増加前の固定1段、現在の入力例は固定3段。前者の初期UNVERIFIED/最終CRITERIA_METを画面でも区別した。
全3回で外部HTTP0、324製品SHA一致/不変。入力/結果画像を目視し、全job終端後に専用GUIを停止した。
証拠はout/rf-optimization-geometry-20260914/browser-new、browser-old、browser-input。全GUIの一括再受入ではない。

2026-09-14：[非アフィン曲線tune版5](CURVED_HARMONIC_TUNING.md)のChrome新版12/旧版7項目を確認。
新版の法則ひな形・元入力数値/固定履歴保持・重複拒否・編集中の古い応答拒否、実4試行の保存再開・対象場表示がPASS。
旧版も17試行・保存再開と場表示がPASS。外部HTTP0、323製品SHA不変、画面目視済み。
初回新版は3項目後に検証器の待機不足で失敗し、期待法則の一致を待つ修正後に全経路を再実行した。
CLI/GUI保存配列完全一致・RF数値一致も確認し、JSON数値表記に由来する両Case hashは各原入力で個別照合した。
生出力/失敗/終端はout/curved-harmonic-tuning-20260914/acceptance.json。旧tuner全互換や他物理の受入ではない。

## 元メッシュと履歴を保持する単独形状変形 — 2026-09-14

[GUI_CURVED_DEFORMATION.md](GUI_CURVED_DEFORMATION.md)の元形状準備/ファイル入力、厳密JSON、native境界/CLI一致、別保存、適用/Undo/後続編集保護、通常保存再読込、実worker、非同期変更拒否をChrome21項目で確認。
既存の分割固定/履歴Undoと実FEMも9項目PASS。後続のプレビュー失敗表示と図中文字の補修後、RF両方針/実反転等を追加6項目で確認した。
新/既存browser各1 FEMとCLI1 FEM、初回参照パス誤指定のbrowser1 FEMは別に保持。独立な元場/幾何/RF再検証は追加FEMなしでPASS。
外部HTTP0、最終画像を目視。実行中316製品は各回不変、後続追加browserは現行製品とSHA一致。全GUIの一括再受入とはしない。

## 曲線寸法の法則による形状Study — 2026-09-14

[CURVED_HARMONIC_STUDY.md](CURVED_HARMONIC_STUDY.md)の現在値ひな形・定数/重複パス拒否・全設定往復・実Study worker・CLI数値一致・完了Studyの導出追跡/保存再生・逐次/適応要求準備・非同期品質変更拒否・旧版1切替/幅をChrome14項目で確認。
共有操作の既存アフィンStudyも11項目/実worker・保存再生がPASS。新旧それぞれ2 FEM、外部HTTP0、最終新GUI画像目視済み。
両browserの製品315ファイルは実行中/最終一致。単独Project変形のプレビュー/適用/Undoや全GUIの一括再受入はこの範囲に含めない。

## 曲線アフィンStudy — 2026-09-14

[CURVED_AFFINE_STUDY.md](CURVED_AFFINE_STUDY.md)の元番号/固定分割を含む定義往復、無効な法則の拒否、実Study worker/保存場、独立スペクトル表示、完了Studyの追跡/保存再生、逐次要求準備、非同期入力変更拒否と旧版1切替をChrome10項目で確認。
係数欄の幅をCSSで補修し、定義往復/幅の3項目と最終画像を別検証した。外部HTTP0、表示確認には新規FEMを使わない。
初回は要求生成を待たずに空欄を読む検証器の失敗で、7項目後に停止。待機を修正した最終結果と区別する。
実逐次/適応workerの再開は別の専用5 FEMで検証した。全GUIの再受入やHosted CIとはしない。

## 曲線局所分割の固定 — 2026-09-14

[FROZEN_CURVED_REFINEMENT.md](FROZEN_CURVED_REFINEMENT.md)のCLI一致/固定状態・保護/保存再読込/解除・後続再指定/図上再選択/Undo/実worker保存/非同期変更拒否をChrome9項目で確認。
既存途中挿入20項目も再実行し、実FEMと6,656要素Canvasを含めPASS。
証拠はout/frozen-curved-refinement-20260914のbrowser/とhistory-regression/。外部HTTP0、各実行中の製品ファイル不変。
固定履歴の画像を目視した。固定を物理精度保証とする表示は追加していない。

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

再現はverify_gui_tuning.mjsへ既存の--url/--out/--requestに加え
`--coupled examples/tuning/pillbox_radius_factor.json`を渡す。--requestは
examples/tuning/pillbox_length.json。数値検証は
`python scripts/validate_coupled_tuning.py --out out/coupled-validation-NEW`。

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

再現（未使用の出力名を指定）:

```bash
python -m superfish_ng gui --workspace out/gui-tuning-NEW --no-browser
node scripts/verify_gui_tuning.mjs --url '起動URL' --out out/browser-tuning-NEW --request examples/tuning/pillbox_length.json
```

既存35項目はverify_gui_mode_tracking.mjsの--sources/--repartition/--same-domain/
--affine/--piecewise/--curved/--reprojectedを本書の各D01受入記録どおりに指定し、空workspaceで実行。
既存11項目はverify_gui_tracked_execution.mjsと
out/d01-tracked-gui-accepted-sources-20260908/request.jsonを使用した。
独立検査は`python scripts/validate_tuning.py --background --out out/tuning-numerical-NEW`。

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

再現手順（出力先はそれぞれ未使用の名前を指定）:

```bash
OPENBLAS_NUM_THREADS=1 python scripts/validate_adaptive_study_jobs.py --out out/adaptive-gui-source-NEW
python -m superfish_ng gui --workspace out/adaptive-gui-workspace-NEW --no-browser
node scripts/verify_gui_adaptive_execution.mjs --url '起動URL' --out out/adaptive-gui-browser-NEW --request out/adaptive-gui-source-NEW/profile-request.json
```

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

再現手順（出力先は未使用の名前を指定）:

```bash
OPENBLAS_NUM_THREADS=1 python scripts/validate_tracked_study_jobs.py --out out/tracked-gui-source-NEW
python -m superfish_ng gui --workspace out/tracked-gui-workspace-NEW --no-browser
node scripts/verify_gui_tracked_execution.mjs --url '起動URL' --out out/tracked-gui-browser-NEW --request out/tracked-gui-source-NEW/request.json
```

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

再現手順（それぞれ未使用の出力先を指定）:

```bash
OPENBLAS_NUM_THREADS=1 python scripts/validate_study_tracking.py --out out/gui-study-NEW
python -m superfish_ng gui --workspace out/gui-study-NEW --no-browser
node scripts/verify_gui_study_tracking.mjs --url '起動URL' --out out/gui-study-browser-NEW
```

## D01対応比較・追跡履歴 — 2026-09-08

out/browser-d01-mode-tracking-final-20260908/report.jsonでChrome8操作PASS、外部要求0、ソース変更なし。
円筒縮退例の取込、合流/分裂の部分空間表示、ID編集禁止、文書ダウンロード一致、
再読込、改変拒否、未確認履歴の保存可能/継続禁止を確認。tracking-history.pngを視認した。
初回は数値の再JSON化で厳密再検証に失敗し、サーバー文書文字列の保持へ修正して全操作を再実行。
初回FAILはout/browser-d01-mode-tracking-20260908に保持する。検証用GUIは停止済み。

```bash
OPENBLAS_NUM_THREADS=1 python scripts/validate_cluster_transitions.py --out out/gui-tracking-source-NEW
python -m superfish_ng gui --workspace out/gui-tracking-workspace-NEW --no-browser
node scripts/verify_gui_mode_tracking.mjs --url '起動URL' --out out/gui-tracking-browser-NEW --sources out/gui-tracking-source-NEW
```

接続テスト5件と標準460件中458合格・2 skip、標準数値回帰PASS。
profile/paired_meshもGUIから共通APIへ接続するが、今回Chromeの数値操作例は円筒写像のみ。
一般追跡・Study/tune全体の受入とは区別する。[詳細](MODE_TRACKING.md)。


## 最小子午面曲率半径の保持 — 2026-09-08

out/gui-meridional-radius-browser-20260908/report.jsonでChrome11操作PASS。
外部要求0、実行中ソース変更なし。構築保存・再読込・適用・実FEM計算の幾何に
minimum_meridional_radius_m=0.019を保持した。tangent-construction.pngの表示を確認し、GUIを停止した。
専用の半径編集欄は追加していない。曲線JSONの読込/保持として検証した。

```bash
node scripts/verify_gui.mjs --url '起動URL' --out out/gui-meridional-radius-NEW --tangent-request examples/construction/radius_constrained_fillet_request.json --tangent-degenerate-request examples/construction/degenerate_fillet_request.json
```

曲率制約の合格を物理ピーク収束へ読み替えない。


## 構築診断の表示・保存・再検証 — 2026-09-08

out/gui-construction-diagnosis-browser-20260908/report.jsonでChrome11操作PASS、外部要求0、
実行中ソース変更なし。版6フィレットの既存8操作に診断表示・ダウンロード/再読込、
診断改変拒否、証明した弧端接触でも未確認構築の適用不可を維持する3操作を追加した。
tangent-degenerate.pngの状態・ボタン表示を視認し、元プロジェクトの不変も確認。
検証用GUIは停止済み。保存診断のPython再読込と版1〜6の構築再読込も確認した。

```bash
node scripts/verify_gui.mjs --url '起動URL' --out out/gui-construction-diagnosis-NEW --tangent-request examples/construction/line_conic_fillet_request.json --tangent-degenerate-request examples/construction/degenerate_fillet_request.json
```

診断の証明、構築の閉輪郭検査、FEM精度の受入を分離する。一般の重解分類は追加していない。


## 版6直線・有限弧フィレット — 2026-09-08

out/gui-line-conic-fillet-browser-20260908/report.jsonでChrome8操作PASS。
半径/回転方向/円弧長/接点上界、明示選択、保存・再構築・適用・二次曲線FEM・描画、
改変拒否を確認。外部要求0、実行中ソース変更なし。tangent-construction.pngの表示も確認。
検証用GUIは停止済み。版1〜6の実保存ファイル再読込をPythonでも確認した。

```bash
node scripts/verify_gui.mjs --url '起動URL' --out out/gui-line-conic-fillet-NEW --tangent-request examples/construction/line_conic_fillet_request.json
```

合成例の周波数1258432805.464176 Hzは実CLIと一致。
UIのPASSは、この形状のRF/物理ピーク収束の証拠ではない。


## 版5有限弧フィレット — 2026-09-08

out/gui-conic-fillet-browser-20260908/report.jsonでChrome8操作PASS。
半径/回転方向/円弧長/元弧とフィレット双方の接点誤差上界、明示選択、保存/再構築/適用、
曲線FEM/描画、改変拒否を確認。外部要求0、実行中ソース変更なし。
tangent-construction.pngも表示確認し、検証用GUIサーバーは停止した。
版1〜5の実保存ファイル再読込はPythonでも別途確認した。

```bash
node scripts/verify_gui.mjs --url '起動URL' --out out/gui-conic-fillet-NEW --tangent-request examples/construction/two_lobe_fillet_request.json
```

合成2山形状の周波数1310579815.6725943 Hzは実CLIと一致。
UIのPASSを、この形状のRF/物理ピーク収束の証拠にはしない。


## 版4指定半径・線分フィレット — 2026-09-08

out/gui-line-fillet-browser-20260908/report.jsonのChrome8操作PASS。
指定半径/円弧長/数値検査の表示、明示選択、保存/再構築/Case適用、二次曲線FEM/描画、
改変拒否を確認。外部要求0、実行中ソース変更なし。tangent-construction.pngも確認した。
検証用GUIは停止済み。版1〜4の実保存ファイル再読込はPythonで別途確認済み。

```bash
node scripts/verify_gui.mjs --url '起動URL' --out out/gui-line-fillet-NEW --tangent-request examples/construction/corner_fillet_request.json
```

この合成フィレット形状のRF/物理ピークの収束検証ではない。
版4の接点/有限範囲/G1数値検査を、版2/3の区間認証として表示しない。


## 版3固定直線・弧接続 — 2026-09-08

out/gui-line-arc-browser-20260908/report.jsonのChrome8操作PASS。
保持線分端と接点、位置誤差上界の表示、明示選択/保存/再構築/Case適用/FEM/描画、
改変拒否を確認。外部要求0、ソース変更なし、tangent-construction.pngも表示確認した。
検証用GUIサーバーは停止済み。旧版1/2の保存ファイル再読込もPythonで確認した。

```bash
node scripts/verify_gui.mjs --url '起動URL' --out out/gui-line-arc-NEW --tangent-request examples/construction/capsule_line_arc_request.json
```

同じ合成カプセルの版2/3構築間には両RQ差0.626214%がある。UIのPASSと
RF収束の未検証を分け、詳細を[接線構築](TANGENT_CONSTRUCTION.md)に記録した。


## 版2区間付き接線構築 — 2026-09-08

out/gui-certified-construction-browser-20260908/report.jsonで8操作PASS。
外部要求0、実行中ソース変更なし。tangent-construction.pngの誤差上界表示も確認した。
版2の証拠・接点誤差上界に加え、明示選択、保存/再読込、Case適用、FEM/場表示、
改変拒否を実Chromeで検査。起動には通常のGUI、検証には次を使う。

```bash
node scripts/verify_gui.mjs --url '起動URL' --out out/gui-certified-NEW --tangent-request examples/construction/capsule_certified_request.json
```

UI検査をRF収束や物理ピーク精度へ読み替えない。版1との合成例のRF差は接線構築記録に保持する。


## G03接線構築GUI追加 — 2026-09-08

out/gui-tangent-browser-final-20260908/report.jsonで7操作PASS、外部要求0、実行中ソース変更なし。
既存の寸法入力/通常FEM・場表示/不正値保持に加え、接線候補表示と現在Case不変、
明示候補選択/閉輪郭検査/保存/要求編集時の解除、保存再読込/明示適用/FEM/場表示、
保存Case改変の拒否を実Chromeで確認した。tangent-construction.pngも表示確認済み。
GUI合成カプセルの基本周波数1170098360.3437803 Hz。精度収束/旧版照合ではない。

初回out/gui-tangent-browser-20260908は、ブラウザーJSON再生成による数値表記変更で
再構築照合に失敗した。サーバーの保存文字列をそのままダウンロードする修正後に再検証。
照合/数値閾値の緩和なし。構築要求はSIのJSONで編集し、GUI操作がフィレットや弧端認証を追加するわけではない。

```bash
node scripts/verify_gui.mjs --url '起動URL' --out out/gui-tangent-NEW --tangent-request examples/construction/capsule_request.json
```


2026-09-06。[計画](GUI_IO_PLAN.md)のG0〜G5、A1〜A8を対象とする。
状態: 技術的受入PASS。操作ガイドは[GUI_GUIDE.md](GUI_GUIDE.md)。

## 実行環境と再現

Linux 6.8.0-138-generic x86_64、Python 3.12.3、NumPy 2.5.2、SciPy 1.18.1。
Matplotlib 3.11.1。ブラウザー操作はChrome 152.0.7977.82、Node 23.11.1の標準CDPクライアント。
通常操作にNodeは不要。GUI描画にはMatplotlibを使い、Web/Qt依存は追加していない。
実行済みOSはLinuxのみ。Hosted CI・他OS・人による使いやすさ評価は未実施。

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate_gui_workflows.py --out out/gui-numerical-NEW
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate.py --out out/validation-gui-NEW
.venv/bin/python -m superfish_ng gui --workspace out/gui-workspace --no-browser
# 上で表示された起動URLを指定する。出力先は毎回新規。
node scripts/verify_gui.mjs --url '起動URL' --out out/gui-browser-NEW --io yes --extended yes --general yes --pillbox yes --ends yes
```

操作検証は実際のキー入力・クリック・ファイル選択を使う。外部HTTP/HTTPS要求を遮断し、
外部要求がないことも判定する。ソースhashを開始・終了時に検査する。
UIのPASSは数値収束のPASSと別。以下のout/はローカル証拠でありソース配布には含めない。

## 受入対応

| ID | 実際に確認する操作・数値 | 証拠 |
|---|---|---|
| A1 | 円筒の寸法・モード設定、長さ40/80/120 mmの掃引、実場からのTM010/TM011同定、周波数/RF/軸場の独立解析比較、半径プローブ | gui-numerical-final-20260906/report.json、gui-browser-accepted-retry-20260906/report.json |
| A2 | 電気/磁気対称と鏡映、左右両側の数値検査、Uと解析場/RFの確認 | 同数値記録のA2、ブラウザーの半領域2例 |
| A3 | flat4・rounded4/7の通常ファイル読込、全モード表示、half-end同定と分散 | 同数値記録のA3-A4/band、ブラウザーの4+4+7モード |
| A4 | half/fullの実輪郭・場/RF比較、full-endへの位相ラベル拒否。端部も組立の通常部分として編集・置換・順序変更して計算 | 同数値記録のfull_ends、ブラウザーのfull-end2例、gui-end-edit-browser-retry-20260906/report.json |
| A5 | 空から折れ線・円弧の3/5反復、寸法・円弧半径変更。面積/接続・一様拡大則・名前削除・細分変化 | test_project.py、同数値記録のA5、ブラウザーのgeneral操作 |
| A6 | 未対応物理/不正円弧/未知・重複キー、不適切バンド、出力衝突・破損、保存例外、中止 | 既存Case検査、test_project/jobs/saved/studies.py、ブラウザーの不正入力・中止 |
| A7 | 入力/条件群の保存往復、GUI入力をCLI/Pythonで再実行、旧結果取込、再起動後復元 | gui-interoperability-20260906/report.json、ブラウザーのio/restore、test_jobs.py |
| A8 | 計算中の応答、中止→再試行、キー操作、単位変換、不正入力保持、完了と未検証の区別 | G0測定（ADR-009）、ブラウザーのgeneral/io、履歴順回帰検査 |

## 数値の判定範囲

周波数0.1%、RF量1%、正規化軸場の相対L2差1%を別々に適用する。
円筒は独立解析解、形状が一般の場合は同一形状での細分変化を使う。
円弧の弦誤差細分とFEM細分は独立した条件群。細分変化は厳密解の誤差上界ではない。
表面ピークはP1推定で別扱いとし、鋭角でのEpk精度保証には拡張しない。
近接・縮退・場対応の曖昧さはUNVERIFIED。独立掃引に一般mode trackingを仮定しない。

新規Wine比較・実機測定照合は実行していない。従来のNG–Wine比較は
[MILESTONE_ACCEPTANCE.md](MILESTONE_ACCEPTANCE.md)等の過去履歴として残す。
今回のPASSはその再実行を意味しない。原本PDF・旧ソース/バイナリを追加閲覧していない。

GUIダウンロードを起点とするCLI/Python再実行ではcanonical Caseが一致し、
周波数・Q0・R/Q・Gの差はゼロだった。証拠は`out/gui-interoperability-20260906/report.json`。
例題名・4/7セル数に応じた製品分岐はない。任意形状の検証は合成ケースと明記する。

## 失敗を残した改善履歴

- `out/gui-numerical-20260906/report.json`はFAIL。合成折れ線3/5セルの第3モードで、
  nr=48→96の周波数変化が0.125998% / 0.108862%と0.1%を超えた。
  RF・軸場は合格。許容差を変えずnr=192を追加し、最終周波数変化は0.051563% / 0.042013%で合格した。
- `out/gui-general-browser-20260906/`は円弧5反復の入力一致でFAIL。
  未編集座標の単位往復丸めを修正し、`gui-general-browser-fixed-20260906`でPASS。
- `out/gui-extended-browser-20260906-third/`は条件群の項目切替競合でFAIL。
  新しい項目候補に旧選択が存在する場合だけ保持し、fourthで25モード表示を確認した。
  それ以前の最初の2試行には検証側のファイル読込待機・鏡映名の期待値の誤りもあった。
- `out/gui-io-browser-20260906/`は図保存でFAIL。受信済み画像Blobからの保存へ修正し、
  `gui-io-browser-fixed-20260906`で入力・プローブ/設定・図・解析比較・条件群保存がPASS。
- `out/gui-browser-final-20260906/`は中止直後の再実行の履歴位置でFAIL。
  同秒IDのランダム部分による並び順が原因。計算そのものは完了していた。
  作成時刻に基づく順序へ修正し、同秒の逆順IDを使う回帰検査と実操作で再確認した。

これらの未達記録を上書きしない。ソルバー補正・許容差緩和・ベンチマーク更新はしていない。

## 最終証拠と実装版の対応

| 検査 | 結果 | ローカル証拠（out/以下） |
|---|---|---|
| 共通APIの全数値受入 | 32項目PASS、525.31秒、実行中の実装変更なし | gui-numerical-final-20260906/report.json |
| GUI全体 | 25操作記録PASS。半領域2例・多セル5例の25モードに加え円筒長さ3点を実操作 | gui-browser-accepted-retry-20260906/report.json |
| 個別端部編集 | 左端12 mm・繰り返し20 mm×3・右端15 mm、順序変更後の全長87 mmと実計算を確認 | gui-end-edit-browser-retry-20260906/report.json |
| 最終回帰 | 101 unittestと既存数値validate PASS | validation-gui-accepted-20260906/validation.json、tests.log |
| GUI入力のCLI/Python再計算 | canonical入力と主要数値一致 | gui-interoperability-20260906/report.json |
| wheel/ソース配布 | 静的資産を含むwheelの独立展開・計算・描画、ソースZIPのmanifestと内容境界を検査 | gui-package-final-20260906/report.json、source-zip-report.json |

32項目の数値受入後、製品ソースの変更はjobs.pyの履歴ソートだけ。数式・保存・
掃引処理の変更はない。最終の101テスト、数値validate、統合ブラウザー操作は
その修正後のソースで実行した。各レポートとジョブmanifestに実装hashを保存する。
数値受入を最新コミットで全件再実行したという主張には置き換えない。

seed shaped_cellとの比較は周波数差ゼロ、RF相対差最大6.67e-16。
比較値は`validation-gui-accepted-20260906/seed-differences.json`。ベンチマーク更新なし。
最後の細分比較での最大値（モードごとに独立判定）を以下に示す。

| 対象 | 周波数変化 [%] | RF変化 [%] | 軸場L2変化 [%] |
|---|---:|---:|---:|
| flat4 half-end | 0.002078 | 0.32373 | 0.019095 |
| rounded4 half-end | 0.000822 | 0.12765 | 0.045251 |
| rounded7 half-end | 0.000822 | 0.57174 | 0.045251 |
| flat4 full-end | 0.006891 | 0.09388 | 0.070079 |
| rounded4 full-end | 0.000770 | 0.02626 | 0.040374 |
| 合成折れ線3/5セル（最大） | 0.051564 | 0.14925 | 0.056082 |
| 合成円弧3/5セル（最大） | 0.094041 | 0.53113 | 0.285279 |

元数値・比較対象は`gui-numerical-final-20260906/final-comparison-summary.json`と
各study-results.json。円弧形状近似の別検査も同レポートに含む。

最終統合操作の最初の試行`gui-browser-accepted-20260906`は、検証スクリプトが
4モード分の行数を考慮せず次の条件のボタンを選び損ねてFAIL。製品変更なしで
行選択を修正したretryがPASS。端部検証の最初の試行も、更新後に有効なままの
編集ボタンが無効になるという誤った待機条件でFAILした。更新済み寸法を待つ
検査へ修正し、製品を変更せず再確認した。

画面は`gui-browser-accepted-retry-20260906/workspace.png`。表示の目視確認を実施した。
ユーザーへの初期画面提示と任意の意見募集は行ったが、本人による操作評価の回答は
得ていない。初心者の主観的な使いやすさの評価や実機設計認証を、この受入PASSに含めない。

## D01多対多集合継承のGUI方式選択 — 2026-09-08

直前基準6f011b7。「モード群をID集合として継続する」の有効時に方式選択を表示。
従来の合流/分裂を既定とし、多対多を含む方式は明示選択する。
保存対応/履歴の再検証で方式を復元し、履歴継続のcontrolsへ反映する。
無効化するとpolicyとlinkを要求から省略。部分空間を個別ID確定と表示しない。

実Chrome `out/browser-connected-policy-final-20260908` の13項目PASS、外部要求0。
既存8項目と、新方式復元・集合/単一IDの区別・従来方式選択・無効化・履歴継続の5項目。
connected-policy.pngの方式選択と注意書きを画像確認した。
再現は専用の空GUIワークスペースで、従来のverify_gui_mode_tracking.mjsに
`--repartition out/d01-cluster-repartition-20260908` を追加する。

変更前 `out/browser-connected-policy-red-20260908` は新policy復元で想定どおりFAIL。
修正直後 `out/browser-connected-policy-20260908` は検証ワークスペースを再利用して
インポート済み件数が初期条件と異なりFAIL。専用の空ワークスペースで再実行した。
旧失敗出力を保持。今回ブラウザー検証は集合継承の操作受入であり、一般枝回復の受入ではない。

## D01同一領域再メッシュのGUI接続 — 2026-09-08

直前基準aac49fc。比較写像に「同じ直線境界の領域（異なるメッシュ）」を追加。
選択時は全境界一致・標本次数確認・対応とRF収束の区別を表示し、頂点対応欄は隠す。
保存対応/履歴から写像を復元し、直接比較・履歴継続に使う。

`out/browser-same-domain-final-20260908` の実Chrome17項目PASS、外部要求0。
既存13項目と、写像復元・折返し再メッシュ比較・ID履歴継続・異領域拒否/履歴保護の4項目。
same-domain.pngで写像と説明・確認済み履歴の保持を画像確認した。
変更前 `out/browser-same-domain-red-20260908` は写像復元で想定どおりFAIL。出力を保持。
再現は空の専用GUIワークスペースで、verify_gui_mode_tracking.mjsに
`--repartition out/d01-cluster-repartition-20260908 --same-domain out/d01-same-domain-final-20260908`
を追加する。基本の --sources は out/d01-cluster-transitions-20260908。

## D01アフィン再メッシュのGUI接続 — 2026-09-08

直前基準a9f7324。アフィン写像選択・a,c,bの入力/保存復元と明示逆変換操作を追加。
逆変換は入力欄だけを1/a、1/c、-b/(a*c)へ変換する。不正時は部分更新しない。
結果の選択は利用者が行い、誤った写像の履歴継続は拒否して確認済み履歴を保持する。
他写像ではアフィン係数を送らない。

out/browser-affine-final-20260908の実Chrome23項目PASS（追加6/既存17）、外部要求0。
affine-history.pngで逆係数・操作説明を画像確認。変更前out/browser-affine-red-20260908は
写像/係数復元で想定どおりFAILし、出力を保持した。
空の専用GUIワークスペースとverify_gui_mode_tracking.mjsで再現する。
既存 --sources/--repartition/--same-domain に
`--affine out/d01-affine-remesh-verified-20260908` を追加する。

## D01区分アフィン再メッシュGUI — 2026-09-08

直前基準8870204。比較メッシュの完全なJSON配列入力・保存復元と旧/新の明示交換を追加。
交換は入力欄だけを更新し、比較/履歴継続で領域・境界・向きを検査する。
入力配列の構造が不正なら交換せず、比較が失敗しても確認済み履歴を保持する。

変更前out/browser-piecewise-red-20260908は写像/比較メッシュ復元で想定どおりFAIL。
初回out/browser-piecewise-final-20260908は比較/交換/履歴継続後の保存検査でFAIL。
Chromeのダウンロード設定が同名ファイルを上書きする一方、検査は新規ファイル名を探していた。
実ファイルにはpiecewise_remeshの2段階履歴が保存されていたため、製品の保存処理は変更せず、
検査を保存内容と確認済み履歴の直接照合へ修正した。初回出力を保持。

最終out/browser-piecewise-recheck-20260908は実Chrome30項目PASS（追加7/既存23）、外部要求0。
piecewise-history.pngで入力・交換操作を画像確認した。空の専用GUIワークスペースで
verify_gui_mode_tracking.mjsへ既存オプションと
`--piecewise out/d01-piecewise-remesh-20260908` を渡して再現する。

## D01同じ二次曲線領域のGUI接続 — 2026-09-08

直前基準a38f83a。写像選択・保存復元、同じ曲線宣言/パラメータ付け/二次境界の条件表示を追加。
比較診断にphysical_mappingを表示し、境界照合の共通区間数・係数距離・丸め幅等を確認できる。
曲線再メッシュの比較/履歴継続ができ、再投影で変わった境界は拒否して確認済み履歴を保持。
保存には境界照合の証拠も含まれる。

out/browser-curved-domain-final-20260908は実Chrome35項目PASS（追加5/既存30）、外部要求0。
curved-history.pngの写像・条件・履歴保持を画像確認。変更前out/browser-curved-domain-red-20260908は
写像復元で想定どおりFAIL。失敗出力を保持。
空の専用GUIワークスペースでverify_gui_mode_tracking.mjsへ既存オプションと
`--curved out/d01-curved-same-domain-final-20260908 --reprojected out/curved-gui-reprojected-20260908`
を追加して再現する。再投影例はellipsoid-1-0/case.jsonを読み、contourをNone、
curve_chord_tolerance_mを1/4、curved_refinement_levelsを0にして実solve/save_runした156三角形の結果。
解析曲線を変えず、二次近似境界だけを変えている。

## N04適応細分GUI — 2026-09-08

両版の入力作成・実worker開始/中止、全域確認途中と中止後の保存再開、f/RQ/G個別差、
対象順位2の場表示、厳密JSONの重複キー拒否を追加。
out/browser-n04-refinement-strict-20260908のChrome19操作PASS、外部リクエストなし。
初回の再読込検査FAILは検証手順をPage.reloadへ修正し、出力を保持した。
最終標準600件中598合格・2 skip、独立P2円筒f/RQ/G・相似則と周波数/RF回帰もPASS。
各検証のソースhashは最終コードと一致。対象・未対応は[適応細分GUI](GUI_ADAPTIVE_REFINEMENT.md)。
一般形状の精度/効率や表面ピークを、このGUI受入で認定しない。

## N03直線表面評価GUI — 2026-09-08

適応結果から任意の確認済み個別IDで評価し、五量の区間判定・ピーク上下界・元輪郭角診断を表示。
保存/全再検証・ページ再読込、別IDの対象場表示、確認待ち/再入角/形状未確認/未収束の区別を追加。
out/browser-affine-surface-initial-20260908で実Chrome16操作が初回PASS。外部ページリクエストなし。
達成と再入角の画像も確認。通信3検査、標準613件中611合格・2 skip、独立円筒解析比較・相似則PASS。
各検証のソースhashは最終コードと一致。対象と残件は[直線表面評価GUI](GUI_AFFINE_SURFACE_CONVERGENCE.md)。

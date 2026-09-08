# 汎用GUI・共通入出力の受入記録

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

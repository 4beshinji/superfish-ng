# 元メッシュと細分履歴を保持する形状変形GUI

2026-09-14 JST、N04残件4の単独Project操作を接続した。
既存の[調和変位API/CLI](CURVED_HARMONIC_DEFORMATION.md)を使い、
目標形状の準備、変形プレビュー、別ファイル保存、適用、Undoを行う。
[形状Study](CURVED_HARMONIC_STUDY.md)は別の複数条件操作として保持する。

## 受入条件

- 元Projectを編集せずに目標形状を準備し、全履歴後の実二次メッシュ境界を表示する。
- API/CLIと同じ変形済みProjectを保存・適用する。元メッシュ、固定分割、RF条件を落とさない。
- 形状・品質・RF条件が変われば古い候補を適用しない。非同期応答と値を元に戻した編集も検査する。
- Undoは変形直前のProjectへ戻し、その後のProject編集を上書きしない。
- 厳密JSON、未固定履歴、品質違反と実メッシュ反転を拒否し、検査失敗を実行中表示のままにしない。
- 通常のProject保存・再読込・実worker・元保存場表示までCLIと一致し、既存の履歴編集を保つ。

## 操作

1. [合成元Project](../examples/curved_harmonic_deformation/source-project.json)を通常の「開く」で読む。
   解析曲線の欄にある「元メッシュと細分履歴を保って形状を変える」を開く。
2. 「現在の曲線から目標形状を準備」で現在のgeometryをコピーするか、
   [目標形状JSON](../examples/curved_harmonic_deformation/target-geometry.json)を専用のファイル欄から読む。
   入力欄はCaseのgeometryオブジェクトで、長さはm、角度はrad。
3. 寸法と共有端点を編集し、RF座標の方針と全段階の最小頂点接線角を指定する。
   marked細分が未固定なら、既存の「元メッシュと分割を固定」を先に使う。
4. 「形状と全履歴を検査してプレビュー」で、元の境界を灰色破線、変形後を青実線で重ねる。
   元/先の要素・節点数、有効長、電圧区間、位相原点と暗黙/明示の区別も表示する。
5. 「変形済みProjectを別ファイルに保存」はサーバーが返した元のJSON文字列を取得する。
   「検査済みの変形を編集画面へ適用」は通常の保存・計算・図上メッシュ確認へ引き渡す。
6. 「直前の形状変形を元に戻す」で、適用前の形状・メッシュ・全履歴・RF条件へ戻す。
   別Projectの読込や適用後のProject編集でUndoを解除する。目標形状の下書きだけの編集はProject編集と分ける。

対象は未組立・未反射のnative曲線P2、閉PEC・軸のTM。
曲線番号/増加分率を対応させ、曲線数・順序・境界タグ・弦分割数を保持する。
単独変形APIはプリミティブ種類の変更を許すが、曲線法則Studyの離散的な種類変更とは別契約。
TE、半領域、未固定markedや品質不足の受理範囲を拡張しない。

`fixed`は元の有効長・電圧区間・位相原点を保持する。
`axis_fraction`は全軸長比でそれらを換算する。位相原点の暗黙/明示も保持する。
形状外のRF区間などの通常Case検査、全初期水準/履歴prefixの品質・正Jacobian・辺交差・予算検査は既存APIに従う。

## 表示と状態の契約

新`gui_curved_deformation.deformation_response`と`preview-curved-deformation`が厳密な4項目を受け取る。
`document`、`geometry_document`、`rf_coordinates`、`minimum_corner_angle_deg`は全て必須。
目標JSON文字列をブラウザー側で再解釈せず厳密readerへ渡すので、重複キーを失わない。
処理は読取専用で、固有値求解やworkspaceのProject作成を行わない。

表示は元/先の全細分履歴後のnative境界である。各辺の始点a、終点b、中点mから、
二次Bezier制御点`2m−(a+b)/2`を作る。同じ縮尺と制御点を含む表示範囲で重ねる。
表示用の再メッシュや直線への置換を行わない。内部要素の選択は適用後の既存図上メッシュ操作で行う。
主画面の通常輪郭プレビューは従来どおり弦近似と明記する。

候補には元Project、入力の文字列/条件、編集世代を対応付ける。
入力イベントは候補・保存/適用ボタン・重ね図を解除する。
応答到着時と保存/適用時に現在値を照合し、入力を変更して元に戻した場合も世代で拒否する。
Undoは適用直後のProjectと一致する場合だけ使え、イベントを発生させない値変更も操作時に拒否する。
新規/読込・別の適用は旧候補とUndoを解除する。既存の履歴だけのUndoとは独立する。

## 検証記録

索引は`out/gui-curved-deformation-20260914/acceptance.json`。
着手HEADは`91e177e`、初期作業ツリーはclean。初回の独立境界テストはGUI応答API不在でredだった。

新`test_gui_curved_deformation`の3件は5.506秒PASS。
全native境界との一致、別の多項式積分によるGreen面積比1.125/回転体積比1.125²、
元入力の保持、全固定履歴、RF全軸長換算、厳密入力、未固定履歴、実負Jacobianを検査する。
プレビュー中の固有値求解は禁止して検査した。

選択実行`selected-tests.log`は56.693秒で実テスト31件が合格し、誤指定した
存在しない`test_project_mesh_operations`のimportだけが失敗した。集約実行の終了1は保持する。
実行したモジュールは新GUI、`test_gui_curved_mesh_selection`、`test_gui_tangent`、
`test_frozen_curved_refinement`、`test_curved_harmonic_deformation`、`test_job_startup_cleanup`。
正しい`test_project_mesh`と`test_project`は別に9件を1.046秒で実行した。
このうち例題往復1件に2つのエラーがあり、新しいStudy例を単独Caseとして読む古い前提が原因だった。
専用Studyパーサーでの往復・元Projectの保持・単独Caseパーサーでの拒否を確認するようテストを補修し、
当該1件は0.204秒PASS。最終の異なる40テスト（新3/既存37）は分割された合格証拠を持つ。
40件が単一実行でPASSしたとはしない。製品Case/Projectパーサーの受理範囲は変えていない。

実Chromeは`browser-final`の新21項目と`browser-frozen-regression`の既存9項目がPASS。
初回`browser`は10項目と実workerまで進み、CLI比較ファイルの誤ったパスで停止した。
参照を`cli-run/solution/results.json`へ修正し、上記最終21項目を実行した。
各ブラウザー実行は通常Project workerの1 FEMを含む。CLIでも同じ変形Projectを1 FEM計算した。
成功した新/既存browserの2 FEMとCLIの1 FEMに加え、初回browserの1 FEMが保存されている。

その後の製品変更は、プレビュー失敗時のステータス3行と、縮小表示する図中文字のCSS1行だけ。
新`browser-additional`は6項目PASS、RF両方針の実選択/明示座標、品質拒否/失敗表示、
有効な凹形状での実メッシュ反転、変更して同じ値へ戻した要求の拒否、表示寸法を確認した。
追加実行には新FEMなし。最終画像を目視し、外部HTTPは全実行で0。
各browser実行中の製品316ファイルは不変。最終追加browserのSHAが現行製品と一致する。

`validate_gui_curved_deformation.py`は既存のGUI/CLI実保存場を読取再検証する。
初回は検証器のR/Q係数2の向きを誤って記述したため失敗した。PHYSICSの
accelerator=`V²/(ωU)`、circuit=`V²/(2ωU)`の定義に修正し、製品/許容差を変更せず再実行した。
`native-validation-final`は1.489秒PASS、新FEMなし。
GUI/CLIの周波数配列と全P2係数配列が完全一致し、146要素の元native境界と表示が完全一致。
全表示RF量を元場から再評価し、独立な電気+磁気エネルギー・正規化・電圧からの両R/Qを確認した。
元/先の独立Green比も再確認。境界の符号付き積分の負号は周回方向であり、負の物理体積ではない。
検証中1,023ソース系ファイルと27nativeファイルは不変だった。

今回はGUI操作と直接消費先に限定し、FEM・変形数学・保存形式・物理許容差は変更していない。
全件validate/seed/Hosted CI/新Wine比較/実測確認は実行していない。
過去の全件FAIL+対象補修+別seedを、今回の単一full PASSに読み替えない。
新規外部資料・依存・旧資産参照なし。既存独立実装と合成形状を使用した。

## 残る範囲

単独変形GUIの今回の受入条件は満たした。初期再メッシュを伴うStudy、
独立メッシュへの自動番号対応、TE/反射/半領域の変形契約、一般的な物理枝回復、
N04一般精度/効率とC00.V/G03/V02ほか全計画は未完。
親33=8受入/17進行/7他未受入/1範囲外とgoal ACTIVEを保持する。

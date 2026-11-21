# N02場対応工程：元P2場・個別ID・欠測を保持する比較

2026-10-07。N02入力/来歴工程 `dd769cc` に続き、保存された元P2場を比較する
有界工程を追加した。**N02はIN_PROGRESS**。原カードの3×3行列・五量区間・
幾何不変量/求積/ピークの集約は後続。親G03/N03、元123カード・互換32要件・全goalは維持する。

## 実装と判定

[geometry_surface_fields.py](../src/superfish_ng/geometry_surface_fields.py) の
`compare_geometry_surface_fields` は、同一の完全解析形状・物理・規格化・RF規約を持つ
native CurvedSolutionを比較する。入力は閉PEC・単一真空・軸接続m=0 TM・P2。
TE/半領域/鏡映/異形状/不正ID/未対応写像はsample前に拒否する。
直接APIは提供場の診断であり、固有対の検証は後述の保存wrapperで行う。
製造多項式による検査をFEM固有モードとして報告しない。

二つの写像を明示的に区別する。

| 写像 | 条件・意味 |
|---|---|
| `analytic_geometry_approximations` | 元の全解析形状が同じ二次近似を、元Studyと同じcentroidで比較。共通域/有限sample診断で、二次境界の一致を要求しない |
| `curved_same_domain` | 全二次辺のBernstein係数一致を確認し、N01の元native追跡も要求。sample_order10、overlap .98、margin .05、cluster gap1e-6、rank閾値1e-8を保持 |

Study互換診断はHφの重なり .98、競合差 .02、計算された近接比1e-6、
絶対軸Ezの相対L2 .01を保持する。周波数順位から個別IDを推測しない。
Hφから得た単一符号を全E/H・軸Ezへ適用し、振幅を調整しない。
元Hφの尺度差とEr/Ezベクトルの尺度差を別に保存する。
内部の相対L2はcentroidの診断値であり、未指定の新閾値を足していない。
軸Ezがゼロで相対差を定義できない場合はUNVERIFIED。

強い固定領域追跡の全個別IDが未確認なら、出力IDはnullで停止する。
262144 sample予算を超えた場合もUNVERIFIEDで、orderを黙って下げない。
既知の同一場を3回一様制限した104→6656要素の反例で、この停止を確認した。
部分空間だけのPASSを個別IDのPASSへ昇格しない。

## 被覆・欠測・旧判定を分離する

元Studyと同じ、前側meshの最大4096個の写像centroidとdeterminant*r重みを使う。
全選択要素番号・物理座標・重み、旧Hφ共通maskと全E/H共通mask、欠測点/重み比、
両側の元Hφ/Er/Ezを保存する。欠測値はJSONのnullとし、点自体を削除しない。
選択点がすべて有効でも `whole_domain_coverage_proven=false` を保持する。
centroidの重み比を厳密な全域被覆率とは呼ばない。

旧Study診断 `legacy_comparison` は独立した欄に保存する。
そのf .001/RF .01をN01のf1e-4・RQ/G .005・ピーク .01の代わりに使わない。
旧共通域だけの判定がPASSでも、新診断に欠測があればUNVERIFIEDとなる。
軸の全積分点・3点Gauss重み・両場・適用符号も保存し、後から根拠を確認できる。
この工程は幾何差/FEM差/求積差/離散ピーク区間/独立物理参照の受入ではない。

## 保存・CLI

版1の要求を `build_saved_geometry_surface_fields` に渡す。
必須は `schema_version`、`document_type=geometry_surface_field_request`、
`previous_run`、`current_run`、前側順位ごとに一意な `previous_ids`、`mapping`。
未知キーや閾値の上書きを拒否する。元入力から全境界/場/固有対/規格化/RFを
read_solutionで再検証してから比較し、新しい固有値求解は行わない。

completionが所有する全ファイルとmarker、全製品Python源をSHAで固定する。
axis CSV/VTKのようなexportも検査中の変異を見逃さない。
`save_geometry_surface_fields` は排他書込、`read_geometry_surface_fields` は
全要求/元ファイル/サンプル/数値/実装SHAを再構築して完全一致を要求する。
報告へ全域保証を追記する改変や、元係数/後のCSV変異・symlinkを拒否する。

CLIは既存validatorへ `--field-pair-request request.json --out <new-dir>` を追加した。
終了値はPASS0/FAIL1/UNVERIFIED3。失敗/未確認でも完成した診断を新規outへ残す。
catalogの数値実行はまだ未実装で、`--catalog` は引き続き明示SHAと `--plan-only` を要する。
元archiveの数値関数・mkdir以降の全数値bodyはAST一致する。

## 実行証拠

rawは `out/n02-surface-fields-20261007/`。
最初のmissing module ERROR、軸ゼロをFAILにしてしまったFAILと修正前sourceを保持した。
さらに不正端Caseの製造をassertRaisesの外で行った検査側ERRORを保持し、
その1件だけ修正して再実行した。他の成功済みmethodのASTと製品源は不変。
native追跡の既存出力キー/個別ID完全性も実装中に照合して修正前sourceを保存した。

| 実行 | 結果・範囲 |
|---|---|
| 製造場の新7件 | 26.097秒の初回は6成功＋1検査側ERROR。修正1件0.360秒で成功 |
| 元nativeの新3件 | 3.775秒、終了0。実FEM2解・3モード、保存完全再生/元Study完全一致/CLI一致、completion全byte/改竄・後export変異拒否 |
| 直接消費4件 | 2.243秒、終了0。元catalog CLI、旧ピーク区間2条件、smooth/singular判定 |
| 旧楕円9解・8区間 | 166.641秒、終了0。六つの固定FEM区間＋二つの幾何区間は全PASS、元Study報告完全一致、全欠測0、新FEM0 |

新10＋直接4＝14個別unitを分割受入。製造場ではH=r(2+3r−4z)、
Er=4r/(omega eps0)、Ez=(4+9r−8z)/(omega eps0)を別式で検査した。
符号反転、振幅2%差とunit overlap、Hの直交不一致、周波数順位交換、近縮退、
欠測とゼロ軸、真の固定P2制限と予算停止を確認した。
製造場は運動学的なP2検査であり、境界条件を満たす固有解と表示しない。
実2 FEMは粗い楕円であり、N01の新3×3系列を物理受入したとはしない。

旧楕円の元report SHA a025a9b0974bce2deec421032957fdd317733330b4fa7fdba1ce496eda48f0e2
と全9 nativeのcompletion全byteは不変。これは元1モード系列の場診断の互換受入で、
N01の新3モード行列・独立Maxwell/物理ピークの成功へは数えない。

元1192 Python源の変更は専用CLI一つのみ、新2源を加え1194。
科学solver/RF定義/全物理閾値は不変。全数値源は実行中固定し、検査側の失敗1methodだけを修正した。
新seed/full/legacy/外部独立求解0、新依存・外部資料・legacy内部参照はなし。

## 原条件の残件

この工程で元保存場・個別対応・欠測の可視化と、実場/製造場の不一致反例を追加した。
旧楕円のf/場/RFの判定を保存したまま、新caseの完全3×3行列をSHAで結び、
幾何モーメント/境界位置、固定FEMの二変化、同じ保存場の求積12/16/24と壁8/16、
ピーク上下界の二変化を集約する工程が残る。
故意のピーク未収束・幾何未確認と、旧楕円全量の新集約判定一致も未受入。
独立非球形物理参照はUNVERIFIEDのまま、自作NG出力を独立参照へ流用しない。
次はN02の保存行列・五量/幾何/求積/ピークの分離評価。その後N03の全系列実検証へ進む。

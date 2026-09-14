# N04: 異なる曲線細分履歴への選択領域の移送

2026-09-14 JST、開始HEAD `c87fab0`。
[N04残件4](N04_ACCEPTANCE.md)のうち、対応する初期P2分割から別々の局所細分を行った
二つのProject間で選択領域を移す機能をAPI・CLI・GUIへ追加した。
受入条件は、番号の独立変更・包含関係のない最終分割・非アフィン形状変更を扱うこと、
交差領域の完全被覆、二つの選択方針、厳密入力・予算・改変拒否、保存再構築、
既存の図上選択/履歴反映/実FEMへ接続することである。
この限定範囲を受入とし、N04全体の一般精度・適応効率は未受入とする。

## 対象と入力

`curved_selection_transfer.transfer_curved_cell_selection(previous, current, request)` は
二つのProjectを変更せず、完全な再構築可能文書を返す。
直接のnative P2 TM、未組立・未反射のProjectを対象とする。
原領域の電気/磁気対称境界は扱う。TEや鏡映後の全空洞への領域移送を受理しない。

[番号対応](CURVED_COMPARISON_CORRESPONDENCE.md)を**履歴適用前の初期分割**へ使い、
全P2節点・要素の向き付き一対一対応を検査する。初期節点/要素番号は独立でよい。
初期分割の接続が対応しない一般再メッシュには使えない。
各側の最終分割は同型・nestedでなくてもよく、局所適合細分の遷移要素も扱う。
二つの形状で同じ物理座標を占める領域の比較ではなく、宣言した初期P2写像に従う領域の移送である。

要求版1の全フィールドは必須。未知フィールド、重複キー、重複番号、真偽値や小数の番号、
空の元選択、範囲外番号、無効な履歴/品質/Case予算を拒否する。

```json
{
  "schema_version": 1,
  "selected_cells": [0, 2, 6],
  "boundary_pairing": "ordered_curve_vertices",
  "coverage_policy": "intersects",
  "max_pair_tests": 100000
}
```

`selected_cells` は変更前Projectの**全履歴後**の0始まり要素番号。
`boundary_pairing` は `same_curve_fractions` または `ordered_curve_vertices`。
前者は同じ曲線分率、後者は曲線内の節点順を対応と宣言する。曲線種類/順序・タグなどは既存の対応検査に従う。
後者は分率の移動を許すため、単なる番号自動推定と区別して明示する。

| `coverage_policy` | 移送先の選択 |
|---|---|
| `intersects` | 正の参照面積を持って重なる全要素。移送領域を覆う |
| `contained` | 要素全体が移送領域に含まれるものだけ。空集合も有効 |

辺や点だけの接触では選択しない。一部だけ重なる要素を別配列で報告する。
覆う集合や内部の集合が元領域と完全一致するとは限らない。

## 参照領域の計算と物理量

各初期要素に参照三角形 `((0,0),(1,0),(0,1))` を置く。
既存native細分から得る親要素番号と親参照頂点を、標準ライブラリーの`Fraction`で合成する。
一様/局所細分は中点を使うため、その二進浮動小数の親座標は有理数として厳密に表せる。
固定済みsplit patternを含め、各履歴を元の品質・要素数上限で実行する。
初期要素ごとの全子要素面積が正で、総和が厳密に1/2となることを確認する。

対応した同じ初期要素に属する旧選択要素と全新要素の組だけを調べる。
その組数を交差計算前に数え、`max_pair_tests`を超えれば拒否する。
この数はbounding boxで除外する組も含む。履歴構築は各Caseの要素上限で別に制約する。
既存`planar_tracking_overlap`の有理数三角形クリッピングを再利用し、
交差多角形の全頂点・面積と新要素ごとの被覆率を分子/分母の整数対で保存する。
各初期要素について、旧選択面積と交差面積総和の厳密一致を必須にする。
被覆率が0より大きく1以下であることも検査する。

ここでの面積は無次元の参照面積であり、異なる初期要素の和も物理面積ではない。
非アフィンなP2写像では参照被覆率と物理面積・回転体積の被覆率は異なる。
独立検証器は別実装の二次形状関数/偏微分と8×8 Gauss-Duffy積分により、
面積 `∫dr dz`、回転体積 `2π∫r dr dz`、既知場Hφ=rの幾何質量 `∫r³dr dz` を照合する。
後者の単位はm⁵で、2πや透磁率を掛けた電磁エネルギーそのものではない。
参照領域の完全被覆、物理積分の一致、実FEMの周波数/RF/場形状は別の検査である。

## 保存、CLIとGUI

戻り値は `document_type="curved_selection_transfer"` の版1文書。
両Project、要求、初期番号対応、全交差多角形/面積/被覆率、選択番号、部分被覆番号、
元/先の最終要素数、検査組数、初期要素ごとの面積照合と適用範囲を保持する。
`status="PASS"` はこの幾何選択の検査結果であり、FEM精度の合格を意味しない。
`replay_curved_selection_transfer(document)` は両Projectから全計算を再構築して照合する。
同値な浮動小数のJSON表記 `0`/`0.0` は受理するが、導出した整数ID・有理数の分子/分母と真偽値の型は厳密に保つ。
自己完結した再構築であり、外部の真正性証明や署名ではない。

```sh
PYTHONPATH=src .venv/bin/python -m superfish_ng transfer-curved-selection old-project.json new-project.json --request request.json --out transfer.json
PYTHONPATH=src .venv/bin/python -m superfish_ng replay-curved-selection-transfer transfer.json
```

出力は全検査後に排他的に作成する。既存出力を上書きしない。
移送文書自体はProjectの履歴を変更しない。

GUIでは移送先の対象段階のメッシュを図上表示し、「別の細分履歴から選択領域を移す」で
旧Projectと旧最終選択番号、境界方針、選択方針、予算を指定する。
成功時はSVG/Canvasの現在選択へ新番号を反映する。
元の全Projectと対象段階・履歴・移送条件・手動選択を応答後に照合し、途中の変更を拒否する。
入力不正/予算超過/古い応答は直前の選択と記録を保持する。
元Project/番号JSONは生テキストをサーバーの厳密readerへ渡す。

移送記録を保存・再読込すると、全再構築の後に旧Projectと選択条件を復元する。
移送先Projectを暗黙に置換せず、現在の対象段階を図上表示して移送を再計算する。
その後は既存の末尾追加/途中挿入/段階再選択ボタンで履歴へ反映できる。
後続の未修復marked行を自動で処理する機能ではない。

## 検証と失敗の扱い

証拠ルートは `out/curved-selection-transfer-20260914/`。合成半楕円と直線三角形を使い、測定構造とは扱わない。
初回の独立親子面積2件はAPI不在で失敗し、実装後0.084秒で合格した。

| 検査 | 観測した結果 |
|---|---|
| 新`test_curved_selection_transfer` | 最終8件を分割して確認。最初の6件は5合格/入力fixtureの履歴方式混在1ERROR（0.523秒）。uniform行へ直した当該1件0.332秒PASS。厳密範囲/追加対称領域2件0.348秒PASS。再読込修正後の関連2件0.317秒PASS |
| 選択した既存回帰 | 初回43件43.847秒は41合格/存在しないモジュール指定1ERROR/HTTP権限1skip。実在する履歴/交差2モジュール8件3.847秒、許可環境の同HTTP1件0.564秒で補完。最終50件の分割合格であり、単一全件PASSではない |
| 専用数値検証 | `numerical/report.json`、4新FEM、6.299秒PASS。異なる局所分割・非アフィン変形・独立番号・両尺度、CLI/保存再生 |
| 新GUI | `browser-reloaded/report.json`、18項目PASS、1新FEM。厳密入力/予算/変更中応答拒否、SVG/Canvas、記録復元、履歴反映/Project保存再読込とRF一致 |
| 従来GUI | `browser-history/report.json`、20項目PASS、1新FEM。途中挿入・修復・Undo・保存/実計算・Canvas |
| 保存記録/場のnative検証 | `native-browser/report.json`、18.602秒PASS、新FEMなし。小規模2選択と6,656要素中96選択の全再構築/独立物理積分、GUI/独立FEMの全係数・周波数・P2座標・接続完全一致、RF11量とエネルギー/RQ定義 |

専用例の初期分割は26要素で対応する。旧111→新112要素は別の局所細分履歴で、
旧選択[0,2,6]は新[81,82]を覆いとして選び、82は部分被覆、包含方針は[81]となる。
移送番号でmarked段階を追加した実FEMは126要素。
旧native選択と有理数交差領域の独立物理積分三量は相対差最大1.555e-15。
尺度2では面積4倍/体積8倍/幾何質量32倍、選択と有理数報告は完全一致した。

尺度1の追加前/後の周波数は1.4440523187044163/1.4440523158092551 GHz。
同じ固定二次領域への局所細分でRitz非増加を確認した。
追加後R/Qはaccelerator 36.332121375279435 Ω、circuit 18.166060687639717 Ω。
尺度2のfは1/2、両R/Q・G・TTFの尺度則相対差最大1.022e-14、
U=1 JでのHφ/Er/Ezの尺度則相対差最大1.651e-13。
この尺度確認を実空洞の離散化誤差や表面ピーク収束保証に読み替えない。

初回ブラウザーは8項目後に検証器のselector文字列エスケープで停止した。
修正後、12項目後のダウンロード記録再読込で製品不具合が見つかった。
JSONの同値な数値表記とNumPy浮動小数metadataを扱う値比較へ修正し、
再現unitのredと補修途中の失敗を保持した。中間のGUI試行は旧モジュールを読み込んだ
長寿命サーバーへの実行であり、最終修正の合格証拠とはしない。
専用サーバーを終了・再起動した `browser-reloaded` で全操作が合格した。
これら途中ブラウザーは実FEM前に停止している。
修正後は既存数値4記録と途中ブラウザー2記録を再構築し、`replay-corrected.json`に6件PASSを保存した。新FEMはない。

両最終ブラウザーは外部HTTP要求0、321製品ファイルのSHAが実行中不変で最終実装に一致する。
選択SVG・Canvas・既存履歴の3画像を目視した。native検証では1042ソース系と23保存artifactが不変。
数値検証時の1041ソース系からは、新native検証器・selector修正・replay修正・追加unitの4パスが変わった。
交差/履歴計算とFEMは不変で、replay修正は関連unit/保存6記録/再起動後GUI/nativeで別に確認した。
数値時ソースが最終ソースと全一致したとは主張しない。全検証handleと専用サーバーは終了済み。

初回回帰の存在しない `test_curved_refinement_history` 指定と、独立プローブのimport経路誤指定も失敗として保持する。
非nested fixtureで局所子番号を単純に「初期番号×4+1」とした試行は、巡回頂点順変更後に別の物質点を指していた。
検証器で独立番号対応を使い、本当に異なる領域を細分する111→112要素の例へ直した。製品や物理許容差は緩めていない。

再現用の主要コマンド（各`--out`は未使用のディレクトリ）：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest test_curved_selection_transfer
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest test_curved_marked_refinement test_curved_refinement test_frozen_curved_refinement test_curved_comparison_correspondence test_gui_curved_mesh_selection test_project test_project_mesh test_gui_hphi test_curved_refinement_steps test_planar_tracking_overlap
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_curved_selection_transfer.py --out '<numerical out>'
node scripts/verify_gui_curved_selection_transfer.mjs --url '<GUI URL>' --out '<browser out>' --sources '<numerical out>'
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_curved_selection_transfer_browser.py --browser '<browser out>' --numerical '<numerical out>' --saved-solution '<GUI job>/solution' --out '<native out>'
```

上のまとめたunitコマンドは再現用であり、今回単一実行した記録ではない。
旧ブラウザーの入力生成/実行方法は[履歴挿入の検証](GUI_CURVED_HISTORY_INSERTION.md)を参照。
全件validate/seed/Hosted CI/新Wine比較は実施していない。既存FEM・物理定数・許容差は変更していない。
新規外部資料・依存・旧資産参照はない。既存の有理数クリッピング/細分親参照写像を再利用した。
異なる初期接続の領域移送、一般共通比較メッシュ、境界分割を変える再メッシュ、N04一般精度/効率は残る。
親33=8受入/17進行/7他未受入/1範囲外、全計画goal ACTIVEを維持する。

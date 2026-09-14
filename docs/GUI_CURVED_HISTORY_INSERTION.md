# N04: 曲線細分履歴の途中への図上挿入

2026-09-14追補：[領域移送](CURVED_SELECTION_TRANSFER.md)で、対応する初期P2分割から異なる履歴へ選択領域を移す明示操作を追加した。
旧Projectの全履歴後の領域を、現在表示している前半Projectへ移し、既存の挿入/再選択に使える。
覆う集合と内包集合を区別し、後続行の一括自動修復は行わない。本書以下の「自動対応なし」は当初の挿入操作単体の契約を表す。
今回も既存Chrome20項目と実FEMがPASS。履歴付き形状Studyの最新範囲は[曲線Study](CURVED_HARMONIC_STUDY.md)・[初期メッシュStudy](CURVED_REMESH_STUDY.md)を参照。

2026-09-14 JST、開始HEAD `16d0cd9`。
[N04残件4](N04_ACCEPTANCE.md)の途中挿入と既存marked段階の図上再選択を追加した。
受入条件は、指定段階の直前のnativeメッシュを表示すること、前半の履歴を保持すること、
後続の旧要素番号を黙って流用しないこと、保存・計算までの修復操作、取り消しと古い選択の拒否である。
この範囲を受入済みとする。N04全体の適応効率・一般物理精度は未受入。

## 操作と番号の意味

「図上選択の反映先」で末尾追加、指定段階の直前への挿入、既存段階の選び直しを選ぶ。
段階は1始まり、図の要素番号は従来どおり0始まり。
1段目の前なら初期メッシュ、k段目の前なら最初のk−1段だけを適用した原領域を表示する。
既存marked行の「図上で選び直す」も、その行の直前を表示する。
5,000要素以下のSVGと、それを超える[Canvas表示](LARGE_CURVED_MESH_SELECTION.md)に共通の操作である。

挿入は元の前半と後続uniform段階、marked段階の種類・角度・順序を保持する。
後続marked段階の番号欄は空欄にし、変更前の文字列を参照用に表示する。
その段階の新しいメッシュを図上表示して選び直すか、確認した番号を手入力する。
未指定のまま保存・Case出力・計算を行うと、従来の厳密な履歴検査で該当段階を示して拒否する。
修復前の後半が未完成でも、有効な前半を使って順に選び直せる。
この編集途中の状態はブラウザー内のdraftであり、新しい保存形式ではない。

旧番号の自動対応付けは提供しない。局所適合細分には遷移要素があり、異なる履歴で生じた
三角形分割が常に包含関係にあるとは限らない。番号や重心だけで対応を推測しない。
「直前の図上変更前の履歴に戻す」は、最後の図上操作より前の全履歴を復元する。
その操作後に行った履歴の手編集も戻る。複数段のundo履歴ではない。
形状・元メッシュ・RF等の計算入力が変わっていれば、旧番号への復元を拒否する。
別Projectの読込でdraft、図上選択、undo状態をリセットする。

一様段数方式への途中挿入では同じ段数のuniform行へ展開し、指定位置にmarked行を入れる。
その全一様段数だけで最低要素数 `4^n` がCaseの要素上限を超える場合は先に拒否する。
実際の生成数・品質・細分予算は従来のnative経路で検査する。

## 実装の境界

`web/app.js`の内部`collect(prefix)`が前半だけの有効なProjectを作り、既存の
`curved-selection-mesh` APIへ送る。空の前半は一様0段で表し、空steps配列を送らない。
既定の`collect()`と保存Caseのスキーマ・FEM・許容差は変えない。
明示元メッシュもProjectに保持する。

選択署名には前半Project、反映先、段階、全行の識別子・種類・生の番号文字列・角度・旧番号表示、
一様段数/履歴方式を含める。応答後・Canvas準備後・反映時に照合する。
後半の入力変更や行の並べ替えも、前半だけのProject比較で見落とさない。
無効になった入力でも通常の「再表示してください」という拒否へ変換する。
履歴表は狭い編集欄で「一様」「選択要素」が読める列幅にした。CSPは保持する。

手動での任意の並べ替え・削除や、形状/初期メッシュ変更に対する自動番号移送は今回の機能ではない。
既存の手編集の注意事項を維持する。履歴付きの形状掃引も未対応。

## 検証

変更前の `out/curved-history-insertion-20260914/baseline-red.json` に操作の欠落を保存した。
同時に、合成半楕円の局所細分で39→56要素となる例を調べた。
P2の参照重心の係数 `(-1/9,-1/9,-1/9,4/9,4/9,4/9)` で求めた同じ番号20の点は
約0.0180272 m変わる。整数の再利用では同じ物理領域を選べないことを先に確認した。
これは測定空洞や旧SUPERFISHの結果ではない。

| 検査 | 結果・範囲 |
|---|---|
| `test_gui_curved_mesh_selection` | 4テスト、10.838秒PASS。native番号/曲線節点、元Case予算、明示元メッシュ |
| 新しいChrome検証 | `browser-first/report.json`、20項目PASS。最初/途中の前半表示、対象/後半変更の拒否、未修復の保存/計算拒否、undo入力ガード/復元、実応答の遅延中変更、修復/保存再読込/実FEM、6,656要素Canvasからの途中挿入 |
| 従来SVG末尾追加 | `browser-append/report.json`、6項目PASS、実FEM。列幅修正後の履歴画像も確認 |
| 従来大規模末尾追加 | `browser-large-append/report.json`、21項目PASS。26,624要素、クリック/キーボード/移動/拡大、準備中変更拒否、非同期破棄 |
| 独立native検証 | `native-verification/report.json`、31.223秒PASS。6応答の全節点/要素配列、途中挿入後の232/26,664要素、独立Green境界積分、保存場再読込とRF9量 |

独立検証の面積と回転体積は、固定した元の二次境界に対して相対1e-12以内。
元の符号付き面積は−0.006282875433407661 m²、体積は−0.0013403138879848234 m³で、
負符号は境界の向きによる。解析楕円への幾何誤差がゼロという主張ではない。
保存された232要素の実FEMでは約1.614628213 GHz、U≈1 J、電気/磁気エネルギー各≈0.5 J。
R/Qはaccelerator≈160.8151379 Ω、circuit≈80.4075690 Ω。
保存場を固有値再計算なしで読み、GUIのRF9量と相対1e-12で一致、エネルギー分配と二つのR/Q定義も確認した。
周波数・RFの離散化誤差や表面ピーク収束の新しい保証ではない。

新ブラウザー検証後の製品変更は列幅CSSだけ。独立検証はその差分パスを明示し、Python/JS/HTMLの一致を要求する。
最終CSSの目視と従来操作は別のブラウザー検証で確認した。
独立検証中は993ソース系ファイル、ブラウザー文書と保存場が不変。
ブラウザーはいずれも外部HTTP要求0。初回/修正後の履歴画像を確認した。
新しい実FEMは小規模の2ジョブ。大規模例では固有値計算を行っていない。
全unit・seed・全validate・Hosted CI・サーバー再起動は実施していない。

再現コマンド（GUI URLは起動時のセッションURL、各out先は新規ディレクトリ）：

専用ブラウザー検証は、既存の合成半楕円にmarked(0)→uniform→marked(20)を付けた入力を使う。
入力は次のように新規出力先へ再作成できる。

```sh
PYTHONPATH=src:tests .venv/bin/python - <<'PY_INPUT'
from dataclasses import replace
from pathlib import Path
import json
from test_curved_reflection import half_case
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
out = Path('out/insertion-input')
out.mkdir(parents=True, exist_ok=False)
case = replace(half_case('z_min', 'electric_symmetry'),
    curved_refinement_steps=(Step('marked', (0,), 5.), Step('uniform'), Step('marked', (20,), 5.)))
(out / 'case.json').write_text(json.dumps(case.to_dict(), indent=2))
PY_INPUT
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest test_gui_curved_mesh_selection
node scripts/verify_gui_curved_history_insertion.mjs --url '<GUI URL>' --out '<browser out>' --case out/insertion-input/case.json
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_curved_history_insertion.py --case out/insertion-input/case.json --browser-directory '<browser out>' --saved-solution '<GUI job>/solution' --out '<native out>'
```

証拠索引は `out/curved-history-insertion-20260914/acceptance.json`。
新規外部資料・依存・旧資産の参照はない。親33課題の8受入/17進行/7他未受入/1範囲外は変えず、全計画goalを継続する。

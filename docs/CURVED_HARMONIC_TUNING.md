# 曲線寸法の法則による周波数調整 — D02版5

2026-09-14。非アフィンな曲線寸法の変更を、既存の二分探索・個別モード追跡・保存再開へ接続する。
元の[調和変位Study](CURVED_HARMONIC_STUDY.md)の幾何契約を使い、各試行を元Projectから作る。
FEM・求積・RF規約・探索判断は変更しない。D02親課題全体と全計画は未完。

受入条件は、独立した幾何積分と単位換算、元の固定細分履歴の保持、実FEMと実試行形状間の追跡、
正しい採用親からの最終細分、無効な内部試行での先行保存保持、厳密な再生と改変拒否、CLI/worker/GUIでの利用。

## 入力と数学

`schema_version: 5`を使う。共通のbounds/target_hz/二つの周波数許容差/探索幅/予算/初期ID/対象IDは
[TUNING.md](TUNING.md)と同じ。版1〜4の入力を変更しない。

| 項目 | 契約 |
|---|---|
| project | direct・非組立・非鏡映のnative曲線P2、軸接続の真空閉PEC/axis TM。markedは全て固定split_patternを要求 |
| parameter / parameter_unit | 空でない名前、`m`または`1` |
| geometry_coefficients | `/curves/<正規の番号>/<既存数値項目>`から、定数項から昇順の有限多項式係数列への辞書 |
| rf_coordinates | `fixed`または`axis_fraction`を明示 |
| minimum_corner_angle_deg | 有限で0より大きく60未満。変形後の写像頂点の接線間角度を検査 |
| controls | `mapping: piecewise_remesh`と既存の標本・重なり・割当・クラスタ・階数条件。`comparison_meshes`の入力は禁止 |
| refinement_scale | 2以上の2の累乗。二次幾何を制限して最終細分する |

法則の対象は既存primitiveのstart/end/center座標、semiaxes、rotation/start/sweep角、start/end parameter。
曲線の種類・数・順序・双曲線の枝、境界タグ、弦分割・品質予算・材料・ソルバーは変更できない。
全法則を同時に適用して形状を検査する。係数cₖの単位は対象項目の単位/(設計変数の単位)ᵏ。
少なくとも一つの非定数係数が必要で、両端が同じ表現可能な形状になる法則も拒否する。

境界をcurve番号/分率で対応させ、元の弦メッシュ内部にはP1調和変位を解く。
各変形後の二次写像Fから`F_current ∘ inverse(F_parent)`の比較を定義する。
元メッシュ番号・固定marked分割・後続uniform/marked履歴を保持する。これは境界分割を変える再メッシュではない。

探索時の比較メッシュは実際の各試行の元弦メッシュと元Projectの全履歴から導出する。
最終試行では採用した親と同じ形状を再構成し、`log2(refinement_scale)`回のuniform制限を追加する。
比較用には両側とも元Projectの履歴を使うため、同じ二次領域を覆う対応分割になる。
粗い場と細かい場は各々の実際のFEM空間から評価する。FEMの最終要素数と比較要素数は別に保存される。
採用親が最初の端点である場合も、その親番号を使う。直前の試行を代用しない。

両端形状・細分設定は出力先を作る前に検査する。区間内部の全形状や根の一意性・単調性は保証しない。
内部で形状/写像が無効なら失敗記録を保存し、直前の検証済みcheckpointを保持する。
追跡が個別IDを解決しなければUNVERIFIEDで停止する。目標差と粗細周波数差は独立のゲートで、離散化誤差上界ではない。

## 使用

再現入力は[examples/tuning/curved_harmonic.json](../examples/tuning/curved_harmonic.json)。
二つの半楕円から作る合成形状であり、実測構造ではない。中心・左右の軸方向半径・共通半径を連動させる。
元Projectはmarked→uniform→markedの固定履歴と26要素の明示元メッシュを含む。
目標1525146908.755006 Hzはx=0.5の予備FEMから選んだ操作例であり、独立な精度参照値ではない。

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng tune examples/tuning/curved_harmonic.json --out out/harmonic-tune-first --max-new-trials 2
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng resume-tune out/harmonic-tune-first/checkpoint-002.json --out out/harmonic-tune-rest
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng replay-tune out/harmonic-tune-rest/checkpoint-004.json
```

出力先は新規のものを指定する。元入力、実試行Project、native解、追跡写像、親番号、判断を再生する。
checkpoint外側は従来の版1。要求の版5と派生比較メッシュの版2を内包する。

GUIは「曲線寸法の変更（調和変位）」を選び、現在の曲線から数値項目のひな形を作れる。
ひな形の定数だけでは変形しないため、必要な項目へ非定数係数を追加する。
入力生成中の形状・調整設定変更を検出して古い結果の反映を拒否する。
法則と調整入力を元JSON文字列のままサーバーへ渡し、重複キーを開始前に拒否する。
既存の辞書形式GUI APIも受理する。保存読込・再開時には版5の法則・単位・RF方針・角度を復元する。

## 検証範囲と来歴

独立検査2件は実装前に版5/API不在で失敗し、実装後15.796秒で合格。
最終関連35unitは309.382秒で合格。新6件と、curved_tuning/tuning/coupled_tuning/polynomial_tuning/gui_tuningを含む。
直接利用先tuning_jobsの7件も7.212秒で合格し、合計42件を二つの実行で確認した。
幾何は非線形法則のGreen面積/回転体積・m換算・最終領域不変、実FEMは端点採用親・保存再開・改変拒否を検査する。
既存版1〜4、失敗保持、CLI/JobManager/GUI transportも対象とした。

専用検証器は`scripts/validate_curved_harmonic_tuning.py`、ブラウザー検証器は
`scripts/verify_gui_curved_harmonic_tuning.mjs`。実行記録は`out/curved-harmonic-tuning-20260914/`。
Chrome新版12項目・旧版1の7項目は合格。新4/旧17試行の実worker、保存再開、正確なダウンロード/再生、改変拒否、対象場を確認。
新版には法則のひな形・元Project/固定履歴/全入力の一致、重複キー拒否、入力編集中の古い応答拒否も含む。
両経路の画像を目視し、外部HTTPは0。全3ブラウザー実行の製品323ファイルSHAは最終実装と一致する。
初回新版は3項目成功後に検証器の待機不足でFAIL。待機条件が埋込みProjectのsemiaxesまで数え、直前の重複入力を誤って準備完了とした。
元入力との差を捕捉する時点がずれていたため、期待するgeometry_coefficients辞書との一致を待つよう検証器だけ補修した。製品/数値許容差は不変。
初期失敗はbrowser-new、最終新版はbrowser-corrected、旧版はbrowser-oldに保持する。
GUI全workerはcomplete、専用serverのargvを照合してSIGINTで終了0。新規/旧版ブラウザーも終了0。
CLI/GUI全4試行の保存係数・固有値・二次幾何/接続配列は完全一致、Case/元メッシュ/RFの数値も一致した（32保存ファイル不変、0.028秒、新FEMなし）。
最初の全results.json一致検査はcase_sha256の違いで失敗した。GUI入力で0.0/1.0等が0/1になり、数値が同じでも原JSONのhashが変わるためである。
補修した確認は各側のCase hashをその原JSONで個別に検証してから、残りの全数値を比較した。製品の完全再生やhash照合は緩和しない。
専用数値は18新FEM、758.895秒でPASS。初期基準・m表現・寸法2倍の3系列は各4試行、146/146/146/584要素でTUNED。
値は0→1→0.5→0.5（m表現は1/10）、最小追跡重なり0.997724。独立Greenの面積倍率1+x/8・体積倍率(1+x/8)²と最終領域不変を確認。
両R/Q・G・TTFと周波数の単位/Maxwell相似差は最大2.221e-14、各要素2点のHφ/Er/Ezは最大2.774e-14。
別の円筒4試行ではTM011の順位3→2を追跡し、Bessel解析周波数との差は最大2.176e-5、最終1.322e-6。
無効内部形状の端点2FEM後、負の半径になる中間値で失敗し、failure-003だけを追加して先行checkpointの完全再生を確認した。
例の目標を選んだ予備1FEMは18に含めない。検証中は1055ソース系SHAが不変。以後の差はブラウザー検証器の待機条件1箇所のみ。
数値は[benchmark](../benchmarks/tuning/curved-harmonic-20260914.json)、全証拠索引はout/curved-harmonic-tuning-20260914/acceptance.json。
全suite/seed/Hosted CI/新Wine比較は今回実行していない。並行検証の時間を単独性能とは解釈しない。

既存の調和変位、固定二次制限、可変物理体積での標本追跡とGreen/Maxwell/Bessel解析を再利用した。
新しい外部資料・依存や旧資産の参照はない。一般関数、任意の境界分割変更、他物理のtune、
全連続経路の物理的同一枝や一般制約付き探索はこの受入に含めない。

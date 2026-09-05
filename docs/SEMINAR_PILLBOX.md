# Pillbox演習の実装・検証 — 2026-09-05

指定資料の全領域pillboxについて、TM010/TM011の計算、長さ掃引、電磁場の図、
電界矢印、軸上・半径方向プローブ、結果を選ぶHTMLページを追加した。
半領域の電気／磁気対称境界は次の作業で、S1全体とセミナーマイルストーン全体は未完了。

## 使用方法

```bash
source .venv/bin/activate
superfish-ng solve examples/seminar_pillbox.json --out out/pillbox-exercise-new
superfish-ng plot out/pillbox-exercise-new --mode 2 --probe-z-m 0.02 --out out/tm011-new.png

# 長さ40/80/120 mm、各3メッシュ、解析照合、全6枚のモード図とHTML
OPENBLAS_NUM_THREADS=1 python scripts/seminar_pillbox.py --out out/seminar-new

# 同じ演習にWine AUTOFISH + SF7による独立照合を追加
OPENBLAS_NUM_THREADS=1 python scripts/seminar_pillbox.py --run-legacy --out out/seminar-wine-new
```

Matplotlibが必要なので未導入環境では `python -m pip install -e '.[plot]'` を実行する。
`scripts/plot_results.py` も同じ `--mode`、`--probe-z-m`、`--mesh` を受け付ける。
コマンドは新規の出力パスを要求する。`index.html` は生成後にブラウザーで開けるローカルファイル。
HTMLには長さ・モードの選択、図、RF量、軸上・半径方向CSV、結果JSONへのリンクを含む。
一般的なケース編集画面はまだなく、再計算はJSON入力とCLIで行う。

今回の成果物は `out/seminar-pillbox-ready-20260905/index.html`。
その `comparison.json` に全解析値、誤差、メッシュ変化、ソースhash、参照出力hashを保存した。
Wine生出力は `out/seminar-pillbox-signed-20260905/wine/` にある。

再計算なしに済むWine参照は、以下のように使える。

```bash
OPENBLAS_NUM_THREADS=1 python scripts/seminar_pillbox.py \
  --reference-run out/seminar-pillbox-signed-20260905 \
  --out out/seminar-reference-reuse-new
```

参照入力AF/SEGの全バイトとSFO/SF7のSHA-256を検査する。NG計算はその都度実行し、
参照データからNGの値を生成したり補正したりしない。

## モードを周波数順位だけで決めない

半径は75 mm、導電率はSUPERFISHと同じ約5.8001276e7 S/m、β=1、U=1 J。
TM01pの解析場 `u ∝ J1(χ01 r/R)/r × cos(pπz/L)` とFEM固有場の質量内積による重なりを用い、
一致度0.99以上のモードを選ぶ。軸上ではBessel関数の極限を使用する。

| 空洞長 | TM010 [MHz] | TM011 [MHz] | TM011の周波数順位 |
|---|---:|---:|---:|
| 40 mm | 1529.901098 | 4048.332314 | 3 |
| 80 mm | 1529.901098 | 2419.062731 | 2 |
| 120 mm | 1529.901098 | 1975.117890 | 2 |

40 mmではTM020がTM011より低くなる。2番目を常にTM011と扱うと誤った長さ依存を示すため、
この順序変更は回帰テストでも確認している。

## 独立したTM011参照計算

`analytic.pillbox_tm_mode` に、TM0npのHφと軸方向cos場から得た蓄積エネルギー・
両端板を含む壁損失・複素加速電圧・2種類のR/Qを追加した。
軸方向cos²の平均はp=0では1、p>0では1/2となる。
TM011のエネルギー、境界損失、位相付き電圧を別の数値積分で検査した。
従来の `pillbox_tm010` とp=0の値も一致する。

長さ40/80/120 mmのそれぞれを `nr=24/48/96` で独立に解いた。
最細メッシュでは全ケースの周波数誤差が0.1%以内、Q0/G/RQ/P/TTF誤差が1%以内、
最終2メッシュ間の変化も同じ閾値以内で合格した。固有値残差は別項目として保持する。

## Wine版とのTM010/TM011照合

L=80 mmについてWine側も `dx=0.2/0.1/0.05 cm` の3段階で実行した。
最細メッシュ比較の相対差は `abs(NG / SUPERFISH - 1)`。

| モード | Wine周波数 [MHz] | NG周波数 [MHz] | 周波数差 | R/Q差 | 軸上Ez L2差 |
|---|---:|---:|---:|---:|---:|
| TM010 | 1529.899420 | 1529.901098 | 0.000110% | 0.01293% | 0.00694% |
| TM011 | 2418.972210 | 2419.062731 | 0.003742% | 0.01577% | 0.03131% |

Q0/G/P/TTFおよびWine側の最終2メッシュ差のゲートも合格。
電圧と壁損失を含む振幅依存量は両コードともU=1 Jへ揃え、ネイティブなWine側のUも別名で記録する。

今回の照合で、**SFOの軸上Ez表は符号反転後も正の値を表示する**ことを確認した。
この表の直接積分はTM011で誤ったR/Qと約141%の場の差を生じた。
値の符号を推測で補うことはせず、SF7の800区間の補間を実行して符号付きEzを取得した。
`OUTSF7.TXT` のcm/MV m⁻¹/A m⁻¹をSIへ変換し、符号を保持したまま独立に積分することで上表の一致を得た。
従来のSFO専用比較は符号が変わらない基本モードに限定することを明示した。

## 可視化と動作確認の範囲

`FieldSampler` は保存した三角形の重心探索と面積座標でP1場を評価し、候補で見つからない場合も
全候補の境界箱を調べる。領域外は明示的なエラー、図用のグリッドではNaNとして除外する。
Er/Ezは要素内の片側微分を用い、見た目の平滑化を数値へ混ぜない。Eの向きとHのピークは同時刻の場ではない。

39件のunittestと `scripts/validate.py` が合格。
TM011の場の反転、電界矢印、磁場、半径方向曲線、図の軸と凡例を生成PNGで確認した。
図の微小な鋸歯状の変化はP1微分が要素間で不連続であるためで、精度向上の代わりに隠していない。
HTMLの6選択肢と画像・CSV・JSONの全27リンクの実在を確認した。ブラウザー上での選択操作はまだ未確認。
Computer Use用Orca CLIが `bad option: --no-sandbox` で起動できず、デスクトップ操作による確認は行えていない。

次は全領域解との照合を伴う半領域の電気／磁気対称境界、その後4セルflat-noseの垂直段差メッシュへ進む。

既存seedの周波数・Q0・R/Qとの差は円筒・非円筒とも最大9.33e-15で、浮動小数点丸めの水準を維持した。

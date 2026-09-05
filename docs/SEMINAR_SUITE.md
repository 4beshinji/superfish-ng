# セミナー全例題の一括実行

`scripts/seminar_suite.py` はS1〜S6の対象を新しい出力先へ順番に計算し、例題選択の入口HTMLを生成する。
現時点では初回一括検証を実行中で、完了・全ゲート合格はまだ主張しない。

## この環境のWine参照を使った再現コマンド

```bash
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/superfish-matplotlib \
  .venv/bin/python scripts/seminar_suite.py \
  --out out/seminar-suite-new \
  --pillbox-reference-run out/seminar-pillbox-ready-20260905 \
  --flat-reference-run out/seminar-flat-ready-20260905 \
  --rounded-reference-root out/seminar-rounded-wine-20260905
```

各NG例題は新規に解く。`--native-runs` や `--native-roots` は一括実行では使用しない。
保存Wine参照はAF/SEGを同じ入力から再生成して全バイト検査し、生SFOと符号付きSF7の電場を読み直す。
旧ソルバー内部・コードは参照せず、参照出力や実行形式をソースZIPへ含めない。
既設Wineを使い、参照も新規計算する場合は参照3引数を省略して `--run-legacy` を指定する。
両コードの細分・全モードを計算するため、数分で終わるスモークテストではない。

進行中の円弧Wine出力を待つ場合のみ `--reference-wait-seconds 14400` などを明示する。
読取専用で必要ファイルの非空・サイズと更新日時の安定を待ち、その後に内容・入力・モードを通常通り検査する。
ファイルの存在だけを数値合格にはしない。途中成果物や期限切れは照合時に失敗し得る。

## 対象と設定

| ジョブ | 内容 |
|---|---|
| validation | unittest、seedの解析・RF・収束回帰 |
| pillbox | 半径75 mm、長さ40/80/120 mm、TM010/TM011、解析とWine比較 |
| symmetry | 両側の電気/磁気対称条件、半領域・全空洞鏡映、解析・独立全領域FEM・Wine参照 |
| flat4 | 平坦4セル、NG nr=128/256/512、Wine dx=0.05/0.025/0.0125/0.01 cm |
| rounded4 | 円弧4セル、NG nr=32/64/128、弦誤差3 µm、Wine3段階 |
| end_cells | flat/roundedのhalf/full端部各4モード、交差分割64/128/256、flat/halfに384を追加 |
| geometry4 | 固定nr=128、円弧弦誤差12/3/0.75 µm |
| geometry7 | 固定nr=128・交差分割、7セルの円弧弦誤差3/0.75/0.1875 µm |
| rounded7 | 交差分割64/128/256、弦誤差0.75 µm、Wine3段階 |

7セルの弦誤差は `--rounded7-chord-m` で指定でき、形状試験もその4倍・1倍・1/4倍に連動する。
既存の3 µm設定でもNG内部細分の合格を確認済みだが、一括の既定値はより細かい0.75 µm。
周波数0.1%、RF量1%、軸場相対L2 1%を維持し、最後の2段階の変化も独立に評価する。
角部ピークの精度保証、端部full-cellのWine照合、一般的なモード交差追跡はこの一括検証に含めない。

## 表示・保存・合否

完了後に出力先の `index.html` を開く。6種類の例題ページへ移動し、モードを選んで場・軸上/半径方向CSVを確認する。
PNGは計算した場の可視化で、図中の単位・正規化を維持する。数値CSVを変えず、比較図だけで符号や軸長を正規化する場合は明記する。
寸法を変える場合は入力JSONを複製して編集し、必ず新しい出力先へ再計算する。メッシュ表示は以下で追加できる。

```bash
superfish-ng plot out/my-run --mode 1 --mesh --out out/my-run-mesh.png
```

- `suite.json`: 進行中はpassed=false。最後に全数値・全7ページの画面検査・実行中ソース不変を合わせた判定。
- `numerical.json`: 全数値ジョブ終了時の不変スナップショット。画面検査の完了判定は含まない。
- 各例題の `comparison.json`: 入力、参照hash、環境、差、同定と細分の各ゲート。
- `JOB.log`: 実行ログ。数値レポートが生成できなかったジョブもFAILとして残す。
- `browser/NAME/verification.json`: 独立したheadless操作・画像・リンク検査。`symmetry` は選択UIがないため静的ページ検査。

Node 22と既設Chromeが画面検査に必要。通常の計算ソルバーへの依存ではない。
`--native-only` または `--skip-browser` を指定すれば該当処理を省略できるが、全マイルストーンの合格にはならない。
失敗したジョブがあっても可能な独立ジョブは続行し、FAIL/INCOMPLETEを入口ページへ表示する。
Wineの出力が未完了、ゲート未達、ブラウザー不在、実行中のソース変更も完了にしない。

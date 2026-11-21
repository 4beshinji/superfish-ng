# セミナーレポート可視化追補版

[実験別索引](index.html)。原本2冊は変更せず、場22図/冊を実験節へ再配置し、保存CSV/JSONから13図を追加した。図の出典とSHA-256はmanifest.json。PNGとSVGは同じデータから生成する。新しい外部資料・依存はない。

周波数・RF・場・細分差の意味を分け、未実施の測定値は補わない。鏡映量の比、相対差の百分率換算、各細分系列の最終保存値を基準とする差だけを後処理する。ソルバー・許容差・元の判定・数値出力は変更していない。

再生成（NumPy/Matplotlibのある環境、出力先は未作成のディレクトリ）:
```sh
.venv/bin/python scripts/build_seminar_visualizations.py seminar-reports-20260910 --out seminar-reports-20260910/NEW_VISUAL_EDITION
```
PDFは生成HTMLをChromeの印刷でA4出力する。既存PDFは原版として保持。

検証：HTML各42画像・251リンク・67元ファイルhashが一致。PDF本家49頁、NG39頁。標準テストは子プロセスimport環境不備により中断。PYTHONPATHを明示した該当2workerテストは90.130秒で合格。ログはlogs/。

# Superfish-ng 計算レポート

[HTMLレポート](report.html) / [PDFレポート](report.pdf)

入力と中間出力はraw、結果表はresults、図はfigures、実行ログはlogsにコピーしました。

`python reproduce.py --list`で追試験入力を一覧できます。`--input`と新しい`--out`を指定してください。本家は`--wine-prefix`、NGの未インストール環境は`--project-root`で既存のソルバーを指定します。元の出力フォルダへのアクセスは不要です。

raw内の絶対パスは実行来歴として保持し、portable-paths.jsonで同梱ファイルと対応づけています。

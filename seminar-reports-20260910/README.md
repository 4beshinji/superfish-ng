# セミナー計算レポート

[入口・全体索引](index.html) ／ [実験別の可視化追補版](05-visualizations/index.html)

- [01-superfish](01-superfish/files.html)：本家Superfishの入力・出力・HTML/PDF・図・ログ
- [02-superfish-ng](02-superfish-ng/files.html)：Superfish-ngの入力・出力・HTML/PDF・図・ログ
- [03-audit](03-audit/files.html)：解析・検証・整理明細
- [04-history](04-history/files.html)：正本と重複しない試行・失敗・作業スクリプト

各冊の inputs.html が入力と対応出力の索引、files.html が全ファイル索引です。追試験には各冊の reproduce.py を使います。

旧作業フォルダは正本とのSHA-256一致を確認して重複を削除し、固有記録を改名・集約しました。旧→新パスは [整理明細](03-audit/organization.json) に記録しています。rawの絶対パスは実行来歴のため書き換えていません。

既存チェックサムとSF7ログ1件の差を整理前に検出し、元の記録と両ハッシュを監査に保存しました。数値計算は再実行していません。

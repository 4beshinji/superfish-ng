# 3386a5fのローカル配布確認

2026-09-09、V02のうちローカルLinuxでの内容・起動確認。公開リリースの受入ではない。
perf/curved-edge-search の3386a5fを、実行中の本体と別のworktreeから梱包した。
後から追加した本記録自体は、このソースZIPの対象コミットに含めない。

scripts/package.pyで2回生成したZIPはバイト完全一致。
474項目（473ファイルとSHA-256一覧）の全ハッシュを検査し、
.git/.venv/out/キャッシュ/既存外部資産を含まないことを確認した。
ZIPのSHA-256は e24513a5b00a69c36b8cece59a8c41ec66ea957cb208001c6131ed0c4b43d6c4。
同一バイトと使用中zlibでの観測であり、異なる圧縮器までの再現性は主張しない。

ZIPを/tmpへ展開し、そのコピーからwheelを作成した。検証中ソースへビルド生成物を作らない。
計算用.venvにはpip/setuptoolsがなかった。システムpipはvirtualenv必須設定で拒否したため、
システムの既存ビルドツールを参照する専用venvを作成した。初回ログも保持。
--no-deps --no-build-isolation --no-index でwheelを構築し、依存の取得は行っていない。
wheelは superfish_ng-0.1.0-py3-none-any.whl、SHA-256は
175a9de35437e530db0403f26c1711960096015f037dce7c60c7491a220712cf。
wheelの再現ビルドは今回の検査範囲に含めない。

wheelのRECORDの全ハッシュ・サイズと、元ソースにある111コード/HTML/CSS/JSファイルの
完全一致、LICENSE/NOTICEを確認した。NumPy/SciPy等はwheelに同梱していない。
--targetの専用ディレクトリへwheelを展開インストールし、-I起動でそのパスだけを明示追加した。
計算には既存NumPy/SciPy環境を使用し、全superfish_ngモジュールの読込元がwheel側であることを確認。
CLI --helpが終了0。球形の曲線P2を実計算し、native保存・再読込が成功した。
ソース版の初期球形対照とのf/RQ/G差は全てゼロ。依存を再導入したクリーン環境の検査ではない。

記録・2つのZIP・wheel・ログは本体の out/curved-edge-distribution-20260909 に保存。
ビルドと実行の専用環境は /tmp/curved-edge-distribution-20260909 に保持している。
保存したsmoke.pyはその実行時パスと既存数値対照を使用する観測スクリプトである。
この部分確認は、wheel上の全機能・全GUI操作、別OS、ユーザー操作評価、hosted CI、
公開リリースの受入を代替しない。V02親課題は引き続き未受入。

# 比較用Wine環境の永続化 — 2026-09-14

ユーザーの指示により、C00/K02・C02の旧曲線入力照合に必要なWine環境を
`/home/sin/.local/share/superfish-reference/` に作成した。
旧 `/tmp/superfish-wine-runtime` は存在しない。再起動による消失は可能性であり、原因は未確定。

今回の受入範囲は、永続領域の専用Wine、起動ラッパー、Windowsコマンドの実行、
Wine再起動後のファイル・レジストリ保存である。この範囲は **PASS**。
SUPERFISH本体とSFCODES.DOCの復元は、自動承認レビューの拒否により未完了。

| 用途 | 保存先（上記ルートからの相対パス） |
|---|---|
| Wine本体・依存・Xvfb・antiword | `runtime/` |
| 専用32-bit Windows環境 | `prefix/` |
| 通常起動 | `bin/wine-superfish` または `wine-local.sh` |
| 仮想画面付き起動 | `bin/wine-superfish-headless` |
| 再構築用Ubuntu公式deb | `downloads/` |
| パッケージhash・実行検証 | `manifests/ubuntu-packages.json`、`manifests/acceptance.json` |
| 構築・失敗・診断記録 | `logs/` |
| 入力仕様文書の保存予定先 | `input-spec/`（文書は未復元） |

```sh
/home/sin/.local/share/superfish-reference/bin/wine-superfish --version
/home/sin/.local/share/superfish-reference/bin/wine-superfish-headless cmd.exe /c ver
```

WineはUbuntu公式 `9.0~repack-4build3`。前回の一時環境構築記録
（PROVENANCE.mdの2026-09-06記録）に合わせた。WineHQ索引も調べたが、そのパッケージは採用していない。
全38パッケージをローカル展開し、システムパッケージや他アプリのWine prefixは変更していない。
ホストの既存共有ライブラリにも依存する。詳細な起動・再構築手順は永続ルートの `README.md`。
初期化時のzlib不足は、Ubuntu公式MinGW zlib DLLの配置で解消した。
失敗prefixを別名で保存し、正常prefixと区別する。

`out/wine-persistent-20260914/verify-runtime.py` はWine 9.0の表示、`cmd.exe /c ver`、
ファイルとレジストリの書込を確認し、専用wineserver終了後に別起動して両方の保存値を照合した。
全6コマンドが終了0。headlessラッパーはWine終了までXvfbを維持し、実行終了後に閉じる。
実機の再起動試験はしていない。永続ルート、runtime、prefix、ラッパーの実体が `/tmp` 外にあることも確認した。
FEMや製品コードの変更はなく、unittest・全数値検証・GUI検証を追加実行していない。

元のローカルアーカイブは
`/home/sin/code/agent/reserch/particle_accelerator/SUPERFISH.zip`。
中に `SUPERFISH/PoissonSuperfish_7.20.exe` があることをZIPのファイル名一覧で確認した。
インストーラー名から実行版7.17や文書版を確定していない。

自動承認レビューは、AGENTS.mdの旧バイナリ取り扱い制限を理由に、
インストーラーを専用永続領域へコピーする操作を拒否した。
AGENTS.mdの「in this implementation repository」という適用範囲と今回のユーザー指示を
再提示したが、リポジトリ外へのコピーも許可できないとの理由で再審査も拒否された。
コピー・代替経路による導入は実行しておらず、明示的な例外許可が必要な残件として保持する。
旧ソルバーのソース・実行形式内部は閲覧せず、再配布もしていない。

許可後は既存インストーラーをこの永続領域へ導入し、付属文書のhash・改訂情報を記録し、
合成入力の実出力で対象版を再確認する。そこまで完了する前にC00の参照環境復元済みとは扱わない。

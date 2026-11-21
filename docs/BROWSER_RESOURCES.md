# GUI 検証のブラウザー資源管理

DEV-BROWSER-01、2026-09-29。対象は Linux 上の検証用 Chrome 起動・停止・一時領域。

## 原因と変更

62 本の GUI 検証器が `mkdtemp("/tmp/ng-gui-chrome-")` と Chrome 起動を複製し、
終了時にプロファイルを削除していなかった。レポート保存失敗や、`try` より前の
`sourceHashes()` の例外では停止処理にも到達しなかった。ギャラリー検証器にも
保存失敗・親強制終了で後処理を飛ばす経路があった。

全 63 本を [`scripts/browser-session.mjs`](../scripts/browser-session.mjs) に接続した。
呼び出し側は `{ profile, browser, dispose } = await launchBrowser()` を使い、
レポート保存を囲む `finally` で `dispose()` を待つ。`browser` は Chrome を管理する
子 Node プロセスで、Chrome の stderr を転送する。検証本体・数値判定は共通化の対象外。

管理プロセスは親との IPC 切断も検出するため、親の未捕捉例外・SIGKILL 時にも
Chrome、同じプロセスグループの子、専用 config を参照する crashpad を回収する。
通常の終了要求で止まらないプロセスには猶予後に SIGKILL を送る。
プロファイル・XDG cache/config・TMPDIR は実行ごとの所有ディレクトリーに収め、
生存プロセスがなくなったことを確認して削除する。回収失敗は非ゼロ終了になる。

## 固定上限と回復

| 項目 | 既定値 / 動作 |
|---|---|
| 一時領域 | `/tmp/superfish-ng-browser-<uid>/slot-0` または `slot-1`、所有ユーザーのみアクセス可能 |
| 並列数 | 同一ユーザーで 2 実行。3 件目は待ち行列を作らず失敗する |
| 実行時間 | 30 分でブラウザーを停止し、検証側も終了 124 |
| 一時領域の実使用量 | 1 実行 512 MiB を 5 秒ごとに監視。超過時は停止・回収して失敗 |
| 空き容量 | 起動前に 1 GiB 以上を要求 |
| Chrome キャッシュ指定 | disk 32 MiB / media 16 MiB |
| stderr | 保持は末尾 65,536 文字。転送にもストリームの流量制御を適用 |
| 終了猶予 | TERM 5 秒、続いて KILL 5 秒。呼び出し側の回収待ちも 15 秒で打ち切り |

512 MiB は監視による停止条件であり、ファイルシステムのハードクォータではない。
監視間隔中の書き込みは上限を超え得る。画像・レポート・計算結果など明示した
`--out` の成果物はこの一時領域とは別であり、利用者の保存物として残る。

各枠には管理プロセスと Chrome の PID・Linux の開始時刻を記録する。
次回起動時は、既知の所有者が死んでおり、対応するブラウザーや子も生存しない枠だけを回収する。
PID の再利用を生存証拠と取り違えない。所有記録不明、起動途中、symlink、生存中の枠は
保持して並列枠に数える。管理プロセス自体が SIGKILL され、Chrome が生存する場合も同様。
両枠が残って起動できない場合は `owner.json` と対応するプロセスを確認して扱う。
経過時間だけを根拠に領域を削除する処理はない。

固定された空の親ディレクトリーは残るが、正常回収後の slot・キャッシュは残らない。
テストの `stateRoot` と小さい `limits` は隔離・時間短縮用。製品検証器は既定値を使う。
新しい検証器もこの入口を使い、独自の `spawn` / `mkdtemp` を追加しない。

## 対象検査

Linux、Node.js 22 以降、Python 3.12、実ブラウザー検証には既存 Chrome を使用する。
新規 npm/Python 依存は不要。

```sh
uv run --no-project --python 3.12 python -m unittest discover -s tests -p test_browser_session.py -v
```

15 件で、繰り返し正常終了、保存失敗、`try` 前の例外、起動失敗、予期しない終了、
SIGTERM / 親 SIGKILL、終了しない子、時間・容量上限、同時起動の枠制限と再利用、
PID 再利用、所有者不明・symlink・生存ブラウザーの保護を確認する。
63 本すべての `node --check` と共通入口の使用も含む。

実 Chrome の代表確認は既存の GUI サーバーに対して次を実行する。
`LAUNCH_URL` はサーバーが表示するセッショントークン付き URL、出力先は未作成のディレクトリー。

```sh
node scripts/verify_gui.mjs --url LAUNCH_URL --out NEW_DIRECTORY --io yes
node scripts/verify_gallery.mjs --html LOCAL_STATIC_HTML --out ANOTHER_NEW_DIRECTORY --mode static
```

## 今回の証拠と範囲

ローカル証拠は `out/browser-lifecycle-20260929-1790636424476937451/` に保存した。
`acceptance.json`、`unit.log`、`before.json`、`gui/report.json`、
`static-gallery/verification.json`、スクリーンショットと再現用 `verify_real.py` を含む。

- 修正前：空の作業ディレクトリーから既存検証器を起動すると source hash 読み込みが
  ENOENT / 終了 1 となり、プロファイルが 1 個残った。再現資源は回収した。
- 修正後：同じ例外、実 Chrome 起動後の親 SIGKILL とも所有領域を回収。
  SIGKILL 前には Chrome 関連 9 プロセスを観測し、回収後は残存 0。
- 対象 unittest 15 件 PASS、3.971 秒。63 本の検証本体が変更前と同一であることも差分比較で確認。
- 実 GUI 7 項目 PASS：入力・求解・不正値拒否、Project/Case 保存と再読込、
  probe/画像/解析比較の保存、Study 定義往復、再読込と認証拒否。
  外部要求 0、実行中の製品ソース変更なし。
- 静的ギャラリー 1 ページ PASS。全検証終了後は slot 0、所有プロセス 0、GUI サーバー終了 0。
  旧 `/tmp/ng-gui-chrome-*` の増加なし。
- 実行環境：Node 24.18.0、Chrome 153.0.8010.36、既存 uv 環境の Python 3.12.3。
  NumPy 2.5.2 / SciPy 1.18.1 / Matplotlib 3.11.1。依存の追加・更新なし。

製品の `src/`・物理許容値は変更していない。全物理 suite・63 経路すべての実ブラウザー再生・
別 OS の保証は今回の検証範囲に含まない。

## 出典

自作の Node 標準 API による資源管理。API の意味は Node 公式の
[child_process](https://nodejs.org/api/child_process.html) と
[fs](https://nodejs.org/docs/latest-v24.x/api/fs.html) を参照した。
外部実装コード・legacy コードの参照や依存追加はない。

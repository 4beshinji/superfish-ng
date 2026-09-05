# 生成HTMLのheadless統合テスト

2026-09-05。ブラウザーの実際のキー入力、画像デコード、表示セクション、データリンクを検証した。
従来の静的なリンク監査だけの状態から進めた。ユーザーの既存デスクトップセッションは操作していない。

```bash
node scripts/verify_gallery.mjs \
  --html out/seminar-rounded4-native-20260905/index.html \
  --out out/browser-check-new
```

既設Node 22とChromeを使用する。今回の実測はNode v22.22.1、Chrome/151.0.7922.137。
新しいnpmパッケージやPythonのWeb依存は不要。`--chrome` で検証用実行形式を明示できる。
選択UIを持たないページには `--mode static` を使い、キーボード選択を検査したとは記録しない。
計算・PNG・HTML生成にはこれらの検証ツールを要求しない。

一時プロファイルを作り、headless Chromeへloopback上の一時DevTools接続を開く。
ページの外部HTTP/HTTPSリクエストは遮断する。リンク先はHTML結果ディレクトリ内のローカルファイルに限定する。
テスト後はそのChromeだけを終了し、そのテストが作成した一時プロファイルだけを削除する。
既存のChromeプロファイル・ログイン状態・ウィンドウは利用しない。

実行手順はChromeの公式headless文書と公開DevToolsプロトコルのAPI定義を参照して新規実装した。
[Chrome Headless](https://developer.chrome.com/docs/automation-and-testing/headless)、
[Target domain](https://chromedevtools.github.io/devtools-protocol/tot/Target/)、
[Runtime domain](https://chromedevtools.github.io/devtools-protocol/tot/Runtime/)。

## 検査内容とエビデンス

- 全画像を実際にデコードし、表示画像のnaturalWidth/Heightが正であることを確認。
- Home/ArrowDownキーで全選択肢へ移動し、選択値と唯一の表示セクションが一致することを確認。
- 全画像・データリンクの存在とSHA-256を保存。
- 最初と最後の選択状態をブラウザーのスクリーンショットとして保存。
- ブラウザー版、HTMLと検証スクリプトのhash、選択ごとの表示状態をverification.jsonへ保存。
- 意図的にchange handlerを欠いたfixtureがFAILになることも実行し、常に成功する検査でないことを確認。

| 画面 | 選択肢 | 画像・リンク | 実行記録 |
|---|---:|---:|---|
| Pillbox全領域 | 6 | 27 | `out/gallery-test-pillbox-final-20260905/verification.json` |
| 丸み付き4セル | 4 | 15 | `out/gallery-test-rounded4-final-20260905/verification.json` |
| 丸み付き7セル | 7 | 24 | `out/gallery-test-rounded7-final-20260905/verification.json` |
| 平坦4セル・最終Wine照合 | 4 | 16 | `out/gallery-test-flat-ready-20260905/verification.json` |
| 交差分割7セル・NG収束合格 | 7 | 24 | `out/gallery-test-rounded7-crossed-20260905/verification.json` |
| 丸み付き4セル・Wine照合合格 | 4 | 16 | `out/gallery-test-rounded4-wine-20260905/verification.json` |
| full/half端部比較 | 8 | 51 | `out/gallery-test-end-cells-ready-20260905/verification.json` |
| 対称境界の静的ページ | 選択操作なし | 21 | `out/gallery-test-symmetry-static-20260905/verification.json` |
| 故障fixture | 2 | 2 | `out/gallery-test-broken-fixture-20260905/verification.json`（期待通りFAIL） |

従来分割の7セル画面の数値FAILはそのまま保持され、交差分割の新しい7セル画面ではNG収束がPASSになった。
UIテストのPASSを数値精度やWine照合のPASSと混同しない。
静的ページ対応後も故障fixtureは期待通りFAIL（`out/gallery-test-broken-suite-20260905`）。
デスクトップのOrca CLIの起動問題を修正したわけではない。
ここで証明したのは生成HTMLのheadlessブラウザー上の操作と描画であり、OS固有のメニュー操作ではない。

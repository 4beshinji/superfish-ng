# 独立実装・情報来歴

## Pillbox演習の拡張 — 2026-09-05

TM0npの公開数学に基づく場からエネルギー・壁損失・電圧を導出し、独立積分で検査する解析参照を追加した。
計算ソルバーを補正・置換していない。可視化はNGの保存場を直接評価する。
WineのSF7を比較用に実行し、符号付きの電場出力を使用した。
実行方法は既存ExamplesのIN7とバッチの起動方法、SF.INIのSF7設定から確認した。
旧コードの内部アルゴリズム・ソースは参照していない。
SFOの絶対値表を高次モードへ適用した初回比較はFAILとして残し、SF7に基づく結果と混同しない。
実行記録と未完了項目は [SEMINAR_PILLBOX.md](SEMINAR_PILLBOX.md) を参照。

## Wine版との照合と演習マイルストーン — 2026-09-05追記

ユーザーからWineで動く本物のSUPERFISHとの照合を明示的に依頼された。
既設AUTOFISHをブラックボックスとして実行し、AF/SEGの入力規約とSFO数値出力を確認した。
旧ソルバーのソース・実行形式の内容の参照、翻訳、逆解析は行っていない。
入力はNGの幾何仕様から比較用に生成し、生の旧形式出力はGit対象外のout/に保管した。
照合に合わせてNGの導電率を揃えたが、FEM/RFの実装は変更していない。
追加のユーザー指定に基づき、ルートの演習本編、Q&A、付録1、付録2のPDFと
対応するSUPERFISH/Pillbox・4cell_flat・4cell・7cellの入力形状を参照し、演習マイルストーンを策定した。
資料中のソフトウェア・入力ファイルをOSSライセンスへ変更したものではない。
過去のseed節の「未参照・未使用」はseed作成時点の記録であり、今回の比較用実行は本節に明示する。

## ローカル開発開始 — 2026-09-05

ユーザー指定の `superfish-ng-0.1.0-seed.zip` を展開し、77エントリのCRCとmanifest対象76ファイルのSHA-256を確認した。
`/home/sin/code/superfish` 直下へ配置し、元READMEは `README-legacy.md` に保存した。
本フォルダには以前から旧環境と講義資料があるため、プロジェクトの参照・配布境界をAGENTS.mdと.gitignoreへ記録した。
旧環境の案内READMEとファイル名のみ確認し、旧ソース・実行形式・講義資料の内容は参照していない。
P0-00として、ZIP収集を明示的な許可リストに変更し、合成fixtureで配布対象外ファイルとシンボリックリンクを検証する。
FEM・RFの数式や実装は変更していない。新しい文献や外部ソルバーのコードは使用していない。
依存ライブラリはPyPIから専用.venvへ導入し、ソース配布には同梱しない。
今回の検証記録は `docs/LOCAL_DEVELOPMENT.md` を参照。

## 今回行ったこと

2026-09-05のユーザー依頼に基づくAI支援による新規実装。
ユーザーが提示した過去の議論には式・機能案・権利関係の一般論が含まれ、旧ソースコードは含まれていなかった。
実装のcanonical仕様はPHYSICS.md、検証基準は公開のMaxwell方程式とpillbox解析解から作成した。
今回のセッションで旧SUPERFISH/POISSONソース、legacy実行形式、非公開資料は取得・使用していない。
旧コード由来の入力デッキを同梱していない。2例題の寸法は今回作成した合成値。

参照した資料と閲覧範囲はREFERENCES.md。関連検索の結果に非公式SUPERFISHミラーへのリンクが表示されたが、
そのリンク先ソース・ファイルは開いていない。MFEM公式例の存在は例一覧で調べ、実装のコピーは行っていない。
cavsim2dはREADMEの製品・依存情報だけを確認し、ソルバ内部のソースを開いていない。

## 主張の限界

これは**参照情報を制限した独立実装**であって、組織的な二チーム分離を実施・監査したclean-room認証ではない。
LLMの学習データに何が含まれていたかは証明できない。別セッションに分ければ学習由来の問題が消える、という主張もしない。
著作権・特許・契約・商標・所属機関の権利を一括してclearance済みとはしていない。
この記録は技術的な来歴管理であり、法的判断書ではない。

## 今後の参照方針

公開の数学・論文・公式API・明示的なOSSライセンスのある現代の依存ライブラリを利用できる。
コードを再利用する場合は出典、バージョン、ライセンス、変更箇所を記録し、独自実装と混同しない。
legacy実装の再翻訳・decompile・同梱は実装経路に入れない。
将来、適切に利用できるlegacy出力を比較基準に使う場合は、実装と独立した参照データとして管理する。
ライセンス条件が分からない出力・入力・図表は「公開されていたから再配布可」としない。

## 新規参照データの記録テンプレート

```json
{
  "id": "reference-case-id",
  "source_url": "public URL or internal record identifier",
  "retrieved_date": "YYYY-MM-DD",
  "permission_or_license": "verified condition; do not guess",
  "solver_name": "name",
  "solver_version": "exact version",
  "geometry_sha256": "hash of an actual geometry file",
  "boundary_conditions": "all surfaces including ends",
  "materials_and_temperature": "specified values",
  "units": "SI or conversion description",
  "phasor_and_rq_convention": "explicit formula",
  "mesh_convergence": "evidence path",
  "reference_uncertainty": "value or unknown",
  "allowed_redistribution": false
}
```

このテンプレートは空の書式であり、実測・legacy参照データが存在することを意味しない。

## 初期成果物の監査可能性

- `benchmarks/validation/validation.json` は実行環境と、その実行に使ったsource/tests/scripts/examplesのSHA-256を記録。
- ZIP内 `MANIFEST.sha256` は同梱ファイルを検査するためのチェックサムであり、第三者認証や電子署名ではない。
- 初期Git履歴はユーザー環境で開始する。架空の研究者署名・貢献履歴は作らない。
- Apache-2.0のLICENSEとNOTICEを用意した。将来の人間による貢献には所属機関条件の確認を含む来歴記録を求める。

# 境界再メッシュ生成の完全保存再生とCLI

2026-10-13 JST、ADD-N04-boundary-remesh-04 **DONE**。先行生成commit `40b67b1`。
[固定仕様](CURVED_BOUNDARY_REMESH_SPEC.md)の七項目文書と九項目検証値を実装した。
全136カードは86 DONE/2 IN_PROGRESS/48 PLANNED、原123は76/2/45。
次は05のStudy/GUI・実worker接続。親N04と全goalは継続する。

## 保存と完全再生

`curved_remesh_generation.build_curved_remesh_generation`は元Projectと版1/2設定を保存し、
生成した版1計画の全prefixをnative再構築する。元と最終の全二次境界比較、seed要素数、
各prefixの要素/境界辺数、最終端点弦の最大辺/面積・最小角、P2隅接線角を保存する。
判定は`GEOMETRY_VERIFIED`、`physical_error_bound`はnull。物理離散化精度を保証しない。
版1のサイズは従来の初期弦メッシュに対する条件を維持し、最終値は観測値として記録する。
端点三角形の面積と角は幾何的な絶対値で測る。P2写像の正Jacobian等は既存native検査に従う。

`replay_curved_remesh_generation`は元Project・全設定から生成を再実行し、
計画・固定分割pattern・全検証値を含む全文書を再構築して照合する。
未知/欠落、元入力の不正、改変された派生値、履歴の欠落・別pattern、整数欄へのbool/float代入、
数値非有限、非nullの誤差上界を拒否する。予算overrideや部分再生の引数を提供しない。
JSONの全深さの重複キーは元`project.parse_json`で辞書化前に拒否する。

ブラウザーのJSON再保存が実数1.0を1と書く場合は、実数欄で同値として扱う。
整数のID/個数・bool・nullの型は厳密に区別する。元仕様の「型込み」はこのJSON数値契約を指す。
文書と入力の整合性を検証するもので、全入力と派生値を整合させた別文書の外部出所を認証するものではない。
入力を変えて予算だけ別指定で元計画の検証を省略する再生はできない。

## CLIと出力保護

既存`generate-curved-remesh-plan`へ`--format plan|document`を追加した。
既定planは従来と同じ裸の版1計画と表示、documentは完全な生成文書を出力する。
新`replay-curved-remesh-generation DOCUMENT [--out PLAN]`は全文書の一致を確認し、
任意の出力へ検証済み裸planを保存する。どちらも固有値を解かない。

新writerは全JSONの有限値検査/直列化と一時ファイルの書き込みを済ませ、
同じ親ディレクトリ内から`os.link`で排他的に公開する。既存ファイルを上書きせず、
公開前の失敗/中断では出力を作らない。一時ディレクトリは終了経路で片付ける。
既存の別CLIの保存方法は変更していない。再メッシュ計画の既定出力内容も維持する。

```sh
uv run --no-sync python -m superfish_ng generate-curved-remesh-plan examples/curved_boundary_remesh/nonaffine-project.json --settings examples/curved_boundary_remesh/nonaffine-settings.json --format document --out out/boundary-generation.json
uv run --no-sync python -m superfish_ng replay-curved-remesh-generation out/boundary-generation.json --out out/boundary-plan.json
```

上記出力名は未使用のものを選ぶ。生成文書をそのままStudyのplan欄へ入れず、再生済み`plan`を渡す。

## 受入証拠

| 検査 | 結果 |
|---|---|
| 先行再現 | 保存reader未実装の一件がImportError、終了1。元red.logを保全 |
| 新saved 9件 | 版1/2、矩形/非アフィン/暗黙sourceの全再生・入力不変、全prefix計数/最終測定、全派生section改変・型・予算・raw重複、ブラウザー数値表記、Study/元比較写像、CLI排他/失敗/中断/原子的公開を確認 |
| 閉式値 | R=.1,L=.2の直角三角形を三段一様制限。要素2/8/32/128、境界4/8/16/32、最大辺√(.1²+.2²)/8、面積.1×.2/128、最小角atan(.1/.2)を別式で照合 |
| 直接消費 | 旧生成9件とStudyの値区間/元形状比較二件を確認。新生成計画も既存Study版4へ渡し、実メッシュ8初期要素/28最終境界辺と元比較mesh26要素を混同せず、再読込後の全Project/座標一致を確認 |
| 実行 | 初回の選択19件91.188秒、handle37111終了0/OK。その後、閉式の一件1.379秒、handle99476終了0/OK。計20個別PASS。成功した19件は再実行しない |
| 実CLI | 設定版1/2各三起動、計6/6終了0。文書生成→完全再生plan→従来既定planを14.399秒で確認、各文書はAPIと一致、両plan全byte一致、元Project/設定ファイルは前後byte不変 |
| 源と範囲 | 元1453対象の変更はgeneration module/CLI/例READMEの三点、新saved test一つで1454対象。他1450源byte一致。生成器の既存全ASTとCLIの当該二入口以外を保持。CLI固定源からは追加閉式testと例READMEの説明だけが変わり、製品源は同byte |

新FEM/seed/full/GUI/legacy0。build/replayの代表検査はsolve禁止で実行した。
全実行handleは終端。生成/科学核を変更せず保存adapterを追加したため、03の独立幾何/行列と
旧41個別受入を再利用し、専用物理系列を重複実行しない。実workerの中止再開/再起動は05、
仕様の専用6FEM・全保存場/RF受入は06へ残す。

rawは`out/n04-boundary-remesh-saved-20261013/`。
開始snapshot、元generation/CLI、red/selected/closed-form log、実CLI六log・文書/planとhash、
受入後source snapshotと`acceptance.json`を保持する。例READMEの現行時点を更新した。
外部資料・新依存・legacyコード/バイナリの参照はない。

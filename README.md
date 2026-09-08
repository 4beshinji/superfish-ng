# Superfish-NG — 0.1.0 research seed

**軸対称RF空洞を公開された数学から独立実装するOSSプロジェクトの初期版です。**
旧SUPERFISHのソース・実行形式には依存しません。Pythonで形状を定義し、実際に有限要素行列を組み立て、固有モードとRF量を計算します。解析式だけを返すモックではありません。

現段階は「閉じた真空PEC空洞の m=0 TM モード」に限定した研究用実装です。
SUPERFISH全体の置換、旧入力形式の全面互換、KEKの実機モデルとの一致はまだ実現・検証していません。
[限定AF読込](docs/LEGACY_INPUT.md)で、単一真空・全PECの直線/段差/短円弧をNG入力へ変換できます。
`import-af`はNG設定を明示し、原入力と変換診断を保存します。未対応指定は位置付きで拒否します。
プロジェクト名は作業名で、LANL・DOE・KEKの公式製品ではありません。

指定4資料に基づく [セミナー例題の計算と可視化](docs/MILESTONE_SEMINAR.md) のマイルストーンは完了しました。
Wine版SUPERFISHとの3形状の基本モード照合は実施済みで、[比較結果](docs/SUPERFISH_COMPARISON.md)を記録しています。
角部のピーク差については、[表面電場の切り分け評価](docs/SURFACE_FIELD_DIAGNOSTICS.md)で局所メッシュ・固定点・丸み対照を調べています。
[境界実長指定と角近傍の局所細分](docs/PHYSICAL_MESH_REFINEMENT.md)を追加し、固定点電場とPEC接線成分の改善を確認しました。
多セルの段差・円弧、4/7モードの計算・同定・分散曲線・表示を実装済みです。
[最終結果の入口](out/seminar-suite-final-20260905/index.html) から例題・モードを選択できます。
全NG新規計算の9検証ジョブ、7ページの画面検査、対象17モードのWine照合が合格しました。
対象・受入基準・対象外は [受入記録](docs/MILESTONE_ACCEPTANCE.md)、細分の履歴は [多セル記録](docs/SEMINAR_MULTICELL.md) に明記しています。

PillboxのTM010/TM011・長さ掃引・電磁場の図は [演習ガイド](docs/SEMINAR_PILLBOX.md) から実行できます。
`python scripts/seminar_pillbox.py --out out/seminar-new` で例題の計算と結果選択HTMLを生成します（plot依存が必要）。
多セルは `python scripts/seminar_multicell.py --case rounded4 --out out/rounded4-new`。
`--case` はflat4/rounded4/rounded7。数値ゲート未達はFAILとして保存・表示します。
端部比較は `python scripts/seminar_end_cells.py --flat-half-extra-n 384 --out out/ends-new`。
収束確認済みの7セル設定は `--triangulation crossed --levels 64 128 256` を明示します。
全演習の新規計算と入口HTMLは [一括実行ガイド](docs/SEMINAR_SUITE.md)。初回の未達結果も上書きせず保持しています。

## ローカルで開始する

現在の作業checkoutは `/home/sin/code/agent/reserch/superfish-ng` です。
過去の記録にある `/home/sin/code/superfish` は当時の配置です。既存checkoutを移動せず、以下の構造で開発します。

```text
superfish/
├── src/superfish_ng/       # FEMソルバー、RF量、CLI
├── tests/                 # 物理・入力出力・配布の回帰テスト
├── examples/              # pillboxと合成セルのJSON入力
├── scripts/               # 検証、描画、パッケージ作成
├── docs/                  # 仕様、開発計画、今回の動作確認記録
├── benchmarks/validation/ # seedに同梱された基準データ
├── benchmarks/seed/       # 原本のチェックサム
├── out/                   # ローカル実行結果（Git・配布対象外）
├── .venv/                 # このPJ専用のPython環境
└── pyproject.toml         # 依存関係とCLI定義
```

この環境では `.venv` を構築済みです。以下で例題を実行できます。

```bash
cd /home/sin/code/agent/reserch/superfish-ng
source .venv/bin/activate
superfish-ng solve examples/pillbox.json --out out/pillbox-new
```

初回構築し直す場合は、このREADMEのあるディレクトリで次を実行します。Linuxを主対象とし、Python 3.12を開発環境に指定しています（`.python-version`）。seed納品時はPython 3.12.13 / NumPy 2.3.5 / SciPy 1.17.0でした。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
superfish-ng solve examples/pillbox.json --out out/pillbox
superfish-ng solve examples/shaped_cell.json --out out/shaped
superfish-ng converge --out out/convergence.json
```

`--out`は新しいパスを指定してください。既存の計算を上書きしません。
CLIの代わりに `python -m superfish_ng ...` も使用できます。
既にNumPy/SciPyがある環境では、インストールせず `PYTHONPATH=src python -m superfish_ng ...` でも動きます。
ZIPに仮想環境や依存ライブラリのwheelは含みません。初回の依存関係取得には通常ネット接続が必要です。

全検証と例題出力を再生成するコマンド:

```bash
OPENBLAS_NUM_THREADS=1 python scripts/validate.py --out out/validation
```

任意の図を生成する場合:

```bash
python -m pip install -e '.[plot]'
python scripts/plot_results.py out/shaped --out out/shaped.png
```

## 実装済み

2026-09-08、中心軌跡交点探索追加後（直前基準 `367c524`）。最新の受入範囲と履歴は [実装状況](docs/IMPLEMENTATION_STATUS.md)。

| 分野 | 現在の内容 |
|---|---|
| 形状 | pillbox、折れ線、段差、短円弧、z折返し単一輪郭、native円/楕円/双曲線弧。軸接続・単一真空領域 |
| メッシュ | タグ付き三角形、自動生成/JSON読込、P1/P2場。曲線輪郭は二次幾何写像と固定幾何細分に対応 |
| 物理 | 真空、回転対称、m=0 TM系、PEC外壁、平坦z端の対称条件と鏡映 |
| 固有値 | 一般化対称固有値問題、SciPy/ARPACKのshift-invert、複数モード |
| 数値検査 | 固有値残差、質量内積での直交性、電気・磁気エネルギー整合 |
| RF量 | f、U、表面抵抗、壁損失、Q0、G、通過位相を含むVacc、R/Q、シャントインピーダンス、TTF |
| 表面電磁場 | P1/P2片側場、曲線離散場の連続極値の囲い込みと角診断。物理ピークの収束保証とは区別 |
| 出力 | 単位と規約を含むJSON、CSV、NPZ、ParaView向けASCII VTK |
| 検証 | 標準376件中374合格・2 skip。Pillbox/Bessel場、球形独立参照、楕円/双曲線の幾何・FEM細分、RF、保存、GUI等。数値・ブラウザー受入は個別記録を参照 |

`benchmarks/validation/` に納品時の実測ログ、解析値との比較、計算場を収録しています。
2026-09-07: [NGSolveとの独立照合](docs/INDEPENDENT_COMPARISON.md)を追加し、
円筒/円錐台の両側収束と周波数・RF量・内部磁場を検証しました。
[境界タグ付き非構造メッシュ入力](docs/MESH_INPUT.md)もCLI/APIで利用できます。
明示した物理・座標・単一真空材料/領域を持つ[v3入力](docs/MODEL_CONTRACT.md)を追加しました。
`superfish-ng capabilities`で対応範囲、`migrate-case`で既存入力からの明示移行を利用できます。
旧v1/v2のhashと数値結果を維持し、追加物理は未実装として拒否します。
v3のrfとGUIで[加速長・電圧積分区間・位相原点](docs/ACCELERATING_CONVENTIONS.md)を指定できます。
指定を省略した既存の周波数・RF結果は変わりません。
`docs/VALIDATION_REPORT.md` に数値と解釈をまとめています。
今回の環境での実行結果と配布処理の変更は [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md) に記録しています。

ルートに以前から存在するWine環境、`SUPERFISH/`、講義PDF、`解説/`、旧起動スクリプトはローカル資産です。
旧READMEは `README-legacy.md` に保存しました。これらはSuperfish-NGの実装・配布対象外で、配布スクリプトは指定したプロジェクトディレクトリとファイルだけを収集します。

## 重要な制約

- m=0のTEモード、m>0の双極・四重極モード、同軸TEM、静電場、静磁場、非線形材料は未実装。
- profile系は `R(z)>0`、arc_profileはz非減少の短円弧に限定します。v3 contour/curved_contourはz折返しを許しますが、軸接続の単一外周に限定し、穴・内導体・任意CAD・RFQは扱いません。
- 両端は既定で金属板、v2入力で電気/磁気対称面を指定できます。細い首は開放ビームポートではありません。
- Q0は理想PEC固有場に常伝導表面抵抗を適用する摂動推定です。複素固有周波数、超伝導BCS損失、放射損失は計算しません。
- 電磁場はピークphasorです。既定で全蓄積エネルギー1 Jに正規化します。運転電力1 Wの指定ではありません。
- R/Qは `|Vacc|²/(ωU)` と `|Vacc|²/(2ωU)` を別名で出力します。
- 周波数順のmode番号は物理モード名ではありません。形状変更時のmode trackingは未実装。
- Wine版SUPERFISHとの基本3形状照合に加え、セミナーの80 mm Pillbox TM010/TM011、flat4・rounded4・rounded7の計17モードを照合済み。full-end比較形状と長さ40/120 mmはWine直接照合の対象外です。測定との比較は未実施で、角部のピーク電場には差が残ります。

## Codexに引き継ぐ

現在の開発計画は[実装の現状](docs/IMPLEMENTATION_STATUS.md)→
[互換対応表](docs/COMPATIBILITY_MATRIX.md)→[仕様・実装・検証への分割](docs/COMPATIBILITY_PLAN.md)。
既存課題の状態は[バックログ](docs/BACKLOG.md)を参照。計画の記載は対応機能の完成を意味しません。

汎用GUIは `superfish-ng gui --workspace out/gui-workspace` で起動します。
形状・円弧・繰り返し部分の編集、計算と中止、保存場・RF量の表示、
寸法掃引・収束比較を、CLI/Pythonと共通の入力・計算機能で扱えます。
描画にはplot extraが必要です。導入と操作は [GUIガイド](docs/GUI_GUIDE.md)、
範囲と判断基準は [開発計画](docs/GUI_IO_PLAN.md)、検証は [受入記録](docs/GUI_ACCEPTANCE.md) を参照。
例題専用の処理を作らず、操作性・再現性・数値の信頼性・保守性で変更を判断します。

このディレクトリをCodexで開きます。Gitを新規に初期化する場合も、このディレクトリをルートとします。

```bash
git init
git add .github .gitignore .python-version AGENTS.md CHANGELOG.md CONTRIBUTING.md LICENSE MANIFEST.in NOTICE README.md pyproject.toml requirements-reproduce.txt src tests scripts examples docs benchmarks
git commit -m "Initial independent axisymmetric RF seed"
```

最初に `AGENTS.md` と `docs/CODEX_HANDOFF.md` を読ませ、同ファイルの開始プロンプトを使用してください。
公開リモートやパッケージの登録は今回行っていません。

配布用ZIPは次で作成できます（`--out` はPJ外の新しいファイル）。収録対象を増やす場合は `scripts/package.py` の許可リストも更新してください。

```bash
python scripts/package.py --out /tmp/superfish-ng-dev.zip
```

`scripts/verify_manifest.py` は、配布ZIPを新規ディレクトリに展開した直後に実行します。
開発中のルートには古いmanifestを置かず、seed原本のmanifestは `benchmarks/seed/manifest.sha256` に保存しています。

| ファイル | 用途 |
|---|---|
| [docs/RESEARCH.md](docs/RESEARCH.md) | 事前調査、既存OSS、採用判断、前の議論の訂正 |
| [docs/PHYSICS.md](docs/PHYSICS.md) | 軸上処理・弱形式・境界条件・RF量の定義 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 依存順と受入基準を持つ開発計画 |
| [docs/BACKLOG.md](docs/BACKLOG.md) | Codex向けの具体的な実装タスク |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | モジュール責務と将来のバックエンド境界 |
| [docs/REFERENCES.md](docs/REFERENCES.md) | 注釈付き文献・一次資料一覧 |
| [docs/references.bib](docs/references.bib) | 論文のBibTeX |
| [docs/PROVENANCE.md](docs/PROVENANCE.md) | 参照制限、今回の参照履歴、clean-roomの限界 |
| [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md) | 依存関係・ライセンス・再現環境 |
| [docs/INPUT_OUTPUT.md](docs/INPUT_OUTPUT.md) | 入力と出力の仕様 |

ライセンスは [Apache-2.0](LICENSE)。第三者文献や依存ライブラリは各自の条件に従います。

要素次数は既定P1とP2を選択できます。Pythonでは`Case(..., element_order=2)`、
v3 JSONでは`"solver": {"modes": 3, "element_order": 2}`を指定します。
v3には明示modelが必要です（[モデル契約](docs/MODEL_CONTRACT.md)）。GUIにも次数選択があります。
P2の場・RF・保存・表示の仕様と検証は[高次場](docs/HIGH_ORDER_FIELDS.md)を参照してください。
直線幾何のP2はN01/N02として受入済みです。v3 curved_contourでは
`mesh.geometry_order=2` と `solver.element_order=2` による曲線FEMも利用できます。
場/RF・保存・描画・Study・鏡映・GUIまで接続済みです（[曲線要素](docs/CURVED_ELEMENTS.md)）。
G03全体は部分対応です。[要件と証拠の照合](docs/G03_ACCEPTANCE.md)を参照してください。有限弧の接線数値判定と明示選択G1接続APIを追加しましたが、
中心軌跡の交点探索を追加しましたが、円錐曲線弧フィレットの接点復元・切詰め・製品接続が残ります。固定直線と弧の接続（版3）と指定半径の線分間フィレット（版4）を保存・Case/CLI/GUIへ接続済みです。
支持曲線の接点座標を有理数区間で囲むAPIを追加しました。有限弧所属/fractionの区間APIも追加し、版2で位置誤差上界付き切詰め・保存・CLI/GUIへ統合しました。適応誤差推定は未対応です。
接線構築は `construct-tangent` → `export-constructed-case` → `solve` で実行できます。
合成例と保存・再構築の仕様は [接線構築](docs/TANGENT_CONSTRUCTION.md) を参照してください。

v3の一般輪郭`contour`はz折返しを含む単一外周を表せます。`mesh.contour_mesh`で
最大辺長・品質・停止上限を明示して自動生成するか、検証済み外部メッシュを渡します。
例は `python -m superfish_ng solve examples/contour_folded.json --out out/contour-new`。
この粗い合成例は操作例であり精度基準ではありません。GUIでは設定編集・自動計算・保存結果表示に対応します。仕様と制限は
[一般輪郭](docs/GENERAL_CONTOUR.md)を参照してください。

# Superfish-NG — 0.1.0 research seed

**軸対称RF空洞を公開された数学から独立実装するOSSプロジェクトの初期版です。**
旧SUPERFISHのソース・実行形式には依存しません。Pythonで形状を定義し、実際に有限要素行列を組み立て、固有モードとRF量を計算します。解析式だけを返すモックではありません。

現段階は「閉じた真空PEC空洞の m=0 TM モード」に限定した研究用実装です。
SUPERFISH全体の置換、旧入力形式の互換性、KEKの実機モデルとの一致はまだ実現・検証していません。
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

本PJのルートは `/home/sin/code/superfish` です。`superfish-ng/` を追加で挟まず、以下の構造で開発します。

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
cd /home/sin/code/superfish
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

| 分野 | 0.1.0 の内容 |
|---|---|
| 形状 | pillbox、折れ線 `R(z)`、垂直段差、半径を保持した短円弧の直線近似。各断面は軸から壁まで真空 |
| メッシュ | 形状に沿った2D三角形、一次要素、軸・PEC・電気/磁気対称境界のタグ |
| 物理 | 真空、回転対称、m=0 TM系、PEC外壁、平坦z端の対称条件と鏡映 |
| 固有値 | 一般化対称固有値問題、SciPy/ARPACKのshift-invert、複数モード |
| 数値検査 | 固有値残差、質量内積での直交性、電気・磁気エネルギー整合 |
| RF量 | f、U、表面抵抗、壁損失、Q0、G、通過位相を含むVacc、R/Q、シャントインピーダンス、TTF |
| 表面電磁場 | Epk/Eacc、Bpk/Eaccの一次要素推定値。角部では収束保証なし |
| 出力 | 単位と規約を含むJSON、CSV、NPZ、ParaView向けASCII VTK |
| 検証 | 82テスト、pillbox収束、Bessel場、RF量、対称境界、段差/円弧・交差分割、バンド同定、表面電場診断。生成HTMLはheadless操作も検証 |

`benchmarks/validation/` に納品時の実測ログ、解析値との比較、計算場を収録しています。
`docs/VALIDATION_REPORT.md` に数値と解釈をまとめています。
今回の環境での実行結果と配布処理の変更は [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md) に記録しています。

ルートに以前から存在するWine環境、`SUPERFISH/`、講義PDF、`解説/`、旧起動スクリプトはローカル資産です。
旧READMEは `README-legacy.md` に保存しました。これらはSuperfish-NGの実装・配布対象外で、配布スクリプトは指定したプロジェクトディレクトリとファイルだけを収集します。

## 重要な制約

- m=0のTEモード、m>0の双極・四重極モード、同軸TEM、静電場、静磁場、非線形材料は未実装。
- `R(z)>0` が必要です。穴・内導体・z方向に折返す輪郭・任意CAD・RFQを扱えません。円弧はz非減少の短円弧のみです。
- 両端は既定で金属板、v2入力で電気/磁気対称面を指定できます。細い首は開放ビームポートではありません。
- Q0は理想PEC固有場に常伝導表面抵抗を適用する摂動推定です。複素固有周波数、超伝導BCS損失、放射損失は計算しません。
- 電磁場はピークphasorです。既定で全蓄積エネルギー1 Jに正規化します。運転電力1 Wの指定ではありません。
- R/Qは `|Vacc|²/(ωU)` と `|Vacc|²/(2ωU)` を別名で出力します。
- 周波数順のmode番号は物理モード名ではありません。形状変更時のmode trackingは未実装。
- Wine版SUPERFISHとの基本3形状照合に加え、セミナーの80 mm Pillbox TM010/TM011、flat4・rounded4・rounded7の計17モードを照合済み。full-end比較形状と長さ40/120 mmはWine直接照合の対象外です。測定との比較は未実施で、角部のピーク電場には差が残ります。

## Codexに引き継ぐ

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

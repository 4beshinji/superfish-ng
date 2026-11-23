# Superfish-NG

軸対称RF空洞の共振モードを計算する、独立実装のFEMソルバーです
（研究シード v0.1.0、Python 3.10+ / NumPy・SciPy）。
空洞形状を与えると、モード周波数・電磁場・RF積分量・表面ピーク場をSI単位で返します。
CLI・Python API・ローカルブラウザーGUIの3入口から、単発の求解から寸法掃引・
周波数調整・制約付きRF探索まで、同じ計算核で実行できます。

この実装は、POISSON/SUPERFISH系の軸対称空洞設計実務を公開数学・論文・公式仕様・
ライセンス互換の現代ライブラリのみから独立に置き換えるという
[長期目標](docs/ROADMAP.md)の研究段階です。歴史コードの移植ではなく、
入力・計算・保存の契約を明示して構築した別実装であり、旧コードやバイナリの
参照・再配布は行いません（[来歴](docs/PROVENANCE.md)）。

## 主な機能

| 分野 | 内容 |
|---|---|
| 形状 | pillbox、折れ線・段差プロファイル、短円弧、z折返し単一輪郭、native 円/楕円/双曲線弧。軸接続・単一真空領域 |
| メッシュ | タグ付き三角形の自動生成とJSON読込、P1/P2 場。曲線輪郭は二次幾何写像と固定幾何細分に対応 |
| 物理 | 真空回転対称 m=0 TM（直線P1/P2・曲線P2）、軸対称TE、PEC外壁、平坦z端の対称条件。専用入口として同軸・正半径 Hφ・軸接続穴付き・材料 Hφ・平面RF・静磁・静電 |
| 固有値 | 一般化対称固有値問題、SciPy/ARPACK shift-invert、複数モード |
| 数値検査 | 固有値残差、質量内積での直交性、電気・磁気エネルギー整合 |
| RF量 | f、U、表面抵抗、壁損失、Q0、G、通過位相を含む Vacc、R/Q（2定義）、シャントインピーダンス、TTF |
| 表面電磁場 | P1/P2 片側場、曲線離散場の連続極値の囲い込みと角診断 |
| モード追跡 | 重み付き部分空間・円筒/profile 写像・明示メッシュ対応。個別ID履歴・回復・再開、合流/分裂の集合継続 |
| 掃引・最適化 | 形状 Study（逐次・適応・メッシュ切替）、制約付き RF 探索、周波数調整（1変数 / 多変数・曲線寸法） |
| 出力 | 単位と規約を含む JSON、CSV、NPZ、ParaView 向け ASCII VTK |
| GUI | ローカルブラウザー GUI（`plot` extra 必須）。編集・計算・中止・保存結果表示・掃引・収束比較 |

全体の構成は [現行の物理入口と構成](docs/ARCHITECTURE.md#current-architecture)、
物理仕様は [物理・数値仕様](docs/PHYSICS.md#現行の範囲と読み方)、
入力版の契約は [モデル契約](docs/MODEL_CONTRACT.md)、
入口別の対応状況は [互換対応表](docs/COMPATIBILITY_MATRIX.md) を参照してください。

## インストール

Linux を主対象とし、開発環境は Python 3.12（`.python-version`）です。NumPy/SciPy が中核依存、
Matplotlib は任意（`plot` extra）です。
環境・依存は[uv](https://docs.astral.sh/uv/)で管理します。

```bash
uv venv --python 3.12
uv pip install --python .venv/bin/python -e .
```

図やGUIを利用する場合:

```bash
uv pip install --python .venv/bin/python -e '.[plot]'
uv run --no-project --python .venv/bin/python superfish-ng gui --workspace out/gui-workspace
```

coreだけではGUI起動を説明付きで拒否します。GUIを含むfull検証にも`plot`が必要です。
CLI例は環境を有効にして実行するか、同じ`uv run --no-project --python .venv/bin/python`を先頭に付けます。
サポートPython 3.10/3.12の解決、現開発環境、過去benchmarkの再現は
[依存・環境契約](docs/DEPENDENCIES.md#current-environments)を参照してください。

既に NumPy/SciPy がある環境では、インストールせず `PYTHONPATH=src python -m superfish_ng ...` でも動作します。

## クイックスタート

CLI で例題を計算します。`--out` には既存の計算を上書きしない新しいパスを指定してください。

```bash
superfish-ng solve examples/pillbox.json --out out/pillbox-new
superfish-ng solve examples/shaped_cell.json --out out/shaped-new
superfish-ng converge --out out/convergence.json
superfish-ng capabilities            # 対応範囲・単位をJSONで表示
```

Python API:

```python
from superfish_ng import Case, solve
from superfish_ng.rf import quantities
from superfish_ng.io import save_run

case = Case.load("examples/pillbox.json")
solution = solve(case)
print(quantities(case, solution, mode=0))  # Python の mode は 0-based
save_run(case, solution, "out/my_run")
```

要素次数は既定 P1 / P2 を選択できます（`Case(..., element_order=2)`）。
v3 JSON では `"solver": {"modes": 3, "element_order": 2}` を指定し、
v3 には明示 `model` が必要です（[モデル契約](docs/MODEL_CONTRACT.md)）。

## GUI

```bash
superfish-ng gui --workspace out/gui-workspace
```

形状・円弧・繰り返し部分の編集、計算と中止、保存場・RF量の表示、寸法掃引・収束比較を
CLI/Python と共通の入力・計算機能で扱えます。操作の手順は [GUIガイド](docs/GUI_GUIDE.md)、
範囲と基準は [GUI開発計画](docs/GUI_IO_PLAN.md)・[受入記録](docs/GUI_ACCEPTANCE.md) を参照。
曲線形状Studyでは、元P2境界を保つ再メッシュ生成と保存復元も利用できます。

## 入力と出力

**入力（何を与えるか）**

- v3 入力は物理・座標・材料・領域を明示します。旧 v1/v2 の hash と数値結果は維持します。
- 外部で作成した境界タグ付き三角形メッシュも読み込めます（[メッシュ入力](docs/MESH_INPUT.md)）。
- 未対応の追加物理は近似せず、エラーとして拒否します。

**出力（何を受け取るか）**

- すべて SI 単位・ピーク phasor 規約です。既定で全蓄積エネルギー 1 J に正規化するため、
  モード間・形状間の相対比較ができます（運転電力 1 W の指定ではありません）。
- TM の R/Q は `|Vacc|²/(ωU)` と `|Vacc|²/(2ωU)` を別名で出力します。
  m=0 TE では軸加速量と両 R/Q を N/A として保存します。平面RFは単位長当たり U′ [J/m]・損失 [W/m]。
- Q0 は理想 PEC 固有場に常伝導表面抵抗を適用する摂動推定です。
  BCS 損失・複素固有周波数・放射損失を含む完全損失モデルではありません。
- 成果物は完了マーカーと hash を持ち、既存出力を上書きしません。
  仕様は [入出力仕様](docs/INPUT_OUTPUT.md)・[保存完了契約](docs/SAVE_COMPLETION.md) を参照。

## 対応範囲とその境界

対応する物理は入口ごとに区別されます。

- **既定入口（`solve`）**: 真空・閉 PEC・軸接続 m=0 TM。直線輪郭 P1/P2、曲線輪郭 P2。
- **専用入口**: 軸対称TE、閉じた同軸真空、正半径 Hφ、軸接続穴付き、材料 Hφ、平面RF、
  静磁・静電（軸対称・平面・off-axis）。それぞれ専用の Case/CLI/保存形式を持ちます。
- 入口ごとの対応・版付きの限定受入は [物理入口表](docs/ARCHITECTURE.md#rf固有問題) と
  [B01対応台帳](docs/development-plan/B01-ledger.md) で確認できます。

数値の解釈に関する境界です。いずれも未対応の入力は黙って近似せず拒否します。

- プロファイル系は `R(z)>0`、arc_profile は z 非減少の短円弧に限定します。
  一般 CAD・任意 RFQ の直接入力は対象外です。
- 表面場の囲い込みは離散場の連続極値に対する保証であり、物理ピークの収束証明とは別判定です。
  ピークの収束は専用の収束検査で別に確認します。
- 周波数順のモード番号は物理モード名ではありません。掃引中の個別モード追跡は明示写像で提供し、
  一般形状の全自動対応は開発中です。
- 小さな固有値残差は離散化誤差が小さいことの証明ではないため、
  周波数・場・RF積分・表面場の検査は別々に管理します。

## 検証

通常は変更した機能と影響先だけを選んで実行します（[変更別の検証手順](docs/TESTING.md)）。
標準ライブラリの `unittest` を使い、pytest は不要です。

```bash
python -m unittest discover -s tests -p test_interface.py -v   # 初回セットアップ確認
OPENBLAS_NUM_THREADS=1 python scripts/validate.py --out out/validation   # 節目・広範変更で一度
```

seed 例題の数値だけを確認する場合:

```bash
OPENBLAS_NUM_THREADS=1 python scripts/validate.py --skip-tests --out out/validation-seed-new
```

受け取れる検証証拠は次のとおりです。

- `benchmarks/validation/` の実測ログと解析比較、[検証報告](docs/VALIDATION_REPORT.md) の数値と解釈。
- NGSolve との独立照合（[独立比較](docs/INDEPENDENT_COMPARISON.md)）。
- 既知形状についての Wine 版 SUPERFISH との限定照合
  （[照合記録](docs/SUPERFISH_COMPARISON.md)・[比較環境](docs/WINE_REFERENCE_ENVIRONMENT.md)）。

これらは実装の verification であり、実測との比較・全入力範囲の互換受入は未実施です。
GUI の計算完了はメッシュ収束を意味しません。
開発中機能の受入状態は台帳（[実装状況](docs/IMPLEMENTATION_STATUS.md)・
[開発バックログ](docs/BACKLOG.md)）で管理します。

## ドキュメント

| 読む目的 | 文書 |
|---|---|
| 物理と数値の定義 | [PHYSICS.md](docs/PHYSICS.md) |
| 構成と物理別入口 | [ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 入力・保存の契約 | [MODEL_CONTRACT.md](docs/MODEL_CONTRACT.md)・[INPUT_OUTPUT.md](docs/INPUT_OUTPUT.md)・[SAVE_COMPLETION.md](docs/SAVE_COMPLETION.md)・[MESH_INPUT.md](docs/MESH_INPUT.md)・[GENERAL_MESH.md](docs/GENERAL_MESH.md) |
| GUI の操作 | [GUI_GUIDE.md](docs/GUI_GUIDE.md) |
| 検証の再現 | [VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md)・[INDEPENDENT_COMPARISON.md](docs/INDEPENDENT_COMPARISON.md)・[TESTING.md](docs/TESTING.md) |
| 依存・環境 | [DEPENDENCIES.md](docs/DEPENDENCIES.md) |
| 来歴・文献 | [PROVENANCE.md](docs/PROVENANCE.md)・[RESEARCH.md](docs/RESEARCH.md)・[REFERENCES.md](docs/REFERENCES.md) / [references.bib](docs/references.bib) |
| 変更履歴 | [CHANGELOG.md](CHANGELOG.md) |
| 開発計画・現状（内部） | [ROADMAP.md](docs/ROADMAP.md)・[BACKLOG.md](docs/BACKLOG.md)・[IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md)・[REFACTORING_PLAN.md](docs/REFACTORING_PLAN.md)・[development-plan/](docs/development-plan/README.md) |
| 作業引き継ぎ（内部） | [CODEX_HANDOFF.md](docs/CODEX_HANDOFF.md) |

docs 全体の分類と読み方は [docs索引](docs/README.md) を参照してください。
docs 直下の大半は作業カードごとの受入・実行記録（append-only）で、
最新の現在地は [development-plan/CURRENT.md](docs/development-plan/CURRENT.md) と
台帳の最上位項目で管理します。セッションの進捗要約は README に載せず、台帳へ追記します。

## 参照・来歴

数学・公開論文・公式仕様・ライセンス互換な現代ライブラリのみを参照します。
参照履歴とその限界（歴史的なtwo-team分離によるmodel-training来歴は確立していないため
clean-room実装とは呼ばない）は [PROVENANCE.md](docs/PROVENANCE.md) に記録しています。

## ライセンス

[Apache-2.0](LICENSE)。第三者文献・依存ライブラリは各自の条件に従います（[NOTICE](NOTICE)）。

## 開発への参加

作業前に [AGENTS.md](AGENTS.md)、[CONTRIBUTING.md](CONTRIBUTING.md)、[CODEX_HANDOFF.md](docs/CODEX_HANDOFF.md) を読んでください。
[BACKLOG.md](docs/BACKLOG.md) から件を選び、受け入れ基準・変更対象テスト・証拠を記録してから実装します。

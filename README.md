# Superfish-NG

軸対称RF空洞のための独立実装 FEM ソルバー（`0.1.0` research seed、Python 3.10+ / NumPy・SciPy）。
canonical スコープは **真空・閉 PEC・軸接続 m=0 TM** で、これを基準に形状・メッシュ・RF量・
モード追跡・専用物理（平面 / 同軸 / 材料 Hφ / TE / 静磁・静電）を拡張しています。

旧 SUPERFISH/POISSON の移植ではなく、互換認定された実装でもありません。
対応範囲は限定受入（limited acceptance）で管理し、未対応の物理・入力は黙って受理せず明示的に拒否します。
現在の受入範囲・証拠の現存/欠落は [B01対応台帳](docs/development-plan/B01-ledger.md)、
日付ごとの実装履歴は [実装状況](docs/IMPLEMENTATION_STATUS.md) を参照してください。

## 主な機能

| 分野 | 内容 |
|---|---|
| 形状 | pillbox、折れ線・段差プロファイル、短円弧、z折返し単一輪郭、native 円/楕円/双曲線弧。軸接続・単一真空領域 |
| メッシュ | タグ付き三角形の自動生成とJSON読込、P1/P2 場。曲線輪郭は二次幾何写像と固定幾何細分に対応 |
| 物理 | 真空回転対称 m=0 TM、直線P1/P2・曲線P2 TE、PEC外壁、平坦z端の対称条件。専用経路として同軸・正半径 Hφ・軸接続穴付き・材料 Hφ・平面 / 静磁・静電 |
| 固有値 | 一般化対称固有値問題、SciPy/ARPACK shift-invert、複数モード |
| 数値検査 | 固有値残差、質量内積での直交性、電気・磁気エネルギー整合 |
| RF量 | f、U、表面抵抗、壁損失、Q0、G、通過位相を含む Vacc、R/Q（2定義）、シャントインピーダンス、TTF |
| 表面電磁場 | P1/P2 片側場、曲線離散場の連続極値の囲い込みと角診断（物理ピークの収束保証とは区別） |
| モード追跡 | 重み付き部分空間・円筒/profile 写像・明示メッシュ対応。個別ID履歴・回復・再開、合流/分裂の集合継続 |
| 掃引・最適化 | 形状 Study（逐次・適応・メッシュ切替）、制約付き RF 探索、周波数調整（1変数 / 多変数・曲線寸法） |
| 出力 | 単位と規約を含む JSON、CSV、NPZ、ParaView 向け ASCII VTK |
| GUI | ローカルブラウザー GUI（`plot` extra 必須）。編集・計算・中止・保存結果表示・掃引・収束比較 |

対応状況の詳細は [物理仕様](docs/PHYSICS.md)、[モデル契約](docs/MODEL_CONTRACT.md)、
[互換対応表](docs/COMPATIBILITY_MATRIX.md) を参照してください。

## インストール

Linux を主対象とし、開発環境は Python 3.12（`.python-version`）です。NumPy/SciPy が中核依存、
Matplotlib は任意（`plot` extra）です。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

図を生成する場合:

```bash
python -m pip install -e '.[plot]'
```

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
CLI/Python と共通の入力・計算機能で扱えます。導線は [GUIガイド](docs/GUI_GUIDE.md)、
範囲と基準は [GUI開発計画](docs/GUI_IO_PLAN.md)・[受入記録](docs/GUI_ACCEPTANCE.md) を参照。

## 入力と出力

- v3 入力は物理・座標・材料・領域を明示します。旧 v1/v2 の hash と数値結果は維持し、
  未対応の追加物理はエラーとして拒否します。
- すべて SI 単位・ピーク phasor 規約です。既定で全蓄積エネルギー 1 J に正規化します。
- TM の R/Q は `|Vacc|²/(ωU)` と `|Vacc|²/(2ωU)` を別名で出力します。m=0 TE では軸加速量と両 R/Q を N/A として保存します。
- 成果物は完了マーカーと hash を持ち、既存出力を上書きしません。仕様は [入出力仕様](docs/INPUT_OUTPUT.md)・[保存完了契約](docs/SAVE_COMPLETION.md) を参照。

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

`benchmarks/validation/` に納品時の実測ログと解析比較、`docs/VALIDATION_REPORT.md` に
数値と解釈を収録しています。NGSolve との独立照合は [独立比較](docs/INDEPENDENT_COMPARISON.md) を参照。

## 重要な制約

- canonical スコープは真空・閉 PEC・軸接続 m=0 TM です。一般形状の TE 追跡、m>0 の双極・四重極、
  軸接続の穴付き領域・曲線内導体、非線形材料の一般経路などは未実装または専用経路に限定されます。
- プロファイル系は `R(z)>0`、arc_profile は z 非減少の短円弧に限定します。一般 CAD・任意 RFQ は扱いません。
- Q0 は理想 PEC 固有場に常伝導表面抵抗を適用する摂動推定です。複素固有周波数、超伝導 BCS 損失、放射損失は計算しません。
- 電磁場はピーク phasor で、既定は全蓄積エネルギー 1 J 正規化です（運転電力 1 W の指定ではありません）。
- 周波数順のモード番号は物理モード名ではありません。明示写像による追跡に部分対応しますが、一般形状の自動対応は未完です。
- 既知形状について Wine 版 SUPERFISH との限定照合がありますが、測定との比較・全範囲の互換受入は未実施です。
  GUI の計算完了はメッシュ収束を意味しません。

## ドキュメント

| ファイル | 用途 |
|---|---|
| [docs/PHYSICS.md](docs/PHYSICS.md) | 軸上処理・弱形式・境界条件・RF量の定義 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | モジュール責務、ADR、将来のバックエンド境界 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 依存順と受入基準を持つ開発計画 |
| [docs/BACKLOG.md](docs/BACKLOG.md) | 実装タスクと現状 |
| [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md) | 受入範囲と日付ごとの実装履歴 |
| [docs/development-plan/](docs/development-plan/README.md) | 未完了課題の作業カード一覧 |
| [docs/RESEARCH.md](docs/RESEARCH.md) | 事前調査、既存OSS、採用判断 |
| [docs/REFERENCES.md](docs/REFERENCES.md) / [docs/references.bib](docs/references.bib) | 文献・一次資料と BibTeX |
| [docs/PROVENANCE.md](docs/PROVENANCE.md) | 参照制限、参照履歴、clean-room の限界 |
| [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md) | 依存関係・ライセンス・再現環境 |
| [docs/CODEX_HANDOFF.md](docs/CODEX_HANDOFF.md) | 作業引き継ぎの記録 |

## 参照・来歴

本実装は独立実装であり、旧 SUPERFISH/POISSON のソース・バイナリを取得・複製・埋め込みません。
数学・公開論文・公式仕様・ライセンス互換な現代ライブラリのみを参照します。詳細と限界は
[PROVENANCE.md](docs/PROVENANCE.md) を参照してください。**clean-room 認定実装ではありません**
（歴史的な二チーム分離やモデル訓練来歴は確立していません）。

## ライセンス

[Apache-2.0](LICENSE)。第三者文献・依存ライブラリは各自の条件に従います（[NOTICE](NOTICE)）。

## 開発への参加

作業前に [AGENTS.md](AGENTS.md)、[CONTRIBUTING.md](CONTRIBUTING.md)、[CODEX_HANDOFF.md](docs/CODEX_HANDOFF.md) を読んでください。
`docs/BACKLOG.md` から件を選び、受け入れ基準・変更対象テスト・証拠を記録してから実装します。

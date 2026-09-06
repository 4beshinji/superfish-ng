# 依存関係と配布方針

## 0.1.0で実際に使用するもの

| 依存 | pyprojectの範囲 | 納品時実行版 | ライセンス/同梱 |
|---|---|---|---|
| Python | >=3.10 | 3.12.13 | ユーザー環境へ導入。ZIPに本体なし |
| NumPy | >=1.24,<3 | 2.3.5 | BSD 3-Clause [R20]、本体なし |
| SciPy | >=1.11,<2 | 1.17.0 | BSD 3-Clause [R21]、本体なし |
| setuptools | >=68 build用 | 84.0.0 | ビルド環境で使用、本体なし |
| Matplotlib | >=3.7,<4 任意 | 3.10.8 | plot専用、本体なし。再配布時は当該版のLICENSEを確認 |
| unittest | Python標準 | 標準 | テストにpytestは不要 |

NumPy/SciPyのwheelはBLAS/LAPACK等を同梱する場合があり、上の表だけではbinary bundle全体のライセンス一覧にならない。
今回のZIPはプロジェクトコードと生成結果のみを配り、依存ライブラリをvendorしていない。

`requirements-reproduce.txt` は今回のcore version snapshot。Python3.12で使用する。
最小サポート版すべてを実測したわけではない。CIマトリクスは同梱するが、Hosted CIは今回未実行。

## 候補を追加する際の判断

| 候補 | 確認した配布条件 | 採用時の注意 |
|---|---|---|
| MFEM | BSD 3-Clause [R11] | 追加solver/mesh依存を含む実際のビルド構成を記録 |
| Palace | Apache-2.0 [R12] | 依存パッケージは各ライセンス。3D基盤を自前で全実装する前に評価 |
| Gmsh | GPL v2以降＋指定の例外 [R9] | 例外を自社コード全般への許可と誤読しない。Python API/結合物の配布形態を検討 |
| GetDP | GPL [R13] | 実際の版の条文とsolver同梱条件を確認 |
| openEMS | GPL v3以降、CSXCADはLGPL v3以降 [R14] | 複数コンポーネントを区別 |
| NGSolve | 公式LICENSEを確認 [R17] | このseedに導入なし。Netgen・オプションライブラリを含め版を固定して評価 |
| cavsim2d | READMEにMIT [R6] | ABCIなど別由来実行形式の再配布を別に確認 |
| SLEPc/PETSc | 今回導入なし | 実際に採用する版とMPI/数値依存を含めて監査する |

本プロジェクトのApache-2.0は、第三者ライブラリやbinaryをApacheへ変更するものではない。
別プロセス呼出し・中間ファイル交換を選ぶ場合も、配布条件が自動的に消えるとは主張しない。
新規依存は、計算精度・メッシュ機能・測定したメモリ/時間の必要性に結び付けてADRを追加する。

## オフライン運用

生成HTMLの任意の統合検証は、既設Node 22とChromeを別プロセスで利用する。
今回の実測はNode v22.22.1とChrome/151.0.7922.137。npm依存はなく、計算・可視化の実行時依存にも加えない。
本体をZIP/wheelへ同梱しない。検証は一時プロファイルとローカル結果ファイルを用い、ページの外部HTTP通信を遮断する。
採用理由と範囲はARCHITECTURE.mdのADR-006、実行記録はBROWSER_VERIFICATION.md。

solverとテストは依存導入後にネット接続を使用しない。
完全オフライン導入が必要な場合は、対象OS/Pythonで `pip download` によりwheelhouseを別途作成し、
ハッシュと依存ライセンス一覧を添えて配布する。今回のZIPはwheelhouseを含まない。

## GUI試作からの方式選定 — 2026-09-06

ADR-009によりPython標準HTTPサーバーと同梱HTML/CSS/JavaScriptを採用する。
追加Python/npmライブラリなし。GUIでの場描画には既存Matplotlibのplot extraが必要。
利用者は既存ブラウザーを使用し、ChromeやNodeをアプリに同梱しない。
`verify_gui.mjs` は任意の開発時検証ツールで、実測はChrome 152.0.7977.82 / Node 23.11.1。
Tkはこの環境では表示環境不足、Qtは未導入。両者のライセンスや性能が同等だという判断ではない。

新規GUIファイルの可読性を整えるため、開発時だけPrettier 3.6.2とRuff 0.15.20を使用した。
Prettierは`/tmp/superfish-gui-npm-cache`から明示したJS/HTML/CSSへ適用し、
package.jsonやnode_modules、実行時依存は追加していない。Ruffは新規Pythonファイルに限定した。
参照は[Prettier CLI](https://prettier.io/docs/cli)と
[Ruff formatter](https://docs.astral.sh/ruff/formatter/)の公式文書。ツール本体の同梱なし。

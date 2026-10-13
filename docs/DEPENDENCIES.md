# 依存関係と配布方針

<a id="current-environments"></a>

## 現行core/GUI環境契約（2026-10-13、RF-02）

依存範囲は `pyproject.toml` のNumPy >=1.24,<3、SciPy >=1.11,<2、
任意のMatplotlib >=3.7,<4（`plot`）を維持する。Pythonのサポート下限は3.10、
開発指定は `.python-version` の3.12。新lockやsolver依存は追加していない。
GUIと全unitを含むfull validatorは`plot`環境で実行する。core-onlyは全GUIテストを
skipしてfull合格とせず、CLI・説明付きGUI拒否と選択した非GUI契約を別に検査する。

| 実測した独立環境 | Python | NumPy / SciPy | Matplotlib | 確認した範囲 |
| --- | --- | --- | --- | --- |
| core 3.10 | 3.10.21 | 2.2.6 / 1.15.3 | 不在 | 同じwheel、CLI、GUI拒否、16資産、既存5unit |
| core 3.12 | 3.12.3 | 2.5.4 / 1.18.1 | 不在 | 同じwheel、CLI、GUI拒否、16資産、既存5unit |
| plot 3.10 | 3.10.21 | 2.2.6 / 1.15.3 | 3.10.9 | 同じwheel、F02実HTTP/認証/strict操作と要求サイズの既存3unit |
| plot 3.12 | 3.12.3 | 2.5.4 / 1.18.1 | 3.11.2 | 同じwheel、F02実HTTP/認証/strict操作と要求サイズの既存3unit |
| 既存開発環境（変更なし） | 3.12.3 | 2.5.2 / 1.18.1 | 3.11.1 | RF-02のfresh環境と区別。過去専用受入の実行版は各記録で確認 |

範囲からの解決なので、別日/OSで同じ版になる保証はない。3.12の実測版を3.10へ固定していない。
全パッケージ版・wheel/SHA・各環境の実行記録は `out/rf02-environments-20261013/`。
coreの5unitはf、独立Bessel場、エネルギー、Q/G/加速器R/Q/TTF、保存と破損拒否の既存gateを使用し、
許容差を変更しない。1環境につき既存2求解fixtureを使用する。
F02の不在注入によるERROR 1、空cacheでのoffline導入失敗、Python取得時の既存bin非置換warningも保持する。
成功したHTTPはlocalhost権限を持つ環境で実行し、skipはない。
8個別test IDを二Python環境で確認した計16実行であり、全unit/seed/full/実ブラウザー受入ではない。
依存宣言・FEM/RFを変えていないため、このカードで新fullは実行せず、RF-03の広範統合で行う。

開発・GUI受入用の新規環境:

```sh
uv venv --python 3.12
uv pip install --python .venv/bin/python -e '.[plot]'
OPENBLAS_NUM_THREADS=1 uv run --no-project --python .venv/bin/python python scripts/validate.py --out out/validation-new
```

core-only契約は別の新規環境で実行する（既存plot環境をcoreと呼ばない）:

```sh
uv venv --python 3.12 .venv-core
uv pip install --python .venv-core/bin/python .
uv run --no-project --python .venv-core/bin/python python scripts/check_core_environment.py --out out/core-new
```

`.github/workflows/ci.yml` は両Pythonのcore jobと、`plot`付きfull jobに分ける。
uv 0.12.5を指定し、[公式setup-uv](https://github.com/astral-sh/setup-uv)のv10.3.0 commitを固定した。
これは環境設定の修正であり、Hosted CIを観測した証拠ではない。CIは未実行。
wheelの全製品Python源・16資産を現sourceへ照合し、legacy資産を同梱していないことを確認する。
納品/OS追加/依存binaryの再配布監査はV02以降の独立条件として保持する。

## 過去の納品benchmarkを再現する環境

`requirements-reproduce.txt` は元のPython 3.12.13、NumPy 2.3.5、SciPy 1.17.0の
core版snapshotを保持する。現開発環境や全サポート版のlockではない。
元Pythonを別環境へ取得し、同ファイルと製品を同時に解決する:

```sh
uv venv --python 3.12.13 .venv-benchmark
uv pip install --python .venv-benchmark/bin/python -r requirements-reproduce.txt .
uv run --no-project --python .venv-benchmark/bin/python superfish-ng capabilities
```

この手順の新benchmark再実行はRF-02で行っていない。後続の図/GUIには対応する`plot`も必要で、
core snapshotだけから過去のMatplotlib版を推測しない。以下は日付付きの依存調査・配布履歴。

## A01の候補比較環境 — 2026-09-14

ADR-018/[A01比較](A01_BACKEND_COMPARISON.md)のため`/tmp/superfish-a01-reference-20260914`へ隔離導入した。
cavsim2d0.1.0/固定48741ffの選択Pythonだけをeditableで読み、実行形式は取得しない。
NGSolve/Netgen6.2.2606はLGPL-2.1-only、Gmsh4.15.2はGPL v2以降と添付例外、netgen-occt7.8.1は添付LGPL2.1、
ngsolve-openblas0.3.33はBSD-3-Clause。metadataと添付licenseを確認した。
NumPy2.5.2/SciPy1.18.1は現製品環境と同版。core宣言だけではIPython importに失敗し、公式jupyter extraを補った。
IPython9.17.1/ipywidgets8.1.9を含む全版をbenchmarks/cavsim2d/a01-20260914.jsonへ保存した。
環境の約1.1 GiBを製品配布へ含めない。MITのwrapper条件を依存binary全体へ拡張しない。
比較solveはオフライン。測定後の決定は製品組込み見送りで、pyproject/通常環境は不変。

## G02の独立照合環境 — 2026-09-08

既存ADR-011のNGSolve参照を一般輪郭へ拡張。検証専用
`/tmp/superfish-g02-reference` にngsolve/netgen-mesher 6.2.2606、
ngsolve-openblas 0.3.33、netgen-occt 7.8.1、NumPy 2.5.3、SciPy 1.18.1を導入。
最初に継承したシステムSciPyとNumPyが不整合だったため、system-site-packagesを
無効化し、上記の既存参照実測版で隔離した。通常製品の依存・既定環境は変更していない。
パッケージの既存ライセンス記録は以下。生成メッシュは自前方式を使い、Netgenは独立参照のみ。

## P0-01の検証専用環境 — 2026-09-07

ADR-011によりNGSolve独立照合だけに導入。製品依存・配布物には追加しない。
Python 3.12.3/Linux、`/tmp/superfish-ng-independent-20260907`、OPENBLAS_NUM_THREADS=1。
初回sandbox内のPyPI接続はDNS失敗、ネットワーク許可で再試行して導入した。
実行中の通信なし。パッケージmetadataと添付LICENSEから確認した情報:

| パッケージ | 実測版 | metadata/添付条件 |
|---|---|---|
| ngsolve | 6.2.2606 | LGPL-2.1-only、添付LICENSE確認 |
| netgen-mesher | 6.2.2606 | LGPL-2.1-only |
| ngsolve-openblas | 0.3.33 | BSD-3-Clause |
| netgen-occt | 7.8.1 | 添付LICENSE_LGPL_21.txtあり。バイナリ全体の再配布監査は未実施 |
| numpy | 2.5.3 | metadata: BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| scipy | 1.18.1 | BSD、wheelにはBLAS等の別条件を含む |

参照: [NGSolve公式LICENSE](https://github.com/NGSolve/ngsolve/blob/master/LICENSE)。
製品への採用や再配布を決定したものではない。API参照・実測精度/自由度/時間は
INDEPENDENT_COMPARISON.mdを参照。

## 0.1.0の納品時に使用したもの（履歴）

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

# N02入力・来歴工程：幾何/表面比較の実行計画

2026-10-07後続：[元場対応・保存・旧楕円場診断の互換受入](N02_GEOMETRY_SURFACE_FIELDS.md)を追加。
元入力仕様は不変。五量/幾何/求積/peak集約は後続。以下は入力工程の履歴。

2026-10-07。N01を `823e9cd` で受入後、N02の最初の有界工程として
catalog入力・全Case/独立幾何/既存参照の来歴検査を実装した。
**N02はIN_PROGRESS**。ここではmesh生成・FEM求解・保存場の再構築を行わず、
幾何/FEM/場/求積/ピーク収束の数値受入はすべてNOT_RUNに保つ。
親G03/N03、元123カード・互換32要件・全goalは継続する。

## 実装と使い方

[geometry_surface_plan.py](../src/superfish_ng/geometry_surface_plan.py) の
`build_geometry_surface_plan` は版1の厳格な要求を受け付ける。
必須項目は `schema_version`、`document_type=geometry_surface_plan_request`、
`catalog`、その `catalog_sha256`、順序を明示した非空の `case_ids`。
任意の `reference_directory` は旧成果物の基点。保存時には絶対パスへ解決する。
未知キー、重複JSONキー、boolを整数/数値に見せた値、未対応物理、緩めた閾値を拒否する。

[N01 catalog](n01_geometry_surface_cases.json) の全recordを検査してから選択する。
未選択recordの不正を無視しない。対象はN01の楕円体・丸め/鋭角二ローブという
明示数学仕様であり、任意曲線の独立幾何参照を実装したという意味ではない。
各系列の元全曲線/axis・PECタグ・規格化・電圧規約を固定し、弦許容差3水準と
uniform FEM level 0/1/2の全Caseを生成する。各幾何の元meshを一つに固定して
追加uniform細分する要件を各行へ保持する。45点は計画数で、求解数は0。

`save_geometry_surface_plan` は排他的に書き、`read_geometry_surface_plan` は
要求から全入力・独立値・参照SHA・全製品Python源SHAを再構成して完全一致を要求する。
symlink、検査中の入力/旧成果物/実装変異、旧成果物のhash不一致を拒否する。
保存結果を変更してNOT_RUNをPASSへ変えることはできない。

元[専用CLI](../scripts/validate_geometry_surface_convergence.py) に入力計画を追加した。
例では未使用の出力先を指定する。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
  uv run --no-sync python scripts/validate_geometry_surface_convergence.py \
  --catalog docs/n01_geometry_surface_cases.json \
  --catalog-sha256 389f62dd1ae053f05a46dc28a949c23e38928cdb9764c09a0727c478e5240433 \
  --case N01-rounded-two-lobe N01-sharp-two-lobe --plan-only \
  --out out/n02-plan-example-unique
```

`--case`省略は全record。catalogには現段階で `--plan-only` と明示SHAを必須とし、
未実装の数値実行を成功表示しない。入力の検査後だけ新規出力を作る。
元 `--archive` 経路は保持し、数値関数とmkdir以降の全数値bodyは元版とAST一致する。
既存archiveをここで再FEMしたという記録ではない。

## 独立幾何と参照の区別

幾何の基準はnativeのmoment関数を呼ばず、楕円体の閉形式と二ローブの明示r(z)から
面積・回転体積を計算する。全解析曲線もパラメータから別に生成して全宣言を照合し、
同じ面積・体積だけを持つ異形状を受け付けない。宣言/native/別基準を2e-12で検査する。
二ローブの積分誤差推定はSciPyの推定であり、形式的な誤差上界とは呼ばない。

独立検査は丸め二ローブを寸法1/2へ変え、Aが1/4、Vが1/8になることを確認した。
さらに元体積の1%変異、フィレット寸法だけの変異、鋭角への有限ピーク要求を拒否した。
鋭角はSINGULAR_GEOMETRYとNOT_APPLICABLE_SINGULARを保持する。
離散ピークの安定性から有限物理ピークの成功へ変えない。

球だけはSphereTMを元FEMに依存せず再生成し、独立PEC根条件と両R/Qの半値関係も照合した。
AVAILABLEは解析参照が存在するという意味であり、新FEMとの照合はNOT_RUN。
非球形の独立Maxwell/物理ピークはnull/UNVERIFIEDのまま。
自作の最細FEM、旧楕円の五量区間、validator自身の出力を独立参照へ昇格させる要求は拒否する。
独立現代/black-box参照の新adapterはこの工程には含めず、N01の入手経路を保持する。

既存report4件はSHAと元PASS/passedを検査してVERIFIED_HISTORYを付ける。
これはhistorical_diagnostic_onlyであり、NGと独立現代ソルバーの比較報告でも
この新形状の独立参照として自動採用しない。欠落はUNVERIFIEDで再生成しない。
SHA不一致・FAIL・相矛盾した元statusは拒否する。
楕円catalogの最細区間は実際の元reportと完全一致を要求する。
過去の1モードCaseと新3モードCaseの受入範囲は合併しない。

## 実行証拠と残る原条件

rawは `out/n02-geometry-surface-plan-20261007/`。
最初のmissing module ERROR、旧baseline項目名の実装誤記FAILと修正前sourceを保持した。
affineのclass selector誤記2 ERRORも保持し、正しいclassの2件だけ追加実行した。
N01コミット後の注記時にuv cache設定を省略してread-only cacheで失敗した操作は、
所定の `/tmp` cacheを指定して修正した。FEMや製品依存の変更はない。

| 実行 | 実終了/範囲 |
|---|---|
| 独立moment変異の新1件 | 修正後0、0.289秒 |
| 残り新6件 | 0、9.456秒。全45計画/独立尺度/strict/参照欠落・自己参照拒否/旧SHA・区間/保存・変異 |
| CLI新1件＋surface metadata旧4件 | 0、2.273秒。新1件は実subprocess、既存出力・未実装数値実行拒否も確認 |
| affine metadata旧2件 | 正しいselectorで0、0.013秒 |
| 全五ケースの実CLI入力計画 | 0、INPUTS_VERIFIED、planned45/newFEM0。保存全再生一致 |

新8＋直接6＝14個別unitを分割受入。成功済みの7件をCLI追加だけのために繰り返していない。
元1190 Python源の変更は専用CLI一つのみ、新規2源を加え1192。
元数値関数/楕円数値body・solver/RF定義/全閾値は不変。
新FEM/seed/full/legacy/独立外部求解は0、新依存・外部資料・legacy内部参照はなし。

| N02原条件 | 現在 |
|---|---|
| 新ケースを入力指定で受け付ける | 入力/来歴計画を限定受入。実FEM/保存行列の指定は後続 |
| 幾何差/FEM差/求積差/元場対応/ピーク上下界を別報告 | 別NOT_RUN欄を設けた。元場による数値報告は未実装 |
| 参照来歴を検査し、欠落をUNVERIFIED | 本工程の既存参照/解析球を受入。新独立参照adapterは後続 |
| 故意のピーク未収束・場不一致・幾何未確認で失敗 | 幾何宣言/物理/有限ピーク条件の不正拒否のみ。実場・ピーク反例は後続 |
| 元楕円成功の判定と一致 | 元関数/数値bodyと元区間の一致を確認。新比較器の判定再生は後続 |
| 自分の出力を独立参照へ使わない | 自己FEM参照の入力拒否を確認 |

次はN02の元保存3×3行列/個別ID・幾何間共通領域のsample/被覆・欠測・全量区間/求積別報告。
実場不一致・未収束の反例と元楕円の新比較器による判定一致が揃うまでN02を閉じない。
N03の全系列物理検証、D07の採用評価も未受入である。

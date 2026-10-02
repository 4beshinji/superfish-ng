# 元区分形状法則と参照比較の受入（P04-b-a）

2026-10-02、基準 `3cb8f50`。親P04-bを形状/比較要求（a）、実調整/全試行所有保存（b）、所有worker/親監査（c）へ分割した。本記録はaだけの受入である。

## 挙動と契約

`PlanarPiecewiseShapeLaw` は元の明示三角形meshを束縛し、各頂点のxy変位をパラメータの有限多項式として宣言する。係数は昇冪、最大8次、m、パラメータは無次元。全試行を元Projectから生成し、前試行の丸めを累積しない。元境界の全頂点を保持するため、元では共線だった節点が変形で角になる場合も境界の弦へ置換しない。

各元セルの符号付きJacobian多項式を有理数で構成し、閉区間の左端正値と既存Sturm根数基盤の根不存在で区間全体の正値を検査する。これは全域の埋込み証明ではない。実試行の丸め後座標を独立にPlanarMeshへ渡し、交差/重なり/T接合などを拒否する。非零有理座標のbinary64ゼロへのunderflowも拒否する。

`PlanarPiecewiseShapeMapping` は元Project/法則/双方のパラメータ/細分数を保存する。両native meshの元法則からの再生成と配列完全一致を確認し、共通dyadic参照分割の元セル番号と双方の重心座標を保つ。改変meshの診断を先に行い、その後に実meshの幾何を再検査する。比較面積は前側の物理xy面積、TE輸送はセルごとの随伴行列である。既存アフィン形状比較の同じ算術を `planar_reference_partition.py` に集約した。

追跡要求/結果version10と調整要求schema_version4を追加した。旧追跡1〜9、旧調整1〜3を維持する。新版調整は `deformation`、元区分法則、同じbounds、既存identity_recoveryを必須にし、検索と最終細分の比較を元参照へ接続する。固有値やRF計算の式、正規化、スペクトルguard、既存許容差は変更しない。

このカードでは新版要求のtrial生成/比較と実FEM対照まで確認する。新版の実調整全工程、可搬な全trial所有保存/再開、worker操作、GUI、親P04/P04-bの受入は後続カードである。

## 独立した不変量と負の対照

- 区間内部の偶数重根 `(p-3/8)^2`、端点零、負Jacobianを拒否し、同式に正の `2^-48` を足した対照を受け付ける。端点だけの標本検査では内部重根を検出できない。
- 右半分だけの伸縮/せん断で既知面積 `.5*(1+p/16)`、境界全節点、順不同の元からの再生成、元不変を照合する。
- C字形の細い帯を端で交差させる反例は、全セルの区間Jacobian検査を通るが、p=1の実幾何で拒否される。局所正値と全域妥当性を別に検査する。
- 参照比較をP04-aの独立した有理数交差overlayとTE/TM、順/逆で照合し、各native親セルの面積被覆と物理電場Gramを確認する。1ULPの元mesh改変、予算超過、版/単位/形状法則の取り違えを拒否する。
- 90度回転と2倍拡大の実TE/TM FEMで `f_new/f_old=1/2`、元スカラー/ベクトル場の回転・振幅、固定 `U'=3 J/m`、電気/磁気エネルギー各1.5 J/m、G不変、Qの平方根2倍、個別追跡を照合する。非アフィン変形一般の固有値則は主張しない。

基準版の調整moduleへ新版要求を渡すとschema_version1〜3のみとして拒否されることを、隔離したmodule読込で記録した。これはAPI未対応の再現であり、旧FEMが誤った数値を返した証拠ではない。

## 実行と証拠

runnerは既存lock環境の `uv run --no-sync python`、`OPENBLAS_NUM_THREADS=1`、`PYTHONPATH=src:tests`、`UV_CACHE_DIR=/tmp/superfish-ng-uv-cache`。標準unittestを使用した。

初回の新7件は4.510秒PASS（終了0）。追加のunderflow/版/各親面積を含む選択29件は146.388秒、28PASS/1FAIL（終了1、session36755）。失敗は旧 `test_nested_partitions_area_transport_and_exact_regeneration` の1ULP改変入力が、従来の `differs` より先に追加幾何検査へ届いたことによる。許容差/期待値を緩めず、再生成一致検査を先に戻し、続いて実meshを再検査する順序へ修正した。

最終修正後は `python -m unittest -v test_planar_piecewise_shape test_planar_affine_shape_mapping test_planar_tuning_jobs` の17件が45.567秒PASS（終了0、session64698）。初回はこの3moduleに加え `test_planar_affine_shape`、`test_planar_tuning`、`test_planar_tuning_recovery`、追跡strict2件を選択した。影響する17件を修正後に再確認し、変更の影響を受けない初回12件の成功を保持する。分割した29件の成功証拠であり、一度の29件成功とは扱わない。

証拠は `out/p04ba-planar-shape-20261002/`。`baseline-rejection.json`、初回 `selected-tests.log`、修正後 `recheck-tests.log`、各開始hashと終端auditを保持する。初回と修正後の各実行中に394製品ファイルhash不変を確認した。全handleは終端、src固定解除。製品srcを各worker実行中に固定した。

canonical axisymmetric TM経路は変更していないためseed/全validateは実行していない。GUI/曲線/材料/独立remesh調整/連続パラメータの個別mode同定の受入をこの結果から推論しない。

## 来歴と判断

既存PlanarMesh、P04-aの場比較、アフィン形状の参照細分、独自の有理多項式/Sturm基盤を再利用した。Jacobian/面積/相似場/RF則は本実装の数学的対照として使用した。新外部資料、依存、legacyソース/実行物の読取・コピー・実行はない。製品解法はFEMのままであり、解析対照はテスト専用である。

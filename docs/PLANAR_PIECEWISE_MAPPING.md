# 平面の明示区分写像と領域検査 — 開発カードP03

2026-10-02受入。`planar_piecewise_mapping.PlanarPiecewiseMapping` は、対応する二つの
比較三角形分割で連続な区分アフィン写像を宣言する。全域で一つのアフィン変換に
ならない変形を扱う。各セル内部は一次写像に限定し、滑らかな非線形写像や曲線境界は
この版では受け付けない。追跡・履歴・調整への接続は後続P04であり、本カードの完了を
親互換課題P02の全受入とは扱わない。

## 契約とAPI

入力は元/先の `PlanarMesh` 比較分割。両側で同じ頂点番号・三角形接続を持つ。
比較分割は実FEMメッシュとは独立でよく、実FEM側の番号や境界細分数の一致は要求しない。
全座標はSIのxyメートルで、binary64座標の値を厳密有理数として評価する。
`to_dict` / `from_dict` は `name=planar_piecewise_affine`、`mapping_version=1` の
厳密宣言で、二つの完全なmesh宣言と資源上限を保存する。未知キー・未対応版・不正値を拒否する。
既存の追跡要求版1〜8へこの宣言を渡すことはまだできない。

各側の分割を再構築し、既存のPlanarMesh契約で辺交差・重複・T接続・頂点link・
円板位相・単一外周・正のセルJacobianを検査する。さらに有理数の外周corner列と
宣言polygonの完全一致、全セル面積和の厳密一致を検査する。面積一致だけを被覆証拠にしない。
両側が有効な同一接続の埋込分割であるため、対応頂点の一次写像は共有辺で連続し、
各セルと全外周を一対一に写す。反転写像はこの版の範囲外。

セルの元/先の辺列行列をP/Qとして `A=Q P^-1`、`F(x)=A x+t` を厳密に計算する。
`linear_xy`、`jacobian_determinants`、`current_to_previous_linear` はセル順の読み取り専用配列。
厳密に正の `det(A)` を要求し、最終binary64変換で非有限・非零から0・行列の特異化/反転が
生じた場合は停止する。表示した浮動小数値を厳密区間や物理誤差上界とは扱わない。

- `map_points(points_xy_m, partition_cells)` は指定した閉比較セルへの所属を有理数で確認し、
  元点の像を評価して最後にbinary64へ丸める。元FEM場の補間・生成は行わない。
- `reversed()` は二つの領域を交換し、各セルの厳密逆写像を再計算する。
- `verify_planar_piecewise_domains(previous_mesh, current_mesh, mapping)` は各側をそれぞれ
  既存の厳密アフィンoverlayの恒等写像で交差分割する。全外周一致と各実FEMセルの厳密被覆を確認する。
  戻り値の `previous` / `current` は各側のSI面積測度を持つ独立overlay。
  各overlayの `previous_cells` は比較セル、`current_cells` はその側の元FEMセルを指す。
  この二つは元/先FEM場の共同比較分割ではない。P04では写像を介した共同分割を別途作る必要がある。

`max_partition_triangles`（既定250000）は各宣言分割の構築前、`max_overlay_triangles`
（既定250000）は各側のoverlay構築時に適用する。`max_candidate_tests`（既定2000000）は
各側の候補探索に個別に適用する。限界超過はValueErrorで停止する。

## xy場の比較規約と独立不変量

`current_to_previous_linear` は各セルの `adj(A)=det(A) A^-1`。
既存アフィン比較のTE scalar-curl規約を区分ごとに保持する。
`R=[[0,1],[-1,0]]` とすると、同じscalarを `h_current(F(x))=h_previous(x)` と写したとき、
`grad_current=A^-T grad_previous`、従って
`adj(A) R grad_current = R grad_previous` となる。
これは比較座標でのxy成分規約であり、非一様変形から新たなMaxwell固有場や周波数を
生成する法則ではない。TMのEz scalar、U′の規格化、物理RF量やモードIDの受入はP04以降で検査する。

独立対照には、単位正方形の `x<=1/2` で `F=(x,y)`、右半分で `F=(2x-1/2,y)` を用いた。
Jacobianは左1/右2、像は幅3/2の矩形。

```text
∫元 x^p y^q det(A) dxdy = (2 - (1/2)^(p+1)) / ((p+1)(q+1))
∫像 X^p Y^q dXdY       = (3/2)^(p+1) / ((p+1)(q+1))
```

この直接解析式を独立な期待値として、総次数4までの6組と三尺度で三角形Gauss積分を検査した。
右半分にyせん断を追加した例で共有辺・正逆と上記curl恒等式を検査した。
一般アフィン極限では既存 `PolygonExactAffineRemeshMapping` の移送係数と一致する。

## 検証と範囲

新7件と既存25件、計32件が1.871秒でPASS（終了0）。
実行ログは `out/p03-planar-piecewise-20261002/selected-tests.log`。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
uv run --no-sync python -m unittest -v \
  test_planar_piecewise_mapping test_planar_tracking_exact_affine \
  test_planar_tracking_overlap test_planar_mesh \
  test_planar_tracking_exact_mapping.ExactAffineMappingTests.test_strict_versioned_declaration_and_unresolved_field_transform \
  test_planar_tracking_exact_mapping.ExactAffineMappingTests.test_inverse_adjugate_uses_exact_determinant_before_rounding
```

| 条件 | 確認した証拠 |
| --- | --- |
| 非アフィン面積/多項式積分 | 既知区分座標写像の直接解析式、三尺度 |
| アフィン極限/xy変換 | 既存の厳密adj係数、独立scalar-curl恒等式、正逆行列 |
| 連続性/全領域被覆 | 共有辺からの二重評価、独立3×4/5×3メッシュの各セル被覆/再構成 |
| 欠落/重複/反転/折返し | 四種の不正分割を拒否、異なるセル番号/接続も拒否 |
| 面積だけでは不十分 | 同面積の並進領域を拒否、既存交差/重複/T接続検査を再確認 |
| 丸めずれ/厳密入力/予算 | 従来meshで許される2^-54 m境界ずれを拒否、厳密往復/版/型/範囲外点/事前上限 |

初回の新7件は6件PASS・1件ERROR。アフィン極限テストが、既存APIの厳密入力契約に
非対応のNumPy行列を渡したためで、テストをlistとPython floatへ修正した。
製品や既存入力契約・許容差を変更せず、上の最終選択検証で確認した。
初回失敗を含む結果を単一の初回PASSとはしない。

環境はuvから既存.venvを `--no-sync` で使用し、Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1。
新規依存なし。新幾何APIと既存の直接数学依存に限定した検証であり、既存FEMを含む回帰は
上記モジュールに含まれる分だけ実行した。seed TMの組立/場/RFは変更していない。
全unittest/全validate、seed再実行、GUI、Hosted CI、新Wine比較は未実行。

来歴：既存自作のPlanarMesh検査、有理数corner判定と厳密アフィン交差APIを再利用し、
区分写像と解析対照を新規実装した。新外部資料・legacyソース/バイナリ参照はない。
受入はP03幾何契約まで。次はP04の元場比較・形状法則・保存履歴・調整への接続。

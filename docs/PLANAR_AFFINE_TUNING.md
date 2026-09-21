# P01 — 平面多項式アフィン調整の接続と受入

2026-09-22、基盤 `8222ed8` に対する実装。P01の専用条件を受入。
親P02/D02と全計画は継続し、個別ID回復は次のP02、GUI拡張は後続カードで扱う。

## 要求と試行

`superfish_ng_planar_tune` schema_version 2は版1の全項目に `shape_law` を加える。
parameterは `deformation`、無次元のboundsは法則の閉区間と一致する必要がある。
[多項式法則](PLANAR_AFFINE_SHAPE.md)の各A係数は無次元、t係数はm、昇冪・最大8次。
全区間の行列式零点（端点・偶数重根を含む）を実FEM/出力作成前に拒否する。
未知キー・不正単位・非JSON配列・異なるboundsを拒否し、未解決の丸め形状は補修しない。
版1の寸法/uniform_scale要求と保存再生を維持する。

元矩形Projectは既存PlanarCaseと同じ点・三角形番号の明示多角形へ変換する。
元多角形はそのまま独立コピーし、全試行を元Projectと法則から生成する。
前試行からの累積変形は行わず、固定U′[J/m]、元偏極・次数・モード数・壁σ・表示単位を保持する。
検索後は既存の実一様細分を適用し、検索周波数gateと別の最終メッシュ差gateを維持する。

実装は [planar_tuning.py](../src/superfish_ng/planar_tuning.py)、
[形状法則/矩形の明示化](../src/superfish_ng/planar_affine_shape.py)。
保存checkpointの外側版1を保持し、内側要求版2と実native/Projectから完全再生する。
旧試行のhash/要求との同一性、別出力への再開、失敗prefix保持の既存処理を通る。
形状法則を保存していない過去checkpointを新法則で再解釈しない。

## 試行間の元場対応

追跡要求/結果版8に
[PlanarAffineShapeMapping](../src/superfish_ng/planar_affine_shape_mapping.py)を追加した。
元Project・多項式法則・両試行値・両細分段数を保存し、両実メッシュを再生成して全配列を完全一致で照合する。
各側の元セル番号/重心座標を保持した共通の二進参照分割を作る。
両メッシュの実座標へ別々に写し、前側の物理xy面積[m²]で元場を積分する。

各比較三角形で実写像F=Jcurrent Jprevious^-1を作り、現側の横Eをadj(F)で前側へ輸送する。
TMの縦Ezはscalarの合成で比較する。既存のアフィン比較と同じ場規約を使う。
[場Gram積分](../src/superfish_ng/planar_tracking_fields.py)には三角形ごとの2×2輸送を追加し、既存の単一行列経路を保持した。
両実FEMの元係数を評価し、新たな固有場や補間した保存場は作らない。

丸めた試行境界を「厳密な大域アフィン像」と断定せず、実形状間の区分アフィン対応として保存/表示する。
全区間で行列式の符号が一定なので、反転時の三角形順序の正規化も両側で一致する。
幾何/輸送が非有限・退化した場合と共通分割予算超過は拒否する。
一般せん断に解析周波数の尺度則があるとは主張しない。
元場の有限部分空間/上側guard/積分次数比較を使い、未解決IDを周波数評価へ昇格しない。

## 条件別の証拠

| P01条件 | 独立検査と結果 |
| --- | --- |
| 有限多項式、単位、全区間拒否 | 基盤のdet=(p−3/8)²反例と微小正対照。新版要求の単位/配列/bounds/未知キー拒否。PASS |
| 元xy Projectから全試行 | 元Project不変・順不同生成、元メッシュ厳密再生成。1 ULP改変拒否。PASS |
| 既存矩形寸法調整との一致 | 同じ6×6グリッドの幅.22 mの矩形と新版多角形の全3固有周波数を相対2e-12で比較。PASS |
| 面積行列式・細分対応 | 尺度/せん断/反転の面積、正逆・片側細分の全親面積被覆、セル別adjugateを独立計算。PASS |
| 回転/尺度の元E/Hと固定U′ | TE/TMの各実FEMで90度回転・2倍尺度、f→f/2、元E/H→回転/2、U′=3 J/mを別検査。全体符号のみを整合。場相対2e-11、f比2e-12。PASS |
| せん断の場積分 | 実元電場Gramを既存の有理数厳密アフィン交差分割で別計算。各Gramを元ノルムで規格化した差2e-12。PASS |
| 実調整・保存・最終細分 | 実順位交換を含む検索2試行→別出力の最終細分→TUNED、両gate/解析目標相対1e-4、完全replay。PASS |
| 既存直接利用先 | 旧寸法/多角形調整、平面追跡、厳密/通常アフィン、旧worker/履歴連鎖。PASS |

主検査は [test_planar_affine_shape_mapping](../tests/test_planar_affine_shape_mapping.py)。
ログは `out/p01-affine-tune-20260922/`。
初回new-tests.logは3件19.730秒、2PASS/1ERROR。ERRORは改変拒否テストが凍結dataclassに直接代入したもので、意図的改変の構成を修正した。
修正後targeted-tests.logは新3＋関連26の29件81.175秒PASS。
field-laws.logは追加TE/TM元場1件0.333秒PASS。
最後にJSON配列のstrict検査だけを追加し、strict-final.logで新1＋基盤3件0.253秒PASS。
この最後の製品差分は入力配列の追加拒否のみで、成功入力の数値経路/場輸送は変更していない。
単一の全件同時実行や現行srcによる全体検証とは呼ばない。

共通実行prefix：
`OPENBLAS_NUM_THREADS=1 PYTHONPATH=.:src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v`。
29件の対象モジュールは `test_planar_affine_shape_mapping test_planar_tuning test_planar_tracking test_planar_tracking_exact_affine test_planar_tracking_affine_remesh`。
全ツールhandleは終了0まで回収済み（初回失敗は終了1として保持）。

TM seed核・材料核は無変更。新分岐の平面比較と既存直接利用先に影響を限定できるため、全suite/seed validatorは実行していない。
新しい外部数学資料・依存・物性値・旧版実行はない。既存Sturm/参照三角形/場比較を再利用する。
受入範囲はP01のアフィン法則と調整経路であり、任意の非線形空間変形・物理枝の連続証明・GUI全操作受入ではない。

# 入出力仕様 v1/v2/v3

## 入力

UTF-8 JSON。トップレベル `schema_version`（1、2または3）とgeometryは必須。
未知キー・重複JSONキー・不正な数値・未対応geometryを拒否する。
材料や境界を入力しなければ自動推定するのではなく、v1の仕様が真空/PECに固定されている。
`epsilon_r` や `boundary:PMC` などを追加するとエラーになる。

```json
{
  "schema_version": 1,
  "name": "pillbox",
  "geometry": {"type": "pillbox", "radius_m": 0.1, "length_m": 0.2},
  "mesh": {"nr": 32, "nz": 40},
  "solver": {"modes": 4},
  "rf": {"beta": 1.0, "conductivity_s_per_m": 58000000, "normalization_j": 1.0}
}
```

profile形状は `{"type":"profile","points_zr_m":[[0,0.05],[0.1,0.1],[0.2,0.05]]}`。
zは0から厳密に増加し、全rは正。点間のRは線形で、両端にPEC端板が付く。

| キー | 既定値 | 制約 |
|---|---:|---|
| name | cavity | 文字列。出力パスとして使わない |
| mesh.nr | 24 | 半径方向分割数、整数>=2 |
| mesh.nz | 32 | 軸方向の目安、整数>=2。各profile区間をceilで分割するため総数は増える場合あり |
| solver.modes | 3 | 正整数、節点数−1より小さい |
| rf.beta | 1.0 | 0<β<=1、一定速度 |
| rf.conductivity_s_per_m | 5.8e7 | 正の有限値、常伝導近似 |
| rf.normalization_j | 1.0 | 正の有限値、全蓄積エネルギー |

極端なアスペクト比・巨大/微小寸法・過大な節点数での数値安定性は保証しない。
v1の従来入力・既定PEC境界・canonical hashは維持する。

### v3: 明示した物理・材料・領域

v3では `model` が必須。形式・対応能力・移行契約は [MODEL_CONTRACT.md](MODEL_CONTRACT.md)。
現時点で受理するのは真空・軸対称m=0 TM・単一interior領域。
v1/v2の入力は通常の読込では移行せず、canonical hashを維持する。

```bash
superfish-ng capabilities
superfish-ng migrate-case examples/pillbox.json --out out/pillbox-v3.json
superfish-ng solve out/pillbox-v3.json --out out/pillbox-v3-run
```

移行先の親ディレクトリは先に用意し、新しいファイル名を指定する。
Pythonでは `superfish_ng.model.upgrade_case(data)` または
`Case(..., model=Model())` を用いる（Modelは `superfish_ng.model` からimport）。
v3へ移行したcaseのhashは版・modelを含むため変わるが、同じメッシュの解とRF量は同じ。
Project/Study/GUI/鏡映/保存再読込は明示modelを保持する。

### v2: 平坦なz端面の対称条件

`"schema_version":2` と `"boundaries":{"z_min":"magnetic_symmetry","z_max":"pec"}` のように指定する。
端面は `pec`（既定）、`electric_symmetry`（自然境界・損失なし）、
`magnetic_symmetry`（u=0の本質境界・損失なし）のいずれか。側壁はPECのまま。
未知の端面キー・境界名、v1へのboundaries追加は拒否する。全PECはv1へ正規化して出力する。
Pythonでは `Case(..., z_min='electric_symmetry')` を用いる。
エネルギー・電圧・R/Qは入力領域の値であり、半領域の値を全空洞の値と解釈しない。
例題では半領域U=0.5 Jとし、明示的な鏡映で全空洞U=1 Jの場を得る。

### v2: 垂直段差のある外壁

`geometry.type:stepped_profile` と `points_zr_m` を用いる。zは0から非減少、半径は正。
同一zの2点による孤立した垂直段差を許す。3点連続の同一z、同一点の重複、逆行するz、
最初・最後の区間が垂直の形状は拒否する。従来profileとv1の拒否条件は変更しない。
mesh.nrは最大半径までの分割数で、壁頂点半径の格子を追加する。nzは非垂直区間の軸分割目安。
例題と検査記録は [SEMINAR_MULTICELL.md](SEMINAR_MULTICELL.md)。

### v2: 元の半径を保持する円弧外壁

`geometry.type:arc_profile` と元の `points_zr_m` を指定し、曲線の区間を以下のように記す。

```json
"arcs": [{"end_index":3,"radius_m":0.003,"direction":"ccw"}],
"chord_tolerance_m":0.000003
```

end_indexは0始まりの頂点番号で、前の頂点からその頂点までが円弧。重複番号は禁止。
directionは(z,r)座標でcwまたはccw。π以下の短円弧のみで、z非減少・正半径の領域を維持する。
元の点・半径・向きと、直線近似の最大弦誤差を別々に保存する。FEM要素自体は直線のP1三角形。
arc_profileにはarcsとchord_tolerance_mの両方が必須。他のgeometryへarc metadataを付けると拒否する。
非常に近い半径格子点は最大半径×32 machine epsilon以内だけ併合する。
円弧も `--reflect-full` に対応する。端点順と円弧終点indexを反射し、半径を維持する。
壁の巡回順も反転するため、反射後のcw/ccw指定は元のままになる。
Wineへの比較用出力は検証済みのccw円弧のみを扱う。一般的なlegacy入力の互換パーサーではない。

### v2: 対角線方向に偏らない交差分割

`mesh.triangulation:"crossed"` は各四辺形の頂点平均へ節点を置き、4つのP1三角形へ分割する。
通常の2三角形分割は `diagonal`（省略時の既定値）。v1の入力・canonical hashは変更しない。
段差の高さが異なる列を結ぶ三角形はそのまま維持し、外壁や円弧の弦誤差を変えない。
nr/nzが同じでも自由度は増える。収束判定は別途必要で、交差分割だけで精度を保証しない。

## コマンド

新しい計算保存はsave_protocol.jsonとsave_complete.jsonを含む。
完了マーカーと全出力hashの検証を通った結果だけをread_solutionで読む。
保存途中の失敗・強制終了では予約ディレクトリが残り得るため、再実行は新しい出力先を使う。
旧結果の読込と新形式の完了検査の違いは [SAVE_COMPLETION.md](SAVE_COMPLETION.md)。

### 限定した旧AF入力から移行する

`superfish-ng import-af INPUT.af --out out/imported-new --nr 32 --nz 64 --modes 1
--conductivity-s-per-m 58000000 --normalization-j 1`。
単一真空・軸接続・全PECの直線/段差/短円弧を受理し、未対応指定は行/列付きで拒否する。
変換後は `superfish-ng solve out/imported-new/case.json --out out/solved-new`。
NGの設定を明示し、旧探索やメッシュの差を変換診断へ保存する。
詳しい変数・文法・制限・受入は [LEGACY_INPUT.md](LEGACY_INPUT.md)。

- `superfish-ng solve CASE --out NEW_DIRECTORY`
- `superfish-ng solve HALF_CASE --reflect-full --out NEW_DIRECTORY`（一端対称・他端PECのみ。鏡映後の全空洞を保存）
- `superfish-ng plot RUN --mode 1 --mesh --probe-z-m 0.02 --out NEW_PNG`（plot依存が必要）
- `superfish-ng converge --levels 8 16 32 64 --out NEW_JSON`
- `superfish-ng --version`

終了コード: 0=成功、1=収束ベンチマークの合格条件未達、2=入力/ファイル/ソルバエラー。
既存出力への上書きは拒否。書込み途中の障害では部分ファイルが残る可能性がある。

## 出力

| ファイル | 内容 |
|---|---|
| case.json | 正規化後の実際の入力。pillboxもprofileに展開される |
| results.json | case hash、環境、規約、mesh規模、全modeのRF量 |
| modes.csv | 各modeを1行としてRF量を記録 |
| fields.npz | 下記の再読込可能なNumPy配列。pickle不要 |
| axis_001.csv等 | z [m] と符号付きEz quadrature [V/m] |
| mode_001.vtk等 | ParaView用の2D meridian三角形と場 |

NPZ:

| 配列名 | 形状 | 意味 |
|---|---|---|
| points_rz_m | (N,2) | r,z [m] |
| triangles | (T,3) | 0-based節点index |
| boundary_edges | (B,2) | 境界辺の節点index |
| boundary_tags | (B,) | axis、pec、electric_symmetry、magnetic_symmetry文字列 |
| boundary_cells | (B,) | 境界に接する要素index |
| axis_nodes | (A,) | z昇順の軸節点 |
| u_a_per_m2 | (N,modes) | Hφ/r、単位A/m² |
| frequencies_hz | (modes,) | 昇順の周波数 |

VTKは **x=r、y=z、z=0** に断面を埋め込む。物理3D軸とviewerの座標を混同しない。
Hφはpoint scalar、Eの円筒成分はcell scalar。Ephasorは−i倍した値。
ParaViewでEを表示する際はCell Dataを選ぶ。回転させる場合は円筒成分のベクトル変換が別途必要。
今回ParaViewアプリによる対話操作は確認していない。

RFキーの式はPHYSICS.md。
`field_construction` に直接固有値計算か鏡映かを記録する。鏡映出力は元のv2入力を
`reflection_source_case` に保存し、部分スペクトルのmode番号であることを明記する。
`*_estimate`は表面場の一次要素推定で、メッシュ独立な設計値を意味しない。
ゼロに近い加速電圧でピーク比が定義しづらい場合はnull。NaN/InfinityをJSONに保存しない。

結果の単位はキー名に含める。`q0`、`transit_time_factor_abs`、`epk_over_eacc_estimate`は無次元。
`bpk_over_eacc_estimate_mt_per_mv_per_m`は mT/(MV/m)。インピーダンスは全長に対するΩで、Ω/mではない。

## 物理長による境界・角近傍の細分化（v2、任意指定）

```json
"mesh": {
  "nr": 96, "nz": 165,
  "boundary_max_edge_m": 0.001,
  "corner_max_edge_m": 0.00025,
  "corner_radius_m": 0.01
}
```

- `boundary_max_edge_m`: 軸を除く外周辺（PECと端面対称境界）の最大実長。斜面では軸方向投影長ではない。
- `corner_max_edge_m` と `corner_radius_m`: 必ず組で指定。折れ線壁の内部頂点のうち方向が変わる点から、指定半径の円盤と交わる**内部辺も含む全辺**の最大長。端板との接合点は対象に含めない。半径は形状の丸め半径ではなく細分領域の大きさ。
- 値は有限の正数。未指定なら従来メッシュをそのまま使う。JSONのnull、v1での指定、不完全な組は拒否する。
- 基底メッシュの辺を中点分割するので、実際の辺は上限より短くなる場合がある。共有辺と所有要素の長辺も細分し、非適合接続を作らない。局所指定でも接続調整により周囲へ細分が広がる。
- 境界長指定はprofile/stepped_profile/arc_profileに対応。円弧は元の弦誤差で線形化した輪郭を保持し、境界細分だけで円弧形状誤差は減らない。角指定はprofile/stepped_profile限定で、arc_profileには明示的なエラーを返す。
- `triangulation` は基底の四辺形分割を選ぶ。追加細分は三角形の辺分割であり、crossed指定時にも追加メッシュの厳密な鏡映対称性は保証しない。

Epkは従来と同じP1片側微分の推定値。特異角のピーク収束を保証する設定ではない。
検証例と計算量は [PHYSICAL_MESH_REFINEMENT.md](PHYSICAL_MESH_REFINEMENT.md)。

## 編集用プロジェクト v1

Case v1/v2は従来どおり直接読み込める。編集情報は別のproject_versionで管理する。
GUI・CLI・Pythonの入口は同じProject.from_dict/loadを使用する。

```json
{
  "project_version": 1,
  "case": {
    "schema_version": 1,
    "geometry": {"type": "pillbox", "radius_m": 0.06, "length_m": 0.09}
  },
  "reflect_full": false,
  "display_length_unit": "mm"
}
```

必須はproject_version=1とcase。reflect_fullはboolean（既定false）、
一端対称・他端PECのときだけtrueを許す。表示長単位はm/mm（既定mm）。初期GUIのフォームはmm表示に統一し、保存時もmmを記録する。
未知キー・重複JSONキーを拒否する。数値の保存単位は表示単位によらずSI。
任意のsectionsは `[{"geometry": <既存geometry>, "count": <正整数>}, ...]`。
各geometryはz=0から始まり、count回平行移動して順に接続する。
一致する接続点は共有し、半径が異なる接続は垂直PEC段差となる。不正な段差接続は拒否する。
円弧半径・向きを保持して終点番号を移し、弦誤差は各円弧部分の指定値の最小値を用いる。
編集時の膨張を防ぐため展開頂点上限は100000。精度を保証する上限ではない。
sectionsを保存する場合、展開したgeometryとcaseのcanonical geometryの一致を必須にする。
`Project.from_sections(template, sections)` で両方を同時に作成できる。

```python
from superfish_ng.project import Project
from superfish_ng.jobs import execute_project
project = Project.load("my-project.json")  # 既存Case JSONも受理
execute_project(project, "out/my-project-new")
```

- `superfish-ng run-project PROJECT_OR_CASE --out NEW_DIRECTORY`
- `superfish-ng gui --workspace out/gui-workspace`（ブラウザー自動起動、plot extra必要）
- `superfish-ng gui --workspace out/gui-workspace --no-browser`（起動URLを表示）

workspaceは計算履歴の保存先として再利用するが、各計算は固有の新規サブディレクトリを作る。
同時に2アプリで同じworkspaceを開かない。Linuxのファイルロックで競合を拒否する。
ジョブ内はproject.json、job.json、log.txt（背景実行時）、solution/（従来の計算出力）、
manifest.json（全出力hashと実装ファイルhash）。完了はmanifest保存後に確定する。
計算中に実装が変わった場合は失敗として新規再実行を要求する。
状態はqueued/running/complete/failed/cancelled/interrupted。completeでも
numerical_validation=not_checkedであり、収束判定とは別。
GUIでの保存はブラウザーのダウンロード。計算入力だけのJSONも出力できる。
操作方法はGUI_GUIDE.md、受入条件はGUI_IO_PLAN.mdを参照。

## 条件群の定義 study v1

```json
{
  "study_version": 1,
  "project": {"project_version": 1, "case": {"schema_version": 1,
    "geometry": {"type": "pillbox", "radius_m": 0.06, "length_m": 0.08}}},
  "kind": "mesh_convergence",
  "parameter": "mesh_scale",
  "values": [1, 2, 4]
}
```

- kind=sweep: 既存の数値フィールドを `/case/...` または `/sections/...` のパスで指定する。
  配列位置は0始まり。値はSI。canonical caseでは円筒もpoints_zr_mへ展開されるため、
  円筒長さは `/case/geometry/points_zr_m/1/0`、値の例は `[0.04,0.08,0.12]`。
- kind=mesh_convergence: parameter=mesh_scale、厳密増加する正整数の倍率列。
  nr/nzを倍率倍、境界/角最大辺長を倍率で割る。細分領域半径と弦誤差は維持する。
- kind=geometry_convergence: 円弧case限定。parameter=/case/geometry/chord_tolerance_m、
  厳密減少する正の弦誤差列。メッシュ設定と円弧半径は維持する。
- 全点の入力を先に検査する。不正なパス、未対応条件、未知キー、非数・不正な値列を拒否する。
  sectionsの値変更は形状を再展開し、case geometryへの直接変更はsectionsとの結び付きを解除する。
- sweepは独立スペクトルの計算であり、番号によるモード追跡をしない。
  同一形状の細分比較だけ、共通の内部点でHφを評価して体積重み付きの重なりを診断する。
  高い一致度と他候補からの分離を要求し、近接縮退・曖昧な対応はUNVERIFIEDにする。
  最大4096個の要素重心での診断であり、連続空間の厳密な内積・誤差上界ではない。
- 周波数、RF量、軸上場の細分変化を別ゲートにする。表面ピークはP1推定として保持する。
  ゼロ分母の相対変化は未定義とし、絶対R/Q差は解釈用に併記する。

`superfish-ng study study.json --out NEW_DIRECTORY` または
`execute_study(Study.from_dict(data), new_directory)` で実行する。
CLIは数値判定FAILの場合に終了コード1。掃引等の未検証はUNVERIFIEDと明示する。
GUIは同じStudyを別プロセスで順次実行し、中止可能。各点を同時に大量起動しない。
study.json、study-results.json、各point-NNNの個別ジョブとmanifestを保存する。
計算完了と数値PASSを区別する。条件群の定義はプロジェクトとは別ファイルで保存する。

バンド同定のCLI: `superfish-ng band RUN --centers-m 0 0.03499 0.06998 0.10497 --out NEW_JSON`。
中心は例示であり、任意の等間隔中心列を指定可能。両端PEC、中心が両端面を含むこと、
元の輪郭頂点・円弧の周期性、実場の同定を検査する。full-end/非周期は拒否する。

## 保存結果の利用

`superfish_ng.saved.read_solution(directory)` は従来save_runの出力を読み込む。
Case hash、配列寸法・有限性・境界、周波数と軸CSVの対応を検査し、再計算しない。
`JobManager.import_result(path)` は完了ジョブまたは従来出力を新しい履歴へコピーする。
旧形式に元の完了manifestがない場合はorigin/source_completionにその事実を残す。
読込検査は数値収束の保証ではない。

- `superfish-ng probe RUN --z-m 0.02 --mode 1 --out NEW_CSV`
  は保存場を401点で評価し、r_m,z_m,Er_quadrature_V_per_m,Ez_quadrature_V_per_m,Hphi_A_per_m,Bphi_Tを出力する。
  同名`.csv.json`にモード番号、周波数、z、標本数、入力hash、U、phasor規約を保存する。
  CSVまたは設定JSONが既存なら上書きしない。Pythonは`export_radial_probe`を使う。
- `superfish-ng compare-pillbox RUN --out NEW_JSON` は一定半径・全PEC円筒を
  独立解析式と比較する。実際のHφからTM0npを対応付け、周波数・RF・軸場の
  誤差を分ける。近接縮退・曖昧なラベルはUNVERIFIED。全モードPASSのときだけ終了コード0。
  Pythonは`compare_pillbox`を使う。例題名による分岐や数値の補正はない。

上記RUNはresults.json/fields.npz等を含むsolutionディレクトリ。管理ジョブでは
`<job>/solution`を指定する。図のキャッシュには場hashと描画実装・依存版を、
プローブには場hashと実装hash・位置・モードを含め、別条件の結果を再利用しない。
GUIは読込直後のSI輪郭を保持し、実際の形状編集時だけmmから再構成する。
表示単位の往復丸めで組立定義とcanonical Caseの厳密一致を壊さないためである。

## 外部メッシュ入力の追加 — 2026-09-07

CLI `solve --mesh mesh.json` とPython `solve(case, mesh_data=...)` を追加。
明示SI/rz・0始まり・全境界タグ付きの三角形JSON。Case schemaは変更しない。
入力検査、生成設定の扱い、保存mesh.jsonとhash、鏡映の仕様は [MESH_INPUT.md](MESH_INPUT.md)。

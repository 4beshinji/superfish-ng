# 異なる初期接続への曲線選択移送：版2計算工程

2026-10-08 JST、ADD-N04-selection-charts-03 **DONE**。開始commit `78870c6`。
[固定仕様](CURVED_SELECTION_CHARTS_SPEC.md)の全参照被覆・二policyを公開Python APIへ接続した。
全131カードは79 DONE/2 IN_PROGRESS/50 PLANNED、原123は76/2/45。
親N04・原互換32要件・全goalは継続。次は04の完全再生とCLI検査。

## 受入条件と実装

両初期メッシュの明示参照座標から、選択外も含む全旧新要素の有理数共通分割を検証する。
その後に旧選択に属する共通三角形だけを集計し、各旧選択要素の交差面積が元参照面積に
厳密一致することを要求する。新要素の正面積交差をintersects、完全被覆をcontainedで選ぶ。
点・辺の接触は選択しない。部分被覆、全親番号/重心座標、元Project、二chartと全予算を保存する。
containedの空結果も成功。参照被覆率を物理面積率やFEM誤差と呼ばず、physical_error_boundはnull。

`curved_selection_transfer`に版2dispatchと専用計算helperを追加した。
循環importを避け、既存`curved_reference_partition`を関数内で読み込む。
builderにはstrict boolの`allow_tm_symmetry=False`を追加し、版2選択callerだけTrueを渡す。
同じ原TM対称セクターと境界折線/tagを検査し、電気/磁気対称を原領域のまま扱う。
TE、組立、鏡映後、P1、自動メッシュへの暗黙chartは受理しない。
旧場比較callerのdefault契約を維持する。初期/最終/共通要素と全辺/組対の予算を適用する。

版2文書の生成までが今回の範囲。既存replayは版1のままで版2を拒否する。
保存改竄/CLI固有検査は04、実ブラウザーは05、独立専用6 FEM/行列/RFは06。
既存版5の場比較成功だけを新版選択の実FEM受入に流用しない。

## 独立検査と直接消費の回帰

新`test_curved_selection_charts`は9個別検査。旧2/新3の初期接続・軸境界追加頂点、
独立番号と逆方向全選択、非nested uniform/marked履歴とfrozen表現、非アフィン旧26/新27、
両z端の電気/磁気対称、sector/境界/向き/型/範囲/予算拒否、入力不変を確認した。

矩形の新側被覆率は厳密に2/3・1/3・1/2、intersects=[0,1,2]、contained=[]。
R=0.1 m、L=0.2 mの旧選択物理面積RL/2=0.01 m²、回転体積2πR²L/3、
Hφ=rの幾何質量R⁴L/5=4e-6 m⁵を閉式と照合した（幾何質量は電磁エネルギーではない）。
旧自作validatorの独立P2基底/微分・8×8 Gauss-Duffyで、元native選択と旧交差合計を
相対3e-12以内で照合。新側はcontained合計≤交差合計≤cover合計を各三量で確認する。
非アフィンと尺度2の面積4/体積8/幾何質量32倍も同じgateでPASS。
製品の物理map evaluatorをこの積分へ流用していない。許容差は仕様どおり不変。

| 実行 | 結果と範囲 |
|---|---|
| 実装前の公開反例 | 閉式一検査が版2未知キーでERROR、終了1。失敗を保存してから実装 |
| 選択した38件 | 新9、入力7、旧selection8/reference6/overlay7、TE版3/4/5尺度1。15.173秒・handle91451終了1。35 PASS、独立積分3件だけscripts import ERROR |
| 最初の3件補完 | root path訂正後、validatorのbare sibling importで3 ERROR。5.102秒・handle15672終了1。元log/helperを保存 |
| import修正後の3件 | 新testへscripts検索pathとbare validator importを接続。10.443秒・handle94297終了0、3 PASS。solveを例外guardし呼出し0 |
| 受入の合計 | 38個別PASS（35成功証拠+修正後3）、反復を加算しない。full/seed/専用validatorではない |
| 元defaultの監査 | 自作NGの開始時archiveと現行builderを矩形[2,8]・非アフィン[26,27]で比較。全reportと両側実評価配列が完全一致、handle99987終了0、FEM0 |

入力7/旧22件の29直接消費は初回で全PASS。修正は新testのhelper importだけなので再実行しない。
最初の6成功new testのmethod ASTは完全一致。旧製品/既存検査は3件補完の前後で不変。
初回wrapperは実TM solve_curved/eigsh各6回を観測、直線_solveは0。
TE経路はこのwrapperに含まれず、TE求解総数を観測値として報告しない。
新幾何9件・補完/監査の追加FEMは0。元FEM/RF核・規格化・物理閾値は変更していない。
seed TM solve経路を変更していないためseedを重複実行しない。

## 証拠と来歴

rawは`out/n04-selection-charts-core-20261008/`。全FAIL/ERROR、開始module/new test archive、
各runner/log/result、`audit-core.py`/`acceptance.json`、source SHAを保持する。
補完runner生成の初回uv default cache拒否（終了2、test/FEM0）も記録し、
既定の`UV_CACHE_DIR=/tmp/superfish-ng-uv-cache`で生成し直した。
実行は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python …`。

元1439対象の変更は二製品moduleだけ、他1437源byte一致。新test追加で1440対象/1227 Python源。
旧selection moduleは追加helper・公開docstringと版2dispatch以外、全AST一致。
default builderの幾何評価は上の独立新旧監査で完全一致。
今回の受入はこの対象検査の範囲であり、過去N03全検証を1440源のfullとして報告しない。
新資料/依存/legacy/外部サービス参照なし。既存自作有理交差、native履歴、独立P2積分、初等閉式を再利用した。

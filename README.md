# Superfish-NG — 0.1.0 research seed

[TEの収束Study](docs/TE_CONVERGENCE_STUDY_PLAN.md)を接続。同一物理Caseの電場・磁場・RFを個別比較し、縮退や積分不安定時はUNVERIFIED。円筒/球形の独立21FEM・GUI三判定・CLI/worker/再起動・標準785件と数値回帰が合格。細分差は物理誤差上界や表面ピーク精度の保証ではない。

[TEの独立パラメータ掃引](docs/TE_STUDY_PLAN.md)を接続。全点の入力検証、TE native保存と別操作の円筒追跡、GUIのR/Q N/A表示を追加。円筒/曲線の独立18FEM・CLI/GUI保存一致・再起動・標準775件と数値回帰を確認。一般形状の追跡は未対応。

[円筒TEのモード追跡](docs/TE_TRACKING_PLAN.md)を接続。Eφによる順位交差・部分空間、全native保存/replay、CLIとGUI履歴へ接続。独立8実FEM・Chrome8項目・標準771件（769合格、2skip）と既存数値回帰を確認。一般形状/曲線写像は後続工程。

[TEのGUI接続](docs/GUI_TE.md)を接続。Eφ/Br/Bzの場表示・SIプローブ・偏波選択とN/A理由を追加。Chrome10項目・独立保存照合/球形解析・標準766件と既存数値回帰を確認した。

[TEのProject・ローカルジョブ](docs/TE_JOBS.md)を接続。通常CLI/worker、完了時の保存場再検証、直接/管理済み取込、元メッシュ保持と管理器再起動を扱う。通常GUIのTE操作は上記で接続。TE追跡等は継続する。

[真空m=0 TE](docs/AXISYMMETRIC_TE.md)を追加。Eφ/rの独立未知数、TEのPEC拘束、場・エネルギー・壁損失、加速量N/A、専用保存/再検証とCLIに対応。直線P1/P2と[曲線P2](docs/CURVED_TE_PLAN.md)に対応し、通常GUIは上記で接続し、追跡等の統合は継続する。

[RF探索の実行内再利用](docs/RF_OPTIMIZATION_REUSE.md)を追加。再開時の完全replayと全nativeファイルの変更検出を維持し、同じ実行内の確認済み祖先の追跡/RF評価を再利用する。保存書式と数値条件は不変。一般性能の受入は継続する。

[RF探索GUI](docs/GUI_RF_OPTIMIZATION.md)を接続。2変数・目的関数・複数制約の入力保存復元、実ジョブの中止と保存再開、試行・水準ごとの個別ID確認付き場表示を行う。再開前の重い検証を管理器のロック外へ移した。開始要求自体の完全検証には引き続き時間を要する。

[RF探索のローカルジョブ](docs/RF_OPTIMIZATION_JOBS.md)を追加。JobManagerで実行・中止・再起動・停止後のcheckpoint選択/再開を行い、3水準のmanifest・祖先・投入予算・所属を再検証する。GUI操作も接続済み。

[RF制約付き2変数探索](docs/RF_OPTIMIZATION.md)を実装。各候補の3水準実FEM、相対写像による個別追跡、制約違反の改善と目的関数探索、予算内の最終細分、全試行の保存再開を接続する。一般変数・一般性能の受入は残る。

[RF設計制約の評価基盤](docs/RF_DESIGN_CRITERIA.md)を追加。保存場を再検証した3水準の包絡で目的関数・複数制約を判定し、未収束/未解決の試行に採用値を与えない。D03の2変数探索器・初期/最終比較へ接続済み。

[外部メッシュ単体の読込と固定形状Study](docs/EXTERNAL_MESH_WORKFLOW.md)を追加。GUIで読込/解除・不正入力時の保持を行い、P1/P2の直線元メッシュを一様細分して比較できる。曲線二次Studyも従来どおり。O02全体は継続中。

[曲線アフィン周波数調整](docs/CURVED_TUNING.md)を追加。設計変数から曲線/元メッシュを変換し、試行間写像を導出して実FEM・追跡・最終細分・保存再開へ接続する。非アフィン曲線変更や制約付き多変数最適化は残る。

[曲線Projectと元メッシュの一括変形](docs/CURVED_PROJECT_TRANSFORM.md)を追加。元分割・接続と二次写像の対応を検査し、RF座標方針と試行間相対写像を明示する。アフィン曲線tuneへ接続済み。一般曲線変更は残る。

[弧ごとの固定分割数](docs/FIXED_CURVE_PARTITIONS.md)を追加。弦誤差条件を維持しながら分割と元メッシュの対応を保存し、曲線二次写像・鏡映・GUIへ接続した。一括変形APIへ接続済み。アフィン曲線tuneへ接続済み。一般曲線変更は残る。

[Project第2版の明示元メッシュ](docs/PROJECT_MESH.md)を追加。通常CLI/Job・GUI読込/保存/実行で指定した接続を保持し、曲線固定幾何Studyと適応入力へ引き継ぐ。曲線tuneの試行ごとのアフィン変形へ接続済み。

[弧の対応を保持するアフィン変形](docs/AFFINE_CONIC_TRANSFORM.md)の幾何APIを追加。回転した楕円・双曲線の両枝を含み、同じfractionの位置・接線・曲率を保持する変換を検査した。Case/元メッシュの一括変形APIへ接続済み。アフィン曲線tuneへ接続済み。一般曲線変更は未実装。

[多項式による非線形座標連動](docs/POLYNOMIAL_TUNING.md)を周波数調整へ追加。設計変数の多項式からprofile座標を作り、実FEM・追跡・二分法・最終細分を行う。両単位表現/両尺度の円筒解析対照がPASS。一般曲線・非多項式関数・制約付き最適化は残る。

[周波数調整の途中保存選択](docs/GUI_TUNING_CHECKPOINTS.md)をGUIへ追加。中止したジョブの保存済み試行を一覧から選び、元ジョブと保存場を再検証して再開できる。一般形状/非多項式連動・制約付き最適化は残る。

[二次境界の空間候補選別](docs/QUADRATIC_BOUNDARY_CANDIDATES.md)を追加。旧自作実装との証明・交差等の最初の拒否理由を維持し、保存済み2,744境界辺の検査単体を中央値23.975秒から0.203秒へ短縮した。全FEM実行や一般形状の速度倍率とは区別する。

[RF合格・表面未達時の明示的一様細分](docs/CURVED_RF_SURFACE_POLICY.md)を追加。元の非球形両尺度・許容差・12回予算で、6イベント/14,665自由度の検証がPASS。既定のR/Q選択は保持し、親採用と五量の停止合格を区別する。

[版5の次計画共有](docs/RF_ADAPTIVE_PENDING_PLAN.md)で、同じ親・確認場のRF選択の再計算を減らした。保存場・request・実装の照合と公開replayを維持し、旧実装との全文書一致を確認した。従来R/Q単独方針の一般収束は未受入。

[適応計算の祖先ジョブ時間](docs/GUI_RF_ADAPTIVE_COST.md)を表示する。再開前・中止したジョブを重複なく合算し、時間未記録・外部出力は不明と表示する。記録されたジョブ時間であり、全workflowの測定とは区別する。

[RF適応版5のGUI](docs/GUI_RF_ADAPTIVE.md)を追加。親・採用列・連続確認を表示し、確認場/採用場の選択、保存再読込、中止後の再開を実ブラウザーで確認した。非球形/両尺度/全workflow費用は、明示した表面細分方針で限定対照を確認した。

[RF適応版5の分岐・保存再開](docs/CURVED_RF_ADAPTIVE_REFINEMENT.md)をAPI/CLI/JobManagerへ接続。元親からの局所細分と確認2回の五量停止を実装し、半球で5イベントの停止・全保存再検証・独立解析五量を確認した。GUI・一般形状/尺度/総費用の受入は残る。

[RF指標の重複再構築](docs/CURVED_RF_GOAL_REUSE.md)を削減。[自動適応の分岐・保存再開の設計](docs/CURVED_RF_ADAPTIVE_PLAN.md)を具体化した。版5の実行・CLI/GUI・反復受入は未実装。

[RF重み付き親要素選択](docs/CURVED_RF_GOAL_INDICATOR.md)を追加。実全域確認の随伴で親残差を局所化し、選択番号から実FEMまで接続した。3形状のR/Q対照差は減少したが、確認/指標費用を含む効率と適応版4への接続は未受入。

[RFの角周波数偏微分](docs/CURVED_RF_FREQUENCY_SENSITIVITY.md)を追加。位相・電場・電磁エネルギーの周波数依存を解析的に微分し、係数随伴との結合を検査した。親子残差と細分選択・効率受入は残る。

[固定周波数のRF随伴](docs/CURVED_RF_ADJOINT.md)を追加。振幅方向を除いた疎連立系と全固有モード展開・行列摂動の照合を実装した。周波数全微分、細分選択器への接続と効率受入は残る。

[固定周波数のRF係数感度](docs/CURVED_RF_SENSITIVITY.md)を追加。複素加速電圧のP2係数ベクトルと両R/Q勾配を、解析積分・有限差分・振幅/位相・Maxwell尺度則、実native場で確認した。適応選択器への接続と効率受入は残る。

[曲線メッシュの図上選択](docs/GUI_CURVED_MESH_SELECTION.md)を追加。実計算空間の要素番号を選び、履歴末尾へ追加する。入力/履歴変更後の古い選択は拒否し、既存履歴・一様段数の両経路で実FEMまで確認。表示は5000要素までで、大規模選択は残る。

[磁気対称の両尺度適応検証](docs/CURVED_MAGNETIC_ADAPTIVE.md)がPASS。6水準の最終停止と追加一様対照の五量差・追跡・高次積分、全水準相似最大1.710e-14を確認した。追加対照差を絶対RF誤差とは扱わず、一般精度/効率は残る。

[曲線適応の単一対称半領域](docs/CURVED_ADAPTIVE_SYMMETRY.md)を追加。鏡映した全PEC境界の滑らかさを確認し、元半領域のRF規約で計算する。両対称/両端の鏡映不変量と半球の両尺度・独立球形五量がPASS。一般接続・幾何誤差・一般精度/効率は残る。

[非球形の両尺度対照](docs/CURVED_NONSPHERE_COMPARISON.md)がPASS。全五量相似差最大8.362e-12、体積保存・Ritz・追跡・積分と追加対照差を確認した。両尺度とも適応100917対一様確認41281自由度で、適応優位は得られなかった。検証対象はdc795e9。一般精度/効率と親N04は未受入。

[履歴を保持する収束Study](docs/CURVED_HISTORY_STUDY.md)を追加。既存の局所細分履歴の末尾へ一様細分を追加し、固定形状の体積不変とRitz単調性、GUIからの作成/保存/実計算を確認した。形状・初期メッシュを変える履歴付き掃引は引き続き拒否する。

[曲線細分履歴のGUI編集](docs/GUI_CURVED_REFINEMENT_HISTORY.md)を追加。局所履歴が保存時に失われる不具合を修正し、段階の追加・順序変更・削除とstrict入力を接続した。Chrome 19項目と実FEM/native一致を確認。5000要素を超える図上選択・形状変更を伴う履歴付き掃引・一般精度/効率は残る。

**軸対称RF空洞を公開された数学から独立実装するOSSプロジェクトの初期版です。**
旧SUPERFISHのソース・実行形式には依存しません。Pythonで形状を定義し、実際に有限要素行列を組み立て、固有モードとRF量を計算します。解析式だけを返すモックではありません。

閉じた真空・軸接続空洞のm=0 TMと、直線P1/P2・曲線P2のm=0 TEを対象とする研究用実装です。TEのGUI専用操作と追跡統合は未対応です。
SUPERFISH全体の置換、旧入力形式の全面互換、KEKの実機モデルとの一致はまだ実現・検証していません。
[限定AF読込](docs/LEGACY_INPUT.md)で、単一真空・全PECの直線/段差/短円弧をNG入力へ変換できます。
`import-af`はNG設定を明示し、原入力と変換診断を保存します。未対応指定は位置付きで拒否します。
プロジェクト名は作業名で、LANL・DOE・KEKの公式製品ではありません。

指定4資料に基づく [セミナー例題の計算と可視化](docs/MILESTONE_SEMINAR.md) のマイルストーンは完了しました。
Wine版SUPERFISHとの3形状の基本モード照合は実施済みで、[比較結果](docs/SUPERFISH_COMPARISON.md)を記録しています。
角部のピーク差については、[表面電場の切り分け評価](docs/SURFACE_FIELD_DIAGNOSTICS.md)で局所メッシュ・固定点・丸み対照を調べています。
[境界実長指定と角近傍の局所細分](docs/PHYSICAL_MESH_REFINEMENT.md)を追加し、固定点電場とPEC接線成分の改善を確認しました。
多セルの段差・円弧、4/7モードの計算・同定・分散曲線・表示を実装済みです。
[最終結果の入口](out/seminar-suite-final-20260905/index.html) から例題・モードを選択できます。
全NG新規計算の9検証ジョブ、7ページの画面検査、対象17モードのWine照合が合格しました。
対象・受入基準・対象外は [受入記録](docs/MILESTONE_ACCEPTANCE.md)、細分の履歴は [多セル記録](docs/SEMINAR_MULTICELL.md) に明記しています。

PillboxのTM010/TM011・長さ掃引・電磁場の図は [演習ガイド](docs/SEMINAR_PILLBOX.md) から実行できます。
`python scripts/seminar_pillbox.py --out out/seminar-new` で例題の計算と結果選択HTMLを生成します（plot依存が必要）。
多セルは `python scripts/seminar_multicell.py --case rounded4 --out out/rounded4-new`。
`--case` はflat4/rounded4/rounded7。数値ゲート未達はFAILとして保存・表示します。
端部比較は `python scripts/seminar_end_cells.py --flat-half-extra-n 384 --out out/ends-new`。
収束確認済みの7セル設定は `--triangulation crossed --levels 64 128 256` を明示します。
全演習の新規計算と入口HTMLは [一括実行ガイド](docs/SEMINAR_SUITE.md)。初回の未達結果も上書きせず保持しています。

## ローカルで開始する

現在の作業checkoutは `/home/sin/code/agent/reserch/superfish-ng` です。
過去の記録にある `/home/sin/code/superfish` は当時の配置です。既存checkoutを移動せず、以下の構造で開発します。

```text
superfish/
├── src/superfish_ng/       # FEMソルバー、RF量、CLI
├── tests/                 # 物理・入力出力・配布の回帰テスト
├── examples/              # pillboxと合成セルのJSON入力
├── scripts/               # 検証、描画、パッケージ作成
├── docs/                  # 仕様、開発計画、今回の動作確認記録
├── benchmarks/validation/ # seedに同梱された基準データ
├── benchmarks/seed/       # 原本のチェックサム
├── out/                   # ローカル実行結果（Git・配布対象外）
├── .venv/                 # このPJ専用のPython環境
└── pyproject.toml         # 依存関係とCLI定義
```

この環境では `.venv` を構築済みです。以下で例題を実行できます。

```bash
cd /home/sin/code/agent/reserch/superfish-ng
source .venv/bin/activate
superfish-ng solve examples/pillbox.json --out out/pillbox-new
```

初回構築し直す場合は、このREADMEのあるディレクトリで次を実行します。Linuxを主対象とし、Python 3.12を開発環境に指定しています（`.python-version`）。seed納品時はPython 3.12.13 / NumPy 2.3.5 / SciPy 1.17.0でした。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
superfish-ng solve examples/pillbox.json --out out/pillbox
superfish-ng solve examples/shaped_cell.json --out out/shaped
superfish-ng converge --out out/convergence.json
```

`--out`は新しいパスを指定してください。既存の計算を上書きしません。
CLIの代わりに `python -m superfish_ng ...` も使用できます。
既にNumPy/SciPyがある環境では、インストールせず `PYTHONPATH=src python -m superfish_ng ...` でも動きます。
ZIPに仮想環境や依存ライブラリのwheelは含みません。初回の依存関係取得には通常ネット接続が必要です。

全検証と例題出力を再生成するコマンド:

```bash
OPENBLAS_NUM_THREADS=1 python scripts/validate.py --out out/validation
```

任意の図を生成する場合:

```bash
python -m pip install -e '.[plot]'
python scripts/plot_results.py out/shaped --out out/shaped.png
```

## 実装済み

2026-09-09、N04曲線辺候補検索追加後（直前基準 `942860b`）。最新の受入範囲と履歴は [実装状況](docs/IMPLEMENTATION_STATUS.md)。

[3386a5fのローカル配布確認](docs/LOCAL_DISTRIBUTION_20260909.md)で、同一ZIP・wheel内容・CLI/曲線native計算を確認。全機能/GUI・別OS・公開リリースの受入は残る。

[曲線辺の候補検索](docs/CURVED_EDGE_SEARCH.md)を空間木へ変更。従来の比較候補・順序・幾何検査報告と拒否条件を維持し、全辺同士の候補検索を削減する。旧保存版1〜4と球形五量は完全一致し、標準656件中654合格・2 skip。非球形の両尺度対照は後続検証でPASS。一般精度/効率は継続する。

[曲線要素の順序付き組立](docs/CURVED_ORDERED_ASSEMBLY.md)を追加。基底・積分寄与を配列化し、従来の加算順序と保存再検証の整合性を維持する。[非球形対照](docs/CURVED_NONSPHERE_COMPARISON.md)は初回の予算不足を保持し、拡大予算の尺度1追加対照がPASS。適応100917自由度に対し一様確認41281自由度で、適応優位は得られなかった。高速化版の両尺度検証も完了しPASS。N04全体の精度・効率は未受入。

[曲線適応の検証済み先祖の再利用](docs/CURVED_VERIFICATION_REUSE.md)を追加。実行中だけ先祖の場/ピーク/積分の重複評価を省き、要求・実装・元ファイル内容の照合と新水準の完全検証を維持する。独立replayは全水準を評価する。細分の一般精度/効率の受入とは区別する。

[曲線適応と一様細分の対照](docs/CURVED_REFINEMENT_EFFICIENCY.md)を追加。同じ初期二次写像の球形で、独立解析五量・追跡・積分・二区間確認と誤差対DOF/時間を実測した。一様3水準/1201自由度に対し適応5水準/2661自由度を要し、この例で効率優位は得られなかった。一般精度/効率の受入は継続する。

[曲線の適応計算版4](docs/CURVED_ADAPTIVE_REFINEMENT.md)をAPI/CLI/JobManagerへ接続。残差選択・native履歴・質量内積追跡、高次積分比較、五量の区間判定、全域確認2回、保存再開を統合する。滑らかさを確認した閉PEC曲線が対象。版4のGUI入力・五量/高次積分表示・保存再開も接続した。一般精度/効率・幾何誤差の受入は残る。

[曲線の親子空間の質量内積追跡](docs/NESTED_CURVED_TRACKING.md)をAPI/保存/CLIへ追加。局所・全域の複数段階履歴、両対称と鏡映の偶奇部分空間を検証し、係数移送からモードID/部分空間を対応付ける。版4の適応停止とGUIへ接続した。一般精度・効率は残る。

[二次曲線FEMの残差指標](docs/CURVED_RESIDUAL_INDICATOR.md)を追加。物理座標の二階微分・曲線流束を評価し、既存の選択APIとCase局所履歴で実細分できる。指標は物理誤差上界ではなく、曲線の適応停止とGUIは版4へ接続した。

[曲線要素の局所適合細分](docs/CURVED_MARKED_REFINEMENT.md)を[Caseの順序付き履歴・native保存再構築](docs/CURVED_REFINEMENT_HISTORY.md)へ接続。通常FEM/CLIと半領域鏡映の保存再検証を確認した。曲線適応停止は版4へ接続した。履歴対応Study・GUI編集は未接続。

[通常RF結果の連続離散ピーク評価](docs/RF_DISCRETE_PEAKS.md)をAPI/保存/CLI/GUIへ追加。直線P1/P2・二次曲線P2の上下界、元RF推定値、規格化、角診断を同じ画面で確認できる。単一メッシュの物理収束合格ではない。

[版3の表面量を含む適応停止](docs/ADAPTIVE_SURFACE_STOPPING.md)をAPI/CLI/JobManagerへ追加。最後の2回の全域細分でf/RQ/Gと連続離散ピーク比上下界を別判定する。版1/版2は維持。版3のGUI入力/表示/保存再開も接続。一般精度/効率は未完。
同一多角形領域の独立再メッシュ比較API/CLI/GUIと明示アフィン変形の比較API/CLI/GUI、明示比較メッシュによる区分アフィン変形の比較API/CLI/GUIと同一二次曲線領域の比較API/CLI/GUIを追加。曲線P2の明示アフィン変形にも、変換後の二次境界全体が一致する条件で対応。明示policyによる多対多のID集合継承とGUIでの方式選択・復元を追加。条件と残件は [追跡仕様](docs/MODE_TRACKING.md)。

| 分野 | 現在の内容 |
|---|---|
| 形状 | pillbox、折れ線、段差、短円弧、z折返し単一輪郭、native円/楕円/双曲線弧。軸接続・単一真空領域 |
| メッシュ | タグ付き三角形、自動生成/JSON読込、P1/P2場。曲線輪郭は二次幾何写像と固定幾何細分に対応 |
| 物理 | 真空、回転対称、m=0 TMおよび直線P1/P2・曲線P2 TE、PEC外壁、平坦z端の対称条件。場の鏡映構築はTMのみ |
| 固有値 | 一般化対称固有値問題、SciPy/ARPACKのshift-invert、複数モード |
| 数値検査 | 固有値残差、質量内積での直交性、電気・磁気エネルギー整合 |
| RF量 | f、U、表面抵抗、壁損失、Q0、G、通過位相を含むVacc、R/Q、シャントインピーダンス、TTF |
| 表面電磁場 | P1/P2片側場、曲線離散場の連続極値の囲い込みと角診断。物理ピークの収束保証とは区別 |
| モード追跡 | [重み付き部分空間・円筒/profile写像・明示メッシュ対応](docs/MODE_TRACKING.md)、2時点対応の保存・再検証CLI/GUI。個別ID履歴・再開に対応。部分空間ID集合も継承。合流/分裂の集合継続と完了Studyの順序追跡、逐次計算・停止・チェックポイント再開CLI・JobManager・GUIに対応。幾何掃引の適応二分・途中再開API/CLI・JobManager・GUIあり。一般写像・個別枝回復は未完 |
| 出力 | 単位と規約を含むJSON、CSV、NPZ、ParaView向けASCII VTK |
| 検証 | 標準検証の最新件数は[実装状況](docs/IMPLEMENTATION_STATUS.md)を参照。Pillbox/Bessel場、球形独立参照、楕円/双曲線の幾何・FEM細分、RF、保存、GUI等。数値・ブラウザー受入は個別記録を参照 |

`benchmarks/validation/` に納品時の実測ログ、解析値との比較、計算場を収録しています。
2026-09-07: [NGSolveとの独立照合](docs/INDEPENDENT_COMPARISON.md)を追加し、
円筒/円錐台の両側収束と周波数・RF量・内部磁場を検証しました。
[境界タグ付き非構造メッシュ入力](docs/MESH_INPUT.md)もCLI/APIで利用できます。
明示した物理・座標・単一真空材料/領域を持つ[v3入力](docs/MODEL_CONTRACT.md)を追加しました。
`superfish-ng capabilities`で対応範囲、`migrate-case`で既存入力からの明示移行を利用できます。
旧v1/v2のhashと数値結果を維持し、追加物理は未実装として拒否します。
v3のrfとGUIで[加速長・電圧積分区間・位相原点](docs/ACCELERATING_CONVENTIONS.md)を指定できます。
指定を省略した既存の周波数・RF結果は変わりません。
`docs/VALIDATION_REPORT.md` に数値と解釈をまとめています。
今回の環境での実行結果と配布処理の変更は [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md) に記録しています。

ルートに以前から存在するWine環境、`SUPERFISH/`、講義PDF、`解説/`、旧起動スクリプトはローカル資産です。
旧READMEは `README-legacy.md` に保存しました。これらはSuperfish-NGの実装・配布対象外で、配布スクリプトは指定したプロジェクトディレクトリとファイルだけを収集します。

## 重要な制約

- TEの一般形状の追跡・鏡映、m>0の双極・四重極モード、同軸TEM、静電場、静磁場、非線形材料は未実装。
- profile系は `R(z)>0`、arc_profileはz非減少の短円弧に限定します。v3 contour/curved_contourはz折返しを許しますが、軸接続の単一外周に限定し、穴・内導体・任意CAD・RFQは扱いません。
- 両端は既定で金属板、v2入力で電気/磁気対称面を指定できます。細い首は開放ビームポートではありません。
- Q0は理想PEC固有場に常伝導表面抵抗を適用する摂動推定です。複素固有周波数、超伝導BCS損失、放射損失は計算しません。
- 電磁場はピークphasorです。既定で全蓄積エネルギー1 Jに正規化します。運転電力1 Wの指定ではありません。
- TMのR/Qは `|Vacc|²/(ωU)` と `|Vacc|²/(2ωU)` を別名で出力します。m=0 TEでは軸加速量と両R/QをN/Aとして保存します。
- 周波数順のmode番号は物理モード名ではありません。明示した写像・対応による追跡に部分対応しますが、一般形状の自動対応や個別枝回復は未完です。
- Wine版SUPERFISHとの基本3形状照合に加え、セミナーの80 mm Pillbox TM010/TM011、flat4・rounded4・rounded7の計17モードを照合済み。full-end比較形状と長さ40/120 mmはWine直接照合の対象外です。測定との比較は未実施で、角部のピーク電場には差が残ります。

## Codexに引き継ぐ

現在の開発計画は[実装の現状](docs/IMPLEMENTATION_STATUS.md)→
[互換対応表](docs/COMPATIBILITY_MATRIX.md)→[仕様・実装・検証への分割](docs/COMPATIBILITY_PLAN.md)。
既存課題の状態は[バックログ](docs/BACKLOG.md)を参照。計画の記載は対応機能の完成を意味しません。

汎用GUIは `superfish-ng gui --workspace out/gui-workspace` で起動します。
形状・円弧・繰り返し部分の編集、計算と中止、保存場・RF量の表示、
寸法掃引・収束比較を、CLI/Pythonと共通の入力・計算機能で扱えます。
描画にはplot extraが必要です。導入と操作は [GUIガイド](docs/GUI_GUIDE.md)、
範囲と判断基準は [開発計画](docs/GUI_IO_PLAN.md)、検証は [受入記録](docs/GUI_ACCEPTANCE.md) を参照。
例題専用の処理を作らず、操作性・再現性・数値の信頼性・保守性で変更を判断します。

このディレクトリをCodexで開きます。Gitを新規に初期化する場合も、このディレクトリをルートとします。

```bash
git init
git add .github .gitignore .python-version AGENTS.md CHANGELOG.md CONTRIBUTING.md LICENSE MANIFEST.in NOTICE README.md pyproject.toml requirements-reproduce.txt src tests scripts examples docs benchmarks
git commit -m "Initial independent axisymmetric RF seed"
```

最初に `AGENTS.md` と `docs/CODEX_HANDOFF.md` を読ませ、同ファイルの開始プロンプトを使用してください。
公開リモートやパッケージの登録は今回行っていません。

配布用ZIPは次で作成できます（`--out` はPJ外の新しいファイル）。収録対象を増やす場合は `scripts/package.py` の許可リストも更新してください。

```bash
python scripts/package.py --out /tmp/superfish-ng-dev.zip
```

`scripts/verify_manifest.py` は、配布ZIPを新規ディレクトリに展開した直後に実行します。
開発中のルートには古いmanifestを置かず、seed原本のmanifestは `benchmarks/seed/manifest.sha256` に保存しています。

| ファイル | 用途 |
|---|---|
| [docs/RESEARCH.md](docs/RESEARCH.md) | 事前調査、既存OSS、採用判断、前の議論の訂正 |
| [docs/PHYSICS.md](docs/PHYSICS.md) | 軸上処理・弱形式・境界条件・RF量の定義 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 依存順と受入基準を持つ開発計画 |
| [docs/BACKLOG.md](docs/BACKLOG.md) | Codex向けの具体的な実装タスク |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | モジュール責務と将来のバックエンド境界 |
| [docs/REFERENCES.md](docs/REFERENCES.md) | 注釈付き文献・一次資料一覧 |
| [docs/references.bib](docs/references.bib) | 論文のBibTeX |
| [docs/PROVENANCE.md](docs/PROVENANCE.md) | 参照制限、今回の参照履歴、clean-roomの限界 |
| [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md) | 依存関係・ライセンス・再現環境 |
| [docs/INPUT_OUTPUT.md](docs/INPUT_OUTPUT.md) | 入力と出力の仕様 |

ライセンスは [Apache-2.0](LICENSE)。第三者文献や依存ライブラリは各自の条件に従います。

要素次数は既定P1とP2を選択できます。Pythonでは`Case(..., element_order=2)`、
v3 JSONでは`"solver": {"modes": 3, "element_order": 2}`を指定します。
v3には明示modelが必要です（[モデル契約](docs/MODEL_CONTRACT.md)）。GUIにも次数選択があります。
P2の場・RF・保存・表示の仕様と検証は[高次場](docs/HIGH_ORDER_FIELDS.md)を参照してください。
直線幾何のP2はN01/N02として受入済みです。v3 curved_contourでは
`mesh.geometry_order=2` と `solver.element_order=2` による曲線FEMも利用できます。
場/RF・保存・描画・Study・鏡映・GUIまで接続済みです（[曲線要素](docs/CURVED_ELEMENTS.md)）。
G03全体は部分対応です。[要件と証拠の照合](docs/G03_ACCEPTANCE.md)を参照してください。
共通接線、固定直線と弧の接続、指定半径の線分間フィレット、円錐曲線弧同士および直線と弧の
フィレットを保存・Case/CLI/GUIへ接続しています。版5/6の弧フィレットは交点の存在/一意性と接点位置誤差を
区間で検査し、G1角度は数値検査として区別します。弧端/退化の追加分類、
旧曲線入力・物理ピーク収束・全要件照合は残件です。曲線幾何の適応誤差推定は未対応です。
`diagnose-offsets` で[弧端・退化の特殊ケース](docs/OFFSET_DEGENERACIES.md)を診断できます。
証拠の確認と有限領域全体の分類完了は別に記録します。版5/6の構築ではGUIにも表示し、
元の構築を含めて保存・再検証できます。CLIは `diagnose-construction` を使います。
曲線輪郭には[PEC壁の最小子午面曲率半径](docs/MERIDIONAL_RADIUS.md)も指定できます。
[モード追跡](docs/MODE_TRACKING.md)は重み付き標本・縮退部分空間と、明示写像による円筒の実FEM交差に部分対応します。
保存履歴・再開に対応し、[追跡付き1変数周波数調整](docs/TUNING.md)をAPI/CLIへ追加しました。
`python -m superfish_ng tune examples/tuning/pillbox_length.json --out out/tune-new`で実行できます。
全個別IDの確認と最終細メッシュ判定を必須とします。
`JobManager.start_tune`で別プロセス実行・取消し・確認済みチェックポイントからの再開も利用できます。GUIの「同じモードの周波数を調整する」から開始・保存・再開でき、成功後は調整対象の場・RFを開けます。
一つの長さ/無次元変数で複数のprofile座標を連動させる指定にも対応します。
半径調整の例は `examples/tuning/pillbox_radius.json` です。
[選択要素の適合細分API](docs/MARKED_REFINEMENT.md)は、直線P1/P2の境界と旧場を保つ係数移送を返します。[残差指標と細分対象選択](docs/RESIDUAL_INDICATOR.md)を追加しました。[追跡付き適応計算](docs/ADAPTIVE_REFINEMENT.md)のf/RQ/G停止・保存再開・CLIも利用できます。版2では局所候補後に全域細分を最低2回行い、RF量を確認します。`JobManager.start_adaptive_refinement`で[別プロセス実行・取消し・再開](docs/ADAPTIVE_REFINEMENT_JOBS.md)も可能です。[GUI](docs/GUI_ADAPTIVE_REFINEMENT.md)からも開始・中止・保存再開・f/RQ/G判定表示・対象場の表示を利用できます。版3で表面量停止をAPI/CLI/JobManagerへ追加しました。版3のGUI入力/表示/保存再開も利用できます。曲線局所細分のCase履歴とnative保存/CLIも接続しました。曲線の適応停止・保存再開は版4で接続しました。版4のGUI入力・判定表示・保存再開も利用できます。任意の局所履歴を直接編集するGUIは未実装です。
一般形状の追跡・制約付き最適化は未完了です。
[表面ピークの収束評価](docs/SURFACE_CONVERGENCE.md)をAPI/CLI/GUIへ追加しました。追跡済みの固定曲線幾何について、周波数・R/Q・G・ピーク比の細分差を別々に判定します。
接線構築は `construct-tangent` → `export-constructed-case` → `solve` で実行できます。
合成例と保存・再構築の仕様は [接線構築](docs/TANGENT_CONSTRUCTION.md) を参照してください。

v3の一般輪郭`contour`はz折返しを含む単一外周を表せます。`mesh.contour_mesh`で
最大辺長・品質・停止上限を明示して自動生成するか、検証済み外部メッシュを渡します。
例は `python -m superfish_ng solve examples/contour_folded.json --out out/contour-new`。
この粗い合成例は操作例であり精度基準ではありません。GUIでは設定編集・自動計算・保存結果表示に対応します。仕様と制限は
[一般輪郭](docs/GENERAL_CONTOUR.md)を参照してください。

[直線P1/P2の連続離散ピーク囲い込み](docs/AFFINE_SURFACE_EXTREMA.md)をAPI/保存/CLIへ追加しました。
`bound-affine-peaks`で既存native場のPECピークを上下から囲み、`replay-affine-peaks`で再検証できます。
物理ピークの収束保証は未対応です。版3では連続離散ピーク比を適応停止に含めます。

[追跡済み直線要素の表面収束評価](docs/AFFINE_SURFACE_CONVERGENCE.md)をAPI/保存/CLIへ追加しました。
[GUI](docs/GUI_AFFINE_SURFACE_CONVERGENCE.md)でも評価・保存再検証・評価したIDの対象場表示を利用できます。
元多角形の角と、f/RQ/G・ピーク比の直近2区間を別判定し、全域確認不足を保持します。
元の適応停止や表面未評価状態は変更しません。

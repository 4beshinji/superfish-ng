# 初期接続が異なる曲線選択移送：要求版2の仕様

2026-10-08 JST、ADD-N04-selection-charts-01 **DONE**。開始commit `e76e58a`。
親N04の[元残件4](N04_ACCEPTANCE.md)を、要求・保存版2と必須五工程へ具体化した。
01受入時点は版2未実装で公開APIが拒否した。現在は[03計算工程](CURVED_SELECTION_CHARTS_CORE.md)もDONEで、
公開APIが版2を計算する。[04完全再生/CLI](CURVED_SELECTION_CHARTS_SAVED.md)もDONE、
GUI・専用FEM受入は05/06に残る。
旧版1、一般FEM、RF・モードID・公開適応停止は変更していない。

## 対象、元要求と表現

対象は直接・未組立・未鏡映のnative曲線P2 TM Project二つ。
元Case、全解析曲線、初期source mesh、全uniform/marked/frozen履歴を保持する。
初期頂点数、接続、境界分割数、最終分割、物理形状・寸法は異なってよい。
物理座標から最近接対応を推測せず、利用者が両初期メッシュの共通参照座標を宣言する。
原領域の電気/磁気対称タグも保持し、同じ `(z_min,z_max)` と対応する全境界タグを要求する。
TE、鏡映後の全空洞、組立Project、直線P1経路、軸非接続/材料などの専用物理は受理しない。
元版1で許される原対称領域を、新版だけ閉PECへ狭めない。

要求版2の全七フィールドを必須とする。版1のフィールド・意味・出力はそのまま保持する。

| フィールド | 型・意味・拒否条件 |
|---|---|
| schema_version | 整数2。bool/float/未知版を拒否 |
| selected_cells | 空でない重複なし整数list。旧Projectの全履歴後の0始まり要素番号。bool/float/負/範囲外を拒否 |
| boundary_pairing | `declared_reference_polylines` のみ。他方針と混用しない |
| coverage_policy | `intersects` または `contained` |
| max_pair_tests | 正整数。全参照辺/自己交差/両側交差の合計予算 |
| max_triangles | 正整数。各native初期/履歴後要素数と共通交差三角形数の上限。各Caseが厳しければその元上限も保持 |
| reference_vertices | `[previous_chart,current_chart]`。各chartは三頂点以上で、各初期source_mesh頂点と同じ順番・個数のlist |
| chart内の各頂点 | 上記配列の要素は有限int/float二座標のlist。無次元。bool/NaN/Inf/文字列/余分な座標を拒否 |

上表の最後の行はreference_verticesの内部条件であり、独立フィールドではない。
JSONの未知/欠落/重複キーは既存 `project.parse_json` と版別validatorで拒否する。
非整数の実座標はbinary64に読まれた**その値**をFraction化し、十進数の理想値へ置き換えない。
APIでFractionを直接入れる追加形式はこのJSON要求版2では提供しない。
reference_verticesは初期頂点の宣言であり、P2全mid節点や最終履歴後の節点に対する配列ではない。
両Projectには明示source_meshが必要。自動生成結果に暗黙のchartを付けない。

## 被覆と選択の計算

既存 `build_curved_reference_partition` を使い、全native履歴を元の品質・Case予算で再構築する。
各初期三角形の有理親座標を合成し、宣言されたchartへ移す。
各曲線の増加分率方向の参照折線、曲線順序・向き・境界タグを両側で照合する。
追加の共線境界頂点を許し、折れ点/逆戻り/接触/重複/正向きの失敗を拒否する。
物理曲線分率の一致やP2物理領域の一致は要求しない。別形状間の対応を明示する機能である。

全旧/新参照三角形を交差させ、選択されていない旧要素も含めて、
各親の被覆面積が親面積と**厳密に等しい**ことを確認する。
全交差三角形は、旧新最終親番号・各親内重心座標・有理頂点とdeterminantを持つ。
元P2物理写像を保持し、境界再投影、場係数の移し替え、固有解による対応推測を行わない。

旧選択集合の和をS、新最終要素jをTj、共通交差三角形をCkとする。
選択された旧親に属するCkだけを数え、
`Aj = sum(area(Ck), current_cell=j, previous_cell in selected_cells)` とする。
`area(Ck)=determinant(Ck)/2` は無次元有理数。新親面積Bjに対し0<Aj<=Bjを必須にする。

- intersectsはAj>0の全新要素を選ぶ。辺/点だけの接触は選ばない。
- containedはAj=Bjの新要素だけを選ぶ。結果の空集合は正しい成功になり得る。
- partially_covered_cellsは0<Aj<Bjの全新要素。covered_fractionはAj/Bj。
- 旧選択の各要素ごとに、交差面積総和=元参照面積を厳密に検査する。

両policyのcoverage/overlapsは同じ全交差証拠を保持し、selected_cellsだけが異なる。
覆う/内部の新要素集合が元Sと完全一致するとは限らない。
参照面積・被覆率を物理面積/回転体積の被覆率やFEM誤差と呼ばない。

`max_pair_tests` は既存builderと同じ全辺検査数Eに、旧n/新mの最終要素に対する
`n*m+n*(n-1)/2+m*(m-1)/2` を加えた値。
選択要素だけを数えて全領域の検査予算を迂回しない。
現実装の全組対照にはこの予算を適用し、250000要素の描画能力を移送能力へ読み替えない。
幾何選択自体に求積は不要。物理積分の独立検査には下記別ゲートを使う。

## 保存、厳密再生と操作

保存版2のtop-levelは、`schema_version`、`document_type="curved_selection_transfer"`、
`status="PASS"`、`previous_project`、`current_project`、`request`、`reference_partition`、
`selection`、`physical_error_bound=null`、`scope` の全十フィールド。
`reference_partition`には元builderの全reportを保持する。
`selection`は以下の全フィールドを持ち、版1のbase_correspondence/base_area_checksを流用しない。

`selected_cells`、`partially_covered_cells`、`coverage`、`overlaps`、
`previous_final_cell_count`、`current_final_cell_count`、`total_pair_tests`、
`source_reference_area`、`intersection_reference_area`、`source_cell_area_checks`。
coverage行は `current_cell/covered_fraction/covered_reference_area`。
overlapsは選択旧親に属する共通三角形の元report行を全保持する。
source_cell_area_checks行は `previous_cell/source_reference_area/intersection_reference_area`。
有理数は分子/正分母の整数対で保存し、導出ID/分子/分母/真偽値の型を厳密に保つ。
Projectの同値な浮動小数JSON表記0/0.0は旧 `_same_json_values` の契約で受理する。

`replay_curved_selection_transfer` は版別の全フィールドを検査して両Projectから完全再計算し、
全派生値を照合する。改竄、不正型、予算超過は失敗し、元入力/出力を変更しない。
自己完結した再計算であり、独立署名/外部真正性証明ではない。
幾何PASSをFEM精度/物理誤差上界のPASSとして表示しない。

CLIの既存 `transfer-curved-selection` / `replay-curved-selection-transfer` へ版2を接続する。
出力は全検査後に排他的作成。元版1ファイルは同じ意味・同じ内容で再生できる。
GUIの既存境界selectへ明示参照折線の選択肢、二chartのraw JSON欄、共通三角形上限を追加する。
chart JSONをclient側で再解析/再直列化せず、raw selected_cellsと同様にstrict server readerへ渡す。
form signatureへ全新欄を含め、対象段階/Project/手動選択が途中で変わると適用を拒否する。
版2の保存再読込は全chart/予算を復元し、版1読込時は新欄を消去して旧方針へ戻す。
元の対象Projectを保存文書から暗黙に置換せず、現在の対象段階で再計算後に履歴反映する。
後続marked番号の修復を自動化しない。

## 閉形式入力例、反例と今回の証拠

入力例は [old-project](../examples/curved_selection_charts/old-project.json)、
[new-project](../examples/curved_selection_charts/new-project.json)、
[intersects](../examples/curved_selection_charts/intersects.json)、
[contained](../examples/curved_selection_charts/contained.json)。全て合成例で、測定構造ではない。
R=0.1 m、L=0.2 m、旧2/新3要素。新側は内部対角線を変え、軸境界に頂点を追加する。
共通chartは単位正方形、旧選択0は0<=y<=x<=1。

| 不変量/選択 | 独立に導いた期待値 |
|---|---|
| 旧選択参照面積 | 1/2 |
| 新0/1/2の交差参照面積 | 1/6、1/12、1/4 |
| 新0/1/2の被覆率 | 2/3、1/3、1/2 |
| intersects / contained | [0,1,2] / [] |
| 選択物理面積 | R*L/2 = 0.01 m² |
| 選択回転体積 | 2*pi*R²*L/3 = 0.004188790204786391 m³ |
| Hφ=rの幾何質量 | R⁴*L/5 = 4e-6 m⁵（電磁エネルギーではない） |

現行版1は要素/節点数不一致を拒否し、提案版2は未知フィールドを拒否することを先に確認した。
既存全領域builderの有理交差証拠から上の期待被覆率を厳密照合し、
5×5 Gauss-Duffyで独立閉形式三積分と比較した最大相対差は3.331e-16（gate3e-12）。
元版1の磁気対称領域はPASSだが、既存chart builderのTM境界検査はこれを拒否することも再現した。
これは新版の明示opt-inが必要な根拠であり、旧場比較consumerの受理範囲を黙って広げない。

[bool番号反例](../examples/curved_selection_charts/invalid-boolean-id.json)は将来版2validatorで拒否する。
現行製品では版2全体が未実装のため、この反例だけを検証済みとは扱わない。
[参照境界の変化](../examples/curved_selection_charts/invalid-reference-boundary.json)は軸中間頂点を
[0.125,0.5]へ移し、既存builderで全参照境界不一致を実際に拒否した。
加えて実装検査では未知/欠落/重複、bool/float番号、空/重複/範囲外、非有限/不足chart、
逆向き/自己交差/タグ/対称セクター不一致、予算、元Project/保存交差/派生選択改変を要求する。

rawは `out/n04-selection-charts-spec-20261008`。
`probe-spec.py`、`existing-overlay.json`、`probe-report.json`、初回/訂正log、源/六例hashを保存した。
初回の対称fixture生成は旧導出contourを残してCase拒否になったため、元失敗/旧helperを保存し、
contour=Noneで元curved geometryから生成し直した。製品/数値ゲートは変更していない。
訂正実行0.490秒・終了0、固有値solveを例外guardして呼出し0。
新FEM/unit/seed/full/legacy0。元1432源はbyte不変、六例追加後1438対象/1225 Python源。
公開版2移送のPASSではなく、仕様と既存幾何機能の成立証拠である。
新文献・依存・旧資産参照なし。既存の自作有理数交差/参照履歴と初等閉式積分を利用した。

## 必須五工程と独立受入ゲート

2026-10-08：02の[strict入力工程](CURVED_SELECTION_CHARTS_INPUT.md)をDONE。
新7/元直接8個別PASS、15件1.761秒・終了0。公開版2の計算/保存/GUIは03〜06の後続。
[03計算工程](CURVED_SELECTION_CHARTS_CORE.md)もDONE。新9/旧29の38個別PASS、
全有理被覆と独立三積分/尺度則を受入。[04保存/CLI](CURVED_SELECTION_CHARTS_SAVED.md)もDONE、
新6/直接9の15個別PASS・実CLI四起動を受入。次は05。以下は各工程の固定条件。

下記工程をTSVへ追加し、親N04・V03/V05の依存へ接続する。01仕様のDONEだけで親を閉じない。

| カード/先行 | 所有・具体変更 | 終了条件と選択検査 |
|---|---|---|
| ADD-N04-selection-charts-02 / 01 | `curved_selection_transfer._validate_chart_request` を新設。版2七項目/配列内部をstrict検査。`tests/test_curved_selection_charts_input.py` 新設 | 六例の型/版判定、上記raw重複/非有限/不正値、旧版1要求不変。入力metadataだけ、新FEM0。02で公開版2の計算対応を主張しない |
| ADD-N04-selection-charts-03 / 02 | 既存transferへ版2dispatchと `_transfer_reference_chart_selection`。`curved_reference_partition.build_curved_reference_partition` / `_boundary` に `allow_tm_symmetry=False` のstrict bool opt-inを追加。版2selectionからTrue、旧consumerはdefault不変。循環importはfunction内importで避ける。`tests/test_curved_selection_charts.py` 新設 | 全有理被覆/二policy、旧[2,3]例、独立番号/非nested履歴/非アフィン/尺度、対称・拒否・予算、入力不変。新unitと旧selection8/reference6/overlay7を関連分だけ確認。旧TM/TE場比較の受理範囲を保持 |
| ADD-N04-selection-charts-04 / 03 | `replay_curved_selection_transfer` の版別十項目全再計算。`cli.main` の既存二command/helpへ接続。上記新testへsaved/CLIケースを追加 | API/CLI/全文書一致、旧版1再生、排他作成、元入力/派生有理数/ID/bool型改竄の拒否・元ファイル不変。新FEM0の保存検査 |
| ADD-N04-selection-charts-05 / 04 | `web/app.js` のcurvedTransferFormSignature/run/open、`web/index.html` の専用欄、既存gui.do_POST transport。新 `scripts/verify_gui_curved_selection_charts.mjs` | 現行実Chromeのraw拒否/二policy/描画選択/保存復元/旧版復元/途中応答/履歴反映。`test_gui_curved_mesh_selection` と新transportケース、元版1実ブラウザー回帰。製品ソース固定・所有process終端・native一致 |
| ADD-N04-selection-charts-06 / 05 | 新 `scripts/validate_curved_selection_charts.py` と条件別受入記録。旧自作8×8独立P2基底/微分、Green境界積分と全nativeを利用 | 下記幾何/行列/実FEM/保存/操作の各gateを別報告し、原四群のこの残件を受入。未達/例外/費用/源hash保持。親N04は他残件完了まで継続 |

独立幾何のgateは有理被覆の完全一致、別P2積分の面積/回転体積/Hφ=r質量の相対3e-12。
非アフィン旧26/新27fixtureと別履歴を含め、元選択native積分と旧交差合計、
新側の交差合計<=cover合計・contained合計<=交差合計を各三量で確認する。
尺度2の面積4/体積8/幾何質量32倍も同じ3e-12。
既知場adapterは固有解ではなく、係数場の代用でFEM受入を作らない。

専用の実FEMは同じ矩形の旧/新Projectへ二uniform履歴を付け、旧選択0の移送先markedを
新側末尾へ加える。尺度1/2で旧・新・marked新の計**6新求解**を実行前計画とする。
Pを新Projectのmarked直前から直後へのnative親子係数移送に限定する。
PᵀMfP/Mc、PᵀKfP/Kcを別組立して相対1e-10、fixed-domain Ritz非増加を相対5e-11、
周波数1/2、U=1 JのHφ/Er/Ezの尺度2倍率2^(-3/2)、両R/Q・G・TTF不変を相対1e-10で確認する。
場の尺度差は全供給点の重み付きL2で測り、ゼロ点の個別比を使わない。
f、場、RF、幾何/被覆は別判定し、粗い矩形の連続物理精度達成を主張しない。
GUIで追加する求解は別の実行数/費用として記録し、6専用求解へ含めない。
保存した全係数/周波数/P2座標/接続はAPI/CLI/GUI再生でbyte/配列一致、全RF量は相対1e-12、
単一符号以外の振幅fitや場補正をしない。両R/QとSI/peak phasor/Uを保持する。
実行はBLAS1/uv、未使用out、3600秒/32 GiB・Case要素上限、移送例max_pair_tests=100000/
max_triangles=1000とする。非アフィン専用例は旧26/新27初期メッシュから、
両側uniform一回と異なるmarked一回を使い、max_pair_tests=100000/max_triangles=10000を明示する。
新モジュール/数値核を増やさず既存selection/参照分割の変更に限定し、seed TM pathは非変更。
全suite/seedはこの仕様のために繰り返さず、広範影響が判明した場合に範囲を広げる。

# 元P2境界の分割数を変更する再メッシュ生成

2026-10-13 JST。ADD-N04-boundary-remesh-01の仕様受入。
[親N04残件4](N04_REMAINING_CARDS.md#add-n04-boundary-remesh-01)を実装可能な五工程へ展開する。
本カードは入力・表現・ゲートの決定まで。公開生成器の版2、保存、GUI、専用FEMは後続02〜06で受入する。

## 対象と採用する表現

元の解析曲線、材料、SI単位、RF座標、正規化、mode設定を保持し、元の内部接続を捨てて
初期メッシュを再生成する。その後、元P2写像の区間制限で境界と内部を適合細分する。
生成結果は既存の置換計画版1（`source_mesh`と完全な固定細分履歴）で表す。
Caseへ新しい自由な六節点外部メッシュ形式を導入する必要はない。
元Projectと要求は不変、求解は行わず、解析解でFEMを置き換えない。

`curved_mesh.curve_geometry_candidate`は初期弦メッシュから解析曲線上の中点等を作る。
細分後の物理節点を新しい弦メッシュへ単純に書き戻す方法では、元P2の保持を保証できない。
既存`curved_refinement.refine_curved_space`と
`curved_marked_refinement.refine_marked_curved_space`は親の参照三角形内で写像を制限し、
解析曲線へ再投影しない。生成器はこの経路を使う。

元境界の各二次辺を、元の向き付きパラメータで
`x(t) = A + B t + C t²`, `0 <= t <= 1` とする。区間`[a,b]`の子辺は
`x_child(s) = x(a+(b-a)s)`であり、端点と中点はそれぞれ`s=0,1,1/2`の値。
係数は`A+Ba+Ca²`, `(b-a)(B+2Ca)`, `(b-a)²C`。単位は座標がm、パラメータは無次元。
全ての元区間を隙間・重複なく被覆し、曲線所有番号、境界タグ、向きを継承する。
元の解析曲線に近いことと、元のP2境界が同じことを混同しない。

旧履歴を置換するため、以前より少ない最終境界辺を作れる。ただし初期弦メッシュが
表す元P2区間自体は併合しない。任意の指定辺数への粗化・曲線の再近似・幾何誤差の改善は
この操作に含めない。直線等で数学的に併合可能でも、本版では元区間を保つ。
境界辺数予算が元区間数より小さい要求は、必要本数とこの制限を明記して拒否する。
幾何を変える方法を採用していないため、新しいN03幾何誤差系列は先行条件に加えない。

物理範囲は既存生成器/置換APIと同じ。unassembled native P2、TMは直接閉PEC/axis、
TEは`curved_same_domain_tracking._te_end_conditions`が許す同一セクター・高々一対称面と
既存の反射検査を通るもの。未対応のTM反射/対称、多穴、非対応物理を拡張しない。
軸の正確なr=0、正Jacobian、半径非負、共有辺の逆向き、交差/重複なし、連結円板、
TE拘束を既存のnative検査で全履歴prefixごとに確認する。

## 版2入力とサイズの意味

`curved_remesh_generation.validate_generation_settings`をstrict入口として追加する。
JSONでは重複キー/NaN/Infinityを`project.parse_json`/`load_document`で拒否する。
辞書APIも未知・欠落・不正型・非有限・巨大整数変換を拒否し、入力を変更しない。
全九共通項目と、下表の履歴指定のちょうど一方を必須とする。隠れた既定値を設けない。

| 項目 | 型・範囲・意味 |
|---|---|
| `schema_version` | boolでない整数2。版1は従来の固定境界・初期弦サイズの意味を維持 |
| `boundary_policy` | 文字列`restrict_native_p2`だけ |
| `max_chord_edge_m` | 有限正数、最終native全辺の端点間距離上限、m |
| `max_chord_triangle_area_m2` | 有限正数、最終nativeの三隅が作る正の弦三角形の面積上限、m² |
| `minimum_corner_angle_deg` | 有限数、0より大きく60未満、各prefixのP2隅接線角と最終弦角の下限、度 |
| `max_triangles` | 正整数、生成seedと全新履歴prefixに適用、元Case上限以下 |
| `max_boundary_edges` | 正整数、axis/PEC/対称を含むseedと全新prefixの境界辺数上限 |
| `max_seed_rounds` | 正整数、独立な内部seed生成の反復上限 |
| `max_rounds` | 正整数、明示履歴適用後に自動追加するmarked段数の上限 |
| `curved_refinement_levels` | boolでない0以上の整数。新seedに適用する一様段数 |
| `curved_refinement_steps` | 既存strict形式の非空配列。新seedに適用する完全な順序付き履歴 |

各辺の上限は設定値と元`Case.contour_mesh.max_edge_m`の小さい方。
非axis境界は元`boundary_max_edge_m`も適用する。角近傍は元境界弦多角形の非共線角を
固定し、端点弦から角までの最短距離が`corner_radius_m`以下の辺へ
`corner_max_edge_m`を適用する。追加したP2子頂点を新しい角とは数えない。
角度下限は設定値と元`contour_mesh.min_angle_deg`の大きい方。
弦長・弦面積は物理曲線の弧長・曲面積とは異なる。幾何積分は独立に検査する。
サイズの浮動小数許容は既存同様`1+1e-12`、角度閾値は緩めない。
ゼロ/負の弦面積、非有限な測定値は成功にせず明示拒否する。

旧細分履歴・旧marked番号を自動継承しない。明示履歴の番号は新seedからの各prefixを
指す。自動履歴はその後ろに追加する。元mesh用の固定patternはトポロジーSHA不一致なら拒否。
旧最終メッシュが新予算より大きくても、元Case自身の検証を通れば粗化できる。
一方、新seed/明示履歴/自動履歴のどのprefixも新予算を超えてはならない。

## 決定的な生成手順と拒否

`generate_curved_remesh_plan`の版1bodyを保持し、版2だけ
`_generate_boundary_remesh_plan`へ分岐する。新しい内部helperは同じmodule内に置ける。

1. 元Project、元Case、初期mesh、元の全native履歴を既存readerで検証する。
   `_boundary_case`で境界を正準化し、旧内部座標/接続/番号をseed生成へ使わない。
   元境界辺数が予算超過ならseed生成前に拒否する。
2. 正準境界座標の各軸幅から`D=2*sqrt(Δr²+Δz²)`を計算し、有限正数を確認する。
   seed専用コピーだけの弦長上限をD、弦面積上限をD²、境界/角サイズ指定をなしとし、
   元角度下限と要素予算を保つ。履歴0、`max_seed_rounds`を既存版1の生成器に渡す。
   これは最終サイズの緩和ではなく、元境界上のP2領域を保つ内部seedの作成条件である。
   元Case/出力Projectへこの作業用設定を保存しない。D/D²のoverflowは拒否する。
3. seed計画を元Projectへ適用して全境界一致を確認し、要求された明示履歴を順に適用する。
   markedの実分割を`CurvedSplitPattern`として固定する。全prefixの品質/予算を確認する。
4. `_native_size_marks`でnative端点弦のサイズ/面積を測り、超過辺に接する全要素と
   面積超過要素を番号順・重複なしで選ぶ。既存marked核の最長辺閉包/遷移を使い、
   新しい固定patternを一段追加する。境界はこの制限写像で分割する。
   サイズ合格でも弦角またはP2角が未達なら成功にせず拒否する。
5. `max_rounds`、要素/境界辺数、品質のいずれかに達して条件未達なら、原因と現測定値を
   含むValueErrorを返す。部分計画を成功出力しない。追加段前に要素/境界増加数を算定して
   予算を確認し、生成後も照合する。自動段には明示履歴段数を含めない。
6. 成功時は全新履歴を固定した版1計画を返す。全段が0なら`curved_refinement_levels=0`、
   それ以外はuniformも含めた`curved_refinement_steps`だけを出力する。
   `remesh_curved_project`で元Caseへ完全再生し、全区間P2一致・最終サイズ・全prefix予算を
   再確認する。元Caseの履歴以外は厳密一致させる。

元の複雑な境界に対するseed構成や品質が有限反復で成功する保証は置かない。
品質を満たす実入力、失敗する実入力を両方受入検査に含め、失敗時に解析曲線への再投影や
元meshの黙った再利用へ切り替えない。最小要素数/最適配置/一般効率を約束しない。

## 正常・拒否例と仕様段階の証拠

入力は[examples/curved_boundary_remesh](../examples/curved_boundary_remesh/README.md)。
正常二要求は矩形の.045 m/.0005 m²、非アフィン曲線の.04 m/.0005 m²。
拒否二要求は非アフィンの元10辺に対する上限9本と、サイズ要求を保った上限10本。
公開版2実装前は正常例も未知キー/未対応版として拒否される。試作結果を公開成功と呼ばない。

ignored `out/n04-boundary-remesh-spec-20261013/`に独立試作、元源hash、入力、固定計画と
`report.json`/`extra-report.json`を保持する。試作は既存APIだけを組み合わせた表現検証である。

| 実測 | 矩形 | 非アフィン曲線 |
|---|---:|---:|
| seed要素 / 元初期境界辺 | 2 / 4 | 8 / 10 |
| 自動制限後の要素 / 境界辺 | 128 / 32 | 84 / 28 |
| 元最終境界辺 | 4 | 24 |
| 最終最大弦長 m | .02795084971874739 | .03664783140614819 |
| 最終最大弦面積 m² | .00015625000000000046 | .0003522634785178638 |
| 最小P2隅角 度 | 26.565051177077784 | 33.556410760989515 |
| 全共通区間での最大係数距離 m | 8.327e-17 | 6.206e-17 |

同じサイズの現行版1は両方とも`fixed quadratic boundary`で拒否した。
別実装のP2基底/8×8 Duffy積分による面積・回転体積・`∫r³ dr dz`の保存と、
境界Green積分を確認した。元三積分との最大相対差は3e-12未満（詳細値はraw report）。
固定patternから全座標/接続を完全一致で再生した。矩形の旧一様4段を置換すると
最終境界64辺から32辺へ粗化できた。別に解析曲線へ再投影した候補は回転体積が変化し、
既存全二次境界比較で拒否された。元1444対象源は両probe前後でbyte不変。
新FEM、unit、seed/full、GUI、legacy実行は0。既存solver.solveを禁止して実行した。

## 保存・CLI・Study GUI

裸の版1計画は既存Project/Study版4へそのまま渡せる。生成条件を監査したい場合は
`build_curved_remesh_generation`と`replay_curved_remesh_generation`を同moduleへ追加する。
保存文書のexact keysは`schema_version`(1)、`document_type`(`curved_remesh_generation`)、
`source_project`、`settings`、`plan`、`validation`、`physical_error_bound`(null)の七項目。
版1/2設定を保持し、再生は全入力から生成を再実行してplan/validationを型込みで厳密比較する。
未知/重複/欠落、改変、履歴pattern混合、緩めた予算での部分再生を拒否する。

`validation`のexact keysは`status`(`GEOMETRY_VERIFIED`)、`boundary_comparison`（既存全区間report）、
`seed_triangle_count`、`prefix_triangle_counts`、`prefix_boundary_edge_counts`、
`final_max_chord_edge_m`、`final_max_chord_triangle_area_m2`、
`final_minimum_chord_angle_deg`、`final_minimum_corner_angle_deg`。
prefix配列はseedを先頭に明示/自動の各段を含む。版1の元サイズ意味は変更せず、
測定された最終量と明記する。物理離散化精度のstatusへ読み替えない。

既存CLI`generate-curved-remesh-plan`へ`--format plan|document`（既定plan）を追加し、
`replay-curved-remesh-generation`で全文書を検査、任意の`--out`へ裸の版1計画を保存する。
出力は既存同様排他的作成、失敗/既存出力は上書きしない。旧plan出力の意味は維持する。

GUIの`remesh-generation-settings` raw JSONを保持し、版2の最終弦サイズと境界辺数、
元P2保持・粗化限界を表示する。既存版1入力を版2へ勝手に変換しない。
`gui.py`の生成actionは完成した文書と計画の受渡しを接続し、raw重複を辞書化前に拒否する。
`web/app.js`の生成前後署名を拡張し、途中のProject/履歴/設定変更、古い応答を拒否する。
生成文書の保存/読込再検査、Study計画への反映、再読込/再起動を検査する。
Studyの`curved_remesh_study`、保存追跡/worker、中止再開で元の全native/全RF/Projectを保持する。
GUI表示や自動検証でFEMを隠れて追加しない。

## 必須五工程と独立受入ゲート

元123カードを保持し、以下をTSVとV03/V05の出口条件へ追加する。
親は互換計画の適応N04。TSVの幾何監査N04とは別ID空間である。

| 子ID | 先行 | 実装入口と終了条件 |
|---|---|---|
| ADD-N04-boundary-remesh-02 | 01 | `validate_generation_settings`と新`tests/test_curved_boundary_remesh_input.py`。全キー/版/型/有限/二history/予算、raw重複、旧意味・入力不変。計算未接続の版2は引き続き明示拒否 |
| ADD-N04-boundary-remesh-03 | 02 | `_generate_boundary_remesh_plan`/`_native_size_marks`と既存制限核。矩形/非アフィン、粗化、番号変更、尺度、Case境界/角、TEタグ、全prefix品質/予算、独立幾何/行列、無求解・決定性を確認 |
| ADD-N04-boundary-remesh-04 | 03 | build/replay、CLI二入口、裸plan/既存Study再生。元入力/全pattern/validationと改変・失敗/排他出力、API/実CLI一致 |
| ADD-N04-boundary-remesh-05 | 04 | `gui.py`/`web/app.js`/`index.html`と既存Study worker。実ブラウザーで新版保存/復元・stale拒否・旧版回帰、実worker中止再開/再起動・native完全保持 |
| ADD-N04-boundary-remesh-06 | 05 | 新`scripts/validate_curved_boundary_remesh.py`。下記独立全ゲート、専用6新FEM、全保存再生と親残件照合 |

数値gateを結果に合わせて緩めない。行列・幾何検査を周波数/場/RF/表面誤差の代用にしない。

| 検査 | 独立量・固定条件 |
|---|---|
| 全P2境界 | 曲線所有ごとに全共通区間の三Bernstein係数を比較。既存512eps×座標尺度以内、gap/overlap/逆向きtag違反は拒否 |
| 領域/既知場 | 別P2基底の8×8 Duffy面積A・`2π∫r dr dz`・`∫r³ dr dz`とGreen境界式 `1/2∮(r dz-z dr)`, `π∮r² dz`, `1/4∮r⁴ dz`。符号を整合させ相対3e-12以内。Hφ=r（u=1）の組立Mも比較 |
| 制限の保存 | 新seed→子の`PᵀK_child P=K_parent`とM、相対行列norm1e-10以内。旧独立内部meshとのGalerkin関係は仮定しない |
| 尺度 | α=1,2、Caseの長さ/角近傍も同時に尺度変換。接続/pattern一致、A/V/既知場質量の4/8/32則、相対3e-12以内 |
| サイズ/品質/拒否 | 成功最終全辺/面積が1+1e-12以内、弦/P2角が原下限以上。全prefix予算、元区間数未満、サイズ競合予算、反復枯渇、旧pattern/未知/重複/改変を拒否 |
| 円筒実FEM | R=.1 m,L=.2 m、TM010、U=1 J。辺.045/.0225 m、面積.0005/.000125 m²とα=1,2の計4solve。f相対3e-3、両R/Q・G・T相対1e-2以内。独立Bessel E/Hの物理体積重み相対L2各2e-2以内。周波数/場/RFを別表示 |
| 非アフィン実FEM | 上記曲線例とα=2の計2solve。fの1/α、両R/Q/G/Tの不変、U=1 JのE/Hのα^-3/2則、全要素求積による各相対差1e-9以内。連続物理/物理peakの未知精度はUNVERIFIED、上界null |
| 保存/利用先 | 全6nativeの元NPZ全配列/全mode/RF/規約・元Projectを公開readerで再生し完全照合。GUI/workerの追加求解は上記6と分けて数え、前後source/入力/output hash、終了handleを記録 |

専用検証のquadratureは12を基準とし、幾何積分は上記独立規則を使用する。
円筒の二水準と尺度、曲線の尺度を実行前に固定し、失敗は元結果を保持する。
物理surface peakの精度を本操作の無条件受入へ追加しないが、保存された元surface量は全量一致させる。
新数値経路03に対して関連unit/独立不変量を一度選び、seed TM数値核を変更する場合だけ
既存seed f/RF検証へ拡張する。共有核の広い変更または境界を絞れない影響時は節目fullを行う。
今回の仕様受入にはunit/full/FEMを実行しない。

出典と再利用：本書の多項式制限/Green式は明示導出と既存独立validatorに基づく。
既存P2制限・固定pattern・全境界比較・版1内部生成器の再利用を選択した。
外部/legacyコード、バイナリ、新依存、ネットワークサービスを導入しない。

# D01：非曲線TM/TE調整の形状対応

2026-10-07更新：版9のTE接続とD03原カードは [STRAIGHT_TE_TUNING_ACCEPTANCE.md](STRAIGHT_TE_TUNING_ACCEPTANCE.md) で受入。以下の「TE版9拒否/未接続」は各段階の履歴。親P01/D02/全goalは継続。

2026-10-07追記：TM版9コアの限定受入は [STRAIGHT_TM_TUNING.md](STRAIGHT_TM_TUNING.md)。以下の「現行拒否」はD01仕様時点の履歴。TE版9は引き続き拒否し、D02全条件は未受入。

2026-10-07、D01の仕様。profile・階段・軸接続単一一般輪郭の既存対応、不足する試行写像、
単位/対称セクター/最終細分を固定する。実装受入はD02（TM）とD03（TE）。
原D02親課題、P01/全goalと原互換32要件は未完のまま維持する。

## 現在の正常/拒否と接続先

| 形状 | TM | TE | 実装先 |
|---|---|---|---|
| 正半径・z厳密増加の連続区分線形profile | 要求1/2/3/7、normalized_profile。円筒のみnormalized_cylinder | 同じ要求、Ephi重み付きprofile追跡。閉PEC/最大一対称端/その鏡映 | 既存tuning・profile_mode_tracking・te_profile_tracking。再実装しない |
| 階段stepped_profile | solve/元保存はあるがtuneは拒否。独立の明示直線区分追跡は利用可 | solve/元保存はあるがtuneは拒否。直線区分の保存追跡入口も不足 | D02の試行生成/写像、D03のEphi/対称境界/保存追跡 |
| z折返し単一一般contour | solve/元保存と独立区分追跡はあるがtuneは拒否 | solve/元保存はあるがtuneと直線区分の保存追跡は拒否 | D02/D03の同じ全境界対応契約、物理別場アダプタ |
| arc_profile/二次native曲線 | 要求4/5/7/8の既存曲線経路を保持 | 既存曲線/対称・鏡映経路を保持 | 本カードで作り直さない。arcの弦を二次nativeと同一視しない |
| 組立/宣言変形のない明示solver mesh | 現在はtune拒否 | 現在はtune拒否 | 自動修復/暗黙変形で対応済みにしない |

TMの非曲線tuneは現在閉PEC端だけ。TEは同一の元端条件と同一の鏡映有無を要求し、
最大一つのelectric_symmetryまたはmagnetic_symmetry端を扱う。両端対称や異セクター間は拒否。
鏡映TEの順位は元半領域セクター内の順序で、全物理スペクトル順位へ改名しない。
TEの加速量/両R/QのN/A、TMのSI・peak phasor・二つのR/Qと固定規格化を保持する。

最小正常/拒否要求は [機械可読の六組](noncurved_tuning_scope_cases.json)。TM/TE×三形状の合成例で、
実機/KEK/LANLの測定形状ではない。各recordには全current_request/current_refusal_requestと、
全future_request/future_refusal_request、現状の拒否理由、追跡先を含める。
profileの正常2件は現行要求2の事前解析だけPASS。階段/輪郭の正常形状4件も現行tuneでは拒否。
将来要求版9は下記仕様であり、**現在の製品では全件拒否**。JSONを現行CLIに渡して使えるとは主張しない。
目標C0/Lは構文/単位検査用の有限Hz値で、対象モードの解析周波数やブラケット成立を表していない。

## 要求版9：元境界と区分アフィン法則

旧要求1〜8とそのhash/判断/再生を変更せず、非曲線専用の版9をD02/D03で追加する。
共通project/parameter/bounds/target_hz/frequency_tolerance_hz/parameter_tolerance/max_trials、
initial_ids/mode_id、controls、refinement_scale/mesh_frequency_tolerance_hzを保持し、
parameter_unit（mまたは1）とshape_lawを必須とする。未知キー、bool、非有限/逆bounds、
重複target/無効IDは拒否。自由な式の連続性/単調性や、区間内の全形状有効性を推測しない。

shape_lawはformat=straight_piecewise_shape_law、version=1、次の厳密な三宣言を持つ。

| 宣言 | 意味 |
|---|---|
| reference_comparison_mesh | 元Caseの全polygonを覆うタグ付きschema1直線三角形。SI m・rz・0-based。比較用であり元solver meshの代用品ではない |
| case_boundary_vertices | 元profile/steppedの各壁点、または正規化済みcontourの全頂点を、元比較meshの境界頂点へ一意対応。全点必須、重複/省略/role変更拒否 |
| bindings | 元比較頂点のr/zへ一つずつ単位付きexpressionを宣言。未指定座標は元の値を保持。同じ座標への重複は拒否、少なくとも一つは変数依存 |

式は既存 [scalar_expressions](SCALAR_EXPRESSIONS.md) の厳密な木だけ。例：
`{"op":"mul","args":[{"constant":0.0625,"unit":"m"},{"variable":"scale"}]}`。
variableはrootで宣言したparameter名だけ、結果はm。parameter_toleranceはその宣言単位、
目標/周波数許容差はHz。Python eval/外部状態/未宣言変数・単位の暗黙換算は使わない。

毎回、元Projectと元比較meshを再読込し、全bindingを同じparameter値で先に評価する。
まとめて一回でCaseと比較meshを再構築し、途中座標の更新順に依存させない。
前試行の丸め座標へ加算しない。元Caseのmodel、規格化、sigma、element_order、RF経路/metadataを保つ。
正常profileはz厳密増加、階段は元の孤立垂直辺を保持し、両角のzが同じ値になる法則を要求する。
壁stepを斜面へ黙って変更しない。元contourの全タグ/軸chain/辺接続を保持し、z折返しは許すが
自己交差/接触/退化を拒否。軸r=0、z=0/Lの端面はその平面と元PEC/対称roleを保つ。

両boundsの事前検査に加え、**各実試行値**で全式/元Case/比較meshを検証する。
共通接続の各三角形は正向き・非退化で、全polygonの被覆と境界roleが元Caseに一致することを
既存mesh検証と同じ基準で確認する。頂点一致/総体積だけから被覆や写像の一意性を推定しない。
全域を覆う有効な対応分割からのみ各三角形のアフィン写像を導出する。
区間内部の無効形状/式定義域/予算不足は失敗値・理由を記録し、最後の有効checkpointを保持する。

## 元FEM場の追跡と不足する実装

隣接実Project、または検索親と最終細分Projectから、元比較分割をそれぞれ評価して
controls.comparison_meshes=[previous,current]を導出する。入力controlsのmappingはpiecewise_remesh、
sample_orderと従来overlap/margin/gap/singular-value設定を保持する。
ユーザーに現在/前試行のmeshを手で差し替えさせない。宣言時controlsにcomparison_meshesを混ぜない。

両側比較meshは同じ頂点番号・向き付き接続・boundary tagsで、各々の実Case全域を覆う。
物理solverは各Caseの実meshで独立に解く。旧場を幾何変換して新しい固有解として保存しない。
TMは既存 `piecewise_remesh_tracking.track_piecewise_remesh_modes` の元Hphiを使用する。
TEは元Ephi専用の直線schema1経路を追加し、Hphi aliasやTMの本質境界を流用しない。
両側のrとdetJによる回転体積 `2*pi*r dr dz` の変化を保持した場内積で比較する。
定数の側別規格化は可能だが、非一様r/Jacobian因子を落とさない。比較sample/求積の未分解を保持する。

TEの保存追跡では現在schema1のpiecewise_remeshを拒否しており、そのguardとtrackerの両方がD03対象。
元電気/磁気対称境界とTE場復元を使い、異端条件、異polarization、通常/鏡映混在、
異なる元セクター間は**場sample前**に拒否する。鏡映分割は元対称平面に従って全域へ導出し、
元セクターのID/順位と全領域の場・体積/RFを区別して記録する。

既存 `_assemble` の実追跡・個別ID完全性と `tracked_frequency_hz` を維持する。
集合対応しかない/未確認ならfrequency=nullで二分更新前に停止し、順位をIDに読み替えない。
既存版6の明示回復を接続する場合も、元UNVERIFIEDやguardを回復要求で迂回しない。

## 最終細分とD02/D03の受入

最終は採用した実parameterの**同じ形状/境界/規格化/RF**で独立した細FEMを求解する。
通常nr/nzをrefinement_scale倍し、contourのmax_edgeとboundary/corner_max_edgeを同じ倍率で小さくする。
元比較幾何は同じまま、細solver meshは変わる。明示solver meshの未宣言変形を黙って行わない。
採用親との実個別IDを確認し、目標差と粗細周波数差の二つを別判定する。
小残差・解析倍率・目標だけの成功をTUNEDへ使わず、差未達はREFINEMENT_FAILEDを保持。
三水準RF制約のD05/D07は別契約で、この二FEM周波数診断を連続誤差上界へ拡大しない。

D02は円筒極限の独立Bessel TM、step全壁/体積/元IDと実失敗、同一候補の生成順/再開一致、
独立細分と保存API/CLI/実GUIの元要求・最終場/両R/Qを確認する。
D03はBessel TEのfと元Ephi/Hr/Hz、stepの独立細分・対称偶奇、
N/A・未確認停止・保存再開を確認する。真の縮退を強制同順位で通さない。
真空一様尺度sのf→f/s、固定Uの場→s^(-3/2)、G不変/Q→sqrt(s)と
境界解析面積/体積A→s²A、V→s³Vを独立不変量として別に使う。解析は検査専用。

直接消費先はtuning/te_tuning、saved_mode_tracking、piecewise/profileの物理別tracking、
tuning_identity_recovery、Study mesh_convergence、tuning_jobs/gui_tuning。
既存曲線経路/旧checkpointの数値や再生を変えず、変更した契約のケースをTESTINGに従って選ぶ。
受入済み曲線TEを不足する直線区分経路の代わりにせず、同時に曲線を再実装対象へ戻さない。

## D01の検査・来歴

rawは `out/d01-noncurved-scope-20261007/`。
`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python`
で同rootに保全した `build-d01-scope.py` / `fix-d01-expressions.py` / `audit-d01-future-domains.py` を実行。
現行profile正常2・未対応4・不正6の要求事前解析と、将来六領域の両bounds mesh/面積/体積尺度、
六不正領域拒否、未実装版9拒否、TE異セクターを場sample前に拒否することを確認した。
136式bindingは既存strict parserで単位/構文/両boundsの有限値を確認。FEM/unit/seed/full/legacy新実行0。

初稿の式leaf表記が既存parserに拒否される反例を保全し、製品無変更で例を既存constant/variable構文へ修正。
式検査runner初回の引数順ERRORも保全し、既存APIどおりに修正して終了0。
これは新形状tuneや物理精度の受入ではない。現行コード/テストを変更せず、過去fullの関連証拠と源を照合する。
新外部資料・依存・legacy内部参照・GPU/Hosted CIなし。既存自作幾何/式/場比較を仕様化した。
D01の仕様受入後はD02、TM実接続と独立検証を続行する。

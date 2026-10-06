# 現行の作業入口

更新：2026-10-07、P07幾何系列・独立mesh・非円形の追加細分/復旧を継続。
原90カードと追加子カードを含む全123カードの計画は継続中。P04の完了は全goalの完了ではない。
このページを現行入口とし、各文書の日付付き追記は履歴として読む。

## 横断レビューと計画（2026-09-22）

ユーザー依頼のREVIEW-01として、`a191b4e`基準の[既存実装レビュー](../IMPLEMENTATION_REVIEW_2026-09-22.md)と
[リファクタリング計画](../REFACTORING_PLAN.md)を作成した。所見10件とRF-01〜RF-10の依存・受入・検証・撤回方法を記録。
依存不在のGUIテストエラーを限定再現したが、製品・テスト・検証器は未変更、修正カードは全てPLANNED。
次にリファクタリングを実施する場合の推奨はRF-01（検証来歴）→RF-02（環境/任意依存）。
既存115開発カードの状態は維持する。以下は既存機能開発の次着手であり、今回の文書作成の継続作業ではない。

## 次の着手

**[P07：平面曲線の実解と元場・RFを実装する](03-planar.md#p07)**。IN_PROGRESS、先行P06はDONE。
[P07進行記録](../PLANAR_CURVED_SOLVER.md)で専用実solve/元12場/実側壁RF、strict点所属と元Domain細分を実装。
新10/旧物理2種類を分割確認。二尺度・両偏波の固定二次円の元12解を保持し、
TMだけL3へ追加2FEMで解析f/E/H/G全対象群を確認した。続く[最終二水準比較](../PLANAR_CURVED_CONVERGENCE.md)で
TEのE差/TMのRF差未達を保持し、追加4FEMでTE L2→L3/TM L3→L4の二尺度f/E/H/全RF差を確認。
保持元解は計18、401製品不変、許容値不変。[独立A/B内部mesh・増求積次数](../PLANAR_CURVED_INDEPENDENT.md)を検証中。続いてN16/32/64幾何と各FEM、
滑らかな楕円/再入角の二尺度・固定FEM差を[P05 gate](../PLANAR_CURVED_RF.md)で別々に検証する。
円の解析PASSだけでP07を閉じない。[P06受入](../PLANAR_CURVED_FEM.md)は継続利用、元398製品は不変。
既存dispatcher/CLI/native/Project/worker/GUIはP08、曲線比較/調整はP09で未接続。
既存P04全子とP05/P06はDONE、原互換親P02/D02とH17/H18、P07〜P09は未完了。

P03の新7/既存25件、計32件は1.871秒PASS（終了0）。
範囲・初回テスト入力エラー・解析不変量・コマンドは上記専用文書に記録。
全validate/seed/GUIの再実行はしていない。実行handle94126は終了0、生存処理の引継ぎなし。

H17は[損失範囲整理](../MATERIAL_HPHI_LOSS_SCOPE.md)まで実施しIN_PROGRESS。
2026-09-22のユーザー選択は「対象版の資料で必要性を確認してから決める」。
追加損失の採否は資料確認まで未確定。H17に依存しないP07を進める。

## 受入証拠と依存待ち

| 状態 | 根拠と限界 |
| --- | --- |
| H13 / H15 / H16カード受入済み | [曲線Hφ](../CURVED_HPHI_ACCEPTANCE.md)、[材料追跡](../MATERIAL_HPHI_ACCEPTANCE.md)、[材料調整と操作](../MATERIAL_HPHI_TUNING_ACCEPTANCE.md)。これらは親P03/P04の全旧互換受入ではない |
| B02 / B03整理済み | [B02](B02-reference-audit.md)、[B03](B03-required-scope.md)。C00.Vと未確認仕様の採否は未確定。TM旧集約JSONの欠落、TE集約hash一致を区別する |
| H18依存待ち | H13/H16はDONE。H17、C07-hphi、C07-materialが残る。H16の成功だけで親P03/P04を閉じない |
| 外部資料の不足 | R25改訂/対象版入力、K29/30ツール仕様、K31実機資料。調査カードの完了を、その資料に依存する実装・検証の完了としない |

全カードの着手可能性はTSVの`depends_on`を現在の状態で照合する。
この表は全残件の省略可能リストではなく、直近の引継ぎに必要な抜粋である。
原要件の全件対応は[計画](README.md)、[B01台帳](B01-ledger.md)と最新の専用受入文書を参照する。

## 実行中処理とソース固定

現行checkpoint：[幾何系列・終端失敗・保存解復旧](../PLANAR_CURVED_GEOMETRY_SERIES.md)。
新15unitを四回に分割PASS、混合細分の後続3unitも別PASS。円/楕円TEのN32/N64二尺度、八例計24新FEM/401製品hash不変。
各全21artifactの八例snapshotを保持。TMと全P07は未受入。
以下の古い日付付き段落は当時の状態であり、現在の生存handleはこの表を優先する。

| 処理 | 生存handle / 出力（全てout/以下） |
| --- | --- |
| 元円独立A/B | 38783 / p07-planar-curved-independent-20261007/mesh |
| 円N64 TM L4分離継続 | 92778 / 3796、p07-planar-geometry-bvh-20261007/circle-tm-s{1,2}-N64-L4-continuation |
| 角TM二尺度の境界B追加 | 37232 / 67404、p07-planar-boundary-refinement-20261007/corner-tm-s{1,2}-boundary |
| 元場groupingの保存実解再構築・測定 | 42739、p07-planar-exact-reference-20261007/field-grouping-physical-replay |

終端を観測した元非円形：TE楕円二尺度は成功25516/25128。
楕円TM尺度1/12945は終了1（B L4 RF未達）、角TE68744/27629と角TM35844/70344も終了1。
楕円TM尺度2/92077は終了143、原因未確定。元五保存解を別復旧先で物理再検証する。
角TM尺度1追加/15560は幾何検査1億回予算切れで終了1、新FEM0。元失敗rawも保持する。
旧38783の検証器5本、現行幾何10本/追加細分9本/復旧10本と全401製品を固定し、
最後の利用handle終端まで変更しない。上のhandleはwrite_stdinで終端確認し、timeoutで再起動しない。
N16の元成功を全hash/物理再構築して再利用。TM N32は全四例PASS、N64は元四例の幾何予算終端を保持して分離branchで未実行L4を継続。
TE尺度2N64のhandle99240/35751は終了0を観測。新混合細分validatorの使用10本も終端まで固定する。
楕円TM尺度1追加49794は1739.032秒/終了1、B L5元親chartの累積丸め上限未達、新FEM0。
元失敗を保持し、新2unitは3.101秒PASS。別B追加二分72293も終了1/1642.629秒、同じ累積元map丸め上限未達、新FEM0。全原失敗を保持し、許容値を緩和しない。
TEのN16/32/64は四系列（円/楕円二尺度）で限定監査PASS、handle25430終了0/13.845秒。
N16の先行物理証拠を全hash/source/数値gate付きで再利用し、新FEM/unit/物理再構築0。
11証拠Directory/239ファイルを保持する。初回二監査の引数/schema参照エラーと終端auditも保持。

main源固定中の独立作業：branch `p07-geometry-bvh` / `a1def65`、worktree `/tmp/superfish-ng-p07-geometry-bvh`。
geometry一製品ファイルだけを閉AABB候補探索へ変更、新4/直接利用先19unitは5.964秒PASS。
main製品401は不変、未統合。別実検査handle27869、出力 `out/p07-planar-geometry-bvh-20261007/`。
元A4の全係数/周波数bitwise/全RF metadata一致と独立energy/壁≤6.968e−12を確認。
分離実測27869は終了0、実L5の98304cell/147968edge・7452020box検査/同じ1e8予算でPASS。
元親map丸め1.875377e−14、解析面積/周長もPASS。新FEM0。
実uniform A5 TMのhandle34914は終了0/3011.913秒PASS、出力同親corner-tm-s1-uniform-A5 / solve-corner-A5.log。
400旧製品不変/geometry一ファイル変更、全prepared/元A4 artifactを照合して新実FEM一回を検証する。
main401は不変、34914の源固定は終了し、branch401/使用検証器は残る43214とN64四handleの終端まで固定。A4→A5対象f/E/H/全RF差は全PASS、独立B/尺度2/全P07は未受入。
分離保存B5復旧43214も開始、出力同親corner-te-s2-saved-B5-recovery / recover-corner-te-s2.log。
旧35422は終了143、cause不明、B5全rawが保存済みなので再FEMせず物理再構築/比較だけで復旧する。
N64 TMの25663/5330/19527は1e8 geometry予算切れで終了1、各L0〜L3保存済み。別終端audit保持。
楕円TM尺度1N32/99546は2457.414秒PASS、L3→L4全gate、新FEM5、401製品不変/全31artifact保持。
N64 TM/残P07は未受入。元完了解の再solveを避け、次の許容差不変の細分へ繋ぐ。
P07 IN_PROGRESS、全123カードgoal ACTIVE。seed/full validate/GUIを実行したとは扱わない。


2026-10-07追加checkpoint：角TE尺度1の53536は終了0/3811.488秒、新実FEM1でA3/B5受入。
円TM尺度1/2のN32（1671/23517）と楕円TM尺度2N32/65048は終了0、各L0〜L4の5実FEM。
既成功楕円TM尺度1N32を合わせTM N32全四例がPASS。全401製品/使用validator不変。
別限定監査31961は終了0、新FEM/unit/物理再構築0、四例105全artifactと数値gate/規約を保持。
N64円TM尺度2/66415も終了1/2501.715秒、L0〜L3保存、L4幾何予算1e8切れ。
分離driver `out/p07-planar-geometry-bvh-20261007/continue-N64-TM.py` を構文検査後に開始。
円s1/s2は92778/3796、楕円s1/s2は86568/16110、出力同親 `<shape>-tm-s<scale>-N64-L4-continuation/`。
全元10validator/source/hash/実終端と400旧製品不変/geometry一変更を照合し、
保存L3の全元chart/native/係数・周波数bitwise/全RF完全一致/独立積分を物理再検証する。
元完了FEMを繰り返さず、未実行L4のみ新実solve。1e8予算/512ε/全物理gateは不変。
branch401/共用11validator/新driverを34914/43214/上の四handleの終端まで固定する。
main401も残る旧三handle38783/50414/27391の終端まで固定。P07/全goal ACTIVE、N64実受入は未確認。


独立追加branch `p07-boundary-refinement`、worktree `/tmp/superfish-ng-p07-boundary-refinement`。
元楕円TM B4の壁RF未達と一様/二分の丸め終端に対し、明示的な境界cell適合細分を実装した。
[元map/energy不変量と実検証範囲](../PLANAR_CURVED_BOUNDARY_REFINEMENT.md)。
新3/旧直接利用10の計13unitは8.048秒PASS/59598終了0、変更前の独立一件ERRORを保持。
新実handle99269、出力 `out/p07-planar-boundary-refinement-20261007/ellipse-tm-s1-boundary/` と同名log。
旧399製品不変・geometry/refinement二変更、全元8/9/10validator、実終端、元係数/全RF完全一致を必須とする。
三保存解を物理再構築し、元Aの受入を再確認後、一回の新境界B FEM/元E/H/全RFを検査する。
branch401/使用10validatorは終端まで固定、main/bvh branch源を変更しない。RF/P07成功は未確認。


独立性能branch `p07-reference-basis-cache`、worktree `/tmp/superfish-ng-p07-reference-basis-cache`。
[参照表のbitwise保存・実測・strict残件](../PLANAR_CURVED_REFERENCE_CACHE.md)。
参照basisだけを最大32表/各4096点まで再利用、実J/K/M/場/係数/RFは再計算する。
新3/旧直接利用22の25種類は分割成功。初回24PASS/既存一ULP所属への期待1FAILを保持し、
cache互換範囲のその一件だけ0.003秒PASS（68737）。元APIの一ULP外参照受理は別reproducerで確認した。
単要素order8/12/16実測は14〜17倍、全mapped配列/K/M bitwise一致。
保存済みellipse TM A4の実物理再構築78576は終了0/288.568秒PASS、新FEM0、出力 `out/p07-planar-reference-basis-cache-20261007/results/`。
前後branch401/使用11コード不変、全元係数/周波数bitwise・全RF metadata完全一致、独立積分最大1.037e−13。
cache単独source固定を解除し、次はstrict参照所属を是正する。main/BVH/boundaryの生存源固定は継続。
既存strict参照の和丸め不備はP07完了前に是正する必要があり、性能成功から解消済みとはしない。
壁参照/元場/locatorの厳密閉所属を整合し、内部boundary表現と実壁RFを別検証する。
全goal/P07 ACTIVE、P08/P09と全原要件を維持。


strict参照修正：[独立反例・閉壁整合](../PLANAR_CURVED_EXACT_REFERENCE.md)。
source固定が解けたcache branchでgeometry/元場/validator/locatorの厳密閉所属を実装した。
新4/旧直接利用24の28種類は分割成功。初回25PASS/閉壁probe二ERRORを保持し、その二件だけ0.217秒PASS、
実TM PEC壁Ez=0の追加一件は0.101秒PASS。許容値は不変、他25成功を繰り返さない。
新物理再構築74571、出力 `out/p07-planar-exact-reference-20261007/physical-replay/` と `replay.log`。
旧397製品不変・geometry/location/refinement/solver四変更を明示し、TE L3/TM A4の全係数/周波数bitwise、
全RF metadata完全一致と閉壁parameterの丸め差≤1e−12/独立積分≤1e−8を検証する。
74571は終了0/230.797秒PASS、新FEM0。全係数/周波数bitwise・全metadata完全一致、RF差TE0/TM最大2.221e−16。
branch401/使用7code/元artifact不変、独立積分最大1.037e−13。branch単独source固定を解除する。
main/BVH/boundaryの生存源を変更せず、全P07と統合は未受入。


楕円TM尺度2の復旧70467は6484.605秒PASS/終了0。元143/原因未確定・五保存解を保持し、
元五解を物理再構築後、未保存のB4/B5だけ二実FEMを追加、A4/B5全gate受入。
B4→B5全RF差最大1.767055e−3、A4対B5最大1.213063e−4、前後401製品/使用10validator不変。
全15artifact snapshot/別terminal auditを保存する。楕円TM尺度1と全P07は未受入。


円独立38783のTM半径0.01 B5は81920cellの全Case/係数・周波数/chart/patternsが保存済み、gateは未保存。
元APIはcellごとに全point vectorをmaskし、order8全域5242880点では一mode当たり429496729600要素を走査する。
読取証拠 `out/p07-planar-exact-reference-20261007/original-circle-field-scan-audit.json`。
次のbounded改善は、pointを一回だけowner別に整理し全元出力をbitwise保持すること。
現handleは生存/源固定を継続し、timeoutによるrestartや保存済みB5の再FEMをしない。

### 先行実行の履歴

2026-10-07 P07：専用比較器 `scripts/planar_curved_mesh_reference.py` と
`scripts/validate_planar_curved_independent.py` を追加。元Domainから全chartを再生成し、
有理数の共通参照分割で元E/Hを直接比較する。新6/既存5unitは28.116秒PASS。
独立壁積分の最初の実行は検証器のJacobian key誤参照で終了1（新FEM1、保持済み）。
keyだけ修正し独立面積/全vector壁検査を1unit追加、session9777へ実行中。
求積系列の修正後session76545、出力 `out/p07-planar-curved-independent-20261007/quadrature-final/`、
logは同親の `quadrature-final.log`。二尺度・両偏波のarea8/12/16、wall12/16/20を別々に解く。
製品401ファイルと検証器5本をhash固定。終了まで製品/使用検証器を変更しない。
追加1unit/session9777は1.475秒PASS/終了0。求積/session76545は42.155秒PASS/終了0、
12元解と最後4解の物理再構築を保存、401製品hash不変。
独立mesh/session38783が実行中。出力は同親 `mesh/`、logは `mesh.log`。
元Aは前回最終二水準の全hash/物理再構築で確認し、Bの初期未達と実細分を別保存する。
TE半径0.01のB L2→L3はTE01 E差1.027957%で未達、A L3対B L3/解析対照はPASS。
許容差を維持しB L4を追加中。楕円/角入力の新4unitは4.734秒PASS、
vector化候補の新3unitは0.018秒PASS/単一patch10.56倍実測、使用validatorへ未接続。
後続の明示adapterは全array/元RF/全参照比較の追加2unitをPASS、群guard拒否1unitもPASS。
円meshの使用検証器には接続せず、別の[楕円・再入角driver](../PLANAR_CURVED_SHAPES.md)へ接続した。
楕円TE尺度1/session25516と角TE尺度1/session68744が実行中。
出力は同親 `ellipse-te-s1/` と `corner-te-s1/`、logは同名 `.log`。
全8非円形を並行検査：ellipse TE s1=25516 / TM s1=12945 / TE s2=25128 / TM s2=92077、
corner TE s1=68744 / TM s1=35844 / TE s2=27629 / TM s2=70344。
各出力は同親 `<shape>-<polarization>-s<scale>/`、logは同名 `.log`。
これらは401製品と使用8検証器をhash固定。円38783を含む全9handle終端まで変更しない。
非円形TE尺度1のA L2→L3は楕円/角ともPASS、Bの初期未達を保持して細分中。
独立FEM尺度・回転・平行移動の新3unitは0.083秒PASS。専用session71524を開始、
出力同親 `covariance/` / `covariance.log`、401製品と使用7検証器をhash固定。
全10handleの終端を観測し、各受入と原P07受入を分ける。
終端：楕円TE尺度1/25516は351.293秒PASS（5実FEM、A L3/B L3の全gate、401製品不変）。
共変性71524は11.919秒PASS（円/楕円/角両偏波12実FEM、全場/RF尺度則最大5.346e−13）。
楕円TE尺度2/25128も450.860秒PASS/終了0（A L3/B L3、5実FEM、401製品不変）。
現在は円mesh38783と非円形の残6handleが継続中：corner TE68744/27629、
ellipse TM12945/92077、corner TM35844/70344。終了した25516/25128/71524を再起動しない。
[仕様・分割検査・失敗履歴](../PLANAR_CURVED_INDEPENDENT.md)。
sessionを `write_stdin` で観測し、timeoutを理由に再起動しない。P07/全goalは未完了。

P07最終二水準：全handle終端、401製品/比較器固定解除。
新5unit/session79738は1.828秒PASS/終了0。初回/session8261はnp.bool_ JSON保存で終了1、新FEM0。
保存型だけboolへ修正し、JSON往復追加の限定1unitは0.521秒PASS/終了0。失敗log/出力を保持。
専用/session72321は1086.911秒PASS/終了0。元14解raw全hash不変、最終8解を物理再構築。
TE01 L1→L2のE差1.031212%/TM L2→L3のP′差0.851679%の未達を保持し、元境界を保った追加4FEM。
TE L2→L3/TM L3→L4の二尺度f/E/H/全RF差PASS、計18元解保持、追加fineの解析対照もPASS。
最大P′差0.221120%、親chart座標上限9.039e−15、独立場energy差2.513e−13、401製品不変。
証拠 `out/p07-planar-curved-convergence-20261002/`、[限定受入と残gate](../PLANAR_CURVED_CONVERGENCE.md)。
次は同初期Domain独立A/B内部meshの全場/全RF、増次数/幾何系列/楕円・角も残る。
P07 IN_PROGRESS/全goal ACTIVE、生存handleなし。

P07初回解析対照（履歴）：全handle終端、401製品hash固定解除。旧398全ファイル不変、新3製品ファイルのみ。
新solver7/同Domain細分3 unit/session19390は10件2.343秒PASS/終了0。旧直線物理2件は初回成功を保持、計12種類。
初回/session18384は8PASS/1FAIL、1.036秒/終了1。ほぼ零TE Exの単独相対値比較を、同係数場と全E/H normへ分離。
限定/session4352は1件1.007秒PASS/終了0。その後の全モードAPI追加で新10件を確認した。失敗log保持。
円三水準/session81249は12FEM、68.327秒/終了1。TE全target L2 PASS、TMはf/E/H PASS/G最大1.13743%で未達。
401hash不変と元12解を保持し、circle-extended/session65520でTM二尺度だけL3へ延長。
追加2FEM、保持14解、111.818秒PASS/終了0。TE L2とTM L3で解析f/E/H/G全対象群PASS、TM G最大0.295791%。
各実行内の401hash不変、独立field energy差最大1.081e−13、元398不変。
延長後の検証器indent/import整理はASTのみ、新FEM/製品変更なし。全handle終端、src固定解除。
証拠 `out/p07-planar-curved-rf-20261002/`、[限定成功と残る全gate](../PLANAR_CURVED_SOLVER.md)。
次は上記P07残条件の独立検証、P07 IN_PROGRESS/全goal ACTIVE。生存handleなし。

P06：全handle終端、398製品hash固定解除。先行unit/session56921は新9/既存5、14件2.317秒PASS/終了0。
shared拒否追加/session95476は1件0.024秒PASS/終了0、全Jacobian拒否追加/session31040は1件0.006秒PASS/終了0。
専用geometry/form validator/session15905は四ring円6Domain/12行列スペクトル、16.202秒PASS/終了0。
mass面積差最大3.331e−16、定数核相対norm最大2.612e−16、N64の面積/周長/距離は1e−4幾何gate以内。
実行前後398製品hash不変、元395製品も不変。新3製品ファイルのみ、shared core/seedに差分なし、seed/full validate未実行。
初回/session28014は8PASS/1FAIL、0.783秒/終了1、重複cell fixtureの未使用node先行拒否を修正し失敗log保持。
証拠 `out/p06-planar-curved-fem-20261002/`、[条件別受入と来歴](../PLANAR_CURVED_FEM.md)。
次はP07、全goal ACTIVE。生存handleなし。

P05：解析reference/session96355終了0、新FEM0。Bessel norm/エネルギー/壁G最大6.662e−16、
等分配8.882e−16、符号curl3.995e−10、二尺度則PASS。
仕様auditは全123カード/依存/節ID/JSON例/入口links20件/二尺度patch・Green積分を確認、2.647秒/終了0。
初回の小見出し未認識は監査器のみ修正し、失敗logを保持。数式照合を再実行しない。
395製品hashは前後不変、文書だけでunittest/seed/全validateは未実行、生存handleなし。
証拠 `out/p05-planar-curved-spec-20261002/`、[仕様受入と後続の責任](../PLANAR_CURVED_RF.md)。
次はP06、全goal ACTIVE。

P04-c-b：全handle終端、395製品hash固定解除。Python/session7780は10件160.560秒PASS/終了0。
独立API/session95901は3pair PASS/終了0、全照合/session12034は3pair全判断/所有履歴、70配列・全RF/最終Project一致/終了0。
browser2/session58021は9項目PASS後の回復宣言誤りで終了1、保存済みpair/履歴を継続したbrowser4/session19976は7項目PASS/終了0。
新サーバー復元/session67927は5項目PASS/終了0、最終CSS限定/session73174は3項目PASS/終了0。
表示修正後の差分はweb HTML/JS/CSSのみ、数値ソース不変。全reportは外部要求0、各実行内の製品hash不変。
server12853はSIGINT終端130、server86426はSIGINT正常終了0。所有browser slotは空。生存handleなし。
証拠 `out/p04cb-planar-tracking-gui-20261002/`、[失敗・分割操作・表示と最終受入](../PLANAR_PIECEWISE_TRACKING_GUI.md)。
修正前form/session51699の宣言喪失、prepare/session6542のfixture順位0、browser初回23379/3回目79214の検証器入力不備を保持。
原P04/全子監査を受入し次はP05。全goalと原互換親P02/D02は継続。

P04-c-a：製品 `c81782d`、395ファイルを固定した実操作。
新版browser4/session1506は11項目PASS/終了0、旧アフィンbrowser/session53127は5項目PASS/終了0。
新サーバーbrowser/session25370は復元4項目PASS/終了0。全reportで外部要求0、製品hash不変。
独立API session83901はTUNED4試行、61.034秒/終了0（api-success/）。
全native照合session33079は終了0、4試行+取込の50配列、Project/要求/全判断/RF一致。
解析TE10相対差1.0703275159507086e-6。全製品hash不変を確認しsrc固定解除。初回audit/session42718はGUI runtime exportへowned-disk readerを誤用して終了1。
監査器だけをruntime replayへ修正し、同じ既存結果を照合してPASS。新FEMは実行しない。
server90303/76968はともにSIGINT正常終了0、全ブラウザー回収済み、所有slotディレクトリなし。
新版/旧版/復元の場画像を目視し、単位J/mとRF N/A、対象順位、全三場を確認した。
最初のsandbox内loopback bindはEPERM/終了2であり、昇格したローカルサーバーを使用。
browser初回99585は起動待ちReferenceError、browser2/7873は旧error誤判定、
browser3/84849は応答前の次入力による正しいstale拒否で終了1、各回収済み。
検証器だけを応答counterで同期しbrowser4成功。各失敗report/logを保持する。
証拠 `out/p04c-planar-browser-20261002/`、[操作/全元場照合](../PLANAR_PIECEWISE_TUNING_GUI.md)。
新GUI1/旧GUI5のPython操作はsession93859、160.930秒PASS/終了0。
修正前地点選択はsession11909、6.316秒ERROR/終了1。証拠 `out/p04c-planar-gui-20261002/`。
上記P04-c-bで単独追跡/履歴と親P04監査も受入。

2026-10-02：P04-b-cのsession19594は603.667秒、17件中16PASS/同じ中止テスト2ERROR、終了1。
移動済み中止jobの旧pathをテストprocess辞書から除く修正後、session11536は1件40.054秒PASS、終了0。
分割17種類（新5/旧直接利用12）PASS、395製品hash不変。全handle/worker終端、src固定解除。
元移動・実中止/再開・管理器再作成・最終回復・未確認null・改変拒否を確認し、親P04-bを監査受入。
証拠 `out/p04bc-planar-worker-20261002/`、[条件別監査](../PLANAR_PIECEWISE_TUNING_WORKER.md)。

2026-10-02：P04-b-bは初回session30100終了1（新7件、2PASS/3FAIL/2ERROR、85.712秒）。
格子改善後session99948終了1（選択21件、20PASS/CLI期限1ERROR、846.030秒）。
旧版1〜3の14件全PASS。CLI300秒期限の再確認session65480は256.734秒PASS（終了0）。
独立TMはsession12993終了1（8/16gridでiteration limit）後、12/24gridのsession11671が
192.929秒PASS（終了0）。分割22件成功、全数値許容差を保持。395製品hash不変、
全handle終端、src固定解除。証拠 `out/p04bb-planar-owned-20261002/` と[専用記録](../PLANAR_PIECEWISE_TUNING_SAVED.md)。

2026-10-02：P04-b-aは初回session36755終了1（28PASS/1FAIL、146.388秒）。
再生成/幾何検査の順序修正後、session64698の影響17件は45.567秒PASS（終了0）、
非影響の初回12件成功を保持する。各実行の394製品hash不変、全handle終端、src固定解除。
証拠 `out/p04ba-planar-shape-20261002/` と[専用文書](../PLANAR_PIECEWISE_SHAPE.md)。

2026-10-02：P04-aのsession39306は終了1（54PASS/誤メソッド名1収集ERROR）。
正しいstrict1件と独立元場/RF2件は別実行で終了0。分割57件PASS、391製品ファイル不変、
全worker/handle終端、src固定解除。証拠 `out/p04a-planar-piecewise-20261002/`、詳細は専用文書。

履歴Chrome session 91632と調整/新サーバーsession 87997は終了0。
全Chrome/サーバー/managerをclose済み。製品src固定解除、生存handleの引継ぎなし。
証拠は `out/p02-planar-history-browser-20260922/` と `out/p02-planar-tune-browser-20260922/`。
各reportの389製品hashを現行ファイルと照合し不変。
sandbox内のプロセス一覧はホスト全体の不存在証明に使わない。

長時間処理を開始したら、この節にツールsession/cell ID、PID（取得できた場合）、
ジョブ/出力パス、開始時実装hash、次の観測方法、ソース固定範囲を記録する。
引継ぎでは同じhandleを観測し、観測timeoutだけで再実行しない。
古い履歴のPID/「生存中」を現在の生存証拠にせず、終端結果または現存handleで確認する。

## 更新手順

1. 開始時に`git status --short`とTSVを確認し、次カードの条件・専用文書・実装を読む。
2. 作業中はこのページの次着手/処理状態を更新する。BACKLOG・CODEX_HANDOFF・計画READMEの先頭案内は固定し、同じ進捗段落を三重追記しない。
3. 受入時は専用文書へ条件別の結果、実行コマンド/終了状態、失敗/未確認、証拠パスを記録する。TSVは満たしたカードだけ更新し、部分受入と親受入を分ける。
4. このページを次カード・残る依存・生存処理に合わせて更新し、整合したローカルコミットを作る。履歴の大量削除/一括再編はしない。
5. 原計画の全条件と追加必須カードを監査して初めてgoal完了を判断する。履歴の「全goal ACTIVE」「次は」は新しい開始命令ではない。

B04確認：3入口から本ページ、着手条件・実装・検査・受入証拠へのリンク、
全111カードと依存、差分を確認しPASS（リンク節IDを含む、git diff --checkもPASS）。文書のみで数値計算・unittestは実行しない。


## 楕円TM境界B・角TE尺度2の終端と角TM残件（2026-10-07）

99269は2464.466秒PASS/終了0。元A3/A4/B4を物理再構築し、新境界Bの実FEMだけ一回追加した。
21760cell（旧B4は20480）、最終元map丸め7.028348e−14。B4→境界Bの対象f差最大2.1547e−8、
E差4.0985e−6、H差2.076318e−4、全RF差1.701740e−3。独立A4対BのRF差最大5.874163e−5。
完全band/独立energy・実壁積分も原gateでPASSし、楕円TM尺度1 A4/境界Bを受入した。
元399製品不変・geometry/refinement二変更、前後401分離製品/使用10validator/全元artifact不変。
別終端auditと全12artifact snapshotを保持。楕円二尺度の両偏波は各固定FEM条件を満たした。

角TE尺度2の保存済みB5復旧43214も3891.121秒PASS/終了0、新FEM0。
元終了143の原因は依然未確定。A3/B4/B5を全元chart/nativeから再構築し、全係数/周波数bitwiseと
元A3/B4全RF完全一致を確認した。対象B4→B5のf差1.101088e−5、E差4.222931e−3、
H差1.208029e−4、RF差3.629551e−5、独立A3対B5 RF差3.721745e−6。
完全band/独立積分もPASSしA3/B5を受入、角TE両尺度の固定FEM条件を満たした。
400旧製品不変・geometry一変更、前後401分離製品/使用10validatorと元39artifact不変。
復旧出力全8artifactのsnapshot/終端auditを保持し、保存済みFEMを再solveしない。

角TM混合細分50414/27391は終了1、7130.991/7129.920秒。各新3実FEMでAの混合細分は受入したが、
Bの第3対象群は最後二水準RF差5.514924e−3（0.551492%）で0.5%gate未達。
対象第1/2群RF差4.502693e−3/4.409091e−3、全f/E/Hと独立A/B（RF最大2.182286e−3）はPASS。
全401製品/使用10validator/元22artifact不変、各全21artifact snapshotと実終端auditを保持する。
B/角TM/P07を受入せず、既存境界patternで各尺度の保存Bへ局所細分を一回だけ追加する。
新driver `extend_planar_curved_corner_boundary.py` の全source/終端/raw preflightは二尺度PASS。
元accepted Aと最終Bを全chart/native/RFから物理再構築し、再FEMせず、新境界Bだけ各一実FEMを検証する。
boundary branch401製品/使用10validatorをhandle37232/67404の終端まで固定する。
出力 `out/p07-planar-boundary-refinement-20261007/corner-tm-s{1,2}-boundary/` と同名log。
1e8 geometry予算・512ε元map丸め・f/E/H/RF許容値・完全guard・独立積分は全て維持する。

上記終端四件の限定監査は新FEM/unit/物理再構築0。全前後hashと数値gateを照合し、受入を
証明済み形状/偏波/尺度に限定する。元円独立mesh38783、N64 TM四件、全P07とP08/P09は継続する。

[元場point groupingの反例・bitwise条件・14unitと保存実解測定](../PLANAR_CURVED_FIELD_GROUPING.md)を追加。
95559は終了0/1.464秒PASS。新測定42739は実終端までcache branch401/使用8codeを固定する。
元38783は半径.01両偏波を受入済み、半径.02 TE B3生成済みで生存中。旧源を改変せず継続する。
現行源固定はmainの38783のみ、BVHのN64四件、boundaryの角TM二件、cacheの42739。
終端99269/43214/50414/27391は上表から外した。先行する過去記録中の「生存」はその時点の記述である。
mainは文書のみ変更、全401製品hash不変。P07/全goalは未完了であり、全123カード範囲を維持する。


## 楕円TM N64両尺度のL4終端受入（2026-10-07）

分離継続86568/16110は終了0、3918.479/3921.632秒PASS。元L0〜L3四保存解と予算切れ終端を保持した。
保存L3の全元chart/native/K/M/係数・周波数・RFを再構築し、未実行L4だけ各一新実FEM。
各114688cellのL4で、対象L3→L4最大f差8.281288e−8、E差7.256088e−6、H差4.070364e−4、
全RF差1.435390e−3。真面積/周長/境界距離、全band、独立energy・壁も原gateでPASS。
最終元map丸め尺度1/2は9.256923e−14/5.064288e−14、512ε以下。
400旧製品不変・geometry一変更、前後401分離製品/使用12code/元各25artifact不変。
各全13artifact snapshotと観測終端auditを同親に保持。限定監査は新FEM/unit/物理再構築0。
楕円TMのN16/32/64二尺度の条件別実証拠が揃った。TEの先行四系列受入と分けて記録する。
元円独立全尺度、円TM N64二尺度92778/3796、角TM境界B二尺度37232/67404、grouping実測42739は継続中。
P07全条件監査・source統合は未完了、P08/P09と全123カードgoal ACTIVEを維持する。
BVH branch401/使用12codeは残る円N64二handle終端まで固定する。


## 楕円TMの有限幾何系列監査（2026-10-07）

楕円TM二尺度のN16/32/64を限定監査36705で受入、4.167秒/終了0。
元source版をmain旧401、geometry一変更のBVH401、geometry/refinement二変更のboundary401へ明示分離し、
全accepted artifact snapshot/前後source/元validatorを照合した。各完全6モードと三対象群のf/E/H/全8RF差、
完全guard gap、U′=1・peak +iωt・J/m/W/m、両R/Qと加速量の理由付きnull、独立energy/壁を数値で検査する。
各元Domainのareaとfine RF areaも照合した。真面積/周長/境界距離は元N16/32/64を小規模再生成して別検査し、
三誤差が単調減少しN64で各1e−4以下を確認した。異なる幾何Domain間の場差は計算していない。
六証拠Directory/計115artifactを保持、新FEM/unit/物理再構築0。
出力 `out/p07-planar-curved-geometry-20261007/ellipse-tm-geometry-series-audit/`、全7audit artifact snapshot/終端も保存。
先行TE四系列とは別のTM楕円二系列受入。残る円TM N64/角TM/元円独立全尺度/source統合/P07全条件を維持する。

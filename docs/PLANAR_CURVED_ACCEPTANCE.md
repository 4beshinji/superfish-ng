# P07：元条件別受入監査（作業中）

2026-10-07。原P07/P05の条件を維持する。これは完了宣言ではない。
P07 IN_PROGRESS、全123カードgoal ACTIVE。各日付付き専用文書を局所証拠とし、
最終受入には残る実終端・統合予定sourceの物理bridge・主source統合を確認する。

## 原条件と現在の証拠

| 条件 | 現在の根拠 | 判定と限界 |
| --- | --- | --- |
| 明示vacuum XY cutoff TE/TM、closed PEC、元P2 Domain/Case、SI/peak +iωt/U′ metadata | [P05契約](PLANAR_CURVED_RF.md)、[P06](PLANAR_CURVED_FEM.md)、[実solver](PLANAR_CURVED_SOLVER.md) | 専用Case/実配列APIで確認。伝搬/TEM/端板/materialや一般dispatcherは含めない |
| 実面積K/M・TE定数核1個除外・TM essential壁、全正帯・規格化・M直交/最低帯再構築 | P06の独立moment/Gram/直線limit、P07実solver7unit/改変拒否、保存解の全native/K/M再構築 | 解析式をsolveに代用しない。小代数残差を離散化差に数えない |
| 元12phasor場、符号付きMaxwell、実J・元係数からの勾配、曲線の片側実壁RF | P07 solver/旧物理unit、独立area/wall積分、[vector reference](PLANAR_CURVED_INDEPENDENT.md) | 公共APIと独立式を確認。各群のE/Hに同じscalar rotation、別phase/振幅fitなし |
| 両R/Q定義・Vacc/Eaccの理由付きnull、U′e/U′m/P′/Rs/Q0/G/壁H積分・SI/次数 | P07全RF、[有限幾何系列監査](PLANAR_CURVED_GEOMETRY_SERIES.md)、[source bridge](PLANAR_CURVED_SOURCE_BRIDGE.md) | 各完全帯の全schemaを数値/metadataで検査。有限加速路を未宣言のcutoffへ作らない |
| 円r=.01/.02、TE対象完全群[2,2,1]＋guard[2]、TM対象[1,2]＋guard[2,1]、三水準以上の絶対f/E/H/G | [元14解と粗いFAIL](PLANAR_CURVED_SOLVER.md)、[追加4解・最終二水準](PLANAR_CURVED_CONVERGENCE.md) | 元P05 f1e−4/E,H1%/G0.5%でPASS、合計18元解。FAILの許容値は保持 |
| 固定円最終二水準のf/E/H/全RF | TE L2→3/TM L3→4二尺度、全元parent/nativeと直接vector差 | PASS。最終FEM差と真円絶対誤差は別判断 |
| 同じ初期二次円の独立A/B、最後二水準＋A対B＋絶対円＋独立積分 | 元38783、半径.01 TE B4/TM B5、半径.02 TE B4がPASS | 半径.02 TMと全最終report/実終端は未確認。P07を閉じない |
| N16/32/64の真面積/周長/距離と十分細かい各固定FEM、二形状/二尺度/両偏波 | [八有限幾何系列監査](PLANAR_CURVED_GEOMETRY_SERIES.md)：TE四系列、TM楕円二系列、TM円二系列 | 全八系列PASS。真幾何誤差の単調減少・最終1e−4と各FEM f/E/H/RFを別判断。異なるDomain間の場比較なし |
| 楕円(.02,.012)二尺度・中心(−.03,.01)・回転π/7、固定A/B f/E/H/RF・guard・独立積分 | TE二尺度A3/B3、TM尺度1 A4/境界B、尺度2 A4/B5 | 旧source variantを明示してPASS。楕円絶対f/Gに円倍率を流用しない |
| 3π/2再入角L字 a=.01/.02、面積3a²/周長8a、局所r^(2/3) harmonic/有限energy・壁積分 | [shape reference/角検証](PLANAR_CURVED_GEOMETRY_SERIES.md)、角TE両尺度A3/B5、角TM両尺度混合A/境界B | TE/TM両尺度PASS。角TM37232/67404終了0、last-two RF最大0.236740%/A対B0.455482%。元混合B第3群0.551492% FAILを保持。有限peak/解析絶対f/Gは未主張 |
| 最終二求積次数で全正帯f/全RF≤1e−8、area8/12/16・wall12/16/20 | [quadrature-final](PLANAR_CURVED_INDEPENDENT.md)、新12実FEM＋四保存再構築、76545終了0 | PASS。max f1.077e−14/RF2.309e−14、独立積分2.198e−14。seed/全validateの証拠ではない |
| 実scale2＋proper rotation/translation、全signed vectorとRFの尺度則≤1e−8 | covariance71524、円/楕円/角・両偏波の12実FEM、[専用証拠](PLANAR_CURVED_INDEPENDENT.md) | PASS、max5.346e−13。粗い元Domainの共変則、絶対/mesh収束へ水増ししない |
| 全元parent完全被覆・P2制限・T接続なし・最終元map丸め≤512ε/local extent | Fraction restriction chain/共通parent overlay、[boundary保存不変量](PLANAR_CURVED_BOUNDARY_REFINEMENT.md) | 全accepted caseで確認。projection/許容値緩和なし。累積丸め/予算失敗を保持 |
| 全域detJ/外周simple閉接触・strict入力・unknown/予算不足のFEM前拒否 | P06 geometryと[閉AABB BVH](PLANAR_CURVED_GEOMETRY_SERIES.md)、[厳密閉参照](PLANAR_CURVED_EXACT_REFERENCE.md) | BVH新4＋旧19、Fraction一ULP反例と閉壁整合28種類分割PASS。主sourceへstrict修正は未統合 |
| 元場point batchの演算/順序保存 | [grouping新3＋旧11の14unitと実TM B5再構築](PLANAR_CURVED_FIELD_GROUPING.md) | bitwise/全RF metadata/独立energy・壁PASS。単回random scalarは低速化、全入力や全FEMの倍率を主張しない |
| 旧源variantから統合予定strict/cache/grouping kernelへ保存配列/全RFを結び付ける | 元401製品＋15validator保全、[noncircle source bridge](PLANAR_CURVED_SOURCE_BRIDGE.md) | 新4unit分割PASS、楕円TM/角TE三例の実bridgeとbyte/全帯trace補足PASS。旧validator source保全済み。受入角TM二尺度bridge16323/8632実行中、最終source統合は未完了 |
| source・provenance・検査範囲・coherent local commit | [CURRENT](development-plan/CURRENT.md)、各raw/source/validator hash・観測終端audit、専用文書/ローカルcommits | 局所証拠として保存。legacy source/binary参照・新依存なし。hosted CI/full/seed/GUI実行を未観測のまま主張しない |

## 完了前の具体条件

2026-10-07の横断照合では、既存reportの円絶対/固定最終二水準四case、非円形独立A/B八case、
求積四case、粗い元Domainの共変六case、有限幾何八系列を元数値gateで確認した。
全対象群/guardのrank被覆、全RF schema/理由付きnull・peak/J/m、独立20次積分、元map boundを別々に検査する。
Boolean PASSだけを根拠にせずf/E/H/RFの数値と元群数を確認した。
出力はignored `out/p07-planar-exact-reference-20261007/completed-physical-gates-bound-inputs.json`。
監査コードhashと読取report/source manifestの全hashを前後照合し、入力を結び付ける。
これは元受入rawの物理再構築や全P07受入の再実行ではなく、新FEM/物理再構築/unitは全0。
初回監査のreport形式差（coarse/fine RFとfirst/second RF、restriction boundとchart bound）による
KeyError三logを保持し、元データ/許容値を変えず形式別の明示照合へ修正した。
下記未確認条件はこの横断照合でも未完了のまま残る。

1. 元円独立38783の半径.02 TMを含む全四caseの実終端と完全report/source/rawを受入する。
2. 角TM二尺度の新境界Bは最後二水準/独立A対B/完全guard/独立積分を原gateで受入済み。全11artifact/401源/10validatorの終端snapshotを最終照合へ使う。
3. 統合予定kernelで元accepted noncircleの全native/K/M/最低帯・係数/周波数bitwise・全RF metadataと
   canonical閉壁浮動差≤1e−12、signed公共場/独立積分を確認する。角TMも同条件で結び付ける。
4. 既存利用handle実終端後に四製品・二strict validator・対応testsを限定統合し、源を保全した旧証拠と
   新kernelの一致を監査する。sourceの差を「全401不変」と表現しない。
5. この表の全P07条件を実際の最終sourceとartifactで再照合し、未確認が残ればIN_PROGRESSを維持する。

P08のnative/Project/CLI-worker/Study/GUI、P09の比較/追跡/調整・所有再開は後続必須カードである。
専用P07 rawは製品native受入形式ではない。P07の将来DONEも全goal/原互換親の完了ではない。

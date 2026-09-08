# G03 接線自動構築の契約と実装順序

2026-09-08。G03全体の受入ではない。既存check_curve_joinは完成した曲線同士の
G1接続を検査するが、未知の接点・接線を構築しない。
本書は共通直線接線の候補列挙から始めた仕様と実装履歴を保持する。
現在は末尾の版6まで保存/Case/CLI/GUIへ統合済み。各節の残件はその時点の履歴であり、
最新の到達点と不足は[G03照合表](G03_ACCEPTANCE.md)に従う。

## 必要な入出力と候補選択

円/楕円/双曲線の有限有向弧を2つ受け、有限接点を持つ共通接線候補を列挙する。
円は楕円の等半軸として扱う。双曲線は指定枝とパラメータ区間に制限する。
候補ごとに元曲線上の接点区間、接点位置、直線の正規化された法線/定数、
接続方向、位置/接線残差、探索完了性を保持する。
複数候補は明示選択を必要とし、配列先頭・短い線・小さい残差だけで自動選択しない。
曲線の切詰めは候補選択後の別操作。元プリミティブを黙って移動・接着しない。
同一点への接触による長さゼロの線をLineSegmentとして生成しない。

線分と曲線では線分の支持直線を使い、延長を許すか/どちらの端を接続するかも
明示する必要がある。任意フィレットを共通直線接線へ読み替えない。
重複する曲線による無限候補、接点が無限遠となる漸近線、弧端付近での判定不能は、
候補なしと区別する。探索未完了を空配列の成功にしない。

## 列挙の数学的方針（円錐曲線全体へ実装済み、有限弧へ未接続）

座標はx=(z,r)。中心cと対称行列Qを用いる。
楕円はQ=R diag(a²,b²) R^T、双曲線はQ=R diag(a²,−b²) R^T。
有限接線n·x=hの接触条件は(h−n·c)²=n^T Q n。
これは非特異円錐曲線と双対曲線の関係[R30](REFERENCES.md)に対応する。
Qの双曲線表現は両枝を含むため、指定枝への制限は接点再構成後に必要。

以下は本実装用の消去計算である。qi=n^T Qi n、D=n·(c2−c1)、
w=h−n·c1と置けば、w²=q1、(w−D)²=q2なので、
2Dw=D²+q1−q2。従って候補法線は

    P(n) = (D² + q1 − q2)² − 4 D² q1 = 0

を満たす。これはnに関する同次四次式。
n=(1,t)とn=(t,1)、−1<=t<=1の2つの座標表示で有限の全法線方向を覆い、
重複方向は射影的に照合する。片方だけで垂直接線を失わない。

P=0は必要条件であり、消去式の根だけで候補を認証しない。
D=0を除算して失わずに別処理し、元の2つの接触条件へ戻る。
有限接点はx=c+Qn/(h−n·c)で再構成するが、分母ゼロを有限点へ丸めない。
その後に枝・有限弧・向き・接線残差を検査する。
同じ物理接点が弧の0/1両端に対応する場合も、切詰めの意味が違うため記録する。
二乗による余分な候補、重根、同一曲線を独立に扱うことを受入条件とする。
二進係数の根の完全列挙を元解析パラメータの厳密実数での存在保証とは呼ばない。
回転/係数化の丸めを最終の位置/接線残差で評価し、判定境界付近は未確認として残す。

## 実装済みの根数・区間分離基盤

polynomial_roots.isolate_real_rootsは有限閉区間の異なる実根を数え、
有理数の点または開区間へ分離する。昇べき係数を入力し、int/Fractionは厳密値、
floatはその二進有理数値として扱う。入力係数の測定/丸め不確かさの保証ではない。

有理数の多項式除算とgcdで重根を除いた後にSturm列を作る。
端点での符号変化差は右閉区間の根数なので、右端根を引いて開区間根数を得る。
左右端の根と二分点の根は別の厳密点として出す。
重根を含む端点への注意は[R31](REFERENCES.md)を確認した。
返す非点区間は開区間であり、境界に別の厳密根があっても混同しない。

PASSでは全根を分離し、各非点区間の幅がabsolute_width以下である。
UNVERIFIEDでは未処理区間と各区間の厳密根数を保持する。
max_boxesは区間処理数だけを制限し、有理数係数演算全体の時間上限ではない。
ゼロ多項式は無限根として拒否。定数非零は根0個。bool、非有限値、逆区間、
非正の幅/予算は拒否する。重複度は返さず、gcd_degreeと異なる根数を返す。

## 残る受入検査

根分離基盤は、既知有理根の積、複素因子、端点三重根、10^-40間隔の根、
係数の符号/尺度、±sqrt(2)、予算不足時の根数保存で検査した。
円錐曲線全体に対する接点再構成の受入は次節に記録する。有限弧の自動構築は未実装。

構築では離れた円の内外接線、接触/交差/包含/同一円、回転・移動・尺度変換、
楕円↔双曲線の枝、端点・逆向き弧、無限遠接点、根の近接・重複を検査する。
候補の全列挙とG1接続を分け、その後に閉輪郭の交差/微小隙間検査を適用する。
保存された構築入力・選択結果の往復、CLI/API/GUI操作、生成形状のFEM検査まで必要。

## 円錐曲線全体の候補・接点再構成 — 2026-09-08

conic_tangents.supporting_conic_tangentsは、入力弧が属する円錐曲線全体の共通接線を列挙する。
有限弧の区間や双曲線の指定枝はまだ制限しない。arc_filter_status=NOT_APPLIEDとscopeを必ず返す。
候補をLineSegmentやCaseとして公開せず、切詰め・接続・候補選択は次の段階に残す。

回転係数と半軸の二進値をFractionへ移し、Q・中心差・四次式を有理数で組み立てる。
各法線座標表示でSturm分離を行う。既定のnormal_widthは2^-44、
max_boxes=10000は各座標表示の上限であり、合計は最大2倍になる。
境界方向±1は座標表示0が所有し、近い候補同士を角度許容差で併合しない。
Dの零点が四次式の厳密根なら、その有理数値を復元してD=0の2定数を生成する。
中心が同じでもQが異なる楕円の共通接線をこの分岐で保持する。

根区間全体で接触二次式が負なら実接点なしとして除外する。
厳密根の接触分母ゼロは無限遠接点として区別する。
区間で分母の符号を分離できない、根予算不足、同一曲線等の零消去式、
浮動小数点で再構成できない場合は未確認理由を保持してUNVERIFIEDとする。
二進係数の根数・接点残差検査のPASSを有限有向弧への構築PASSとは呼ばない。

接点はx=c+Qn/wを有理数で計算してからfloat化する。
返したfloat座標の陰関数、返した法線と陰関数勾配の向き、返した直線上の位置を再検査する。
位置の表現はnormal·(x−origin)=offsetとし、originは第1曲線の中心、offsetはSI長。
既定residual_tolerance=1e-10は無次元の残差であり、絶対位置誤差の上界ではない。
接点間距離の非有限値も拒否する。返した座標で接点が一致する場合は
coincident_contacts_at_output_precisionを立て、厳密実数での零長証明と混同しない。

独立検査は離れた単位円の4接線と接点間距離sqrt(12),sqrt(12),4,4、
接触円の3接線、交差円の2接線、包含円の0接線、同一円の未確認、
回転/移動と1e-5/1/1e5尺度の楕円、異半軸・異回転/同中心楕円、
双曲線の陰関数、共通漸近線の無限遠除外、座標精度不足と予算不足。
最初のfixtureは一周弧とNumPy数値型を指定して既存の厳密入力で拒否されたため、
半周弧とPython数値型へ修正した。基になるconics入力制約の緩和はない。

次は有限弧の区間/枝/向きに候補を制限し、位置許容差とG1検査を伴う切詰めと接続を実装する。
その後に選択結果の保存・CLI/GUI・閉輪郭の全体検査を行う。自動フィレットも未完のまま保持する。

## 有限弧の数値判定と明示選択G1構築 — 2026-09-08

`arc_tangents.finite_arc_tangents`を追加した。支持円錐曲線の列挙結果を保持し、
接点を逆回転して楕円のatan2、双曲線のasinhから元弧のfractionへ戻す。
楕円は2π周期の代表を列挙し、双曲線は指定枝を確認する。fractionの既定端点ガードは
1e-8、再評価した接点の位置残差は既定1e-9 m、接線方向許容差は既定1e-8 rad。
全てstrict入力で、構築操作では位置・角度許容差を明示必須とする。

**これは浮動小数点のガード付き数値判定であり、接点パラメータの厳密区間包囲ではない。**
`arc_filter_status=NUMERICALLY_ASSESSED`とscopeを出力し、根の厳密分離と区別する。
端点近傍は見かけ上の端点一致もUNVERIFIEDとし、内側に丸めない。
パラメータ分解能がガードに足りない場合、再評価の位置・接線が許容差を超える場合も未確認。
一方の弧で明確に範囲外なら候補を除外できる。支持曲線段階の未確認はそのまま保持する。
元の根区間はsupporting_resultに残るが、fraction推定値の保証区間へ読み替えない。
厳密な接点区間伝播と弧端を含む認証は引き続き残件。

候補は第1接点→第2接点の向きについてFORWARD/OPPOSED/ZERO_LENGTHを記録する。
逆向きや零長を候補一覧から消さず、自動的に曲線を反転しない。
`connect_finite_arcs`は同じ入力の候補indexを明示して再列挙し、全判定PASSかつFORWARDのみ受理する。
第1弧は始点→接点、第2弧は接点→終点を残す。中心・半軸・回転・枝は変えない。
新しい弧の実端点からLineSegmentを作り、両接合部を既存check_curve_joinで再検査する。
元のプリミティブは変更せず、弧/線/弧と選択・診断を返す。indexは入力変更をまたぐ安定IDではない。
局所G1検査は閉輪郭の自己交差・軸接続・微小隙間検査やFEM受入を代替しない。

独立9検査: 上半円の上接線、両弧/片弧の反転、周期境界、回転/移動/尺度、
双曲線両枝と区間、弧端内外のガード、零長、未完探索とstrict設定、切詰めの
元曲線/端点保存と両G1接合。異なる双曲線枝に候補なしとした初回期待値は誤りだった。
`z²-r²=1`と`z²-(r-4)²=1`には接点`(sqrt(1.25),-.5)`と
`(-sqrt(1.25),4.5)`の斜め接線があるため、独立陰関数/接線式に基づいて期待値を訂正した。
実装の候補を削除して合わせていない。新API追加前のテストImportErrorも先に確認した。

次は構築要求/選択結果の保存、Case/CLI/GUIと閉輪郭検証への接続。
端点認証、支持直線と弧の接線、曲率指定フィレット、G03全要件照合は残る。

標準319件中317合格・2 skip、out/validation-g03-finite-arcs-20260908がPASS。
seed周波数差ゼロ、RF/エネルギー差最大8.882e-16。実行中docstring変更で失敗した別テストログも保持する。

## 構築文書・閉輪郭・CLI — 2026-09-08

`tangent_construction.construct_tangent_case`は版1の要求を受ける。
`case_template`はv3 curved_contourの**未完成の編集文書**であり、選択前はCaseとして有効とは限らない。
`pair_start`は配列内で連続する2つのPEC円錐曲線弧を指す0始まりindex。末尾から先頭への巡回は対象外。
`controls`にはposition_tolerance_m、angle_tolerance_rad、parameter_guard、normal_width、
max_boxes、residual_toleranceを全て明示する。primitiveのstrict読書きを既存輪郭と共通化した。
候補表示時も要求の未知キー・曲線・モデルを検査する。輪郭全体とmesh/solver/rf等の
計算設定の完全検査は選択後のCase.from_dictで行い、未完成templateをそのままsolveへ渡さない。

候補未選択ではCANDIDATESまたはUNVERIFIEDを返し、caseはnull。
候補indexを明示すると第1弧/接線/第2弧へ置換し、3辺へPECタグを渡す。
残る曲線と全計算設定を維持して既存Case.from_dictへ渡す。閉輪郭の接合・向き・軸接続・
領域範囲・交差/離隔と全入力が合格した場合だけCASE_VALIDATEDとcanonical caseを返す。
これは幾何・入力の検査であり、メッシュ生成・FEM収束の受入を表すステータスではない。

保存文書には元要求、要求SHA256、候補index、全列挙診断、接合残差、生成Case、
schema/software版と適用範囲を含める。有理根区間は分子/分母の10進文字列で保持する。
`read_construction`は要求から再構築し、保存JSON全体と一致を検査する。
単なるhash一致ではなく候補/Caseの対応を検査するが、署名や改ざん防止認証ではない。
再計算の厳密JSON一致は同じ実装/環境を対象とする。別環境で丸めが異なる場合や版変更時は
元要求から再生成する。単一JSONを排他新規作成し、途中ファイルは読込/再構築検査に通らない。
既存ファイルは上書きしない。失敗した新規ファイルを自動削除しない。

合成例（実測・旧デッキ由来ではない）:

```bash
superfish-ng construct-tangent examples/construction/capsule_request.json --out out/capsule-candidates.json
# 候補のcontacts_zr_m / connection_directionを確認して選択する。この例の0は上側の接線。
superfish-ng construct-tangent examples/construction/capsule_request.json --candidate-index 0 --out out/capsule-construction.json
superfish-ng export-constructed-case out/capsule-construction.json --out out/capsule-case.json
superfish-ng solve out/capsule-case.json --out out/capsule-solve
```

construct-tangentはUNVERIFIEDを診断付き保存して終了1、入力/構築/保存エラーは終了2。
export-constructed-caseは保存文書の再構築とCASE_VALIDATEDを確認してCase単独を出力する。
CLI/Pythonとも同じ構築・FEMを使う。GUIはまだ構築操作へ接続していない。

独立検査はカプセル断面積`dR+πR²/2`、回転体積`πR²d+4πR³/3`、
全寸法2倍の実FEM周波数1/2・両R/Q/G/TTF不変、元要求不変、保存再構築・変更検出、
未知指定/不正pair/全体接合失敗、CLI出力/上書き拒否、未確認候補からのCase出力拒否。
初回カプセル入力は長さ0.2 mの既存例のjoin_tolerance=1e-14 mを流用し、
長さ0.6 mで曲線境界boxの丸めpaddingに足りず拒否された。合成入力を1e-12 mへ明示設定した。
既存の1e-10 L上限制約・境界判定・数値受入閾値は変更していない。

次はGUIからの候補表示/選択/保存/ケース適用、厳密な接点区間/弧端認証、
直線と弧の接線・フィレット、G03全要件照合。今回の相似則は離散FEMの不変量であり、
このカプセルの実周波数/RFの収束や旧版照合を証明しない。

本段階の最終標準326件中324合格・2 skip、out/validation-g03-construction-cli-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー差最大8.882e-16。実装を固定して検証し、基準データの更新なし。

## GUI接続の操作契約 — 2026-09-08

形状編集内の「円錐曲線の共通接線を構築」で要求/保存結果を読み込み、
接点(z,r)・長さ・方向の候補表を表示する。要求のSI JSONを編集できる。
候補は初期未選択とし、順方向の候補を明示選択して閉輪郭を検査する。
未確認/逆向き/零長候補を計算用形状へ自動適用しない。
検査済みのCaseも「編集画面へ適用」を押すまで既存プロジェクトを置き換えない。
適用時には形状だけでなく要求に含む計算条件も渡すことをボタンに明記する。
保存・CLI・GUIは同じ構築/再構築/Case/FEMを使う。

要求の編集・候補変更・別ファイル読込で適用可能な古い結果を解除する。
非同期応答は要求の世代と本文を確認し、編集前の結果を遅れて適用可能にしない。
保存結果はサーバーで要求から再構築してから表示する。改変検出や入力失敗時は適用不可。
このファイル形式は構築文書で、通常の「入力を開く」には完成したCase/Projectを渡す。
GUIの保存はブラウザーのダウンロードであり、指定ディスク位置への排他保存はCLIの契約。

初回の実ブラウザー検査では、JavaScriptのJSON再生成が`1.0`等の表記を変え、
保存後の厳密再構築照合に失敗した。数値閾値や照合を緩めず、サーバー生成の保存文字列を
応答のserializedへ含め、ブラウザーで再シリアライズせずダウンロードするよう修正した。
元の初回FAILはout/gui-tangent-browser-20260908/report.jsonに保持する。

GUI最終受入はout/gui-tangent-browser-final-20260908/report.json、7操作PASS。
外部要求0・実行中ソース変更なし。画面はtangent-construction.png。人による使いやすさ評価は未実施。

GUI最終版の標準328件中326合格・2 skip、out/validation-g03-tangent-gui-final-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー差最大8.882e-16、基準更新なし。検証用サーバーは停止済み。

## 支持曲線の接点座標区間 — 2026-09-08

`contact_enclosures.supporting_contact_enclosures`は既存の法線根分離結果から
接点の閉有理数boxを返す。接点再構成に使った中心・Qの二進係数を厳密値として扱う。
これは別APIであり、既存の構築文書・GUI・有限弧のガード付き判定は変更しない。
古い保存構築文書の再構築形式を途中で変えない。

根区間Tに対してD(T)、q1(T)、q2(T)を有理数Horner区間で囲み、
`w1=(D²+q1-q2)/(2D)`、`w2=w1-D`、`x_i=c_i+Qi n/wi`を区間演算する。
分母区間が0を含む場合は未確認とし、中心点の符号で除算を正当化しない。
厳密有理根が復元されている場合はその一点を使用し、それ以外の開根区間は閉区間へ拡大する。
D=0ではq1=q2を満たす根に対し±sqrt(q1)の両接触定数を保持する。
平方根の上下界は二乗した有理数比較で検査した既存sqrt境界を用いる。
したがって無理数接点をfloat接点そのもので囲んだことにはしない。

返却量:

- contact_boxes_zr_m: 各接点のz/r閉区間（Fraction、SI m）。
- coordinate_widths_m: 各座標幅。max_contact_width_m（既定1e-9 m）以下かをwidth_statusで判定。
- returned_point_error_bounds_m: 支持曲線APIが返したfloat接点から、box内の厳密接点までのEuclid距離上界。
- local_contact_boxes: 中心を引き、二進回転・半軸行列を厳密に逆変換した無次元区間。
- specified_branch_status: 双曲線の指定枝とのMATCHES/OTHER/UNVERIFIED。楕円はNOT_APPLICABLE。

二進cos/sinは有理数としてc²+s²=1とは限らないため、局所変換は転置だけでなく
逆行列の分母c²+s²を使う。局所双曲線xの符号から指定枝を検査し、asinhの近似値へ依存しない。
OTHERの候補も支持曲線全体の一覧へ残す。指定枝・有限有向弧への構築選択とは別の結果である。

全体PASSは支持曲線探索の完了、全候補の分母分離・区間生成・指定座標幅の達成を表す。
幅未達でも生成済みboxを保持し、理由と候補indexを未確認一覧へ出す。
返却float接点の誤差上界はbox幅とは別に報告する。元の実数回転・測定寸法の不確かさや
有限弧端の所属はこのPASSの対象外。未分離根や一致曲線による無限/退化候補も成功に変換しない。

独立8検査では、離れた単位円の内接線接点(1/2,±sqrt(3/4))と(7/2,∓sqrt(3/4))、
外接線、同中心異半軸楕円の±4/sqrt(5),±1/sqrt(5)、双曲線の±sqrt(5/4)を
丸めた参照sqrtではなく有理数の二乗比較で包囲確認する。
2^-20/1/2^20尺度・平行移動・直角回転、根幅によるbox縮小、返却接点誤差上界、
指定枝反転、幅未達・予算不足・同一曲線・不正幅も検査した。API追加前のImportErrorを先行確認。

次は局所接点boxと有限弧端の比較、端点一致/内外の判定を既存構築の版付き契約へ接続する。
双曲線の有限区間、楕円の有向周期区間、区間に基づく切詰めの誤差管理は未完。
直線と弧の接線・フィレット・G03全要件照合も継続する。

追加の厳密座標検査では回転0.37 radの二進係数で(3/5,4/5)を順変換し、
局所boxの逆変換が両座標とも一点の3/5,4/5に厳密一致することを確認。
out/validation-g03-contact-enclosures-20260908/local_inverse_invariant.jsonに記録した。

接点区間APIの最終標準336件中334合格・2 skip、out/validation-g03-contact-enclosures-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー差最大8.882e-16。基準更新なし。GUI/Wineは今回未実行。

## 有限弧の所属とfraction区間 — 2026-09-08

`certified_arcs.certified_finite_arc_tangents`は支持曲線の接点boxから、有限弧の
INTERIOR/EXTERIOR/START/END/UNVERIFIEDを判定し、受理候補のfractionも閉有理数区間で返す。
対象は保存された二進パラメータを厳密値とする曲線。楕円の終角はstart+sweepの有理数和、
回転・半軸は支持円錐曲線の二進係数契約を使う。元の実数入力の丸め前の形状まで認証しない。
既存の版1構築・保存・CLI/GUIは数値ガード判定のまま維持し、このAPIの結果へ置換しない。

端点のsin/cos/sinhは`transcendental_interval`で有理数Taylor和と剰余から囲む。
sin/cosは導関数絶対値<=1のLagrange剰余を使い、次の非零項の絶対値を上下へ加減する。
sinhは|x|で全項正の部分和を下界とし、次項以降の比の上界q<1が得られた場合に
次項/(1-q)を残尾上界とする。負入力は奇偶性を使って区間を反転する。
libmの近似sin/cos/asinhや固定の経験的epsilonを端点証明には使わない。
既定endpoint_width=2^-100、max_series_terms=96。幅未達/残尾未評価で予算を使い切ると未確認。
予算は項数であって演算時間上限ではない。

双曲線はまず局所x区間で指定枝を検査し、局所yとsinh(start/end)を単調比較する。
楕円は有向弧の像を長さ2 rad以下（π未満）のCCW sectorへ分割する。
各sectorの両端方向との外積の区間符号を調べ、全sectorの和集合として内外を判断する。
逆向きやatanの±π境界を特例の角度丸めへ変換しない。
内部sectorの境界上でも、元の両弧端との分離と非負の両外積で内部所属を証明できる。
START/ENDは接点と端点boxの両座標が厳密一点として等しい場合だけ認める。
端点boxが重なるだけでは一致とはしない。有限弧に属さないことも証明が必要で、未確認を除外へ変換しない。

fractionは元弧の始点から候補までの単調な進行率。元弧のprefixへの所属を二分して
区間を狭めるため、float atan/asinhの逆評価は不要。
既定fraction_width=2^-32、max_fraction_steps=64。START/ENDは厳密な0/1、
二分点との厳密一致はその有理数一点を返す。比較未分離/級数予算不足/二分予算不足は
最後の有効な閉区間を保持してUNVERIFIED。内部所属自体が未確認の場合はfraction区間なし。
全体PASSには支持曲線の探索/接点box幅・有限弧所属・fraction幅の全達成が必要。
所属が確定してもfraction未達なら候補と区間を残し、全体は未確認にする。

独立8検査は、級数の厳密0・奇偶性、Decimal.expを用いるsinhの別計算、
角度0の既知点と±10^-20 radの内外/端点、長い有向弧・反転・周期境界・内部sector境界、
双曲線の有限区間/枝/端点、支持曲線候補からの接続、根/級数予算不足と端点をまたぐbox、
既知fractionの1/2・1/3・2/3と10^-20近傍、fraction予算不足でも真値を保持すること。
API追加前のImportErrorを先に確認した。式・実装は既存接点区間と初等解析から独立導出し、外部コード参照なし。

次は区間から選んだ浮動小数点の切詰め位置を、接点boxへの距離上界と明示した位置許容差で検査し、
版付き構築要求/保存/CLI/GUIへ接続する。空になる弧・零長接続・端点を再利用する場合の操作契約も必要。
直線と弧の接線/フィレット、G03全要件照合は継続する。

既存合成カプセルの2弧にも実行し、候補1件・両接点INTERIOR・fraction幅2^-32でPASS。
out/validation-g03-certified-arcs-20260908/capsule_membership.jsonへ有理数区間を保存した。
この例でもfractionを厳密な1/2へ丸めない。証拠の区間は[1/2,2147483649/4294967296]。
独立テストは `.venv/bin/python -m unittest discover -s tests -p test_certified_arcs.py -v` で再現する。

有限弧所属/fraction APIの標準344件中342合格・2 skip、out/validation-g03-certified-arcs-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー差最大8.882e-16。基準更新なし。GUI/Wineは今回未実行。

## 版2の区間付き切詰めと製品接続 — 2026-09-08

構築要求/保存文書のschema_version=2を追加した。Case自体は既存のv3。
版1は従来のガード付き数値判定と同じ再構築結果を維持し、保存済みGUI文書の実再読込も確認した。
版2は`certified_construction`を使い、所属/fraction/接点区間を構築へ接続する。
CLIのconstruct-tangent/export-constructed-case、GUIの構築欄は要求版を保持して同じ経路を使う。

版2のcontrolsは全て明示必須:
position_tolerance_m、angle_tolerance_rad、normal_width、max_boxes、residual_tolerance、
max_contact_width_m、endpoint_width、max_series_terms、fraction_width、max_fraction_steps。
版1のparameter_guardは版2では未知キーとして拒否する。閾値を自動で緩めない。

切詰め位置は確定したfraction閉区間の中点をfloatへ変換し、変換後も有理数比較で区間内かを検査する。
内部接点で空/表現不能な弧が生じる場合は拒否する。第1弧のENDと第2弧のSTARTは元プリミティブを再利用。
第1弧START/第2弧ENDは保持弧が空になるためEMPTY_ARCとし、元の弧を自動削除しない。
零長・逆向き・位置/角度の未達も候補と理由を残し、選択不可にする。

生成した弧の数学的端点を、その新しい二進パラメータからsin/cos/sinhの区間で再評価する。
coshは正のsqrt(1+sinh²)から囲む。中心・半軸・二進回転を有理数演算し、実装が返すfloat座標もboxへ含める。
この端点boxと厳密接点boxの各座標差の最大二乗和からEuclid誤差上界を得て、明示位置許容差を検査する。
従って表示floatだけが接点へ近いことを数学的端点の誤差保証へ読み替えない。
保持する外側終点についても元/生成弧の端点boxから誤差上界を検査する。
実線分は生成弧のfloat端点から作り、既存check_curve_joinで両接合の位置とG1角度を数値検査する。
**接点誤差/所属/fractionは区間検査、G1角度は浮動小数点検査**である。厳密な角度区間保証とは呼ばない。

探索statusは証拠の探索完了性。候補ごとの切詰め未達はUNVERIFIEDと理由付きで残す。
別候補の切詰め未達だけで、所属探索が完了した選択可能候補を消さない。
最終の明示選択には探索PASSと選択候補FORWARDを要求し、続いて既存Caseの閉輪郭/全設定検査を適用する。
保存には証拠、fraction、生成曲線、接点/外端誤差上界と数値G1結果を保持し、再読込で全体を再構築照合する。
GUIは版2の最大接点誤差上界と角度が数値検査であることを表示する。

例はexamples/construction/capsule_certified_request.json。許容差1e-12 mに対し、
生成接点の誤差上界は約8.94e-15/8.92e-15 m。測定形状ではなく合成カプセルである。

```bash
superfish-ng construct-tangent examples/construction/capsule_certified_request.json --candidate-index 0 --out out/capsule-v2-construction.json
superfish-ng export-constructed-case out/capsule-v2-construction.json --out out/capsule-v2-case.json
superfish-ng solve out/capsule-v2-case.json --out out/capsule-v2-solve
```

追加5テスト: 区間内の選択位置と位置上界、厳密端点再利用/空弧拒否、版2保存/版1継続、
位置許容差未達・未知設定・不正選択、GUI応答/再構築、解析面積/体積と実FEM相似則(f半減・両RQ/G/TTF不変)。
版2の切詰めも微小な位置誤差を持ち、メッシュ細分・RF精度収束を代替しない。
次は直線と弧の接線・フィレットとG03全要件照合。G03全体/全互換の完成はまだ宣言しない。

版1/2の合成カプセル比較はout/validation-g03-certified-construction-20260908/capsule_v1_v2_comparison.json。
双方617節点/1152三角形だが座標・接続は異なり、周波数相対差1.41259e-8、
R/Q相対差0.00312004、G相対差6.77706e-8、TTF相対差0.00154291がある。
接点位置の微小差に加え、生成メッシュが変わった計算同士の比較であり、純粋な幾何誤差と分離していない。
この差を隠す補正や閾値変更は行わず、カプセルのRF精度収束は未検証として保持する。

版2統合の標準349件中347合格・2 skip、out/validation-g03-certified-construction-20260908 PASS。
Chrome8操作PASS、seed周波数差ゼロ、RF/エネルギー差最大8.882e-16、基準更新なし。検証用GUIは停止済み。

## 版3の固定支持直線と有限弧 — 2026-09-08

`line_arc_tangent_candidates` / `connect_line_arc` を追加した。指定した線分の支持直線を
固定し、その直線が円/楕円/双曲線の支持曲線に接する場合だけ有限接点を構築する。
二進入力から有理数で中心c、行列Q、法線n、w=n·(line_start−c)を作り、
接線条件w²=nQnを厳密に判定する。不等ならNOT_TANGENT、両辺ゼロなら
有限接点を持たないAT_INFINITYとして区別する。有限接点はc+Qn/wで厳密な有理数。
近傍の非接線を許容差で接線へ補正しない。回転後の入力丸めでも条件が崩れれば拒否する。

接点を元の線分start+t(end−start)へ射影し、有理数tを記録する。
`allow_extension=false`ではt∉[0,1]を除外する。延長を許可しても有向線分を反転しない。
直線→弧では線分始点と弧終点、弧→直線では弧始点と線分終点を保持する。
保持線分が空ならEMPTY_LINE、弧が空ならEMPTY_ARC、逆向きならOPPOSED。
元弧の枝/有向有限区間への所属とfractionは既存の有理数区間APIで確認する。
未分離・予算不足・表現不能・位置誤差未達はUNVERIFIEDと理由を保持し、Case化しない。

新線分の接点側は厳密接点のfloat表現とし、保持端点は元線分から継承する。
切詰め弧の数学的/出力端点と、線分のfloat接点それぞれの厳密接点からの距離上界、
弧の保持外端の誤差上界を位置許容差と照合する。float化した新線分の支持直線が
厳密に元の直線と一致する保証ではない。接合G1角度は数値検査である。

構築schema_version=3は隣接したPEC線分1本とPEC弧1本を任意の順で受理する。
`pair_start`と配列順が接続端を指定する。曲線2本を曲線2本で置換し、完成Case全体を検査する。
要求/保存/CLI/GUIは版1/2と同じ入口で、保存文書は再構築による全体照合を維持する。
controlsは全て明示必須:
position_tolerance_m、angle_tolerance_rad、allow_extension、endpoint_width、
max_series_terms、fraction_width、max_fraction_steps。版2の根探索用controls等は拒否する。
GUIの位置表は保持線分端点と接点を区別し、長さは保持線分の長さである。

```bash
superfish-ng construct-tangent examples/construction/capsule_line_arc_request.json --candidate-index 0 --out out/line-arc-construction.json
superfish-ng export-constructed-case out/line-arc-construction.json --out out/line-arc-case.json
superfish-ng solve out/line-arc-case.json --out out/line-arc-solve
```

独立検査は既知の円/双曲線接点、有限区間/枝、延長許可と方向、非接線/漸近線の区別、
空区間拒否、級数予算、厳密controls、保存往復とGUI共通経路。
合成カプセルの解析面積/回転体体積と、実FEMの2倍相似則(f半減、両RQ/G/TTF不変)も確認した。
これらは接線構築の幾何不変量とFEMの尺度不変量であり、任意形状のRF収束保証ではない。
新規外部資料/コード/依存なし。既存の二次形式と初等幾何から独立導出した。
任意半径フィレット・旧曲線入力・G03全要件照合は引き続き未完。

版3統合の標準356件中354合格・2 skip、out/validation-g03-line-arc-20260908 PASS。
seed周波数差ゼロ、RF/エネルギー差最大8.882e-16、基準変更なし。Chrome8操作もPASS。
同所capsule_v2_v3_comparison.jsonでは版2/3カプセルのf差2.32491e-8、
両RQ差0.626214%、G差8.12673e-8、TTF差0.310662%。双方617節点/1152三角形。
微小な構築差を含む再メッシュ同士の比較であり、純粋な幾何誤差とは分離していない。
位置保証をRF保証にはせず、カプセルのRF精度収束は未検証として保持する。

## 版4の指定半径・線分フィレット — 2026-09-08

`line_fillet_candidates` / `connect_line_fillet` は2本の有向線分の間へ、指定半径Rの
小円弧を構築する。支持直線の交点Vは二進入力の有理数で解く。平行・同一直線・
反転はPARALLEL_SUPPORTSとして区別し、角度を微小量ずらして構築しない。
単位接線u,v、符号付き転向角θ=atan2(cross(u,v),dot(u,v))から
切詰め距離d=R tan(|θ|/2)を求め、接点をV−du、V+dvとする。
計算にはR|cross|/(1+dot)、反転に近い場合には同値なR(1−dot)/|cross|を使う。
中心は第1接点から、転向側の単位法線方向へRだけ移した位置である。
これは支持直線が交差する場合の、元の向きを保持する小円弧の構築。
大円弧や方向反転による別枝を自動選択しない。

R、位置許容差、G1角度許容差は正の有限値を明示する。延長許可もboolで明示する。
`allow_extension=false`では接点が両有限線分内に必要で、未許可の延長は
OUTSIDE_SEGMENT。延長を許可しても第1線分始点/第2線分終点は保持し、
空/逆向きになる保持線分はEMPTY_LINEとして接続しない。半径を自動縮小しない。
生成接点の支持直線距離、生成線分/円弧の両G1接続、保持線分と元線分の方向を
数値検査する。表現不能・許容差未達はUNVERIFIEDと理由を保持する。
接点/有限区間/G1の検査は浮動小数点を含み、版2/3の区間認証とは異なる。
出力の円プリミティブは指定Rを両半軸として保持し、曲率は1/Rである。
曲率ゼロの線分とのG2接続を意味しない。

構築schema_version=4では隣接PEC線分2本を受け、明示候補0の選択により
線分・円弧・線分へ置換する。controlsはradius_m、allow_extension、
position_tolerance_m、angle_tolerance_radだけを全て明示必須とする。
他版の探索controlsや円錐曲線のフィレット指定は受理しない。
保存文書は要求/生成幾何/診断/完成Caseを同じ入口で再構築照合し、
Caseの閉輪郭・自己交差・軸接続・設定の全体検査を維持する。
GUIは指定半径、円弧長、数値検査であることを表示する。
候補表の2位置は接点であり、長さ欄はこの版では弦長ではなく円弧長を示す。

```bash
superfish-ng construct-tangent examples/construction/corner_fillet_request.json --candidate-index 0 --out out/fillet-construction.json
superfish-ng export-constructed-case out/fillet-construction.json --out out/fillet-case.json
superfish-ng solve out/fillet-case.json --out out/fillet-solve
```

合成例は長さ0.2 m、半径0.1 mの長方形断面の上部右角をR=0.02 mで丸める。
二次曲線幾何/二次場FEMを明示する。測定空洞や旧版の例題とは呼ばない。
独立検査は直角の既知接点/中心/曲率、除去面積R²(1−π/4)、回転/鏡映/尺度/逆順、
浅い/鈍い転向、過大半径・有限範囲・延長・空線分・平行/反転・厳密controls、
保存改変拒否とGUI、完成Caseの面積と曲線FEM相似則(f半減、両RQ/G/TTF不変)。
初回はAPI未実装のImportErrorを確認してから実装した。
これは線分間フィレットの受入であり、円/楕円/双曲線弧を含むフィレット、
物理ピークの収束、旧曲線入力、G03全要件照合は引き続き残件である。

版4統合の標準363件中361合格・2 skip、out/validation-g03-line-fillet-20260908 PASS。
seed周波数差0、RF/エネルギー差最大8.882e-16、基準変更なし。
Chrome8操作と版1〜4の実保存ファイル再読込PASS。検証中の実装変更なし。
合成例の周波数1152045668.073337 Hz、R/Q(acc)=57.172456 ohmをCLI/GUIで確認。
この形状のRF精度・物理ピーク収束は未検証として保持する。

## 円錐曲線フィレットの中心軌跡区間 — 2026-09-08

指定半径のフィレット中心は、元曲線xの単位接線Tと左法線N=(-T_r,T_z)を使い
C=x+dN上にある。dの符号が左右を指定する。符号付き曲率κに対し
C'=(1−dκ)x'。1−dκ=0では通常の正則な交点探索の仮定が崩れる。
円では半径分の内側オフセットが中心一点に潰れる。

`normal_offset_bounds` は有限fraction閉区間上のC、fraction導関数C'、κ、1−dκを
有理数区間で返す。sin/cosは中点の厳密級数区間へLipschitz半径を加え、[-1,1]と交差。
sinhは単調な両端の級数区間、coshはsqrt(1+sinh²)から囲む。
平方根は既存の有理数二乗比較による外向きfloat境界を有理数へ戻す。
楕円速度はb²+(a²−b²)sin²、双曲線速度はb²+(a²+b²)sinh²を使い、
常に正の速度下限を保持する。円では定曲率を使って相関を保ち、中心への潰れを厳密に扱う。

回転係数c,sは既存の二進係数で、c²+s²を勝手に1と置かない。
速度二乗・曲率分子へこの行列式を含め、指定された二進線形写像の曲線を囲む。
κの符号は楕円でsign(sweep)、双曲線で−branch*sign(parameter_span)。
FORWARD/REVERSEDは1−dκの正/負を全区間で証明したもの。
COLLAPSEDは円が中心へ潰れる特別な場合であり、一般弧で区間が0を含む場合は
UNVERIFIEDとする。区間が0を含むだけで尖点の存在や根数を証明しない。
この境界は数学的中心軌跡を囲み、別途float評価した出力プリミティブの丸めまでは含めない。

`partition_normal_offset` は元の全有限fraction [0,1]を二分し、正則・潰れ・未確認を
欠落なく保持する。指定fraction幅まで狭めても未分離ならUNVERIFIED。
区間処理数や級数の予算が尽きても、未処理区間を捨てず理由付きで保存する。
PASSは全区間の正則性、SINGULARは潰れを含み他に未確認がない場合。
どちらもフィレット候補の交点探索・存在/個数・切詰めの完成とは呼ばない。

独立6検査は円の半径変化/中心への潰れ、楕円/両枝双曲線の頂点曲率、
回転形状の点/数値微分の包含、楕円の既知折返し位置を未確認区間に保持すること、
全区間被覆と予算不足、方向反転/尺度不変・厳密指定、Decimalによる二進回転頂点照合。
新規外部資料/コード/依存はなく、初等微分幾何と既存の有理数区間核から独立導出した。
次の交点探索・製品接続を含む残件は[G03照合表](G03_ACCEPTANCE.md)を参照。

標準369件中367合格・2 skip、out/validation-g03-normal-offsets-20260908 PASS。
同所offset_partitions.jsonは円SINGULAR、楕円の既知折返し位置を含む2未確認区間、
双曲線PASSの各入力/結果を保持する。seed周波数差0、RF差最大8.882e-16。
GUI/Wineの今回実行はなく、未接続の弧フィレットを操作受入済みとはしない。

## 中心軌跡の有限領域交点探索 — 2026-09-08

`offset_intersections.intersect_normal_offsets` は2本の円/楕円/双曲線弧と
左右それぞれの符号付き距離を受け、明示fraction長方形内の中心軌跡の交点を探す。
既定の対象は[0,1]×[0,1]。通常フィレットには半径と左右の組合せを別途指定する必要があり、
このAPI単体がその組合せ選択や元弧の切詰めを行うわけではない。

F(s,t)=C1(s)−C2(t)、J=[C1',−C2']を既存有理数区間核で囲む。
長方形Xの中点mと非特異な点行列Aを使い、
K=m−AF(m)+(I−AJ(X))(X−m)を計算する。
座標包絡が交わらない場合、またはKとXが交わらない場合だけ根なしと除外する。
K∩Xへ狭めるときも、元のXに存在し得る根は全て残る。
KがXの内側へ厳密に入り、さらに本実装が要求する∞ノルム収縮上界<1を満たせば、
存在する一意の根として認証する。数学的な包含条件は[R32](REFERENCES.md)の
Theorem 13.3を確認した。実装は既存のFraction区間演算から独立に記述した。

Aは区間Jacobian中点の逆行列候補をfloat化し、その二進値を有理数へ戻して使う。
Aの近似精度を証拠にせず、非特異性・包含・収縮を有理数で検査する。
Kの座標はprecision_bits（既定96）の二進格子へ外向きに丸め、分母の増大を制御する。
この格子で要求幅まで狭められなければ未確認であり、要求を自動で緩めない。

認証後も根を保持してparameter_boxをfraction_width以下へ狭める。
戻り値は根のfraction箱、中心座標箱、存在/一意性を証明したdomain_box・K箱・
中点・前処理行列・収縮上界を含む。正規化残差や近似接点を根の証拠にしない。
root配列はfraction箱で並べる。未確認領域が一つでも残れば全体はUNVERIFIEDで、
認証済みの他の根と未確認領域を両方保持する。PASSでは未処理領域がなく、全根の幅が達成される。

接触・同一軌跡・潰れ・弧端/分割境界の交点は、通常の内部包含で解決できない場合がある。
それらを根なしや単一根へ読み替えず、予算不足・格子精度不足・級数未達と同様に理由を保存する。
閉じた子領域の共有境界にある根を両方で内部認証して重複計上しない。
max_boxesは処理長方形数を制限し、有理数演算全体の時間上限ではない。
この交点認証は数学的な二進パラメータモデルのもので、生成float弧の誤差やFEM精度とは別。

独立7テストは円の2交点、楕円の陰関数から得る4交点、非零距離の楕円/双曲線頂点交点、
有限弧制限・離隔、弧端/接触/同一/潰れの未確認保持、2倍尺度と順序交換、
区間数/格子精度/級数予算、不正指定。既知交点にはDecimal100桁の別計算も使用する。
未実装ImportErrorを先に確認し、接触テストの有限弧が接点を含まなかった初期fixtureは
接点を含む弧へ訂正した。正しい「有限弧に交点なし」を失敗へ変える修正ではない。

次は根箱から有限接点を復元し、半径と左右の組合せ・有向フィレット・空弧/線分を検査する。
線分中心軌跡との接続、弧端・退化の追加分類、保存/Case/CLI/GUI、独立形状/FEM検証は残件。

標準376件中374合格・2 skip、out/validation-g03-offset-intersections-20260908 PASS。
同所intersection_examples.jsonには円2交点・楕円4交点・楕円/双曲線1交点のPASSと、
接触例の未確認領域を保持。seed周波数差0、RF差最大8.882e-16、基準変更なし。
GUI/Wineは今回未実行。数学的交点の認証を完成したフィレット操作の受入とはしない。

## 版5の有限弧フィレット構築・製品接続 — 2026-09-08

`conic_fillet_candidates` / `connect_conic_fillet` は認証済みの中心軌跡交点から
有限弧の接点を復元し、元弧・指定半径円弧・元弧へ切り詰める。
元弧と同じ向きのG1接続には、両接点の中心が同じ符号の左法線距離に必要である。
`turn_direction=1`は(z,r)平面で反時計回り、−1は時計回りで、両軌跡にd=turn_direction*radius_mを使う。
向きを黙って反転せず、左右の組合せを暗黙に選ばない。
`max_sweep_rad`は正で2π以下。指定方向では大回りとなる候補もあり、上限超過はSWEEP_LIMIT。
半径や方向を変えてその候補を合格にしない。

根箱の中点をfloatへ変換し、第1弧の始点側と第2弧の終点側を保持する。
中心も認証座標箱の中点をfloatへ変換する。狭い箱の中にfloatが存在しない場合もあるため、
中点の二進表現が元の根箱内かを記録するが、その一致を正確な接点の根拠にしない。
接点箱は元弧の根fraction区間を距離0の法線オフセット区間で評価して得る。
生成した両元弧端点と円弧端点は、新しい二進パラメータから数学的端点を再評価し、
実装が出すfloat座標も囲む。その箱と元の接点箱の距離上界を明示位置許容差と照合する。
中心の丸め誤差と、保持する両外端の誤差上界も検査する。
空/表現不能な弧・接点/半径方向の潰れ・未達は理由付きで選択不可。

float丸めで接合点が進行方向にわずかに重なる場合、閉輪郭の隣接検査は拒否する。
この検査は変更せず、必要な場合だけ円弧の両端を内側へ取り、前向きの微小な隙間を残す。
内側へ取る角度はmin(position_tolerance_m/(16R),angle_tolerance_rad/16,|sweep|/16)。
中心とRは保持し、内側へ取った角度と元の要求角を保存する。
調整後も位置誤差上界・G1角度・進行方向の重なりを再検査し、失敗時はUNVERIFIED。
これは明示許容差内のfloat構築であり、生成した弧同士の数学的な厳密接触/G1角度保証ではない。
**接点位置は区間上界、G1角度と最大円弧角は生成プリミティブの数値検査**として区別する。

構築要求/保存schema_version=5は隣接PEC円/楕円/双曲線弧2本を受ける。
controlsは全て明示必須: radius_m、turn_direction、max_sweep_rad、position_tolerance_m、
angle_tolerance_rad、fraction_width、max_boxes、precision_bits、endpoint_width、max_series_terms。
線分、延長指定、他版だけのcontrolsは拒否する。元の全有限弧に対する探索PASSと
選択候補FORWARDを要求し、完成Case全体の閉輪郭・自己交差・軸接続・全設定も検査する。
他候補の数値構築未達は残すが、探索が完了した選択可能候補を隠さない。

同じconstruct-tangent / export-constructed-caseとGUI構築欄で保存・再構築・適用できる。
GUIには半径、回転方向、円弧長、元弧/フィレットを含む最大接点誤差上界を表示する。
未復元の接点・長さは0などの架空値で埋めない。保存はサーバーの直列化文字列を維持し、
再読込では要求から再構築して全体照合する。版1〜4の従来経路は保持する。

```bash
superfish-ng construct-tangent examples/construction/two_lobe_fillet_request.json --candidate-index 0 --out out/conic-fillet-construction.json
superfish-ng export-constructed-case out/conic-fillet-construction.json --out out/conic-fillet-case.json
superfish-ng solve out/conic-fillet-case.json --out out/conic-fillet-solve
```

合成2山形状は半径0.1 mの2円弧を半径0.02 mの時計回り円弧でつなぎ、
軸長0.4 m、二次曲線幾何/二次場を使う。測定空洞や旧版の実測例とは呼ばない。
追加6テストは既知円の接点/半径/小回り・大回り、楕円/双曲線の四分円、
方向反転、厳密指定/未達、保存/GUIと独立解析面積・体積、実曲線FEMの相似則。
相似則は周波数半減・両RQ/G/TTF不変であり、この形状のRF/ピーク精度収束は未検証。

初回の閉輪郭隣接失敗はout/g03-conic-fillet-overlap-before-20260908.jsonに保持する。
約3e-17 mのfloat接合差が進行方向へ重なった例であり、隣接/許容差検査を緩めず
上記の位置上界付き内側処理で解消した。接点復元前には未実装ImportErrorも確認した。
線分と円錐曲線弧のフィレット、弧端/退化の追加分類、旧入力、物理ピーク収束は残件。

版5統合の標準382件中380合格・2 skip、out/validation-g03-conic-fillet-20260908 PASS。
seed周波数差0、RF/エネルギー差最大8.882e-16、基準変更なし。
Chrome8操作と版1〜5の実保存ファイル再読込もPASS。検証用GUIは停止済み。
合成例の周波数1310579815.6725943 Hz、R/Q(acc)=85.595228 ohmを実CLIで確認。
フィレット接点誤差上界は最大約6.36e-14 mで、要求1e-12 m以内。
この形状のRF精度/物理ピーク収束は引き続き未検証として保持する。


## 版6の直線・有限弧フィレット — 2026-09-08

版6は隣接PECプリミティブを線分1本と円/楕円/双曲線の有限弧1本に制限する。
版5の全controlsに `allow_extension`（明示bool）を加え、同じフィレット構築核を使う。
2直線には版4、2弧には版5を使う。旧版の要求/保存結果は従来の経路で再構築照合する。

線分は二進端点を厳密な有理数として、x(t)=P+tD、D=Q−Pと表す。
左法線N=(−D_r,D_z)/|D|を平方根の外向き区間で囲み、中心軌跡x(t)+dN、
導関数D、符号付き曲率0、速度係数1を返す。距離は両曲線でd=turn_direction*radius_m。
`normal_offset_bounds` / `intersect_normal_offsets` の線分パラメータは有限の実数区間を
許し、円錐曲線弧は常に[0,1]に制限する。特異性分割APIは従来の有限弧用のままである。

延長なしでは線分も[0,1]を探索する。延長ありでは弧の全中心軌跡を包絡し、
`t=D・(C_arc−C_line(0))/|D|²` の区間から必要な支持直線パラメータを囲む。
両端へ1パラメータ単位を足して探索領域の内部に交点を含める。無限範囲の走査や
任意の遠方打切りではなく、元の有限弧から導いた有限領域である。
包絡精度が作れない場合も入力/精度エラーを返し、空候補の成功とは扱わない。

直線→弧は線分始点、弧→直線は線分終点を保持する。延長しても空/逆向きの保持部分は拒否。
線分接点は有理数のアフィン式からfloatへ丸め、元の認証接点箱との距離上界を検査する。
保持外端・中心・生成円弧の上界、G1数値検査、必要時の位置上界付き端点内側処理は版5と同じ。
元線分と保持線分の方向差も数値検査し、line_fraction、line_extended、line_first、
allow_extension、retained_line_direction_error_radを候補に保存する。
根探索の完了と候補の構築可否は別であり、弧端・接触/重根・潰れ等の未確認領域は残す。

```bash
superfish-ng construct-tangent examples/construction/line_conic_fillet_request.json --candidate-index 0 --out out/line-conic-fillet-construction.json
superfish-ng export-constructed-case out/line-conic-fillet-construction.json --out out/line-conic-fillet-case.json
superfish-ng solve out/line-conic-fillet-case.json --out out/line-conic-fillet-solve
```

合成例は半径0.1 mの円弧とz=0.15 mの直線壁を半径0.02 mの反時計回り円弧で接続する。
二次曲線幾何/二次場を指定する。追加6テストで3-4-5線分の法線区間、既知円と双曲線の接点、
延長・順序反転・逆向き拒否、保存/GUI・解析面積/体積、FEM相似則を確認する。
周波数半減と両RQ/G/TTF不変は、この合成形状のRF精度/物理ピーク収束を保証しない。
最新の標準数値回帰・実ブラウザー・旧版再読込の証拠は[引継ぎ](CODEX_HANDOFF.md)を参照。
既存の区間演算/交点核と初等線形射影から独立実装し、新しい外部資料・依存は追加していない。


## 弧端・退化の診断 — 2026-09-08

[法線オフセット診断](OFFSET_DEGENERACIES.md)に厳密な特殊ケース分類を追加した。
`diagnose-offsets` は独立した診断要求/出力であり、構築要求版1〜6の保存や候補選択を変えない。
共有パラメータの証拠、円の接触/潰れ、直線の接触/重複を確認し、有限弧所属までの完全分類と
支持曲線または共有部分だけの証拠を分ける。一般の弧端/重解・構築/GUI接続は継続する。

構築診断接続（2026-09-08）: 版5/6の実探索区間から特殊ケース診断を作り、
構築込みの別文書としてCLI/GUI保存・再構築照合へ接続した。元構築版1〜6の形式は維持する。
診断のCERTIFIED/UNVERIFIEDを候補選択・閉輪郭検査・FEM精度の判定へ読み替えない。
[構築診断の契約](OFFSET_DEGENERACIES.md)と[GUI手順](GUI_GUIDE.md)を参照。


最小半径制約の接続（2026-09-08）: [minimum_meridional_radius_m](MERIDIONAL_RADIUS.md)を
完成曲線輪郭の任意指定として追加。PEC曲線内部の区間検査とPEC-PECのG1数値検査を課し、
構築/保存/鏡映へ保持する。既存の数値minimum_radius_mプロパティと認証の根拠は区別する。

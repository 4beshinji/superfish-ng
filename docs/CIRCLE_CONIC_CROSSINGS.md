# G03: 円と非円円錐曲線オフセットの全交点

2026-09-14 JST 後続更新：[非円対で一方の距離が0の交点](CONIC_IMPLICIT_OFFSET.md)を診断版10へ追加した。
本分類器と保存診断版9の規則は保持している。以下は各段階の履歴である。

2026-09-14 JST 後続更新：[構築版8](CIRCLE_CONIC_FILLET.md)で本分類の全元点対をフィレット候補/Caseへ接続した。
本分類器と診断版9の規則は変更していない。以下は診断実装時の受入記録である。

2026-09-14 JST、専用範囲を受入。BACKLOGの曲線同士の一般交点から、円と非円楕円/双曲線を選ぶ。
受入条件は一般二進回転と符号付き距離を保持した全交点、偽解除外、有限弧端、
接触/カスプ/潰れ円、同一中心の元点対と中心数の分離、尺度/反転/順序交換、
予算不足、診断保存/CLI/GUI、旧版再現と独立の元関数による検証。
FEMと元の構築/Case適用可否は維持する。非円弧同士の一般交点は後続に残る。

開始758ec12。楕円x²/4+y²=1と円x²+y²=9/4の既知4交点
x²=5/3,y²=7/12が診断版8で全域未確認になることを変更前に記録した。

## 円の距離式と全根の証明

非円弧には[直線交点と同じ有理チャート](LINE_NONCIRCULAR_CROSSINGS.md)を使う。
楕円はH=1+q²、X=h(1−q²)、Y=2q、h=±1、q∈[−1,1]。
双曲線はH=1−q²、X=branch(1+q²)、Y=2q、q∈(−1,1)。
左楕円チャートの両端は右側と重複するため除き、双曲線の両端は無限遠として除く。
Uを回転後の元位置分子、Vを元角度/双曲線パラメータの接線分子、S=V·Vとすると、
オフセット点はP=C+U/H+d JV/√S。dは元弧の向きを調整した符号付き距離であり、H,Sは内部で正。

相手円の中心をO、半軸をa₀、二進回転成分をc₀,s₀、k=c₀²+s₀²とする。
円オフセットの符号付き支持半径はρ=a₀√k−d₀。負のρも保持し、有限元弧の向きへ戻す。
W=(C−O)H+Uと置くと、|P−O|²=ρ²は次の元式になる。

```text
A = W·W + (d² − a₀²k − d₀²)H²
B = 2d H (W·JV)
K = 2a₀d₀ H²
(A + K√k)√S + B = 0
E = (A² + K²k)S − B²
G = 2AKS
E² − kG² = 0
```

最後の式は次数24以下の有理数多項式。√kが有理数、またはd₀=0なら、
(A+K√k)²S−B²=0を直接使えて次数12以下になる。
既存Sturm法で平方因子を除いた全実根を分離した後、各根でE+G√k=0と、
A+K√kおよびBの反対符号（両零を含む）を証明する。
二乗後の根だけでは元の交点としない。零はgcd/Sturm根数、非零は有理区間分離で証明し、
正平方根を含む符号は元符号と二乗差から確認する。新しい外部資料や数式処理依存は使っていない。

## 有限所属・接触種別・潰れ円

非円元点箱と中心箱は既存の囲み処理を使う。
非潰れ円の元局所座標はR₀ᵀ(P−O)/(ρ√k)であり、分母の符号も保持する。
局所成分が厳密零なら、円への所属証明から他成分は厳密±1となる。
これにより両方の有限弧の開始/終了0を近接判定でなく等号として識別する。
それ以外の有限所属は、元二進パラメータに対する既存の認証付き三角/双曲線境界で確認する。

非円オフセットの速度係数が零ならCUSP。正則時の円との接触はW·V=0で判定できる。
法線変位JVはVに直交するため、(P−O)·Vの零判定がこの有理多項式へ帰着する。
非零ならTRANSVERSE、零ならREGULAR_TANGENCY。相手円が潰れている場合はCOLLAPSED_CIRCLEを優先する。
同じ中心を持つ異なる非円元点は、既存の同一円錐曲線の反射定理と根の反射等号でまとめる。
証拠には全元点を残し、元点対数と有限中心数を区別する。

ρ=0はd₀>0かつd₀²=a₀²kの厳密比較で判定する。
交わる場合には有限円弧内の全パラメータが同じ点に写るためINFINITE_PARAMETER_PAIRSとなる。
非円側が有限範囲外、または支持自体が離隔なら0中心/無限対なし。
実装中、交点が一つもない場合にcircle_collapsedがfalseになるメタデータ誤りを発見し、
失敗を再現してから入力円の厳密比較へ修正した。根、中心、有限所属の計算はこの修正で変えていない。

公開診断の予算はチャート毎10,000分割箱、根毎512細分。係数演算時間の上限ではない。
元符号・根箱・有限所属・同一中心の証明が不足したらUNVERIFIEDで、中心総数を返さない。
記録済み一般二進回転の単独smokeでは1条件96.146秒、独立50条件の総計は155.833秒だった。
これは同じ環境での観測値であり、実行時間の保証ではない。

## 版・保存・CLI・GUI

新規normal_offset_diagnosisとconstruction_offset_diagnosisは診断版9。
旧版8の分類器を`_classify_offset_degeneracies_v8`として固定し、旧1〜8の保存文書は元版の規則で再計算する。
構築版1〜7は変更しない。新しい診断結果を元の候補indexや構築Caseへ暗黙に適用しない。
構築版5/6/7が保持する実探索区間・符号付き距離を引き継ぐ。
公開要求のフィールドは従来通り厳密検査し、新しい内部根予算を未対応キーとして黙認しない。

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m superfish_ng diagnose-offsets examples/construction/circle_conic_offset_diagnosis_request.json --out out/circle-conic-diagnosis-new.json
```

この合成例は冒頭の既知4交点で、実CLIも4中心/有限範囲完了を保存して終了0。
元構築版5の候補なし/未確認と新版の診断完了は両立する。新版でフィレットを構築する接続は後続課題。

変更前の自前診断版8の全文書2件を`tests/fixtures/offset_diagnosis_v8_circle_conic.json`へ保存。
164639 bytes、SHA256 `216a030a4f5520c03fd033ced818f0be635a9dfb0a703016153071a84a6feed9`。
選択済みCaseと未確認構築の両方を保存/再計算/CLI/GUIで全文書照合した。旧版資産ではない。

## 独立検証と受入の範囲

集約は`out/circle-conic-crossings-20260914/acceptance.json`。
着手時の不変量は`baseline.json`。新規8unitは9.353秒でPASS（`first-unit.log`）。
関連73unitの初回123.378秒は68合格/5失敗で、失敗は旧公開版番号・旧対応範囲・
現在有効になった版番号を改変入力としていた期待に限られた（`focused.log`）。
診断専用の旧範囲テストは_v6/_v8へ固定し、公開版9と旧全文書再現は別テストで検査する。
CLI未確認例は今も未対応の非円弧同士へ変更し、以前の例の新しいDISJOINTも検査した。
修正対象6件と追加2モジュール14件の20unitは4.834秒、19合格/旧範囲期待1失敗。
その1件も旧版へ固定して0.008秒PASS。関連87件それぞれの最終状態が合格している。
87件の一括全再実行ではない。途中の失敗、零長等の旧検査、許容差は保持した。
離隔した潰れ円のメタデータは`collapse-metadata-before-fix.log`で失敗を再現し、上記修正対象に含めた。

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_circle_conic_crossings test_line_noncircular_crossings test_algebraic_circular_offsets \
  test_offset_degeneracies test_same_conic_offset_intersections test_construction_diagnostics \
  test_tangent_construction test_conic_fillet test_line_conic_fillet test_algebraic_conic_fillet \
  test_finite_circular_crossings test_line_noncircular_offset_contacts
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_circle_conic_crossings.py --out out/circle-conic-independent-new
```

専用validatorは140桁の元三角/双曲線の単位法線変位と円距離式を評価する。
距離停留点は別導出の四次式のNumPy根から元パラメータNewtonで精密化し、カスプは元曲率半径から得る。
全停留点/カスプで区切った単調区間を二分し、端点、有限相手弧、中心重複と接触種別を照合する。
製品の有理チャート、消去式、Sturmコードは参照で呼ばない。参照自体は高精度数値照合であり、
NumPyの根近似に別の認証証明があるとは主張しない。
尺度2^−60/1/2^60、両枝、反転/交換、正負の円支持半径、一般回転、有限制限と特殊ケースの
初回50条件がPASS。メタデータ修正後は影響する潰れ円の入射/離隔/有限範囲外の3条件を実行し、0.027105秒PASS。
その後、一般二進回転と負の円支持半径を同時に使う有限弧の向きを追加1条件で独立照合し、4.075243秒PASS。
重複を除く53条件。全根/中心を計算する式は維持したため、同じ一般回転の重い検証は繰り返していない。
各条件の全診断と両時点のsource SHAを保存。報告は
`out/circle-conic-independent-20260914/report.json`、`out/circle-conic-independent-collapse-20260914/report.json`、
`out/circle-conic-independent-negative-rotated-20260914/report.json`。

実Chromeは旧8/新9、円/楕円/双曲線、端点/カスプ/同一中心/潰れ円/予算不足の10入力で、
初回/実サーバー再起動各55チェック22取得がPASS。合計110チェック44取得。
全22保存ファイルの再起動前後バイト一致、2つの選択済みCaseの適用/native Case全文書一致、
改変拒否・編集時失効・Case拒否・未確認構築の適用禁止を確認した。
初回後のメタデータ修正はこの10入力の保存内容に影響せず、再起動後は修正済みsourceで検査した。
各実行中のsource変更なし/外部HTTPなし。再起動後の新規有限交点/カスプ/潰れ円3画面を目視し、
カスプの詳細JSONはCDPでも確認。報告は`out/circle-conic-browser-{initial,restarted}-20260914/report.json`。
両サーバーは正常終了で停止済み。

FEMと物理規約は変更しない。既存の構築1/5/6の実FEM尺度検査は関連unitに含めた。
今回は全suite/seed validator/Hosted CIの実行ではない。新しい外部資料・依存・旧版資産/実行・subagentなし。
新診断から円/非円フィレットへの接続、非円弧同士の一般交点、G03全体、物理ピーク収束、C00.V/V02は残る。
親33=8受入/17進行/7他未受入/1範囲外、全計画goalの継続を維持する。

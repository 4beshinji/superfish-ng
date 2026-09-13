# G03: 元の非円円錐曲線と法線オフセットの全交点

2026-09-14 JST、専用範囲を受入。開始8e5ffb8。非円曲線同士の一般処理の最初の段階として、
少なくとも一方の符号付き距離が0である楕円/双曲線の組合せを扱う。
元の二次形式への代入、全根分離、元平方根符号、有限両弧と双曲線の枝、接触/カスプと中心重複、
独立の元関数/尺度/反転/交換、予算不足、厳密CLI、旧診断1〜9/構築1〜9の保持を受入条件とする。
両方の距離が非零の一般処理や新しいフィレット構築の代用とはしない。

変更前、楕円z²/4+r²=1とz²+r²/4=1の既知4交点z²=r²=4/5は全域未確認だった。
out/conic-implicit-offset-20260914/baseline.jsonへ記録した。
構築/Case/FEMは保持し、G03全体・物理ピーク収束・C00.V/V02と全計画は継続する。

## 二次形式と消去式

オフセットを持つ曲線をsource、距離0の曲線をtargetと呼ぶ。
両距離0なら入力の第1曲線をsourceとする。両曲線は非円楕円または指定枝の双曲線。
有理チャートは既存の[直線/非円交点](LINE_NONCIRCULAR_CROSSINGS.md)と同じで、
sourceの点をC+U/H、元パラメータの接線をV/H、S=V·V>0、JVを接線の左90度回転とする。
弧の向きを補正した符号付き距離をdとすれば、オフセット点はP=C+U/H+d JV/√S。
楕円の左右2チャートの重複境界を除き、双曲線チャートの±1は無限遠として除く。

targetの半軸をa,b、二進回転成分をc,s、k=c²+s²とする。
楕円はε=+1、双曲線はε=−1で、中心Oからの変位wに対して

```text
Q(w) = b²(c wz + s wr)² + ε a²(−s wz + c wr)²
K = a² b² k²
F(w) = Q(w) − K
```

を使う。回転ノルムを1へ近似せず、双曲線の枝はこの陰関数だけで決めない。
Qの対称双線形形式をBとし、W=(C−O)H+Uと置くと、代入した元式は

```text
A = (Q(W) − K H²) S + d² H² Q(JV)
B0 = 2d H B(W, JV)
H² S F(P−O) = A + B0 √S
E = A² − B0² S
```

となる。Eは次数16以下。d=0なら余分に二乗せず、次数4以下のQ(W)−K H²を分離する。
既存の有理Sturm法で異なる全実根を囲み、各根でA+B0√S=0を再検査する。
等号はgcd/Sturm根数と正平方根の符号条件、非零は有理区間分離で確認する。
二乗式の根だけでは交点としない。根分割/符号精密化予算が足りなければ根区間と未完理由を保存する。

targetの元局所座標は((c wz+s wr)/(ka), (−s wz+c wr)/(kb))。
成分の厳密零を元平方根式で確認し、陰関数への所属が証明済みの場合に限って、
楕円の軸上成分や双曲線の頂点を厳密0/±1へ戻す。距離による端点への吸着はしない。
元の三角/双曲線関数の認証付き区間で、source/target両方の有限所属を検査する。
双曲線の他枝はEXTERIOR。所属未確認は無交点に読み替えない。

## 接触・カスプ・中心重複

正則なsourceオフセットとtargetが接する条件はB(P−O,V)=0。
分母H√Sが正なので、B(W,V)√S+d H B(JV,V)の厳密零で判定する。
sourceオフセットの速度係数1−dκが零ならCUSPを優先し、正則時はREGULAR_TANGENCYまたはTRANSVERSE。
既存の曲率式を使い、元接線の方向とオフセット速度の反転を混同しない。
同じ中心へ来る別のsource元点は、既存の同一円錐曲線オフセットの反射等号でまとめる。
全元点対はintersectionsへ残し、same_center_groupsと有限中心数を分ける。

既知の検査例は次の通り。

- 楕円半軸(2,1)/(1,2)、両距離0：z²=r²=4/5の4交点。
- 楕円半軸(2,1)と双曲線半軸(1,1)：z²=8/5、r²=3/5。指定枝ごと2交点。
- 同枝双曲線半軸(1,1)/(2,3)：z²=32/5、r²=27/5。異なる枝への所属は除外。
- 楕円(2,1)の距離1/4と元楕円(7/4,1/2)：元角度0で中心(7/4,0)の通常接触。両有限弧の開始/終了等号を検査。
- 楕円(2,1)の距離1/2と元楕円(3/2,3/4)：中心(3/2,0)でカスプ。
- 楕円(2,1)の距離2と、中心(1,0)・半軸(1,1/2)・回転πの元楕円：元角度0/πの2点が中心(0,0)へ来る。有限弧を制限した例で1中心/2元点対を確認。

消去多項式が恒等的に零なら、有限元点対の列挙としては未確認を残す。
既存の同一曲線分類が完了する場合はその結果を保持するが、異なるパラメータ表現の同一非円支持曲線などは残件。
これは一般の両非零オフセットの解法でも、そのフィレット候補構築でもない。

## API・CLI・保存版

classify_offset_degeneraciesの新規診断版10へ接続した。両距離非零の一般非円組合せは従来版9の結果を保持する。
新探索が未完了で従来の共有点証拠がある場合は、それを維持してgeneral_conic_crossing_searchへ未完了探索を添える。
以前の公開分類器本体は_classify_offset_degeneracies_v9として保存し、保存構築診断1〜9は当時の規則で再現する。
構築文書そのものは版1〜9を保持し、元構築の候補選択・Case適用可否を診断で変更しない。

独立診断要求は引き続きschema_version=1、出力normal_offset_diagnosisは版10。
距離、有限分率区間、endpoint_width、max_series_terms以外の要求制御を拒否する。
根分割max_root_boxes=10000と代数根精密化max_refinements=512は証拠へ明記する。
低水準分類器では専用検証用にこれらを指定できるが、厳密CLI要求へ未対応キーを通さない。
根箱予算は係数演算時間の保証ではない。

```bash
superfish-ng diagnose-offsets examples/construction/conic_implicit_offset_request.json --out out/conic-implicit-diagnosis-new.json
```

[この例](../examples/construction/conic_implicit_offset_request.json)は4交点の独立診断要求で、完成Caseではない。
新しい一方距離0の解析はAPI/CLIの範囲。GUIの接線構築欄へ独立診断要求を適用する機能は追加していない。
構築に付属する新規診断は版10となり、旧保存診断9は読み込み時に9のまま照合する。

## 独立検証

専用validatorは製品のチャート/消去多項式/Sturm根を数値参照に使わず、元角度/双曲線パラメータからP、
targetの二次形式F(P)、source接線とtarget勾配の内積gを別に評価する。
gの零点を1024/2048分割の二つの標本密度で探し、140桁Newton法で精密化して一致を確認する。
既知の軸と解析的な曲率カスプも加え、Fの単調区間を二分して接点を求める。
この標本探索による参照の完全性は数値検査であり、参照自体の認証付き証明ではない。
有限target所属は独立の逆回転/角度またはasinhと枝符号で確認する。

20系列×4変種の80条件が96.727825秒でPASS。尺度2^-40/1/2^40、両弧反転・順序交換、
楕円/双曲線両枝、正負距離、端点・接触・カスプ・自己接点・有限制限、一般二進回転と平行移動を含む。
200元点対と196中心を照合し、内訳は横断172、通常接触24、カスプ4。
中心区間だけでなくsource/target両元局所座標の囲み、接触種別と全数を検査した。
原曲線とそのオフセットの幾何検証であり、FEM離散化精度や物理ピーク収束を主張しない。

関連97 unittestが56.631秒でPASS。初回の新7件は6合格/テスト期待1失敗、1.333秒。
内側のtargetには反対向きの外側オフセットの根がないため、「二乗の偽解が必ずある」という期待が誤っていた。
反対向きのオフセットが(9/4,0)で触れる外側楕円(9/4,3/2)を別に用意し、要求した内側オフセットの離隔と偽解除外を確認した。
製品コードはこのテスト修正で変更していない。現行の新規診断版を確認する既存テストは9から10へ更新し、旧保存版の期待は保持した。

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_conic_implicit_offset test_circle_conic_crossings test_line_noncircular_crossings \
  test_circle_conic_fillet test_circular_fillet test_algebraic_circular_offsets \
  test_finite_circular_crossings test_general_coincident_circle_arcs test_same_conic_offset_intersections \
  test_line_noncircular_offset_contacts test_offset_degeneracies test_construction_diagnostics test_conic_fillet
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_conic_implicit_offset.py \
  --out out/conic-implicit-offset-independent-new
```

自前保存構築診断9は、開始8e5ffb8で全文再現してからtests/fixtures/offset_diagnosis_v9.jsonへコピーした。
元はout/circular-fillet-browser-restarted-20260914/downloads/endpoint-9-built-diagnosis.json、88729 bytes、
SHA256=e4c775e8e6ca1097ed3787ab44a33b11203b50774f9508d84005c74382f219d8。
新しい外部資料・依存・旧版資産/実行・subagentは使っていない。

実Chromeは7入力、初回49/実サーバー再起動47チェック、各19取得でPASS。
構築5/8/9に付く新診断10、旧保存診断9の保持、生要求からの再構築、無限候補/精度不足の適用不可、
改変拒否・編集失効・Case側beta=0の拒否と元Caseのnative出力を確認した。
再起動前後の対応する全19保存ファイルがバイト一致し、再起動後3画面を目視した。
これは既存の構築GUIの保持検証であり、新しい独立診断をGUIで操作したという証拠ではない。
両GUIサーバーは正常終了で停止済み。独立validatorと両ブラウザーの製品source300ファイルは不変。
独立診断例の実CLIも、版10/4中心/全域完了で終了0を確認した。

集約はout/conic-implicit-offset-20260914/acceptance.json。入力/個別ログ/CLI/fixture来歴も同ディレクトリ。
独立結果はout/conic-implicit-offset-independent-20260914、ブラウザーはout/conic-implicit-offset-browser-{initial,restarted}-20260914。
既存構築版5のFEM尺度unitを含むが、今回の新しい幾何のFEM精度を検査したとはしない。
構築/Case/mesh/solver/場/RFを変更しておらず、全suite/seed/Hosted CIは実行していない。
許容差/benchmarksは不変。両非零の一般交点・新候補構築・同一支持の残件、物理ピーク収束と全計画は未完。
親33=8受入/17進行/7他未受入/1範囲外、goalはACTIVE。

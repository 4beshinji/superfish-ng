# G03: 円同士の全元点対からのフィレット構築

2026-09-14 JST、専用範囲を受入。開始a354d29。BACKLOGの円同士の全候補構築を選んだ。
受入条件は一般二進回転・符号付き支持半径の全交点/有限所属と元分率順序、
同一支持円の有限端点/無限元点対、潰れ円、厳密零長、非空保持と出力誤差、
旧構築1〜8/診断1〜9、Case/CLI/GUIの保存・適用・再起動、独立幾何と実FEM尺度則。
構築版9を追加し、旧版の診断/構築や共有FEM/trimの規則を維持した。

円C=(7/8,3/8),R=5/4,角[-1,0]と円C=(0,0),R=2,角[0,1]、
距離5/8で既知中心(11/8,0)、接点(15/8,−3/8)/(2,0)、掃引atan2(3,4)。
旧探索max_boxes=128はUNVERIFIED/0候補。記録はout/circular-fillet-20260914/baseline.json。
旧版8の最終受入ブラウザー出力は変更前に全文再現してfixture化した。
非円弧同士の一般交点、物理ピーク収束、G03全体/C00.V/V02と全計画は残る。

## 支持円・有限元点対・順序の証明

既存の[根号代数による円オフセット分類](ALGEBRAIC_CIRCULAR_OFFSETS.md)と
[同一支持円の周期分類](GENERAL_COINCIDENT_CIRCLE_ARCS.md)を変更せず再利用する。
元円iの半軸ai、二進回転成分ci,si、元弧の向きσi、符号付き距離diに対し、
ki=ci²+si²、符号付き支持半径ρi=ai√ki−σi diを保持する。
√kiを1へ置き換えず、ρi<0の逆向き写像も保持する。
異なる中心ならΔ=C2−C1、L²=Δ·Δとして

```text
α = (ρ1² − ρ2² + L²)/(2L²)
B = C1 + αΔ
h² = ρ1²/L² − α²
P = B ± √h² JΔ
```

二つの回転ノルムと最後の√h²の最大3段の正平方根を既存RadicalTowerで扱う。
h²の厳密符号から支持点0/1/2個を区別する。二重の接点を近接判定で二つへ分裂させない。
同心で半径が異なる場合は離隔、同心同半径なら周期分類へ渡す。
各非潰れ円の元局所座標はRiᵀ(P−Ci)/(ρi√ki)。符号と厳密0/±1を保った区間で有限所属を判定し、
元の有向分率を囲む。両元分率の辞書式順序を分離できたときだけ候補番号を確定する。
円は許された有限弧で単射なので、異なる中心の候補は第1分率も異なる。
分率区間が重なって順序を証明できなければUNVERIFIEDで選択不可。

同一支持円は全候補周期の区間を照合する。正の長さの共有範囲は無限元点対となり、
有限番号一覧へ変換しない。孤立した共通端点は証明された元角度から両元分率を厳密に計算する。
中心は相関したρ/√kと元角度の三角関数区間から囲み、両曲線の囲みの共通部分を使う。
元角度0以外の共有端点も、この等号証明を使える場合は分率0/1のまま保持できる。
系列予算などで所属が未確認の周期は、離隔へ読み替えない。

一方の円が中心へ潰れ、他方の有限弧がその中心を通る場合は、中心1個でも元点対が無限個ある。
両円が同じ中心へ潰れる場合も同様。有限所属で除外できた場合、または異なる中心へ潰れた場合は空集合。
無限元点対の診断がCERTIFIEDでも構築/Case適用は許可しない。

等しい非零の符号付き距離では、同じ元接点である条件は
σ1(P−C1)/ρ1 = σ2(P−C2)/ρ2。両分母を交差乗算して、根号代数で成分の厳密零を判定する。
同一支持円では対応する有向単位半径の符号を比較する。負の支持半径もこの判定に含まれる。
元接点が一致した候補はZERO_LENGTHとし、零長円弧を作らない。
低水準APIで距離が異なる場合、この等距離の判定は適用せず一致状態をnullにする。

## 構築・入力・保存

既存の[有界trimとフィレット出力](CIRCLE_CONIC_FILLET.md)へ全元点対を渡す。
第1曲線の分率1/第2曲線の分率0は元曲線全体を残せる。
逆の端点による空の保持範囲は選択不可。指定半径・向き・最大角、元接点/中心/外端点の誤差上界、
丸めによる逆向き重なりを避ける有界な内側切詰め、数値G1を検査し、閉輪郭/Case検査は選択後に行う。
探索PASSと候補FORWARD、CASE_VALIDATEDを区別する。候補先頭を自動選択しない。

構築要求schema_version=9は隣接する二つのPEC円弧を要求する。
controlsはradius_m、turn_direction、max_sweep_rad、position_tolerance_m、angle_tolerance_rad、
fraction_width、max_fraction_steps、max_radical_refinements、endpoint_width、max_series_terms。
代数的な支持点は最大2個なので根分割箱予算は使わない。
max_radical_refinementsは元分率を囲む際の追加根号精密化回数で、各回の相対囲み幅は
endpoint_width/2^(8+64j)、j=0,1,...。既存の支持点有限所属分類は元の最大3回の規則を保持する。
精密化予算は実行時間の上限ではない。allow_extension、max_boxes、max_root_boxes、max_refinements、
precision_bitsなど別版のキーは拒否する。整数制御のbooleanや不正な候補番号も拒否する。
旧構築1〜8の再現規則と旧診断1〜9を保持した。構築9と診断9は別の版番号空間である。

[合成要求](../examples/construction/circular_fillet_request.json)の利用例。出力先は未使用の名前を選ぶ。

```bash
superfish-ng construct-tangent examples/construction/circular_fillet_request.json --candidate-index 0 --out out/circular-built-new.json
superfish-ng export-constructed-case out/circular-built-new.json --out out/circular-case-new.json
superfish-ng diagnose-construction out/circular-built-new.json --out out/circular-diagnosis-new.json
```

## 独立幾何・面積/体積・実FEM

専用validatorは二進回転係数を入力とする160桁の別のEuclid幾何、角度/周期区間、元曲線/有向接線で比較する。
製品のRadicalTowerや候補順序・元分率証明を数値参照には使わない。
参照側の丸め近傍の判定は数値検証用であり、認証付き証明とは扱わない。
端点、全体保持、一般回転/平行移動、正負の距離、外接/内接、負支持半径、接触前後2^-30の分離、
同一支持円の共有端点/重なり、異なる回転ノルムの同心円、片方/両方の潰れ円の28系列を用意した。
尺度2^-40/1/2^40 × 両弧反転の有無 × 順序交換の有無、計336条件がPASS。
288条件が有限、48条件は無限元点対。有限の264元点対について全数/順序/元分率/中心囲みを照合し、
198 FORWARD、48 ZERO_LENGTH、18 UNVERIFIED（全て空の保持範囲）だった。
FORWARD候補では元関数の実接点誤差≤宣言上界≤許容差、半径と数値G1も独立に確認した。

合成閉輪郭は前段の円/楕円例の第2曲線を半径2uの円へ変更したもの。u=1/32 m、
円C=(23/8,11/8)u、半径5u/4、回転−π/2、局所角0〜1.25と、
円C=(2,1)u、半径2u、角0〜πの間へ半径5u/8を挿入し、後者全体を残す。
軸と3本のPEC線分を含む6元プリミティブから7プリミティブを構築する。測定構造ではない。
α=atan2(3,4)とし、理想接点の線/円弧積分を独立に足し合わせると

```text
A = (751/256 + 153π/64 − 75α/128) u²
V = π (75395/6144 + 1299π/256 − 225α/128) u³
```

出力CaseのA=0.00983096900053497 m²、V=0.0025963867042530834 m³。
理想積分との差は約−6.568e−15 m²、+4.467e−17 m³で、絶対許容差1e−12以内。
出力の丸め/内側切詰めを含むため理想形状との厳密同一性ではない。
元P2 FEMでこのCaseと全長2倍のCaseを解いた。2354節点の座標は2倍、接続は同一、
係数場形の相関は0.9999999999999997。各2倍/元の比は次の通り。

| 量 | 比 |
|---|---:|
| 周波数 | 0.500000000000002 |
| accelerator R/Q | 0.9999999999999726 |
| circuit R/Q | 0.9999999999999726 |
| geometry factor G | 1.0000000000000016 |
| abs(TTF) | 0.9999999999999967 |

尺度則は離散化誤差や凹角を含む形状の物理ピーク収束の保証ではない。
FEM/場/RFの式・SIと正規化・許容差・benchmarksは変更していない。

## 実行記録・再現性

関連62 unittestの最終状態が全てPASS。初回の新9件は8合格/1失敗、2.564秒。
一般回転.3と.7の二進ノルムが等しいというテストの仮定が誤っていた。
同一支持の入力を±.3へ修正し、元の.3/.7が異なる同心円として離隔する検査も残した。
関連62件37.834秒は61合格/既存の診断新版期待1失敗。
開始HEADにも残っていた「新規診断は版8」という期待を現行9へ修正した。
最初の編集ではインデントを誤ってロードに失敗し、修正後の該当1件が1.486秒でPASS。
旧保存版の再現期待は維持した。これらのテスト修正で製品を変更していない。
62件の一括成功実行とは報告しない。幾何336条件とFEMの一括validatorは25.241157秒でPASS。

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_circular_fillet test_circle_conic_fillet test_algebraic_circular_offsets \
  test_general_coincident_circle_arcs test_conic_fillet test_tangent_construction \
  test_construction_diagnostics test_certified_construction test_certified_arcs
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_general_coincident_circle_arcs.GeneralCoincidentCircleArcTests.test_version_two_and_one_saved_documents_keep_original_rules_and_bytes
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_circular_fillet.py \
  --out out/circular-fillet-independent-new
```

実Chromeは各19入力、初回94/実サーバー再起動92チェック、各43取得でPASS。
初回の新構築9は生要求から候補を編集・選択して構築し、再起動後は保存文書から復元した。
旧構築5/6/7/8と新9の計5 Caseの適用/native出力、構築/診断の元バイト保存・再計算一致、
零長/未分離順序/予算不足/無限候補の選択不可、改変拒否・編集失効・Case側beta=0の拒否を確認。
対応する全43保存ファイルが再起動前後でバイト一致した。
構築済み端点・同一支持円の順方向候補/零長候補・両潰れ円の再起動後4画面を目視した。
両GUIサーバーは正常終了で停止済み。独立validator/両ブラウザーの製品source299ファイルは不変。

自前構築版8 fixtureの元はout/circle-conic-fillet-browser-restarted-20260914/downloads/endpoint-8-built-construction.json。
開始a354d29で全文再現を確認し、tests/fixtures/fillet_construction_v8.jsonへ67125 bytesを保存した。
SHA256は48a2352084a5d6e88789143a418617ee13a32d556cbecfa624527aa46358c21c。
既存5/6/7の全文fixtureも再現した。新しい外部資料・依存・旧版資産/実行・subagentは使っていない。
集約はout/circular-fillet-20260914/acceptance.json。個別入力/ログ/fixture来歴も同ディレクトリ。
独立結果はout/circular-fillet-independent-20260914、ブラウザーはout/circular-fillet-browser-{initial,restarted}-20260914。
既存構築1/2/5のFEM尺度unitと新Caseの専用検証で影響を限定し、全suite/seed/Hosted CIは実行していない。
親33=8受入/17進行/7他未受入/1範囲外、全計画goalはACTIVE。

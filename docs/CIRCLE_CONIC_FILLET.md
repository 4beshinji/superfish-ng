# G03: 全元点対からの円・非円円錐曲線フィレット構築

2026-09-14 JST 後続更新：[円同士の全元点対構築9](CIRCULAR_FILLET.md)を追加受入した。
本書の構築8と共有trimの規則は変更していない。以下はこの段階の履歴である。

2026-09-14 JST、専用範囲を受入。BACKLOGの診断済み交点から候補構築へ接続する子課題。
構築版8で円と非円楕円/双曲線の全元点対を候補へ接続した。
受入条件は元分率による候補順、全体を残す端点、厳密零長、カスプ/同一中心/潰れ円、
半径/向き/最大角と出力誤差、独立の既知幾何、反転/交換/尺度、予算不足と厳密入力、
旧構築1〜7/診断1〜9、保存/CLI/GUIの選択/適用/再起動、合成閉輪郭の面積/体積と実FEM尺度則。
円同士の全根からのフィレット構築は従来版5のKrawczyk探索が残る。
非円弧同士の一般交点、物理ピーク収束、G03全体と全計画も後続に残る。

開始2c90c5c。円C=(7/8,3/8),R=5/4、弧角[−1,0]と、楕円a=2,b=1、弧角[0,1]。
指定半径5/8・反時計回りなら、既知の中心(11/8,0)、接点(15/8,−3/8)/(2,0)、
掃引atan2(3,4)で楕円全体を残せる。旧Krawczyk探索は端点上の根を未確認とした。
変更前のmax_boxes=128の記録はout/circle-conic-fillet-20260914/baseline.json。
新版は全2根を円の元分率順に列挙し、この既知端点はcandidate_index=1となる。

## 全元点対・順序・厳密零長

[円と非円弧の全交点分類](CIRCLE_CONIC_CROSSINGS.md)を変更せず再利用し、
各非円元点と符号を保持した円の逆写像から、両方の元弧分率を認証付き区間に戻す。
その区間を辞書式順序に分離できた場合だけ候補番号を確定する。
非潰れ円は許された有限弧で単射なので、同じ中心の元点対は円側の分率を共通区間へ絞れる。
非円側の別元点は統合しない。円が第1曲線で同じ中心の場合は第2分率で順序を証明する。
隣接候補の順序を分離できなければUNVERIFIEDで、選択を許可しない。

等しい非零の符号付きオフセット距離では、同じ中心から同じ元接点へ戻る条件は、
両方の有向元接線が同方向であること。平行でない元接線は非一致と証明できる。
平行性は分類器のsource_radial_derivative_signの厳密零、方向は有理接線区間の内積符号で確認する。
円支持半径が負になった場合や、非円オフセットの速度が反転した場合にも元接線を使う。
元接点一致はfloatの距離しきい値で判定せずZERO_LENGTHとし、零長円弧を生成しない。
異なる距離を受け取る低水準交点APIは、この等距離の接点一致判定を適用しない。

潰れ円が有限非円弧と離隔するなら、完了した空候補集合となる。
交差して円側の元点が無限個になる場合は診断の証拠を保持し、有限の候補番号一覧を作らずUNVERIFIEDとする。
無限元点対の診断がCERTIFIEDでもCase適用を許可する根拠にはならない。

候補構築には既存の[出力誤差付きtrim処理](ALGEBRAIC_CONIC_FILLET.md)を使う。
第1曲線の分率1と第2曲線の分率0では元曲線全体を保持できる。
第1曲線の分率0/第2曲線の分率1による空の保持範囲は選択不可。
指定半径・向き・最大角、中心/接点/外端点の位置誤差上界と数値G1を別に検査する。
丸めた出力が元弧を逆向きに重ねる場合は既存の有界な内側切詰めを使い、その変位も誤差へ含める。
探索PASS、候補FORWARD、選択後の閉輪郭/Case合格はそれぞれ別の条件である。

## 入力・保存・利用例

構築要求schema_version=8は、選択した隣接PECプリミティブの一方が等半軸の円、
他方が非円楕円または指定枝の双曲線であることを要求する。
controlsはradius_m、turn_direction、max_sweep_rad、position_tolerance_m、angle_tolerance_rad、
fraction_width、max_root_boxes、max_refinements、max_fraction_steps、endpoint_width、max_series_terms。
根/分率/超越関数の予算不足は未確認として保存する。根箱予算は係数演算時間の上限ではない。
allow_extensionはfalseでも未対応キーとして拒否し、旧max_boxes/precision_bitsも版8では拒否する。
候補選択は明示的な非負整数に限る。旧構築1〜7の規則と旧診断1〜9の再現規則は保持した。
構築版8と新規オフセット診断版9は別の版番号空間である。

[合成閉輪郭の要求](../examples/construction/circle_conic_fillet_request.json)は次で構築・書出しできる。
出力先は未使用の名前を選ぶ。

```bash
superfish-ng construct-tangent examples/construction/circle_conic_fillet_request.json --candidate-index 0 --out out/circle-conic-built-new.json
superfish-ng export-constructed-case out/circle-conic-built-new.json --out out/circle-conic-case-new.json
superfish-ng diagnose-construction out/circle-conic-built-new.json --out out/circle-conic-diagnosis-new.json
```

## 独立幾何と実FEM

専用validatorは製品の消去多項式/Sturm根列挙を参照に使わず、140桁の元三角/双曲線式、
独立の距離停留四次式/NumPy根とNewton補正、曲率カスプ、単調区間の二分から接点を求める。
円の元分率も符号付き逆写像から独立に求める。この数値参照自体は認証付き証明ではない。
端点、両曲線全体保持、カスプ、同一中心、負の円支持半径、双曲線両枝、一般二進回転と平行移動の
11系列を、尺度2^-40/1/2^40、有向弧反転/順序交換の4変種で検査した。
44条件・100元点対について、全数/順序/中心区間/元分率、元接点の一致、半径/向き/最大角、
実際の高精度接点誤差≤宣言上界≤許容差、数値G1を照合した。
結果は91 FORWARD、5 UNVERIFIED（全て空の保持範囲）、4 ZERO_LENGTH。

合成Caseはu=1/32 mとして、6元プリミティブから7プリミティブへ構築する。
円C=(23/8,11/8)u、R=5u/4、回転−π/2、局所角0〜1.25と、
楕円C=(2,1)u、半軸(2,3/2)u、角0〜πの間へ半径5u/8を挿入し、楕円全体を保持する。
残る境界は軸と3本のPEC線分で、測定されたKEK/LANL形状ではない。
α=atan2(3,4)とすると、理想的な接点を使った独立の線/円弧/楕円弧積分は

```text
A = (751/256 + 121π/64 − 75α/128) u²
V = π (46723/6144 + 1043π/256 − 225α/128) u³
```

出力CaseのA=0.008296988212649329 m²、V=0.0018477792177466828 m³。
理想積分との差はそれぞれ約−6.566e−15 m²、+4.47e−17 m³で、宣言した絶対許容差1e−12以内。
出力の丸め/内側切詰めを含むため、理想形状との厳密な同一性とはしない。

このCaseと全長2倍のCaseを元のP2 FEMで解いた。1934節点の座標が2倍、接続が同一、
係数場形の相関は丸めの範囲で1だった。各2倍/元の比は次の通り。

| 量 | 比 |
|---|---:|
| 周波数 | 0.5000000000000018 |
| accelerator R/Q | 0.9999999999999893 |
| circuit R/Q | 0.9999999999999893 |
| geometry factor G | 1.0000000000000069 |
| abs(TTF) | 0.9999999999999942 |

これは尺度不変量の検査であり、離散化誤差や凹角を含む形状の物理ピーク収束の保証ではない。
FEM/場/RFの式、単位と正規化、許容差、benchmarksを変更していない。

## 実行済み検証と来歴

関連62 unittestが49.421秒でPASS。その後に独立な負支持半径の接点一致1件を追加し、
3.465秒でPASS。重複を除く63件であり、63件の一括実行ではない。

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_circle_conic_fillet test_circle_conic_crossings test_algebraic_conic_fillet \
  test_conic_fillet test_line_conic_fillet test_tangent_construction \
  test_construction_diagnostics test_certified_construction test_certified_arcs
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_circle_conic_fillet.CircleConicFilletTests.test_negative_circle_radius_preserves_exact_coincident_source_contacts
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_circle_conic_fillet.py \
  --out out/circle-conic-fillet-independent-new
```

初回の新8テストは7合格/1エラー、7.040秒。テスト側が存在しない--case-outを使ったため、
既存の独立したexport-constructed-caseコマンドへ修正した。
後から追加した負支持半径テストも、最初は既知の軸上接点2個だけを全根とする誤りがあった。
単位円と楕円半軸(2,1)、距離2ではs=√(1+3sin²θ)により
(s−2)(s²+2s−4)=0となる。s=2の軸上2接点に加え、s=√5−1の4交点がある。
参照を6候補/厳密零長2個へ修正し、反転と順序交換の全4条件で合格した。
これらのテスト入力/参照修正で製品コードを変えていない。
専用validatorの幾何44条件とFEMをまとめた実行は61.535295秒でPASS。

実Chromeで14入力を検査し、初回78/実サーバー再起動後76チェックが合格。
初回は生の版8要求から候補を編集して構築し、再起動後は保存済み構築/診断から復元した。
旧5/6/7と新8の計4 Caseの適用/native出力、構築/診断保存の再計算一致、
厳密零長/未完了探索/未分離順序の選択不可、改変拒否/編集失効、Case側beta=0の拒否を確認。
計64取得、対応する全32ファイルが再起動前後でバイト一致した。
再起動後の構築済み端点・同一中心・潰れ円の3画面を目視した。カスプ詳細はCDPで検査した。
両GUIサーバーは正常終了で停止済み。独立validatorと両ブラウザー実行の製品source298ファイルは不変。

自前構築版7の最終受入済みブラウザー出力を開始2c90c5cで全文再現確認してfixture化した。
元はout/algebraic-conic-fillet-browser-restarted-20260914/downloads/endpoint-7-built-construction.json、
保存先はtests/fixtures/fillet_construction_v7.json、53003 bytes、SHA256は
e122622fd9ccf6f23265d99942f85befcd44688a919225eb9c5100504794ffaf。
先に試した開発途中のendpoint-constructed.jsonは全文再現に失敗したため採用していない。
既存版5/6のfixtureも全文再現が合格した。新しい外部資料・依存・旧版資産/実行・subagentは使っていない。

集約はout/circle-conic-fillet-20260914/acceptance.json、個別ログ/入力/fixture-provenanceも同ディレクトリ。
独立結果はout/circle-conic-fillet-independent-20260914/report.jsonと各元点対/FEM出力、
ブラウザーはout/circle-conic-fillet-browser-{initial,restarted}-20260914/report.json。
既存構築1/5/6のFEM尺度unitと新Caseの直接検証で影響を限定し、全suite/seed/Hosted CIは実行していない。
G03全体・C00.V対象版/必須集合・V02利用者業務と全計画は未完。
親33=8受入/17進行/7他未受入/1範囲外を維持し、goalはACTIVE。

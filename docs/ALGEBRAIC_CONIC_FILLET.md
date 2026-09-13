# G03: 全根列挙からの直線・円錐曲線フィレット構築

2026-09-14 JST、専用範囲を受入。[全交点診断](LINE_NONCIRCULAR_CROSSINGS.md)から
新しい構築版7へ接続したG03子課題。円/楕円/双曲線と直線の全元点対を列挙し、
候補順、端点で残す範囲、指定半径/向き/最大角、出力誤差とCaseを別々に検査する。
関連71テスト（70件と追加1件）、独立非円36条件/円24条件、FEM尺度不変量、
Chrome初回/実再起動138チェック54取得が合格。G03全体と全計画は未完。

## 着手時の不変量と受入条件

開始HEADは`a1640d0`。楕円a=2,b=1の元始点(2,0)、半径5/8、直線方向(3,4)に対して、
中心(11/8,0)、直線接点(15/8,−3/8)の既知フィレットが旧探索では境界上のため未確認になる。
線分を(−9/8,−35/8)→(39/8,29/8)、弧を開始0/掃引1とすると、接点分率は(1/2,0)。
元楕円全体を残せること、単位法線変位、半径と掃引atan2(3,4)を探索から独立に確認した。
この入力には別の内部元点対もあるため、既知の端点候補は直線分率順でindex=1になる。

受入条件は円/非円楕円/両枝双曲線、正負方向・元曲線交換・明示延長、
端点/接触/カスプ/同一中心、全候補順と予算不足の未確認、空でない保持範囲、
指定半径/最大角・位置誤差上界/G1、閉輪郭/Case、旧版の再現、保存/CLI/GUIの適用と再起動。
FEMの式・SI/peak-phasor/R/Q定義・許容差・モード順の契約は変更しない。

## 全元点対と候補順の証明

`algebraic_offset_parameters.intersect_algebraic_line_offsets`は既存の有理チャート/Sturm根分離、
元平方根符号、有限所属の証明を再利用する。非潰れ円にも同じチャートを許可する内部引数を追加した。
既存診断の呼出しではその引数はfalseなので診断版8の結果は変えない。
二進回転のc²+s²は厳密に保持する。非潰れ円のオフセットは単射の半径倍率変換なので、
異なる元点の中心は同じとしない。潰れ円は固定済み診断版6の規則で確認する。
潰れた中心と有限線分が離隔なら0候補でPASS、交わる場合の無限元点対はUNVERIFIEDとし、
有限候補indexを作らない。

各根の元弧分率は既存の認証付き逆三角/双曲線関数で囲む。直線分率は中心箱を方向ベクトルへ
射影し、厳密なSTART/ENDなら探索区間端をそのまま使う。元点対は同じ中心でも統合しない。
同じ中心の直線分率箱を共通の包含区間に揃え、元曲線の分率対で辞書式に並べる。
直線が先で中心が同じなら元弧分率が順序を決める。隣接候補の順序が区間で分離できなければ、
全体をUNVERIFIEDとして選択を拒否する。source_root_index、center_group、接触種別と分率証拠を保存する。

構築要求は`schema_version=7`、隣接するPECの直線1本と円錐曲線弧1本。
必須controlsは`radius_m`、`turn_direction`、`max_sweep_rad`、`position_tolerance_m`、
`angle_tolerance_rad`、`allow_extension`、`fraction_width`、`max_root_boxes`、
`max_refinements`、`max_fraction_steps`、`endpoint_width`、`max_series_terms`。
旧Krawczyk用`max_boxes`/`precision_bits`や未対応キーは拒否する。
根・分率・有限所属・順序の予算不足を各stageに保存し、確認済み候補があっても全探索未確認なら接続しない。

## 出力幾何と厳密な零長

新しい`algebraic_conic_fillet`は、既存`conic_fillet`から切り出した有限延長/出力検査を使う。
版7だけ、先行曲線の分率1と後続曲線の分率0で元primitive全体を保持できる。
先行分率0/後続分率1の空範囲は拒否する。元弧の自動延長は行わず、線分の延長は明示指定とする。
半径/向き/最大角、丸め後のtrim/fillet/中心/外側端点の誤差上界、重なり検査と数値G1を保持する。
位置誤差の証明、数値G1、閉輪郭とCaseの検査は別の証拠である。

実装中に、楕円(2,1)、開始−0.1/掃引3.4、直線x=2、符号付き距離2の元点(2,0)で、
厳密に同じ二接点が丸めた分率によって約9.1e−14離れ、SWEEP_LIMITになる不変量違反を再現した。
等しい符号付き距離では、元接線が同じ向きに平行なら接点は一致する。
元射影導関数の厳密零と、向きを含む接線内積の区間符号からこれを証明し、
浮動小数点のtrimより前にZERO_LENGTH/距離0を返す。反対向きなら距離2|d|であり、
内積符号が未確認なら候補を確定しない。旧構築版5/6の丸め規則は維持した。

構築版1〜6は従来の経路を保持する。共有処理の変更前に自前版5/6の選択済み全構築文書を保存し、
変更後の全体再計算一致を検査した。fixtureは`tests/fixtures/fillet_construction_v5_v6.json`、
SHA256は`fab22e8ba7e7d03f4eeb596ac791fcd3a8e1ce086c33fa7c4322757c1cc53e19`。
診断文書の版は8のままで旧1〜8を保持し、構築5/6/7を受け取れるようにした。
構築版7と診断版7は別の版番号空間である。

## 独立検証と実行記録

記録の基点は`out/algebraic-conic-fillet-20260914/`、集約は`acceptance.json`。
着手時の既知解は`initial-invariant.json`/`baseline.log`、零長の修正前失敗は
`zero-contact-invariant.log`/`zero-contact-failing-test.log`に保存した。

関連70unittestは39.042秒でPASS（`focused.log`）。共有trimの直接消費先である
`test_conic_fillet`/`test_line_conic_fillet`の既存FEM尺度検査、構築/診断再実行も含む。
その後に追加した円チャート1テストは4.073秒でPASS（`circular-charts.log`）。
回転0/0.3、距離0.5/3、尺度2^−60/1/2^60、順序交換の24条件を別の120桁円交点式と照合した。
71件の一括再実行をしたという意味ではない。

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_algebraic_conic_fillet test_line_conic_fillet test_conic_fillet \
  test_tangent_construction test_construction_diagnostics \
  test_line_noncircular_crossings test_line_noncircular_offset_contacts \
  test_algebraic_root_signs test_polynomial_roots test_offset_intersections test_normal_offsets
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_algebraic_conic_fillet.AlgebraicConicFilletTests.test_circle_charts_preserve_rotation_norm_reversed_radius_and_scale
```

`scripts/validate_algebraic_conic_fillet.py`は独立の140桁元三角/双曲線式、射影極値と単調区間二分法で
9系列×4変種=36条件を照合する。尺度2^−40/1/2^40、反転/交換、端点/カスプ/同一中心、一般回転と
双曲線両枝を含む。全元点対/順序/零長/空範囲/最大角と、出力接点の実際の誤差≤宣言上界、G1を検査する。
初回は独立参照側が同一中心の直線分率の微小な計算差を順序としたため途中失敗。
参照側で同一中心を揃えた実行は36条件全て完了し、その後のFEM比較でdriverの`.mesh`参照が失敗した。
`.space.geometry`へ修正しFEM部だけ再実行、4.083486秒でPASS。
製品コードはこの参照/driver修正で変更していない。36条件は`independent-corrected.log`の全完了行と
事後集約`geometry-completion.json`が証拠であり、成功した一括driver報告や個別全記録はない。
現在のdriverは`--only geometry|fem|all`を持ち、全実行ではFEM前に幾何報告を保存する。

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_algebraic_conic_fillet.py --only geometry --out out/algebraic-fillet-geometry-new
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_algebraic_conic_fillet.py --only fem --out out/algebraic-fillet-fem-new
```

`examples/construction/algebraic_endpoint_fillet_request.json`は合成の軸接続閉PEC輪郭。
最初の負zを含む試案は既存の軸[0,L]規約で拒否されたため、適正な端壁/段差を持つ入力へ修正した。
候補0で全元楕円を残す7primitiveのCaseになる。u=1/32、α=atan2(3,4)とすると、独立の解析積分は
A=(13/4+3π/2+325/512+25α/128)u²、
V=π(10+3π−1/2048−247/768+25α/64)u³。
実測A=0.008518396890328007 m²、V=0.0018555456059688837 m³は両参照値と倍精度で一致した。
P2曲線FEMの1倍/2倍、1354節点で同じ接続と2倍の座標、係数場の相関1を確認。
比は周波数0.5、両R/Q=0.9999999999999937、G=1.000000000000002、TTF=1.0000000000000013。
FEM報告/場は`out/algebraic-conic-fillet-fem-20260914/`にある。
これは尺度/場形/RFの不変量であり、離散化誤差の上界や角を含む形状の物理ピーク収束ではない。

## 保存・実ブラウザーと残件

Chromeは11入力を初回72チェック、実サーバー再起動後66チェック、各27取得でPASS。
旧構築5/6、新7の端点/円/楕円の選択済みCase、端点/同一中心/カスプ/潰れ円/予算/位置精度の
候補表示を確認した。初回には新版3入力で候補選択前表示と編集失効を追加検査したため6チェック多い。
5つの選択済みCaseを編集画面へ適用し、native Case書出しの全内容を照合した。
元Caseのbeta=0は候補表示時に未完成入力として保持され、選択後Case検査で拒否される。
ZERO_LENGTHや未完了探索の選択禁止、保存内容改変拒否、要求編集時の結果失効、拒否後の再読込復旧も確認。
構築/診断/Caseの全27保存ファイルは実再起動前後でバイト一致、外部HTTPはなく製品sourceも不変。
初回の端点構築/同一中心/カスプの3画面を目視し、カスプ詳細はCDPでも確認した。
報告は`out/algebraic-conic-fillet-browser-{initial,restarted}-20260914/report.json`。
両サーバーは正常終了で停止済み。

今回の検証は上記専用範囲。全suite/seed validator/Hosted CIは実行していない。
FEMの共通式は変更せず、既存直接消費先と新しい実FEM尺度比較で影響を限定した。
新しい外部資料・依存・旧版資産/実行・subagentは使っていない。
曲線同士の一般交点/重解、G03全体の受入、物理ピーク収束、C00.V/V02は残る。
親33=8受入/17進行/7他未受入/1範囲外と全計画goalの継続を維持する。

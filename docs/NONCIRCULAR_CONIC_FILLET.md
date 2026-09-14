# G03: 非円円錐曲線同士の全元点対からのフィレット構築

2026-09-14 JST、開始HEAD c21c54f。BACKLOGの一般非円フィレット構築を選択した。
受入条件は、有限オフセット交点の全元点対と辞書式順序、同一中心の別元点対、
共有端点・カスプ・厳密零長、非空保持と出力位置上界、旧版再現、Case/CLI/GUI操作、
独立幾何と生成Caseの解析積分・実FEM尺度則である。検証結果は末尾に記録する。

## 元点対を保持した構築

構築版10は2本の非円楕円弧または双曲線弧を受け付ける。
指定半径R>0、回転方向σ∈{−1,+1}から、両元曲線の有向左法線距離d=σRを設定する。
次の既存分類を順に再利用する。

1. [主軸表現が異なる同一支持](REPARAMETERIZED_CONIC_OFFSETS.md)の同じ向き補正距離。
   正長の共有範囲は無限元点対。孤立した共有端点と全ての有向反射元点対を展開する。
2. [同じ支持の等絶対距離・反対枝](EQUAL_DISTANCE_CONIC_BRANCHES.md)。
   同じ物理枝の反対法線側は離隔、反対双曲線枝は有限所属後の0/1/2中心を使う。
3. [一般有限射影と相手実点回復](GENERAL_CONIC_OFFSET_INTERSECTIONS.md)。
   元射影の各根と全相手実元点から、距離符号・有限所属を満たす対を使う。

中心数を候補数へ読み替えない。同じ第一元点に相手の2足がある場合は、証明済みの
第一元点IDで第一分率区間を共通化し、第二分率で順序を判定する。
別の第一元点なら第一分率区間の厳密分離が必要。中点による仮ソートの後にこの分離を証明する。
根号の局所座標から元の有向分率を囲み、atan/近似値の大小だけで候補番号を確定しない。
要求幅・予算で所属、元点同一性または順序を確定できなければUNVERIFIEDで選択不可。

同一支持の共有端点は元パラメータ等号から両分率を厳密に求める。
反射元点は既存のincluded_parameter_pairsを全て展開し、共有端点との第一元点同一性と
中心重複を別々に証明する。反射2点は別の元接点である。
一般交点では、有向元接線が非平行なら両元接点は異なる。
平行なら元接線区間の内積符号と距離の符号から元接点一致を判定する。
オフセットがカスプでも元円錐曲線の接線は正則なので、この判定を適用できる。

元接点一致はZERO_LENGTHとして一覧に残す。出力丸めで微小な円弧を作らない。
全元点対の列挙がPASSでも、個々の候補には最大掃引角超過、空保持弧、出力精度不足があり得る。
第一分率1と第二分率0はそれぞれ元弧全体を保持できる。第一0と第二1は保持弧が空になる。
選択可能なFORWARDだけを既存の共通フィレット出力処理へ渡す。
指定R・中心・回転方向を保ち、trim接点・円弧接点・中心・残す外端点の誤差上界を
position_tolerance_mと個別に比較する。G1は別の浮動小数点角度検査、閉輪郭/物理条件は別のCase検査である。

反転は保存された元角度範囲に対して評価する。既存EllipseArcの開始角正規化は二進πを使うため、
反転前の厳密共有端点が反転後の有限弧へ厳密に残るとは限らない。
独立検証も真のπによる物理点と正規化後の有限範囲を照合し、範囲外の端点を強制的に戻さない。

## 入力・保存・操作

新しい例は[noncircular_conic_fillet_request.json](../examples/construction/noncircular_conic_fillet_request.json)。
schema_version=10、非円2弧、pair_start、完全なcase_templateを指定する。
必須controlsはradius_m、turn_direction、max_sweep_rad、position_tolerance_m、angle_tolerance_rad、
fraction_width、max_root_boxes、max_refinements、max_fraction_steps、endpoint_width、max_series_terms。
延長は非対応。allow_extension、旧探索用max_boxes、未知キー、不正な数値/整数は拒否する。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m superfish_ng construct-tangent \
  examples/construction/noncircular_conic_fillet_request.json --candidate-index 0 \
  --out out/noncircular-example-new.json
```

出力は新規パスに保存する。候補番号を省くとCase未確定のプレビューになる。
CLI/GUIとも明示選択後に全Caseを検査し、検証された形状と計算条件だけを適用する。
構築版1〜9の再現規則は変更しない。付属診断は現行13を使い、保存診断1〜13を保持する。
構築10と診断12以下の新しい組合せは拒否する。構築と診断は別の版番号空間である。

## 独立な幾何と実FEM

最初の不変量は、中心(0,2)、半軸(2,1)の反対双曲線枝をパラメータ
第一[−0.5,0.5]、第二[0.5,−0.5]、d=2で結ぶ例である。
既知中心(0,2)、元接点(2,2)/(−2,2)、半径2の上半円がある。
変更前の版5/max_boxes=8はUNVERIFIED・0候補・未解決3箱だった。
新方式は両分率1/2、厳密中心、正則接触の1候補を列挙する。
記録はout/noncircular-conic-fillet-20260914/baseline.json。

専用検証器は元の三角/双曲線関数と単位法線をDecimal 140桁で直接計算する。
一般位置6例は独立した3×3円錐曲線/円行列と5×5 Sylvester行列式、
2048/4096点走査と二分法で元候補を求め、相手元接線に垂直な足から符号付き接点を照合する。
数値走査は完全性証明ではない。共有端点、同一中心の4足、反対枝、反射元点は
別の解析不変量/元法線成分の二分法で検査し、2^−40/1/2^40尺度と逆順反転を含む。
元カスプ/相手カスプは既知四分円の接点のみを別に確認し、その既知対を全根リストとは主張しない。
各参照対で分率・中心囲み・順序・零長/掃引/空保持の状態、生成trim/円弧接点の誤差上界、G1を照合する。

合成Caseはzを移動して軸を[0,L]にそろえた反対双曲線と上半円であり、測定空洞ではない。
x=z−z中心、a=2、b=1、H=2、t=0.5とすると上境界は
|x|≤aでr=H+sqrt(a²−x²)、a≤|x|≤a cosh(t)でr=H−(b/a)sqrt(x²−a²)。
軸と垂直端面で閉じた連続形状の独立積分は

```text
A = 2aH cosh(t) + πa²/2 − ab[cosh(t)sinh(t)−t]
V = π{2aH² cosh(t) + Hπa² + 4a³/3
      − 2Hab[cosh(t)sinh(t)−t]
      + 2ab²[cosh³(t)/3−cosh(t)+2/3]}
```

Caseの連続面積/体積と比較し、実際にP2/二次曲線FEMで尺度1と2を別々に求解する。
同じメッシュ接続・2倍座標、係数場形、周波数1/2、両R/Q・G・TTFの不変性を確認する。
これらは相似不変量であり、離散化誤差、物理表面ピーク収束、全形状の精度保証ではない。

## 検証記録と来歴

本段階は既存の独自分類・分率囲み・共通出力処理を再利用した。
新規外部資料/コード、旧SUPERFISH、追加依存、subagentは使用していない。
自作の受入済み構築9を開始HEADで全再現してからtests/fixtures/circular_fillet_v9.jsonへ保存した。
53,925 bytes、SHA256 ad2b9fe40c302939192954ed55e6bc5fd8f4e900089549847985db02191f642d。
元データは前段階の再起動Chrome取得であり、来歴は
out/noncircular-conic-fillet-20260914/fixture-provenance.jsonにある。

初回の新9テストは9.408秒PASS。直接利用する分類/GUI/保存経路を含む関連57テストは42.890秒PASS。
対象はtest_noncircular_conic_fillet、test_conic_offset_intersections、test_equal_distance_conic_branches、
test_reparameterized_conic_offsets、test_gui_tangent、test_circle_conic_fillet、test_circular_filletと、
test_tangent_constructionの再現、test_certified_constructionの版1/2、test_conic_filletの版5Case検査。
版3/4の保存/GUI/厳密入力/解析面積も別の2ケースで確認し、0.665秒PASS。旧版だけのFEMは再実行しない。

専用検証の最終結果は32条件・61参照元点対、146.511秒PASS。
一般6条件の16対、解析系24条件の43対、既知カスプ2条件の2対を区別している。
987ファイル（src/tests/scripts/examples）は開始終了で不変。
連続面積15.1289918351868313 m²、体積167.1595705414297741 m³。
両尺度の相対差は面積0、体積2.22045e−16。
実FEMは各7,519幾何節点で同じ接続、場係数相関1.0000000000000002。
尺度2/1比はf=0.4999999999999984、両R/Q=1.0000000000000195、
G=1.0000000000000007、TTF=1.000000000000004。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_noncircular_conic_fillet.py \
  --out out/noncircular-conic-fillet-independent-unique
```

既存ディレクトリを上書きせず、--only geometry/fem/allで範囲を明示できる。
今回の報告はout/noncircular-conic-fillet-independent-fixed-20260914/report.json。
初回は一般6例と反対枝の検査後、共有端点の反転参照が誤って2対を期待して停止した。
正規化された開始角は4−2×二進πであり、元の厳密端点0は実際の弧外。
製品の1候補を変更せず参照の有限所属を修正し、専用全検査を再実行した。
最初の合成Case作成では軸が[−L/2,L/2]だったため、既存Case検査が正しく拒否した。
軸を[0,L]へ平行移動してから正式な例とした。許容値・FEM・既存出力処理は変更していない。

Chrome153.0.8010.36は9入力、初回56/サーバー実再起動後54チェック、計42取得がPASS。
元Case全体の適用/出力、全構築/診断、初回と再起動の21組の保存バイト一致、
ZERO_LENGTH/無限対/出力精度不足/不正beta/改変拒否を確認した。
3画像（構築Case、同一中心4足、再起動後カスプ）を目視確認。
実行中の製品307ファイルは不変、外部HTTP要求0、各Chromeと専用GUIは終了を確認した。
GUI停止は記録PIDと専用argvを照合して実施した。
準備スクリプトの旧fixture名誤りとpythonコマンド名の不在は、正しいパスと.venv/bin/pythonに修正して再実行した。

証拠索引はout/noncircular-conic-fillet-20260914/acceptance.json、
同ディレクトリのunit/独立/ブラウザーログ、out/noncircular-conic-fillet-browser-{initial,restarted}-20260914/report.json。
今回は新幾何の専用FEMを実行した。共有seed経路に変更がなくseed検証・全validate・Hosted CIは実行していない。
本書はG03の限定範囲の受入であり、物理ピーク収束、旧曲線入力対応、G03全体/C00.V/V02は残る。
親33=8受入/17進行/7他未受入/1範囲外を維持し、全計画goalは継続中。

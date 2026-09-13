# 同じ円錐曲線の等距離オフセットと反対枝

2026-09-14 JST。G03の一般非円フィレット構築に先立ち、全元点対列挙を妨げる
等距離の恒等零射影を分類する限定課題。専用範囲で受入済み。診断13へ接続し、旧診断1〜12/構築1〜9を保持する。

## 変更前の不変量と受入条件

開始HEAD1692c5c。双曲線 `(x,y)=(branch*2*cosh(t), sinh(t))` の右枝を `t=-.5→.5`、
左枝を `.5→-.5` とする。両方とも元進行方向の左へ同じ正距離dだけオフセットする。
双方の凸な領域から外向きのオフセットで、d=1なら離隔、d=2なら原点で接触、
d=2.25なら上下の2交点を持つ。従来の必要射影は3例とも恒等零で、診断12は未確認。
この0/1/2の独立な幾何不変量を `out/equal-distance-conic-branches-20260914/baseline.json` に保存した。

受入条件は、共通支持の厳密な判定、二進回転ノルムと距離符号、全反対枝接点、
接触/横断と有限弧端、1 ULPの差、尺度/反転/交換、精度不足、旧保存版再現、CLI/構築付属GUI。
同じ凸な枝に対する逆向き等距離オフセットの離隔も確定する。
新しいフィレット構築自体は、この分類から元点対の順序と出力誤差を確定する次段階。

## 同じ物理枝の反対法線側

楕円の内部、または双曲線の一枝が囲む凸な側を、閉凸集合Kとする。
楕円は厳密凸、双曲線の右枝は厳密凸関数の上集合、左枝はその鏡像である。
回転係数の行列 `R=[[c,-s],[s,c]]` は正の尺度を持つ回転なので凸性を保つ。

境界点Xの単位外法線Nに対し、`P=X+dN (d>0)` はKの外側にあり、Xが唯一の最近点になる。
任意の境界点Yについて支持不等式 `N dot (Y-X) <= 0` が成り立ち、

```text
|P-Y|² = d² + |Y-X|² - 2d N dot (Y-X) >= d²
```

YがXと異なれば厳密に大きい。一方、同じPが別の境界点の内向き距離dの点なら、
その点YもPから距離dであるためX=Yを強制され、法線の向きに矛盾する。
従って、内向きオフセットが反対側の境界を越えるほどdが大きくても両側は交わらない。
この証明は一枝の任意の有限弧にも適用できる。

同じ支持/同じ向き補正距離の場合は、既存の有限重なり・共有端点・自己接触分類が担当する。
主軸交換・半回転による物理枝と元パラメータ方向の変化は、既存の厳密な支持変換で補正する。
数値的に近い支持や回転にはこの証明を適用しない。

## 双曲線の反対の物理枝

まず第一曲線の主軸座標へそろえ、半軸a,b、回転ノルム `n=c²+s²` とする。
同じ円錐曲線上の異なる2点が、半径|d|の一つの円に法線接触すると仮定する。
各接点に対し、[相手実点回復](GENERAL_CONIC_OFFSET_INTERSECTIONS.md)の三次行列式は重根を持つ。
三次式は異なる二重根を二つ持てず、階数2の核点は一つなので、共通重根で行列階数が1となる。

`A=1/a², B=-1/b²` とした対角主軸形では、階数1の可能性は次の二つだけ。

| 零になる対角項 | 固有値lambda | 回復される元点 | 反対枝の可否 |
|---|---|---|---|
| `A+lambda*n` | `-A/n` | xの両符号、同じy | 反対枝を含める |
| `B+lambda*n` | `-B/n` | 同じx、yの両符号 | 実点があれば同じ枝だけ |

前者の元パラメータ正方向に対する法線距離符号は `-branch*sign(lambda)=branch`。
両枝がそれぞれの凸な領域から外向きの場合だけ、反対枝の実接点を持てる。
内向きが片方でも含まれるなら離隔する。

第一曲線の正規化座標をx=X/a, y=Y/bとし、q=y²と書く。
yは枝の頂点を結ぶ方向に直交する座標で、証拠中の `normalized_transverse_coordinate_squared` がqである。

```text
q = b²(d²-n*a²)/(n*a²*(a²+b²))
first source local  = ( branch*sqrt(1+q), ±sqrt(q))
second mapped local = (-branch*sqrt(1+q), ±sqrt(q))
center local        = (0, ±(a²+b²)/b * sqrt(q))
```

中心は第一曲線のRで物理座標へ戻し、第二曲線の元点は支持変換の逆で元の主軸表現へ戻す。
q<0なら0点、q=0なら原点側の1接点、q>0なら全支持では2点。有限弧/枝の所属は両側で別々に検査する。
`d²=n*a²` が厳密な接触条件であり、回転ノルムを1へ丸めたり距離の許容差で吸着させたりしない。
q=0では元接線が平行、q>0では横断。両側とも外向きなので速度係数は `1+|d|*|kappa|>0` でカスプはない。
元点は別の物理枝にあり、元点対は零長接点ではない。

## 実装・保存契約

`equal_distance_conic_branches.py` を新設。既存の `_support_map` で同じ物理枝を認識できない場合、
双曲線の宣言枝を反転した入力で支持全体の同一性を検査し、実際の反対枝を区別する。
絶対距離が同じ非零有理数の場合だけ適用する。異なる支持/距離にはNoneを返して一般交点の分類を維持する。
平方根区間は正規化座標で閉じ込め、有限弧判定で精度不足なら総中心数をnullにする。

新規診断13。診断12を `_classify_offset_degeneracies_v12` に固定し、保存版ごとの規則を維持する。
旧診断12で未確認だった反対枝構築を新規13で分類するが、元構築のCaseや適用可否を変更しない。
12の未確認記録を13へ番号だけ変更したものと、中心数を改変したものは再現検査で拒否する。

旧診断12 fixtureは前段階の受入済み自作Chrome取得を1692c5cで全再現した後に保存。
`tests/fixtures/offset_diagnosis_v12.json` は88,730 bytes、SHA256
`4d71a33e63253e19ebc3de2ce9b0745eb936c8539fbc80e48cd49413f11efe86`。
来歴を `out/equal-distance-conic-branches-20260914/fixture-provenance.json` に残した。
旧ソルバー、追加依存、ネットワークサービスは使用しない。新規文献を取り込まず、上の幾何/行列計算を独自に導出した。

## 検証記録

- 初回専用6テストは0.016秒でPASS。
- 診断13への接続後の関連112テストは55.486秒でPASS。
- その後に追加した主軸交換/半回転での同じ物理枝の内外法線判定もPASS。数値実装は追加前後で同じ。
- 独立検証は140桁の元点と単位法線を用い、第一曲線のオフセット中心の主軸x座標を二分法で零にする。
  実装のqの閉形式を参照値に使わない。反射した相手元点を元の主軸へ戻し、両法線位置・有限所属・速度/接触種別を比較する。
  4半軸組/3主軸表現/3尺度/4距離/4符号組の576条件、有限元点対94が一致。
- 同じ楕円・左右双曲線枝における厳密な支持半平面と最近点距離不等式1,080組も合格。
  有限サンプルを全域の証明とはせず、上の閉凸集合の一意性の論証と合わせる。
- 初回独立実行は576条件を保存した後、凸性検査のHyperbolaArc生成で位置引数とbranchキーワードが重複して停止した。
  検証器のrotation_rad引数を明示する修正後、全専用検証が2.404秒でPASS。製品の数値実装は不変。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_equal_distance_conic_branches test_conic_offset_intersections test_reparameterized_conic_offsets \
  test_conic_implicit_offset test_offset_degeneracies test_same_conic_offset_intersections \
  test_general_coincident_circle_arcs test_finite_circular_crossings test_algebraic_circular_offsets \
  test_line_noncircular_offset_contacts test_line_noncircular_crossings test_circle_conic_crossings \
  test_circular_fillet test_circle_conic_fillet test_gui_tangent
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
  scripts/validate_equal_distance_conic_branches.py --out out/<new-directory>
```

実Chromeでは新構築9/診断13、旧保存診断12、反対枝の1/2中心、距離不足、同じ枝の反対法線側、
両枝内向き、精度不足の9入力を操作した。初回51チェック21取得、実サーバー再起動後49チェック21取得、
合計100チェック42取得がPASS。全構築/診断・元保存バイト・Case適用可否・改変拒否・不正RF条件を確認。
初回2画像と再起動2画像も目視した。両サーバーはPID/argvを照合後に正常終了、外部要求なし。
数値ソース312ファイル（Python/HTML/JS/CSSは306）は検証から文書編集後まで不変。
専用検証後に追加した主軸表現テスト1件だけを別に実行し、製品/検証器を再実行して数を更新してはいない。

証拠の所在：

- `out/equal-distance-conic-branches-20260914/acceptance.json`
- 同 `initial-focused.log` / `focused.log` / `mapped-normal-invariant.log`
- 同 `independent.log`（初回検証器の引数誤りを保持）
- `out/equal-distance-conic-branches-independent-fixed-20260914/report.json`
- `out/equal-distance-conic-branches-browser-initial-20260914/report.json`
- `out/equal-distance-conic-branches-browser-restarted-20260914/report.json`

FEM/メッシュ/新規フィレット出力を変更していないため、今回のseed/FEM/全validate/Hosted CIは未実行。
許容差とベンチマークは変更していない。親33=8受入/17進行/7他未受入/1範囲外を維持する。
一般非円の全元点対からの構築、G03全体、物理ピーク収束、C00.V/V02と全計画は継続中。

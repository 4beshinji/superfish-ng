# 両非零の円錐曲線オフセット交点

2026-09-14 JST。G03のうち、[全元候補射影](GENERAL_CONIC_OFFSET_PROJECTION.md)が有限な
非円楕円/双曲線対について、相手の実元点を全回復し、向き付き距離・有限弧・枝・接触種別と
中心重複を分類する限定課題。公開診断版12。構築版は1〜9のまま。専用範囲で受入済み。

## 受入条件と変更前の反例

同心楕円 `(a,b)=(2,1)` と `(1,2)`、元角度 `[-3,3]`、両向き付き距離 `1/4` では、
射影候補は8、真の交点は4。残る4候補は相手への距離の向きが反対である。
変更前 `1cc75c1` の射影は意図どおり `target_incidence_certified=False`、公開診断11は未完。
`out/conic-offset-target-recovery-20260914/baseline.json` に基準を保存した。
必要条件の零をそのまま実交点と数えないことが、今回の独立な幾何不変量である。

受入条件は、全候補に対する実元点の存在と距離符号、有限相手弧/枝、元/相手カスプと接線一致、
一中心に複数元点対がある場合の全対保存、端点・尺度・反転・一般二進回転・予算不足、
旧保存版再現とCLI/構築付属診断GUI。恒等零の射影は有限列挙として完了させない。

## 行列束の重根からの相手元点回復

以下は独自の行列計算による導出。旧実装や外部ソルバーを参照しない。
相手の中心をO、主半軸をa,b、回転係数をc,s、`n=c²+s²`、
楕円を `epsilon=1`、双曲線を `epsilon=-1` とする。
二進回転係数を正規直交へ丸め直さず、nも厳密有理数として残す。
相手局所座標で `A=1/a², B=epsilon/b²`、オフセット中心Pの座標を(u,v)、距離をeとすると、

```text
Q = diag(A,B,-1)
C = [[n,0,-nu], [0,n,-nv], [-nu,-nv,n(u²+v²)-e²]]
p(lambda) = a²b² det(Q+lambda C)
          = c0 + c1 lambda + c2 lambda² + c3 lambda³
c0 = -epsilon, c3 = -n²e²a²b² != 0
```

射影が元の正根号で `disc(p)=0` と証明した点だけを処理する。
三次実多項式の重根rは実数で、c0が非零なのでrも非零。
`T=c2²-3 c3 c1` が非零なら

```text
r = (9 c3 c0 - c1 c2)/(2T)        （二重根）
```

Tが零なら `r=-c2/(3c3)`（三重根）。`T<0` は実重根と両立しない。
射影の `c1=E1/D,c2=E2/D`、`D>0` を保ち、rは根号多項式の分子N/分母Lとして扱う。
数体の一般除算や既約因数分解は用いない。

`A+rn` と `B+rn` がともに非零なら行列の階数は2で、核から一つの有限点を得る。

```text
X = rn u/(A+rn), Y = rn v/(B+rn)
```

階数2の対称行列の余因子は核ベクトルの外積の非零倍。
`p'(r)=0` により核点は `x^T C x=0`、さらに `x^T Q x=0` を満たす。
従ってこれは円と元円錐曲線の実接点である。
この論証で元点の存在と距離の大きさを確定し、距離の向きは次の別条件で確認する。

非円ではAとBが異なるため、二つの対角項が同時に零にはならない。
一方が零の場合、行列式とその導関数の零から対応する中心座標が零、行列の階数が1となる。
核平面と元円錐曲線の交点は、正規化座標x=X/a,y=Y/bにより次の形になる。

| 零対角項 | 既知座標 | その平方 | 自由座標の平方 |
|---|---|---|---|
| `A+rn=0` | `y=A v/((A-B)b)` | `epsilon(e²A²/n-A)/(B-A)` | `x²=1-epsilon y²` |
| `B+rn=0` | `x=B u/((B-A)a)` | `(e²B²/n-B)/(A-B)` | `y²=epsilon(1-x²)` |

自由座標の平方は有理数。負なら実点なし、零なら1点、正なら両符号の2点を保存する。
例：相手楕円(2,1)、e=14、P=(0,12)ではy=-4、x²=-15となり、実接点は存在しない。
相手楕円(2,1)、e=2、P=0では元点(±2,0)が両方存在する。

## 距離の向き、カスプ、有限弧、中心数

相手の元パラメータが増える向きの左法線は、楕円では元二次形式の勾配と逆向き、
双曲線では `-branch` 倍の向きになる。
従って相手の向き補正済み距離の符号は、楕円では `-sign(r)`、
宣言した双曲線枝では `-branch*sign(r)` と一致する必要がある。
逆符号は除外し、さらに回復した点の有限所属で実際の枝を検査する。

重根rと残る単根sによって、符号付き曲率kappaに対し `e_oriented*kappa=s/r` が成り立つ。
これは接点原点・単位法線/接線座標で行列式を
`-(q_tt+lambda)(g_normal-lambda*e_oriented)²` と因数分解して得られる。
したがって相手オフセット速度係数は

```text
1-e_oriented*kappa = (3 c3 r+c2)/(c3 r)
```

で、三重根はカスプを表す。元側の速度係数は既存射影の独立な曲率式を使う。
両側が正則なら、相手勾配と元接線の内積が零かを厳密に判定し、
`REGULAR_TANGENCY` と `TRANSVERSE` を区別する。どちらかの速度係数が零なら `CUSP`。
元/相手の接触種別はFEMの表面場ピークや誤差の評価ではない。

実装は `root_radical_arithmetic.py` の `A(q)+B(q)sqrt(S(q))` と非零分母付き比を使う。
階数1では追加の `sqrt(k)` を持つ `U+V sqrt(k)` を、符号と実ノルムで判定する。
独立な根号だと仮定しないため、従属根号による厳密接線一致も保持する。
座標は外向き有理区間とし、正規化頂点0/±1は厳密値で残す。

既存の有限弧判定へ元角度端点を渡す。元点対は一つも潰さず、同じ元候補内の相手2点、
および異なる元候補の自己接触反射定理によって中心だけを統合する。
全根、全回復、全所属、中心統合が完了した場合だけ総中心数を報告する。
予算不足・恒等零・有限所属未確認では総数はnull。既存の証明済み接触証拠は保持する。

## 実装と保存版

- `conic_offset_intersections.py` が全相手元点・接触種別・有限所属・中心統合を担当する。
- 射影のprivate handlerで同じ孤立根を再利用し、重いSturm列を相手回復のために再構築しない。
  射影専用の公開入口は従来どおり必要候補だけを返す。
- 新規診断12。診断11は `_classify_offset_degeneracies_v11` に固定し、旧1〜11を同じ規則で再現する。
  構築1〜9は変更せず、診断が有限でも未検証構築の選択・Case適用を許可しない。
- `tests/fixtures/offset_diagnosis_v11.json` は変更前に受入済みの自作ブラウザー取得。
  88,730 bytes、SHA256 `c83656d570c532208b7a3c9910dc999b907eabfaedd570d73b1055327c09f44f`。
  変更前1cc75c1で全再現してからコピーした。来歴は `fixture-provenance.json` に保存。

## 検査記録

初回の内部16テストは16.424秒で合格。公開版接続後の関連118テストは57.639秒で合格。
その後に追加した全4元点対と従属根号の2解析不変量は0.589秒で合格。実装はこの追加前後で同じ。
旧版未知を求めるテストは、旧11の規則を明示して保存契約を検査するようにし、
現在版の未知CLI例は恒等零/逆符号距離に変更した。許容差は変更していない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_root_radical_arithmetic test_conic_offset_intersections test_conic_offset_projection \
  test_primitive_polynomial_roots test_algebraic_root_signs test_conic_implicit_offset \
  test_reparameterized_conic_offsets test_offset_degeneracies test_same_conic_offset_intersections \
  test_general_coincident_circle_arcs test_finite_circular_crossings test_algebraic_circular_offsets \
  test_line_noncircular_offset_contacts test_line_noncircular_crossings test_circle_conic_crossings \
  test_circular_fillet test_circle_conic_fillet test_gui_tangent
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
  scripts/validate_conic_offset_intersections.py --out out/<new-directory>
```

独立参照は140桁の元角度/単位法線と3×3行列束/5×5Sylvester行列、相手の元角度での
`(P-C(t)) dot C'(t)=0` を使う。2048/4096点の二密度と二分法で相手実点を求め、
元の符号付き法線位置・有限元弧・回復座標・直接微分による速度/接線種別を比較する。
数値走査を完全性の証明とは呼ばず、重根/階数1/厳密端点は別の解析テストで補う。
初回7条件は数値比較すべて合格したが、終了時の全ファイル不変性検査で失敗した。
その間に編集したのは新しい保存テストと旧版期待の3テストファイルで、数値実装は変更していない。
初回ログを保持し、失敗した不変性検査を含めて確定するため、入力SHAと変更パスを保存する実行器へ修正し、
テスト編集を終えた状態で専用検証を一度再実行した。137.664秒で全ガードを含めPASS。
7条件36射影候補、独立な法線足87、符号と有限域を満たす18元点対が一致した。

既存の実Chrome driverを使い、新構築9/診断12、旧保存診断11、一般楕円4中心、双曲線2中心、
階数1の相手2点/1中心、元カスプ、精度不足の計8入力を操作した。
初回53チェック19取得、PID/スクリプトを確認して実サーバーを終了・再起動後は51チェック19取得、
合計104チェック38取得がPASS。全構築/診断の内容、元保存バイト、Case適用可否、改変拒否、
不正RF条件、保存後の復元を確認。初回3画像と再起動2画像も目視した。
作業用サーバーは両方正常終了し、外部ネットワーク要求なし。

証拠の所在：

- `out/conic-offset-target-recovery-20260914/acceptance.json`（範囲と最終集計）
- 同ディレクトリの `initial-focused.log` / `focused.log` / `extra-invariants.log`
- 同 `independent.log`（初回の数値合格と最終ガード失敗を保持）
- `out/conic-offset-intersections-independent-frozen-20260914/report.json`（最終専用PASS、全入力SHA）
- `out/conic-offset-intersections-browser-initial-20260914/report.json`
- `out/conic-offset-intersections-browser-restarted-20260914/report.json`

同じ数値ソース311ファイル（Python/HTML/JS/CSSは305）での証拠を文書編集後に照合した。
全unittest/全validate、seed/実FEM、Hosted CIは今回の専用範囲で実行していない。
新しいメッシュ/構築・場計算を変更していないためであり、過去のFEM証拠を今回の実行と数えない。

## 残件

射影が恒等零になる未分類の場合（同じ支持の逆符号等距離など）は未完。
一般非円対からの新しいフィレット構築、G03全体と対象版C00.V/利用者業務V02、
物理的表面ピークの収束を含む全計画も継続する。
親バックログ33件の状態は8受入/17進行/7他未受入/1範囲外のまま。

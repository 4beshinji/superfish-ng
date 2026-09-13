# G03: 直線と非円楕円・双曲線オフセットの接触

2026-09-14 JST、専用範囲を受入。一般円診断に続くG03の弧端/重解の限定子課題。

直線の方向D、左法線N=JD、元始点P、距離dlに対する支持線は
N·X=N·P+dl|D|。円錐曲線の中心Cと二進回転R、
Q=R diag(a²,εb²) Rᵀ（楕円ε=1、双曲線ε=−1）、W=NᵀQNとする。
W>0なら元支持線に平行な接線を持つ元曲線点は
C+σQN/√W、σ=±1。双曲線は指定された枝に属する側だけを残す。
楕円ではd=sign(span) dc、双曲線ではd=branch sign(span) dcとすると、
対応するオフセット点はC+σQN/√W−σd N/|D|。
支持線との接触条件は N·(C−P)+σ√W−(dl+σd)|D|=0。
二つの平方根を保持し、二乗差の再帰的符号で等号と1 ULPの差を判定する。

曲線の投影の導関数は(1−dc κsigned) N·p'。
楕円ではオフセット係数が元の全周で正または負なら、上の二候補が全ての極値。
ρmin=min(a,b)² L/max(a,b)、ρmax=max(a,b)² L/min(a,b)、L=√(c²+s²)なので、
d<ρmin（負のdも含む）またはd>ρmaxならこの符号を全周で証明できる。
符号が負なら極大/極小を交換する。線が値域外なら無交点、極値に等しければ
支持接点が唯一。有限弧/線分所属を追加して全有限範囲の0/1点を確定する。
双曲線の指定枝はd≥0、またはd<0かつ|d|<b²L/aなら全枝で係数が正。
W>0の唯一の元接触点が全枝の極値であり、同じ0/1点判定を使う。

上記の全域条件を満たさなくても、接触点の支持式・有限所属は検証できる。
接触点で係数が零ならカスプ接触、それ以外なら通常接触と明示する。
複数の元接点が同じ中心を与える場合を代数等号で統合する。
この場合はTANGENCY_WITNESSESとして、確認した中心数と全領域の完全性を分ける。
他の交点や、元接線と直線が平行でないカスプは後続の残件とする。

受け入れ条件は、両曲線種/双曲線両枝/一般回転の接触・1 ULP差・弧端・線分端、
正則条件の全域0/1点と非正則時の証拠限定、交換/反転/尺度、同一中心重複、
旧保存版1〜6と新規版7、CLI/GUI保存・復元と元構築の保持。
関連テスト・独立参照・実Chromeで検証し、FEM/構築・物理許容差は変更しない。
G03全体、C00.V/V02・物理ピーク収束と全計画は未完のまま維持する。

## 実装と互換性

`src/superfish_ng/line_noncircular_offset_contacts.py`が支持式・曲率半径の全域境界・
接点の速度係数・有限所属を評価する。平方根の符号と等号には既存の
`quadratic_radicals.RadicalTower`、弧端所属には既存の認証区間を使う。
予算不足なら未確認を返し、非正則時の証拠数を`finite_center_count`へ代入しない。
例えばa=2,b=1の楕円を内側へ2だけオフセットすると、左右頂点が同じ中心を与えるが、
直線x=0には別の交点もある。二つの元接点を中心一つへ統合し、全域未完了を維持する。

新規normal/construction診断は版7。旧版1〜6は当時の分類器で再検証する。
版6の自前構築診断4件を公開分類器の変更前、開始HEAD `bcdbc97`で保存した。
fixtureは`tests/fixtures/offset_diagnosis_v6_line_noncircular.json`、SHA256は
`5212e402c43fb1193e20c2b2b5491215c8384d58387ca4ad3fb954222c405593`。
GUIでは確認済み接触中心数と全域未完了を併記する。元構築・Case・適用可否は保持する。

## 検証記録

関連65unitが25.979秒で合格。新規7件と根号/円/同一支持/構築診断、conic_fillet、
直線円錐曲線の版6構築保存/GUI消費先を含む。新規テストでは独立に既知の頂点・
有理点の接触位置、厳密端点と1 ULP差、カスプ、同一中心、予算不足を確認した。
着手時の旧分類器は既知の楕円/双曲線接触4例を全てUNVERIFIEDと返していた。

専用参照は160桁Decimalで元接点から単位法線変位を求め、曲率半径の境界と照合する。
頂点の一般回転0/.3/.7/1.2、尺度2^-160/1/2^160、非主軸の既知有理接点、
双曲線両枝・反転・交換・有限範囲を含む1,944条件が0.867秒で合格。
内訳はSINGLE_TANGENCY 1,026、DISJOINT 342、TANGENCY_WITNESSES 432、UNVERIFIED 144。
参照位置に製品のQ支持接点式を再利用していない。

実Chrome初回/実サーバー再起動は各16入力・59チェック・32取得、計118チェック・64取得が合格。
旧版6/新版7の通常接触・非正則接触・カスプ・同一中心・既存有効Caseを検査した。
構築/診断32ファイルは再起動前後で全バイト一致。元構築・保存診断の完全一致、適用可否、
改変拒否・編集時無効化、外部HTTPなし、検証中の全src不変も確認した。
新版の通常接触証拠・カスプ・同一中心の3画像を目視し、確認数と全域未完了の表示を確認。
カスプの詳細JSONはCDPで検査した。両GUIはSIGINT後の終了コード0を確認して停止済み。

記録は以下の既存出力を保持する。再実行時は新しい出力先を使う。

- `out/line-noncircular-offset-contacts-20260914/initial-invariants.json`、`first-unit.log`、`final-focused.log`、`acceptance.json`
- `out/line-noncircular-offset-contacts-independent-20260914/report.json`
- `out/line-noncircular-offset-contacts-browser-initial-20260914/report.json`
- `out/line-noncircular-offset-contacts-browser-restarted-20260914/report.json`
- `out/line-noncircular-offset-contacts-20260914/verify-browser.mjs`と`browser-cases.json`

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_line_noncircular_offset_contacts test_quadratic_radicals \
  test_algebraic_circular_offsets test_finite_circular_crossings \
  test_offset_degeneracies test_construction_diagnostics \
  test_coincident_circle_arcs test_general_coincident_circle_arcs \
  test_same_conic_offset_intersections test_conic_fillet \
  test_line_conic_fillet.LineConicFilletTests.test_version6_case_area_volume_replay_and_gui
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
  scripts/validate_line_noncircular_offset_contacts.py --out out/line-noncircular-offset-contacts-independent-new
```

検証範囲は変更した幾何診断と直接消費先。既存conic_filletのFEM尺度検査を含むが、
全suite/seed検証/Hosted CIは今回実行していない。FEM・物理規約・許容差・benchmarksは不変。
全域の射影境界と平行接触式は自前に導出し、新外部資料・依存・旧版資産/実行は使っていない。
次は一般の非円交点、元接線が平行でないカスプ、曲線同士、新フィレット候補構築を限定する。

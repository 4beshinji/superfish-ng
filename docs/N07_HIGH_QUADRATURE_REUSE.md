# N07：同じ高次native組立の共有

2026-10-08 JST、N07 **DONE**。[固定12行の前後照合・費用と採用](N07_ACCEPTANCE.md)を受入した。
以下は着手時の実装/限定検査記録。測定された一原因だけを選んだ。
[N06実測](N06_ACCEPTANCE.md)で、丸めuniform反復1の高次求積確認内assembly九回が86.471秒を占めた。
元 `_quadrature` と `geometry_surface_numerics.quadrature_check` は、同じspaceの次数24を重ねて組み立てる。
受入条件は、同じN05三ケース/二反復/12行・目標/予算で前後比較し、元場/RF・親子質量を保つこと。
採用は実測終端後に決め、精度条件は変更しない。全goal/N04は継続する。

## 修正前の証拠と共有範囲

N06元球の実保存場で、二consumerが `[24,16,24]` を呼ぶことを先に再現した。
二つの24次数CSRのdata/indices/indptrは完全一致し、元RF/求積診断dictも元報告と完全一致。
「同じ24次数を一回だけ計算する」という工程条件は失敗した。新FEM/場標本は0。
これは費用の失敗で、元FEMの物理誤りを捏造しない。

`adaptive_efficiency_assembly_reuse.py` は一つのhigher-quadrature区間だけで、元assemblerが生成した一つのpairを共有する。
初回は元引数/元callableへ渡して実組立する。同じspace object、元整数次数、全operand SHAの一致だけが命中条件。
元CurvedSpaceとCurvedGeometryCandidate/RestrictedGeometry、元QuadraticTriangleのread-only配列を要求する。
全point/cell-node/全local-map配列を束縛し、変異はentry失効、組立中の変異は非成功にする。
private CSR copyをreadonlyで保管し、命中時は独立したmutable CSR copyを返す。
512 MiBを超えるentryは共有せず、元組立へ戻る。N05の32 GiB/3600秒等の予算は変えない。
区間終了でentryを破棄し、別水準/worker・eigenpair・独立参照は共有しない。
元例外を同じobjectで伝播し、module aliasを正常/失敗とも復元する。外部の競合置換は保全して非成功にする。
foreign threadを拒否する。呼出し回数と完成組立数、命中/失効/byte数を分け、lookup/copy/storeも実観測する。

`adaptive_efficiency_worker` の元高次診断二つをこの区間で囲み、量別診断と共有metadataを保存する。
元FEM/RF/指標/選択/親子restriction/求積の数値bodyを変更しない。
元workerをrawへarchiveし、元1430源のうち変更はworker一つ、元1429源は同byte。
新1432対象/1225 Python源で、通常のseed TM solveはこの共有区間を使わない。

## 独立の物理と限定検査

定数試行u=1ではHphi=r、curl_z=2。
全P2境界の別Green積分 `integral(r^p dA)=abs(closed_integral(r^(p+1)/(p+1) dz))` を用い、
cached Kの定数二次形を `4 integral(r dA)`、Mを `integral(r^3 dA)` と独立比較して相対1e-12内を確認した。
閉境界三節点の別Lagrange式とGauss6を使い、FEM cell組立式を同じ形でなぞらない。
これはMaxwell試行場/エネルギーの不変量で、cavity eigenmodeやFEMの代替ではない。
全域子spaceの `P.T M_f P` と `P.T K_f P` は元相対1e-10内。元marked-parent mass/energyの一検査もPASS。

新9個別unitを分割受入。元matrix bit一致/初回返り値object/コピー変異隔離、operand変異による失効、
別space/別次数/型不正/oversize、元例外、外部競合、foreign thread、事前拒否を確認した。
実球adaptive二水準は元 `_assemble` と指標/実ID/選択/RF/peak/求積が完全一致。
元全RF求積診断ともdict完全一致で、各水準の24次数実call/完成は1回、命中1回。
開発FEMは初回2/訂正後2/最終2の計6回、benchmarkへ数えない。

初回10検査6.939秒は8PASS/2ERROR。元の細分geometry型RestrictedGeometryを共有対象から落としていた。
明示した元二型へ訂正し、関係二検査9.110秒PASS。元科学kernel/数値条件の変更はない。
型不正を広げた一検査0.396秒FAILは、Python dict equalityが24.0/NumPy整数を24と等しいと扱い、
命中で元整数型validatorを通らないことを再現した。型を厳密に照合し、関係四検査0.849秒PASS。
失敗時のcall/完成数metadata追加後、元例外一検査0.211秒、実worker一検査8.743秒PASS。
重複実行は個別件数へ加算しない。新seed/full/legacyは0。

rawは `out/n07-high-order-reuse-20261008` の各log、`worker-before.py`、`assembly-reuse-limited-acceptance.json`。
主uv/BLAS1/明示PYTHONPATH、standard unittest。限定受入時はN07 IN_PROGRESSを維持した。
後続の固定12fresh実測と全native/全mode場/量別RF・求積・選択/実IDの前後監査は、
[N07受入](N07_ACCEPTANCE.md)で終端後に採用判断を記録した。
